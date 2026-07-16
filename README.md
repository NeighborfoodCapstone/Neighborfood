# NeighborFood

지역 기반 식재료 공동구매 플랫폼 — FastAPI + SQLite 백엔드, 정적 HTML 프런트엔드

버전: **v2.1.0** (2026-07-11)

---

## 주요 기능

- 회원가입 / 로그인 (login_id + 비밀번호, PBKDF2-SHA256)
- 게시글 작성 (나눔 / 공동구매 / 교환)
- 공동구매 참여 (원자적 카운터, 중복 참여 방지)
- QR 코드 대면 거래 인증
- 영수증 OCR 인증 (CLOVA OCR 또는 Tesseract fallback)
- 냉장고 관리 (영수증 인증 품목 자동 등록)
- 1:1 / 그룹 채팅 (REST 폴링)
- 찜(위시리스트), 신고, 공지사항
- 관리자 대시보드
- GPS 위치 인증
- 카카오맵 연동

---

## 요구사항

- Python 3.10 이상
- (선택) CLOVA OCR API 키 — 없으면 Tesseract fallback 사용
- (선택) Kakao Developers JavaScript 키 — 지도 기능 사용 시 필요

---

## 시작하기

### 1. 저장소 클론

```bash
git clone https://github.com/NeighborfoodCapstone/Neighborfood.git
cd Neighborfood
```

### 2. 가상환경 설정 및 패키지 설치

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

`.env` 파일을 열어 필요한 값을 채웁니다:

```
CLOVA_OCR_INVOKE_URL=   # CLOVA OCR Invoke URL (선택)
CLOVA_OCR_SECRET=       # CLOVA OCR Secret Key (선택)
KAKAO_JS_KEY=           # 카카오 JS API 키 (지도 기능 사용 시 필요)
```

> `.env` 파일은 `.gitignore`에 포함되어 있으므로 GitHub에 올라가지 않습니다.

### 4. 서버 실행

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

서버가 실행되면 브라우저에서 접속합니다:

- 홈: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API 문서 (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 프런트엔드: [http://127.0.0.1:8000/frontend/Home.html](http://127.0.0.1:8000/frontend/Home.html)

> DB 파일(`data/neighborfood.db`)은 서버 첫 실행 시 자동으로 생성됩니다.

---

## 폴더 구조

```
Neighborfood/
├── main.py                  # FastAPI 앱 진입점
├── requirements.txt
├── .env.example             # 환경변수 템플릿
├── .gitignore
├── sql/
│   └── neighborfood_schema.sql   # 스키마 참조 문서 (Source of Truth)
├── data/
│   └── neighborfood.db      # SQLite 단일 DB (자동 생성)
├── uploads/                 # 업로드 이미지 저장 경로
├── app/
│   ├── config.py            # 경로·상수 설정
│   ├── core/
│   │   ├── deps.py          # get_current_user / get_current_admin 의존성
│   │   └── utils.py         # 시간·토큰·비밀번호 헬퍼
│   ├── db/
│   │   ├── base.py          # make_conn, init_all_databases
│   │   ├── auth_db.py       # users, sessions, auth_codes
│   │   ├── transaction_db.py
│   │   ├── qr_db.py
│   │   ├── receipt_db.py
│   │   ├── member_db.py     # wishlists, conversations, messages
│   │   ├── fridge_db.py
│   │   ├── admin_db.py      # notices, reports
│   │   └── location_verify_db.py
│   ├── models/              # Pydantic 요청/응답 스키마
│   └── routers/             # API 라우터 (엔드포인트별 1파일)
│       ├── auth.py
│       ├── posts.py
│       ├── users.py
│       ├── wishlist.py
│       ├── chat.py
│       ├── transactions.py
│       ├── fridge.py
│       ├── admin.py
│       ├── reports.py
│       ├── qr.py
│       ├── receipt.py
│       └── location_verify.py
└── frontend/                # 정적 HTML 프런트엔드
    ├── shared/
    │   ├── auth.js          # fetch 래퍼 (Bearer 토큰 자동 주입)
    │   └── guard.js         # 회원 전용 페이지 보호
    ├── Home.html
    ├── Login.html
    ├── Register.html
    └── ...
```

---

## 인증 방식

Bearer 토큰 세션 인증을 사용합니다.

1. `POST /auth/login` — login_id + password → `{ token, expiresAt }` 반환
2. 이후 모든 인증 필요 API 요청에 `Authorization: Bearer <token>` 헤더 포함
3. `frontend/shared/auth.js`가 `window.fetch`를 래핑하여 토큰을 자동 주입

토큰 유효기간은 `config.py`의 `SESSION_TTL_DAYS`로 조정합니다 (기본 7일).

---

## 데이터베이스

단일 파일 SQLite(`data/neighborfood.db`)를 사용합니다.

- WAL 모드 + `busy_timeout=5000` 으로 동시 접근 안정성 확보
- 앱 시작 시 `init_all_databases()`가 모든 테이블을 `CREATE TABLE IF NOT EXISTS`로 생성
- 기존 DB에 신규 컬럼이 추가될 경우 `ALTER TABLE … ADD COLUMN` 멱등 마이그레이션 자동 실행
- 전체 스키마 정의는 `sql/neighborfood_schema.sql` 참조

---

## API 라우터 목록

| 접두사 | 태그 | 설명 |
|---|---|---|
| `/auth` | 인증 | 회원가입, 로그인, 로그아웃, 내 정보 |
| `/api/posts` | 게시글 | 목록, 상세, 작성, 수정, 삭제, 공동구매 참여 |
| `/api/users` | 회원 | 프로필 조회·수정, 회원 탈퇴, 활동 내역 |
| `/api/wishlist` | 찜 목록 | 찜 추가·취소, 내 찜 목록 |
| `/api/chats` | 채팅 | 채팅방 생성, 메시지 송수신 (REST 폴링) |
| `/api/transactions` | 거래 | 거래 생성·조회·상태 변경 |
| `/api/fridge` | 내 냉장고 | 영수증 인증 품목 등록, 목록 조회, 상태 변경 |
| `/api/qr` | QR 거래 인증 | QR 세션 발급·검증 |
| `/api/receipt` | 영수증 인증 | OCR 업로드, 품목 선택·인증 |
| `/api/admin` | 관리자 | 회원·게시글·신고 관리, 공지사항 |
| `/api/reports` | 신고 | 게시글·회원 신고 접수 |
| `/api/location-verify` | GPS 위치 인증 | 위치 인증 세션 생성·검증 |