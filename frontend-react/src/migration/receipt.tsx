import { useState } from "react";
import {
  Page,
  Form,
  Feedback,
  useAction,
  api,
  send,
  uid,
  href,
  money,
} from "./core";
import type { Row } from "./core";
export function Receipt() {
  const a = useAction(),
    [file, setFile] = useState<File | null>(null),
    [scan, setScan] = useState<Row | null>(null),
    [items, setItems] = useState<Row[]>([]),
    [receipt, setReceipt] = useState<Row | null>(null),
    [added, setAdded] = useState(false);
  const update = (i: number, k: string, v: unknown) =>
    setItems((xs) => xs.map((x, n) => (n === i ? { ...x, [k]: v } : x)));
  return (
    <Page title="영수증 인증">
      <Form
        onSubmit={() =>
          a.run(async () => {
            if (!file) return;
            const fd = new FormData();
            fd.append("file", file);
            const d = await api("/api/receipt/scan?subjectId=" + uid(), {
              method: "POST",
              body: fd,
            });
            setScan(d.scan);
            setItems(d.scan.items.map((x: Row) => ({ ...x, selected: true })));
            setReceipt(null);
            setAdded(false);
          })
        }
      >
        <label className="rx-field">
          영수증 사진
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
          />
        </label>
        <button className="rx-primary" disabled={a.busy || !file}>
          영수증 분석
        </button>
      </Form>
      <Feedback {...a} />
      {scan && (
        <>
          <h2>{scan.store || "매장명 미인식"}</h2>
          <p>
            {scan.purchasedAt} · {money(scan.total)}
          </p>
          {!items.length && (
            <p>인식된 품목이 없습니다. 사진을 다시 촬영해 주세요.</p>
          )}
          <div className="rx-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>선택</th>
                  <th>품목</th>
                  <th>수량</th>
                  <th>금액</th>
                </tr>
              </thead>
              <tbody>
                {items.map((x, i) => (
                  <tr key={i}>
                    <td>
                      <input
                        aria-label={x.name + " 선택"}
                        type="checkbox"
                        checked={x.selected}
                        disabled={!!receipt}
                        onChange={(e) =>
                          update(i, "selected", e.target.checked)
                        }
                      />
                    </td>
                    <td>
                      <input
                        aria-label="품목명"
                        value={x.name}
                        disabled={!!receipt}
                        onChange={(e) => update(i, "name", e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        aria-label="수량"
                        type="number"
                        min={1}
                        value={x.qty}
                        disabled={!!receipt}
                        onChange={(e) =>
                          update(i, "qty", Number(e.target.value))
                        }
                      />
                    </td>
                    <td>
                      <input
                        aria-label="금액"
                        type="number"
                        min={0}
                        value={x.price}
                        disabled={!!receipt}
                        onChange={(e) =>
                          update(i, "price", Number(e.target.value))
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            className="rx-primary"
            disabled={a.busy || !!receipt || !items.some((x) => x.selected)}
            onClick={() =>
              a.run(async () => {
                const d = await send("/api/receipt/verify", {
                  scanId: scan.id,
                  subjectId: String(uid()),
                  store: scan.store,
                  purchasedAt: scan.purchasedAt,
                  items: items
                    .filter((x) => x.selected)
                    .map(({ name, qty, price }) => ({ name, qty, price })),
                });
                setReceipt(d.receipt);
              }, "영수증 인증이 완료되었습니다.")
            }
          >
            선택 항목 인증
          </button>
          {receipt && (
            <div className="rx-actions">
              <button
                disabled={a.busy || added}
                onClick={() =>
                  a.run(async () => {
                    await send("/api/fridge/from-receipt", {
                      receiptId: receipt.id,
                    });
                    setAdded(true);
                  }, "냉장고에 등록했습니다.")
                }
              >
                {added ? "냉장고 등록 완료" : "냉장고에 추가"}
              </button>
              <a href={href("Fridge")}>내 냉장고</a>
            </div>
          )}
        </>
      )}
    </Page>
  );
}
