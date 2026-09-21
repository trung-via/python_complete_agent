"""Deterministic offline contract tests for the authorized one-shot carrier."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from src.product_intelligence.adapters.tiktok_pdp import (
    TikTokPdpBindingReceipt,
    TikTokPdpBlockedOrLoginError,
    TikTokPdpCollectionResult,
    TikTokPdpExtractionError,
    TikTokPdpIdentityBasis,
    TikTokPdpIdentityError,
)
from src.product_intelligence.models import ProductCandidateSnapshot
from src.product_intelligence.tiktok_pdp_live_pilot import (
    ARTIFACT_FILENAME,
    AUTHORIZED_PDP_URL,
    AUTHORIZED_SOURCE_ID,
    PILOT_CONTEXT_ID,
    TikTokPdpLivePilotArtifactExistsError,
    TikTokPdpLivePilotJobRootError,
    run_tiktok_pdp_live_pilot,
)


OBSERVED_AT = datetime(2026, 9, 21, 9, 30, tzinfo=timezone.utc)
ENDPOINT = "http://operator-only.invalid:9222/devtools/browser/secret-value"


def _result() -> TikTokPdpCollectionResult:
    return TikTokPdpCollectionResult(
        snapshot=ProductCandidateSnapshot(
            candidate_id=f"tiktok:{AUTHORIZED_SOURCE_ID}",
            platform="tiktok",
            source_product_id=AUTHORIZED_SOURCE_ID,
            url=AUTHORIZED_PDP_URL,
            observed_at=OBSERVED_AT,
            collector="tiktok_public_pdp_v1",
            title="Den LED cam bien chuyen dong",
            shop_name="Example Shop",
            price=99000.0,
            original_price=129000.0,
            discount_percent=23.0,
            sold_count=12,
            rating=4.8,
            review_count=7,
        ),
        binding=TikTokPdpBindingReceipt(
            requested_url=AUTHORIZED_PDP_URL,
            observed_url=AUTHORIZED_PDP_URL,
            identity_bases=(
                TikTokPdpIdentityBasis("OBSERVED_URL", AUTHORIZED_SOURCE_ID),
            ),
        ),
    )


class FakeSession:
    close_calls = 0

    async def close(self):
        self.close_calls += 1
        raise AssertionError("Human browser must not be closed")


class FakeManager:
    instances = []

    def __init__(self, *, cdp_endpoint):
        self.cdp_endpoint = cdp_endpoint
        self.session = FakeSession()
        self.get_calls = []
        self.close_session_calls = 0
        self.close_all_calls = 0
        type(self).instances.append(self)

    async def get_or_create_session(self, run_id):
        self.get_calls.append(run_id)
        return self.session

    async def close_session(self, run_id):
        self.close_session_calls += 1
        raise AssertionError(run_id)

    async def close_all(self):
        self.close_all_calls += 1
        raise AssertionError("Human browser must not be closed")


class FakeCollector:
    instances = []
    failure = None

    def __init__(self, session):
        self.session = session
        self.calls = []
        type(self).instances.append(self)

    async def collect(self, requested_url, *, observed_at):
        self.calls.append((requested_url, observed_at))
        if type(self).failure is not None:
            raise type(self).failure
        return _result()


@pytest.fixture(autouse=True)
def _reset_fakes():
    FakeManager.instances = []
    FakeCollector.instances = []
    FakeCollector.failure = None


@pytest.mark.asyncio
async def test_success_is_fixed_one_attempt_exclusive_safe_and_secret_free(tmp_path):
    root = tmp_path / "external-pilot"
    outcome = await run_tiktok_pdp_live_pilot(
        job_root=root,
        cdp_endpoint=ENDPOINT,
        clock=lambda: OBSERVED_AT,
        manager_factory=FakeManager,
        collector_factory=FakeCollector,
    )

    assert len(FakeManager.instances) == len(FakeCollector.instances) == 1
    manager = FakeManager.instances[0]
    collector = FakeCollector.instances[0]
    assert manager.cdp_endpoint == ENDPOINT
    assert len(manager.get_calls) == 1
    assert collector.session is manager.session
    assert collector.calls == [(AUTHORIZED_PDP_URL, OBSERVED_AT)]
    assert OBSERVED_AT.tzinfo is not None and OBSERVED_AT.utcoffset() is not None
    assert manager.close_session_calls == manager.close_all_calls == 0
    assert manager.session.close_calls == 0

    assert outcome.artifact_path == root.resolve() / ARTIFACT_FILENAME
    document = json.loads(outcome.artifact_path.read_text(encoding="utf-8"))
    assert document == outcome.to_document()
    assert document["operation"] == {
        "status": "SUCCESS",
        "classification": "ONE_SHOT_LIVE_PUBLIC_PDP_PILOT_ENABLEMENT_AND_AUTHORIZATION",
        "context_id": PILOT_CONTEXT_ID,
        "source_product_id": AUTHORIZED_SOURCE_ID,
        "requested_url": AUTHORIZED_PDP_URL,
        "observed_at": OBSERVED_AT.isoformat(),
        "authorized_capture_attempts": 1,
        "capture_execution_owner": "HUMAN_OPERATOR",
        "review_status": "HUMAN_REVIEW_REQUIRED",
    }
    assert set(document) == {"schema_version", "operation", "binding", "snapshot"}
    assert set(document["snapshot"]) == {
        "candidate_id",
        "platform",
        "source_product_id",
        "url",
        "observed_at",
        "collector",
        "title",
        "shop_name",
        "price",
        "original_price",
        "discount_percent",
        "sold_count",
        "rating",
        "review_count",
    }
    persisted = outcome.artifact_path.read_text(encoding="utf-8")
    assert ENDPOINT not in persisted
    for forbidden in (
        "cookie",
        "token",
        "credential",
        "raw_html",
        "screenshot",
        "affiliate",
        "sales_velocity",
        "category",
        "brand",
        "model",
    ):
        assert forbidden not in persisted.lower()


@pytest.mark.asyncio
async def test_repository_job_root_fails_before_browser_or_collector():
    repository_root = Path(__file__).resolve().parents[2]
    with pytest.raises(TikTokPdpLivePilotJobRootError):
        await run_tiktok_pdp_live_pilot(
            job_root=repository_root / ".git" / "unsafe-pilot",
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )
    assert FakeManager.instances == FakeCollector.instances == []


@pytest.mark.asyncio
async def test_existing_artifact_is_not_overwritten_or_attempted(tmp_path):
    root = tmp_path / "external-pilot"
    root.mkdir()
    artifact = root / ARTIFACT_FILENAME
    artifact.write_text("do-not-overwrite", encoding="utf-8")
    with pytest.raises(TikTokPdpLivePilotArtifactExistsError):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )
    assert artifact.read_text(encoding="utf-8") == "do-not-overwrite"
    assert FakeManager.instances == FakeCollector.instances == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    (
        TikTokPdpBlockedOrLoginError("challenge or login stopped capture"),
        TikTokPdpIdentityError("identity mismatch stopped capture"),
        TikTokPdpExtractionError("required title was unavailable"),
    ),
)
async def test_collection_failures_create_no_snapshot_and_never_retry(tmp_path, failure):
    FakeCollector.failure = failure
    root = tmp_path / "failed-pilot"
    with pytest.raises(type(failure)):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )
    assert len(FakeCollector.instances) == 1
    assert FakeCollector.instances[0].calls == [(AUTHORIZED_PDP_URL, OBSERVED_AT)]
    assert not (root / ARTIFACT_FILENAME).exists()
    manager = FakeManager.instances[0]
    assert manager.close_session_calls == manager.close_all_calls == 0
    assert manager.session.close_calls == 0


@pytest.mark.asyncio
async def test_naive_clock_fails_before_capture(tmp_path):
    with pytest.raises(Exception, match="timezone-aware"):
        await run_tiktok_pdp_live_pilot(
            job_root=tmp_path / "pilot",
            cdp_endpoint=ENDPOINT,
            clock=lambda: datetime(2026, 9, 21, 9, 30),
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )
    assert FakeManager.instances == FakeCollector.instances == []


def test_carrier_has_no_forbidden_semantic_or_lifecycle_dependencies():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "product_intelligence"
        / "tiktok_pdp_live_pilot.py"
    )
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
            "product_source",
            "affiliate",
            "scoring",
            "ranking",
            "approval",
            "persistence",
        )
    )
    assert ".close(" not in source
    assert "close_session" not in source
    assert "close_all" not in source
    assert "retry" not in source.lower()
    assert "while " not in source
    assert "for requested_url" not in source
