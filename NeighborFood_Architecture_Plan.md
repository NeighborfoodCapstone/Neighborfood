# NeighborFood FastAPI — 아키텍처 현황 및 개발 이력

> 최종 수정: 2026-08-12
> 상태: **핵심 거래 흐름(채팅→약속→GPS 100m 실검증→QR→납부→정산완료→매너평가) 완성 + 관리자·UX 갭 해소 완료**
> 서버: 단일 FastAPI / DB: 단일 SQLite(`data/neighborfood.db`)

---

## 1. 프로젝트 개요

NeighborFood는 이웃 간 식재료 나눔·교환·공동구매를 중개하는 로컬 커뮤니티 플랫폼입니다.
실제 자금 이체 없이 납부 상태만 추적하고, GPS·QR 이중 인증으로 거래 신뢰를 확보합니다.

**핵심 거래 흐름:**
```
게시글 등록 → 채팅(약속 확정) → GPS 100m 실검증 → QR 대면 인증
→ 납부 표시 → 정산 완료 → 매너 평가(trust_score 반영)
```

---

## 2. 기술 스택

| 구분 | 기술 |
|---|---|
| 백엔드 | FastAPI (Python), Uvicorn |
| DB | SQLite 3 단일 파일 (`data/neighborfood.db`) |
| 인증 | Bearer 세션 토큰 (`sessions` 테이블), PBKDF2-SHA256 비밀번호 해시 |
| 프론트엔드 | Vanilla HTML/JS, Tailwind CSS CDN, Material Symbols |
| 지도 | Kakao Maps SDK (`.env` 동적 로드, 소스 코드 키 하드코딩 금지) |
| QR/바코드 | html5-qrcode (QR·1D 동시 인식) |
| 영수증 OCR | CLOVA OCR 연동 |

---

## 3. 디렉토리 구조

```
project_root/
├── main.py                      FastAPI 엔트리포인트 (미들웨어·마운트·라우터 등록)
├── app/
│   ├── config.py                DB_PATH, UPLOAD_DIR, SESSION_TTL_DAYS 등 상수
│   ├── core/
│   │   ├── deps.py              get_current_user / get_current_admin / get_bearer_token
│   │   └── utils.py             now_utc, to_iso, hash_password, verify_password
│   ├── db/
│   │   ├── base.py              make_conn() — sqlite3 Row factory + WAL 설정
│   │   ├── auth_db.py           users · sessions · auth_codes · posts DDL
│   │   ├── member_db.py         wishlists · conversations · messages · conversation_members DDL
│   │   ├── transaction_db.py    transactions · groupbuy_participants · manner_ratings
│   │   │                        settlements · settlement_shares DDL
│   │   ├── settlement_db.py     정산 CRUD + GPS/QR 검증 + transactions 연동 함수
│   │   ├── fridge_db.py         fridge_items DDL + CRUD
│   │   ├── admin_db.py          notices · reports DDL + CRUD
│   │   ├── qr_db.py             qr_sessions DDL + CRUD
│   │   ├── receipt_db.py        receipts · receipt_items DDL + CRUD
│   │   └── location_verify_db.py location_verify_sessions DDL, DEFAULT_RADIUS_M=100
│   ├── models/
│   │   ├── auth.py · user.py · post.py · member.py · fridge.py
│   │   └── qr.py · receipt.py
│   └── routers/
│       ├── auth.py              인증 (register, login, logout, OTP, reset)
│       ├── users.py             회원 프로필·탈퇴·동네 인증·비밀번호 변경
│       ├── posts.py             게시글 CRUD·참여·취소·약속·my-status·자동 만료
│       ├── chat.py              1:1 채팅 + 그룹 채팅
│       ├── wishlist.py          찜 목록
│       ├── transactions.py      거래 생성·상태 전환
│       ├── fridge.py            내 냉장고
│       ├── settlements.py       공동구매 정산 (13종 API)
│       ├── ratings.py           매너 평가 (trust_score 연동)
│       ├── reports.py           신고 제출·취소
│       ├── admin.py             관리자 전용 API
│       ├── location_verify.py   GPS 위치 인증 (Haversine 100m 검증)
│       ├── qr.py                QR 거래 인증
│       └── receipt.py           영수증 OCR 인증
│
├── frontend/
│   ├── shared/
│   │   ├── auth.js              토큰 저장·fetch 자동 인증 주입·logout·401 처리
│   │   ├── guard.js             회원 전용 페이지 접근 가드 (nfRequireMember)
│   │   ├── profile.js           프로필 조회/수정/탈퇴 헬퍼
│   │   └── tokens.css           디자인 토큰 (CSS 변수)
│   └── (HTML 파일 목록은 §9 참조)
│
├── sql/neighborfood_schema.sql  전체 테이블 DDL (단일 진실 소스)
├── data/neighborfood.db         실제 SQLite DB
├── uploads/                     이미지 업로드 저장소
├── seed_posts.py                더미 게시글 시드 (개발용)
├── seed_admin.py                관리자 계정 부트스트랩 (1회성)
├── Seed_Account.py              Capstone_1 테스트 계정 + 완료 거래 시드
├── Seed_capstone_settlement.py  정산 수동 테스트용 시드 (Capstone_1~3)
├── Seed_settlement_verify.py    정산 API 자동 검증 스크립트
├── nf_functional_test.py        전체 기능 자동 테스트 스크립트
├── reset_db.py                  DB 초기화 (테이블 DELETE + Admin 재생성)
└── .env / .env.example          환경변수 (KAKAO_JS_KEY, DB_PATH 등)
```

---

## 4. DB 테이블 구성

| 테이블 | 설명 | 위치 |
|---|---|---|
| `users` | 회원 (login_id·pw·trust_score·role·status·neighborhood_lat/lng) | auth_db |
| `sessions` | Bearer 세션 토큰 | auth_db |
| `auth_codes` | OTP 인증코드 (비밀번호 재설정 전용) | auth_db |
| `posts` | 게시글 통합 (share·exchange·groupbuy, appointment 좌표 포함) | auth_db |
| `wishlists` | 찜 목록 | member_db |
| `conversations` | 채팅방 (kind: direct/group) | member_db |
| `messages` | 채팅 메시지 (is_system 컬럼 포함) | member_db |
| `conversation_members` | 그룹 채팅 멤버십 + 읽음 포인터 | member_db |
| `transactions` | 거래 이력 (pending→confirmed→completed) | transaction_db |
| `groupbuy_participants` | 공동구매 참여자 기록 | transaction_db |
| `manner_ratings` | 매너 평가 (score, comment, trust_score 반영) | transaction_db |
| `settlements` | 공동구매 정산 헤더 | transaction_db |
| `settlement_shares` | 정산 참여자별 분담 (gps_verified·quality_agreed·status) | transaction_db |
| `fridge_items` | 내 냉장고 식재료 | fridge_db |
| `notices` | 관리자 공지사항 | admin_db |
| `reports` | 신고 (target_type: post/user) | admin_db |
| `qr_sessions` | QR 거래 인증 세션 | qr_db |
| `receipts` / `receipt_items` | 영수증 OCR 인증 | receipt_db |
| `location_verify_sessions` | GPS 위치 인증 세션 | location_verify_db |

---

## 5. API 엔드포인트 전체 목록

### 인증 (Auth)
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| POST | `/api/auth/register` | - | 가입 (id·pw·phone) → 세션 토큰 발급 |
| POST | `/api/auth/login` | - | ID·비밀번호 로그인 → 세션 토큰 발급 |
| POST | `/logout` | ✅ | 현재 세션 토큰 폐기 |
| POST | `/request-auth` | - | 비밀번호 재설정 OTP 발송 (30초 쿨다운) |
| POST | `/reset-password` | - | OTP 검증 + 비밀번호 변경 + 전 세션 폐기 |

### 회원 (Users) — `/api/users/*`
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/users/me` | 내 프로필 (전화번호 마스킹, 동네 좌표 포함) |
| PATCH | `/api/users/me` | 닉네임·이미지·이메일·소개·관심·식이 수정 |
| PATCH | `/api/users/me/password` | 비밀번호 변경 (현재 세션 유지, 타 세션 폐기) |
| POST | `/api/users/withdraw` | 탈퇴 (소프트삭제·익명화·전 세션 폐기) |
| POST | `/api/users/neighborhood` | 동네 인증 (이름+GPS 좌표 저장) |

### 게시글 (Posts)
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| POST | `/upload-images` | - | 이미지 업로드 |
| POST | `/posts` | ✅ | 게시글 등록 (author_id=세션 회원) |
| GET | `/posts` | - | 목록 (타입·카테고리 필터, 자동 만료 처리 포함) |
| GET | `/posts/{id}` | - | 단건 (작성자 닉네임·trust_score 조인) |
| PATCH | `/posts/{id}` | ✅ | 게시글 수정 (작성자/admin, 안전 필드 한정) |
| DELETE | `/posts/{id}` | ✅ | 소프트삭제 (작성자/admin) |
| POST | `/posts/{id}/appointment` | ✅ | 약속 장소·시간·좌표 저장 (작성자만, 정산 자동 승계) |
| GET | `/posts/{id}/my-status` | ✅ | 내 역할 조회 (isAuthor, isParticipant) |
| POST | `/posts/{id}/join` | ✅ | 공동구매 참여 (중복·정원 초과·미납 차단) |
| DELETE | `/posts/{id}/join` | ✅ | 참여 취소 (정산 시작 후 차단, 그룹챗 퇴장+시스템 메시지) |

### 채팅 (Chats) — `/api/chats/*`
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/chats` | 1:1 방 생성 (이미 있으면 기존 반환) |
| GET | `/api/chats` | 내 채팅방 목록 (1:1+그룹 통합, 안 읽은 수 포함) |
| GET | `/api/chats/{id}/messages` | 메시지 조회 (증분 폴링) + 읽음 처리 |
| POST | `/api/chats/{id}/messages` | 메시지 전송 |
| POST | `/api/chats/group/{post_id}` | 그룹 채팅방 열기/합류 (작성자·참여자만) |
| GET | `/api/chats/group/{id}/messages` | 그룹 메시지 조회 (발신자 닉네임 포함, is_system 지원) |
| POST | `/api/chats/group/{id}/messages` | 그룹 메시지 전송 |
| GET | `/api/chats/group/{id}/members` | 그룹 참여자 목록 |

### 찜 (Wishlist) — `/api/wishlist/*`
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/wishlist` | 내 찜 목록 (삭제 글 제외) |
| PUT | `/api/wishlist/{post_id}` | 찜 추가 (멱등) |
| DELETE | `/api/wishlist/{post_id}` | 찜 해제 (멱등) |

### 거래 (Transactions) — `/api/transactions/*`
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/transactions` | 내 거래 목록 + 통계 |
| POST | `/api/transactions` | 거래 생성 |
| PATCH | `/api/transactions/{id}` | 상태 전환 (전이 규칙 검증) |

### 정산 (Settlements) — `/api/settlements/*`
| Method | Path | 권한 | 설명 |
|---|---|---|---|
| POST | `/api/settlements` | 주최자 | 정산 생성, 참여자별 분담 자동 계산 |
| GET | `/api/settlements/my` | 본인 | 내가 관련된 정산 목록 |
| GET | `/api/settlements/post/{post_id}` | 관련자 | 게시글 기준 정산 조회 |
| GET | `/api/settlements/{id}` | 관련자 | 정산 상세 |
| POST | `/api/settlements/{id}/shares/me/gps-done` | 참여자 | GPS 인증 완료 표시 (Haversine 100m 서버 재검증) |
| POST | `/api/settlements/{id}/shares/me/qr-done` | 참여자 | QR 인증 완료 표시 (quality_agreed=1) |
| POST | `/api/settlements/{id}/shares/me/pay` | 참여자 | 납부 표시 (GPS+QR 완료 후에만 가능) |
| POST | `/api/settlements/{id}/complete` | 주최자 | 정산 완료 처리 → transactions 행 자동 생성 |
| POST | `/api/settlements/{id}/cancel` | 주최자 | 정산 취소 |
| POST | `/api/settlements/{id}/shares/{uid}/noshow` | 주최자 | 노쇼 신고 (trust_score -1.0, reports 자동 기록) |
| DELETE | `/api/settlements/{id}/shares/{uid}/noshow` | 주최자 | 노쇼 취소 (unpaid 복원, trust_score +1.0, 신고 삭제) |
| GET | `/api/settlements/{id}/participants/gps-status` | 주최자 | 참여자별 GPS 인증 현황 폴링 |

### 매너 평가 (Ratings) — `/api/ratings/*`
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/ratings` | 평가 등록 (transaction_id 기준, trust_score 업데이트) |
| PATCH | `/api/ratings/{id}` | 평가 수정 |
| DELETE | `/api/ratings/{id}` | 평가 삭제 |
| GET | `/api/ratings/received` | 받은 평가 목록 (user_id 파라미터로 타인 조회 가능) |

### 내 냉장고 (Fridge) — `/api/fridge/*`
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/fridge` | 식재료 목록 (유통기한 임박순) |
| GET | `/api/fridge/summary` | 전체/임박(D-3)/만료 개수 |
| POST | `/api/fridge` | 식재료 추가 |
| POST | `/api/fridge/from-receipt` | 영수증에서 냉장고로 가져오기 |
| PATCH | `/api/fridge/{id}` | 식재료 수정 |
| DELETE | `/api/fridge/{id}` | 식재료 삭제 |

### 신고 (Reports) — `/api/reports/*`
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/reports` | 신고 제출 (target_type: post/user) |
| DELETE | `/api/reports/{id}` | 신고 취소 (본인만) |

### 관리자 (Admin) — `/api/admin/*` (admin 가드)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/admin/dashboard` | 회원·게시글·거래·신고대기 KPI 집계 |
| GET | `/api/admin/users` | 회원 목록·검색 (report_count·tx_count 포함) |
| PATCH | `/api/admin/users/{id}` | 회원 정지·복구·역할 승격 |
| GET | `/api/admin/notices` | 공지 목록 |
| POST | `/api/admin/notices` | 공지 작성 |
| DELETE | `/api/admin/notices/{id}` | 공지 삭제 |
| GET | `/api/admin/reports` | 신고 목록 |
| GET | `/api/admin/reports/{id}` | 신고 단건 |
| PATCH | `/api/admin/reports/{id}` | 신고 처리 (resolved·dismissed) |
| GET | `/api/admin/chats` | 채팅방 목록 (모니터링) |
| GET | `/api/admin/chats/{id}/messages` | 채팅 메시지 조회 |

### 공지 공개 API
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/notices` | 공개 공지 목록 (비인증, 최대 50건) |
| GET | `/api/config/kakao-key` | 카카오 JS 키 반환 (프론트 동적 로드용) |

### GPS 위치 인증 — `/api/location-verify/*`
| Method | Path | 인증 | 설명 |
|---|---|---|---|
| GET | `/api/location-verify/health` | - | 상태 확인 |
| POST | `/api/location-verify/dummy-target` | ✅ | 타겟 좌표 기반 인증 세션 생성 (subject_id 서버 고정) |
| POST | `/api/location-verify/{id}/gps-check` | ✅ 소유자 | GPS 좌표 제출 → Haversine ≤100m 판정 |
| POST | `/api/location-verify/{id}/qr-issued` | ✅ 소유자 | QR 세션 연결 |
| GET | `/api/location-verify/{id}` | ✅ 소유자 | 세션 단건 조회 |
| GET | `/api/location-verify/history/list` | ✅ | 이력 (일반: 본인만, admin: 전체) |

### QR 인증 — `/api/qr/*`
`request`, `verify`, `verify/{token}`, `history`

### 영수증 인증 — `/api/receipt/*`
`scan`, `verify`, `issue`, `confirm`, `token/{token}`, `{id}`, `history`

---

## 6. 프론트엔드 페이지 현황

### 사용자 화면

| 파일 | 상태 | 비고 |
|---|---|---|
| `Splash.html` / `Onboarding.html` | ✅ 정적 | 온보딩 플로우 |
| `Login.html` / `Signup.html` | ✅ 연동 | 가입·로그인 API 연결 |
| `Password_Reset.html` | ✅ 연동 | OTP 비밀번호 재설정 |
| `Home.html` | ✅ 연동 | 게시글 목록 실데이터 |
| `Index.html` | ✅ 정적 | 랜딩 페이지 |
| `Map.html` | ✅ 연동 | Kakao 지도 + 주변 게시글 |
| `Search.html` / `Search_Results.html` | ✅ 연동 | 검색 API 연결 |
| `Product_Detail.html` | ✅ 연동 | 나눔·교환 게시글 상세 |
| `Group_Buy_Detail.html` | ✅ 연동 | 공동구매 상세 + 참여/취소 토글 + 작성자 3-dot 메뉴 |
| `Create_Post.html` | ✅ 연동 | 게시글 등록 + 편집 모드(`?edit={id}`) |
| `Reservation.html` | ✅ 연동 | 거래 신청 (실좌표 연동) |
| `Location_Detail.html` | ✅ 연동 | 장소 지도 상세 |
| `Neighborhood_Setting.html` | ✅ 연동 | 동네 인증 (GPS 좌표 저장) |
| `My_Page.html` | ✅ 연동 | 내 프로필·신뢰 온도·리뷰 수 |
| `Edit_Profile.html` | ✅ 연동 | 프로필 수정 (이메일·소개·관심·식이) |
| `My_Activity.html` | ✅ 연동 | 채팅·내 글·거래 내역 탭 + 매너 평가 모달 |
| `Wishlist.html` | ✅ 연동 | 찜 목록 실데이터 |
| `Fridge.html` | ✅ 연동 | 내 냉장고 (수동 추가·영수증 가져오기) |
| `Chat_List.html` / `Chat_Detail.html` | ✅ 연동 | 1:1 채팅 |
| `Group_Chat.html` | ✅ 연동 | 그룹 채팅 + 약속 모달 + 정산 시작 버튼 |
| `Transaction_History.html` | ✅ 연동 | 거래 내역 + 정산 보기 링크 |
| `Settlement.html` | ✅ 연동 | 공동구매 정산 전체 흐름 (주최자/참여자 분기) |
| `Local_Verify_Demo.html` | ✅ 연동 | GPS 100m 위치 인증 (정산 모드 약속 좌표 자동 로드) |
| `QR_Scan.html` | ✅ 연동 | QR·바코드 스캔 (정산 QR 발급 모드 포함) |
| `Receipt_Verify.html` | ✅ 연동 | 영수증 OCR 인증 |
| `Report.html` | ✅ 연동 | 신고 제출 |
| `Help.html` | ✅ 연동 | 고객센터 + 공개 공지 아코디언 (비회원 열람 가능) |
| `Withdraw.html` | ✅ 연동 | 회원 탈퇴 |
| `Verify.html` | ✅ 정적 | OTP 인증 화면 |

### 관리자 화면

| 파일 | 상태 | 비고 |
|---|---|---|
| `Admin_Dashboard.html` | ✅ 연동 | KPI 4종 + 신고 목록 실데이터 |
| `Admin_Users.html` | ✅ 연동 | 회원 목록·검색·정지·승격·로그아웃 |
| `Admin_Notices.html` | ✅ 연동 | 공지 목록·작성·삭제 (예약·푸시는 준비 중 안내) |
| `Admin_Chat_History.html` | ✅ 연동 | 채팅방 목록 + 메시지 조회 |
| `Admin_Report_Detail.html` | ✅ 연동 | 신고 단건 로드 + 기각·경고·삭제·정지 액션 |
| `Admin_Staff_Invite.html` | ⬜ 미연동 | 운영진 목록 하드코딩, 승격 UI 미구현 |

---

## 7. 개발 이력 (시간순)

### 2026-06 초기 구현
- 지역 게시판 (나눔·교환·공동구매) CRUD
- 회원 가입·로그인·OTP 비밀번호 재설정·프로필 수정·탈퇴
- QR 거래 인증·영수증 OCR 인증
- 찜 목록·1:1 채팅·동네 인증
- 거래(`transactions`)·공동구매 참여자(`groupbuy_participants`) 기본 구조
- 내 냉장고·그룹 채팅·관리자(notices·reports) 기본 구현
- 관리자 계정 부트스트랩(`seed_admin.py`)
- 신고(`POST /api/reports`) + 관리자 처리
- GPS 위치 인증(`location_verify_sessions` + `/api/location-verify/*`) 기초 구현

### 2026-07-09 커밋 전 점검
- 공동구매 참여 레이스컨디션 수정 (원자적 `UPDATE` + `rowcount==0` → 409)
- Kakao 지도 키: `Map.html` → `/api/config/kakao-key` 동적 로드 전환
- `neighborfood_schema.sql` 6개 테이블 누락분 동기화
- `tokens.css` 전 39개 화면 적용
- `requirements.txt` FastAPI/Uvicorn 버전 갱신

### 2026-08-03 보안 강화 + 핵심 기능 완성 (P0/P1)
- **Kakao 지도 키 하드코딩 전면 제거** — 잔여 6개 화면 모두 동적 로드로 전환
- **GPS 위치 인증 보안 강화**
  - 전 엔드포인트 `Depends(get_current_user)` 추가
  - `subject_id`를 서버가 로그인 사용자 id로 강제 고정
  - `_assert_owner()` 신설 (소유자/admin만 통과)
  - 이력 조회: 일반 사용자 → 본인 세션만, admin → 전체
  - `mark_qr_verified_by_qr_session()` 실제 호출로 GPS↔QR 연동 완성
- **`Reservation.html`** 실좌표 연동 (기존 하드코딩 제거)

### 2026-08-04 정산 시스템 구현
- **신규 파일**: `settlement_db.py`, `settlements.py`
- **신규 테이블**: `settlements`, `settlement_shares`
- **API 13종** 구현 (생성·목록·상세·GPS완료·QR완료·납부·완료·취소·노쇼 신고/취소·GPS 폴링)
- `Settlement.html` 전체 흐름 실데이터 연동 (주최자/참여자 역할 분기)
- `Group_Buy_Detail.html` "정산하기" 버튼, `Transaction_History.html` "정산 보기" 링크 추가
- 정산 완료 시 `transactions` 행 자동 생성 (매너 평가 흐름 연동)

### 2026-08-07 전체 흐름 완성
- **GPS 100m 실검증** — 기존 self-referencing 구조를 약속 좌표 고정 + Haversine 서버 재검증으로 교체
- **`POST /posts/{id}/appointment`** 신규 (채팅 단계에서 먼저 약속 확정, 정산 생성 시 자동 승계)
- `Group_Chat.html`: "정산 시작하기" 버튼, 약속 모달 GPS 좌표 캡처, `/api/posts/` → `/posts/` 3곳 경로 버그 수정
- `Settlement.html`: "참여자 QR 스캔하기" 버튼, 완료 후 "매너 평가 남기기" 버튼, isAuthor 판별 버그 수정
- `Local_Verify_Demo.html`: 정산 모드 약속 좌표 자동 로드, `RADIUS_M=100`, PWA `isSecureContext` 체크
- `DEFAULT_RADIUS_M` 300 → **100** (프론트·백 동기화)

### 2026-08-12 UX 갭 감사 및 해소 (이번 세션)
기능 갭 감사 보고서(Unreachable UI·Admin 스텁·권장 기능 3개 카테고리)를 기반으로 우선순위별 구현 진행.

**Phase 2 — 관리자 & 핵심 UX**

| 항목 | 파일 | 내용 |
|---|---|---|
| Admin_Notices 라이브 연동 | `Admin_Notices.html` | 공지 목록·작성·삭제 API 연결, 예약·푸시는 "준비 중" 안내, 사이드바 로그아웃 |
| Admin_Chat_History 라이브 연동 | `Admin_Chat_History.html` | 대화방 목록 + 메시지 실데이터, 정적 더미 제거 |
| 공동구매 참여/취소 토글 | `Group_Buy_Detail.html` | `GET /posts/{id}/my-status` 기반 버튼 전환, 취소 시 `DELETE .../join` 호출 |
| 작성자 3-dot 드롭다운 | `Group_Buy_Detail.html` | 수정(`Create_Post.html?edit={id}`) + 삭제(`DELETE /posts/{id}`) 메뉴 |
| 매너 평가 리다이렉트 수정 | `Settlement.html` | 완료 버튼 → `My_Activity.html?tab=history` |
| 공개 공지 UI | `Help.html` | `GET /api/notices?limit=10` 아코디언 표시 (비회원 열람) |
| 게시글 수정 흐름 | `Create_Post.html`, `My_Activity.html` | "수정" 링크 추가, `?edit=` 프리필, `PATCH /posts/{id}` 제출, 참여자 있는 공구 인원·가격 잠금 |

**Phase 3 — 보조 개선**

| 항목 | 파일 | 내용 |
|---|---|---|
| 게시글 자동 만료 | `posts.py` | `list_posts()` 진입 시 만료 글 `expired` 일괄 전환 |
| 참여 취소 그룹챗 연동 | `posts.py` | `messages.is_system` 컬럼 멱등 마이그레이션, 그룹챗 퇴장 + 시스템 메시지 삽입 |
| 취소 버튼 스타일 수정 | `Group_Buy_Detail.html` | Tailwind `error` 색 미정의 문제 → `style.cssText` 인라인 직접 지정(`#ba1a1a`) |

**`GET /api/notices` (공개 공지 API)**: `main.py`에 이미 구현 확인 — 재구현 없음  
**`PATCH /api/users/me/password`**: `users.py`에 이미 구현 확인 — 재구현 없음  
**`DELETE /posts/{id}/join` (백엔드)**: `posts.py`에 이미 구현 확인 — 재구현 없음  
**`Admin_Users.html`·`Admin_Report_Detail.html`**: 이미 라이브 연동 확인 — 재구현 없음

---

## 8. 잔여 작업 목록

| 우선순위 | 항목 | 상세 |
|---|---|---|
| 🔴 **필수** | **미납 정산 참여 차단** | `posts.py`의 `join_groupbuy`에 "진행 중 정산에 미납 share가 있으면 새 공동구매 참여 차단" 로직 적용. 코드 예시는 `Settlement_Implementation_Plan.md` 섹션 3·`settlement_db.py`의 `has_unpaid_settlement()` 참조. 현재 함수는 구현되어 있으나 `join_groupbuy` 내에서 호출이 누락된 상태 |
| 🟡 **권장** | **`Admin_Staff_Invite.html` 연동** | 운영진 목록 하드코딩 → 실데이터 교체. 기존 계정 검색 후 `PATCH /api/admin/users/{id}` (`role='admin'`)으로 승격하는 UI 구현. 백엔드 API는 완비 |
| 🟡 **권장** | **작성자 매너 평가 표시** | `Product_Detail.html`·`Group_Buy_Detail.html` 작성자 카드에 `GET /api/ratings/received?user_id={authorId}` 연동하여 긍정/부정 건수 표시. API 완비 |
| 🟢 **개선** | **관리자 사이드바 배지 동적화** | `Admin_Report_Detail.html`·`Admin_Staff_Invite.html` 사이드바의 신고 배지가 `"24"` 하드코딩. `GET /api/admin/dashboard`의 `reportsPending` 값으로 교체 |
| 🟢 **개선** | **공지 추가 노출** | `Home.html` 상단 배너 등에 `GET /api/notices` 연결하여 사용자 접근성 향상 |
| 🟢 **개선** | **배포 CORS 도메인 제한** | `main.py`의 `allow_origins=["*"]`를 `.env`의 실제 도메인으로 교체 (배포 전 필수) |

---

## 9. 주요 정책 결정 사항

| 항목 | 결정 내용 |
|---|---|
| 게시글 수정 가능 필드 | 제목·설명·카테고리·위치만 허용. 공동구매 인원·가격은 `gb_current==0`일 때만 수정 가능 |
| 참여 취소 정책 | 정산 생성(pending/completed) 전까지 취소 허용. 시간 기반 컷오프 없음 |
| 공지 기능 범위 | 즉시 게시·목록·삭제만 연동. 예약 발행·임시저장·푸시 알림은 스키마 미지원으로 보류 |
| 운영진 관리 | 이메일 초대 없이 기존 계정 검색 → `admin` 역할 승격 방식 유지 |
| 전역 401 리다이렉트 | 적용 안 함. 비회원 홈 접근 probe 회귀 방지를 위해 페이지별 `nfRequireMember()` 수동 방식 유지 |
| GPS 인증 반경 | 300m → **100m** (프론트·백 동기화 완료) |
| 비밀번호 변경 | 현재 세션 유지, 타 기기 세션 일괄 폐기 |
| 공동구매 참여 취소 | `groupbuy_participants` 삭제 + `gb_current` 원자적 감소 + 그룹챗 `conversation_members` 제거 + 시스템 메시지 삽입 (`is_system=1`) |
| 게시글 삭제 | 소프트삭제 (`status='deleted'`). 거래·채팅 이력 보존 |

---

## 10. 개발 환경 명령어

```bash
# 서버 실행
uvicorn main:app --reload

# 프론트엔드 접근 (localStorage 공유를 위해 동일 출처 사용)
http://127.0.0.1:8000/frontend/<파일>.html

# 카메라 사용 화면 (QR·영수증 — HTTPS 또는 localhost 필요)
http://127.0.0.1:8000/QR_Scan.html
http://127.0.0.1:8000/Receipt_Verify.html

# API 문서
http://127.0.0.1:8000/docs

# 더미 데이터
python seed_posts.py

# 관리자 계정 생성/승격
python seed_admin.py                  # 신규 생성 (login_id=Admin)
python seed_admin.py <login_id>       # 기존 계정 admin 역할 승격

# 테스트 계정 시드 (정산 수동 테스트용)
python Seed_Account.py               # Capstone_1 + 완료 거래 1건
python Seed_capstone_settlement.py   # Capstone_1~3 + 공동구매 정산 시드

# 자동 기능 테스트
python nf_functional_test.py

# DB 초기화 (전체 데이터 삭제 + Admin 재생성)
python reset_db.py
```

**테스트 계정 기본값:**

| 계정 | login_id | password | 역할 |
|---|---|---|---|
| 관리자 | `Admin` | `admin0000` | admin |
| 일반1 | `Capstone_1` | `capstone1` | user |
| 일반2 | `Capstone_2` | `capstone2` | user |
| 일반3 | `Capstone_3` | `capstone3` | user |

---

## 11. 범위 외 항목 (Excluded)

- 유통기한 임박 추천 / 레시피 추천 / 식재료 객체 인식
- 오프라인 모드 / 실시간 WebSocket 채팅 (현재 REST 4초 폴링)
- 이메일 초대 기반 운영진 관리 (현재 계정 승격 방식)
- 공지 예약 발행 / 임시저장 / 푸시 알림
- 실제 결제 / 외부 송금 연동

## 12. 금지 항목 (Prohibited)

- 식품 소분 판매 UI
- 포장 훼손 거래 UI