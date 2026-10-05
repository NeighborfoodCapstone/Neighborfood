import * as PortOne from "@portone/browser-sdk/v2";
import { useEffect, useState } from "react";
import { api, send, useData, useAction, Feedback, uid, token, Page, Load, href, go, money } from "./core";

const savedKey = (id: number) => `nf-portone-test-${uid()}-${id}`;

// PG redirects append parameters outside the app's hash router.
export function acceptPaymentReturn() {
  const query = new URLSearchParams(location.search);
  if (query.get("nfPaymentReturn") !== "1") return;
  const params: Record<string, string> = {};
  for (const key of ["paymentId", "code", "message", "settlementId", "quick"]) {
    const value = query.get(key);
    if (value) params[key] = value;
  }
  history.replaceState(null, "", location.pathname + href("Payment_Result", params));
}

export function PortOneTest({ settlementId }: { settlementId: number; payable: boolean }) {
  return <section className="rx-card">
    <h3>테스트 결제</h3>
    <p className="rx-muted">결제 내용을 확인하고 포트원 테스트 결제를 진행합니다.</p>
    <div className="rx-actions">
      <a className="rx-primary" href={href("Payment_Checkout", { settlementId })}>결제 확인으로</a>
      <a href={href("Payment_Preview")}>화면 미리보기</a>
    </div>
  </section>;
}

export function PaymentCheckout({ q, preview = false }: { q: URLSearchParams; preview?: boolean }) {
  const id = Number(q.get("settlementId"));
  const state = useData(!preview && id > 0 ? `/api/settlements/${id}` : null);
  const config = useData(preview ? null : "/api/payments/portone/config");
  const action = useAction();
  const d = state.data?.settlement;
  const me = d?.shares?.find((share: { userId: number }) => share.userId === uid());
  const ready = d?.status === "pending" && me?.payable && config.data?.enabled;
  async function checkout() {
    const prepared = await send("/api/payments/portone/prepare", { settlement_id: id });
    const request = prepared.request;
    localStorage.setItem(savedKey(id), request.paymentId);
    if (prepared.status === "PAID") {
      go("Payment_Result", { settlementId: id, paymentId: request.paymentId });
      return;
    }
    const redirect = new URL(location.pathname, location.origin);
    redirect.searchParams.set("nfPaymentReturn", "1");
    redirect.searchParams.set("settlementId", String(id));
    try {
      const response = await PortOne.requestPayment({ ...request, redirectUrl: redirect.toString() });
      go("Payment_Result", { settlementId: id, paymentId: request.paymentId,
        code: response?.code, message: response?.message });
    } catch {
      go("Payment_Result", { settlementId: id, paymentId: request.paymentId,
        message: "결제창 응답을 받지 못했습니다. 서버에서 승인 여부를 확인합니다." });
    }
  }
  return <Page title="결제 확인">
    <p className="rx-muted">결제 확인 → GPS·QR 인증 → 결제창 → 결과 확인</p>
    <a className="rx-primary" href={href("Payment_Quick")}>포트원 결제창 빠른 테스트</a>
    {preview && <p className="rx-badge">화면 미리보기 · 실제 결제 요청 없음</p>}
    {!preview && !(id > 0) && <p>정산 상세에서 결제 확인으로 이동해 주세요.</p>}
    <Load state={state}>
      {(preview || me) && <>
        <section className="rx-card">
          <h2>{preview ? "공동구매 분담금 (예시)" : `공동구매 정산 #${d.id}`}</h2>
          <p>{preview ? "참여자 본인 분담금" : me.nickname}</p>
          <h2>{money(preview ? 12000 : me.amount)}</h2>
          <p>결제 수단: 카드</p>
          <p className="rx-muted">테스트 결제이며 실제 납부·판매자 송금에는 반영하지 않습니다.</p>
        </section>
        <section className="rx-card">
          <h3>거래 인증</h3>
          <p>GPS {preview || me.gpsVerified ? "완료" : "대기"} · QR {preview || me.qualityAgreed ? "완료" : "대기"}</p>
          {!preview && !me.payable && <p>진행 중인 미납 분담금의 GPS·QR 인증을 완료해 주세요.</p>}
          {!preview && d.status === "pending" && me.status === "unpaid" && <div className="rx-actions">
            {!me.gpsVerified ? <a className="rx-primary" href={href("Local_Verify_Demo", { settlementId:id, returnTo:"payment" })}>GPS 인증으로 계속</a>
              : <a className="rx-primary" href={href("QR_Scan", { settlementId:id, returnTo:"payment", mode:"issue" })}>{me.qualityAgreed ? "QR 인증 내역 확인" : "QR 인증으로 계속"}</a>}
          </div>}
        </section>
      </>}
      {!preview && d && !me && <p>본인의 분담금이 있는 참여자만 결제할 수 있습니다.</p>}
    </Load>
    {!preview && config.data && !config.data.enabled && <p>포트원 테스트 설정이 필요합니다. 설정 후 다시 열어 주세요.</p>}
    <Feedback error={config.error} />
    <Feedback {...action} />
    <div className="rx-actions">
      {preview ? <a className="rx-primary" href={href("Payment_Preview", { stage: "result" })}>결과 화면 미리보기</a>
        : <button className="rx-primary" disabled={action.busy || !ready} onClick={() => action.run(checkout)}>{action.busy ? "결제창 연결 중…" : "테스트 결제하기"}</button>}
      {!preview && id > 0 && <a href={href("Settlement", { settlementId: id })}>정산으로 돌아가기</a>}
      {!preview && id > 0 && <a href={href("Payment_Result", { settlementId: id, paymentId: localStorage.getItem(savedKey(id)) || undefined })}>이전 결제 결과 확인</a>}
      {preview && <a href={href("Home")}>홈으로</a>}
    </div>
  </Page>;
}

export function PaymentResult({ q, preview = false }: { q: URLSearchParams; preview?: boolean }) {
  const id = Number(q.get("settlementId"));
  const paymentId = q.get("paymentId") || (!preview && id > 0 ? localStorage.getItem(savedKey(id)) : "");
  const [revision, retry] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ verified: boolean; status: string; amount: number; currency: string; checkedAt: string; recordedStatus: string } | null>(null);
  const [sample, setSample] = useState("PAID");
  useEffect(() => {
    if (preview || !paymentId) return;
    const controller = new AbortController();
    setBusy(true); setError(""); setResult(null);
    api(`/api/payments/portone/${encodeURIComponent(paymentId)}/verify`, { method: "POST", signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setResult(data); })
      .catch(e => { if (!controller.signal.aborted) setError(e.message || "승인 조회에 실패했습니다."); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [preview, paymentId, revision]);
  const state = preview ? sample : busy ? "CHECKING" : error ? "ERROR" : result?.status || "EMPTY";
  const titles: Record<string, string> = { CHECKING: "결제 승인 확인 중", PAID: "테스트 결제 완료", FAILED: "결제가 완료되지 않았습니다", CANCELLED: "결제가 취소되었습니다", PARTIAL_CANCELLED: "일부 금액이 취소되었습니다", ERROR: "승인 여부를 확인하지 못했습니다", EMPTY: "조회할 결제 정보가 없습니다" };
  const approved = preview ? sample === "PAID" : result?.verified === true;
  return <Page title="결제 결과">
    <p className="rx-muted">결제 확인 → GPS·QR 인증 → 결제창 → 결과 확인</p>
    {preview && <p className="rx-badge">예시 화면 · 포트원 조회를 실행하지 않습니다</p>}
    <section className="rx-card rx-payment-result" aria-live="polite" aria-busy={busy}>
      <div className="rx-result-symbol" key={state} aria-hidden="true">{state === "CHECKING" ? <span className="rx-spinner" /> : approved ? "✓" : "!"}</div>
      <h2>{titles[state] || "결제 승인 대기 중"}</h2>
      <p>{state === "CHECKING" ? "서버에서 포트원 결제 내역을 조회하고 있습니다." : approved ? "서버 검증 완료: 테스트 결제 승인 상태입니다." : "승인 완료가 확인되기 전에는 결제 성공으로 처리하지 않습니다."}</p>
      {paymentId && <p style={{ overflowWrap: "anywhere" }}>결제 ID: {paymentId}</p>}
      {!preview && result && <>
        <p>포트원 조회 상태: {result.status}</p>
        <p>검증 금액: {money(result.amount)} ({result.currency})</p>
        <p>서버 저장 상태: {result.recordedStatus}</p>
        <p>서버 확인 시각: {new Date(result.checkedAt.replace(" ", "T")).toLocaleString("ko-KR")}</p>
      </>}
      {!preview && q.get("message") && <p>결제창 안내: {q.get("message")}</p>}
      {!preview && q.get("code") && <p>결제창 코드: {q.get("code")}</p>}
      <Feedback error={error} />
      <p className="rx-muted">테스트 기록만 저장하며 기존 정산의 납부 상태는 변경하지 않습니다.</p>
    </section>
    {preview && <div className="rx-actions">{[["PAID", "성공"], ["CHECKING", "확인 중"], ["FAILED", "실패"], ["CANCELLED", "취소"], ["ERROR", "조회 오류"]].map(([value,label]) => <button key={value} aria-pressed={sample === value} onClick={() => setSample(value)}>{label}</button>)}</div>}
    <div className="rx-actions">
      {!preview && approved && id > 0 && q.get("quick") !== "1" && <a className="rx-primary" href={href("QR_Scan", { settlementId:id, mode:"issue", returnTo:"settlement" })}>거래 QR 인증으로 계속</a>}
      {!preview && approved && <p>결제 승인과 QR 인증 완료는 별도로 확인합니다.</p>}
      {!preview && <button disabled={busy || !paymentId} onClick={() => retry(n => n + 1)}>승인 여부 다시 확인</button>}
      <a className="rx-primary" href={href(preview ? "Payment_Preview" : q.get("quick") === "1" ? "Payment_Quick" : "Payment_Checkout", preview ? {} : { settlementId: id })}>{approved ? "결제 내용 보기" : "결제 확인으로 돌아가기"}</a>
      {!preview && <a href={href("Settlement", id > 0 ? { settlementId: id } : {})}>정산으로 돌아가기</a>}
    </div>
  </Page>;
}


export function PaymentQuick() {
  const loggedIn = !!token();
  const config = useData(loggedIn ? "/api/payments/portone/config" : null);
  const action = useAction();
  const key = `nf-portone-quick-${uid()}`;
  const [lastId, setLastId] = useState(() => localStorage.getItem(key) || "");
  const [confirmed, setConfirmed] = useState(false);
  async function openCheckout() {
    const prepared = await api("/api/payments/portone/quick-prepare", { method: "POST" });
    const request = prepared.request;
    localStorage.setItem(key, request.paymentId);
    setLastId(request.paymentId);
    const redirect = new URL(location.pathname, location.origin);
    redirect.searchParams.set("nfPaymentReturn", "1");
    redirect.searchParams.set("quick", "1");
    try {
      const response = await PortOne.requestPayment({ ...request, redirectUrl: redirect.toString() });
      go("Payment_Result", { quick: "1", paymentId: request.paymentId, code: response?.code, message: response?.message });
    } catch {
      go("Payment_Result", { quick: "1", paymentId: request.paymentId, message: "결제창 응답을 받지 못했습니다. 서버 조회 결과를 확인해 주세요." });
    }
  }
  return <Page title="포트원 빠른 테스트">
    <section className="rx-card">
      <h2>결제창 바로 열기</h2>
      <p>정산 생성·GPS·QR 없이 결제창과 승인 조회를 확인합니다.</p>
      <h2>1,000원 · 테스트 카드 결제</h2>
      <p className="rx-muted">테스트 주문만 생성하며 실제 정산에는 반영하지 않습니다.</p>
      {!loggedIn && <a className="rx-primary" href={href("Login", { next: "Payment_Quick" })}>로그인하고 테스트하기</a>}
      {loggedIn && <>
        <p>{config.loading ? "설정 확인 중…" : config.error ? "서버 연결을 확인해 주세요." : config.data?.enabled ? "포트원 설정 확인됨" : "서버 .env의 PORTONE_* 설정 후 API를 재시작해 주세요."}</p>
        <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /> 포트원 콘솔의 테스트 채널 키를 설정했습니다.</label>
        <p className="rx-muted">실서비스 채널이면 실제 결제가 발생할 수 있습니다.</p>
        <div className="rx-actions">
          <button className="rx-primary" disabled={action.busy || !config.data?.enabled || !confirmed} onClick={() => action.run(openCheckout)}>{action.busy ? "결제창 연결 중…" : "포트원 결제창 열기"}</button>
          {lastId && <a href={href("Payment_Result", { quick: "1", paymentId: lastId })}>마지막 결제 결과 확인</a>}
        </div>
      </>}
      <Feedback error={config.error} /><Feedback {...action} />
    </section>
    <a href={href("Payment_Preview")}>화면 미리보기로 돌아가기</a>
  </Page>;
}
