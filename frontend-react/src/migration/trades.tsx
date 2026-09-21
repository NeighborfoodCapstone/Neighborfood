import { PlaceField } from "./location";
import { useEffect, useState } from "react";
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
      <Load state={s}>
        <Empty items={s.data?.items || []} />
        <div className="rx-list">
          {(s.data?.items || []).map((c: Row) => (
            <a
              className="rx-row"
              href={href(c.kind === "group" ? "Group_Chat" : "Chat_Detail", {
                id: c.id,
              })}
              key={c.id}
            >
              <div>
                <h2>{c.partnerNickname}</h2>
                <p>{c.post_title}</p>
                <p>{c.last_message || "대화를 시작해 보세요."}</p>
              </div>
              {c.unread_count > 0 && (
                <span className="rx-badge">{c.unread_count}</span>
              )}
            </a>
          ))}
        </div>
      </Load>
    </Page>
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
  useEffect(() => {
    if (!id) return;
    const tick = setInterval(() => {
      if (!document.hidden) s.reload();
    }, 5000);
    return () => clearInterval(tick);
  }, [id]);
  return (
    <Page title={group ? "공동구매 채팅" : "채팅"}>
      {conversation && (
        <>
          <h2>{conversation.partnerNickname}</h2>
          <a
            className="rx-row"
            href={href(group ? "Group_Buy_Detail" : "Product_Detail", {
              id: conversation.post_id,
            })}
          >
            {post.data?.title || conversation.post_title}
          </a>
        </>
      )}
      <Load state={members}>
        {group && (
          <details>
            <summary>참여자</summary>
            {(members.data?.items || members.data?.members || []).map(
              (m: Row) => (
                <p key={m.user_id || m.id}>{m.nickname}</p>
              ),
            )}
          </details>
        )}
      </Load>
      <Load state={s}>
        <div className="rx-messages" aria-live="polite">
          {(s.data?.items || []).map((m: Row) => (
            <div
              key={m.id}
              className={"rx-message " + (m.sender_id === uid() ? "mine" : "")}
            >
              <small>{m.sender_nickname || ""}</small>
              <p>{m.content}</p>
              <small>
                {m.created_at
                  ? new Date(m.created_at).toLocaleString("ko-KR")
                  : ""}
              </small>
            </div>
          ))}
        </div>
      </Load>
      <Form
        onSubmit={() =>
          a.run(async () => {
            if (!draft.trim()) return;
            await send(path, { content: draft.trim() });
            setDraft("");
            s.reload();
          })
        }
      >
        <div className="rx-search">
          <input
            aria-label="메시지"
            value={draft}
            maxLength={1000}
            onChange={(e) => setDraft(e.target.value)}
            required
          />
          <button
            className="rx-primary"
            disabled={a.busy || !id || !draft.trim()}
          >
            전송
          </button>
        </div>
        <Feedback {...a} />
      </Form>
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
                ? ["confirmed", "canceled"]
                : t.status === "confirmed"
                  ? ["completed", "canceled"]
                  : []
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
          <a href={href("Local_Verify_Demo", { settlementId: d.id })}>
            GPS 인증
          </a>
          <a href={href("QR_Scan", { settlementId: d.id })}>QR 인증</a>
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
