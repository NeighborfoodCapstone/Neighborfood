import {
  createContext,
  useCallback,
  useContext,
  useState,
} from "react";
import type { ReactNode } from "react";
const Idle = () => () => {};
const LoadingContext = createContext<() => () => void>(Idle);
export function useLoadingTask() {
  return useContext(LoadingContext);
}
export function LoadingState({
  label = "불러오는 중…",
  compact = false,
}: {
  label?: string;
  compact?: boolean;
}) {
  return (
    <div
      className={"rx-loading-state" + (compact ? " compact" : "")}
      role="status"
      aria-live="polite"
    >
      <span className="rx-spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
export function RouteLoading({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState(0);
  const begin = useCallback(() => {
    let released = false;
    setPending((n) => n + 1);
    return () => {
      if (!released) {
        released = true;
        setPending((n) => Math.max(0, n - 1));
      }
    };
  }, []);
  const busy = pending > 0;
  return (
    <LoadingContext.Provider value={begin}>
      <div className="rx-route-stage" aria-busy={busy}>
        <div className="rx-route-content">
          {children}
        </div>
        {busy && (
          <div className="rx-route-progress">
            <LoadingState label="화면을 불러오는 중…" />
          </div>
        )}
      </div>
    </LoadingContext.Provider>
  );
}
