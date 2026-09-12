/* NeighborFood 관리자 페이지 공용 가드 — frontend/shared/adminGuard.js
 * 6개 Admin_*.html 에 중복되어 있던 아래 로직을 하나로 통합한 것입니다:
 *   1) /api/users/me 로 로그인 여부 확인
 *   2) role !== 'admin' 이면 접근 차단
 *   3) 사이드바의 관리자 이름(#adminName, #adminGreet)·신고 배지(#navReportBadge)
 *      요소가 있으면 실데이터로 채움 (없는 페이지는 조용히 건너뜀 — 예: Admin_Report_Detail.html)
 *
 * 로드 순서 (반드시 이 순서):
 *   <script src="shared/auth.js"></script>
 *   <script src="shared/adminGuard.js"></script>
 *
 * 사용법 (각 페이지 하단 스크립트에서):
 *   (async function () {
 *     const me = await nfRequireAdmin('Admin_Users.html');
 *     if (!me) return;                 // 가드가 이미 리다이렉트 처리함
 *     // ... 이 페이지만의 데이터 로딩 로직 ...
 *   })();
 *
 * 반환값: 통과 시 사용자 객체(me), 실패(리다이렉트) 시 null.
 */
(function () {
  "use strict";

  async function nfRequireAdmin(pageFile) {
    var API  = window.location.origin;
    var here = pageFile || (location.pathname.split("/").pop() || "Home.html");

    var me = null;
    try {
      var res = await fetch(API + "/api/users/me");
      if (res.ok) me = await res.json();
      else if (typeof window.nfHandleAuthError === "function") window.nfHandleAuthError(res);
    } catch (e) {
      /* 네트워크 오류는 비로그인과 동일하게 처리 */
    }

    if (!me) {
      location.replace("Login.html?next=" + encodeURIComponent(here));
      return null;
    }
    if (me.role !== "admin") {
      alert("관리자만 접근할 수 있어요.");
      location.replace("Home.html");
      return null;
    }

    // 사이드바 요소 자동 채움 (요소가 없는 페이지는 getElementById가 null을 반환하므로 안전하게 무시됨)
    var nameEl = document.getElementById("adminName");
    if (nameEl) nameEl.textContent = me.nickname || "관리자";
    var greetEl = document.getElementById("adminGreet");
    if (greetEl) greetEl.textContent = me.nickname || "관리자";

    var badgeEl = document.getElementById("navReportBadge");
    if (badgeEl) {
      try {
        var d = await fetch(API + "/api/admin/dashboard").then(function (r) {
          return r.ok ? r.json() : null;
        });
        if (d && typeof d.reportsPending !== "undefined") {
          badgeEl.textContent = d.reportsPending;
        }
      } catch (e) {
        /* 배지 갱신 실패는 가드 통과 자체에 영향을 주지 않음 */
      }
    }

    return me;
  }

  window.nfRequireAdmin = nfRequireAdmin;
})();