# NeighborFood — 개발환경 세팅 & 기여 가이드

> 프로젝트: 지역 기반 식재료 공동구매 플랫폼  
> 저장소: https://github.com/NeighborfoodCapstone/Neighborfood.git  
> 최종 수정: 2026-06-02

---

## 목차

1. [사전 준비 — 필수 소프트웨어 설치](#1-사전-준비)
2. [처음 한 번만 — 환경 세팅](#2-최초-환경-세팅)
3. [서버 실행 방법](#3-서버-실행)
4. [코드 수정 & GitHub 업로드 워크플로](#4-코드-수정--github-워크플로)
5. [브랜치 전략](#5-브랜치-전략)
6. [자주 발생하는 오류 해결](#6-오류-해결)

---

## 1. 사전 준비

새 PC(학교 실습실 포함)에서 시작하기 전에 아래 세 가지가 설치되어 있어야 합니다.

| 소프트웨어 | 최소 버전 | 다운로드 |
|---|---|---|
| Python | 3.10 이상 | https://www.python.org/downloads/ |
| Git | 최신 버전 | https://git-scm.com/downloads |
| VS Code | 최신 버전 | https://code.visualstudio.com/ |

### 설치 후 확인

```bash
python --version   # Python 3.10.x 이상 출력되면 OK
git --version      # git version 2.x.x 출력되면 OK
code --version     # VS Code 버전 출력되면 OK
```

> ⚠️ **Python 설치 시 반드시** "Add Python to PATH" 항목에 체크해야 합니다.  
> 체크하지 않으면 `python` 명령어가 동작하지 않습니다.

### VS Code 권장 확장 프로그램

VS Code 실행 후 Extensions(`Ctrl+Shift+X`)에서 아래 항목을 검색해 설치합니다.

| 확장 프로그램 | ID | 용도 |
|---|---|---|
| Python | `ms-python.python` | Python 자동완성·실행 |
| Live Server | `ritwickdey.liveserver` | HTML 실시간 미리보기 |
| SQLite Viewer | `qwtel.sqlite-viewer` | DB 파일 내용 확인 |

---

## 2. 최초 환경 세팅

> 새 PC에서 **처음 한 번만** 실행합니다.

### Step 1 — 저장소 클론

```bash
cd C:\Projects
git clone https://github.com/NeighborfoodCapstone/Neighborfood.git
cd Neighborfood
```

### Step 2 — VS Code로 열기

```bash
code .
```

### Step 3 — Python 가상환경 생성 및 활성화

VS Code 터미널(`Ctrl + `` `)에서 실행합니다.
-
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Mac / Linux)
source venv/bin/activate
```

> ✅ 터미널 프롬프트 앞에 **(venv)** 가 붙으면 활성화 성공입니다.

### Step 4 — 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### Step 5 — 환경변수 파일 생성

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

> 📌 `.env` 파일은 Git에 올라가지 않습니다. PC마다 각자 생성해야 합니다.

---

## 3. 서버 실행

### 매일 작업 시작 시

```bash
# 1. 가상환경 활성화
venv\Scripts\activate

# 2. 최신 코드 받기 (항상 먼저 실행!)
git pull origin main

# 3. 백엔드 서버 실행
uvicorn main:app --reload
```

서버가 켜지면 아래 주소로 접속해 확인합니다.

| 주소 | 내용 |
|---|---|
| http://127.0.0.1:8000/docs | API 전체 목록 (Swagger UI) |
| http://127.0.0.1:8000/api/qr/health | QR API 상태 확인 |
| http://127.0.0.1:8000/api/receipt/health | 영수증 API 상태 확인 |

### 프론트엔드 실행 방법

**방법 A — Live Server (일반 화면용)**

VS Code 파일 탐색기에서 HTML 파일 우클릭 → **Open with Live Server**  
접속 주소: `http://127.0.0.1:5500/frontend/파일명.html`

**방법 B — FastAPI 통해 열기 (QR·인증 화면 필수)**

```
http://127.0.0.1:8000/frontend/QR_Scan.html
http://127.0.0.1:8000/frontend/Verify.html
http://127.0.0.1:8000/frontend/Receipt_Verify.html
```

> ⚠️ 카메라(QR 스캔)가 필요한 화면은 반드시 **방법 B**를 사용해야 합니다.  
> 브라우저 보안 정책상 카메라는 `localhost(8000)` 에서만 허용됩니다.

### 서버 종료

```bash
Ctrl + C   # 터미널에서 서버 중단
deactivate # 가상환경 비활성화 (선택)
```

---

## 4. 코드 수정 & GitHub 워크플로

> 환경 세팅이 완료된 상태에서 매일 반복하는 작업 흐름입니다.

### 전체 흐름

```
최신 코드 받기 → 코드 수정 → 테스트 → 스테이징 → 커밋 → 푸시
```

---

### Step 1 — 작업 시작 전 최신 코드 받기

```bash
git pull origin main
```

> ✅ 작업을 시작하기 전 **반드시** 먼저 실행합니다.  
> 동료가 어제 수정한 내용을 내 PC에 반영합니다.

---

### Step 2 — 코드 수정

VS Code에서 파일을 수정하고 저장합니다 (`Ctrl + S`).  
`--reload` 옵션 덕분에 저장 시 서버가 자동으로 재시작됩니다.

---

### Step 3 — 변경 내용 확인

```bash
git status        # 변경된 파일 목록 확인
git diff          # 변경된 내용 상세 확인
```

---

### Step 4 — 스테이징 (올릴 파일 선택)

```bash
# 전체 변경 파일 스테이징
git add .

# 특정 파일만 스테이징
git add app/routers/qr.py
git add frontend/QR_Scan.html
```

---

### Step 5 — 커밋 (변경 내용 저장)

```bash
git commit -m "커밋 메시지"
```

**좋은 커밋 메시지 예시**

```bash
git commit -m "fix: QR 검증 실패 시 not_found 반환값 수정"
git commit -m "feat: 거래 영수증 발급 API 추가"
git commit -m "refactor: auth_db.py with 컨텍스트 매니저 적용"
git commit -m "docs: README 실행 방법 업데이트"
```

**나쁜 커밋 메시지 예시**

```bash
git commit -m "수정"       # ❌ 무엇을 수정했는지 알 수 없음
git commit -m "fix"        # ❌ 너무 모호함
git commit -m "업데이트"   # ❌ 내용 없음
```

---

### Step 6 — 푸시 (GitHub에 업로드)

```bash
git push origin main
```

---

### 전체 명령어 한눈에 보기

```bash
# ── 매일 작업 시작 ──────────────────────────────────
venv\Scripts\activate          # 가상환경 켜기
git pull origin main           # 최신 코드 받기
uvicorn main:app --reload      # 서버 실행

# ── 작업 완료 후 GitHub에 올리기 ─────────────────────
git add .                      # 변경 파일 선택
git commit -m "작업 내용 설명" # 변경 내용 저장
git push origin main           # GitHub에 업로드

# ── 종료 ────────────────────────────────────────────
Ctrl + C                       # 서버 끄기
deactivate                     # 가상환경 끄기
```

---

## 5. 브랜치 전략

새 기능을 개발할 때는 `main` 브랜치를 직접 수정하지 않고 별도 브랜치를 만듭니다.

```bash
# 1. 새 브랜치 만들고 이동
git checkout -b feature/기능이름

# 예시
git checkout -b feature/receipt-trade
git checkout -b fix/qr-verify-bug

# 2. 작업 후 커밋
git add .
git commit -m "feat: 거래 영수증 API 추가"

# 3. GitHub에 올리기
git push origin feature/receipt-trade

# 4. GitHub에서 Pull Request 생성 → 팀원 확인 → main 병합
```

**브랜치 네이밍 규칙**

| 접두사 | 용도 | 예시 |
|---|---|---|
| `feature/` | 새 기능 개발 | `feature/receipt-trade` |
| `fix/` | 버그 수정 | `fix/qr-verify-bug` |
| `refactor/` | 코드 구조 개선 | `refactor/auth-module` |
| `docs/` | 문서 작업 | `docs/readme-update` |

---

## 6. 오류 해결

### "No module named 'fastapi'"

```bash
# 가상환경이 꺼진 상태. 다시 활성화
venv\Scripts\activate
```

### "Address already in use" (포트 충돌)

```bash
# 8000번 포트 사용 중인 프로세스 찾기
netstat -ano | findstr :8000

# PID로 종료 (예: PID가 1234인 경우)
taskkill /PID 1234 /F
```

### "fatal: not a git repository"

```bash
git init
git branch -M main
git remote add origin https://github.com/NeighborfoodCapstone/Neighborfood.git
```

### "Updates were rejected" (push 거부)

```bash
# 원격 변경사항을 먼저 받아오기
git pull origin main
# 이후 다시 push
git push origin main
```

### .db 파일이 git status에 보일 때

```bash
# Git 추적에서 제거 (파일은 유지됨)
git rm --cached data/auth.db
git rm --cached data/qr_auth.db
git rm --cached data/receipt_auth.db
```

### Live Server에서 카메라 권한 거부

QR_Scan.html은 Live Server(5500포트)가 아닌 FastAPI(8000포트)로 열어야 합니다.

```
http://127.0.0.1:8000/frontend/QR_Scan.html
```

---

## 프로젝트 폴더 구조 참고

```
Neighborfood/
├── main.py                  # FastAPI 서버 시작점
├── requirements.txt         # Python 패키지 목록
├── .env.example             # 환경변수 템플릿
├── .gitignore
├── README.md
│
├── app/                     # 백엔드 코어
│   ├── config.py
│   ├── core/utils.py
│   ├── db/                  # DB 연결 및 스키마
│   │   ├── auth_db.py
│   │   ├── qr_db.py
│   │   └── receipt_db.py
│   ├── models/              # Pydantic 모델
│   └── routers/             # API 라우터
│       ├── auth.py
│       ├── posts.py
│       ├── qr.py
│       └── receipt.py
│
├── sql/                     # DB 스키마 정의 SQL 파일
├── frontend/                # HTML 화면 파일들
│
├── data/          ← Git 제외  # SQLite DB 파일 (자동 생성)
├── uploads/       ← Git 제외  # 업로드 이미지
└── venv/          ← Git 제외  # Python 가상환경
```

---

*NeighborFood Capstone Team · 2026*