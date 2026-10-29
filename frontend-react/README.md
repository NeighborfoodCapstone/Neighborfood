# NeighborFood — React 프런트엔드 (`frontend-react/`)

이웃 간 식재료 나눔·공동구매·교환을 위한 로컬 커뮤니티 플랫폼 **NeighborFood**의 웹 프런트엔드입니다.
기존 정적 HTML 39개 화면을 모두 React(TypeScript)로 이전한 구현이며, **배포 시 사용자에게 보이는 UI는 이 앱**입니다.
(루트의 `frontend/` 정적 HTML은 최종 점검 전까지 병행 보존하는 이전 버전이며, 배포 UI가 아닙니다.)

> PWA 화면 구성 감사(2026-10-29): 공통 사이드 메뉴, 프로필 동네 설정 경로, 채팅·정산 상태와 냉장고 대화상자를 개선했습니다. 검증 범위와 실제 기기·외부 서비스의 미확인 사항은 `docs/UI_AUDIT_REPORT.md`를 참고하세요.
> 상태(2026-10-12): 2026-10-11~12 팀원 작업으로 QR/영수증 화면 개선, 프로필 사진, 신뢰 온도 게이지(`TrustTemperature.tsx`)가 추가되었고, 백엔드는 환경변수로 Supabase를 선택할 수 있게 되었습니다(프런트 코드 변경 없이 API 주소만 영향). 배포 방식(Oracle 유지 / Vercel+Supabase)은 10/16에 확정 예정입니다.
> 이전 상태(2026-10-06): 화면 39개 이전·빌드 통과 + PortOne 테스트 결제 화면 4종(`Payment_*`, 2026-10-05) 추가, 운영 서버(`https://neighborfood.duckdns.org`)에 `dist/` 배포됨(PortOne 반영본은 서버 재배포 확인 필요). 실제 모바일·카메라(QR)·GPS·Kakao 지도·OCR 동작은 실환경 검증 단계입니다.
> **PWA(설치·오프라인)는 아직 구현되지 않았습니다**(`vite-plugin-pwa` 도입 예정).

## 기술 스택

| 구분 | 내용 |
|---|---|
| 프레임워크 | React 19 + TypeScript, Vite 8 |
| 린터 | Oxlint (`.oxlintrc.json`, `react/rules-of-hooks` error) |
| 주요 라이브러리 | `qrcode`(QR 생성), `jsqr`(QR 스캔), `@portone/browser-sdk`(PortOne V2 테스트 결제창, 2026-10-05) |
| 라우팅 | 해시 라우팅 (`#/화면이름?쿼리`) — 새로고침·직접 접속에 서버 설정이 필요 없음 |
| 백엔드 | FastAPI + SQLite 기본, 선택적으로 Supabase(PostgreSQL) (저장소 루트, 이 폴더는 API만 호출) |
| 요구 사항 | Node.js 20.19 이상(20.x), 22.12 이상(22.x), 또는 24 이상, npm |

## 빠른 시작 (로컬 개발)

백엔드와 프런트엔드를 **각각 다른 터미널**에서 실행합니다.

```bash
# 1) 저장소 루트 — FastAPI 백엔드
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 2) frontend-react — React 개발 서버
cd frontend-react
npm ci
npm run dev        # 표시되는 Local 주소(기본 http://localhost:5173)로 접속
```

- 화면은 `http://localhost:5173/#/Home`, `#/Product_Detail?id=1`처럼 직접 열 수 있습니다.
- 일반 화면 목록은 `#/Index`에서 볼 수 있습니다. 관리자 화면은 관리자 권한 확인 후 마이페이지에서 접근합니다.
- 개발 서버가 `/api`, `/posts`, `/uploads`, `/upload-images`, `/logout`, `/request-auth`, `/reset-password` 요청을 FastAPI(기본 `http://127.0.0.1:8000`)로 전달하므로 별도 CORS·`.env.local` 설정이 필요 없습니다.
- 빈 화면이 나오면 새로 만든 DB에 게시글이 없는 것일 수 있습니다(`data/neighborfood.db`는 Git에 포함되지 않음).

## npm 스크립트

| 명령 | 설명 |
|---|---|
| `npm run dev` | 개발 서버(HMR) |
| `npm run build` | 타입 검사(`tsc -b`) + 프로덕션 빌드 → `dist/` |
| `npm run preview` | 빌드 결과를 로컬에서 미리보기(API 프록시 포함) |
| `npm run lint` | Oxlint |
| `npm test` | Vitest/jsdom 메뉴·채팅 오류 복구·거래 상태 UI 회귀 테스트 |

## 폴더 구조

```text
frontend-react/
├─ index.html · vite.config.ts · tsconfig*.json · package.json
├─ public/                      정적 자산(파비콘 등)
├─ docs/
│  ├─ DESIGN_CONTEXT.md         공통 디자인·로딩·자동완성·게시글 상세 기준
│  ├─ MIGRATION_REPORT.md       화면 39개 이전 매핑·검증/미검증 범위
│  └─ UI_AUDIT_REPORT.md        PWA 화면별 감사·비교 캡처·잔여 검증
└─ src/
   ├─ main.tsx · App.tsx        진입점·라우트 연결(RouteLoading, Guard, Screen)
   ├─ neighborfood/             메인 화면과 공통 레이아웃
   │  ├─ api.ts                 백엔드 주소(backend)·게시글 목록 조회
   │  ├─ HomePage.tsx · home.css
   │  ├─ AppLayout.tsx · Icon.tsx
   └─ migration/                나머지 화면과 공통 모듈
      ├─ core.tsx               api()·useData·useAction·Page·Form 등 공통 로직(인증 토큰 포함)
      ├─ loading.tsx            공통 로딩 컨텍스트
      ├─ autocomplete.tsx       공통 자동완성(검색·회원·주소)
      ├─ routes.tsx             화면 목록(screens)·공개 화면(publicScreens)·Screen 분기·Guard
      ├─ TrustTemperature.tsx · trust-temperature.css · profile.css   신뢰 온도 캔버스 게이지(0~40°)·프로필 사진 스타일 (2026-10-11)
      ├─ auth.tsx · posts.tsx · PostGallery.tsx · fridge.tsx · trades.tsx
      ├─ location.tsx · receipt.tsx · qr.tsx · admin.tsx
      ├─ portone.tsx · Scanner.tsx · scanner.css · interface.css   PortOne 테스트 결제(Payment_Checkout/Result/Quick/Preview) · QR·영수증 공용 카메라 스캐너 · 스타일 (2026-10-05)
      └─ design.css             공통 디자인 토큰·폼·버튼·리스트 스타일
```

### 새 화면 추가 방법
1. `src/migration/`의 해당 모듈에 컴포넌트를 만듭니다. 데이터 조회는 `useData`, 쓰기 요청은 `useAction`/`send`, 레이아웃은 `Page`를 사용합니다.
2. `routes.tsx`의 `screens` 배열과 `Screen`의 `switch`에 화면 이름을 등록합니다.
3. 로그인 없이 볼 수 있는 화면이면 `publicScreens`에도 추가합니다. 그 외 화면은 `Guard`가 로그인 화면으로 보냅니다.

### 개발 규칙
- 요청·오류·인증 처리는 `core.tsx`의 공통 코드를 사용하고, 화면마다 `fetch`를 직접 만들지 않습니다.
- 스타일은 `design.css`의 토큰을 사용합니다. 세부 기준은 `docs/DESIGN_CONTEXT.md`를 따릅니다.
- 인증 토큰은 브라우저 `localStorage`(또는 `sessionStorage`)의 `nf_token`에 저장됩니다.
- React 환경변수(`VITE_*`)에는 비밀키를 넣지 않습니다(빌드 결과에 그대로 포함됨).

## 환경 변수 (모두 선택)

| 변수 | 위치 | 용도 |
|---|---|---|
| `NEIGHBORFOOD_BACKEND` | 개발 서버 실행 환경 | Vite 프록시가 API를 전달할 주소. 기본 `http://127.0.0.1:8000` |
| `VITE_API_BASE_URL` | `frontend-react/.env.local` (또는 Vercel 빌드 환경변수) | 공개 API 주소를 직접 쓸 때만 지정. **FastAPI가 `dist/`를 함께 서빙하는 배포(Oracle)에서는 비워 두고**, 프런트를 Vercel 등 다른 도메인에 둘 때(Vercel+Supabase 방식)는 API 주소를 지정하고 서버 `ALLOWED_ORIGINS`에 프런트 도메인을 추가합니다 |

## 배포 (FastAPI가 `dist/`를 서빙)

운영 서버는 React 앱과 API가 **같은 도메인**에서 동작합니다. 그래서 프록시나 `VITE_API_BASE_URL` 없이 상대 경로로 API를 호출합니다.

1. **로컬 PC에서 빌드합니다.** 서버(메모리 1GB급)에서는 `npm run build`를 실행하지 않습니다(메모리 부족 위험).
   ```bash
   cd frontend-react
   npm ci
   npm run build        # 결과: frontend-react/dist/
   ```
2. `dist/` 폴더를 서버의 `<저장소>/frontend-react/dist/`로 업로드합니다(`dist/`는 Git에 포함되지 않음).
   ```bash
   ssh <사용자>@<서버> "rm -rf ~/Neighborfood/frontend-react/dist"      # 이전 빌드 제거(최초에는 없어도 됨)
   scp -r dist <사용자>@<서버>:~/Neighborfood/frontend-react/            # dist 폴더째 업로드 — 서버에 dist/가 없어도 동작
   ```
   > `scp -r dist/* …/dist/` 형태는 서버에 `dist/` 폴더가 이미 있어야 하므로 최초 업로드에는 위 방식을 씁니다(2026-10-06 보정). 개인키를 쓰면 `-i "<개인키 경로>"`를 붙입니다.
3. 서버의 FastAPI(`main.py`)는 `frontend-react/dist/index.html`이 있으면 `/`에서 React 앱을 서빙하고, 없으면 임시 안내 페이지를 보여줍니다. 위치를 바꾸려면 서버 `.env`에 `FRONTEND_DIST_DIR=<절대경로>`를 지정합니다.
   - **`dist/`를 처음 올린 뒤에는 서비스를 한 번 재시작**합니다(`sudo systemctl restart neighborfood`). 서버가 시작할 때 `dist/index.html` 유무를 확인하기 때문입니다.
   - 이후 `dist/`만 교체할 때는 재시작이 필요 없습니다. 이전 빌드의 `assets/` 파일이 남아도 동작에는 영향이 없으며, 정리하려면 업로드 전에 서버의 `dist/` 내용을 지웁니다.
4. 서버 `.env`의 `ALLOWED_ORIGINS`에 서비스 도메인(예: `https://neighborfood.duckdns.org`)을 넣습니다.
5. **HTTPS가 필요합니다.** 카메라(QR)·GPS는 `localhost`가 아닌 주소에서는 HTTPS에서만 동작합니다.

> 코드(백엔드)를 갱신할 때는 서버에서 `git pull` 후 `sudo systemctl restart neighborfood`를 실행합니다. 프런트를 갱신할 때는 로컬에서 다시 빌드해 `dist/`를 교체합니다.

> 배포 방식은 위의 Oracle(같은 도메인) 방식과 Vercel+Supabase 방식이 병행 검토 중이며 10/16에 확정합니다. Vercel 방식의 백엔드 준비는 `../docs/SUPABASE_MIGRATION.md`를 참고하세요(현재 실환경 미검증, 이미지 업로드 요청당 4MB 제한).

## 최근 화면 변경 (2026-10-11)

- **QR_Scan**(`qr.tsx`): 스캔 모드에서는 상단 탭을 숨기고 보조 버튼으로 모드를 오갑니다.
- **Receipt_Verify**(`receipt.tsx`): OCR 분석 중에는 `Scanner`가 `processing` 상태를 표시합니다.
- **My_Page / Edit_Profile**(`auth.tsx`): 프로필 사진(5MB 이하)을 `/upload-images`로 올려 `profile_image`에 저장하고, 신뢰 온도를 게이지로 표시합니다. 업로드와 영수증 API는 로그인이 필요합니다.

## 자주 발생하는 문제

| 증상 | 확인 |
|---|---|
| 화면은 열리는데 목록·로그인이 실패 | FastAPI가 8000번 포트에서 실행 중인지, `http://127.0.0.1:8000/docs`가 열리는지 확인 |
| 다른 주소로 가면 로그인이 풀림 | 접속 주소(출처)가 다르면 `localStorage` 토큰이 공유되지 않음. 해당 주소에서 다시 로그인 |
| 배포 후 흰 화면 | 브라우저 개발자 도구에서 `/assets/*` 404 여부 확인. `dist/`를 통째로 교체했는지 확인(`index.html`과 `assets/`는 한 세트) |
| `npm` 명령 오류 | 현재 경로가 `frontend-react`인지 확인 |
| 지도·OCR만 실패 | 루트 `.env`의 `KAKAO_JS_KEY`, `CLOVA_OCR_*`와 백엔드 로그 확인 |

## 관련 문서

| 문서 | 용도 |
|---|---|
| `../README.md` | 프로젝트 개요·전체 실행 가이드·API 라우터 목록 |
| `../NeighborFood_Architecture_Plan.md` | 아키텍처·API 전체 목록·개발 이력·잔여 작업 |
| `../docs/SUPABASE_MIGRATION.md` | Supabase·Vercel 선택 모드 (팀원 작성) |
| `docs/DESIGN_CONTEXT.md` | 공통 디자인 기준 |
| `docs/MIGRATION_REPORT.md` | 화면 이전 매핑·검증 범위 |
| `docs/UI_AUDIT_REPORT.md` | PWA 화면 감사·전후 캡처·실환경 제약 |