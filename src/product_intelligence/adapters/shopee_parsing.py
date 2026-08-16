from __future__ import annotations

import hashlib
import re
import urllib.parse
from typing import Optional


def parse_shopee_price(text: Optional[str]) -> Optional[float]:
    """
    Parses a localized Vietnamese Shopee price string into a float.
    Handles ranges (returns lower bound), currency symbols (₫, đ, VND), and multiplier suffixes (k, tr).
    Returns None if malformed, negative, or non-positive.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned:
        return None

    # If price range (e.g. "₫150.000 - ₫200.000" or "150.000 - 200.000"), take the first part
    if " - " in cleaned or ("-" in cleaned and not cleaned.startswith("-")):
        parts = cleaned.split("-", 1)
        if len(parts) == 2 and parts[0].strip():
            cleaned = parts[0].strip()

    # Reject explicitly negative numbers
    if cleaned.startswith("-"):
        return None

    # Handle 'tr' or 'triệu' suffix (e.g. "1.5tr", "1,5 triệu")
    match_tr = re.search(r"([\d.,]+)\s*(?:tr|triệu)\b", cleaned)
    if match_tr:
        num_str = match_tr.group(1).replace(",", ".")
        try:
            val = float(num_str) * 1_000_000.0
            return val if val > 0 else None
        except ValueError:
            return None

    # Handle 'k' suffix (e.g. "150k", "15.5k", "15,5k")
    match_k = re.search(r"([\d.,]+)\s*k\b", cleaned)
    if match_k:
        num_str = match_k.group(1).replace(",", ".")
        try:
            val = float(num_str) * 1_000.0
            return val if val > 0 else None
        except ValueError:
            return None

    # Remove currency symbols and common words
    cleaned = re.sub(r"[₫đvnd\s]", "", cleaned)

    # If starts with negative sign after cleanup
    if cleaned.startswith("-"):
        return None

    # In Vietnamese currency format, '.' is thousands separator (150.000) and ',' is decimal (150.000,50)
    # If both '.' and ',' appear: e.g. "150.000,50" -> "150000.50"
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned:
        # Check if dot is thousands separator (e.g. 150.000 or 1.500.000)
        # Groups of 3 digits after dot indicate thousands separator
        parts = cleaned.split(".")
        if all(len(p) == 3 for p in parts[1:]):
            cleaned = cleaned.replace(".", "")
        else:
            # Standard decimal dot
            pass
    elif "," in cleaned:
        # Check if comma is thousands separator or decimal
        parts = cleaned.split(",")
        if all(len(p) == 3 for p in parts[1:]):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")

    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def parse_shopee_sold_count(text: Optional[str]) -> Optional[int]:
    """
    Parses a localized sold volume string into an integer count.
    Handles forms like 'Đã bán 1,2k', '1.5k Đã bán', 'Đã bán 1200', 'Đã bán 1.5tr'.
    Returns None if malformed or non-positive.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned or cleaned.startswith("-"):
        return None

    # Match number with 'k' or 'K' multiplier (e.g. "1.2k", "1,2k", "10k+")
    match_k = re.search(r"([\d.,]+)\s*k", cleaned)
    if match_k:
        num_str = match_k.group(1).replace(",", ".")
        try:
            val = int(round(float(num_str) * 1_000))
            return val if val > 0 else None
        except ValueError:
            return None

    # Match number with 'tr' or 'triệu' multiplier (e.g. "1.5tr", "1,5 triệu")
    match_tr = re.search(r"([\d.,]+)\s*(?:tr|triệu)", cleaned)
    if match_tr:
        num_str = match_tr.group(1).replace(",", ".")
        try:
            val = int(round(float(num_str) * 1_000_000))
            return val if val > 0 else None
        except ValueError:
            return None

    # Match plain integer count (e.g. "đã bán 1200" or "đã bán 1.200")
    match_plain = re.search(r"(?:đã\s*bán\s*)?([\d.,]+)", cleaned)
    if match_plain:
        num_str = match_plain.group(1).replace(".", "").replace(",", "")
        try:
            val = int(num_str)
            return val if val > 0 else None
        except ValueError:
            return None

    return None


def parse_shopee_rating(text: Optional[str]) -> Optional[float]:
    """
    Parses a rating string into a float in [0.0, 5.0].
    Handles forms like '4.8', '4,8', '4.9 / 5', '5.0'.
    Returns None if invalid or out of bounds.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned or cleaned.startswith("-"):
        return None

    # Match rating number (e.g. "4.8" or "4,8" or "4.8/5")
    match = re.search(r"([\d.,]+)(?:\s*/\s*5)?", cleaned)
    if match:
        num_str = match.group(1).replace(",", ".")
        try:
            val = float(num_str)
            if 0.0 <= val <= 5.0:
                return round(val, 2)
        except ValueError:
            return None

    return None


def parse_shopee_review_count(text: Optional[str]) -> Optional[int]:
    """
    Parses a review count from parentheses or review label strings (e.g. '(1.2k)', '(350)').
    Returns None if unparseable or non-positive.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned or cleaned.startswith("-"):
        return None

    # Match within parentheses or standalone with 'k'
    match_k = re.search(r"\(?\s*([\d.,]+)\s*k\s*\)?", cleaned)
    if match_k:
        num_str = match_k.group(1).replace(",", ".")
        try:
            val = int(round(float(num_str) * 1_000))
            return val if val > 0 else None
        except ValueError:
            return None

    match_plain = re.search(r"\(?\s*([\d.,]+)\s*\)?", cleaned)
    if match_plain:
        num_str = match_plain.group(1).replace(".", "").replace(",", "")
        try:
            val = int(num_str)
            return val if val > 0 else None
        except ValueError:
            return None

    return None


def parse_shopee_discount_percent(text: Optional[str]) -> Optional[float]:
    """
    Parses discount percentage string (e.g. '-25%', '25% GIẢM', 'GIẢM 30%').
    Returns float in [0.0, 100.0] or None.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned:
        return None

    match = re.search(r"([\d.,]+)\s*%", cleaned)
    if match:
        num_str = match.group(1).replace(",", ".")
        try:
            val = float(num_str)
            if 0.0 <= val <= 100.0:
                return round(val, 2)
        except ValueError:
            return None

    return None


def extract_shopee_product_id(
    url_or_href: Optional[str],
    item_id_attr: Optional[str] = None,
) -> Optional[str]:
    """
    Extracts the stable Shopee product/item ID from URL or attribute.
    Handles URL patterns:
      - '-i.{shop_id}.{item_id}'
      - '/product/{shop_id}/{item_id}'
      - '/item/{item_id}'
    """
    if item_id_attr and item_id_attr.strip().isdigit():
        return item_id_attr.strip()

    if not url_or_href:
        return None

    # Pattern 1: -i.{shop_id}.{item_id}
    m1 = re.search(r"-i\.(\d+)\.(\d+)", url_or_href)
    if m1:
        return m1.group(2)

    # Pattern 2: /product/{shop_id}/{item_id}
    m2 = re.search(r"/product/(\d+)/(\d+)", url_or_href)
    if m2:
        return m2.group(2)

    # Pattern 3: /item/{item_id}
    m3 = re.search(r"/item/(\d+)", url_or_href)
    if m3:
        return m3.group(1)

    return None


def build_shopee_candidate_id(source_product_id: Optional[str], url: str) -> str:
    """
    Generates a deterministic candidate ID.
    Prefers 'shopee_{source_product_id}' when available, otherwise derives a SHA-256 fingerprint.
    Never uses Python's process-randomized hash().
    """
    if source_product_id:
        return f"shopee_{source_product_id}"

    # Normalize URL by removing query parameters and trailing slashes
    clean_url = url.strip().split("?")[0].rstrip("/")
    digest = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:16]
    return f"shopee_url_{digest}"


def build_shopee_search_url(query: str, page: int = 1) -> str:
    """
    Builds a deterministic URL-encoded Shopee search URL.
    """
    encoded_query = urllib.parse.quote_plus(query.strip())
    if page <= 1:
        return f"https://shopee.vn/search?keyword={encoded_query}"
    return f"https://shopee.vn/search?keyword={encoded_query}&page={page - 1}"
