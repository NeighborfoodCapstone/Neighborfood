# Neighborfood Supabase 전환 패치 적용 안내

기준: GitHub main `28190b45ab4d17684c021252a39193a9acd39440`.
기존 화면·URL·필드·Bear​​er 로그인·테스트 결제 흐름을 유지한다. PostgreSQL을 사용할 때만 공통 DB 연결 계층에서 현재 SQL의 SQLite 문법을 변환한다. 기존 SQLite 모드도 유지한다.

## 1. 최신 코드 받기와 패치 적용

패치 파일을 `C:\Users\bluem\Downloads\apply_neighborfood_supabase.py`에 저장한다.
Git Bash에서:

```bash
cd /c/Users/bluem/Neighborfood
git pull --rebase origin main
python /c/Users/bluem/Downloads/apply_neighborfood_supabase.py --root /c/Users/bluem/Neighborfood --check
python /c/Users/bluem/Downloads/apply_neighborfood_supabase.py --root /c/Users/bluem/Neighborfood
```

`python`이 없으면 `py`를 사용한다. 충돌이나 원본 불일치가 나오면 중단하고 출력 내용을 확인한다. 강제 push나 hard reset을 하지 않는다.

원본 파일과 기존 SQLite DB의 일관된 스냅샷은 `.supabase_patch_backups/<시각>/`에 백업한다. `.env`는 패치가 열거나 수정하지 않는다. 업로드 폴더는 삭제하지 않으며, 기존 이미지는 별도 복사해 보관한다. 같은 패치 재실행은 변경 없이 종료한다. 수정 대상 파일 내용이 기준과 다르면 적용을 거부한다. 적용 전에 임시 복사본에 파일을 반영하고 Python 구문을 검사한다.

## 2. 의존성 설치

기존 프로젝트 가상환경을 활성화한 상태에서:

```bash
python -m pip install -r requirements.txt
```

## 3. 비밀번호·서버 키를 PC에서 입력

```bash
python scripts/configure_supabase.py
```

서울 프로젝트의 **DB 비밀번호**, `sb_secret_`까지 포함한 **Secret key 전체**를 차례로 입력한다. 입력은 화면에 표시되지 않는다. Git Bash가 숨김 입력을 지원하지 않는다는 메시지를 내면 PowerShell에서 프로젝트 폴더로 이동해 같은 명령을 실행한다.

프로젝트 URL·Transaction pooler 주소는 이번 대화에서 확인한 서울 프로젝트 값을 사용한다. DB 비밀번호의 특수문자는 스크립트가 URL 인코딩한다. 기존 OCR·PortOne·Kakao 값은 보존한다. 기존 `.env`가 있으면 `.env.supabase.bak`에 보존하며 둘 다 Git 추적 제외 대상이다. `.env`가 Git 추적 중이면 실행을 거부한다. React `.env.local`에 API 주소가 없으면 로컬 주소를 추가한다. 기존 주소가 있다면 확인해 `http://127.0.0.1:8000`으로 맞춘다.

직접 설정하려면 `supabase.env.example`을 참고해 기존 서버 `.env`에 값을 추가한다. 예시 전체를 복사해서 기존 OCR·결제 설정을 지우지 않는다. Data API는 계속 꺼둔다.

## 4. 새 DB에 스키마 적용

```bash
python scripts/supabase_migrate.py
python scripts/check_supabase.py
```

`001_supabase.sql`은 현재 21개 앱 테이블, 인덱스, 관계, ID 시퀀스를 생성한다. public 스키마에 기존 테이블이 있으면 덮어쓰지 않고 중단한다. 전체를 트랜잭션으로 적용한다. 완료한 버전의 재실행은 변경 없이 종료한다.

각 앱 테이블은 RLS를 켜고 공개 역할 권한을 제거한다. 기존처럼 서버에서 회원 권한을 확인한다. PostgreSQL 연결은 대시보드에서 제공한 `postgres.<프로젝트ID>` 계정으로 하며 브라우저에 전달하지 않는다. 요청마다 테이블을 새로 만들거나 스키마를 자동 변경하지 않는다.

버킷은 `food-images`: 공개, `receipts`: 비공개여야 한다. 점검 스크립트는 연결·스키마 버전·버킷 존재·공개 여부를 읽기 전용으로 확인한다.

## 5. 기존 데이터를 가져올 경우에만

새 계정으로 테스트하려면 이 단계는 건너뛴다. 기존 회원·게시글·거래를 유지하려면 앱 사용을 잠시 멈추고, 기존 DB·uploads를 별도 백업한 뒤:

```bash
python scripts/import_sqlite.py data/neighborfood.db
python scripts/import_uploads.py uploads
```

대상 앱 테이블이 비어 있을 때만 DB를 가져온다. 원본 SQLite는 읽기 전용으로 열고 스냅샷을 만들어 사용한다. 행 수를 확인하고 FK·UNIQUE 제약을 적용하며 ID 시퀀스를 조정한다. 기존 원본은 수정하지 않는다. 이전 데이터가 제약을 위반하면 전체 DB 가져오기를 롤백하고 오류를 확인한다.

이미지 가져오기는 별도 작업이다. 원본 파일명은 유지하고 영수증은 비공개 버킷으로 옮긴다. 이미 같은 이름이 업로드돼 있거나 파일 제한을 넘기면 중단한다. DB 롤백과 Storage 롤백은 별개이며, 실패 후 재시도 전에 이미 옮긴 파일 목록을 확인한다.

## 6. 로컬 실행

터미널 1:

```bash
cd /c/Users/bluem/Neighborfood
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

터미널 2:

```bash
cd /c/Users/bluem/Neighborfood/frontend-react
npm install
npm run dev
```

`http://localhost:5173/#/Home`에서 새 회원 가입 또는 이전 회원 로그인 → 게시글 등록·조회·수정 → 사진 → OCR → GPS → QR → 정산·PortOne 테스트를 확인한다. 서버를 재시작해 DB와 사진이 유지되는지도 확인한다.

### 의도적으로 강화한 접근 제어

- 게시글 사진 업로드는 로그인 필요. 기존 React 요청은 Bearer 토큰을 전송한다.
- 영수증 촬영·인증·내역은 로그인한 본인의 데이터만 처리한다. 다른 회원의 subjectId를 보내면 거부한다.
- 영수증 DB에는 만료되는 서명 URL 대신 기존 파일명을 저장한다. 촬영 응답의 imageUrl은 5분짜리 서명 URL이며, 다시 볼 때 `/api/receipt/image/{파일명}`에 인증 토큰으로 요청하면 서버가 소유권을 확인해 새 URL로 리다이렉트한다.
- 공개 `/uploads/{파일명}`은 게시글 사진용 공개 버킷으로만 연결한다. 영수증 버킷을 공개로 바꾸지 않는다.

## 7. Vercel 배포 준비

로컬 기능 확인 후 코드만 커밋·push한다. 서버 프로젝트는 저장소 루트의 `main.py`를 FastAPI 진입점으로 사용한다. React 프로젝트는 `frontend-react`, Vite, `npm run build`, `dist`를 사용한다.

API 환경변수: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `ALLOWED_ORIGINS`와 기존 OCR·PortOne·Kakao 변수. SSL은 기본 require이며 prepared statements는 Transaction pooler에 맞춰 비활성화한다.
React 환경변수: `VITE_API_BASE_URL`에 실제 API 배포 주소만 입력한다. 비밀 값은 넣지 않는다.

Vercel에서는 SQLite fallback을 거부한다. 임시 OCR 파일은 `/tmp`에서 처리하고 삭제한다. 이미지·DB는 Supabase에 유지된다. 데이터 마이그레이션은 배포 전에 별도로 실행한다. 두 프로젝트의 주소가 확정되면 API의 ALLOWED_ORIGINS, 지도 허용 도메인, PortOne 설정을 실제 주소로 맞춘다.

이미지 한 요청의 합계는 4MiB 이하로 제한한다. Vercel은 multipart overhead를 포함한 요청 크기 제한이 있으므로 실제 사진은 여유 있게 4MB 미만을 권장한다. 더 큰 원본 업로드를 하려면 별도의 브라우저 직접 업로드 흐름이 필요하며 이번 패치에는 포함하지 않았다. Clova는 기존 HTTP OCR을 사용하고 Tesseract 설치는 Vercel 전제가 아니다.

## 8. 파일만 되돌리기

적용 시 출력된 백업 경로로:

```bash
python /c/Users/bluem/Downloads/apply_neighborfood_supabase.py --root /c/Users/bluem/Neighborfood --rollback BACKUP_DIRECTORY
```

패치 후 수정된 파일은 덮어쓰지 않고 중단한다. 이 명령은 코드 파일만 되돌린다. Supabase의 DB·Storage나 설정 스크립트가 만든 `.env`는 되돌리지 않는다. `.env`를 원래 상태로 되돌리려면 별도 보관한 `.env.supabase.bak`을 사용한다. DB·이미지를 삭제하지 않는다.

## 검증 범위

기존 자동화와 추가 Storage 인증 테스트를 실행했다. 실제 서울 Supabase 연결·업로드·Clova·휴대폰 카메라·PortOne 외부 호출·Vercel 배포는 사용자 환경에서 다음 단계로 검증해야 한다. 모든 기능의 실제 서비스 검증이 끝났다는 뜻은 아니다.
