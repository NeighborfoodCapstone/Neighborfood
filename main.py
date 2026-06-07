# 마지막 수정 : 2026.06.07
# 깃헙 저장소  : https://github.com/NeighborfoodCapstone/Neighborfood.git
# API 문서    : http://127.0.0.1:8000/docs
#
# 역할: FastAPI 앱 인스턴스 생성, 미들웨어, 라우터 등록만 담당합니다.
#       모든 비즈니스 로직은 app/ 하위 모듈에 분리되어 있습니다.

import os
from fastapi                 import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles     import StaticFiles
from fastapi.responses       import FileResponse, HTMLResponse

from app.config              import UPLOAD_DIR, PAGE_DIR, NO_CACHE
from app.db.base             import init_all_databases
from app.routers             import auth, posts, qr, receipt

# ── 앱 생성 ────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "NeighborFood API",
    description = "지역 기반 식재료 공동구매 플랫폼 API",
    version     = "2.0.0",
)

# ── 정적 파일 서빙 ─────────────────────────────────────────────────────────
app.mount("/uploads",  StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/frontend", StaticFiles(directory=PAGE_DIR),   name="frontend")

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],   # 배포 시 실제 도메인으로 교체
    allow_methods = ["*"],
    allow_headers = ["*"],
)

# ── 시작 이벤트: 모든 DB 초기화 ───────────────────────────────────────────
@app.on_event("startup")
def startup() -> None:
    init_all_databases()

# ── 라우터 등록 ────────────────────────────────────────────────────────────
app.include_router(auth.router,     tags=["인증"])
app.include_router(posts.router,    tags=["게시글"])
app.include_router(qr.router,      prefix="/api/qr",      tags=["QR 거래 인증"])
app.include_router(receipt.router, prefix="/api/receipt", tags=["영수증 인증"])

# ── 인증 HTML 페이지 직접 서빙 (카메라 사용 화면 — localhost 보안 컨텍스트 필요) ─
@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse("""
    <!doctype html><html lang="ko"><head><meta charset="utf-8">
    <title>NeighborFood QR</title>
    <style>body{font-family:system-ui;background:#0a0a0a;color:#fff;
    display:grid;place-items:center;height:100vh;margin:0}
    a{display:block;margin:10px;padding:14px 22px;border-radius:14px;
    background:#006e1c;color:#fff;text-decoration:none;font-weight:700}</style>
    </head><body><div style="text-align:center">
    <h2>NeighborFood QR 거래 인증</h2>
    <a href="/frontend/QR_Create.html">① 내 QR 생성</a>
    <a href="/frontend/QR_Scan.html">② QR 스캔 / 검증</a>
    <a href="/frontend/Receipt_Verify.html">③ 영수증 인증</a>
    </div></body></html>
    """, headers=NO_CACHE)

@app.get("/QR_Create.html",      response_class=HTMLResponse)
def serve_qr_create():
    return FileResponse(os.path.join(PAGE_DIR, "QR_Create.html"), headers=NO_CACHE)

@app.get("/QR_Scan.html",        response_class=HTMLResponse)
def serve_qr_scan():
    return FileResponse(os.path.join(PAGE_DIR, "QR_Scan.html"), headers=NO_CACHE)

@app.get("/Receipt_Verify.html", response_class=HTMLResponse)
def serve_receipt_verify():
    return FileResponse(os.path.join(PAGE_DIR, "Receipt_Verify.html"), headers=NO_CACHE)

# ── 로컬 실행 진입점 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
