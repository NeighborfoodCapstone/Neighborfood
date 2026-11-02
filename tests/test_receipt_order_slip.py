from app.db.receipt_db import parse_receipt


def test_real_ocr_order_slip_names_quantities_and_total():
    # User-supplied OCR text: CLOVA reads names column before quantity column.
    text = """등
뒤가
서늘해도
음료에
집중하십시오
[주문(대기)번호]
147
주문내역
상품명
수량
구분
아이스
아메리카노
큐브라떼
쿠키프라페
2
신규
1
신규
1
신규
주문금액
17,000
결제금액
받은금액
17,000
17,000
문해
주셔서
감사합니다.
25-06-02
15:49:58
[4]
/
R33_KIDSK"""
    result = parse_receipt(text)
    assert result["store"] is None
    assert result["total"] == 17000
    assert result["items"] == [
        {"name": "아이스 아메리카노", "qty": 2, "price": 0, "priceMissing": True},
        {"name": "큐브라떼", "qty": 1, "price": 0, "priceMissing": True},
        {"name": "쿠키프라페", "qty": 1, "price": 0, "priceMissing": True},
    ]


def test_ambiguous_order_slip_does_not_invent_items_or_prices():
    text = "주문내역\n상품명\n수량\n구분\n카라멜\n마끼아또\n2\n신규\n주문금액\n9,000"
    result = parse_receipt(text)
    assert result["items"] == []
    assert result["total"] == 9000


def test_order_slip_does_not_deduplicate_repeated_items():
    text = "주문내역\n상품명\n수량\n구분\n아메리카노\n아메리카노\n1\n신규\n2\n신규\n주문금액\n9,000"
    assert [(item["name"], item["qty"]) for item in parse_receipt(text)["items"]] == [
        ("아메리카노", 1), ("아메리카노", 2)
    ]


def test_missing_price_marker_survives_receipt_confirmation(client, make_user):
    user = make_user("order_slip_test")
    response = user.post("/api/receipt/verify", {"items": [
        {"name": "아이스 아메리카노", "qty": 2, "price": 0, "priceMissing": True}
    ]})
    assert response.status_code == 200
    assert response.json()["receipt"]["selectedItems"][0]["priceMissing"] is True
