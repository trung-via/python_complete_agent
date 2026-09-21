"""Offline regressions for the fixed attach-only TikTok PDP DOM diagnostic."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

import pytest

from src.product_intelligence.tiktok_pdp_dom_diagnostic import (
    ARTIFACT_FILENAME,
    DIAGNOSTIC_CONTEXT_ID,
    DIAGNOSTIC_SCRIPT,
    DIAGNOSTIC_SOURCE_ID,
    TikTokPdpDomDiagnosticArtifactExistsError,
    TikTokPdpDomDiagnosticError,
    TikTokPdpDomDiagnosticJobRootError,
    run_tiktok_pdp_dom_diagnostic,
)


OBSERVED_AT = datetime(2026, 9, 21, 10, 15, tzinfo=timezone.utc)
ENDPOINT = "http://operator.invalid:9222/devtools/browser/diagnostic-secret"
OBSERVED_URL = (
    "https://shop.tiktok.com/vn/pdp/"
    "den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/1731381331718341815"
)


def _candidate(hint="TITLE_LIKE", excerpt="bounded visible excerpt"):
    return {
        "field_hint": hint,
        "text_excerpt": excerpt,
        "tag_name": "h1",
        "class_tokens": ["title", "pdp"],
        "data-testid": "product-title",
        "data-e2e": "",
        "aria-label": "",
        "role": "heading",
        "itemprop": "name",
        "parent_signature": "div.product",
        "grandparent_signature": "main.pdp",
    }


def _payload(**overrides):
    payload = {
        "schema_version": 1,
        "observed_url": OBSERVED_URL,
        "explicit_product_ids": [DIAGNOSTIC_SOURCE_ID],
        "page_state": {
            "has_bounded_root": True,
            "blocked": False,
            "login": False,
            "unavailable": False,
        },
        "candidates": [_candidate()],
    }
    payload.update(overrides)
    return payload


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
        raise AssertionError("diagnostic must not directly close the borrowed session")


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
        if type(self).close_failure is not None:
            raise type(self).close_failure

    async def close_all(self):
        self.close_all_calls += 1
        raise AssertionError("diagnostic must not call close_all")


@pytest.fixture(autouse=True)
def _reset_fakes():
    FakeManager.instances = []
    FakeManager.payload = _payload()
    FakeManager.close_failure = None


@pytest.fixture
def external_temp_path():
    with tempfile.TemporaryDirectory(prefix="task234-dom-diagnostic-") as directory:
        yield Path(directory)


@pytest.mark.asyncio
async def test_success_evaluates_once_is_fixed_bounded_external_and_secret_free(
    external_temp_path,
):
    root = external_temp_path / "diagnostic"
    outcome = await run_tiktok_pdp_dom_diagnostic(
        job_root=root,
        cdp_endpoint=ENDPOINT,
        clock=lambda: OBSERVED_AT,
        manager_factory=FakeManager,
    )
    manager = FakeManager.instances[0]
    assert manager.cdp_endpoint == ENDPOINT
    assert manager.get_calls == [f"human-dom-diagnostic:{DIAGNOSTIC_CONTEXT_ID}"]
    assert manager.session.evaluate_calls == [DIAGNOSTIC_SCRIPT]
    assert manager.session.navigate_calls == manager.session.click_calls == []
    assert manager.session.type_calls == manager.session.scroll_calls == []
    assert manager.close_session_calls == manager.get_calls
    assert manager.close_all_calls == manager.session.close_calls == 0

    assert outcome.artifact_path == root.resolve() / ARTIFACT_FILENAME
    document = json.loads(outcome.artifact_path.read_text(encoding="utf-8"))
    assert document == outcome.to_document()
    assert document["diagnostic"] == {
        "status": "SUCCESS",
        "classification": "ATTACH_ONLY_BOUNDED_DOM_DIAGNOSTIC",
        "context_id": DIAGNOSTIC_CONTEXT_ID,
        "source_product_id": DIAGNOSTIC_SOURCE_ID,
        "observed_at": OBSERVED_AT.isoformat(),
        "evidence_authority": "NONE",
        "candidate_count": 1,
    }
    assert set(document) == {"schema_version", "diagnostic", "candidates"}
    assert set(document["candidates"][0]) == {
        "field_hint", "text_excerpt", "tag_name", "class_tokens", "data-testid",
        "data-e2e", "aria-label", "role", "itemprop", "parent_signature",
        "grandparent_signature",
    }
    persisted = outcome.artifact_path.read_text(encoding="utf-8").lower()
    assert ENDPOINT.lower() not in persisted
    for forbidden in (
        "innerhtml", "outerhtml", "cookie", "localstorage", "sessionstorage",
        "header", "request_body", "response_body", "credential", "qr", "profile",
        "screenshot", "affiliate", "productcandidatesnapshot", "signalevidence",
    ):
        assert forbidden not in persisted


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    (
        _payload(page_state={"has_bounded_root": True, "blocked": True, "login": False, "unavailable": False}),
        _payload(page_state={"has_bounded_root": True, "blocked": False, "login": True, "unavailable": False}),
        _payload(page_state={"has_bounded_root": True, "blocked": False, "login": False, "unavailable": True}),
        _payload(observed_url="https://shop.tiktok.com/vn/pdp/other/999", explicit_product_ids=["999"]),
        _payload(
            observed_url="https://shop.tiktok.com/vn/search?q=led",
            explicit_product_ids=[DIAGNOSTIC_SOURCE_ID],
        ),
    ),
)
async def test_unavailable_challenge_login_unrelated_or_unverifiable_fails_closed(
    external_temp_path, payload
):
    FakeManager.payload = payload
    root = external_temp_path / "failed"
    with pytest.raises(TikTokPdpDomDiagnosticError):
        await run_tiktok_pdp_dom_diagnostic(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
        )
    manager = FakeManager.instances[0]
    assert len(manager.session.evaluate_calls) == 1
    assert manager.close_session_calls == manager.get_calls
    assert not (root / ARTIFACT_FILENAME).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "observed_url",
    (
        "https://shop.tiktok.com/vn",
        "https://shop.tiktok.com/vn/category/home-and-living",
    ),
)
async def test_unrelated_shop_page_with_target_product_card_fails_closed(
    external_temp_path, observed_url
):
    FakeManager.payload = _payload(
        observed_url=observed_url,
        explicit_product_ids=[DIAGNOSTIC_SOURCE_ID],
    )
    root = external_temp_path / "unrelated-card"

    with pytest.raises(TikTokPdpDomDiagnosticError):
        await run_tiktok_pdp_dom_diagnostic(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
        )

    assert not (root / ARTIFACT_FILENAME).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("state_name", ("blocked", "login"))
async def test_challenge_or_login_overlay_over_valid_pdp_fails_closed(
    external_temp_path, state_name
):
    page_state = {
        "has_bounded_root": True,
        "blocked": False,
        "login": False,
        "unavailable": False,
    }
    page_state[state_name] = True
    FakeManager.payload = _payload(page_state=page_state)
    root = external_temp_path / f"{state_name}-overlay"

    with pytest.raises(TikTokPdpDomDiagnosticError):
        await run_tiktok_pdp_dom_diagnostic(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
        )

    assert not (root / ARTIFACT_FILENAME).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    (
        {**_payload(), "raw_html": "<body>forbidden</body>"},
        _payload(candidates=[_candidate(excerpt="x" * 121)]),
        _payload(candidates=[_candidate()] * 4),
        _payload(candidates=[_candidate("SHOP_LIKE"), _candidate("TITLE_LIKE")]),
    ),
)
async def test_malformed_unbounded_over_cap_or_unsorted_payload_is_rejected(
    external_temp_path, payload
):
    FakeManager.payload = payload
    with pytest.raises(TikTokPdpDomDiagnosticError):
        await run_tiktok_pdp_dom_diagnostic(
            job_root=external_temp_path / "malformed",
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
        )


@pytest.mark.asyncio
async def test_repository_root_and_existing_artifact_fail_before_attach(external_temp_path):
    repository_root = Path(__file__).resolve().parents[2]
    with pytest.raises(TikTokPdpDomDiagnosticJobRootError):
        await run_tiktok_pdp_dom_diagnostic(
            job_root=repository_root / ".git" / "unsafe",
            cdp_endpoint=ENDPOINT,
            manager_factory=FakeManager,
        )
    root = external_temp_path / "exclusive"
    root.mkdir()
    artifact = root / ARTIFACT_FILENAME
    artifact.write_text("preserve", encoding="utf-8")
    with pytest.raises(TikTokPdpDomDiagnosticArtifactExistsError):
        await run_tiktok_pdp_dom_diagnostic(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            manager_factory=FakeManager,
        )
    assert artifact.read_text(encoding="utf-8") == "preserve"
    assert FakeManager.instances == []


@pytest.mark.asyncio
async def test_evaluate_failure_releases_session_and_preserves_primary(external_temp_path):
    primary = RuntimeError("evaluate failed")
    FakeManager.payload = primary
    FakeManager.close_failure = RuntimeError("release also failed")
    with pytest.raises(TikTokPdpDomDiagnosticError) as raised:
        await run_tiktok_pdp_dom_diagnostic(
            job_root=external_temp_path / "failed",
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
        )
    assert raised.value.__cause__ is primary
    assert ENDPOINT not in str(raised.value)
    manager = FakeManager.instances[0]
    assert len(manager.session.evaluate_calls) == 1
    assert manager.close_session_calls == manager.get_calls
    assert manager.close_all_calls == manager.session.close_calls == 0


def test_diagnostic_source_has_no_navigation_or_forbidden_semantic_dependencies():
    module_path = Path(__file__).resolve().parents[2] / "src" / "product_intelligence" / "tiktok_pdp_dom_diagnostic.py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(
        forbidden in imported.lower()
        for imported in imports
        for forbidden in (
            "product_source", "affiliate", "scoring", "ranking", "approval", "persistence",
            "tiktok_pdp.TikTokPdpCollector",
        )
    )
    assert ".navigate(" not in source
    assert ".click(" not in source
    assert ".type_text(" not in source
    assert ".scroll(" not in source
    assert "session.evaluate(DIAGNOSTIC_SCRIPT)" in source
    assert "manager.close_session(_SESSION_RUN_ID)" in source
    assert "close_all" not in source
    assert "session.close" not in source


def test_diagnostic_script_scopes_identity_and_detects_page_level_overlays():
    assert "root.querySelectorAll(" in DIAGNOSTIC_SCRIPT
    assert "node.closest(pdpRootSelector) === root" in DIAGNOSTIC_SCRIPT
    assert "iframe[src*=\"captcha\" i]" in DIAGNOSTIC_SCRIPT
    assert "form[action*=\"/login\" i]" in DIAGNOSTIC_SCRIPT
    assert "input[type=\"password\"]" in DIAGNOSTIC_SCRIPT
    assert "meta[itemprop=\"productID\"], [data-product-id]" not in DIAGNOSTIC_SCRIPT
