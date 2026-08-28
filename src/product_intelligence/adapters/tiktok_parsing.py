from __future__ import annotations

import hashlib
import re
import urllib.parse
from typing import Optional


def parse_tiktok_price(text: Optional[str]) -> Optional[float]:
    """
    Parses a localized TikTok Shop price string into a float.
    Handles ranges (returns lower bound), currency symbols (₫, đ, VND, $, £, etc.), and multiplier suffixes (k, tr, m).
    Returns None if malformed, negative, zero, or non-positive.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned:
        return None

    # If price range (e.g. "₫150.000 - ₫200.000" or "150k - 200k" or "10.00 - 20.00"), take the first part
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        if len(parts) == 2 and parts[0].strip():
            cleaned = parts[0].strip()

    # Reject any explicitly negative price (e.g. "-150", "-150k", "₫-150.000", "Price: -150k", "-$19.99", "$-19.99")
    if re.search(r"-\s*[\$₫đ£€¥]?\s*\d", cleaned) or re.search(r"[\$₫đ£€¥]\s*-\s*\d", cleaned) or re.search(r"(?:^|[^\w\d])-\s*[\d]", cleaned):
        return None

    # Handle 'tr' or 'triệu' or 'm' / 'mil' suffix (e.g. "1.5tr", "1,5 triệu", "1.5m")
    match_tr = re.search(r"([\d.,]+)\s*(?:tr|triệu|m|mil)\b", cleaned)
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

    # Remove currency symbols, common currency codes, and whitespace
    cleaned = re.sub(r"[₫đvnd$£€¥\s]", "", cleaned)

    # If starts with negative sign or contains hyphen after cleanup
    if cleaned.startswith("-") or "-" in cleaned:
        return None

    if not cleaned:
        return None

    # In localized formats, check dot and comma
    if "." in cleaned and "," in cleaned:
        # e.g. "150.000,50" -> 150000.50 or "1,500.00" -> 1500.00
        first_dot = cleaned.find(".")
        first_comma = cleaned.find(",")
        if first_dot < first_comma:
            # European/Vietnamese convention: '.' thousands, ',' decimal
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # US/UK convention: ',' thousands, '.' decimal
            cleaned = cleaned.replace(",", "")
    elif "." in cleaned:
        parts = cleaned.split(".")
        # If multiple dots or single dot with exactly 3 digits after (and part before is integer) -> thousands separator
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1 and parts[0].isdigit() and parts[1].isdigit()):
            cleaned = cleaned.replace(".", "")
        else:
            # Standard decimal dot
            pass
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1 and parts[0].isdigit() and parts[1].isdigit()):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")

    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def parse_tiktok_sold_count(text: Optional[str]) -> Optional[int]:
    """
    Parses a localized sold volume string into an integer count.
    Handles forms like 'Đã bán 1,2k', '1.5k Sold', 'Sold 1200', '1.5k+ sold', 'Đã bán 1.5tr'.
    Returns None if malformed, zero, negative, or non-positive.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned:
        return None

    # Reject any explicitly negative sold count (e.g. "Đã bán -1200", "-5", "Sold -1.5k")
    if re.search(r"-\s*\d", cleaned):
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

    # Match number with 'tr' or 'triệu' or 'm' multiplier (e.g. "1.5tr", "1,5 triệu", "1.2m")
    match_tr = re.search(r"([\d.,]+)\s*(?:tr|triệu|m\b)", cleaned)
    if match_tr:
        num_str = match_tr.group(1).replace(",", ".")
        try:
            val = int(round(float(num_str) * 1_000_000))
            return val if val > 0 else None
        except ValueError:
            return None

    # Match plain integer count (e.g. "đã bán 1200" or "đã bán 1.200" or "1,200 sold")
    match_plain = re.search(r"([\d.,]+)", cleaned)
    if match_plain:
        num_str = match_plain.group(1).replace(".", "").replace(",", "")
        try:
            val = int(num_str)
            return val if val > 0 else None
        except ValueError:
            return None

    return None


def parse_tiktok_rating(text: Optional[str]) -> Optional[float]:
    """
    Parses a rating string into a float in [0.0, 5.0].
    Handles forms like '4.8', '4,8', '4.9 / 5', '5.0', '4.5/5'.
    Returns None if invalid or out of bounds.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned:
        return None

    # Reject negative ratings (e.g. "-4.8", "Rating: -4.8", "-4.5/5")
    if re.search(r"-\s*\d", cleaned):
        return None

    # Match rating number (e.g. "4.8" or "4,8" or "4.8/5")
    match = re.search(r"([\d.,]+)(?:\s*/\s*5(?:\.0)?)?", cleaned)
    if match:
        num_str = match.group(1).replace(",", ".")
        try:
            val = float(num_str)
            if 0.0 <= val <= 5.0:
                return round(val, 2)
        except ValueError:
            return None

    return None


def parse_tiktok_review_count(text: Optional[str]) -> Optional[int]:
    """
    Parses a review count from parentheses or review label strings (e.g. '(1.2k)', '(350)', '350 reviews').
    Returns None if unparseable, zero, negative, or non-positive.
    """
    if not text:
        return None

    cleaned = text.strip().lower()
    if not cleaned:
        return None

    # Reject negative review counts (e.g. "(-350)", "-350 reviews", "Đánh giá: -1.2k")
    if re.search(r"-\s*\d", cleaned):
        return None

    # Match within parentheses or standalone with 'k'
    match_k = re.search(r"\(?\s*([\d.,]+)\s*k\s*(?:reviews|đánh giá|nhận xét)?\s*\)?", cleaned)
    if match_k:
        num_str = match_k.group(1).replace(",", ".")
        try:
            val = int(round(float(num_str) * 1_000))
            return val if val > 0 else None
        except ValueError:
            return None

    match_plain = re.search(r"\(?\s*([\d.,]+)\s*(?:reviews|đánh giá|nhận xét)?\s*\)?", cleaned)
    if match_plain:
        num_str = match_plain.group(1).replace(".", "").replace(",", "")
        try:
            val = int(num_str)
            return val if val > 0 else None
        except ValueError:
            return None

    return None


def parse_tiktok_discount_percent(text: Optional[str]) -> Optional[float]:
    """
    Parses discount percentage string (e.g. '-25%', '25% OFF', 'GIẢM 30%', '30%').
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


def extract_tiktok_product_id(
    url_or_href: Optional[str],
    item_id_attr: Optional[str] = None,
) -> Optional[str]:
    """
    Extracts the stable TikTok Shop product/item ID from URL or attribute.
    Handles URL patterns:
      - '/product/{id}'
      - '/item/{id}'
      - 'itemId={id}', 'item_id={id}', 'product_id={id}', 'productId={id}'
    """
    if item_id_attr and item_id_attr.strip().isdigit():
        return item_id_attr.strip()

    if not url_or_href:
        return None

    # Pattern 1: /product/{id}
    m1 = re.search(r"/product/(\d+)", url_or_href)
    if m1:
        return m1.group(1)

    # Pattern 2: /item/{id}
    m2 = re.search(r"/item/(\d+)", url_or_href)
    if m2:
        return m2.group(1)

    # Pattern 3: itemId={id} or item_id={id} or product_id={id} or productId={id}
    m3 = re.search(r"(?:itemId|item_id|product_id|productId)=(\d+)", url_or_href, re.IGNORECASE)
    if m3:
        return m3.group(1)

    return None


def build_tiktok_candidate_id(source_product_id: Optional[str], url: str) -> str:
    """
    Generates a deterministic candidate ID.
    Prefers 'tiktok_{source_product_id}' when available, otherwise extracts a product ID discoverable from the URL,
    and otherwise derives a SHA-256 fingerprint from the URL with fragments removed.
    Never uses Python's process-randomized hash().
    """
    if source_product_id:
        return f"tiktok_{source_product_id}"

    extracted_id = extract_tiktok_product_id(url)
    if extracted_id:
        return f"tiktok_{extracted_id}"

    # Normalize URL by removing fragments and stripping whitespace / trailing slashes
    clean_url = url.strip().split("#")[0].rstrip("/")
    digest = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:16]
    return f"tiktok_url_{digest}"


def build_tiktok_search_url(query: str, page: int = 1, locale: str = "vi-VN") -> str:
    """
    Builds a deterministic URL-encoded TikTok Shop search URL.
    Validates that query is non-empty string and page is a positive integer (page >= 1).
    Rejects bool, float, zero, negative, and other non-integer values.
    Raises ValueError on invalid inputs.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query must be a non-empty string.")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("Page must be a positive integer >= 1.")

    encoded_query = urllib.parse.quote_plus(query.strip())
    # TikTok Shop search URL structure
    if page <= 1:
        return f"https://www.tiktok.com/shop/search?q={encoded_query}"
    return f"https://www.tiktok.com/shop/search?q={encoded_query}&page={page}"
