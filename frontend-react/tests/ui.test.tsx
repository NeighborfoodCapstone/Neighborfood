import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppLayout } from "../src/neighborfood/AppLayout";
import { Chat, Settlement } from "../src/migration/trades";
import { Screen } from "../src/migration/routes";
import { MapPage } from "../src/migration/location";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
  history.replaceState(null, "", "/");
});

describe("공통 메뉴", () => {
  it("메뉴를 열고 포커스를 가둔 뒤 Escape로 닫고 원래 위치로 돌려준다", async () => {
    const user = userEvent.setup();
    render(<AppLayout><h1>본문</h1></AppLayout>);
    const trigger = screen.getByRole("button", { name: "전체 메뉴 열기" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "전체 메뉴" });
    const close = within(dialog).getByRole("button", { name: "메뉴 닫기" });
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(close);
    expect(document.querySelector("main")?.hasAttribute("inert")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
    expect(within(dialog).getAllByRole("link").map((link) => link.textContent?.replace("›", "").trim())).toEqual([
      "내 냉장고", "찜 목록", "내 활동", "채팅", "거래 내역", "정산", "영수증 인증", "도움말",
    ]);
    await user.tab({ shift: true });
    expect(document.activeElement).toBe(within(dialog).getByRole("link", { name: "도움말" }));
    await user.tab();
    expect(document.activeElement).toBe(close);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(trigger);
    expect(document.body.style.overflow).toBe("");
  });

  it("채팅을 선택하면 기존 라우트로 이동하고 메뉴를 닫는다", async () => {
    const user = userEvent.setup();
    render(<AppLayout><h1>본문</h1></AppLayout>);
    await user.click(screen.getByRole("button", { name: "전체 메뉴 열기" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("link", { name: "채팅" }));
    await waitFor(() => expect(location.hash).toBe("#/Chat_List"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("공개 화면 목록에서 관리자 메뉴를 노출하지 않는다", () => {
    render(<Screen page="Index" q={new URLSearchParams()} />);
    expect(screen.getByRole("link", { name: "Help" })).not.toBeNull();
    expect(screen.queryByRole("link", { name: /Admin_/ })).toBeNull();
  });
});

describe("채팅 전송", () => {
  it("전송 중 네트워크 오류가 나면 초안과 이해 가능한 오류를 유지한다", async () => {
    localStorage.setItem("nf_token", "synthetic-test-token");
    localStorage.setItem("nf_userId", "1");
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(input instanceof Request ? input.url : input.toString(), window.location.href).pathname;
      if (path === "/api/chats/8/messages" && init?.method === "POST") throw new TypeError("Failed to fetch");
      const data = path === "/api/chats"
        ? { items: [{ id: 8, kind: "direct", post_id: 12, post_title: "가상 게시글", partnerNickname: "이웃" }] }
        : path === "/posts/12"
          ? { id: 12, title: "가상 게시글" }
          : path === "/api/chats/8/messages"
            ? { items: [{ id: 1, sender_id: 2, content: "기존 대화", created_at: "2026-10-29T00:00:00Z" }] }
            : null;
      if (!data) throw new Error(`Unexpected request: ${path}`);
      return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
    }));
    const user = userEvent.setup();
    render(<Chat q={new URLSearchParams("id=8")} />);
    await screen.findByText("기존 대화");
    const draft = screen.getByRole("textbox", { name: "메시지" }) as HTMLTextAreaElement;
    await user.type(draft, "지워지면 안 되는 초안");
    await user.click(screen.getByRole("button", { name: "전송" }));
    await screen.findByRole("alert");
    expect(draft.value).toBe("지워지면 안 되는 초안");
    expect(draft.disabled).toBe(false);
  });

  it("초기 연결 실패 후 다시 불러오면 메시지와 대화 정보를 함께 복구한다", async () => {
    localStorage.setItem("nf_token", "synthetic-test-token");
    localStorage.setItem("nf_userId", "1");
    let offline = true;
    const failed = new Set<string>();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(input instanceof Request ? input.url : input.toString(), window.location.href).pathname;
      if (offline) {
        failed.add(path);
        throw new TypeError("Failed to fetch");
      }
      const data = path === "/api/chats"
        ? { items: [{ id: 8, kind: "direct", post_id: 12, post_title: "가상 게시글", partnerNickname: "이웃" }] }
        : path === "/posts/12"
          ? { id: 12, title: "가상 게시글" }
          : path === "/api/chats/8/messages"
            ? { items: [{ id: 1, sender_id: 2, content: "복구된 대화", created_at: "2026-10-29T00:00:00Z" }] }
            : null;
      if (!data) throw new Error(`Unexpected request: ${path}`);
      return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
    }));
    const user = userEvent.setup();
    render(<Chat q={new URLSearchParams("id=8")} />);
    const retry = await screen.findByRole("button", { name: "대화 다시 불러오기" });
    await waitFor(() => expect(failed.has("/api/chats")).toBe(true));
    offline = false;
    await user.click(retry);
    await screen.findByText("복구된 대화");
    expect(await screen.findByRole("link", { name: "가상 게시글" })).not.toBeNull();
  });
});

describe("서버 상태에 따른 거래·장소 화면", () => {
  it("게시글을 지정하지 않은 거래 장소 화면은 가짜 가격 대신 선택 안내를 표시한다", () => {
    render(<MapPage q={new URLSearchParams()} detail />);
    expect(screen.getByRole("status")).not.toBeNull();
    expect(screen.queryByText("0원")).toBeNull();
  });

  it.each([false, true])("정산 GPS 인증이 %s일 때 QR 접근 가능 상태를 표시한다", async (verified) => {
    localStorage.setItem("nf_token", "synthetic-test-token");
    localStorage.setItem("nf_userId", "1");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      settlement: {
        id: 23, requesterId: 2, status: "pending", totalAmount: 1000,
        paidCount: 0, participantCount: 1,
        shares: [{ userId: 1, nickname: "참여자", amount: 1000, status: "unpaid",
          gpsVerified: verified, qualityAgreed: false, payable: false }],
      },
    }), { status: 200, headers: { "Content-Type": "application/json" } })));
    render(<Settlement q={new URLSearchParams("settlementId=23")} />);
    await screen.findByText("참여자");
    const qr = screen.queryByRole("link", { name: "QR 인증" });
    if (verified) {
      expect(qr).not.toBeNull();
    } else {
      expect(qr).toBeNull();
    }
    expect((screen.getByRole("button", { name: "납부 표시" }) as HTMLButtonElement).disabled).toBe(true);
  });

});
