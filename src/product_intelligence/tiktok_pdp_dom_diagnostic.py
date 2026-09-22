"""Attach-only, evidence-authority-NONE TikTok PDP structural diagnostic."""
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
ARTIFACT_FILENAME = "tiktok-pdp-dom-diagnostic-v2.json"
_SESSION_RUN_ID = f"human-dom-diagnostic:{DIAGNOSTIC_CONTEXT_ID}"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MAX_NODES = 600
_MAX_ATTRIBUTE = 80
_MAX_SIGNATURE = 120
_MAX_CLASS_TOKENS = 4
_MAX_CLASS_TOKEN = 48
_ROOT_PROBE_KEYS = {"title_anchor_count", "price_anchor_count", "action_anchor_count", "visible_explicit_pdp_root_count", "explicit_root_with_commerce_anchors_count", "main_present", "main_visible", "main_has_commerce_anchors", "multi_anchor_common_ancestor_found", "selected_root_kind"}
_ROOT_KINDS = {"NONE", "EXPLICIT_PDP_ROOT", "MAIN", "MULTI_ANCHOR_COMMON_ANCESTOR"}
_SIGNATURE_KEYS = {"tag_name", "class_tokens", "data-testid", "data-e2e", "role", "itemprop", "parent_signature", "grandparent_signature"}
_CANDIDATE_KEYS = {"candidate_kind", "match_basis", "semantic_hint", "tag_name", "class_tokens", "data-testid", "data-e2e", "role", "itemprop", "parent_signature", "grandparent_signature", "relation_to_title", "fixed_or_sticky"}
_COMMERCE_PROBE_KEYS = {"document_ready_state", "bounded_nodes_scanned", "bounded_scan_truncated", "visible_currency_like_count", "near_title_currency_like_count", "visible_interactive_count", "near_title_action_like_count", "visible_loading_marker_count", "open_shadow_root_count", "visible_iframe_count", "title_anchor_signature", "title_ancestor_signatures", "currency_candidates", "action_candidates"}
_READY_STATES = {"LOADING", "INTERACTIVE", "COMPLETE", "UNKNOWN"}
_RELATIONS = {"TITLE_NODE", "OUTSIDE_TITLE_NEIGHBORHOOD"} | {f"TITLE_NEIGHBORHOOD_LEVEL_{n}" for n in range(1, 7)}
_CURRENCY_BASES = {"VND_SYMBOL_TEXT", "VND_CODE_TEXT", "SEMANTIC_PRICE_ATTRIBUTE", "PRICE_STRUCTURAL_ATTRIBUTE"}
_ACTION_BASES = {"NATIVE_BUTTON", "ROLE_BUTTON", "SELECT_CONTROL", "INPUT_CONTROL", "TABINDEX_ATTRIBUTE", "ONCLICK_ATTRIBUTE", "POINTER_CURSOR", "ACTION_TEXT_HINT", "ACTION_STRUCTURAL_ATTRIBUTE"}
_SEMANTIC_HINTS = {"BUY_LIKE", "CART_LIKE", "VARIANT_LIKE", "QUANTITY_LIKE", "OTHER"}
_SAFE_ATOM = re.compile(r"^[A-Za-z0-9_.:/-]*$")
_SAFE_SIGNATURE = re.compile(r"^[A-Za-z0-9_.:-]*$")
_RAW_VALUE = re.compile(r"(?:₫|\bVND\b|\d{4,}|\b\d[\d.,]*\s*(?:₫|VND)\b)", re.I)

BLOCKED_OR_CHALLENGE = "BLOCKED_OR_CHALLENGE"
LOGIN_GATE = "LOGIN_GATE"
LISTING_UNAVAILABLE = "LISTING_UNAVAILABLE"
NO_BOUNDED_PDP_ROOT = "NO_BOUNDED_PDP_ROOT"
IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
MALFORMED_DIAGNOSTIC_PAYLOAD = "MALFORMED_DIAGNOSTIC_PAYLOAD"


class TikTokPdpDomDiagnosticError(RuntimeError):
    """A sanitized fail-closed diagnostic error."""


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
        raise TikTokPdpDomDiagnosticJobRootError("an explicit external diagnostic job root is required")
    try:
        resolved = Path(job_root).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise TikTokPdpDomDiagnosticJobRootError("the external diagnostic job root could not be resolved") from exc
    if resolved == _REPOSITORY_ROOT or _REPOSITORY_ROOT in resolved.parents:
        raise TikTokPdpDomDiagnosticJobRootError("the diagnostic job root must be outside the Git repository")
    return resolved


def _write_artifact(path: Path, document: dict[str, object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except FileExistsError as exc:
        raise TikTokPdpDomDiagnosticArtifactExistsError("the fixed diagnostic artifact already exists") from exc
    except OSError as exc:
        raise TikTokPdpDomDiagnosticJobRootError("the diagnostic artifact could not be created") from exc


# Exactly one evaluate. TreeWalker is light-DOM only: iframe documents and shadow
# roots are counted at their boundary but never traversed.
DIAGNOSTIC_SCRIPT = r"""
() => {
 const MAX=600, clip=(v,n)=>String(v||'').replace(/\s+/g,' ').trim().slice(0,n);
 const atom=(v,n)=>{const s=clip(v,n);return/^[A-Za-z0-9_.:/-]*$/.test(s)&&!/\d{4,}/.test(s)?s:''};
 const tokens=e=>Array.from(e&&e.classList||[]).slice(0,4).map(v=>atom(v,48)).filter(Boolean);
 const compact=e=>e?clip([String(e.tagName||'').toLowerCase(),...tokens(e).slice(0,2)].filter(Boolean).join('.'),120):'';
 const sig=e=>e?{tag_name:atom(e.tagName,24).toLowerCase(),class_tokens:tokens(e),'data-testid':atom(e.getAttribute('data-testid'),80),'data-e2e':atom(e.getAttribute('data-e2e'),80),role:atom(e.getAttribute('role'),80),itemprop:atom(e.getAttribute('itemprop'),80),parent_signature:compact(e.parentElement),grandparent_signature:compact(e.parentElement&&e.parentElement.parentElement)}:null;
 const visible=e=>{if(!e||typeof e.getBoundingClientRect!=='function')return false;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'};
 const first=(scope,selectors,cap)=>{const out=[];for(const selector of selectors)for(const e of Array.from(scope.querySelectorAll(selector)).slice(0,cap)){if(visible(e)&&!out.includes(e))out.push(e);if(out.length>=cap)return out}return out};
 const rootSelector='[data-e2e*="pdp" i], [data-testid*="pdp" i], [itemtype*="Product"]';
 const titleSelectors=['h1','[role="heading"][aria-level="1"]','[data-e2e*="title" i]','[data-testid*="title" i]','[itemprop="name"]'];
 const priceSelectors=['[data-e2e*="price" i]','[data-testid*="price" i]','[itemprop="price"]','[class*="price" i]'];
 const actionSelectors=['button[data-e2e*="buy" i]','button[data-testid*="buy" i]','button[data-e2e*="cart" i]','button[data-testid*="cart" i]','[data-e2e*="quantity" i]','[data-testid*="quantity" i]','[data-e2e*="variant" i]','[data-testid*="variant" i]','[role="radiogroup"]','select'];
 let root=null,rootKind='NONE',titleAnchor=null;
 const pageTitle=clip(document.title,200).toLowerCase(),url=String(location.href||'');
 const marker=ss=>ss.some(s=>Array.from(document.querySelectorAll(s)).slice(0,4).some(visible));
 const blocked=/captcha|challenge|verify|security check|robot/.test(pageTitle)||marker(['iframe[src*="captcha" i]','iframe[src*="challenge" i]','[data-e2e*="captcha" i]','[data-testid*="captcha" i]','[data-e2e*="challenge" i]','[data-testid*="challenge" i]','[id*="captcha" i]','[aria-label*="security check" i]']);
 const login=/\/login(?:[/?#]|$)/i.test(url)||/log in|login|sign in|đăng nhập/.test(pageTitle)||marker(['form[action*="/login" i]','input[type="password"]','[data-e2e*="login" i]','[data-testid*="login" i]','[aria-label*="log in" i]','[aria-label*="sign in" i]']);
 let identity=false;try{const u=new URL(url),m=u.pathname.match(/^\/[a-z]{2}\/pdp\/[^/]+\/(\d+)\/?$/i);identity=/^https?:$/.test(u.protocol)&&u.hostname.toLowerCase()==='shop.tiktok.com'&&Boolean(m)&&m[1]==='1731381331718341815'}catch(_){identity=false}
 const unavailable=/(?:product|item|listing).{0,32}(?:not available|unavailable)|(?:not available|unavailable).{0,32}(?:product|item|listing)/i.test(pageTitle)||marker(['[data-e2e="product-unavailable" i]','[data-testid="product-unavailable" i]','[data-e2e="listing-unavailable" i]','[data-testid="listing-unavailable" i]','[role="alert"][data-e2e*="unavailable" i]','[role="alert"][data-testid*="unavailable" i]','[aria-label="product unavailable" i]','[aria-label="listing unavailable" i]']);
 const commerce=scope=>{const t=first(scope,titleSelectors,4),p=first(scope,priceSelectors,4),a=first(scope,actionSelectors,4);return t.some(x=>p.some(y=>a.some(z=>x!==y&&x!==z&&y!==z)))};
 let tc=0,pc=0,ac=0,erc=0,ercc=0,mp=false,mv=false,mc=false,caf=false;
 if(identity&&!blocked&&!login&&!unavailable){
  const roots=[];for(const e of Array.from(document.querySelectorAll(rootSelector)).slice(0,8))if(e!==document.body&&e!==document.documentElement&&visible(e)){roots.push(e);if(commerce(e)){if(!root){root=e;rootKind='EXPLICIT_PDP_ROOT'}ercc++}}erc=roots.length;
  const main=document.querySelector('main');mp=Boolean(main);mv=Boolean(main&&visible(main));mc=Boolean(mv&&commerce(main));if(!root&&mc){root=main;rootKind='MAIN'}
  if(document.body){const ts=first(document.body,titleSelectors,12),ps=first(document.body,priceSelectors,12),as=first(document.body,actionSelectors,12);titleAnchor=ts[0]||null;tc=ts.length;pc=ps.length;ac=as.length;
   const chain=e=>{const out=[];while(e&&out.length<8){if(e===document.body||e===document.documentElement)break;out.push(e);e=e.parentElement}return out};
   outer:for(const t of ts)for(const p of ps){const pa=new Set(chain(p));for(const a of as){if(t===p||t===a||p===a)continue;const aa=new Set(chain(a)),common=chain(t).find(e=>pa.has(e)&&aa.has(e));if(common&&visible(common)){caf=true;if(!root){root=common;rootKind='MULTI_ANCHOR_COMMON_ANCESTOR'}break outer}}}
  }
 }
 const relation=e=>{if(!titleAnchor)return'OUTSIDE_TITLE_NEIGHBORHOOD';if(e===titleAnchor)return'TITLE_NODE';let x=e;for(let n=1;n<=6&&x;n++){x=x.parentElement;if(x&&(x===titleAnchor||x.contains(titleAnchor)))return`TITLE_NEIGHBORHOOD_LEVEL_${n}`}x=titleAnchor;for(let n=1;n<=6&&x;n++){x=x.parentElement;if(x&&x.contains(e))return`TITLE_NEIGHBORHOOD_LEVEL_${n}`}return'OUTSIDE_TITLE_NEIGHBORHOOD'};
 const structural=e=>clip([e.getAttribute('data-testid'),e.getAttribute('data-e2e'),e.getAttribute('role'),e.getAttribute('itemprop'),e.className].join(' '),400).toLowerCase();
 const candidate=(e,kind,basis,hint)=>({candidate_kind:kind,match_basis:basis,semantic_hint:hint,tag_name:atom(e.tagName,24).toLowerCase(),class_tokens:tokens(e),'data-testid':atom(e.getAttribute('data-testid'),80),'data-e2e':atom(e.getAttribute('data-e2e'),80),role:atom(e.getAttribute('role'),80),itemprop:atom(e.getAttribute('itemprop'),80),parent_signature:compact(e.parentElement),grandparent_signature:compact(e.parentElement&&e.parentElement.parentElement),relation_to_title:relation(e),fixed_or_sticky:['fixed','sticky'].includes(getComputedStyle(e).position)});
 const nodes=[];let truncated=false;if(identity&&!blocked&&!login&&!unavailable&&document.documentElement){const w=document.createTreeWalker(document.documentElement,NodeFilter.SHOW_ELEMENT);let e=w.currentNode;while(e&&nodes.length<MAX){nodes.push(e);e=w.nextNode()}truncated=Boolean(e)}
 const currencies=[],actions=[];let vc=0,ntc=0,vi=0,nta=0,vl=0,os=0,vf=0;
 for(const e of nodes){if(e.shadowRoot&&e.shadowRoot.mode==='open')os=Math.min(MAX,os+1);if(!visible(e))continue;if(String(e.tagName).toLowerCase()==='iframe')vf=Math.min(MAX,vf+1);const text=clip(Array.from(e.childNodes||[]).filter(n=>n.nodeType===Node.TEXT_NODE).slice(0,8).map(n=>n.nodeValue||'').join(' '),160),attrs=structural(e);if(/loading|skeleton|spinner|busy|progress/.test(attrs)||/^loading\b|đang tải/i.test(text))vl=Math.min(MAX,vl+1);
  let cb=null;if(/₫|\bđ\b/i.test(text))cb='VND_SYMBOL_TEXT';else if(/\bvnd\b/i.test(text))cb='VND_CODE_TEXT';else if(/price/i.test(String(e.getAttribute('itemprop')||'')))cb='SEMANTIC_PRICE_ATTRIBUTE';else if(/price/.test(attrs))cb='PRICE_STRUCTURAL_ATTRIBUTE';if(cb){vc=Math.min(MAX,vc+1);if(relation(e)!=='OUTSIDE_TITLE_NEIGHBORHOOD')ntc=Math.min(MAX,ntc+1);if(currencies.length<3)currencies.push(candidate(e,'CURRENCY_LIKE',cb,'OTHER'))}
  const tag=String(e.tagName||'').toLowerCase(),style=getComputedStyle(e);let ab=null;if(tag==='button')ab='NATIVE_BUTTON';else if(String(e.getAttribute('role')||'').toLowerCase()==='button')ab='ROLE_BUTTON';else if(tag==='select')ab='SELECT_CONTROL';else if(tag==='input')ab='INPUT_CONTROL';else if(e.hasAttribute('tabindex'))ab='TABINDEX_ATTRIBUTE';else if(e.hasAttribute('onclick'))ab='ONCLICK_ATTRIBUTE';else if(style.cursor==='pointer')ab='POINTER_CURSOR';else if(/buy|cart|variant|quantity|mua|giỏ|phân loại|số lượng/i.test(text))ab='ACTION_TEXT_HINT';else if(/buy|cart|variant|quantity/.test(attrs))ab='ACTION_STRUCTURAL_ATTRIBUTE';if(ab){vi=Math.min(MAX,vi+1);if(relation(e)!=='OUTSIDE_TITLE_NEIGHBORHOOD')nta=Math.min(MAX,nta+1);if(actions.length<5){const both=`${attrs} ${text}`,hint=/cart|giỏ/i.test(both)?'CART_LIKE':/buy|mua/i.test(both)?'BUY_LIKE':/variant|phân loại/i.test(both)?'VARIANT_LIKE':/quantity|số lượng/i.test(both)?'QUANTITY_LIKE':'OTHER';actions.push(candidate(e,'ACTION_LIKE',ab,hint))}}
 }
 const ancestors=[];let parent=titleAnchor&&titleAnchor.parentElement;while(parent&&ancestors.length<6&&parent!==document.body&&parent!==document.documentElement){ancestors.push(sig(parent));parent=parent.parentElement}
 const ids=[],identityNodes=root?[root]:[];if(root&&root.matches(rootSelector))for(const e of Array.from(root.querySelectorAll('meta[property="product:retailer_item_id"], meta[itemprop="productID"], [itemprop="productID"]')).slice(0,4))if(e.closest(rootSelector)===root)identityNodes.push(e);for(const e of identityNodes.slice(0,4)){const ip=String(e.getAttribute('itemprop')||'').toLowerCase()==='productid'?e.textContent:'',v=clip(e.getAttribute('content')||e.getAttribute('data-product-id')||e.getAttribute('data-item-id')||ip,32);if(/^\d+$/.test(v)&&!ids.includes(v))ids.push(v)}
 const ready=String(document.readyState||'').toUpperCase();
 return{schema_version:2,observed_url:url,explicit_product_ids:ids,page_state:{identity_bound:identity,has_bounded_root:Boolean(root),root_kind:rootKind,blocked,login,unavailable},root_probe:{title_anchor_count:tc,price_anchor_count:pc,action_anchor_count:ac,visible_explicit_pdp_root_count:erc,explicit_root_with_commerce_anchors_count:ercc,main_present:mp,main_visible:mv,main_has_commerce_anchors:mc,multi_anchor_common_ancestor_found:caf,selected_root_kind:rootKind},commerce_probe:{document_ready_state:['LOADING','INTERACTIVE','COMPLETE'].includes(ready)?ready:'UNKNOWN',bounded_nodes_scanned:nodes.length,bounded_scan_truncated:truncated,visible_currency_like_count:vc,near_title_currency_like_count:ntc,visible_interactive_count:vi,near_title_action_like_count:nta,visible_loading_marker_count:vl,open_shadow_root_count:os,visible_iframe_count:vf,title_anchor_signature:sig(titleAnchor),title_ancestor_signatures:ancestors,currency_candidates:currencies,action_candidates:actions}};
}
"""


def _malformed() -> TikTokPdpDomDiagnosticError:
    return TikTokPdpDomDiagnosticError(MALFORMED_DIAGNOSTIC_PAYLOAD)


def _bounded_string(value: object, maximum: int, *, signature: bool = False) -> bool:
    pattern = _SAFE_SIGNATURE if signature else _SAFE_ATOM
    return isinstance(value, str) and len(value) <= maximum and pattern.fullmatch(value) is not None and _RAW_VALUE.search(value) is None


def _validate_signature(value: object, *, nullable: bool = False) -> dict[str, object] | None:
    if nullable and value is None:
        return None
    if not isinstance(value, dict) or set(value) != _SIGNATURE_KEYS:
        raise _malformed()
    limits = {"tag_name": 24, "data-testid": _MAX_ATTRIBUTE, "data-e2e": _MAX_ATTRIBUTE, "role": _MAX_ATTRIBUTE, "itemprop": _MAX_ATTRIBUTE}
    if any(not _bounded_string(value[key], limit) for key, limit in limits.items()):
        raise _malformed()
    if any(not _bounded_string(value[key], _MAX_SIGNATURE, signature=True) for key in ("parent_signature", "grandparent_signature")):
        raise _malformed()
    tokens = value["class_tokens"]
    if not isinstance(tokens, list) or len(tokens) > _MAX_CLASS_TOKENS or any(not _bounded_string(token, _MAX_CLASS_TOKEN) for token in tokens):
        raise _malformed()
    return dict(value)


def _validate_candidate(value: object, kind: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _CANDIDATE_KEYS or value["candidate_kind"] != kind:
        raise _malformed()
    bases = _CURRENCY_BASES if kind == "CURRENCY_LIKE" else _ACTION_BASES
    if value["match_basis"] not in bases or value["semantic_hint"] not in _SEMANTIC_HINTS or (kind == "CURRENCY_LIKE" and value["semantic_hint"] != "OTHER") or value["relation_to_title"] not in _RELATIONS or not isinstance(value["fixed_or_sticky"], bool):
        raise _malformed()
    _validate_signature({key: value[key] for key in _SIGNATURE_KEYS})
    return dict(value)


def _validate_root_probe(probe: object, state: dict[str, object]) -> dict[str, object]:
    if not isinstance(probe, dict) or set(probe) != _ROOT_PROBE_KEYS:
        raise _malformed()
    for key in ("title_anchor_count", "price_anchor_count", "action_anchor_count"):
        if not isinstance(probe[key], int) or isinstance(probe[key], bool) or not 0 <= probe[key] <= 12:
            raise _malformed()
    for key in ("visible_explicit_pdp_root_count", "explicit_root_with_commerce_anchors_count"):
        if not isinstance(probe[key], int) or isinstance(probe[key], bool) or not 0 <= probe[key] <= 8:
            raise _malformed()
    if probe["explicit_root_with_commerce_anchors_count"] > probe["visible_explicit_pdp_root_count"]:
        raise _malformed()
    for key in ("main_present", "main_visible", "main_has_commerce_anchors", "multi_anchor_common_ancestor_found"):
        if not isinstance(probe[key], bool):
            raise _malformed()
    if (probe["main_has_commerce_anchors"] and not probe["main_visible"]) or (probe["main_visible"] and not probe["main_present"]):
        raise _malformed()
    if probe["selected_root_kind"] not in _ROOT_KINDS or probe["selected_root_kind"] != state.get("root_kind"):
        raise _malformed()
    return dict(probe)


def _validate_commerce_probe(probe: object) -> dict[str, object]:
    if not isinstance(probe, dict) or set(probe) != _COMMERCE_PROBE_KEYS or probe["document_ready_state"] not in _READY_STATES:
        raise _malformed()
    counts = ("bounded_nodes_scanned", "visible_currency_like_count", "near_title_currency_like_count", "visible_interactive_count", "near_title_action_like_count", "visible_loading_marker_count", "open_shadow_root_count", "visible_iframe_count")
    if any(not isinstance(probe[key], int) or isinstance(probe[key], bool) or not 0 <= probe[key] <= _MAX_NODES for key in counts):
        raise _malformed()
    if not isinstance(probe["bounded_scan_truncated"], bool) or (probe["bounded_scan_truncated"] and probe["bounded_nodes_scanned"] != _MAX_NODES):
        raise _malformed()
    if probe["near_title_currency_like_count"] > probe["visible_currency_like_count"] or probe["near_title_action_like_count"] > probe["visible_interactive_count"]:
        raise _malformed()
    ancestors, currency, actions = probe["title_ancestor_signatures"], probe["currency_candidates"], probe["action_candidates"]
    if not isinstance(ancestors, list) or len(ancestors) > 6 or not isinstance(currency, list) or len(currency) > 3 or not isinstance(actions, list) or len(actions) > 5:
        raise _malformed()
    result = dict(probe)
    result["title_anchor_signature"] = _validate_signature(probe["title_anchor_signature"], nullable=True)
    result["title_ancestor_signatures"] = [_validate_signature(item) for item in ancestors]
    result["currency_candidates"] = [_validate_candidate(item, "CURRENCY_LIKE") for item in currency]
    result["action_candidates"] = [_validate_candidate(item, "ACTION_LIKE") for item in actions]
    return result


def _validate_payload(payload: object, *, failure_writer: Callable[[dict[str, object], dict[str, object]], None] | None = None) -> tuple[dict[str, object], dict[str, object]]:
    required = {"schema_version", "observed_url", "explicit_product_ids", "page_state", "root_probe", "commerce_probe"}
    if not isinstance(payload, dict) or set(payload) != required or payload["schema_version"] != 2 or not isinstance(payload["observed_url"], str) or len(payload["observed_url"]) > 2048:
        raise _malformed()
    state = payload["page_state"]
    state_keys = {"identity_bound", "has_bounded_root", "root_kind", "blocked", "login", "unavailable"}
    if not isinstance(state, dict) or set(state) != state_keys or any(not isinstance(state[key], bool) for key in ("identity_bound", "has_bounded_root", "blocked", "login", "unavailable")) or state["root_kind"] not in _ROOT_KINDS or state["has_bounded_root"] != (state["root_kind"] != "NONE"):
        raise _malformed()
    root_probe = _validate_root_probe(payload["root_probe"], state)
    commerce_probe = _validate_commerce_probe(payload["commerce_probe"])
    if state["blocked"]:
        raise TikTokPdpDomDiagnosticError(BLOCKED_OR_CHALLENGE)
    if state["login"]:
        raise TikTokPdpDomDiagnosticError(LOGIN_GATE)
    if state["unavailable"]:
        raise TikTokPdpDomDiagnosticError(LISTING_UNAVAILABLE)
    ids = payload["explicit_product_ids"]
    if not isinstance(ids, list) or len(ids) > 4 or any(not isinstance(item, str) or not item.isdigit() or len(item) > 32 for item in ids):
        raise _malformed()
    try:
        parsed = urlsplit(payload["observed_url"])
    except ValueError as exc:
        raise TikTokPdpDomDiagnosticError(IDENTITY_MISMATCH) from exc
    match = re.fullmatch(r"/[a-z]{2}/pdp/[^/]+/(?P<product_id>\d+)/?", parsed.path, flags=re.I)
    extracted = extract_tiktok_product_id(payload["observed_url"])
    if parsed.scheme.lower() not in {"http", "https"} or (parsed.hostname or "").lower() != "shop.tiktok.com" or match is None or not state["identity_bound"] or extracted != match.group("product_id") or extracted != DIAGNOSTIC_SOURCE_ID:
        raise TikTokPdpDomDiagnosticError(IDENTITY_MISMATCH)
    if not state["has_bounded_root"]:
        if failure_writer is not None:
            failure_writer(root_probe, commerce_probe)
        raise TikTokPdpDomDiagnosticError(NO_BOUNDED_PDP_ROOT)
    return root_probe, commerce_probe


async def run_tiktok_pdp_dom_diagnostic(*, job_root: str | Path, cdp_endpoint: str, clock: Callable[[], datetime] = _utc_now, manager_factory: Callable[..., _SessionManager] = PlaywrightBrowserManager) -> TikTokPdpDomDiagnosticOutcome:
    """Inspect the already-open fixed PDP once without navigation or interaction."""
    root = _resolve_external_job_root(job_root)
    artifact_path = root / ARTIFACT_FILENAME
    if artifact_path.exists():
        raise TikTokPdpDomDiagnosticArtifactExistsError("the fixed diagnostic artifact already exists")
    if not isinstance(cdp_endpoint, str) or not cdp_endpoint.strip():
        raise TikTokPdpDomDiagnosticError("an explicit operator-owned CDP endpoint is required")
    observed_at = clock()
    if not isinstance(observed_at, datetime) or observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise TikTokPdpDomDiagnosticError("the diagnostic timestamp must be timezone-aware")
    try:
        manager = manager_factory(cdp_endpoint=cdp_endpoint)
        session = await manager.get_or_create_session(_SESSION_RUN_ID)
    except Exception as exc:
        raise TikTokPdpDomDiagnosticError("the operator-owned browser session could not be borrowed") from exc
    operation_error: BaseException | None = None
    try:
        try:
            payload = await session.evaluate(DIAGNOSTIC_SCRIPT)
        except Exception as exc:
            raise TikTokPdpDomDiagnosticError("the bounded current-page evaluation failed") from exc
        metadata = {"classification": "ATTACH_ONLY_BOUNDED_COMMERCE_OBSERVABILITY_DIAGNOSTIC", "context_id": DIAGNOSTIC_CONTEXT_ID, "source_product_id": DIAGNOSTIC_SOURCE_ID, "observed_at": observed_at.isoformat(), "evidence_authority": "NONE"}

        def write_failure_artifact(root_probe: dict[str, object], commerce_probe: dict[str, object]) -> None:
            document = {"schema_version": 2, "diagnostic": {"status": "FAIL_CLOSED", **metadata, "failure_reason": NO_BOUNDED_PDP_ROOT}, "root_probe": root_probe, "commerce_probe": commerce_probe}
            _write_artifact(artifact_path, document)

        root_probe, commerce_probe = _validate_payload(payload, failure_writer=write_failure_artifact)
        document: dict[str, object] = {"schema_version": 2, "diagnostic": {"status": "SUCCESS", **metadata}, "root_probe": root_probe, "commerce_probe": commerce_probe}
        _write_artifact(artifact_path, document)
    except BaseException as exc:
        operation_error = exc
        raise
    finally:
        try:
            await manager.close_session(_SESSION_RUN_ID)
        except Exception as exc:
            if operation_error is None:
                raise TikTokPdpDomDiagnosticError("the borrowed browser session could not be released") from exc
    return TikTokPdpDomDiagnosticOutcome(artifact_path=artifact_path, document=document)


__all__ = ["ARTIFACT_FILENAME", "BLOCKED_OR_CHALLENGE", "DIAGNOSTIC_CONTEXT_ID", "DIAGNOSTIC_SCRIPT", "DIAGNOSTIC_SOURCE_ID", "IDENTITY_MISMATCH", "LISTING_UNAVAILABLE", "LOGIN_GATE", "MALFORMED_DIAGNOSTIC_PAYLOAD", "NO_BOUNDED_PDP_ROOT", "TikTokPdpDomDiagnosticArtifactExistsError", "TikTokPdpDomDiagnosticError", "TikTokPdpDomDiagnosticJobRootError", "TikTokPdpDomDiagnosticOutcome", "run_tiktok_pdp_dom_diagnostic"]
