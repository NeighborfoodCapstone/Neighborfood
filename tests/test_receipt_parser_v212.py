from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.receipt_db import parse_receipt


def item_map(result):
    return {
        item["name"]: (item["qty"], item["price"])
        for item in result.get("items", [])
    }


def test_real_nonghyup_clova_output():
    text = """
농협
주소:경기
의정부시
대표:
최영*
사업자번호
:
127-82-*****
홈페이지
:http://www.
nonghyup.com/
영수증
미지참시
교환/환불
불가(30일내)
교환/환불
구매점에서
가능(결제카드지참)
전화:031-***-****
김갑순
상품(코드)
2015-11-03
16:31:53
0002-00085
단가
수량
금액
1
1
001
P굿모닝우유
900ML
*88010-****-****
1,350
002
양파
*231973
3,300
003
P무
*231913
500
1
004
P깻잎
*231308
750
88010-****-****
005
P하선정
바로먹기좋은장아찌
150g
1,380
006
P브로커리
*232285
1,280
1
[2,150]
1,350
3,300
500
750
1,380
1,280
1
1
판매총액:
8,560
부가세과세물품가액:
부가세:
>>
발
신용
을
금
액:
8,560
8,560
<<
7,180
1,255
125
바코드앞
*면세,
#영세,
상품명
P포인트
회원:2010190034***
박*분님
우수고객포인트:
잔여포인트:
사용가능포인트:
40
14,198
14,190
신용카드
매출전표(고객용)
할부:00개월
매출금액:
8,560원
"""
    result = parse_receipt(text)
    items = item_map(result)

    expected = {
        "굿모닝우유 900ML": (1, 1350),
        "양파": (1, 3300),
        "무": (1, 500),
        "깻잎": (1, 750),
        "하선정 바로먹기좋은장아찌 150g": (1, 1380),
        "브로커리": (1, 1280),
    }

    assert result["total"] == 8560, result
    assert items == expected, result
    assert sum(price for _, price in items.values()) == 8560, result


def test_masked_barcode_same_line():
    text = """
농협
상품(코드)
001 P우유 900ML
*88010-****-**** 1,350 1 1,350
002 P깻잎
88010-****-**** 750 1 750
판매총액 2,100
"""
    result = parse_receipt(text)
    assert item_map(result) == {
        "우유 900ML": (1, 1350),
        "깻잎": (1, 750),
    }, result


def test_starbucks_regression():
    text = """
스타벅스
주문번호: 123
품목명 단가 수량 금액
티끌 드립 4,500 1 4,500
I-T)아메리카노
4,100 2 8,200
결제금액 12,700
카카오페이
번호: 123456
발급: 가능
"""
    result = parse_receipt(text)
    assert result["total"] == 12700, result
    assert item_map(result) == {
        "티끌 드립": (1, 4500),
        "I-T)아메리카노": (2, 8200),
    }, result


def test_normal_small_prices():
    text = """
농협
상품(코드)
001 P무
*231913
500
1
002 P깻잎
*231308
750
1
판매총액:
1,250
"""
    result = parse_receipt(text)
    assert item_map(result) == {
        "무": (1, 500),
        "깻잎": (1, 750),
    }, result


def test_kakao_product_name():
    text = """
동네마트
상품명 단가 수량 금액
카카오닙스 3,000 1 3,000
우유 2,000 1 2,000
합계 5,000
카카오페이
"""
    result = parse_receipt(text)
    assert item_map(result) == {
        "카카오닙스": (1, 3000),
        "우유": (1, 2000),
    }, result


def main():
    tests = [
        test_real_nonghyup_clova_output,
        test_masked_barcode_same_line,
        test_starbucks_regression,
        test_normal_small_prices,
        test_kakao_product_name,
    ]

    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")

    print()
    print("[OK] receipt parser v2.1.2 regression tests passed")


if __name__ == "__main__":
    main()
