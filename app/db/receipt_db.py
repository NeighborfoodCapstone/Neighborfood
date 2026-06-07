import json
import re
import sqlite3
from app.config     import DB_PATH
from app.db.base    import make_conn
from app.core.utils import to_iso, now_utc

# ── OCR 의존성 (선택) ──────────────────────────────────────────────────────
#   pip install pillow pytesseract + 시스템에 tesseract (+ 한글 데이터: kor) 설치
#   설치되어 있으면 실제 OCR 실행, 없으면 데모 항목으로 자동 폴백합니다.
try:
    from PIL import Image, ImageOps
    _PIL_OK = True
except Exception:
    _PIL_OK = False
try:
    import pytesseract
    _TESS_OK = True
except Exception:
    _TESS_OK = False

# ── OCR 파싱용 정규식 (모듈 로드 시 1회 컴파일) ───────────────────────────
RC_PRICE    = re.compile(r'(\d{1,3}(?:,\d{3})+|\d{3,})')
RC_QTY      = re.compile(r'(?:(\d+)\s*[xX×*]|[xX×*]\s*(\d+)|(\d+)\s*개)')
RC_DATE     = re.compile(
    r'(20\d{2}[-./]\s*\d{1,2}[-./]\s*\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)'
)
RC_TOTAL_KW = ('합계', '총액', '결제', '받을금액', '받을 금액', '판매합계', '합 계')
RC_NOISE_KW = ('사업자', '대표', 'TEL', 'tel', '전화', '주소', '카드', '승인',
               '거스름', '부가세', '과세', '면세', 'POS', '영수증', '매장')


# ── DB 연결 & 초기화 ───────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    """통합 DB(neighborfood.db) 연결을 반환합니다."""
    return make_conn(DB_PATH, foreign_keys=True)


def init_receipt_db() -> None:
    """receipts 테이블과 인덱스를 초기화합니다."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id            TEXT PRIMARY KEY,
                subject_id    TEXT,
                store_name    TEXT,
                purchased_at  TEXT,
                items         TEXT NOT NULL DEFAULT '[]',
                selected_items TEXT NOT NULL DEFAULT '[]',
                total         INTEGER,
                status        TEXT NOT NULL DEFAULT 'SCANNED'
                              CHECK (status IN ('SCANNED', 'VERIFIED', 'FAILED')),
                trust_delta   REAL NOT NULL DEFAULT 0,
                ocr_engine    TEXT,
                image_path    TEXT,
                scanned_at    TEXT NOT NULL,
                verified_at   TEXT,
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_receipts_subject_scanned
            ON receipts (subject_id, scanned_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_receipts_status_scanned
            ON receipts (status, scanned_at)
        """)
        conn.commit()


def row_to_dict(row) -> dict:
    """receipts Row → API 응답용 dict 변환."""
    def _loads(value):
        try:
            return json.loads(value or "[]")
        except json.JSONDecodeError:
            return []
    return {
        "id":            row["id"],
        "subjectId":     row["subject_id"],
        "store":         row["store_name"],
        "purchasedAt":   row["purchased_at"],
        "items":         _loads(row["items"]),
        "selectedItems": _loads(row["selected_items"]),
        "total":         row["total"],
        "status":        row["status"],
        "trustDelta":    row["trust_delta"],
        "ocrEngine":     row["ocr_engine"],
        "scannedAt":     row["scanned_at"],
        "verifiedAt":    row["verified_at"],
    }


# ── OCR 함수 ───────────────────────────────────────────────────────────────

def _rc_to_int(value: str) -> int:
    try:
        return int(value.replace(',', ''))
    except Exception:
        return 0


def redact_pii(text: str) -> str:
    """개인 식별 정보(주민/카드/휴대폰/사업자번호)를 마스킹해 원문을 저장하지 않습니다."""
    if not text:
        return ""
    text = re.sub(r'01[016-9][-\s]?\d{3,4}[-\s]?\d{4}', '010-****-****', text)
    text = re.sub(r'\d{6}\s*-\s*[1-4]\d{6}', '******-*******', text)
    text = re.sub(
        r'\b(?:\d[ -]?){13,16}\b',
        lambda m: '****-****-****-' + re.sub(r'\D', '', m.group())[-4:],
        text,
    )
    text = re.sub(r'\d{3}-\d{2}-\d{5}', '***-**-*****', text)
    return text


def ocr_text(image_path: str) -> str:
    """이미지에서 텍스트를 추출합니다. 라이브러리가 없으면 빈 문자열을 반환해 데모로 폴백합니다."""
    if not (_PIL_OK and _TESS_OK):
        return ""
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)
        img = img.convert('L')
        img = ImageOps.autocontrast(img)
        w, h = img.size
        if max(w, h) < 1000:
            scale = 1000 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)))
        for lang in ('kor+eng', 'eng', None):
            try:
                return pytesseract.image_to_string(img, lang=lang) if lang \
                    else pytesseract.image_to_string(img)
            except Exception:
                continue
        return ""
    except Exception as exc:
        print(f"[영수증 OCR] 인식 실패: {exc}")
        return ""


def parse_receipt(text: str) -> dict:
    """OCR 텍스트에서 매장명·구매일시·품목·합계를 추출합니다."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    store = purchased_at = total = None
    items = []

    for ln in lines:
        m = RC_DATE.search(ln)
        if m:
            purchased_at = re.sub(r'\s+', ' ', m.group(1)).replace('.', '-').replace('/', '-')
            break

    for ln in lines:
        if RC_DATE.search(ln) or any(k in ln for k in RC_NOISE_KW):
            continue
        if RC_PRICE.fullmatch(ln.replace(' ', '')):
            continue
        store = ln
        break

    for ln in lines:
        if any(k in ln for k in RC_TOTAL_KW):
            prices = RC_PRICE.findall(ln)
            if prices:
                total = _rc_to_int(prices[-1])

    for ln in lines:
        if any(k in ln for k in RC_TOTAL_KW) or RC_DATE.search(ln):
            continue
        if any(k in ln for k in RC_NOISE_KW):
            continue
        prices = list(RC_PRICE.finditer(ln))
        if not prices:
            continue
        price = _rc_to_int(prices[-1].group(1))
        if price < 100:
            continue
        name = ln[:prices[-1].start()]
        qty  = 1
        qm   = RC_QTY.search(name)
        if qm:
            qty = int(next((g for g in qm.groups() if g), 1))
        name = RC_QTY.sub(' ', name)
        name = re.sub(r'(?<!\S)[xX×*](?!\S)', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip(' .-:·')
        if not name or not re.search(r'[가-힣A-Za-z]', name):
            continue
        items.append({"name": name, "qty": qty, "price": price})

    return {"store": store, "purchasedAt": purchased_at, "total": total, "items": items}


def demo_items() -> dict:
    """OCR 실패 시 데모 화면이 항상 동작하도록 하는 폴백 항목 (화면 mock과 동일)."""
    return {
        "store":       "로컬푸드마트 한들점",
        "purchasedAt": to_iso(now_utc())[:10],
        "total":       9500,
        "items": [
            {"name": "유기농 시금치",   "qty": 2, "price": 4800},
            {"name": "친환경 우유 1L", "qty": 1, "price": 3200},
            {"name": "국내산 애호박",  "qty": 1, "price": 1500},
        ],
    }