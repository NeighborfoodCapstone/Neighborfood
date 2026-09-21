import { useEffect, useId, useImperativeHandle, useRef, useState } from "react";
import type { Ref } from "react";
import { api } from "./core";
import { LoadingState } from "./loading";
export type Suggestion = {
  value: string;
  label: string;
  detail?: string;
  data?: Record<string, any>;
};
export type SuggestionLoader = (
  query: string,
  signal: AbortSignal,
) => Promise<Suggestion[]>;
export type AutocompleteHandle = { show: () => void };
export async function postSuggestions(
  query: string,
  signal: AbortSignal,
): Promise<Suggestion[]> {
  const d = await api(
    "/posts?" + new URLSearchParams({ keyword: query, limit: "8" }),
    { signal },
  );
  const seen = new Set<string>();
  return (d.items || [])
    .filter((x: any) => {
      if (!x.title || seen.has(x.title)) return false;
      seen.add(x.title);
      return true;
    })
    .map((x: any) => ({
      value: x.title,
      label: x.title,
      detail: [x.category, x.address].filter(Boolean).join(" · "),
    }));
}
export async function memberSuggestions(
  query: string,
  signal: AbortSignal,
): Promise<Suggestion[]> {
  const d = await api("/api/admin/users?q=" + encodeURIComponent(query), {
    signal,
  });
  return (d.items || []).slice(0, 8).map((x: any) => ({
    value: x.login_id || x.nickname,
    label: x.nickname || x.login_id,
    detail: x.login_id,
  }));
}
export function SuggestionList({
  id,
  items,
  active,
  onPick,
}: {
  id: string;
  items: Suggestion[];
  active: number;
  onPick: (x: Suggestion) => void;
}) {
  return (
    <ul id={id} role="listbox" className="rx-suggestion-list">
      {items.map((item, index) => (
        <li
          id={id + "-" + index}
          key={item.value + "-" + index}
          role="option"
          aria-selected={index === active}
          className={index === active ? "is-active" : ""}
          onPointerDown={(e) => e.preventDefault()}
          onClick={() => onPick(item)}
        >
          <span>{item.label}</span>
          {item.detail && <small>{item.detail}</small>}
        </li>
      ))}
    </ul>
  );
}
export function Autocomplete({
  value,
  onChange,
  onSelect,
  load = postSuggestions,
  label,
  id,
  name,
  placeholder,
  required = false,
  maxLength = 100,
  ref,
}: {
  value: string;
  onChange: (v: string) => void;
  onSelect?: (item: Suggestion) => void;
  load?: SuggestionLoader;
  label: string;
  id?: string;
  name?: string;
  placeholder?: string;
  required?: boolean;
  maxLength?: number;
  ref?: Ref<AutocompleteHandle>;
}) {
  const unique = useId(),
    listId = unique + "-list",
    input = useRef<HTMLInputElement>(null),
    box = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false),
    [items, setItems] = useState<Suggestion[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [active, setActive] = useState(-1),
    [composing, setComposing] = useState(false),
    [retry, setRetry] = useState(0);
  const sequence = useRef(0),
    composition = useRef(false);
  useImperativeHandle(
    ref,
    () => ({
      show: () => {
        input.current?.focus();
        setOpen(true);
        setRetry((n) => n + 1);
      },
    }),
    [],
  );
  useEffect(() => {
    const n = ++sequence.current;
    const controller = new AbortController();
    setActive(-1);
    setError("");
    setItems([]);
    if (!open || !value.trim() || composing) {
      setBusy(false);
      return () => controller.abort();
    }
    setBusy(true);
    const timeout = setTimeout(() => {
      load(value.trim(), controller.signal)
        .then((rows) => {
          if (n === sequence.current && !controller.signal.aborted)
            setItems(rows.slice(0, 8));
        })
        .catch((e) => {
          if (n === sequence.current && !controller.signal.aborted)
            setError(e.message || "목록을 불러오지 못했습니다.");
        })
        .finally(() => {
          if (n === sequence.current && !controller.signal.aborted)
            setBusy(false);
        });
    }, 250);
    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [value, open, load, composing, retry]);
  useEffect(() => {
    function dismiss(e: PointerEvent) {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);
  useEffect(() => {
    if (active >= 0)
      document
        .getElementById(listId + "-" + active)
        ?.scrollIntoView?.({ block: "nearest" });
  }, [active, listId]);
  function pick(item: Suggestion) {
    setOpen(false);
    setActive(-1);
    onChange(item.value);
    onSelect?.(item);
  }
  const expanded = open && !!value.trim() && !composing;
  return (
    <div
      className="rx-autocomplete"
      ref={box}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null))
          setOpen(false);
      }}
    >
      <input
        ref={input}
        id={id || unique}
        name={name}
        aria-label={label}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={expanded}
        aria-controls={expanded ? listId : undefined}
        aria-activedescendant={
          expanded && active >= 0 ? listId + "-" + active : undefined
        }
        value={value}
        placeholder={placeholder}
        required={required}
        maxLength={maxLength}
        autoComplete="off"
        onChange={(e) => {
          setActive(-1);
          setItems([]);
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onCompositionStart={() => {
          composition.current = true;
          setComposing(true);
        }}
        onCompositionEnd={() => {
          composition.current = false;
          setComposing(false);
        }}
        onKeyDown={(e) => {
          if (
            composition.current ||
            e.nativeEvent.isComposing ||
            e.keyCode === 229
          )
            return;
          if (e.key === "Escape") {
            e.preventDefault();
            setOpen(false);
            setActive(-1);
          } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            setOpen(true);
            if (items.length)
              setActive((n) =>
                e.key === "ArrowDown"
                  ? (n + 1) % items.length
                  : n < 0
                    ? items.length - 1
                    : (n - 1 + items.length) % items.length,
              );
          } else if (e.key === "Enter") {
            if (expanded && active >= 0 && items[active]) {
              e.preventDefault();
              pick(items[active]);
            } else setOpen(false);
          }
        }}
      />
      {expanded && (
        <div className="rx-suggestions">
          {busy ? (
            <>
              <ul
                id={listId}
                role="listbox"
                className="rx-suggestion-list"
                aria-label="자동완성 목록"
              />
              <LoadingState compact label="검색 중…" />
            </>
          ) : error ? (
            <>
              <ul id={listId} role="listbox" className="rx-suggestion-list" />
              <p className="rx-suggestion-message" role="status">
                {error}
              </p>
              <button
                type="button"
                className="rx-suggestion-retry"
                onClick={() => setRetry((n) => n + 1)}
              >
                다시 불러오기
              </button>
            </>
          ) : items.length ? (
            <SuggestionList
              id={listId}
              items={items}
              active={active}
              onPick={pick}
            />
          ) : (
            <>
              <ul id={listId} role="listbox" className="rx-suggestion-list" />
              <p className="rx-suggestion-message" role="status">
                일치하는 항목이 없습니다.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
