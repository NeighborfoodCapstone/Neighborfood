import { LoadingState, useLoadingTask } from "./loading";
import { useEffect, useRef, useState } from "react";
import type { ReactNode, FormEvent } from "react";
import { backend } from "../neighborfood/api";
export type Row = Record<string, any>;
export const token = () =>
  localStorage.getItem("nf_token") || sessionStorage.getItem("nf_token") || "";
export function logoutLocal() {
  for (const s of [localStorage, sessionStorage]) {
    s.removeItem("nf_token");
    s.removeItem("nf_userId");
  }
}
export function saveSession(d: Row) {
  logoutLocal();
  localStorage.setItem("nf_token", d.token);
  localStorage.setItem("nf_userId", String(d.userId));
}
export const uid = () =>
  Number(
    localStorage.getItem("nf_userId") || sessionStorage.getItem("nf_userId"),
  );
export function href(page: string, query: Record<string, unknown> = {}) {
  return (
    "#/" +
    page.replace(/\.html$/, "") +
    (Object.keys(query).length
      ? "?" +
        new URLSearchParams(
          Object.entries(query)
            .filter(([, v]) => v != null)
            .map(([k, v]) => [k, String(v)]),
        )
      : "")
  );
}
export function go(page: string, query: Record<string, unknown> = {}) {
  location.hash = href(page, query);
}
export function route() {
  const raw = location.hash.replace(/^#\/?/, "") || "Home";
  const [page, query] = raw.split("?");
  return { page: page.replace(/\.html$/, ""), q: new URLSearchParams(query) };
}
export function useRoute() {
  const [r, set] = useState(route);
  useEffect(() => {
    const cb = () => {
      set(route());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", cb);
    return () => window.removeEventListener("hashchange", cb);
  }, []);
  return r;
}
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
export async function api(
  path: string,
  options: RequestInit = {},
): Promise<any> {
  const headers = new Headers(options.headers);
  const auth = token();
  if (auth) headers.set("Authorization", "Bearer " + auth);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const res = await fetch(backend + path, { ...options, headers });
  const d = await res.json().catch(() => ({}));
  if (!res.ok || d.ok === false) {
    if (res.status === 401 && auth) logoutLocal();
    throw new ApiError(
      typeof d.detail === "string"
        ? d.detail
        : d.message ||
            (res.status === 401
              ? "로그인이 필요합니다."
              : res.status === 403
                ? "이 작업의 권한이 없습니다."
                : `요청 실패 (${res.status})`),
      res.status,
    );
  }
  return d;
}
export const send = (path: string, body: unknown, method = "POST") =>
  api(path, { method, body: JSON.stringify(body) });
export function useData(path: string | null) {
  const begin = useLoadingTask();
  const previousPath = useRef<string | null>(null);
  const [data, set] = useState<any>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(!!path),
    [revision, bump] = useState(0);
  useEffect(() => {
    const foreground = revision === 0 || previousPath.current !== path;
    previousPath.current = path;
    if (foreground) set(null);
    setError("");
    if (!path) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    const done = foreground ? begin() : () => {};
    if (foreground) setLoading(true);
    api(path, { signal: controller.signal })
      .then(set)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        done();
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
      done();
    };
  }, [path, revision, begin]);
  return { data, error, loading, reload: () => bump((n) => n + 1) };
}
export function useAction() {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const lock = useRef(false);
  return {
    busy,
    error,
    notice,
    run: async (fn: () => Promise<void>, message = "") => {
      if (lock.current) return;
      lock.current = true;
      setBusy(true);
      setError("");
      setNotice("");
      try {
        await fn();
        setNotice(message);
      } catch (e) {
        setError(e instanceof Error ? e.message : "처리에 실패했습니다.");
      } finally {
        lock.current = false;
        setBusy(false);
      }
    },
  };
}
export function Feedback({
  error,
  notice,
}: {
  error?: string;
  notice?: string;
}) {
  return (
    <>
      {error && (
        <p role="alert" className="rx-error">
          {error}
          {!token() && (
            <>
              {" "}
              <a href={href("Login", { next: location.hash.slice(2) })}>
                로그인
              </a>
            </>
          )}
        </p>
      )}
      {notice && (
        <p role="status" className="rx-notice">
          {notice}
        </p>
      )}
    </>
  );
}
export function Load({
  state,
  children,
}: {
  state: ReturnType<typeof useData>;
  children: ReactNode;
}) {
  if (state.loading) return <LoadingState />;
  if (state.error)
    return (
      <>
        <Feedback error={state.error} />
        <button onClick={state.reload}>다시 불러오기</button>
      </>
    );
  return <>{children}</>;
}
export function Page({
  title,
  children,
  actions,
}: {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  useEffect(() => {
    document.title = title + " · Neighborfood";
  }, [title]);
  return (
    <section className="rx-page">
      <header className="rx-title">
        <h1>{title}</h1>
        {actions}
      </header>
      {children}
    </section>
  );
}
export function Field({
  label,
  name,
  type = "text",
  value,
  onChange,
  required = false,
  min,
  max,
  step,
  placeholder,
}: {
  label: string;
  name?: string;
  type?: string;
  value?: string | number;
  onChange?: (value: string) => void;
  required?: boolean;
  min?: number;
  max?: number;
  step?: string;
  placeholder?: string;
}) {
  return (
    <label className="rx-field">
      <span>{label}</span>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange ? (e) => onChange(e.target.value) : undefined}
        required={required}
        min={min}
        max={max}
        step={step}
        placeholder={placeholder}
      />
    </label>
  );
}
export function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: (string | [string, string])[];
}) {
  return (
    <label className="rx-field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => {
          const [v, t] = Array.isArray(o) ? o : [o, o];
          return (
            <option key={v} value={v}>
              {t}
            </option>
          );
        })}
      </select>
    </label>
  );
}
export function Form({
  children,
  onSubmit,
}: {
  children: ReactNode;
  onSubmit: (f: FormData) => void;
}) {
  return (
    <form
      className="rx-form"
      onSubmit={(e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        onSubmit(new FormData(e.currentTarget));
      }}
    >
      {children}
    </form>
  );
}
export const text = (f: FormData, k: string) => String(f.get(k) || "").trim();
export const categories = [
  "채소",
  "과일",
  "육류",
  "베이커리",
  "유제품",
  "양념·가루",
];
export const types: Record<string, string> = {
  share: "나눔",
  exchange: "교환",
  groupbuy: "공동구매",
};
export const status: Record<string, string> = {
  pending: "대기",
  confirmed: "확정",
  completed: "완료",
  canceled: "취소",
  active: "진행 중",
  expired: "만료",
  unpaid: "미납",
  paid: "납부 표시",
  noshow: "불참",
  suspended: "이용 정지",
  resolved: "처리 완료",
  dismissed: "반려",
};
export const money = (n: unknown) =>
  Number(n || 0).toLocaleString("ko-KR") + "원";
export function Empty({ items }: { items: unknown[] }) {
  return items.length ? null : (
    <p className="rx-empty">표시할 항목이 없습니다.</p>
  );
}
export function PostList({ items }: { items: Row[] }) {
  return (
    <>
      <Empty items={items} />
      <div className="rx-list">
        {items.map((p) => (
          <a
            className="rx-row"
            key={p.id}
            href={href(
              p.type === "groupbuy" ? "Group_Buy_Detail" : "Product_Detail",
              { id: p.id },
            )}
          >
            {p.images?.[0] && (
              <img
                className="rx-thumb"
                src={backend + "/uploads/" + encodeURIComponent(p.images[0])}
                alt=""
              />
            )}
            <div>
              <small>
                {types[p.type]} · {status[p.status] || p.status}
              </small>
              <h3>{p.title}</h3>
              <p>
                {p.type === "share"
                  ? "무료 나눔"
                  : p.type === "exchange"
                    ? "교환 · " + (p.exchange_want || "협의")
                    : money(p.gb_price)}
              </p>
              <small>{p.address}</small>
            </div>
          </a>
        ))}
      </div>
    </>
  );
}
