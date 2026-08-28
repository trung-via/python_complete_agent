from __future__ import annotations

import pytest

from src.product_intelligence.adapters.tiktok_parsing import (
    build_tiktok_candidate_id,
    build_tiktok_search_url,
    extract_tiktok_product_id,
    parse_tiktok_discount_percent,
    parse_tiktok_price,
    parse_tiktok_rating,
    parse_tiktok_review_count,
    parse_tiktok_sold_count,
)


def test_parse_tiktok_price_various_formats() -> None:
    # Standard Vietnamese dot-separated VND prices
    assert parse_tiktok_price("₫150.000") == 150000.0
    assert parse_tiktok_price("150.000đ") == 150000.0
    assert parse_tiktok_price("₫ 1.250.000") == 1250000.0
    assert parse_tiktok_price("150000") == 150000.0

    # International currency symbols
    assert parse_tiktok_price("$19.99") == 19.99
    assert parse_tiktok_price("£12.50") == 12.50

    # Price ranges take the lower bound
    assert parse_tiktok_price("₫150.000 - ₫200.000") == 150000.0
    assert parse_tiktok_price("120.000 - 180.000") == 120000.0
    assert parse_tiktok_price("150k - 200k") == 150000.0

    # Suffixes: k / tr / triệu / m
    assert parse_tiktok_price("150k") == 150000.0
    assert parse_tiktok_price("15.5k") == 15500.0
    assert parse_tiktok_price("1,5 triệu") == 1500000.0
    assert parse_tiktok_price("2.5tr") == 2500000.0
    assert parse_tiktok_price("1.2m") == 1200000.0

    # Decimal format
    assert parse_tiktok_price("150.000,50") == 150000.50
    assert parse_tiktok_price("1,500.50") == 1500.50

    # Invalid, malformed, negative, zero, or empty values return None
    assert parse_tiktok_price(None) is None
    assert parse_tiktok_price("") is None
    assert parse_tiktok_price("   ") is None
    assert parse_tiktok_price("Contact for price") is None
    assert parse_tiktok_price("₫0") is None
    assert parse_tiktok_price("0") is None
    assert parse_tiktok_price("-50000") is None
    assert parse_tiktok_price("Price: -150k") is None
    assert parse_tiktok_price("Giá: -50k") is None
    assert parse_tiktok_price("₫-150.000") is None
    assert parse_tiktok_price("₫ -150k") is None
    assert parse_tiktok_price("-$19.99") is None
    assert parse_tiktok_price("$-19.99") is None
    assert parse_tiktok_price("-150k - 200k") is None


def test_parse_tiktok_sold_count_various_formats() -> None:
    # Standard integer sold counts
    assert parse_tiktok_sold_count("Đã bán 1200") == 1200
    assert parse_tiktok_sold_count("Đã bán 1.200") == 1200
    assert parse_tiktok_sold_count("150") == 150
    assert parse_tiktok_sold_count("1,200 sold") == 1200

    # Multiplier formats: k, K, tr, triệu, m
    assert parse_tiktok_sold_count("Đã bán 1,2k") == 1200
    assert parse_tiktok_sold_count("Đã bán 1.5k") == 1500
    assert parse_tiktok_sold_count("1.5k Sold") == 1500
    assert parse_tiktok_sold_count("10k+ sold") == 10000
    assert parse_tiktok_sold_count("Đã bán 1,5tr") == 1500000
    assert parse_tiktok_sold_count("2 triệu đã bán") == 2000000
    assert parse_tiktok_sold_count("1.2m sold") == 1200000

    # Invalid / empty / zero / negative
    assert parse_tiktok_sold_count(None) is None
    assert parse_tiktok_sold_count("") is None
    assert parse_tiktok_sold_count("No sales yet") is None
    assert parse_tiktok_sold_count("0") is None
    assert parse_tiktok_sold_count("-5") is None
    assert parse_tiktok_sold_count("Đã bán -1200") is None
    assert parse_tiktok_sold_count("Đã bán -1.5k") is None
    assert parse_tiktok_sold_count("Sold -100") is None
    assert parse_tiktok_sold_count("-5 sold") is None
    assert parse_tiktok_sold_count("Đã bán - 1.2k") is None


def test_parse_tiktok_rating_various_formats() -> None:
    assert parse_tiktok_rating("4.8") == 4.8
    assert parse_tiktok_rating("4,8") == 4.8
    assert parse_tiktok_rating("5.0") == 5.0
    assert parse_tiktok_rating("4.9 / 5") == 4.9
    assert parse_tiktok_rating("4.5/5") == 4.5
    assert parse_tiktok_rating("5/5") == 5.0
    assert parse_tiktok_rating("0.0") == 0.0

    # Out of bounds or invalid or negative
    assert parse_tiktok_rating(None) is None
    assert parse_tiktok_rating("") is None
    assert parse_tiktok_rating("5.5") is None
    assert parse_tiktok_rating("-1.0") is None
    assert parse_tiktok_rating("Rating: -4.5") is None
    assert parse_tiktok_rating("-4.8") is None
    assert parse_tiktok_rating("-4.5/5") is None
    assert parse_tiktok_rating("Đánh giá: -5.0") is None
    assert parse_tiktok_rating("No ratings") is None


def test_parse_tiktok_review_count_various_formats() -> None:
    assert parse_tiktok_review_count("(1.2k)") == 1200
    assert parse_tiktok_review_count("(350)") == 350
    assert parse_tiktok_review_count("1.2k reviews") == 1200
    assert parse_tiktok_review_count("350 nhận xét") == 350
    assert parse_tiktok_review_count("1.5k đánh giá") == 1500

    assert parse_tiktok_review_count(None) is None
    assert parse_tiktok_review_count("") is None
    assert parse_tiktok_review_count("0") is None
    assert parse_tiktok_review_count("-10") is None
    assert parse_tiktok_review_count("( -350 )") is None
    assert parse_tiktok_review_count("-350 reviews") is None
    assert parse_tiktok_review_count("Đánh giá: -1.2k") is None
    assert parse_tiktok_review_count("(-1.2k)") is None


def test_parse_tiktok_discount_percent() -> None:
    assert parse_tiktok_discount_percent("-25%") == 25.0
    assert parse_tiktok_discount_percent("25% OFF") == 25.0
    assert parse_tiktok_discount_percent("GIẢM 30%") == 30.0
    assert parse_tiktok_discount_percent("50%") == 50.0
    assert parse_tiktok_discount_percent("0%") == 0.0
    assert parse_tiktok_discount_percent("100%") == 100.0

    assert parse_tiktok_discount_percent(None) is None
    assert parse_tiktok_discount_percent("") is None
    assert parse_tiktok_discount_percent("120%") is None
    assert parse_tiktok_discount_percent("-500%") is None


def test_extract_tiktok_product_id() -> None:
    # Pattern /product/<id>
    u1 = "https://www.tiktok.com/view/product/1729482910481234567"
    assert extract_tiktok_product_id(u1) == "1729482910481234567"

    # Pattern /item/<id>
    u2 = "https://shop.tiktok.com/item/1729482910481234567?locale=vi-VN"
    assert extract_tiktok_product_id(u2) == "1729482910481234567"

    # Pattern itemId=<id>
    u3 = "https://www.tiktok.com/shop?itemId=1729482910481234567&other=1"
    assert extract_tiktok_product_id(u3) == "1729482910481234567"

    # Pattern item_id=<id> / product_id=<id> / productId=<id>
    u4 = "https://www.tiktok.com/shop?item_id=1729482910481234567"
    assert extract_tiktok_product_id(u4) == "1729482910481234567"
    u5 = "https://www.tiktok.com/shop?product_id=1729482910481234567"
    assert extract_tiktok_product_id(u5) == "1729482910481234567"

    # Direct attribute
    assert extract_tiktok_product_id(None, item_id_attr="1729482910481234567") == "1729482910481234567"

    # Missing / unparseable
    assert extract_tiktok_product_id("https://www.tiktok.com/shop/search?q=phone") is None
    assert extract_tiktok_product_id(None) is None
    assert extract_tiktok_product_id("") is None


def test_build_tiktok_candidate_id_determinism_and_fallback() -> None:
    url_with_id = "https://www.tiktok.com/view/product/1729482910481234567?track=123#section1"

    # When item ID is explicitly known
    id1 = build_tiktok_candidate_id("1729482910481234567", url_with_id)
    id2 = build_tiktok_candidate_id("1729482910481234567", url_with_id)
    assert id1 == "tiktok_1729482910481234567"
    assert id1 == id2

    # When item ID is omitted but discoverable from URL, preserve product identity
    id_extracted = build_tiktok_candidate_id(None, url_with_id)
    assert id_extracted == "tiktok_1729482910481234567"

    # Query-carried product identity is also preserved
    url_query_id = "https://www.tiktok.com/shop?itemId=1729482910481234567&source=feed#section"
    assert build_tiktok_candidate_id(None, url_query_id) == "tiktok_1729482910481234567"

    # When item ID is genuinely unknown, derive cryptographic SHA-256 fingerprint without fragment
    url_fallback_1 = "https://www.tiktok.com/shop/search?q=phone#section1"
    url_fallback_2 = "https://www.tiktok.com/shop/search?q=phone#section2"
    id_fp1 = build_tiktok_candidate_id(None, url_fallback_1)
    id_fp2 = build_tiktok_candidate_id(None, url_fallback_2)
    assert id_fp1.startswith("tiktok_url_")
    assert id_fp1 == id_fp2


def test_build_tiktok_search_url() -> None:
    assert build_tiktok_search_url("tai nghe bluetooth", page=1) == "https://www.tiktok.com/shop/search?q=tai+nghe+bluetooth"
    assert build_tiktok_search_url("ban phim co", page=2) == "https://www.tiktok.com/shop/search?q=ban+phim+co&page=2"
    assert build_tiktok_search_url("chuot gaming", page=3) == "https://www.tiktok.com/shop/search?q=chuot+gaming&page=3"

    # Boundary failures on invalid inputs: non-string query, empty query, non-positive integer, bool, float
    with pytest.raises(ValueError):
        build_tiktok_search_url("")
    with pytest.raises(ValueError):
        build_tiktok_search_url("   ")
    with pytest.raises(ValueError):
        build_tiktok_search_url("test", page=0)
    with pytest.raises(ValueError):
        build_tiktok_search_url("test", page=-1)
    with pytest.raises(ValueError):
        build_tiktok_search_url("test", page=True)  # type: ignore
    with pytest.raises(ValueError):
        build_tiktok_search_url("test", page=False)  # type: ignore
    with pytest.raises(ValueError):
        build_tiktok_search_url("test", page=1.5)  # type: ignore
    with pytest.raises(ValueError):
        build_tiktok_search_url("test", page="1")  # type: ignore


def test_parsing_has_no_side_effects() -> None:
    # Directly verify that the parsing module has no forbidden filesystem/network/browser/queue/Drive/LLM/scoring/ranking/approval or TikTok deep-ingestion dependency
    import ast
    import inspect
    from pathlib import Path
    from src.product_intelligence.adapters import tiktok_parsing

    functions = [
        tiktok_parsing.parse_tiktok_price,
        tiktok_parsing.parse_tiktok_sold_count,
        tiktok_parsing.parse_tiktok_rating,
        tiktok_parsing.parse_tiktok_review_count,
        tiktok_parsing.parse_tiktok_discount_percent,
        tiktok_parsing.extract_tiktok_product_id,
        tiktok_parsing.build_tiktok_candidate_id,
        tiktok_parsing.build_tiktok_search_url,
    ]
    for fn in functions:
        assert inspect.isfunction(fn)

    # Inspect AST of the module to guarantee no forbidden dependencies
    source_path = Path(inspect.getfile(tiktok_parsing))
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    allowed_module_prefixes = {"__future__", "hashlib", "re", "urllib.parse", "typing"}
    forbidden_terms = [
        "os", "pathlib", "shutil", "socket", "http", "requests", "httpx", "aiohttp",
        "playwright", "selenium", "browser", "webdriver", "queue", "celery", "redis",
        "google", "drive", "openai", "anthropic", "llm", "policy", "scoring", "ranking",
        "approval", "deep_ingest", "scraper", "crawler",
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert alias.name in allowed_module_prefixes or root_pkg in allowed_module_prefixes, f"Forbidden import: {alias.name}"
                for forbidden in forbidden_terms:
                    assert forbidden not in alias.name.lower(), f"Forbidden dependency import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            root_pkg = module_name.split(".")[0]
            assert module_name in allowed_module_prefixes or root_pkg in allowed_module_prefixes, f"Forbidden import from: {module_name}"
            for forbidden in forbidden_terms:
                assert forbidden not in module_name.lower(), f"Forbidden dependency import from: {module_name}"

