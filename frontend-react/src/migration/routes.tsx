import type { ReactNode } from "react";
import {
  AuthPage,
  PasswordReset,
  Profile,
  EditProfile,
  Withdraw,
} from "./auth";
import {
  Search,
  Wishlist,
  Detail,
  CreatePost,
  Reservation,
  Report,
} from "./posts";
import { Chats, Chat, Activity, Settlement } from "./trades";
import { Fridge } from "./fridge";
import { MapPage, Neighborhood, LocationVerify } from "./location";
import { Receipt } from "./receipt";
import { QR } from "./qr";
import {
  Dashboard,
  AdminUsers,
  Notices,
  AdminReport,
  AdminChats,
} from "./admin";
import { Page, href, token, useData, Load } from "./core";
export const screens = [
  "Home",
  "Index",
  "Splash",
  "Onboarding",
  "Login",
  "Signup",
  "Password_Reset",
  "Verify",
  "My_Page",
  "Edit_Profile",
  "Withdraw",
  "Search",
  "Search_Results",
  "Wishlist",
  "Product_Detail",
  "Group_Buy_Detail",
  "Create_Post",
  "Reservation",
  "Report",
  "Chat_List",
  "Chat_Detail",
  "Group_Chat",
  "My_Activity",
  "Transaction_History",
  "Settlement",
  "Fridge",
  "Map",
  "Neighborhood_Setting",
  "Location_Detail",
  "Local_Verify_Demo",
  "Receipt_Verify",
  "QR_Scan",
  "Help",
  "Admin_Dashboard",
  "Admin_Users",
  "Admin_Notices",
  "Admin_Report_Detail",
  "Admin_Chat_History",
  "Admin_Staff_Invite",
];
const publicScreens = new Set([
  "Home",
  "Index",
  "Splash",
  "Onboarding",
  "Login",
  "Signup",
  "Password_Reset",
  "Verify",
  "Search",
  "Search_Results",
  "Product_Detail",
  "Group_Buy_Detail",
  "Map",
  "Location_Detail",
  "Help",
]);
export function Guard({
  page,
  children,
}: {
  page: string;
  children: ReactNode;
}) {
  if (!publicScreens.has(page) && !token())
    return (
      <Page title="로그인이 필요합니다">
        <a
          className="rx-primary"
          href={href("Login", { next: location.hash.slice(2) })}
        >
          로그인
        </a>
      </Page>
    );
  if (page.startsWith("Admin_")) return <AdminGuard>{children}</AdminGuard>;
  return <>{children}</>;
}
function AdminGuard({ children }: { children: ReactNode }) {
  const s = useData("/api/users/me");
  return (
    <Load state={s}>
      {s.data?.role === "admin"
        ? children
        : s.data && (
            <Page title="접근 권한 없음">
              <p>관리자만 이용할 수 있습니다.</p>
              <a href={href("Home")}>홈으로</a>
            </Page>
          )}
    </Load>
  );
}
function Help() {
  return (
    <Page title="도움말">
      {[
        [
          "식재료를 나누려면?",
          "식재료 등록에서 나눔·교환·공동구매 유형을 선택하고 내용을 입력합니다.",
        ],
        [
          "거래 장소는 어떻게 정하나요?",
          "채팅으로 약속을 정하고 지도에서 장소를 확인합니다. 정산 거래는 주최자가 약속 좌표를 등록해야 GPS 인증을 진행할 수 있습니다.",
        ],
        [
          "문제가 있는 게시글은?",
          "게시글 상세의 신고 기능에서 사유를 작성해 접수할 수 있습니다.",
        ],
        [
          "영수증 인식이 잘못됐어요.",
          "영수증 분석 후 품목·수량·금액을 수정하고 선택 항목을 인증할 수 있습니다.",
        ],
        [
          "납부 표시가 실제 결제인가요?",
          "현재 정산의 납부 표시는 사용자가 입금 사실을 표시하는 기능입니다. 결제 대행사의 결제 승인 기능과는 다릅니다.",
        ],
      ].map(([q, a]) => (
        <details key={q}>
          <summary>{q}</summary>
          <p>{a}</p>
        </details>
      ))}
    </Page>
  );
}
export function Screen({ page, q }: { page: string; q: URLSearchParams }) {
  switch (page) {
    case "Login":
      return <AuthPage />;
    case "Signup":
      return <AuthPage signup />;
    case "Password_Reset":
    case "Verify":
      return <PasswordReset />;
    case "My_Page":
      return <Profile />;
    case "Edit_Profile":
      return <EditProfile />;
    case "Withdraw":
      return <Withdraw />;
    case "Search":
    case "Search_Results":
      return <Search q={q} />;
    case "Wishlist":
      return <Wishlist />;
    case "Product_Detail":
    case "Group_Buy_Detail":
      return <Detail q={q} />;
    case "Create_Post":
      return <CreatePost q={q} />;
    case "Reservation":
      return <Reservation q={q} />;
    case "Report":
      return <Report q={q} />;
    case "Chat_List":
      return <Chats />;
    case "Chat_Detail":
      return <Chat q={q} />;
    case "Group_Chat":
      return <Chat q={q} group />;
    case "My_Activity":
      return <Activity />;
    case "Transaction_History":
      return <Activity history />;
    case "Settlement":
      return <Settlement q={q} />;
    case "Fridge":
      return <Fridge />;
    case "Map":
      return <MapPage q={q} />;
    case "Location_Detail":
      return <MapPage q={q} detail />;
    case "Neighborhood_Setting":
      return <Neighborhood />;
    case "Local_Verify_Demo":
      return <LocationVerify q={q} />;
    case "Receipt_Verify":
      return <Receipt />;
    case "QR_Scan":
      return <QR q={q} />;
    case "Admin_Dashboard":
      return <Dashboard />;
    case "Admin_Users":
      return <AdminUsers />;
    case "Admin_Staff_Invite":
      return <AdminUsers staff />;
    case "Admin_Notices":
      return <Notices />;
    case "Admin_Report_Detail":
      return <AdminReport q={q} />;
    case "Admin_Chat_History":
      return <AdminChats />;
    case "Help":
      return <Help />;
    case "Index":
      return (
        <Page title="화면 목록">
          <div className="rx-menu">
            {screens
              .filter((p) => p !== "Index")
              .map((p) => (
                <a key={p} href={href(p)}>
                  {p}
                </a>
              ))}
          </div>
        </Page>
      );
    case "Splash":
    case "Onboarding":
      return (
        <Page title="Neighborfood">
          <div className="rx-menu">
            <a href={href("Home")}>홈 둘러보기</a>
            <a href={href("Login")}>로그인</a>
            <a href={href("Signup")}>회원가입</a>
            <a href={href("Neighborhood_Setting")}>내 동네 설정</a>
          </div>
        </Page>
      );
    default:
      return (
        <Page title="페이지를 찾을 수 없습니다">
          <a href={href("Home")}>홈으로</a>
        </Page>
      );
  }
}
