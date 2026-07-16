#!/usr/bin/env python3
"""
seed_posts.py — 더미 게시글 30개 생성 스크립트 (API 호출 방식)

사용법:
    1) 서버를 먼저 켭니다:  uvicorn main:app --reload
    2) 다른 터미널에서:      python seed_posts.py
    3) 다른 포트/호스트면:   python seed_posts.py --base http://127.0.0.1:8000

동작:
    - 더미 회원 4명을 가입(이미 있으면 로그인)시킨 뒤,
    - 나눔(share)·공동구매(groupbuy)·교환(exchange)을 골고루 섞어 30개 등록합니다.
    - 표준 라이브러리(urllib)만 사용 — 추가 설치 불필요.
"""
import argparse
import json
import random
import sys
import urllib.error
import urllib.request

# ── 더미 회원 ────────────────────────────────────────────────────────────
USERS = [
    {"login_id": "seed_minji",  "password": "seedpass1!", "phone_number": "010-2000-0001", "nickname": "민지네부엌"},
    {"login_id": "seed_junho",  "password": "seedpass1!", "phone_number": "010-2000-0002", "nickname": "준호삼촌"},
    {"login_id": "seed_yuna",   "password": "seedpass1!", "phone_number": "010-2000-0003", "nickname": "유나마켓"},
    {"login_id": "seed_dohyun", "password": "seedpass1!", "phone_number": "010-2000-0004", "nickname": "도현이네"},
]

# 서울 광진구 주요 지역 좌표 및 명칭
NEIGHBORHOODS = [
    ("화양동 건대입구역 앞", 37.5404, 127.0692),
    ("자양동 뚝섬유원지 인근", 37.5315, 127.0667),
    ("구의동 광진구청 인근", 37.5385, 127.0824),
    ("광장동 광나루역 인근", 37.5453, 127.1034),
    ("능동 어린이대공원 정문", 37.5478, 127.0746),
    ("중곡동 중곡역 인근", 37.5656, 127.0842),
    ("군자동 세종대학교 앞", 37.5503, 127.0731),
]

# ── 게시글 풀: 유형별로 골고루 (총 30개 생성을 위해 데이터 풀 확장) ───────
SHARE = [
    ("쪽파 한 단 나눔해요", "채소", "텃밭에서 너무 많이 자라서 나눠요. 오늘 저녁까지 가져가실 분!"),
    ("두부 2모 나눔", "신선식품", "1+1으로 산 두부 한 모가 남아서요. 유통기한 넉넉합니다."),
    ("바나나 다섯 개 나눔", "과일", "혼자라 다 못 먹어요. 살짝 익었지만 맛있어요."),
    ("식빵 한 봉지 나눔", "베이커리", "선물 받았는데 글루텐 못 먹어서요. 오늘 구운 거예요."),
    ("계란 6알 나눔합니다", "신선식품", "여행 가기 전에 정리해요. 냉장 보관했습니다."),
    ("당근 3개 나눔", "채소", "카레 해먹고 남은 당근이에요. 싱싱합니다."),
    ("시리얼 반 박스 나눔", "가공식품", "입맛에 안 맞아서요. 미개봉에 가깝습니다."),
    ("귤 한 봉지 나눔", "과일", "제주 다녀온 지인이 너무 많이 줘서 나눠요."),
    ("대파 한 단 무료 나눔", "채소", "요리하고 남은 싱싱한 대파 나눔합니다."),
    ("방울토마토 한 팩 소분 나눔", "과일", "박스로 사서 혼자 다 못 먹을 것 같아 나눕니다.")
]
GROUPBUY = [
    ("양파 10kg 같이 사요", "채소", "도매로 10kg 사서 1인분씩 나눠요. 너무 많아서 혼자 못 사요.", 5, 4000),
    ("삼겹살 공구 (1근씩)", "정육", "정육점 대량 주문이요. 근당 가격으로 저렴하게.", 6, 9000),
    ("제철 사과 한 박스 공구", "과일", "농장 직거래 박스를 나눠 담아요. 신선해요.", 4, 7000),
    ("우유 24팩 공동구매", "유제품", "대형마트 묶음을 나눠요. 유통기한 길어요.", 8, 1300),
    ("쌀 20kg 같이 나눠요", "곡물", "한 포대 사서 5kg씩 4명. 햅쌀입니다.", 4, 16000),
    ("커피 원두 1kg 공구", "음료", "로스터리 1kg를 250g씩 나눠요. 취향 맞는 분!", 4, 9000),
    ("생수 2L 12병 공구", "음료", "묶음으로 사서 나눠요. 들고 오기 힘들어서요.", 6, 800),
    ("스팸 6캔 묶음 공구", "가공식품", "마트에서 번들로 저렴하게 사서 나눌 분 구합니다.", 3, 2500),
    ("아보카도 5과 공구", "과일", "인터넷으로 대량 주문해서 나누려고 합니다.", 5, 1800),
    ("닭가슴살 팩 대량 공구", "냉동식품", "10팩 묶음 저렴하게 나눠서 가져가실 분!", 2, 1500)
]
EXCHANGE = [
    ("라면 ↔ 즉석밥 교환해요", "가공식품", "라면 한 봉지 남았는데 즉석밥이랑 바꾸실 분.", "즉석밥"),
    ("간장 ↔ 식용유 교환", "조미료", "간장 새 거 있는데 식용유가 필요해요.", "식용유"),
    ("사과 ↔ 배 교환", "과일", "사과는 많은데 배가 먹고 싶어서요.", "배"),
    ("파스타면 ↔ 소면 교환", "가공식품", "파스타면 한 봉지랑 소면 바꿔요.", "소면"),
    ("고추장 ↔ 된장 교환해요", "조미료", "고추장 큰 통 있어서 된장이랑 나눠요.", "된장"),
    ("참치캔 ↔ 연어캔 교환", "가공식품", "선물세트 들어온 참치캔을 연어캔과 교환 원합니다.", "연어캔"),
    ("카누 커피 ↔ 현미녹차 교환", "음료", "믹스나 티백 종류 교환 원해요.", "현미녹차"),
    ("소금 ↔ 설탕 교환", "조미료", "가는 소금 남는 것 설탕이랑 바꿉니다.", "설탕"),
    ("비빔면 ↔ 짜파게티 교환", "가공식품", "종류별로 드실 분 서로 교환해요.", "짜파게티"),
    ("콘시리얼 ↔ 초코시리얼 교환", "가공식품", "초코맛 시리얼로 교환 원해요.", "초코시리얼")
]


def _post(base, path, payload, token=None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"detail": str(e)}
    except urllib.error.URLError as e:
        print(f"  [연결 실패] 서버가 켜져 있는지 확인하세요 -> {base}\n  ({e})")
        sys.exit(1)


def get_token(base, u):
    status, body = _post(base, "/api/auth/register", u)
    if status == 200 and body.get("token"):
        print(f"  + 회원 가입: {u['nickname']} ({u['login_id']})")
        return body["token"]
    status, body = _post(base, "/api/auth/login",
                         {"login_id": u["login_id"], "password": u["password"]})
    if status == 200 and body.get("token"):
        print(f"  · 기존 회원 로그인: {u['nickname']} ({u['login_id']})")
        return body["token"]
    print(f"  [실패] {u['login_id']}: {status} {body}")
    return None


def build_posts():
    items = []
    for title, cat, desc in SHARE:
        items.append({"type": "share", "title": title, "category": cat, "description": desc})
    for title, cat, desc, target, price in GROUPBUY:
        items.append({"type": "groupbuy", "title": title, "category": cat, "description": desc,
                      "gb_target": target, "gb_price": price})
    for title, cat, desc, want in EXCHANGE:
        items.append({"type": "exchange", "title": title, "category": cat, "description": desc,
                      "exchange_want": want})
    
    for it in items:
        name, lat, lng = random.choice(NEIGHBORHOODS)
        it["address"] = name
        it["lat"] = round(lat + random.uniform(-0.005, 0.005), 6)
        it["lng"] = round(lng + random.uniform(-0.005, 0.005), 6)
        
    random.shuffle(items)
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000",
                    help="서버 주소 (기본 http://127.0.0.1:8000)")
    ap.add_argument("--seed", type=int, default=None, help="난수 시드(재현용)")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    base = args.base.rstrip("/")
    print(f"대상 서버: {base}\n")

    print("[1/2] 더미 회원 준비")
    tokens = [t for t in (get_token(base, u) for u in USERS) if t]
    if not tokens:
        print("토큰을 하나도 얻지 못했습니다. 서버/인증 설정을 확인하세요.")
        sys.exit(1)

    print(f"\n[2/2] 게시글 등록 (작성자 {len(tokens)}명에 분배)")
    posts = build_posts()
    ok = 0
    counts = {"share": 0, "groupbuy": 0, "exchange": 0}
    for i, p in enumerate(posts):
        token = tokens[i % len(tokens)]
        status, body = _post(base, "/posts", p, token=token)
        if status == 200 and body.get("id"):
            ok += 1
            counts[p["type"]] += 1
            print(f"  #{body['id']:>3} [{p['type']:>8}] {p['title']}")
        else:
            print(f"  [실패] {p['title']}: {status} {body}")

    print(f"\n완료: {ok}/{len(posts)}개 등록 "
          f"(나눔 {counts['share']} · 공동구매 {counts['groupbuy']} · 교환 {counts['exchange']})")
    print(f"확인: {base}/posts  또는  {base}/frontend/Home.html")


if __name__ == "__main__":
    main()