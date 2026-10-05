# PortOne V2 테스트 연동 (2026-09-28)

기준: 원격 main e221dc9. FastAPI + SQLite / React + TypeScript + Vite 구조 유지.

## 구현 범위

- React 정산 상세에 포트원 테스트 결제 영역 추가.
- GPS → QR 완료한 본인의 미납 분담금을 서버에서 읽어 테스트 주문 생성.
- 사용자/정산별 같은 paymentId 재사용, 브라우저 종료 후 승인 재조회 가능.
- PortOne V2 결제 조회로 ID, 상점, 채널, 금액, KRW, TEST 채널, PAID 검증.
- `portone_test_payments`에 상태 저장. 실제 납부 표시·정산 완료·판매자 지급은 변경하지 않음.
- 테스트 취소 상태도 다시 조회 시 반영. 자동 환불, 웹훅, 모바일 리다이렉트는 후속 작업.
- 별도 standalone 테스트 화면이나 기존 HTML 결제 화면을 추가하지 않음.

## 설정

1. 포트원 콘솔에서 V2 상점과 **테스트 채널**을 선택한다. LIVE 채널을 넣으면 결제창 자체에서 실제 청구가 가능하므로 반드시 TEST 채널을 사용한다.
2. 루트 `.env`에 `portone.env.example`의 항목을 추가한다. 기존 Kakao/CLOVA 설정은 유지한다.
3. `PORTONE_STORE_ID`, `PORTONE_CHANNEL_KEY`, `PORTONE_API_SECRET`을 입력하고 `PORTONE_TEST_ENABLED=true`로 바꾼다.
4. API 시크릿은 서버 `.env`에만 저장한다. VITE_ 변수나 채팅에 붙여 넣지 않는다.
5. API와 React 서버를 재시작한다.

```bash
cd /c/Users/bluem/Neighborfood
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

다른 Git Bash:

```bash
cd /c/Users/bluem/Neighborfood/frontend-react
npm install && npm run build && npm run dev
```

React 로그인 → 내 활동 → 정산 → 본인의 정산 상세 → GPS/QR → 테스트 결제창 열기.
승인 여부 다시 확인은 저장된 paymentId를 서버에서 조회한다. 한 사용자/정산은 하나의 테스트 주문을 사용한다.
취소 완료된 주문으로 새 결제가 거부되는 PG라면 새로운 테스트 정산을 만들어 진행한다.
현재 PC 반환값 방식이다. 모바일에서는 아직 사용하지 않는다.

## API / 파일

- GET /api/payments/portone/config: 활성화 상태만 반환.
- POST /api/payments/portone/prepare: settlement_id만 수신, 가격은 DB 기준.
- POST /api/payments/portone/{payment_id}/verify: 본인 주문 조회/검증.
- app/routers/portone.py: API/테스트 주문 저장.
- frontend-react/src/migration/portone.tsx: SDK와 조회 UI.
- main.py: 라우터 및 테스트 테이블 초기화.
- tests/test_portone.py: 금액·권한·게이트·반복 요청·취소·오류 검증.

## 검증 및 제한

Python 전체 tests 17개 통과(신규 12개), TypeScript/Vite 빌드 통과, FastAPI startup/401 확인.
외부 API는 mock 검증이며 실제 PortOne 계정/키 및 PG 결제창 승인 검증은 수행하지 않았다.
기존 GPS/QR의 서버 검증 조건을 사용하며 거래별 세션 결속 강화는 이번 범위에 포함하지 않는다.

## 기존 결제 코드 정리

원격 소스에는 Toss SDK/라우터가 없었다. 문서 내 옛 로컬 변경 안내를 정리했다.
배포 패치는 알려진 로컬 app/routers/toss_test.py, frontend/Toss_Payment_Test.html 및
.env의 TOSS_/TOSSPAYMENTS_ 변수만 백업 후 제거한다.
main.py는 알려진 직접 연동 import/router만 제거했을 때 원격 코드와 일치하는 경우에만 처리한다.
미확인 코드가 남으면 전체 적용을 중단한다. 이때 해당 파일을 확보하여 다시 제작해야 한다.
백업에는 제거된 키가 있을 수 있으므로 Git에 올리거나 공유하지 않는다.
Git 과거 커밋을 재작성하지 않으며 외부 콘솔 키 폐기는 수행하지 않는다.

공식 문서:
- https://developers.portone.io/opi/ko/integration/start/v2/checkout
- https://developers.portone.io/api/rest-v2/payment
