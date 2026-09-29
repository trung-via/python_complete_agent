"""Human-operated attach-only P8 Real Case Evidence Bundle carrier.

Captures one sanitized rendered-page projection plus one full-page visual cross-check
and one manifest from the already-open exact TikTok Shop Vietnam PDP.
Writes exactly three final artifacts create-exclusively to an external job root.

This module owns only carrier-specific orchestration. Browser lifecycle,
parsing, evidence admission, Product Truth, and commerce decisions remain outside.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Callable, Mapping, Protocol
from urllib.parse import urlsplit

from src.browser.models import BrowserConfig
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.product_intelligence.tiktok_pdp_dom_scope import TIKTOK_PDP_DOM_SCOPE_JS


CONTEXT_ID = "p8-pilot-001-led-motion-tiktok-vn"
AUTHORIZED_SOURCE_ID = "1731381331718341815"
AUTHORIZED_PDP_URL = (
    "https://shop.tiktok.com/vn/pdp/"
    "den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815"
)
CLASSIFICATION = "P8_REAL_CASE_SOURCE_OBSERVATION_BUNDLE_ONE_SHOT_ONLY"
EPISTEMIC_BOUNDARY = "BUNDLE_IS_NOT_CANONICAL_EVIDENCE"
SANITATION_POLICY = "P8_BOUNDED_RENDERED_STRUCTURAL_ALLOWLIST_V1"

CASE_BUNDLE_BROWSER_TIMEOUT_SECONDS = 120
CASE_BUNDLE_TIMEOUT_SECONDS = CASE_BUNDLE_BROWSER_TIMEOUT_SECONDS
BROWSER_SESSION_TIMEOUT_SECONDS = CASE_BUNDLE_BROWSER_TIMEOUT_SECONDS

MANIFEST_FILENAME = "p8-real-case-manifest-v1.json"
PROJECTION_FILENAME = "p8-real-case-page-projection-v1.json"
SCREENSHOT_FILENAME = "p8-real-case-full-page-v1.png"

_SESSION_RUN_ID = f"human-case-bundle:{CONTEXT_ID}"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_MAX_SCANNED_NODES = 2000
_MAX_RECORDS = 500
_MAX_TEXT_LENGTH = 160
_MAX_SERIALIZED_BYTES = 256 * 1024  # 256 KB
_MAX_ATTRIBUTE = 80
_MAX_TAG_NAME = 24
_MAX_CLASS_TOKENS = 4
_MAX_CLASS_TOKEN = 48
_MAX_CONTEXT = 80

_SAFE_ATOM = re.compile(r"^[A-Za-z0-9_.:/-]*$")
_SAFE_HEADING = re.compile(r"^[^<>{}\\]*$")
_RAW_VALUE = re.compile(r"(?:₫|\bVND\b|\d{4,}|\b\d[\d.,]*\s*(?:₫|VND)\b)", re.I)

_RECORD_KEYS = {
    "ordinal",
    "tag_name",
    "role",
    "itemprop",
    "data-testid",
    "data-e2e",
    "class_tokens",
    "section_heading_context",
    "visible_text",
    "is_leaf",
}

BLOCKED_OR_CHALLENGE = "BLOCKED_OR_CHALLENGE"
LOGIN_GATE = "LOGIN_GATE"
LISTING_UNAVAILABLE = "LISTING_UNAVAILABLE"
IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
MALFORMED_PROJECTION = "MALFORMED_PROJECTION"
POST_MANIFEST_WRITE_FAILURE = "POST_MANIFEST_WRITE_FAILURE"


class TikTokPdpCaseBundleError(RuntimeError):
    """Sanitized failure for the case bundle carrier."""


class TikTokPdpCaseBundleJobRootError(TikTokPdpCaseBundleError):
    """The external job root is missing, inside repository, or inaccessible."""


class TikTokPdpCaseBundleArtifactExistsError(TikTokPdpCaseBundleError):
    """A bundle artifact already exists in the external job root."""


class _Session(Protocol):
    async def evaluate(self, script: str) -> object: ...
    async def screenshot(self) -> bytes: ...


class _SessionManager(Protocol):
    async def get_or_create_session(
        self,
        run_id: str,
        config: BrowserConfig | None = None,
    ) -> _Session: ...
    async def close_session(self, run_id: str) -> None: ...


@dataclass(frozen=True)
class TikTokPdpCaseBundleOutcome:
    manifest_path: Path
    projection_path: Path
    screenshot_path: Path
    manifest: Mapping[str, object]

    def to_document(self) -> dict[str, object]:
        return {
            "bundle": {
                "status": "SUCCESS",
                **self.manifest,
            }
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_external_job_root(job_root: str | Path) -> Path:
    if not isinstance(job_root, (str, Path)) or not str(job_root).strip():
        raise TikTokPdpCaseBundleJobRootError("an explicit external job root is required")
    try:
        resolved = Path(job_root).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise TikTokPdpCaseBundleJobRootError(
            "the external job root could not be resolved"
        ) from exc
    if resolved == _REPOSITORY_ROOT or _REPOSITORY_ROOT in resolved.parents:
        raise TikTokPdpCaseBundleJobRootError(
            "the bundle job root must be outside the Git repository"
        )
    return resolved


CASE_BUNDLE_SCRIPT = (
    r"""() => {
 const MAX_SCANNED = 2000;
 const MAX_RECORDS = 500;
 const MAX_TEXT = 160;
"""
    + TIKTOK_PDP_DOM_SCOPE_JS
    + r"""
 const pageTitle = clip(document.title, 200).toLowerCase(), url = String(location.href || '');
 const marker = ss => ss.some(s => Array.from(document.querySelectorAll(s)).slice(0, 4).some(visible));
 const blocked = /captcha|challenge|verify|security check|robot/.test(pageTitle) || marker([
   'iframe[src*="captcha" i]', 'iframe[src*="challenge" i]',
   '[data-e2e*="captcha" i]', '[data-testid*="captcha" i]',
   '[data-e2e*="challenge" i]', '[data-testid*="challenge" i]',
   '[id*="captcha" i]', '[aria-label*="security check" i]'
 ]);
 const login = /\/login(?:[/?#]|$)/i.test(url) || /log in|login|sign in|đăng nhập/.test(pageTitle) || marker([
   'form[action*="/login" i]', 'input[type="password"]',
   '[data-e2e*="login" i]', '[data-testid*="login" i]',
   '[aria-label*="log in" i]', '[aria-label*="sign in" i]'
 ]);
 let identity = false;
 try {
   const u = new URL(url);
   const m = u.pathname.match(/^\/vn\/pdp\/[^/]+\/(\d+)\/?$/i);
   identity = u.protocol === 'https:' && u.hostname.toLowerCase() === 'shop.tiktok.com' && Boolean(m) && m[1] === '1731381331718341815';
 } catch(_) {
   identity = false;
 }
 const unavailable = /(?:product|item|listing).{0,32}(?:not available|unavailable)|(?:not available|unavailable).{0,32}(?:product|item|listing)/i.test(pageTitle) || marker([
   '[data-e2e="product-unavailable" i]', '[data-testid="product-unavailable" i]',
   '[data-e2e="listing-unavailable" i]', '[data-testid="listing-unavailable" i]',
   '[role="alert"][data-e2e*="unavailable" i]', '[role="alert"][data-testid*="unavailable" i]',
   '[aria-label="product unavailable" i]', '[aria-label="listing unavailable" i]'
 ]);

 if (!identity || blocked || login || unavailable) {
   return {
     schema_version: 1,
     observed_url: url,
     page_state: {
       identity_bound: identity,
       blocked: Boolean(blocked),
       login: Boolean(login),
       unavailable: Boolean(unavailable)
     },
     truncation: {
       is_truncated: false,
       scanned_nodes_truncated: false,
       records_truncated: false,
       text_truncated: false,
       bytes_truncated: false,
       total_scanned_nodes: 0,
       total_records: 0
     },
     records: []
   };
 }

 const scope = resolveBoundedPdpDomScope();
 const root = scope.root;
 const targetRoot = root || document.body || document.documentElement;

 const isExcludedRegion = e => {
   let cur = e;
   while (cur && cur !== targetRoot && cur !== document.body && cur !== document.documentElement) {
     const tag = String(cur.tagName || '').toLowerCase();
     if (['header', 'nav', 'footer', 'aside'].includes(tag)) return true;
     const role = String(cur.getAttribute('role') || '').toLowerCase();
     if (['navigation', 'banner', 'contentinfo'].includes(role)) return true;
     const attrs = [
       cur.getAttribute('data-e2e'),
       cur.getAttribute('data-testid'),
       cur.getAttribute('id'),
       cur.getAttribute('aria-label'),
       typeof cur.className === 'string' ? cur.className : ''
     ].filter(Boolean).join(' ').toLowerCase();
     if (
       /\b(?:account|profile|session|user-info|user-profile|user-name|username|user-avatar|avatar|top-nav|site-nav|global-nav|navbar|nav-bar|navigation|bottom-nav|login|signin|sign-in|logout|sign-out)\b/i.test(attrs) ||
       /(?:account|profile|session|avatar|user[-_](?:info|profile|name|avatar))/i.test(cur.getAttribute('data-e2e') || '') ||
       /(?:account|profile|session|avatar|user[-_](?:info|profile|name|avatar))/i.test(cur.getAttribute('data-testid') || '')
     ) {
       return true;
     }
     cur = cur.parentElement;
   }
   return false;
 };

 const skippedTags = new Set(['script', 'style', 'noscript', 'template', 'svg', 'iframe', 'header', 'nav', 'footer', 'aside']);
 const records = [];
 let scannedCount = 0;
 let scannedTruncated = false;
 let recordsTruncated = false;
 let textTruncated = false;

 const walker = document.createTreeWalker(
   targetRoot,
   NodeFilter.SHOW_ELEMENT
 );

 let current = walker.currentNode;
 while (current && scannedCount < MAX_SCANNED) {
   scannedCount++;
   const tag = String(current.tagName || '').toLowerCase();
   if (!skippedTags.has(tag) && visible(current) && !isExcludedRegion(current)) {
     let headingCtx = null;
     let p = current;
     for (let i = 0; i < 4 && p; i++) {
       const h = p.querySelector ? p.querySelector('h1, h2, h3, [role="heading"]') : null;
       if (h && visible(h) && !isExcludedRegion(h)) {
         headingCtx = clip(h.textContent, 60);
         break;
       }
       p = p.parentElement;
     }

     const directTextNodes = Array.from(current.childNodes || [])
       .filter(n => n.nodeType === Node.TEXT_NODE)
       .slice(0, 8);
     const rawDirectText = directTextNodes.map(n => n.nodeValue || '').join(' ');
     const clippedText = clip(rawDirectText, MAX_TEXT);
     if (rawDirectText.length > MAX_TEXT) {
       textTruncated = true;
     }

     const role = atom(current.getAttribute('role'), 80);
     const itemprop = atom(current.getAttribute('itemprop'), 80);
     const testid = atom(current.getAttribute('data-testid'), 80);
     const dataE2e = atom(current.getAttribute('data-e2e'), 80);
     const classTokens = tokens(current);
     const hasStructuralAttrs = Boolean(role || itemprop || testid || dataE2e);

     if (clippedText || hasStructuralAttrs || ['h1', 'h2', 'h3', 'button', 'a', 'select'].includes(tag)) {
       if (records.length < MAX_RECORDS) {
         records.push({
           ordinal: records.length + 1,
           tag_name: atom(tag, 24),
           role: role,
           itemprop: itemprop,
           'data-testid': testid,
           'data-e2e': dataE2e,
           class_tokens: classTokens,
           section_heading_context: headingCtx,
           visible_text: clippedText,
           is_leaf: current.children ? current.children.length === 0 : true
         });
       } else {
         recordsTruncated = true;
       }
     }
   }
   current = walker.nextNode();
 }
 if (current) {
   scannedTruncated = true;
 }

 const isTruncated = scannedTruncated || recordsTruncated || textTruncated;

 return {
   schema_version: 1,
   observed_url: url,
   page_state: {
     identity_bound: identity,
     blocked: false,
     login: false,
     unavailable: false
   },
   truncation: {
     is_truncated: isTruncated,
     scanned_nodes_truncated: scannedTruncated,
     records_truncated: recordsTruncated,
     text_truncated: textTruncated,
     bytes_truncated: false,
     total_scanned_nodes: scannedCount,
     total_records: records.length
   },
   records: records
 };
}"""
)


def _validate_record(record: object, expected_ordinal: int) -> dict[str, object]:
    if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    if record["ordinal"] != expected_ordinal:
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    tag_name = record["tag_name"]
    if (
        not isinstance(tag_name, str)
        or not tag_name
        or len(tag_name) > _MAX_TAG_NAME
        or not _SAFE_ATOM.fullmatch(tag_name)
        or tag_name
        in (
            "script",
            "style",
            "noscript",
            "template",
            "svg",
            "iframe",
            "header",
            "nav",
            "footer",
            "aside",
        )
    ):
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    for key in ("role", "itemprop", "data-testid", "data-e2e"):
        val = record[key]
        if not isinstance(val, str) or len(val) > _MAX_ATTRIBUTE or not _SAFE_ATOM.fullmatch(val):
            raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    tokens = record["class_tokens"]
    if (
        not isinstance(tokens, list)
        or len(tokens) > _MAX_CLASS_TOKENS
        or any(
            not isinstance(tok, str)
            or len(tok) > _MAX_CLASS_TOKEN
            or not _SAFE_ATOM.fullmatch(tok)
            for tok in tokens
        )
    ):
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    heading = record["section_heading_context"]
    if heading is not None and (
        not isinstance(heading, str)
        or len(heading) > _MAX_CONTEXT
        or not _SAFE_HEADING.fullmatch(heading)
    ):
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    text = record["visible_text"]
    if (
        not isinstance(text, str)
        or len(text) > _MAX_TEXT_LENGTH
        or "<script" in text.lower()
        or "<style" in text.lower()
        or "<input" in text.lower()
    ):
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    if not isinstance(record["is_leaf"], bool):
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    return dict(record)


def _validate_projection_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    required_keys = {"schema_version", "observed_url", "page_state", "truncation", "records"}
    if set(payload) != required_keys or payload["schema_version"] != 1:
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    state = payload["page_state"]
    state_keys = {"identity_bound", "blocked", "login", "unavailable"}
    if not isinstance(state, dict) or set(state) != state_keys:
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    if any(not isinstance(state[k], bool) for k in state_keys):
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)

    if state["blocked"]:
        raise TikTokPdpCaseBundleError(BLOCKED_OR_CHALLENGE)
    if state["login"]:
        raise TikTokPdpCaseBundleError(LOGIN_GATE)
    if state["unavailable"]:
        raise TikTokPdpCaseBundleError(LISTING_UNAVAILABLE)
    if not state["identity_bound"]:
        raise TikTokPdpCaseBundleError(IDENTITY_MISMATCH)

    url = payload["observed_url"]
    if not isinstance(url, str) or len(url) > 2048:
        raise TikTokPdpCaseBundleError(IDENTITY_MISMATCH)
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise TikTokPdpCaseBundleError(IDENTITY_MISMATCH) from exc
    match = re.fullmatch(r"/vn/pdp/[^/]+/(?P<product_id>\d+)/?", parsed.path, flags=re.I)
    if (
        parsed.scheme.lower() != "https"
        or (parsed.hostname or "").lower() != "shop.tiktok.com"
        or match is None
        or match.group("product_id") != AUTHORIZED_SOURCE_ID
    ):
        raise TikTokPdpCaseBundleError(IDENTITY_MISMATCH)

    trunc = payload["truncation"]
    trunc_keys = {
        "is_truncated",
        "scanned_nodes_truncated",
        "records_truncated",
        "text_truncated",
        "bytes_truncated",
        "total_scanned_nodes",
        "total_records",
    }
    if not isinstance(trunc, dict) or set(trunc) != trunc_keys:
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    for k in (
        "is_truncated",
        "scanned_nodes_truncated",
        "records_truncated",
        "text_truncated",
        "bytes_truncated",
    ):
        if not isinstance(trunc[k], bool):
            raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    for k in ("total_scanned_nodes", "total_records"):
        if not isinstance(trunc[k], int) or isinstance(trunc[k], bool) or trunc[k] < 0:
            raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)

    raw_records = payload["records"]
    if not isinstance(raw_records, list):
        raise TikTokPdpCaseBundleError(MALFORMED_PROJECTION)
    validated_records = [
        _validate_record(rec, idx + 1) for idx, rec in enumerate(raw_records)
    ]
    return {
        "schema_version": 1,
        "record_type": "P8_REAL_CASE_PAGE_PROJECTION",
        "classification": CLASSIFICATION,
        "context_id": CONTEXT_ID,
        "source_product_id": AUTHORIZED_SOURCE_ID,
        "observed_url": url,
        "page_state": state,
        "truncation": trunc,
        "records": validated_records,
    }


def _prepare_projection_bytes(projection_doc: dict[str, object]) -> bytes:
    json_str = json.dumps(projection_doc, ensure_ascii=False, indent=2)
    payload_bytes = json_str.encode("utf-8") + b"\n"
    if len(payload_bytes) <= _MAX_SERIALIZED_BYTES:
        return payload_bytes

    records = list(projection_doc["records"])
    trunc = dict(projection_doc["truncation"])
    trunc["bytes_truncated"] = True
    trunc["records_truncated"] = True
    trunc["is_truncated"] = True

    while len(payload_bytes) > _MAX_SERIALIZED_BYTES and records:
        records.pop()
        trunc["total_records"] = len(records)
        doc_copy = dict(projection_doc)
        doc_copy["records"] = records
        doc_copy["truncation"] = trunc
        json_str = json.dumps(doc_copy, ensure_ascii=False, indent=2)
        payload_bytes = json_str.encode("utf-8") + b"\n"

    projection_doc["records"] = records
    projection_doc["truncation"] = trunc
    return payload_bytes


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _build_manifest_doc(
    *,
    started_at: datetime,
    observed_at: datetime,
    projection_bytes: bytes,
    screenshot_bytes: bytes,
    truncation_info: Mapping[str, object],
) -> dict[str, object]:
    proj_hash = _sha256(projection_bytes)
    shot_hash = _sha256(screenshot_bytes)
    return {
        "schema_version": 1,
        "bundle_version": 1,
        "record_type": "P8_REAL_CASE_SOURCE_OBSERVATION_BUNDLE_MANIFEST",
        "classification": CLASSIFICATION,
        "context_id": CONTEXT_ID,
        "source_product_id": AUTHORIZED_SOURCE_ID,
        "requested_url": AUTHORIZED_PDP_URL,
        "stable_listing_reference": AUTHORIZED_PDP_URL,
        "capture_started_at": started_at.isoformat(),
        "observed_at": observed_at.isoformat(),
        "execution_owner": "HUMAN_OPERATOR",
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "screenshot_review_status": "HUMAN_REVIEW_REQUIRED",
        "epistemic_boundary": EPISTEMIC_BOUNDARY,
        "sanitation_policy": SANITATION_POLICY,
        "truncation": dict(truncation_info),
        "artifacts": {
            "manifest": {
                "filename": MANIFEST_FILENAME,
            },
            "page_projection": {
                "filename": PROJECTION_FILENAME,
                "sha256": proj_hash,
                "byte_count": len(projection_bytes),
            },
            "screenshot": {
                "filename": SCREENSHOT_FILENAME,
                "sha256": shot_hash,
                "byte_count": len(screenshot_bytes),
            },
        },
        "artifact_records": [
            {
                "filename": MANIFEST_FILENAME,
                "artifact_type": "MANIFEST",
            },
            {
                "filename": PROJECTION_FILENAME,
                "artifact_type": "PAGE_PROJECTION",
                "sha256": proj_hash,
                "byte_count": len(projection_bytes),
            },
            {
                "filename": SCREENSHOT_FILENAME,
                "artifact_type": "SCREENSHOT",
                "sha256": shot_hash,
                "byte_count": len(screenshot_bytes),
            },
        ],
    }


async def run_tiktok_pdp_case_bundle(
    *,
    job_root: str | Path,
    cdp_endpoint: str,
    clock: Callable[[], datetime] = _utc_now,
    manager_factory: Callable[..., _SessionManager] = PlaywrightBrowserManager,
) -> TikTokPdpCaseBundleOutcome:
    """Capture one attach-only P8 real-case evidence bundle for Human review."""
    # 1. Non-consuming local gates
    root = _resolve_external_job_root(job_root)
    manifest_path = root / MANIFEST_FILENAME
    projection_path = root / PROJECTION_FILENAME
    screenshot_path = root / SCREENSHOT_FILENAME

    if (
        manifest_path.exists()
        or projection_path.exists()
        or screenshot_path.exists()
    ):
        raise TikTokPdpCaseBundleArtifactExistsError(
            "one or more case bundle artifacts already exist in the job root"
        )
    if not isinstance(cdp_endpoint, str) or not cdp_endpoint.strip():
        raise TikTokPdpCaseBundleError("an explicit operator-owned CDP endpoint is required")

    started_at = clock()
    if (
        not isinstance(started_at, datetime)
        or started_at.tzinfo is None
        or started_at.utcoffset() is None
    ):
        raise TikTokPdpCaseBundleError("the operation timestamp must be timezone-aware")
    observed_at = started_at

    # 2. Acquire borrowed session, evaluate projection, capture screenshot
    session_acquired = False
    manager = None
    operation_error: BaseException | None = None
    try:
        try:
            manager = manager_factory(cdp_endpoint=cdp_endpoint)
            session = await manager.get_or_create_session(
                _SESSION_RUN_ID,
                config=BrowserConfig(timeout_seconds=CASE_BUNDLE_BROWSER_TIMEOUT_SECONDS),
            )
            session_acquired = True
        except Exception as exc:
            raise TikTokPdpCaseBundleError(
                "the operator-owned browser session could not be borrowed"
            ) from exc

        try:
            raw_payload = await session.evaluate(CASE_BUNDLE_SCRIPT)
        except Exception as exc:
            raise TikTokPdpCaseBundleError(
                "the bounded page projection evaluation failed"
            ) from exc

        # Validate and prepare projection before screenshot
        projection_doc = _validate_projection_payload(raw_payload)
        projection_doc["observed_at"] = observed_at.isoformat()
        projection_bytes = _prepare_projection_bytes(projection_doc)

        try:
            png_bytes = await session.screenshot()
        except Exception as exc:
            raise TikTokPdpCaseBundleError(
                "the full-page screenshot capture failed"
            ) from exc

        if not isinstance(png_bytes, (bytes, bytearray)) or len(png_bytes) == 0:
            raise TikTokPdpCaseBundleError("the captured screenshot is empty or invalid")
        png_bytes = bytes(png_bytes)
        if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise TikTokPdpCaseBundleError("the captured screenshot is not a valid PNG image")

    except BaseException as exc:
        operation_error = exc
        raise
    finally:
        if session_acquired and manager is not None:
            try:
                await manager.close_session(_SESSION_RUN_ID)
            except Exception as exc:
                if operation_error is None:
                    raise TikTokPdpCaseBundleError(
                        "the borrowed browser session could not be released"
                    ) from exc

    # 3. Construct manifest in memory with hashes and byte counts
    manifest_doc = _build_manifest_doc(
        started_at=started_at,
        observed_at=observed_at,
        projection_bytes=projection_bytes,
        screenshot_bytes=png_bytes,
        truncation_info=projection_doc["truncation"],
    )
    manifest_bytes = (
        json.dumps(manifest_doc, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )

    # 4. Durable Consumption Boundary: Write manifest create-exclusively first
    try:
        root.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("xb") as stream:
            stream.write(manifest_bytes)
    except FileExistsError as exc:
        raise TikTokPdpCaseBundleArtifactExistsError(
            "the bundle manifest already exists"
        ) from exc
    except OSError as exc:
        raise TikTokPdpCaseBundleJobRootError(
            "the bundle manifest could not be created"
        ) from exc

    # 5. Post-manifest writing: any failure here is consumed fail-closed
    try:
        with projection_path.open("xb") as stream:
            stream.write(projection_bytes)
        if _sha256(projection_bytes) != manifest_doc["artifacts"]["page_projection"]["sha256"]:
            raise TikTokPdpCaseBundleError("page projection integrity hash mismatch")
    except Exception as exc:
        raise TikTokPdpCaseBundleError(POST_MANIFEST_WRITE_FAILURE) from exc

    try:
        with screenshot_path.open("xb") as stream:
            stream.write(png_bytes)
        if _sha256(png_bytes) != manifest_doc["artifacts"]["screenshot"]["sha256"]:
            raise TikTokPdpCaseBundleError("screenshot integrity hash mismatch")
    except Exception as exc:
        raise TikTokPdpCaseBundleError(POST_MANIFEST_WRITE_FAILURE) from exc

    return TikTokPdpCaseBundleOutcome(
        manifest_path=manifest_path,
        projection_path=projection_path,
        screenshot_path=screenshot_path,
        manifest=manifest_doc,
    )


__all__ = [
    "AUTHORIZED_PDP_URL",
    "AUTHORIZED_SOURCE_ID",
    "BLOCKED_OR_CHALLENGE",
    "BROWSER_SESSION_TIMEOUT_SECONDS",
    "CASE_BUNDLE_BROWSER_TIMEOUT_SECONDS",
    "CASE_BUNDLE_SCRIPT",
    "CASE_BUNDLE_TIMEOUT_SECONDS",
    "CLASSIFICATION",
    "CONTEXT_ID",
    "EPISTEMIC_BOUNDARY",
    "IDENTITY_MISMATCH",
    "LISTING_UNAVAILABLE",
    "LOGIN_GATE",
    "MALFORMED_PROJECTION",
    "MANIFEST_FILENAME",
    "POST_MANIFEST_WRITE_FAILURE",
    "PROJECTION_FILENAME",
    "SANITATION_POLICY",
    "SCREENSHOT_FILENAME",
    "TikTokPdpCaseBundleArtifactExistsError",
    "TikTokPdpCaseBundleError",
    "TikTokPdpCaseBundleJobRootError",
    "TikTokPdpCaseBundleOutcome",
    "run_tiktok_pdp_case_bundle",
]
