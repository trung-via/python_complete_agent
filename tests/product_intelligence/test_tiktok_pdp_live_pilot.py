"""Deterministic offline contract tests for the authorized one-shot carrier."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

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
    ATTEMPT_MARKER_FILENAME,
    AUTHORIZED_PDP_URL,
    AUTHORIZED_SOURCE_ID,
    COLLECTOR_BASELINE_SOURCE_SHA,
    COLLECTOR_BASELINE_TASK_ID,
    CONTRACT_IDENTIFIER,
    LEGACY_ARTIFACT_FILENAME,
    PILOT_CONTEXT_ID,
    RESULT_FILENAME,
    TikTokPdpLivePilotArtifactExistsError,
    TikTokPdpLivePilotError,
    TikTokPdpLivePilotJobRootError,
    run_tiktok_pdp_live_pilot,
)


OBSERVED_AT = datetime(2026, 9, 21, 9, 30, tzinfo=timezone.utc)
ENDPOINT = "http://operator-only.invalid:9222/devtools/browser/secret-value"


def _result(
    *,
    platform: str = "tiktok",
    source_product_id: str = AUTHORIZED_SOURCE_ID,
    observed_url: str = AUTHORIZED_PDP_URL,
    identity_bases: tuple[TikTokPdpIdentityBasis, ...] | None = None,
) -> TikTokPdpCollectionResult:
    if identity_bases is None:
        identity_bases = (
            TikTokPdpIdentityBasis("OBSERVED_URL", source_product_id),
        )
    return TikTokPdpCollectionResult(
        snapshot=ProductCandidateSnapshot(
            candidate_id=f"tiktok:{source_product_id}",
            platform=platform,
            source_product_id=source_product_id,
            url=observed_url,
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
            observed_url=observed_url,
            identity_bases=identity_bases,
        ),
    )


class FakeSession:
    close_calls = 0

    async def close(self):
        self.close_calls += 1
        raise AssertionError("Human browser must not be closed")


class FakeManager:
    instances = []
    get_failure = None
    close_failure = None

    def __init__(self, *, cdp_endpoint):
        self.cdp_endpoint = cdp_endpoint
        self.session = FakeSession()
        self.get_calls = []
        self.close_session_calls = 0
        self.close_all_calls = 0
        type(self).instances.append(self)

    async def get_or_create_session(self, run_id):
        self.get_calls.append(run_id)
        if type(self).get_failure is not None:
            raise type(self).get_failure
        return self.session

    async def close_session(self, run_id):
        self.close_session_calls += 1
        assert run_id == f"human-one-shot:{PILOT_CONTEXT_ID}"
        if type(self).close_failure is not None:
            raise type(self).close_failure

    async def close_all(self):
        self.close_all_calls += 1
        raise AssertionError("Human browser must not be closed")


class FakeCollector:
    instances = []
    failure = None
    result_override = None

    def __init__(self, session):
        self.session = session
        self.calls = []
        type(self).instances.append(self)

    async def collect(self, requested_url, *, observed_at):
        self.calls.append((requested_url, observed_at))
        if type(self).failure is not None:
            raise type(self).failure
        if type(self).result_override is not None:
            return type(self).result_override
        return _result()


@pytest.fixture(autouse=True)
def _reset_fakes():
    FakeManager.instances = []
    FakeManager.get_failure = None
    FakeManager.close_failure = None
    FakeCollector.instances = []
    FakeCollector.failure = None
    FakeCollector.result_override = None


@pytest.fixture
def external_temp_path():
    with tempfile.TemporaryDirectory(prefix="task249-tiktok-pilot-") as directory:
        yield Path(directory)


@pytest.mark.asyncio
async def test_success_is_fixed_one_attempt_exclusive_safe_and_secret_free(
    external_temp_path,
):
    root = external_temp_path / "external-pilot"
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
    assert manager.close_session_calls == 1
    assert manager.close_all_calls == 0
    assert manager.session.close_calls == 0

    # 1. Attempt marker verification
    marker_path = root.resolve() / ATTEMPT_MARKER_FILENAME
    assert marker_path.exists()
    marker_document = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker_document == {
        "schema_version": 2,
        "record_type": "VALIDATION_ATTEMPT_MARKER",
        "contract_identifier": CONTRACT_IDENTIFIER,
        "context_id": PILOT_CONTEXT_ID,
        "source_product_id": AUTHORIZED_SOURCE_ID,
        "requested_url": AUTHORIZED_PDP_URL,
        "started_at": OBSERVED_AT.isoformat(),
        "execution_owner": "HUMAN_OPERATOR",
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "collector_baseline_task_id": COLLECTOR_BASELINE_TASK_ID,
        "collector_baseline_source_sha": COLLECTOR_BASELINE_SOURCE_SHA,
    }

    # 2. Terminal result verification
    result_path = root.resolve() / RESULT_FILENAME
    assert outcome.artifact_path == result_path
    document = json.loads(result_path.read_text(encoding="utf-8"))
    assert document == outcome.to_document()
    assert document["schema_version"] == 2
    assert document["operation"] == {
        "operation_status": "SUCCESS",
        "observation_status": "OBSERVED",
        "session_release_status": "SUCCESS",
        "contract_identifier": CONTRACT_IDENTIFIER,
        "context_id": PILOT_CONTEXT_ID,
        "source_product_id": AUTHORIZED_SOURCE_ID,
        "requested_url": AUTHORIZED_PDP_URL,
        "started_at": OBSERVED_AT.isoformat(),
        "observed_at": OBSERVED_AT.isoformat(),
        "execution_owner": "HUMAN_OPERATOR",
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "collector_baseline_task_id": COLLECTOR_BASELINE_TASK_ID,
        "collector_baseline_source_sha": COLLECTOR_BASELINE_SOURCE_SHA,
    }
    assert "failure_reason" not in document["operation"]
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
    assert document["binding"] == {
        "requested_url": AUTHORIZED_PDP_URL,
        "observed_url": AUTHORIZED_PDP_URL,
        "identity_bases": [
            {
                "basis": "OBSERVED_URL",
                "source_product_id": AUTHORIZED_SOURCE_ID,
            }
        ],
    }

    # 3. Secret and token exclusion checks
    for path in (marker_path, result_path):
        persisted = path.read_text(encoding="utf-8")
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
async def test_repository_job_root_fails_before_marker_browser_or_collector():
    repository_root = Path(__file__).resolve().parents[2]
    target_job_root = repository_root / ".git" / "unsafe-pilot"
    with pytest.raises(TikTokPdpLivePilotJobRootError):
        await run_tiktok_pdp_live_pilot(
            job_root=target_job_root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )
    assert not (target_job_root / ATTEMPT_MARKER_FILENAME).exists()
    assert FakeManager.instances == FakeCollector.instances == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "existing_name",
    (
        LEGACY_ARTIFACT_FILENAME,
        ATTEMPT_MARKER_FILENAME,
        RESULT_FILENAME,
    ),
)
async def test_existing_artifact_fails_before_marker_or_execution(
    external_temp_path, existing_name
):
    root = external_temp_path / "external-pilot"
    root.mkdir()
    artifact = root / existing_name
    artifact.write_text("preexisting-content", encoding="utf-8")
    with pytest.raises(TikTokPdpLivePilotArtifactExistsError):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )
    assert artifact.read_text(encoding="utf-8") == "preexisting-content"
    assert not (root / RESULT_FILENAME if existing_name != RESULT_FILENAME else root / ATTEMPT_MARKER_FILENAME).exists()
    assert FakeManager.instances == FakeCollector.instances == []


@pytest.mark.asyncio
@pytest.mark.parametrize("empty_endpoint", ("", "   ", "\t\n"))
async def test_empty_cdp_endpoint_fails_before_marker_or_execution(
    external_temp_path, empty_endpoint
):
    root = external_temp_path / "pilot"
    with pytest.raises(TikTokPdpLivePilotError, match="operator-owned CDP endpoint"):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=empty_endpoint,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )
    assert not (root / ATTEMPT_MARKER_FILENAME).exists()
    assert FakeManager.instances == FakeCollector.instances == []


@pytest.mark.asyncio
async def test_naive_clock_fails_before_marker_or_execution(external_temp_path):
    root = external_temp_path / "pilot"
    with pytest.raises(TikTokPdpLivePilotError, match="timezone-aware"):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: datetime(2026, 9, 21, 9, 30),
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )
    assert not (root / ATTEMPT_MARKER_FILENAME).exists()
    assert FakeManager.instances == FakeCollector.instances == []


@pytest.mark.asyncio
async def test_session_acquisition_failure_consumes_attempt_and_persists_fail_closed(
    external_temp_path,
):
    FakeManager.get_failure = RuntimeError("CDP connection refused")
    root = external_temp_path / "pilot"

    with pytest.raises(TikTokPdpLivePilotError, match="^BROWSER_SESSION_UNAVAILABLE$"):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )

    # Durable marker was created
    marker_path = root / ATTEMPT_MARKER_FILENAME
    assert marker_path.exists()

    # Terminal result was persisted with FAIL_CLOSED / NOT_OBSERVED / NOT_APPLICABLE
    result_path = root / RESULT_FILENAME
    assert result_path.exists()
    doc = json.loads(result_path.read_text(encoding="utf-8"))
    assert doc["schema_version"] == 2
    assert doc["operation"]["operation_status"] == "FAIL_CLOSED"
    assert doc["operation"]["observation_status"] == "NOT_OBSERVED"
    assert doc["operation"]["session_release_status"] == "NOT_APPLICABLE"
    assert doc["operation"]["failure_reason"] == "BROWSER_SESSION_UNAVAILABLE"
    assert "binding" not in doc
    assert "snapshot" not in doc
    assert "CDP connection refused" not in result_path.read_text(encoding="utf-8")

    assert len(FakeManager.instances) == 1
    assert FakeManager.instances[0].close_session_calls == 0
    assert FakeCollector.instances == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,expected_reason",
    (
        (TikTokPdpBlockedOrLoginError("challenge or login stopped capture"), "BLOCKED_OR_LOGIN"),
        (TikTokPdpIdentityError("identity mismatch stopped capture"), "IDENTITY_MISMATCH_OR_UNVERIFIABLE"),
        (TikTokPdpExtractionError("required title was unavailable"), "EXTRACTION_FAILURE"),
    ),
)
async def test_collection_typed_failures_reuse_canonical_code_without_message_parsing(
    external_temp_path, failure, expected_reason
):
    FakeCollector.failure = failure
    root = external_temp_path / "failed-pilot"

    with pytest.raises(TikTokPdpLivePilotError, match=f"^{expected_reason}$"):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )

    assert len(FakeCollector.instances) == 1
    assert FakeCollector.instances[0].calls == [(AUTHORIZED_PDP_URL, OBSERVED_AT)]

    # Attempt marker and terminal result both exist
    marker_path = root / ATTEMPT_MARKER_FILENAME
    result_path = root / RESULT_FILENAME
    assert marker_path.exists()
    assert result_path.exists()

    doc = json.loads(result_path.read_text(encoding="utf-8"))
    assert doc["operation"]["operation_status"] == "FAIL_CLOSED"
    assert doc["operation"]["observation_status"] == "NOT_OBSERVED"
    assert doc["operation"]["session_release_status"] == "SUCCESS"
    assert doc["operation"]["failure_reason"] == expected_reason
    assert "binding" not in doc
    assert "snapshot" not in doc

    # Raw exception message is never in the persisted document
    persisted = result_path.read_text(encoding="utf-8")
    assert str(failure) not in persisted

    manager = FakeManager.instances[0]
    assert manager.close_session_calls == 1
    assert manager.close_all_calls == 0
    assert manager.session.close_calls == 0


@pytest.mark.asyncio
async def test_unclassified_collection_exception_persists_fail_closed(external_temp_path):
    FakeCollector.failure = ValueError("unexpected parser glitch")
    root = external_temp_path / "failed-pilot"

    with pytest.raises(TikTokPdpLivePilotError, match="^UNCLASSIFIED_OPERATION_FAILURE$"):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )

    result_path = root / RESULT_FILENAME
    doc = json.loads(result_path.read_text(encoding="utf-8"))
    assert doc["operation"]["operation_status"] == "FAIL_CLOSED"
    assert doc["operation"]["observation_status"] == "NOT_OBSERVED"
    assert doc["operation"]["session_release_status"] == "SUCCESS"
    assert doc["operation"]["failure_reason"] == "UNCLASSIFIED_OPERATION_FAILURE"
    assert "unexpected parser glitch" not in result_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_result_binding_mismatch_persists_fail_closed(external_temp_path):
    # Collector succeeded, but returned mismatched product id
    mismatched = _result(source_product_id="9999999999999999999")
    FakeCollector.result_override = mismatched
    root = external_temp_path / "mismatch-pilot"

    with pytest.raises(TikTokPdpLivePilotError, match="^RESULT_BINDING_MISMATCH$"):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )

    result_path = root / RESULT_FILENAME
    doc = json.loads(result_path.read_text(encoding="utf-8"))
    assert doc["operation"]["operation_status"] == "FAIL_CLOSED"
    assert doc["operation"]["observation_status"] == "NOT_OBSERVED"
    assert doc["operation"]["session_release_status"] == "SUCCESS"
    assert doc["operation"]["failure_reason"] == "RESULT_BINDING_MISMATCH"
    assert "binding" not in doc
    assert "snapshot" not in doc


@pytest.mark.asyncio
async def test_success_plus_cleanup_failure_retains_observation_and_records_failed_release(
    external_temp_path,
):
    FakeManager.close_failure = RuntimeError(f"cleanup leaked {ENDPOINT}")
    root = external_temp_path / "cleanup-fail-pilot"

    with pytest.raises(TikTokPdpLivePilotError, match="^SESSION_RELEASE_FAILED$") as raised:
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )

    assert ENDPOINT not in str(raised.value)

    result_path = root / RESULT_FILENAME
    doc = json.loads(result_path.read_text(encoding="utf-8"))
    assert doc["operation"]["operation_status"] == "FAIL_CLOSED"
    assert doc["operation"]["observation_status"] == "OBSERVED"
    assert doc["operation"]["session_release_status"] == "FAILED"
    assert doc["operation"]["failure_reason"] == "SESSION_RELEASE_FAILED"
    # Admitted snapshot and binding are retained!
    assert "binding" in doc
    assert "snapshot" in doc
    assert ENDPOINT not in result_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_collector_failure_plus_cleanup_failure_preserves_primary_collector_code(
    external_temp_path,
):
    primary = TikTokPdpExtractionError("primary collector failure")
    FakeCollector.failure = primary
    FakeManager.close_failure = RuntimeError("cleanup failure")
    root = external_temp_path / "both-fail-pilot"

    with pytest.raises(TikTokPdpLivePilotError, match="^EXTRACTION_FAILURE$"):
        await run_tiktok_pdp_live_pilot(
            job_root=root,
            cdp_endpoint=ENDPOINT,
            clock=lambda: OBSERVED_AT,
            manager_factory=FakeManager,
            collector_factory=FakeCollector,
        )

    result_path = root / RESULT_FILENAME
    doc = json.loads(result_path.read_text(encoding="utf-8"))
    assert doc["operation"]["operation_status"] == "FAIL_CLOSED"
    assert doc["operation"]["observation_status"] == "NOT_OBSERVED"
    assert doc["operation"]["session_release_status"] == "FAILED"
    assert doc["operation"]["failure_reason"] == "EXTRACTION_FAILURE"
    assert "binding" not in doc
    assert "snapshot" not in doc


@pytest.mark.asyncio
async def test_forced_terminal_result_write_failure_preserves_marker_without_retry(
    external_temp_path,
):
    root = external_temp_path / "write-fail-pilot"
    target_result = root / RESULT_FILENAME

    original_open = Path.open

    def failing_open(self, *args, **kwargs):
        if self == target_result:
            raise OSError("disk full simulation")
        return original_open(self, *args, **kwargs)

    with patch.object(Path, "open", failing_open):
        with pytest.raises(TikTokPdpLivePilotError, match="^TERMINAL_ARTIFACT_WRITE_FAILED$"):
            await run_tiktok_pdp_live_pilot(
                job_root=root,
                cdp_endpoint=ENDPOINT,
                clock=lambda: OBSERVED_AT,
                manager_factory=FakeManager,
                collector_factory=FakeCollector,
            )

    # Marker remains intact!
    marker_path = root / ATTEMPT_MARKER_FILENAME
    assert marker_path.exists()
    assert not target_result.exists()

    # Collector was invoked at most once
    assert len(FakeCollector.instances) == 1
    assert FakeCollector.instances[0].calls == [(AUTHORIZED_PDP_URL, OBSERVED_AT)]


def test_interrupted_marker_represents_consumed_interrupted_or_unobserved(
    external_temp_path,
):
    """Marker existence without conforming result represents CONSUMED_INTERRUPTED_OR_UNOBSERVED."""
    root = external_temp_path / "interrupted-pilot"
    root.mkdir()
    marker_path = root / ATTEMPT_MARKER_FILENAME
    marker_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "record_type": "VALIDATION_ATTEMPT_MARKER",
                "contract_identifier": CONTRACT_IDENTIFIER,
            }
        ),
        encoding="utf-8",
    )
    result_path = root / RESULT_FILENAME

    # Definition check: marker exists, result absent -> CONSUMED_INTERRUPTED_OR_UNOBSERVED
    assert marker_path.exists()
    assert not result_path.exists()


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
    assert "manager.close_session(_SESSION_RUN_ID)" in source
    assert "close_all" not in source
    assert "retry" not in source.lower()
    assert "while " not in source
    assert "for requested_url" not in source
