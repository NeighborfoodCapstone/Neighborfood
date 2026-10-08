# NeighborFood FastAPI — 아키텍처 현황 및 개발 이력

> 최종 수정: 2026-10-08 (2026-10-08 구현 완료 — 그룹 채팅 거래 액션 바(B안: 약속·정산·GPS·QR 링크)·로그인 상태 비밀번호 변경 API(`PATCH /api/users/me/password`)·공개 공지 API(`GET /api/notices`)·게시글 수정 API 확장(사진·유형·인원·가격)·정산 흐름 자동화 테스트(`tests/test_settlement_flow.py` 등 pytest 12개 신규)·QR 발급 화면 토큰 표시·복사 줄 추가(`qr.tsx`). 같은 날 수동 UI 검증(액션 바·비밀번호 변경·공지·게시글 수정) 통과. 남은 작업: PWA·PortOne 서버 검증·실환경(기기) 검증·서버 운영 마무리. 이전 수정: 2026-10-08 (2026-10-08 잔여 작업 방침 확정 — 시연·발표 전 처리(그룹 채팅 액션 바·PortOne 서버 검증·실환경 검증·서버 운영 마무리)와 구현/제외 결정 항목(비밀번호 변경·공개 공지·게시글 수정 API·PWA)은 모두 작업 예정, 정적 HTML 폐기는 구현 100% 완료 후 영향 점검 뒤 진행, 선택 사항은 별도 시점에 처리). 이전 수정: 2026-10-07 (GitHub `ec1da57`(main) 기준 문서-저장소 정합성 점검 — 저장소에 없는 문서 참조 표기, 화면 수(39+4) 표기, 팀원 `PORTONE_TEST_SETUP.md` 시점 차이 주석, 낡은 문구 정정·`frontend/shared/profile.js` 부재 정정). 이전 수정: 2026-10-06 (운영 서버 HTTPS 배포 완료(Nginx·Let's Encrypt·`dist/` 서빙)와 팀원 PortOne V2 테스트 결제 연동 반영 — 신규 API 4종·테이블 2개 추가, §9 외부 결제 정책 갱신. 상세는 §2·§3·§4·§5·§6·§7·§8·§9 참고. 이전 수정 2026-09-30 (배포 서버 백엔드 배치·도메인 연결 반영, 코드 변경 없음 — §7·§8 참고. 이전 수정 2026-09-21: React 전체 화면 이전(`frontend-react/`, 화면 39개)·공통 디자인·로딩·자동완성·게시글 상세 개선 반영, 공개 공지 API 미구현·게시글 수정 범위 정정. 상세는 §2·§3·§5·§6·§7·§8·§9·§10·§11 참고)
> 2026-09-08 수정: 기술 스택 사용 목적 서술 추가, 디렉토리 구조를 README.md와 정합화 / 존재하지 않는 `receipt_items` 테이블 언급 2곳 정정 — 영수증 품목은 `receipts.items`/`selected_items` JSON 컬럼으로만 저장
> 2026-09-12 업데이트: 관리자 기능 실데이터 연동 완료(가드 공용화·회원 관리·신고 상세·운영진 관리·대시보드 통계), 미납 정산 참여 차단 리팩터링, 주최자 귀책/먹튀 trust_score 자동 페널티, `seed_admin.py` 복원, CORS `.env` 동적 분기 준비. 상세는 §7 개발 이력 참고.
> 2026-09-14 업데이트: `frontend-react/` 워크스페이스 신규 추가 — 홈 화면(`HomePage.tsx`)만 React로 재구현한 부분 마이그레이션. 기존 정적 HTML 프런트엔드(`frontend/`)와 하이브리드로 병행 운영하며, 신규 백엔드 API는 없음(기존 `GET /posts` 재사용). 상세는 §7 개발 이력 참고.
> 2026-09-19 업데이트: 문서-소스 정합성 점검 — `reset_db.py` 존재 확인, `users` 동네 인증 저장 항목 정정(좌표 미저장), 비밀번호 변경 API 미구현 표기, §5 API 표 누락 4건(admin stats·정산 약속·내 신고·거래별 내 평가) 추가. 코드 변경 없음.
> 2026-09-20~21 업데이트: `frontend-react/`가 기존 HTML 39개 화면 식별자를 모두 React(TypeScript)로 이전(§6·§7 참고, 구현 완료 — 실제 브라우저·기기 검증은 진행 중). 기존 정적 HTML은 최종 점검 전까지 병행 보존. 신규 백엔드 API·DB 변경 없음. 문서 정정: 공개 공지 API(`GET /api/notices`)는 코드에 없음, `PATCH /posts/{id}`는 인원·가격을 반영하지 않음.
> 2026-09-30 업데이트: 배포 환경 구성 착수 — Oracle Cloud Micro 서버에 저장소 클론·가상환경·`.env`·systemd 서비스(`127.0.0.1:8000`)로 백엔드를 배치하고 도메인 `neighborfood.duckdns.org`를 연결. Nginx 리버스 프록시·HTTPS·`dist/` 서빙은 미완료. 신규 API·DB 변경 없음. 상세는 §7·§8 참고.
> 2026-10-03~10-06 업데이트: ① 작성자 매너 평가 표시·`frontend-react/README.md` 교체·`main.py` `dist/` 서빙 코드(10/3). ② 운영 서버 완성(10/3): Nginx 리버스 프록시 → Let's Encrypt HTTPS(만료 2027-01-01, 자동 갱신) → 로컬 빌드 `dist/` 업로드 → 카카오 지도 확인. ③ 팀원 PortOne V2 **테스트 결제**·QR 스캔 UI 통합 푸시(10/5, `ec1da57`): `app/routers/portone.py`·`portone_*` 테이블 2개·`/api/payments/portone/*` 4종·`portone.tsx`·`Scanner.tsx`. 정산 납부 상태는 바꾸지 않음. ④ 서버 운영 가이드·배포 방식 비교 문서 작성(10/5~6). 상세는 §7 참고.
> 상태: **핵심 거래 흐름(채팅→약속→GPS 100m 실검증→QR→납부→정산완료→매너평가) 완성 + 관리자·UX 갭 해소 + 영수증 파서 v2.1 마트형 개선 + React 전체 화면 이전(구현 완료, 실제 환경 검증 진행 중) + 운영 서버 HTTPS 배포(2026-10-03) + PortOne 테스트 결제 연동(2026-10-05 푸시, 서버 반영 확인 필요)**
> 배포: Oracle Cloud Micro(Ubuntu 24.04) + Nginx + Let's Encrypt(`https://neighborfood.duckdns.org`), FastAPI는 systemd로 `127.0.0.1:8000`에서 실행하며 로컬에서 빌드한 `frontend-react/dist/`를 서빙
> 서버: 단일 FastAPI / DB: 단일 SQLite(`data/neighborfood.db`) / 프런트엔드: React·Vite(`frontend-react/`, 화면 39개 이전) + 정적 HTML(`frontend/`, 최종 점검 전까지 병행 보존)

---

## 1. 프로젝트 개요

NeighborFood는 이웃 간 식재료 나눔·교환·공동구매를 중개하는 로컬 커뮤니티 플랫폼입니다.
실제 자금 이체 없이 납부 상태만 추적하고, GPS·QR 이중 인증으로 거래 신뢰를 확보합니다. 정산 상세에서는 PortOne(토스페이먼츠) **테스트 채널** 결제를 체험할 수 있으나 실결제가 아니며 납부 상태·정산 완료·판매자 지급에는 영향을 주지 않습니다(§9).

**핵심 거래 흐름:**
```
게시글 등록 → 채팅(약속 확정) → GPS 100m 실검증 → QR 대면 인증
→ 납부 표시 → 정산 완료 → 매너 평가(trust_score 반영)
```

---

## 2. 기술 스택

| 구분 | 기술 | 사용 목적 |
|---|---|---|
| 백엔드 | FastAPI (Python), Uvicorn | 비동기 I/O 기반으로 REST API를 빠르게 구축하고, Swagger(`/docs`) 문서를 자동 생성하기 위해 사용 |
| DB | SQLite 3 단일 파일 (`data/neighborfood.db`) | 별도 DB 서버 운영 부담 없이 단일 파일로 배포·백업·로컬 개발을 단순화하기 위해 사용 |
| 인증 | Bearer 세션 토큰 (`sessions` 테이블), PBKDF2-SHA256 비밀번호 해시 (표준 라이브러리) | 외부 인증 라이브러리 의존 없이 표준 라이브러리만으로 안전한 비밀번호 저장과 세션 기반 인증을 구현하기 위해 사용 |
| 프론트엔드 | Vanilla HTML/JS, Tailwind CSS CDN, Material Symbols | 별도 빌드 도구 없이 정적 파일만으로 화면을 빠르게 구성하고, 39개 화면에 일관된 디자인 토큰을 적용하기 위해 사용 |
| 프론트엔드(React, 2026-09-14 신규 → 2026-09-20~21 전체 이전) | `frontend-react/` — Vite 8 + React 19 + TypeScript, Oxlint, Node.js 20+, `qrcode`·`jsqr` | 기존 정적 HTML 39개 화면을 React로 이전해 컴포넌트 기반 구조·공통 디자인·공통 로딩·자동완성을 적용하고 향후 PWA 전환에 대비(PWA 기능 자체는 미구현). 의존성 설치는 `npm ci`(lockfile 기준 재현성 보장). 개발/preview 서버가 API 요청을 FastAPI로 프록시하며 신규 백엔드 API 없음. 기존 정적 HTML은 병행 보존 |
| 지도 | Kakao Maps SDK (`.env` 동적 로드, 소스 코드 키 하드코딩 금지) | 국내 서비스에 적합한 지도·좌표 데이터를 제공하고, API 키를 `.env`로 동적 로드해 소스코드 유출을 막기 위해 사용 |
| QR/바코드 | html5-qrcode (QR·1D 동시 인식) | 브라우저 카메라로 QR·1D 바코드를 동시에 인식해 대면 거래 인증을 구현하기 위해 사용. 2026-09 기준 `frontend/vendor/html5-qrcode.min.js`로 로컬 사본을 두어 CDN 장애 시에도 스캔 기능이 동작하도록 함 |
| 영수증 OCR | CLOVA OCR 연동 + Tesseract fallback (parser v2.1: 마트형·카페형 구조 동시 지원) | 1차로 CLOVA OCR의 인식 정확도를 활용하고, 키가 없거나 호출이 실패해도 Tesseract로 대체해 영수증 인증 기능이 항상 동작하도록 하기 위해 사용 |
| 결제(테스트, 2026-10-05 신규) | PortOne V2 (`@portone/browser-sdk/v2`) + 토스페이먼츠 **테스트 채널**, 서버 `requests`로 결제 조회 | 실결제 없이 결제 흐름(주문 생성 → 결제창 → 서버 검증)을 시연하기 위해 사용. 금액·결제 ID·통화·채널 TEST·PAID를 서버가 PortOne REST API로 재검증하며, `.env`의 `PORTONE_*`가 없으면 503. API 시크릿은 서버 `.env`에만 저장 |
| 배포(2026-10-03) | Oracle Cloud `VM.Standard.E2.1.Micro`(Ubuntu 24.04, 1GB+스왑 1GB), Nginx(`client_max_body_size 20M`), certbot(Let's Encrypt), DuckDNS, systemd | 무료 티어 서버 1대에서 HTTPS(카메라 QR·GPS 필수 조건)를 제공. 앱은 `127.0.0.1:8000`에만 바인딩하고 Nginx만 외부 노출. 프런트는 서버(1GB)에서 빌드하지 않고 PC에서 빌드한 `dist/`를 scp로 업로드 |

---

## 3. 디렉토리 구조

```
project_root/
├── main.py                      FastAPI 엔트리포인트 (미들웨어·마운트·라우터 등록)
├── seed_admin.py                관리자 계정 생성/승격 (2026-09-12 복원)
├── reset_db.py                  DB 초기화 — 전체 데이터 삭제 + Admin 재생성
├── app/
│   ├── config.py                DB_PATH, UPLOAD_DIR, SESSION_TTL_DAYS=30, RECEIPT_TRUST_DELTA=0.3 등
│   ├── core/
│   │   ├── deps.py              get_current_user / get_current_admin / get_bearer_token
│   │   └── utils.py             now_utc, to_iso, hash_password, verify_password, parse_token
│   ├── db/
│   │   ├── base.py              make_conn() — sqlite3 Row factory + WAL 설정
│   │   ├── auth_db.py           users · sessions · auth_codes · posts DDL
│   │   ├── member_db.py         wishlists · conversations · messages(is_system) · conversation_members DDL
│   │   ├── transaction_db.py    transactions · groupbuy_participants · manner_ratings
│   │   │                        settlements · settlement_shares DDL
│   │   ├── settlement_db.py     정산 CRUD + GPS/QR 검증 + transactions 연동 함수
│   │   ├── fridge_db.py         fridge_items DDL + CRUD
│   │   ├── admin_db.py          notices · reports DDL + CRUD
│   │   ├── qr_db.py             qr_sessions DDL + CRUD
│   │   ├── receipt_db.py        receipts DDL(items/selected_items는 JSON 컬럼) + OCR (CLOVA/Tesseract, parser v2.1)
│   │   └── location_verify_db.py location_verify_sessions DDL, DEFAULT_RADIUS_M=100
│   ├── models/
│   │   ├── auth.py · user.py · post.py · member.py · fridge.py
│   │   └── qr.py · receipt.py
│   └── routers/
│       ├── auth.py              인증 (register, login, logout, OTP, reset)
│       ├── users.py             회원 프로필·탈퇴·동네 인증·비밀번호 변경
│       ├── posts.py             게시글 CRUD·참여·취소·약속·my-status·자동 만료
│       ├── chat.py              1:1 채팅 + 그룹 채팅 (is_system 지원)
│       ├── wishlist.py          찜 목록
│       ├── transactions.py      거래 생성·상태 전환
│       ├── fridge.py            내 냉장고
│       ├── settlements.py       공동구매 정산 (GPS→QR 2단계, 노쇼 신고/취소 포함)
│       ├── ratings.py           매너 평가 (trust_score 연동)
│       ├── reports.py           신고 제출·취소
│       ├── admin.py             관리자 전용 API
│       ├── location_verify.py   GPS 위치 인증 (Haversine 100m 검증)
│       ├── qr.py                QR 거래 인증
│       ├── receipt.py           영수증 OCR 인증
│       └── portone.py           PortOne V2 테스트 결제 (`/api/payments/portone/*`, `portone_*` 테이블 `init_db()`) [신규 2026-10-05]
│
├── frontend/                    정적 HTML 프런트엔드
│   ├── shared/
│   │   ├── auth.js              토큰 저장·fetch 자동 인증 주입·logout·401 처리
│   │   ├── guard.js             회원 전용 페이지 접근 가드 (nfRequireMember)
│   │   ├── adminGuard.js        관리자 전용 페이지 접근 가드 (nfRequireAdmin) [신규 2026-09-12]
│   │   ├── (profile.js)         저장소에 없음(2026-10-07 확인) — 프로필 호출은 `Edit_Profile.html` 등 각 화면의 인라인 `fetch`로 처리
│   │   └── tokens.css           디자인 토큰 (CSS 변수)
│   ├── vendor/
│   │   └── html5-qrcode.min.js  QR·바코드 스캔 라이브러리 로컬 사본 [신규] — CDN 장애 대비 1차 로드 경로
│   └── (HTML 파일 목록은 §6 참조)
│
├── frontend-react/              React(Vite) 프런트엔드 [2026-09-14 신규 → 2026-09-20~21 전체 이전] — 화면 39개 이전(구현), `frontend/`와 병행 보존
│   ├── docs/
│   │   ├── DESIGN_CONTEXT.md     React 공통 디자인·로딩·자동완성·게시글 상세 기준
│   │   └── MIGRATION_REPORT.md   화면 39개 이전 매핑·검증 범위·미검증 범위
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── assets/              hero.png · react.svg · vite.svg
│   │   ├── neighborfood/        승인된 메인(홈) 화면·공통 레이아웃
│   │   │   ├── api.ts            백엔드 주소(VITE_API_BASE_URL, 미설정 시 상대경로+Vite 프록시) · getPosts() · legacy()(#/화면명 해시 경로)
│   │   │   ├── AppLayout.tsx     헤더 + 하단 네비게이션 공통 레이아웃 (홈/지도/등록/내 활동/마이)
│   │   │   ├── HomePage.tsx      홈 피드 — 카테고리 필터·검색·게시글 카드 그리드, GET /posts 재사용
│   │   │   ├── home.css          HomePage 전용 스타일
│   │   │   └── Icon.tsx          인라인 SVG 아이콘 컴포넌트
│   │   ├── migration/           나머지 화면 React 모듈 (2026-09-20~21)
│   │   │   ├── routes.tsx        화면 목록·라우팅·접근 제어(회원/관리자)·도움말·진입 화면
│   │   │   ├── core.tsx          공통 API 요청·인증 토큰·오류·상태 처리·공통 UI
│   │   │   ├── design.css        공통 디자인 토큰·폼·버튼·리스트·대화상자
│   │   │   ├── loading.tsx       화면 전환·최초 조회 공통 로딩
│   │   │   ├── autocomplete.tsx  검색·회원·주소 공통 자동완성
│   │   │   ├── PostGallery.tsx   게시글 상세 사진 갤러리
│   │   │   ├── auth.tsx · posts.tsx · fridge.tsx · trades.tsx   인증·프로필 / 게시글·검색·찜·등록·신고 / 냉장고 / 채팅·내 활동·정산
│   │   │   ├── location.tsx · qr.tsx · receipt.tsx · admin.tsx  지도·GPS / QR / 영수증 / 관리자
│   │   │   └── portone.tsx · Scanner.tsx · scanner.css · interface.css  PortOne 테스트 결제 화면(Payment_*) / QR·영수증 공용 카메라 스캐너 / 스캐너·인터페이스 스타일 [신규 2026-10-05]
│   │   ├── App.css · App.tsx(해시 라우팅 + AppLayout + 접근 가드, 홈은 HomePage) · index.css · main.tsx(StrictMode 진입점)
│   ├── index.html               Vite 진입 HTML (#root, /src/main.tsx 로드)
│   ├── package.json / package-lock.json   react·react-dom 19.2, qrcode, jsqr, devDeps: vite 8·typescript·@vitejs/plugin-react·oxlint
│   ├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
│   ├── vite.config.ts           @vitejs/plugin-react + 개발/preview API 프록시(NEIGHBORFOOD_BACKEND, 기본 http://127.0.0.1:8000)
│   ├── .oxlintrc.json           Oxlint 설정 (ESLint 대체 린터, react/typescript/oxc 플러그인)
│   ├── README.md                프로젝트 설명·실행·폴더 구조·배포 절차 (2026-10-03 교체 완료)
│   └── dist/                    `npm run build` 결과 — Git 미포함, 로컬 빌드 후 서버로 업로드(FastAPI가 `/`에서 서빙)
│
├── sql/neighborfood_schema.sql  전체 테이블 DDL (단일 진실 소스)
├── tests/
│   ├── test_receipt_parser_v212.py  영수증 파서 회귀·유닛 테스트 [신규] — pytest 없이 단독 실행 가능
│   ├── conftest.py                  pytest 공용 픽스처 — 임시 SQLite DB로 전체 앱(TestClient) 구동 [신규 2026-10-08]
│   ├── test_account_notice_post.py  비밀번호 변경·공개 공지·게시글 수정 확장 API 테스트 [신규 2026-10-08]
│   ├── test_settlement_flow.py      정산 흐름 자동화 테스트(약속→GPS 100m→QR→납부→완료→매너 평가, 노쇼·취소·미납 참여 차단) [신규 2026-10-08]
│   └── test_portone.py      PortOne 테스트 결제 검증(금액·권한·게이트·반복 요청·취소·오류, 외부 API는 mock) [신규 2026-10-05]
├── docs/PORTONE_TEST_SETUP.md   PortOne 테스트 연동 범위·설정·제한 (팀원 작성, 2026-09-28 — ⚠️ 2026-09-28 기준 작성본이라 `quick-prepare`·`Payment_Quick`/`Payment_Preview`(2026-10-05 추가)를 반영하지 않고 API를 3종으로 기술함 — 현행 API는 4종(팀원 문서는 수정하지 않음))
├── portone.env.example          `PORTONE_*` 4개 환경변수 템플릿 (값은 서버 `.env`에만)
├── data/neighborfood.db         실제 SQLite DB
├── uploads/                     이미지 업로드 저장소
├── .env / .env.example          환경변수 (KAKAO_JS_KEY, CLOVA_OCR_* 등) — VITE_API_BASE_URL은 선택 항목(미설정 시 상대경로+Vite 프록시, §8 참고)
├── README.md · Capstone.md · neighborfood_ERD.md · Settlement_Implementation_Plan.md · 본 문서  프로젝트 문서 (React 관련 문서는 frontend-react/docs/ 참고)
├── Neighborfood_React_실행_안내.md   백엔드 + React 로컬 실행 안내서
└── frontend-react/.env.local    React 전용 환경변수 (VITE_API_BASE_URL — 공개 API 주소를 직접 쓸 때만, Vite의 gitignore 기본 항목, 수동 생성)
```

> ⚠️ **문서-저장소 정합성 안내 (2026-09-08 확인, README.md와 동일)**
> [2026-09-19 정정] 아래 7개 중 `seed_admin.py`(09-12 복원)와 `reset_db.py`는 저장소에 **존재**합니다. 나머지 5개(`seed_posts.py`, `Seed_Account.py`, `Seed_capstone_settlement.py`, `Seed_settlement_verify.py`, `nf_functional_test.py`)만 없습니다.
> 이전 버전에는 `seed_posts.py`, `seed_admin.py`, `Seed_Account.py`, `Seed_capstone_settlement.py`, `Seed_settlement_verify.py`, `nf_functional_test.py`, `reset_db.py` 7개 루트 스크립트가 있었으나, 저장소 최신 구조 확인 결과 더 이상 존재하지 않아 트리에서 제거함(각 스크립트의 과거 역할은 README.md "폴더 구조" 절의 표 참고). 자동화 테스트는 현재 `tests/test_receipt_parser_v212.py`(영수증 파서 전용)와 `tests/test_portone.py`(PortOne 테스트 결제, 2026-10-05 추가) 두 개가 존재하며, 정산 등 나머지 기능의 자동화 테스트는 §8(`Settlement_Implementation_Plan.md`) 기준 미구현 상태로 수동 테스트 병행 중.
> **2026-09-12 갱신**: 위 7개 중 `seed_admin.py`는 관리자 계정 부트스트랩/승격 스크립트로 복원되어 정상 동작합니다 (§10 참고). 나머지 6개는 여전히 저장소에 존재하지 않습니다.
> **2026-09-14 갱신 [당시 기준 — 아래 2026-09-21 갱신 참고]**: `frontend-react/`(Vite + React 19 + TypeScript) 워크스페이스가 신규 추가되었습니다. 현재는 홈 화면(`HomePage.tsx`)만 구현되어 있고, 나머지 화면은 `src/neighborfood/api.ts`의 `legacy()` 헬퍼를 통해 기존 정적 HTML(`frontend/*.html`)로 하드 네비게이션합니다. 신규 백엔드 API는 없으며 기존 `GET /posts` 목록 API를 그대로 재사용합니다. `.env.example`에 `VITE_API_BASE_URL` 항목이 아직 없고 `frontend-react/README.md`도 Vite 기본 템플릿 그대로입니다 — §8 잔여 작업 목록 참고.
> **2026-09-21 갱신**: `frontend-react/`는 위 트리와 같이 기존 HTML 39개 화면 식별자를 모두 React로 이전한 상태입니다(§6 참고). 신규 백엔드 API는 없으며, 기존 정적 HTML은 최종 점검이 끝나기 전까지 유지합니다. `frontend-react/README.md`는 이 시점에는 Vite 기본 템플릿이었으나 2026-10-03 프로젝트 설명으로 교체되었습니다. **※ 2026-10-07 보충 — 화면 수: 기존 HTML 이전분 39개 + PortOne 결제 화면 4개(`Payment_Checkout`·`Payment_Result`·`Payment_Quick`·`Payment_Preview`, 2026-10-05 신규) = `routes.tsx` `screens` 기준 총 43개.**

---

## 4. DB 테이블 구성

| 테이블 | 설명 | 위치 |
|---|---|---|
| `users` | 회원 (login_id·pw·trust_score·role·status·neighborhood·neighborhood_verified_at — 동네 좌표는 저장하지 않음) | auth_db |
| `sessions` | Bearer 세션 토큰 (TTL 30일) | auth_db |
| `auth_codes` | OTP 인증코드 (비밀번호 재설정 전용) | auth_db |
| `posts` | 게시글 통합 (share·exchange·groupbuy, appointment 좌표 포함) | auth_db |
| `wishlists` | 찜 목록 | member_db |
| `conversations` | 채팅방 (kind: direct/group) | member_db |
| `messages` | 채팅 메시지 (`is_system` 컬럼 포함 — 시스템 알림용) | member_db |
| `conversation_members` | 그룹 채팅 멤버십 + 읽음 포인터 | member_db |
| `transactions` | 거래 이력 (pending→confirmed→completed) | transaction_db |
| `groupbuy_participants` | 공동구매 참여자 기록 | transaction_db |
| `manner_ratings` | 매너 평가 (score, comment, trust_score 반영) | transaction_db |
| `settlements` | 공동구매 정산 헤더 | transaction_db |
| `settlement_shares` | 정산 참여자별 분담 (gps_verified·quality_agreed·status) | transaction_db |
| `fridge_items` | 내 냉장고 식재료 | fridge_db |
| `notices` | 관리자 공지사항 | admin_db |
| `reports` | 신고 (target_type: post/user) | admin_db |
| `qr_sessions` | QR 거래 인증 세션 | qr_db |
| `receipts` | 영수증 OCR 인증 (품목은 `items`/`selected_items` JSON 컬럼으로 저장, 별도 테이블 없음) | receipt_db |
| `location_verify_sessions` | GPS 위치 인증 세션 | location_verify_db |
| `portone_test_payments` | PortOne 테스트 결제 주문 (payment_id PK, user_id·settlement_id UNIQUE, amount·store_id·channel_key·status·checked_at) — 정산 납부 상태와 무관 | routers/portone.py `init_db()` |
| `portone_quick_test_payments` | PortOne 빠른 테스트(1,000원) 주문 (payment_id PK, user_id, amount, status, checked_at) | routers/portone.py `init_db()` |

> `frontend-react/` 추가(2026-09-14) 및 전체 화면 이전(2026-09-20~21)으로 인한 DB 스키마 변경은 없습니다. React 화면은 기존 테이블 조회·수정 API만 사용합니다. **단, 2026-10-05 PortOne 테스트 결제 연동으로 `portone_test_payments`·`portone_quick_test_payments` 2개 테이블이 추가**되었습니다(`sql/neighborfood_schema.sql`에는 없고 서버 시작 시 `portone.init_db()`가 생성하며 물리 FK는 없는 논리 참조입니다. 상세는 `neighborfood_ERD.md` §9-8).

---

## 5. API 엔드포인트 전체 목록

### 인증 (Auth)
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| POST | `/api/auth/register` | - | 가입 (id·pw·phone) → 세션 토큰 발급 |
| POST | `/api/auth/login` | - | ID·비밀번호 로그인 → 세션 토큰 발급 |
| POST | `/logout` | ✅ | 현재 세션 토큰 폐기 |
| POST | `/request-auth` | - | 비밀번호 재설정 OTP 발송 (30초 쿨다운) |
| POST | `/reset-password` | - | OTP 검증 + 비밀번호 변경 + 전 세션 폐기 |

### 회원 (Users) — `/api/users/*`
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/users/me` | 내 프로필 (전화번호 마스킹, 동네 이름·인증일 포함) |
| PATCH | `/api/users/me` | 닉네임·이미지·이메일·소개·관심·식이 수정 |
| PATCH | `/api/users/me/password` | ✅ **구현(2026-10-08)** — 현재 비밀번호 검증(불일치 401) → 새 비밀번호 6~64자(현재와 동일 400) 저장 → **현재 세션 유지, 타 기기 세션 전부 폐기**. React: `Edit_Profile` 하단 "비밀번호 변경" 폼 |
| POST | `/api/users/withdraw` | 탈퇴 (소프트삭제·익명화·전 세션 폐기) |
| POST | `/api/users/neighborhood` | 동네 인증 (GPS 좌표를 국내 범위로 검증 후 동네 이름·인증일 저장, 좌표 자체는 저장하지 않음) |

### 게시글 (Posts)
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| POST | `/upload-images` | - | 이미지 업로드 |
| POST | `/posts` | ✅ | 게시글 등록 (author_id=세션 회원) |
| GET | `/posts` | - | 목록 (타입·카테고리 필터, 자동 만료 처리 포함) — **`frontend-react/` `HomePage.tsx`가 재사용** |
| GET | `/posts/{id}` | - | 단건 (작성자 닉네임·trust_score 조인) |
| PATCH | `/posts/{id}` | ✅ | 게시글 수정 (작성자/admin, 참여자 있는 공구 인원·가격 잠금) |
| DELETE | `/posts/{id}` | ✅ | 소프트삭제 (작성자/admin) |
| POST | `/posts/{id}/appointment` | ✅ | 약속 장소·시간·좌표 저장 (작성자만, 정산 자동 승계) |
| GET | `/posts/{id}/my-status` | ✅ | 내 역할 조회 (isAuthor, isParticipant) |
| POST | `/posts/{id}/join` | ✅ | 공동구매 참여 (중복·정원 초과·미납 차단) |
| DELETE | `/posts/{id}/join` | ✅ | 참여 취소 (정산 시작 후 차단, 그룹챗 퇴장+시스템 메시지) |

### 채팅 (Chats) — `/api/chats/*`
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/chats` | 1:1 방 생성 (이미 있으면 기존 반환) |
| GET | `/api/chats` | 내 채팅방 목록 (1:1+그룹 통합, 안 읽은 수 포함) |
| GET | `/api/chats/{id}/messages` | 메시지 조회 (증분 폴링) + 읽음 처리 |
| POST | `/api/chats/{id}/messages` | 메시지 전송 |
| POST | `/api/chats/group/{post_id}` | 그룹 채팅방 열기/합류 (작성자·참여자만) |
| GET | `/api/chats/group/{id}/messages` | 그룹 메시지 조회 (발신자 닉네임 포함, is_system 지원) |
| POST | `/api/chats/group/{id}/messages` | 그룹 메시지 전송 |
| GET | `/api/chats/group/{id}/members` | 그룹 참여자 목록 |

### 찜 (Wishlist) — `/api/wishlist/*`
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/wishlist` | 내 찜 목록 (삭제 글 제외) |
| PUT | `/api/wishlist/{post_id}` | 찜 추가 (멱등) |
| DELETE | `/api/wishlist/{post_id}` | 찜 해제 (멱등) |

### 거래 (Transactions) — `/api/transactions/*`
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/transactions` | 내 거래 목록 + 통계 |
| POST | `/api/transactions` | 거래 생성 |
| PATCH | `/api/transactions/{id}` | 상태 전환 (전이 규칙 검증) |

### 정산 (Settlements) — `/api/settlements/*`
| Method | Path | 권한 | 설명 |
|---|---|---|---|
| POST | `/api/settlements` | 주최자 | 정산 생성, 참여자별 분담 자동 계산 |
| GET | `/api/settlements/my` | 본인 | 내가 관련된 정산 목록 |
| GET | `/api/settlements/post/{post_id}` | 관련자 | 게시글 기준 정산 조회 |
| GET | `/api/settlements/{id}` | 관련자 | 정산 상세 |
| POST | `/api/settlements/{id}/shares/me/gps-done` | 참여자 | GPS 인증 완료 표시 (Haversine 100m 서버 재검증) |
| POST | `/api/settlements/{id}/shares/me/qr-done` | 참여자 | QR 인증 완료 표시 (quality_agreed=1) |
| POST | `/api/settlements/{id}/shares/me/pay` | 참여자 | 납부 표시 (GPS+QR 완료 후에만 가능) |
| POST | `/api/settlements/{id}/appointment` | 주최자 | 정산의 약속 장소·시간·좌표 확정 (pending 정산만) |
| POST | `/api/settlements/{id}/complete` | 주최자 | 정산 완료 처리 → transactions 행 자동 생성 |
| POST | `/api/settlements/{id}/cancel` | 주최자 | 정산 취소 |
| POST | `/api/settlements/{id}/shares/{uid}/noshow` | 주최자 | 노쇼 신고 (trust_score -1.0, reports 자동 기록) |
| DELETE | `/api/settlements/{id}/shares/{uid}/noshow` | 주최자 | 노쇼 취소 (unpaid 복원, trust_score +1.0, 신고 삭제) |
| GET | `/api/settlements/{id}/participants/gps-status` | 주최자 | 참여자별 GPS 인증 현황 폴링 |

### 매너 평가 (Ratings) — `/api/ratings/*`
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/ratings` | 평가 등록 (transaction_id 기준, trust_score 업데이트) |
| PATCH | `/api/ratings/{id}` | 평가 수정 |
| DELETE | `/api/ratings/{id}` | 평가 삭제 |
| GET | `/api/ratings/received` | 받은 평가 목록 (user_id 파라미터로 타인 조회 가능) |
| GET | `/api/ratings/transaction/{tx_id}/me` | 특정 거래에 내가 남긴 평가 조회 (수정·삭제용 id 포함) |

### 내 냉장고 (Fridge) — `/api/fridge/*`
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/fridge` | 식재료 목록 (유통기한 임박순) |
| GET | `/api/fridge/summary` | 전체/임박(D-3)/만료 개수 |
| POST | `/api/fridge` | 식재료 추가 |
| POST | `/api/fridge/from-receipt` | 영수증에서 냉장고로 가져오기 |
| PATCH | `/api/fridge/{id}` | 식재료 수정 |
| DELETE | `/api/fridge/{id}` | 식재료 삭제 |

### 신고 (Reports) — `/api/reports/*`
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/reports` | 신고 제출 (target_type: post/user) |
| GET | `/api/reports/my` | 내가 제출한 신고 목록 (최근 50건) |
| DELETE | `/api/reports/{id}` | 신고 취소 (본인만) |

### 관리자 (Admin) — `/api/admin/*` (admin 가드)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/dashboard` | 회원·게시글·거래·신고대기 KPI 집계 |
| GET | `/api/admin/stats` | 대시보드 통계 (최근 7일 접수/처리 추이, 신고 사유 상위 5개, 처리율) |
| GET | `/api/admin/users` | 회원 목록·검색 (report_count·tx_count 포함) |
| PATCH | `/api/admin/users/{id}` | 회원 정지·복구·역할 승격 |
| GET | `/api/admin/notices` | 공지 목록 |
| POST | `/api/admin/notices` | 공지 작성 |
| DELETE | `/api/admin/notices/{id}` | 공지 삭제 |
| GET | `/api/admin/reports` | 신고 목록 |
| GET | `/api/admin/reports/{id}` | 신고 단건 |
| PATCH | `/api/admin/reports/{id}` | 신고 처리 (resolved·dismissed) |
| GET | `/api/admin/chats` | 채팅방 목록 (모니터링) |
| GET | `/api/admin/chats/{id}/messages` | 채팅 메시지 조회 |

### PortOne 테스트 결제 — `/api/payments/portone/*` (신규 2026-10-05, 전부 로그인 필요)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/payments/portone/config` | 테스트 결제 활성화 여부(`enabled`)와 `mode: "test"`만 반환 (키 값은 반환하지 않음) |
| POST | `/api/payments/portone/prepare` | `settlement_id`만 수신, 금액은 서버 DB의 본인 분담금 기준. 정산 `pending`·본인 `unpaid`·**GPS→QR 완료** 필요. 사용자·정산별 같은 `paymentId` 재사용 |
| POST | `/api/payments/portone/{payment_id}/verify` | 본인 주문을 PortOne REST로 조회해 ID·상점·채널 키·금액·통화(KRW)·**채널 TEST**·PAID 검증 후 상태 저장. 취소 상태도 재조회 시 반영 |
| POST | `/api/payments/portone/quick-prepare` | 1,000원 빠른 테스트 주문 생성(`Payment_Quick` 화면) |

> 설정이 없으면(`PORTONE_TEST_ENABLED=true` 및 `PORTONE_STORE_ID`·`PORTONE_CHANNEL_KEY`·`PORTONE_API_SECRET` 필요) 503. **정산의 납부 표시·정산 완료·판매자 지급은 변경하지 않습니다.** 자동 환불·웹훅은 미구현입니다.

### 공개 API (비인증)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/notices` | ✅ **구현(2026-10-08)** — 비인증 공개 공지 목록(`?limit=1~50`, 기본 10, 최신순, `{count, items:[{id,title,content,created_at}]}`, 작성자 비노출). `Help.html`·React `Help` 화면의 공지 아코디언이 호출. 등록·삭제는 관리자 전용 `/api/admin/notices` |
| GET | `/api/config/kakao-key` | 카카오 JS 키 반환 (프론트 동적 로드용) |

### GPS 위치 인증 — `/api/location-verify/*`
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| GET | `/api/location-verify/health` | - | 상태 확인 |
| POST | `/api/location-verify/dummy-target` | ✅ | 타겟 좌표 기반 인증 세션 생성 (subject_id 서버 고정) |
| POST | `/api/location-verify/{id}/gps-check` | ✅ 소유자 | GPS 좌표 제출 → Haversine ≤100m 판정 |
| POST | `/api/location-verify/{id}/qr-issued` | ✅ 소유자 | QR 세션 연결 |
| GET | `/api/location-verify/{id}` | ✅ 소유자 | 세션 단건 조회 |
| GET | `/api/location-verify/history/list` | ✅ | 이력 (일반: 본인만, admin: 전체) |

### QR 인증 — `/api/qr/*`
`request`, `verify`, `verify/{token}`, `history`

### 영수증 인증 — `/api/receipt/*`
`scan`, `verify`, `issue`, `confirm`, `token/{token}`, `{id}`, `history`

> **참고**: `frontend-react/`는 위 목록의 기존 API를 사용합니다. 신규 엔드포인트는 2026-10-05 PortOne 테스트 결제 4종과 2026-10-08 `PATCH /api/users/me/password`·`GET /api/notices` 2종입니다. `PATCH /posts/{id}`는 제목·설명·카테고리·상태·교환 희망·주소·좌표에 더해 **사진(`images`, 최대 10장)·거래 유형(`type`)·목표 인원(`gb_target`)·1인 금액(`gb_price`)**을 반영합니다(2026-10-08). 참여자가 있거나 진행 중/완료 정산이 있으면 유형·인원·가격은 409로 잠깁니다.

---

## 6. 프론트엔드 페이지 현황

### 사용자 화면

| 파일 | 상태 | 비고 |
|---|---|---|
| `Splash.html` / `Onboarding.html` | ✅ 정적 | 온보딩 플로우 |
| `Login.html` / `Signup.html` | ✅ 연동 | 가입·로그인 API 연결 |
| `Password_Reset.html` | ✅ 연동 | OTP 비밀번호 재설정 |
| `Home.html` | ✅ 연동 | 게시글 목록 실데이터 — ⚠️ 아래 "React(Vite) 프런트엔드" 절 참고(React `HomePage.tsx`와 병행 존재) |
| `Index.html` | ✅ 정적 | 랜딩 페이지 |
| `Map.html` | ✅ 연동 | Kakao 지도 + 주변 게시글 |
| `Search.html` / `Search_Results.html` | ✅ 연동 | 검색 API 연결 |
| `Product_Detail.html` | ✅ 연동 | 나눔·교환 게시글 상세 |
| `Group_Buy_Detail.html` | ✅ 연동 | 공동구매 상세 + 참여/취소 토글 + 작성자 3-dot 메뉴 |
| `Create_Post.html` | ✅ 연동 | 게시글 등록 + 편집 모드(`?edit={id}`) |
| `Reservation.html` | ✅ 연동 | 거래 신청 (실좌표 연동) |
| `Location_Detail.html` | ✅ 연동 | 장소 지도 상세 |
| `Neighborhood_Setting.html` | ✅ 연동 | 동네 인증 (GPS 좌표 저장) |
| `My_Page.html` | ✅ 연동 | 내 프로필·신뢰 온도·리뷰 수 |
| `Edit_Profile.html` | ✅ 연동 | 프로필 수정 (이메일·소개·관심·식이) |
| `My_Activity.html` | ✅ 연동 | 채팅·내 글·거래 내역 탭 + 매너 평가 모달 + 게시글 수정 링크 |
| `Wishlist.html` | ✅ 연동 | 찜 목록 실데이터 |
| `Fridge.html` | ✅ 연동 | 내 냉장고 (수동 추가·영수증 가져오기) |
| `Chat_List.html` / `Chat_Detail.html` | ✅ 연동 | 1:1 채팅 |
| `Group_Chat.html` | ✅ 연동 | 그룹 채팅 + 약속 모달 + 정산 시작 버튼 |
| `Transaction_History.html` | ✅ 연동 | 거래 내역 + 정산 보기 링크 |
| `Settlement.html` | ✅ 연동 | 공동구매 정산 전체 흐름 (주최자/참여자 분기, 완료 후 매너평가 리다이렉트) |
| `Local_Verify_Demo.html` | ✅ 연동 | GPS 100m 위치 인증 (정산 모드 약속 좌표 자동 로드) |
| `QR_Scan.html` | ✅ 연동 | QR·바코드 스캔 (정산 QR 발급 모드 포함) |
| `Receipt_Verify.html` | ✅ 연동 | 영수증 OCR 인증 |
| `Report.html` | ✅ 연동 | 신고 제출 |
| `Help.html` | ✅ 연동 | 고객센터 + 공개 공지 아코디언 — 2026-10-08 `GET /api/notices` 구현으로 공지 목록 표시(이전 정정 해소) |
| `Withdraw.html` | ✅ 연동 | 회원 탈퇴 |
| `Verify.html` | ✅ 정적 | OTP 인증 화면 |

### 관리자 화면

| 파일 | 상태 | 비고 |
|---|---|---|
| `Admin_Dashboard.html` | ✅ 연동 | KPI 4종 + 신고 목록 실데이터 |
| `Admin_Users.html` | ✅ 연동 | 회원 목록·검색·정지·승격·로그아웃 |
| `Admin_Notices.html` | ✅ 연동 | 공지 목록·작성·삭제 (예약·푸시는 준비 중 안내) |
| `Admin_Chat_History.html` | ✅ 연동 | 채팅방 목록 + 메시지 조회 |
| `Admin_Report_Detail.html` | ✅ 연동 | 신고 단건 로드 + 기각·삭제·정지 액션 (경고 발송은 스키마 미지원으로 준비 중 안내) |
| `Admin_Staff_Invite.html` | ✅ 연동 | 회원 검색 → 운영진 승격/권한 해제 (이메일 초대 없이 §9 정책대로 재설계, 2026-09-12) |

### React(Vite) 프런트엔드 — 화면 39개 전체 이전 (2026-09-20~21, 홈 화면은 2026-09-14)

기존 정적 HTML 39개 화면 식별자를 React 경로(`#/화면명`)로 이전한 구현입니다. 39개 화면이 39개의 독립 TSX 파일은 아니며, 같은 그룹의 화면은 하나의 컴포넌트와 props를 공유합니다. 홈은 승인된 메인 디자인의 `HomePage.tsx`를 유지합니다.

| 기존 화면 식별자 | React 구현 / 연결 |
|---|---|
| Home | `neighborfood/HomePage.tsx` — 카테고리 필터·검색·게시글 카드 그리드, `GET /posts` 재사용 |
| Login, Signup | `migration/auth.tsx` — 로그인·가입·토큰 저장 |
| Password_Reset, Verify | `auth.tsx` — 인증번호 요청→비밀번호 변경 공통 흐름 (Verify는 별도 OTP 성공 페이지 대신 이 흐름 공유) |
| My_Page, Edit_Profile, Withdraw | `auth.tsx` — 프로필 조회·수정·탈퇴·로그아웃 |
| Search, Search_Results, Wishlist | `migration/posts.tsx` — 검색·분류·찜 목록 |
| Product_Detail, Group_Buy_Detail | `posts.tsx`(+`PostGallery.tsx`) — 상세·찜·신고·작성자 작업·공동구매 |
| Create_Post, Reservation, Report | `posts.tsx` — 사진 업로드·등록/수정·거래 신청·신고 |
| Fridge | `migration/fridge.tsx` — 조회·추가·수정·삭제·상태 전환 |
| Chat_List, Chat_Detail, Group_Chat | `migration/trades.tsx` — 실제 채팅·그룹·메시지 폴링 |
| My_Activity, Transaction_History | `trades.tsx` — 게시글·거래·신고·매너 평가 |
| Settlement | `trades.tsx` — 정산 생성·약속·인증·납부 표시·불참·완료/취소 |
| Map, Location_Detail, Neighborhood_Setting | `migration/location.tsx` — Kakao 지도·검색·위치·동네 설정 |
| Local_Verify_Demo | `location.tsx` — 서버 GPS 검증·정산·QR 연결 |
| QR_Scan | `migration/qr.tsx` — QR 발급(2026-10-08 발급 직후 QR 토큰 읽기 전용 표시·"토큰 복사" 추가, 발급 상태일 때만 노출)·카메라 스캔(공용 `Scanner.tsx`, 2026-10-05 통합)·토큰 검증·정산 연결 |
| Payment_Checkout, Payment_Result, Payment_Quick, Payment_Preview (정적 HTML에 없는 신규 화면 4종, 2026-10-05) | `migration/portone.tsx` — 정산 상세의 "결제 확인으로" → 결제 확인 → PortOne 테스트 결제창 → 결과 조회 / 빠른 테스트 / 예시 미리보기. PG 리다이렉트 복귀는 `acceptPaymentReturn()`으로 `#/Payment_Result`에 연결(모바일 동작 미검증) |
| Receipt_Verify | `migration/receipt.tsx` — OCR 업로드·항목 편집/선택·인증·냉장고 등록 |
| Admin_Dashboard, Admin_Users, Admin_Notices | `migration/admin.tsx` — 관리자 데이터·회원·공지 |
| Admin_Report_Detail, Admin_Chat_History, Admin_Staff_Invite | `admin.tsx` — 신고 처리·채팅 기록·회원 권한 관리 |
| Help | `migration/routes.tsx` — 현재 기능에 맞춘 도움말 (미구현 안내는 옮기지 않음) |
| Splash, Onboarding, Index | `routes.tsx` — 홈·로그인·가입·동네 설정 진입 링크 / React 화면 목록 |

**공통 구성**: `core.tsx`(API 요청·인증 토큰·오류·상태 처리), `design.css`(공통 디자인 토큰·폼·버튼·리스트·대화상자), `loading.tsx`(화면 전환·최초 조회 공통 로딩, 백그라운드 재조회는 기존 내용 유지), `autocomplete.tsx`(검색·회원·주소 공통 자동완성 — 250ms 디바운스·최대 8개·이전 요청 취소·한글 조합 처리·방향키/Enter/Esc), `PostGallery.tsx`(게시글 상세 사진 갤러리), `routes.tsx`(화면 목록·라우팅·접근 제어).

**경로·서버·인증**: 화면 이동은 해시 경로(`/#/Fridge`, `/#/Product_Detail?id=1`)라 새로고침에 별도 서버 라우팅이 필요 없습니다. Vite 개발/preview 서버가 `/api`·`/posts`·`/uploads`·`/upload-images`·`/logout`·`/request-auth`·`/reset-password`를 FastAPI(8000)로 프록시합니다. React는 자체 로그인·토큰 처리를 가지며(`nf_token` 등), 정적 HTML(`127.0.0.1:8000`)과 접속 출처가 달라 `localStorage`가 공유되지 않으므로 React에서 별도 로그인합니다. 회원 전용 화면은 토큰이 없으면 로그인 안내를 표시하고, `Admin_*`은 `GET /api/users/me`의 role이 admin일 때만 열리며 서버도 권한을 검사합니다.

**검증 범위**: TypeScript·Vite 프로덕션 빌드 통과, 별도 테스트 FastAPI/SQLite에서 로그인·냉장고 등록·사용 완료·게시글 폼 제출·상세 이동·공동구매 참여·그룹 채팅·정산(생성→약속→GPS→QR→납부 표시→완료)·거래 상태 전환·평가·찜 API 확인, 일반 회원의 관리자 화면 접근 차단 확인, 공통 자동완성(입력·키보드 선택·이전 응답 취소)·로딩·사진 전환 동작 검사. **미검증**: 실제 브라우저 화면·모바일 터치·키보드 전체 탐색, 카메라 스캔·위치 정확도·Kakao SDK·CLOVA OCR(실제 환경 확인 필요), 기존 HTML과의 세부 상호작용·레이아웃 1:1 동등성.

**이전 시 제한**: 정산의 납부 표시는 결제 승인·자동 송금이 아님. (2026-10-08 해소: 게시글 수정 API 확장으로 사진·유형·인원·가격 편집 가능, 공개 공지 API 구현으로 도움말에 공지 노출)

> **병행 구조 안내**: 기존 정적 HTML(`frontend/`)은 삭제하지 않고 최종 점검이 끝나기 전까지 유지합니다(§9). 정식 배포는 **React(`dist/`)를 FastAPI가 `/`에서 서빙**하는 방식으로 2026-10-03 적용되었고(§7), 정적 HTML(`frontend/`)의 최종 처리만 미결정입니다(§8). PWA 설치·오프라인 기능은 구현되지 않았습니다.

---

## 7. 개발 이력 (시간순)

### 2026-06 초기 구현
- 지역 게시판 (나눔·교환·공동구매) CRUD
- 회원 가입·로그인·OTP 비밀번호 재설정·프로필 수정·탈퇴
- QR 거래 인증·영수증 OCR 인증
- 찜 목록·1:1 채팅·동네 인증
- 거래(`transactions`)·공동구매 참여자(`groupbuy_participants`) 기본 구조
- 내 냉장고·그룹 채팅·관리자(notices·reports) 기본 구현
- 관리자 계정 부트스트랩(`seed_admin.py`)
- 신고(`POST /api/reports`) + 관리자 처리
- GPS 위치 인증(`location_verify_sessions` + `/api/location-verify/*`) 기초 구현

### 2026-07-09 커밋 전 점검
- 공동구매 참여 레이스컨디션 수정 (원자적 `UPDATE` + `rowcount==0` → 409)
- Kakao 지도 키: `Map.html` → `/api/config/kakao-key` 동적 로드 전환
- `neighborfood_schema.sql` 6개 테이블 누락분 동기화
- `tokens.css` 전 39개 화면 적용
- `requirements.txt` FastAPI/Uvicorn 버전 갱신

### 2026-08-03 보안 강화 + 핵심 기능 완성 (P0/P1)
- **Kakao 지도 키 하드코딩 전면 제거** — 잔여 6개 화면 모두 동적 로드로 전환
- **GPS 위치 인증 보안 강화**
  - 전 엔드포인트 `Depends(get_current_user)` 추가
  - `subject_id`를 서버가 로그인 사용자 id로 강제 고정
  - `_assert_owner()` 신설 (소유자/admin만 통과)
  - 이력 조회: 일반 사용자 → 본인 세션만, admin → 전체
  - `mark_qr_verified_by_qr_session()` 실제 호출로 GPS↔QR 연동 완성
- **`Reservation.html`** 실좌표 연동 (기존 하드코딩 제거)

### 2026-08-04 정산 시스템 구현
- **신규 파일**: `settlement_db.py`, `settlements.py`
- **신규 테이블**: `settlements`, `settlement_shares`
- **API 13종** 구현 (생성·목록·상세·GPS완료·QR완료·납부·완료·취소·노쇼 신고/취소·GPS 폴링)
- `Settlement.html` 전체 흐름 실데이터 연동 (주최자/참여자 역할 분기)
- `Group_Buy_Detail.html` "정산하기" 버튼, `Transaction_History.html` "정산 보기" 링크 추가
- 정산 완료 시 `transactions` 행 자동 생성 (매너 평가 흐름 연동)

### 2026-08-07 전체 흐름 완성
- **GPS 100m 실검증** — 기존 self-referencing 구조를 약속 좌표 고정 + Haversine 서버 재검증으로 교체
- **`POST /posts/{id}/appointment`** 신규 (채팅 단계에서 먼저 약속 확정, 정산 생성 시 자동 승계)
- `Group_Chat.html`: "정산 시작하기" 버튼, 약속 모달 GPS 좌표 캡처, `/api/posts/` → `/posts/` 경로 버그 수정
- `Settlement.html`: "참여자 QR 스캔하기" 버튼, 완료 후 "매너 평가 남기기" 버튼
- `Local_Verify_Demo.html`: 정산 모드 약속 좌표 자동 로드, `RADIUS_M=100`, PWA `isSecureContext` 체크
- `DEFAULT_RADIUS_M` 300 → **100** (프론트·백 동기화)

### 2026-08-12 UX 갭 감사 및 해소
기능 갭 감사 보고서(Unreachable UI·Admin 스텁·권장 기능 3개 카테고리)를 기반으로 우선순위별 구현 진행.

**Phase 2 — 관리자 & 핵심 UX**

| 항목 | 파일 | 내용 |
|---|---|---|
| Admin_Notices 라이브 연동 | `Admin_Notices.html` | 공지 목록·작성·삭제 API 연결, 예약·푸시는 "준비 중" 안내, 사이드바 로그아웃 |
| Admin_Chat_History 라이브 연동 | `Admin_Chat_History.html` | 대화방 목록 + 메시지 실데이터, 정적 더미 제거 |
| 공동구매 참여/취소 토글 | `Group_Buy_Detail.html` | `GET /posts/{id}/my-status` 기반 버튼 전환, 취소 시 `DELETE .../join` 호출 |
| 작성자 3-dot 드롭다운 | `Group_Buy_Detail.html` | 수정(`Create_Post.html?edit={id}`) + 삭제(`DELETE /posts/{id}`) 메뉴 |
| 매너 평가 리다이렉트 수정 | `Settlement.html` | 완료 버튼 → `My_Activity.html?tab=history` |
| 공개 공지 UI | `Help.html` | `GET /api/notices?limit=10` 아코디언 표시 (비회원 열람) — 2026-10-08 공개 API 구현으로 정상 표시 |
| 게시글 수정 흐름 | `Create_Post.html`, `My_Activity.html` | "수정" 링크 추가, `?edit=` 프리필, `PATCH /posts/{id}` 제출, 참여자 있는 공구 인원·가격 잠금 |

**Phase 3 — 보조 개선**

| 항목 | 파일 | 내용 |
|---|---|---|
| 게시글 자동 만료 | `posts.py` | `list_posts()` 진입 시 만료 글 `expired` 일괄 전환 |
| 참여 취소 그룹챗 연동 | `posts.py` | `messages.is_system` 컬럼 멱등 마이그레이션, 그룹챗 퇴장 + 시스템 메시지 삽입 |
| 취소 버튼 스타일 수정 | `Group_Buy_Detail.html` | Tailwind `error` 색 미정의 문제 → `style.cssText` 인라인 직접 지정(`#ba1a1a`) |

### 2026-08-17 영수증 파서 노이즈 키워드 보강
- **`receipt_db.py` `RC_NOISE_KW` 보강**: 스타벅스 등 카페형 영수증에서 "POS/카카오페이/번호/발급/가능" 등 메타 문구가 식재료 품목으로 잘못 인식되던 문제를 `is_meta_line()` 키워드 보강으로 해결

### 2026-08-22 영수증 파서 v2.1 — 마트형 구조 지원
- **`receipt_db.py` `parse_receipt()` parser v2.1 업데이트**:
  - 마트형 `순번 → 품목명 → 바코드/PLU → 단가 → 수량 → 금액` 구조 파싱 로직 추가
  - `*231973` 같은 PLU 코드·긴 바코드·`[2,150]` 같은 참고가를 실제 가격으로 오인하지 않도록 정규식 강화
  - 500/750원처럼 콤마 없는 3자리 가격도 품목 영역에서는 허용
  - `900ML`, `150g` 같은 용량 토큰은 상품명에 이어 붙이는 처리 추가
  - CLOVA가 한 행을 여러 `inferText` 토큰으로 쪼개도 품목 상태를 유지

### 2026-09-12 관리자 기능 실데이터 연동 + 신뢰 페널티 자동화
- **공용 관리자 가드**: `frontend/shared/adminGuard.js` 신설(`nfRequireAdmin()`), 6개 `Admin_*.html` 전체에서 중복 가드 로직 통합 + 사이드바 신고 배지·관리자 이름 실데이터화 + 로그아웃 버튼 미연동 3곳 수정
- **`seed_admin.py` 복원**: README.md에 문서화되어 있었으나 저장소에 없던 관리자 계정 부트스트랩/승격 스크립트를 동일 인터페이스로 재작성
- **`Admin_Users.html` 실데이터 연동**: `GET /api/admin/users`에 `status` 필터 + `tx_count`/`report_count` 집계 추가, 검색·필터칩·정지/복구/승격/강등 액션 연결
- **신고 처리 실데이터 연동**: `GET /api/admin/reports/{id}` 신설(신고자·대상 회원/게시글·누적 신고수), `Admin_Report_Detail.html`에서 기각·게시글삭제·계정정지·처리완료 액션 실연결 (증빙 이미지·AI 검토·채팅 연결·관리자 메모·처리 로그는 스키마 미지원으로 준비 중 안내). 대시보드 신고 표 행 클릭 시 상세로 이동하도록 연결
- **`Admin_Staff_Invite.html` 재설계**: 이메일 초대 mock → §9 정책에 맞춘 회원 검색→승격/권한 해제 UI로 전면 교체 (백엔드 API 재사용, 추가 없음)
- **대시보드 통계 연동**: `GET /api/admin/stats` 신설(주간 접수/처리 추이, 신고 사유 분포, 최근 7일 처리율). 커뮤니티 건강도(하드코딩 98/100) → 이번 주 신고 처리율로 교체, 최근 운영 활동 로그는 activity log 테이블 미지원으로 준비 중 안내
- **CORS `.env` 동적 분기**: `main.py`가 `ALLOWED_ORIGINS`(콤마 구분)를 읽어 배포 도메인만 허용, 미설정 시 개발 편의를 위해 `*` 유지. 실제 도메인 입력은 배포 시점으로 유예
- **미납 정산 참여 차단 리팩터링**: `posts.py`의 인라인 SQL을 `settlement_db.has_unpaid_settlement()` 호출로 교체 (동작 변화 없음, 로직 단일화)
- **주최자 귀책/먹튀 trust_score 자동 페널티**: `PATCH /api/admin/reports/{id}`에서 `target_type='user'`인 신고가 `pending → resolved`로 확정될 때 자동으로 `-2.0` 적용 (클램프 0~99, 이미 처리된 신고 재처리 시 중복 적용 안 됨). 상세는 `Settlement_Implementation_Plan.md` §6 참고
- **회원 직접 신고 진입점 신설**: `Product_Detail.html` 작성자 카드 하단에 "이 회원 신고하기" 링크 추가(`targetType=user`, 본인 게시글이면 숨김). 기존 `authorName`이 `author_id`(숫자)를 그대로 표시하던 버그도 함께 수정. `Group_Buy_Detail.html`·`Product_Detail.html`의 "게시글 신고하기" 링크가 대상 정보(targetId 등) 없이 연결되던 버그 수정

### 2026-09-14 React(Vite) 홈 화면 부분 마이그레이션 시작 (이후 2026-09-20·21 전체 이전으로 확장)
- **신규 워크스페이스**: `frontend-react/` — Vite 8 + React 19 + TypeScript, Node.js 20 이상 필요, 린터는 ESLint 대신 **Oxlint**(`.oxlintrc.json`, `react/rules-of-hooks` error) 사용. 의존성 설치는 `npm ci`(lockfile 기준)
- **신규 파일**: `src/main.tsx`(React 진입점, StrictMode), `src/App.tsx`(AppLayout+HomePage 조합), `src/neighborfood/AppLayout.tsx`(헤더+하단 네비 공통 레이아웃), `src/neighborfood/HomePage.tsx`(홈 피드 — 카테고리 필터·검색·게시글 카드 그리드), `src/neighborfood/api.ts`(백엔드 연동 헬퍼), `src/neighborfood/Icon.tsx`(SVG 아이콘)
- **백엔드 연동**: `api.ts`의 `getPosts(category, keyword, signal)`이 기존 `GET /posts?limit=24&category=...&keyword=...`를 그대로 호출 — **신규 백엔드 API 없음**. 백엔드 주소는 `VITE_API_BASE_URL` 환경변수(기본값 `http://127.0.0.1:8000`)로 지정
- **레거시 연계**: `legacy(page)` 헬퍼(`${backend}/frontend/${page}`)로 지도(`Map.html`)·등록(`Create_Post.html`)·내 활동(`My_Activity.html`)·마이(`My_Page.html`)·내 냉장고(`Fridge.html`)·내 동네 설정(`Neighborhood_Setting.html`)·게시글 상세(`Product_Detail.html`/`Group_Buy_Detail.html`)로 하드 네비게이션(SPA 라우팅 아님)
- **구조 성격**: 기존 정적 HTML `Home.html`을 대체·삭제하지 않고 **병행 운영**하는 하이브리드 마이그레이션. 전면 전환 로드맵은 아직 없음(§8 잔여 작업 목록 참고)
- **알려진 미비점**: `.env.example`에 `VITE_API_BASE_URL` 템플릿이 아직 없음(변경 시 `frontend-react/.env.local`을 직접 생성해야 함 — `.env.local`은 Vite의 gitignore 기본 항목), `frontend-react/README.md`가 Vite 기본 템플릿 그대로 미교체, `frontend/`와 `frontend-react/` 간 회원 인증(토큰) 공유 방식 미정(현재는 React 쪽에 로그인 필요 화면이 없어 즉시 영향 없음)

> ※ 위 2026-09-14 항목은 당시 기준(홈 화면 한정)이며, 이후 경과는 아래 2026-09-20·2026-09-21 절을 현행 기준으로 봅니다.

### 2026-09-20 React 전체 화면 이전 (신규)
- **범위**: 기존 HTML 39개 화면 식별자를 React 경로로 매핑·이전(`frontend-react/src/migration/` — `auth.tsx`·`posts.tsx`·`fridge.tsx`·`trades.tsx`·`location.tsx`·`qr.tsx`·`receipt.tsx`·`admin.tsx`·`routes.tsx`·`core.tsx`·`design.css`). 기존 `HomePage.tsx`·`home.css`는 승인본으로 유지. 상세 매핑은 §6, 기록은 `frontend-react/docs/MIGRATION_REPORT.md`
- **구조**: 해시 라우팅(`#/화면명`), `App.tsx`가 `useRoute`·`Guard`·`Screen`으로 화면을 렌더. `api.ts`의 `legacy(page)`는 이제 정적 HTML 하드 네비게이션이 아니라 `#/화면명` 해시 경로를 반환
- **서버 연동**: FastAPI·SQLite·기존 HTML 변경 없음. `vite.config.ts`에 개발/preview 프록시 추가(`NEIGHBORFOOD_BACKEND`), `VITE_API_BASE_URL` 미설정 시 상대경로 사용. `package.json`에 `qrcode`·`jsqr`(+`@types/qrcode`) 추가
- **디자인**: 승인된 메인 화면 v2를 기준으로 공통 토큰 적용(`frontend-react/docs/DESIGN_CONTEXT.md`)

### 2026-09-21 공통 로딩·자동완성·게시글 상세 보강 + GitHub 반영 (신규)
- **공통 로딩**(`loading.tsx`): 화면 전환·최초 데이터 조회에 공통 로딩 표시, 백그라운드 재조회는 기존 내용 유지
- **공통 자동완성**(`autocomplete.tsx`): 검색·회원 검색·주소 검색, 입력창 기존 폭 유지, 250ms 디바운스·최대 8개·이전 요청 취소·한글 조합 중 요청 방지·방향키/Enter/Esc
- **게시글 상세**(`PostGallery.tsx` + `posts.tsx`): 큰 사진 갤러리, 데스크톱 최대 폭 1320px 2열·900px 이하 1열
- **GitHub 반영**: 커밋 `9df3688`(24개 파일, +5,184/−43), 미커밋 로컬 변경은 저장소에 포함하지 않음
- **문서 정정**: 공개 공지 API(`GET /api/notices`) 미구현 확인(관리자 전용 `/api/admin/notices`만 존재), `PATCH /posts/{id}`가 인원·가격을 반영하지 않음을 확인
- **미검증·미구현**: 실제 브라우저·모바일·기기 검증 미완료, PWA 설치·오프라인 기능 미구현

### 2026-09-30 배포 서버 구성 착수 (서버·도메인, 코드 변경 없음)
- **서버 배치**: Oracle Cloud(Osaka) Micro 인스턴스(Ubuntu 24.04)에 저장소를 클론(`e221dc9`)하고 Python 3.12 가상환경에 `requirements.txt` 설치. 서버 `.env`에는 CLOVA·Kakao·`ALLOWED_ORIGINS=https://neighborfood.duckdns.org`를 기입(값은 저장소에 없음, 권한 600, `.env` 파서는 줄 끝 주석을 제거하지 않으므로 `KEY=값`만 기입)
- **실행 방식**: systemd 서비스 `neighborfood`가 `uvicorn main:app --host 127.0.0.1 --port 8000`(`--reload` 없음, worker 1개 — SQLite 사용)을 상시 실행. 재시작 후 `active`, `GET /docs` 200 확인. 시작 시 `data/neighborfood.db`가 자동 생성됨
- **도메인**: DuckDNS `neighborfood.duckdns.org`를 서버 Public IP에 연결(IP는 문서에 기재하지 않음). 현재는 Nginx 기본 화면만 응답하며, 앱은 `127.0.0.1`에만 열려 있어 외부 접속은 Nginx 프록시 설정 이후 가능
- **점검**: `.env`·DB·키 파일이 저장소 추적 대상·커밋 이력에 없음, `.gitignore`에 `.env`·`*.db`·`venv/`·`dist/` 포함, 하드코딩된 키 없음 확인(2026-09-30). 이 시점 GitHub `main`에는 팀원의 React 잔여 화면·결제 관련 후속 작업이 포함되어 있지 않음
- **[2026-10-03 갱신 — 아래 절에서 대부분 완료]** 미완료였던 항목: Nginx 리버스 프록시, HTTPS(certbot), `dist/` 업로드와 `main.py`의 SPA 마운트, 관리자 계정 생성(앱에 비밀번호 변경 API가 없어 기본 비밀번호 계정 대신 일반 가입 후 `python seed_admin.py <login_id>`로 승격 권장), 실환경 검증, PWA


### 2026-10-01~03 매너 평가 표시·README 교체·`dist/` 서빙 (코드 변경)
- **작성자 매너 평가 표시**: 게시글 상세 작성자 카드에 `GET /api/ratings/received?user_id=` 요약(👍/👎 건수)을 표시. 로그인 시에만 조회하며 0건·오류 시 숨김. 신규 API 없음
- **`frontend-react/README.md` 교체**: Vite 기본 템플릿 → 프로젝트 설명·실행·폴더 구조·배포 절차(문서 사고 경위: 루트 `README.md`가 한때 이 내용으로 덮어써져 복구 후 분리)
- **`main.py` `dist/` 서빙**: `frontend-react/dist/index.html`이 있으면 `/`에서 React 앱을 서빙(없으면 임시 안내 페이지), `FRONTEND_DIST_DIR`로 위치 변경 가능, `index.html`은 no-cache·`assets/`는 장기 캐시. 서버 시작 시 `dist/index.html` 유무를 확인하므로 **최초 업로드 후 재시작 1회 필요**

### 2026-10-03 운영 서버 HTTPS 배포 완료 (Nginx·certbot·`dist/`)
- **Nginx 리버스 프록시**: `server_name neighborfood.duckdns.org`, `/` → `127.0.0.1:8000`(`X-Forwarded-*` 헤더, `proxy_read_timeout 90s`), `client_max_body_size 20M`(사진·영수증 업로드), 기본 사이트 제거. Nginx 경유 `/docs` 200 확인
- **HTTPS**: certbot(`--nginx`)으로 Let's Encrypt 인증서 발급(만료 2027-01-01), HTTP→HTTPS 리다이렉트, `certbot renew --dry-run` 성공, `certbot.timer`로 자동 갱신
- **프런트 배포**: 서버(1GB)에서는 빌드하지 않고 PC에서 `npm run build`한 `dist/`를 scp 업로드 → 서비스 재시작 → 로그 `[SPA] React 빌드 서빙` 확인
- **외부 서비스**: HTTPS 도메인의 `#/Map`에서 카카오 지도 렌더링 확인(Kakao 허용 도메인에 `https://neighborfood.duckdns.org` 등록)
- **일상 배포 절차**: 백엔드 = 서버 `git pull` + `sudo systemctl restart neighborfood` / 프런트 = PC 빌드 후 `dist/` 교체(재시작 불필요) / `.env` 변경 = 재시작. 업로드 이미지는 서버 디스크 `uploads/`에 저장되고 DB에는 파일명만 저장되므로 백업은 `data/`와 `uploads/`를 함께 해야 함
- **상세 운영·점검·장애 대응**: `NeighborFood_서버_실행_점검_가이드.md`. **미확인(2-5)**: 재부팅 후 자동 시작, systemd `Restart=` 정책, SSH 비밀번호 로그인 차단, 부하테스트(5~6명 동시·OCR 겹침), 관리자 계정 승격, 서버 `.env`의 PortOne 키 ← 해당 문서 (저장소 미포함 — 개별 보관)

### 2026-10-05 PortOne V2 테스트 결제 + QR 스캔 UI 통합 (팀원 박준기, 커밋 `ec1da57`)
- **서버**: `app/routers/portone.py` 신규, `main.py`에 라우터(`/api/payments/portone`) 등록·`portone.init_db()` 호출, 테이블 `portone_test_payments`·`portone_quick_test_payments`, 환경변수 `PORTONE_TEST_ENABLED/STORE_ID/CHANNEL_KEY/API_SECRET`(템플릿 `portone.env.example`). 가격은 서버가 DB 분담금으로 결정하고 PortOne REST로 재검증(TEST 채널만 성공 인정). 정산 납부 상태 불변
- **프런트**: `portone.tsx`(Payment_Checkout·Result·Quick·Preview), `Scanner.tsx`·`scanner.css`·`interface.css`(QR·영수증 공용 스캐너와 스타일), `routes.tsx`·`trades.tsx` 수정, 영수증 화면 중앙 정렬
- **테스트**: `tests/test_portone.py` 12개(외부 API mock). 실제 PortOne 계정·PG 결제창 승인은 10/5 테스트 결제창 화면으로 확인(실행 환경은 미확인). 거래별 세션 결속 강화·자동 환불·웹훅·모바일 리다이렉트 검증은 범위 밖
- **"임시결제" 의미 확정**: 5주차 보고서의 "임시결제"는 포트원 **테스트 채널 결제**이며 실결제 구현이 아님 → §9 외부 결제 정책 갱신
- **서버 반영 상태 미확인**: 서버 `git pull`·`.env` 키 추가·`dist/` 재빌드/업로드·재시작이 아직 기록에 없음(절차: `캡스톤_전시회_준비_일정.md` "PortOne 서버 반영") ← `캡스톤_전시회_준비_일정.md` (저장소 미포함 — 개별 보관)
- **확인된 공백**: 이 푸시 이후에도 React 그룹 채팅에는 거래 액션 바(약속 → 정산/GPS/QR 진입점)가 없음(약속은 정산 상세에서만 입력)

### 2026-10-05~06 배포 방식 검토·문서 정리 (코드 변경 없음)
- `NeighborFood_배포방식_비교_Oracle_vs_Vercel.md`: Oracle VM 유지 vs Vercel+Supabase 비교 → **Oracle 유지 + 리스크 보강** 권고(서버 구축 완료, 세션·QR·GPS 상태는 이미 SQLite에 저장되어 "메모리→DB 이전"은 불필요, 전환 시 실제 작업은 SQLite→PostgreSQL 이전·업로드 저장소 이전) ← 해당 문서 (저장소 미포함 — 개별 보관)
- 졸업작품집 원고·시스템 구성도·ERD 산출물 작성(`졸업작품집_원고_작업_기록.md`, `졸업작품집_원고_유의사항.md`) ← 해당 문서 2종 (저장소 미포함 — 개별 보관)
- 문서 정합화: ERD 21테이블, §4·§5·§6 PortOne 반영, §9 결제 정책 갱신

---

## 8. 잔여 작업 목록

| 우선순위 | 항목 | 상세 |
|---|---|---|
| ✅ **완료 (2026-10-03)** | **작성자 매너 평가 표시** | React `posts.tsx` 상세 작성자 카드에 `GET /api/ratings/received?user_id=` 요약(👍/👎) 연동 완료. 정적 HTML 상세는 미적용 |
| 🟢 **준비 완료** | **배포 CORS 도메인 제한** | `main.py`가 `.env`의 `ALLOWED_ORIGINS`를 읽어 동적 분기하도록 구현 완료(2026-09-12). 값 미설정 시 개발 편의를 위해 `*` 유지. **2026-09-30: 배포 서버 `.env`에 `ALLOWED_ORIGINS=https://neighborfood.duckdns.org` 반영 완료**(다른 도메인에서 서빙하게 되면 값을 함께 수정해야 함). 정적 빌드(`dist`) 배포 시에는 Vite 프록시가 없으므로 API 프록시를 배포 서버에 구성하거나 `VITE_API_BASE_URL`로 공개 API 주소를 지정해야 함 |
| 🟡 **권장 (2026-10-06 갱신)** | **배포 서버 운영 마무리(2-5)** | Nginx·HTTPS·`dist/` 서빙은 2026-10-03 완료. 남은 것: 관리자 계정 승격(`seed_admin.py <login_id>`, 기본 비밀번호 `admin0000` 계정 생성 금지), 재부팅 후 서비스·nginx 자동 시작 확인, systemd `Restart=` 정책, SSH 비밀번호 로그인 차단 확인, 부하테스트(`ab -n 100 -c 6`, OCR 겹침), `apt` 업데이트<br>**[2026-10-08 방침] 구현·보완 예정(시연·발표 전 처리)** |
| 🟢 **선택 (2026-09-21 갱신)** | **`VITE_API_BASE_URL` 템플릿 정리** | React는 미설정 시 상대경로 + Vite 프록시를 사용하므로 필수 아님. 공개 API 주소를 직접 쓰는 경우에만 `frontend-react/.env.local`에 지정. 템플릿 항목 추가는 선택 사항<br>**[2026-10-08 방침] 차후 필요하다고 판단될 때 처리** |
| ✅ **완료 (2026-10-03)** | **`frontend-react/README.md` 교체** | 프로젝트 설명·실행·폴더 구조·배포 절차로 교체됨. 보정 필요: 배포 절차의 `scp -r dist/* …/dist/`는 서버에 `dist/`가 이미 있어야 동작하므로 최초 업로드용 명령(`rm -rf` 후 `scp -r dist …/frontend-react/`)으로 수정 권장 |
| ✅ **완료 (2026-10-08)** | ~~로그인 상태 비밀번호 변경 API~~ | `PATCH /api/users/me/password` 구현(현재 세션 유지·타 세션 폐기), React `Edit_Profile` 폼, pytest(`tests/test_account_notice_post.py`) |
| 🔵 **정책 결정 필요 (2026-10-06 갱신)** | **React·정적 HTML 병행 정리** | 정식 배포는 React `dist/` 서빙으로 확정·적용(2026-10-03). 정적 HTML(`frontend/`)과 `main.py`의 `/frontend`·`/QR_Scan.html`·`/Receipt_Verify.html` 직접 라우트의 최종 폐기·보존 여부만 미결정<br>**[2026-10-08 방침] 프로젝트 구현이 100% 끝난 뒤, 폐기해도 문제가 없는지 점검한 후 폐기 예정** |
| ✅ **완료 (2026-10-08)** | ~~공개 공지 API~~ | `GET /api/notices` 구현(`app/routers/notices.py`, `main.py` 등록), React `Help` 공지 아코디언, pytest |
| 🟡 **권장 (신규 2026-09-21)** | **React 화면 실제 환경 검증** | 브라우저 화면 비교·모바일 터치·키보드 탐색, 카메라(QR)·GPS·Kakao SDK·CLOVA OCR 동작 확인. 기존 HTML과의 세부 동등성은 미확정<br>**[2026-10-08 방침] 구현·보완 예정(시연·발표 전 처리)** |
| ✅ **완료 (2026-10-08)** | ~~게시글 수정 API 확장~~ | `PATCH /posts/{id}`가 사진·유형·목표 인원·1인 금액 반영(참여자·정산 있으면 유형·인원·가격 409 잠금, 인원 2명 이상·가격 1원 이상 검증, 사진 최대 10장). React `PostForm` 사진 추가/삭제·유형/인원/가격 편집 활성화 |
| 🟡 **권장 (신규 2026-09-21)** | **PWA 전환** | 설치·오프라인 기능 미구현(PWA 전환을 위한 프런트 구조 정비 단계). 반응형 기준은 메인 1080px 중앙 영역·760px 모바일 분기<br>**[2026-10-08 방침] 작업 예정** |
| 🟡 **권장 (신규 2026-10-06)** | **PortOne 테스트 결제 서버 반영·검증** | 코드는 GitHub에 있으나 서버 `git pull`·`.env`(`PORTONE_*`, TEST 채널)·`dist/` 재빌드/업로드·재시작은 미확인. 반영 후 정산 → GPS → QR → 테스트 결제 흐름과 포트원 콘솔 허용 도메인 확인. 시연은 테스트 모드 고정, 모바일 리다이렉트 복귀는 미검증<br>**[2026-10-08 방침] 구현·보완 예정(시연·발표 전 처리)**. 서버 반영·검증을 마친 뒤 팀원 문서 `docs/PORTONE_TEST_SETUP.md`를 함께 갱신 예정 |
| ✅ **완료 (2026-10-08)** | ~~그룹 채팅 거래 액션 바 복원~~ | `trades.tsx`의 `TradeBar`: 방장 약속 정하기/변경(`POST /posts/{id}/appointment`) → 정산 시작/상세 링크 → GPS 인증 → QR 발급/스캔 링크, 진행 현황(GPS·QR 완료 수). **B안(GPS·QR 링크까지 포함)으로 구현** |
| ✅ **완료 (2026-10-08)** | ~~QR 발급 화면 토큰 확인 줄~~ | `qr.tsx` 발급 카드에 토큰 읽기 전용 입력칸·복사 버튼 추가(카메라 스캔이 어려울 때 상대방 스캔 입력칸에 붙여 넣어 인증, 개발자도구 없이 확인). 서버 변경 없음 |
| 🟢 **선택 (신규 2026-10-06)** | **ERD·원고 정합성** | 졸업작품집 ERD 그림은 핵심 18개 테이블(`auth_codes`·결제 테이블 제외). 결제 테이블까지 보이려면 그림 갱신 필요<br>**[2026-10-08 방침] 작업 동기가 그림을 갱신한 뒤 문서에 반영 예정** |

> 완료된 항목(미납 정산 참여 차단, `Admin_Staff_Invite.html` 연동, 관리자 사이드바 배지 동적화)은 §7 "2026-09-12" 절 참고. React 홈 화면 추가 경과는 §7 "2026-09-14" 절, 전체 화면 이전은 §7 "2026-09-20"·"2026-09-21" 절 참고.

---

## 9. 주요 정책 결정 사항

| 항목 | 결정 내용 |
|---|---|
| 게시글 수정 가능 필드 | 서버 `PATCH /posts/{id}`는 제목·설명·카테고리·상태·교환 희망·주소·좌표·**사진·거래 유형·목표 인원·1인 금액**(2026-10-08 확장). 참여자(`gb_current>0` 또는 `groupbuy_participants`)나 진행 중/완료 정산이 있으면 유형·인원·가격은 409로 잠금, 사진·제목 등은 계속 수정 가능. 유형을 공동구매로 바꾸려면 인원(≥2)·가격(≥1) 필수, 공동구매에서 다른 유형으로 바꾸면 gb_* 값 정리 |
| 참여 취소 정책 | 정산 생성(pending/completed) 전까지 취소 허용. 시간 기반 컷오프 없음 |
| 공지 기능 범위 | 즉시 게시·목록·삭제만 연동. 예약 발행·임시저장·푸시 알림은 스키마 미지원으로 보류 |
| 운영진 관리 | 이메일 초대 없이 기존 계정 검색 → `admin` 역할 승격 방식 유지 |
| 전역 401 리다이렉트 | 적용 안 함. 비회원 홈 접근 probe 회귀 방지를 위해 페이지별 `nfRequireMember()` 수동 방식 유지 |
| GPS 인증 반경 | 300m → **100m** (프론트·백 동기화 완료) |
| 비밀번호 변경 | 설계 결정: 현재 세션 유지, 타 기기 세션 일괄 폐기 — ✅ `PATCH /api/users/me/password`로 구현(2026-10-08) |
| 공동구매 참여 취소 | `groupbuy_participants` 삭제 + `gb_current` 원자적 감소 + 그룹챗 `conversation_members` 제거 + 시스템 메시지 삽입 (`is_system=1`) |
| 게시글 삭제 | 소프트삭제 (`status='deleted'`). 거래·채팅 이력 보존 |
| 세션 유효 기간 | `SESSION_TTL_DAYS = 30` (30일) |
| React 프런트엔드 도입 범위 (2026-09-14 → 2026-09-21 갱신) | 2026-09-14 홈 화면 1개만 우선 도입 → 2026-09-20~21 기존 화면 39개 전체 React 이전(구현). Node.js 20+, `npm ci`, 해시 라우팅, Vite 프록시 사용. 기존 정적 HTML은 최종 점검이 끝나기 전까지 유지 |
| 인증 방식(React) | React는 자체 로그인·토큰 처리(`auth.tsx`·`core.tsx`)를 가지며 정적 HTML과 `localStorage`를 공유하지 않음(출처 분리) — 각자 로그인 방식으로 정리 |
| 외부 결제 연동 (2026-10-06 갱신) | **실결제·자동 송금은 미예정**. 2026-10-05 팀원이 PortOne V2 **테스트 채널** 결제만 연동(서버 재검증·TEST 채널만 성공 인정·`portone_*` 테이블). 정산의 납부 표시는 여전히 사용자가 입금 사실을 표시하는 기능이며 결제 승인·자동 송금이 아니고, 테스트 결제는 납부 상태·정산 완료·판매자 지급을 바꾸지 않음. 발표·문서에서는 "테스트 결제"로 표기. LIVE 채널 키는 사용 금지 |
| 배포 방식 (2026-10-06) | Oracle Cloud Micro 1대 + Nginx + Let's Encrypt 유지(Vercel+Supabase 전환은 비권장, `NeighborFood_배포방식_비교_Oracle_vs_Vercel.md`). 체크포인트 1(10/16) 부하테스트로 최종 확정(비교 문서 (저장소 미포함 — 개별 보관)), 미달 시 유료 shape 전환을 D-10~D-7에 착수 |
| 프런트 배포 방식 | 서버에서 `npm run build` 금지(1GB 메모리). PC에서 빌드한 `dist/`를 업로드하고 FastAPI가 서빙. 같은 도메인이라 `VITE_API_BASE_URL`은 비워 둠 |
| 업로드 이미지 저장 | 서버 디스크 `uploads/`에 저장하고 DB에는 파일명만 저장. 백업·이전 시 `data/`와 `uploads/`를 함께 처리 |
| 서버 노출 범위 | 앱은 `127.0.0.1:8000`에만 바인딩, 외부는 Nginx(80/443)만. 방화벽은 OCI Security List + 서버 iptables 이중 |
| 비밀 정보 취급 | 비밀번호·API 키·OCID·개인키 경로·실제 IP·DuckDNS token·PortOne 시크릿은 문서·채팅에 적지 않고 서버 `.env`에만 둠 |

---

## 10. 개발 환경 명령어

```bash
# 서버 실행
uvicorn main:app --reload

# 프론트엔드 접근 (localStorage 공유를 위해 동일 출처 사용)
http://127.0.0.1:8000/frontend/<파일>.html

# 카메라 사용 화면 (QR·영수증 — HTTPS 또는 localhost 필요)
http://127.0.0.1:8000/QR_Scan.html
http://127.0.0.1:8000/Receipt_Verify.html

# API 문서
http://127.0.0.1:8000/docs

# 더미 데이터
python seed_posts.py                  # ⚠️ 2026-09-08 기준 저장소에 미존재 (아래 안내 참고)

# 관리자 계정 생성/승격 [2026-09-12 복원 완료]
python seed_admin.py                  # 신규 생성 (login_id=Admin, pw=admin0000)
python seed_admin.py <login_id>       # 기존 계정을 admin 역할로 승격

# 테스트 계정 시드 (정산 수동 테스트용)
python Seed_Account.py               # ⚠️ 2026-09-08 기준 저장소에 미존재
python Seed_capstone_settlement.py   # ⚠️ 2026-09-08 기준 저장소에 미존재

# 자동 기능 테스트 (정산 포함 전체 흐름) — ⚠️ 2026-09-08 기준 저장소에 미존재, §3 정합성 안내 참고
python nf_functional_test.py

# DB 초기화 (전체 데이터 삭제 + Admin 재생성) — [2026-09-19 존재 확인] ⚠️ 전 데이터 삭제, 서버 종료 후 실행
python reset_db.py                    # 확인 프롬프트 표시
python reset_db.py --yes              # 확인 생략
python reset_db.py --pw <비밀번호>     # Admin 비밀번호 지정 (기본 admin0000)

# 영수증 파서 회귀 테스트 [신규] — (PortOne 테스트 `tests/test_portone.py`와 함께 현재 저장소에 존재하는 자동화 테스트)
python tests/test_receipt_parser_v212.py

# API 자동화 테스트 [신규 2026-10-08] — 임시 DB 사용(실제 data/neighborfood.db 미변경). pip install pytest httpx
python -m pytest tests -q
```

> 위 명령 중 더미 데이터·테스트 시드·전체 기능 테스트(4개 스크립트)는 대응 스크립트가 저장소에서 제거되어 현재 실행되지 않습니다. `reset_db.py`(DB 초기화)는 2026-09-19 존재를 확인했습니다. §3의 "문서-저장소 정합성 안내" 참고. `seed_admin.py`는 2026-09-12 복원되어 정상 동작합니다.

**React(Vite) 프런트엔드 [2026-09-14 신규 → 2026-09-20~21 전체 이전] — `frontend-react/`:**

```bash
# 최초 1회 (lockfile 기준 재현성 보장 — 오류 시에만 npm install 사용)
cd frontend-react
npm ci

# 개발 서버 실행 (백엔드 uvicorn(8000)이 먼저 실행되어 있어야 함)
npm run dev                # http://localhost:5173 (Vite 기본 포트) — 화면은 /#/화면명 해시 경로 (예: /#/Fridge)

# API 프록시 대상 변경 / 공개 API 주소 직접 지정 (선택)
# NEIGHBORFOOD_BACKEND=http://127.0.0.1:8000  (Vite 프록시 대상, 환경변수)
# VITE_API_BASE_URL=...                       (frontend-react/.env.local — Git에 올라가지 않음)

# 빌드 / 린트 / 프리뷰
npm run build               # tsc -b && vite build
npm run lint                # oxlint
npm run preview             # 빌드 결과 로컬 프리뷰 (API 프록시 포함)
```

> React(`localhost:5173`)와 정적 HTML(`127.0.0.1:8000`)은 접속 출처가 달라 로그인 상태가 공유되지 않으므로 React에서 별도 로그인합니다. 카메라(QR)·GPS 화면은 HTTPS 또는 localhost에서만 동작합니다.


**테스트 계정 기본값:**

| 계정 | login_id | password | 역할 |
|---|---|---|---|
| 관리자 | `Admin` | `admin0000` | admin |
| 일반1 | `Capstone_1` | `capstone1` | user |
| 일반2 | `Capstone_2` | `capstone2` | user |
| 일반3 | `Capstone_3` | `capstone3` | user |

---

## 11. 범위 외 항목 (Excluded)

- 유통기한 임박 추천 / 레시피 추천 / 식재료 객체 인식
- 오프라인 모드 / 실시간 WebSocket 채팅 (현재 REST 4초 폴링)
- 이메일 초대 기반 운영진 관리 (현재 계정 승격 방식)
- 공지 예약 발행 / 임시저장 / 푸시 알림
- 실제 결제 / 외부 송금 연동 (기본 미예정 — 여유가 있을 경우에 한해 추가 검토, 현재 정산은 사용자 납부 표시 방식)

## 12. 금지 항목 (Prohibited)

- 식품 소분 판매 UI
- 포장 훼손 거래 UI