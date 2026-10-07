# Neighborfood React 실행 안내

이 문서는 GitHub 저장소를 공유받은 사람이 Neighborfood의 FastAPI 백엔드와 React 프론트엔드를 로컬에서 실행하기 위한 안내서입니다.

> 문서 최종 갱신: 2026-10-07 (GitHub `ec1da57`(main) 기준 문서-저장소 정합성 점검 — 저장소에 없는 문서 참조 표기, 화면 수(39+4) 표기, 팀원 `PORTONE_TEST_SETUP.md` 시점 차이 주석, 낡은 문구 정정) · 이전: 2026-10-06 (운영 서버 배포·PortOne 테스트 결제 안내 추가) · 이전: 2026-09-21 (React 전체 화면 이전 반영)

현재 `frontend-react`는 기존 정적 HTML 39개 화면 식별자를 모두 React(TypeScript)로 이전한 구현입니다(홈 화면은 2026-09-14, 나머지 화면은 2026-09-20~21 이전). 기존 정적 HTML(`frontend/`)은 삭제하지 않고 최종 점검이 끝나기 전까지 병행 보존하며, FastAPI·SQLite 백엔드는 변경하지 않았습니다. React 화면은 백엔드 API를 사용하므로 백엔드와 React 서버를 함께 실행해야 합니다. ※ 화면 수: 기존 HTML 이전분 39개 + PortOne 결제 화면 4개(`Payment_Checkout`·`Payment_Result`·`Payment_Quick`·`Payment_Preview`, 2026-10-05 신규) = `routes.tsx` `screens` 기준 총 43개.

> ⚠️ 이전 구현은 빌드와 자동 테스트를 통과했지만, 실제 브라우저·모바일·카메라(QR)·GPS·Kakao 지도·CLOVA OCR 동작은 실제 환경에서 확인이 필요합니다(상세: `frontend-react/docs/MIGRATION_REPORT.md`). PWA 설치·오프라인 기능은 구현되지 않았습니다.

## 1. 준비 프로그램

- Git
- Python 3
- Node.js 20 이상
- npm

설치 여부는 Git Bash에서 확인할 수 있습니다.

```bash
git --version
py --version
node --version
npm --version
```

`py` 명령을 찾지 못하면 `python --version`으로 확인하고, 아래 명령의 `py`를 `python`으로 바꿔 실행합니다.

## 2. 저장소 내려받기

처음 받는 경우:

```bash
cd /c/Users/사용자명/Downloads
git clone https://github.com/NeighborfoodCapstone/Neighborfood.git
cd Neighborfood
```

이미 저장소가 있는 경우:

```bash
cd /c/저장소가_있는_경로/Neighborfood
git status -sb
git pull --ff-only origin main
```

로컬 변경이 있으면 먼저 내용을 확인하고 보관 또는 커밋한 뒤 pull합니다. 외부 서비스 키(`.env`)와 기존 로컬 DB(`data/neighborfood.db`) 데이터는 Git pull만으로 공유되지 않습니다.

## 3. 최초 1회 의존성 설치

저장소 루트에서 Python 패키지를 설치합니다.

```bash
py -m pip install -r requirements.txt
```

이어서 React 패키지를 설치합니다. QR 생성·스캔용 `qrcode`·`jsqr` 패키지가 포함되어 있습니다.

```bash
cd frontend-react
npm ci
```

`npm ci`가 lockfile 관련 오류로 중단되는 경우에만 `npm install`을 사용합니다. 설치가 실패하면 다음 단계로 넘어가지 말고 오류를 먼저 확인합니다.

설치 후 타입 검사와 빌드가 통과하는지 확인할 수 있습니다(선택). 이 명령은 서버를 켜지 않습니다.

```bash
npm run build
```

## 4. 서버 실행

Git Bash 창을 두 개 열고 각 서버를 따로 실행합니다. 두 창 모두 실행 상태로 유지해야 합니다.

### 첫 번째 창: FastAPI 백엔드

```bash
cd /c/저장소가_있는_경로/Neighborfood
py -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

정상 시작 로그는 다음과 같습니다.

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

- 백엔드: <http://127.0.0.1:8000>
- API 문서: <http://127.0.0.1:8000/docs>

`main:app` 모듈을 찾지 못하면 `main.py`가 있는 저장소 루트에서 실행했는지 확인합니다. 가상환경을 사용한다면 해당 환경을 활성화하고 그 환경의 Python으로 실행합니다.

### 두 번째 창: React 프론트엔드

```bash
cd /c/저장소가_있는_경로/Neighborfood/frontend-react
npm run dev
```

터미널에 다음과 비슷한 주소가 표시됩니다.

```text
Local: http://localhost:5173/
```

브라우저에서 표시된 `Local` 주소로 접속합니다. 5173번 포트를 다른 프로그램이 사용 중이면 5174처럼 다른 포트가 표시될 수 있으므로 터미널에 나온 주소를 기준으로 접속합니다.

React 화면 이동은 해시 경로를 사용합니다. 예를 들어 `http://localhost:5173/#/Fridge`(냉장고), `http://localhost:5173/#/Product_Detail?id=1`(게시글 상세)처럼 직접 열 수 있으며, 새로고침에 별도 서버 설정이 필요 없습니다. 전체 화면 목록은 `http://localhost:5173/#/Index`에서 볼 수 있습니다.

Vite 서버는 `/api`, `/posts`, `/uploads`, `/upload-images`, `/logout`, `/request-auth`, `/reset-password` 요청을 FastAPI(기본 `http://127.0.0.1:8000`)로 전달합니다. 기존 8000번 포트의 정적 HTML 주소(`http://127.0.0.1:8000/frontend/*.html`)에서는 React 화면이 표시되지 않습니다.

## 5. 다음부터 빠르게 실행하기

패키지 변경이 없으면 매번 설치·빌드를 반복하지 않아도 됩니다. 창 두 개에서 각각 실행합니다.

```bash
# 첫 번째 창 — API
cd /c/저장소가_있는_경로/Neighborfood
py -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
# 두 번째 창 — React
cd /c/저장소가_있는_경로/Neighborfood/frontend-react
npm run dev
```

## 6. 종료

각 서버가 실행 중인 Git Bash 창에서 `Ctrl+C`를 누르면 해당 서버가 종료됩니다.

## 7. 새로 받은 변경사항 반영

서버를 종료한 뒤 저장소 루트에서 실행합니다.

```bash
cd /c/저장소가_있는_경로/Neighborfood
git pull --ff-only origin main

cd frontend-react
npm ci
```

그다음 4번의 방법으로 백엔드와 React 서버를 다시 실행합니다.

## 8. 자주 발생하는 문제

### `localhost에서 연결을 거부했습니다`

접속하려는 서버가 꺼진 상태입니다. React 화면이라면 `npm run dev`, 백엔드라면 Uvicorn 실행 명령을 다시 실행합니다. 서버 창을 닫았거나 `Ctrl+C`로 종료하지 않았는지 확인합니다.

### 다른 주소로 이동하면 로그인이 풀려 있습니다

React 화면(`localhost:5173`)과 백엔드 정적 화면(`127.0.0.1:8000`)은 접속 주소(출처)가 달라 브라우저 `localStorage`의 로그인 토큰이 공유되지 않습니다. React는 자체 로그인 화면(`/#/Login`)을 가지므로 React에서 다시 로그인합니다.

### 화면은 열리지만 목록·로그인이 실패합니다

FastAPI 서버가 8000번 포트에서 실행 중인지 확인합니다. 백엔드 창에 `Application startup complete.`가 표시되는지, 브라우저에서 <http://127.0.0.1:8000/docs>가 열리는지 확인합니다.

### 메인 화면에 게시글이 없습니다

SQLite 데이터베이스 파일은 Git에 포함하지 않습니다. 새로 복제한 환경에서는 게시글 데이터가 없어 빈 화면 안내가 표시될 수 있습니다.

### `npm` 명령에서 package.json 오류가 납니다

현재 경로가 `frontend-react`인지 확인합니다.

### Python 모듈을 찾지 못합니다

저장소 루트에서 다음 명령을 다시 실행합니다. 가상환경을 사용한다면 해당 환경의 Python인지 확인합니다.

```bash
py -m pip install -r requirements.txt
```

### 지도·OCR 등 특정 기능만 실패합니다

필요한 외부 서비스 환경 설정(`.env`의 `KAKAO_JS_KEY`, `CLOVA_OCR_*`)과 백엔드 창의 로그를 확인합니다. 카메라(QR)·GPS 기능은 HTTPS 또는 `localhost`에서만 동작합니다.

### 다른 PC나 스마트폰에서 접속해야 합니다

`localhost`는 접속한 기기 자신을 뜻하므로, 위 안내는 서버를 켠 같은 PC에서 확인하는 방법입니다. 같은 네트워크의 다른 기기에서 확인하려면 React 서버를 외부 접속 허용 상태로 실행하고, 접속하는 기기에서는 React 터미널의 `Network` 주소로 접속합니다.

```bash
cd frontend-react
npm run dev -- --host 0.0.0.0
```

API 요청은 React 서버가 실행 PC의 FastAPI로 전달하므로 `frontend-react/.env.local` 설정은 필요하지 않습니다. 다만 카메라(QR)·GPS는 `localhost`가 아닌 주소에서는 HTTPS가 아니면 브라우저가 차단할 수 있습니다.

## 9. 환경 변수 안내

기본 화면 확인에는 별도의 비밀키가 필요하지 않습니다. OCR(CLOVA), 카카오 지도 등 외부 서비스를 사용하는 기능은 각자의 로컬 `.env` 설정이 필요합니다(템플릿: 루트 `.env.example`). 실제 키가 들어 있는 `.env` 파일은 GitHub에 올리지 않습니다.

- `NEIGHBORFOOD_BACKEND`(React 개발 서버, 선택): Vite 프록시가 API 요청을 전달할 백엔드 주소. 기본값은 `http://127.0.0.1:8000`입니다.
- `VITE_API_BASE_URL`(React 전용, 선택): 공개 API 주소를 직접 사용할 때만 `frontend-react/.env.local`에 넣습니다. 미설정 시 상대경로와 Vite 프록시를 사용하므로 로컬 개발에는 필요하지 않으며, 루트 `.env.example`에는 템플릿 항목이 없습니다. React 환경변수에는 비밀키를 넣지 않습니다.
- 배포 시에는 루트 `.env`의 `ALLOWED_ORIGINS`에 React 앱이 서빙되는 도메인을 반드시 추가해야 합니다(로컬 개발은 비워 두면 전체 허용). 정적 빌드(`dist`)로 배포할 때는 Vite 프록시가 없으므로 같은 API 프록시를 배포 서버에 구성하거나 `VITE_API_BASE_URL`로 공개 API 주소를 지정해야 합니다.

## 9-1. PortOne 테스트 결제 실행 (선택, 2026-10-05 추가)

정산 상세의 "테스트 결제" 화면을 쓰려면 루트 `.env`에 `portone.env.example`의 4개 항목을 추가합니다.

```text
PORTONE_TEST_ENABLED=true
PORTONE_STORE_ID=<PortOne V2 상점 ID>
PORTONE_CHANNEL_KEY=<테스트 채널 키>
PORTONE_API_SECRET=<API 시크릿>
```

- **반드시 PortOne 콘솔의 TEST 채널**을 사용합니다(LIVE 채널은 결제창에서 실제 청구가 가능). 서버도 채널 타입이 TEST가 아니면 성공으로 인정하지 않습니다.
- API 시크릿은 `.env`에만 두고 `VITE_` 변수·채팅·문서·스크린샷에 남기지 않습니다. 설정 후 백엔드를 재시작합니다.
- 흐름: 로그인 → 내 활동 → 정산 → 본인 정산 상세 → GPS 인증 → QR 인증 → "결제 확인으로" → 테스트 결제창 → 결과 확인. 설정 없이 `#/Payment_Preview`로 화면만 미리 볼 수 있고, `#/Payment_Quick`은 1,000원 빠른 테스트입니다.
- 테스트 결제는 정산의 납부 표시·완료 상태를 바꾸지 않습니다. 자동 테스트: `python -m pytest tests/test_portone.py`(pytest 별도 설치 필요, 외부 API mock). 상세는 `docs/PORTONE_TEST_SETUP.md`(⚠️ 2026-09-28 기준 작성본 — `quick-prepare`·`Payment_Quick`/`Payment_Preview`는 반영되지 않았고 API를 3종으로 기술, 현행은 4종).

## 9-2. 운영 서버에 배포하기 (요약)

- **백엔드**: 서버에서 `cd ~/Neighborfood && git pull` → `sudo systemctl restart neighborfood`
- **프런트**: 서버에서 빌드하지 말고(메모리 1GB) PC에서 `npm run build` 후 `dist/`를 서버 `~/Neighborfood/frontend-react/dist/`로 교체 업로드합니다(첫 업로드 후에만 서비스 재시작). 같은 도메인이므로 `VITE_API_BASE_URL`은 비워 둡니다.
- 운영 주소 `https://neighborfood.duckdns.org`(Nginx + Let's Encrypt). 점검·백업·장애 대응은 `NeighborFood_서버_실행_점검_가이드.md`를 따릅니다 (저장소 미포함 — 개별 보관).

## 10. 다음 점검 순서

1. 새로 받은 저장소에서 React 빌드와 API 시작을 확인합니다.
2. 로그인 → 메인 검색 → 게시글 상세 → 찜/신청 → 채팅 → 내 활동 흐름을 확인합니다.
3. 자동완성 폭·키보드 조작·로딩 종료·실패 후 재시도를 확인합니다.
4. 모바일 화면에서 사진·본문·하단 메뉴 배치를 확인합니다.
5. 카메라·GPS·QR·OCR 등 실제 기기 및 외부 API 기능을 점검합니다.

## 11. 관련 문서

| 문서 | 용도 |
|---|---|
| `README.md` | 프로젝트 개요·전체 실행 가이드·API 라우터 목록 |
| `Capstone.md` | 개발 컨텍스트·제약사항·범위 |
| `NeighborFood_Architecture_Plan.md` | 아키텍처·API 전체 목록·개발 이력·잔여 작업 |
| `neighborfood_ERD.md` | DB 구조(ERD)·디렉토리 구조 |
| `frontend-react/docs/DESIGN_CONTEXT.md` | React 공통 디자인·로딩·자동완성·게시글 상세 기준 |
| `frontend-react/docs/MIGRATION_REPORT.md` | 화면 39개 React 이전 매핑·검증 범위·미검증 범위 |
| `NeighborFood_서버_실행_점검_가이드.md` | 운영 서버 실행·점검·갱신 배포·장애 대응 | *(저장소 미포함 — 개별 보관)*
| `docs/PORTONE_TEST_SETUP.md` | PortOne 테스트 결제 설정·범위·제한 |