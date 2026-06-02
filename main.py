# 마지막 수정 : 2026.05.23
# 깃헙 저장소 주소 : https://github.com/NeighborfoodCapstone/Neighborfood.git
# API문서 저장소 주소 : http://localhost:8000/docs
# 
# 통합 내용: 기존 게시판/OTP API(main.py) + QR 거래 인증 API(QR_auth.py)

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs
import sqlite3
import random
import json
import os
import uuid
import hashlib
import secrets
import re

app = FastAPI(title="NeighborFood API")

# ── 업로드 디렉토리 ──────────────────────────────────────────────────────
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 정적 파일 서빙: 프론트에서 <img src="http://localhost:8000/uploads/xxx.jpg"> 형태로 접근
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 배포 시 실제 도메인으로 교체
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── DB 초기화 (인증 및 게시글) ───────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()

    # 기존 인증코드 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_codes (
            phone_number TEXT PRIMARY KEY,
            code         TEXT NOT NULL,
            expiry_time  TEXT NOT NULL
        )
    """)

    # 게시글 통합 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            type            TEXT NOT NULL,
            title           TEXT NOT NULL,
            description     TEXT,
            category        TEXT,
            images          TEXT DEFAULT '[]',
            address         TEXT,
            lat             REAL,
            lng             REAL,
            author_id       TEXT NOT NULL,
            status          TEXT DEFAULT 'active',
            created_at      TEXT NOT NULL,
            expires_at      TEXT,
            -- 공동구매 전용
            gb_target       INTEGER,
            gb_current      INTEGER DEFAULT 0,
            gb_price        INTEGER,
            -- 교환 전용
            exchange_want   TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ── DB 초기화 및 헬퍼 함수 (QR 인증) ─────────────────────────────────────────
QR_DB_PATH = os.path.join(os.path.dirname(__file__), "qr_auth.db")

def qr_get_conn():
    conn = sqlite3.connect(QR_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def qr_now_utc():
    return datetime.now(timezone.utc)

def qr_to_iso(dt: datetime):
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

def qr_from_iso(value: str):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def qr_hash_token(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def qr_parse_token(raw_value: str):
    if not raw_value:
        return ""

    value = raw_value.strip()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)

        query = parse_qs(parsed.query)
        if "token" in query:
            return query["token"][0]

        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return path_parts[-1]

    return value

def qr_row_to_dict(row):
    return {
        "id": row["id"],
        "subjectId": row["subject_id"],
        "purpose": row["purpose"],
        "status": row["status"],
        "issuedAt": row["issued_at"],
        "expiresAt": row["expires_at"],
        "usedAt": row["used_at"],
        "lastScannedAt": row["last_scanned_at"],
    }

def qr_init_db():
    with qr_get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS qr_sessions (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'ISSUED'
                    CHECK (status IN ('ISSUED', 'VERIFIED', 'EXPIRED')),
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                last_scanned_at TEXT,
                scanner_ip TEXT,
                scanner_user_agent TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_subject_issued
            ON qr_sessions (subject_id, issued_at)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_status_expires
            ON qr_sessions (status, expires_at)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_token_hash
            ON qr_sessions (token_hash)
            """
        )

        conn.commit()

def qr_expire_old_sessions():
    current_time = qr_to_iso(qr_now_utc())

    with qr_get_conn() as conn:
        conn.execute(
            """
            UPDATE qr_sessions
            SET status = 'EXPIRED',
                updated_at = ?
            WHERE status = 'ISSUED'
              AND expires_at < ?
            """,
            (current_time, current_time),
        )
        conn.commit()


# ── DB 초기화 및 헬퍼 함수 (영수증 인증) ─────────────────────────────────────
#   QR 인증(qr_sessions)과 동일한 설계 패턴으로, 영수증 인증은 별도 DB 파일을 씁니다.
#   상태 흐름:  SCANNED(분석 완료) → VERIFIED(선택 항목으로 인증) / FAILED
#   - 시간/직렬화 헬퍼(qr_now_utc, qr_to_iso 등)는 QR 쪽 것을 그대로 재사용합니다.
RECEIPT_DB_PATH = os.path.join(os.path.dirname(__file__), "receipt_auth.db")

# 인증 성공 1건당 올라가는 신뢰 온도(°) — 화면의 "신뢰 온도 +0.3°" 배지와 동일
RECEIPT_TRUST_DELTA = 0.3

# OCR 의존성(선택). 설치돼 있으면 실제 인식, 없으면 데모 항목으로 자동 폴백합니다.
#   pip install pillow pytesseract  +  시스템에 tesseract(+ 한글 데이터: kor) 설치
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

def receipt_get_conn():
    conn = sqlite3.connect(RECEIPT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def receipt_init_db():
    with receipt_get_conn() as conn:
        conn.execute(
            """
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
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_subject_scanned
            ON receipts (subject_id, scanned_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_status_scanned
            ON receipts (status, scanned_at)
            """
        )
        conn.commit()

# ── OCR / 파싱용 정규식 (모듈 로드 시 1회 컴파일) ────────────────────────────
RC_PRICE = re.compile(r'(\d{1,3}(?:,\d{3})+|\d{3,})')
RC_QTY   = re.compile(r'(?:(\d+)\s*[xX×*]|[xX×*]\s*(\d+)|(\d+)\s*개)')
RC_DATE  = re.compile(
    r'(20\d{2}[-./]\s*\d{1,2}[-./]\s*\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)'
)
RC_TOTAL_KW = ('합계', '총액', '결제', '받을금액', '받을 금액', '판매합계', '합 계')
RC_NOISE_KW = ('사업자', '대표', 'TEL', 'tel', '전화', '주소', '카드', '승인',
               '거스름', '부가세', '과세', '면세', 'POS', '영수증', '매장')

def _rc_to_int(value: str):
    try:
        return int(value.replace(',', ''))
    except Exception:
        return 0

def receipt_redact_pii(text: str):
    """개인 식별 정보(주민/카드/휴대폰/사업자번호)를 마스킹해 원문을 저장하지 않도록 합니다."""
    if not text:
        return ""
    # 휴대폰 (카드보다 먼저 처리해야 자릿수가 섞이지 않습니다)
    text = re.sub(r'01[016-9][-\s]?\d{3,4}[-\s]?\d{4}', '010-****-****', text)
    # 주민등록번호
    text = re.sub(r'\d{6}\s*-\s*[1-4]\d{6}', '******-*******', text)
    # 카드번호(13~16자리) → 끝 4자리만 표시
    text = re.sub(
        r'\b(?:\d[ -]?){13,16}\b',
        lambda m: '****-****-****-' + re.sub(r'\D', '', m.group())[-4:],
        text,
    )
    # 사업자등록번호
    text = re.sub(r'\d{3}-\d{2}-\d{5}', '***-**-*****', text)
    return text

def receipt_ocr_text(image_path: str):
    """이미지에서 텍스트를 추출합니다. 라이브러리/엔진이 없으면 빈 문자열을 반환해 데모로 폴백합니다."""
    if not (_PIL_OK and _TESS_OK):
        return ""
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)   # 휴대폰 회전 보정
        img = img.convert('L')               # 흑백
        img = ImageOps.autocontrast(img)
        w, h = img.size
        if max(w, h) < 1000:                 # 작은 이미지는 업스케일해 인식률 향상
            scale = 1000 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)))
        for lang in ('kor+eng', 'eng', None):  # 한글 데이터 없으면 단계적 폴백
            try:
                return pytesseract.image_to_string(img, lang=lang) if lang \
                    else pytesseract.image_to_string(img)
            except Exception:
                continue
        return ""
    except Exception as exc:
        print(f"[영수증 OCR] 인식 실패: {exc}")
        return ""

def receipt_parse(text: str):
    """OCR 텍스트에서 매장명·구매일시·품목·합계를 추출합니다."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    store = purchased_at = total = None
    items = []

    for ln in lines:                       # 구매일시
        m = RC_DATE.search(ln)
        if m:
            purchased_at = re.sub(r'\s+', ' ', m.group(1)).replace('.', '-').replace('/', '-')
            break

    for ln in lines:                       # 매장명: 날짜/금액/잡음이 아닌 첫 줄
        if RC_DATE.search(ln) or any(k in ln for k in RC_NOISE_KW):
            continue
        if RC_PRICE.fullmatch(ln.replace(' ', '')):
            continue
        store = ln
        break

    for ln in lines:                       # 합계
        if any(k in ln for k in RC_TOTAL_KW):
            prices = RC_PRICE.findall(ln)
            if prices:
                total = _rc_to_int(prices[-1])

    for ln in lines:                       # 품목: 가격으로 끝나는 일반 줄
        if any(k in ln for k in RC_TOTAL_KW) or RC_DATE.search(ln):
            continue
        if any(k in ln for k in RC_NOISE_KW):
            continue
        prices = list(RC_PRICE.finditer(ln))
        if not prices:
            continue
        price = _rc_to_int(prices[-1].group(1))
        if price < 100:                    # 금액으로 보기엔 너무 작은 수 제외
            continue
        name = ln[:prices[-1].start()]
        qty = 1
        qm = RC_QTY.search(name)
        if qm:
            qty = int(next((g for g in qm.groups() if g), 1))
        name = RC_QTY.sub(' ', name)
        name = re.sub(r'(?<!\S)[xX×*](?!\S)', ' ', name)  # 홀로 남은 수량기호 제거
        name = re.sub(r'\s+', ' ', name).strip(' .-:·')
        if not name or not re.search(r'[가-힣A-Za-z]', name):
            continue
        items.append({"name": name, "qty": qty, "price": price})

    return {"store": store, "purchasedAt": purchased_at, "total": total, "items": items}

def receipt_demo_items():
    """OCR을 못 했을 때 데모 흐름이 항상 동작하도록 하는 폴백 항목 (화면 mock과 동일)."""
    return {
        "store": "로컬푸드마트 한들점",
        "purchasedAt": qr_to_iso(qr_now_utc())[:10],
        "total": 9500,
        "items": [
            {"name": "유기농 시금치", "qty": 2, "price": 4800},
            {"name": "친환경 우유 1L", "qty": 1, "price": 3200},
            {"name": "국내산 애호박", "qty": 1, "price": 1500},
        ],
    }

def receipt_row_to_dict(row):
    def _loads(value):
        try:
            return json.loads(value or "[]")
        except json.JSONDecodeError:
            return []
    return {
        "id": row["id"],
        "subjectId": row["subject_id"],
        "store": row["store_name"],
        "purchasedAt": row["purchased_at"],
        "items": _loads(row["items"]),
        "selectedItems": _loads(row["selected_items"]),
        "total": row["total"],
        "status": row["status"],
        "trustDelta": row["trust_delta"],
        "ocrEngine": row["ocr_engine"],
        "scannedAt": row["scanned_at"],
        "verifiedAt": row["verified_at"],
    }


# ── 요청/응답 모델 ─────────────────────────────────────────────────────────

# 1. SMS 인증 모델
class AuthRequest(BaseModel):
    phone_number: str = Field(..., pattern=r'^010-\d{4}-\d{4}$',
                              description="010-XXXX-XXXX 형식")

class VerifyRequest(BaseModel):
    phone_number: str
    code: str = Field(..., min_length=6, max_length=6)

# 2. 게시글 모델
class PostCreate(BaseModel):
    type: str = Field(..., pattern=r'^(share|exchange|groupbuy)$',
                      description="share | exchange | groupbuy")
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""
    category: Optional[str] = None
    images: List[str] = []         
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    author_id: str                 
    expires_at: Optional[str] = None
    gb_target: Optional[int] = None
    gb_price: Optional[int] = None
    exchange_want: Optional[str] = None

# 3. QR 인증 모델
class QrIssueRequest(BaseModel):
    subjectId: str
    purpose: str = "pickup_confirm"
    ttlSeconds: int = 300

class QrVerifyRequest(BaseModel):
    token: str | None = None
    rawValue: str | None = None

# 4. 영수증 인증 모델
class ReceiptItemModel(BaseModel):
    name: str
    qty: int = 1
    price: int = 0

class ReceiptVerifyRequest(BaseModel):
    scanId: Optional[str] = None
    subjectId: Optional[str] = None
    store: Optional[str] = None
    purchasedAt: Optional[str] = None
    items: List[ReceiptItemModel] = []


# ─────────────────────────────────────────────────────────────────────────
# SMS 인증 API
# ─────────────────────────────────────────────────────────────────────────

@app.post("/request-auth")
async def request_auth(request: AuthRequest):
    auth_code = str(random.randint(100000, 999999))
    expiry = (datetime.now() + timedelta(minutes=5)).isoformat()

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO auth_codes (phone_number, code, expiry_time)
        VALUES (?, ?, ?)
    """, (request.phone_number, auth_code, expiry))
    conn.commit()
    conn.close()

    print(f"\n[SMS 발송] {request.phone_number} → 인증번호: [{auth_code}]  (만료: 5분)\n")

    return {
        "message": "인증번호가 발송되었습니다.",
        "auth_code": auth_code
    }


@app.post("/verify-auth")
async def verify_auth(req: VerifyRequest):
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT code, expiry_time FROM auth_codes WHERE phone_number = ?",
        (req.phone_number,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404,
            detail="인증 요청 기록이 없습니다. 인증요청을 먼저 눌러 주세요.")

    saved_code, expiry_str = row

    if datetime.fromisoformat(expiry_str) < datetime.now():
        raise HTTPException(status_code=410,
            detail="인증번호가 만료되었습니다. 재전송 후 다시 시도해 주세요.")

    if saved_code != req.code:
        raise HTTPException(status_code=400,
            detail="인증번호가 일치하지 않습니다. 다시 확인해 주세요.")

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM auth_codes WHERE phone_number = ?", (req.phone_number,))
    conn.commit()
    conn.close()

    print(f"\n[인증 완료] {req.phone_number}\n")
    return {"message": "인증이 완료되었습니다.", "verified": True}


# ─────────────────────────────────────────────────────────────────────────
# 게시글 관련 API
# ─────────────────────────────────────────────────────────────────────────

@app.post("/upload-images")
async def upload_images(files: List[UploadFile] = File(...)):
    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    saved = []

    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in allowed_ext:
            raise HTTPException(status_code=400,
                detail=f"허용되지 않은 확장자: {ext}")

        new_name = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(UPLOAD_DIR, new_name)

        with open(path, "wb") as out:
            out.write(await f.read())

        saved.append(new_name)
        print(f"[이미지 저장] {f.filename} → {new_name}")

    return {"files": saved}


@app.post("/posts")
async def create_post(post: PostCreate):
    if post.type == "groupbuy":
        if not post.gb_target or not post.gb_price:
            raise HTTPException(status_code=400,
                detail="공동구매는 목표 인원(gb_target)과 1인당 가격(gb_price)이 필요합니다.")

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO posts (
            type, title, description, category, images,
            address, lat, lng, author_id, status,
            created_at, expires_at,
            gb_target, gb_current, gb_price, exchange_want
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post.type, post.title, post.description, post.category,
        json.dumps(post.images, ensure_ascii=False),
        post.address, post.lat, post.lng,
        post.author_id, "active",
        datetime.now().isoformat(),
        post.expires_at,
        post.gb_target, 0 if post.type == "groupbuy" else None,
        post.gb_price, post.exchange_want
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"\n[게시글 등록] #{new_id} ({post.type}) {post.title} by {post.author_id}\n")
    return {"id": new_id, "message": "게시글이 등록되었습니다."}


@app.get("/posts")
async def list_posts(
    keyword: Optional[str] = Query(None, description="제목·설명·카테고리 검색어"),
    type:    Optional[str] = Query(None, description="share|exchange|groupbuy"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    limit:   int = 100,
):
    conn = sqlite3.connect("auth.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = "SELECT * FROM posts WHERE 1=1"
    params = []

    if type:
        sql += " AND type = ?"
        params.append(type)
        
    if category:
        sql += " AND category LIKE ?"
        params.append(f"%{category}%")
        
    if keyword:
        sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = cursor.execute(sql, params).fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        try:
            item["images"] = json.loads(item["images"] or "[]")
        except json.JSONDecodeError:
            item["images"] = []
        results.append(item)

    return {"count": len(results), "items": results}


@app.get("/posts/{post_id}")
async def get_post(post_id: int):
    conn = sqlite3.connect("auth.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")

    item = dict(row)
    try:
        item["images"] = json.loads(item["images"] or "[]")
    except json.JSONDecodeError:
        item["images"] = []

    return item


@app.delete("/posts/{post_id}")
async def delete_post(post_id: int):
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    
    row = cursor.execute("SELECT title FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")
        
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    
    print(f"\n[게시글 삭제] #{post_id} '{row[0]}' 게시글이 삭제되었습니다.\n")
    return {"id": post_id, "message": "게시글이 성공적으로 삭제되었습니다."}


@app.post("/posts/{post_id}/join")
async def join_groupbuy(post_id: int):
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    row = cursor.execute("SELECT type, gb_target, gb_current FROM posts WHERE id = ?",
                         (post_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    p_type, target, current = row
    if p_type != "groupbuy":
        conn.close()
        raise HTTPException(status_code=400, detail="공동구매 게시글만 참여할 수 있습니다.")
    if current >= target:
        conn.close()
        raise HTTPException(status_code=409, detail="이미 모집이 완료되었습니다.")

    new_current = current + 1
    cursor.execute("UPDATE posts SET gb_current = ? WHERE id = ?", (new_current, post_id))
    conn.commit()
    conn.close()
    return {"id": post_id, "gb_current": new_current, "gb_target": target}


# ─────────────────────────────────────────────────────────────────────────
# QR 거래 인증 API
# ─────────────────────────────────────────────────────────────────────────

@app.post("/api/qr/request")
def issue_qr(body: QrIssueRequest):
    qr_init_db()

    subject_id = body.subjectId.strip()

    if not subject_id:
        return {
            "ok": False,
            "message": "subjectId가 비어 있습니다."
        }

    ttl = max(60, min(body.ttlSeconds, 900))

    session_id = f"qrs_{secrets.token_hex(8)}"
    raw_token = secrets.token_urlsafe(32)
    token_hash = qr_hash_token(raw_token)

    issued_at = qr_now_utc()
    expires_at = issued_at + timedelta(seconds=ttl)

    issued_at_text = qr_to_iso(issued_at)
    expires_at_text = qr_to_iso(expires_at)

    with qr_get_conn() as conn:
        conn.execute(
            """
            INSERT INTO qr_sessions (
                id,
                subject_id,
                purpose,
                token_hash,
                status,
                issued_at,
                expires_at,
                used_at,
                last_scanned_at,
                scanner_ip,
                scanner_user_agent,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, 'ISSUED', ?, ?, NULL, NULL, NULL, NULL, ?, ?)
            """,
            (
                session_id,
                subject_id,
                body.purpose,
                token_hash,
                issued_at_text,
                expires_at_text,
                issued_at_text,
                issued_at_text,
            ),
        )
        conn.commit()

    verify_url = f"http://127.0.0.1:8000/api/qr/verify/{raw_token}"

    return {
        "ok": True,
        "session": {
            "id": session_id,
            "subjectId": subject_id,
            "purpose": body.purpose,
            "status": "ISSUED",
            "issuedAt": issued_at_text,
            "expiresAt": expires_at_text,
            "usedAt": None,
            "lastScannedAt": None,
            "token": raw_token,
            "verifyUrl": verify_url,
        },
    }


@app.post("/api/qr/verify")
def verify_qr(body: QrVerifyRequest, request: Request):
    qr_init_db()
    qr_expire_old_sessions()

    raw_value = body.token or body.rawValue or ""
    token = qr_parse_token(raw_value)

    if not token:
        return {
            "ok": False,
            "result": "invalid_input",
            "message": "QR 토큰이 비어 있습니다.",
        }

    token_hash = qr_hash_token(token)
    scanned_at = qr_to_iso(qr_now_utc())

    scanner_ip = request.client.host if request.client else None
    scanner_user_agent = request.headers.get("user-agent")

    with qr_get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            WHERE token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

        if row is None:
            return {
                "ok": False,
                "result": "not_found",
                "message": "저장된 인증 세션을 찾을 수 없습니다.",
            }

        conn.execute(
            """
            UPDATE qr_sessions
            SET last_scanned_at = ?,
                scanner_ip = ?,
                scanner_user_agent = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                scanned_at,
                scanner_ip,
                scanner_user_agent,
                scanned_at,
                row["id"],
            ),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            WHERE id = ?
            """,
            (row["id"],),
        ).fetchone()

        if row["status"] == "EXPIRED":
            return {
                "ok": False,
                "result": "expired",
                "message": "만료된 QR입니다.",
                "session": qr_row_to_dict(row),
            }

        if row["status"] == "VERIFIED":
            return {
                "ok": False,
                "result": "already_used",
                "message": "이미 사용된 QR입니다.",
                "session": qr_row_to_dict(row),
            }

        if qr_from_iso(row["expires_at"]) < qr_now_utc():
            conn.execute(
                """
                UPDATE qr_sessions
                SET status = 'EXPIRED',
                    updated_at = ?
                WHERE id = ?
                """,
                (scanned_at, row["id"]),
            )
            conn.commit()

            row = conn.execute(
                """
                SELECT *
                FROM qr_sessions
                WHERE id = ?
                """,
                (row["id"],),
            ).fetchone()

            return {
                "ok": False,
                "result": "expired",
                "message": "만료된 QR입니다.",
                "session": qr_row_to_dict(row),
            }

        conn.execute(
            """
            UPDATE qr_sessions
            SET status = 'VERIFIED',
                used_at = ?,
                last_scanned_at = ?,
                scanner_ip = ?,
                scanner_user_agent = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                scanned_at,
                scanned_at,
                scanner_ip,
                scanner_user_agent,
                scanned_at,
                row["id"],
            ),
        )
        conn.commit()

        updated = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            WHERE id = ?
            """,
            (row["id"],),
        ).fetchone()

    return {
        "ok": True,
        "result": "verified",
        "message": "QR 인증이 완료되었습니다.",
        "session": qr_row_to_dict(updated),
    }


@app.get("/api/qr/verify/{token}")
def verify_qr_by_url(token: str, request: Request):
    body = QrVerifyRequest(token=token)
    return verify_qr(body, request)

@app.post("/api/qr/verify/{token}")
def verify_qr_post_by_url(token: str, request: Request):
    body = QrVerifyRequest(token=token)
    return verify_qr(body, request)

@app.get("/api/qr/history")
def get_qr_history(limit: int = 20):
    qr_init_db()
    qr_expire_old_sessions()

    limit = max(1, min(limit, 50))

    with qr_get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            ORDER BY issued_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return {
        "ok": True,
        "items": [qr_row_to_dict(row) for row in rows],
    }


# ─────────────────────────────────────────────────────────────────────────
# 영수증 거래 인증 API
#   POST /api/receipt/scan    : 영수증 이미지 업로드 → OCR/파싱 → 인식 항목 반환
#   POST /api/receipt/verify  : 선택 항목으로 인증 확정 → 신뢰 온도 가산
#   GET  /api/receipt/history : 최근 영수증 인증 이력
# ─────────────────────────────────────────────────────────────────────────

@app.post("/api/receipt/scan")
async def scan_receipt(file: UploadFile = File(...), subjectId: str = Query("")):
    receipt_init_db()

    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"허용되지 않은 확장자: {ext}")

    new_name = f"receipt_{uuid.uuid4().hex}{ext}"
    image_path = os.path.join(UPLOAD_DIR, new_name)
    with open(image_path, "wb") as out:
        out.write(await file.read())

    # OCR → 개인정보 마스킹 → 파싱 (원문 PII는 저장하지 않음)
    raw_text = receipt_ocr_text(image_path)
    safe_text = receipt_redact_pii(raw_text)
    parsed = receipt_parse(safe_text) if safe_text else {"items": []}

    ocr_engine = "tesseract"
    if not parsed.get("items"):           # 인식 실패 시 데모 항목으로 폴백
        parsed = receipt_demo_items()
        ocr_engine = "demo"

    scan_id = f"rcpt_{secrets.token_hex(8)}"
    now = qr_to_iso(qr_now_utc())
    items_json = json.dumps(parsed["items"], ensure_ascii=False)

    with receipt_get_conn() as conn:
        conn.execute(
            """
            INSERT INTO receipts (
                id, subject_id, store_name, purchased_at, items, selected_items,
                total, status, trust_delta, ocr_engine, image_path,
                scanned_at, verified_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, '[]', ?, 'SCANNED', 0, ?, ?, ?, NULL, ?, ?)
            """,
            (
                scan_id, subjectId.strip() or None, parsed.get("store"),
                parsed.get("purchasedAt"), items_json, parsed.get("total"),
                ocr_engine, new_name, now, now, now,
            ),
        )
        conn.commit()

    print(f"\n[영수증 분석] {scan_id} · 엔진={ocr_engine} · 항목 {len(parsed['items'])}개\n")

    return {
        "ok": True,
        "scan": {
            "id": scan_id,
            "subjectId": subjectId.strip() or None,
            "store": parsed.get("store"),
            "purchasedAt": parsed.get("purchasedAt"),
            "total": parsed.get("total"),
            "items": parsed["items"],
            "ocrEngine": ocr_engine,
            "imageUrl": f"/uploads/{new_name}",
            "status": "SCANNED",
            "scannedAt": now,
        },
    }


@app.post("/api/receipt/verify")
def verify_receipt(body: ReceiptVerifyRequest):
    receipt_init_db()

    selected = [item.dict() for item in body.items]
    if not selected:
        return {
            "ok": False,
            "result": "no_items",
            "message": "인증할 항목을 1개 이상 선택하세요.",
        }

    now = qr_to_iso(qr_now_utc())
    selected_json = json.dumps(selected, ensure_ascii=False)
    trust_delta = RECEIPT_TRUST_DELTA

    with receipt_get_conn() as conn:
        row = None
        if body.scanId:
            row = conn.execute(
                "SELECT * FROM receipts WHERE id = ?", (body.scanId,)
            ).fetchone()

        if row is not None:
            if row["status"] == "VERIFIED":
                return {
                    "ok": False,
                    "result": "already_used",
                    "message": "이미 인증에 사용된 영수증입니다.",
                    "receipt": receipt_row_to_dict(row),
                }
            conn.execute(
                """
                UPDATE receipts
                SET status = 'VERIFIED',
                    selected_items = ?,
                    trust_delta = ?,
                    store_name = COALESCE(?, store_name),
                    purchased_at = COALESCE(?, purchased_at),
                    verified_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (selected_json, trust_delta, body.store, body.purchasedAt,
                 now, now, row["id"]),
            )
            receipt_id = row["id"]
        else:
            # scanId 없이 직접 인증(수동 추가 등): 새 VERIFIED 레코드 생성
            receipt_id = f"rcpt_{secrets.token_hex(8)}"
            conn.execute(
                """
                INSERT INTO receipts (
                    id, subject_id, store_name, purchased_at, items, selected_items,
                    total, status, trust_delta, ocr_engine, image_path,
                    scanned_at, verified_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, 'manual', NULL, ?, ?, ?, ?)
                """,
                (
                    receipt_id, (body.subjectId or "").strip() or None, body.store,
                    body.purchasedAt, selected_json, selected_json,
                    sum(i.get("price", 0) for i in selected), trust_delta,
                    now, now, now, now,
                ),
            )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM receipts WHERE id = ?", (receipt_id,)
        ).fetchone()

    print(f"\n[영수증 인증 완료] {receipt_id} · 항목 {len(selected)}개 · 신뢰온도 +{trust_delta}°\n")

    return {
        "ok": True,
        "result": "verified",
        "message": "영수증 인증이 완료되었습니다.",
        "trustDelta": trust_delta,
        "receipt": receipt_row_to_dict(updated),
    }


@app.get("/api/receipt/history")
def get_receipt_history(limit: int = 20):
    receipt_init_db()
    limit = max(1, min(limit, 50))

    with receipt_get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM receipts
            ORDER BY scanned_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return {
        "ok": True,
        "items": [receipt_row_to_dict(row) for row in rows],
    }


# ─────────────────────────────────────────────────────────────────────────
# 프론트엔드 페이지 서빙 (QR 생성 / QR 인식)
#   - main.py와 같은 폴더에 QR_Create.html, QR_Scan.html 을 두면 됩니다.
#   - 같은 출처(http://127.0.0.1:8000)로 열리므로 CORS 문제 없이 fetch가 동작하고,
#     localhost는 보안 컨텍스트라 카메라(getUserMedia)와 crypto.subtle도 사용 가능합니다.
# ─────────────────────────────────────────────────────────────────────────
PAGE_DIR = os.path.dirname(__file__)

# 브라우저가 옛 HTML을 캐시에 물고 있지 않도록 (개발 중 stale 방지)
NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

@app.get("/", response_class=HTMLResponse)
def qr_index():
    return HTMLResponse(
        """
    <!doctype html><html lang="ko"><head><meta charset="utf-8">
    <title>NeighborFood QR</title>
    <style>body{font-family:system-ui;background:#0a0a0a;color:#fff;display:grid;
    place-items:center;height:100vh;margin:0}a{display:block;margin:10px;padding:14px 22px;
    border-radius:14px;background:#006e1c;color:#fff;text-decoration:none;font-weight:700}</style>
    </head><body><div style="text-align:center">
    <h2>NeighborFood QR 거래 인증</h2>
    <a href="/QR_Create.html">① 내 QR 생성</a>
    <a href="/QR_Scan.html">② QR 스캔 / 검증</a>
    <a href="/Receipt_Verify.html">③ 영수증 인증</a>
    </div></body></html>
    """,
        headers=NO_CACHE,
    )

@app.get("/QR_Create.html", response_class=HTMLResponse)
def serve_qr_create():
    return FileResponse(os.path.join(PAGE_DIR, "QR_Create.html"), headers=NO_CACHE)

@app.get("/QR_Scan.html", response_class=HTMLResponse)
def serve_qr_scan():
    return FileResponse(os.path.join(PAGE_DIR, "QR_Scan.html"), headers=NO_CACHE)

@app.get("/Receipt_Verify.html", response_class=HTMLResponse)
def serve_receipt_verify():
    return FileResponse(os.path.join(PAGE_DIR, "Receipt_Verify.html"), headers=NO_CACHE)


# ── 로컬 실행 진입점 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)