import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminDemo } from "../src/migration/demo";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  localStorage.clear();
});

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

function stubApi() {
  const calls: string[] = [];
  let created = false;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(input instanceof Request ? input.url : input.toString(), window.location.href);
    const method = init?.method ?? "GET";
    calls.push(`${method} ${url.pathname}${url.search ? "?" + url.searchParams.toString() : ""}`);
    if (url.pathname === "/api/admin/demo/users")
      return json({ ok: true, items: [{ id: 5, loginId: "booth_guest", nickname: "부스손님", demoTrades: 0 }] });
    if (url.pathname === "/api/admin/demo/trades" && method === "GET")
      return json({
        ok: true, user: { id: 5, loginId: "booth_guest" },
        spot: { address: "서울 중랑구 용마산로90길 28 (서일대학교 호천관)", lat: 37.589, lng: 127.094 },
        count: created ? 1 : 0,
        items: created ? [{
          postId: 7, type: "share", typeLabel: "나눔", title: "[체험] 남는 대파 나눠요",
          place: "서울 중랑구 용마산로90길 28 (서일대학교 호천관)", appointmentAt: null,
          next: "체험자가 약속 일시를 정해야 합니다.",
          participants: [{ userId: 2, nickname: "체험이웃 하나", gps: false, qr: false, paid: false }],
          settlement: null, transaction: { id: 3, status: "confirmed" },
        }] : [],
      });
    if (url.pathname === "/api/admin/demo/trades" && method === "POST") { created = true; return json({ ok: true, trade: {} }); }
    if (url.pathname === "/api/admin/demo/trades" && method === "DELETE") { created = false; return json({ ok: true, removed: 1 }); }
    throw new Error(`Unexpected request: ${method} ${url.pathname}`);
  }));
  return calls;
}

describe("관리자 체험 모드 화면", () => {
  it("체험자를 고르고 유형을 정해 더미 거래를 만들고 초기화한다", async () => {
    localStorage.setItem("nf_token", "synthetic-test-token");
    const calls = stubApi();
    render(<AdminDemo />);
    await userEvent.click(await screen.findByRole("button", { name: /booth_guest/ }));
    expect(await screen.findByText(/호천관/)).toBeTruthy();
    await userEvent.selectOptions(screen.getByLabelText("거래 유형"), "share");
    await userEvent.click(screen.getByRole("button", { name: "더미 거래 생성" }));
    await waitFor(() => expect(calls).toContain("POST /api/admin/demo/trades"));
    expect(await screen.findByText(/남는 대파 나눠요/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "위치 인증 + QR 발급" })).toBeTruthy();
    // 초기화는 두 번 눌러야 실행된다
    await userEvent.click(screen.getByRole("button", { name: "이 체험자 거래 초기화" }));
    expect(calls.some((c) => c.startsWith("DELETE"))).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: /정말 초기화/ }));
    await waitFor(() => expect(calls.some((c) => c.startsWith("DELETE"))).toBe(true));
    expect(await screen.findByText(/체험 거래가 없습니다/)).toBeTruthy();
  });
});
