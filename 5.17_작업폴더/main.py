# 마지막 수정 : 2026.05.17
# 깃헙 저장소 주소 : https://github.com/NeighborfoodCapstone/Neighborfood.git
#
# 추가 사항 (2026.05.17)
#   - posts 테이블 신설 (나눔/교환/공동구매 통합, type 컬럼으로 구분)
#   - 게시글 CRUD: POST /posts, GET /posts, GET /posts/{id}, DELETE /posts/{id} (신규 추가)
#   - 이미지 업로드: POST /upload-images (로컬 uploads/ 디렉토리 저장)
#   - 정적 파일 서빙: /uploads/* 로 업로드된 이미지 제공
#
# 시연 한정 단순화
#   - author_id는 프론트에서 하드코딩된 값을 그대로 받음 (로그인 기능 미연동)

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List
import sqlite3
import random
import json
import os
import uuid
from datetime import datetime, timedelta

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


# ── DB 초기화 ─────────────────────────────────────────────────────────────
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

    # ── 게시글 통합 테이블 ──
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


# ── 요청/응답 모델 ─────────────────────────────────────────────────────────
class AuthRequest(BaseModel):
    phone_number: str = Field(..., pattern=r'^010-\d{4}-\d{4}$',
                              description="010-XXXX-XXXX 형식")

class VerifyRequest(BaseModel):
    phone_number: str
    code: str = Field(..., min_length=6, max_length=6)

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


# ── 인증번호 발송 ──────────────────────────────────────────────────────────
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


# ── 인증번호 검증 ──────────────────────────────────────────────────────────
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

# ── 이미지 업로드 (여러 장 동시) ──────────────────────────────────────────
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


# ── 게시글 등록 ───────────────────────────────────────────────────────────
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


# ── 게시글 목록 조회 ─────────────────────────────────────────────────────
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


# ── 게시글 상세 조회 ─────────────────────────────────────────────────────
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


# ── 게시글 임의 삭제 (시연용 신규 추가) ──────────────────────────────────────
@app.delete("/posts/{post_id}")
async def delete_post(post_id: int):
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    
    # 게시글 존재 여부 확인
    row = cursor.execute("SELECT title FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")
        
    # 데이터베이스에서 레코드 삭제
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    
    print(f"\n[게시글 삭제] #{post_id} '{row[0]}' 게시글이 삭제되었습니다.\n")
    return {"id": post_id, "message": "게시글이 성공적으로 삭제되었습니다."}


# ── 공동구매 참여 인원 증가 ──────────────────────────────────────────────
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


# ── 로컬 실행 진입점 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)