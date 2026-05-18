# NeighborFood — 게시글 등록·검색·열람 모듈

졸업작품 시연용 PWA 플랫폼의 핵심 기능 구현입니다.
**`게시글 작성 → 게시판 등록 → 검색 후 열람`** 흐름 + 공동구매 참여까지 동작합니다.

---

## 📦 포함 파일

| 파일 | 역할 |
|------|------|
| `main.py` | FastAPI 백엔드 (인증 + 게시글 + 이미지 업로드 API) |
| `Create_Post.html` | 게시글 작성 화면 |
| `Search.html` | 검색어 입력 화면 |
| `Search_Results.html` | 검색 결과 목록 화면 |
| `Product_Detail.html` | 나눔/교환 게시글 상세 화면 |
| `Group_Buy_Detail.html` | 공동구매 게시글 상세 화면 |

---

## 🚀 실행 방법

### 1. 의존성 설치

```bash
pip install fastapi uvicorn python-multipart pydantic
```

### 2. 백엔드 서버 실행

```bash
python main.py
```

서버가 `http://127.0.0.1:5500` 에서 기동됩니다.
처음 실행하면 같은 폴더에 `auth.db` (SQLite) 와 `uploads/` (이미지 저장소) 가 자동 생성됩니다.

### 3. 프론트엔드 실행

HTML 파일들을 같은 폴더에 둔 채로 **간단한 정적 서버**로 열어야 합니다.
(파일을 더블클릭해서 `file://` 로 열면 CORS 때문에 fetch가 막힙니다.)

```bash
# 새 터미널에서 같은 폴더에서 실행
python -m http.server 5500
```

브라우저에서 `http://127.0.0.1:5500/Create_Post.html` 같은 식으로 접속.

---

## 🗄️ 데이터베이스 구조

기존 `auth_codes` 테이블 + 새로 추가된 `posts` 테이블:

```sql
CREATE TABLE posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,        -- 'share' | 'exchange' | 'groupbuy'
    title           TEXT NOT NULL,
    description     TEXT,
    category        TEXT,                 -- '채소' | '과일' | ...
    images          TEXT DEFAULT '[]',    -- JSON 문자열 (파일명 배열)
    address         TEXT,
    lat             REAL,
    lng             REAL,
    author_id       TEXT NOT NULL,        -- 시연용 하드코딩
    status          TEXT DEFAULT 'active',
    created_at      TEXT NOT NULL,
    expires_at      TEXT,
    -- 공동구매 전용
    gb_target       INTEGER,
    gb_current      INTEGER DEFAULT 0,
    gb_price        INTEGER,
    -- 교환 전용
    exchange_want   TEXT
);
```

**나눔·교환·공동구매를 한 테이블에 합쳤고 `type` 컬럼으로 구분합니다.**

---

## 🔌 API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/upload-images` | 이미지 파일들을 업로드. `multipart/form-data` 로 보내면 서버가 uuid 파일명으로 저장 후 파일명 배열 반환 |
| `POST` | `/posts` | 게시글 등록. JSON 바디로 모든 필드를 받음 |
| `GET`  | `/posts` | 게시글 목록. `?keyword=` `?type=` `?category=` 쿼리스트링 지원 |
| `GET`  | `/posts/{id}` | 게시글 상세 |
| `POST` | `/posts/{id}/join` | 공동구매 참여 인원 +1 |

이미지 정적 서빙: `GET /uploads/{filename}` 으로 업로드된 이미지에 접근 가능.

FastAPI 자동 문서: `http://127.0.0.1:5500/docs` 에서 모든 엔드포인트를 테스트해볼 수 있습니다.

---

## 🎬 시연 시나리오

### A. 게시글 작성 → 등록

1. `Create_Post.html` 접속
2. 거래 유형 선택 (나눔 / 교환 / 공동구매)
3. 사진 영역의 ➕ 클릭 → 로컬 이미지 선택 → 자동 업로드
4. 제목·카테고리·설명 입력
5. 교환이면 "원하는 품목", 공동구매면 "목표 인원·1인당 가격" 입력
6. 하단 **"게시하기"** 클릭 → 등록 성공 시 자동으로 해당 글의 상세 페이지로 이동

### B. 검색 → 열람

1. `Search.html` 접속
2. 검색어 입력 후 Enter 또는 "검색" 버튼
3. `Search_Results.html?keyword=...` 로 이동, 결과가 카드로 렌더링
4. 상단 탭(전체/나눔/공동구매/교환)으로 타입별 필터링
5. 카드 클릭 시 자동으로 적절한 상세 페이지로 이동:
   - 공동구매 → `Group_Buy_Detail.html?id=...`
   - 그 외 → `Product_Detail.html?id=...`

### C. 공동구매 참여

1. 공동구매 상세 페이지 하단의 **"참여 신청하기"** → `Reservation.html?id=...` 로 이동
2. (현재 Reservation.html은 폼만 있고 백엔드 연동 X — 다음 단계에서 진행)
3. API 호출 자체는 `POST /posts/{id}/join` 으로 동작 검증됨

---

## ⚙️ 시연용 단순화 사항

- **로그인 미연동**: `Create_Post.html` 상단에 `CURRENT_USER_ID = 'user_demo_01'` 로 하드코딩 (값을 바꾸면 다른 유저로 가장 가능)
- **위치 좌표**: `Create_Post.html` 작성 시 한들마을 3단지 좌표(37.5452, 127.0865)로 고정 송신
- **API 주소**: 모든 프론트 파일 상단에 `const API_BASE = 'http://127.0.0.1:5500';` — 배포 시 실제 서버 주소로 교체
- **CORS**: `main.py` 의 `allow_origins=["*"]` — 배포 시 실제 도메인으로 제한 필요

---

## 🧪 검증 결과

자체 통합 테스트로 다음 항목이 모두 통과되었습니다:

- 3가지 타입(share/exchange/groupbuy) 등록 ✅
- 이미지 다중 업로드 + JSON 직렬화/복원 ✅
- 키워드 검색 (제목·설명 LIKE) ✅
- 타입 필터 / 카테고리 필터 ✅
- 게시글 상세 조회 ✅
- 공동구매 참여 카운터 증가 & 정원 초과 차단 (409) ✅
- 404 / 400 / 확장자 검증 등 에러 케이스 ✅
- 5개 HTML 파일 JS 구문 검증 ✅

---

## 🔜 다음 단계 (제안)

1. `Reservation.html` 백엔드 연동 (공동구매는 `/posts/{id}/join`, 나눔은 채팅 시작)
2. 사용자 인증 시스템 (`users` 테이블 + 로그인 토큰)
3. `Home.html` 피드를 실제 `/posts` API에서 받아오기
4. 채팅 (`Chat_Detail.html`, `Chat_List.html`) 백엔드 — WebSocket 권장
5. 거래 완료 처리 → 후기 작성 (`Review.html`) 흐름