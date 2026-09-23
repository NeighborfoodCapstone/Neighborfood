# Role: Senior Full-stack Engineer Assistant
당신은 '1인 가구 지역 식재료 공동구매 플랫폼(NeighborFood)' 프로젝트의 전담 개발자입니다. 아래의 컨텍스트와 제약 사항을 완벽히 숙지하고 개발을 수행하십시오.
 
> 최종 갱신: 2026-09-21 · React 전체 화면 이전·공통 디자인·로딩·자동완성 반영(아래 참고). 이전 갱신: 2026-09-19 문서-소스 정합성 점검. 이전 주요 갱신: 2026-08-12 · UX 갭 감사·해소 완료 (관리자 연동·참여 취소·게시글 수정·공지 표시·매너 평가 리다이렉트)
> 2026-09-08 문서-저장소 정합성 검토: `seed_admin.py`·`seed_posts.py`·`posts.json`이 실제 저장소에 더 이상 존재하지 않는 것으로 확인됨 (아래 §4 "문서-저장소 정합성 안내" 참고). `frontend/vendor/html5-qrcode.min.js`, `tests/test_receipt_parser_v212.py` 신규 반영. 정산 API 개수 오기재(9종→13종) 2곳 정정, "## Included" 목록의 자기모순(이미 완료된 매너평가·참여취소 흐름이 잔여로 중복 기재) 정정.
> 2026-09-12 관리자 기능 실데이터 연동 완료: `seed_admin.py` 복원, `adminGuard.js` 신설, `Admin_Users.html`·`Admin_Report_Detail.html`·`Admin_Staff_Invite.html`·`Admin_Dashboard.html` 전면 실연동, 미납 정산 참여 차단 리팩터링, 주최자 귀책/먹튀 trust_score 자동 페널티, 회원 직접 신고 진입점 신설.
> 2026-09-19 문서-소스 정합성 점검: 루트 스크립트 중 `reset_db.py`가 저장소에 존재함을 확인하고 트리·§6 Commands에 반영, 트리의 문서 파일명 오타(`Cpastone.md`→`Capstone.md`) 정정, `Neighborfood_React_실행_안내.md` 추가 반영. 코드 변경 없음.
> 2026-09-14 `frontend-react/` 신규 추가: Vite 8 + React 19 + TypeScript 기반 홈 화면 부분 마이그레이션 시작(기존 정적 HTML `frontend/`와 병행 운영하는 하이브리드 구조). 신규 백엔드 API 없음 — 기존 `GET /posts` 재사용. 상세는 아래 §2·§4·§6 참고.
> 2026-09-20~21 React 전체 화면 이전: `frontend-react/`에 기존 HTML 39개 화면 식별자를 React(TypeScript)로 이전(`src/migration/`), 공통 디자인·로딩·자동완성·게시글 상세 개선 적용, 2026-09-21 GitHub 반영. 백엔드·DB·기존 HTML은 변경 없이 병행 보존. 문서 정정: 공개 공지 API(`GET /api/notices`)는 코드에 없음, 게시글 수정 API는 인원·가격을 반영하지 않음. 상세는 아래 §1·§2·§4·§5·§6 및 `frontend-react/docs/` 참고.
 
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
- 관리자 기능(`/api/admin/*`, `notices`·`reports`, 6종 화면 실데이터 연동 완료 2026-09-12) + `seed_admin.py`(계정 부트스트랩, 2026-09-12 복원)
- 신고(`reports` + `POST /api/reports` → 관리자 처리)
- 배포 대응: 전 화면 `API_BASE`=`window.location.origin`(상대경로), `tokens.css` 전체 39개 화면 적용 완료
- GPS 위치 인증(`location_verify_sessions` + `/api/location-verify/*`, 더미 타겟 생성·GPS 반경 체크·QR 연동) — `Local_Verify_Demo.html`
- 공동구매 참여 레이스 컨디션 수정 — `posts.py`에서 원자적 UPDATE로 전환 (2026-07-09)
- `neighborfood_schema.sql` 동기화 — 코드에만 있던 6개 테이블(`wishlists`·`conversations`·`conversation_members`·`messages`·`notices`·`reports`) DDL 반영, 스키마 파일=코드 완전 일치 (2026-07-09)
- **카카오맵 키 하드코딩 전면 제거** — 전 화면(`Map` + 잔여 6개 화면)이 `/api/config/kakao-key` 동적 로드로 전환, 소스 내 실키 완전 소거 (2026-08-03)
- **GPS 위치 인증 보안 강화 + 실흐름 연결** — 전 API Bearer 인증 필수, `subject_id` 서버 강제 고정, 소유자 검증(`_assert_owner`), 이력 본인 필터, QR 인증 성공 시 `QR_VERIFIED` 연동 실호출, `Local_Verify_Demo.html` 로그인 가드, `Reservation.html` 진입점 연결 (2026-08-03)
- **수령 장소 지정** — `Reservation.html`이 게시글의 실제 `address`/`lat`/`lng`를 장소 카드·지도 링크·신청 요약에 반영, 주소 미등록 시 "채팅으로 협의" 폴백 (2026-08-03)
- **정산 시스템** — `settlements` + `settlement_shares` 테이블, `/api/settlements/*` API 13종(약속·GPS·QR·노쇼 취소 `DELETE` 포함, 2026-08-04 최초 9종에서 2026-08-06~07 확장), `Settlement.html` 실데이터 연동, `Group_Buy_Detail.html`·`Transaction_History.html` 진입점 추가 (2026-08-04)
- **전체 흐름 완성(채팅→정산→매너평가)** (2026-08-07):
  - `posts` 테이블에 `appointment_place/at/lat/lng` 4개 컬럼 추가 (`auth_db.py` 멱등 마이그레이션 포함)
  - `POST /posts/{id}/appointment` 신규 — 정산 없이 채팅 단계에서 약속 확정 가능, 정산 생성 시 자동 승계
  - GPS 반경 300m → **100m** 통일 (`location_verify_db.py`, `location_verify.py`, `Local_Verify_Demo.html`)
  - GPS self-referencing 버그 수정 — 약속 좌표를 target으로 사용, 서버 Haversine 재검증 (`verify_participant_gps`)
  - `Group_Chat.html`: "정산 시작하기" 버튼, 약속 모달 GPS 좌표 캡처·프리필, PWA `isSecureContext` 체크
  - `Settlement.html`: "QR 스캔" 안내, "매너 평가 남기기" 완료 버튼, `/api/posts/`→`/posts/` 경로 버그 수정
  - `Local_Verify_Demo.html`: 약속 좌표 자동 로드(`nfLoadAppointmentTarget`), PWA 체크
  - `My_Activity.html`: 완료 거래 "매너 평가하기" + 평가 모달 + `trust_score` 반영
- **UX 갭 감사·해소 + 버그 수정** (2026-08-12):
  - `Admin_Notices.html`: 공지 목록·작성·삭제 API 실연동, 예약·푸시는 "준비 중" 안내, 사이드바 로그아웃
  - `Admin_Chat_History.html`: 대화방 목록·메시지 실연동, 정적 더미 제거
  - `Group_Buy_Detail.html`: 참여/취소 버튼 토글 (`GET /posts/{id}/my-status`), 취소 시 `DELETE .../join` 연동, 작성자 3-dot 드롭다운 메뉴 (수정·삭제), 취소 버튼 스타일 수정 (Tailwind `error` 색 미정의 → `style.cssText` 인라인 직접 지정)
  - `Settlement.html`: 완료 후 "매너 평가 남기기" → `My_Activity.html?tab=history` 리다이렉트
  - `Help.html`: `GET /api/notices?limit=10` 공개 공지 아코디언 표시 (비회원 포함) — ⚠️ 2026-09-21 정정: 공개 공지 API는 코드에 없음(관리자 전용 `/api/admin/notices`만 존재)
  - `Create_Post.html` + `My_Activity.html`: 게시글 수정 흐름 (`?edit={id}` 프리필, `PATCH /posts/{id}`, 참여자 있는 공구 인원·가격 잠금) — ⚠️ 2026-09-21 정정: 서버 `PATCH /posts/{id}`는 인원·가격·사진·거래 유형을 반영하지 않음(제목·설명·카테고리·상태·교환 희망·주소·좌표만)
  - `posts.py`: `list_posts()` 진입 시 만료 글 일괄 `expired` 전환, `cancel_join_groupbuy`에 그룹챗 퇴장 + `messages.is_system` 시스템 메시지 삽입 추가
  - `neighborfood_schema.sql` · `neighborfood_ERD.md`: `messages.is_system` 컬럼 동기화
- **React(Vite) 홈 화면 부분 마이그레이션 시작** (2026-09-14 — ⚠️ 이후 2026-09-20 전체 이전으로 확장, 아래 두 항목이 현행 기준):
  - `frontend-react/` 워크스페이스 신규 추가 — Vite 8 + React 19 + TypeScript, 린터는 ESLint 대신 Oxlint 사용
  - `HomePage.tsx` — 카테고리 필터·검색·게시글 카드 그리드로 기존 `Home.html`의 피드 화면을 재구현, `GET /posts`를 그대로 재사용(신규 API 없음)
  - `AppLayout.tsx` — 헤더 + 하단 네비게이션(홈/지도/등록/내 활동/마이) 공통 레이아웃
  - `api.ts` — `legacy(page)` 헬퍼로 지도·등록·내 활동·마이페이지·게시글 상세 등 나머지 화면을 기존 정적 HTML(`frontend/*.html`)로 하드 네비게이션. 백엔드 주소는 `VITE_API_BASE_URL` 환경변수(기본값 `http://127.0.0.1:8000`)로 지정
  - 정적 HTML 프런트엔드(`frontend/`)는 그대로 유지 — **두 프런트엔드가 병행 운영되는 하이브리드 구조** (2026-09-20 갱신: 전체 화면 이전 구현 완료, 아래 참고)
- **React 전체 화면 이전** (2026-09-20, 신규):
  - 기존 HTML 39개 화면 식별자를 React 경로로 매핑 — 인증(`auth.tsx`), 게시글·검색·찜·상세·등록·거래 신청·신고(`posts.tsx`), 냉장고(`fridge.tsx`), 채팅·내 활동·거래 내역·정산(`trades.tsx`), 지도·동네·GPS 인증(`location.tsx`), QR(`qr.tsx`), 영수증(`receipt.tsx`), 관리자(`admin.tsx`), 화면 목록·라우팅·접근 제어·도움말(`routes.tsx`). 39개 화면이 39개의 독립 TSX 파일은 아니며 같은 그룹은 컴포넌트·props를 공유
  - 공통 API 요청·인증 토큰·오류 처리는 `src/migration/core.tsx`, 공통 스타일은 `design.css`. 화면 이동은 해시 경로(`/#/Fridge`, `/#/Product_Detail?id=1`)
  - FastAPI·SQLite·기존 HTML은 변경하지 않음. Vite 개발/preview 프록시가 `/api`·`/posts`·`/uploads` 등을 FastAPI(8000)로 전달(`NEIGHBORFOOD_BACKEND`로 변경 가능), `VITE_API_BASE_URL` 지정 시 공개 API 주소를 직접 사용. QR 생성·스캔용 `qrcode`·`jsqr` 의존성 추가
  - 검증: TypeScript·Vite 프로덕션 빌드 통과, 별도 테스트 DB에서 로그인·냉장고·게시글 등록·공동구매 참여·그룹 채팅·정산(생성→약속→GPS→QR→납부 표시→완료)·거래 상태·평가·찜 API 흐름과 관리자 접근 차단을 자동 확인. 실제 브라우저 화면·모바일·카메라·위치 정확도·Kakao SDK·CLOVA OCR은 미검증
  - 이전 시 제한: 게시글 수정 API 제약으로 사진·거래 유형·목표 인원·1인 금액 편집 제한, 공개 공지 API 부재로 관리자 공지를 일반 회원 화면에 미노출, Verify는 별도 OTP 성공 페이지 대신 비밀번호 재설정 흐름 공유, Splash·Onboarding은 진입 링크로 정리, 미구현 안내(자동 환불 등)는 도움말로 옮기지 않음. 정산의 납부 표시는 결제 승인·자동 송금이 아님
- **공통 디자인·로딩·자동완성·게시글 상세 보강 + GitHub 반영** (2026-09-21, 신규):
  - 승인된 메인 화면 디자인을 기준으로 색·버튼·입력·목록을 공통화(`frontend-react/docs/DESIGN_CONTEXT.md`), 홍보 문구·가짜 추천·가짜 통계·미연결 위젯을 추가하지 않는 기준 유지
  - 화면 전환·최초 조회 공통 로딩(`loading.tsx`, 백그라운드 재조회는 기존 내용 유지), 검색·회원 검색·주소 검색 공통 자동완성(`autocomplete.tsx` — 250ms 디바운스·최대 8개·이전 요청 취소·한글 조합 처리·방향키/Enter/Esc), 게시글 상세 사진 갤러리(`PostGallery.tsx`)와 데스크톱 2열·모바일 1열 배치
  - GitHub main 반영: 커밋 `9df3688`(24개 파일). PWA 설치·오프라인 기능은 미구현(PWA 전환을 위한 프런트 구조 정비)
미완료(잔여):
- 작성자 매너 평가 표시 — `Product_Detail.html`·`Group_Buy_Detail.html` 작성자 카드에 `GET /api/ratings/received?user_id={authorId}` 연동 (API 완비)
- `frontend-react/README.md` 교체 — 현재 Vite 기본 템플릿 문서 그대로이며 프로젝트 설명(실행 방법·구조)으로 교체 필요 (선택: 공개 API 주소를 직접 쓸 경우에만 `VITE_API_BASE_URL` 템플릿 항목 추가)
- 공개 공지 API 미구현 — 문서에 있던 `GET /api/notices`는 코드에 없음(관리자 전용 `/api/admin/notices`만 존재). `Help.html` 공지 목록이 표시되지 않으며 React 화면도 관리자 공지를 일반 회원에게 노출하지 않음
- React 화면 실제 환경 검증 — 브라우저 화면·모바일 터치·키보드 탐색, 카메라(QR)·GPS·Kakao SDK·CLOVA OCR
- 게시글 수정 API 확장 여부 — 사진·거래 유형·목표 인원·1인 금액 수정 불가(React 편집 제한 중)
- PWA 전환 — 설치·오프라인 기능 미구현
- 정적 HTML(`frontend/`) 최종 처리 — 최종 점검이 끝나기 전까지 유지, 이후 처리 방식과 정식 배포 서빙 방식 결정 필요
완료로 전환된 기존 잔여 항목:
- ~~상호 매너 평가~~ → ✅ `ratings.py` + `manner_ratings` 테이블 + `trust_score` 원자적 UPDATE 구현 완료 (2026-08 이전)
- ~~공동구매 참여 취소 흐름~~ → ✅ `DELETE /posts/{id}/join` (백엔드), 프론트 토글·시스템 메시지 모두 완료 (2026-08-12)
- ~~`posts.py` `join_groupbuy` 미납 정산 참여 차단~~ → ✅ `settlement_db.has_unpaid_settlement()` 호출로 리팩터링 완료 (2026-09-12)
- ~~`Admin_Staff_Invite.html` 운영진 관리 연동~~ → ✅ 회원 검색→승격/권한 해제 UI로 재설계 완료 (2026-09-12)
- ~~관리자 사이드바 신고 배지 동적화~~ → ✅ `adminGuard.js` 공용 가드로 전 페이지 실데이터 반영 완료 (2026-09-12)
주의:
- 기존 구조 유지
- 최소 수정 원칙
- 전체 리팩토링 금지
잠재 이슈 (알려진 위험):
- (해결됨) **공동구매 인원 정합성**: `posts.py`의 `join_groupbuy`가 `SET gb_current = gb_current + 1 WHERE ... AND gb_current < gb_target` 원자적 UPDATE로 전환 완료(2026-07-09). 단, 참여 취소(cancel) 흐름은 아직 미정의.
- (해결됨) **trust_score 레이스**: `ratings.py`에서 `SET trust_score = MIN(99, MAX(0, trust_score + ?))` 원자적 UPDATE 적용 완료. 매너 평가 기능 자체도 구현 완료.
- **SQLite 동시성**: 채팅 폴링(4초) + 정산·평가 쓰기 경합 시 `database is locked` 드물게 발생 가능. WAL + `busy_timeout`으로 완화 중.
- **배포 보안**: 도메인 제한·토큰 취급 정책은 시연/개발 수준. `main.py`가 `.env`의 `ALLOWED_ORIGINS`로 CORS를 동적 분기하도록 준비 완료(2026-09-12, 미설정 시 `*` 유지) — **배포 시 실제 도메인 값 입력 필요**(2026-09-14: `frontend-react/`가 서빙되는 도메인도 함께 추가해야 함. 2026-09-21: 정적 빌드(`dist`) 배포 시에는 Vite 프록시가 없으므로 같은 API 프록시를 배포 서버에 구성하거나 `VITE_API_BASE_URL`로 공개 API 주소를 지정해야 함). `seed_admin.py` 기본 비밀번호(`admin0000`)도 배포 전 변경 권장.
- **OCR 환경 의존**: 실제 OCR 구동을 위해 서버에 `tesseract` 설치 필요. 미설치 시 데모 폴백.
- (해결됨) **Kakao 키 하드코딩**: 전 화면 `/api/config/kakao-key` 동적 로드로 전환 완료(2026-08-03). 단, 이미 노출된 이력이 있는 키라면 GitHub 공개 전 카카오 개발자 콘솔에서 키 재발급 권장.
- (해결됨) **GPS 위치 인증 무인증 공개**: 전 API 인증 필수 + 소유자 검증 + 이력 본인 필터로 전환 완료(2026-08-03).
- (해결됨) **GPS self-referencing 버그**: 기존엔 참여자가 자신의 현재 위치를 target으로 만들어 항상 통과됐으나, 2026-08-07 수정으로 주최자 약속 좌표를 target으로 고정하고 서버 Haversine 재검증(≤100m)으로 전환 완료.
- (해결됨) 관리자 계정 생성 → `seed_admin.py`: `python seed_admin.py`(admin 생성) / `python seed_admin.py <login_id>`(기존 계정 승격). 전화번호 충돌 시 명확한 에러 메시지, 재실행해도 안전(멱등). 2026-09-12 복원 및 테스트 완료.
- **프런트엔드 이원화 (2026-09-14 신규, 2026-09-21 갱신)**: `frontend/`(정적 HTML)와 `frontend-react/`(React, 화면 39개 이전)가 병행 보존됨. React는 자체 로그인(`auth.tsx`)과 토큰 처리(`core.tsx`)를 가지며, 두 프런트엔드는 접속 출처가 달라 `localStorage` 토큰이 공유되지 않으므로 React에서 별도 로그인이 필요함(인증 공유 문제는 각자 로그인 방식으로 정리). 정적 HTML은 최종 점검 전까지 유지하며 이후 처리 방식은 미결정.
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
* **Goal:** 지역 기반 식재료 공동구매 웹앱. **단일 FastAPI 백엔드 + 단일 SQLite** 구성, 프론트엔드는 정적 HTML(Tailwind)과 React(Vite) 화면 39개 이전본이 병행. (2026-09-14: `frontend-react/` 홈 화면 추가 → 2026-09-20~21: 화면 39개 전체 이전, 백엔드·DB 구성 원칙은 변경 없음)
* **Compliance:** 식품위생법 준수(소분 판매 금지, 완제품/원형 농산물 거래만 허용).
* **Strict Constraint:**
    1. 백엔드는 **단일 FastAPI 서버**로 운영한다. (Spring Boot/MySQL 분리 계획은 폐기됨)
    2. 데이터베이스는 **단일 SQLite 파일(`data/neighborfood.db`)**을 사용한다. (MariaDB 통합 계획은 폐기됨)
    3. AI 처리는 OCR(영수증) 등 경량 기능으로 한정한다. (추천/객체 인식 파이프라인 금지)
    4. 'Immutable Paths'에 명시된 구조와 핵심 로직은 가능한 한 유지한다.
    5. 하드코딩 금지 (`.env` 사용).
    6. 비동기 처리 강제 (UI 블로킹 금지).
> 참고: 초기 기획의 Next.js / Spring Boot / MySQL / Redis / S3 다중 스택은 캡스톤 범위에 맞춰 **단일 FastAPI + SQLite**로 단순화되었습니다. 기존 프론트엔드는 정적 HTML + Tailwind(CDN)로 작성되고 FastAPI가 함께 서빙합니다. (2026-09-20~21: `frontend-react/`(Vite + React 19 SPA)로 기존 화면 39개를 전체 이전(구현)했으며, 기존 정적 HTML(`frontend/`)은 최종 점검이 끝나기 전까지 삭제하지 않고 병행 보존합니다.)
 
---
# 2. Tech Stack
* **Frontend:** 정적 HTML + Tailwind CSS (CDN). FastAPI `/frontend` 또는 Live Server로 서빙. 공통 JS는 `frontend/shared/`.
* **Frontend(React, 2026-09-14 신규 → 2026-09-20~21 전체 이전):** `frontend-react/` — Vite 8 + React 19 + TypeScript, 린터는 Oxlint(ESLint 대체), Node.js 20 이상 필요. 기존 화면 39개를 해시 라우팅(`/#/화면명`)으로 이전했으며 정적 HTML(`frontend/`)과 병행 보존. 의존성 설치는 `npm ci`(lockfile 기준, QR 생성·스캔용 `qrcode`·`jsqr` 포함). 개발/preview 서버가 `/api`·`/posts`·`/uploads` 등을 FastAPI(8000)로 프록시(`NEIGHBORFOOD_BACKEND`로 변경 가능)하며, 공개 API 주소를 직접 쓰려면 `VITE_API_BASE_URL` 지정. 신규 백엔드 API 없음. 공통 디자인 기준은 `frontend-react/docs/DESIGN_CONTEXT.md`.
* **Backend:** FastAPI (Python 3.10+), 3-Tier 모듈 구조(`app/config·core·db·models·routers`).
* **Database:** SQLite 3 단일 파일 `data/neighborfood.db` (외래키 활성화, WAL).
* **Auth:** **ID/비밀번호 가입·로그인**(가입 시 휴대폰 번호 입력만 받고 OTP 검증 없음) → 세션 토큰(Bearer) 발급. OTP는 **비밀번호 재설정에만** 사용. 비밀번호는 표준 라이브러리 PBKDF2-SHA256(`salt$hash`)으로 저장. 인가는 `app/core/deps.py` 의존성, 프런트는 `shared/auth.js`(토큰 보관·주입) + `shared/guard.js`(회원 전용 페이지 가드).
* **접근 정책:** 비회원은 **게시판(목록·상세)과 지도(Map)만** 이용 가능. 글 작성·거래·채팅·찜·내 활동·마이페이지·동네 인증은 회원 전용. 역할은 비회원/회원/관리자 3단계. 관리자 기능은 `get_current_admin` 가드의 `/api/admin/*`로 구현되어 있으며, admin 계정은 `seed_admin.py`로 생성/승격한다 (2026-09-12 복원).
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
* **TypeScript(`frontend-react/`, 신규 2026-09-14):** 컴포넌트 파일은 PascalCase(`.tsx`), 유틸/타입 전용 파일은 camelCase(`.ts`). 함수형 컴포넌트 + Hooks만 사용, 클래스 컴포넌트 금지. 린트는 Oxlint(`npm run lint`)로 수행하며 `react/rules-of-hooks`는 error 레벨 유지. (2026-09-21: 화면 모듈은 `src/migration/`에 두고 API 요청·인증·오류 처리는 `core.tsx`를 공유, 공통 스타일은 `design.css`, iframe·HTML 문자열 주입·기존 script 실행 래퍼로 화면을 대체하지 않음)
---
# 4. Immutable Paths (주의)
아래 파일 및 구조는 가능한 한 유지한다.
- 대규모 리팩토링 금지
- 파일명/구조 변경 금지
- 기존 핵심 로직 삭제 금지
단, 버그 수정, 기능 추가, 최소 수정(minimal diff)은 허용한다. 명시적 요청 없이 전체 구조 변경을 수행하지 않는다.
 
**실제 디렉토리 구조** (`app`=서버 / `frontend`=정적 화면·JS / `frontend-react`=React(Vite) 화면 [2026-09-20~21 전체 이전] / `sql`=스키마 / `data`=실제 DB)
 
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
│   │   ├── transaction_db.py      transactions·groupbuy_participants·settlements·settlement_shares
│   │   ├── settlement_db.py       settlements·settlement_shares CRUD (신규 2026-08-04)
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
│                    ratings.py  settlements.py  (신규 2026-08-04)
├── frontend/                    ▶ 정적 HTML 페이지 + JS 파일
│   ├── *.html                     사용자/관리자 화면 (Home·Verify·Create_Post·QR_Scan·Local_Verify_Demo·Admin_* 등)
│   │   (인증 흐름) Splash · Onboarding · Login · Signup · Password_Reset (.html)
│   ├── shared/                    공통 JS/CSS
│   │   ├── auth.js                토큰 저장(localStorage) + fetch 자동 인증 주입
│   │   ├── guard.js               회원 전용 페이지 가드 (nfRequireMember())
│   │   ├── adminGuard.js          관리자 전용 페이지 가드 (nfRequireAdmin(), 신규 2026-09-12)
│   │   ├── profile.js             프로필/탈퇴 호출 헬퍼
│   │   └── tokens.css             디자인 토큰(CSS 변수)
│   └── vendor/                    외부 라이브러리 로컬 사본 [신규]
│       └── html5-qrcode.min.js    QR/바코드 스캔 — CDN 장애 대비 1차 로드 경로
├── frontend-react/              ▶ React(Vite) 화면 39개 전체 이전 [2026-09-20~21] — 정적 HTML은 병행 보존
│   ├── docs/                      DESIGN_CONTEXT.md(공통 디자인·로딩·자동완성 기준) · MIGRATION_REPORT.md(화면 매핑·검증 범위)
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── assets/                hero.png · react.svg · vite.svg
│   │   ├── neighborfood/          승인된 메인(홈) 화면·공통 레이아웃
│   │   │   ├── api.ts              백엔드 주소(VITE_API_BASE_URL, 미설정 시 상대경로+Vite 프록시)·getPosts()·legacy()(#/화면명)
│   │   │   ├── AppLayout.tsx       헤더 + 하단 네비게이션 공통 레이아웃
│   │   │   ├── HomePage.tsx        홈 피드 (카테고리·검색·게시글 카드, GET /posts 연동)
│   │   │   ├── home.css            HomePage 전용 스타일
│   │   │   └── Icon.tsx            인라인 SVG 아이콘 컴포넌트
│   │   ├── migration/             나머지 화면 React 모듈 [2026-09-20~21]
│   │   │   ├── routes.tsx · core.tsx · design.css · loading.tsx · autocomplete.tsx · PostGallery.tsx   (라우팅·접근 제어 / 공통 요청·인증 / 공통 스타일 / 로딩 / 자동완성 / 상세 갤러리)
│   │   │   └── auth.tsx · posts.tsx · fridge.tsx · trades.tsx · location.tsx · qr.tsx · receipt.tsx · admin.tsx   (화면 그룹별 모듈)
│   │   ├── App.css  App.tsx(해시 라우팅+AppLayout+접근 가드)  index.css  main.tsx
│   ├── index.html                 Vite 진입 HTML (#root, /src/main.tsx 로드)
│   ├── package.json  package-lock.json   react/react-dom 19.2, qrcode, jsqr / devDeps: vite 8·typescript·oxlint 등
│   ├── tsconfig.json  tsconfig.app.json  tsconfig.node.json
│   ├── vite.config.ts             @vitejs/plugin-react + 개발/preview API 프록시(NEIGHBORFOOD_BACKEND)
│   ├── .oxlintrc.json             Oxlint 설정 (ESLint 대체)
│   └── README.md                  ⚠️ Vite 템플릿 기본 문서 — 아직 프로젝트 설명으로 미교체

├── sql/                         ▶ 현재 프로젝트 스키마
│   └── neighborfood_schema.sql
├── tests/                       ▶ 자동화 테스트 [신규]
│   └── test_receipt_parser_v212.py  영수증 파서 v2.1.2 회귀 테스트 (pytest 없이 단독 실행)
├── data/                        ▶ 실제 데이터베이스
│   └── neighborfood.db            단일 SQLite (startup 자동 생성, gitignore)
├── uploads/                     업로드 이미지 (gitignore)
├── venv/  .venv/  .vscode/  __pycache__/  node_modules/(frontend-react 전용)
├── main.py                      FastAPI 엔트리포인트 (미들웨어·마운트·라우터 등록)
├── seed_admin.py                관리자 계정 생성/승격 (2026-09-12 복원)
├── reset_db.py                  DB 초기화 — 전체 데이터 삭제 + Admin 재생성 (2026-09-19 존재 확인)
├── Capstone.md  NeighborFood_Architecture_Plan.md  neighborfood_ERD.md  README.md  Settlement_Implementation_Plan.md
├── Neighborfood_React_실행_안내.md   백엔드 + React 로컬 실행 안내서
├── requirements.txt
└── .env  .env.example  .gitignore
```
 
> ⚠️ **문서-저장소 정합성 안내 (2026-09-08 확인, README.md·NeighborFood_Architecture_Plan.md와 동일 사안)**
> 이전 버전 트리에는 `seed_admin.py`(관리자 계정 부트스트랩), `seed_posts.py`(더미 게시글 시드), `posts.json`(초기 게시글 시드 데이터) 3개 파일이 있었으나, 저장소 최신 구조 확인 결과 더 이상 존재하지 않아 제거함.
> **2026-09-12 갱신**: 이 중 `seed_admin.py`는 복원되어 정상 동작합니다(위 "잠재 이슈"·"현재 완료"·"접근 정책" 항목 갱신됨). `seed_posts.py`·`posts.json`은 여전히 저장소에 존재하지 않습니다.
> **2026-09-19 갱신**: 루트의 `reset_db.py`(DB 초기화)는 저장소에 존재합니다(위 트리 참고). 이 안내문의 삭제 대상 파일은 `seed_posts.py`·`posts.json`(및 README.md에 나열된 시드/테스트 스크립트)입니다.
> **2026-09-14 갱신**: `frontend-react/` 워크스페이스가 신규 추가되었습니다(홈 화면 부분 마이그레이션).
> **2026-09-21 갱신**: `frontend-react/`가 기존 HTML 39개 화면 식별자를 모두 React로 이전한 상태입니다(구현 완료, 실제 환경 검증 진행 중). `.env.example`의 `VITE_API_BASE_URL`은 미설정 시 상대경로+Vite 프록시를 쓰므로 선택 항목이며, `frontend-react/README.md`는 Vite 기본 템플릿 그대로입니다 — 후속 정리 필요(상단 "미완료(잔여)" 참고).
 
**핵심 파일 (변경 주의)**
* **엔트리포인트:** `main.py` (앱 생성·미들웨어·정적 마운트·라우터 등록 전담)
* **설정/공통:** `app/config.py`, `app/core/utils.py`, `app/core/deps.py`
* **DB 레이어:** `app/db/base.py`, `auth_db.py`, `transaction_db.py`, `settlement_db.py`, `member_db.py`, `fridge_db.py`, `admin_db.py`, `qr_db.py`, `receipt_db.py`, `location_verify_db.py`
* **스키마 정의:** `sql/neighborfood_schema.sql` (단일 진실 소스), 산출물 `data/neighborfood.db`
* **모델:** `app/models/auth.py`, `user.py`, `post.py`, `qr.py`, `receipt.py`, `member.py`, `fridge.py`
* **라우터:** `app/routers/auth.py`, `users.py`, `posts.py`, `qr.py`, `receipt.py`, `wishlist.py`, `chat.py`, `transactions.py`, `fridge.py`, `admin.py`, `reports.py`, `location_verify.py`, `ratings.py`, `settlements.py`
* **프런트 공통(정적 HTML):** `frontend/shared/auth.js`, `frontend/shared/guard.js`, `frontend/shared/adminGuard.js`(관리자 가드, 신규 2026-09-12), `frontend/shared/profile.js`, `frontend/shared/tokens.css`
* **프런트 공통(React, 2026-09-14 신규 → 2026-09-20~21 확장):** `frontend-react/src/neighborfood/`(`api.ts` 백엔드 연동·`legacy()` 해시 경로, `AppLayout.tsx` 공통 레이아웃, `HomePage.tsx` 홈 피드, `Icon.tsx`), `frontend-react/src/migration/`(`routes.tsx` 라우팅·접근 제어, `core.tsx` 공통 요청·인증, `design.css` 공통 스타일, `loading.tsx`, `autocomplete.tsx`, `PostGallery.tsx`와 화면 모듈)
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
- 관리자 계정 부트스트랩 `seed_admin.py` (2026-09-12 복원), 전 화면 상대경로 `API_BASE` 적용
- 신고(`reports` + `POST /api/reports` → 관리자 처리) 구현 완료
- GPS 위치 인증(`location_verify_sessions` + `/api/location-verify/*`) 구현 완료 — `Local_Verify_Demo.html`
- 공동구매 참여 원자적 UPDATE, Kakao 키 `.env` 전환(Map.html), `neighborfood_schema.sql`·`tokens.css` 동기화, `requirements.txt` 갱신 완료 (2026-07-09 커밋 전 점검)
- Kakao 키 하드코딩 전면 제거(전 화면), GPS 위치 인증 보안 강화(인증·소유권·이력 필터·QR 연동 실호출·진입점 연결), 수령 장소 지정(`Reservation.html` 실좌표 연동) 완료 (2026-08-03)
- **정산 시스템** 구현 완료 — `settlements`+`settlement_shares` 테이블, `/api/settlements/*` API 13종(노쇼 취소 `DELETE .../noshow` 포함), `Settlement.html` 실데이터 연동, `Group_Buy_Detail.html`·`Transaction_History.html` 진입점 추가 (2026-08-04)
- **전체 흐름 완성** — GPS 100m 실검증·약속 좌표 저장·`POST /posts/{id}/appointment`·채팅 UX 갭 해소·매너 평가 버튼 완료 (2026-08-07)
- **React(Vite) 프런트엔드 전체 화면 이전** — `frontend-react/`에 기존 HTML 39개 화면 식별자를 React(TypeScript)로 이전(홈 2026-09-14, 나머지 2026-09-20), 공통 디자인·로딩·자동완성·게시글 상세 개선(2026-09-21). 빌드·자동 테스트 통과, 실제 브라우저·기기 검증은 잔여
## Included (구현 대상 — 잔여)
- ~~`posts.py` `join_groupbuy` 미납 정산 참여 차단 로직~~ — ✅ **완료** (2026-09-12): `settlement_db.has_unpaid_settlement()` 호출로 적용
- ~~`qr.py` QR 인증 성공 시 `quality_agreed` 연동~~ — **불필요** (2026-08-07): `POST /api/settlements/{id}/shares/me/qr-done`으로 대체 완료
- ~~상호 매너 평가(`manner_ratings` 테이블 + `trust_score` 반영)~~ — ✅ 완료(2026-08 이전, 상단 "완료로 전환된 기존 잔여 항목" 참고). [2026-09-08 정정: 이 목록에 잘못 남아있던 항목]
- ~~공동구매 참여 취소 흐름~~ — ✅ 완료(2026-08-12, 상단 "완료로 전환된 기존 잔여 항목" 참고). [2026-09-08 정정: 이 목록에 잘못 남아있던 항목]
- `frontend-react/README.md` 프로젝트 설명으로 교체, 공개 공지 API 미구현 대응, React 화면 실제 환경 검증, 게시글 수정 API 확장 여부, PWA 전환, 정적 HTML 최종 처리 (2026-09-21 갱신 — 상단 "미완료(잔여)" 참고)
## Excluded (범위 외)
- 유통기한 임박 추천
- 레시피 추천
- 식재료 객체 인식
- 오프라인 모드
- 실제 결제 / 외부 송금 연동 (기본 미예정 — 여유가 있을 경우에 한해 추가 검토, 현재 정산은 사용자 납부 표시 방식)
## Prohibited (금지)
- 식품 소분 판매
- 포장 훼손 거래 UI
---
# 6. Commands
* **Frontend(정적 HTML):** Live Server(5500) 또는 `http://127.0.0.1:8000/frontend/<파일>.html`
  (카메라 사용 화면(QR/영수증)은 8000 포트로 열 것. 인증·게시는 같은 출처에서 진행)
* **Frontend(React, 2026-09-14 신규 → 2026-09-20~21 전체 이전):** `cd frontend-react && npm ci && npm run dev` → [http://localhost:5173](http://localhost:5173) (Vite 기본 포트, 화면은 `/#/화면명` 해시 경로). 백엔드(`uvicorn main:app`, 8000번)가 먼저 실행 중이어야 하며 Vite 서버가 API 요청을 프록시함. 프록시 대상은 `NEIGHBORFOOD_BACKEND`, 공개 API 주소 직접 지정은 `VITE_API_BASE_URL`(필요 시 `frontend-react/.env.local`). React와 정적 HTML은 접속 출처가 달라 로그인 상태가 공유되지 않으므로 React에서 별도 로그인. 기타: `npm run build`(`tsc -b && vite build`), `npm run lint`(oxlint), `npm run preview`
* **Backend / AI:** `uvicorn main:app --reload`
* **더미 데이터:** ~~`python seed_posts.py`~~ (⚠️ 2026-09-08 기준 저장소에 미존재)
* **관리자 계정:** `python seed_admin.py` (신규 생성, login_id=Admin/pw=admin0000) / `python seed_admin.py <login_id>` (기존 계정 승격) — 2026-09-12 복원
* **영수증 파서 테스트 [신규]:** `python tests/test_receipt_parser_v212.py`
* **API 문서:** `http://127.0.0.1:8000/docs`
* **DB 초기화:** 서버 startup 시 `init_all_databases()`가 `neighborfood.db`를 자동 생성
* **DB 데이터 전체 삭제 + Admin 재생성:** `python reset_db.py` (`--yes` 확인 생략, `--pw <비밀번호>` Admin 비밀번호 지정) — ⚠️ 전 데이터 삭제, 서버 종료 후 실행