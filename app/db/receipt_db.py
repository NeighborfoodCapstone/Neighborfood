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
# 품목이 아닌 메타/결제/안내 문구 키워드.
# is_meta_line()에서 실제로 사용합니다(기존에는 정의만 되고 미사용이었음).
# (2026-08-17 시정: 스타벅스 등에서 POS/카카오페이/번호/발급/가능 등이 품목으로
#  잘못 인식되던 문제를 막기 위해 키워드를 보강)
RC_NOISE_KW = (
    # 상점/사업자/연락 정보
    '사업자', '대표', 'TEL', 'tel', '전화', '주소', '등록번호', '가맹', '단말',
    # 카드/결제/승인
    '카드', '승인', '일시불', '신용', '체크', '현금', '거스름', '잔액',
    # 간편결제(브랜드 단위로만 필터 — '카카오'만으로는 '카카오닙스' 등 상품 오필터 위험)
    '카카오페이', '삼성페이', '네이버페이', '제로페이', '애플페이', 'kakaopay', 'pay',
    # 세금/합계/금액 항목
    '부가세', '부가가치세', '과세', '면세', '공급가', '합계', '총액', '받을금액',
    '받은금액', '청구액', '판매액', '매출',
    # POS/영수증/발급/번호/안내 문구
    'POS', '포스', '영수증', '발급', '번호', '가능', '교환', '환불', '고객',
    '포인트', '적립', '바코드', '매장', '계산원', '상품코드', '품명', '과세물품',
    # 표 헤더성 단어
    '단가', '수량', '금액',
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

    2026-08-22 parser v2.1:
    - 기존 스타벅스/카페형 한 줄·줄분리 파싱을 유지한다.
    - 마트형 ``순번 → 품목명 → 바코드/PLU → 단가 → 수량 → 금액`` 구조를 처리한다.
    - CLOVA가 한 행을 여러 inferText 토큰으로 쪼개도 품목 상태를 유지한다.
    - ``*231973`` 같은 PLU, 긴 바코드, ``[2,150]`` 같은 참고가를 실제 가격으로 쓰지 않는다.
    - 500/750원처럼 콤마가 없는 3자리 가격도 품목 영역에서는 허용한다.
    - ``900ML``, ``150g`` 같은 용량 토큰은 상품명에 이어 붙인다.
    - 판매총액/결제/회원/포인트 영역에 들어가면 품목 파싱을 종료한다.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln and ln.strip()]
    store = None
    purchased_at = None
    total = None
    items: List[Dict[str, Any]] = []

    def clean_line(s: str) -> str:
        return re.sub(r"\s+", " ", str(s or "").strip())

    def compact_line(s: str) -> str:
        return re.sub(r"\s+", "", clean_line(s))

    # 용량 표기(900ML/150g) 안의 숫자를 가격으로 오인하지 않도록
    # 영숫자에 붙어 있지 않은 3~7자리 숫자만 금액 후보로 본다.
    money_re = re.compile(
        r"(?<![A-Za-z0-9])(?:\d{1,3}(?:,\d{3})+|\d{3,7})(?![A-Za-z0-9])"
    )

    def money_tokens(s: str) -> List[int]:
        result: List[int] = []
        for token in money_re.findall(s or ""):
            raw = token.replace(",", "")
            if not raw:
                continue
            value = int(raw)
            if 0 < value <= 2_000_000:
                result.append(value)
        return result

    def is_total_label(s: str) -> bool:
        compact = compact_line(s)
        return bool(
            re.search(
                r"판매총액|합계|총액|결제금액|받을금액|받은금액|판매금액|청구액",
                compact,
            )
        )

    def is_item_header(s: str) -> bool:
        compact = compact_line(s)
        return bool(
            re.search(
                r"상품\(?코드\)?|품명|상품명|메뉴명|메뉴|상품내역",
                compact,
                re.I,
            )
        )

    def is_item_stop(s: str) -> bool:
        compact = compact_line(s)
        return bool(
            re.search(
                r"판매총액|판매금액|받을금액|받은금액|결제금액|결제수단|"
                r"합계|총액|부가세|회원|포인트|신용카드|카드매출|승인|할부|현금영수증",
                compact,
                re.I,
            )
        )

    def is_meta_line(s: str) -> bool:
        raw = clean_line(s)
        compact = compact_line(raw)

        if RC_DATE.search(raw):
            return True

        # T:, POS:, No:, 번호:, 발급: 같은 라벨형 메타
        if re.match(r"^[A-Za-z]{1,4}\s*[:：]", raw):
            return True
        if re.match(
            r"^(번호|발급|승인|카드|가맹|단말|전표|거래|매출전표|주문|영수증|회원|할부)\s*[:：]",
            raw,
        ):
            return True

        for word in RC_NOISE_KW:
            if word.lower() in compact.lower():
                return True

        if re.search(r"(할인|쿠폰|프로모션)", compact, re.I):
            return True

        # 전화/승인번호처럼 숫자 비중이 지나치게 높은 줄
        alnum = re.sub(r"[^0-9A-Za-z가-힣]", "", compact)
        if alnum:
            digit_ratio = len(re.sub(r"[^0-9]", "", alnum)) / max(1, len(alnum))
            if digit_ratio > 0.85:
                return True

        return False

    def normalize_item_name(s: str, strip_mart_p: bool = False) -> str:
        value = clean_line(s)
        # 마트 품목행 끝의 참고/정상가 [2,150] 등은 상품명에서 제거
        value = re.sub(r"\s*\[\s*\d[\d,]*\s*\]\s*$", "", value)

        # 순번 직후의 P는 농협/마트 계열 품목 플래그로 취급.
        # 영문 상품명 Pepsi 등의 첫 P를 지우지 않도록 한글 앞에서만 제거한다.
        if strip_mart_p:
            value = re.sub(r"^[Pp]\s*(?=[가-힣])", "", value)

        value = re.sub(r"^[#*\-\s]+", "", value)
        return clean_line(value)

    def is_possible_name(s: str) -> bool:
        value = clean_line(s)
        if not (1 <= len(value) <= 60):
            return False
        # '무'처럼 한 글자인 실제 품목은 허용한다.
        if len(value) == 1 and not re.fullmatch(r"[가-힣]", value):
            return False
        if is_meta_line(value):
            return False
        if not re.search(r"[가-힣A-Za-z]", value):
            return False
        if re.search(r"\d{8,}", re.sub(r"[,\-\s]", "", value)):
            return False
        return True

    def is_size_token(s: str) -> bool:
        return bool(
            re.fullmatch(
                r"\d+(?:\.\d+)?\s*(?:ml|l|g|kg|개|입|팩|병|캔)",
                clean_line(s),
                re.I,
            )
        )

    def is_bracket_price(s: str) -> bool:
        return bool(re.fullmatch(r"\[\s*\d[\d,]*\s*\]", clean_line(s)))

    def is_product_code_only(s: str) -> bool:
        # parser v2.1.2 masked barcode + trailing columns fix
        # 일반 PLU/바코드와 CLOVA 마스킹 바코드를 가격 후보에서 제외한다.
        value = clean_line(s)

        if not re.fullmatch(r"[*#]?\s*[\d,*#\-]+", value):
            return False

        digits = re.sub(r"\D", "", value)
        has_marker = value.lstrip().startswith(("*", "#"))
        has_mask = bool(re.search(r"[*#]{2,}", value))

        if has_mask and len(digits) >= 5:
            return True
        if has_marker:
            return 5 <= len(digits) <= 14
        return 8 <= len(digits) <= 14

    def strip_leading_product_code(s: str) -> str:
        """'바코드/PLU + 금액...' 행이면 앞의 코드만 제거한다."""
        value = clean_line(s)
        match = re.match(r"^\s*([*#]?\s*[\d,*#\-]+)\s+(.+)$", value)
        if not match:
            return value

        prefix = match.group(1)
        digits = re.sub(r"\D", "", prefix)
        has_marker = prefix.lstrip().startswith(("*", "#"))
        has_mask = bool(re.search(r"[*#]{2,}", prefix))

        is_code = (
            (has_mask and len(digits) >= 5)
            or (has_marker and 5 <= len(digits) <= 14)
            or (not has_marker and 8 <= len(digits) <= 14)
        )
        return clean_line(match.group(2)) if is_code else value

    def name_from_price_line(s: str, strip_mart_p: bool = False) -> str:
        value = money_re.sub(" ", s)
        # 단독 수량(1, 2 등)은 제거하되 900ML/150g처럼 문자에 붙은 숫자는 보존
        value = re.sub(
            r"(?<![A-Za-z0-9])\d{1,2}(?![A-Za-z0-9])",
            " ",
            value,
        )
        return normalize_item_name(value, strip_mart_p=strip_mart_p)

    # 구매일시
    for ln in lines:
        match = RC_DATE.search(ln)
        if match:
            purchased_at = match.group(0).replace(".", "-").replace("/", "-")
            break

    # 상호명
    for ln in lines:
        value = clean_line(ln)
        if re.search(
            r"(E[·\.\-]?\s*MART|이마트|마트|슈퍼|시장|상점|농협|스타벅스)",
            value,
            re.I,
        ):
            value = re.split(r"\d{3}[- ]?\d{2}[- ]?\d{5}", value)[0].strip()
            if 2 <= len(value) <= 40:
                store = value
                break

    if not store:
        for ln in lines[:10]:
            value = clean_line(ln)
            if len(value) >= 2 and is_possible_name(value):
                store = value
                break

    # 총액. CLOVA가 '판매총액' / '8,560'을 서로 다른 토큰으로 쪼개는 경우도 처리.
    for i, ln in enumerate(lines):
        if not is_total_label(ln):
            continue

        values = money_tokens(ln)
        if values:
            total = values[-1]
            break

        for j in range(i + 1, min(i + 3, len(lines))):
            values = money_tokens(lines[j])
            if values:
                total = values[-1]
                break
        if total is not None:
            break

    # 품목 헤더가 있으면 그 뒤부터 시작한다.
    start_idx = 0
    header_found = False
    for i, ln in enumerate(lines):
        if is_item_header(ln):
            start_idx = i + 1
            header_found = True
            break

    candidate_lines = lines[start_idx:] if header_found else lines

    used = set()
    current_name: Optional[str] = None
    current_prices: List[int] = []
    qty_candidates: List[int] = []
    seen_item = False
    awaiting_name_after_seq = False

    def finalize_current() -> None:
        nonlocal current_name, current_prices, qty_candidates, seen_item

        if current_name and current_prices:
            amount = current_prices[-1]
            qty = 1

            # 단가 + 수량 + 금액 형태면 수량을 복원한다.
            if len(current_prices) >= 2:
                unit_price = current_prices[-2]

                # OCR이 수량을 별도 토큰으로 준 경우 우선 사용
                for q in reversed(qty_candidates):
                    if 1 <= q <= 99 and unit_price * q == amount:
                        qty = q
                        break
                else:
                    if unit_price > 0 and amount % unit_price == 0:
                        inferred = amount // unit_price
                        if 1 <= inferred <= 99:
                            qty = inferred

            key = (current_name, amount)
            if key not in used:
                items.append(
                    {
                        "name": current_name,
                        "qty": qty,
                        # 기존 API 의미 유지: price에는 해당 품목 행의 최종 금액을 저장
                        "price": amount,
                    }
                )
                used.add(key)
                seen_item = True

        current_name = None
        current_prices = []
        qty_candidates = []

    for ln in candidate_lines:
        value = clean_line(ln)

        if RC_DATE.search(value):
            continue

        # 판매총액/결제/회원 영역 진입 시 품목 파싱 종료
        if is_item_stop(value):
            finalize_current()
            if header_found or seen_item:
                break
            continue

        # 헤더가 여러 OCR 토큰으로 쪼개진 경우 남은 헤더 토큰 제거
        if re.fullmatch(
            r"(단가|수량|금액|상품\(코드\)|상품코드|품명)",
            value,
            re.I,
        ):
            continue

        # CLOVA가 '001'과 'P굿모닝우유'를 따로 반환하는 경우.
        if re.fullmatch(r"\d{1,3}", value):
            number = int(value)

            # 001/002/...는 가격보다 품목 순번일 가능성이 훨씬 높다.
            if len(value) == 3 and value.startswith("0"):
                finalize_current()
                awaiting_name_after_seq = True
                continue

            if current_name is None:
                awaiting_name_after_seq = True
                continue

            # 이미 단가+금액을 모두 모은 뒤 숫자가 나오면 다음 순번으로 본다.
            if len(current_prices) >= 2:
                finalize_current()
                awaiting_name_after_seq = True
                continue

            # current_name 뒤 첫 3자리 숫자는 500/750원 같은 소액 가격일 수 있다.
            if not current_prices:
                if number >= 100:
                    current_prices.append(number)
                elif 1 <= number <= 99:
                    qty_candidates.append(number)
                continue

            # 단가 하나를 읽은 뒤 1~99면 수량, 100 이상이면 최종 금액 후보
            if number <= 99:
                qty_candidates.append(number)
            else:
                current_prices.append(number)
            continue

        # '001 P양파', '003 P무'처럼 순번과 품목명이 같은 OCR 행에 있는 경우
        numbered = re.match(r"^\s*\d{1,3}\s*[.)-]?\s+(.+)$", value)
        if numbered:
            finalize_current()
            body = normalize_item_name(numbered.group(1), strip_mart_p=True)
            prices = money_tokens(body)

            if prices:
                name = name_from_price_line(body, strip_mart_p=True)
                if is_possible_name(name):
                    current_name = name
                    current_prices.extend(prices)
            elif is_possible_name(body):
                current_name = body

            awaiting_name_after_seq = False
            continue

        if awaiting_name_after_seq:
            body = normalize_item_name(value, strip_mart_p=True)
            if is_possible_name(body):
                current_name = body
                awaiting_name_after_seq = False
                continue

        # 굿모닝우유 / 900ML처럼 용량만 다음 OCR 토큰으로 분리된 경우
        if current_name and is_size_token(value):
            current_name = clean_line(f"{current_name} {value}")
            continue

        # [2,150] 같은 정상가/참고가는 실제 결제금액으로 쓰지 않는다.
        # CLOVA가 품목 뒤에 가격 열 전체를 다시 나열할 때 마지막 품목이 오염되지 않도록,
        # 이미 현재 품목 가격을 확보했다면 참고가 진입 시 현재 품목을 먼저 확정한다.
        if current_name and is_bracket_price(value):
            if current_prices:
                finalize_current()
            continue

        # *231973, *88,010, 8801104210645 같은 코드-only 토큰은 무시하되
        # current_name 상태는 그대로 유지한다.
        if current_name and is_product_code_only(value):
            continue

        # '*231973 3,300 1 3,300' 같이 코드와 금액 행이 합쳐진 경우
        numeric_row = strip_leading_product_code(value)
        prices = money_tokens(numeric_row)

        if current_name and prices:
            current_prices.extend(prices)

            for qty_text in re.findall(
                r"(?<![A-Za-z0-9])\d{1,2}(?![A-Za-z0-9])",
                numeric_row,
            ):
                qty = int(qty_text)
                if 1 <= qty <= 99:
                    qty_candidates.append(qty)

            # 한 행에 단가와 최종금액이 모두 있으면 즉시 품목 확정
            if len(prices) >= 2:
                finalize_current()
            continue

        if is_meta_line(value):
            continue

        # 'I-T)아메리카노 4,100 2 8,200' 같은 같은-행 품목
        if prices:
            name = name_from_price_line(numeric_row)
            if is_possible_name(name):
                finalize_current()
                current_name = name
                current_prices.extend(prices)

                for qty_text in re.findall(
                    r"(?<![A-Za-z0-9])\d{1,2}(?![A-Za-z0-9])",
                    numeric_row,
                ):
                    qty = int(qty_text)
                    if 1 <= qty <= 99:
                        qty_candidates.append(qty)

                if len(prices) >= 2:
                    finalize_current()
                continue

        # 품목명이 OCR에서 여러 텍스트 토큰으로 쪼개진 경우 가격이 나오기 전까지 합친다.
        if is_possible_name(value):
            if store and value == store:
                continue
            if re.search(r"대한민국|할인점|고객센터|감사합니다", value):
                continue

            if current_name:
                if current_prices:
                    finalize_current()
                    current_name = normalize_item_name(value)
                else:
                    merged = clean_line(f"{current_name} {value}")
                    current_name = (
                        merged if len(merged) <= 60 else normalize_item_name(value)
                    )
            else:
                current_name = normalize_item_name(value)

    finalize_current()

    # 기존 v2 동작 유지: 여러 품목 중 '총액' 자체가 품목으로 섞인 경우 제거
    if total is not None and len(items) > 1:
        items = [item for item in items if item["price"] != total]

    return {
        "store": store,
        "purchasedAt": purchased_at,
        "total": total,
        "items": items,
    }

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