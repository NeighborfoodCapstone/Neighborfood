/* guard.js — 회원 전용 페이지 보조 가드
 * auth.js(필수)가 nfRequireMember·nfIsLoggedIn·nfLogout 등을 이미 제공합니다.
 * 이 파일은 auth.js가 없을 때를 대비한 폴백과, 401 처리 헬퍼만 보강합니다.
 * 사용: <script src="shared/auth.js"></script>
 *       <script src="shared/guard.js"></script>
 *       <script>nfRequireMember();</script>
 */
(function () {
  'use strict';

  // auth.js가 이미 정의했다면 절대 덮어쓰지 않음 (중복 정의 충돌 방지)
  if (typeof window.nfIsLoggedIn !== 'function') {
    window.nfIsLoggedIn = function () {
      try { return !!localStorage.getItem('nf_token'); } catch (e) { return false; }
    };
  }
  if (typeof window.nfRequireMember !== 'function') {
    window.nfRequireMember = function (loginPage) {
      if (window.nfIsLoggedIn()) return true;
      var here = location.pathname.split('/').pop() + location.search;
      location.replace((loginPage || 'Login.html') + '?next=' + encodeURIComponent(here));
      return false;
    };
  }

  // 서버가 401(만료/무효)을 주면 토큰 정리 후 로그인으로 — auth.js엔 없는 헬퍼
  window.nfHandleAuthError = function (res) {
    if (res && res.status === 401) {
      if (typeof window.nfClearToken === 'function') window.nfClearToken();
      else { try { localStorage.removeItem('nf_token'); } catch (e) {} }
      window.nfRequireMember();
      return true;
    }
    return false;
  };
})();
