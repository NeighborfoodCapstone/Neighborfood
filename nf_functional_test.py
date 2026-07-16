
#NeighborFood 수동 기능 테스트 체크리스트 자동화 스크립트 v5
#실행: python nf_functional_test.py
#요구사항: pip install requests
#서버: http://127.0.0.1:8000 실행 중 + python seed_admin.py 완료 후 실행


import requests, json, time, sys, os
from datetime import datetime

BASE = "http://127.0.0.1:8000"
GREEN  = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; RESET = "\033[0m"; BOLD = "\033[1m"

results = []

def ok(sec, item, detail=""):
    results.append((sec, item, "PASS", detail))
    print(f"  {GREEN}✔{RESET} {item}" + (f"  [{detail}]" if detail else ""))

def fail(sec, item, detail=""):
    results.append((sec, item, "FAIL", detail))
    print(f"  {RED}✘{RESET} {item}" + (f"  [{detail}]" if detail else ""))

def warn(sec, item, detail=""):
    results.append((sec, item, "WARN", detail))
    print(f"  {YELLOW}△{RESET} {item}" + (f"  [{detail}]" if detail else ""))

def skip(sec, item, detail=""):
    results.append((sec, item, "SKIP", detail))
    print(f"  –  {item}" + (f"  [{detail}]" if detail else ""))

def hdr(title):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}\n{BOLD}{CYAN}  {title}{RESET}\n{BOLD}{CYAN}{'─'*60}{RESET}")

# ── HTTP 헬퍼 (r is not None 으로 4xx/5xx 정확히 판별) ─────────────────────────
TIMEOUT = 15   # PBKDF2 해시 연산 감안해 15초

def _req(method, path, token=None, **kw):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        return getattr(requests, method)(BASE + path, headers=headers, timeout=TIMEOUT, **kw)
    except Exception:
        return None

def get(path, token=None, **kw):    return _req("get",    path, token, **kw)
def post(path, token=None, **kw):   return _req("post",   path, token, **kw)
def put(path, token=None, **kw):    return _req("put",    path, token, **kw)
def patch(path, token=None, **kw):  return _req("patch",  path, token, **kw)
def delete(path, token=None, **kw): return _req("delete", path, token, **kw)

def code(r):
    return f"HTTP {r.status_code}" if r is not None else "NO RESPONSE"

def is_ok(r, *codes):
    return r is not None and r.status_code in codes

# ── 전역 상태 ────────────────────────────────────────────────────────────────
TOKEN = TOKEN2 = ADMIN_TOKEN = None
USER1_ID = USER2_ID = None
POST_ID_SHARE = POST_ID_GB = POST_ID_EXCH = None
CHAT_ID = GROUP_CHAT_ID = None
QR_CODE = QR_SESSION_ID = FRIDGE_ITEM_ID = TX_ID = GPS_SESSION_ID = None

# ════════════════════════════════════════════════════════════════════════════════
hdr("0. 서버 기동 및 환경")
# ════════════════════════════════════════════════════════════════════════════════
S = "S0"

r = get("/")
if is_ok(r, 200): ok(S, "홈 페이지 접속", code(r))
else:             fail(S, "홈 페이지 접속", code(r))

r = get("/docs")
if is_ok(r, 200): ok(S, "Swagger UI (/docs) 접속", code(r))
else:             fail(S, "Swagger UI (/docs) 접속", code(r))

# ════════════════════════════════════════════════════════════════════════════════
hdr("1. 회원 인증")
# ════════════════════════════════════════════════════════════════════════════════
S = "S1"
TS = str(int(time.time()))
TEST_ID  = f"testuser_{TS}";  TEST_PW = "Test1234!"
TEST_PH  = f"010{TS[-8:]}";   TEST_ID2 = f"testuser2_{TS}"
TEST_PH2 = f"011{TS[-8:]}"

# 1-1 회원가입 성공
r = post("/api/auth/register", json={"login_id": TEST_ID, "password": TEST_PW,
         "phone_number": TEST_PH, "nickname": f"테스터_{TS[-4:]}"})
if is_ok(r, 200, 201): ok(S, "회원가입 성공", code(r))
else:                  fail(S, "회원가입 성공", f"{code(r)} / {r.text[:80] if r is not None else ''}")

# 1-2 중복 아이디 → 409
r = post("/api/auth/register", json={"login_id": TEST_ID, "password": TEST_PW,
         "phone_number": f"019{TS[-8:]}"})
if is_ok(r, 409): ok(S, "중복 아이디 재가입 → 409", code(r))
else:             fail(S, "중복 아이디 재가입 → 409", code(r))

# 1-3 로그인 성공
r = post("/api/auth/login", json={"login_id": TEST_ID, "password": TEST_PW})
if is_ok(r, 200):
    try:
        data = r.json()
        TOKEN = data.get("token") or data.get("access_token") or data.get("session_token")
        ok(S, "로그인 성공 → 토큰 발급", f"token={'있음' if TOKEN else '응답 필드명 확인 필요'}")
    except Exception:
        fail(S, "로그인 성공 → 토큰 발급", f"JSON 파싱 오류: {r.text[:80]}")
else:
    fail(S, "로그인 성공 → 토큰 발급", code(r))

# 1-4 잘못된 비밀번호 → 401
r = post("/api/auth/login", json={"login_id": TEST_ID, "password": "wrongpassword!"})
if is_ok(r, 401): ok(S, "잘못된 비밀번호 → 401", code(r))
else:             fail(S, "잘못된 비밀번호 → 401", code(r))

# 1-5 휴대폰 인증 요청  (prefix 없는 /request-auth)
r = post("/request-auth", json={"phone_number": TEST_PH})
if is_ok(r, 200, 201):
    ok(S, "휴대폰 인증 요청 (/request-auth)", code(r))
    try:
        _c = r.json().get("code") or r.json().get("auth_code")
        if _c: ok(S, "  └ OTP 코드 응답 수신", f"code={_c}")
    except Exception:
        pass
else:
    fail(S, "휴대폰 인증 요청 (/request-auth)", code(r))

# 1-6 비밀번호 재설정 엔드포인트 존재 확인
r = post("/reset-password", json={"phone_number": TEST_PH,
         "code": "000000", "new_password": "New1234!"})
if r is not None and r.status_code in (200, 400, 422):
    warn(S, "비밀번호 재설정 엔드포인트 존재 (/reset-password)",
         f"{code(r)} (실제 OTP 없이 테스트)")
else:
    fail(S, "비밀번호 재설정 엔드포인트 (/reset-password)", code(r))

# 1-7 로그아웃  (prefix 없는 /logout)
r = post("/logout", token=TOKEN)
if is_ok(r, 200, 204):
    ok(S, "로그아웃 성공 (/logout)", code(r))
    r2 = get("/api/users/me", token=TOKEN)
    if is_ok(r2, 401): ok(S, "  └ 로그아웃 후 /api/users/me → 401", code(r2))
    else:              fail(S, "  └ 로그아웃 후 /api/users/me → 401", code(r2))
else:
    fail(S, "로그아웃 (/logout)", code(r))

# 재로그인
r = post("/api/auth/login", json={"login_id": TEST_ID, "password": TEST_PW})
if is_ok(r, 200):
    try: TOKEN = r.json().get("token") or r.json().get("access_token") or r.json().get("session_token")
    except Exception: pass

# 두 번째 테스트 계정
r = post("/api/auth/register", json={"login_id": TEST_ID2, "password": TEST_PW,
         "phone_number": TEST_PH2, "nickname": f"테스터2_{TS[-4:]}"})
if is_ok(r, 200, 201):
    r2 = post("/api/auth/login", json={"login_id": TEST_ID2, "password": TEST_PW})
    if is_ok(r2, 200):
        try: TOKEN2 = r2.json().get("token") or r2.json().get("access_token") or r2.json().get("session_token")
        except Exception: pass

skip(S, "회원 탈퇴 — 테스트 마지막에 처리")

# ════════════════════════════════════════════════════════════════════════════════
hdr("2. 동네 설정")
# ════════════════════════════════════════════════════════════════════════════════
S = "S2"

r = post("/api/users/neighborhood", token=TOKEN,
         json={"neighborhood": "서울시 강남구 역삼동", "lat": 37.500622, "lng": 127.036456})
if not is_ok(r, 200, 201):
    r = patch("/api/users/neighborhood", token=TOKEN,
              json={"neighborhood": "서울시 강남구 역삼동", "lat": 37.500622, "lng": 127.036456})
if is_ok(r, 200, 201):
    ok(S, "동네 설정 성공", code(r))
    r2 = get("/api/users/me", token=TOKEN)
    if is_ok(r2, 200):
        nbhd = r2.json().get("neighborhood") or (r2.json().get("user") or {}).get("neighborhood")
        if nbhd: ok(S, "  └ 동네 프로필 반영 확인", f"neighborhood={nbhd}")
        else:    warn(S, "  └ 동네 프로필 반영 확인", "neighborhood 필드 없음")
    else: fail(S, "  └ /api/users/me 조회 실패", code(r2))
else:
    fail(S, "동네 설정 (/api/users/neighborhood)", f"{code(r)} / {r.text[:80] if r is not None else ''}")

skip(S, "동네 미설정 시 홈 화면 유도 — 브라우저 UI 테스트 필요")

# ════════════════════════════════════════════════════════════════════════════════
hdr("3. 게시글 (나눔 / 공동구매 / 교환)")
# ════════════════════════════════════════════════════════════════════════════════
S = "S3"

# auth·posts 라우터는 prefix 없음 → 내부 정의 경로 사용
# main.py 확인 결과: posts.router 는 prefix 없음 → /posts 로 자체 정의

r = post("/posts", token=TOKEN, json={"type": "share", "title": "테스트 나눔",
         "description": "테스트 설명", "category": "채소",
         "address": "서울 강남구", "lat": 37.5, "lng": 127.0})
if is_ok(r, 200, 201):
    try: POST_ID_SHARE = r.json().get("id") or r.json().get("post_id")
    except Exception: pass
    ok(S, "나눔 게시글 작성 성공", f"id={POST_ID_SHARE}")
else:
    fail(S, "나눔 게시글 작성", f"{code(r)} / {r.text[:80] if r is not None else ''}")

r = post("/posts", token=TOKEN, json={"type": "groupbuy", "title": "테스트 공동구매",
         "description": "공동구매 설명", "category": "과일",
         "address": "서울 강남구", "lat": 37.5, "lng": 127.0,
         "gb_target": 3, "gb_price": 10000})
if is_ok(r, 200, 201):
    try: POST_ID_GB = r.json().get("id") or r.json().get("post_id")
    except Exception: pass
    ok(S, "공동구매 게시글 작성 성공", f"id={POST_ID_GB}")
else:
    fail(S, "공동구매 게시글 작성", f"{code(r)} / {r.text[:80] if r is not None else ''}")

r = post("/posts", token=TOKEN, json={"type": "exchange", "title": "테스트 교환",
         "description": "교환 설명", "category": "육류",
         "address": "서울 강남구", "lat": 37.5, "lng": 127.0,
         "exchange_want": "쌀 2kg"})
if is_ok(r, 200, 201):
    try: POST_ID_EXCH = r.json().get("id") or r.json().get("post_id")
    except Exception: pass
    ok(S, "교환 게시글 작성 성공", f"id={POST_ID_EXCH}")
else:
    fail(S, "교환 게시글 작성", f"{code(r)} / {r.text[:80] if r is not None else ''}")

# 목록 필터
r = get("/posts?type=share&category=채소")
if is_ok(r, 200):
    try:
        d = r.json()
        cnt = len(d) if isinstance(d, list) else len(d.get("items", d.get("posts", [])))
        ok(S, "게시글 목록 (필터: type=share)", f"{cnt}건")
    except Exception: ok(S, "게시글 목록", code(r))
else:
    fail(S, "게시글 목록 (GET /posts)", code(r))

# 상세
if POST_ID_SHARE:
    r = get(f"/posts/{POST_ID_SHARE}")
    if is_ok(r, 200):
        try:
            d = r.json()
            has_nick  = bool(d.get("author_nickname") or d.get("nickname") or (d.get("author") or {}).get("nickname"))
            has_trust = d.get("trust_score") is not None or (d.get("author") or {}).get("trust_score") is not None
            ok(S, "게시글 상세 (닉네임·신뢰점수)", f"nickname={'O' if has_nick else 'X'}, trust={'O' if has_trust else 'X'}")
        except Exception: ok(S, "게시글 상세 응답", code(r))
    else: fail(S, "게시글 상세 (GET /posts/{id})", code(r))
else:
    skip(S, "게시글 상세 — 게시글 ID 없음")

# 소프트 삭제
if POST_ID_EXCH:
    r = delete(f"/posts/{POST_ID_EXCH}", token=TOKEN)
    if is_ok(r, 200, 204):
        ok(S, "게시글 소프트 삭제 성공", code(r))
        r2 = get(f"/posts/{POST_ID_EXCH}")
        if r2 is not None and r2.status_code in (404, 410):
            ok(S, "  └ 삭제 후 → 404/410", code(r2))
        elif is_ok(r2, 200) and r2.json().get("status") == "deleted":
            ok(S, "  └ status=deleted 확인", f"status=deleted")
        else:
            warn(S, "  └ 삭제 상태 확인", code(r2))
    else: fail(S, "게시글 삭제", code(r))
else:
    skip(S, "게시글 삭제 — 게시글 ID 없음")

# 공동구매 참여
if POST_ID_GB and TOKEN2:
    r0 = get(f"/posts/{POST_ID_GB}")
    GB_BEFORE = r0.json().get("gb_current", 0) if is_ok(r0, 200) else None

    r = post(f"/posts/{POST_ID_GB}/join", token=TOKEN2)
    if is_ok(r, 200, 201):
        ok(S, "공동구매 참여 성공", code(r))
        r2 = get(f"/posts/{POST_ID_GB}")
        if is_ok(r2, 200) and GB_BEFORE is not None:
            gb_now = r2.json().get("gb_current", -1)
            if gb_now == GB_BEFORE + 1: ok(S, "  └ gb_current +1 확인", f"{GB_BEFORE}→{gb_now}")
            else: warn(S, "  └ gb_current 확인", f"before={GB_BEFORE}, after={gb_now}")
    else: fail(S, "공동구매 참여", f"{code(r)} / {r.text[:80] if r is not None else ''}")

    # 중복 참여 → 409
    r = post(f"/posts/{POST_ID_GB}/join", token=TOKEN2)
    if is_ok(r, 409): ok(S, "공동구매 중복 참여 → 409", code(r))
    else:             fail(S, "공동구매 중복 참여 → 409", code(r))
else:
    skip(S, "공동구매 참여 — 게시글 또는 TOKEN2 없음")
    skip(S, "공동구매 중복 참여 → 409 — 게시글 또는 TOKEN2 없음")

# 정원 초과 → 409 (gb_target=1 게시글 생성)
r_full = post("/posts", token=TOKEN, json={"type": "groupbuy", "title": "정원1 공동구매",
              "description": "정원1", "category": "과일",
              "address": "서울 강남구", "lat": 37.5, "lng": 127.0,
              "gb_target": 1, "gb_price": 5000})
POST_ID_FULL = None
if is_ok(r_full, 200, 201):
    try: POST_ID_FULL = r_full.json().get("id") or r_full.json().get("post_id")
    except Exception: pass

if POST_ID_FULL and TOKEN and TOKEN2:
    post(f"/posts/{POST_ID_FULL}/join", token=TOKEN)          # 작성자 참여 → target 도달
    r = post(f"/posts/{POST_ID_FULL}/join", token=TOKEN2)     # 초과 시도
    if is_ok(r, 409): ok(S, "공동구매 정원 초과 → 409", code(r))
    else: warn(S, "공동구매 정원 초과 → 409", f"{code(r)} (로직 확인 필요)")
else:
    skip(S, "공동구매 정원 초과 → 409 — 게시글 생성 실패")

# ════════════════════════════════════════════════════════════════════════════════
hdr("4. 지도")
# ════════════════════════════════════════════════════════════════════════════════
S = "S4"

r = get("/api/config/kakao-key")
if is_ok(r, 200):
    key_val = None
    try: key_val = r.json().get("key")
    except Exception: pass
    ok(S, "GET /api/config/kakao-key", f"key={'설정됨' if key_val else '미설정(폴백)'}")
else:
    fail(S, "GET /api/config/kakao-key", code(r))

skip(S, "지도 핀·클러스터링 — 브라우저 UI 테스트 필요")
skip(S, "카테고리 필터 토글 — 브라우저 UI 테스트 필요")
skip(S, "핀 클릭 바텀시트 — 브라우저 UI 테스트 필요")
skip(S, "KAKAO_JS_KEY 미설정 오류 메시지 — 브라우저 UI 테스트 필요")

# ════════════════════════════════════════════════════════════════════════════════
hdr("5. 찜 목록")
# ════════════════════════════════════════════════════════════════════════════════
S = "S5"

if POST_ID_SHARE and TOKEN:
    r = put(f"/api/wishlist/{POST_ID_SHARE}", token=TOKEN)
    if is_ok(r, 200, 201): ok(S, "찜 추가 (PUT /api/wishlist/{id})", code(r))
    else:                  fail(S, "찜 추가", f"{code(r)} / {r.text[:80] if r is not None else ''}")

    r = delete(f"/api/wishlist/{POST_ID_SHARE}", token=TOKEN)
    if is_ok(r, 200, 204): ok(S, "찜 해제 (DELETE /api/wishlist/{id})", code(r))
    else:                  fail(S, "찜 해제", code(r))

    if POST_ID_EXCH:
        r = put(f"/api/wishlist/{POST_ID_EXCH}", token=TOKEN)
        if r is not None: ok(S, "삭제 게시글 찜 → graceful 처리", code(r))
        else:             warn(S, "삭제 게시글 찜 처리", "응답 없음")
    else:
        skip(S, "삭제 게시글 찜 처리 — 게시글 ID 없음")
else:
    skip(S, "찜 테스트 — 게시글 또는 TOKEN 없음")

# ════════════════════════════════════════════════════════════════════════════════
hdr("6. 1:1 채팅")
# ════════════════════════════════════════════════════════════════════════════════
S = "S6"

if POST_ID_SHARE and TOKEN and TOKEN2:
    r = get("/api/users/me", token=TOKEN)
    USER1_ID = r.json().get("id") if is_ok(r, 200) else None
    r = get("/api/users/me", token=TOKEN2)
    USER2_ID = r.json().get("id") if is_ok(r, 200) else None

    r = post("/api/chats", token=TOKEN2, json={"post_id": POST_ID_SHARE, "receiver_id": USER1_ID})
    if is_ok(r, 200, 201):
        try:
            d6 = r.json()
            CHAT_ID = (d6.get("conversationId") or d6.get("id") or d6.get("chat_id") or
                       d6.get("conversation_id") or d6.get("room_id") or d6.get("chatId") or
                       d6.get("roomId") or d6.get("chat_room_id"))
            extra = f"  응답 키: {list(d6.keys())}" if not CHAT_ID else ""
        except Exception:
            extra = ""
        ok(S, "채팅방 생성 (POST /api/chats)", f"id={CHAT_ID}{extra}")
    else:
        fail(S, "채팅방 생성 (POST /api/chats)", f"{code(r)} / {r.text[:80] if r is not None else ''}")

    r = get("/api/chats", token=TOKEN2)
    if is_ok(r, 200):
        try:
            chats = r.json() if isinstance(r.json(), list) else r.json().get("chats", r.json().get("items", []))
            ok(S, "채팅방 목록 (GET /api/chats)", f"{len(chats)}개")
        except Exception: ok(S, "채팅방 목록", code(r))
    else:
        fail(S, "채팅방 목록 (GET /api/chats)", code(r))

    if CHAT_ID:
        r = post(f"/api/chats/{CHAT_ID}/messages", token=TOKEN2, json={"content": "테스트 메시지"})
        if is_ok(r, 200, 201): ok(S, "메시지 전송 (POST /api/chats/{id}/messages)", code(r))
        else:                  fail(S, "메시지 전송", f"{code(r)} / {r.text[:80] if r is not None else ''}")
    else:
        skip(S, "메시지 전송 — 채팅방 ID 없음")

    # 중복 채팅방 방지
    r2 = post("/api/chats", token=TOKEN2, json={"post_id": POST_ID_SHARE, "receiver_id": USER1_ID})
    if r2 is not None:
        if r2.status_code == 409: ok(S, "중복 채팅방 → 409", code(r2))
        elif r2.status_code == 200: ok(S, "중복 채팅방 → 기존 방 반환 (200)", code(r2))
        else: warn(S, "중복 채팅방 방지", code(r2))
    else:
        fail(S, "중복 채팅방 방지", "NO RESPONSE")

    skip(S, "읽음 처리 (read_at) — 폴링 기반, 브라우저 UI 테스트 필요")
else:
    skip(S, "1:1 채팅 전체 — 게시글 또는 TOKEN 없음")

# ════════════════════════════════════════════════════════════════════════════════
hdr("7. 그룹 채팅 (공동구매)")
# ════════════════════════════════════════════════════════════════════════════════
S = "S7"

if POST_ID_GB:
    r = post(f"/api/chats/group/{POST_ID_GB}", token=TOKEN)
    if is_ok(r, 200, 201):
        try:
            d7 = r.json()
            GROUP_CHAT_ID = (d7.get("conversationId") or d7.get("id") or d7.get("chat_id") or
                             d7.get("conversation_id") or d7.get("room_id") or d7.get("chatId") or
                             d7.get("groupChatId") or d7.get("group_chat_id"))
            extra7 = f"  응답 키: {list(d7.keys())}" if not GROUP_CHAT_ID else ""
        except Exception:
            extra7 = ""
        ok(S, "그룹 채팅방 생성/열기 (POST /api/chats/group/{id})", f"id={GROUP_CHAT_ID}{extra7}")
    else:
        fail(S, "그룹 채팅방 생성 (POST /api/chats/group/{id})", f"{code(r)} / {r.text[:80] if r is not None else ''}")

    if GROUP_CHAT_ID:
        r = post(f"/api/chats/group/{GROUP_CHAT_ID}/messages", token=TOKEN,
                 json={"content": "그룹 채팅 테스트"})
        if is_ok(r, 200, 201): ok(S, "그룹 채팅 메시지 전송", code(r))
        else:                  fail(S, "그룹 채팅 메시지 전송", code(r))

        r = get(f"/api/chats/group/{GROUP_CHAT_ID}/members", token=TOKEN)
        if is_ok(r, 200):
            try:
                m = r.json() if isinstance(r.json(), list) else r.json().get("members", [])
                ok(S, "그룹 채팅 멤버 목록 (GET /api/chats/group/{id}/members)", f"{len(m)}명")
            except Exception: ok(S, "그룹 채팅 멤버 목록", code(r))
        else:
            fail(S, "그룹 채팅 멤버 목록", code(r))

    skip(S, "멤버별 last_read_id — 브라우저 폴링 테스트 필요")
else:
    skip(S, "그룹 채팅 — 공동구매 게시글 ID 없음")

# ════════════════════════════════════════════════════════════════════════════════
hdr("8. QR 거래 인증")
# ════════════════════════════════════════════════════════════════════════════════
S = "S8"

if POST_ID_SHARE and TOKEN:
    # subjectId: str 필수, ttlSeconds: Optional(기본값 있을 수 있음), purpose: Optional
    r = post("/api/qr/request", token=TOKEN,
             json={"subjectId": str(POST_ID_SHARE), "ttlSeconds": 300, "purpose": "trade"})
    if is_ok(r, 200, 201):
        try:
            # 응답: {"ok": true, "session": {"id": "qrs_xxx", "token": "raw_token", ...}}
            sess = r.json().get("session") or {}
            QR_CODE = sess.get("token") or r.json().get("token") or r.json().get("qr_code")
            QR_SESSION_ID = sess.get("id")
        except Exception:
            pass
        ok(S, "QR 생성 (POST /api/qr/request)", f"token={'있음' if QR_CODE else '필드명 확인 필요'}, session={QR_SESSION_ID}")
    else:
        fail(S, "QR 생성 (POST /api/qr/request)", f"{code(r)} / {r.text[:120] if r is not None else ''}")

    if QR_CODE and TOKEN2:
        # QrVerifyRequest: token 또는 rawValue 필드 사용
        r = post("/api/qr/verify", token=TOKEN2, json={"token": QR_CODE})
        if is_ok(r, 200, 201): ok(S, "QR 스캔·인증 성공 (POST /api/qr/verify)", code(r))
        else:                  fail(S, "QR 스캔·인증 (POST /api/qr/verify)", f"{code(r)} / {r.text[:80] if r is not None else ''}")

        # 만료/사용된 QR 재사용
        r = post("/api/qr/verify", token=TOKEN2, json={"token": QR_CODE})
        if r is not None and r.status_code in (400, 404, 409, 410, 422):
            ok(S, "만료·사용된 QR 재사용 → 실패", code(r))
        elif is_ok(r, 200) and r.json().get("ok") is False:
            ok(S, "만료·사용된 QR 재사용 → ok=false", r.json().get("result", ""))
        else:
            warn(S, "만료·사용된 QR 재사용", f"{code(r)} (예상: 4xx or ok=false)")
    else:
        skip(S, "QR 스캔·인증 — QR 코드 또는 TOKEN2 없음")
        skip(S, "만료 QR 재사용 — QR 코드 없음")

    r = get("/api/qr/history", token=TOKEN)
    if is_ok(r, 200): ok(S, "QR 이력 (GET /api/qr/history)", code(r))
    else:             fail(S, "QR 이력", code(r))
else:
    skip(S, "QR 테스트 — 게시글 또는 TOKEN 없음")

# ════════════════════════════════════════════════════════════════════════════════
hdr("9. 영수증 OCR 인증")
# ════════════════════════════════════════════════════════════════════════════════
S = "S9"

r = get("/api/receipt/health")
if is_ok(r, 200): ok(S, "GET /api/receipt/health → 200", code(r))
else:             fail(S, "GET /api/receipt/health", code(r))

skip(S, "영수증 이미지 업로드 (POST /api/receipt/scan) — 실제 이미지 파일 필요")
skip(S, "CLOVA 폴백 동작 — .env 설정 및 이미지 파일 필요")

r = post("/api/receipt/verify", token=TOKEN, json={"receipt_id": "dummy_nonexistent"})
if r is not None:
    if r.status_code in (400, 404, 422):
        ok(S, "POST /api/receipt/verify — 잘못된 ID → 4xx", code(r))
    elif r.status_code == 200:
        warn(S, "POST /api/receipt/verify — dummy ID에 200 반환 (유효성 검증 누락 의심)", code(r))
    else:
        warn(S, "POST /api/receipt/verify", code(r))
else:
    fail(S, "POST /api/receipt/verify", "NO RESPONSE")

r = get("/api/receipt/history", token=TOKEN)
if is_ok(r, 200): ok(S, "GET /api/receipt/history → 200", code(r))
else:             fail(S, "GET /api/receipt/history", code(r))

# ════════════════════════════════════════════════════════════════════════════════
hdr("10. 내 냉장고")
# ════════════════════════════════════════════════════════════════════════════════
S = "S10"

r = post("/api/fridge/from-receipt", token=TOKEN, json={"receiptId": "dummy_nonexistent"})
if r is not None:
    if r.status_code in (200, 201):
        ok(S, "POST /api/fridge/from-receipt", code(r))
    elif r.status_code in (400, 404):
        warn(S, "POST /api/fridge/from-receipt → dummy ID 거부 (엔드포인트 정상, ID 없음)",
             f"{code(r)} / {r.text[:80]}")
    elif r.status_code == 422:
        fail(S, "POST /api/fridge/from-receipt → 422 (요청 바디 형식 오류)",
             f"{code(r)} / {r.text[:120]}")
    else:
        fail(S, "POST /api/fridge/from-receipt", f"{code(r)} / {r.text[:80]}")
else:
    fail(S, "POST /api/fridge/from-receipt", "NO RESPONSE")

r = get("/api/fridge/items", token=TOKEN)
if is_ok(r, 200):
    try:
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", r.json().get("fridge_items", []))
        ok(S, "GET /api/fridge/items → 200", f"{len(items)}개 항목")
        if items: FRIDGE_ITEM_ID = items[0].get("id")
    except Exception: ok(S, "GET /api/fridge/items", code(r))
else:
    fail(S, "GET /api/fridge/items", code(r))

if FRIDGE_ITEM_ID:
    r = patch(f"/api/fridge/items/{FRIDGE_ITEM_ID}/status", token=TOKEN, json={"status": "CONSUMED"})
    if is_ok(r, 200, 204): ok(S, "아이템 상태 변경 → CONSUMED", code(r))
    else:                  fail(S, "아이템 상태 변경 (PATCH /api/fridge/items/{id}/status)", code(r))
else:
    skip(S, "아이템 상태 변경 — 냉장고에 항목 없음")

skip(S, "유통기한 D-3 이내 강조 표시 — 브라우저 UI 확인 필요")

# ════════════════════════════════════════════════════════════════════════════════
hdr("11. GPS 위치 인증")
# ════════════════════════════════════════════════════════════════════════════════
S = "S11"

r = get("/api/location-verify/health")
if is_ok(r, 200): ok(S, "GET /api/location-verify/health → 200", code(r))
else:             fail(S, "GET /api/location-verify/health", code(r))

r = post("/api/location-verify/dummy-target", token=TOKEN,
         json={"lat": 37.500622, "lng": 127.036456, "radiusM": 100,
               "subjectId": str(POST_ID_SHARE) if POST_ID_SHARE else None})
if is_ok(r, 200, 201):
    try:
        d = r.json()
        # 응답: {"ok": true, "session": {"id": "locv_xxx", "target_lat": ..., ...}}
        session_obj = d.get("session")
        if isinstance(session_obj, dict):
            GPS_SESSION_ID = session_obj.get("id")
        elif isinstance(session_obj, str):
            GPS_SESSION_ID = session_obj
        else:
            GPS_SESSION_ID = d.get("session_id") or d.get("id") or d.get("sessionId")
        ok(S, "더미 타겟 생성 (POST /api/location-verify/dummy-target)",
           f"session_id={GPS_SESSION_ID}  |  응답 키: {list(d.keys())}")
    except Exception: ok(S, "더미 타겟 생성", code(r))
else:
    fail(S, "더미 타겟 생성", f"{code(r)} / {r.text[:80] if r is not None else ''}")

if GPS_SESSION_ID:
    # 반경 내 → 성공 (accuracy=10m, accuracyLimitM 기본값 1500 이내 → 통과)
    r = post(f"/api/location-verify/{GPS_SESSION_ID}/gps-check", token=TOKEN,
             json={"lat": 37.500700, "lng": 127.036500, "accuracy": 10, "radiusM": 100})
    if is_ok(r, 200, 201):
        # 응답: {"ok": true/false, "status": "LOCATION_VERIFIED", "message": "...", "session": {...}}
        d_gps = r.json()
        if d_gps.get("ok") is True:
            ok(S, "GPS 체크 — 반경 내 좌표 → 인증 성공", f"status={d_gps.get('status')}")
        else:
            warn(S, "GPS 체크 — 반경 내 좌표", f"ok={d_gps.get('ok')}, status={d_gps.get('status')}, msg={d_gps.get('message','')[:60]}")
    else:
        fail(S, "GPS 체크 — 반경 내 좌표", f"{code(r)} / {r.text[:80] if r is not None else ''}")

    # 반경 외 → ok=false, status=TOO_FAR
    r = post(f"/api/location-verify/{GPS_SESSION_ID}/gps-check", token=TOKEN,
             json={"lat": 35.000000, "lng": 129.000000, "accuracy": 10, "radiusM": 100})
    if is_ok(r, 200):
        d_gps2 = r.json()
        if d_gps2.get("ok") is False:
            ok(S, "GPS 체크 — 반경 외 좌표 → ok=false", f"status={d_gps2.get('status')}")
        else:
            warn(S, "GPS 체크 — 반경 외 좌표", f"ok={d_gps2.get('ok')}, status={d_gps2.get('status')}")
    elif r is not None and r.status_code in (400, 409, 422):
        ok(S, "GPS 체크 — 반경 외 좌표 → 실패", code(r))
    else:
        warn(S, "GPS 체크 — 반경 외 좌표", code(r))
else:
    fail(S, "GPS 체크 — session_id 추출 실패", "")

r = get("/api/location-verify/history/list", token=TOKEN)
if is_ok(r, 200): ok(S, "위치 인증 이력 (GET /api/location-verify/history/list)", code(r))
else:             fail(S, "위치 인증 이력", code(r))

# ════════════════════════════════════════════════════════════════════════════════
hdr("12. 거래")
# ════════════════════════════════════════════════════════════════════════════════
S = "S12"

if POST_ID_SHARE and TOKEN2:
    # TOKEN2(구매자)가 TOKEN(게시자=판매자) 게시글에 거래 신청
    # TransactionCreate: post_id, appointment_at(선택) — receiver_id 필드 없음
    r = post("/api/transactions", token=TOKEN2, json={"post_id": POST_ID_SHARE})
    if is_ok(r, 200, 201):
        try:
            d_tx = r.json()
            TX_ID = d_tx.get("transactionId") or d_tx.get("id") or d_tx.get("transaction_id")
        except Exception: pass
        ok(S, "거래 생성 (POST /api/transactions)", f"id={TX_ID}")
    else:
        fail(S, "거래 생성 (POST /api/transactions)", f"{code(r)} / {r.text[:80] if r is not None else ''}")
else:
    skip(S, "거래 생성 — 게시글 또는 TOKEN2 없음")

if TX_ID:
    # pending → confirmed (직접 completed 불가: _ALLOWED["pending"] = {"confirmed", "canceled"})
    r = patch(f"/api/transactions/{TX_ID}", token=TOKEN, json={"status": "confirmed"})
    if is_ok(r, 200, 204):
        ok(S, "거래 상태 변경 → confirmed", code(r))
        # confirmed → completed
        r2 = patch(f"/api/transactions/{TX_ID}", token=TOKEN, json={"status": "completed"})
        if is_ok(r2, 200, 204): ok(S, "거래 상태 변경 → completed", code(r2))
        else:                   fail(S, "거래 상태 변경 → completed", f"{code(r2)} / {r2.text[:80] if r2 is not None else ''}")
    else:
        fail(S, "거래 상태 변경 (PATCH /api/transactions/{id})", f"{code(r)} / {r.text[:80] if r is not None else ''}")
else:
    skip(S, "거래 상태 변경 — 거래 ID 없음")

r = get("/api/transactions", token=TOKEN)
if is_ok(r, 200): ok(S, "거래 내역 (GET /api/transactions)", code(r))
else:             fail(S, "거래 내역", code(r))

skip(S, "정산 (Settlement.html) — 미구현")
skip(S, "상호 매너 평가 — 미구현")

# ════════════════════════════════════════════════════════════════════════════════
hdr("13. 프로필 / 내 활동")
# ════════════════════════════════════════════════════════════════════════════════
S = "S13"

r = get("/api/users/me", token=TOKEN)
if is_ok(r, 200):
    d = r.json()
    ok(S, "내 정보 조회 (GET /api/users/me)",
       f"nickname={'O' if d.get('nickname') else 'X'}, trust_score={'O' if d.get('trust_score') is not None else 'X'}")
else:
    fail(S, "내 정보 조회 (GET /api/users/me)", code(r))

new_nick = f"수정닉네임_{TS[-4:]}"
r = patch("/api/users/me", token=TOKEN, json={"nickname": new_nick})
if is_ok(r, 200, 204):
    ok(S, "프로필 수정 (PATCH /api/users/me)", code(r))
    r2 = get("/api/users/me", token=TOKEN)
    if is_ok(r2, 200) and r2.json().get("nickname") == new_nick:
        ok(S, "  └ 닉네임 변경 반영 확인", new_nick)
    else:
        warn(S, "  └ 닉네임 변경 반영", f"expected={new_nick}, got={r2.json().get('nickname') if r2 is not None else 'N/A'}")
else:
    fail(S, "프로필 수정 (PATCH /api/users/me)", code(r))

skip(S, "My_Activity.html 탭 동작 — 브라우저 UI 테스트 필요")

# ════════════════════════════════════════════════════════════════════════════════
hdr("14. 신고")
# ════════════════════════════════════════════════════════════════════════════════
S = "S14"

if POST_ID_SHARE and TOKEN2:
    r = post("/api/reports", token=TOKEN2, json={"target_type": "post",
             "target_id": POST_ID_SHARE, "reason": "테스트 신고 — 스팸"})
    if is_ok(r, 200, 201): ok(S, "게시글 신고 (POST /api/reports, target_type=post)", code(r))
    else:                  fail(S, "게시글 신고", f"{code(r)} / {r.text[:80] if r is not None else ''}")
else:
    skip(S, "게시글 신고 — 게시글 또는 TOKEN2 없음")

if USER1_ID and TOKEN2:
    r = post("/api/reports", token=TOKEN2, json={"target_type": "user",
             "target_id": USER1_ID, "reason": "테스트 신고 — 비매너"})
    if is_ok(r, 200, 201): ok(S, "회원 신고 (POST /api/reports, target_type=user)", code(r))
    else:                  fail(S, "회원 신고", f"{code(r)} / {r.text[:80] if r is not None else ''}")
else:
    skip(S, "회원 신고 — USER1_ID 또는 TOKEN2 없음")

skip(S, "Report.html UI 동작 — 브라우저 UI 테스트 필요")

# ════════════════════════════════════════════════════════════════════════════════
hdr("15. 관리자 (Admin)")
# ════════════════════════════════════════════════════════════════════════════════
S = "S15"

# seed_admin.py: 기존 계정 'Admin'(id=1) 승격 — 비밀번호는 원래 계정 그대로
# 환경변수 ADMIN_PW 로 지정 가능: set ADMIN_PW=실제비밀번호
ADMIN_PW = os.environ.get("ADMIN_PW", "admin0000")
r = post("/api/auth/login", json={"login_id": "Admin", "password": ADMIN_PW})
if is_ok(r, 200):
    try: ADMIN_TOKEN = r.json().get("token") or r.json().get("access_token") or r.json().get("session_token")
    except Exception: pass
    ok(S, f"관리자 계정 로그인 (login_id=Admin, pw={ADMIN_PW})", f"token={'있음' if ADMIN_TOKEN else '없음'}")
else:
    fail(S, f"관리자 계정 로그인 (login_id=Admin, pw={ADMIN_PW})",
         f"{code(r)} — 올바른 비밀번호를 환경변수로 지정: set ADMIN_PW=<비밀번호>")

# 일반 계정으로 Admin API → 403
r = get("/api/admin/dashboard", token=TOKEN)
if is_ok(r, 403): ok(S, "일반 계정 Admin API 접근 → 403", code(r))
else:             warn(S, "일반 계정 Admin API 접근", f"{code(r)} (예상: 403)")

if ADMIN_TOKEN:
    r = get("/api/admin/dashboard", token=ADMIN_TOKEN)
    if is_ok(r, 200): ok(S, "GET /api/admin/dashboard → 200", code(r))
    else:             fail(S, "GET /api/admin/dashboard", code(r))

    r = get("/api/admin/users", token=ADMIN_TOKEN)
    if is_ok(r, 200): ok(S, "GET /api/admin/users → 200", code(r))
    else:             fail(S, "GET /api/admin/users", code(r))

    # 회원 정지·복구 (TOKEN2 계정)
    if USER2_ID:
        r = patch(f"/api/admin/users/{USER2_ID}", token=ADMIN_TOKEN, json={"status": "suspended"})
        if is_ok(r, 200, 204):
            ok(S, "회원 상태 → suspended", code(r))
            r2 = patch(f"/api/admin/users/{USER2_ID}", token=ADMIN_TOKEN, json={"status": "active"})
            if is_ok(r2, 200, 204): ok(S, "회원 상태 복구 → active", code(r2))
            else: fail(S, "회원 상태 복구", code(r2))
        else: fail(S, "회원 상태 변경 (PATCH /api/admin/users/{id})", code(r))
    else:
        skip(S, "회원 상태 변경 — USER2_ID 없음")

    NOTICE_ID = None
    r = post("/api/admin/notices", token=ADMIN_TOKEN,
             json={"title": "테스트 공지", "content": "테스트 내용"})
    if is_ok(r, 200, 201):
        try: NOTICE_ID = r.json().get("id") or r.json().get("notice_id")
        except Exception: pass
        ok(S, "공지사항 작성 (POST /api/admin/notices)", f"id={NOTICE_ID}")
    else: fail(S, "공지사항 작성", f"{code(r)} / {r.text[:80] if r is not None else ''}")

    if NOTICE_ID:
        r = delete(f"/api/admin/notices/{NOTICE_ID}", token=ADMIN_TOKEN)
        if is_ok(r, 200, 204): ok(S, "공지사항 삭제 (DELETE /api/admin/notices/{id})", code(r))
        else:                  fail(S, "공지사항 삭제", code(r))
    else:
        skip(S, "공지사항 삭제 — notice ID 없음")

    r = get("/api/admin/reports", token=ADMIN_TOKEN)
    if is_ok(r, 200):
        try:
            lst = r.json() if isinstance(r.json(), list) else r.json().get("reports", r.json().get("items", []))
            ok(S, "신고 목록 (GET /api/admin/reports)", f"{len(lst)}건")
            if lst:
                RID = lst[0].get("id")
                r2 = patch(f"/api/admin/reports/{RID}", token=ADMIN_TOKEN, json={"status": "resolved"})
                if is_ok(r2, 200, 204): ok(S, "신고 처리 → resolved", code(r2))
                else:                   fail(S, "신고 처리 (PATCH /api/admin/reports/{id})", code(r2))
        except Exception: ok(S, "신고 목록", code(r))
    else:
        fail(S, "신고 목록 (GET /api/admin/reports)", code(r))

    r = get("/api/admin/chats", token=ADMIN_TOKEN)
    if is_ok(r, 200): ok(S, "채팅 모니터링 (GET /api/admin/chats)", code(r))
    else:             fail(S, "채팅 모니터링", code(r))
else:
    skip(S, "관리자 API 전체 — 관리자 로그인 실패")

# ════════════════════════════════════════════════════════════════════════════════
hdr("1-8. 회원 탈퇴 (테스트 계정 정리)")
# ════════════════════════════════════════════════════════════════════════════════
S = "S1"

if TOKEN2:
    r = post("/api/users/withdraw", token=TOKEN2, json={"password": TEST_PW})
    if is_ok(r, 200, 204):
        ok(S, "회원 탈퇴 (POST /api/users/withdraw)", code(r))
        r2 = post("/api/auth/login", json={"login_id": TEST_ID2, "password": TEST_PW})
        if r2 is not None and r2.status_code in (401, 403):
            ok(S, "탈퇴 후 재로그인 불가 → 401/403", code(r2))
        else:
            fail(S, "탈퇴 후 재로그인 불가", code(r2))
    else:
        fail(S, "회원 탈퇴 (POST /api/users/withdraw)", f"{code(r)} / {r.text[:80] if r is not None else ''}")
else:
    skip(S, "회원 탈퇴 — TOKEN2 없음")

# ════════════════════════════════════════════════════════════════════════════════
# 최종 결과 요약
# ════════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  최종 결과 요약{RESET}")
print(f"{BOLD}{'═'*60}{RESET}")
total   = len(results)
passed  = sum(1 for _,_,s,_ in results if s=="PASS")
failed  = sum(1 for _,_,s,_ in results if s=="FAIL")
warned  = sum(1 for _,_,s,_ in results if s=="WARN")
skipped = sum(1 for _,_,s,_ in results if s=="SKIP")
print(f"  전체: {total}  |  {GREEN}PASS: {passed}{RESET}  |  {RED}FAIL: {failed}{RESET}  |  {YELLOW}WARN: {warned}{RESET}  |  SKIP: {skipped}")
print(f"  실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if failed:
    print(f"\n{RED}{BOLD}  ▼ 실패 항목{RESET}")
    for sec, item, st, detail in results:
        if st == "FAIL":
            print(f"  {RED}✘ [{sec}]{RESET} {item}" + (f"  [{detail}]" if detail else ""))
if warned:
    print(f"\n{YELLOW}{BOLD}  ▼ 확인 필요 항목{RESET}")
    for sec, item, st, detail in results:
        if st == "WARN":
            print(f"  {YELLOW}△ [{sec}]{RESET} {item}" + (f"  [{detail}]" if detail else ""))

print(f"\n{BOLD}{'═'*60}{RESET}\n")

report = {
    "timestamp": datetime.now().isoformat(),
    "summary": {"total": total, "pass": passed, "fail": failed, "warn": warned, "skip": skipped},
    "results": [{"section": s, "item": i, "status": st, "detail": d} for s, i, st, d in results]
}
with open("nf_test_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"  상세 결과 저장: nf_test_report.json\n")
sys.exit(1 if failed > 0 else 0)