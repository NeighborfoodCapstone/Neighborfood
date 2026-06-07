// frontend/shared/auth.js
// =====================================================================
//  NeighborFood 공통 인증 헬퍼
//  - /verify-auth 응답의 token 을 sessionStorage에 보관합니다.
//  - 이후 모든 API fetch 요청에 Authorization: Bearer <token> 를 자동 주입합니다.
//  - 사용법: 각 페이지의 <head> 또는 스크립트보다 먼저 한 줄만 추가하세요.
//        <script src="shared/auth.js"></script>
//    Verify.html 인증 성공 시:  window.nfSetToken(data.token);
//    로그아웃 시:               window.nfClearToken();  (+ POST /logout 호출)
// =====================================================================
(function () {
  "use strict";
  var KEY = "nf_token";

  window.nfSetToken   = function (t) { try { if (t) sessionStorage.setItem(KEY, t); } catch (e) {} };
  window.nfGetToken   = function ()  { try { return sessionStorage.getItem(KEY); } catch (e) { return null; } };
  window.nfClearToken = function ()  { try { sessionStorage.removeItem(KEY); } catch (e) {} };
  window.nfIsLoggedIn = function ()  { return !!window.nfGetToken(); };

  // 같은 출처/백엔드(8000) 요청에만 토큰을 붙입니다(외부 API에는 주입하지 않음).
  function isApiUrl(u) {
    if (typeof u !== "string") return false;
    if (u.charAt(0) === "/") return true;               // 상대경로(같은 출처)
    if (u.indexOf("127.0.0.1:8000") !== -1) return true; // 로컬 백엔드
    if (u.indexOf("localhost:8000") !== -1) return true;
    return false;
  }

  var origFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    var token = window.nfGetToken();
    if (token && isApiUrl(input)) {
      init = init || {};
      var headers = new Headers(init.headers || {});
      if (!headers.has("Authorization")) {
        headers.set("Authorization", "Bearer " + token);
      }
      init.headers = headers;
    }
    return origFetch(input, init);
  };
})();