# NeighborFood

지역 기반 식재료 공동구매 플랫폼 — FastAPI + SQLite 백엔드, 정적 HTML 프런트엔드

버전: **v2.1.0** (2026-08-22)
문서 최종 갱신: 2026-09-12 (관리자 기능 실데이터 연동 완료, `seed_admin.py` 복원 반영)

---

## 주요 기능

- 회원가입 / 로그인 (login_id + 비밀번호, PBKDF2-SHA256)
- 게시글 작성·수정·삭제 (나눔 / 공동구매 / 교환), 자동 만료 처리
- 공동구매 참여 / 취소 (원자적 카운터, 중복·정원·미납 차단)
- 공동구매 정산 (분담금 자동 계산, GPS→QR 2단계 순차 인증 후 납부 활성화, 노쇼 신고/취소)
- QR 코드 대면 거래 인증 (`frontend/vendor/html5-qrcode.min.js` 로컬 사본 우선 로드 → CDN 장애 시에도 스캔 동작)
- 영수증 OCR 인증 (CLOVA OCR → Tesseract fallback, v2.1 마트형 파서 지원)
- 냉장고 관리 (영수증 인증 품목 자동 등록, 유통기한 D-day)
- 1:1 / 그룹 채팅 (REST 폴링, 참여 취소 시 시스템 메시지 삽입)
- 매너 평가 (thumbs up/down → trust_score 반영)
- 찜(위시리스트), 신고, 공지사항
- GPS 위치 인증 (Haversine 100m 서버 재검증)
- 카카오맵 연동 (`.env` 동적 로드, 소스코드 키 하드코딩 금지)
- 관리자 대시보드 (회원·신고·공지·채팅 모니터링)

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

### 5. 관리자 계정 생성

```bash
python seed_admin.py                  # 신규 생성 (login_id=Admin, pw=admin0000)
python seed_admin.py <login_id>       # 기존 계정을 admin 역할로 승격
```

> 2026-09-12: `seed_admin.py`가 복원되어 정상 동작합니다. 프로덕션 배포 전에는 기본 비밀번호(`admin0000`)를 변경하세요.

### 6. (선택) 더미 데이터 주입

```bash
python seed_posts.py                  # 더미 게시글 시드
python Seed_Account.py                # Capstone_1 계정 + 완료 거래 1건
python Seed_capstone_settlement.py    # Capstone_1~3 계정 + 공동구매 정산 시드
```

> ⚠️ `seed_posts.py`, `Seed_Account.py`, `Seed_capstone_settlement.py` 모두 2026-09-08 기준 저장소에 존재하지 않는 것으로 확인되었습니다. 더미 데이터가 필요하면 API(`POST /posts` 등)를 직접 호출하거나 스크립트 재도입을 기다려야 합니다.

### 7. (선택) 영수증 파서 테스트 실행

```bash
python tests/test_receipt_parser_v212.py
```

`pytest` 등 외부 프레임워크 없이 단독 실행되며, 마트형(농협)·카페형(스타벅스) 영수증 구조에 대한 5개 회귀 테스트를 수행합니다.

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
│   ├── config.py            # 경로·상수 설정 (SESSION_TTL_DAYS=30, RECEIPT_TRUST_DELTA=0.3)
│   ├── core/
│   │   ├── deps.py          # get_current_user / get_current_admin 의존성
│   │   └── utils.py         # 시간·토큰·비밀번호 헬퍼
│   ├── db/
│   │   ├── base.py          # make_conn, init_all_databases
│   │   ├── auth_db.py       # users, sessions, auth_codes, posts
│   │   ├── transaction_db.py# transactions, groupbuy_participants, manner_ratings
│   │   ├── settlement_db.py # settlements, settlement_shares CRUD + GPS/QR 검증
│   │   ├── member_db.py     # wishlists, conversations, messages, conversation_members
│   │   ├── fridge_db.py     # fridge_items
│   │   ├── admin_db.py      # notices, reports
│   │   ├── qr_db.py         # qr_sessions
│   │   ├── receipt_db.py    # receipts + OCR (CLOVA/Tesseract, parser v2.1)
│   │   └── location_verify_db.py  # location_verify_sessions (반경 100m)
│   ├── models/              # Pydantic 요청/응답 스키마
│   │   └── auth.py  user.py  post.py  qr.py  receipt.py  member.py  fridge.py
│   └── routers/             # API 라우터 (엔드포인트별 1파일)
│       ├── auth.py
│       ├── posts.py         # 게시글 CRUD·참여·취소·약속·my-status·자동 만료
│       ├── users.py
│       ├── wishlist.py
│       ├── chat.py          # 1:1 + 그룹 채팅
│       ├── transactions.py
│       ├── settlements.py   # 공동구매 정산 (GPS→QR 2단계 인증, 노쇼 처리)
│       ├── ratings.py       # 매너 평가 (trust_score 반영)
│       ├── fridge.py
│       ├── admin.py
│       ├── reports.py
│       ├── qr.py
│       ├── receipt.py
│       └── location_verify.py
├── frontend/                # 정적 HTML 프런트엔드
│   ├── shared/
│   │   ├── auth.js          # fetch 래퍼 (Bearer 토큰 자동 주입)
│   │   ├── guard.js         # 회원 전용 페이지 보호 (nfRequireMember)
│   │   ├── adminGuard.js    # 관리자 전용 페이지 보호 (nfRequireAdmin) [신규 2026-09-12]
│   │   ├── profile.js       # 프로필 조회·수정·탈퇴 헬퍼
│   │   └── tokens.css       # 디자인 토큰 (CSS 변수)
│   ├── vendor/
│   │   └── html5-qrcode.min.js  # QR/바코드 스캔 라이브러리 로컬 사본 [신규] — CDN 장애 대비 1차 로드 경로
│   ├── Home.html
│   ├── Login.html
│   ├── Signup.html
│   └── ...
└── tests/
    └── test_receipt_parser_v212.py  # 영수증 파서 회귀·유닛 테스트 [신규] — pytest 없이 단독 실행 가능
```

> ⚠️ **문서-저장소 정합성 안내 (2026-09-08 확인, 2026-09-12 갱신)**
> 이전 버전 문서에는 아래 7개 루트 스크립트가 명시되어 있었으나, 저장소 최신 구조 확인 결과 더 이상 존재하지 않는 것으로 확인되어 트리에서 제거했습니다. 각 스크립트의 과거 역할은 참고용으로 남겨둡니다.
>
> | 파일 | 과거 역할 | 현재 상태 |
> |---|---|---|
> | `seed_admin.py` | 관리자 계정 부트스트랩 | ✅ **2026-09-12 복원**, 정상 동작 |
> | `seed_posts.py` | 더미 게시글 시드 (개발용) | ⬜ 미존재 |
> | `Seed_Account.py` | 테스트 계정 + 완료 거래 시드 | ⬜ 미존재 |
> | `Seed_capstone_settlement.py` | 정산 수동 테스트용 시드 | ⬜ 미존재 |
> | `Seed_settlement_verify.py` | 정산 API 자동 검증 스크립트 | ⬜ 미존재 |
> | `nf_functional_test.py` | 전체 기능 자동 테스트 스크립트 | ⬜ 미존재 |
> | `reset_db.py` | DB 초기화 (테이블 DELETE + Admin 재생성) | ⬜ 미존재 |
>
> 현재 저장소에 존재하는 자동화 테스트는 `tests/test_receipt_parser_v212.py`(영수증 파서 전용) 하나뿐이며, 더미 시드·정산 등 나머지 기능은 위 스크립트가 없는 상태이므로 별도 수동 절차로 병행해야 합니다. 관리자 계정 생성은 `seed_admin.py` 복원으로 정상 동작합니다(아래 "5. 관리자 계정 생성" 참고). 아래 "6. 더미 데이터 주입" 안내는 여전히 미존재 상태를 반영합니다.

---

## 인증 방식

Bearer 토큰 세션 인증을 사용합니다.

1. `POST /api/auth/login` — login_id + password → `{ token, expiresAt }` 반환
2. 이후 모든 인증 필요 API 요청에 `Authorization: Bearer <token>` 헤더 포함
3. `frontend/shared/auth.js`가 `window.fetch`를 래핑하여 토큰을 자동 주입

토큰 유효기간은 `config.py`의 `SESSION_TTL_DAYS`로 조정합니다 (기본 **30일**).

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
| `/api/auth` | 인증 | 회원가입, 로그인, 로그아웃, OTP 비밀번호 재설정 |
| `/posts` | 게시글 | 목록·상세·작성·수정·삭제, 공동구매 참여/취소, 약속 확정, my-status |
| `/api/users` | 회원 | 프로필 조회·수정, 비밀번호 변경, 회원 탈퇴, 동네 인증 |
| `/api/wishlist` | 찜 목록 | 찜 추가·취소, 내 찜 목록 |
| `/api/chats` | 채팅 | 1:1·그룹 채팅방 생성, 메시지 송수신 (REST 폴링) |
| `/api/transactions` | 거래 | 거래 생성·조회·상태 변경 |
| `/api/settlements` | 정산 | 공동구매 정산 (분담 자동계산, GPS/QR 인증, 노쇼 신고/취소) |
| `/api/ratings` | 매너 평가 | thumbs up/down 평가 등록·수정·삭제, trust_score 반영 |
| `/api/fridge` | 내 냉장고 | 영수증 인증 품목 등록, 목록 조회, 상태 변경 |
| `/api/qr` | QR 거래 인증 | QR 세션 발급·검증 |
| `/api/receipt` | 영수증 인증 | OCR 업로드, 품목 선택·인증 |
| `/api/admin` | 관리자 | 회원·신고·공지 관리, 채팅 모니터링, 대시보드 통계(`/stats`) |
| `/api/reports` | 신고 | 게시글·회원 신고 접수·취소 |
| `/api/location-verify` | GPS 위치 인증 | 위치 인증 세션 생성·검증 (Haversine 100m) |
| `/api/notices` | 공개 공지 | 비인증 공지 조회 (Help.html 아코디언 표시) |
| `/api/config/kakao-key` | 설정 | 카카오 JS 키 반환 (프론트 동적 로드용) |

---

## 테스트 계정 기본값

| 계정 | login_id | password | 역할 |
|---|---|---|---|
| 관리자 | `Admin` | `admin0000` | admin |
| 일반1 | `Capstone_1` | `capstone1` | user |
| 일반2 | `Capstone_2` | `capstone2` | user |
| 일반3 | `Capstone_3` | `capstone3` | user |