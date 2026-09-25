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
from src.product_intelligence.tiktok_pdp_dom_scope import TIKTOK_PDP_DOM_SCOPE_JS

DIAGNOSTIC_CONTEXT_ID = "p8-pilot-001-led-motion-tiktok-vn"
DIAGNOSTIC_SOURCE_ID = "1731381331718341815"
ARTIFACT_FILENAME = "tiktok-pdp-dom-diagnostic-v5.json"
_SESSION_RUN_ID = f"human-dom-diagnostic:{DIAGNOSTIC_CONTEXT_ID}"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MAX_NODES = 600
_MAX_TITLE_LOCAL_NODES = 300
_MAX_ATTRIBUTE = 80
_MAX_SIGNATURE = 120
_MAX_CLASS_TOKENS = 4
_MAX_CLASS_TOKEN = 48
_ROOT_PROBE_KEYS = {"title_anchor_count", "price_anchor_count", "action_anchor_count", "visible_explicit_pdp_root_count", "explicit_root_with_commerce_anchors_count", "main_present", "main_visible", "main_has_commerce_anchors", "multi_anchor_common_ancestor_found", "selected_root_kind", "selected_title_local_ancestor_level"}
_ROOT_KINDS = {"NONE", "EXPLICIT_PDP_ROOT", "MAIN", "MULTI_ANCHOR_COMMON_ANCESTOR", "TITLE_LOCAL_COMMERCE_QUORUM"}
_SIGNATURE_KEYS = {"tag_name", "class_tokens", "data-testid", "data-e2e", "role", "itemprop", "parent_signature", "grandparent_signature"}
_CANDIDATE_KEYS = {"candidate_kind", "match_basis", "semantic_hint", "tag_name", "class_tokens", "data-testid", "data-e2e", "role", "itemprop", "parent_signature", "grandparent_signature", "relation_to_title", "fixed_or_sticky"}
_COMMERCE_PROBE_KEYS = {"document_ready_state", "bounded_nodes_scanned", "bounded_scan_truncated", "visible_currency_like_count", "near_title_currency_like_count", "visible_interactive_count", "near_title_action_like_count", "visible_loading_marker_count", "open_shadow_root_count", "visible_iframe_count", "title_anchor_signature", "title_ancestor_signatures", "currency_candidates", "action_candidates"}
_TITLE_LOCAL_RECORD_KEYS = {"ancestor_level", "ancestor_signature", "bounded_nodes_scanned", "bounded_scan_truncated", "current_price_selector_match_count", "current_action_selector_match_count", "visible_currency_like_count", "commerce_semantic_action_like_count", "strong_commerce_action_like_count", "paired_strong_commerce_control_count", "title_local_root_quorum_satisfied", "native_or_role_control_count", "pointer_only_interaction_count", "visible_loading_marker_count", "open_shadow_root_boundary_count", "visible_iframe_boundary_count", "candidate_samples"}
_TITLE_LOCAL_CANDIDATE_KEYS = {"candidate_category", "match_basis", "semantic_hint", "tag_name", "class_tokens", "data-testid", "data-e2e", "role", "itemprop", "parent_signature", "grandparent_signature"}
_TITLE_LOCAL_CATEGORIES = {"CURRENCY_LIKE", "COMMERCE_SEMANTIC_ACTION", "NATIVE_OR_ROLE_CONTROL", "POINTER_ONLY_INTERACTION"}
_PRICE_ROLE_PROBE_KEYS = {"bounded_nodes_scanned", "bounded_scan_truncated", "currency_candidate_count", "collector_eligible_candidate_count", "leaf_candidate_count", "strike_through_signal_count", "explicit_current_structural_signal_count", "explicit_original_structural_signal_count", "unresolved_role_candidate_count", "range_like_candidate_count", "multi_numeric_candidate_count", "distinct_text_equivalence_group_count", "candidate_samples"}
_PRICE_ROLE_SAMPLE_KEYS = {"ordinal", "match_basis", "relation_to_title", "tag_name", "class_tokens", "data-testid", "data-e2e", "role", "itemprop", "parent_signature", "grandparent_signature", "inside_interactive_control", "inside_title_subtree", "leaf_currency_candidate", "strike_through", "numeric_token_count", "range_like", "text_equivalence_group", "same_parent_currency_peer_count", "nearby_variant_control", "font_weight_bucket", "font_size_peer_relation"}
_FONT_WEIGHT_BUCKETS = {"BOLD", "NORMAL", "LIGHT", "UNKNOWN"}
_FONT_SIZE_PEER_RELATIONS = {"LARGER", "SMALLER", "EQUAL", "UNKNOWN"}
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
DIAGNOSTIC_SCRIPT = (
    r"""() => {
 const MAX=600;
"""
    + TIKTOK_PDP_DOM_SCOPE_JS
    + r"""
 let root=null,rootKind='NONE',titleAnchor=null;
 const pageTitle=clip(document.title,200).toLowerCase(),url=String(location.href||'');
 const marker=ss=>ss.some(s=>Array.from(document.querySelectorAll(s)).slice(0,4).some(visible));
 const blocked=/captcha|challenge|verify|security check|robot/.test(pageTitle)||marker(['iframe[src*="captcha" i]','iframe[src*="challenge" i]','[data-e2e*="captcha" i]','[data-testid*="captcha" i]','[data-e2e*="challenge" i]','[data-testid*="challenge" i]','[id*="captcha" i]','[aria-label*="security check" i]']);
 const login=/\/login(?:[/?#]|$)/i.test(url)||/log in|login|sign in|đăng nhập/.test(pageTitle)||marker(['form[action*="/login" i]','input[type="password"]','[data-e2e*="login" i]','[data-testid*="login" i]','[aria-label*="log in" i]','[aria-label*="sign in" i]']);
 let identity=false;try{const u=new URL(url),m=u.pathname.match(/^\/[a-z]{2}\/pdp\/[^/]+\/(\d+)\/?$/i);identity=/^https?:$/.test(u.protocol)&&u.hostname.toLowerCase()==='shop.tiktok.com'&&Boolean(m)&&m[1]==='1731381331718341815'}catch(_){identity=false}
 const unavailable=/(?:product|item|listing).{0,32}(?:not available|unavailable)|(?:not available|unavailable).{0,32}(?:product|item|listing)/i.test(pageTitle)||marker(['[data-e2e="product-unavailable" i]','[data-testid="product-unavailable" i]','[data-e2e="listing-unavailable" i]','[data-testid="listing-unavailable" i]','[role="alert"][data-e2e*="unavailable" i]','[role="alert"][data-testid*="unavailable" i]','[aria-label="product unavailable" i]','[aria-label="listing unavailable" i]']);
 let rootProbe={title_anchor_count:0,price_anchor_count:0,action_anchor_count:0,visible_explicit_pdp_root_count:0,explicit_root_with_commerce_anchors_count:0,main_present:false,main_visible:false,main_has_commerce_anchors:false,multi_anchor_common_ancestor_found:false,selected_root_kind:'NONE',selected_title_local_ancestor_level:null},titleLocal=[],ancestors=[];
 if(identity&&!blocked&&!login&&!unavailable){
  const scope=resolveBoundedPdpDomScope();
  root=scope.root;rootKind=scope.rootKind;titleAnchor=scope.titleAnchor;rootProbe=scope.rootProbe;titleLocal=scope.titleLocal;ancestors=scope.titleAncestors;
 }
 const relation=e=>{if(!titleAnchor)return'OUTSIDE_TITLE_NEIGHBORHOOD';if(e===titleAnchor)return'TITLE_NODE';let x=e;for(let n=1;n<=6&&x;n++){x=x.parentElement;if(x&&(x===titleAnchor||x.contains(titleAnchor)))return`TITLE_NEIGHBORHOOD_LEVEL_${n}`}x=titleAnchor;for(let n=1;n<=6&&x;n++){x=x.parentElement;if(x&&x.contains(e))return`TITLE_NEIGHBORHOOD_LEVEL_${n}`}return'OUTSIDE_TITLE_NEIGHBORHOOD'};
 const candidate=(e,kind,basis,hint)=>({candidate_kind:kind,match_basis:basis,semantic_hint:hint,tag_name:atom(e.tagName,24).toLowerCase(),class_tokens:tokens(e),'data-testid':atom(e.getAttribute('data-testid'),80),'data-e2e':atom(e.getAttribute('data-e2e'),80),role:atom(e.getAttribute('role'),80),itemprop:atom(e.getAttribute('itemprop'),80),parent_signature:compact(e.parentElement),grandparent_signature:compact(e.parentElement&&e.parentElement.parentElement),relation_to_title:relation(e),fixed_or_sticky:['fixed','sticky'].includes(getComputedStyle(e).position)});
 const nodes=[];let truncated=false;if(identity&&!blocked&&!login&&!unavailable&&document.documentElement){const w=document.createTreeWalker(document.documentElement,NodeFilter.SHOW_ELEMENT);let e=w.currentNode;while(e&&nodes.length<MAX){nodes.push(e);e=w.nextNode()}truncated=Boolean(e)}
 const currencies=[],actions=[];let vc=0,ntc=0,vi=0,nta=0,vl=0,os=0,vf=0;
 for(const e of nodes){if(e.shadowRoot&&e.shadowRoot.mode==='open')os=Math.min(MAX,os+1);if(!visible(e))continue;if(String(e.tagName).toLowerCase()==='iframe')vf=Math.min(MAX,vf+1);const text=clip(Array.from(e.childNodes||[]).filter(n=>n.nodeType===Node.TEXT_NODE).slice(0,8).map(n=>n.nodeValue||'').join(' '),160),attrs=structural(e);if(/loading|skeleton|spinner|busy|progress/.test(attrs)||/^loading\b|đang tải/i.test(text))vl=Math.min(MAX,vl+1);
  let cb=null;if(/₫|\bđ\b/i.test(text))cb='VND_SYMBOL_TEXT';else if(/\bvnd\b/i.test(text))cb='VND_CODE_TEXT';else if(/price/i.test(String(e.getAttribute('itemprop')||'')))cb='SEMANTIC_PRICE_ATTRIBUTE';else if(/price/.test(attrs))cb='PRICE_STRUCTURAL_ATTRIBUTE';if(cb){vc=Math.min(MAX,vc+1);if(relation(e)!=='OUTSIDE_TITLE_NEIGHBORHOOD')ntc=Math.min(MAX,ntc+1);if(currencies.length<3)currencies.push(candidate(e,'CURRENCY_LIKE',cb,'OTHER'))}
  const tag=String(e.tagName||'').toLowerCase(),style=getComputedStyle(e);let ab=null;if(tag==='button')ab='NATIVE_BUTTON';else if(String(e.getAttribute('role')||'').toLowerCase()==='button')ab='ROLE_BUTTON';else if(tag==='select')ab='SELECT_CONTROL';else if(tag==='input')ab='INPUT_CONTROL';else if(e.hasAttribute('tabindex'))ab='TABINDEX_ATTRIBUTE';else if(e.hasAttribute('onclick'))ab='ONCLICK_ATTRIBUTE';else if(style.cursor==='pointer')ab='POINTER_CURSOR';else if(/buy|cart|variant|quantity|mua|giỏ|phân loại|số lượng/i.test(text))ab='ACTION_TEXT_HINT';else if(/buy|cart|variant|quantity/.test(attrs))ab='ACTION_STRUCTURAL_ATTRIBUTE';if(ab){vi=Math.min(MAX,vi+1);if(relation(e)!=='OUTSIDE_TITLE_NEIGHBORHOOD')nta=Math.min(MAX,nta+1);if(actions.length<5){const both=`${attrs} ${text}`,hint=/cart|giỏ/i.test(both)?'CART_LIKE':/buy|mua/i.test(both)?'BUY_LIKE':/variant|phân loại/i.test(both)?'VARIANT_LIKE':/quantity|số lượng/i.test(both)?'QUANTITY_LIKE':'OTHER';actions.push(candidate(e,'ACTION_LIKE',ab,hint))}}
 }
 const ids=[],identityNodes=root?[root]:[];if(root&&root.matches(rootSelector))for(const e of Array.from(root.querySelectorAll('meta[property="product:retailer_item_id"], meta[itemprop="productID"], [itemprop="productID"]')).slice(0,4))if(e.closest(rootSelector)===root)identityNodes.push(e);for(const e of identityNodes.slice(0,4)){const ip=String(e.getAttribute('itemprop')||'').toLowerCase()==='productid'?e.textContent:'',v=clip(e.getAttribute('content')||e.getAttribute('data-product-id')||e.getAttribute('data-item-id')||ip,32);if(/^\d+$/.test(v)&&!ids.includes(v))ids.push(v)}
 let priceRoleProbe={bounded_nodes_scanned:0,bounded_scan_truncated:false,currency_candidate_count:0,collector_eligible_candidate_count:0,leaf_candidate_count:0,strike_through_signal_count:0,explicit_current_structural_signal_count:0,explicit_original_structural_signal_count:0,unresolved_role_candidate_count:0,range_like_candidate_count:0,multi_numeric_candidate_count:0,distinct_text_equivalence_group_count:0,candidate_samples:[]};
 if(root){
  const isCtrl=el=>el&&visible(el)&&(String(el.tagName||'').toLowerCase()==='button'||String(el.getAttribute('role')||'').toLowerCase()==='button');
  const isInsideBtn=el=>{let cur=el;while(cur&&cur!==root){const tg=String(cur.tagName||'').toLowerCase(),ro=String(cur.getAttribute('role')||'').toLowerCase();if(tg==='button'||ro==='button'||cur.hasAttribute('onclick')||isCtrl(cur))return true;cur=cur.parentElement}return false};
  const isStrikeThrough=el=>{let cur=el;while(cur&&cur!==root){const tag=String(cur.tagName||'').toLowerCase();if(tag==='del'||tag==='s'||tag==='strike')return true;try{const st=getComputedStyle(cur),dec=(st.textDecorationLine||st.textDecoration||'').toLowerCase();if(dec.includes('line-through'))return true}catch(_){}cur=cur.parentElement}return false};
  const rw=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT);
  const rnodes=[];let rn=rw.nextNode();while(rn&&rnodes.length<LOCAL_MAX){rnodes.push(rn);rn=rw.nextNode()}
  const priceTruncated=Boolean(rn);
  const cands=[];
  for(const node of rnodes){
   if(!visible(node))continue;
   const t=clip(node.innerText||node.textContent||'',160).trim();
   if(!t||!/\d/.test(t))continue;
   const attrs=structural(node);
   let cb=null;
   if(/₫|\bđ\b/i.test(t))cb='VND_SYMBOL_TEXT';
   else if(/\bvnd\b/i.test(t))cb='VND_CODE_TEXT';
   else if(/price/i.test(String(node.getAttribute('itemprop')||'')))cb='SEMANTIC_PRICE_ATTRIBUTE';
   else if(/price/.test(attrs))cb='PRICE_STRUCTURAL_ATTRIBUTE';
   if(cb){
    const inBtn=isInsideBtn(node);
    const inTitle=Boolean(titleAnchor&&(node===titleAnchor||titleAnchor.contains(node)));
    const strike=isStrikeThrough(node);
    let cur=node,parts=[];
    while(cur&&cur!==root){
     const curText=clip(cur.innerText||cur.textContent||'',160).trim();
     if(curText===t){
      parts.push(structural(cur));
      const ip=String(cur.getAttribute('itemprop')||'').trim().toLowerCase();if(ip)parts.push('itemprop-'+ip);
      const al=String(cur.getAttribute('aria-label')||'').trim().toLowerCase();if(al)parts.push('aria-'+al);
     }else break;
     cur=cur.parentElement;
    }
    const roleAttrs=parts.join(' ');
    const isExpOrig=/original|regular|was|high[-_]?price|strikethrough/i.test(roleAttrs)||/itemprop-highprice/i.test(roleAttrs);
    const isExpCurr=/current|product[-_]?price|special[-_]?price|sale[-_]?price|offer[-_]?price|final[-_]?price|low[-_]?price/i.test(roleAttrs)||/itemprop-price\b|itemprop-lowprice\b/i.test(roleAttrs);
    const numToks=(t.match(/\d+(?:[.,]\d+)?/g)||[]).length;
    const isRange=/\d+\s*[-–—~]\s*\d+/.test(t);
    const isUnres=(!isExpCurr&&!strike&&!isExpOrig)||(isExpCurr&&(strike||isExpOrig));
    const isElig=!inBtn&&!inTitle;
    let fwBucket='NORMAL';try{const fw=parseInt(getComputedStyle(node).fontWeight||'400',10);if(fw>=600)fwBucket='BOLD';else if(fw<=300)fwBucket='LIGHT'}catch(_){fwBucket='UNKNOWN'}
    const nearbyVar=Boolean(node.closest('[data-e2e*="variant" i],[data-testid*="variant" i],[role="radiogroup"],select')||(node.parentElement&&node.parentElement.querySelector('[data-e2e*="variant" i],[data-testid*="variant" i],[role="radiogroup"],select')));
    cands.push({node,text:t,basis:cb,inBtn,inTitle,strike,isExpOrig,isExpCurr,numToks,isRange,isUnres,isElig,fwBucket,nearbyVar});
   }
  }
  const textGroups=new Map();
  for(const c of cands){
   const norm=c.text.toLowerCase().replace(/\s+/g,' ');
   if(!textGroups.has(norm))textGroups.set(norm,`TEXT_GROUP_${textGroups.size+1}`);
   c.group=textGroups.get(norm);
  }
  for(const c of cands){
   c.isLeaf=!cands.some(o=>o!==c&&c.node.contains(o.node)&&o.text===c.text);
   c.samePeers=cands.filter(o=>o!==c&&o.node.parentElement===c.node.parentElement).length;
   let fsRel='EQUAL';try{
    const myFs=parseFloat(getComputedStyle(c.node).fontSize||'16');
    const peers=cands.filter(o=>o!==c).map(o=>{try{return parseFloat(getComputedStyle(o.node).fontSize||'16')}catch(_){return myFs}});
    if(peers.length>0){if(peers.every(p=>myFs>p))fsRel='LARGER';else if(peers.every(p=>myFs<p))fsRel='SMALLER';else if(peers.some(p=>myFs>p)&&peers.some(p=>myFs<p))fsRel='UNKNOWN';else fsRel='EQUAL'}
   }catch(_){fsRel='UNKNOWN'}
   c.fsRel=fsRel;
  }
  const prSamples=cands.slice(0,8).map((c,i)=>({
   ordinal:i+1,
   match_basis:c.basis,
   relation_to_title:relation(c.node),
   tag_name:atom(c.node.tagName,24).toLowerCase(),
   class_tokens:tokens(c.node),
   'data-testid':atom(c.node.getAttribute('data-testid'),80),
   'data-e2e':atom(c.node.getAttribute('data-e2e'),80),
   role:atom(c.node.getAttribute('role'),80),
   itemprop:atom(c.node.getAttribute('itemprop'),80),
   parent_signature:compact(c.node.parentElement),
   grandparent_signature:compact(c.node.parentElement&&c.node.parentElement.parentElement),
   inside_interactive_control:c.inBtn,
   inside_title_subtree:c.inTitle,
   leaf_currency_candidate:c.isLeaf,
   strike_through:c.strike,
   numeric_token_count:Math.min(10,c.numToks),
   range_like:c.isRange,
   text_equivalence_group:c.group,
   same_parent_currency_peer_count:Math.min(50,c.samePeers),
   nearby_variant_control:c.nearbyVar,
   font_weight_bucket:c.fwBucket,
   font_size_peer_relation:c.fsRel
  }));
  priceRoleProbe={
   bounded_nodes_scanned:rnodes.length,
   bounded_scan_truncated:priceTruncated,
   currency_candidate_count:cands.length,
   collector_eligible_candidate_count:cands.filter(c=>c.isElig).length,
   leaf_candidate_count:cands.filter(c=>c.isLeaf).length,
   strike_through_signal_count:cands.filter(c=>c.strike).length,
   explicit_current_structural_signal_count:cands.filter(c=>c.isExpCurr).length,
   explicit_original_structural_signal_count:cands.filter(c=>c.isExpOrig).length,
   unresolved_role_candidate_count:cands.filter(c=>c.isUnres).length,
   range_like_candidate_count:cands.filter(c=>c.isRange).length,
   multi_numeric_candidate_count:cands.filter(c=>c.numToks>1).length,
   distinct_text_equivalence_group_count:textGroups.size,
   candidate_samples:prSamples
  };
 }
 const ready=String(document.readyState||'').toUpperCase();
 return{schema_version:5,observed_url:url,explicit_product_ids:ids,page_state:{identity_bound:identity,has_bounded_root:Boolean(root),root_kind:rootKind,blocked,login,unavailable},root_probe:rootProbe,commerce_probe:{document_ready_state:['LOADING','INTERACTIVE','COMPLETE'].includes(ready)?ready:'UNKNOWN',bounded_nodes_scanned:nodes.length,bounded_scan_truncated:truncated,visible_currency_like_count:vc,near_title_currency_like_count:ntc,visible_interactive_count:vi,near_title_action_like_count:nta,visible_loading_marker_count:vl,open_shadow_root_count:os,visible_iframe_count:vf,title_anchor_signature:sig(titleAnchor),title_ancestor_signatures:ancestors,currency_candidates:currencies,action_candidates:actions},title_local_topology_probe:titleLocal,price_role_probe:priceRoleProbe};
}
"""
)


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
    level = probe["selected_title_local_ancestor_level"]
    if probe["selected_root_kind"] == "TITLE_LOCAL_COMMERCE_QUORUM":
        if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 6:
            raise _malformed()
        if probe["title_anchor_count"] != 1:
            raise _malformed()
    else:
        if level is not None:
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


def _validate_title_local_candidate(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _TITLE_LOCAL_CANDIDATE_KEYS:
        raise _malformed()
    category = value["candidate_category"]
    basis = value["match_basis"]
    hint = value["semantic_hint"]
    allowed_bases = {
        "CURRENCY_LIKE": _CURRENCY_BASES,
        "COMMERCE_SEMANTIC_ACTION": {"ACTION_TEXT_HINT", "ACTION_STRUCTURAL_ATTRIBUTE"},
        "NATIVE_OR_ROLE_CONTROL": {"NATIVE_BUTTON", "ROLE_BUTTON", "SELECT_CONTROL", "INPUT_CONTROL"},
        "POINTER_ONLY_INTERACTION": {"TABINDEX_ATTRIBUTE", "ONCLICK_ATTRIBUTE", "POINTER_CURSOR"},
    }
    if category not in _TITLE_LOCAL_CATEGORIES or basis not in allowed_bases[category] or hint not in _SEMANTIC_HINTS:
        raise _malformed()
    if (category == "COMMERCE_SEMANTIC_ACTION") != (hint != "OTHER"):
        raise _malformed()
    _validate_signature({key: value[key] for key in _SIGNATURE_KEYS})
    return dict(value)


def _validate_title_local_topology_probe(probe: object) -> list[dict[str, object]]:
    if not isinstance(probe, list) or len(probe) > 6:
        raise _malformed()
    result: list[dict[str, object]] = []
    category_rank = {category: rank for rank, category in enumerate(("CURRENCY_LIKE", "COMMERCE_SEMANTIC_ACTION", "NATIVE_OR_ROLE_CONTROL", "POINTER_ONLY_INTERACTION"))}
    count_keys = (
        "bounded_nodes_scanned", "current_price_selector_match_count",
        "current_action_selector_match_count", "visible_currency_like_count",
        "commerce_semantic_action_like_count", "strong_commerce_action_like_count",
        "paired_strong_commerce_control_count", "native_or_role_control_count",
        "pointer_only_interaction_count", "visible_loading_marker_count",
        "open_shadow_root_boundary_count", "visible_iframe_boundary_count",
    )
    for expected_level, record in enumerate(probe, start=1):
        if not isinstance(record, dict) or set(record) != _TITLE_LOCAL_RECORD_KEYS or record["ancestor_level"] != expected_level:
            raise _malformed()
        if any(not isinstance(record[key], int) or isinstance(record[key], bool) or not 0 <= record[key] <= _MAX_TITLE_LOCAL_NODES for key in count_keys):
            raise _malformed()
        if not isinstance(record["bounded_scan_truncated"], bool) or (record["bounded_scan_truncated"] and record["bounded_nodes_scanned"] != _MAX_TITLE_LOCAL_NODES):
            raise _malformed()
        if any(record[key] > record["bounded_nodes_scanned"] for key in count_keys[1:]):
            raise _malformed()
        if record["strong_commerce_action_like_count"] > record["commerce_semantic_action_like_count"]:
            raise _malformed()
        if record["paired_strong_commerce_control_count"] > record["strong_commerce_action_like_count"]:
            raise _malformed()
        if not isinstance(record["title_local_root_quorum_satisfied"], bool):
            raise _malformed()
        expected_quorum = (record["visible_currency_like_count"] >= 1 and record["paired_strong_commerce_control_count"] >= 1)
        if record["title_local_root_quorum_satisfied"] != expected_quorum:
            raise _malformed()
        samples = record["candidate_samples"]
        if not isinstance(samples, list) or len(samples) > 8:
            raise _malformed()
        validated_samples = [_validate_title_local_candidate(sample) for sample in samples]
        categories = [sample["candidate_category"] for sample in validated_samples]
        if categories != sorted(categories, key=category_rank.__getitem__) or any(categories.count(category) > 2 for category in _TITLE_LOCAL_CATEGORIES):
            raise _malformed()
        category_counts = {"CURRENCY_LIKE": "visible_currency_like_count", "COMMERCE_SEMANTIC_ACTION": "commerce_semantic_action_like_count", "NATIVE_OR_ROLE_CONTROL": "native_or_role_control_count", "POINTER_ONLY_INTERACTION": "pointer_only_interaction_count"}
        if any(categories.count(category) > record[count_key] for category, count_key in category_counts.items()):
            raise _malformed()
        validated = dict(record)
        validated["ancestor_signature"] = _validate_signature(record["ancestor_signature"])
        validated["candidate_samples"] = validated_samples
        result.append(validated)
    return result


def _validate_price_role_sample(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _PRICE_ROLE_SAMPLE_KEYS:
        raise _malformed()
    if not isinstance(value["ordinal"], int) or isinstance(value["ordinal"], bool) or not 1 <= value["ordinal"] <= 8:
        raise _malformed()
    if value["match_basis"] not in _CURRENCY_BASES or value["relation_to_title"] not in _RELATIONS:
        raise _malformed()
    _validate_signature({key: value[key] for key in ("tag_name", "class_tokens", "data-testid", "data-e2e", "role", "itemprop", "parent_signature", "grandparent_signature")})
    for key in ("inside_interactive_control", "inside_title_subtree", "leaf_currency_candidate", "strike_through", "range_like", "nearby_variant_control"):
        if not isinstance(value[key], bool):
            raise _malformed()
    if not isinstance(value["numeric_token_count"], int) or isinstance(value["numeric_token_count"], bool) or not 0 <= value["numeric_token_count"] <= 10:
        raise _malformed()
    if not isinstance(value["same_parent_currency_peer_count"], int) or isinstance(value["same_parent_currency_peer_count"], bool) or not 0 <= value["same_parent_currency_peer_count"] <= 50:
        raise _malformed()
    if not _bounded_string(value["text_equivalence_group"], 24) or re.fullmatch(r"TEXT_GROUP_\d+|NONE", value["text_equivalence_group"]) is None:
        raise _malformed()
    if value["font_weight_bucket"] not in _FONT_WEIGHT_BUCKETS or value["font_size_peer_relation"] not in _FONT_SIZE_PEER_RELATIONS:
        raise _malformed()
    return dict(value)


def _validate_price_role_probe(probe: object) -> dict[str, object]:
    if not isinstance(probe, dict) or set(probe) != _PRICE_ROLE_PROBE_KEYS:
        raise _malformed()
    count_keys = (
        "bounded_nodes_scanned", "currency_candidate_count",
        "collector_eligible_candidate_count", "leaf_candidate_count",
        "strike_through_signal_count", "explicit_current_structural_signal_count",
        "explicit_original_structural_signal_count", "unresolved_role_candidate_count",
        "range_like_candidate_count", "multi_numeric_candidate_count",
        "distinct_text_equivalence_group_count",
    )
    if any(not isinstance(probe[key], int) or isinstance(probe[key], bool) or not 0 <= probe[key] <= _MAX_TITLE_LOCAL_NODES for key in count_keys):
        raise _malformed()
    if not isinstance(probe["bounded_scan_truncated"], bool) or (probe["bounded_scan_truncated"] and probe["bounded_nodes_scanned"] != _MAX_TITLE_LOCAL_NODES):
        raise _malformed()
    for key in (
        "collector_eligible_candidate_count", "leaf_candidate_count",
        "strike_through_signal_count", "explicit_current_structural_signal_count",
        "explicit_original_structural_signal_count", "unresolved_role_candidate_count",
        "range_like_candidate_count", "multi_numeric_candidate_count",
        "distinct_text_equivalence_group_count",
    ):
        if probe[key] > probe["currency_candidate_count"]:
            raise _malformed()
    if probe["currency_candidate_count"] > probe["bounded_nodes_scanned"]:
        raise _malformed()
    samples = probe["candidate_samples"]
    if not isinstance(samples, list) or len(samples) > 8 or len(samples) > probe["currency_candidate_count"]:
        raise _malformed()
    validated_samples = [_validate_price_role_sample(sample) for sample in samples]
    if any(sample["ordinal"] != idx + 1 for idx, sample in enumerate(validated_samples)):
        raise _malformed()
    result = dict(probe)
    result["candidate_samples"] = validated_samples
    return result


def _validate_payload(payload: object, *, failure_writer: Callable[[dict[str, object], dict[str, object], list[dict[str, object]], dict[str, object]], None] | None = None) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]], dict[str, object]]:
    required = {"schema_version", "observed_url", "explicit_product_ids", "page_state", "root_probe", "commerce_probe", "title_local_topology_probe", "price_role_probe"}
    if not isinstance(payload, dict) or set(payload) != required or payload["schema_version"] != 5 or not isinstance(payload["observed_url"], str) or len(payload["observed_url"]) > 2048:
        raise _malformed()
    state = payload["page_state"]
    state_keys = {"identity_bound", "has_bounded_root", "root_kind", "blocked", "login", "unavailable"}
    if not isinstance(state, dict) or set(state) != state_keys or any(not isinstance(state[key], bool) for key in ("identity_bound", "has_bounded_root", "blocked", "login", "unavailable")) or state["root_kind"] not in _ROOT_KINDS or state["has_bounded_root"] != (state["root_kind"] != "NONE"):
        raise _malformed()
    root_probe = _validate_root_probe(payload["root_probe"], state)
    commerce_probe = _validate_commerce_probe(payload["commerce_probe"])
    title_local_topology_probe = _validate_title_local_topology_probe(payload["title_local_topology_probe"])
    price_role_probe = _validate_price_role_probe(payload["price_role_probe"])
    if root_probe["selected_root_kind"] == "TITLE_LOCAL_COMMERCE_QUORUM":
        selected_level = root_probe["selected_title_local_ancestor_level"]
        if selected_level is None or selected_level > len(title_local_topology_probe):
            raise _malformed()
        for idx, record in enumerate(title_local_topology_probe, start=1):
            if idx < selected_level:
                if record["bounded_scan_truncated"] or record["title_local_root_quorum_satisfied"]:
                    raise _malformed()
            elif idx == selected_level:
                if record["bounded_scan_truncated"] or not record["title_local_root_quorum_satisfied"]:
                    raise _malformed()
                break
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
            failure_writer(root_probe, commerce_probe, title_local_topology_probe, price_role_probe)
        raise TikTokPdpDomDiagnosticError(NO_BOUNDED_PDP_ROOT)
    return root_probe, commerce_probe, title_local_topology_probe, price_role_probe


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
        metadata = {"classification": "ATTACH_ONLY_BOUNDED_TITLE_LOCAL_COMMERCE_OBSERVABILITY_DIAGNOSTIC", "context_id": DIAGNOSTIC_CONTEXT_ID, "source_product_id": DIAGNOSTIC_SOURCE_ID, "observed_at": observed_at.isoformat(), "evidence_authority": "NONE"}

        def write_failure_artifact(root_probe: dict[str, object], commerce_probe: dict[str, object], title_local_topology_probe: list[dict[str, object]], price_role_probe: dict[str, object]) -> None:
            document = {"schema_version": 5, "diagnostic": {"status": "FAIL_CLOSED", **metadata, "failure_reason": NO_BOUNDED_PDP_ROOT}, "root_probe": root_probe, "commerce_probe": commerce_probe, "title_local_topology_probe": title_local_topology_probe, "price_role_probe": price_role_probe}
            _write_artifact(artifact_path, document)

        root_probe, commerce_probe, title_local_topology_probe, price_role_probe = _validate_payload(payload, failure_writer=write_failure_artifact)
        document: dict[str, object] = {"schema_version": 5, "diagnostic": {"status": "SUCCESS", **metadata}, "root_probe": root_probe, "commerce_probe": commerce_probe, "title_local_topology_probe": title_local_topology_probe, "price_role_probe": price_role_probe}
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
