"""TASK-163 live Shopee evidence-to-grounded-QA certification.

This module is a certification fixture only.  It composes existing production
authorities without defining a reusable application surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import logging
import os
from pathlib import Path

import pytest

from src.browser.errors import BrowserError
from src.core.types import ToolCall, ToolResult, ToolStatus
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.canonical_catalog import CatalogRegistrationStatus
from src.product_intelligence.canonical_catalog_sqlite import (
    create_sqlite_canonical_catalog,
)
from src.product_intelligence.discovery import (
    DiscoveryBlockedError,
    DiscoveryNavigationError,
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
    plan_family_knowledge_review,
)
from src.product_intelligence.grounded_answer import GroundedAnswerStatus
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
    intake_product_source_evidence,
)
from src.product_source.models import ProductSourcePack
from src.providers.base import LLMProvider, LLMResponse
from src.tools.shopee_scrape_tool import ShopeeScrapeTool


_DEFAULT_PLATFORM = "shopee"
_DEFAULT_QUERY = "bình giữ nhiệt inox"
_DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:9222"
_CERTIFICATION_RUN_ID = "task-163-p6-certification"
_CERTIFICATION_ACTOR = "p6-certification"
_CERTIFICATION_TIMESTAMP = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
_QUESTION = "Which persisted evidence comes from shopee?"


class _FailureCategory(str, Enum):
    CONFIGURATION = "LIVE_P6B_CONFIGURATION"
    CDP_BROWSER = "LIVE_P6B_CDP_BROWSER"
    DISCOVERY_BLOCKED = "LIVE_P6B_DISCOVERY_BLOCKED"
    DISCOVERY_NAVIGATION = "LIVE_P6B_DISCOVERY_NAVIGATION"
    DISCOVERY_ORCHESTRATION = "LIVE_P6B_DISCOVERY_ORCHESTRATION"
    DISCOVERY_EMPTY = "LIVE_P6B_DISCOVERY_EMPTY"
    ACQUISITION_BLOCKED = "LIVE_P6B_ACQUISITION_BLOCKED"
    ACQUISITION_EXTRACTION = "LIVE_P6B_ACQUISITION_EXTRACTION"
    ACQUISITION_DOWNLOAD = "LIVE_P6B_ACQUISITION_DOWNLOAD"
    ACQUISITION_UPLOAD = "LIVE_P6B_ACQUISITION_UPLOAD"
    ACQUISITION_PARTIAL = "LIVE_P6B_ACQUISITION_PARTIAL"
    ACQUISITION_UNAVAILABLE = "LIVE_P6B_ACQUISITION_UNAVAILABLE"
    INTAKE = "LIVE_P6B_INTAKE"
    DUPLICATE_OBSERVATION = "LIVE_P6B_DUPLICATE_OBSERVATION"
    FAMILY_PLANNING = "LIVE_P6B_FAMILY_PLANNING"
    FAMILY_ADMISSION = "LIVE_P6B_FAMILY_ADMISSION"
    VARIANT_ADMISSION = "LIVE_P6B_VARIANT_ADMISSION"
    GROUNDED_QA = "LIVE_P6B_GROUNDED_QA"
    CLEANUP = "LIVE_P6B_CLEANUP"


class _CertificationFailure(Exception):
    def __init__(self, category: _FailureCategory) -> None:
        super().__init__(category.value)
        self.category = category


@dataclass(frozen=True)
class _LiveConfiguration:
    platform: str
    query: str
    cdp_endpoint: str


def _validate_configuration(
    platform: str,
    query: str,
    cdp_endpoint: str,
) -> _LiveConfiguration:
    if platform != _DEFAULT_PLATFORM:
        raise _CertificationFailure(_FailureCategory.CONFIGURATION)
    if not query.strip() or "\n" in query or "\r" in query:
        raise _CertificationFailure(_FailureCategory.CONFIGURATION)
    if not cdp_endpoint.strip() or "\n" in cdp_endpoint or "\r" in cdp_endpoint:
        raise _CertificationFailure(_FailureCategory.CONFIGURATION)
    return _LiveConfiguration(platform, query, cdp_endpoint)


def _load_configuration() -> _LiveConfiguration:
    return _validate_configuration(
        os.environ.get("PI_LIVE_CERT_PLATFORM", _DEFAULT_PLATFORM),
        os.environ.get("PI_LIVE_CERT_QUERY", _DEFAULT_QUERY),
        os.environ.get("PI_LIVE_CERT_CDP_ENDPOINT", _DEFAULT_CDP_ENDPOINT),
    )


class _InMemoryDriveSink:
    def __init__(self) -> None:
        self.folder_calls = 0
        self.upload_calls = 0

    def get_or_create_folder(self, name: str, parent_id: str | None = None) -> str:
        self.folder_calls += 1
        return f"task-163-folder-{self.folder_calls:02d}"

    def upload_file(self, file_path: str, folder_id: str | None = None) -> str:
        self.upload_calls += 1
        return f"task-163-upload-{self.upload_calls:02d}"


class _DeterministicProvider(LLMProvider):
    def __init__(self) -> None:
        self.generate_calls = 0

    async def generate(self, messages, tools) -> LLMResponse:
        self.generate_calls += 1
        content = json.dumps(
            {
                "status": "ANSWERED",
                "answer_text": "The persisted context contains Shopee evidence.",
                "citation_ids": ["H001-W001"],
                "limitations": [],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return LLMResponse(
            provider="task-163-zero-network",
            provider_response_id="task-163-response-001",
            content=content,
        )


def _classify_acquisition(result: ToolResult) -> _FailureCategory | None:
    if result.status is ToolStatus.SUCCESS and result.error is None:
        return None
    if result.status is ToolStatus.PARTIAL_SUCCESS:
        return _FailureCategory.ACQUISITION_PARTIAL
    code = result.error.code if result.error is not None else None
    return {
        "EXTRACTION_BLOCKED": _FailureCategory.ACQUISITION_BLOCKED,
        "EXTRACTION_EMPTY": _FailureCategory.ACQUISITION_EXTRACTION,
        "DOWNLOAD_FAILED": _FailureCategory.ACQUISITION_DOWNLOAD,
        "UPLOAD_FAILED": _FailureCategory.ACQUISITION_UPLOAD,
    }.get(code, _FailureCategory.ACQUISITION_UNAVAILABLE)


def _require_confined_manifest(result: ToolResult, output_root: Path) -> None:
    category = _classify_acquisition(result)
    if category is not None:
        raise _CertificationFailure(category)
    if type(result.data) is not dict:
        raise _CertificationFailure(_FailureCategory.ACQUISITION_UNAVAILABLE)
    manifest_value = result.data.get("manifest_path")
    if type(manifest_value) is not str:
        raise _CertificationFailure(_FailureCategory.ACQUISITION_UNAVAILABLE)
    root = output_root.resolve()
    manifest = Path(manifest_value).resolve()
    manifests = tuple(output_root.rglob("source_pack.json"))
    if (
        manifest.name != "source_pack.json"
        or not manifest.is_relative_to(root)
        or len(manifests) != 1
        or manifests[0].resolve() != manifest
    ):
        raise _CertificationFailure(_FailureCategory.ACQUISITION_UNAVAILABLE)


async def _certify_with_manager(
    manager: PlaywrightBrowserManager,
    configuration: _LiveConfiguration,
    tmp_path: Path,
) -> None:
    adapter = ShopeeDiscoveryAdapter(browser=manager)
    request = DiscoveryRequest(
        query=configuration.query,
        max_candidates=20,
        max_pages=1,
    )
    plan = PlatformDiscoveryPlan(
        platform=configuration.platform,
        adapter=adapter,
        request=request,
    )
    evaluated_at = datetime.now(timezone.utc)
    try:
        discovery = await orchestrate_discovery(
            (plan,),
            observed_at=evaluated_at,
            evaluated_at=evaluated_at,
            shortlist_size=1,
        )
    except DiscoveryBlockedError:
        raise _CertificationFailure(_FailureCategory.DISCOVERY_BLOCKED) from None
    except DiscoveryNavigationError:
        raise _CertificationFailure(_FailureCategory.DISCOVERY_NAVIGATION) from None
    except BrowserError:
        raise _CertificationFailure(_FailureCategory.CDP_BROWSER) from None
    except OrchestrationError:
        raise _CertificationFailure(_FailureCategory.DISCOVERY_ORCHESTRATION) from None
    except Exception:
        raise _CertificationFailure(_FailureCategory.DISCOVERY_ORCHESTRATION) from None

    if not discovery.shortlist:
        raise _CertificationFailure(_FailureCategory.DISCOVERY_EMPTY)
    candidate = discovery.shortlist[0].candidate

    drive = _InMemoryDriveSink()
    scrape_tool = ShopeeScrapeTool()
    output_roots = (
        tmp_path / "observation-001",
        tmp_path / "observation-002",
    )
    context_base = {
        "browser_manager": manager,
        "gdrive": drive,
        "gdrive_folder_id": "task-163-dummy-drive-folder",
    }
    # These are two planned observations. Any first failure raises before the
    # loop can begin the second acquisition.
    for ordinal, output_root in enumerate(output_roots, start=1):
        call = ToolCall(
            name=scrape_tool.name,
            arguments={"url": candidate.url},
            call_id=f"task-163-acquisition-{ordinal:03d}",
            run_id=_CERTIFICATION_RUN_ID,
        )
        try:
            acquisition = await scrape_tool.execute(
                call,
                {**context_base, "output_dir": str(output_root)},
            )
        except Exception:
            raise _CertificationFailure(
                _FailureCategory.ACQUISITION_UNAVAILABLE
            ) from None
        _require_confined_manifest(acquisition, output_root)

    if drive.folder_calls != 6 or drive.upload_calls < 2:
        raise _CertificationFailure(_FailureCategory.ACQUISITION_UNAVAILABLE)

    try:
        inventory = intake_product_source_evidence(
            tuple(str(root) for root in output_roots)
        )
    except Exception:
        raise _CertificationFailure(_FailureCategory.INTAKE) from None
    if (
        len(inventory.manifest_paths) != 2
        or len(inventory.source_packs) != 2
        or any(type(pack) is not ProductSourcePack for pack in inventory.source_packs)
    ):
        raise _CertificationFailure(_FailureCategory.INTAKE)

    identities = tuple(
        SourceObservationIdentity.from_pack(pack) for pack in inventory.source_packs
    )
    if len(set(identities)) != 2:
        raise _CertificationFailure(_FailureCategory.DUPLICATE_OBSERVATION)

    try:
        review_plan = plan_family_knowledge_review(inventory)
    except Exception:
        raise _CertificationFailure(_FailureCategory.FAMILY_PLANNING) from None
    if (
        len(review_plan.proposals) != 1
        or type(review_plan.proposals[0]) is not FamilyMergeProposal
    ):
        raise _CertificationFailure(_FailureCategory.FAMILY_PLANNING)
    proposal = review_plan.proposals[0]

    database_path = tmp_path / "task-163-canonical-catalog.sqlite"
    try:
        empty_catalog = create_sqlite_canonical_catalog(database_path)
        if empty_catalog.families or empty_catalog.variants:
            raise _CertificationFailure(_FailureCategory.FAMILY_ADMISSION)
        family_decision = record_planned_family_decision(
            review_plan,
            proposal,
            decision=FamilyMergeDecision.APPROVE,
            actor=_CERTIFICATION_ACTOR,
            decided_at=_CERTIFICATION_TIMESTAMP,
        )
        family_admission = durably_admit_planned_family(
            review_plan,
            family_decision,
            family_id="p6-cert-family-001",
            database_path=database_path,
        )
    except _CertificationFailure:
        raise
    except Exception:
        raise _CertificationFailure(_FailureCategory.FAMILY_ADMISSION) from None
    if (
        family_admission.registration.status is not CatalogRegistrationStatus.INSERTED
        or len(family_admission.family.members) != 2
        or set(family_admission.family.members) != set(identities)
    ):
        raise _CertificationFailure(_FailureCategory.FAMILY_ADMISSION)

    for ordinal, member in enumerate(family_admission.family.members, start=1):
        try:
            variant_review = prepare_sellable_variant_review(
                family_admission.family,
                (member,),
            )
            variant_decision = record_reviewed_sellable_variant_decision(
                variant_review,
                decision=SellableVariantDecision.APPROVE,
                actor=_CERTIFICATION_ACTOR,
                decided_at=_CERTIFICATION_TIMESTAMP,
            )
            variant_admission = durably_admit_reviewed_sellable_variant(
                variant_review,
                variant_decision,
                variant_id=f"p6-cert-variant-{ordinal:03d}",
                database_path=database_path,
            )
        except Exception:
            raise _CertificationFailure(_FailureCategory.VARIANT_ADMISSION) from None
        if (
            variant_admission.registration.status
            is not CatalogRegistrationStatus.INSERTED
            or variant_admission.variant.members != (member,)
        ):
            raise _CertificationFailure(_FailureCategory.VARIANT_ADMISSION)

    provider = _DeterministicProvider()
    try:
        answer = await answer_persisted_grounded_question(
            database_path,
            inventory.manifest_paths,
            question=_QUESTION,
            provider=provider,
            max_hits=2,
        )
    except Exception:
        raise _CertificationFailure(_FailureCategory.GROUNDED_QA) from None
    variant_ids = {hit.hit.profile.variant_id for hit in answer.context.hits}
    if (
        answer.status is not GroundedAnswerStatus.ANSWERED
        or not answer.citation_ids
        or provider.generate_calls != 1
        or len(answer.context.hits) != 2
        or variant_ids
        != {"p6-cert-variant-001", "p6-cert-variant-002"}
    ):
        raise _CertificationFailure(_FailureCategory.GROUNDED_QA)


async def _execute_live_certification(tmp_path: Path) -> None:
    configuration = _load_configuration()
    manager = PlaywrightBrowserManager(cdp_endpoint=configuration.cdp_endpoint)
    primary_failure: _CertificationFailure | None = None
    try:
        await _certify_with_manager(manager, configuration, tmp_path)
    except _CertificationFailure as exc:
        primary_failure = exc
    except Exception:
        primary_failure = _CertificationFailure(_FailureCategory.CDP_BROWSER)
    finally:
        try:
            await manager.close_all()
        except Exception:
            if primary_failure is None:
                primary_failure = _CertificationFailure(_FailureCategory.CLEANUP)
    if primary_failure is not None:
        raise primary_failure


@pytest.mark.asyncio
async def test_live_real_evidence_canonical_qa(tmp_path: Path) -> None:
    previous_logging_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        await _execute_live_certification(tmp_path)
    except _CertificationFailure as exc:
        pytest.fail(exc.category.value, pytrace=False)
    finally:
        logging.disable(previous_logging_disable)


@pytest.mark.parametrize(
    ("platform", "query", "endpoint"),
    [
        ("tiktok", _DEFAULT_QUERY, _DEFAULT_CDP_ENDPOINT),
        (_DEFAULT_PLATFORM, "", _DEFAULT_CDP_ENDPOINT),
        (_DEFAULT_PLATFORM, "line one\nline two", _DEFAULT_CDP_ENDPOINT),
        (_DEFAULT_PLATFORM, _DEFAULT_QUERY, ""),
        (_DEFAULT_PLATFORM, _DEFAULT_QUERY, "endpoint\rvalue"),
    ],
)
def test_configuration_validation_is_bounded(
    platform: str,
    query: str,
    endpoint: str,
) -> None:
    with pytest.raises(_CertificationFailure) as failure:
        _validate_configuration(platform, query, endpoint)
    assert failure.value.category is _FailureCategory.CONFIGURATION


def test_configuration_defaults_and_values_are_preserved() -> None:
    configured = _validate_configuration(
        _DEFAULT_PLATFORM,
        "  exact query  ",
        "http://127.0.0.1:9333/custom",
    )
    assert configured == _LiveConfiguration(
        _DEFAULT_PLATFORM,
        "  exact query  ",
        "http://127.0.0.1:9333/custom",
    )


def test_in_memory_drive_and_acquisition_classifier_are_bounded() -> None:
    sink = _InMemoryDriveSink()
    assert sink.get_or_create_folder("ignored") == "task-163-folder-01"
    assert sink.upload_file("ignored") == "task-163-upload-01"
    assert (sink.folder_calls, sink.upload_calls) == (1, 1)
    assert {
        _classify_acquisition(
            ToolResult(
                call_id="bounded",
                run_id="bounded",
                tool_name="bounded",
                status=status,
            )
        )
        for status in (ToolStatus.PARTIAL_SUCCESS, ToolStatus.FAILURE)
    } == {
        _FailureCategory.ACQUISITION_PARTIAL,
        _FailureCategory.ACQUISITION_UNAVAILABLE,
    }
