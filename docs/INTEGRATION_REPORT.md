# NeighborFood 통합 개선 결과 및 운영 전 확인 사항

> **전체 작업 상태: 부분 완료.** 코드와 격리 환경 검증은 진행했지만 운영 Supabase·NAVER Cloud·Vercel, 실제 휴대폰과 배포 환경은 확인하지 못했다. OCR을 개방하거나 운영 DB를 변경하지 않았으며, 완료 게이트가 남아 있어 커밋과 GitHub push도 하지 않았다. 아래 수치는 격리 테스트 결과이며 운영 상태가 아니다.

## 1. 기준 커밋과 Git 상태

- 작업 시작 시 로컬 브랜치 `main`, 기준 커밋 `7070d34`, 작업 트리는 깨끗한 상태였다. 원격 주소는 <https://github.com/NeighborfoodCapstone/Neighborfood.git>이다. 사용자는 GitHub 동기화가 완료되었다고 알렸으며, 이번 작업 중 원격 fetch로 최신 상태를 다시 확인하지 않았다.
- 최종 커밋: **없음**. 개선 사항은 로컬 작업 트리에만 있다. 기본 브랜치 반영·PR·push: **미실시**. 원격에 반영된 변경 URL은 없다.
- 사유: 운영 백업·마이그레이션·RLS/Storage와 외부 OCR 과금 방어 및 Firewall, 실기기·실 OCR·배포 검증이 완료되지 않았다. 검증되지 않은 변경을 `main`에 push하지 않는 지시를 우선했다.
- 사용한 자문: Muse(설계), Beam/`step-tester`(경계·수용 조건), Kimi(위험 변경 검토). 자문은 제안이며 실제 수정·명령·테스트·브라우저 실행은 주 작업자가 담당했다.

## 2. 다섯 작업의 상태와 변경 파일

| 작업 | 상태 | 실제 개선 및 미완료 사항 |
| --- | --- | --- |
| A. DB 정합성·접근 제어 | 부분 완료 | 추가형 SQL, 거래·영수증 원자성, QR/GPS 결합, 로컬 영수증 접근 제한. PGlite 리허설은 통과했으나 운영 스키마·백업·복원·Storage/RLS는 미확인. |
| B. OCR 비용 방어 | 부분 완료 | DB 공유 예약, 전역·회원 한도, 멱등성, 보수적 실패 계수, 기본 중단 및 관리자 스위치. NAVER의 독립적 강제 제한과 실 과금 검증은 미확인. |
| C. 시연 관리자 | 부분 완료 | 기본 자격증명 제거, 기존 계정 승격·회수 명령과 서버 관리자 검사, OCR 대시보드. 가상 계정으로 승격·회수를 확인했으나 실제 시연 환경은 미확인. |
| D. 거래 양측 검증 | 부분 완료 | 수령자 GPS·QR 발급, 제공자 QR 검증, DB 완료 및 정산의 권한·상태·증거·중복 처리. 격리 UI/SQLite에서 검증했으나 실제 Supabase·스마트폰 대면 시나리오는 미수행. |
| E. React UI·UX | 부분 완료 | 기존 스캐너 형태를 유지하며 거래 상태·QR 실패·영수증 수동 입력·관리자 OCR 상태 표시 개선. 가상 모바일 화면만 확인했으며 승인 시안과의 최종 비교·사용자 시각 승인은 받지 못함. |

변경 파일:

- DB·보안: `migrations/002_ocr_guard.sql`, `migrations/003_trade_verification.sql`, `app/db/base.py`, `app/db/ocr_guard.py`, `app/db/trade_verification.py`, `app/db/qr_db.py`, `app/db/location_verify_db.py`, `app/db/receipt_db.py`, `app/db/settlement_db.py`, `app/db/transaction_db.py`, `main.py`, `requirements.txt`.
- API·권한: `app/models/qr.py`, `app/routers/admin.py`, `app/routers/location_verify.py`, `app/routers/posts.py`, `app/routers/qr.py`, `app/routers/ratings.py`, `app/routers/receipt.py`, `app/routers/settlements.py`, `app/routers/transactions.py`, `seed_admin.py`, `reset_db.py`.
- 화면: `frontend-react/src/migration/admin.tsx`, `location.tsx`, `qr.tsx`, `receipt.tsx`, `trades.tsx`; 기존 정적 화면 `frontend/Local_Verify_Demo.html`, `frontend/QR_Scan.html`, `frontend/Receipt_Verify.html`.
- 회귀 테스트: `tests/test_ocr_guard.py`, `tests/test_trade_verification.py`, `tests/test_receipt_privacy.py`, `tests/test_receipt_trust.py`, `tests/test_settlement_flow.py`, `tests/test_supabase_storage.py`.
- 문서: `README.md`, `Capstone.md`, `NeighborFood_Architecture_Plan.md`, `docs/SUPABASE_MIGRATION.md`, 이 보고서.

## 3. DB 인벤토리, 마이그레이션 및 복구

### 현재 코드 기준 인벤토리

- FastAPI OpenAPI는 격리 실행 기준 84개 경로와 102개 작업이다. 인증·회원·게시글·채팅·거래·정산·GPS·QR·영수증·냉장고·관리자·신고·공지·PortOne 라우터를 사용한다. 실제 배포의 목록은 확인하지 않았다.
- `001_supabase.sql`은 앱 테이블 21개와 스키마 버전 표식을 정의한다. 추가 SQL은 OCR 설정·요청·관리자 감사 3개와 QR 검증 감사 1개 테이블을 추가한다. 실제 운영 테이블·인덱스·트리거·함수 및 별도 수동 변경은 확인하지 않았다.
- 관계: 게시글 작성자와 신청자가 `transactions`로 연결되고, GPS와 QR은 해당 거래 또는 정산에 연결된다. 거래 QR은 발급 당시 GPS 세션 및 스캔 사용자를 참조한다. 정산 분담별 완료 거래는 `(settlement_id, receiver_id)` 고유 인덱스로 중복을 막는다. 영수증은 소유자·상태와 이미지 경로를 저장하고 이미지 바이너리는 DB에 넣지 않는다.
- 앱 환경변수 이름만 확인했다: `DATABASE_URL`, `DATABASE_SSLMODE`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `CLOVA_OCR_INVOKE_URL`, `CLOVA_OCR_SECRET`, `ALLOWED_ORIGINS`, `FRONTEND_DIST_DIR`, `KAKAO_JS_KEY`, `PORTONE_TEST_ENABLED`, `PORTONE_STORE_ID`, `PORTONE_CHANNEL_KEY`, `PORTONE_API_SECRET`, `VERCEL`, `NEIGHBORFOOD_BACKEND`, `VITE_API_BASE_URL`. 실제 비밀값은 읽거나 보고하지 않았다.
- 현행 저장소의 의도는 게시글 이미지 `food-images`와 비공개 영수증 `receipts` 분리다. **실제 버킷 공개 설정·정책·서명 URL TTL은 확인하지 않았다.** 로컬의 새 영수증은 `data/receipts`에 저장하고 인증된 본인에게만 제공하며 기존 `uploads/receipt_*`에 대한 앱 경유 공개 접근을 차단했다. 정적 파일을 앱 밖의 프록시/CDN이 직접 제공한다면 이 차단을 우회할 수 있으므로 별도 점검이 필요하다.

### 적용 순서 및 안전 조건

1. 운영 변경 전에 승인받은 DB 백업을 만들고 **별도로 Storage 객체도 백업**한다. Supabase DB 백업에 Storage 객체가 포함된다고 가정하지 않는다. 백업 복원 가능 여부와 다운타임을 격리 프로젝트에서 확인한다. [Supabase 백업](https://supabase.com/docs/guides/platform/backups), [프로젝트 복제](https://supabase.com/docs/guides/platform/clone-project).
2. 실제 스키마·마이그레이션 이력, 중복/외래키 불일치, 권한과 데이터 보존 요구를 먼저 확인한다. `scripts/supabase_migrate.py`는 기존 `001_supabase.sql`의 초기 설치용이지 `002`·`003`을 자동 적용하는 도구가 아니다. 이미 사용 중인 DB에 `001`을 재실행하지 않는다.
3. 격리된 동일 버전 DB에서 `002_ocr_guard.sql` → `003_trade_verification.sql`을 검토·적용한다. 각각 트랜잭션으로 작성됐지만 대부분의 `CREATE`/`ADD COLUMN`은 재실행 가능한 형태가 아니다. 테이블·컬럼·인덱스가 이미 있거나 기존 중복으로 고유 인덱스를 만들 수 없으면 중단하고 차이를 조사한다. PostgreSQL 서버에서 필요한 앱 DB 역할의 권한도 점검한다.
4. 운영 적용은 별도 승인·검증된 백업 후 동일한 순서로 진행하고, 서버와 프런트를 함께 배포한다. OCR 중단과 외부 진입 차단은 유지한다.
5. SQL 실행 중 오류 시 해당 트랜잭션을 롤백한다. 이미 `COMMIT`된 변경에 단순 `ROLLBACK`을 실행해도 이전 상태로 돌아가지 않는다. 장애 시 우선 OCR 스위치와 외부 진입을 차단하고 추가형 스키마를 보존한다. DB 복원·데이터 삭제는 별도 승인과 검증된 복원 절차가 필요하다. 이전 앱으로 되돌리면 새 DB 스위치를 무시하는 구 경로가 노출될 수 있으므로 WAF와 직접 백엔드 경로를 차단한 상태에서만 복구를 판단한다.

읽기 전용 사전 확인 예시(대상 DB를 두 번 확인하고 권한 있는 운영자가 실행):

```sql
SELECT to_regclass('public.neighborfood_schema_version') AS base_version_table,
       to_regclass('public.ocr_guard_settings') AS ocr_settings,
       to_regclass('public.ocr_requests') AS ocr_requests,
       to_regclass('public.qr_verification_events') AS qr_events;
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('transactions', 'qr_sessions', 'location_verify_sessions')
  AND column_name IN ('settlement_id', 'transaction_id', 'scanner_id', 'location_session_id');
```

새 OCR 요청의 `object_name`, `storage_kind`, `scan_id`, `status`는 저장 실패 후 미연결 객체 조사의 단서다. 권한 있는 관리자가 `object_name IS NOT NULL AND scan_id IS NULL`을 먼저 조사하고 DB·Storage 양쪽을 대조한다. 조회만으로 고아라고 단정하거나 자동 삭제하지 않는다. 보존 기간과 정리 승인 절차는 미확정이다.

### 격리 리허설 결과

- PGlite의 빈 PostgreSQL 호환 환경에서 `001` 적용, 가상 사용자 삽입 후 `002`·`003` 각각을 별도 트랜잭션에서 적용·롤백했다. 새 테이블이 사라지고 가상 사용자가 보존됐다.
- 이어 `002`·`003`을 적용했다. 가상 사용자 1명 보존, OCR 기본값 `enabled=0`, 새 테이블 4개에 RLS 활성, `anon`의 OCR 요청 테이블 SELECT 및 `authenticated`의 QR 감사 테이블 SELECT 권한 없음, QR의 GPS 세션 컬럼 존재를 확인했다.
- 이는 SQL 문법·일부 권한과 롤백 리허설일 뿐 실제 Supabase 서버, 기존 운영 데이터, 앱 DB 역할, Storage 정책 또는 PostgreSQL 다중 인스턴스 동시성 테스트가 아니다.

## 4. OCR 제한과 긴급 중단

호출 흐름: 인증된 영수증 업로드 → 4 MiB 이하 및 JPEG/PNG/TIFF MIME·확장자·이미지 내용·24MP 이하 검사 → DB 잠금으로 사용량 예약 → 중단 스위치 재확인 및 전송 상태 기록 → 서버에서만 OCR → 파싱·비공개 저장·영수증/호출 기록 확정. 외부 공급자 키를 프런트에 넘기지 않는다.

- 초기 예시값은 UTC 기준 회원 일 3회·월 30회, 서비스 전체 월 300회이며 **운영 확정 금액이나 무료 한도가 아니다**. 실제 가격·서비스 규모를 확인한 뒤 승인된 운영 설정으로 결정해야 한다.
- PostgreSQL에서는 설정 행 잠금, SQLite에서는 `BEGIN IMMEDIATE`로 예약을 직렬화한다. 모든 앱 인스턴스가 **같은 PostgreSQL DB와 보호된 API 경로**를 사용해야 전역 상한이 의미 있다. 프로세스 로컬 카운터가 아니다.
- 예약·전송·성공·실패·취소를 기록하고, 실패·타임아웃·전송 여부가 불분명한 요청과 취소까지 보수적으로 한도에 포함한다. 계정별 5초 속도 제한과 이미지 중복 검사, `Idempotency-Key` 재생 방지를 사용한다. 한도 초과는 HTTP 429와 재시도 시각을 제공한다. DB 오류는 외부 호출 없이 실패 처리한다.
- 격리 동시성 테스트에서 다중 계정 6개 요청에 전역 한도 2를 적용했을 때 모의 OCR 호출은 2회였다. 다른 경계·실패·멱등성·권한 사례도 SQLite 테스트에 포함된다. 실제 PostgreSQL 다중 서버에서의 부하·동시성은 미검증이다.
- 관리자 `GET/PATCH /api/admin/ocr`와 대시보드의 스위치는 서버 관리자 인가와 변경 감사 기록을 사용한다. 기본값은 중단이다. 외부 안전 확인 체크는 **관리자의 확인 진술일 뿐 NAVER/Vercel 설정을 프로그램이 검증하지 않는다**. 이미 공급자에게 전송된 요청은 긴급 중단으로 취소할 수 없다.
- 수동 영수증 입력은 유지한다. 수동 입력과 인식 품목이 없는 영수증은 신뢰온도를 올리지 않는다. 유효하게 인식된 영수증은 중복 확정 없이 신뢰온도에 최대 0.3을 같은 트랜잭션으로 반영하고 99를 넘지 않게 제한한다.

## 5. NAVER Cloud 비용 보호: 실제 적용 여부

**이번 작업에서 콘솔 설정, 실제 쿼터, 단가, 잔여 무료량, 과금 알림 또는 강제 차단을 확인하거나 변경하지 않았다. 설정 증거도 없다.** 다음은 운영자가 실제 상품·도메인에 맞게 수행할 절차다.

1. [CLOVA OCR 도메인 안내](https://guide.ncloud-docs.com/docs/clovaocr-domain)를 기준으로 사용 중인 도메인과 실제 호출 경로를 확인한다. API Gateway를 사용할 수 있는 상품·경로인지, 다른 직접 호출이 우회할 수 없는지 검증한다.
2. [API Gateway Usage Plan](https://guide.ncloud-docs.com/docs/apigw-apigw-2-3)에서 적용 가능한 호출률·일/월 쿼터를 확인하고 실제 Product/API/Stage에 연결한다. 테스트 호출 및 공급자 계측으로 제한 도달 시 **정말 공급자 호출이 차단되는지** 검증한다. 적용 범위, 초과 동작, 별도 API Gateway 비용은 실제 계약과 화면에서 확인한다.
3. [Cost Explorer 예산](https://guide.ncloud-docs.com/docs/costexplorer-budget)에서 예산·알림 수신자를 설정한다. 전일 비용 기반 알림은 지연될 수 있으며 **알림은 지출 강제 차단이 아니다**. 청구 단가, 무료 제공량, 부가 비용과 경계 초과 비용을 별도로 확인한다.
4. 독립적인 강제 제한을 실제로 확보하지 못하면 OCR 차단을 유지한다. 사용량·한도·차단 테스트 증거는 비밀값을 제외하고 운영 기록으로 남긴다.

## 6. Vercel Firewall 및 실 OCR 상태

- 실제 프로젝트·환경·규칙·직접 백엔드 주소를 확인하지 못했다. 따라서 차단이 실제로 켜져 있다고 주장할 수 없으며, 해제하거나 개방하지도 않았다.
- 운영자가 [Vercel WAF Custom Rules](https://vercel.com/docs/vercel-firewall/vercel-waf/custom-rules)에 따라 대상 프로젝트/환경/호스트 및 `/api/receipt/scan` 경로의 Deny 규칙을 확인하고 게시 상태를 확인해야 한다. Vercel을 거치지 않는 백엔드 직접 경로가 있다면 그 경로도 별도로 차단해야 한다.
- 외부 독립 제한과 DB 전역 제한·관리자 중단·모의 동시성·권한 테스트를 실제 배포에서 검증하기 전까지 차단을 유지한다. 이후 승인된 최소 호출만 허용하고 공급자 호출량·과금·재차단/개방 여부를 기록한다. **실제 OCR 호출과 최종 Firewall 상태는 미검증**이다.

## 7. 거래 A/B 시나리오와 실패 이력

- 기준선 격리 재현에서 로그인하지 않은 QR 발급이 HTTP 200이었고 수령자 혼자 거래 수락·완료를 각각 HTTP 200으로 처리할 수 있었다. 수정 후에는 비로그인 QR 발급 401, 수령자 수락 403, 직접 완료 409를 테스트했다.
- 정책: A가 게시글과 약속을 만들고 B가 신청하면 A만 수락한다. B가 해당 거래의 최근 GPS를 확인해 QR을 발급하고 A가 스캔한다. 서버가 당사자·거래·GPS·QR·상태를 확인한 뒤 QR 사용과 완료를 원자적으로 기록한다. 정산은 참여자의 GPS·QR을 주최자가 검증하고 납부 상태와 완료 거래를 함께 확인한다.
- 범위 밖 위치·정확도 불량·타인·다른 거래·취소·QR 만료/재사용·동시 스캔·이중 평가, 정산 완료 중간 삽입 실패와 약속 변경 재인증을 격리 테스트했다. QR 재발급 시 이전 미사용 QR은 만료하고 QR에 발급 당시 GPS 세션을 연결한다. 게시글과 정산의 약속 변경은 한 트랜잭션으로 반영한다.
- 측정 반경은 100m, 브라우저가 보고한 정확도 허용값은 기존 ±1500m에서 ±100m로 엄격하게 조정했다. 정확도가 나쁜 기기는 실외 등에서 재시도해야 할 수 있다. **위치값과 정확도는 클라이언트가 위조할 수 있으며, 이 검사는 물리적 현장 존재의 강한 증명이 아니다.**
- 신뢰온도 기준선에서 수동 영수증 응답은 +0.3을 표시했지만 실제 회원 점수는 바뀌지 않았다. 수정 후 가상 수동 영수증 저장 전후 점수는 모두 36.5였고, 인식 영수증의 원자적 점수 갱신·상한·실패 롤백은 테스트했다.

### 재현 가능한 가상 시연

차단된 격리/승인된 테스트 환경에서 가상 계정 A/B를 사용한다. A가 나눔 글과 좌표를 등록하고 B가 신청한다. A가 신청을 수락한 후 B가 GPS를 인증해 QR을 발급한다. A가 해당 거래의 QR을 스캔 또는 직접 입력한다. 양쪽 거래 내역을 새로고침해 완료를 확인하고 동일 QR의 재사용이 실패하는지 확인한다. 실제 카메라·GPS와 실제 Supabase는 별도 실환경 검증이 필요하다.

## 8. UI 및 모바일 확인

- 기존 QR 정사각형 가이드·네 모서리와 영수증 세로형 촬영 영역을 유지했다. 거래 화면에 역할별 신청·수락·GPS·QR 경로와 상태를, 영수증 화면에 중단 안내·직접 입력 경로를, 관리자에 전역 사용량과 중단 상태를 표시한다. QR 재사용 등 실패 시 성공이 아닌 실패 상태가 표시되는 것을 확인했다.
- 390×844 가상 Chromium에서 화면 캡처 및 실제 조작으로 수령자 GPS(좌표 에뮬레이션) → QR 발급 → 제공자 토큰 직접 입력 → 양측 완료, OCR 중단 안내 → 수동 입력·저장, 관리자 사용량 화면을 확인했다. 별도 가상 거래에서는 발급 화면이 생성한 PNG를 QR 사진 입력 요소에 주입해 디코딩과 거래 완료를 확인했다. 카메라 권한이 없는 환경에서 스캔 화면은 권한 안내를 표시했다.
- 실제 스마트폰 카메라·촬영 사진의 QR 인식·GPS, 키보드/안전 영역의 모든 경우, 마이페이지·자동완성 전 화면 회귀와 기존 승인 시안의 완전한 전후 비교는 미확인이다. 디자인 합격은 사용자 확인 전까지 단정하지 않는다.

## 9. 실제 실행한 테스트와 미수행 검증

| 항목 | 실행 결과 | 범위·한계 |
| --- | --- | --- |
| 기준선 `python -m pytest tests -q` | 32개 통과 | 격리 복사본, 기존 코드 기준 |
| 최종 `python -m pytest tests -q --disable-warnings --ignore=tests/test_security_baseline_probe.py` | 53개 통과, 경고 279개 | SQLite 임시 DB, 외부 OCR 모의. 제외 경로는 격리 복사본에만 있던 취약한 기준선 재현용 임시 테스트다. |
| `npm run build` | `tsc -b && vite build` 성공 | 격리 복사본, 실제 배포 아님 |
| PGlite `001`→`002`→`003`, 개별 롤백 리허설 | 위 3절의 보존·RLS·권한·GPS 결합 확인 | 실제 Supabase 서버·기존 데이터 아님 |
| 로컬 FastAPI + 가상 모바일 Chromium | GPS·QR·완료, QR 재사용 실패, 생성 PNG의 사진 입력 디코딩, OCR 중단·수동 영수증, 관리자 대시보드 확인 | 가상 계정·위치와 프로그램으로 주입한 이미지; 외부 카메라/지도/공급자 미사용 |
| `seed_admin.py promote` / `revoke` | 격리 가상 계정 대화식 승격·회수 성공, 관리자 API 200→403 확인 | 운영 계정 미변경 |

실제 Supabase 정책/Storage/복원, 배포 및 운영 로그, NAVER 차단/과금, Vercel Firewall, 실제 OCR, 휴대폰 카메라·GPS·사진 인식, 실제 결제/PortOne은 수행하지 않았다. 역사 검색은 제한된 패턴의 점검이며 모든 비밀정보 부재를 증명하지 않는다. 저장소 이력에는 과거 기본 관리자 자격증명 관련 문구가 있었으므로 실제 사용 여부를 운영자가 확인하고 필요하면 회전해야 한다. 현재 운영 자격증명은 읽지 않았다.

## 10. 남은 승인·권한 및 운영 후속 작업

1. 운영 담당자: 백업·복원·Storage 객체, 실제 스키마/RLS/정책·DB 계정 권한을 확인하고 격리 Supabase에 마이그레이션 및 다중 인스턴스 테스트를 수행한다.
2. NAVER/Vercel 운영자: 5·6절의 독립 제한과 직접 접근 차단을 실제 콘솔에서 검증하고 증거를 남긴다. 실제 사용량과 비용을 확인하기 전에는 OCR을 열지 않는다.
3. 시연 담당자: 가상 계정을 정상 가입한 뒤 대상 DB와 백업 확인 후 `python seed_admin.py promote`, 종료 후 `python seed_admin.py revoke`를 대화식으로 사용한다. ID·자격증명을 저장소/보고서에 기록하지 않는다. 운영 DB 권한 변경은 별도 승인 대상이다.
4. 사용자와 시연 담당자: 스마트폰 카메라·사진 QR·GPS·실제 화면, 시안 비교, 두 계정 교환 및 실 OCR을 승인된 범위에서 확인한다. 위치 위조와 OCR 사용량·실패 계수 정책, 이미지 보존 기간 및 객체 정리 권한도 결정한다.
5. 전 게이트 통과 후 변경 파일과 비밀정보 유입 여부를 검토하고 팀 정책에 따른 통합 PR/병합 및 배포를 수행한다. 실제 상태가 확인되지 않은 항목을 완료로 체크하지 않는다.

## 11. GitHub 반영 및 후속 Git Bash 절차

현재 push하지 않았으므로 반영 URL은 없다. 아래는 **위 운영·보안·실환경 게이트와 검토를 모두 통과한 뒤에만** 사용할 예시다. 대상 브랜치와 기존 작업을 먼저 확인하며 `git add .`를 사용하지 않는다.

```bash
cd /c/Users/bluem/Neighborfood
git status --short --branch
git fetch origin
# 팀 정책과 원격 기본 브랜치를 확인한 후, 이름이 사용 중이 아니면:
git switch -c feat/integration-safety

git add README.md Capstone.md NeighborFood_Architecture_Plan.md \
  docs/SUPABASE_MIGRATION.md docs/INTEGRATION_REPORT.md \
  migrations/002_ocr_guard.sql migrations/003_trade_verification.sql \
  app/db/base.py app/db/ocr_guard.py app/db/trade_verification.py \
  app/db/qr_db.py app/db/location_verify_db.py app/db/receipt_db.py \
  app/db/settlement_db.py app/db/transaction_db.py app/models/qr.py \
  app/routers/admin.py app/routers/location_verify.py app/routers/posts.py \
  app/routers/qr.py app/routers/ratings.py app/routers/receipt.py \
  app/routers/settlements.py app/routers/transactions.py \
  frontend-react/src/migration/admin.tsx frontend-react/src/migration/location.tsx \
  frontend-react/src/migration/qr.tsx frontend-react/src/migration/receipt.tsx \
  frontend-react/src/migration/trades.tsx frontend/Local_Verify_Demo.html \
  frontend/QR_Scan.html frontend/Receipt_Verify.html \
  main.py requirements.txt seed_admin.py reset_db.py \
  tests/test_ocr_guard.py tests/test_trade_verification.py \
  tests/test_receipt_privacy.py tests/test_receipt_trust.py \
  tests/test_settlement_flow.py tests/test_supabase_storage.py

git diff --cached --stat
git diff --cached --check
# 스테이징한 내용·비밀정보·개인정보를 안전한 환경에서 검토한 후:
git commit -m "feat: improve transaction verification and OCR safeguards"
git push -u origin feat/integration-safety
# 팀의 승인된 PR/병합 절차와 배포 후 원격 상태를 확인한다.
```
