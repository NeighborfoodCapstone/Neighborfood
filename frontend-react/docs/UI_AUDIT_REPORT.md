# NeighborFood React/PWA 화면 구성·UI 감사

## 1. 범위와 판정

**상태: 구현 및 격리 검증 완료, 실환경·최종 시각 승인은 미완료.** 지시서의 모든 실기기·외부 서비스·모든 조작 검증이나 기존 통합 작업의 완료를 주장하지 않는다. 설치형 PWA와 오프라인 기능은 이번 작업 범위가 아니며 기존 README 기준 미구현이다.

- 작업 시작 기준: `main`, 로컬 `d8b07ae`, 작업 트리 깨끗함. 원격 fetch는 하지 않았다. 이번 변경은 로컬 작업 트리에 있으며 커밋·push하지 않았다.
- 선택된 팀 정의를 읽을 수 없다는 런타임 오류가 있어 하위 에이전트에 위임하지 않았다. 조사·수정·테스트·브라우저 확인은 주 작업자가 수행했다.
- `screens`의 43개 라우트를 실제 FastAPI/React 격리 환경에서 가상 계정·게시글·채팅·정산·신고 데이터로 열었다. 390×845 CSS px와 1920×1080 CSS px에서 각 43개, 총 86개 렌더링을 관찰했으며 로딩 대기 시간 초과와 문서 전체 가로 오버플로는 관찰하지 않았다. 이것은 **해당 데이터와 두 뷰포트에 한정**되며 각 화면의 모든 버튼·오류·권한 조합을 실행했다는 뜻이 아니다.
- 선택된 Kakao 지도 설정이 없는 격리 환경에서는 지도 오류 안내를 확인했다. 카메라 권한이 없는 Chromium에서는 QR/영수증 카메라 권한 안내를 확인했다. 실제 지도·카메라가 성공했다고 해석하지 않는다.
- 표의 `R`은 위 두 크기에서 렌더링 및 표시 데이터를 확인했다는 뜻이다. `I`는 아래 3절에 적은 실제 조작까지 확인한 경우다. `검증 필요`는 화면을 열었더라도 외부 장치·서비스 또는 미실행 조작이 남았다는 뜻이다. `API/환경 필요`는 외부 의존성이 없는 것처럼 꾸미지 않은 항목이다. 우선순위는 지시서의 P1/P2를 사용한다.
- 이미지 열의 접두어 `X`는 `ui-audit/before-X-mobile.png`, `after-X-mobile.png`, `before-X-desktop.png`, `after-X-desktop.png`를 뜻한다. `공통 home`은 해당 화면 자체가 아니라 헤더 변경 대표 캡처다. 상세 링크는 4절에 있다. 가상 테스트 데이터가 추가되어 전후 캡처의 데이터 양은 일부 다르므로 픽셀 단위 동등 비교가 아니다.

## 2. 화면별 감사표

| 화면/라우트 | 구현 경로 | 실제 확인·분류 | 우선 | 수정 파일 | 테스트 결과 | 이미지 | 보류 사유 |
|---|---|---|---|---|---|---|---|
| Home | `neighborfood/HomePage.tsx` | 기존 홈 구성 유지, 공통 헤더 변경 | P2 | `AppLayout.tsx` | R, 홈 진입 I | `home`, `menu` | 실제 배포·기기 미확인 |
| Index | `migration/routes.tsx` | 공개 목록의 관리자 링크 노출 확인 후 숨김, UI 수정 | P1 | `routes.tsx` | R, 비로그인 관리자 링크 0개 I | `index` | 관리자 직접 URL의 서버 권한은 계속 필요 |
| Splash | `migration/routes.tsx` | 단순 링크만 있던 진입 화면에 실제 이용 순서 안내, UI 수정 | P2 | `routes.tsx`, `interface.css` | R | `splash` | 실제 사용자 시각 승인 필요 |
| Onboarding | `migration/routes.tsx` | 핵심 행동과 실제 거래 단계 설명 보강, UI 수정 | P2 | `routes.tsx`, `interface.css`, `design.css` | R, 홈 이동 I | `onboarding` | 실제 기기 검토 필요 |
| Login | `migration/auth.tsx` | 기존 폼 유지 | P2 | 공통 `core.tsx` | R, 가상 계정 로그인·로그아웃·재로그인 I | 공통 `home` | 실제 인증 배포 환경 미확인 |
| Signup | `migration/auth.tsx` | 기존 가입 폼 유지 | P2 | 공통 `core.tsx` | R, 가상 계정 가입 I | 공통 `home` | 실제 휴대폰 가입 정책 미확인 |
| Password_Reset | `migration/auth.tsx` | 번호 입력과 요청 화면 렌더링, 기능 검증 필요 | P2 | 공통 `core.tsx` | R | 공통 `home` | OTP 발송·실제 번호 미사용 |
| Verify | `migration/auth.tsx` | 비밀번호 재설정 화면 재사용, 기능 검증 필요 | P2 | 공통 `core.tsx` | R | 공통 `home` | OTP·비밀번호 재설정 미실행 |
| My_Page | `migration/auth.tsx` | 8개 긴 메뉴 제거, 프로필·신뢰온도·계정·관리자 접근 유지, UI 수정 | P1 | `auth.tsx`, `AppLayout.tsx` | R, 프로필·관리자 역할 표시 I | `profile` | 실제 사진 업로드·기기 미확인 |
| Edit_Profile | `migration/auth.tsx` | 기존 프로필 수정에 동네 설정 진입 추가, UI 수정 | P1 | `auth.tsx` | R, 닉네임 저장 및 동네 진입 I | `edit-profile` | 실제 사진·지도 SDK 미확인 |
| Withdraw | `migration/auth.tsx` | 기존 확인 및 탈퇴 흐름 유지 | P2 | 공통 `core.tsx` | R, 가상 계정 탈퇴 후 홈·세션 삭제 I | 공통 `home` | 실제 계정 탈퇴 미실행 |
| Search | `migration/posts.tsx` | 검색·필터 유지 | P1 | 공통 `core.tsx` | R, 가상 키워드 검색 결과 I | 공통 `home` | 느린 네트워크·모든 필터 조합 미검증 |
| Search_Results | `migration/posts.tsx` | Search 화면과 실제 검색 결과 재사용 | P1 | 공통 `core.tsx` | R, 쿼리 결과 표시 | 공통 `home` | 모든 자동완성 입력 조합 미검증 |
| Wishlist | `migration/posts.tsx` | 실제 빈 목록·저장 목록 유지 | P1 | 공통 `AppLayout.tsx` | R, 상세 찜 등록→목록→해제 I | 공통 `home` | 다른 계정·대량 목록 미검증 |
| Product_Detail | `migration/posts.tsx` | 게시글 정보·신청·찜 행동 유지 | P1 | 공통 `design.css` | R, 찜·거래 신청 I | 공통 `home` | 실제 사진 업로드·모든 오류 미검증 |
| Group_Buy_Detail | `migration/posts.tsx` | 실제 참여·채팅·정산 동선 유지 | P1 | 공통 `design.css` | R, 가상 참여·그룹 채팅 연결 | 공통 `home` | 대규모 참여·실기기 미검증 |
| Create_Post | `migration/posts.tsx` | 기존 입력과 실제 저장 유지 | P1 | 공통 `core.tsx`, `design.css` | R, 가상 나눔 게시글 저장 I | 공통 `home` | Kakao 지도·실제 사진 업로드 미확인 |
| Reservation | `migration/posts.tsx` | 신청→기존 대화 연결 유지 | P1 | 공통 `core.tsx` | R, 신청 후 채팅 및 제공자 수락 I | 공통 `home` | 실환경 동시 신청 미검증 |
| Report | `migration/posts.tsx` | 실제 신고 폼 렌더링, 기능 검증 필요 | P2 | 공통 `core.tsx` | R, 가상 신고는 API로 생성 | 공통 `home` | 폼 제출·관리 처리 전체 UI 왕복 미실행 |
| Chat_List | `migration/trades.tsx` | 상대/그룹·게시글·마지막 메시지·시각·서버 미읽음 위계와 말줄임, UI 수정 | P1 | `trades.tsx`, `interface.css` | R, 양쪽 방 이동·840자 말줄임 I | `chat-list` | 실제 네트워크 지연·다수 방 미검증 |
| Chat_Detail | `migration/trades.tsx` | 최신 위치·읽기 중 새 메시지·전송 오류 복구 및 입력 가림 수정, UI 수정 | P1 | `trades.tsx`, `core.tsx`, `interface.css` | R, 두 계정 왕복·오프라인·중복·스크롤 I | `chat-direct` | 서버의 200개 조회 제한, 실제 키보드/IME 미검증 |
| Group_Chat | `migration/trades.tsx` | 참여자·거래 바 유지, 말풍선·입력·복구 개선, UI 수정 | P1 | `trades.tsx`, `interface.css` | R, 두 계정 왕복·참여자·거래 바 I | `chat-group` | 모든 참여자 상태·실제 기기 미검증 |
| My_Activity | `migration/trades.tsx` | 게시글·거래 상태 및 하단 진입 유지 | P1 | 공통 `core.tsx`, `AppLayout.tsx` | R, 제공자 수락 I | 공통 `home` | 모든 취소·평가 UI 조합 미검증 |
| Transaction_History | `migration/trades.tsx` | 거래 목록·상태 필터 유지 | P1 | 공통 `core.tsx`, `AppLayout.tsx` | R, A/B 완료 상태는 API 확인 | 공통 `home` | 대량 내역·실환경 미검증 |
| Settlement | `migration/trades.tsx` | GPS 대기 중 QR을 실행 가능하게 표시하던 동선 수정 | P1 | `trades.tsx` | R, GPS 전 QR 비노출·납부 비활성, GPS 후 QR 노출 I | `settlement` | 실제 입금·결제 및 Supabase 미검증 |
| Payment_Checkout | `migration/portone.tsx` | 테스트 결제와 납부 표시 구분 유지 | P2 | 공통 `design.css` | R, GPS/QR 대기 표시 | 대표 `payment-primary` | 외부 결제 요청 미실행 |
| Payment_Result | `migration/portone.tsx` | 승인 확인 전 성공 표시 방지 문구 유지 | P2 | 공통 `design.css` | R, 결제 ID 없는 상태 확인 | 대표 `payment-primary` | 실제 승인·취소 조회 미실행 |
| Payment_Preview | `migration/portone.tsx` | 예시임을 명시, 주요 링크 색·터치 높이 수정 | P2 | `design.css` | R, 주요 링크 44px·흰색/어두운 배경 확인 | `payment-primary` | 실제 결제 동작 아님 |
| Payment_Quick | `migration/portone.tsx` | 테스트 결제임을 명시한 화면 유지 | P2 | 공통 `design.css` | R | 대표 `payment-primary` | 실제 포트원 호출·과금 방지를 위해 미실행 |
| Fridge | `migration/fridge.tsx` | 편집창이 Esc에 반응하지 않고 배경 포커스·스크롤을 허용하던 문제 수정 | P1 | `fridge.tsx`, `interface.css` | R, 가상 품목 저장·모달 Tab/Esc/바깥 클릭·포커스 복귀 I | `fridge`, `fridge-modal` | 실제 모바일 키보드 미검증 |
| Map | `migration/location.tsx` | 목록·필터 유지, 지도는 외부 환경 필요 | P2 | 공통 `core.tsx` | R, 키 없는 환경의 오류 확인 | 공통 `home` | 실제 Kakao 지도·권한·마커 미검증 |
| Neighborhood_Setting | `migration/location.tsx` | 기존 검색/GPS/저장 재사용 | P2 | 공통 `core.tsx` | R, 프로필에서 진입·가상 지오코더와 실제 로컬 저장 API I | `edit-profile` | 실제 Kakao 주소 검색·GPS 기기 미검증 |
| Location_Detail | `migration/location.tsx` | 게시글 ID가 없을 때 가짜 `0원` 표시 대신 선택 안내, UI 수정 | P2 | `location.tsx` | R, ID 없음 안내 및 유효 ID 게시글 I | `location-detail-empty` | 실제 지도 SDK 미검증 |
| Local_Verify_Demo | `migration/location.tsx` | 기존 거래 GPS 인증 유지 | P2 | 공통 `core.tsx` | R, 좌표 에뮬레이션으로 거래 GPS I | 공통 `home` | 실제 단말 위치·위조 방지 보장 아님 |
| Receipt_Verify | `migration/receipt.tsx`, `Scanner.tsx` | 기존 세로형 촬영 경험 유지 | P1 | 공통 `AppLayout.tsx`, `design.css` | R, OCR 중단 안내·수동 품목 저장 I | `receipt` | 실 카메라·실 OCR·운영 차단 상태 미확인 |
| QR_Scan | `migration/qr.tsx`, `Scanner.tsx` | 기존 정사각형 가이드·상태 유지 | P1 | 공통 `AppLayout.tsx`, `design.css` | R, 거래 QR 직접 입력 및 가상 PNG 디코딩 I | `qr` | 실제 휴대폰 카메라·촬영 사진 미검증 |
| Help | `migration/routes.tsx` | 공지·FAQ 실제 응답 기반 유지 | P2 | 공통 `AppLayout.tsx` | R, 메뉴 진입 I | 공통 `home` | 모든 공지·FAQ 내용의 운영 최신성 미확인 |
| Admin_Dashboard | `migration/admin.tsx` | 관리자 전용 대시보드·OCR 중단 상태 유지 | P1 | 공통 `core.tsx` | R, 가상 관리자 접근·일반 사용자 거부 I | 공통 `home` | 실제 운영 관리자·OCR 스위치 미조작 |
| Admin_Users | `migration/admin.tsx` | 회원 `active`를 게시글의 ‘진행 중’이 아닌 회원 ‘활동’으로 표시, UI 수정 | P1 | `admin.tsx` | R, 가상 관리자 목록 I | `admin-users` | 실제 계정 정지·해제 미실행 |
| Admin_Notices | `migration/admin.tsx` | 빈 공지 목록 안내 추가, UI 수정 | P1 | `admin.tsx` | R, 빈 목록 I | `admin-notices` | 공지 생성·삭제 UI 미실행 |
| Admin_Report_Detail | `migration/admin.tsx` | 가상 신고의 실제 상세 표시 유지 | P1 | 공통 `core.tsx` | R, 가상 신고 표시 | 공통 `home` | 처리·반려 버튼은 미실행 |
| Admin_Chat_History | `migration/admin.tsx` | 관리자 대화 목록·건수 표시 유지 | P1 | 공통 `core.tsx` | R, 가상 방 목록 | 공통 `home` | 모든 상세·권한 시나리오 미검증 |
| Admin_Staff_Invite | `migration/admin.tsx` | 관리자 전용 운영진 목록 유지 | P1 | `admin.tsx` | R, 가상 관리자 목록 | `admin-users` 대표 | 실제 권한 부여·회수 버튼 미실행 |

## 3. 변경 이유 및 실제 검증

### 정보 구조와 접근성

- 이전: 헤더 오른쪽이 `Neighborhood_Setting`으로 바로 이동하고 `My_Page`에 동네 설정과 8개 부가 기능이 나열됐다. 이후: 같은 위치의 전체 메뉴가 `Fridge`, `Wishlist`, `My_Activity`, `Chat_List`, `Transaction_History`, `Settlement`, `Receipt_Verify`, `Help`로 이동한다. 하단 내 활동 등 기존 진입점과 기존 해시 URL은 유지했다.
- 마이페이지의 사진·닉네임·현재 동네·신뢰온도·프로필 수정·로그아웃·탈퇴는 유지한다. 관리자 링크는 서버가 반환한 `role=admin`일 때만 표시하고 기존 `AdminGuard`/서버 인가도 유지한다. 공개 `Index`에서 관리자 링크 6개가 보이던 것을 제거했다. 관리자 직접 URL과 권한 검사는 삭제하지 않았다.
- 동네 변경은 `Edit_Profile` → 기존 `Neighborhood_Setting` → `POST /api/users/neighborhood`이다. 격리 브라우저에서 가상 지오코더와 GPS 좌표를 주입해 이 API에 저장하고 `GET /api/users/me` 및 마이페이지 표시가 일치하는 것을 확인했다. Kakao SDK 자체의 성공 검증이 아니다.
- 드로어의 8개 링크를 각각 클릭해 목적 해시와 닫힘을 확인했다. Esc·바깥 클릭·Tab/Shift+Tab 순환, 포커스 복귀, 배경 `inert`·스크롤 잠금, 320×400에서 내부 스크롤, 1920×1080에서 360px 폭, reduced motion에서 애니메이션 없음도 확인했다. 비로그인 냉장고 접근은 기존 로그인 가드로, 일반 회원의 관리자 직접 접근은 권한 없음으로 처리됐다.
- 냉장고 편집창은 기존에 Esc 후에도 열린 상태였고 배경 스크롤이 잠기지 않았다. 네이티브 모달로 전환해 포커스를 품목에 놓고, Tab이 모달 안에 머물며 Esc·바깥 클릭으로 닫고 원래 버튼에 포커스를 돌린다. 가상 품목 저장도 확인했다.

### 채팅·거래·시각 위계

- 변경 전 긴 1:1 대화에서 스크롤 위치가 `0`이고 `scrollHeight=1718`, `clientHeight=648`이었다. 변경 후 최초 진입은 최하단, 이전 대화 열람 중 새 메시지가 오면 위치를 유지하고 ‘새 메시지 보기’로 이동한다. 폴링 중 기존 대화 컨테이너를 교체하거나 매번 로딩 애니메이션을 표시하지 않는다.
- 브라우저 점검 중 새 메시지 버튼이 하단 내비게이션에 가려지는 문제와 고정 입력창이 마지막 말풍선을 가리는 문제를 실제 좌표로 재현했다. 버튼 위치를 조정하고 입력 영역의 실제 높이를 관찰해 대화 하단 여백을 조정했다. 최종 점검에서 마지막 말풍선은 입력창과 겹치지 않았고, 오류 메시지로 입력 영역이 커져도 겹치지 않았다.
- 두 가상 계정이 1:1과 그룹에서 실제 API로 메시지를 주고받았다. 오프라인 전송 시 초안과 오류가 유지되고 재시도 후 동일 메시지는 한 건만 저장됐다. 처음 로딩이 오프라인으로 실패한 뒤 재시도하면 메시지뿐 아니라 대화 정보도 복구한다. 840자 메시지는 줄바꿈되고 목록에서 말줄임됐다. HTML처럼 보이는 메시지도 텍스트로 표시됐으며, 채팅 이탈 후 6.2초 동안 해당 메시지 폴링 요청은 0회였다.
- 그룹의 참여자·게시글·약속/정산/GPS/QR 진입은 그대로 둔다. 정산에서 GPS가 대기일 때 QR 링크와 납부 실행을 막고, 격리 API로 GPS를 연결한 뒤 QR 링크가 나타나는 것을 확인했다. 프런트가 완료 상태를 임의로 만들지 않는다.
- 공통 주요 행동 링크는 CSS 선택자 우선순위 때문에 일반 흰 버튼처럼 보이던 문제를 수정했다. 실제 계산 스타일은 배경 `rgb(41, 41, 41)`, 글자 흰색, 높이 44px이다. 기존 중립 팔레트·중앙 폭·상/하단 구조와 QR/영수증 촬영 영역 비율은 유지했다.
- 장소 상세를 ID 없이 열면 목록 응답을 단일 게시글로 취급해 `0원`이 보이던 문제를 재현하고 선택 안내로 변경했다. ID가 있는 실제 가상 게시글의 장소 상세도 확인했다. 온보딩은 기존 링크만 보이던 화면에 실제 서비스 이용 순서와 우선 행동을 추가했다.

### 실행한 자동 검사

| 명령·환경 | 결과 | 범위 |
|---|---|---|
| `npm test` | Vitest 4.1.0, **8개 통과** | 드로어 열기/포커스/Esc/라우팅, 공개 관리자 링크, 전송 실패 초안, 초기 연결 재시도, 빈 장소 상세, GPS별 정산 QR 상태 |
| `npm run build` | 성공 | TypeScript + Vite 8.3.0, 격리 복사본 |
| `npm run lint` | 종료 코드 0, **경고 41개·오류 0개** | 전체 프런트. 경고가 남아 있으며 전부 해결했다고 주장하지 않는다 |
| `python -m pytest tests -q --disable-warnings` | **53개 통과, 경고 279개** | 격리 SQLite, 이전 통합 기능 회귀. 실제 Supabase/외부 OCR 아님 |
| Chromium + 로컬 FastAPI | 위 R/I 시나리오 확인 | 가상 사용자·좌표·PNG, 카메라 권한 거부 환경 |

프런트 테스트 의존성은 별도 npm 사용자 설정과 캐시를 지정해 로컬 저장소에 설치했다. 테스트와 빌드는 비밀 환경 파일을 복사하지 않은 격리 복사본에서 실행했다. 테스트 도구는 기존 Vite와 호환되는 Vitest 4.1/jsdom 26이며 Node 20.19+(20.x), 22.12+(22.x), 또는 24 이상이 필요하다. 실제 실행은 Node 24.15였다.

## 4. 변경 전·후 캡처

이미지는 전부 가상 데이터이며 `frontend-react/docs/ui-audit/`에 있다. 모바일은 390×845, PC는 1920×1080 CSS px다. 일부 변경 전 화면은 `d8b07ae` 소스를 격리 복사본에 재구성해 캡처했다. Index·온보딩·ID 없는 장소·주요 링크의 ‘전’은 공통 헤더 변경 후 해당 개별 수정 직전에 캡처한 화면이다. 데이터와 스크롤은 일부 달라질 수 있다.

| 화면 | 모바일 전 | 모바일 후 | PC 전 | PC 후 |
|---|---|---|---|---|
| 홈/공통 헤더 | [전](ui-audit/before-home-mobile.png) | [후](ui-audit/after-home-mobile.png) | [전](ui-audit/before-home-desktop.png) | [후](ui-audit/after-home-desktop.png) |
| 전체 메뉴 | [기존 헤더](ui-audit/before-home-mobile.png) | [드로어](ui-audit/after-menu-mobile.png) | [기존 헤더](ui-audit/before-home-desktop.png) | [드로어](ui-audit/after-menu-desktop.png) |
| 프로필 | [전](ui-audit/before-profile-mobile.png) | [후](ui-audit/after-profile-mobile.png) | [전](ui-audit/before-profile-desktop.png) | [후](ui-audit/after-profile-desktop.png) |
| 프로필 수정 | [전](ui-audit/before-edit-profile-mobile.png) | [후](ui-audit/after-edit-profile-mobile.png) | [전](ui-audit/before-edit-profile-desktop.png) | [후](ui-audit/after-edit-profile-desktop.png) |
| 화면 목록 | [전](ui-audit/before-index-mobile.png) | [후](ui-audit/after-index-mobile.png) | [전](ui-audit/before-index-desktop.png) | [후](ui-audit/after-index-desktop.png) |
| Splash | [전](ui-audit/before-splash-mobile.png) | [후](ui-audit/after-splash-mobile.png) | [전](ui-audit/before-splash-desktop.png) | [후](ui-audit/after-splash-desktop.png) |
| Onboarding | [전](ui-audit/before-onboarding-mobile.png) | [후](ui-audit/after-onboarding-mobile.png) | [전](ui-audit/before-onboarding-desktop.png) | [후](ui-audit/after-onboarding-desktop.png) |
| 채팅 목록 | [전](ui-audit/before-chat-list-mobile.png) | [후](ui-audit/after-chat-list-mobile.png) | [전](ui-audit/before-chat-list-desktop.png) | [후](ui-audit/after-chat-list-desktop.png) |
| 1:1 채팅 | [전](ui-audit/before-chat-direct-mobile.png) | [후](ui-audit/after-chat-direct-mobile.png) | [전](ui-audit/before-chat-direct-desktop.png) | [후](ui-audit/after-chat-direct-desktop.png) |
| 그룹 채팅 | [전](ui-audit/before-chat-group-mobile.png) | [후](ui-audit/after-chat-group-mobile.png) | [전](ui-audit/before-chat-group-desktop.png) | [후](ui-audit/after-chat-group-desktop.png) |
| 냉장고 | [전](ui-audit/before-fridge-mobile.png) | [후](ui-audit/after-fridge-mobile.png) | [전](ui-audit/before-fridge-desktop.png) | [후](ui-audit/after-fridge-desktop.png) |
| 냉장고 모달 | [전](ui-audit/before-fridge-modal-mobile.png) | [후](ui-audit/after-fridge-modal-mobile.png) | [전](ui-audit/before-fridge-modal-desktop.png) | [후](ui-audit/after-fridge-modal-desktop.png) |
| 정산 | [전](ui-audit/before-settlement-mobile.png) | [후](ui-audit/after-settlement-mobile.png) | [전](ui-audit/before-settlement-desktop.png) | [후](ui-audit/after-settlement-desktop.png) |
| 관리자 회원 | [전](ui-audit/before-admin-users-mobile.png) | [후](ui-audit/after-admin-users-mobile.png) | [전](ui-audit/before-admin-users-desktop.png) | [후](ui-audit/after-admin-users-desktop.png) |
| 관리자 공지 | [전](ui-audit/before-admin-notices-mobile.png) | [후](ui-audit/after-admin-notices-mobile.png) | [전](ui-audit/before-admin-notices-desktop.png) | [후](ui-audit/after-admin-notices-desktop.png) |
| ID 없는 장소 상세 | [전](ui-audit/before-location-detail-empty-mobile.png) | [후](ui-audit/after-location-detail-empty-mobile.png) | [전](ui-audit/before-location-detail-empty-desktop.png) | [후](ui-audit/after-location-detail-empty-desktop.png) |
| 주요 행동 링크 | [전](ui-audit/before-payment-primary-mobile.png) | [후](ui-audit/after-payment-primary-mobile.png) | [전](ui-audit/before-payment-primary-desktop.png) | [후](ui-audit/after-payment-primary-desktop.png) |
| QR 스캔 | [전](ui-audit/before-qr-mobile.png) | [후](ui-audit/after-qr-mobile.png) | [전](ui-audit/before-qr-desktop.png) | [후](ui-audit/after-qr-desktop.png) |
| 영수증 촬영 | [전](ui-audit/before-receipt-mobile.png) | [후](ui-audit/after-receipt-mobile.png) | [전](ui-audit/before-receipt-desktop.png) | [후](ui-audit/after-receipt-desktop.png) |

## 5. 남은 제약 및 Git 상태

1. 실제 스마트폰의 노치·홈 제스처·주소 표시줄 변화·소프트 키보드와 한글 IME, 실제 카메라·사진 QR·GPS, 사용자 디자인 승인은 확인하지 못했다. 가상 뷰포트·지오코더·PNG 검증과 구분해야 한다.
2. Kakao 지도·실제 OCR·NAVER 사용량 제한·Vercel Firewall·실제 Supabase RLS/Storage·PortOne 결제는 접근/안전 조건이 없어 수행하지 않았다. 기존 [통합 결과 보고서](../../docs/INTEGRATION_REPORT.md)의 차단·백업·실환경 게이트를 먼저 완료해야 한다.
3. 채팅 API는 현재 오래된 순으로 최대 200개를 반환한다. 그 이상에서 최신 메시지/페이징을 정확히 확인하려면 백엔드 계약 검토가 필요하다. 이 디자인 작업에서 API·DB·읽음/실시간 기능을 변경하거나 가짜로 표시하지 않았다.
4. 각 라우트의 렌더링과 위에 명시한 조작은 확인했지만 OTP 발송, 실제 사용자 탈퇴, 관리자 계정 정지·공지 삭제·신고 처리, 실제 결제 등은 실행하지 않았다. 각 행의 보류 항목은 완료로 체크하지 않는다.
5. 테스트 중 첫 `npm install`은 Windows의 Node CSPRNG 초기화 오류로 실패했고 패키지 파일 변경은 없었다. 환경을 격리해 재실행한 뒤 Node 20 호환 버전으로 조정해 테스트를 통과했다. 브라우저에서는 초기 자동화가 메뉴 슬라이드 중 클릭을 시도해 실패하여 애니메이션 종료를 기다린 뒤 재검증했다. 가상 탈퇴의 예상 도착 화면을 로그인으로 잘못 잡은 검사는 실제 동작인 홈 이동·세션 삭제를 확인해 바로잡았다.
6. 현재 변경은 `main`의 로컬 작업 트리에만 있다. 필수 운영·통합 게이트와 사용자 검토가 끝나지 않아 커밋·GitHub push·배포는 하지 않았다. 기존 통합 보고서의 안전한 후속 절차를 따른다.
