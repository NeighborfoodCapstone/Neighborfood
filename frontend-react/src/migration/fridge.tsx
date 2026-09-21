import { useState } from "react";
import {
  Page,
  Form,
  Select,
  Feedback,
  useAction,
  useData,
  Load,
  send,
  api,
  href,
  text,
  Empty,
} from "./core";
import type { Row } from "./core";
export function Fridge() {
  const [filter, setFilter] = useState("ACTIVE"),
    [edit, setEdit] = useState<Row | null>(null),
    [adding, setAdding] = useState(false);
  const s = useData("/api/fridge/items?status=" + filter + "&limit=200"),
    a = useAction();
  return (
    <Page
      title="내 냉장고"
      actions={
        <button
          onClick={() => {
            setAdding(true);
            setEdit(null);
          }}
        >
          식재료 추가
        </button>
      }
    >
      <div className="rx-actions">
        <a href={href("Receipt_Verify")}>영수증으로 등록</a>
        <Select
          label="상태"
          value={filter}
          onChange={setFilter}
          options={[
            ["ACTIVE", "보관 중"],
            ["CONSUMED", "사용 완료"],
            ["EXPIRED", "기한 만료"],
            ["DISCARDED", "폐기"],
          ]}
        />
      </div>
      <Feedback {...a} />
      <Load state={s}>
        <Empty items={s.data?.items || []} />
        <div className="rx-list">
          {(s.data?.items || []).map((x: Row) => (
            <article key={x.id} className="rx-card">
              <h2>{x.name}</h2>
              <p>
                {x.category} · {x.quantity || x.qty || ""}
              </p>
              <p>소비기한 {x.expiry_date || x.expiryDate || "미설정"}</p>
              <p>{x.memo}</p>
              <div className="rx-actions">
                <button
                  onClick={() => {
                    setEdit(x);
                    setAdding(true);
                  }}
                >
                  수정
                </button>
                {filter === "ACTIVE" && (
                  <>
                    <button
                      disabled={a.busy}
                      onClick={() =>
                        a.run(async () => {
                          await send(
                            "/api/fridge/items/" + x.id + "/status",
                            { status: "CONSUMED" },
                            "PATCH",
                          );
                          s.reload();
                        })
                      }
                    >
                      사용 완료
                    </button>
                    <button
                      disabled={a.busy}
                      onClick={() =>
                        a.run(async () => {
                          await send(
                            "/api/fridge/items/" + x.id + "/status",
                            { status: "DISCARDED" },
                            "PATCH",
                          );
                          s.reload();
                        })
                      }
                    >
                      폐기
                    </button>
                  </>
                )}
                <button
                  disabled={a.busy}
                  onClick={() =>
                    a.run(async () => {
                      if (!confirm("이 식재료를 삭제할까요?")) return;
                      await api("/api/fridge/items/" + x.id, {
                        method: "DELETE",
                      });
                      s.reload();
                    })
                  }
                >
                  삭제
                </button>
              </div>
            </article>
          ))}
        </div>
      </Load>
      {adding && (
        <div
          className="rx-dialog"
          role="dialog"
          aria-modal="true"
          aria-label="식재료 편집"
        >
          <div className="rx-dialog-body">
            <h2>{edit ? "식재료 수정" : "식재료 추가"}</h2>
            <Form
              onSubmit={(f) =>
                a.run(async () => {
                  await send(
                    "/api/fridge/items" + (edit ? "/" + edit.id : ""),
                    {
                      name: text(f, "name"),
                      category: text(f, "category") || null,
                      quantity: text(f, "quantity") || null,
                      expiry_date: text(f, "expiry_date") || null,
                      memo: text(f, "memo") || null,
                    },
                    edit ? "PATCH" : "POST",
                  );
                  setAdding(false);
                  s.reload();
                })
              }
            >
              {[
                ["name", "품목"],
                ["category", "분류"],
                ["quantity", "수량"],
                ["expiry_date", "소비기한"],
                ["memo", "메모"],
              ].map(([name, label]) => (
                <label className="rx-field" key={name}>
                  {label}
                  <input
                    autoFocus={name === "name"}
                    name={name}
                    required={name === "name"}
                    type={name === "expiry_date" ? "date" : "text"}
                    defaultValue={edit?.[name] || ""}
                  />
                </label>
              ))}
              <Feedback {...a} />
              <div className="rx-actions">
                <button className="rx-primary" disabled={a.busy}>
                  저장
                </button>
                <button type="button" onClick={() => setAdding(false)}>
                  닫기
                </button>
              </div>
            </Form>
          </div>
        </div>
      )}
    </Page>
  );
}
