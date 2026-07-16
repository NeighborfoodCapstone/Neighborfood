# NeighborFood FastAPI — 아키텍처 현황 및 확장 가이드

> 최종 수정: 2026-07-08
> 상태: **내 냉장고 · 그룹(공동구매) 채팅 · 관리자 기능 · 신고 구현 완료 + 배포 대응(상대경로 API_BASE)**
> 서버: 단일 FastAPI / DB: 단일 SQLite 파일(`data/neighborfood.db`)

---

## 0-A3. 최근 완료 작업 (2026-06-13) — 내 냉장고 · 그룹 채팅 · 관리자

| # | 작업 | 내용 |
|---|------|------|
| 1 | **내 냉장고** | `fridge_items` + `/api/fridge`(목록·요약·추가·수정·삭제). 유통기한 D-day 계산, 홈·마이페이지 '소비 임박' 요약 연동, `Fridge.html` 신설 |
| 2 | **그룹(공동구매) 채팅** | `conversations.kind`(direct/group) + `conversation_members`(멤버별 `last_read_id`). `/api/chats/group/*`(방 열기·메시지·멤버), 통합 수신함(`GET /api/chats`)이 1:1+그룹 반환. `Group_Chat.html` 신설. Group_Buy_Detail '참여 신청'이 실제 `/posts/{id}/join` 호출 후 그룹 채팅 입장 |
| 3 | **관리자 기능** | `get_current_admin` + `/api/admin/*`(대시보드·회원 정지/승격·공지 CRUD·신고 처리·채팅 모니터링). 관리자 6종 화면 메뉴 링크 정상화(공백→언더스코어), `Login.html`이 admin → `Admin_Dashboard.html`로 분기 |
| 4 | **신고** | `reports` + `POST /api/reports`(회원 제출) → 관리자 처리(`PATCH /api/admin/reports/{id}`) |
| 5 | **계정 부트스트랩** | `seed_admin.py` — 일반 가입으로 불가한 admin 계정을 1회성 생성/승격(전화번호 충돌 자동 회피, `python seed_admin.py [login_id]`) |
| 6 | **배포 대응·버그 수정** | 전 화면 `API_BASE`를 `window.location.origin`(상대경로)으로 통일(127/localhost/배포 호환 + 토큰 주입 정상화). Reservation '신청'→실제 채팅 생성, Chat_Detail 상품 카드 동적화, `tokens.css` 적용 |

> 후순위/예정: 정산(`settlements`), 상호 매너 평가(`manner_ratings`), 수령 장소 지정.

---

## 0-A2. 최근 완료 작업 (2026-06-11) — 회원 화면 실데이터 연동

| # | 작업 | 내용 |
|---|------|------|
| 1 | **거래 API** | `transactions` 라우터 신설 — `GET /api/transactions`(목록+통계), `POST`(생성, provider=글 작성자), `PATCH /{id}`(상태 전환·전이 규칙). `appointment_at` 컬럼 추가 |
| 2 | **users 확장** | `email`·`bio`·`interests`·`dietary` 컬럼 추가(멱등). 프로필 PATCH로 저장(이메일 형식 검증, 관심사 JSON) |
| 3 | **탈퇴** | 현재 비밀번호 확인 → 소프트삭제 + 개인정보 익명화(전화/닉네임 placeholder, 나머지 NULL). 거래 이력 보존 |
| 4 | **프런트 연동** | Transaction_History·Wishlist·Chat_List·Chat_Detail(4초 폴링)을 신규 API에 연결. 하드코딩 제거 |
| 5 | **프로필 화면** | Edit_Profile 저장(PATCH)·탈퇴 링크·이메일 입력·전화번호 인증 표시·관심사 칩. Withdraw 비밀번호 확인·취소→Home |
| 6 | **동네 인증** | Neighborhood_Setting '현재 위치로 인증' → `POST /api/users/neighborhood` 연동 |
| 7 | **진입/링크** | Map 검색창 뒤로가기, Home 등록탭→Create_Post, Product_Detail 하트(비회원 차단)·채팅하기, My_Page 메뉴 5개 링크·로그아웃, Help.html 연결 |

---

## 0-A. 최근 완료 작업 (2026-06-10) — 인증 정책 전환 + 회원 기능 확장

| # | 작업 | 내용 |
|---|------|------|
| 1 | **인증 전환** | 가입/로그인을 **ID·비밀번호**로 변경 (`POST /api/auth/register`, `POST /api/auth/login`). 가입 시 휴대폰 번호는 입력만 받고 OTP 검증 없음 |
| 2 | **OTP 용도 변경** | `/request-auth`(가입된 번호에만 발송) → `/reset-password`(코드 검증+비밀번호 변경+전 세션 폐기). **비밀번호 재설정 전용** |
| 3 | **비밀번호 저장** | 표준 라이브러리 PBKDF2-SHA256 `salt$hash` (외부 의존성 없음, `app/core/utils.py`) |
| 4 | **users 스키마** | `login_id`(UK)·`password_hash`·`neighborhood`·`neighborhood_verified_at` 컬럼 추가. 테스트 DB는 초기화 후 재생성(`data/neighborfood.db` 삭제), 구버전 파일 보호용 멱등 `ALTER TABLE` 포함 |
| 5 | **회원 기능 백엔드** | 찜 목록(`wishlists` + `/api/wishlist/*`), 1:1 채팅(`conversations`·`messages` + `/api/chats/*`, REST 폴링), 동네 인증(`POST /api/users/neighborhood`) |
| 6 | **프런트 진입 흐름** | `Splash.html` → (첫 방문) `Onboarding.html` → `Home.html`. `Login.html`/`Signup.html`/`Password_Reset.html` 신규. `shared/guard.js`(회원 전용 페이지 가드) 추가 |
| 7 | **접근 정책** | 비회원: 게시판·지도 열람만. 회원: 글 작성·거래·채팅·찜·내 활동·마이·동네 인증. 관리자 기능은 후순위 |
| 8 | **정리** | `main.py`의 `/frontend` 중복 마운트 제거, `wishlist`·`chat` 라우터 등록 |

> ⚠️ 기존 `Verify.html`(OTP 가입·로그인)은 더 이상 진입 경로가 아닙니다. `My_Page`/`Home`의 로그인 동선은 `Login.html`로 연결하세요.

---

## 0-B. 이전 완료 작업 (2026-06-08)

| # | 작업 | 결과 |
|---|------|------|
| 1 | **회원 기능 백엔드** — `GET/PATCH /api/users/me`, `POST /api/users/withdraw` | 프로필 조회·수정(닉네임 중복 409)·탈퇴(소프트삭제+세션 폐기) 완료 |
| 2 | **프런트 인증 연동** — `shared/auth.js`(localStorage 토큰 + fetch 자동 `Authorization` 주입), `Verify.html` 토큰 저장 + 신규 가입 시 닉네임 등록, `shared/profile.js` 헬퍼 | 인증→게시 흐름 정상 |
| 3 | **바코드 스캔** — `QR_Scan.html`이 html5-qrcode로 QR+1D 바코드 동시 인식, Open Food Facts 상품 조회 | QR/바코드 겸용 스캔 동작 |
| 4 | **정적 서빙 수정** — `main.py`에 `/shared` 마운트 추가 | 루트 서빙 페이지의 `shared/*` 404 해결 |
| 5 | **안정화 수정** — WAL+busy_timeout, posts 소프트삭제, 작성자 닉네임 조인, `transactions` CASCADE 제거 + `groupbuy_participants` 신설, OTP 재요청 쿨다운/응답 비노출, 만료 세션 청소 + `POST /logout` | 잠금/이력유실/보안 리스크 해소 |

---

## 1. 디렉토리 구조 (현행)

핵심 디렉토리: **`app`(서버) · `frontend`(화면+JS) · `sql`(스키마) · `data`(실제 DB)**

```
NEIGHBORFOOD/                            ← 프로젝트 루트 (Git 저장소)
│
├── app/                                 ▶ 서버 파일 (FastAPI 백엔드)
│   ├── config.py                          경로 상수, DB_PATH, SESSION_TTL_DAYS
│   ├── core/
│   │   ├── utils.py                       시간/해시/토큰 헬퍼
│   │   └── deps.py                        get_bearer_token / get_current_user / get_current_admin
│   ├── db/                                DB 접속 계층 (모두 neighborfood.db 공유)
│   │   ├── base.py                        make_conn()(WAL+busy_timeout), init_all_databases()
│   │   ├── auth_db.py                     users · sessions · auth_codes · posts
│   │   ├── transaction_db.py              transactions · groupbuy_participants
│   │   ├── member_db.py                   wishlists · conversations(+kind) · messages · conversation_members
│   │   ├── fridge_db.py                   fridge_items (내 냉장고)
│   │   ├── admin_db.py                    notices · reports
│   │   ├── qr_db.py                       qr_sessions
│   │   └── receipt_db.py                  receipts (+ OCR 유틸)
│   ├── models/                            Pydantic 모델
│   │   ├── auth.py  user.py  post.py  qr.py  receipt.py  member.py  fridge.py
│   └── routers/                           API 라우터
│       ├── auth.py  users.py  posts.py  qr.py  receipt.py
│       ├── wishlist.py  chat.py  transactions.py
│       ├── fridge.py  admin.py  reports.py
│
├── frontend/                            ▶ HTML 페이지 + JS 파일
│   ├── (사용자 화면)
│   │   Home · Index · Map · Search · Search_Results ·
│   │   Product_Detail · Group_Buy_Detail · Create_Post ·
│   │   Reservation · Location_Detail · Neighborhood_Setting ·
│   │   Wishlist · My_Page · My_Activity · Edit_Profile · Withdraw ·
│   │   Fridge · Group_Chat · Chat_List · Chat_Detail ·
│   │   Verify · Transaction_History · Settlement · Report ·
│   │   QR_Create · QR_Scan · Receipt_Verify ·
│   │   Splash · Onboarding · Login · Signup · Password_Reset · Help  (.html)
│   ├── (관리자 화면)
│   │   Admin_Dashboard · Admin_Users · Admin_Notices ·
│   │   Admin_Report_Detail · Admin_Chat_History · Admin_Staff_Invite  (.html)
│   └── shared/                            공통 자산 (JS · CSS)
│       ├── auth.js                        토큰 저장(localStorage) + fetch 자동 인증 주입
│       ├── guard.js                       회원 전용 페이지 접근 가드 (nfRequireMember())
│       ├── profile.js                     프로필 조회/수정/탈퇴 호출 헬퍼
│       └── tokens.css                     디자인 토큰(CSS 변수)
│
├── sql/                                 ▶ 현재 프로젝트 스키마
│   └── neighborfood_schema.sql            전체 테이블 DDL (단일 진실 소스)
│
├── data/                                ▶ 실제 데이터베이스
│   └── neighborfood.db                    단일 SQLite (startup 시 자동 생성, gitignore)
│
├── uploads/                             업로드 이미지 저장소 (gitignore)
├── venv/  .venv/                        파이썬 가상환경 (gitignore)
├── .vscode/  __pycache__/               에디터 설정 / 바이트코드 캐시 (gitignore)
│
├── main.py                              FastAPI 엔트리포인트 (미들웨어·정적 마운트·라우터 등록)
├── posts.json                           초기 게시글 시드 데이터(JSON)
├── seed_admin.py                        관리자 계정 부트스트랩(1회성)
├── seed_posts.py                        더미 게시글 시드(개발용)
├── Cpastone.md                          개발 컨텍스트/제약 문서
├── NeighborFood_Architecture_Plan.md    (이 문서) 아키텍처 현황·로드맵
├── neighborfood_ERD.md                  DB 구조 + 디렉토리
├── README.md                            프로젝트 개요·실행 가이드
├── requirements.txt                     파이썬 의존성
└── .env  .env.example  .gitignore       환경 변수 / 템플릿 / 제외 목록
```

### 모듈 역할 요약

| 파일/폴더 | 역할 | Git 커밋 |
|---|---|---|
| `main.py` | 앱 생성, 미들웨어, 정적 마운트(`/frontend`·`/shared`·`/uploads`), 라우터 등록 | ✅ |
| `app/config.py` | 경로·상수 중앙 관리 (`DB_PATH`, `SESSION_TTL_DAYS`) | ✅ |
| `app/core/` | 시간·해싱·토큰 유틸 + 인증/인가 의존성 | ✅ |
| `app/db/` | 단일 `neighborfood.db`에 도메인별 테이블 초기화 | ✅ |
| `app/models/` · `app/routers/` | Pydantic 모델 / FastAPI 라우터 | ✅ |
| `frontend/` · `frontend/shared/` | 정적 화면 / 공통 JS·CSS | ✅ |
| `sql/neighborfood_schema.sql` | DDL 단일 진실 소스 | ✅ |
| `seed_admin.py` | 관리자 계정 부트스트랩(1회성) | ✅ |
| `seed_posts.py` | 더미 게시글 시드(개발용) | ✅ |
| `data/neighborfood.db` · `uploads/` | SQLite 바이너리 / 업로드 | ❌ |

---

## 2. 데이터 레이어

단일 `data/neighborfood.db`에 모든 테이블이 있고, 모든 연결은 `make_conn(DB_PATH, foreign_keys=True)`로 생성되어 WAL 저널 + `busy_timeout`으로 동시 접근 잠금을 완화합니다.

```python
# app/db/base.py — 초기화 순서 (FK 부모 우선)
def init_all_databases() -> None:
    init_auth_db()          # ① users · sessions · auth_codes · posts
    init_transaction_db()   # ② transactions · groupbuy_participants
    init_qr_db()            # ③ qr_sessions
    init_receipt_db()       # ④ receipts
    init_member_db()        # ⑤ wishlists · conversations(+kind) · messages · conversation_members
    init_fridge_db()        # ⑥ fridge_items
    init_admin_db()         # ⑦ notices · reports
```

### 테이블 구성 (15개)

| 테이블 | 역할 | 키/FK |
|---|---|---|
| `users` | 회원 | PK `id`, UNIQUE `login_id`, UNIQUE `phone_number` |
| `sessions` | 로그인 세션(Bearer) | PK `token`, FK `user_id → users.id` (CASCADE) |
| `auth_codes` | OTP 단명 코드 | PK `phone_number` |
| `posts` | 게시글 통합 | PK `id`, FK `author_id → users.id` |
| `transactions` | 거래 앵커 (`appointment_at` 포함) | PK `id`, FK `post_id → posts.id`(이력 보존), `provider_id/receiver_id → users.id` |
| `groupbuy_participants` | 공동구매 참여자 | PK `(post_id, user_id)`, FK posts·users |
| `wishlists` | 찜 목록 | PK `(user_id, post_id)`, FK users(CASCADE)·posts |
| `conversations` | 채팅방(1:1·그룹) | PK `id`, `kind`(direct/group), FK post·host·guest |
| `conversation_members` | 그룹 채팅 멤버십 | PK `(conversation_id, user_id)`, `last_read_id` |
| `messages` | 채팅 메시지 | PK `id`, FK `conversation_id`(CASCADE)·`sender_id` |
| `fridge_items` | 내 냉장고 | PK `id`, FK `user_id → users.id`(CASCADE) |
| `notices` | 공지(관리자) | PK `id`, FK `author_id → users.id` |
| `reports` | 신고 | PK `id`, FK `reporter_id → users.id`, `target_type`/`target_id`(논리적) |
| `qr_sessions` | QR 인증 세션 | PK `id`, `subject_id`(논리적) |
| `receipts` | 영수증 OCR | PK `id`, `subject_id`(논리적) |

---

## 3. 인증/인가 흐름 (현행 — 2026-06-10 전환)

가입/로그인은 ID·비밀번호, OTP는 비밀번호 재설정 전용입니다. 토큰은 프런트가 `localStorage`에 보관해 같은 출처의 모든 페이지에서 공유합니다.

```
[진입]  Splash.html → (첫 방문) Onboarding.html → Home.html   ※ 로그아웃 상태로 진입 가능
[가입]  Signup.html  → POST /api/auth/register (id·pw·phone, OTP 없음)
                      → users INSERT + sessions 발급 → 토큰 저장 → 즉시 로그인 상태
[로그인] Login.html   → POST /api/auth/login (id·pw)
                      → PBKDF2 검증 → sessions 발급 → 토큰 저장(nfSetToken/localStorage)
                      → role=admin 이면 Admin_Dashboard.html 로 분기
[비밀번호 재설정] Password_Reset.html
        ① POST /request-auth   → 가입된 번호에만 OTP 발송(콘솔, 30초 쿨다운, 존재 여부 비노출)
        ② POST /reset-password → 코드 검증 → password_hash 갱신 → 해당 회원 전 세션 폐기
[이후 모든 요청] shared/auth.js 가 fetch 를 감싸 Authorization: Bearer <token> 자동 주입
                → 서버 get_current_user 의존성으로 인가
[회원 전용 페이지] shared/guard.js 의 nfRequireMember() → 미로그인 시 Login.html?next=... 리다이렉트
[로그아웃]    POST /logout → 해당 토큰 행 삭제 + 토큰 제거
```

**접근 정책:** 비회원은 게시판(`GET /posts*`)·지도만 이용. 글 작성·거래(QR/영수증)·채팅·찜·내 활동·마이페이지·동네 인증은 회원 전용.

- 게시글 작성/삭제/참여는 인증 필요. `author_id`는 클라이언트 값이 아니라 **세션 회원 id**로 결정(위변조 방지), 삭제는 작성자/관리자만 가능(소프트삭제).
- **출처(origin) 주의:** `localStorage`는 포트별로 분리됩니다. 인증과 게시는 반드시 같은 출처(권장: `http://127.0.0.1:8000/frontend/...`)에서 진행해야 토큰이 공유됩니다.

---

## 4. API 엔드포인트 (현행)

### 인증 (Auth)
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| POST | `/api/auth/register` | - | 가입(id·pw·phone, OTP 없음) → 세션 토큰 발급 |
| POST | `/api/auth/login` | - | ID·비밀번호 로그인 → 세션 토큰 발급 |
| POST | `/logout` | ✅ | 현재 세션 토큰 폐기 |
| POST | `/request-auth` | - | [비밀번호 재설정] 가입된 번호에만 OTP 발송(코드 비노출, 30초 쿨다운) |
| POST | `/reset-password` | - | [비밀번호 재설정] 코드 검증 + 비밀번호 변경 + 전 세션 폐기 |

### 회원 (Users) — `/api/users/*`
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| GET | `/api/users/me` | ✅ | 내 프로필 조회(전화번호 마스킹, 동네 정보·이메일·소개·관심·식이 포함) |
| PATCH | `/api/users/me` | ✅ | 닉네임/이미지/이메일/소개/관심/식이 수정(닉네임 중복 409) |
| POST | `/api/users/withdraw` | ✅ | 탈퇴(소프트삭제) + 전 세션 폐기 |
| POST | `/api/users/neighborhood` | ✅ | 동네(위치) 인증 — 동네 이름+GPS 좌표 기록 |

### 찜 목록 (Wishlist) — `/api/wishlist/*` (회원 전용)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/wishlist` | 내 찜 목록(삭제 글 제외, 작성자 닉네임 조인) |
| PUT | `/api/wishlist/{post_id}` | 찜 추가(멱등) |
| DELETE | `/api/wishlist/{post_id}` | 찜 해제(멱등) |

### 채팅 (Chats) — `/api/chats/*` (회원 전용, REST 폴링)
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/chats` | 게시글 작성자와 1:1 방 생성(이미 있으면 기존 방 반환) |
| GET | `/api/chats` | 내 채팅방 목록(마지막 메시지·안 읽은 수 포함, 1:1+그룹 통합) |
| GET | `/api/chats/{id}/messages?after_id=` | 메시지 조회(증분 폴링) + 상대 메시지 읽음 처리 |
| POST | `/api/chats/{id}/messages` | 메시지 전송 |
| POST | `/api/chats/group/{post_id}` | 공동구매 그룹 채팅방 열기/합류(작성자·참여자만) |
| GET | `/api/chats/group/{id}/messages?after_id=` | 그룹 메시지 조회(발신자 닉네임 포함) + 읽음 갱신 |
| POST | `/api/chats/group/{id}/messages` | 그룹 메시지 전송 |
| GET | `/api/chats/group/{id}/members` | 그룹 참여자 목록 |

### 게시글 (Posts)
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| POST | `/upload-images` | - | 이미지 업로드 |
| POST | `/posts` | ✅ | 게시글 등록(author_id=세션 회원) |
| GET | `/posts` · `/posts/{id}` | - | 목록·단건(작성자 닉네임 조인, deleted 제외) |
| DELETE | `/posts/{id}` | ✅ | 소프트삭제(작성자/관리자) |
| POST | `/posts/{id}/join` | ✅ | 공동구매 참여(참여자 기록, 중복 409) |

### 내 냉장고 (Fridge) — `/api/fridge/*` (회원 전용)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/fridge` | 내 식재료 목록(유통기한 임박순) |
| GET | `/api/fridge/summary` | 전체/임박(D-3)/만료 개수 요약 |
| POST | `/api/fridge` | 식재료 추가(유통기한 형식 검증) |
| PATCH | `/api/fridge/{id}` | 식재료 수정(본인만, 부분 수정) |
| DELETE | `/api/fridge/{id}` | 식재료 삭제(멱등) |

### 거래 (Transactions) — `/api/transactions/*` (회원 전용)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/transactions` | 내 거래 목록 + 통계(진행/완료) |
| POST | `/api/transactions` | 거래 생성(provider=글 작성자, `appointment_at` 선택) |
| PATCH | `/api/transactions/{id}` | 상태 전환(전이 규칙 검증) |

### 신고 (Reports) — `/api/reports` (회원 전용)
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/reports` | 게시글/회원 신고 제출(`target_type`/`target_id`/`reason`) |

### 관리자 (Admin) — `/api/admin/*` (`get_current_admin` 가드)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/dashboard` | 회원·게시글·거래·신고대기 집계 |
| GET / PATCH | `/api/admin/users` · `/users/{id}` | 회원 목록·검색 / 정지·승격(본인 변경 차단) |
| GET / POST / DELETE | `/api/admin/notices` · `/notices/{id}` | 공지 목록·작성·삭제 |
| GET / PATCH | `/api/admin/reports` · `/reports/{id}` | 신고 목록 / 처리(resolved·dismissed) |
| GET | `/api/admin/chats` · `/chats/{id}/messages` | 채팅 모니터링(신고 처리용) |

### QR / 바코드 — `/api/qr/*`
`request`, `verify`, `verify/{token}`, `history`. (스캔 화면 `QR_Scan.html`은 QR·1D 바코드 동시 인식)

### 영수증 — `/api/receipt/*`
`scan`, `verify`, `issue`, `confirm`, `token/{token}`, `{id}`, `history`.

### 정적 서빙 (main.py)
`/frontend`(전체 페이지), `/shared`(공통 자산), `/uploads`. 카메라 사용 화면은 `/QR_Scan.html` 등 루트 라우트로도 서빙.

---

## 5. 향후 작업 로드맵

거래 앵커(`transactions`)·참여자(`groupbuy_participants`)가 준비되어, 남은 기능은 대부분 테이블 추가 + 라우터 연결로 단순화됩니다.

| 상태 | 작업 | 신규 테이블(예정) | 비고 |
|---|---|---|---|
| ✅ 완료 | ID/비밀번호 인증 전환, OTP=재설정 전용, 찜·채팅·동네 인증 백엔드, Splash/Onboarding/Login/Signup/Password_Reset 화면 | `wishlists`·`conversations`·`messages` | 2026-06-10 |
| ✅ 완료 | Home 접근 분기 — 마이/내 활동/등록 탭·FAB(+)에 로그인 분기, 회원 전용 화면에 `guard.js`+`nfRequireMember()` 부착 | - | 2026-06-10 |
| ✅ 완료 | 회원 기능(프로필·탈퇴), 프런트 인증 연동, 바코드 스캔 | - | 2026-06-08 |
| ✅ 완료 | 거래 API (`transactions`), 프로필 확장(`email`·`bio`·`interests`·`dietary`), 회원 화면 실데이터 연동 | - | 2026-06-11 |
| ✅ 완료 | 내 냉장고 (`fridge_items`·`Fridge.html`) | `fridge_items` | 2026-06-13 |
| ✅ 완료 | 그룹(공동구매) 채팅 | `conversation_members`(+`kind`) | 2026-06-13 |
| ✅ 완료 | 관리자 기능 + `seed_admin.py` | `notices`·`reports` | 2026-06-13 |
| ✅ 완료 | 신고 (`POST /api/reports` → 관리자 처리) | - | 2026-06-13 |
| ✅ 완료 | 배포 대응: 전 화면 상대경로 `API_BASE`, `tokens.css` 적용 | - | 2026-06-13 |
| ⬜ 잔여 | 정산 요청 | `settlements` | FK `transaction_id` (+참여자 분담) |
| ⬜ 잔여 | 상호 매너 평가 | `manner_ratings` | `trust_score` 원자적 반영 |
| ⬜ 잔여 | 수령 장소 지정 | - | `posts.lat/lng` 프론트 활용 |
| ⬜ 잔여 | (정리) Kakao 지도 JS 키 설정 | - | 비차단 항목 |
