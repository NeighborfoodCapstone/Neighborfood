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

export function AppLayout({
  children,
  page = "Home",
}: {
  children: ReactNode;
  page?: string;
}) {
  return (
    <div className="nf-app">
      <a className="nf-skip" href="#main-content">
        본문으로 이동
      </a>
      <header className="nf-header">
        <div className="nf-header-inner">
          <a href="#/Home" className="nf-brand" aria-label="Neighborfood 홈">
            <Icon name="leaf" />
            <span>
              neighborfood<span className="nf-brand-dot">.</span>
            </span>
          </a>
          <a
            className="nf-neighborhood"
            href={legacy("Neighborhood_Setting.html")}
          >
            내 동네 설정 <span aria-hidden="true">⌄</span>
          </a>
        </div>
      </header>
      <main id="main-content" className="nf-main">
        {children}
      </main>
      <nav className="nf-bottom" aria-label="주요 메뉴">
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
    </div>
  );
}
