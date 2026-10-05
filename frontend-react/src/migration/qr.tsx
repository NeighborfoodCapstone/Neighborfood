import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { Scanner } from "./Scanner";
import { Page, Form, Field, Feedback, useAction, useData, Load, api, send, uid, href } from "./core";
import type { Row } from "./core";
const labels: Record<string,string> = { ISSUED:"발급됨", VERIFIED:"인증 완료", EXPIRED:"만료됨" };
const purposes: Record<string,string> = { pickup_confirm:"픽업 확인", groupbuy_receive:"공동구매 수령", seller_check:"판매자 확인" };
const when = (v?:string) => v ? new Date(v).toLocaleString("ko-KR") : "—";
export function QR({ q }: { q: URLSearchParams }) {
  const a = useAction();
  const [scanStatus,setScanStatus] = useState<"idle"|"checking"|"success"|"error">("idle");
  const [mode,setMode] = useState(q.get("mode") === "issue" ? "issue" : q.get("mode") === "history" ? "history" : "scan");
  const [issued,setIssued] = useState<Row|null>(null);
  const [image,setImage] = useState("");
  const [raw,setRaw] = useState(q.get("token") || "");
  const [result,setResult] = useState<Row|null>(null);
  const [purpose,setPurpose] = useState("pickup_confirm");
  const [ttl,setTtl] = useState("300");
  const [localScans,setLocalScans] = useState<Row[]>([]);
  const [linkWarning,setLinkWarning] = useState("");
  const [now,setNow] = useState(Date.now());
  const history = useData("/api/qr/my-history?limit=50");
  const settlement=q.get("settlementId");
  const transaction = useData(settlement ? `/api/settlements/${encodeURIComponent(settlement)}` : null);
  const myShare = transaction.data?.settlement?.shares?.find((s:Row)=>s.userId===uid());
  const paymentFlow=q.get("returnTo")==="payment";
  const loc=q.get("locationSessionId") || sessionStorage.getItem("nf_location_session");
  const current=(history.data?.items || []).find((x:Row)=>x.id===issued?.id) || issued;
  const remaining=issued ? Math.max(0,Math.ceil((new Date(issued.expiresAt).getTime()-now)/1000)) : 0;
  const currentStatus=current?.status==="ISSUED" && !remaining ? "EXPIRED" : current?.status;
  useEffect(()=>{
    if (!issued || currentStatus!=="ISSUED") return;
    const timer=setInterval(()=>setNow(Date.now()),1000);
    const poll=setInterval(()=>{if(!document.hidden)history.reload();},3000);
    return ()=>{clearInterval(timer);clearInterval(poll);};
  },[issued?.id,currentStatus]);
  function verify(value:string) {
    if(a.busy) return;
    setResult(null);setScanStatus("checking");
    a.run(async()=>{
      let token=value.trim();
      try { const url=new URL(token); const params=new URLSearchParams(url.hash.split("?")[1]);token=params.get("token") || url.pathname.split("/verify/")[1] || token; } catch { /* token input */ }
      try {
        const d=await send("/api/qr/verify",{rawValue:token});
        setScanStatus("success");setResult(d);setLocalScans(xs=>[{id:d.session?.id,at:new Date().toISOString(),message:d.message,ok:true},...xs].slice(0,20));history.reload();
      } catch(e) {setScanStatus("error");setLocalScans(xs=>[{at:new Date().toISOString(),message:e instanceof Error?e.message:"인증 실패",ok:false},...xs].slice(0,20));throw e;}
    },"QR 인증이 완료되었습니다.");
  }
  async function issue() {
    setLinkWarning("");
    const d=await send("/api/qr/request",{subjectId:String(uid()),purpose,ttlSeconds:Number(ttl)});
    setIssued(d.session);setNow(Date.now());setImage("");history.reload();
    setImage(await QRCode.toDataURL(location.origin+location.pathname+href("QR_Scan",{token:d.session.token}),{width:400,margin:3,errorCorrectionLevel:"M"}));
    if(loc)try {await send(`/api/location-verify/${encodeURIComponent(loc)}/qr-issued`,{qrSessionId:d.session.id});}catch {setLinkWarning("QR은 발급됐지만 위치 인증 기록 연결에 실패했습니다. GPS 인증 상태를 확인해 주세요.");}
  }
  return <Page title="QR 거래 인증">
    {settlement && <p className="rx-muted">정산 #{settlement} · 내 QR을 발급해 거래 상대에게 보여 주세요. 상대방이 스캔하면 인증 상태를 확인할 수 있습니다.</p>}
    {myShare && <section className="rx-card"><strong>공동구매 정산 #{settlement}</strong><p>{myShare.nickname} · {Number(myShare.amount).toLocaleString("ko-KR")}원</p><p>거래 QR 인증: {myShare.qualityAgreed ? "완료" : "대기"}</p></section>}
    <Feedback error={transaction.error} />
    <div className="rx-qr-tabs" role="tablist" aria-label="QR 기능">
      {[["scan","QR 스캔"],["issue","내 QR 발급"],["history","인증 내역"]].map(([key,label])=><button key={key} role="tab" id={`qr-tab-${key}`} aria-selected={mode===key} aria-controls="qr-panel" onClick={()=>{setMode(key);history.reload();}}>{label}</button>)}
    </div>
    <Feedback {...a}/>
    <div id="qr-panel" role="tabpanel" aria-labelledby={`qr-tab-${mode}`}>
    {mode==="scan" && <>
      <Scanner kind="qr" onRead={verify} disabled={a.busy} status={scanStatus} onReset={()=>{setScanStatus("idle");setResult(null);}}/>
      <p className="rx-muted">상대방이 발급한 QR을 중앙 정사각형에 맞춰 주세요.</p>
      <details><summary>QR 내용 직접 입력</summary><Form onSubmit={()=>verify(raw)}><Field label="QR 내용 또는 인증 토큰" value={raw} onChange={setRaw} required/><button className="rx-primary" disabled={a.busy}>인증 확인</button></Form></details>
      {q.get("token") && <button disabled={a.busy} onClick={()=>verify(q.get("token")!)}>전달받은 QR 인증</button>}
      {result && <section className="rx-card" role="status"><h3>{result.message}</h3><p>인증 번호: {result.session?.id}</p><p>{when(result.session?.usedAt)}</p></section>}
    </>}
    {mode==="issue" && <>
      <section className="rx-card">
        <h2>내 거래 QR</h2><p>발급 대상: 내 계정 #{uid()}</p>
        <Form onSubmit={()=>a.run(issue)}>
          <label className="rx-field">발급 목적<select value={purpose} onChange={e=>setPurpose(e.target.value)}>{Object.entries(purposes).map(([v,label])=><option key={v} value={v}>{label}</option>)}</select></label>
          <label className="rx-field">유효 시간<select value={ttl} onChange={e=>setTtl(e.target.value)}>{[["60","1분"],["180","3분"],["300","5분"],["900","15분"]].map(([v,label])=><option key={v} value={v}>{label}</option>)}</select></label>
          <button className="rx-primary" disabled={a.busy}>{issued?"새 QR 발급":"QR 발급"}</button>
        </Form>
      </section>
      {!issued && <div className="rx-qr-placeholder" role="status">{a.busy ? "QR 발급 중…" : "발급한 QR이 여기에 표시됩니다"}</div>}
      {issued && <section className="rx-card rx-issued-qr" aria-live="polite">
        <div className="rx-qr-placeholder">{a.busy ? <span role="status">QR 발급 중…</span> : image && currentStatus==="ISSUED" ? <img src={image} alt="상대방에게 보여줄 거래 인증 QR"/> : <span>{labels[currentStatus] || "QR 준비 중…"}</span>}</div>
        <h3>{labels[currentStatus] || currentStatus}</h3>
        {currentStatus==="ISSUED" && <p>남은 시간 {Math.floor(remaining/60)}분 {remaining%60}초</p>}
        {currentStatus==="EXPIRED" && <p>유효 시간이 지났습니다. 새 QR을 발급해 주세요.</p>}
        <p>발급: {when(issued.issuedAt)}</p><p>만료: {when(issued.expiresAt)}</p>
        {current?.usedAt && <p>인증: {when(current.usedAt)}</p>}
        <button onClick={()=>history.reload()} disabled={history.loading}>인증 상태 새로고침</button>
        <Feedback error={history.error}/>
      </section>}
      <Feedback error={linkWarning}/>
    </>}
    {mode==="history" && <>
      <h2>내 QR 발급·인증 내역</h2><button onClick={()=>history.reload()} disabled={history.loading}>새로고침</button>
      <Load state={history}>
        {!history.data?.items?.length && <p>발급한 QR이 없습니다.</p>}
        {(history.data?.items || []).map((item:Row)=><article className="rx-card" key={item.id}><h3>{labels[item.status] || item.status} · {purposes[item.purpose] || item.purpose}</h3><p>발급: {when(item.issuedAt)}</p><p>만료: {when(item.expiresAt)}</p><p>인증: {when(item.usedAt)}</p><small>{item.id}</small></article>)}
      </Load>
      <h2>이 화면에서 스캔한 결과</h2><button disabled={!localScans.length} onClick={()=>setLocalScans([])}>이번 스캔 결과 지우기</button><p className="rx-muted">아래 스캔 결과는 화면을 나가면 초기화됩니다. 위 발급·인증 내역은 서버 기록입니다.</p>
      {localScans.length===0 && <p>이번 화면에서 스캔한 기록이 없습니다.</p>}
      {localScans.map((item,i)=><article className="rx-card" key={i}><strong>{item.ok?"인증 성공":"인증 실패"}</strong><p>{item.message}</p><small>{when(item.at)}</small></article>)}
    </>}
    </div>
    {settlement && <div className="rx-actions"><button className="rx-primary" disabled={a.busy} onClick={()=>a.run(async()=>{
      await api(`/api/settlements/${settlement}/shares/me/qr-done`,{method:"POST"});
      location.hash=href(paymentFlow?"Payment_Checkout":"Settlement",{settlementId:settlement});
    })}>{paymentFlow?"인증 확인 후 결제로 계속":"정산에 인증 결과 반영"}</button><a href={href(paymentFlow?"Payment_Checkout":"Settlement",{settlementId:settlement})}>돌아가기</a></div>}
  </Page>;
}
