"""Attach-only structural diagnostic for the fixed TASK-233 TikTok PDP.

This carrier has evidence authority NONE.  It emits bounded selector-discovery hints,
never ProductCandidateSnapshot values, and delegates borrowed-session cleanup to the
existing browser manager lifecycle authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Callable, Mapping, Protocol
from urllib.parse import urlsplit

from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.product_intelligence.adapters.tiktok_parsing import extract_tiktok_product_id


DIAGNOSTIC_CONTEXT_ID = "p8-pilot-001-led-motion-tiktok-vn"
DIAGNOSTIC_SOURCE_ID = "1731381331718341815"
ARTIFACT_FILENAME = "tiktok-pdp-dom-diagnostic-v1.json"
_SESSION_RUN_ID = f"human-dom-diagnostic:{DIAGNOSTIC_CONTEXT_ID}"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_HINTS = (
    "TITLE_LIKE",
    "SHOP_LIKE",
    "CURRENT_PRICE_LIKE",
    "ORIGINAL_PRICE_LIKE",
    "DISCOUNT_LIKE",
    "SOLD_LIKE",
    "RATING_LIKE",
    "REVIEW_LIKE",
)
_CANDIDATE_KEYS = {
    "field_hint",
    "text_excerpt",
    "tag_name",
    "class_tokens",
    "data-testid",
    "data-e2e",
    "aria-label",
    "role",
    "itemprop",
    "parent_signature",
    "grandparent_signature",
}
_MAX_PER_HINT = 3
_MAX_CANDIDATES = len(_HINTS) * _MAX_PER_HINT
_MAX_EXCERPT = 120
_MAX_ATTRIBUTE = 80
_MAX_SIGNATURE = 120
_MAX_CLASS_TOKENS = 4
_MAX_CLASS_TOKEN = 48

BLOCKED_OR_CHALLENGE = "BLOCKED_OR_CHALLENGE"
LOGIN_GATE = "LOGIN_GATE"
LISTING_UNAVAILABLE = "LISTING_UNAVAILABLE"
NO_BOUNDED_PDP_ROOT = "NO_BOUNDED_PDP_ROOT"
IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
MALFORMED_DIAGNOSTIC_PAYLOAD = "MALFORMED_DIAGNOSTIC_PAYLOAD"


class TikTokPdpDomDiagnosticError(RuntimeError):
    """Fail-closed diagnostic error that never contains operator secrets."""


class TikTokPdpDomDiagnosticJobRootError(TikTokPdpDomDiagnosticError):
    """The external artifact boundary is missing or unsafe."""


class TikTokPdpDomDiagnosticArtifactExistsError(TikTokPdpDomDiagnosticError):
    """The fixed diagnostic artifact already exists."""


class _Session(Protocol):
    async def evaluate(self, script: str): ...


class _SessionManager(Protocol):
    async def get_or_create_session(self, run_id: str) -> _Session: ...

    async def close_session(self, run_id: str) -> None: ...


@dataclass(frozen=True)
class TikTokPdpDomDiagnosticOutcome:
    artifact_path: Path
    document: Mapping[str, object]

    def to_document(self) -> dict[str, object]:
        return dict(self.document)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_external_job_root(job_root: str | Path) -> Path:
    if not isinstance(job_root, (str, Path)) or not str(job_root).strip():
        raise TikTokPdpDomDiagnosticJobRootError(
            "an explicit external diagnostic job root is required"
        )
    try:
        resolved = Path(job_root).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise TikTokPdpDomDiagnosticJobRootError(
            "the external diagnostic job root could not be resolved"
        ) from exc
    if resolved == _REPOSITORY_ROOT or _REPOSITORY_ROOT in resolved.parents:
        raise TikTokPdpDomDiagnosticJobRootError(
            "the diagnostic job root must be outside the Git repository"
        )
    return resolved


# One evaluation only. It never navigates or interacts. Root discovery is URL-bound,
# capped, and refuses body/html as an output surface.
DIAGNOSTIC_SCRIPT = r"""
() => {
  const clip = (value, limit) => String(value || '').replace(/\s+/g, ' ').trim().slice(0, limit);
  const signature = (element) => {
    if (!element) return '';
    const classes = Array.from(element.classList || []).slice(0, 2).map(v => clip(v, 48));
    return clip([String(element.tagName || '').toLowerCase(), ...classes].filter(Boolean).join('.'), 120);
  };
  const visible = (element) => {
    if (!element || typeof element.getBoundingClientRect !== 'function') return false;
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const firstVisible = (scope, selectors, cap) => {
    const found = [];
    for (const selector of selectors) {
      for (const node of Array.from(scope.querySelectorAll(selector)).slice(0, cap)) {
        if (visible(node) && !found.includes(node)) found.push(node);
        if (found.length >= cap) return found;
      }
    }
    return found;
  };
  const pdpRootSelector = '[data-e2e*="pdp" i], [data-testid*="pdp" i], [itemtype*="Product"]';
  let root = null;
  let rootKind = 'NONE';
  const titleText = clip(document.title, 200).toLowerCase();
  const url = String(window.location.href || '');
  const hasVisibleMarker = (selectors) => selectors.some(selector =>
    Array.from(document.querySelectorAll(selector)).slice(0, 4).some(visible)
  );
  const blocked = /captcha|challenge|verify|security check|robot/.test(titleText) || hasVisibleMarker([
    'iframe[src*="captcha" i]', 'iframe[src*="challenge" i]',
    '[data-e2e*="captcha" i]', '[data-testid*="captcha" i]',
    '[data-e2e*="challenge" i]', '[data-testid*="challenge" i]',
    '[id*="captcha" i]', '[aria-label*="security check" i]'
  ]);
  const login = /\/login(?:[/?#]|$)/i.test(url) || /log in|login|sign in|đăng nhập/.test(titleText) ||
    hasVisibleMarker([
      'form[action*="/login" i]', 'input[type="password"]',
      '[data-e2e*="login" i]', '[data-testid*="login" i]',
      '[aria-label*="log in" i]', '[aria-label*="sign in" i]'
    ]);
  let identityBound = false;
  try {
    const current = new URL(url);
    const match = current.pathname.match(/^\/[a-z]{2}\/pdp\/[^/]+\/(\d+)\/?$/i);
    identityBound = /^https?:$/.test(current.protocol) &&
      current.hostname.toLowerCase() === 'shop.tiktok.com' &&
      Boolean(match) && match[1] === '1731381331718341815';
  } catch (_) {
    identityBound = false;
  }
  const unavailable = /(?:product|item|listing).{0,32}(?:not available|unavailable)|(?:not available|unavailable).{0,32}(?:product|item|listing)/i.test(titleText) ||
    hasVisibleMarker([
      '[data-e2e="product-unavailable" i]', '[data-testid="product-unavailable" i]',
      '[data-e2e="listing-unavailable" i]', '[data-testid="listing-unavailable" i]',
      '[role="alert"][data-e2e*="unavailable" i]', '[role="alert"][data-testid*="unavailable" i]',
      '[aria-label="product unavailable" i]', '[aria-label="listing unavailable" i]'
    ]);
  const titleSelectors = [
    'h1', '[role="heading"][aria-level="1"]', '[data-e2e*="title" i]',
    '[data-testid*="title" i]', '[itemprop="name"]'
  ];
  const priceSelectors = [
    '[data-e2e*="price" i]', '[data-testid*="price" i]', '[itemprop="price"]',
    '[class*="price" i]'
  ];
  const actionSelectors = [
    'button[data-e2e*="buy" i]', 'button[data-testid*="buy" i]',
    'button[data-e2e*="cart" i]', 'button[data-testid*="cart" i]',
    '[data-e2e*="quantity" i]', '[data-testid*="quantity" i]',
    '[data-e2e*="variant" i]', '[data-testid*="variant" i]',
    '[role="radiogroup"]', 'select'
  ];
  const hasCommerceAnchors = (scope) => {
    const titles = firstVisible(scope, titleSelectors, 4);
    const prices = firstVisible(scope, priceSelectors, 4);
    const actions = firstVisible(scope, actionSelectors, 4);
    return titles.some(title => prices.some(price => actions.some(action =>
      title !== price && title !== action && price !== action
    )));
  };
  if (identityBound && !blocked && !login && !unavailable) {
    for (const candidate of Array.from(document.querySelectorAll(pdpRootSelector)).slice(0, 8)) {
      if (candidate !== document.body && candidate !== document.documentElement && visible(candidate) && hasCommerceAnchors(candidate)) {
        root = candidate;
        rootKind = 'EXPLICIT_PDP_ROOT';
        break;
      }
    }
    if (!root) {
      const main = document.querySelector('main');
      if (main && visible(main) && hasCommerceAnchors(main)) {
        root = main;
        rootKind = 'MAIN';
      }
    }
    if (!root && document.body) {
      const titles = firstVisible(document.body, titleSelectors, 12);
      const prices = firstVisible(document.body, priceSelectors, 12);
      const actions = firstVisible(document.body, actionSelectors, 12);
      const ancestorChain = (node) => {
        const chain = [];
        let current = node;
        while (current && chain.length < 8) {
          if (current === document.body || current === document.documentElement) break;
          chain.push(current);
          current = current.parentElement;
        }
        return chain;
      };
      outer: for (const title of titles) {
        const titleAncestors = ancestorChain(title);
        for (const price of prices) {
          const priceAncestors = new Set(ancestorChain(price));
          for (const action of actions) {
            if (title === price || title === action || price === action) continue;
            const actionAncestors = new Set(ancestorChain(action));
            const common = titleAncestors.find(node => priceAncestors.has(node) && actionAncestors.has(node));
            if (common && visible(common)) {
              root = common;
              rootKind = 'MULTI_ANCHOR_COMMON_ANCESTOR';
              break outer;
            }
          }
        }
      }
    }
  }
  const ids = [];
  const identityNodes = root ? [root] : [];
  if (root && root.matches(pdpRootSelector)) {
    for (const node of Array.from(root.querySelectorAll(
        'meta[property="product:retailer_item_id"], meta[itemprop="productID"], [itemprop="productID"]')).slice(0, 4)) {
      if (node.closest(pdpRootSelector) === root) identityNodes.push(node);
    }
  }
  for (const node of identityNodes.slice(0, 4)) {
    const itempropValue = String(node.getAttribute('itemprop') || '').toLowerCase() === 'productid'
      ? node.textContent : '';
    const value = clip(
      node.getAttribute('content') || node.getAttribute('data-product-id') || node.getAttribute('data-item-id') ||
      itempropValue,
      32
    );
    if (/^\d+$/.test(value) && !ids.includes(value)) ids.push(value);
  }
  const rules = [
    ['TITLE_LIKE', /title|product.name|product-title|pdp-title/i, /^h1$/i],
    ['SHOP_LIKE', /shop|seller|store/i, /shop|seller|store/i],
    ['CURRENT_PRICE_LIKE', /sale.price|current.price|product.price|price-current/i, /₫|đ|vnd/i],
    ['ORIGINAL_PRICE_LIKE', /original.price|list.price|price-original/i, /₫|đ|vnd/i],
    ['DISCOUNT_LIKE', /discount|promotion/i, /-?\s*\d{1,3}\s*%/i],
    ['SOLD_LIKE', /sold|sales/i, /đã bán|sold/i],
    ['RATING_LIKE', /rating|star/i, /\b[0-5](?:[.,]\d)?\b/i],
    ['REVIEW_LIKE', /review|comment/i, /đánh giá|review/i],
  ];
  const candidates = [];
  const counts = Object.fromEntries(rules.map(rule => [rule[0], 0]));
  const nodes = root ? [root, ...Array.from(root.querySelectorAll('*')).slice(0, 399)] : [];
  for (let index = 0; index < nodes.length && candidates.length < 24; index += 1) {
    const element = nodes[index];
    if (!visible(element)) continue;
    const text = clip(element.innerText || element.textContent, 120);
    if (!text) continue;
    const structural = clip([
      element.getAttribute('data-testid'), element.getAttribute('data-e2e'),
      element.getAttribute('aria-label'), element.getAttribute('role'),
      element.getAttribute('itemprop'), element.className
    ].join(' '), 400);
    for (const [hint, structuralPattern, textPattern] of rules) {
      if (counts[hint] >= 3 || (!structuralPattern.test(structural) && !textPattern.test(text))) continue;
      candidates.push({
        field_hint: hint,
        text_excerpt: text,
        tag_name: clip(element.tagName, 24).toLowerCase(),
        class_tokens: Array.from(element.classList || []).slice(0, 4).map(v => clip(v, 48)),
        'data-testid': clip(element.getAttribute('data-testid'), 80),
        'data-e2e': clip(element.getAttribute('data-e2e'), 80),
        'aria-label': clip(element.getAttribute('aria-label'), 80),
        role: clip(element.getAttribute('role'), 80),
        itemprop: clip(element.getAttribute('itemprop'), 80),
        parent_signature: signature(element.parentElement),
        grandparent_signature: signature(element.parentElement && element.parentElement.parentElement),
      });
      counts[hint] += 1;
    }
  }
  const hintOrder = Object.fromEntries(rules.map((rule, index) => [rule[0], index]));
  candidates.sort((left, right) => hintOrder[left.field_hint] - hintOrder[right.field_hint]);
  return {
    schema_version: 1,
    observed_url: url,
    explicit_product_ids: ids,
    page_state: {
      identity_bound: identityBound,
      has_bounded_root: Boolean(root),
      root_kind: rootKind,
      blocked,
      login,
      unavailable
    },
    candidates,
  };
}
"""


def _bounded_string(value: object, maximum: int) -> bool:
    return isinstance(value, str) and len(value) <= maximum


def _validate_candidate(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _CANDIDATE_KEYS:
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    if value["field_hint"] not in _HINTS:
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    limits = {
        "text_excerpt": _MAX_EXCERPT,
        "tag_name": 24,
        "data-testid": _MAX_ATTRIBUTE,
        "data-e2e": _MAX_ATTRIBUTE,
        "aria-label": _MAX_ATTRIBUTE,
        "role": _MAX_ATTRIBUTE,
        "itemprop": _MAX_ATTRIBUTE,
        "parent_signature": _MAX_SIGNATURE,
        "grandparent_signature": _MAX_SIGNATURE,
    }
    if any(not _bounded_string(value[key], limit) for key, limit in limits.items()):
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    tokens = value["class_tokens"]
    if (
        not isinstance(tokens, list)
        or len(tokens) > _MAX_CLASS_TOKENS
        or any(not _bounded_string(token, _MAX_CLASS_TOKEN) for token in tokens)
    ):
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    return dict(value)


def _validate_payload(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version", "observed_url", "explicit_product_ids", "page_state", "candidates"
    }:
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    if payload["schema_version"] != 1 or not _bounded_string(payload["observed_url"], 2048):
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    state = payload["page_state"]
    if (
        not isinstance(state, dict)
        or set(state) != {
            "identity_bound", "has_bounded_root", "root_kind", "blocked", "login", "unavailable"
        }
        or any(
            not isinstance(state[key], bool)
            for key in ("identity_bound", "has_bounded_root", "blocked", "login", "unavailable")
        )
        or not isinstance(state["root_kind"], str)
        or state["root_kind"] not in {
            "NONE", "EXPLICIT_PDP_ROOT", "MAIN", "MULTI_ANCHOR_COMMON_ANCESTOR"
        }
        or state["has_bounded_root"] != (state["root_kind"] != "NONE")
    ):
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    if state["blocked"]:
        raise TikTokPdpDomDiagnosticError(BLOCKED_OR_CHALLENGE)
    if state["login"]:
        raise TikTokPdpDomDiagnosticError(LOGIN_GATE)
    if state["unavailable"]:
        raise TikTokPdpDomDiagnosticError(LISTING_UNAVAILABLE)
    explicit_ids = payload["explicit_product_ids"]
    if (
        not isinstance(explicit_ids, list)
        or len(explicit_ids) > 4
        or any(not isinstance(item, str) or not item.isdigit() or len(item) > 32 for item in explicit_ids)
    ):
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    observed_url = payload["observed_url"]
    try:
        parsed_url = urlsplit(observed_url)
        hostname = parsed_url.hostname or ""
    except ValueError as exc:
        raise TikTokPdpDomDiagnosticError(IDENTITY_MISMATCH) from exc
    pdp_path_match = re.fullmatch(
        r"/[a-z]{2}/pdp/[^/]+/(?P<product_id>\d+)/?",
        parsed_url.path,
        flags=re.IGNORECASE,
    )
    if (
        parsed_url.scheme.lower() not in {"http", "https"}
        or hostname.lower() != "shop.tiktok.com"
        or pdp_path_match is None
    ):
        raise TikTokPdpDomDiagnosticError(IDENTITY_MISMATCH)
    path_product_id = pdp_path_match.group("product_id")
    extracted_url_id = extract_tiktok_product_id(observed_url)
    observed_id = extracted_url_id if extracted_url_id == path_product_id else None
    if not state["identity_bound"] or observed_id != DIAGNOSTIC_SOURCE_ID:
        raise TikTokPdpDomDiagnosticError(IDENTITY_MISMATCH)
    if not state["has_bounded_root"]:
        raise TikTokPdpDomDiagnosticError(NO_BOUNDED_PDP_ROOT)
    candidates_raw = payload["candidates"]
    if not isinstance(candidates_raw, list) or len(candidates_raw) > _MAX_CANDIDATES:
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    candidates = [_validate_candidate(item) for item in candidates_raw]
    expected_order = {hint: index for index, hint in enumerate(_HINTS)}
    if candidates != sorted(candidates, key=lambda item: expected_order[item["field_hint"]]):
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    counts = {hint: 0 for hint in _HINTS}
    for item in candidates:
        counts[item["field_hint"]] += 1
    if any(count > _MAX_PER_HINT for count in counts.values()):
        raise TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)
    return candidates


async def run_tiktok_pdp_dom_diagnostic(
    *,
    job_root: str | Path,
    cdp_endpoint: str,
    clock: Callable[[], datetime] = _utc_now,
    manager_factory: Callable[..., _SessionManager] = PlaywrightBrowserManager,
) -> TikTokPdpDomDiagnosticOutcome:
    """Inspect the already-open fixed PDP once without navigation or interaction."""

    root = _resolve_external_job_root(job_root)
    artifact_path = root / ARTIFACT_FILENAME
    if artifact_path.exists():
        raise TikTokPdpDomDiagnosticArtifactExistsError(
            "the fixed diagnostic artifact already exists"
        )
    if not isinstance(cdp_endpoint, str) or not cdp_endpoint.strip():
        raise TikTokPdpDomDiagnosticError("an explicit operator-owned CDP endpoint is required")
    observed_at = clock()
    if not isinstance(observed_at, datetime) or observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise TikTokPdpDomDiagnosticError("the diagnostic timestamp must be timezone-aware")

    try:
        manager = manager_factory(cdp_endpoint=cdp_endpoint)
        session = await manager.get_or_create_session(_SESSION_RUN_ID)
    except Exception as exc:
        raise TikTokPdpDomDiagnosticError(
            "the operator-owned browser session could not be borrowed"
        ) from exc

    operation_error: BaseException | None = None
    try:
        try:
            payload = await session.evaluate(DIAGNOSTIC_SCRIPT)
        except Exception as exc:
            raise TikTokPdpDomDiagnosticError(
                "the bounded current-page evaluation failed"
            ) from exc
        candidates = _validate_payload(payload)
        document: dict[str, object] = {
            "schema_version": 1,
            "diagnostic": {
                "status": "SUCCESS",
                "classification": "ATTACH_ONLY_BOUNDED_DOM_DIAGNOSTIC",
                "context_id": DIAGNOSTIC_CONTEXT_ID,
                "source_product_id": DIAGNOSTIC_SOURCE_ID,
                "observed_at": observed_at.isoformat(),
                "evidence_authority": "NONE",
                "candidate_count": len(candidates),
            },
            "candidates": candidates,
        }
        try:
            root.mkdir(parents=True, exist_ok=True)
            with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(document, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        except FileExistsError as exc:
            raise TikTokPdpDomDiagnosticArtifactExistsError(
                "the fixed diagnostic artifact already exists"
            ) from exc
        except OSError as exc:
            raise TikTokPdpDomDiagnosticJobRootError(
                "the diagnostic artifact could not be created"
            ) from exc
    except BaseException as exc:
        operation_error = exc
        raise
    finally:
        try:
            await manager.close_session(_SESSION_RUN_ID)
        except Exception as exc:
            if operation_error is None:
                raise TikTokPdpDomDiagnosticError(
                    "the borrowed browser session could not be released"
                ) from exc

    return TikTokPdpDomDiagnosticOutcome(artifact_path=artifact_path, document=document)


__all__ = [
    "ARTIFACT_FILENAME",
    "BLOCKED_OR_CHALLENGE",
    "DIAGNOSTIC_CONTEXT_ID",
    "DIAGNOSTIC_SCRIPT",
    "DIAGNOSTIC_SOURCE_ID",
    "IDENTITY_MISMATCH",
    "LISTING_UNAVAILABLE",
    "LOGIN_GATE",
    "MALFORMED_DIAGNOSTIC_PAYLOAD",
    "NO_BOUNDED_PDP_ROOT",
    "TikTokPdpDomDiagnosticArtifactExistsError",
    "TikTokPdpDomDiagnosticError",
    "TikTokPdpDomDiagnosticJobRootError",
    "TikTokPdpDomDiagnosticOutcome",
    "run_tiktok_pdp_dom_diagnostic",
]
