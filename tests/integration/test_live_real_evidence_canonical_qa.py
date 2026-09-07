"""Certification-only live proof of real evidence through persistent grounded QA.

TASK-156 composes only already-published Product Intelligence authorities.  Its
APPROVE decisions and opaque IDs exist solely in disposable pytest state; they
are not production Human decisions, identity allocation, or semantic policy.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
import inspect
import json
import logging
import os
from pathlib import Path
import textwrap
from typing import Any, Optional

import pytest

from src.browser.errors import BrowserError
from src.core.errors import AgentException
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.adapters.tiktok import TikTokDiscoveryAdapter
from src.product_intelligence.canonical_catalog import CatalogRegistrationStatus
from src.product_intelligence.canonical_catalog_sqlite import (
    create_sqlite_canonical_catalog,
)
from src.product_intelligence.discovery import (
    DiscoveryBlockedError,
    DiscoveryError,
    DiscoveryRequest,
)
from src.product_intelligence.entity_resolution import SourceObservationIdentity
from src.product_intelligence.family_decision_admission import (
    durably_admit_planned_family,
    record_planned_family_decision,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision,
    FamilyMergeProposal,
)
from src.product_intelligence.family_review_planning import (
    FamilyKnowledgeReviewPlan,
    plan_family_knowledge_review,
)
from src.product_intelligence.grounded_answer import (
    GroundedAnswer,
    GroundedAnswerStatus,
)
from src.product_intelligence.orchestration import (
    OrchestrationError,
    PlatformDiscoveryPlan,
    orchestrate_discovery,
)
from src.product_intelligence.persistent_grounded_qa import (
    answer_persisted_grounded_question,
)
from src.product_intelligence.sellable_variant_approval import (
    SellableVariantDecision,
)
from src.product_intelligence.sellable_variant_review_admission import (
    durably_admit_reviewed_sellable_variant,
    prepare_sellable_variant_review,
    record_reviewed_sellable_variant_decision,
)
from src.product_intelligence.source_evidence_intake import (
    SourceEvidenceInventory,
    intake_product_source_evidence,
)
from src.product_source.models import ProductSourcePack
from src.providers.base import LLMProvider, LLMResponse
from src.tools.shopee_scrape_tool import ShopeeScrapeTool
from src.tools.tiktok_scrape_tool import TikTokScrapeTool


DEFAULT_LIVE_CERT_PLATFORM = "shopee"
DEFAULT_LIVE_CERT_QUERY = "bình giữ nhiệt inox"
DEFAULT_LIVE_CERT_CDP_ENDPOINT = "http://127.0.0.1:9222"
CERTIFICATION_RUN_ID = "p6-cert-run-001"
CERTIFICATION_ACTOR = "p6-certification"
CERTIFICATION_DRIVE_ROOT = "p6-cert-drive-root"
CERTIFICATION_FAMILY_ID = "p6-cert-family-001"
CERTIFICATION_VARIANT_IDS = (
    "p6-cert-variant-001",
    "p6-cert-variant-002",
)
CERTIFICATION_DECIDED_AT = datetime(2026, 9, 7, 0, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class LiveP6bConfig:
    platform: str
    query: str
    cdp_endpoint: str


def resolve_live_p6b_config() -> LiveP6bConfig:
    """Read and validate only the three TASK-154-compatible settings."""

    platform = os.environ.get(
        "PI_LIVE_CERT_PLATFORM", DEFAULT_LIVE_CERT_PLATFORM
    )
    if platform not in ("shopee", "tiktok"):
        raise ValueError("PI_LIVE_CERT_PLATFORM must name an allowed platform")

    query = os.environ.get("PI_LIVE_CERT_QUERY", DEFAULT_LIVE_CERT_QUERY)
    if not query.strip() or "\n" in query or "\r" in query:
        raise ValueError("PI_LIVE_CERT_QUERY must be non-empty and single-line")

    cdp_endpoint = os.environ.get(
        "PI_LIVE_CERT_CDP_ENDPOINT", DEFAULT_LIVE_CERT_CDP_ENDPOINT
    )
    if not cdp_endpoint.strip() or "\n" in cdp_endpoint or "\r" in cdp_endpoint:
        raise ValueError(
            "PI_LIVE_CERT_CDP_ENDPOINT must be non-empty and single-line"
        )

    return LiveP6bConfig(
        platform=platform,
        query=query,
        cdp_endpoint=cdp_endpoint,
    )


class InMemoryCertificationDriveSink:
    """Minimal synchronous, zero-network sink required by the scrape tools."""

    def __init__(self) -> None:
        self.folder_call_count = 0
        self.upload_call_count = 0

    def get_or_create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> str:
        del name, parent_id
        self.folder_call_count += 1
        return f"p6-cert-folder-{self.folder_call_count:03d}"

    def upload_file(
        self,
        file_path: str,
        folder_id: Optional[str] = None,
    ) -> str:
        del file_path, folder_id
        self.upload_call_count += 1
        return f"p6-cert-file-{self.upload_call_count:03d}"


class DeterministicCertificationProvider(LLMProvider):
    """Certification-only provider with one fixed, zero-network response."""

    _RESPONSE = json.dumps(
        {
            "status": "ANSWERED",
            "answer_text": "Persisted marketplace evidence is available.",
            "citation_ids": ["H001-E001"],
            "limitations": [],
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )

    def __init__(self) -> None:
        self.generate_call_count = 0

    async def generate(self, messages: list[Any], tools: list[dict]) -> LLMResponse:
        del messages, tools
        self.generate_call_count += 1
        if self.generate_call_count != 1:
            raise RuntimeError("certification provider called more than once")
        return LLMResponse(
            provider="p6-certification-fake",
            provider_response_id="p6-cert-response-001",
            content=self._RESPONSE,
        )


def classify_discovery_failure(exc: BaseException) -> str:
    """Map discovery failures by existing safe exception class only."""

    if isinstance(exc, BrowserError):
        return "LIVE_CDP_UNAVAILABLE"
    if isinstance(exc, DiscoveryBlockedError):
        return "LIVE_P6B_DISCOVERY_BLOCKED"
    if isinstance(exc, (DiscoveryError, OrchestrationError)):
        return "LIVE_P6B_DISCOVERY_UNAVAILABLE"
    return "LIVE_P6B_DISCOVERY_UNAVAILABLE"


def classify_acquisition_result(result: ToolResult) -> str:
    """Map a non-success result using only bounded status and error code."""

    code = getattr(result.error, "code", None) if result.error is not None else None
    if code == "EXTRACTION_BLOCKED":
        return "LIVE_P6B_ACQUISITION_EXTRACTION_BLOCKED"
    if code == "EXTRACTION_EMPTY":
        return "LIVE_P6B_ACQUISITION_EXTRACTION"
    if code == "DOWNLOAD_FAILED":
        return "LIVE_P6B_ACQUISITION_DOWNLOAD"
    if code == "UPLOAD_FAILED":
        return "LIVE_P6B_ACQUISITION_UPLOAD"
    if result.status is ToolStatus.PARTIAL_SUCCESS:
        return "LIVE_P6B_ACQUISITION_PARTIAL"
    return "LIVE_P6B_ACQUISITION_UNAVAILABLE"


def classify_acquisition_exception(exc: BaseException) -> str:
    """Map acquisition exceptions by existing safe exception class only."""

    if isinstance(exc, BrowserError):
        return "LIVE_CDP_UNAVAILABLE"
    return "LIVE_P6B_ACQUISITION_UNAVAILABLE"


def _fail_sanitized(category: str) -> None:
    raise pytest.fail.Exception(category, pytrace=False) from None


def _confined_manifest_path(result: ToolResult, output_root: str) -> Path:
    """Validate one successful tool result without rehydrating its evidence."""

    if type(result) is not ToolResult:
        _fail_sanitized("LIVE_P6B_ACQUISITION_UNAVAILABLE")
    if result.status is not ToolStatus.SUCCESS or result.error is not None:
        _fail_sanitized(classify_acquisition_result(result))
    if type(result.data) is not dict:
        _fail_sanitized("LIVE_P6B_ACQUISITION_UNAVAILABLE")
    raw_manifest_path = result.data.get("manifest_path")
    if type(raw_manifest_path) is not str or not raw_manifest_path:
        _fail_sanitized("LIVE_P6B_ACQUISITION_UNAVAILABLE")
    try:
        manifest_path = Path(raw_manifest_path).resolve(strict=True)
        root_path = Path(output_root).resolve(strict=True)
        manifest_path.relative_to(root_path)
    except (OSError, RuntimeError, ValueError):
        _fail_sanitized("LIVE_P6B_ACQUISITION_UNAVAILABLE")
    if (
        manifest_path.name != "source_pack.json"
        or not manifest_path.is_file()
        or manifest_path.is_symlink()
    ):
        _fail_sanitized("LIVE_P6B_ACQUISITION_UNAVAILABLE")
    return manifest_path


@pytest.mark.asyncio
async def test_live_real_evidence_canonical_qa(tmp_path: Path) -> None:
    """Certify the published real-evidence to persistent grounded-QA chain."""

    try:
        config = resolve_live_p6b_config()
    except BaseException:
        _fail_sanitized("LIVE_P6B_CONFIG_INVALID")

    manager = PlaywrightBrowserManager(cdp_endpoint=config.cdp_endpoint)
    previous_logging_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    primary_exc: Optional[BaseException] = None
    try:
        try:
            if config.platform == "shopee":
                adapter = ShopeeDiscoveryAdapter(browser=manager)
            else:
                adapter = TikTokDiscoveryAdapter(browser=manager)
            request = DiscoveryRequest(
                query=config.query,
                max_pages=1,
                max_candidates=20,
            )
            discovery_plan = PlatformDiscoveryPlan(
                platform=config.platform,
                adapter=adapter,
                request=request,
            )
            discovery_timestamp = datetime.now(timezone.utc)
            discovery_result = await orchestrate_discovery(
                (discovery_plan,),
                observed_at=discovery_timestamp,
                evaluated_at=discovery_timestamp,
                shortlist_size=1,
            )
        except pytest.fail.Exception:
            raise
        except BaseException as exc:
            _fail_sanitized(classify_discovery_failure(exc))

        if not discovery_result.shortlist:
            _fail_sanitized("LIVE_P6B_DISCOVERY_EMPTY")
        candidate = discovery_result.shortlist[0].candidate
        candidate_url = candidate.url

        if config.platform == "shopee":
            tool = ShopeeScrapeTool()
        else:
            tool = TikTokScrapeTool()
        drive_sink = InMemoryCertificationDriveSink()
        acquisition_roots = (
            str(tmp_path / "observation-001"),
            str(tmp_path / "observation-002"),
        )
        returned_manifest_paths: list[Path] = []

        for ordinal, output_root in enumerate(acquisition_roots, start=1):
            call = ToolCall(
                name=tool.name,
                arguments={"url": candidate_url},
                call_id=f"p6-cert-call-{ordinal:03d}",
                run_id=CERTIFICATION_RUN_ID,
            )
            context = {
                "browser": manager,
                "browser_manager": manager,
                "gdrive": drive_sink,
                "gdrive_folder_id": CERTIFICATION_DRIVE_ROOT,
                "output_dir": output_root,
            }
            try:
                tool_result = await tool.execute(call, context)
            except pytest.fail.Exception:
                raise
            except BaseException as exc:
                _fail_sanitized(classify_acquisition_exception(exc))
            returned_manifest_paths.append(
                _confined_manifest_path(tool_result, output_root)
            )

        try:
            inventory = intake_product_source_evidence(acquisition_roots)
        except BaseException:
            _fail_sanitized("LIVE_P6B_INTAKE_UNAVAILABLE")
        if (
            type(inventory) is not SourceEvidenceInventory
            or len(inventory.manifest_paths) != 2
            or len(inventory.source_packs) != 2
            or any(type(pack) is not ProductSourcePack for pack in inventory.source_packs)
        ):
            _fail_sanitized("LIVE_P6B_INTAKE_UNAVAILABLE")

        for output_root, returned_manifest_path in zip(
            acquisition_roots,
            returned_manifest_paths,
            strict=True,
        ):
            try:
                matching_inventory_paths = tuple(
                    Path(path).resolve()
                    for path in inventory.manifest_paths
                    if Path(path).resolve().is_relative_to(Path(output_root).resolve())
                )
            except (OSError, RuntimeError, ValueError):
                _fail_sanitized("LIVE_P6B_INTAKE_UNAVAILABLE")
            if matching_inventory_paths != (returned_manifest_path,):
                _fail_sanitized("LIVE_P6B_INTAKE_UNAVAILABLE")

        identities = tuple(
            SourceObservationIdentity.from_pack(pack)
            for pack in inventory.source_packs
        )
        if len(identities) != 2 or identities[0] == identities[1]:
            _fail_sanitized("LIVE_P6B_DUPLICATE_OBSERVATION")

        try:
            review_plan = plan_family_knowledge_review(inventory)
        except BaseException:
            _fail_sanitized("LIVE_P6B_FAMILY_NOT_ACTIONABLE")
        if (
            type(review_plan) is not FamilyKnowledgeReviewPlan
            or len(review_plan.proposals) != 1
            or type(review_plan.proposals[0]) is not FamilyMergeProposal
        ):
            _fail_sanitized("LIVE_P6B_FAMILY_NOT_ACTIONABLE")
        proposal = review_plan.proposals[0]

        database_path = tmp_path / "p6-cert-catalog.sqlite"
        try:
            create_sqlite_canonical_catalog(database_path)
            family_decision = record_planned_family_decision(
                review_plan,
                proposal,
                decision=FamilyMergeDecision.APPROVE,
                actor=CERTIFICATION_ACTOR,
                decided_at=CERTIFICATION_DECIDED_AT,
            )
            family_admission = durably_admit_planned_family(
                review_plan,
                family_decision,
                family_id=CERTIFICATION_FAMILY_ID,
                database_path=database_path,
            )
        except BaseException:
            _fail_sanitized("LIVE_P6B_FAMILY_ADMISSION_UNAVAILABLE")
        family = family_admission.family
        if (
            family_admission.registration.status
            is not CatalogRegistrationStatus.INSERTED
            or len(family.members) != 2
            or set(family.members) != set(identities)
        ):
            _fail_sanitized("LIVE_P6B_FAMILY_ADMISSION_UNAVAILABLE")

        admitted_variants = []
        for member, variant_id in zip(
            family.members,
            CERTIFICATION_VARIANT_IDS,
            strict=True,
        ):
            try:
                variant_review = prepare_sellable_variant_review(
                    family,
                    (member,),
                )
                variant_decision = record_reviewed_sellable_variant_decision(
                    variant_review,
                    decision=SellableVariantDecision.APPROVE,
                    actor=CERTIFICATION_ACTOR,
                    decided_at=CERTIFICATION_DECIDED_AT,
                )
                variant_admission = durably_admit_reviewed_sellable_variant(
                    variant_review,
                    variant_decision,
                    variant_id=variant_id,
                    database_path=database_path,
                )
            except BaseException:
                _fail_sanitized("LIVE_P6B_VARIANT_ADMISSION_UNAVAILABLE")
            if (
                variant_admission.registration.status
                is not CatalogRegistrationStatus.INSERTED
                or variant_admission.variant.members != (member,)
            ):
                _fail_sanitized("LIVE_P6B_VARIANT_ADMISSION_UNAVAILABLE")
            admitted_variants.append(variant_admission.variant)

        if (
            len(admitted_variants) != 2
            or admitted_variants[0].members == admitted_variants[1].members
            or tuple(variant.variant_id for variant in admitted_variants)
            != CERTIFICATION_VARIANT_IDS
        ):
            _fail_sanitized("LIVE_P6B_VARIANT_ADMISSION_UNAVAILABLE")

        provider = DeterministicCertificationProvider()
        question = f"Which persisted evidence comes from {config.platform}?"
        try:
            answer = await answer_persisted_grounded_question(
                database_path,
                inventory.manifest_paths,
                question=question,
                provider=provider,
                max_hits=2,
            )
        except BaseException:
            _fail_sanitized("LIVE_P6B_GROUNDED_QA_UNAVAILABLE")

        if (
            type(answer) is not GroundedAnswer
            or answer.status is not GroundedAnswerStatus.ANSWERED
            or not answer.citation_ids
            or provider.generate_call_count != 1
            or len(answer.context.hits) != 2
            or {
                hit.hit.profile.variant_id for hit in answer.context.hits
            }
            != set(CERTIFICATION_VARIANT_IDS)
        ):
            _fail_sanitized("LIVE_P6B_GROUNDED_QA_UNAVAILABLE")
    except pytest.fail.Exception as exc:
        primary_exc = exc
        raise
    except BaseException:
        primary_exc = pytest.fail.Exception(
            "LIVE_P6B_UNAVAILABLE",
            pytrace=False,
        )
        raise primary_exc from None
    finally:
        try:
            await manager.close_all()
        except BaseException:
            if primary_exc is None:
                _fail_sanitized("LIVE_CDP_UNAVAILABLE")
        finally:
            logging.disable(previous_logging_disable)


def test_resolve_live_p6b_config_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PI_LIVE_CERT_PLATFORM", raising=False)
    monkeypatch.delenv("PI_LIVE_CERT_QUERY", raising=False)
    monkeypatch.delenv("PI_LIVE_CERT_CDP_ENDPOINT", raising=False)

    assert resolve_live_p6b_config() == LiveP6bConfig(
        platform="shopee",
        query="bình giữ nhiệt inox",
        cdp_endpoint="http://127.0.0.1:9222",
    )


def test_resolve_live_p6b_config_forwards_exact_explicit_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PI_LIVE_CERT_PLATFORM", "tiktok")
    monkeypatch.setenv("PI_LIVE_CERT_QUERY", "  exact query  ")
    monkeypatch.setenv(
        "PI_LIVE_CERT_CDP_ENDPOINT",
        "http://127.0.0.1:9333/path?exact=yes",
    )

    config = resolve_live_p6b_config()
    assert config.platform == "tiktok"
    assert config.query == "  exact query  "
    assert config.cdp_endpoint == "http://127.0.0.1:9333/path?exact=yes"


@pytest.mark.parametrize(
    ("environment_name", "value"),
    [
        ("PI_LIVE_CERT_PLATFORM", "Shopee"),
        ("PI_LIVE_CERT_PLATFORM", ""),
        ("PI_LIVE_CERT_QUERY", ""),
        ("PI_LIVE_CERT_QUERY", "   "),
        ("PI_LIVE_CERT_QUERY", "first\nsecond"),
        ("PI_LIVE_CERT_QUERY", "first\rsecond"),
        ("PI_LIVE_CERT_CDP_ENDPOINT", ""),
        ("PI_LIVE_CERT_CDP_ENDPOINT", "   "),
        ("PI_LIVE_CERT_CDP_ENDPOINT", "endpoint\nextra"),
    ],
)
def test_resolve_live_p6b_config_rejects_invalid_explicit_values(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    value: str,
) -> None:
    monkeypatch.delenv("PI_LIVE_CERT_PLATFORM", raising=False)
    monkeypatch.delenv("PI_LIVE_CERT_QUERY", raising=False)
    monkeypatch.delenv("PI_LIVE_CERT_CDP_ENDPOINT", raising=False)
    monkeypatch.setenv(environment_name, value)

    with pytest.raises(ValueError):
        resolve_live_p6b_config()


def test_in_memory_drive_sink_has_only_bounded_protocol_state() -> None:
    sink = InMemoryCertificationDriveSink()

    assert sink.get_or_create_folder("ignored", parent_id="ignored") == (
        "p6-cert-folder-001"
    )
    assert sink.upload_file("ignored", folder_id="ignored") == "p6-cert-file-001"
    assert sink.folder_call_count == 1
    assert sink.upload_call_count == 1
    public_methods = {
        name
        for name in dir(sink)
        if not name.startswith("_") and callable(getattr(sink, name))
    }
    assert public_methods == {"get_or_create_folder", "upload_file"}
    assert set(vars(sink)) == {"folder_call_count", "upload_call_count"}


@pytest.mark.asyncio
async def test_fake_provider_is_deterministic_and_counts_one_call() -> None:
    provider = DeterministicCertificationProvider()

    response = await provider.generate([], [])

    assert provider.generate_call_count == 1
    assert response.provider == "p6-certification-fake"
    assert response.provider_response_id == "p6-cert-response-001"
    assert json.loads(response.content or "") == {
        "status": "ANSWERED",
        "answer_text": "Persisted marketplace evidence is available.",
        "citation_ids": ["H001-E001"],
        "limitations": [],
    }


@pytest.mark.parametrize(
    ("error_code", "status", "expected"),
    [
        (
            "EXTRACTION_BLOCKED",
            ToolStatus.FAILURE,
            "LIVE_P6B_ACQUISITION_EXTRACTION_BLOCKED",
        ),
        (
            "EXTRACTION_EMPTY",
            ToolStatus.FAILURE,
            "LIVE_P6B_ACQUISITION_EXTRACTION",
        ),
        ("DOWNLOAD_FAILED", ToolStatus.FAILURE, "LIVE_P6B_ACQUISITION_DOWNLOAD"),
        ("UPLOAD_FAILED", ToolStatus.FAILURE, "LIVE_P6B_ACQUISITION_UPLOAD"),
        ("UNKNOWN", ToolStatus.PARTIAL_SUCCESS, "LIVE_P6B_ACQUISITION_PARTIAL"),
        ("UNKNOWN", ToolStatus.FAILURE, "LIVE_P6B_ACQUISITION_UNAVAILABLE"),
    ],
)
def test_acquisition_diagnostic_is_bounded_and_sanitized(
    error_code: str,
    status: ToolStatus,
    expected: str,
) -> None:
    sensitive = (
        "https://market.invalid/item cookie=secret html=<private> "
        "C:\\Users\\private\\download.jpg token=private"
    )
    result = ToolResult(
        call_id="offline-call",
        run_id="offline-run",
        tool_name="offline-tool",
        status=status,
        error=AgentException(sensitive, code=error_code),
    )

    category = classify_acquisition_result(result)

    assert category == expected
    assert sensitive not in category
    assert "https://" not in category
    assert "cookie" not in category
    assert "Users" not in category
    with pytest.raises(pytest.fail.Exception) as exc_info:
        _fail_sanitized(category)
    assert exc_info.value.msg == expected
    assert exc_info.value.pytrace is False


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (
            DiscoveryBlockedError("https://private.invalid token=private"),
            "LIVE_P6B_DISCOVERY_BLOCKED",
        ),
        (
            DiscoveryError("https://private.invalid token=private"),
            "LIVE_P6B_DISCOVERY_UNAVAILABLE",
        ),
        (
            BrowserError("https://private.invalid token=private"),
            "LIVE_CDP_UNAVAILABLE",
        ),
        (
            RuntimeError("https://private.invalid token=private"),
            "LIVE_P6B_DISCOVERY_UNAVAILABLE",
        ),
    ],
)
def test_discovery_diagnostic_is_bounded_and_sanitized(
    exc: BaseException,
    expected: str,
) -> None:
    category = classify_discovery_failure(exc)
    assert category == expected
    assert "https://" not in category
    assert "token" not in category


def test_live_route_source_uses_only_published_composition_boundaries() -> None:
    source = textwrap.dedent(
        inspect.getsource(test_live_real_evidence_canonical_qa)
    )
    tree = ast.parse(source)
    called_names = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    called_attributes = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]

    assert called_names.count("PlaywrightBrowserManager") == 1
    assert called_names.count("orchestrate_discovery") == 1
    assert called_names.count("intake_product_source_evidence") == 1
    assert called_names.count("plan_family_knowledge_review") == 1
    assert called_names.count("create_sqlite_canonical_catalog") == 1
    assert called_names.count("record_planned_family_decision") == 1
    assert called_names.count("durably_admit_planned_family") == 1
    assert called_names.count("prepare_sellable_variant_review") == 1
    assert called_names.count("record_reviewed_sellable_variant_decision") == 1
    assert called_names.count("durably_admit_reviewed_sellable_variant") == 1
    assert called_names.count("answer_persisted_grounded_question") == 1
    assert called_attributes.count("execute") == 1
    assert called_attributes.count("close_all") == 1
