import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Icon } from "./Icon";
import type { IconName } from "./Icon";
import { legacy } from "./api";

const links: { label: string; icon: IconName; page: string }[] = [
  { label: "홈", icon: "home", page: "" },
  { label: "지도", icon: "map", page: "Map.html" },
  { label: "등록", icon: "plus", page: "Create_Post.html" },
  { label: "내 활동", icon: "activity", page: "My_Activity.html" },
  { label: "마이", icon: "user", page: "My_Page.html" },
];

const menuLinks = [
  ["Fridge", "내 냉장고"],
  ["Wishlist", "찜 목록"],
  ["My_Activity", "내 활동"],
  ["Chat_List", "채팅"],
  ["Transaction_History", "거래 내역"],
  ["Settlement", "정산"],
  ["Receipt_Verify", "영수증 인증"],
  ["Help", "도움말"],
];

export function AppLayout({
  children,
  page = "Home",
}: {
  children: ReactNode;
  page?: string;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  const close = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const previousOverflow = document.body.style.overflow;
    const opener = trigger.current;
    document.body.style.overflow = "hidden";
    close.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMenuOpen(false);
      } else if (event.key === "Tab") {
        const items = panel.current?.querySelectorAll<HTMLElement>("a[href], button:not([disabled])");
        if (!items?.length) return;
        const first = items[0], last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    const onNavigate = () => setMenuOpen(false);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("hashchange", onNavigate);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("hashchange", onNavigate);
      if (opener?.isConnected) opener.focus();
    };
  }, [menuOpen]);
  return (
    <div className="nf-app">
      <a className="nf-skip" href="#main-content" inert={menuOpen || undefined}>
        본문으로 이동
      </a>
      <header className="nf-header" inert={menuOpen || undefined}>
        <div className="nf-header-inner">
          <a href="#/Home" className="nf-brand" aria-label="Neighborfood 홈">
            <Icon name="leaf" />
            <span>
              neighborfood<span className="nf-brand-dot">.</span>
            </span>
          </a>
          <button
            ref={trigger}
            type="button"
            className="nf-neighborhood nf-menu-trigger"
            aria-label="전체 메뉴 열기"
            aria-expanded={menuOpen}
            aria-controls="nf-side-menu"
            onClick={() => setMenuOpen(true)}
          >
            전체 메뉴 <span aria-hidden="true">☰</span>
          </button>
        </div>
      </header>
      <main id="main-content" className="nf-main" inert={menuOpen || undefined}>
        {children}
      </main>
      <nav className="nf-bottom" aria-label="주요 메뉴" inert={menuOpen || undefined}>
        <div className="nf-bottom-inner">
          {links.map((link) => (
            <a
              key={link.label}
              href={link.page ? legacy(link.page) : "#/Home"}
              aria-current={
                (
                  link.page
                    ? page === link.page.replace(".html", "")
                    : page === "Home"
                )
                  ? "page"
                  : undefined
              }
            >
              <Icon name={link.icon} />
              <span>{link.label}</span>
            </a>
          ))}
        </div>
      </nav>
      {menuOpen && (
        <div className="nf-drawer">
          <button type="button" className="nf-drawer-backdrop" tabIndex={-1}
            aria-hidden="true" onClick={() => setMenuOpen(false)} />
          <aside id="nf-side-menu" ref={panel} className="nf-drawer-panel"
            role="dialog" aria-modal="true" aria-labelledby="nf-menu-title">
            <div className="nf-drawer-header">
              <h2 id="nf-menu-title">전체 메뉴</h2>
              <button ref={close} type="button" className="nf-drawer-close"
                aria-label="메뉴 닫기" onClick={() => setMenuOpen(false)}>×</button>
            </div>
            <p className="nf-drawer-hint">로그인이 필요한 메뉴는 로그인 후 이용할 수 있습니다.</p>
            <nav className="nf-drawer-links" aria-label="전체 메뉴">
              {menuLinks.map(([route, label]) => (
                <a key={route} href={legacy(route + ".html")} onClick={() => setMenuOpen(false)}>
                  <span>{label}</span><span aria-hidden="true">›</span>
                </a>
              ))}
            </nav>
          </aside>
        </div>
      )}
    </div>
  );
}
