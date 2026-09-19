# Neighborfood React 실행 안내

이 문서는 GitHub 저장소를 공유받은 사람이 Neighborfood의 FastAPI 백엔드와 React 프론트엔드를 로컬에서 실행하기 위한 안내서입니다.

현재 `frontend-react`는 전체 화면 이전본이 아니라 **홈 화면만 React로 재구현한 부분 마이그레이션 단계**입니다(기존 정적 HTML `frontend/`와 병행하는 하이브리드 구조). 홈 화면의 게시글 목록은 FastAPI의 `GET /posts`를 호출하므로 백엔드와 React 서버를 함께 실행해야 합니다. 지도·등록·내 활동·마이페이지 등 나머지 메뉴는 백엔드가 서빙하는 기존 정적 HTML(`http://127.0.0.1:8000/frontend/*.html`)로 이동합니다.

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
git pull origin main
```

## 3. 최초 1회 의존성 설치

저장소 루트에서 Python 패키지를 설치합니다.

```bash
py -m pip install -r requirements.txt
```

이어서 React 패키지를 설치합니다.

```bash
cd frontend-react
npm ci
```

`npm ci`가 lockfile 관련 오류로 중단되는 경우에만 `npm install`을 사용합니다.

## 4. 서버 실행

Git Bash 창을 두 개 열고 각 서버를 따로 실행합니다. 두 창 모두 실행 상태로 유지해야 합니다.

### 첫 번째 창: FastAPI 백엔드

```bash
cd /c/저장소가_있는_경로/Neighborfood
py -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

정상 실행 시 다음 주소를 사용할 수 있습니다.

- 백엔드: <http://127.0.0.1:8000>
- API 문서: <http://127.0.0.1:8000/docs>

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

## 5. 종료

각 서버가 실행 중인 Git Bash 창에서 `Ctrl+C`를 누르면 해당 서버가 종료됩니다.

## 6. 새로 받은 변경사항 반영

서버를 종료한 뒤 저장소 루트에서 실행합니다.

```bash
cd /c/저장소가_있는_경로/Neighborfood
git pull origin main

cd frontend-react
npm ci
```

그다음 4번의 방법으로 백엔드와 React 서버를 다시 실행합니다.

## 7. 자주 발생하는 문제

### `localhost에서 연결을 거부했습니다`

접속하려는 서버가 꺼진 상태입니다. React 화면이라면 `npm run dev`, 백엔드라면 Uvicorn 실행 명령을 다시 실행합니다.

### 다른 메뉴로 이동하면 로그인이 풀려 있습니다

React 화면(`localhost:5173`)과 백엔드 정적 화면(`127.0.0.1:8000`)은 접속 주소(출처)가 달라 브라우저 `localStorage`의 로그인 토큰이 공유되지 않습니다. 현재 React 쪽에는 로그인이 필요한 화면이 없어 홈 피드 조회에는 영향이 없으며, 정적 화면으로 이동한 뒤 그쪽에서 로그인하면 됩니다. 인증 공유 방식은 후속 정책 결정 사항입니다(`Capstone.md`, `NeighborFood_Architecture_Plan.md` §8 참고).

### 화면은 열리지만 게시글을 불러오지 못합니다

FastAPI 서버가 8000번 포트에서 실행 중인지 확인합니다. 브라우저에서 <http://127.0.0.1:8000/docs>가 열리는지도 확인합니다.

### 메인 화면에 게시글이 없습니다

SQLite 데이터베이스 파일은 Git에 포함하지 않습니다. 새로 복제한 환경에서는 게시글 데이터가 없어 빈 화면 안내가 표시될 수 있습니다.

### Python 모듈을 찾지 못합니다

저장소 루트에서 다음 명령을 다시 실행합니다.

```bash
py -m pip install -r requirements.txt
```

### 다른 PC나 스마트폰에서 접속해야 합니다

백엔드와 React를 다음처럼 외부 접속 허용 상태로 실행합니다.

```bash
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
cd frontend-react
npm run dev -- --host 0.0.0.0
```

이 경우 `frontend-react/.env.local`에 실행 PC의 내부 IP를 지정한 뒤 React 서버를 재시작해야 합니다.

```dotenv
VITE_API_BASE_URL=http://실행_PC_IP:8000
```

접속하는 기기와 실행 PC가 같은 네트워크에 있어야 하며, 브라우저에서는 React 터미널의 `Network` 주소로 접속합니다.

## 8. 환경 변수 안내

기본 메인 화면 확인에는 별도의 비밀키가 필요하지 않습니다. OCR(CLOVA), 카카오 지도 등 외부 서비스를 사용하는 기능은 각자의 로컬 `.env` 설정이 필요합니다(템플릿: 루트 `.env.example`). 실제 키가 들어 있는 `.env` 파일은 GitHub에 올리지 않습니다.

- `VITE_API_BASE_URL`(React 전용)은 `frontend-react/.env.local`에 넣습니다. 루트 `.env.example`에는 아직 템플릿 항목이 없습니다.
- 배포 시에는 루트 `.env`의 `ALLOWED_ORIGINS`에 React 앱이 서빙되는 도메인을 반드시 추가해야 합니다(로컬 개발은 비워 두면 전체 허용).

## 9. 관련 문서

| 문서 | 용도 |
|---|---|
| `README.md` | 프로젝트 개요·전체 실행 가이드·API 라우터 목록 |
| `Capstone.md` | 개발 컨텍스트·제약사항·범위 |
| `NeighborFood_Architecture_Plan.md` | 아키텍처·API 전체 목록·개발 이력·잔여 작업 |
| `neighborfood_ERD.md` | DB 구조(ERD)·디렉토리 구조 |