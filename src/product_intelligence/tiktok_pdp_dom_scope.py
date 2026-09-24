"""Bounded TikTok PDP DOM-scope resolution structural capability.

Owns only deterministic DOM scoping mechanics. Owns no identity, browser
lifecycle, price parsing, observation admission, evidence, Product Truth,
ranking, approval, or action semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence


BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION = "BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION"

ROOT_KINDS = (
    "NONE",
    "EXPLICIT_PDP_ROOT",
    "MAIN",
    "MULTI_ANCHOR_COMMON_ANCESTOR",
    "TITLE_LOCAL_COMMERCE_QUORUM",
)


@dataclass(frozen=True)
class BoundedPdpDomScopeRecord:
    """Immutable DOM scope resolution record."""

    has_bounded_root: bool
    root_kind: str
    selected_level: Optional[int]
    root_probe: Mapping[str, Any]
    title_local_probe: Sequence[Mapping[str, Any]]


TIKTOK_PDP_DOM_SCOPE_JS = r"""
 const LOCAL_MAX=300,clip=(v,n)=>String(v||'').replace(/\s+/g,' ').trim().slice(0,n);
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
 const commerce=scope=>{const t=first(scope,titleSelectors,4),p=first(scope,priceSelectors,4),a=first(scope,actionSelectors,4);return t.some(x=>p.some(y=>a.some(z=>x!==y&&x!==z&&y!==z)))};
 const structural=e=>clip([e.getAttribute('data-testid'),e.getAttribute('data-e2e'),e.getAttribute('role'),e.getAttribute('itemprop'),e.className].join(' '),400).toLowerCase();
 const localCandidate=(e,category,basis,hint)=>({candidate_category:category,match_basis:basis,semantic_hint:hint,tag_name:atom(e.tagName,24).toLowerCase(),class_tokens:tokens(e),'data-testid':atom(e.getAttribute('data-testid'),80),'data-e2e':atom(e.getAttribute('data-e2e'),80),role:atom(e.getAttribute('role'),80),itemprop:atom(e.getAttribute('itemprop'),80),parent_signature:compact(e.parentElement),grandparent_signature:compact(e.parentElement&&e.parentElement.parentElement)});
 const resolveBoundedPdpDomScope=()=>{
  let root=null,rootKind='NONE',titleAnchor=null;
  let tc=0,pc=0,ac=0,erc=0,ercc=0,mp=false,mv=false,mc=false,caf=false;
  const roots=[];for(const e of Array.from(document.querySelectorAll(rootSelector)).slice(0,8))if(e!==document.body&&e!==document.documentElement&&visible(e)){roots.push(e);if(commerce(e)){if(!root){root=e;rootKind='EXPLICIT_PDP_ROOT'}ercc++}}erc=roots.length;
  const main=document.querySelector('main');mp=Boolean(main);mv=Boolean(main&&visible(main));mc=Boolean(mv&&commerce(main));if(!root&&mc){root=main;rootKind='MAIN'}
  if(document.body){const ts=first(document.body,titleSelectors,12),ps=first(document.body,priceSelectors,12),as=first(document.body,actionSelectors,12);titleAnchor=ts[0]||null;tc=ts.length;pc=ps.length;ac=as.length;
   const chain=e=>{const out=[];while(e&&out.length<8){if(e===document.body||e===document.documentElement)break;out.push(e);e=e.parentElement}return out};
   outer:for(const t of ts)for(const p of ps){const pa=new Set(chain(p));for(const a of as){if(t===p||t===a||p===a)continue;const aa=new Set(chain(a)),common=chain(t).find(e=>pa.has(e)&&aa.has(e));if(common&&visible(common)){caf=true;if(!root){root=common;rootKind='MULTI_ANCHOR_COMMON_ANCESTOR'}break outer}}}
  }
  const ancestors=[];let parent=titleAnchor&&titleAnchor.parentElement;while(parent&&ancestors.length<6&&parent!==document.body&&parent!==document.documentElement){ancestors.push(sig(parent));parent=parent.parentElement}
  const titleLocal=[];let selectedLevel=null,fallbackTruncated=false;parent=titleAnchor&&titleAnchor.parentElement;for(let level=1;parent&&level<=6;level++,parent=parent.parentElement){
   const localNodes=[];let localTruncated=false;const walker=document.createTreeWalker(parent,NodeFilter.SHOW_ELEMENT);let e=walker.nextNode();while(e&&localNodes.length<LOCAL_MAX){localNodes.push(e);e=walker.nextNode()}localTruncated=Boolean(e);
   let pm=0,am=0,cc=0,sc=0,stc=0,nc=0,pi=0,lm=0,sb=0,ib=0;const currencySamples=[],semanticSamples=[],nativeSamples=[],pointerSamples=[];
   const pairedControls=new Set();
   const isCtrl=el=>el&&visible(el)&&(String(el.tagName||'').toLowerCase()==='button'||String(el.getAttribute('role')||'').toLowerCase()==='button');
   for(const node of localNodes){if(node.shadowRoot&&node.shadowRoot.mode==='open')sb=Math.min(LOCAL_MAX,sb+1);if(!visible(node))continue;const tag=String(node.tagName||'').toLowerCase();if(tag==='iframe')ib=Math.min(LOCAL_MAX,ib+1);if(priceSelectors.some(selector=>node.matches(selector)))pm=Math.min(LOCAL_MAX,pm+1);if(actionSelectors.some(selector=>node.matches(selector)))am=Math.min(LOCAL_MAX,am+1);
    const text=clip(Array.from(node.childNodes||[]).filter(n=>n.nodeType===Node.TEXT_NODE).slice(0,8).map(n=>n.nodeValue||'').join(' '),160),attrs=structural(node);if(/loading|skeleton|spinner|busy|progress/.test(attrs)||/^loading\b|đang tải/i.test(text))lm=Math.min(LOCAL_MAX,lm+1);
    let cb=null;if(/₫|\bđ\b/i.test(text))cb='VND_SYMBOL_TEXT';else if(/\bvnd\b/i.test(text))cb='VND_CODE_TEXT';else if(/price/i.test(String(node.getAttribute('itemprop')||'')))cb='SEMANTIC_PRICE_ATTRIBUTE';else if(/price/.test(attrs))cb='PRICE_STRUCTURAL_ATTRIBUTE';if(cb){cc=Math.min(LOCAL_MAX,cc+1);if(currencySamples.length<2)currencySamples.push(localCandidate(node,'CURRENCY_LIKE',cb,'OTHER'))}
    const both=`${attrs} ${text}`;let hint=null;if(/cart|giỏ/i.test(both))hint='CART_LIKE';else if(/buy|mua/i.test(both))hint='BUY_LIKE';else if(/variant|phân loại/i.test(both))hint='VARIANT_LIKE';else if(/quantity|số lượng/i.test(both))hint='QUANTITY_LIKE';
    if(hint){
     sc=Math.min(LOCAL_MAX,sc+1);
     if(hint==='BUY_LIKE'||hint==='CART_LIKE'){
      stc=Math.min(LOCAL_MAX,stc+1);
      let paired=null;
      if(isCtrl(node))paired=node;
      else{let cur=node.parentElement;while(cur&&cur!==parent){if(isCtrl(cur)){paired=cur;break}cur=cur.parentElement}}
      if(paired)pairedControls.add(paired);
     }
     const basis=/buy|cart|variant|quantity/.test(attrs)?'ACTION_STRUCTURAL_ATTRIBUTE':'ACTION_TEXT_HINT';if(semanticSamples.length<2)semanticSamples.push(localCandidate(node,'COMMERCE_SEMANTIC_ACTION',basis,hint));continue;
    }
    const role=String(node.getAttribute('role')||'').toLowerCase();let nb=null;if(tag==='button')nb='NATIVE_BUTTON';else if(role==='button')nb='ROLE_BUTTON';else if(tag==='select')nb='SELECT_CONTROL';else if(tag==='input')nb='INPUT_CONTROL';if(nb){nc=Math.min(LOCAL_MAX,nc+1);if(nativeSamples.length<2)nativeSamples.push(localCandidate(node,'NATIVE_OR_ROLE_CONTROL',nb,'OTHER'));continue}
    let pb=null;if(node.hasAttribute('tabindex'))pb='TABINDEX_ATTRIBUTE';else if(node.hasAttribute('onclick'))pb='ONCLICK_ATTRIBUTE';else if(getComputedStyle(node).cursor==='pointer')pb='POINTER_CURSOR';if(pb){pi=Math.min(LOCAL_MAX,pi+1);if(pointerSamples.length<2)pointerSamples.push(localCandidate(node,'POINTER_ONLY_INTERACTION',pb,'OTHER'))}
   }
   const pairedCount=Math.min(LOCAL_MAX,pairedControls.size);
   const quorum=(cc>=1&&pairedCount>=1);
   if(!root&&tc===1&&!fallbackTruncated&&selectedLevel===null){
    if(localTruncated){fallbackTruncated=true}
    else if(quorum&&parent!==document.body&&parent!==document.documentElement&&visible(parent)){
     root=parent;rootKind='TITLE_LOCAL_COMMERCE_QUORUM';selectedLevel=level;
    }
   }
   titleLocal.push({ancestor_level:level,ancestor_signature:sig(parent),bounded_nodes_scanned:localNodes.length,bounded_scan_truncated:localTruncated,current_price_selector_match_count:pm,current_action_selector_match_count:am,visible_currency_like_count:cc,commerce_semantic_action_like_count:sc,strong_commerce_action_like_count:stc,paired_strong_commerce_control_count:pairedCount,title_local_root_quorum_satisfied:quorum,native_or_role_control_count:nc,pointer_only_interaction_count:pi,visible_loading_marker_count:lm,open_shadow_root_boundary_count:sb,visible_iframe_boundary_count:ib,candidate_samples:[...currencySamples,...semanticSamples,...nativeSamples,...pointerSamples]});
  }
  return {
   root,
   rootKind,
   selectedLevel,
   titleAnchor,
   titleAncestors: ancestors,
   rootProbe: {
    title_anchor_count: tc,
    price_anchor_count: pc,
    action_anchor_count: ac,
    visible_explicit_pdp_root_count: erc,
    explicit_root_with_commerce_anchors_count: ercc,
    main_present: mp,
    main_visible: mv,
    main_has_commerce_anchors: mc,
    multi_anchor_common_ancestor_found: caf,
    selected_root_kind: rootKind,
    selected_title_local_ancestor_level: selectedLevel
   },
   titleLocal
  };
 };
"""


def get_bounded_pdp_dom_scope_script() -> str:
    """Return the canonical shared JavaScript resolver script."""
    return TIKTOK_PDP_DOM_SCOPE_JS


__all__ = [
    "BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION",
    "BoundedPdpDomScopeRecord",
    "ROOT_KINDS",
    "TIKTOK_PDP_DOM_SCOPE_JS",
    "get_bounded_pdp_dom_scope_script",
]
