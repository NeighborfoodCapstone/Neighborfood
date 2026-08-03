# Role: Senior Full-stack Engineer Assistant
당신은 '1인 가구 지역 식재료 공동구매 플랫폼(NeighborFood)' 프로젝트의 전담 개발자입니다. 아래의 컨텍스트와 제약 사항을 완벽히 숙지하고 개발을 수행하십시오.

> 최종 갱신: 2026-08-03 · GPS 위치 인증 보안 강화·실흐름 연결 + Kakao 키 하드코딩 전면 제거 + 수령 장소 지정 완료

현재 완료:
- 게시판 (나눔/공동구매/교환 통합)
- 지도 (Kakao Map)
- QR 거래 인증 / 바코드 스캔
- 영수증 OCR 인증
- 회원 기능 (ID/비밀번호 가입·로그인, 프로필 수정·탈퇴, Bearer 세션 인증/인가)
- OTP 휴대폰 인증 — **비밀번호 재설정 전용**으로 용도 변경
- 찜 목록 · 1:1 채팅(REST 폴링) · 동네(위치) 인증 백엔드
- 단일 SQLite 통합(`neighborfood.db`) + 외래키(FK) 적용
- 거래 앵커(`transactions`, `appointment_at` 컬럼 포함) · 공동구매 참여자(`groupbuy_participants`)
- 거래(transactions) API · 회원 화면 실데이터 연동 · 프로필 확장(이메일·소개·관심·식이)
- 내 냉장고(`fridge_items` + `/api/fridge`, 유통기한 D-day) — `Fridge.html`
- 그룹(공동구매) 채팅(`conversations.kind`·`conversation_members` + `/api/chats/group/*`) — `Group_Chat.html`
- 관리자 기능(`/api/admin/*`, `notices`·`reports`, 6종 화면 연결) + `seed_admin.py`(계정 부트스트랩)
- 신고(`reports` + `POST /api/reports` → 관리자 처리)
- 배포 대응: 전 화면 `API_BASE`=`window.location.origin`(상대경로), `tokens.css` 전체 39개 화면 적용 완료
- GPS 위치 인증(`location_verify_sessions` + `/api/location-verify/*`, 더미 타겟 생성·GPS 반경 체크·QR 연동) — `Local_Verify_Demo.html`
- 공동구매 참여 레이스 컨디션 수정 — `posts.py`에서 원자적 UPDATE로 전환 (2026-07-09)
- `neighborfood_schema.sql` 동기화 — 코드에만 있던 6개 테이블(`wishlists`·`conversations`·`conversation_members`·`messages`·`notices`·`reports`) DDL 반영, 스키마 파일=코드 완전 일치 (2026-07-09)
- **카카오맵 키 하드코딩 전면 제거** — 전 화면(`Map` + 잔여 6개 화면)이 `/api/config/kakao-key` 동적 로드로 전환, 소스 내 실키 완전 소거 (2026-08-03)
- **GPS 위치 인증 보안 강화 + 실흐름 연결** — 전 API Bearer 인증 필수, `subject_id` 서버 강제 고정, 소유자 검증(`_assert_owner`), 이력 본인 필터, QR 인증 성공 시 `QR_VERIFIED` 연동 실호출, `Local_Verify_Demo.html` 로그인 가드, `Reservation.html` 진입점 연결 (2026-08-03)
- **수령 장소 지정** — `Reservation.html`이 게시글의 실제 `address`/`lat`/`lng`를 장소 카드·지도 링크·신청 요약에 반영, 주소 미등록 시 "채팅으로 협의" 폴백 (2026-08-03)

미완료(잔여):
- 정산(`settlements` 테이블 + API + `Settlement.html` 연동 — 현재 fetch 0건 정적 목업)
- 상호 매너 평가(`manner_ratings` 테이블 + API — `trust_score` 갱신 로직 자체가 부재)
- 공동구매 참여 취소 흐름 (`gb_current` 원자적 감소 + 참여자 삭제)

주의:
- 기존 구조 유지
- 최소 수정 원칙
- 전체 리팩토링 금지

잠재 이슈 (알려진 위험):
- (해결됨) **공동구매 인원 정합성**: `posts.py`의 `join_groupbuy`가 `SET gb_current = gb_current + 1 WHERE ... AND gb_current < gb_target` 원자적 UPDATE로 전환 완료(2026-07-09). 단, 참여 취소(cancel) 흐름은 아직 미정의.
- **trust_score 레이스**: 매너 평가 시 `SET trust_score = trust_score + ?` 형태의 원자적 UPDATE 필수(매너 평가 기능 자체는 아직 미구현).
- **SQLite 동시성**: 채팅 폴링(4초) + 정산·평가 쓰기 경합 시 `database is locked` 드물게 발생 가능. WAL + `busy_timeout`으로 완화 중.
- **배포 보안**: 도메인 제한·토큰 취급 정책은 시연/개발 수준. 실제 배포 시 점검 필요. CORS `allow_origins=["*"]`, `seed_admin.py` 기본 비밀번호는 배포 도메인 확정 전까지 의도적으로 보류.
- **OCR 환경 의존**: 실제 OCR 구동을 위해 서버에 `tesseract` 설치 필요. 미설치 시 데모 폴백.
- (해결됨) **Kakao 키 하드코딩**: 전 화면 `/api/config/kakao-key` 동적 로드로 전환 완료(2026-08-03). 단, 이미 노출된 이력이 있는 키라면 GitHub 공개 전 카카오 개발자 콘솔에서 키 재발급 권장.
- (해결됨) **GPS 위치 인증 무인증 공개**: 전 API 인증 필수 + 소유자 검증 + 이력 본인 필터로 전환 완료(2026-08-03). 단, 타겟 좌표를 클라이언트가 지정하는 구조(`dummy-target`)는 유지 중 — 실 거래 연동 시 `posts.lat/lng` 기반 서버 지정으로 전환 필요.
- (해결됨) 관리자 계정 생성 → `seed_admin.py`: `python seed_admin.py`(admin 생성) / `python seed_admin.py <login_id>`(기존 계정 승격). 전화번호 충돌 자동 회피, 멱등.

# Response Rules

When modifying code:

1. Do not rewrite entire files unnecessarily.
2. Prefer minimal diff changes.
3. Preserve existing folder structure.
4. Avoid introducing new dependencies unless required.
5. Explain major architectural changes before applying them.
6. Do not rename files without explicit instruction.
7. Prioritize stability over abstraction.

# 1. Project Core & Constraint Summary (가장 중요)
* **Goal:** 지역 기반 식재료 공동구매 웹앱. **단일 FastAPI 백엔드 + 정적 HTML(Tailwind) 프론트엔드 + 단일 SQLite** 구성.
* **Compliance:** 식품위생법 준수(소분 판매 금지, 완제품/원형 농산물 거래만 허용).
* **Strict Constraint:**
    1. 백엔드는 **단일 FastAPI 서버**로 운영한다. (Spring Boot/MySQL 분리 계획은 폐기됨)
    2. 데이터베이스는 **단일 SQLite 파일(`data/neighborfood.db`)**을 사용한다. (MariaDB 통합 계획은 폐기됨)
    3. AI 처리는 OCR(영수증) 등 경량 기능으로 한정한다. (추천/객체 인식 파이프라인 금지)
    4. 'Immutable Paths'에 명시된 구조와 핵심 로직은 가능한 한 유지한다.
    5. 하드코딩 금지 (`.env` 사용).
    6. 비동기 처리 강제 (UI 블로킹 금지).

> 참고: 초기 기획의 Next.js / Spring Boot / MySQL / Redis / S3 다중 스택은 캡스톤 범위에 맞춰 **단일 FastAPI + SQLite**로 단순화되었습니다. 프론트엔드는 별도 SPA 프레임워크 없이 정적 HTML + Tailwind(CDN)로 작성되고 FastAPI가 함께 서빙합니다.

---
# 2. Tech Stack
* **Frontend:** 정적 HTML + Tailwind CSS (CDN). FastAPI `/frontend` 또는 Live Server로 서빙. 공통 JS는 `frontend/shared/`.
* **Backend:** FastAPI (Python 3.10+), 3-Tier 모듈 구조(`app/config·core·db·models·routers`).
* **Database:** SQLite 3 단일 파일 `data/neighborfood.db` (외래키 활성화, WAL).
* **Auth:** **ID/비밀번호 가입·로그인**(가입 시 휴대폰 번호 입력만 받고 OTP 검증 없음) → 세션 토큰(Bearer) 발급. OTP는 **비밀번호 재설정에만** 사용. 비밀번호는 표준 라이브러리 PBKDF2-SHA256(`salt$hash`)으로 저장. 인가는 `app/core/deps.py` 의존성, 프런트는 `shared/auth.js`(토큰 보관·주입) + `shared/guard.js`(회원 전용 페이지 가드).
* **접근 정책:** 비회원은 **게시판(목록·상세)과 지도(Map)만** 이용 가능. 글 작성·거래·채팅·찜·내 활동·마이페이지·동네 인증은 회원 전용. 역할은 비회원/회원/관리자 3단계. 관리자 기능은 `get_current_admin` 가드의 `/api/admin/*`로 구현되어 있으며, admin 계정은 `seed_admin.py`로만 생성/승격한다.
* **AI Module:** FastAPI 내 OCR (pillow + pytesseract, 미설치 시 데모 폴백).
* **Storage:** 로컬 `uploads/` 디렉토리 (S3 등 외부 스토리지는 향후 선택 사항).
* **users 확장 컬럼:** `email`, `bio`, `interests`(JSON), `dietary`(JSON) — 프로필 PATCH로 저장, `Edit_Profile.html` 연동 완료.

---
# 3. Code Style & Rules
* **Indentation:** 4 Spaces (No Tabs)
* **Naming:**
    * Pydantic 모델/클래스: PascalCase
    * 함수/변수: snake_case (Python 관례)
    * JS 함수/변수: camelCase
    * DB 컬럼/SQL: snake_case
    * API 응답 키: camelCase (기존 QR/영수증 라우터 관례 유지)
* **Tailwind:** Layout > Box Model > Typography > Visuals > Interactive 순서 정렬. 인라인 스타일 지양.

---
# 4. Immutable Paths (주의)
아래 파일 및 구조는 가능한 한 유지한다.
- 대규모 리팩토링 금지
- 파일명/구조 변경 금지
- 기존 핵심 로직 삭제 금지

단, 버그 수정, 기능 추가, 최소 수정(minimal diff)은 허용한다. 명시적 요청 없이 전체 구조 변경을 수행하지 않는다.

**실제 디렉토리 구조** (`app`=서버 / `frontend`=화면·JS / `sql`=스키마 / `data`=실제 DB)

```
NEIGHBORFOOD/
├── app/                         ▶ 서버 파일 (FastAPI 백엔드)
│   ├── config.py                  경로 상수, DB_PATH, SESSION_TTL_DAYS
│   ├── core/                      공통 유틸
│   │   ├── utils.py               시간/해시/토큰 헬퍼
│   │   └── deps.py                인증·인가 의존성 (get_current_user, get_current_admin)
│   ├── db/                        DB 접속 계층 (모두 neighborfood.db 공유)
│   │   ├── base.py                make_conn()(WAL+busy_timeout), init_all_databases()
│   │   ├── auth_db.py             users·sessions·auth_codes·posts
│   │   ├── transaction_db.py      transactions·groupbuy_participants
│   │   ├── member_db.py           wishlists·conversations(+kind)·messages·conversation_members
│   │   ├── fridge_db.py           fridge_items (내 냉장고)
│   │   ├── admin_db.py            notices·reports
│   │   ├── qr_db.py               qr_sessions
│   │   ├── receipt_db.py          receipts (+OCR)
│   │   └── location_verify_db.py  location_verify_sessions (GPS 위치 인증)
│   ├── models/                    Pydantic 모델
│   │   └── auth.py  user.py  post.py  qr.py  receipt.py  member.py  fridge.py
│   └── routers/                   API 라우터
│       └── auth.py  users.py  posts.py  qr.py  receipt.py  wishlist.py  chat.py
│                    transactions.py  fridge.py  admin.py  reports.py  location_verify.py
├── frontend/                    ▶ HTML 페이지 + JS 파일
│   ├── *.html                     사용자/관리자 화면 (Home·Verify·Create_Post·QR_Scan·Local_Verify_Demo·Admin_* 등)
│   │   (인증 흐름) Splash · Onboarding · Login · Signup · Password_Reset (.html)
│   └── shared/                    공통 JS/CSS
│       ├── auth.js                토큰 저장(localStorage) + fetch 자동 인증 주입
│       ├── guard.js               회원 전용 페이지 가드 (nfRequireMember())
│       ├── profile.js             프로필/탈퇴 호출 헬퍼
│       └── tokens.css             디자인 토큰(CSS 변수)
├── sql/                         ▶ 현재 프로젝트 스키마
│   └── neighborfood_schema.sql
├── data/                        ▶ 실제 데이터베이스
│   └── neighborfood.db            단일 SQLite (startup 자동 생성, gitignore)
├── uploads/                     업로드 이미지 (gitignore)
├── venv/  .venv/  .vscode/  __pycache__/
├── main.py                      FastAPI 엔트리포인트 (미들웨어·마운트·라우터 등록)
├── posts.json                   초기 게시글 시드 데이터
├── seed_admin.py                관리자 계정 부트스트랩(1회성)
├── seed_posts.py                더미 게시글 시드(개발용)
├── Cpastone.md  NeighborFood_Architecture_Plan.md  neighborfood_ERD.md  README.md
├── requirements.txt
└── .env  .env.example  .gitignore
```

**핵심 파일 (변경 주의)**
* **엔트리포인트:** `main.py` (앱 생성·미들웨어·정적 마운트·라우터 등록 전담)
* **설정/공통:** `app/config.py`, `app/core/utils.py`, `app/core/deps.py`
* **DB 레이어:** `app/db/base.py`, `auth_db.py`, `transaction_db.py`, `member_db.py`, `fridge_db.py`, `admin_db.py`, `qr_db.py`, `receipt_db.py`, `location_verify_db.py`
* **스키마 정의:** `sql/neighborfood_schema.sql` (단일 진실 소스), 산출물 `data/neighborfood.db`
* **모델:** `app/models/auth.py`, `user.py`, `post.py`, `qr.py`, `receipt.py`, `member.py`, `fridge.py`
* **라우터:** `app/routers/auth.py`, `users.py`, `posts.py`, `qr.py`, `receipt.py`, `wishlist.py`, `chat.py`, `transactions.py`, `fridge.py`, `admin.py`, `reports.py`, `location_verify.py`
* **프런트 공통:** `frontend/shared/auth.js`, `frontend/shared/guard.js`, `frontend/shared/profile.js`, `frontend/shared/tokens.css`

---
# 5. Scope & Exclusion

## Implemented Features (Already Completed)
아래 기능은 이미 구현되어 있으므로 기존 로직을 보존하고 불필요한 재작성을 피한다.

- 지역 게시판(나눔/공동구매/교환) 구현 완료
- Kakao Map 렌더링 구현 완료
- QR 거래 인증 / 바코드 스캔 구현 완료
- OTP 휴대폰 인증 구현 완료 (비밀번호 재설정 전용)
- 영수증 OCR 인증 구현 완료
- 회원 기능 구현 완료 (ID/비밀번호 가입·로그인, OTP=비밀번호 재설정 전용, 프로필 수정·탈퇴, Bearer 토큰, FK 적용)
- 프로필 확장 완료 (`email`, `bio`, `interests`, `dietary` 컬럼 + Edit_Profile 연동)
- 찜 목록·1:1 채팅·동네 인증 백엔드 구현 완료 (회원 전용)
- 거래(transactions) API 구현 완료 (목록·생성·상태 전환, `appointment_at` 약속 시간 포함)
- 회원 화면 실데이터 연동 완료 (거래 내역·찜·채팅·프로필 수정·탈퇴)
- 단일 SQLite 통합 완료
- 거래 앵커(`transactions`)·공동구매 참여자(`groupbuy_participants`) 골격
- 내 냉장고(`fridge_items`)·그룹 채팅(`conversation_members`)·관리자(`notices`·`reports`) 구현 완료
- 관리자 계정 부트스트랩 `seed_admin.py`, 전 화면 상대경로 `API_BASE` 적용
- 신고(`reports` + `POST /api/reports` → 관리자 처리) 구현 완료
- GPS 위치 인증(`location_verify_sessions` + `/api/location-verify/*`) 구현 완료 — `Local_Verify_Demo.html`
- 공동구매 참여 원자적 UPDATE, Kakao 키 `.env` 전환(Map.html), `neighborfood_schema.sql`·`tokens.css` 동기화, `requirements.txt` 갱신 완료 (2026-07-09 커밋 전 점검)
- Kakao 키 하드코딩 전면 제거(전 화면), GPS 위치 인증 보안 강화(인증·소유권·이력 필터·QR 연동 실호출·진입점 연결), 수령 장소 지정(`Reservation.html` 실좌표 연동) 완료 (2026-08-03)

## Included (구현 대상 — 잔여)
- 정산 요청(`settlements` 테이블 + API + `Settlement.html` 연동)
- 상호 매너 평가(`manner_ratings` 테이블 + `trust_score` 반영)
- 공동구매 참여 취소 흐름

## Excluded (범위 외)
- 유통기한 임박 추천
- 레시피 추천
- 식재료 객체 인식
- 오프라인 모드

## Prohibited (금지)
- 식품 소분 판매
- 포장 훼손 거래 UI

---
# 6. Commands
* **Frontend:** Live Server(5500) 또는 `http://127.0.0.1:8000/frontend/<파일>.html`
  (카메라 사용 화면(QR/영수증)은 8000 포트로 열 것. 인증·게시는 같은 출처에서 진행)
* **Backend / AI:** `uvicorn main:app --reload`
* **더미 데이터:** `python seed_posts.py`
* **관리자 계정:** `python seed_admin.py` (신규 생성) / `python seed_admin.py <login_id>` (기존 계정 승격)
* **API 문서:** `http://127.0.0.1:8000/docs`
* **DB 초기화:** 서버 startup 시 `init_all_databases()`가 `neighborfood.db`를 자동 생성