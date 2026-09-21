import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import jsQR from "jsqr";
import {
  Page,
  Form,
  Field,
  Feedback,
  useAction,
  api,
  send,
  uid,
  href,
} from "./core";
import type { Row } from "./core";
export function QR({ q }: { q: URLSearchParams }) {
  const a = useAction(),
    [issued, setIssued] = useState<Row | null>(null),
    [image, setImage] = useState(""),
    [camera, setCamera] = useState(false),
    [raw, setRaw] = useState(""),
    [result, setResult] = useState<Row | null>(null),
    [scanError, setScanError] = useState("");
  const video = useRef<HTMLVideoElement>(null);
  const settlement = q.get("settlementId"),
    loc =
      q.get("locationSessionId") ||
      sessionStorage.getItem("nf_location_session");
  const acceptRef = useRef<(value: string) => void>(() => {});
  function verify(value: string) {
    setCamera(false);
    a.run(async () => {
      let token = value;
      try {
        const u = new URL(value);
        const h = new URLSearchParams(u.hash.split("?")[1]);
        token = h.get("token") || u.pathname.split("/verify/")[1] || value;
      } catch {
        /* Raw tokens are allowed by the API. */
      }
      const d = await send("/api/qr/verify", { rawValue: token });
      setResult(d);
    }, "QR 인증이 완료되었습니다.");
  }
  acceptRef.current = verify;
  useEffect(() => {
    if (!camera) return;
    let cancelled = false,
      stream: MediaStream | undefined,
      timer = 0;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    async function start() {
      try {
        if (!navigator.mediaDevices?.getUserMedia)
          throw Error("카메라는 HTTPS 또는 localhost에서 사용할 수 있습니다.");
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        const v = video.current;
        if (!v) return;
        v.srcObject = stream;
        await v.play();
        const tick = () => {
          if (cancelled) return;
          if (v.readyState >= 2 && v.videoWidth && ctx) {
            canvas.width = v.videoWidth;
            canvas.height = v.videoHeight;
            ctx.drawImage(v, 0, 0);
            const frame = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(frame.data, frame.width, frame.height);
            if (code) {
              acceptRef.current(code.data);
              return;
            }
          }
          timer = window.setTimeout(tick, 180);
        };
        tick();
      } catch (e) {
        if (!cancelled) {
          setScanError(
            e instanceof Error ? e.message : "카메라를 열지 못했습니다.",
          );
          setCamera(false);
        }
      }
    }
    start();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [camera]);
  return (
    <Page title="QR 거래 인증">
      <div className="rx-actions">
        <button
          onClick={() => {
            setScanError("");
            setCamera(true);
          }}
          disabled={camera}
        >
          카메라로 스캔
        </button>
        {camera && (
          <button onClick={() => setCamera(false)}>카메라 종료</button>
        )}
      </div>
      {camera && <video className="rx-video" ref={video} muted playsInline />}
      <Feedback error={scanError} />
      <Form onSubmit={() => verify(raw)}>
        <Field
          label="QR 내용 또는 인증 토큰"
          value={raw}
          onChange={setRaw}
          required
        />
        <button className="rx-primary" disabled={a.busy}>
          인증 확인
        </button>
      </Form>
      <Feedback {...a} />
      <h2>내 거래 QR 발급</h2>
      <p>상대방이 이 QR을 스캔하여 대면 거래를 확인합니다.</p>
      <button
        disabled={a.busy}
        onClick={() =>
          a.run(async () => {
            const d = await send("/api/qr/request", {
              subjectId: String(uid()),
              purpose: "pickup_confirm",
              ttlSeconds: 300,
            });
            if (loc)
              await send(
                "/api/location-verify/" +
                  encodeURIComponent(loc) +
                  "/qr-issued",
                { qrSessionId: d.session.id },
              );
            setIssued(d.session);
            const url =
              location.origin +
              location.pathname +
              href("QR_Scan", { token: d.session.token });
            setImage(
              await QRCode.toDataURL(url, {
                width: 280,
                margin: 3,
                errorCorrectionLevel: "M",
              }),
            );
          })
        }
      >
        5분 유효 QR 발급
      </button>
      {issued && (
        <div className="rx-card">
          <img className="rx-qr" src={image} alt="거래 인증 QR" />
          <p>만료: {new Date(issued.expiresAt).toLocaleTimeString("ko-KR")}</p>
        </div>
      )}
      {q.get("token") && (
        <button disabled={a.busy} onClick={() => verify(q.get("token")!)}>
          전달받은 QR 인증
        </button>
      )}
      {result && <p>인증 상태: {result.message}</p>}
      {settlement && (
        <button
          disabled={a.busy}
          onClick={() =>
            a.run(async () => {
              await api(
                "/api/settlements/" + settlement + "/shares/me/qr-done",
                { method: "POST" },
              );
              location.hash = href("Settlement", { settlementId: settlement });
            })
          }
        >
          정산에 인증 결과 반영
        </button>
      )}
    </Page>
  );
}
