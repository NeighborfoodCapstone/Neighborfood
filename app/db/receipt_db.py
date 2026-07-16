import json
import mimetypes
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.config import DB_PATH
from app.core.utils import now_utc, to_iso
from app.db.base import make_conn

# ── OCR 의존성: 로컬 fallback ─────────────────────────────────────────────
# CLOVA OCR 환경변수가 없거나 호출 실패 시, 설치되어 있으면 pytesseract로 fallback합니다.
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

# ── OCR 파싱용 정규식 ─────────────────────────────────────────────────────
RC_PRICE = re.compile(r'(\d{1,3}(?:,\d{3})+|\d{3,})')
RC_QTY = re.compile(r'(?:(\d+)\s*[xX×*]|[xX×*]\s*(\d+)|(\d+)\s*개)')
RC_DATE = re.compile(
    r'(20\d{2}[-./]\s*\d{1,2}[-./]\s*\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)'
)
RC_TOTAL_KW = ('합계', '총액', '결제', '받을금액', '받을 금액', '판매합계', '합 계', '총 합계')
RC_NOISE_KW = (
    '사업자', '대표', 'TEL', 'tel', '전화', '주소', '카드', '승인', '거스름', '부가세',
    '과세', '면세', 'POS', '영수증', '매장', '고객', '현금', '잔액', '포인트', '바코드'
)

# ── DB 연결 & 초기화 ───────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    """통합 DB(neighborfood.db) 연결을 반환합니다."""
    return make_conn(DB_PATH, foreign_keys=True)


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def init_receipt_db() -> None:
    """receipts 테이블과 인덱스를 초기화합니다. 기존 DB에는 필요한 컬럼을 ALTER로 추가합니다."""
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id TEXT PRIMARY KEY,
            subject_id TEXT,
            store_name TEXT,
            purchased_at TEXT,
            items TEXT NOT NULL DEFAULT '[]',
            selected_items TEXT NOT NULL DEFAULT '[]',
            total INTEGER,
            status TEXT NOT NULL DEFAULT 'SCANNED'
                CHECK (status IN ('SCANNED', 'VERIFIED', 'FAILED')),
            trust_delta REAL NOT NULL DEFAULT 0,
            ocr_engine TEXT,
            image_path TEXT,
            scanned_at TEXT NOT NULL,
            verified_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        # 기존 DB 호환: 오늘 작업에서 추가하는 디버그/검증용 컬럼
        if not _has_column(conn, "receipts", "safe_ocr_text"):
            conn.execute("ALTER TABLE receipts ADD COLUMN safe_ocr_text TEXT")
        if not _has_column(conn, "receipts", "ocr_result_json"):
            conn.execute("ALTER TABLE receipts ADD COLUMN ocr_result_json TEXT")
        if not _has_column(conn, "receipts", "raw_ocr_json"):
            conn.execute("ALTER TABLE receipts ADD COLUMN raw_ocr_json TEXT")

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
    def _loads(value, default):
        try:
            return json.loads(value or default)
        except json.JSONDecodeError:
            return json.loads(default)

    return {
        "id": row["id"],
        "subjectId": row["subject_id"],
        "store": row["store_name"],
        "purchasedAt": row["purchased_at"],
        "items": _loads(row["items"], "[]"),
        "selectedItems": _loads(row["selected_items"], "[]"),
        "total": row["total"],
        "status": row["status"],
        "trustDelta": row["trust_delta"],
        "ocrEngine": row["ocr_engine"],
        "imagePath": row["image_path"],
        "scannedAt": row["scanned_at"],
        "verifiedAt": row["verified_at"],
        "safeOcrText": row["safe_ocr_text"] if "safe_ocr_text" in row.keys() else None,
        "ocrResult": _loads(row["ocr_result_json"], "{}") if "ocr_result_json" in row.keys() else {},
        "rawOcr": _loads(row["raw_ocr_json"], "{}") if "raw_ocr_json" in row.keys() else {},
    }

# ── 개인정보 마스킹 ───────────────────────────────────────────────────────
def redact_pii(text: str) -> str:
    """개인 식별 정보(주민/카드/휴대폰/사업자번호)를 마스킹합니다."""
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

# ── CLOVA OCR 호출 ────────────────────────────────────────────────────────
_DOTENV_LOADED = False


def _load_local_env_once() -> None:
    """프로젝트 루트의 .env를 최소 파서로 읽습니다. python-dotenv 없이 동작합니다."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('\"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception as exc:
        print(f"[.env] 로드 실패: {exc}")


def _clova_env() -> Tuple[str, str]:
    """CLOVA OCR Invoke URL / Secret을 환경변수 또는 .env에서 읽습니다."""
    _load_local_env_once()
    invoke_url = os.getenv("CLOVA_OCR_INVOKE_URL", "").strip()
    secret = os.getenv("CLOVA_OCR_SECRET", "").strip()
    return invoke_url, secret


def _image_format(image_path: str) -> str:
    ext = Path(image_path).suffix.lower().lstrip(".")
    if ext == "jpg":
        return "jpg"
    if ext == "jpeg":
        return "jpeg"
    if ext == "png":
        return "png"
    if ext == "tif":
        return "tiff"
    if ext in {"tiff", "pdf"}:
        return ext
    return "jpg"


def _flatten_clova_text(raw: Dict[str, Any]) -> str:
    """CLOVA 응답에서 inferText를 최대한 넓게 수집해 일반 파서에 넘깁니다."""
    out: List[str] = []
    for image in raw.get("images", []) or []:
        for field in image.get("fields", []) or []:
            text = field.get("inferText") or field.get("value") or ""
            if text:
                out.append(str(text))
        # 영수증/문서 OCR류가 structuredResult를 반환할 때 대비
        structured = image.get("structuredResult") or image.get("receipt") or {}
        if isinstance(structured, dict):
            out.extend(_flatten_values(structured))
    return "\n".join(out).strip()


def _flatten_values(value: Any) -> List[str]:
    result: List[str] = []
    if isinstance(value, dict):
        for v in value.values():
            result.extend(_flatten_values(v))
    elif isinstance(value, list):
        for v in value:
            result.extend(_flatten_values(v))
    elif value is not None:
        s = str(value).strip()
        if s:
            result.append(s)
    return result


def clova_ocr_text(image_path: str) -> Tuple[str, Dict[str, Any]]:
    """CLOVA OCR 호출. 환경변수가 없으면 빈 문자열을 반환합니다."""
    invoke_url, secret = _clova_env()
    if not invoke_url or not secret:
        return "", {"enabled": False, "reason": "missing_env"}

    image_format = _image_format(image_path)
    request_json = {
        "version": "V2",
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "images": [{"format": image_format, "name": "receipt"}],
    }

    mime_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
    headers = {"X-OCR-SECRET": secret}

    try:
        with open(image_path, "rb") as f:
            files = {"file": (Path(image_path).name, f, mime_type)}
            data = {"message": json.dumps(request_json, ensure_ascii=False)}
            res = requests.post(invoke_url, headers=headers, data=data, files=files, timeout=20)
        res.raise_for_status()
        raw = res.json()
        text = _flatten_clova_text(raw)
        return text, {"enabled": True, "ok": True, "raw": raw}
    except Exception as exc:
        print(f"[CLOVA OCR] 호출 실패: {exc}")
        return "", {"enabled": True, "ok": False, "error": str(exc)}

# ── 로컬 Tesseract fallback ───────────────────────────────────────────────
def tesseract_ocr_text(image_path: str) -> str:
    """이미지에서 텍스트를 추출합니다. 라이브러리가 없으면 빈 문자열을 반환합니다."""
    if not (_PIL_OK and _TESS_OK):
        return ""
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("L")
        img = ImageOps.autocontrast(img)
        w, h = img.size
        if max(w, h) < 1000:
            scale = 1000 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)))
        for lang in ("kor+eng", "eng", None):
            try:
                return pytesseract.image_to_string(img, lang=lang) if lang else pytesseract.image_to_string(img)
            except Exception:
                continue
        return ""
    except Exception as exc:
        print(f"[영수증 OCR] 로컬 인식 실패: {exc}")
        return ""


def run_ocr(image_path: str) -> Tuple[str, str, Dict[str, Any]]:
    """CLOVA → Tesseract 순서로 OCR을 실행하고 (engine, text, debug)를 반환합니다."""
    clova_text, clova_debug = clova_ocr_text(image_path)
    if clova_text:
        return "clova", redact_pii(clova_text), clova_debug

    tess_text = tesseract_ocr_text(image_path)
    if tess_text:
        return "tesseract", redact_pii(tess_text), {"clova": clova_debug, "fallback": "tesseract"}

    return "demo", "", {"clova": clova_debug, "fallback": "demo"}

# ── 파싱 ─────────────────────────────────────────────────────────────────
def _rc_to_int(value: str) -> int:
    try:
        return int(value.replace(",", ""))
    except Exception:
        return 0


def parse_receipt(text: str) -> dict:
    """OCR 텍스트에서 매장명·구매일시·품목·합계를 추출합니다.

    개선 기준:
    - 데모값을 절대 넣지 않는다.
    - 마트형 영수증처럼 품목명 라인과 단가/수량/금액 라인이 분리된 경우를 처리한다.
    - 사업자번호/전화번호/카드번호/승인번호/바코드/단말기번호를 품목/가격으로 오인하지 않는다.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln and ln.strip()]
    store = None
    purchased_at = None
    total = None
    items: List[Dict[str, Any]] = []

    def clean_line(s: str) -> str:
        return re.sub(r"\s+", " ", str(s or "").strip())

    def money_tokens(s: str) -> List[int]:
        """가격 후보만 추출한다. 사업자번호/바코드 같은 긴 숫자는 제거."""
        result: List[int] = []
        for token in re.findall(r"\d{1,3}(?:,\d{3})+|\d{4,}", s or ""):
            raw = re.sub(r"[^0-9]", "", token)
            if not raw:
                continue
            if len(raw) >= 8 and "," not in token:
                continue
            value = int(raw)
            if 0 < value <= 2_000_000:
                result.append(value)
        return result

    def is_meta_line(s: str) -> bool:
        compact = re.sub(r"\s+", "", s or "")
        meta_words = [
            "사업자", "대표", "주소", "전화", "TEL", "Tel", "tel", "등록번호",
            "카드", "승인", "일시불", "신용", "현금", "체크", "단말", "가맹",
            "영수증", "교환", "환불", "고객", "포인트", "적립", "부가세",
            "과세", "면세", "공급가", "잔액", "합계", "총액", "받을금액",
            "받은금액", "거스름", "결제", "매출", "매장", "계산원",
            "상품코드", "단가", "수량", "금액", "품명", "과세물품",
            "청구액", "판매액", "부가가치세"
        ]
        if any(w.lower() in compact.lower() for w in meta_words):
            return True
        alnum = re.sub(r"[^0-9A-Za-z가-힣]", "", compact)
        if alnum and len(re.sub(r"[^0-9]", "", alnum)) / max(1, len(alnum)) > 0.7:
            return True
        return False

    def is_possible_name(s: str) -> bool:
        s = clean_line(s)
        if not (2 <= len(s) <= 60):
            return False
        if is_meta_line(s):
            return False
        if not re.search(r"[가-힣A-Za-z]", s):
            return False
        if re.search(r"\d{8,}", re.sub(r"[,\-\s]", "", s)):
            return False
        return True

    # 날짜
    for ln in lines:
        m = RC_DATE.search(ln)
        if m:
            purchased_at = m.group(0).replace(".", "-").replace("/", "-")
            break

    # 상호명
    for ln in lines:
        s = clean_line(ln)
        if re.search(r"(E[·\.\-]?\s*MART|이마트|마트|슈퍼|시장|상점)", s, re.I):
            s = re.split(r"\d{3}[- ]?\d{2}[- ]?\d{5}", s)[0].strip()
            if 2 <= len(s) <= 40:
                store = s
                break
    if not store:
        for ln in lines[:10]:
            s = clean_line(ln)
            if is_possible_name(s):
                store = s
                break

    # 합계/총액
    for ln in lines:
        if re.search(r"합계|총액|결제금액|받을금액|받은금액|판매금액|청구액", ln):
            nums = money_tokens(ln)
            if nums:
                total = nums[-1]

    if total is None:
        all_prices: List[int] = []
        for ln in lines:
            if re.search(r"합계|총액|결제|금액|청구액", ln):
                all_prices.extend(money_tokens(ln))
        if all_prices:
            total = max(all_prices)

    # 품목 추출: 품목명 라인과 가격 라인 분리 대응
    pending_name = None
    used = set()

    for ln in lines:
        s = clean_line(ln)

        # "001 품목명" 형태
        m_no = re.match(r"^\d{1,3}\s+(.+)$", s)
        if m_no and is_possible_name(m_no.group(1)):
            pending_name = clean_line(m_no.group(1))
            continue

        prices = money_tokens(s)

        # pending 품목명 + 현재 가격라인 결합
        if pending_name and prices:
            price = prices[-1]
            qty = 1
            if len(prices) >= 2 and prices[-2] > 0 and price % prices[-2] == 0:
                q = price // prices[-2]
                if 1 <= q <= 99:
                    qty = q
            key = (pending_name, price)
            if key not in used:
                items.append({"name": pending_name, "qty": qty, "price": price})
                used.add(key)
            pending_name = None
            continue

        # 같은 줄에 품목명 + 가격이 같이 있는 경우
        if prices:
            name = re.sub(r"\d{1,3}(?:,\d{3})+|\d{4,}", "", s)
            name = re.sub(r"^[#*\-\s]+", "", clean_line(name))
            if is_possible_name(name):
                price = prices[-1]
                qty = 1
                if len(prices) >= 2 and prices[-2] > 0 and price % prices[-2] == 0:
                    q = price // prices[-2]
                    if 1 <= q <= 99:
                        qty = q
                key = (name, price)
                if key not in used:
                    items.append({"name": name, "qty": qty, "price": price})
                    used.add(key)
                pending_name = None
                continue

        # 품목명만 있는 줄
        if is_possible_name(s):
            if store and s == store:
                continue
            if re.search(r"대한민국|할인점|고객센터|감사합니다|이마트\s*탄현점", s):
                continue
            pending_name = s
            continue

    if total is not None and len(items) > 1:
        items = [it for it in items if it["price"] != total]

    return {"store": store, "purchasedAt": purchased_at, "total": total, "items": items}

def empty_receipt_result() -> dict:
    """OCR/파싱 실패 시 가짜 항목 없이 빈 결과를 반환합니다."""
    return {
        "store": None,
        "purchasedAt": None,
        "total": None,
        "items": [],
    }


# 이전 함수명 호환용: 더 이상 데모 항목/데모 메타데이터를 반환하지 않습니다.
demo_items = empty_receipt_result
