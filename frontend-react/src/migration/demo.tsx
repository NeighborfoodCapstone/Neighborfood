// 관리자 체험 모드 — 부스 체험자에게 더미 거래를 배정하고, 노트북에서 가상 참여자의 QR 을 발급한다.
import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { Page, Feedback, Load, Select, useAction, useData, api, send, href } from "./core";
import type { Row } from "./core";
import { AdminNav } from "./admin";

const TYPE_OPTIONS: [string, string][] = [
  ["random", "랜덤 (공동구매·나눔·교환 중)"],
  ["groupbuy", "공동구매"],
  ["share", "나눔"],
  ["exchange", "교환"],
];

const base = "/api/admin/demo";

function Chip({ on, children }: { on: boolean; children: string }) {
  return <span className={on ? "rx-chip rx-chip-on" : "rx-chip"}>{(on ? "✓ " : "· ") + children}</span>;
}

// 노트북 화면에 띄우는 QR: 체험자 폰이 스캔하면 상태가 '인증 완료'로 바뀐다.
function QrBox({ issued, onDone }: { issued: Row; onDone: () => void }) {
  const [image, setImage] = useState("");
  const [status, setStatus] = useState("ISSUED");
  const [now, setNow] = useState(Date.now());
  const s = issued.session;
  useEffect(() => {
    const url =
      location.origin +
      location.pathname +
      href("QR_Scan", { token: s.token, transactionId: s.transactionId, settlementId: s.settlementId });
    QRCode.toDataURL(url, { width: 360, margin: 3, errorCorrectionLevel: "M" }).then(setImage).catch(() => setImage(""));
    setStatus("ISSUED");
  }, [s.id]);
  useEffect(() => {
    if (status !== "ISSUED") return;
    const tick = setInterval(() => setNow(Date.now()), 1000);
    const poll = setInterval(async () => {
      try {
        const d = await api(`${base}/qr/${encodeURIComponent(s.id)}`);
        if (d.status !== "ISSUED") {
          setStatus(d.status);
          if (d.status === "VERIFIED") onDone();
        }
      } catch {
        /* 다음 주기에 재시도 */
      }
    }, 2000);
    return () => {
      clearInterval(tick);
      clearInterval(poll);
    };
  }, [s.id, status]);
  const left = Math.max(0, Math.ceil((new Date(s.expiresAt).getTime() - now) / 1000));
  const state = status === "ISSUED" && !left ? "EXPIRED" : status;
  return (
    <section className="rx-card rx-issued-qr" aria-live="polite" aria-label="가상 참여자 QR">
      <h3>{issued.neighbor}의 QR</h3>
      {state === "ISSUED" && image && <img src={image} alt="체험자 폰으로 스캔할 QR" width={300} height={300} />}
      {state === "ISSUED" && <p>체험자 폰의 'QR 스캔'으로 읽어 주세요. 남은 시간 {Math.floor(left / 60)}분 {left % 60}초</p>}
      {state === "VERIFIED" && <p role="status"><strong>✓ 체험자 폰에서 인증 완료!</strong></p>}
      {state === "EXPIRED" && <p role="status">유효 시간이 지났습니다. 다시 발급해 주세요.</p>}
      {state === "ISSUED" && (
        <details>
          <summary>카메라 스캔이 어려울 때: 토큰 직접 입력</summary>
          <input readOnly value={s.token} onFocus={(e) => e.currentTarget.select()} aria-label="QR 토큰" />
        </details>
      )}
    </section>
  );
}

function TradeCard({ t, reload }: { t: Row; reload: () => void }) {
  const a = useAction();
  const [issued, setIssued] = useState<Row | null>(null);
  return (
    <article className="rx-card" aria-label={t.title}>
      <h3>
        [{t.typeLabel}] {t.title}
      </h3>
      <p className="rx-muted">
        {t.place || "장소 미정"} · {t.appointmentAt ? new Date(t.appointmentAt).toLocaleString("ko-KR") : "일시 미정(체험자가 정함)"}
      </p>
      <p>{t.next}</p>
      <Feedback {...a} />
      {t.participants.map((p: Row) => (
        <div key={p.userId} className="rx-actions" aria-label={p.nickname}>
          <strong>{p.nickname}</strong>
          <Chip on={p.gps}>위치(호천관)</Chip>
          <Chip on={p.qr}>QR</Chip>
          {t.type === "groupbuy" && <Chip on={p.paid}>납부</Chip>}
          {!(p.qr && (t.type !== "groupbuy" || p.paid)) && !p.qr && (
            <button
              className="rx-primary"
              disabled={a.busy}
              onClick={() =>
                a.run(async () => {
                  setIssued(await api(`${base}/trades/${t.postId}/participants/${p.userId}/qr`, { method: "POST" }));
                })
              }
            >
              위치 인증 + QR 발급
            </button>
          )}
          {t.type === "groupbuy" && p.qr && !p.paid && t.settlement && (
            <button
              disabled={a.busy}
              onClick={() =>
                a.run(async () => {
                  await send(`${base}/settlements/${t.settlement.id}/participants/${p.userId}/pay`, {});
                  setIssued(null);
                  reload();
                }, "납부 처리했습니다.")
              }
            >
              납부 처리
            </button>
          )}
        </div>
      ))}
      {issued && <QrBox issued={issued} onDone={reload} />}
    </article>
  );
}

export function AdminDemo() {
  const [draft, setDraft] = useState("");
  const [loginId, setLoginId] = useState("");
  const [kind, setKind] = useState("random");
  const [confirmReset, setConfirmReset] = useState(false);
  const a = useAction();
  const users = useData(`${base}/users?` + new URLSearchParams({ q: draft }));
  const trades = useData(loginId ? `${base}/trades?` + new URLSearchParams({ loginId }) : null);
  useEffect(() => {
    if (!loginId) return;
    const timer = setInterval(() => {
      if (!document.hidden) trades.reload();
    }, 4000);
    return () => clearInterval(timer);
  }, [loginId]);
  const spot = trades.data?.spot;
  return (
    <Page title="체험 모드(부스)">
      <AdminNav />
      <section className="rx-card">
        <h2>1. 체험자 선택</h2>
        <label className="rx-field">
          체험자 로그인 ID 검색
          <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="아이디 또는 닉네임 (비우면 최근 가입자)" />
        </label>
        <Load state={users}>
          {(users.data?.items || []).map((u: Row) => (
            <button
              key={u.id}
              type="button"
              className={u.loginId === loginId ? "rx-primary" : ""}
              onClick={() => {
                setLoginId(u.loginId);
                setConfirmReset(false);
              }}
            >
              {u.loginId} ({u.nickname}){u.demoTrades ? ` · 체험 거래 ${u.demoTrades}` : ""}
            </button>
          ))}
          {users.data && !users.data.items.length && <p>일치하는 회원이 없습니다.</p>}
        </Load>
      </section>
      {loginId && (
        <>
          <section className="rx-card">
            <h2>2. {loginId}에게 더미 거래 배정</h2>
            <Select label="거래 유형" value={kind} onChange={setKind} options={TYPE_OPTIONS} />
            <Feedback {...a} />
            <div className="rx-actions">
              <button
                className="rx-primary"
                disabled={a.busy}
                onClick={() =>
                  a.run(async () => {
                    await send(`${base}/trades`, { loginId, type: kind });
                    trades.reload();
                    users.reload();
                  }, "더미 거래를 만들었습니다. 체험자 폰의 채팅 목록에서 확인하세요.")
                }
              >
                더미 거래 생성
              </button>
              <button
                disabled={a.busy}
                onClick={() => {
                  if (!confirmReset) return setConfirmReset(true);
                  setConfirmReset(false);
                  a.run(async () => {
                    await api(`${base}/trades?` + new URLSearchParams({ loginId }), { method: "DELETE" });
                    trades.reload();
                    users.reload();
                  }, "체험 데이터를 초기화했습니다.");
                }}
              >
                {confirmReset ? "정말 초기화 (한 번 더 클릭)" : "이 체험자 거래 초기화"}
              </button>
            </div>
            {spot && (
              <p className="rx-muted">
                만남 장소 고정: {spot.address} ({spot.lat}, {spot.lng}) ·{" "}
                <a href={`https://map.kakao.com/link/map/호천관,${spot.lat},${spot.lng}`} target="_blank" rel="noreferrer">
                  지도로 확인
                </a>
              </p>
            )}
          </section>
          <h2>3. 진행 상황 (4초마다 자동 갱신)</h2>
          <Load state={trades}>
            {trades.data && !trades.data.items.length && <p>체험 거래가 없습니다. 위에서 생성해 주세요.</p>}
            {(trades.data?.items || []).map((t: Row) => (
              <TradeCard key={t.postId} t={t} reload={trades.reload} />
            ))}
          </Load>
        </>
      )}
    </Page>
  );
}
