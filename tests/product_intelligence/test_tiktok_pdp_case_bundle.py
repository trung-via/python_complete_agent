"""Offline regressions for the attach-only P8 Real Case Evidence Bundle carrier."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import pytest

from src.product_intelligence.tiktok_pdp_case_bundle import (
    AUTHORIZED_PDP_URL,
    AUTHORIZED_SOURCE_ID,
    BLOCKED_OR_CHALLENGE,
    CASE_BUNDLE_SCRIPT,
    CLASSIFICATION,
    CONTEXT_ID,
    EPISTEMIC_BOUNDARY,
    IDENTITY_MISMATCH,
    LISTING_UNAVAILABLE,
    LOGIN_GATE,
    MALFORMED_PROJECTION,
    MANIFEST_FILENAME,
    POST_MANIFEST_WRITE_FAILURE,
    PROJECTION_FILENAME,
    SANITATION_POLICY,
    SCREENSHOT_FILENAME,
    TikTokPdpCaseBundleArtifactExistsError,
    TikTokPdpCaseBundleError,
    TikTokPdpCaseBundleJobRootError,
    TikTokPdpCaseBundleOutcome,
    run_tiktok_pdp_case_bundle,
)

OBSERVED_AT = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
ENDPOINT = "http://operator.invalid:9222/devtools/browser/case-bundle-secret"
OBSERVED_URL = f"https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/{AUTHORIZED_SOURCE_ID}"
PNG_PAYLOAD = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


def _sample_record(ordinal: int = 1, tag: str = "h1", text: str = "Test Title", **overrides):
    rec = {
        "ordinal": ordinal,
        "tag_name": tag,
        "role": "heading",
        "itemprop": "name",
        "data-testid": "product-title",
        "data-e2e": "pdp-title",
        "class_tokens": ["title-text", "header"],
        "section_heading_context": "Product Information",
        "visible_text": text,
        "is_leaf": True,
    }
    rec.update(overrides)
    return rec


def _valid_projection_payload(**overrides):
    payload = {
        "schema_version": 1,
        "observed_url": OBSERVED_URL,
        "page_state": {
            "identity_bound": True,
            "blocked": False,
            "login": False,
            "unavailable": False,
        },
        "truncation": {
            "is_truncated": False,
            "scanned_nodes_truncated": False,
            "records_truncated": False,
            "text_truncated": False,
            "bytes_truncated": False,
            "total_scanned_nodes": 50,
            "total_records": 2,
        },
        "records": [
            _sample_record(1, "h1", "Đèn LED Cảm Biến Chuyển Động"),
            _sample_record(2, "span", "33.600₫", role="", itemprop="price"),
        ],
    }
    payload.update(overrides)
    return payload


class FakeSession:
    def __init__(self, payload=None, png_bytes=PNG_PAYLOAD, evaluate_exc=None, screenshot_exc=None):
        self.payload = payload if payload is not None else _valid_projection_payload()
        self.png_bytes = png_bytes
        self.evaluate_exc = evaluate_exc
        self.screenshot_exc = screenshot_exc
        self.evaluate_calls = []
        self.screenshot_calls = 0

    async def evaluate(self, script: str):
        self.evaluate_calls.append(script)
        if self.evaluate_exc is not None:
            raise self.evaluate_exc
        return self.payload

    async def screenshot(self) -> bytes:
        self.screenshot_calls += 1
        if self.screenshot_exc is not None:
            raise self.screenshot_exc
        return self.png_bytes


class FakeManager:
    def __init__(self, session: FakeSession | None = None, session_exc=None, close_exc=None):
        self.session = session or FakeSession()
        self.session_exc = session_exc
        self.close_exc = close_exc
        self.acquired_run_ids = []
        self.closed_run_ids = []

    async def get_or_create_session(self, run_id: str):
        if self.session_exc is not None:
            raise self.session_exc
        self.acquired_run_ids.append(run_id)
        return self.session

    async def close_session(self, run_id: str):
        self.closed_run_ids.append(run_id)
        if self.close_exc is not None:
            raise self.close_exc


@pytest.mark.asyncio
async def test_case_bundle_success_flow(tmp_path):
    fake_session = FakeSession()
    fake_manager = FakeManager(session=fake_session)
    job_root = tmp_path / "bundle-run-001"

    outcome = await run_tiktok_pdp_case_bundle(
        job_root=job_root,
        cdp_endpoint=ENDPOINT,
        clock=lambda: OBSERVED_AT,
        manager_factory=lambda cdp_endpoint: fake_manager,
    )

    assert isinstance(outcome, TikTokPdpCaseBundleOutcome)
    assert outcome.manifest_path == job_root / MANIFEST_FILENAME
    assert outcome.projection_path == job_root / PROJECTION_FILENAME
    assert outcome.screenshot_path == job_root / SCREENSHOT_FILENAME

    # Exactly three files created
    files = sorted(p.name for p in job_root.iterdir())
    assert files == [
        "p8-real-case-full-page-v1.png",
        "p8-real-case-manifest-v1.json",
        "p8-real-case-page-projection-v1.json",
    ]

    # Verify manifest contents
    manifest_bytes = outcome.manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest["schema_version"] == 1
    assert manifest["bundle_version"] == 1
    assert manifest["classification"] == CLASSIFICATION
    assert manifest["context_id"] == CONTEXT_ID
    assert manifest["source_product_id"] == AUTHORIZED_SOURCE_ID
    assert manifest["requested_url"] == AUTHORIZED_PDP_URL
    assert manifest["stable_listing_reference"] == AUTHORIZED_PDP_URL
    assert manifest["execution_owner"] == "HUMAN_OPERATOR"
    assert manifest["review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert manifest["screenshot_review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert manifest["epistemic_boundary"] == EPISTEMIC_BOUNDARY
    assert manifest["sanitation_policy"] == SANITATION_POLICY

    # Verify projection hash and byte count
    proj_bytes = outcome.projection_path.read_bytes()
    expected_proj_hash = hashlib.sha256(proj_bytes).hexdigest().upper()
    assert manifest["artifacts"]["page_projection"]["sha256"] == expected_proj_hash
    assert manifest["artifacts"]["page_projection"]["byte_count"] == len(proj_bytes)

    # Verify screenshot hash and byte count
    shot_bytes = outcome.screenshot_path.read_bytes()
    expected_shot_hash = hashlib.sha256(shot_bytes).hexdigest().upper()
    assert manifest["artifacts"]["screenshot"]["sha256"] == expected_shot_hash
    assert manifest["artifacts"]["screenshot"]["byte_count"] == len(shot_bytes)
    assert shot_bytes == PNG_PAYLOAD

    # Verify session lifecycle
    assert len(fake_session.evaluate_calls) == 1
    assert fake_session.evaluate_calls[0] == CASE_BUNDLE_SCRIPT
    assert fake_session.screenshot_calls == 1
    assert fake_manager.acquired_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]
    assert fake_manager.closed_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]

    # Verify document presentation
    doc = outcome.to_document()
    assert doc["bundle"]["status"] == "SUCCESS"
    assert doc["bundle"]["classification"] == CLASSIFICATION


@pytest.mark.asyncio
async def test_job_root_inside_repository_fails_without_consuming():
    repo_root = Path(__file__).resolve().parents[2]
    with pytest.raises(TikTokPdpCaseBundleJobRootError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=repo_root / "inside_repo",
            cdp_endpoint=ENDPOINT,
        )
    assert "must be outside the Git repository" in str(exc_info.value)


@pytest.mark.asyncio
async def test_empty_job_root_or_cdp_fails_without_consuming(tmp_path):
    with pytest.raises(TikTokPdpCaseBundleJobRootError):
        await run_tiktok_pdp_case_bundle(job_root="", cdp_endpoint=ENDPOINT)

    with pytest.raises(TikTokPdpCaseBundleError):
        await run_tiktok_pdp_case_bundle(
            job_root=tmp_path / "valid_root",
            cdp_endpoint="   ",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "existing_name",
    [MANIFEST_FILENAME, PROJECTION_FILENAME, SCREENSHOT_FILENAME],
)
async def test_existing_artifact_in_job_root_fails_before_execution(tmp_path, existing_name):
    job_root = tmp_path / "existing-root"
    job_root.mkdir(parents=True, exist_ok=True)
    (job_root / existing_name).write_text("existing", encoding="utf-8")

    called = False

    def factory(cdp_endpoint):
        nonlocal called
        called = True
        return FakeManager()

    with pytest.raises(TikTokPdpCaseBundleArtifactExistsError):
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=factory,
        )
    assert not called


@pytest.mark.asyncio
async def test_session_acquisition_failure_does_not_consume(tmp_path):
    job_root = tmp_path / "session_fail_root"
    fake_manager = FakeManager(session_exc=RuntimeError("CDP connection refused"))

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp: fake_manager,
        )
    assert "could not be borrowed" in str(exc_info.value)
    assert not job_root.exists() or list(job_root.iterdir()) == []


@pytest.mark.asyncio
async def test_evaluate_failure_does_not_consume(tmp_path):
    job_root = tmp_path / "eval_fail_root"
    fake_session = FakeSession(evaluate_exc=RuntimeError("JS execution crashed"))
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp: fake_manager,
        )
    assert "bounded page projection evaluation failed" in str(exc_info.value)
    assert not (job_root / MANIFEST_FILENAME).exists()
    assert fake_manager.closed_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]


@pytest.mark.asyncio
async def test_screenshot_failure_does_not_consume(tmp_path):
    job_root = tmp_path / "shot_fail_root"
    fake_session = FakeSession(screenshot_exc=RuntimeError("Screenshot crashed"))
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp: fake_manager,
        )
    assert "full-page screenshot capture failed" in str(exc_info.value)
    assert not (job_root / MANIFEST_FILENAME).exists()


@pytest.mark.asyncio
async def test_invalid_screenshot_bytes_fail_without_consuming(tmp_path):
    job_root = tmp_path / "invalid_shot_root"
    fake_session = FakeSession(png_bytes=b"not-a-png-file")
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp: fake_manager,
        )
    assert "not a valid PNG image" in str(exc_info.value)
    assert not (job_root / MANIFEST_FILENAME).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flag", "error_code"),
    [
        ("blocked", BLOCKED_OR_CHALLENGE),
        ("login", LOGIN_GATE),
        ("unavailable", LISTING_UNAVAILABLE),
    ],
)
async def test_page_state_failures_fail_closed_without_consuming(tmp_path, flag, error_code):
    job_root = tmp_path / f"state_{flag}_root"
    payload = _valid_projection_payload()
    payload["page_state"][flag] = True

    fake_session = FakeSession(payload=payload)
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp: fake_manager,
        )
    assert str(exc_info.value) == error_code
    assert not (job_root / MANIFEST_FILENAME).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_url",
    [
        "https://shop.tiktok.com/vn/pdp/other-slug/9999999999999999999",
        "https://evil.com/vn/pdp/item/1731381331718341815",
        "https://shop.tiktok.com/us/pdp/item/1731381331718341815",
    ],
)
async def test_identity_mismatch_fails_closed_without_consuming(tmp_path, bad_url):
    job_root = tmp_path / "bad_url_root"
    payload = _valid_projection_payload(observed_url=bad_url)
    fake_session = FakeSession(payload=payload)
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp: fake_manager,
        )
    assert str(exc_info.value) == IDENTITY_MISMATCH
    assert not (job_root / MANIFEST_FILENAME).exists()


@pytest.mark.asyncio
async def test_manifest_first_consumption_and_post_manifest_failure(tmp_path, monkeypatch):
    job_root = tmp_path / "post_manifest_fail_root"
    fake_session = FakeSession()
    fake_manager = FakeManager(session=fake_session)

    original_open = Path.open

    def failing_open(self, mode="r", *args, **kwargs):
        if self.name == PROJECTION_FILENAME and "x" in mode:
            raise PermissionError("Simulated disk error writing projection")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp: fake_manager,
        )
    assert str(exc_info.value) == POST_MANIFEST_WRITE_FAILURE

    # Manifest was created! The attempt is consumed!
    assert (job_root / MANIFEST_FILENAME).exists()
    assert not (job_root / PROJECTION_FILENAME).exists()

    # Second invocation fails because manifest already exists
    with pytest.raises(TikTokPdpCaseBundleArtifactExistsError):
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp: fake_manager,
        )


@pytest.mark.asyncio
async def test_byte_truncation_enforces_limit(tmp_path):
    job_root = tmp_path / "truncation_root"
    # Create large number of records
    large_records = [
        _sample_record(i + 1, "div", f"Item text number {i} " + "X" * 100)
        for i in range(500)
    ]
    payload = _valid_projection_payload(records=large_records)
    fake_session = FakeSession(payload=payload)
    fake_manager = FakeManager(session=fake_session)

    outcome = await run_tiktok_pdp_case_bundle(
        job_root=job_root,
        cdp_endpoint=ENDPOINT,
        manager_factory=lambda cdp: fake_manager,
    )

    proj_bytes = outcome.projection_path.read_bytes()
    assert len(proj_bytes) <= 256 * 1024
    proj_doc = json.loads(proj_bytes)
    assert proj_doc["truncation"]["is_truncated"] is True
    assert proj_doc["truncation"]["bytes_truncated"] is True


def test_ast_no_forbidden_intelligence_or_decision_imports():
    source_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "product_intelligence"
        / "tiktok_pdp_case_bundle.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    forbidden_symbols = {
        "ProductCandidateSnapshot",
        "SignalEvidence",
        "TikTokAffiliateEvidenceProfile",
        "ValueOfInformationPlan",
        "MarketTestEvidenceProfile",
        "CommerceDecisionLoopCase",
        "WinningProductScorer",
        "RankedCandidate",
    }

    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)

    intersection = imported_names.intersection(forbidden_symbols)
    assert not intersection, f"Forbidden symbols imported: {intersection}"
