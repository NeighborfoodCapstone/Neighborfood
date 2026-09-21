# React 전환 적용본 — 2026-09-20

## 범위

기존 HTML 39개의 화면 식별자를 React 경로로 매핑했다. 메인은 현재 승인본을 유지한다. API·DB·기존 HTML 파일은 변경하지 않는다. 아래 그룹 내 공통 기능은 하나의 React 컴포넌트와 props로 공유한다. 39개 식별자가 39개의 독립 TSX 파일이라는 뜻은 아니다.

| 기존 화면 식별자 | React 구현 / 연결 |
|---|---|
| Home | 기존 HomePage 유지 |
| Login, Signup | auth.tsx / 로그인·가입·토큰 저장 |
| Password_Reset, Verify | auth.tsx / 인증번호 요청→비밀번호 변경 공통 흐름 |
| My_Page, Edit_Profile, Withdraw | auth.tsx / 프로필 조회·수정·탈퇴·로그아웃 |
| Search, Search_Results, Wishlist | posts.tsx / 검색·분류·찜 목록 |
| Product_Detail, Group_Buy_Detail | posts.tsx / 상세·찜·신고·작성자 작업·공동구매 |
| Create_Post, Reservation, Report | posts.tsx / 사진 업로드·등록/수정·거래 신청·신고 |
| Fridge | fridge.tsx / 조회·추가·수정·삭제·상태 전환 |
| Chat_List, Chat_Detail, Group_Chat | trades.tsx / 실제 채팅·그룹·메시지 폴링 |
| My_Activity, Transaction_History | trades.tsx / 게시글·거래·신고·매너 평가 |
| Settlement | trades.tsx / 정산 생성·약속·인증·납부 표시·불참·완료/취소 |
| Map, Location_Detail, Neighborhood_Setting | location.tsx / Kakao 지도·검색·위치·동네 설정 |
| Local_Verify_Demo | location.tsx / 서버 GPS 검증·정산·QR 연결 |
| QR_Scan | qr.tsx / QR 발급·카메라 스캔·토큰 검증·정산 연결 |
| Receipt_Verify | receipt.tsx / OCR 업로드·항목 편집/선택·인증·냉장고 등록 |
| Admin_Dashboard, Admin_Users, Admin_Notices | admin.tsx / 관리자 데이터·회원·공지 |
| Admin_Report_Detail, Admin_Chat_History, Admin_Staff_Invite | admin.tsx / 신고 처리·채팅 기록·회원 권한 관리 |
| Help | routes.tsx / 현재 기능에 맞춘 도움말 |
| Splash, Onboarding | routes.tsx / 홈·로그인·가입·동네 설정 진입 |
| Index | routes.tsx / React 화면 목록 |

## 경로와 서버

React 내부 이동은 #/페이지명 형태다. 예: /#/Fridge, /#/Product_Detail?id=1. 기존 홈의 상세 링크와 하단 메뉴도 React로 연결한다. 새로고침에 별도 서버 라우팅 설정이 필요 없다. 기존 8000 포트 HTML 주소를 덮어쓰지는 않는다.

Vite dev/preview 프록시가 /api, /posts, /uploads 등을 기존 FastAPI 8000번으로 전달한다. NEIGHBORFOOD_BACKEND로 프록시 대상을 바꿀 수 있다. VITE_API_BASE_URL이 있으면 해당 공개 주소를 직접 사용한다. 정적 dist 배포 시에는 같은 API 프록시를 배포 서버에도 구성하거나 공개 API 주소를 설정해야 한다. 이 패치는 PWA 설치/오프라인 기능을 새로 구현하지 않는다.

## 검증한 범위

- TypeScript·Vite production 빌드 통과.
- happy-dom에서 실제 React를 마운트하고 별도 테스트 FastAPI/SQLite에 로그인, 냉장고 등록·사용 완료, 게시글 폼 제출·상세 이동을 실행했다.
- 일반 화면 경로와 관리자 화면을 마운트하고 일반 회원의 관리자 접근 차단을 확인했다.
- 별도 DB에서 API로 두 계정의 공동구매 참여·그룹 채팅, 정산 생성→약속→GPS→QR→납부 표시→완료를 확인했다.
- 거래 상태 전환·평가·찜 API도 확인했다.
- 테스트용 데이터·계정·DB는 적용본에 포함하지 않았다.

## 아직 검증하지 않은 범위와 주의할 차이

- 실제 브라우저의 화면 전후 비교·모바일 터치·키보드 전체 탐색은 미검증이다. DOM 테스트는 화면 렌더링 검증이 아니다.
- 실제 카메라 스캔, 위치 정확도, Kakao SDK, CLOVA OCR은 사용자 환경에서 확인해야 한다. GPS 테스트는 테스트 좌표로 서버 연결을 검증한 것이다.
- 기존 HTML의 모든 세부 상호작용/레이아웃과 1:1 동등하다고 확정하지 않았다. Verify는 별도 OTP 성공 페이지 대신 실제 비밀번호 재설정 흐름을 공유하고, 시작 화면은 진입 링크로 정리했다.
- 기존 Help의 자동 환불·응답 시간 보장 등 미구현 안내는 그대로 옮기지 않았다. 일반 공개 공지 API가 없어 관리자 공지를 일반 회원 화면에 노출하지 않았다.
- 게시글 수정 API는 사진·거래 유형·목표 인원·1인 금액을 수정하지 못하므로 해당 필드는 편집을 제한했다. 기존 서버를 바꾸지 않았다.
- 정산의 납부 표시는 결제 승인이나 자동 송금이 아니다. 기존의 GPS/QR 권한·신뢰 모델 자체를 개선하는 백엔드 패치는 포함하지 않는다.
- 관리자 주간 통계는 실제 데이터를 표로 표시한다. 채팅 상세는 상대/그룹명과 원 게시글로 이동하는 정보를 포함한다. 원본 HTML의 세부 장식·애니메이션까지 동등하다고 확정하지 않았다.

## 적용 후 확인 순서

로그인 → 메인 검색 → 상세 → 찜/신청 → 채팅 → 내 활동, 냉장고 CRUD, 지도/동네, GPS→QR→정산, 영수증→냉장고, 관리자 작업을 확인한다. 확인 전 운영 배포 완료로 간주하지 않는다.

## 적용 — Git Bash

apply_neighborfood_react_migration.py를 다운로드 폴더에 저장한다. 기존 Vite 터미널은 Ctrl+C로 종료한 뒤 실행한다.

```bash
cd /c/Users/bluem/Neighborfood/frontend-react
py /c/Users/bluem/Downloads/apply_neighborfood_react_migration.py && npm install && npm run build && npm run dev
```

이번에는 QR 생성·스캔 의존성이 추가되어 npm install이 필요하다. npm 설치가 실패하면 이어서 실행하지 않고 오류를 확인한다. 기존 FastAPI는 별도 터미널에서 계속 실행한다.

```bash
cd /c/Users/bluem/Neighborfood
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

접속은 Vite가 출력한 주소(보통 http://localhost:5173/)이다. 8000 포트의 기존 HTML 주소에서 보면 React 전환본이 표시되지 않는다. React와 기존 HTML의 localStorage는 포트별로 분리되므로 React에서 다시 로그인한다.

## 패치 특성·복원

승인된 HomePage.tsx와 home.css는 교체하지 않는다. 새로운 화면 소스 11개와 App.tsx, AppLayout.tsx, api.ts, vite.config.ts, 문서 2개, package.json을 처리한다. 기존 의존성과 npm 스크립트는 보존하며 QR 관련 의존성만 병합한다. package-lock.json은 npm install이 갱신한다.

백업은 저장소 밖 C:/Users/bluem/Neighborfood_react_backups/날짜_시간에 생성한다. 기존 수정 대상에 예상하지 못한 로컬 변경이 있으면 전체 적용 전에 중단한다. --check 옵션으로 변경 없이 확인할 수 있다. --restore에 출력된 실제 백업 경로를 넣으면 복원할 수 있다. 복원 후 npm install로 잠금 파일을 맞춘다. 적용 이후 추가 수정이 있으면 복원도 중단해 보호한다.

## Git 반영

화면 확인 후 저장소 루트에서 아래 명령으로 React 변경만 올린다. 백엔드·Toss 로컬 변경이나 DB는 포함하지 않는다.

```bash
cd /c/Users/bluem/Neighborfood
git add frontend-react
git --no-pager diff --cached --stat
git commit -m "feat: migrate remaining screens to React with shared design"
git push origin main
```

push가 원격 변경 때문에 거절되면 강제 푸시하지 말고 상태를 확인한다. 이 패치는 Git 명령을 자동 실행하지 않는다.
