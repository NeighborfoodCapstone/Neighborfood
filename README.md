# NeighborFood

지역 기반 식재료 공동구매 플랫폼 — FastAPI + SQLite 백엔드, 정적 HTML 프런트엔드 + React(Vite) 프런트엔드(홈 화면, 부분 마이그레이션 진행 중)

버전: **v2.1.0** (2026-08-22)
문서 최종 갱신: 2026-09-19 (문서-소스 정합성 점검 반영: `reset_db.py` 존재 확인, 라우터 경로 정정, 미구현 API(비밀번호 변경) 표기, 관련 문서 목록 추가)
이전 갱신: 2026-09-14 (`frontend-react/`(Vite + React 19 + TypeScript) 신규 추가 — 홈 화면 부분 마이그레이션 반영)

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
- **(신규 2026-09-14) React(Vite) 홈 화면** — 기존 정적 `Home.html`과 별도로 `frontend-react/`에 SPA 홈 피드 구현. 나머지 화면은 정적 HTML로 하드 네비게이션하는 하이브리드 구조 (§"React 프런트엔드" 절 참고)

---

## 요구사항

- Python 3.10 이상
- Node.js 20 이상 (React 프런트엔드 `frontend-react/` 실행 시 필요 — `npm` 포함)
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
ALLOWED_ORIGINS=        # CORS 허용 도메인(콤마 구분). 비우면 * 허용 — 배포 시 실제 도메인 필수
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

### 5. (선택, 신규 2026-09-14) React 프런트엔드 실행 — 홈 화면

`frontend-react/`에 Vite + React 19 + TypeScript 기반의 홈 화면이 추가되었습니다. 기존 정적 HTML(`frontend/Home.html`)을 완전히 대체하는 것이 아니라 **홈 피드 화면만 React로 재구현한 하이브리드 구조**입니다 — 지도·등록·내 활동·마이페이지 등 나머지 화면은 여전히 기존 정적 HTML로 이동합니다.

```bash
cd frontend-react
npm ci
npm run dev
```

- 기본 접속: [http://localhost:5173](http://localhost:5173) (Vite 기본 포트)
- 백엔드 API 주소는 `VITE_API_BASE_URL` 환경변수로 지정합니다(미설정 시 `http://127.0.0.1:8000` 기본값 사용). 필요 시 `frontend-react/.env.local`을 새로 만들어 추가하세요(`.env.local`은 Vite 기본 gitignore 항목이므로 Git에 올라가지 않습니다):
  ```
  VITE_API_BASE_URL=http://127.0.0.1:8000
  ```
- 백엔드(`uvicorn main:app`)가 먼저 실행 중이어야 홈 피드(`GET /posts`)가 정상 로드됩니다.
- CORS: `main.py`의 `ALLOWED_ORIGINS` 미설정 시 전체 허용(`*`)이므로 로컬 개발 중에는 별도 설정이 필요 없습니다. 배포 시 React 앱이 서빙되는 도메인을 `.env`의 `ALLOWED_ORIGINS`에 반드시 추가하세요.
- 기타 명령: `npm run build`(`tsc -b && vite build`), `npm run lint`(oxlint), `npm run preview`

> ⚠️ **알려진 미비 사항 (2026-09-14 확인)**: 루트 `.env.example`에는 아직 `VITE_API_BASE_URL` 템플릿 항목이 없습니다(위 값을 수동으로 추가해야 함). `frontend-react/README.md`는 Vite 기본 템플릿 문서 그대로이며 프로젝트 설명으로 아직 교체되지 않았습니다.

### 6. 관리자 계정 생성

```bash
python seed_admin.py                  # 신규 생성 (login_id=Admin, pw=admin0000)
python seed_admin.py <login_id>       # 기존 계정을 admin 역할로 승격
```

> 2026-09-12: `seed_admin.py`가 복원되어 정상 동작합니다. 프로덕션 배포 전에는 기본 비밀번호(`admin0000`)를 변경하세요.

### 7. (선택) 더미 데이터 주입

```bash
python seed_posts.py                  # 더미 게시글 시드
python Seed_Account.py                # Capstone_1 계정 + 완료 거래 1건
python Seed_capstone_settlement.py    # Capstone_1~3 계정 + 공동구매 정산 시드
```

> ⚠️ `seed_posts.py`, `Seed_Account.py`, `Seed_capstone_settlement.py` 모두 2026-09-08 기준 저장소에 존재하지 않는 것으로 확인되었습니다. 더미 데이터가 필요하면 API(`POST /posts` 등)를 직접 호출하거나 스크립트 재도입을 기다려야 합니다.

### 8. (선택) 영수증 파서 테스트 실행

```bash
python tests/test_receipt_parser_v212.py
```

`pytest` 등 외부 프레임워크 없이 단독 실행되며, 마트형(농협)·카페형(스타벅스) 영수증 구조에 대한 5개 회귀 테스트를 수행합니다.

### 9. (선택) DB 초기화

```bash
python reset_db.py                    # 확인 프롬프트 후 모든 회원·게시글 및 연관 데이터 삭제 + Admin 재생성
python reset_db.py --yes              # 확인 프롬프트 생략
python reset_db.py --pw MyPass1!      # Admin 비밀번호 직접 지정 (기본 admin0000)
```

> ⚠️ **전체 데이터가 삭제됩니다.** 프로젝트 루트에서 실행해야 `data/neighborfood.db`를 찾습니다. 서버가 실행 중이면 먼저 종료하세요.

---

## 폴더 구조

```
Neighborfood/
├── main.py                  # FastAPI 앱 진입점
├── seed_admin.py            # 관리자 계정 생성/승격 (2026-09-12 복원)
├── reset_db.py              # DB 초기화 — 전체 데이터 삭제 + Admin 재생성
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
├── frontend-react/          # React(Vite) 프런트엔드 [신규 2026-09-14] — 홈 화면 부분 마이그레이션
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── assets/               # hero.png, react.svg, vite.svg
│   │   ├── neighborfood/         # 프로젝트 전용 코드
│   │   │   ├── api.ts            # 백엔드 연동 (getPosts, legacy() 헬퍼) — VITE_API_BASE_URL 사용
│   │   │   ├── AppLayout.tsx     # 헤더 + 하단 네비게이션 공통 레이아웃
│   │   │   ├── HomePage.tsx      # 홈 피드 (카테고리·검색·게시글 카드, GET /posts 연동)
│   │   │   ├── home.css          # HomePage 전용 스타일
│   │   │   └── Icon.tsx          # 인라인 SVG 아이콘 컴포넌트
│   │   ├── App.css
│   │   ├── App.tsx               # AppLayout + HomePage 조합
│   │   ├── index.css
│   │   └── main.tsx              # React 진입점 (StrictMode)
│   ├── index.html             # Vite 진입 HTML (#root, /src/main.tsx 로드)
│   ├── package.json           # react 19.2, react-dom 19.2 / devDeps: vite 8, typescript, oxlint 등
│   ├── package-lock.json
│   ├── tsconfig.json  tsconfig.app.json  tsconfig.node.json
│   ├── vite.config.ts         # @vitejs/plugin-react 플러그인 등록
│   ├── .oxlintrc.json         # Oxlint 설정 (ESLint 대체 린터)
│   ├── .gitignore
│   └── README.md              # ⚠️ Vite 템플릿 기본 문서 — 아직 프로젝트 설명으로 미교체
├── tests/
│   └── test_receipt_parser_v212.py  # 영수증 파서 회귀·유닛 테스트 [신규] — pytest 없이 단독 실행 가능
├── README.md  Capstone.md  NeighborFood_Architecture_Plan.md  neighborfood_ERD.md
├── Settlement_Implementation_Plan.md  Neighborfood_React_실행_안내.md   # 프로젝트 문서 (아래 "관련 문서" 참고)
```

> ℹ️ **React 프런트엔드 추가 안내 (2026-09-14, 신규)**
> `frontend-react/`가 신규 추가되었습니다(Vite 8 + React 19 + TypeScript, 린터는 ESLint 대신 **Oxlint** 사용). 현재는 홈 화면(`HomePage.tsx`)만 React로 구현되어 있고, 지도·등록·내 활동·마이페이지·상세 화면 등 나머지 이동은 `src/neighborfood/api.ts`의 `legacy(page)` 헬퍼(`${backend}/frontend/${page}`)를 통해 기존 정적 HTML로 **하드 네비게이션**(SPA 라우팅 아님)합니다. 신규 백엔드 API는 추가되지 않았으며, 기존 `GET /posts` 목록 API를 그대로 재사용합니다.
> **후속 필요 작업**: ① `.env.example`에 `VITE_API_BASE_URL` 템플릿 항목 추가, ② `frontend-react/README.md`를 Vite 기본 템플릿에서 프로젝트 설명으로 교체, ③ 배포 시 `.env`의 `ALLOWED_ORIGINS`에 React 앱 서빙 도메인 추가.

> ⚠️ **문서-저장소 정합성 안내 (2026-09-08 확인, 2026-09-12 갱신)**
> 이전 버전 문서에는 아래 7개 루트 스크립트가 명시되어 있었고, 2026-09-08 확인 시 모두 없는 것으로 보고 트리에서 제거했습니다. **2026-09-19 재확인 결과 `seed_admin.py`(2026-09-12 복원)와 `reset_db.py`는 저장소에 존재**하며, 나머지 5개는 여전히 없습니다.
>
> | 파일 | 과거 역할 | 현재 상태 |
> |---|---|---|
> | `seed_admin.py` | 관리자 계정 부트스트랩 | ✅ **2026-09-12 복원**, 정상 동작 |
> | `seed_posts.py` | 더미 게시글 시드 (개발용) | ⬜ 미존재 |
> | `Seed_Account.py` | 테스트 계정 + 완료 거래 시드 | ⬜ 미존재 |
> | `Seed_capstone_settlement.py` | 정산 수동 테스트용 시드 | ⬜ 미존재 |
> | `Seed_settlement_verify.py` | 정산 API 자동 검증 스크립트 | ⬜ 미존재 |
> | `nf_functional_test.py` | 전체 기능 자동 테스트 스크립트 | ⬜ 미존재 |
> | `reset_db.py` | DB 초기화 (테이블 DELETE + Admin 재생성) | ✅ **존재 확인 (2026-09-19)** — 아래 "9. DB 초기화" 참고 |
>
> 현재 저장소에 존재하는 자동화 테스트는 `tests/test_receipt_parser_v212.py`(영수증 파서 전용) 하나뿐이며(`reset_db.py`는 테스트가 아닌 DB 초기화 도구), 더미 시드·정산 검증 등 나머지 기능은 표에서 ⬜ 미존재로 표기된 스크립트가 없는 상태이므로 별도 수동 절차로 병행해야 합니다. 관리자 계정 생성은 `seed_admin.py` 복원으로 정상 동작합니다(아래 "6. 관리자 계정 생성" 참고). 아래 "7. 더미 데이터 주입" 안내는 여전히 미존재 상태를 반영합니다.

---

## 인증 방식

Bearer 토큰 세션 인증을 사용합니다.

1. `POST /api/auth/login` — login_id + password → `{ token, expiresAt }` 반환
2. 이후 모든 인증 필요 API 요청에 `Authorization: Bearer <token>` 헤더 포함
3. `frontend/shared/auth.js`가 `window.fetch`를 래핑하여 토큰을 자동 주입

토큰 유효기간은 `config.py`의 `SESSION_TTL_DAYS`로 조정합니다 (기본 **30일**).

> `frontend-react/`는 현재 로그인 필요 화면을 구현하지 않았으므로(홈 피드만 존재) 별도의 토큰 저장·주입 로직이 없습니다. 회원 전용 기능은 `legacy()`로 이동한 기존 정적 HTML에서 `auth.js`가 계속 처리합니다.

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
| `/api/auth` | 인증 | 회원가입(`/register`), 로그인(`/login`) |
| (접두사 없음) | 인증 | 로그아웃 `POST /logout`, 비밀번호 재설정 OTP `POST /request-auth` · `POST /reset-password` |
| `/posts` | 게시글 | 목록·상세·작성·수정·삭제, 공동구매 참여/취소, 약속 확정, my-status |
| `/api/users` | 회원 | 프로필 조회·수정, 회원 탈퇴, 동네 인증(동네 이름·인증일 저장, 좌표는 국내 범위 검증만) — ⚠️ 로그인 상태 비밀번호 변경 API는 **미구현** |
| `/api/wishlist` | 찜 목록 | 찜 추가·취소, 내 찜 목록 |
| `/api/chats` | 채팅 | 1:1·그룹 채팅방 생성, 메시지 송수신 (REST 폴링) |
| `/api/transactions` | 거래 | 거래 생성·조회·상태 변경 |
| `/api/settlements` | 정산 | 공동구매 정산 (분담 자동계산, GPS/QR 인증, 노쇼 신고/취소) |
| `/api/ratings` | 매너 평가 | thumbs up/down 평가 등록·수정·삭제, 받은 평가·거래별 내 평가 조회, trust_score 반영 |
| `/api/fridge` | 내 냉장고 | 영수증 인증 품목 등록, 목록 조회, 상태 변경 |
| `/api/qr` | QR 거래 인증 | QR 세션 발급·검증 |
| `/api/receipt` | 영수증 인증 | OCR 업로드, 품목 선택·인증 |
| `/api/admin` | 관리자 | 회원·신고·공지 관리, 채팅 모니터링, 대시보드 통계(`/stats`) |
| `/api/reports` | 신고 | 게시글·회원 신고 접수·취소, 내 신고 목록(`GET /my`) |
| `/api/location-verify` | GPS 위치 인증 | 위치 인증 세션 생성·검증 (Haversine 100m) |
| `/api/notices` | 공개 공지 | 비인증 공지 조회 (Help.html 아코디언 표시) |
| `/api/config/kakao-key` | 설정 | 카카오 JS 키 반환 (프론트 동적 로드용) |

> `frontend-react/`는 신규 API를 추가하지 않았으며 위 목록의 `GET /posts`(게시글 목록)만 재사용합니다.

---

## 테스트 계정 기본값

| 계정 | login_id | password | 역할 |
|---|---|---|---|
| 관리자 | `Admin` | `admin0000` | admin |
| 일반1 | `Capstone_1` | `capstone1` | user |
| 일반2 | `Capstone_2` | `capstone2` | user |
| 일반3 | `Capstone_3` | `capstone3` | user |

---

## 관련 문서

| 문서 | 용도 |
|---|---|
| `Capstone.md` | 개발 컨텍스트·제약사항·범위(포함/제외) 요약 |
| `NeighborFood_Architecture_Plan.md` | 아키텍처 현황, API 전체 목록, 개발 이력, 잔여 작업 |
| `neighborfood_ERD.md` | DB 구조(ERD)와 디렉토리 구조 |
| `Settlement_Implementation_Plan.md` | 공동구매 정산 시스템 설계·구현 계획 |
| `Neighborfood_React_실행_안내.md` | 백엔드 + React(`frontend-react/`) 로컬 실행 안내서 |