# 마지막 수정 : 2026.10.01 (React 빌드 dist 서빙 추가)
# 깃헙 저장소  : https://github.com/NeighborfoodCapstone/Neighborfood.git
# API 문서    : http://127.0.0.1:8000/docs
#
# 역할: FastAPI 앱 인스턴스 생성, 미들웨어, 라우터 등록만 담당합니다.
#       모든 비즈니스 로직은 app/ 하위 모듈에 분리되어 있습니다.

import os
from contextlib              import asynccontextmanager
from pathlib                 import Path
from fastapi                 import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles     import StaticFiles
from fastapi.responses       import FileResponse, HTMLResponse

from app.config              import UPLOAD_DIR, PAGE_DIR, NO_CACHE
from app.db.base             import init_all_databases
from app.routers             import auth, posts, qr, receipt, users, wishlist, chat, transactions, fridge, admin, reports
from app.routers             import location_verify, ratings, settlements


# ── .env 로더 (receipt_db.py의 _load_local_env_once와 동일한 방식, 의존성 추가 없음) ──
def _load_local_env_once() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env_once()
KAKAO_JS_KEY = os.getenv("KAKAO_JS_KEY", "")

# ── React 프런트엔드 빌드(dist) 위치 ──────────────────────────────────────
# 로컬에서 `npm run build`한 frontend-react/dist 를 서버에 올리면 이 앱이 "/"에서 서빙합니다.
# 위치를 바꾸려면 .env에 FRONTEND_DIST_DIR=<절대경로> 를 지정하세요.
# index.html이 없으면(미배포·로컬 개발) 기존 임시 안내 페이지를 그대로 사용합니다.
_DIST_DIR  = Path(os.getenv("FRONTEND_DIST_DIR", "").strip()
                  or Path(__file__).resolve().parent / "frontend-react" / "dist")
_SERVE_SPA = (_DIST_DIR / "index.html").is_file()


# ── 수명주기(lifespan): 시작 시 모든 DB 초기화 ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_all_databases()   # startup
    yield
    # (shutdown 시 정리할 자원이 있으면 여기에)


# ── 앱 생성 ────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "NeighborFood API",
    description = "지역 기반 식재료 공동구매 플랫폼 API",
    version     = "2.1.0",
    lifespan    = lifespan,
)

# ── 정적 파일 서빙 ─────────────────────────────────────────────────────────
app.mount("/uploads",  StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/frontend", StaticFiles(directory=PAGE_DIR),   name="frontend")
app.mount("/shared",   StaticFiles(directory=os.path.join(PAGE_DIR, "shared")), name="shared")

# ── CORS ──────────────────────────────────────────────────────────────────
# .env의 ALLOWED_ORIGINS(콤마 구분)가 있으면 그 도메인만 허용하고, 없으면 개발 편의를
# 위해 "*"로 전체 허용합니다. 배포 시에는 반드시 .env에 실제 도메인을 지정하세요.
#   예) ALLOWED_ORIGINS=https://neighborfood.com,https://www.neighborfood.com
_origins_raw = os.getenv("ALLOWED_ORIGINS", "").strip()
_allowed_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()] or ["*"]
if _allowed_origins == ["*"]:
    print("[CORS] ALLOWED_ORIGINS 미설정 → 모든 출처 허용(*). 배포 전 .env에 도메인을 지정하세요.")
else:
    print(f"[CORS] 허용 출처: {_allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins = _allowed_origins,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

# ── 프런트 설정값 배포 (하드코딩 금지 원칙: 프런트가 필요한 키를 여기서 내려줌) ──
@app.get("/api/config/kakao-key")
def get_kakao_key():
    """Map.html이 카카오맵 SDK를 동적으로 로드할 때 사용하는 JS 키를 반환합니다.
    실제 값은 .env의 KAKAO_JS_KEY에서 읽어오며, 이 소스코드에는 값을 두지 않습니다."""
    return {"key": KAKAO_JS_KEY}

# ── 라우터 등록 ────────────────────────────────────────────────────────────
app.include_router(auth.router,             tags=["인증"])
app.include_router(posts.router,            tags=["게시글"])
app.include_router(users.router,            prefix="/api/users",        tags=["회원"])
app.include_router(qr.router,               prefix="/api/qr",           tags=["QR 거래 인증"])
app.include_router(receipt.router,          prefix="/api/receipt",      tags=["영수증 인증"])
app.include_router(wishlist.router,         prefix="/api/wishlist",     tags=["찜 목록"])
app.include_router(chat.router,             prefix="/api/chats",        tags=["채팅"])
app.include_router(transactions.router,     prefix="/api/transactions", tags=["거래"])
app.include_router(fridge.router,           prefix="/api/fridge",       tags=["내 냉장고"])
app.include_router(admin.router,            prefix="/api/admin",        tags=["관리자"])
app.include_router(reports.router,          prefix="/api/reports",      tags=["신고"])
app.include_router(location_verify.router,  prefix="/api/location-verify", tags=["GPS 위치 인증"])
app.include_router(ratings.router,          prefix="/api/ratings",      tags=["매너 평가"])
app.include_router(settlements.router,      prefix="/api/settlements",  tags=["정산"])

# ── 인증 HTML 페이지 직접 서빙 (카메라 사용 화면 — localhost 보안 컨텍스트 필요) ─
def index():
    return HTMLResponse("""
    <!doctype html><html lang="ko"><head><meta charset="utf-8">
    <title>NeighborFood</title>
    <style>body{font-family:system-ui;background:#0a0a0a;color:#fff;
    display:grid;place-items:center;height:100vh;margin:0}
    a{display:block;margin:10px;padding:14px 22px;border-radius:14px;
    background:#006e1c;color:#fff;text-decoration:none;font-weight:700}</style>
    </head><body><div style="text-align:center">
    <h2>NeighborFood</h2>
    <a href="/frontend/Home.html">홈 화면</a>
    <a href="/frontend/QR_Scan.html">① QR / 바코드 스캔</a>
    <a href="/frontend/Receipt_Verify.html">③ 영수증 인증</a>
    </div></body></html>
    """, headers=NO_CACHE)

if not _SERVE_SPA:
    app.get("/", response_class=HTMLResponse)(index)   # dist 미배포 시에만 임시 안내 페이지

@app.get("/QR_Scan.html",        response_class=HTMLResponse)
def serve_qr_scan():
    return FileResponse(os.path.join(PAGE_DIR, "QR_Scan.html"), headers=NO_CACHE)

@app.get("/Receipt_Verify.html", response_class=HTMLResponse)
def serve_receipt_verify():
    return FileResponse(os.path.join(PAGE_DIR, "Receipt_Verify.html"), headers=NO_CACHE)

# ── React 앱(dist) 서빙 ────────────────────────────────────────────────────
# React는 해시 라우팅(#/화면)이라 SPA 폴백 라우트가 필요 없습니다.
# "/" 마운트는 위에서 등록한 API·/uploads·/frontend·/shared 등 모든 경로보다 뒤에서만 매칭됩니다.
class _SPAStaticFiles(StaticFiles):
    """index.html은 재배포가 바로 반영되도록 no-cache, 해시가 붙은 assets/는 장기 캐시."""
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            immutable = path.replace("\\", "/").startswith("assets/")
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable" if immutable else "no-cache"
            )
        return response

if _SERVE_SPA:
    print(f"[SPA] React 빌드 서빙: {_DIST_DIR}")
    app.mount("/", _SPAStaticFiles(directory=str(_DIST_DIR), html=True), name="spa")
else:
    print(f"[SPA] dist 없음({_DIST_DIR}) → 임시 안내 페이지 사용. 배포 시 frontend-react/dist 를 업로드하세요.")

# ── 로컬 실행 진입점 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)