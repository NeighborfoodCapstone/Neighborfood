import { Autocomplete, memberSuggestions } from "./autocomplete";
import { useState } from "react";
import {
  Page,
  Form,
  Field,
  Select,
  Feedback,
  Load,
  Empty,
  useAction,
  useData,
  api,
  send,
  text,
  href,
  uid,
  status,
} from "./core";
import type { Row } from "./core";
export function AdminNav() {
  return (
    <nav className="rx-admin-nav" aria-label="관리자 메뉴">
      {[
        ["Admin_Dashboard", "대시보드"],
        ["Admin_Users", "회원"],
        ["Admin_Notices", "공지"],
        ["Admin_Chat_History", "채팅 기록"],
        ["Admin_Staff_Invite", "운영진"],
      ].map(([p, n]) => (
        <a key={p} href={href(p)}>
          {n}
        </a>
      ))}
    </nav>
  );
}
export function Dashboard() {
  const s = useData("/api/admin/dashboard"),
    r = useData("/api/admin/reports"),
    stats = useData("/api/admin/stats");
  return (
    <Page title="관리자 대시보드">
      <AdminNav />
      <Load state={s}>
        {s.data && (
          <dl className="rx-stats">
            {Object.entries({
              users: "회원",
              posts: "게시글",
              transactions: "거래",
              reportsPending: "대기 신고",
              todaySignups: "오늘 가입",
              ongoingTransactions: "진행 중 거래",
            }).map(([k, label]) => (
              <div key={k}>
                <dt>{label}</dt>
                <dd>{s.data[k]}</dd>
              </div>
            ))}
          </dl>
        )}
      </Load>
      <h2>최근 7일 신고</h2>
      <Load state={stats}>
        {stats.data && (
          <>
            <p>
              처리율 {stats.data.resolveRate}% · {stats.data.weekHandled}/
              {stats.data.weekTotal}건
            </p>
            <div className="rx-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>날짜</th>
                    <th>접수</th>
                    <th>처리</th>
                  </tr>
                </thead>
                <tbody>
                  {(stats.data.weekly || []).map((x: Row) => (
                    <tr key={x.day}>
                      <td>{x.day}</td>
                      <td>{x.received}</td>
                      <td>{x.handled}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h3>신고 사유</h3>
            {(stats.data.reasons || []).map((x: Row) => (
              <p key={x.reason}>
                {x.reason} · {x.count}건 ({x.percent}%)
              </p>
            ))}
          </>
        )}
      </Load>
      <h2>신고 목록</h2>
      <Load state={r}>
        <Empty items={r.data?.items || []} />
        {(r.data?.items || []).map((x: Row) => (
          <a
            key={x.id}
            className="rx-row"
            href={href("Admin_Report_Detail", { id: x.id })}
          >
            <div>
              <h3>{x.target_title || x.reason}</h3>
              <p>{x.reason}</p>
              <small>
                {x.reporter_nickname} · {status[x.status] || x.status}
              </small>
            </div>
          </a>
        ))}
      </Load>
    </Page>
  );
}
export function AdminUsers({ staff = false }: { staff?: boolean }) {
  const [draft, setDraft] = useState(""),
    [keyword, setKeyword] = useState(""),
    [filter, setFilter] = useState("");
  const s = useData(
      "/api/admin/users?" +
        new URLSearchParams({
          q: keyword,
          ...(filter ? { status: filter } : {}),
        }),
    ),
    a = useAction();
  return (
    <Page title={staff ? "운영진 관리" : "회원 관리"}>
      <AdminNav />
      <Form onSubmit={() => setKeyword(draft)}>
        <div className="rx-search">
          <Autocomplete
            label="회원 검색"
            value={draft}
            onChange={setDraft}
            onSelect={(item) => setKeyword(item.value)}
            load={memberSuggestions}
            placeholder="닉네임 또는 아이디"
          />
          <button className="rx-search-button">검색</button>
        </div>
      </Form>
      <Select
        label="상태"
        value={filter}
        onChange={setFilter}
        options={[
          ["", "전체"],
          ["active", "활동"],
          ["suspended", "정지"],
        ]}
      />
      <Feedback {...a} />
      <Load state={s}>
        <Empty items={s.data?.items || []} />
        <div className="rx-table-wrap">
          <table>
            <thead>
              <tr>
                <th>회원</th>
                <th>상태</th>
                <th>권한</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {(s.data?.items || []).map((u: Row) => (
                <tr key={u.id}>
                  <td>
                    {u.nickname}
                    <small>{u.login_id}</small>
                  </td>
                  <td>{status[u.status] || u.status}</td>
                  <td>{u.role === "admin" ? "관리자" : "회원"}</td>
                  <td>
                    {u.id !== uid() && (
                      <button
                        disabled={a.busy}
                        onClick={() =>
                          a.run(async () => {
                            const body = staff
                              ? { role: u.role === "admin" ? "user" : "admin" }
                              : {
                                  status:
                                    u.status === "suspended"
                                      ? "active"
                                      : "suspended",
                                };
                            if (
                              !confirm(
                                "이 회원의 " +
                                  (staff ? "권한" : "상태") +
                                  "을 변경할까요?",
                              )
                            )
                              return;
                            await send(
                              "/api/admin/users/" + u.id,
                              body,
                              "PATCH",
                            );
                            s.reload();
                          })
                        }
                      >
                        {staff
                          ? u.role === "admin"
                            ? "권한 해제"
                            : "관리자 지정"
                          : u.status === "suspended"
                            ? "정지 해제"
                            : "이용 정지"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Load>
    </Page>
  );
}
export function Notices() {
  const s = useData("/api/admin/notices"),
    a = useAction();
  return (
    <Page title="공지 관리">
      <AdminNav />
      <Form
        onSubmit={(f) =>
          a.run(async () => {
            await send("/api/admin/notices", {
              title: text(f, "title"),
              content: text(f, "content"),
            });
            s.reload();
          }, "공지가 등록되었습니다.")
        }
      >
        <Field label="제목" name="title" required />
        <label className="rx-field">
          내용
          <textarea name="content" required maxLength={4000} />
        </label>
        <button className="rx-primary" disabled={a.busy}>
          공지 등록
        </button>
        <Feedback {...a} />
      </Form>
      <Load state={s}>
        {(s.data?.items || []).map((n: Row) => (
          <article className="rx-card" key={n.id}>
            <h2>{n.title}</h2>
            <p className="rx-description">{n.content}</p>
            <small>{n.author_nickname}</small>
            <button
              disabled={a.busy}
              onClick={() =>
                a.run(async () => {
                  if (!confirm("공지를 삭제할까요?")) return;
                  await api("/api/admin/notices/" + n.id, { method: "DELETE" });
                  s.reload();
                })
              }
            >
              삭제
            </button>
          </article>
        ))}
      </Load>
    </Page>
  );
}
export function AdminReport({ q }: { q: URLSearchParams }) {
  const s = useData(q.get("id") ? "/api/admin/reports/" + q.get("id") : null),
    a = useAction();
  return (
    <Page title="신고 상세">
      <AdminNav />
      <Load state={s}>
        {s.data && (
          <>
            <dl>
              <dt>신고 사유</dt>
              <dd>{s.data.reason}</dd>
              <dt>대상</dt>
              <dd>{s.data.target_title || s.data.target_id}</dd>
              <dt>신고자</dt>
              <dd>{s.data.reporter_nickname}</dd>
              <dt>상태</dt>
              <dd>{status[s.data.status] || s.data.status}</dd>
            </dl>
            <a
              href={href(
                s.data.target_type === "post"
                  ? "Product_Detail"
                  : "Admin_Users",
                s.data.target_type === "post" ? { id: s.data.target_id } : {},
              )}
            >
              대상 확인
            </a>
            <Feedback {...a} />
            {s.data.status === "pending" && (
              <div className="rx-actions">
                {[
                  ["resolved", "처리 완료"],
                  ["dismissed", "반려"],
                ].map(([next, label]) => (
                  <button
                    key={next}
                    disabled={a.busy}
                    onClick={() =>
                      a.run(async () => {
                        if (!confirm(label + " 처리할까요?")) return;
                        await send(
                          "/api/admin/reports/" + q.get("id"),
                          { status: next },
                          "PATCH",
                        );
                        s.reload();
                      })
                    }
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </Load>
    </Page>
  );
}
export function AdminChats() {
  const s = useData("/api/admin/chats"),
    [id, setId] = useState(""),
    m = useData(id ? "/api/admin/chats/" + id + "/messages" : null);
  return (
    <Page title="채팅 기록">
      <AdminNav />
      <div className="rx-split">
        <Load state={s}>
          <div className="rx-list">
            {(s.data?.items || []).map((c: Row) => (
              <button
                className="rx-row"
                key={c.id}
                onClick={() => setId(String(c.id))}
              >
                {c.post_title} · {c.message_count}개
              </button>
            ))}
          </div>
        </Load>
        <Load state={m}>
          <div>
            {(m.data?.items || []).map((x: Row) => (
              <article className="rx-card" key={x.id}>
                <small>
                  {x.sender_nickname} · {x.created_at}
                </small>
                <p>{x.content}</p>
              </article>
            ))}
          </div>
        </Load>
      </div>
    </Page>
  );
}
