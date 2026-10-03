# NeighborFood — React 프런트엔드 (`frontend-react/`)

이웃 간 식재료 나눔·공동구매·교환을 위한 로컬 커뮤니티 플랫폼 **NeighborFood**의 웹 프런트엔드입니다.
기존 정적 HTML 39개 화면을 모두 React(TypeScript)로 이전한 구현이며, **배포 시 사용자에게 보이는 UI는 이 앱**입니다.
(루트의 `frontend/` 정적 HTML은 최종 점검 전까지 병행 보존하는 이전 버전이며, 배포 UI가 아닙니다.)

> 상태: 화면 39개 이전·빌드 통과. 실제 모바일·카메라(QR)·GPS·Kakao 지도·OCR 동작은 실환경 검증 단계입니다.
> **PWA(설치·오프라인)는 아직 구현되지 않았습니다**(`vite-plugin-pwa` 도입 예정).

## 기술 스택

| 구분 | 내용 |
|---|---|
| 프레임워크 | React 19 + TypeScript, Vite 8 |
| 린터 | Oxlint (`.oxlintrc.json`, `react/rules-of-hooks` error) |
| 주요 라이브러리 | `qrcode`(QR 생성), `jsqr`(QR 스캔) |
| 라우팅 | 해시 라우팅 (`#/화면이름?쿼리`) — 새로고침·직접 접속에 서버 설정이 필요 없음 |
| 백엔드 | FastAPI + SQLite (저장소 루트, 이 폴더는 API만 호출) |
| 요구 사항 | Node.js 20 이상, npm |

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
- 전체 화면 목록은 `#/Index`에서 볼 수 있습니다.
- 개발 서버가 `/api`, `/posts`, `/uploads`, `/upload-images`, `/logout`, `/request-auth`, `/reset-password` 요청을 FastAPI(기본 `http://127.0.0.1:8000`)로 전달하므로 별도 CORS·`.env.local` 설정이 필요 없습니다.
- 빈 화면이 나오면 새로 만든 DB에 게시글이 없는 것일 수 있습니다(`data/neighborfood.db`는 Git에 포함되지 않음).

## npm 스크립트

| 명령 | 설명 |
|---|---|
| `npm run dev` | 개발 서버(HMR) |
| `npm run build` | 타입 검사(`tsc -b`) + 프로덕션 빌드 → `dist/` |
| `npm run preview` | 빌드 결과를 로컬에서 미리보기(API 프록시 포함) |
| `npm run lint` | Oxlint |

## 폴더 구조

```text
frontend-react/
├─ index.html · vite.config.ts · tsconfig*.json · package.json
├─ public/                      정적 자산(파비콘 등)
├─ docs/
│  ├─ DESIGN_CONTEXT.md         공통 디자인·로딩·자동완성·게시글 상세 기준
│  └─ MIGRATION_REPORT.md       화면 39개 이전 매핑·검증/미검증 범위
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
      ├─ auth.tsx · posts.tsx · PostGallery.tsx · fridge.tsx · trades.tsx
      ├─ location.tsx · receipt.tsx · qr.tsx · admin.tsx
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
| `VITE_API_BASE_URL` | `frontend-react/.env.local` | 공개 API 주소를 직접 쓸 때만 지정. **FastAPI가 `dist/`를 함께 서빙하는 배포에서는 비워 둡니다** |

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
   scp -r dist/* <사용자>@<서버>:~/Neighborfood/frontend-react/dist/
   ```
3. 서버의 FastAPI(`main.py`)는 `frontend-react/dist/index.html`이 있으면 `/`에서 React 앱을 서빙하고, 없으면 임시 안내 페이지를 보여줍니다. 위치를 바꾸려면 서버 `.env`에 `FRONTEND_DIST_DIR=<절대경로>`를 지정합니다.
   - **`dist/`를 처음 올린 뒤에는 서비스를 한 번 재시작**합니다(`sudo systemctl restart neighborfood`). 서버가 시작할 때 `dist/index.html` 유무를 확인하기 때문입니다.
   - 이후 `dist/`만 교체할 때는 재시작이 필요 없습니다. 이전 빌드의 `assets/` 파일이 남아도 동작에는 영향이 없으며, 정리하려면 업로드 전에 서버의 `dist/` 내용을 지웁니다.
4. 서버 `.env`의 `ALLOWED_ORIGINS`에 서비스 도메인(예: `https://neighborfood.duckdns.org`)을 넣습니다.
5. **HTTPS가 필요합니다.** 카메라(QR)·GPS는 `localhost`가 아닌 주소에서는 HTTPS에서만 동작합니다.

> 코드(백엔드)를 갱신할 때는 서버에서 `git pull` 후 `sudo systemctl restart neighborfood`를 실행합니다. 프런트를 갱신할 때는 로컬에서 다시 빌드해 `dist/`를 교체합니다.

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
| `docs/DESIGN_CONTEXT.md` | 공통 디자인 기준 |
| `docs/MIGRATION_REPORT.md` | 화면 이전 매핑·검증 범위 |