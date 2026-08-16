from __future__ import annotations

import pytest

from src.product_intelligence.adapters.shopee_parsing import (
    build_shopee_candidate_id,
    build_shopee_search_url,
    extract_shopee_product_id,
    parse_shopee_discount_percent,
    parse_shopee_price,
    parse_shopee_rating,
    parse_shopee_review_count,
    parse_shopee_sold_count,
)


def test_parse_shopee_price_various_formats() -> None:
    # Standard Vietnamese dot-separated VND prices
    assert parse_shopee_price("₫150.000") == 150000.0
    assert parse_shopee_price("150.000đ") == 150000.0
    assert parse_shopee_price("₫ 1.250.000") == 1250000.0
    assert parse_shopee_price("150000") == 150000.0

    # Price ranges take the lower bound
    assert parse_shopee_price("₫150.000 - ₫200.000") == 150000.0
    assert parse_shopee_price("120.000 - 180.000") == 120000.0

    # Suffixes: k / tr / triệu
    assert parse_shopee_price("150k") == 150000.0
    assert parse_shopee_price("15.5k") == 15500.0
    assert parse_shopee_price("1,5 triệu") == 1500000.0
    assert parse_shopee_price("2.5tr") == 2500000.0

    # Decimal format
    assert parse_shopee_price("150.000,50") == 150000.50

    # Invalid, malformed, negative, or empty values return None
    assert parse_shopee_price(None) is None
    assert parse_shopee_price("") is None
    assert parse_shopee_price("   ") is None
    assert parse_shopee_price("Liên hệ") is None
    assert parse_shopee_price("₫0") is None
    assert parse_shopee_price("-50000") is None


def test_parse_shopee_sold_count_various_formats() -> None:
    # Standard integer sold counts
    assert parse_shopee_sold_count("Đã bán 1200") == 1200
    assert parse_shopee_sold_count("Đã bán 1.200") == 1200
    assert parse_shopee_sold_count("150") == 150

    # Multiplier formats: k, K, tr, triệu
    assert parse_shopee_sold_count("Đã bán 1,2k") == 1200
    assert parse_shopee_sold_count("Đã bán 1.5k") == 1500
    assert parse_shopee_sold_count("10k+ đã bán") == 10000
    assert parse_shopee_sold_count("Đã bán 1,5tr") == 1500000
    assert parse_shopee_sold_count("2 triệu đã bán") == 2000000

    # Invalid / empty
    assert parse_shopee_sold_count(None) is None
    assert parse_shopee_sold_count("") is None
    assert parse_shopee_sold_count("Chưa có lượt bán") is None
    assert parse_shopee_sold_count("0") is None
    assert parse_shopee_sold_count("-5") is None


def test_parse_shopee_rating_various_formats() -> None:
    assert parse_shopee_rating("4.8") == 4.8
    assert parse_shopee_rating("4,8") == 4.8
    assert parse_shopee_rating("5.0") == 5.0
    assert parse_shopee_rating("4.9 / 5") == 4.9
    assert parse_shopee_rating("5/5") == 5.0

    # Out of bounds or invalid
    assert parse_shopee_rating(None) is None
    assert parse_shopee_rating("") is None
    assert parse_shopee_rating("5.5") is None
    assert parse_shopee_rating("-1.0") is None
    assert parse_shopee_rating("Chưa có đánh giá") is None


def test_parse_shopee_review_count_various_formats() -> None:
    assert parse_shopee_review_count("(1.2k)") == 1200
    assert parse_shopee_review_count("(350)") == 350
    assert parse_shopee_review_count("1.2k đánh giá") == 1200
    assert parse_shopee_review_count("350 nhận xét") == 350

    assert parse_shopee_review_count(None) is None
    assert parse_shopee_review_count("") is None
    assert parse_shopee_review_count("0") is None


def test_parse_shopee_discount_percent() -> None:
    assert parse_shopee_discount_percent("-25%") == 25.0
    assert parse_shopee_discount_percent("25% GIẢM") == 25.0
    assert parse_shopee_discount_percent("GIẢM 30%") == 30.0
    assert parse_shopee_discount_percent("50%") == 50.0

    assert parse_shopee_discount_percent(None) is None
    assert parse_shopee_discount_percent("") is None
    assert parse_shopee_discount_percent("120%") is None
    assert parse_shopee_discount_percent("-500%") is None


def test_extract_shopee_product_id() -> None:
    # URL pattern -i.{shop_id}.{item_id}
    u1 = "https://shopee.vn/Tai-nghe-Bluetooth-i.1234567.8901234"
    assert extract_shopee_product_id(u1) == "8901234"

    # URL pattern /product/{shop_id}/{item_id}
    u2 = "https://shopee.vn/product/1234567/8901234"
    assert extract_shopee_product_id(u2) == "8901234"

    # Direct attribute
    assert extract_shopee_product_id(None, item_id_attr="8901234") == "8901234"

    # Unparseable URL
    assert extract_shopee_product_id("https://shopee.vn/search?keyword=test") is None


def test_build_shopee_candidate_id_determinism() -> None:
    url = "https://shopee.vn/product/1234567/8901234?sp_atk=abc"

    # When item ID is known
    id1 = build_shopee_candidate_id("8901234", url)
    id2 = build_shopee_candidate_id("8901234", url)
    assert id1 == "shopee_8901234"
    assert id1 == id2

    # When item ID is unknown, derive SHA-256 fingerprint
    id_fp1 = build_shopee_candidate_id(None, url)
    id_fp2 = build_shopee_candidate_id(None, url)
    assert id_fp1.startswith("shopee_url_")
    assert id_fp1 == id_fp2


def test_build_shopee_search_url() -> None:
    assert build_shopee_search_url("tai nghe bluetooth", page=1) == "https://shopee.vn/search?keyword=tai+nghe+bluetooth"
    assert build_shopee_search_url("ban phim co", page=2) == "https://shopee.vn/search?keyword=ban+phim+co&page=1"
    assert build_shopee_search_url("chuot gaming", page=3) == "https://shopee.vn/search?keyword=chuot+gaming&page=2"
