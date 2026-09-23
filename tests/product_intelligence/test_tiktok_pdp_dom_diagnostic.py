"""Offline regressions for the schema-version-3 attach-only diagnostic."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

import pytest

from src.product_intelligence.tiktok_pdp_dom_diagnostic import (
    ARTIFACT_FILENAME, BLOCKED_OR_CHALLENGE, DIAGNOSTIC_CONTEXT_ID,
    DIAGNOSTIC_SCRIPT, DIAGNOSTIC_SOURCE_ID, IDENTITY_MISMATCH,
    LISTING_UNAVAILABLE, LOGIN_GATE, MALFORMED_DIAGNOSTIC_PAYLOAD,
    NO_BOUNDED_PDP_ROOT, TikTokPdpDomDiagnosticArtifactExistsError,
    TikTokPdpDomDiagnosticError, TikTokPdpDomDiagnosticJobRootError,
    run_tiktok_pdp_dom_diagnostic,
)

OBSERVED_AT = datetime(2026, 9, 22, 5, 59, tzinfo=timezone.utc)
ENDPOINT = "http://operator.invalid:9222/devtools/browser/diagnostic-secret"
OBSERVED_URL = "https://shop.tiktok.com/vn/pdp/item/1731381331718341815"


def _signature():
    return {"tag_name": "h1", "class_tokens": ["title", "pdp"], "data-testid": "product-title", "data-e2e": "", "role": "heading", "itemprop": "name", "parent_signature": "div.product", "grandparent_signature": "main.pdp"}


def _candidate(kind="CURRENCY_LIKE", **overrides):
    value = {"candidate_kind": kind, "match_basis": "SEMANTIC_PRICE_ATTRIBUTE" if kind == "CURRENCY_LIKE" else "NATIVE_BUTTON", "semantic_hint": "OTHER" if kind == "CURRENCY_LIKE" else "BUY_LIKE", **_signature(), "relation_to_title": "TITLE_NEIGHBORHOOD_LEVEL_1", "fixed_or_sticky": False}
    value.update(overrides)
    return value


def _state(root_kind="EXPLICIT_PDP_ROOT", **overrides):
    value = {"identity_bound": True, "has_bounded_root": root_kind != "NONE", "root_kind": root_kind, "blocked": False, "login": False, "unavailable": False}
    value.update(overrides)
    return value


def _root_probe(root_kind="EXPLICIT_PDP_ROOT", **overrides):
    value = {
        "title_anchor_count": 1,
        "price_anchor_count": 1,
        "action_anchor_count": 1,
        "visible_explicit_pdp_root_count": 1,
        "explicit_root_with_commerce_anchors_count": 1,
        "main_present": False,
        "main_visible": False,
        "main_has_commerce_anchors": False,
        "multi_anchor_common_ancestor_found": False,
        "selected_root_kind": root_kind,
        "selected_title_local_ancestor_level": 1 if root_kind == "TITLE_LOCAL_COMMERCE_QUORUM" else None,
    }
    if root_kind == "NONE":
        value.update({"price_anchor_count": 0, "action_anchor_count": 0, "visible_explicit_pdp_root_count": 0, "explicit_root_with_commerce_anchors_count": 0, "selected_title_local_ancestor_level": None})
    value.update(overrides)
    return value


def _commerce_probe(**overrides):
    value = {"document_ready_state": "INTERACTIVE", "bounded_nodes_scanned": 600, "bounded_scan_truncated": True, "visible_currency_like_count": 2, "near_title_currency_like_count": 1, "visible_interactive_count": 3, "near_title_action_like_count": 1, "visible_loading_marker_count": 1, "open_shadow_root_count": 1, "visible_iframe_count": 1, "title_anchor_signature": _signature(), "title_ancestor_signatures": [_signature()], "currency_candidates": [_candidate()], "action_candidates": [_candidate("ACTION_LIKE")]}
    value.update(overrides)
    return value


def _local_candidate(category="CURRENCY_LIKE", **overrides):
    bases = {
        "CURRENCY_LIKE": ("SEMANTIC_PRICE_ATTRIBUTE", "OTHER"),
        "COMMERCE_SEMANTIC_ACTION": ("ACTION_STRUCTURAL_ATTRIBUTE", "BUY_LIKE"),
        "NATIVE_OR_ROLE_CONTROL": ("NATIVE_BUTTON", "OTHER"),
        "POINTER_ONLY_INTERACTION": ("POINTER_CURSOR", "OTHER"),
    }
    basis, hint = bases[category]
    value = {"candidate_category": category, "match_basis": basis, "semantic_hint": hint, **_signature()}
    value.update(overrides)
    return value


def _title_local_topology_probe(**overrides):
    value = {
        "ancestor_level": 1,
        "ancestor_signature": _signature(),
        "bounded_nodes_scanned": 300,
        "bounded_scan_truncated": True,
        "current_price_selector_match_count": 1,
        "current_action_selector_match_count": 1,
        "visible_currency_like_count": 1,
        "commerce_semantic_action_like_count": 1,
        "strong_commerce_action_like_count": 1,
        "paired_strong_commerce_control_count": 1,
        "title_local_root_quorum_satisfied": True,
        "native_or_role_control_count": 1,
        "pointer_only_interaction_count": 1,
        "visible_loading_marker_count": 1,
        "open_shadow_root_boundary_count": 1,
        "visible_iframe_boundary_count": 1,
        "candidate_samples": [
            _local_candidate(),
            _local_candidate("COMMERCE_SEMANTIC_ACTION"),
            _local_candidate("NATIVE_OR_ROLE_CONTROL"),
            _local_candidate("POINTER_ONLY_INTERACTION"),
        ],
    }
    value.update(overrides)
    return [value]


def _payload(**overrides):
    state = overrides.get("page_state", _state())
    value = {"schema_version": 4, "observed_url": OBSERVED_URL, "explicit_product_ids": [DIAGNOSTIC_SOURCE_ID], "page_state": state, "root_probe": _root_probe(state["root_kind"]), "commerce_probe": _commerce_probe(), "title_local_topology_probe": _title_local_topology_probe()}
    value.update(overrides)
    return value


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.evaluate_calls = []
        self.navigate_calls = []
        self.click_calls = []
        self.type_calls = []
        self.scroll_calls = []
        self.close_calls = 0

    async def evaluate(self, script):
        self.evaluate_calls.append(script)
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload

    async def close(self):
        self.close_calls += 1
        raise AssertionError("borrowed session must not be directly closed")


class FakeManager:
    instances = []
    payload = _payload()
    close_failure = None

    def __init__(self, *, cdp_endpoint):
        self.cdp_endpoint = cdp_endpoint
        self.session = FakeSession(type(self).payload)
        self.get_calls = []
        self.close_session_calls = []
        self.close_all_calls = 0
        type(self).instances.append(self)

    async def get_or_create_session(self, run_id):
        self.get_calls.append(run_id)
        return self.session

    async def close_session(self, run_id):
        self.close_session_calls.append(run_id)
        if type(self).close_failure:
            raise type(self).close_failure


@pytest.fixture(autouse=True)
def _reset():
    FakeManager.instances = []
    FakeManager.payload = _payload()
    FakeManager.close_failure = None


@pytest.fixture
def external_temp_path():
    with tempfile.TemporaryDirectory(prefix="task246-dom-diagnostic-") as directory:
        yield Path(directory)


@pytest.mark.asyncio
async def test_v4_success_is_create_exclusive_bounded_structural_and_one_evaluate(external_temp_path):
    outcome = await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path, cdp_endpoint=ENDPOINT, clock=lambda: OBSERVED_AT, manager_factory=FakeManager)
    manager = FakeManager.instances[0]
    assert ARTIFACT_FILENAME == "tiktok-pdp-dom-diagnostic-v4.json"
    assert manager.session.evaluate_calls == [DIAGNOSTIC_SCRIPT]
    assert manager.session.navigate_calls == manager.session.click_calls == manager.session.type_calls == manager.session.scroll_calls == []
    assert manager.close_session_calls == manager.get_calls
    document = json.loads(outcome.artifact_path.read_text(encoding="utf-8"))
    assert set(document) == {"schema_version", "diagnostic", "root_probe", "commerce_probe", "title_local_topology_probe"}
    assert document["schema_version"] == 4
    assert document["diagnostic"]["evidence_authority"] == "NONE"
    assert document["commerce_probe"] == _commerce_probe()
    assert document["title_local_topology_probe"] == _title_local_topology_probe()
    persisted = outcome.artifact_path.read_text(encoding="utf-8").lower()
    for forbidden in (ENDPOINT.lower(), "text_excerpt", "aria-label", "href", "innerhtml", "outerhtml", "productcandidatesnapshot", "signalevidence", "actual price", "actual title"):
        assert forbidden not in persisted


@pytest.mark.asyncio
async def test_no_root_writes_one_v4_fail_closed_probe_then_preserves_nonzero(external_temp_path):
    probe = _root_probe("NONE")
    commerce = _commerce_probe(title_anchor_signature=_signature(), currency_candidates=[], action_candidates=[], visible_currency_like_count=0, near_title_currency_like_count=0, visible_interactive_count=0, near_title_action_like_count=0)
    FakeManager.payload = _payload(page_state=_state("NONE"), root_probe=probe, commerce_probe=commerce)
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{NO_BOUNDED_PDP_ROOT}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path, cdp_endpoint=ENDPOINT, clock=lambda: OBSERVED_AT, manager_factory=FakeManager)
    document = json.loads((external_temp_path / ARTIFACT_FILENAME).read_text(encoding="utf-8"))
    assert document == {"schema_version": 4, "diagnostic": {"status": "FAIL_CLOSED", "classification": "ATTACH_ONLY_BOUNDED_TITLE_LOCAL_COMMERCE_OBSERVABILITY_DIAGNOSTIC", "context_id": DIAGNOSTIC_CONTEXT_ID, "source_product_id": DIAGNOSTIC_SOURCE_ID, "observed_at": OBSERVED_AT.isoformat(), "evidence_authority": "NONE", "failure_reason": NO_BOUNDED_PDP_ROOT}, "root_probe": probe, "commerce_probe": commerce, "title_local_topology_probe": _title_local_topology_probe()}


@pytest.mark.asyncio
@pytest.mark.parametrize(("state", "reason"), [(_state(blocked=True), BLOCKED_OR_CHALLENGE), (_state(login=True), LOGIN_GATE), (_state(unavailable=True), LISTING_UNAVAILABLE), (_state(identity_bound=False), IDENTITY_MISMATCH)])
async def test_other_safe_failures_are_artifact_free(external_temp_path, state, reason):
    FakeManager.payload = _payload(page_state=state)
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{reason}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path, cdp_endpoint=ENDPOINT, manager_factory=FakeManager)
    assert not (external_temp_path / ARTIFACT_FILENAME).exists()


@pytest.mark.asyncio
async def test_legacy_root_precedence_over_title_local_quorum(external_temp_path):
    for legacy_kind in ("EXPLICIT_PDP_ROOT", "MAIN", "MULTI_ANCHOR_COMMON_ANCESTOR"):
        level1 = {**_title_local_topology_probe()[0], "bounded_scan_truncated": False, "title_local_root_quorum_satisfied": True}
        probe = _root_probe(legacy_kind, selected_title_local_ancestor_level=None)
        if legacy_kind == "MAIN":
            probe.update({"main_present": True, "main_visible": True, "main_has_commerce_anchors": True, "visible_explicit_pdp_root_count": 0, "explicit_root_with_commerce_anchors_count": 0})
        elif legacy_kind == "MULTI_ANCHOR_COMMON_ANCESTOR":
            probe.update({"multi_anchor_common_ancestor_found": True, "visible_explicit_pdp_root_count": 0, "explicit_root_with_commerce_anchors_count": 0})
        FakeManager.payload = _payload(page_state=_state(legacy_kind), root_probe=probe, title_local_topology_probe=[level1])
        outcome = await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path / legacy_kind, cdp_endpoint=ENDPOINT, clock=lambda: OBSERVED_AT, manager_factory=FakeManager)
        doc = outcome.to_document()
        assert doc["root_probe"]["selected_root_kind"] == legacy_kind
        assert doc["root_probe"]["selected_title_local_ancestor_level"] is None


@pytest.mark.asyncio
async def test_synthetic_topology_selects_narrowest_complete_qualifying_ancestor(external_temp_path):
    level1 = {
        **_title_local_topology_probe()[0],
        "ancestor_level": 1,
        "bounded_nodes_scanned": 32,
        "bounded_scan_truncated": False,
        "visible_currency_like_count": 1,
        "commerce_semantic_action_like_count": 0,
        "strong_commerce_action_like_count": 0,
        "paired_strong_commerce_control_count": 0,
        "title_local_root_quorum_satisfied": False,
        "candidate_samples": [_local_candidate()],
    }
    level2 = {
        **_title_local_topology_probe()[0],
        "ancestor_level": 2,
        "bounded_nodes_scanned": 84,
        "bounded_scan_truncated": False,
        "visible_currency_like_count": 1,
        "commerce_semantic_action_like_count": 1,
        "strong_commerce_action_like_count": 1,
        "paired_strong_commerce_control_count": 1,
        "title_local_root_quorum_satisfied": True,
        "candidate_samples": [_local_candidate(), _local_candidate("COMMERCE_SEMANTIC_ACTION")],
    }
    level3 = {
        **_title_local_topology_probe()[0],
        "ancestor_level": 3,
        "bounded_nodes_scanned": 85,
        "bounded_scan_truncated": False,
        "visible_currency_like_count": 1,
        "commerce_semantic_action_like_count": 1,
        "strong_commerce_action_like_count": 1,
        "paired_strong_commerce_control_count": 1,
        "title_local_root_quorum_satisfied": True,
        "candidate_samples": [_local_candidate(), _local_candidate("COMMERCE_SEMANTIC_ACTION")],
    }
    probe = _root_probe("TITLE_LOCAL_COMMERCE_QUORUM", selected_title_local_ancestor_level=2)
    FakeManager.payload = _payload(
        page_state=_state("TITLE_LOCAL_COMMERCE_QUORUM"),
        root_probe=probe,
        title_local_topology_probe=[level1, level2, level3],
    )
    outcome = await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path, cdp_endpoint=ENDPOINT, clock=lambda: OBSERVED_AT, manager_factory=FakeManager)
    doc = outcome.to_document()
    assert doc["root_probe"]["selected_root_kind"] == "TITLE_LOCAL_COMMERCE_QUORUM"
    assert doc["root_probe"]["selected_title_local_ancestor_level"] == 2
    assert doc["diagnostic"]["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_buy_cart_pairing_and_deduplication():
    # Structural invariants in DIAGNOSTIC_SCRIPT: pairing to self if button, to ancestor button if inside,
    # deduplication via Set, and strong hint restricted to BUY_LIKE / CART_LIKE
    assert "if(isCtrl(node))paired=node;" in DIAGNOSTIC_SCRIPT
    assert "while(cur&&cur!==parent){if(isCtrl(cur)){paired=cur;break}cur=cur.parentElement}" in DIAGNOSTIC_SCRIPT
    assert "pairedControls.add(paired)" in DIAGNOSTIC_SCRIPT
    assert "if(hint==='BUY_LIKE'||hint==='CART_LIKE')" in DIAGNOSTIC_SCRIPT
    assert "const pairedCount=Math.min(LOCAL_MAX,pairedControls.size)" in DIAGNOSTIC_SCRIPT
    assert "const quorum=(cc>=1&&pairedCount>=1)" in DIAGNOSTIC_SCRIPT


@pytest.mark.asyncio
async def test_false_positive_rejection_for_generic_controls_pointer_only_and_quantity_variant(external_temp_path):
    # Case 1: generic button only (no strong commerce actions)
    generic_only = {
        **_title_local_topology_probe()[0],
        "bounded_nodes_scanned": 50,
        "bounded_scan_truncated": False,
        "visible_currency_like_count": 1,
        "commerce_semantic_action_like_count": 0,
        "strong_commerce_action_like_count": 0,
        "paired_strong_commerce_control_count": 0,
        "native_or_role_control_count": 2,
        "title_local_root_quorum_satisfied": False,
        "candidate_samples": [_local_candidate(), _local_candidate("NATIVE_OR_ROLE_CONTROL")],
    }
    FakeManager.payload = _payload(page_state=_state("NONE"), root_probe=_root_probe("NONE"), title_local_topology_probe=[generic_only])
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{NO_BOUNDED_PDP_ROOT}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path / "generic", cdp_endpoint=ENDPOINT, manager_factory=FakeManager)

    # Case 2: pointer-only interactions
    pointer_only = {
        **_title_local_topology_probe()[0],
        "bounded_nodes_scanned": 50,
        "bounded_scan_truncated": False,
        "visible_currency_like_count": 1,
        "commerce_semantic_action_like_count": 0,
        "strong_commerce_action_like_count": 0,
        "paired_strong_commerce_control_count": 0,
        "pointer_only_interaction_count": 5,
        "title_local_root_quorum_satisfied": False,
        "candidate_samples": [_local_candidate(), _local_candidate("POINTER_ONLY_INTERACTION")],
    }
    FakeManager.payload = _payload(page_state=_state("NONE"), root_probe=_root_probe("NONE"), title_local_topology_probe=[pointer_only])
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{NO_BOUNDED_PDP_ROOT}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path / "pointer", cdp_endpoint=ENDPOINT, manager_factory=FakeManager)

    # Case 3: QUANTITY_LIKE / VARIANT_LIKE only (not strong actions)
    quantity_variant_only = {
        **_title_local_topology_probe()[0],
        "bounded_nodes_scanned": 50,
        "bounded_scan_truncated": False,
        "visible_currency_like_count": 1,
        "commerce_semantic_action_like_count": 2,
        "strong_commerce_action_like_count": 0,
        "paired_strong_commerce_control_count": 0,
        "native_or_role_control_count": 1,
        "title_local_root_quorum_satisfied": False,
        "candidate_samples": [_local_candidate(), _local_candidate("COMMERCE_SEMANTIC_ACTION", semantic_hint="QUANTITY_LIKE"), _local_candidate("NATIVE_OR_ROLE_CONTROL")],
    }
    FakeManager.payload = _payload(page_state=_state("NONE"), root_probe=_root_probe("NONE"), title_local_topology_probe=[quantity_variant_only])
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{NO_BOUNDED_PDP_ROOT}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path / "qv", cdp_endpoint=ENDPOINT, manager_factory=FakeManager)


@pytest.mark.asyncio
async def test_truncation_fails_closed_and_does_not_skip_narrower_unresolved_subtree(external_temp_path):
    # Level 1 truncated without quorum -> fails closed even though level 2 has quorum
    level1_truncated = {
        **_title_local_topology_probe()[0],
        "ancestor_level": 1,
        "bounded_nodes_scanned": 300,
        "bounded_scan_truncated": True,
        "visible_currency_like_count": 0,
        "strong_commerce_action_like_count": 0,
        "paired_strong_commerce_control_count": 0,
        "title_local_root_quorum_satisfied": False,
        "candidate_samples": [],
    }
    level2_quorum = {
        **_title_local_topology_probe()[0],
        "ancestor_level": 2,
        "bounded_nodes_scanned": 50,
        "bounded_scan_truncated": False,
        "visible_currency_like_count": 1,
        "strong_commerce_action_like_count": 1,
        "paired_strong_commerce_control_count": 1,
        "title_local_root_quorum_satisfied": True,
        "candidate_samples": [_local_candidate(), _local_candidate("COMMERCE_SEMANTIC_ACTION")],
    }
    # Attempting to select level 2 when level 1 was truncated must fail validation
    invalid_payload = _payload(
        page_state=_state("TITLE_LOCAL_COMMERCE_QUORUM"),
        root_probe=_root_probe("TITLE_LOCAL_COMMERCE_QUORUM", selected_title_local_ancestor_level=2),
        title_local_topology_probe=[level1_truncated, level2_quorum],
    )
    FakeManager.payload = invalid_payload
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{MALFORMED_DIAGNOSTIC_PAYLOAD}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path / "trunc1", cdp_endpoint=ENDPOINT, manager_factory=FakeManager)

    # When level 1 is truncated, root cannot be selected, so it must fail closed as NO_BOUNDED_PDP_ROOT
    probe = _root_probe("NONE")
    FakeManager.payload = _payload(
        page_state=_state("NONE"),
        root_probe=probe,
        title_local_topology_probe=[level1_truncated, level2_quorum],
    )
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{NO_BOUNDED_PDP_ROOT}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path / "trunc2", cdp_endpoint=ENDPOINT, manager_factory=FakeManager)


@pytest.mark.asyncio
async def test_missing_or_ambiguous_title_anchor_fails_closed(external_temp_path):
    # Missing title anchor (count = 0)
    probe_missing = _root_probe("NONE", title_anchor_count=0)
    FakeManager.payload = _payload(page_state=_state("NONE"), root_probe=probe_missing, title_local_topology_probe=[])
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{NO_BOUNDED_PDP_ROOT}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path / "missing", cdp_endpoint=ENDPOINT, manager_factory=FakeManager)

    # Ambiguous title anchor (count = 2)
    probe_ambiguous = _root_probe("NONE", title_anchor_count=2)
    FakeManager.payload = _payload(page_state=_state("NONE"), root_probe=probe_ambiguous)
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{NO_BOUNDED_PDP_ROOT}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path / "ambiguous", cdp_endpoint=ENDPOINT, manager_factory=FakeManager)


def _bad_payloads():
    yield {**_payload(), "raw_html": "<body>forbidden</body>"}
    yield _payload(schema_version=3)
    yield _payload(schema_version=1)
    yield _payload(commerce_probe={**_commerce_probe(), "text_excerpt": "forbidden"})
    yield _payload(commerce_probe=_commerce_probe(document_ready_state="HYDRATED"))
    yield _payload(commerce_probe=_commerce_probe(bounded_nodes_scanned=601))
    yield _payload(commerce_probe=_commerce_probe(bounded_nodes_scanned=599, bounded_scan_truncated=True))
    yield _payload(commerce_probe=_commerce_probe(currency_candidates=[_candidate()] * 4))
    yield _payload(commerce_probe=_commerce_probe(action_candidates=[_candidate("ACTION_LIKE")] * 6))
    yield _payload(commerce_probe=_commerce_probe(title_ancestor_signatures=[_signature()] * 7))
    yield _payload(commerce_probe=_commerce_probe(currency_candidates=[_candidate(match_basis="RAW_TEXT_₫199000")]))
    yield _payload(commerce_probe=_commerce_probe(currency_candidates=[_candidate(**{"data-testid": "199000"})]))
    yield _payload(commerce_probe=_commerce_probe(currency_candidates=[_candidate(relation_to_title="XPATH:/html/body")]))
    yield _payload(commerce_probe=_commerce_probe(action_candidates=[_candidate("ACTION_LIKE", semantic_hint="CHECKOUT")]))
    yield _payload(commerce_probe=_commerce_probe(action_candidates=[_candidate("ACTION_LIKE", match_basis="RAW_BUTTON_TEXT")]))
    yield _payload(commerce_probe=_commerce_probe(action_candidates=[{**_candidate("ACTION_LIKE"), "href": "/buy"}]))
    yield _payload(commerce_probe=_commerce_probe(action_candidates=[{**_candidate("ACTION_LIKE"), "id": "buy"}]))
    yield _payload(commerce_probe=_commerce_probe(action_candidates=[{**_candidate("ACTION_LIKE"), "aria-label": "buy now"}]))
    yield _payload(commerce_probe=_commerce_probe(action_candidates=[_candidate("ACTION_LIKE", **{"data-testid": "arbitrary page text"})]))
    yield _payload(title_local_topology_probe=[_title_local_topology_probe()[0]] * 7)
    yield _payload(title_local_topology_probe=_title_local_topology_probe(bounded_nodes_scanned=301))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(bounded_nodes_scanned=299, bounded_scan_truncated=True))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(ancestor_level=2))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(candidate_samples=[_local_candidate("POINTER_ONLY_INTERACTION")] * 3))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(candidate_samples=[_local_candidate("POINTER_ONLY_INTERACTION"), _local_candidate()]))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(candidate_samples=[{**_local_candidate(), "href": "/raw"}]))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(candidate_samples=[_local_candidate("POINTER_ONLY_INTERACTION", semantic_hint="BUY_LIKE")]))
    yield _payload(title_local_topology_probe=[{**_title_local_topology_probe()[0], "selected_root": "div.pdp"}])
    yield _payload(title_local_topology_probe=_title_local_topology_probe(strong_commerce_action_like_count=2, commerce_semantic_action_like_count=1))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(paired_strong_commerce_control_count=2, strong_commerce_action_like_count=1))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(title_local_root_quorum_satisfied=False))
    yield _payload(title_local_topology_probe=_title_local_topology_probe(visible_currency_like_count=0, title_local_root_quorum_satisfied=True))
    yield _payload(root_probe=_root_probe("TITLE_LOCAL_COMMERCE_QUORUM", selected_title_local_ancestor_level=None))
    yield _payload(root_probe=_root_probe("TITLE_LOCAL_COMMERCE_QUORUM", selected_title_local_ancestor_level=7))
    yield _payload(root_probe=_root_probe("TITLE_LOCAL_COMMERCE_QUORUM", title_anchor_count=2))
    yield _payload(root_probe=_root_probe("EXPLICIT_PDP_ROOT", selected_title_local_ancestor_level=1))
    yield _payload(page_state=_state("TITLE_LOCAL_COMMERCE_QUORUM"), root_probe=_root_probe("TITLE_LOCAL_COMMERCE_QUORUM", selected_title_local_ancestor_level=1), title_local_topology_probe=_title_local_topology_probe(bounded_scan_truncated=True))


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", list(_bad_payloads()))
async def test_forbidden_fields_values_caps_and_enums_fail_closed(external_temp_path, payload):
    FakeManager.payload = payload
    with pytest.raises(TikTokPdpDomDiagnosticError, match=f"^{MALFORMED_DIAGNOSTIC_PAYLOAD}$"):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path, cdp_endpoint=ENDPOINT, manager_factory=FakeManager)
    assert not (external_temp_path / ARTIFACT_FILENAME).exists()


@pytest.mark.asyncio
async def test_existing_v4_artifact_and_repository_root_fail_before_attach(external_temp_path):
    artifact = external_temp_path / ARTIFACT_FILENAME
    artifact.write_text("immutable", encoding="utf-8")
    with pytest.raises(TikTokPdpDomDiagnosticArtifactExistsError):
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path, cdp_endpoint=ENDPOINT, manager_factory=FakeManager)
    with pytest.raises(TikTokPdpDomDiagnosticJobRootError):
        await run_tiktok_pdp_dom_diagnostic(job_root=Path(__file__).resolve().parents[2] / ".git" / "unsafe", cdp_endpoint=ENDPOINT, manager_factory=FakeManager)
    assert artifact.read_text(encoding="utf-8") == "immutable"
    assert FakeManager.instances == []


@pytest.mark.asyncio
async def test_evaluate_failure_releases_via_manager_and_sanitizes_endpoint(external_temp_path):
    primary = RuntimeError("evaluate failed")
    FakeManager.payload = primary
    FakeManager.close_failure = RuntimeError("release failed")
    with pytest.raises(TikTokPdpDomDiagnosticError) as raised:
        await run_tiktok_pdp_dom_diagnostic(job_root=external_temp_path, cdp_endpoint=ENDPOINT, manager_factory=FakeManager)
    assert raised.value.__cause__ is primary
    assert ENDPOINT not in str(raised.value)
    assert FakeManager.instances[0].close_session_calls == FakeManager.instances[0].get_calls


def test_script_is_hard_bounded_light_dom_structural_only_and_preserves_lifecycle():
    source = (Path(__file__).resolve().parents[2] / "src/product_intelligence/tiktok_pdp_dom_diagnostic.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not any(forbidden in name.lower() for name in imports for forbidden in ("product_source", "affiliate", "scoring", "ranking", "approval", "persistence", "tiktok_pdp.tiktokpdpcollector"))
    assert "session.evaluate(DIAGNOSTIC_SCRIPT)" in source
    assert "manager.close_session(_SESSION_RUN_ID)" in source
    assert ".navigate(" not in source and ".click(" not in source and ".scroll(" not in source
    assert "const MAX=600" in DIAGNOSTIC_SCRIPT
    assert "LOCAL_MAX=300" in DIAGNOSTIC_SCRIPT
    assert "const rootSelector='[data-e2e*=\"pdp\" i], [data-testid*=\"pdp\" i], [itemtype*=\"Product\"]'" in DIAGNOSTIC_SCRIPT
    assert "const titleSelectors=['h1','[role=\"heading\"][aria-level=\"1\"]','[data-e2e*=\"title\" i]','[data-testid*=\"title\" i]','[itemprop=\"name\"]']" in DIAGNOSTIC_SCRIPT
    assert "const priceSelectors=['[data-e2e*=\"price\" i]','[data-testid*=\"price\" i]','[itemprop=\"price\"]','[class*=\"price\" i]']" in DIAGNOSTIC_SCRIPT
    assert "const actionSelectors=['button[data-e2e*=\"buy\" i]','button[data-testid*=\"buy\" i]','button[data-e2e*=\"cart\" i]','button[data-testid*=\"cart\" i]','[data-e2e*=\"quantity\" i]','[data-testid*=\"quantity\" i]','[data-e2e*=\"variant\" i]','[data-testid*=\"variant\" i]','[role=\"radiogroup\"]','select']" in DIAGNOSTIC_SCRIPT
    assert "document.createTreeWalker(document.documentElement,NodeFilter.SHOW_ELEMENT)" in DIAGNOSTIC_SCRIPT
    assert "querySelectorAll('*')" not in DIAGNOSTIC_SCRIPT
    assert ".contentDocument" not in DIAGNOSTIC_SCRIPT and ".shadowRoot.querySelector" not in DIAGNOSTIC_SCRIPT
    assert "bounded_scan_truncated:truncated" in DIAGNOSTIC_SCRIPT
    assert "title_local_topology_probe:titleLocal" in DIAGNOSTIC_SCRIPT
    assert "ancestor_level:level" in DIAGNOSTIC_SCRIPT
    assert "current_price_selector_match_count:pm" in DIAGNOSTIC_SCRIPT
    assert "current_action_selector_match_count:am" in DIAGNOSTIC_SCRIPT
    assert "commerce_semantic_action_like_count:sc" in DIAGNOSTIC_SCRIPT
    assert "strong_commerce_action_like_count:stc" in DIAGNOSTIC_SCRIPT
    assert "paired_strong_commerce_control_count:pairedCount" in DIAGNOSTIC_SCRIPT
    assert "title_local_root_quorum_satisfied:quorum" in DIAGNOSTIC_SCRIPT
    assert "native_or_role_control_count:nc" in DIAGNOSTIC_SCRIPT
    assert "pointer_only_interaction_count:pi" in DIAGNOSTIC_SCRIPT
    assert "selected_title_local_ancestor_level:selectedLevel" in DIAGNOSTIC_SCRIPT
    assert "candidate_samples:[...currencySamples,...semanticSamples,...nativeSamples,...pointerSamples]" in DIAGNOSTIC_SCRIPT
    assert "currency_candidates:currencies" in DIAGNOSTIC_SCRIPT and "action_candidates:actions" in DIAGNOSTIC_SCRIPT
    assert "document.body.innerText" not in DIAGNOSTIC_SCRIPT and "innerHTML" not in DIAGNOSTIC_SCRIPT and "outerHTML" not in DIAGNOSTIC_SCRIPT
    assert "TITLE_LOCAL_COMMERCE_QUORUM" in DIAGNOSTIC_SCRIPT
    assert "schema_version:4" in DIAGNOSTIC_SCRIPT


def test_script_has_valid_four_or_more_digit_atom_rejection_guard():
    """Regress the exact missing-opening-delimiter defect, not general JS syntax."""
    assert r"&&!/\d{4,}/.test(s)" in DIAGNOSTIC_SCRIPT
    assert r"&&!\d{4,}/.test(s)" not in DIAGNOSTIC_SCRIPT
