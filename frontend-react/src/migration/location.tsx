import { Autocomplete } from "./autocomplete";
import type { AutocompleteHandle, SuggestionLoader } from "./autocomplete";
import { useEffect, useRef, useState } from "react";
import {
  Page,
  Select,
  types,
  Form,
  Feedback,
  Load,
  PostList,
  useAction,
  useData,
  api,
  send,
  go,
  href,
} from "./core";
import type { Row } from "./core";
declare global {
  interface Window {
    kakao: any;
  }
}
let sdk: Promise<any> | undefined;
export function loadMap(): Promise<any> {
  if (window.kakao?.maps?.services) return Promise.resolve(window.kakao);
  if (!sdk)
    sdk = api("/api/config/kakao-key")
      .then(
        (d) =>
          new Promise((resolve, reject) => {
            if (!d.key) {
              reject(Error("지도 설정을 불러오지 못했습니다."));
              return;
            }
            const s = document.createElement("script");
            s.src =
              "https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&libraries=services,clusterer&appkey=" +
              encodeURIComponent(d.key);
            s.onload = () =>
              window.kakao.maps.load(() => resolve(window.kakao));
            s.onerror = () => {
              sdk = undefined;
              reject(Error("지도를 불러오지 못했습니다."));
            };
            document.head.appendChild(s);
          }),
      )
      .catch((e) => {
        sdk = undefined;
        throw e;
      });
  return sdk;
}
export function locate(): Promise<{
  lat: number;
  lng: number;
  accuracy: number;
}> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(Error("위치 서비스를 지원하지 않는 브라우저입니다."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) =>
        resolve({
          lat: p.coords.latitude,
          lng: p.coords.longitude,
          accuracy: p.coords.accuracy,
        }),
      (e) => reject(Error(e.message)),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  });
}
export function MapView({
  points,
  center,
  onPick,
}: {
  points: Row[];
  onPick?: (p: { lat: number; lng: number }) => void;
  center?: { lat: number; lng: number };
}) {
  const ref = useRef<HTMLDivElement>(null),
    [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    const markers: any[] = [];
    const listeners: { obj: any; event: string; cb: (event?: any) => void }[] =
      [];
    let map: any;
    loadMap()
      .then((k) => {
        if (cancelled || !ref.current) return;
        const c = center ||
          points.find((p) => p.lat != null && p.lng != null) || {
            lat: 37.5665,
            lng: 126.978,
          };
        map = new k.maps.Map(ref.current, {
          center: new k.maps.LatLng(c.lat, c.lng),
          level: 5,
        });
        if (onPick) {
          const cb = (event: any) =>
            onPick({ lat: event.latLng.getLat(), lng: event.latLng.getLng() });
          k.maps.event.addListener(map, "click", cb);
          listeners.push({ obj: map, event: "click", cb });
        }
        points
          .filter((p) => p.lat != null && p.lng != null)
          .forEach((p) => {
            const m = new k.maps.Marker({
              map,
              position: new k.maps.LatLng(p.lat, p.lng),
              title: p.title || "거래 장소",
            });
            markers.push(m);
            if (p.id) {
              const cb = () =>
                go(
                  p.type === "groupbuy" ? "Group_Buy_Detail" : "Product_Detail",
                  { id: p.id },
                );
              k.maps.event.addListener(m, "click", cb);
              listeners.push({ obj: m, event: "click", cb });
            }
          });
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
      markers.forEach((m) => m.setMap(null));
      listeners.forEach((x) =>
        window.kakao.maps.event.removeListener(x.obj, x.event, x.cb),
      );
      if (ref.current) ref.current.replaceChildren();
      map = null;
    };
  }, [JSON.stringify(points), center?.lat, center?.lng]);
  return (
    <>
      <Feedback error={error} />
      <div className="rx-map" ref={ref} aria-label="거래 위치 지도" />
    </>
  );
}
export function MapPage({
  q,
  detail = false,
}: {
  q: URLSearchParams;
  detail?: boolean;
}) {
  const [type, setType] = useState("");
  const [keyword, setKeyword] = useState(""),
    [draft, setDraft] = useState(""),
    [center, setCenter] = useState<{ lat: number; lng: number }>();
  const s = useData(
      detail && q.get("id")
        ? "/posts/" + q.get("id")
        : "/posts?limit=100&keyword=" +
            encodeURIComponent(keyword) +
            "&type=" +
            encodeURIComponent(type),
    ),
    a = useAction();
  const points = s.data
    ? detail
      ? [s.data.post || s.data]
      : s.data.items || []
    : [];
  return (
    <Page title={detail ? "거래 장소" : "동네 지도"}>
      {!detail && (
        <Form onSubmit={() => setKeyword(draft)}>
          <div className="rx-search">
            <Autocomplete
              label="지도 검색"
              value={draft}
              onChange={setDraft}
              onSelect={(item) => setKeyword(item.value)}
            />
            <button className="rx-search-button">검색</button>
          </div>
        </Form>
      )}
      {!detail && (
        <Select
          label="거래 유형"
          value={type}
          onChange={setType}
          options={[["", "전체"], ...Object.entries(types)]}
        />
      )}
      <button
        disabled={a.busy}
        onClick={() => a.run(async () => setCenter(await locate()))}
      >
        내 위치
      </button>
      <Feedback {...a} />
      <Load state={s}>
        <MapView points={points} center={center} />
        <PostList items={points} />
      </Load>
    </Page>
  );
}
export const addressSuggestions: SuggestionLoader = async (query, signal) => {
  const k = await loadMap();
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  return new Promise((resolve, reject) => {
    new k.maps.services.Geocoder().addressSearch(
      query,
      (rows: Row[], status: string) => {
        if (signal.aborted) {
          reject(new DOMException("Aborted", "AbortError"));
          return;
        }
        if (status === k.maps.services.Status.ZERO_RESULT) {
          resolve([]);
          return;
        }
        if (status !== k.maps.services.Status.OK) {
          reject(Error("주소를 불러오지 못했습니다."));
          return;
        }
        resolve(
          rows
            .slice(0, 8)
            .map((x) => ({
              value: x.address_name,
              label: x.address_name,
              detail: x.road_address?.address_name,
              data: x,
            })),
        );
      },
    );
  });
};
export function Neighborhood() {
  const searchBox = useRef<AutocompleteHandle>(null);
  const a = useAction(),
    [pos, setPos] = useState<{ lat: number; lng: number }>(),
    [address, setAddress] = useState(""),
    [search, setSearch] = useState("");
  return (
    <Page title="내 동네 설정">
      <Form onSubmit={() => searchBox.current?.show()}>
        <div className="rx-search">
          <Autocomplete
            ref={searchBox}
            label="동네 주소"
            value={search}
            onChange={setSearch}
            load={addressSuggestions}
            required
            onSelect={(item) => {
              setAddress(item.value);
              setPos({ lat: Number(item.data!.y), lng: Number(item.data!.x) });
            }}
          />
          <button className="rx-search-button">검색</button>
        </div>
      </Form>
      <button
        disabled={a.busy}
        onClick={() =>
          a.run(async () => {
            const p = await locate();
            const k = await loadMap();
            const r: Row[] = await new Promise((resolve, reject) =>
              new k.maps.services.Geocoder().coord2Address(
                p.lng,
                p.lat,
                (rows: Row[], s: string) =>
                  s === k.maps.services.Status.OK
                    ? resolve(rows)
                    : reject(Error("주소 확인에 실패했습니다.")),
              ),
            );
            setPos(p);
            setAddress(r[0].address.address_name);
          })
        }
      >
        현재 위치로 찾기
      </button>
      {pos && <MapView points={[pos]} center={pos} />}
      <p>{address}</p>
      <Feedback {...a} />
      <button
        className="rx-primary"
        disabled={a.busy || !pos || !address}
        onClick={() =>
          a.run(async () => {
            await send("/api/users/neighborhood", {
              ...pos,
              neighborhood: address,
            });
            go("My_Page");
          })
        }
      >
        이 동네로 설정
      </button>
    </Page>
  );
}
export function LocationVerify({ q }: { q: URLSearchParams }) {
  const a = useAction(),
    settlementId = q.get("settlementId"),
    s = useData(settlementId ? "/api/settlements/" + settlementId : null),
    [target, setTarget] = useState<{ lat: number; lng: number }>(),
    [session, setSession] = useState<Row | null>(null),
    [verified, setVerified] = useState(false);
  const lat = s.data?.settlement?.appointmentLat,
    lng = s.data?.settlement?.appointmentLng;
  const point =
    settlementId && lat != null && lng != null
      ? { lat: Number(lat), lng: Number(lng) }
      : target;
  return (
    <Page title="GPS 위치 인증">
      <Load state={s}>
        <p>약속 장소 반경 100m 이내인지 확인합니다.</p>
        {point && <MapView points={[point]} center={point} />}{" "}
        {!settlementId && (
          <Form
            onSubmit={(f) => {
              const lat = String(f.get("lat") || ""),
                lng = String(f.get("lng") || "");
              if (!lat || !lng) return;
              setTarget({ lat: Number(lat), lng: Number(lng) });
              setSession(null);
              setVerified(false);
            }}
          >
            <PlaceField initial={target} />
            <button>거래 장소 설정</button>
          </Form>
        )}
        {settlementId && !point && (
          <p>주최자가 약속 좌표를 먼저 설정해야 합니다.</p>
        )}
        <Feedback {...a} />
        <button
          className="rx-primary"
          disabled={a.busy || !point}
          onClick={() =>
            a.run(async () => {
              if (!point) return;
              const p = await locate();
              const issued =
                session ||
                (
                  await send("/api/location-verify/dummy-target", {
                    ...point,
                    radiusM: 100,
                    address: s.data?.settlement?.appointmentPlace || "",
                  })
                ).session;
              setSession(issued);
              await send("/api/location-verify/" + issued.id + "/gps-check", {
                ...p,
                radiusM: 100,
                accuracyLimitM: 1500,
              });
              if (settlementId)
                await api(
                  "/api/settlements/" + settlementId + "/shares/me/gps-done",
                  { method: "POST" },
                );
              sessionStorage.setItem("nf_location_session", issued.id);
              setVerified(true);
            }, "위치 인증이 완료되었습니다.")
          }
        >
          현재 위치 인증
        </button>
        {verified && session && (
          <a
            className="rx-primary"
            href={href("QR_Scan", {
              locationSessionId: session.id,
              settlementId,
              mode: "issue",
            })}
          >
            QR 인증으로 이동
          </a>
        )}
      </Load>
    </Page>
  );
}

export function PlaceField({
  initial = {},
  addressName = "address",
}: {
  initial?: Row;
  addressName?: string;
}) {
  const addressBox = useRef<AutocompleteHandle>(null);
  const a = useAction(),
    [address, setAddress] = useState(initial?.address || ""),
    [pos, setPos] = useState<{ lat: number; lng: number } | undefined>(
      initial?.lat != null && initial?.lng != null
        ? { lat: Number(initial.lat), lng: Number(initial.lng) }
        : undefined,
    );
  return (
    <fieldset>
      <legend>거래 장소</legend>
      <label className="rx-field">
        주소
        <Autocomplete
          ref={addressBox}
          name={addressName}
          label="주소"
          value={address}
          onChange={(v) => {
            setAddress(v);
            setPos(undefined);
          }}
          load={addressSuggestions}
          onSelect={(item) =>
            setPos({ lat: Number(item.data!.y), lng: Number(item.data!.x) })
          }
        />
      </label>
      <div className="rx-actions">
        <button
          type="button"
          disabled={a.busy || !address}
          className="rx-search-button"
          onClick={() => addressBox.current?.show()}
        >
          주소 검색
        </button>
        <button
          type="button"
          disabled={a.busy}
          onClick={() =>
            a.run(async () => {
              const p = await locate();
              setPos(p);
              const k = await loadMap();
              const rows: Row[] = await new Promise((resolve, reject) =>
                new k.maps.services.Geocoder().coord2Address(
                  p.lng,
                  p.lat,
                  (r: Row[], s: string) =>
                    s === k.maps.services.Status.OK
                      ? resolve(r)
                      : reject(Error("주소를 확인하지 못했습니다.")),
                ),
              );
              setAddress(rows[0].address.address_name);
            })
          }
        >
          내 위치
        </button>
      </div>
      <Feedback {...a} />
      <MapView points={pos ? [pos] : []} center={pos} onPick={setPos} />
      <small>지도에서 정확한 거래 위치를 선택할 수 있습니다.</small>
      <input type="hidden" name="lat" value={pos?.lat ?? ""} />
      <input type="hidden" name="lng" value={pos?.lng ?? ""} />
    </fieldset>
  );
}
