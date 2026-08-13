# NeighborFood — 정산 시스템 구현 계획 (A+ 안)

> 작성: 2026-08-03  
> 최종 수정: 2026-08-06  
> 상태: **전체 흐름 구현 완료** — 채팅→약속→GPS(100m)→QR→납부→정산완료→매너평가 end-to-end 동작 확인  
> 참조 화면: `Settlement.html` · `Group_Chat.html` · `Local_Verify_Demo.html` (모두 실데이터 연동)

---

## 1. 개요 및 설계 원칙

### 핵심 컨셉: 신뢰 기반 납부 추적 + 자동화 보완
앱이 실제 자금을 보관하거나 이동시키지 않는다. 참여자는 카카오페이·계좌이체 등 외부 수단으로 직접 송금하고, 앱은 상태만 추적한다. 단, 기존 구현된 GPS·QR·trust_score 인프라를 연결해 신뢰 모델을 보강한다.

### 기존 인프라와의 연결 원칙
- 새로운 시스템을 만들지 않고 기존 코드를 연결(wiring)하는 방식을 최우선으로 한다.
- `qr_sessions`, `location_verify_sessions`, `trust_score`, `groupbuy_participants`를 모두 재활용한다.

---

## 2. DB 설계

### 2-0. `posts` 테이블 — 약속 컬럼 추가 (2026-08-06)
채팅 단계에서 정산 생성 전에도 약속을 확정할 수 있도록 `posts`에 약속 정보를 저장한다.  
정산 생성 시 `create_settlement()`가 이 값을 자동 승계한다.

```sql
ALTER TABLE posts ADD COLUMN appointment_place TEXT;
ALTER TABLE posts ADD COLUMN appointment_at    TEXT;
ALTER TABLE posts ADD COLUMN appointment_lat   REAL;  -- GPS 100m 검증 기준 위도
ALTER TABLE posts ADD COLUMN appointment_lng   REAL;  -- GPS 100m 검증 기준 경도
```
(`auth_db.py`의 `init_auth_db()`에 멱등 마이그레이션 포함)

### 2-1. `settlements` 테이블 — 정산 헤더
`transaction_db.py`의 `init_transaction_db()`에 추가 (같은 DB 파일 사용).

```sql
CREATE TABLE IF NOT EXISTS settlements (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id           INTEGER NOT NULL REFERENCES posts(id),
    requester_id      INTEGER NOT NULL REFERENCES users(id),
    total_amount      INTEGER NOT NULL,
    account_info      TEXT,
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','completed','canceled')),
    appointment_place TEXT,          -- 거래 약속 장소 (posts에서 승계 또는 채팅에서 변경)
    appointment_at    TEXT,          -- 거래 약속 일시(ISO-8601)
    appointment_lat   REAL,          -- 약속 좌표 위도 (참여자 GPS 100m 검증 기준)
    appointment_lng   REAL,          -- 약속 좌표 경도
    created_at        TEXT NOT NULL,
    completed_at      TEXT
);
```

### 2-2. `settlement_shares` 테이블 — 참여자별 분담
```sql
CREATE TABLE IF NOT EXISTS settlement_shares (
    settlement_id  INTEGER NOT NULL REFERENCES settlements(id),
    user_id        INTEGER NOT NULL REFERENCES users(id),
    amount         INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'unpaid'
                   CHECK (status IN ('unpaid','paid','noshow')),
    gps_verified   INTEGER NOT NULL DEFAULT 0,  -- Step 1: 거래 지점 GPS 인증 완료(100m)
    quality_agreed INTEGER NOT NULL DEFAULT 0,  -- Step 2: 대면 QR 인증 완료(품질 동의)
    auto_confirmed INTEGER NOT NULL DEFAULT 0,  -- (레거시, 미사용 — 하위호환 보존)
    paid_at        TEXT,
    created_at     TEXT NOT NULL,
    PRIMARY KEY (settlement_id, user_id)
);
```

### 추가 컬럼 정리
| 컬럼 | 용도 | 세팅 시점 | 비고 |
|---|---|---|---|
| `gps_verified` | 거래 지점 100m 이내 GPS 인증 완료 | `POST /api/settlements/{id}/shares/me/gps-done` | **Step 1** |
| `quality_agreed` | 대면 QR 인증 완료(품질 동의) | `POST /api/settlements/{id}/shares/me/qr-done` | **Step 2** |
| `auto_confirmed` | ~~GPS+24h 자동 납부~~ | ~~조회 시점 서버 판단~~ | **제거됨**(레거시 컬럼 보존) |

### 스키마 파일 위치
`neighborfood_schema.sql`의 `-- 5-2. manner_ratings` 다음, `-- 6. qr_sessions` 앞에 `-- 5-3. settlements` 섹션으로 삽입.

---

## 3. API 설계

### 라우터 파일
`app/routers/settlements.py` 신규 생성 → `main.py`에 `/api/settlements` 등록.

### 엔드포인트 목록

**정산 헤더 관리**

| Method | Path | 권한 | 설명 |
|---|---|---|---|
| `POST` | `/api/settlements` | 주최자 | 정산 생성 — `posts.appointment_*` 자동 승계 |
| `GET` | `/api/settlements/post/{post_id}` | 관련자 | 게시글 기준 정산 조회 |
| `GET` | `/api/settlements/{id}` | 관련자 | 정산 상세 |
| `GET` | `/api/settlements/my` | 본인 | 내 정산 목록 |
| `POST` | `/api/settlements/{id}/appointment` | 주최자 | 정산의 약속 장소·시간·좌표 확정 |
| `POST` | `/api/settlements/{id}/complete` | 주최자 | 정산 완료 처리 (미납 0명 조건) → `transactions` 행 자동 생성 |
| `POST` | `/api/settlements/{id}/cancel` | 주최자 | 정산 취소 |

**참여자 인증 (순차 2단계)**

| Method | Path | 권한 | 설명 |
|---|---|---|---|
| `POST` | `/api/settlements/{id}/shares/me/gps-done` | 참여자 | **Step 1**: GPS 인증 완료 보고 — 서버가 `location_verify_sessions`에서 `current_lat/lng`를 조회해 약속 좌표까지 Haversine 거리 재검증(≤100m) |
| `POST` | `/api/settlements/{id}/shares/me/qr-done` | 참여자 | **Step 2**: QR 인증 완료 보고 — GPS Step 1 선행 필수, 서버가 `qr_sessions.status=VERIFIED` 재검증 |
| `POST` | `/api/settlements/{id}/shares/me/pay` | 참여자 | 납부 표시 — `gps_verified=1 AND quality_agreed=1` 모두 충족해야 허용 |
| `GET` | `/api/settlements/{id}/participants/gps-status` | 주최자 | 참여자별 GPS 인증 현황(거리·시각) — 5초 폴링용 |

**노쇼 처리**

| Method | Path | 권한 | 설명 |
|---|---|---|---|
| `POST` | `/api/settlements/{id}/shares/{uid}/noshow` | 주최자 | 노쇼 신고 → trust_score -1.0 + 신고 자동 기록 |
| `DELETE` | `/api/settlements/{id}/shares/{uid}/noshow` | 주최자 | 노쇼 취소 → unpaid 복원 + trust_score +1.0 + 신고 삭제 |

**게시글 약속 (정산 없이도 채팅 단계에서 확정 가능)**

| Method | Path | 권한 | 설명 |
|---|---|---|---|
| `POST` | `/posts/{id}/appointment` | 주최자 | 게시글에 약속 저장 — 정산이 있으면 자동 동기화, 없으면 정산 생성 시 승계 |

### 주요 비즈니스 규칙

**정산 생성 (`POST /api/settlements`)**
```
요청자 = post.author_id 본인만 가능
동일 post_id에 pending/completed 정산이 이미 있으면 409
groupbuy_participants 에서 참여자 목록 조회
분담 = total_amount // N  (나머지는 주최자 몫, shares에 미포함)
settlement_shares를 참여자 수만큼 일괄 INSERT (status='unpaid')
```

**자동 납부 확인 판단 (`GET /api/settlements/{id}` 조회 시)**
```
각 share에 대해:
  share.status == 'unpaid' AND
  location_verify_sessions에 해당 user_id(subject_id)의
    LOCATION_VERIFIED 기록이 있음 AND
  해당 세션의 verified_at 으로부터 24시간 초과
    → share.status = 'paid', auto_confirmed = 1, paid_at = now
```
별도 스케줄러 없이 조회 시점에 서버가 판단.

**노쇼 신고 (`POST .../shares/{user_id}/noshow`)**
```
share.status = 'noshow'
users.trust_score -= 1.0 (원자적, 클램프 0~99)
신고 사유를 reports 테이블에 자동 기록 (target_type='user')
```

**노쇼 취소 (`DELETE .../shares/{user_id}/noshow`)**
```
조건: settlement.status = 'pending' AND share.status = 'noshow'
share.status → 'unpaid' (paid_at = NULL 초기화)
users.trust_score += 1.0 (원자적, 클램프 0~99)
자동 기록된 신고 삭제 — status='pending'인 것만 (관리자가 이미 처리한 신고는 보존)
```

**참여 권한 제한 (기존 `posts.py` 수정)**
```python
# join_groupbuy 시작 부분에 추가
unpaid = conn.execute("""
    SELECT 1 FROM settlement_shares ss
    JOIN settlements s ON s.id = ss.settlement_id
    WHERE ss.user_id = ? AND ss.status = 'unpaid'
      AND s.status = 'pending'
    LIMIT 1
""", (uid,)).fetchone()
if unpaid:
    raise HTTPException(400, "미완료된 정산이 있어 공동구매에 참여할 수 없습니다.")
```

---

## 4. 인증 흐름 — 순차 2단계 GPS → QR (2026-08-06 확정)

### 4-1. 납부 버튼 활성화 조건

```
gps_verified = 1  (Step 1)   AND
quality_agreed = 1 (Step 2)
→ "납부했어요" 버튼 활성화
```

### 4-2. Step 1: GPS 위치 인증 (≤100m)

```
[참여자] Local_Verify_Demo.html?settlementId={id}&subjectId={uid}
  ↓ 페이지 진입 시 GET /api/settlements/{id} → appointment_lat/lng 로드
  ↓ 약속 좌표로 location_verify 세션 자동 생성 (target = 약속 장소)
  ↓ "GPS 인증하기" 클릭 → 현재 위치 vs 약속 좌표 거리 계산(Haversine)
  ↓ ≤100m → LOCATION_VERIFIED → "정산으로 돌아가기"

POST /api/settlements/{id}/shares/me/gps-done
  ↓ 서버: location_verify_sessions.current_lat/lng 조회
  ↓       appointment_lat/lng 까지 Haversine 재계산 (서버 검증)
  ↓ ≤100m → settlement_shares.gps_verified = 1
```

**핵심**: 프론트 전송 값을 신뢰하지 않고 DB에 저장된 current_lat/lng로 서버에서 재검증.

### 4-3. Step 2: QR 인증 (대면 품질 동의)

```
[참여자] Settlement.html → "2단계 QR 인증하러 가기"
  ↓ QR_Scan.html (issue 모드) → 자기 QR 발급

[주최자] QR_Scan.html (scan 모드) → 참여자 QR 스캔
  ↓ qr_sessions.status → VERIFIED

[참여자] "정산으로 돌아가기" → Settlement.html?settlementId=&qr=1

POST /api/settlements/{id}/shares/me/qr-done
  ↓ 서버: qr_sessions WHERE subject_id = user_id AND status = 'VERIFIED' 재검증
  ↓ settlement_shares.quality_agreed = 1
```

**qr.py 라우터 의존 없음** — `qr_sessions` 테이블을 직접 조회해 settlements.py가 자체 완결.

### 4-4. 정산 완료 → transactions 연동

```
POST /api/settlements/{id}/complete
  ↓ status → 'completed'
  ↓ paid 참여자마다 transactions 행 자동 생성 (provider=주최자, receiver=참여자, status='completed')
  ↓ My_Activity.html 거래 내역에 노출 + "매너 평가하기" 활성화
```

---

## 5. ~~GPS 자동 확인 흐름~~ → **제거됨** (2026-08-06)

24h 경과 후 자동 납부 확인(`auto_confirm_by_gps`) 로직은 설계 결정에 따라 제거됨.  
`settlement_shares.auto_confirmed` 컬럼은 하위호환을 위해 보존하나 더 이상 세팅되지 않음.

대체: **Step 1 GPS 인증**(≤100m, 즉시) → **Step 2 QR 인증**(대면) → **납부 버튼 활성화** 순차 게이트.

---

## 6. 신뢰 모델 (시나리오별 처리)

| 시나리오 | 처리 | trust_score 변화 | 구현 상태 |
|---|---|---|---|
| 정상 완료 | shares 전원 paid → completed | 없음 (매너 평가로 별도 반영) | ✅ |
| 참여자 노쇼 | `POST .../noshow` → share='noshow' + reports 자동 생성 | 참여자 **-1.0** | ✅ |
| 노쇼 취소(철회) | `DELETE .../noshow` → share='unpaid' 복원 + 신고 삭제 | 참여자 **+1.0** 복원 | ✅ |
| 주최자 귀책 | 참여자가 일반 신고(`POST /api/reports`) | 관리자 확정 후 **-2.0** + 정지 | 🔶 신고만 |
| 주최자 먹튀 | 관리자 확정 → 계정 정지 | **-2.0** | 📋 2차 예정 |
| 참여자 먹튀 | 강화 노쇼 → fraud 상태 | **-2.0** | 📋 2차 예정 |
| 미납 정산 누적 | 다음 공동구매 참여 자동 차단 | — | ✅ |

### trust_score 페널티 전체 체계

| 이벤트 | 변화량 | 처리 방식 |
|---|---|---|
| 매너 평가 👍 (thumbs up) | **+0.5** | `ratings.py` → `trust_score + 0.5` |
| 매너 평가 👎 (thumbs down) | **-0.5** | `ratings.py` → `trust_score - 0.5` |
| 평가 작성 보상 | **+0.1** | `ratings.py` → 평가 작성자에게 지급 |
| 노쇼 신고 | **-1.0** | `settlements.py POST .../noshow` |
| 노쇼 취소(복원) | **+1.0** | `settlements.py DELETE .../noshow` |
| 먹튀/주최자 귀책 | **-2.0** | 관리자 확정 후 자동 적용 (2차 예정) |

모든 변경은 `MAX(0, MIN(99, trust_score ± ?)` 원자적 클램프 적용.

---

## 7. 프론트엔드 — 전체 흐름 (2026-08-06 완성)

### 7-0. 완성된 end-to-end 흐름

```
[Group_Chat.html]
  주최자: "약속 변경/장소·시간 정하기" → 모달 (게시글 위치 프리필)
         → POST /posts/{id}/appointment (정산 전에도 저장 가능)
  주최자: "정산 시작하기" → Settlement.html?postId={id}
  참여자: "거래 인증·정산" → Settlement.html?settlementId={id}

[Settlement.html]
  정산 없음 + 주최자 → 금액 입력 폼 → POST /api/settlements 생성
  정산 있음 + 참여자 → 3단계 버튼 분기:
    ① "1단계 · GPS 인증하러 가기" → Local_Verify_Demo.html (약속 좌표 자동 로드)
    ② "2단계 · QR 인증하러 가기" → QR_Scan.html (발급 모드)
    ③ "납부했어요" (gps+qr 완료 시 활성)
  정산 있음 + 주최자 → 납부 현황 + GPS 현황 5초 폴링
                      → "참여자 QR 스캔하기" (QR 대기 참여자 있을 때)
                      → "정산 완료 처리" (미납 0명 시 활성)
  정산 완료 → "매너 평가 남기기" → My_Activity.html

[My_Activity.html]
  완료 거래마다 "매너 평가하기" → 평가 모달 → POST /api/ratings
  → trust_score ±0.5 반영
```

### 7-1. Settlement.html URL 진입 방식
```
Settlement.html?postId=123       ← 채팅방 "정산 시작하기" / Group_Buy_Detail "정산하기"
Settlement.html?settlementId=456 ← 채팅방 "거래 인증·정산" / Transaction_History "정산 보기"
```

### 7-2. 참여자 버튼 3단계 상태

| 단계 | 조건 | 상단 버튼 | 하단 버튼 |
|---|---|---|---|
| 약속 미확정 | `!appointmentAt && !appointmentPlace` | (비활성) 거래 장소·시간 확정 대기 중 | — |
| GPS 미인증 | `!gpsVerified` | (비활성) GPS 인증 후 진행 가능 | ✅ 1단계 · GPS 인증하러 가기 |
| QR 미인증 | `gpsVerified && !qualityAgreed` | (비활성) QR 인증 후 납부 가능 | ✅ 2단계 · QR 인증하러 가기 |
| 납부 가능 | `gpsVerified && qualityAgreed` | ✅ {금액} 납부했어요 (활성) | — |
| 납부 완료 | `status='paid'` | (비활성) 납부 완료됨 | — |

### 7-3. 진입점 파일 목록
- `Group_Chat.html` — 약속 모달, "정산 시작하기", "거래 인증·정산" 버튼
- `Group_Buy_Detail.html` — "정산하기" 버튼
- `Transaction_History.html` — "정산 보기" 링크
- `My_Activity.html` — 완료 거래 "매너 평가하기" 버튼

---

## 8. 테스트 시나리오 (`nf_functional_test.py`)

섹션 12 (거래) 뒤에 섹션 12-1 (정산) 추가:

```
1) 정산 생성 (POST /api/settlements)         → 201, shares 자동 생성 확인
2) 게시글 기준 정산 조회                      → 200, pending 상태
3) 중복 정산 생성 시도                        → 409
4) 참여자 납부 (POST .../shares/me/pay)       → 200, paid_at 세팅 확인
5) 납부 중복 시도                             → 400/409
6) 비관련자 접근                              → 403
7) 노쇼 신고 (POST .../shares/{uid}/noshow)  → 200, trust_score 감소 확인
8) 주최자 완료 처리                           → 200, status=completed 확인
9) 완료 후 취소 시도                          → 400
10) 미납 정산 있는 사용자 공동구매 참여 시도  → 400 차단 확인
```

---

## 9. 구현 순서

```
✅ ① DB 스키마 (settlements + settlement_shares DDL, transaction_db.py init)
✅ ② settlement_db.py 신규 (CRUD + 인증 함수 일체)
✅ ③ settlements.py 라우터 신규 (API 13종 — 노쇼·GPS·QR·약속 포함)
✅ ④ main.py 라우터 등록
⬜ ⑤ posts.py join_groupbuy 참여 차단 로직 — 로컬 수동 적용 필요
✅ ⑥-대체 settlements.py에서 qr_sessions 직접 검증 (qr.py 의존 제거)
✅ ⑦ Settlement.html 3단계 버튼 + GPS 폴링 + QR 안내 + 완료 후 매너평가 버튼
✅ ⑧ Group_Buy_Detail.html + Transaction_History.html 진입점
✅ ⑨ Group_Chat.html 약속 모달 + 정산 시작하기 + GPS 이동 버튼
✅ ⑩ Local_Verify_Demo.html 정산 모드 — 약속 좌표 자동 로드
✅ ⑪ My_Activity.html 매너 평가 버튼 + 모달
✅ ⑫ auth_db.py posts 약속 컬럼 마이그레이션
✅ ⑬ posts.py POST /posts/{id}/appointment 신규
✅ ⑭ settlement_db.py create_transactions_for_settlement (완료→거래 연동)
✅ ⑮ location_verify.py 전체 라우터 재구성 (stub→완전한 파일)
✅ ⑯ location_verify_db.py DEFAULT_RADIUS_M = 100
✅ ⑰ nf_functional_test.py 시나리오 추가
✅ ⑱ 마크다운 4개 파일 업데이트 (2026-08-06)
```

---

## 10. 영향 범위 (수정 파일 목록)

| 구분 | 파일 | 변경 종류 | 상태 |
|---|---|---|---|
| 스키마 | `neighborfood_schema.sql` | settlements·shares DDL + posts 약속 컬럼 | ✅ |
| DB 초기화 | `transaction_db.py` | settlements DDL + gps_verified + appointment_lat/lng | ✅ |
| DB 초기화 | `auth_db.py` | posts 약속 컬럼 DDL + 멱등 마이그레이션 | ✅ |
| DB 레이어 | `settlement_db.py` | CRUD + GPS/QR 검증 + transactions 연동 + 폴링 함수 | ✅ |
| 라우터 신규 | `settlements.py` | API 13종 (약속·GPS·QR·노쇼·완료→거래 포함) | ✅ |
| 라우터 수정 | `posts.py` | `POST /posts/{id}/appointment` 신규 | ✅ |
| 라우터 재구성 | `location_verify.py` | stub → 완전한 라우터 (5개 엔드포인트, 보안 포함) | ✅ |
| DB 레이어 수정 | `location_verify_db.py` | DEFAULT_RADIUS_M = 100 | ✅ |
| 라우터 등록 | `main.py` | settlements import + include_router | ✅ |
| 기존 라우터 수정 | `posts.py` | `join_groupbuy` 참여 차단 로직 | ⬜ 미적용 |
| 프론트 | `Settlement.html` | 3단계 버튼·GPS 폴링·QR 안내·완료 후 리뷰 버튼 | ✅ |
| 프론트 | `Group_Chat.html` | 약속 모달(좌표 포함)·정산 시작하기·GPS 이동 버튼 | ✅ |
| 프론트 | `Local_Verify_Demo.html` | 정산 모드 약속 좌표 자동 로드·100m 기준 | ✅ |
| 프론트 | `QR_Scan.html` | 정산 흐름 발급 모드 + 복귀 버튼 | ✅ |
| 프론트 | `My_Activity.html` | 완료 거래 매너 평가 버튼 + 모달 | ✅ |
| 프론트 | `Group_Buy_Detail.html` | "정산하기" 진입점 | ✅ |
| 프론트 | `Transaction_History.html` | "정산 보기" 링크 | ✅ |
| 테스트 | `nf_functional_test.py` | 섹션 12-1 (노쇼 취소 포함) | ✅ |

**신규 파일**: `settlement_db.py`, `settlements.py` 2개  
**재구성 파일**: `location_verify.py` 1개  
**수정 파일**: 12개 (posts.py join_groupbuy 제외)  
**마크다운 업데이트**: 4개 완료