import { PortOneTest } from "./portone";
import { PlaceField } from "./location";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { LoadingState } from "./loading";
import {
  Page,
  Form,
  Field,
  Select,
  Feedback,
  Load,
  Empty,
  PostList,
  useData,
  useAction,
  send,
  api,
  href,
  text,
  uid,
  status,
  money,
} from "./core";
import type { Row } from "./core";
export function Chats() {
  const s = useData("/api/chats");
  return (
    <Page title="채팅">
      <p className="rx-muted">거래와 공동구매에 관한 대화를 확인하세요.</p>
      <Load state={s}>
        {!s.data?.items?.length && <p className="rx-empty">아직 대화가 없습니다. 게시글에서 거래를 시작해 보세요.</p>}
        <div className="rx-list rx-chat-list">
          {(s.data?.items || []).map((c: Row) => (
            <a
              className="rx-row rx-chat-row"
              href={href(c.kind === "group" ? "Group_Chat" : "Chat_Detail", {
                id: c.id,
              })}
              key={c.id}
            >
              <div className="rx-chat-row-content">
                <div className="rx-chat-row-heading">
                  <h2>{c.kind === "group" ? c.post_title || "공동구매 채팅" : c.partnerNickname || "이웃"}</h2>
                  {c.last_message_at && <time dateTime={c.last_message_at}>{when(c.last_message_at)}</time>}
                </div>
                <p className="rx-chat-context">
                  {c.kind === "group"
                    ? `공동구매${c.member_count != null ? ` · ${c.member_count}명` : ""}`
                    : c.post_title}
                </p>
                <p className="rx-chat-preview">{c.last_message || "대화를 시작해 보세요."}</p>
              </div>
              {c.unread_count > 0 && (
                <span className="rx-badge" aria-label={`읽지 않은 메시지 ${c.unread_count}개`}>{c.unread_count}</span>
              )}
            </a>
          ))}
        </div>
      </Load>
    </Page>
  );
}
// 공동구매 채팅 상단의 거래 진행 바: 약속 → 정산 → GPS → QR 진입점 (정적 Group_Chat.html 액션 바 복원)
function when(value?: string) {
  if (!value) return "일시 미정";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("ko-KR");
}
function TradeBar({
  post,
  postId,
  onSaved,
}: {
  post: Row;
  postId: string | number;
  onSaved: () => void;
}) {
  const a = useAction(),
    stl = useData("/api/settlements/post/" + postId),
    [open, setOpen] = useState(false),
    isHost = String(post.author_id) === String(uid()),
    d = stl.data?.settlement,
    active = d && d.status !== "canceled",
    place = active ? d.appointmentPlace : post.appointment_place,
    at = active ? d.appointmentAt : post.appointment_at,
    lat = active ? d.appointmentLat : post.appointment_lat,
    lng = active ? d.appointmentLng : post.appointment_lng,
    hasAppointment = !!(place || at),
    shares: Row[] = active ? d.shares || [] : [],
    me = shares.find((x) => x.userId === uid()),
    gps = shares.filter((x) => x.gpsVerified).length,
    qr = shares.filter((x) => x.qualityAgreed).length,
    waitingQr = shares.filter((x) => x.gpsVerified && !x.qualityAgreed).length;
  return (
    <section className="rx-card" aria-label="거래 진행">
      <h3>거래 진행</h3>
      <p>
        {hasAppointment
          ? "약속: " + (place || "장소 미정") + " · " + when(at)
          : "약속이 아직 정해지지 않았습니다."}
      </p>
      {active && (
        <p className="rx-muted">
          정산 {status[d.status]} · 납부 {d.paidCount}/{d.participantCount} ·
          GPS {gps}/{shares.length} · QR {qr}/{shares.length}
        </p>
      )}
      <Feedback {...a} />
      <div className="rx-actions">
        {isHost && (!active || d.status === "pending") && (
          <button type="button" onClick={() => setOpen(!open)}>
            {hasAppointment ? "약속 변경" : "약속 정하기"}
          </button>
        )}
        {isHost && !active && hasAppointment && (
          <a className="rx-primary" href={href("Settlement", { postId })}>
            정산 시작하기
          </a>
        )}
        {isHost && !active && !hasAppointment && (
          <span className="rx-muted">약속을 정하면 정산을 시작할 수 있습니다.</span>
        )}
        {active && (
          <a href={href("Settlement", { settlementId: d.id })}>정산 상세</a>
        )}
        {me && d.status === "pending" && (
          <>
            <a
              href={href("Local_Verify_Demo", {
                settlementId: d.id,
                returnTo: "payment",
              })}
            >
              1단계 GPS 인증{me.gpsVerified ? " ✓" : ""}
            </a>
            {me.gpsVerified ? (
              <a
                href={href("QR_Scan", {
                  settlementId: d.id,
                  mode: "issue",
                  returnTo: "payment",
                })}
              >
                2단계 QR 인증{me.qualityAgreed ? " ✓" : ""}
              </a>
            ) : (
              <span className="rx-muted">GPS 인증 후 QR 인증</span>
            )}
          </>
        )}
        {isHost && active && d.status === "pending" && waitingQr > 0 && (
          <a href={href("QR_Scan", { settlementId: d.id, mode: "scan" })}>
            참여자 QR 스캔 ({waitingQr})
          </a>
        )}
      </div>
      {open && (
        <Form
          onSubmit={(f) =>
            a.run(async () => {
              const raw = text(f, "at");
              await send("/posts/" + postId + "/appointment", {
                place: text(f, "place"),
                appointment_at: raw ? new Date(raw).toISOString() : null,
                lat: text(f, "lat") ? Number(text(f, "lat")) : null,
                lng: text(f, "lng") ? Number(text(f, "lng")) : null,
              });
              setOpen(false);
              onSaved();
              stl.reload();
            })
          }
        >
          <PlaceField
            addressName="place"
            initial={{ address: place || "", lat, lng }}
          />
          <Field label="일시" name="at" type="datetime-local" required />
          <button className="rx-primary" disabled={a.busy}>
            약속 저장
          </button>
        </Form>
      )}
    </section>
  );
}
export function Chat({
  q,
  group = false,
}: {
  q: URLSearchParams;
  group?: boolean;
}) {
  const id = q.get("id"),
    path = "/api/chats/" + (group ? "group/" : "") + id + "/messages";
  const chats = useData("/api/chats");
  const conversation = (chats.data?.items || []).find(
    (x: Row) => String(x.id) === id,
  );
  const post = useData(conversation ? "/posts/" + conversation.post_id : null);
  const s = useData(id ? path : null),
    members = useData(
      group && id ? "/api/chats/group/" + id + "/members" : null,
    ),
    a = useAction(),
    [draft, setDraft] = useState("");
  const messageArea = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLFormElement>(null);
  const initialized = useRef(false);
  const followLatest = useRef(true);
  const followOwnSend = useRef(false);
  const previousLastId = useRef<unknown>(null);
  const [newMessages, setNewMessages] = useState(false);
  const [composerHeight, setComposerHeight] = useState(0);
  useLayoutEffect(() => {
    const element = composer.current;
    if (!element) return;
    const measure = () => setComposerHeight(element.offsetHeight);
    measure();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", measure);
      return () => window.removeEventListener("resize", measure);
    }
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useLayoutEffect(() => {
    if (initialized.current && followLatest.current && messageArea.current)
      messageArea.current.scrollTop = messageArea.current.scrollHeight;
  }, [composerHeight]);
  const messages: Row[] = s.data?.items || [];
  const lastId = messages.length ? messages[messages.length - 1].id : null;
  const reloadMessages = s.reload;
  useLayoutEffect(() => {
    const area = messageArea.current;
    if (!s.data || !area) return;
    if (!initialized.current || (lastId !== previousLastId.current && (followLatest.current || followOwnSend.current))) {
      area.scrollTop = area.scrollHeight;
      followLatest.current = true;
      followOwnSend.current = false;
      setNewMessages(false);
    } else if (lastId !== null && lastId !== previousLastId.current) {
      setNewMessages(true);
    }
    initialized.current = true;
    previousLastId.current = lastId;
  }, [s.data, lastId]);
  useEffect(() => {
    if (!id) return;
    const tick = setInterval(() => {
      if (!document.hidden) reloadMessages();
    }, 5000);
    return () => clearInterval(tick);
  }, [id, reloadMessages]);
  return (
    <Page title={group ? "공동구매 채팅" : "채팅"}>
      {chats.error && !s.error && <div><Feedback error={chats.error} /><button type="button" onClick={chats.reload}>대화 정보 다시 불러오기</button></div>}
      {conversation && (
        <div className="rx-chat-conversation">
          <h2>{group ? "공동구매 대화" : conversation.partnerNickname || "이웃"}</h2>
          <a href={href(group ? "Group_Buy_Detail" : "Product_Detail", {
            id: conversation.post_id,
          })}>
            {post.data?.title || conversation.post_title} <span aria-hidden="true">›</span>
          </a>
        </div>
      )}
      {group && <Load state={members}>
        <details>
          <summary>참여자{members.data?.members ? ` ${members.data.members.length}명` : ""}</summary>
          {(members.data?.items || members.data?.members || []).map(
            (m: Row) => <p key={m.user_id || m.id}>{m.nickname}</p>,
          )}
        </details>
      </Load>}
      {group && conversation && post.error && <div><Feedback error={post.error} /><button type="button" onClick={post.reload}>거래 정보 다시 불러오기</button></div>}
      {group && conversation && post.data && (
        <TradeBar
          post={post.data}
          postId={conversation.post_id}
          onSaved={post.reload}
        />
      )}
      {!id && <p className="rx-empty">채팅 목록에서 대화방을 선택해 주세요. <a href={href("Chat_List")}>채팅 목록</a></p>}
      {s.loading && !s.data && <LoadingState label="대화를 불러오는 중…" />}
      {s.error && <div><Feedback error={s.error} /><button type="button" onClick={() => {
        s.reload();
        if (chats.error) chats.reload();
      }}>대화 다시 불러오기</button></div>}
      {s.data && <>
        <div className="rx-messages" ref={messageArea} role="log" aria-label="대화 내용" tabIndex={0}
          style={{ paddingBottom: composerHeight ? composerHeight + 24 : 84 }}
          onScroll={(event) => {
            const area = event.currentTarget;
            followLatest.current = area.scrollHeight - area.scrollTop - area.clientHeight < 80;
            if (followLatest.current) setNewMessages(false);
          }}>
          {!messages.length && <p className="rx-chat-empty">아직 메시지가 없습니다. 첫 메시지를 보내 보세요.</p>}
          {messages.map((m: Row) => (
            <div key={m.id} className={"rx-message " + (m.sender_id === uid() ? "mine" : "")}>
              <small>{m.is_system ? "안내" : m.sender_id === uid() ? "나" : m.sender_nickname || conversation?.partnerNickname || "상대방"}</small>
              <p>{m.content}</p>
              {m.created_at && <time dateTime={m.created_at}>{when(m.created_at)}</time>}
            </div>
          ))}
        </div>
        {newMessages && <button type="button" className="rx-chat-new" onClick={() => {
          const area = messageArea.current;
          if (area) area.scrollTop = area.scrollHeight;
          followLatest.current = true;
          setNewMessages(false);
        }}>새 메시지 보기</button>}
      </>}
      <form ref={composer} className="rx-form rx-chat-composer" onSubmit={(event) => {
        event.preventDefault();
        void a.run(async () => {
          if (!draft.trim()) return;
          await send(path, { content: draft.trim() });
          setDraft("");
          followOwnSend.current = true;
          s.reload();
        });
      }}>
        <div className="rx-chat-input">
          <textarea aria-label="메시지" value={draft} maxLength={1000} rows={2}
            onChange={(event) => setDraft(event.target.value)}
            disabled={a.busy || !id || !s.data} placeholder="메시지를 입력하세요" required />
          <button className="rx-primary" disabled={a.busy || !id || !s.data || !draft.trim()}>
            전송
          </button>
        </div>
        <Feedback {...a} />
      </form>
    </Page>
  );
}
export function Activity({ history = false }: { history?: boolean }) {
  const [filter, setFilter] = useState("");
  const tx = useData("/api/transactions" + (filter ? "?status=" + filter : "")),
    p = useData(history ? null : "/posts?limit=100"),
    reports = useData(history ? null : "/api/reports/my"),
    a = useAction();
  return (
    <Page title={history ? "거래 내역" : "내 활동"}>
      {!history && (
        <>
          <div className="rx-actions">
            <a href={href("Chat_List")}>채팅</a>
            <a href={href("Settlement")}>정산</a>
            <a href={href("Wishlist")}>찜 목록</a>
          </div>
          <h2>내 게시글</h2>
          <Load state={p}>
            <PostList
              items={(p.data?.items || []).filter(
                (x: Row) => String(x.author_id) === String(uid()),
              )}
            />
          </Load>
        </>
      )}
      <h2>거래</h2>
      <button type="button" disabled={tx.loading} onClick={() => tx.reload()}>거래 상태 새로고침</button>
      <Select
        label="상태"
        value={filter}
        onChange={setFilter}
        options={[
          ["", "전체"],
          ["pending", "대기"],
          ["confirmed", "확정"],
          ["completed", "완료"],
          ["canceled", "취소"],
        ]}
      />
      <Feedback {...a} />
      <Load state={tx}>
        <Empty items={tx.data?.items || []} />
        {(tx.data?.items || []).map((t: Row) => (
          <article className="rx-card" key={t.id}>
            <a href={href("Product_Detail", { id: t.postId })}>
              <h3>{t.postTitle}</h3>
            </a>
            <p>
              {t.partner} · {status[t.status]}
            </p>
            <p>{t.appointmentAt}</p>
            <div className="rx-actions">
              {(t.status === "pending"
                ? t.myRole === "provider" ? ["confirmed", "canceled"] : ["canceled"]
                : t.status === "confirmed" ? ["canceled"] : []
              ).map((next) => (
                <button
                  key={next}
                  disabled={a.busy}
                  onClick={() =>
                    a.run(async () => {
                      if (!confirm("거래를 " + status[next] + " 처리할까요?"))
                        return;
                      await send(
                        "/api/transactions/" + t.id,
                        { status: next },
                        "PATCH",
                      );
                      tx.reload();
                    })
                  }
                >
                  {status[next]}
                </button>
              ))}
            </div>
            {t.status === "confirmed" && <>
              <p>약속 장소: {t.appointmentPlace || "제공자가 설정해야 합니다"}</p>
              <p>약속 일시: {t.appointmentAt ? when(t.appointmentAt) : "제공자가 설정해야 합니다"}</p>
              {t.myRole === "provider" ? <>
                <details>
                  <summary>약속 장소·일시 설정</summary>
                  <Form onSubmit={(f) => a.run(async () => {
                    const raw = text(f, "at");
                    await send("/posts/" + t.postId + "/appointment", {
                      place: text(f, "place"),
                      appointment_at: raw ? new Date(raw).toISOString() : null,
                      lat: text(f, "lat") ? Number(text(f, "lat")) : null,
                      lng: text(f, "lng") ? Number(text(f, "lng")) : null,
                    });
                    tx.reload();
                  }, "약속 장소가 저장되었습니다.")}>
                    <PlaceField addressName="place" initial={{ address: t.appointmentPlace || "", lat: t.targetLat, lng: t.targetLng }} />
                    <Field label="일시" name="at" type="datetime-local" required />
                    <button disabled={a.busy}>약속 저장</button>
                  </Form>
                </details>
                <a href={href("QR_Scan", { transactionId: t.id, mode: "scan" })}>신청자의 QR 스캔</a>
              </> : <div className="rx-actions">
                <a href={href("Local_Verify_Demo", { transactionId: t.id })}>GPS 위치 인증</a>
                <a href={href("QR_Scan", { transactionId: t.id, mode: "issue" })}>거래 QR 발급</a>
              </div>}
              {t.gpsVerifiedAt && <p className="rx-muted">최근 위치 인증: {when(t.gpsVerifiedAt)} (QR 인증 전 5분 이내 재확인)</p>}
            </>}
            {t.status === "completed" && <Rating id={t.id} />}
          </article>
        ))}
      </Load>
      {!history && (
        <>
          <h2>내 신고</h2>
          <Load state={reports}>
            <Empty items={reports.data?.items || []} />
            {(reports.data?.items || []).map((r: Row) => (
              <article className="rx-card" key={r.id}>
                <p>{r.reason}</p>
                <small>{status[r.status] || r.status}</small>
                {r.status === "pending" && (
                  <button
                    disabled={a.busy}
                    onClick={() =>
                      a.run(async () => {
                        await api("/api/reports/" + r.id, { method: "DELETE" });
                        reports.reload();
                      })
                    }
                  >
                    신고 취소
                  </button>
                )}
              </article>
            ))}
          </Load>
        </>
      )}
    </Page>
  );
}
function Rating({ id }: { id: number }) {
  const s = useData("/api/ratings/transaction/" + id + "/me"),
    a = useAction(),
    [score, setScore] = useState("1");
  const r = s.data?.rated ? { id: s.data.ratingId } : null;
  return (
    <details>
      <summary>거래 평가</summary>
      <Load state={s}>
        <Form
          onSubmit={(f) =>
            a.run(async () => {
              await send(
                "/api/ratings" + (r ? "/" + r.id : ""),
                {
                  transaction_id: id,
                  score: Number(score),
                  comment: text(f, "comment"),
                },
                r ? "PATCH" : "POST",
              );
              s.reload();
            }, "평가가 저장되었습니다.")
          }
        >
          <Select
            label="평가"
            value={score}
            onChange={setScore}
            options={[
              ["1", "좋았어요"],
              ["-1", "아쉬웠어요"],
            ]}
          />
          <Field label="평가 내용" name="comment" />
          <Feedback {...a} />
          <button disabled={a.busy}>{r ? "평가 수정" : "평가 등록"}</button>
          {r && (
            <button
              type="button"
              disabled={a.busy}
              onClick={() =>
                a.run(async () => {
                  await api("/api/ratings/" + r.id, { method: "DELETE" });
                  s.reload();
                })
              }
            >
              평가 삭제
            </button>
          )}
        </Form>
      </Load>
    </details>
  );
}
export function Settlement({ q }: { q: URLSearchParams }) {
  const id = q.get("settlementId") || q.get("id"),
    post = q.get("postId");
  const s = useData(
      id
        ? "/api/settlements/" + id
        : post
          ? "/api/settlements/post/" + post
          : "/api/settlements/my",
    ),
    a = useAction();
  const d = s.data?.settlement;
  return (
    <Page title="정산">
      <Feedback {...a} />
      {!id && !post && (
        <Load state={s}>
          <Empty items={s.data?.items || []} />
          {(s.data?.items || []).map((x: Row) => (
            <a
              className="rx-row"
              key={x.id}
              href={href("Settlement", { settlementId: x.id })}
            >
              정산 #{x.id} · {money(x.totalAmount)} · {status[x.status]}
            </a>
          ))}
        </Load>
      )}
      {post && !d && !s.loading && (
        <>
          <Feedback error={s.error} />
          <Form
            onSubmit={(f) =>
              a.run(async () => {
                await send("/api/settlements", {
                  post_id: Number(post),
                  total_amount: Number(text(f, "amount")),
                  account_info: text(f, "account"),
                });
                s.reload();
              })
            }
          >
            <Field
              label="총 정산 금액"
              name="amount"
              type="number"
              min={1}
              required
            />
            <Field label="입금 계좌" name="account" required />
            <button className="rx-primary" disabled={a.busy}>
              정산 시작
            </button>
          </Form>
        </>
      )}
      {(id || d) && (
        <Load state={s}>
          {d && <SettlementDetail d={d} reload={s.reload} />}
        </Load>
      )}
    </Page>
  );
}
function SettlementDetail({ d, reload }: { d: Row; reload: () => void }) {
  const a = useAction(),
    own = d.requesterId === uid(),
    me = (d.shares || []).find((s: Row) => s.userId === uid());
  return (
    <>
      <h2>{money(d.totalAmount)}</h2>
      <p>
        {status[d.status]} · {d.paidCount}/{d.participantCount}명 납부 표시
      </p>
      <p>{d.accountInfo}</p>
      <p>
        {d.appointmentPlace} · {d.appointmentAt}
      </p>
      <p className="rx-muted">
        납부 표시는 사용자의 확인 기록이며 결제 대행사의 결제 승인이 아닙니다.
      </p>
      <Feedback {...a} />
      {own && d.status === "pending" && (
        <details>
          <summary>약속 장소·일시 설정</summary>
          <Form
            onSubmit={(f) =>
              a.run(async () => {
                await send("/api/settlements/" + d.id + "/appointment", {
                  place: text(f, "place"),
                  appointment_at: text(f, "at"),
                  lat: text(f, "lat") ? Number(text(f, "lat")) : null,
                  lng: text(f, "lng") ? Number(text(f, "lng")) : null,
                });
                reload();
              })
            }
          >
            <PlaceField
              addressName="place"
              initial={{
                address: d.appointmentPlace,
                lat: d.appointmentLat,
                lng: d.appointmentLng,
              }}
            />
            <Field label="일시" name="at" type="datetime-local" required />

            <button disabled={a.busy}>약속 저장</button>
          </Form>
        </details>
      )}
      <div className="rx-list">
        {d.shares.map((s: Row) => (
          <article className="rx-card" key={s.userId}>
            <h3>{s.nickname}</h3>
            <p>
              {money(s.amount)} · {status[s.status]}
            </p>
            <small>
              GPS {s.gpsVerified ? "완료" : "대기"} · QR{" "}
              {s.qualityAgreed ? "완료" : "대기"}
            </small>
            {own && d.status === "pending" && (
              <button
                disabled={a.busy}
                onClick={() =>
                  a.run(async () => {
                    if (
                      !confirm(
                        s.status === "noshow"
                          ? "불참 처리를 취소할까요?"
                          : "불참 처리할까요?",
                      )
                    )
                      return;
                    await api(
                      "/api/settlements/" +
                        d.id +
                        "/shares/" +
                        s.userId +
                        "/noshow",
                      { method: s.status === "noshow" ? "DELETE" : "POST" },
                    );
                    reload();
                  })
                }
              >
                {s.status === "noshow" ? "불참 취소" : "불참 처리"}
              </button>
            )}
          </article>
        ))}
      </div>
      {me && d.status === "pending" && (
        <div className="rx-actions">
          <a href={href("Local_Verify_Demo", { settlementId: d.id, returnTo: "payment" })}>
            GPS 인증
          </a>
          {me.gpsVerified
            ? <a href={href("QR_Scan", { settlementId: d.id, mode: "issue", returnTo: "payment" })}>QR 인증</a>
            : <span className="rx-muted">GPS 인증 후 QR 인증</span>}
          <button
            className="rx-primary"
            disabled={a.busy || !me.payable}
            onClick={() =>
              a.run(async () => {
                await api("/api/settlements/" + d.id + "/shares/me/pay", {
                  method: "POST",
                });
                reload();
              })
            }
          >
            납부 표시
          </button>
        </div>
      )}
      {me && <PortOneTest key={d.id} settlementId={d.id} payable={d.status === "pending" && !!me.payable} />}
      {own && d.status === "pending" && (
        <div className="rx-actions">
          <button
            disabled={a.busy || !d.canComplete}
            onClick={() =>
              a.run(async () => {
                await api("/api/settlements/" + d.id + "/complete", {
                  method: "POST",
                });
                reload();
              })
            }
          >
            정산 완료
          </button>
          <button
            disabled={a.busy}
            onClick={() =>
              a.run(async () => {
                if (!confirm("정산을 취소할까요?")) return;
                await api("/api/settlements/" + d.id + "/cancel", {
                  method: "POST",
                });
                reload();
              })
            }
          >
            정산 취소
          </button>
        </div>
      )}
    </>
  );
}
