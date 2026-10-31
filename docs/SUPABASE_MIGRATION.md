# Supabase 스키마 복구와 배포 절차

## 현재 상태와 안전 경계

이 저장소의 기준 경로는 `supabase/migrations/`다. `migrations/001_supabase.sql`, `002_ocr_guard.sql`, `003_trade_verification.sql`은 비교·검증을 위해 보존한 **이전 원본**이며, 새 파일과 함께 직접 실행하지 않는다. 과거의 001 전용 `scripts/supabase_migrate.py`는 Supabase 이력을 기록하지 않아 제거했다.

실제 운영 `public` 스키마, Supabase 마이그레이션 이력, Storage 버킷·정책, Vercel 배포는 아직 확인되지 않았다. 코드와 격리 테스트만으로 운영 DB 복구가 완료된 것은 아니다. 운영 자동 배포는 비활성 상태로 두고, 운영 DB의 파괴적 변경이나 자동 배포 활성화는 별도 승인 없이 수행하지 않는다. 기존 Vercel OCR Firewall을 해제하지 않는다.

| 순서 | 정식 마이그레이션 | 내용 |
| --- | --- | --- |
| 1 | `20261031000100_initial.sql` | 앱 테이블 21개 및 버전 표식, 인덱스·관계·RLS |
| 2 | `20261031000200_ocr_guard.sql` | OCR 설정·호출·관리 감사 테이블 3개, 기본 비활성 |
| 3 | `20261031000300_trade_verification.sql` | 정산·거래별 GPS/QR 연결, 제약·인덱스, QR 감사 테이블 |

세 파일은 `auth`·`storage` 스키마와 Storage 버킷을 생성·초기화하지 않는다. 원본 001의 `public` 전체 테이블·시퀀스에 대한 역할 권한 회수를 앱 소유 객체만 대상으로 한정했다. 원본 002/003의 명시적 `BEGIN`/`COMMIT`은 제거하고 Supabase 실행기의 파일별 트랜잭션에 맡긴다. 기존 앱 테이블의 RLS와 `anon`/`authenticated` 접근 차단은 유지한다.

`public.neighborfood_schema_version`의 `28190b4-v1`은 초기 스키마의 과거 표식일 뿐 002/003의 적용 이력이 아니다. 실제 마이그레이션 이력은 `supabase_migrations.schema_migrations`에서 확인한다.

## 1. 운영자가 먼저 수행할 읽기 전용 점검

1. 대상이 올바른 서울 프로젝트인지 확인한다. DB 백업을 만들고 복원 가능성을 격리 환경에서 확인한다. **Storage 객체는 DB 백업과 별도로 보존**한다. 사용자·게시글 등 데이터 행, 접속 문자열, 키, 세션 토큰을 로그나 GitHub에 올리지 않는다.
2. Supabase SQL Editor에서 아래 쿼리를 실행한다. 모두 조회 전용이다. 테이블·컬럼·정책 이름과 집계 결과만 공유하고 비밀정보나 서비스 데이터를 공유하지 않는다.

```sql
-- public 테이블과 각 테이블의 RLS 상태. auth/storage 자체는 변경하지 않는다.
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
ORDER BY c.relname;

-- 앱 RLS 정책과 anon/authenticated 테이블 권한을 확인한다.
SELECT tablename, policyname, roles, cmd FROM pg_policies
WHERE schemaname = 'public' ORDER BY tablename, policyname;
SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')
ORDER BY table_name, grantee, privilege_type;

-- 앱 필수 컬럼, 특히 거래·정산·GPS·QR 및 OCR 설정을 확인한다.
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- 인덱스와 제약·외래키를 정식 마이그레이션과 대조한다.
SELECT tablename, indexname, indexdef
FROM pg_indexes WHERE schemaname = 'public'
ORDER BY tablename, indexname;
SELECT t.relname AS table_name, c.conname, c.contype, pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'public'
ORDER BY t.relname, c.conname;

-- 이력 테이블의 존재부터 확인한다. 없으면 다음 이력 SELECT는 실행하지 않는다.
SELECT to_regclass('supabase_migrations.schema_migrations') AS migration_history;

-- 기존 버킷의 공개 여부와 정책 이름만 확인한다. 객체와 정책은 수정하지 않는다.
SELECT id, public FROM storage.buckets WHERE id IN ('food-images', 'receipts');
SELECT tablename, policyname, roles, cmd FROM pg_policies
WHERE schemaname = 'storage' ORDER BY tablename, policyname;
```

이력 테이블이 있을 때만 별도로 `SELECT version FROM supabase_migrations.schema_migrations ORDER BY version;`을 실행한다. `public.ocr_guard_settings`가 있을 때만 `SELECT enabled, user_daily_limit, user_monthly_limit, global_monthly_limit FROM public.ocr_guard_settings WHERE id = 1;`을 실행한다. 예상 기본값은 `0, 3, 30, 300`이다. 기존 값이 다르다고 자동으로 덮어쓰지 않는다.

`food-images`는 공개, `receipts`는 비공개여야 한다. 실제 기존 정책과 버킷이 예상과 다르면 중단하고 운영자가 확인한다. RLS가 켜져 있다는 사실만으로 앱 DB 역할에 올바른 권한이 있다고 단정하지 않는다. 실제 클라이언트 권한·RLS 정책과 서버 역할도 별도로 확인한다.

## 2. 최초 DB 구축과 이력 불일치 처리

1. GitHub Integration의 Working directory는 `.`, production branch는 `main`으로 둔다. 현재 **Deploy to production은 끈 상태**다. `supabase/config.toml`에는 운영 `[remotes]`, Storage 버킷, Auth 설정을 선언하지 않는다.
2. Supabase CLI 설치 후 운영자가 대화형으로 로그인하고 프로젝트를 연결한다. 프로젝트 참조는 대시보드에서 확인하고, 비밀번호·토큰은 명령행 인자나 로그에 넣지 않는다.

```sh
supabase login
supabase link --project-ref <대시보드에서_확인한_프로젝트_참조>
supabase migration list --linked
supabase db push --linked --dry-run
```

3. 세 버전의 이력과 실제 객체를 대조한다. 앱 객체가 전혀 없고 세 버전이 모두 미적용일 때만 세 파일이 순서대로 적용 대상인지 확인한다. 다른 `public` 객체가 존재하면 이름 충돌·권한을 함께 검토한다. 이력에 기존 원격 버전이 있는데 저장소에 파일이 없거나, 일부 앱 객체가 남아 있거나, 이력상 적용됐지만 실제 객체가 없으면 **중단**한다. 기존 수동 실행은 Supabase 이력을 남기지 않았을 수 있다.
4. 불일치 상황에서는 SQL·컬럼·타입·기본값·인덱스·FK·CHECK·RLS·역할 권한을 모두 대조하고 백업과 데이터 보존 방안을 검토한다. 무조건 `migration repair`로 applied/reverted를 찍거나 기존 SQL을 재실행하지 않는다. 정확한 보정 계획을 별도로 승인받아야 한다. 특히 앱 테이블만 지웠는데 이력은 남은 경우 CLI는 이미 적용된 파일을 건너뛸 수 있다.
5. 검증된 백업, 격리 리허설과 **운영 변경 승인 후에만** 운영자가 아래 명령을 실행한다. 실패하면 중단하고 이력과 실제 스키마를 다시 읽기 전용으로 조사한다. 각 파일이 성공할 때마다 이력이 기록되므로 앞 파일이 이미 완료된 경우 전체가 한 번에 롤백된 것으로 가정하지 않는다.

```sh
supabase db push --linked
supabase migration list --linked
python scripts/check_supabase.py
```

`check_supabase.py`는 필수 테이블·컬럼 접근성과 두 버킷의 존재·공개 여부를 읽기 전용으로 확인한다. 이력·모든 제약·RLS 정책 전체를 검증하지는 않는다. 앱은 PostgreSQL 시작 시 26개 앱/표식 테이블의 필수 컬럼을 확인하고 누락 또는 접근 불가 항목을 명시한다. 인덱스·FK·RLS·이력의 일치 여부는 위 운영 점검이 별도로 필요하다. 오류 메시지를 없애기 위해 DDL을 서버 시작 시 자동 실행하지 않는다.

기존 `scripts/import_sqlite.py`는 대상의 모든 `public` 테이블이 비어 있어야 한다. 002가 만드는 `ocr_guard_settings`에는 초기 행이 있으므로 현재 정식 001→003 적용 직후에는 이 도구가 중단된다. OCR 기본 차단을 지우거나 기존 값을 덮어쓰며 강행하지 않는다. 기존 SQLite 데이터 복구가 필요하면 데이터·감사 보존을 별도 설계하고 백업·승인을 거쳐 진행한다. `scripts/import_uploads.py`의 Storage 이전도 별도 작업이며 DB 가져오기와 서로 자동 롤백되지 않는다.

## 3. GitHub 자동 동기화와 Vercel 순서

Supabase 공식 GitHub Integration은 `supabase/migrations/`와 이력을 인식하며, production 자동 배포를 켜면 `main`의 새 마이그레이션을 적용한다. 그러나 Supabase와 Vercel이 같은 push를 독립적으로 감시하면 **DB 적용 성공 전에 새 API가 배포될 수 있다**. 따라서 이 저장소의 운영 경로는 아래 **단일 실행자**를 사용한다.

1. Supabase Integration은 연결하되 **Deploy to production을 계속 끈다**. preview 브랜치 기능은 별도 설정과 요금제에 따른다. 이 상태에서 GitHub Actions의 Supabase CLI만 운영 마이그레이션을 실행한다. Integration의 production 자동 실행과 Actions를 동시에 켜지 않는다.
2. 루트 `vercel.json`은 `main`의 API 프로젝트 Git 자동 배포를 비활성화하도록 설정한다. Vercel 프로젝트의 실제 Root Directory가 저장소 루트이고 이 설정이 적용되는지 대시보드에서 먼저 확인한다. 다른 Vercel 프로젝트·수동 배포·Deploy Hook·우회 워크플로는 별도이며, 그 경로가 `main`을 자동 배포하면 순서 보장은 성립하지 않는다.
3. `.github/workflows/production-deploy.yml`은 `main` push 또는 수동 실행에서만 동작한다. 저장소 변수 `PRODUCTION_DEPLOY_ENABLED`가 정확히 `true`가 아니면 운영 작업은 **실패가 아닌 skipped**로 표시된다. push 전 저장소에서 이 변수가 설정되지 않았는지 확인한다. GitHub Environment `production`에 승인자와 배포 브랜치 제한을 설정하고, 아래 Secrets를 운영자가 직접 등록한다.

| GitHub Environment secret | 용도 |
| --- | --- |
| `SUPABASE_ACCESS_TOKEN` | 해당 프로젝트 범위의 Supabase CLI 토큰 |
| `SUPABASE_DB_PASSWORD` | 해당 프로젝트 DB 비밀번호 |
| `SUPABASE_PROJECT_ID` | 대상 프로젝트 참조 |
| `VERCEL_TOKEN` | 해당 API 프로젝트 배포·승격 권한 토큰 |
| `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | 대상 API 팀·프로젝트 식별자 |
| `VERCEL_AUTOMATION_BYPASS_SECRET` | 스테이징된 배포에 Vercel Deployment Protection이 있을 때만 필요 |

Supabase 공식 문서는 `supabase link`용 토큰에 Project Settings, API Keys, API Key Secrets의 읽기 권한을 명시한다. DB 비밀번호와 Vercel 토큰은 각 해당 대상에 필요한 최소 권한으로 관리한다. Vercel bypass secret은 보호된 배포뿐 아니라 일부 Firewall 검사를 우회할 수 있으므로 신뢰된 환경에만 보관하며 워크플로의 `/posts` 점검에만 사용한다. 기존 OCR 경로의 Firewall 규칙은 변경하거나 테스트 호출하지 않는다.

4. 별도 운영 승인과 전체 격리·운영 최초 구축 검증 후에만 저장소 변수 `PRODUCTION_DEPLOY_ENABLED=true`를 설정한다. 이후 한 `main` push는 `supabase db push` 성공 → Vercel production 환경의 비승격 배포(`--skip-domain`) → 그 배포의 `GET /posts`가 정상 JSON 응답인지 확인 → 성공 시에만 승격한다. 하나라도 실패하면 다음 단계는 실행되지 않는다. 같은 워크플로의 운영 배포는 직렬화하고 DB 적용 전과 승격 전에 해당 커밋이 현재 `main`인지 확인한다. 마지막 확인 직후 새 push가 발생하는 경쟁까지 원자적으로 막지는 못하므로 다른 배포 경로를 차단하고 운영 상태를 관찰한다. `/posts` 확인은 인증·거래·RLS·Storage 전체의 검증을 대신하지 않는다.
5. 이미 성공한 DB 마이그레이션은 이후 Vercel 빌드·점검 실패로 자동 롤백되지 않는다. 호환되는 이전 API를 유지하고 원인·이력·실제 스키마를 조사한다. 코드 롤백이나 DB 복원은 별도 승인과 검증된 절차로 진행한다. 향후 스키마 변경은 이전 API와 호환되는 추가 → 배포·이전 → 별도 승인된 제거 순서로 설계한다.

운영 설정·Secrets·승인, 실제 GitHub Actions 실행, Supabase Integration 상태와 Vercel 프로젝트 설정은 이 저장소에서 자동으로 완료되지 않는다. GitHub Actions를 사용하지 않고 Integration의 production 자동 배포를 선택한다면 Actions 운영 작업은 끄고, Vercel 자동 배포도 계속 차단한 뒤 Supabase 적용 성공을 확인하고 별도로 Vercel을 배포해야 한다. 독립된 두 자동 배포만으로는 순서를 보장할 수 없다.

## 4. 검증 결과와 남은 확인

격리된 PostgreSQL 17에서 Supabase CLI로 001→002→003을 적용하고 재실행 시 이력이 중복되지 않음을 확인했다. 별도 DB에 적용한 과거 SQL과 235개 컬럼, 68개 인덱스, 92개 제약을 대조했고, 앱/표식 테이블 26개 RLS, 공개 역할의 테이블·시퀀스 권한 차단, 합성 `auth`·`storage` 객체와 무관한 `public` 권한 보존, OCR 기본 비활성을 확인했다. 별도 실패 유발 마이그레이션에서는 CLI가 실패하고 해당 파일의 테이블 생성과 이력 기록이 롤백됐다. 이 검증은 실제 Supabase의 Storage 정책이나 운영 DB를 확인한 것이 아니다.

격리 PostgreSQL에 연결한 실제 FastAPI 서버에서 `/posts`, 합성 회원가입·로그인·채팅·거래·GPS·QR·정산 및 OCR 차단을 확인했다. 스키마 생성 권한이 없는 합성 서버 역할(`BYPASSRLS` 및 필요한 테이블·시퀀스 권한 부여)로도 같은 흐름을 확인했다. 이는 운영 서버 역할을 확인했다는 뜻이 아니다. SQLite 회귀 테스트 53개와 명시적으로 활성화한 PostgreSQL 회귀 테스트 1개가 통과했다. 해당 PostgreSQL 테스트는 `NEIGHBORFOOD_TEST_POSTGRES_DSN`을 지정하지 않으면 건너뛰며, 지정할 때는 사전 마이그레이션된 로컬 `nf_test_*` DB만 허용하고 테스트 DDL을 롤백한다.

워크플로는 `actionlint`로 검사했고, 로컬 HTTP 점검에서 정상 응답만 통과하고 503·잘못된 JSON·리다이렉트는 승격을 차단함을 확인했다. 실제 GitHub Actions/Vercel 실행은 아니다.

**미완료:** 실제 운영 스키마·이력 조회 및 복원, 실제 Storage/RLS·버킷 정책 확인, GitHub Actions/Integration 운영 실행과 Vercel 배포·API 확인, 실기기·외부 서비스 검증. 이 항목은 운영자 권한·승인과 실제 프로젝트 연결 후 별도로 확인한다.

참고: [Supabase GitHub Integration](https://supabase.com/docs/guides/deployment/branching/github-integration), [Supabase CLI 환경·권한](https://supabase.com/docs/guides/deployment/managing-environments), [Vercel Git 배포 설정](https://vercel.com/docs/project-configuration/git-configuration), [Vercel 단계별 배포·승격](https://vercel.com/docs/deployments/promoting-a-deployment).
