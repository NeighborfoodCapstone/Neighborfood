# NeighborFood

지역 기반 식재료 공동구매 플랫폼 — FastAPI 백엔드(DB·파일 저장소는 **SQLite·로컬 `uploads/`가 기본**, 환경변수 설정 시에만 **Supabase(PostgreSQL)·Supabase Storage** 사용), React(Vite) 프런트엔드(기존 화면 39개 전체 이전 구현) + 기존 정적 HTML 프런트엔드(병행 보존)

버전: **v2.1.0** (2026-08-22)
문서 최종 갱신: 2026-10-12 (팀원 박준기 푸시 2건 반영 — `b6859f0`(10/12) **Supabase(PostgreSQL)·Supabase Storage 선택 지원**(`DATABASE_URL`·`SUPABASE_URL`이 있을 때만 활성, 없으면 기존 SQLite·로컬 `uploads/` 그대로), 게시글 사진 업로드·영수증 API **로그인 필수 + 본인 영수증만 처리**, 영수증 이미지 서명 URL 조회(`GET /api/receipt/image/{name}`), `migrations/001_supabase.sql`·`scripts/`·`docs/SUPABASE_MIGRATION.md`·`supabase.env.example` 신규. `fc80abd`(10/11) QR 스캔 화면 구성 변경·영수증 분석 중 상태 표시·프로필 사진 업로드·신뢰온도 게이지(`TrustTemperature.tsx`). **배포 방식은 Oracle 유지 / Vercel+Supabase 전환 두 방향을 모두 열어 두고, 부하테스트 후 10/16 체크포인트에서 확정**합니다. pytest 32개 통과(2026-10-12 확인). 미검증: Supabase 실연결·Vercel 배포·CLOVA OCR·휴대폰 카메라·PortOne 외부 호출 — 최종 결정 전에 검증 예정). 이전 갱신: 2026-10-08 (2026-10-08 구현 완료 — 그룹 채팅 거래 액션 바(B안: 약속·정산·GPS·QR 링크)·로그인 상태 비밀번호 변경 API(`PATCH /api/users/me/password`)·공개 공지 API(`GET /api/notices`)·게시글 수정 API 확장(사진·유형·인원·가격)·정산 흐름 자동화 테스트(`tests/test_settlement_flow.py` 등 pytest 12개 신규)·QR 발급 화면 토큰 표시·복사 줄 추가(`qr.tsx`). 같은 날 수동 UI 검증(액션 바·비밀번호 변경·공지·게시글 수정) 통과. 남은 작업: PWA·PortOne 서버 검증·실환경(기기) 검증·서버 운영 마무리.). 이전 갱신 내용: 2026-10-08 잔여 작업 방침 확정 — 시연·발표 전 처리(그룹 채팅 액션 바·PortOne 서버 검증·실환경 검증·서버 운영 마무리)와 구현/제외 결정 항목(비밀번호 변경·공개 공지·게시글 수정 API·PWA)은 모두 작업 예정, 정적 HTML 폐기는 구현 100% 완료 후 영향 점검 뒤 진행, 선택 사항은 별도 시점에 처리)
이전 갱신: 2026-10-07 (GitHub `ec1da57`(main) 기준 문서-저장소 정합성 점검 — 저장소에 없는 문서 참조 표기, 화면 수(39+4) 표기, 팀원 `PORTONE_TEST_SETUP.md` 시점 차이 주석, 낡은 문구 정정·`frontend/shared/profile.js` 부재 정정)
이전 갱신: 2026-10-06 (운영 서버 HTTPS 배포 완료·PortOne V2 테스트 결제 연동 반영: 주요 기능·라우터 표·폴더 구조·알려진 제한·관련 문서 갱신)
이전 갱신: 2026-09-21 (React 전체 화면 이전·공통 디자인·로딩·자동완성·게시글 상세 개선 반영, 공개 공지 API 미구현 정정, 게시글 수정 범위 정정, `frontend-react/docs/` 문서 추가)
이전 갱신: 2026-09-19 (문서-소스 정합성 점검 반영: `reset_db.py` 존재 확인, 라우터 경로 정정, 미구현 API(비밀번호 변경) 표기, 관련 문서 목록 추가)
이전 갱신: 2026-09-14 (`frontend-react/`(Vite + React 19 + TypeScript) 신규 추가 — 홈 화면 부분 마이그레이션 반영)

---

## 주요 기능

- 회원가입 / 로그인 (login_id + 비밀번호, PBKDF2-SHA256)
- 게시글 작성·수정·삭제 (나눔 / 공동구매 / 교환), 자동 만료 처리
- 공동구매 참여 / 취소 (원자적 카운터, 중복·정원·미납 차단)
- 공동구매 정산 (분담금 자동 계산, GPS→QR 2단계 순차 인증 후 납부 활성화, 노쇼 신고/취소)
- QR 코드 대면 거래 인증 (`frontend/vendor/html5-qrcode.min.js` 로컬 사본 우선 로드 → CDN 장애 시에도 스캔 동작)
- 영수증 OCR 인증 (CLOVA OCR → Tesseract fallback, v2.1 마트형 파서 지원)
- 냉장고 관리 (영수증 인증 품목 자동 등록, 유통기한 D-day)
- 1:1 / 그룹 채팅 (REST 폴링, 참여 취소 시 시스템 메시지 삽입)
- 매너 평가 (thumbs up/down → trust_score 반영)
- 찜(위시리스트), 신고, 공지사항
- GPS 위치 인증 (Haversine 100m 서버 재검증)
- 카카오맵 연동 (`.env` 동적 로드, 소스코드 키 하드코딩 금지)
- 관리자 대시보드 (회원·신고·공지·채팅 모니터링)
- PortOne V2 **테스트 결제** (정산 상세 → 결제 확인 → 테스트 결제창, 테스트 채널 전용·실결제 아님·정산 납부 상태 불변, 2026-10-05)
- 운영 서버: Oracle Cloud + Nginx + Let's Encrypt HTTPS(`https://neighborfood.duckdns.org`), 로컬 빌드 `dist/`를 FastAPI가 서빙 (2026-10-03)
- **Supabase(PostgreSQL)·Supabase Storage 선택 지원** (2026-10-12, 팀원 박준기) — `DATABASE_URL`을 설정하면 PostgreSQL(Transaction pooler), `SUPABASE_URL`·`SUPABASE_SECRET_KEY`를 설정하면 이미지가 Supabase Storage에 저장됩니다. 미설정이면 기존 SQLite·로컬 `uploads/`로 동작하므로 **Oracle 서버 방식과 Vercel+Supabase 방식을 모두 열어 둔 상태**입니다(방식 확정은 10/16 체크포인트, §4-1).
- 프로필 사진 업로드·신뢰온도 게이지 (2026-10-11, React `auth.tsx`·`TrustTemperature.tsx`), 영수증·사진 업로드 로그인 필수 및 본인 영수증 전용 처리 (2026-10-12)
- **(2026-09-20~21) React(Vite) 프런트엔드** — `frontend-react/`에 기존 정적 HTML 39개 화면 식별자를 React(TypeScript)로 이전(인증·게시글·냉장고·거래·채팅·정산·위치·QR·영수증·관리자). 공통 디자인·공통 로딩·자동완성·게시글 상세 개선 적용. 기존 정적 HTML은 최종 점검이 끝나기 전까지 병행 보존 (§5 및 "React 프런트엔드" 안내 참고) ※ 화면 수: 기존 HTML 이전분 39개 + PortOne 결제 화면 4개(`Payment_Checkout`·`Payment_Result`·`Payment_Quick`·`Payment_Preview`, 2026-10-05 신규) = `routes.tsx` `screens` 기준 총 43개.

---

## 요구사항

- Python 3.10 이상
- Node.js 20 이상 (React 프런트엔드 `frontend-react/` 실행 시 필요 — `npm` 포함)
- (선택) CLOVA OCR API 키 — 없으면 Tesseract fallback 사용
- (선택) Kakao Developers JavaScript 키 — 지도 기능 사용 시 필요
- (선택) Supabase 프로젝트(서울 리전) — PostgreSQL·Storage 모드 사용 시 필요 (`psycopg[binary]`, `python-dotenv`는 `requirements.txt`에 포함)

---

## 시작하기

### 1. 저장소 클론

```bash
git clone https://github.com/NeighborfoodCapstone/Neighborfood.git
cd Neighborfood
```

### 2. 가상환경 설정 및 패키지 설치

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

`.env` 파일을 열어 필요한 값을 채웁니다:

```
CLOVA_OCR_INVOKE_URL=   # CLOVA OCR Invoke URL (선택)
CLOVA_OCR_SECRET=       # CLOVA OCR Secret Key (선택)
KAKAO_JS_KEY=           # 카카오 JS API 키 (지도 기능 사용 시 필요)
ALLOWED_ORIGINS=        # CORS 허용 도메인(콤마 구분). 비우면 * 허용 — 배포 시 실제 도메인 필수
PORTONE_TEST_ENABLED=   # (선택) PortOne 테스트 결제 사용 시 true — 템플릿: portone.env.example
PORTONE_STORE_ID=       # (선택) PortOne V2 상점 ID
PORTONE_CHANNEL_KEY=    # (선택) PortOne **테스트 채널** 키 (LIVE 채널 금지)
PORTONE_API_SECRET=     # (선택) PortOne API 시크릿 — 서버 .env에만, VITE_ 변수·채팅·문서 금지
```

> `.env` 파일은 `.gitignore`에 포함되어 있으므로 GitHub에 올라가지 않습니다. 2026-10-12부터 `.env.*`(단 `.env.example`·`*.env.example` 제외), `.supabase_patch_backups/`도 Git 추적 제외입니다. 서버는 시작 시 프로젝트 루트의 `.env`를 `python-dotenv`로 읽습니다(이미 설정된 환경변수는 덮어쓰지 않음).
> Supabase를 쓸 때만 `DATABASE_URL`·`DATABASE_SSLMODE`·`SUPABASE_URL`·`SUPABASE_SECRET_KEY`를 추가합니다. 템플릿은 `supabase.env.example`이며(기존 OCR·PortOne·Kakao 값을 지우지 말고 **추가**), 비밀번호·secret key는 문서·채팅·Git에 적지 않습니다. 자세한 절차는 §4-1과 `docs/SUPABASE_MIGRATION.md`를 참고하세요.
> `PORTONE_*` 4개 항목은 `.env.example`에는 없고 별도 템플릿 `portone.env.example`에만 있습니다. PortOne 테스트 결제를 쓸 때 그 내용을 `.env`에 추가하세요(위 블록의 `PORTONE_*` 줄은 추가할 항목의 예시입니다).

### 4. 서버 실행

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

서버가 실행되면 브라우저에서 접속합니다:

- 홈: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API 문서 (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- 프런트엔드: [http://127.0.0.1:8000/frontend/Home.html](http://127.0.0.1:8000/frontend/Home.html)

> DB 파일(`data/neighborfood.db`)은 서버 첫 실행 시 자동으로 생성됩니다. (`DATABASE_URL`이 설정되어 있으면 SQLite 파일 대신 PostgreSQL에 연결하며, 이때는 아래 §4-1의 스키마 적용이 먼저 필요합니다.)

### 4-1. (선택) Supabase(PostgreSQL)·Storage 모드 — 2026-10-12, 팀원 박준기 (`b6859f0`)

기존 화면·URL·필드·Bearer 로그인·PortOne 테스트 결제 흐름은 그대로 두고, **DB 연결 계층과 이미지 저장소만** 교체할 수 있게 한 기능입니다. 기본값(환경변수 미설정)은 SQLite + 로컬 `uploads/`입니다.

| 환경변수 | 효과 |
|---|---|
| `DATABASE_URL` (+ `DATABASE_SSLMODE`, 기본 `require`) | 설정 시 `app/db/base.py`의 `make_conn()`이 SQLite 대신 `app/db/postgres.py`의 PostgreSQL 연결(Transaction pooler, prepared statements 비활성)을 반환합니다. 기존 SQLite 문법(`?` 자리표시자, `INSERT OR IGNORE/REPLACE`, `date('now')`, `MAX(a,b)` 등)은 이 계층이 변환합니다. |
| `SUPABASE_URL`, `SUPABASE_SECRET_KEY` | 설정 시 게시글 사진은 공개 버킷 `food-images`, 영수증 사진은 비공개 버킷 `receipts`에 저장되고(`app/storage.py`), `/uploads/{파일명}`은 공개 URL로 307 리다이렉트됩니다. |
| `VERCEL` | Vercel 실행 시 SQLite 대체·로컬 업로드를 거부하고(`DATABASE_URL`·Supabase 설정 필수), 데이터·업로드 경로를 `/tmp/neighborfood`로 바꿉니다. |

적용 순서(요약 — 전체 절차·롤백·Vercel 환경변수는 `docs/SUPABASE_MIGRATION.md`):

```bash
python -m pip install -r requirements.txt     # psycopg[binary], python-dotenv 포함
python scripts/configure_supabase.py          # DB 비밀번호·secret key를 숨김 입력으로 .env에 기록
python scripts/supabase_migrate.py            # 빈 DB에 migrations/001_supabase.sql 적용 (버전 28190b4-v1)
python scripts/check_supabase.py              # 연결·스키마 버전·버킷(food-images 공개 / receipts 비공개) 읽기 전용 점검
# 기존 데이터를 옮길 때만:
python scripts/import_sqlite.py data/neighborfood.db
python scripts/import_uploads.py uploads
```

> ⚠️ **PostgreSQL 모드 주의사항 (2026-10-12 정적 점검, 실제 Supabase 연결 검증 전)**
> - PostgreSQL 모드에서는 서버가 `CREATE TABLE`·`ALTER TABLE`·`CREATE INDEX`를 실행하지 않습니다(테이블이 없으면 "Run scripts/supabase_migrate.py" 오류). 스키마 변경은 마이그레이션 파일로만 적용합니다. `migrations/001_supabase.sql`은 커밋 `28190b4` 시점의 초기화 스키마(앱 테이블 21개 + `neighborfood_schema_version`)입니다.
> - `messages.is_system` 컬럼은 SQLite에서 공동구매 참여 취소 시 `posts.py`가 `ALTER TABLE`로 지연 추가하는 컬럼이라 **마이그레이션 SQL에 포함되어 있지 않습니다**. PostgreSQL 모드에서는 그 `ALTER`가 실행되지 않으므로, 그룹 채팅방이 있는 공동구매의 **참여 취소 시스템 메시지 삽입이 실패할 수 있습니다**. 실제 Supabase에서 확인하고, 필요하면 마이그레이션에 컬럼을 추가해야 합니다(§8·`NeighborFood_Architecture_Plan.md` §8).
> - 이미지 한 요청의 합계는 **4MB 이하**입니다(Vercel 요청 크기 제한 대비). Oracle(Nginx 20MB) 방식에서도 같은 코드 제한이 적용됩니다.
> - `DATABASE_URL`·`SUPABASE_*`를 쓰지 않으면 이 절의 내용은 동작에 영향을 주지 않습니다.

### 5. (선택) React 프런트엔드 실행 — 전체 화면 (2026-09-20~21)

`frontend-react/`(Vite + React 19 + TypeScript)에 기존 정적 HTML 39개 화면 식별자가 React 화면으로 이전되어 있습니다(구현 완료 — 실제 브라우저·모바일·기기 검증은 진행 중). 기존 정적 HTML(`frontend/`)은 삭제하지 않고 병행 보존하며, 최종 점검이 끝나기 전까지 유지합니다. 백엔드(FastAPI·SQLite)와 API는 변경하지 않았습니다.

```bash
cd frontend-react
npm ci
npm run dev
```

- 기본 접속: [http://localhost:5173](http://localhost:5173) (Vite 기본 포트, 포트가 사용 중이면 터미널에 표시된 실제 `Local` 주소 사용). 화면 이동은 해시 경로입니다(예: `/#/Fridge`, `/#/Product_Detail?id=1`).
- 백엔드(`uvicorn main:app`, 8000번 포트)가 먼저 실행 중이어야 합니다. Vite 개발 서버·preview가 `/api`, `/posts`, `/uploads`, `/upload-images`, `/logout`, `/request-auth`, `/reset-password` 요청을 FastAPI(기본 `http://127.0.0.1:8000`)로 전달합니다. 프록시 대상은 환경변수 `NEIGHBORFOOD_BACKEND`로 바꿀 수 있습니다.
- 공개 API 주소를 직접 쓰려면 `VITE_API_BASE_URL`을 지정합니다(미설정 시 상대경로 + 프록시). 필요 시 `frontend-react/.env.local`에 추가하세요(`.env.local`은 Git에 올라가지 않습니다).
- 로그인: React(`localhost:5173`)와 정적 HTML(`127.0.0.1:8000`)은 접속 출처가 달라 브라우저 `localStorage`가 공유되지 않습니다. React 화면에서는 React 로그인 화면으로 별도 로그인합니다.
- CORS: `main.py`의 `ALLOWED_ORIGINS` 미설정 시 전체 허용(`*`)이므로 로컬 개발 중에는 별도 설정이 필요 없습니다. 배포 시 React 앱이 서빙되는 도메인을 `.env`의 `ALLOWED_ORIGINS`에 반드시 추가하세요. 정적 빌드(`dist`) 배포 시에는 Vite 프록시가 없으므로 같은 API 프록시를 배포 서버에 구성하거나 `VITE_API_BASE_URL`로 공개 API 주소를 지정해야 합니다.
- 기타 명령: `npm run build`(`tsc -b && vite build`), `npm run lint`(oxlint), `npm run preview`
- 상세 실행·문제 해결은 `Neighborfood_React_실행_안내.md`, 화면 매핑·검증 범위는 `frontend-react/docs/MIGRATION_REPORT.md`, 디자인 기준은 `frontend-react/docs/DESIGN_CONTEXT.md`를 참고하세요.

> ⚠️ **알려진 미비·제한 사항 (2026-09-21 기준)**
> - ~~`frontend-react/README.md` 템플릿 미교체~~ → 2026-10-03 교체 완료. 다만 배포 절차의 `scp -r dist/* …/dist/`는 서버에 `dist/`가 있어야 하므로 최초 업로드에는 `NeighborFood_서버_실행_점검_가이드.md` §5-2의 명령을 사용하세요. (저장소 미포함 — 개별 보관)
> - ~~그룹 채팅 화면에 거래 액션 바(약속·정산·GPS·QR 진입점)가 없습니다~~ → ✅ 2026-10-08 구현(`trades.tsx` `TradeBar`, B안).
> - (2026-10-12) 게시글·프로필 사진 업로드(`POST /upload-images`)와 영수증 API(`/api/receipt/*`)는 로그인이 필요합니다. 다른 회원의 `subjectId`로 영수증을 등록·인증하면 403입니다.
> - 실제 브라우저의 시각 확인·모바일 터치·키보드 탐색, 카메라(QR)·GPS·Kakao SDK·CLOVA OCR 동작은 실제 환경에서 확인이 필요합니다. 기존 HTML과 세부 동작·레이아웃이 1:1 동일하다고 확정하지 않았습니다.
> - 게시글 수정 API(`PATCH /posts/{id}`)는 2026-10-08부터 사진·거래 유형·목표 인원·1인 금액도 수정합니다(참여자·정산이 있으면 유형·인원·가격은 409로 잠김). React 화면도 해당 필드 편집이 가능합니다.
> - 공개 공지 API(`GET /api/notices`)가 2026-10-08 구현되어 React `Help` 화면과 정적 `Help.html`에 관리자 공지가 표시됩니다.
> - PWA 설치·오프라인 기능은 구현되지 않았습니다(PWA 전환을 위한 프런트 구조 정비 단계).
> - 정산의 "납부 표시"는 결제 승인이나 자동 송금이 아닙니다. 실결제·자동 송금은 예정되어 있지 않고, 2026-10-05 연동된 PortOne 결제는 **테스트 채널 전용**이며 납부 상태·정산 완료·판매자 지급을 바꾸지 않습니다.

### 6. 관리자 계정 생성

```bash
python seed_admin.py                  # 신규 생성 (login_id=Admin, pw=admin0000)
python seed_admin.py <login_id>       # 기존 계정을 admin 역할로 승격
```

> 2026-09-12: `seed_admin.py`가 복원되어 정상 동작합니다. 프로덕션 배포 전에는 기본 비밀번호(`admin0000`)를 변경하세요.

### 7. (선택) 더미 데이터 주입

```bash
python seed_posts.py                  # 더미 게시글 시드
python Seed_Account.py                # Capstone_1 계정 + 완료 거래 1건
python Seed_capstone_settlement.py    # Capstone_1~3 계정 + 공동구매 정산 시드
```

> ⚠️ `seed_posts.py`, `Seed_Account.py`, `Seed_capstone_settlement.py` 모두 2026-09-08 기준 저장소에 존재하지 않는 것으로 확인되었습니다. 더미 데이터가 필요하면 API(`POST /posts` 등)를 직접 호출하거나 스크립트 재도입을 기다려야 합니다.

### 8. (선택) 영수증 파서 테스트 실행

```bash
python tests/test_receipt_parser_v212.py
```

API 자동화 테스트(2026-10-08 추가, 임시 DB 사용 — 실제 `data/neighborfood.db`는 변경되지 않음):

```bash
pip install pytest httpx
python -m pytest tests -q
```

2026-10-12 기준 **32개 전부 통과**를 확인했습니다(정산·계정·공지·게시글 수정·PortOne·Supabase 저장소 라우팅/영수증 소유권 테스트 포함). `tests/test_supabase_storage.py`의 3개는 외부 키·서비스 없이 저장소 호출을 mock하므로 **실제 Supabase 연결을 검증하지는 않습니다.** 모든 pytest는 임시 SQLite DB를 사용합니다.

위의 `python tests/test_receipt_parser_v212.py`는 `pytest` 등 외부 프레임워크 없이 단독 실행되며, 마트형(농협)·카페형(스타벅스) 영수증 구조에 대한 5개 회귀 테스트를 수행합니다.

### 9. (선택) DB 초기화

```bash
python reset_db.py                    # 확인 프롬프트 후 모든 회원·게시글 및 연관 데이터 삭제 + Admin 재생성
python reset_db.py --yes              # 확인 프롬프트 생략
python reset_db.py --pw MyPass1!      # Admin 비밀번호 직접 지정 (기본 admin0000)
```

> ⚠️ **전체 데이터가 삭제됩니다.** 프로젝트 루트에서 실행해야 `data/neighborfood.db`를 찾습니다. 서버가 실행 중이면 먼저 종료하세요.

---

## 폴더 구조

```
Neighborfood/
├── main.py                  # FastAPI 앱 진입점
├── seed_admin.py            # 관리자 계정 생성/승격 (2026-09-12 복원)
├── reset_db.py              # DB 초기화 — 전체 데이터 삭제 + Admin 재생성
├── requirements.txt         # psycopg[binary]·python-dotenv 추가 (2026-10-12)
├── .env.example             # 환경변수 템플릿
├── supabase.env.example     # Supabase 선택 모드용 환경변수 템플릿 — 기존 .env에 추가 [신규 2026-10-12]
├── portone.env.example      # PORTONE_* 환경변수 템플릿
├── .gitignore               # .env.*·.supabase_patch_backups/ 추가 (2026-10-12)
├── sql/
│   └── neighborfood_schema.sql   # 스키마 참조 문서 (SQLite 기준 Source of Truth)
├── migrations/
│   └── 001_supabase.sql     # PostgreSQL(Supabase)용 초기 스키마 — 28190b4 시점, 앱 테이블 21개 + neighborfood_schema_version [신규 2026-10-12]
├── scripts/                 # Supabase 적용·점검·이전 스크립트 [신규 2026-10-12]
│   ├── configure_supabase.py   # DB 비밀번호·secret key 숨김 입력 → .env 기록(기존 값 보존, .env.supabase.bak 백업)
│   ├── supabase_migrate.py     # 빈 DB에 migrations/001_supabase.sql 적용(재실행 안전)
│   ├── check_supabase.py       # 연결·스키마 버전·버킷 읽기 전용 점검
│   ├── import_sqlite.py        # (선택) 기존 SQLite 데이터를 빈 PostgreSQL 테이블로 복사
│   └── import_uploads.py       # (선택) 기존 uploads/ 이미지를 Storage 버킷으로 업로드
├── data/
│   └── neighborfood.db      # SQLite 단일 DB (자동 생성, SQLite 모드)
├── uploads/                 # 업로드 이미지 저장 경로 (로컬 모드)
├── app/
│   ├── config.py            # 경로·상수 설정 (SESSION_TTL_DAYS=30, RECEIPT_TRUST_DELTA=0.3), .env 로드(python-dotenv), VERCEL 시 /tmp 경로
│   ├── storage.py           # Supabase Storage HTTP API(저장·공개 URL·영수증 서명 URL, 요청 합계 4MB 제한) [신규 2026-10-12]
│   ├── core/
│   │   ├── deps.py          # get_current_user / get_current_admin 의존성
│   │   └── utils.py         # 시간·토큰·비밀번호 헬퍼
│   ├── db/
│   │   ├── base.py          # make_conn(DATABASE_URL이 있으면 PostgreSQL 연결 반환), init_all_databases
│   │   ├── postgres.py      # SQLite→PostgreSQL 호환 계층(자리표시자·함수·INSERT OR IGNORE 변환, DDL 미실행) [신규 2026-10-12]
│   │   ├── auth_db.py       # users, sessions, auth_codes, posts
│   │   ├── transaction_db.py# transactions, groupbuy_participants, manner_ratings
│   │   ├── settlement_db.py # settlements, settlement_shares CRUD + GPS/QR 검증
│   │   ├── member_db.py     # wishlists, conversations, messages, conversation_members
│   │   ├── fridge_db.py     # fridge_items
│   │   ├── admin_db.py      # notices, reports
│   │   ├── qr_db.py         # qr_sessions
│   │   ├── receipt_db.py    # receipts + OCR (CLOVA/Tesseract, parser v2.1)
│   │   └── location_verify_db.py  # location_verify_sessions (반경 100m)
│   ├── models/              # Pydantic 요청/응답 스키마
│   │   └── auth.py  user.py  post.py  qr.py  receipt.py  member.py  fridge.py
│   └── routers/             # API 라우터 (엔드포인트별 1파일)
│       ├── auth.py
│       ├── posts.py         # 게시글 CRUD·참여·취소·약속·my-status·자동 만료
│       ├── users.py
│       ├── wishlist.py
│       ├── chat.py          # 1:1 + 그룹 채팅
│       ├── transactions.py
│       ├── settlements.py   # 공동구매 정산 (GPS→QR 2단계 인증, 노쇼 처리)
│       ├── ratings.py       # 매너 평가 (trust_score 반영)
│       ├── fridge.py
│       ├── admin.py
│       ├── reports.py
│       ├── qr.py
│       ├── receipt.py       # 영수증 OCR (2026-10-12: 로그인·본인 소유 검증, 이미지 서명 URL 조회)
│       ├── location_verify.py
│       └── portone.py       # PortOne V2 테스트 결제 (/api/payments/portone/*) [신규 2026-10-05]
├── frontend/                # 정적 HTML 프런트엔드
│   ├── shared/
│   │   ├── auth.js          # fetch 래퍼 (Bearer 토큰 자동 주입)
│   │   ├── guard.js         # 회원 전용 페이지 보호 (nfRequireMember)
│   │   ├── adminGuard.js    # 관리자 전용 페이지 보호 (nfRequireAdmin) [신규 2026-09-12]
│   │   ├── (profile.js)     # 저장소에 없음(2026-10-07 확인) — 프로필 호출은 `Edit_Profile.html` 등 각 화면의 인라인 `fetch`로 처리
│   │   └── tokens.css       # 디자인 토큰 (CSS 변수)
│   ├── vendor/
│   │   └── html5-qrcode.min.js  # QR/바코드 스캔 라이브러리 로컬 사본 [신규] — CDN 장애 대비 1차 로드 경로
│   ├── Home.html
│   ├── Login.html
│   ├── Signup.html
│   └── ...
├── frontend-react/          # React(Vite) 프런트엔드 [2026-09-20~21] — 화면 39개 전체 이전(구현), 정적 HTML은 병행 보존
│   ├── docs/
│   │   ├── DESIGN_CONTEXT.md     # React 공통 디자인·로딩·자동완성·게시글 상세 기준
│   │   └── MIGRATION_REPORT.md   # 화면 39개 이전 매핑·검증 범위·미검증 범위
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── assets/               # hero.png, react.svg, vite.svg
│   │   ├── neighborfood/         # 승인된 메인(홈) 화면·공통 레이아웃
│   │   │   ├── api.ts            # 백엔드 주소(VITE_API_BASE_URL, 미설정 시 상대경로+Vite 프록시)·getPosts()·legacy()(→ #/화면명 해시 경로)
│   │   │   ├── AppLayout.tsx     # 헤더 + 하단 네비게이션 공통 레이아웃
│   │   │   ├── HomePage.tsx      # 홈 피드 (카테고리·검색·게시글 카드, GET /posts 연동)
│   │   │   ├── home.css          # HomePage 전용 스타일
│   │   │   └── Icon.tsx          # 인라인 SVG 아이콘 컴포넌트
│   │   ├── migration/            # 나머지 화면 React 모듈 (2026-09-20~21)
│   │   │   ├── routes.tsx        # 화면 목록·라우팅·접근 제어(회원/관리자)·도움말·진입 화면
│   │   │   ├── core.tsx          # 공통 API 요청·인증 토큰·오류·상태 처리·공통 UI
│   │   │   ├── design.css        # 공통 디자인 토큰·폼·버튼·리스트·대화상자
│   │   │   ├── loading.tsx       # 화면 전환·최초 조회 공통 로딩
│   │   │   ├── autocomplete.tsx  # 검색·회원·주소 공통 자동완성
│   │   │   ├── PostGallery.tsx   # 게시글 상세 사진 갤러리
│   │   │   ├── auth.tsx          # 로그인·가입·비밀번호 재설정·프로필(사진 업로드·신뢰온도)·탈퇴
│   │   │   ├── TrustTemperature.tsx · trust-temperature.css · profile.css   # 신뢰온도 게이지(canvas)·프로필 사진 스타일 [신규 2026-10-11]
│   │   │   ├── posts.tsx         # 검색·찜·게시글 상세·등록/수정·거래 신청·신고
│   │   │   ├── fridge.tsx        # 내 냉장고
│   │   │   ├── trades.tsx        # 채팅·그룹 채팅·내 활동·거래 내역·정산·매너 평가
│   │   │   ├── location.tsx      # Kakao 지도·동네 설정·GPS 위치 인증
│   │   │   ├── qr.tsx            # QR 발급(토큰 표시·복사)·카메라 스캔(스캔 모드에서는 탭 숨김, 발급·내역은 보조 버튼)·토큰 검증
│   │   │   ├── receipt.tsx       # 영수증 OCR(분석 중 상태 표시)·품목 편집·인증·냉장고 등록
│   │   │   ├── admin.tsx         # 관리자 대시보드·회원·공지·신고·채팅 기록
│   │   │   ├── portone.tsx       # PortOne 테스트 결제 화면 Payment_Checkout·Result·Quick·Preview [신규 2026-10-05]
│   │   │   ├── Scanner.tsx       # QR·영수증 공용 카메라 스캐너 [신규 2026-10-05]
│   │   │   └── scanner.css · interface.css   # 스캐너·인터페이스 스타일 [신규 2026-10-05]
│   │   ├── App.css
│   │   ├── App.tsx               # 해시 라우팅 + AppLayout + 접근 가드 (홈은 HomePage)
│   │   ├── index.css
│   │   └── main.tsx              # React 진입점 (StrictMode)
│   ├── index.html             # Vite 진입 HTML (#root, /src/main.tsx 로드)
│   ├── package.json           # react 19.2, react-dom 19.2, qrcode, jsqr / devDeps: vite 8, typescript, oxlint 등
│   ├── package-lock.json
│   ├── tsconfig.json  tsconfig.app.json  tsconfig.node.json
│   ├── vite.config.ts         # @vitejs/plugin-react + 개발/preview API 프록시 (NEIGHBORFOOD_BACKEND)
│   ├── .oxlintrc.json         # Oxlint 설정 (ESLint 대체 린터)
│   ├── .gitignore
│   └── README.md              # 프로젝트 설명·실행·구조·배포 절차 (2026-10-03 교체 완료)

├── tests/
│   ├── test_receipt_parser_v212.py  # 영수증 파서 회귀·유닛 테스트 [신규] — pytest 없이 단독 실행 가능
│   ├── conftest.py                  # pytest 공용 픽스처(임시 DB + TestClient) [신규 2026-10-08]
│   ├── test_account_notice_post.py  # 비밀번호 변경·공개 공지·게시글 수정 확장 테스트 [신규 2026-10-08]
│   ├── test_settlement_flow.py      # 정산 흐름 자동화 테스트 [신규 2026-10-08]
│   ├── test_portone.py              # PortOne 테스트 결제 검증 (외부 API mock) [신규 2026-10-05]
│   └── test_supabase_storage.py     # Storage 라우팅·영수증 소유권·4MB 제한 (외부 서비스 mock) [신규 2026-10-12]
├── docs/PORTONE_TEST_SETUP.md   # PortOne 테스트 연동 범위·설정·제한
├── docs/SUPABASE_MIGRATION.md   # Supabase 전환 패치 적용·로컬 실행·Vercel 배포 준비·롤백 안내 (팀원 작성, 2026-10-12)
├── README.md  Capstone.md  NeighborFood_Architecture_Plan.md  neighborfood_ERD.md
├── Settlement_Implementation_Plan.md  Neighborfood_React_실행_안내.md   # 프로젝트 문서 (아래 "관련 문서" 참고)
```

> ℹ️ **React 프런트엔드 안내 (2026-09-14 추가 → 2026-09-20~21 전체 화면 이전 반영)**
> `frontend-react/`(Vite 8 + React 19 + TypeScript, 린터는 ESLint 대신 **Oxlint**)는 2026-09-14 홈 화면으로 시작해, 2026-09-20 기존 HTML 39개 화면 식별자를 React 경로로 매핑·이전했고(`src/migration/`), 2026-09-21 공통 로딩·자동완성·게시글 상세 개선을 보강했습니다. 화면 이동은 해시 경로(`#/화면명`)이며, 39개 화면이 39개의 독립 TSX 파일은 아니고 같은 그룹의 화면은 하나의 컴포넌트와 props를 공유합니다. 신규 백엔드 API는 추가되지 않았고 기존 FastAPI API를 그대로 사용합니다.
> **후속 필요 작업 (2026-10-12 갱신)**: **⓪ 배포 방식 최종 결정 — 10/16 체크포인트 이전에 Oracle 부하테스트와 Supabase·Vercel 실환경 검증(DB 연결·Storage 업로드·`messages.is_system` 보완 여부·OCR·카메라·PortOne)을 마치고 Oracle 유지 / Vercel+Supabase 전환 중 확정**, ① 실제 브라우저·모바일·기기(카메라·GPS·OCR) 검증, ② PortOne 테스트 결제 서버 반영·검증, ③ PWA 전환, ④ 배포 시 `.env`의 `ALLOWED_ORIGINS`에 React 앱 서빙 도메인 추가 및 정적 빌드 배포 방식 결정, ⑤ 정적 HTML(`frontend/`)의 최종 처리(구현 100% 완료 후 영향 점검 뒤 폐기). ✅ 2026-10-08 완료: 공개 공지 API, 비밀번호 변경 API, 게시글 수정 API 확장, 그룹 채팅 거래 액션 바, 정산 흐름 자동화 테스트.


> ⚠️ **문서-저장소 정합성 안내 (2026-09-08 확인, 2026-09-12 갱신)**
> 이전 버전 문서에는 아래 7개 루트 스크립트가 명시되어 있었고, 2026-09-08 확인 시 모두 없는 것으로 보고 트리에서 제거했습니다. **2026-09-19 재확인 결과 `seed_admin.py`(2026-09-12 복원)와 `reset_db.py`는 저장소에 존재**하며, 나머지 5개는 여전히 없습니다.
>
> | 파일 | 과거 역할 | 현재 상태 |
> |---|---|---|
> | `seed_admin.py` | 관리자 계정 부트스트랩 | ✅ **2026-09-12 복원**, 정상 동작 |
> | `seed_posts.py` | 더미 게시글 시드 (개발용) | ⬜ 미존재 |
> | `Seed_Account.py` | 테스트 계정 + 완료 거래 시드 | ⬜ 미존재 |
> | `Seed_capstone_settlement.py` | 정산 수동 테스트용 시드 | ⬜ 미존재 |
> | `Seed_settlement_verify.py` | 정산 API 자동 검증 스크립트 | ⬜ 미존재 |
> | `nf_functional_test.py` | 전체 기능 자동 테스트 스크립트 | ⬜ 미존재 |
> | `reset_db.py` | DB 초기화 (테이블 DELETE + Admin 재생성) | ✅ **존재 확인 (2026-09-19)** — 아래 "9. DB 초기화" 참고 |
>
> 현재 저장소에 존재하는 자동화 테스트는 `tests/test_receipt_parser_v212.py`(영수증 파서), `tests/test_portone.py`(PortOne 테스트 결제), 2026-10-08 추가된 `tests/test_account_notice_post.py`·`tests/test_settlement_flow.py`(공용 픽스처 `tests/conftest.py`, 임시 DB), 그리고 2026-10-12 추가된 `tests/test_supabase_storage.py`(Storage 라우팅·영수증 소유권, 외부 서비스 mock)입니다. 나머지(더미 시드·일부 검증 스크립트 등)는 표에서 ⬜ 미존재로 표기된 스크립트가 없는 상태이므로 별도 수동 절차로 병행해야 합니다(`reset_db.py`는 테스트가 아닌 DB 초기화 도구). 관리자 계정 생성은 `seed_admin.py` 복원으로 정상 동작합니다(아래 "6. 관리자 계정 생성" 참고). 아래 "7. 더미 데이터 주입" 안내는 여전히 미존재 상태를 반영합니다.

---

## 인증 방식

Bearer 토큰 세션 인증을 사용합니다.

1. `POST /api/auth/login` — login_id + password → `{ token, expiresAt }` 반환
2. 이후 모든 인증 필요 API 요청에 `Authorization: Bearer <token>` 헤더 포함
3. `frontend/shared/auth.js`가 `window.fetch`를 래핑하여 토큰을 자동 주입

토큰 유효기간은 `config.py`의 `SESSION_TTL_DAYS`로 조정합니다 (기본 **30일**).

> `frontend-react/`는 자체 로그인 화면(`src/migration/auth.tsx`)과 토큰 처리(`src/migration/core.tsx`, `nf_token` 등)를 가집니다. React(`localhost:5173`)와 정적 HTML(`127.0.0.1:8000`)은 접속 출처가 달라 `localStorage`가 공유되지 않으므로 React 화면에서는 React에서 로그인합니다. 회원 전용 화면은 토큰이 없으면 로그인 안내를 표시하고, 관리자 화면(`Admin_*`)은 `GET /api/users/me`의 role이 admin일 때만 열리며 서버에서도 권한을 검사합니다.

---

## 데이터베이스

**기본은 단일 파일 SQLite(`data/neighborfood.db`)** 이며, `DATABASE_URL`을 설정하면 **PostgreSQL(Supabase)** 을 사용할 수 있습니다(2026-10-12, §4-1). 두 방식 모두 같은 `db/*.py` 코드를 공유합니다.

- (SQLite) WAL 모드 + `busy_timeout=5000` 으로 동시 접근 안정성 확보
- (SQLite) 앱 시작 시 `init_all_databases()`가 모든 테이블을 `CREATE TABLE IF NOT EXISTS`로 생성
- (SQLite) 기존 DB에 신규 컬럼이 추가될 경우 `ALTER TABLE … ADD COLUMN` 멱등 마이그레이션 자동 실행
- (PostgreSQL) 스키마는 `scripts/supabase_migrate.py`가 `migrations/001_supabase.sql`로 한 번 적용하며, 서버는 DDL을 실행하지 않습니다. 모든 앱 테이블에 RLS를 켜고 공개 역할 권한을 제거하며, 회원 권한 검사는 기존처럼 서버가 담당합니다.
- 전체 스키마 정의는 `sql/neighborfood_schema.sql`(SQLite 기준) 참조. 테이블·컬럼 상세는 `neighborfood_ERD.md`

---

## API 라우터 목록

| 접두사 | 태그 | 설명 |
|---|---|---|
| `/api/auth` | 인증 | 회원가입(`/register`), 로그인(`/login`) |
| (접두사 없음) | 인증 | 로그아웃 `POST /logout`, 비밀번호 재설정 OTP `POST /request-auth` · `POST /reset-password` |
| `/posts` | 게시글 | 목록·상세·작성·수정·삭제, 공동구매 참여/취소, 약속 확정, my-status, 사진 업로드 `POST /upload-images`(**로그인 필요**, 요청 합계 4MB 이하, 2026-10-12) |
| `/api/users` | 회원 | 프로필 조회·수정, 회원 탈퇴, 동네 인증(동네 이름·인증일 저장, 좌표는 국내 범위 검증만), 로그인 상태 비밀번호 변경(`PATCH /api/users/me/password`, 2026-10-08) |
| `/api/wishlist` | 찜 목록 | 찜 추가·취소, 내 찜 목록 |
| `/api/chats` | 채팅 | 1:1·그룹 채팅방 생성, 메시지 송수신 (REST 폴링) |
| `/api/transactions` | 거래 | 거래 생성·조회·상태 변경 |
| `/api/settlements` | 정산 | 공동구매 정산 (분담 자동계산, GPS/QR 인증, 노쇼 신고/취소) |
| `/api/ratings` | 매너 평가 | thumbs up/down 평가 등록·수정·삭제, 받은 평가·거래별 내 평가 조회, trust_score 반영 |
| `/api/fridge` | 내 냉장고 | 영수증 인증 품목 등록, 목록 조회, 상태 변경 |
| `/api/qr` | QR 거래 인증 | QR 세션 발급·검증, 이력(`/history`, `/my-history`) |
| `/api/receipt` | 영수증 인증 | `GET /health`, OCR 업로드 `POST /scan`, 품목 선택·인증 `POST /verify`, 내 이력 `GET /history`, 이미지 조회 `GET /image/{name}`. 2026-10-12부터 `health` 외 **모두 로그인 필요·본인 영수증만**(타인 `subjectId`는 403, 이미지는 소유자만 서명 URL로 307 리다이렉트) |
| `/api/admin` | 관리자 | 회원·신고·공지 관리, 채팅 모니터링, 대시보드 통계(`/stats`) |
| `/api/reports` | 신고 | 게시글·회원 신고 접수·취소, 내 신고 목록(`GET /my`) |
| `/api/location-verify` | GPS 위치 인증 | 위치 인증 세션 생성·검증 (Haversine 100m) |
| `/api/payments/portone` | PortOne 테스트 결제 | `GET /config`, `POST /prepare`(정산 분담금 주문), `POST /{payment_id}/verify`(PortOne 조회 검증), `POST /quick-prepare`(1,000원 빠른 테스트). 테스트 채널 전용, 설정(`PORTONE_*`) 없으면 503, 정산 납부 상태 불변 (2026-10-05) |
| `/api/notices` | 공개 공지 | 비인증 공지 목록 조회(2026-10-08 구현, `?limit=1~50`). 등록·삭제는 관리자 전용 `/api/admin/notices` |
| `/api/config/kakao-key` | 설정 | 카카오 JS 키 반환 (프론트 동적 로드용) |

> React 화면은 신규 API로 PortOne 테스트 결제 4종과 2026-10-08 추가된 비밀번호 변경·공개 공지 2종을 사용하며 그 외는 기존 API를 그대로 사용합니다. 게시글 수정 `PATCH /posts/{id}`는 제목·설명·카테고리·상태·교환 희망·주소·좌표·사진·거래 유형·목표 인원·1인 금액을 반영하고, 참여자·정산이 있으면 유형·인원·가격은 409로 잠깁니다.

---

## 테스트 계정 기본값

| 계정 | login_id | password | 역할 |
|---|---|---|---|
| 관리자 | `Admin` | `admin0000` | admin |
| 일반1 | `Capstone_1` | `capstone1` | user |
| 일반2 | `Capstone_2` | `capstone2` | user |
| 일반3 | `Capstone_3` | `capstone3` | user |

---

## 관련 문서

| 문서 | 용도 |
|---|---|
| `Capstone.md` | 개발 컨텍스트·제약사항·범위(포함/제외) 요약 |
| `NeighborFood_Architecture_Plan.md` | 아키텍처 현황, API 전체 목록, 개발 이력, 잔여 작업 |
| `neighborfood_ERD.md` | DB 구조(ERD)와 디렉토리 구조 |
| `Settlement_Implementation_Plan.md` | 공동구매 정산 시스템 설계·구현 계획 |
| `Neighborfood_React_실행_안내.md` | 백엔드 + React(`frontend-react/`) 로컬 실행 안내서 |
| `NeighborFood_서버_실행_점검_가이드.md` | 운영 서버(Oracle Cloud) 실행·점검·갱신 배포·백업·장애 대응 | *(저장소 미포함 — 개별 보관)*
| `NeighborFood_배포방식_비교_Oracle_vs_Vercel.md` | 배포 방식 비교(Oracle 유지 + 리스크 보강 권고) | *(저장소 미포함 — 개별 보관)*
| `캡스톤_전시회_준비_일정.md` | 전시회(11/3)까지 일정·서버 진행 상태·체크포인트·이력 | *(저장소 미포함 — 개별 보관)*
| `졸업작품집_원고_작업_기록.md` · `졸업작품집_원고_유의사항.md` | 졸업작품집 원고 구성·키워드·화면 목록과 제출 전 유의사항 | *(저장소 미포함 — 개별 보관)*
| `docs/SUPABASE_MIGRATION.md` | Supabase(PostgreSQL)·Storage 전환 패치 적용, 로컬 실행, Vercel 배포 준비, 롤백 (팀원 작성, 2026-10-12 — 기준 커밋이 `28190b4`이고 작성자 PC 경로가 예시로 적혀 있어 문서는 수정하지 않음) |
| `docs/PORTONE_TEST_SETUP.md` | PortOne 테스트 결제 설정·범위·제한 (팀원 작성) — ⚠️ 2026-09-28 기준 작성본이라 `quick-prepare`·`Payment_Quick`/`Payment_Preview`(2026-10-05 추가)를 반영하지 않고 API를 3종으로 기술함 — 현행 API는 4종(팀원 문서는 수정하지 않음) |
| `frontend-react/docs/DESIGN_CONTEXT.md` | React 공통 디자인·로딩·자동완성·게시글 상세 기준 |
| `frontend-react/docs/MIGRATION_REPORT.md` | 화면 39개 React 이전 매핑·검증 범위·미검증 범위 |