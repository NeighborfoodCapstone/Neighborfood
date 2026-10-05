import { useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import "./scanner.css";

type Props = { kind: "qr" | "receipt"; onRead?: (text: string) => void; onCapture?: (file: File) => void; disabled?: boolean; preview?: string; onReset?: () => void; status?: "idle" | "checking" | "success" | "error" };
export function Scanner({ kind, onRead, onCapture, disabled = false, preview = "", status = "idle", onReset }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const handlers = useRef({ onRead, onCapture });
  handlers.current = { onRead, onCapture };
  const [frozen, setFrozen] = useState("");
  const [active, setActive] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [capturing, setCapturing] = useState(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    if (!active || disabled) return;
    let disposed = false;
    let stream: MediaStream | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const element = video.current;
    const stop = () => {
      disposed = true;
      clearTimeout(timer);
      stream?.getTracks().forEach(track => track.stop());
      if (element) element.srcObject = null;
    };
    const hide = () => { if (document.hidden) { stop(); setReady(false); setActive(false); } };
    document.addEventListener("visibilitychange", hide);
    setReady(false); setError("");
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", { willReadFrequently: true });
    async function start() {
      try {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error("카메라는 HTTPS 또는 localhost에서 사용할 수 있습니다. 사진 선택이나 직접 입력을 이용해 주세요.");
        stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 1920 } } });
        if (disposed || !element) { stream.getTracks().forEach(track => track.stop()); return; }
        element.srcObject = stream;
        await element.play();
        if (disposed) return;
        setReady(true);
        if (kind !== "qr") return;
        function decode() {
          if (disposed || !element || !context) return;
          if (element.readyState >= 2 && element.videoWidth) {
            const side = Math.min(element.videoWidth, element.videoHeight);
            canvas.width = canvas.height = Math.min(960, side);
            context.drawImage(element, (element.videoWidth-side)/2, (element.videoHeight-side)/2, side, side, 0, 0, canvas.width, canvas.height);
            const frame = context.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(frame.data, frame.width, frame.height);
            if (code?.data) {
              setFrozen(canvas.toDataURL("image/jpeg", 0.8));
              stop(); setActive(false); setReady(false);
              handlers.current.onRead?.(code.data);
              return;
            }
          }
          timer = setTimeout(decode, 180);
        }
        decode();
      } catch (e) {
        if (disposed) return;
        stop(); setReady(false); setActive(false);
        const name = e instanceof Error ? e.name : "";
        setError(name === "NotAllowedError" ? "카메라 권한이 필요합니다. 주소창의 사이트 설정에서 허용한 뒤 다시 시작해 주세요."
          : name === "NotFoundError" ? "연결된 카메라가 없습니다. 사진 선택이나 직접 입력을 이용해 주세요."
          : name === "NotReadableError" ? "다른 앱에서 카메라를 사용 중인지 확인한 뒤 다시 시작해 주세요."
          : e instanceof Error ? e.message : "카메라를 열지 못했습니다.");
      }
    }
    void start();
    return () => { stop(); document.removeEventListener("visibilitychange", hide); };
  }, [active, disabled, attempt, kind]);
  function capture() {
    const element = video.current;
    if (!element?.videoWidth || !ready || capturing) return;
    const canvas = document.createElement("canvas");
    canvas.width = element.videoWidth; canvas.height = element.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) { setError("사진을 만들지 못했습니다. 다시 시도해 주세요."); return; }
    context.drawImage(element, 0, 0);
    setCapturing(true);
    canvas.toBlob(blob => {
      if (!alive.current) return;
      setCapturing(false);
      if (!blob) { setError("촬영에 실패했습니다. 다시 촬영해 주세요."); return; }
      setActive(false); setReady(false);
      handlers.current.onCapture?.(new File([blob], `receipt-${Date.now()}.jpg`, { type: "image/jpeg" }));
    }, "image/jpeg", 0.92);
  }
  return <section className={`rx-scanner rx-scanner-${kind}`}>
    <div className={`rx-scanner-view rx-scan-${status}${capturing ? " rx-capture" : ""}`}>
      <video ref={video} autoPlay muted playsInline aria-label={kind === "qr" ? "QR 스캐너 카메라" : "영수증 촬영 카메라"} />
      {(preview || frozen) && <img className="rx-scanner-still" src={preview || frozen} alt={kind === "qr" ? "감지한 QR 화면" : "촬영하거나 선택한 영수증"} />}
      {status === "success" && <span className="rx-scan-check" aria-label="인증 완료">✓</span>}
      <div className="rx-scanner-guide" aria-hidden="true" />
      <p className="rx-scanner-caption" role="status">{status === "success" ? "QR 인증 완료" : status === "error" ? "인증 실패 · 아래 사유를 확인해 주세요" : status === "checking" ? "인증 확인 중…" : preview ? "촬영한 영수증 · 아래에서 인식을 진행해 주세요" : disabled ? "처리 중입니다" : ready && active ? kind === "qr" ? "QR 코드를 화면 중앙에 맞춰 주세요" : "영수증 전체가 보이도록 맞춰 주세요" : active ? "카메라 연결 중 · 권한 요청을 허용해 주세요" : "카메라가 정지되었습니다"}</p>
    </div>
    {error && <p className="rx-scanner-error" role="alert">{error}</p>}
    <div className="rx-actions rx-scanner-controls">
      {kind === "receipt" && <button type="button" className="rx-primary" disabled={!ready || !active || disabled || capturing} onClick={capture}>{capturing ? "사진 저장 중…" : "영수증 촬영"}</button>}
      {active ? <button type="button" onClick={() => { setActive(false); setReady(false); }}>카메라 중지</button> : <button type="button" disabled={disabled || capturing} onClick={() => { onReset?.(); setFrozen(""); setActive(true); setAttempt(n => n + 1); }}>카메라 다시 시작</button>}
    </div>
  </section>;
}
