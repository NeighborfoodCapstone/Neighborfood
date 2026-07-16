/* NeighborFood 공통 인증 유틸 — frontend/shared/auth.js
 * 모든 페이지에서 <script src="shared/auth.js"></script> 로 로드합니다.
 * 제공 함수: nfSetToken, nfGetToken, nfClearToken, nfIsLoggedIn,
 *            nfLogout, nfHandleAuthError
 * 부가 기능: window.fetch 를 감싸 동일 출처 요청에 Authorization 자동 주입
 * (회원 전용 페이지 가드 nfRequireMember 는 shared/guard.js 담당)
 */
(function () {
  "use strict";

  var TOKEN_KEY  = "nf_token";   // localStorage 키 (페이지에서 직접 참조하지 않음)
  var LOGIN_PAGE = "Login.html";

  // ── 토큰 보관소 ─────────────────────────────────────────────────────────
  function nfSetToken(token) {
    if (token) { try { localStorage.setItem(TOKEN_KEY, token); } catch (e) {} }
  }
  function nfGetToken() {
    try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; }
  }
  function nfClearToken() {
    try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}
  }
  function nfIsLoggedIn() {
    return !!nfGetToken();
  }

  // ── 로그아웃 ────────────────────────────────────────────────────────────
  // 서버 세션을 폐기한 뒤 토큰을 지우고 redirectTo 로 이동합니다.
  // 서버 호출 성공 여부와 무관하게 클라이언트 토큰은 항상 제거합니다.
  function nfLogout(redirectTo) {
    var dest = redirectTo || "Home.html";
    var done = function () { nfClearToken(); window.location.href = dest; };
    if (!nfGetToken()) { done(); return; }
    // 아래 fetch 래퍼가 Authorization 을 자동 주입합니다.
    fetch("/logout", { method: "POST" }).then(done).catch(done);
  }

  // ── 401/403 처리 ────────────────────────────────────────────────────────
  // 인증 오류 응답이면 토큰을 비우고 로그인 페이지로 이동합니다.
  // 사용법:  const r = await fetch(...); if (nfHandleAuthError(r)) return;
  function nfHandleAuthError(response) {
    if (!response || (response.status !== 401 && response.status !== 403)) return false;
    nfClearToken();
    var here = (window.location.pathname.split("/").pop() || "Home.html");
    var next = encodeURIComponent(here + window.location.search);
    window.location.href = LOGIN_PAGE + "?next=" + next;
    return true;
  }

  // ── fetch 자동 Authorization 주입 ──────────────────────────────────────
  // 동일 출처(또는 상대경로) 요청에만 토큰을 붙입니다. 외부 API(openfoodfacts 등)나
  // 이미 Authorization 이 설정된 요청은 변경하지 않습니다.
  var _origFetch = window.fetch ? window.fetch.bind(window) : null;
  if (_origFetch) {
    window.fetch = function (input, init) {
      init = init || {};
      try {
        var url = (typeof input === "string") ? input : (input && input.url) || "";
        var sameOrigin = true;
        if (/^https?:\/\//i.test(url)) {
          sameOrigin = (new URL(url).origin === window.location.origin);
        }
        var token = nfGetToken();
        if (token && sameOrigin) {
          var srcHeaders = init.headers ||
                           (typeof input !== "string" && input ? input.headers : null) || {};
          var headers = new Headers(srcHeaders);
          if (!headers.has("Authorization")) {
            headers.set("Authorization", "Bearer " + token);
            init.headers = headers;
          }
        }
      } catch (e) { /* 주입 실패해도 원본 요청은 그대로 진행 */ }
      return _origFetch(input, init);
    };
  }

  // ── 전역 노출 ───────────────────────────────────────────────────────────
  window.nfSetToken        = nfSetToken;
  window.nfGetToken        = nfGetToken;
  window.nfClearToken      = nfClearToken;
  window.nfIsLoggedIn      = nfIsLoggedIn;
  window.nfLogout          = nfLogout;
  window.nfHandleAuthError = nfHandleAuthError;
})();
