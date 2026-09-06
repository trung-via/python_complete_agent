"""TASK-145 regressions for the read-only Product Intelligence CLI."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import importlib
from io import StringIO
import json
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

from dataclasses import replace
from src.core.errors import AgentException
from src.product_intelligence import cli
from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.adapters.tiktok import TikTokDiscoveryAdapter
from src.product_intelligence.approval import (
    ApprovalDecision,
    ApprovalError,
    EnqueueOutcome,
    EnqueueResult,
    create_approval_record,
    enqueue_approval,
)
from src.product_intelligence.discovery import (
    DiscoveryBlockedError,
    DiscoveryError,
    DiscoveryInvalidRequestError,
    DiscoveryNavigationError,
    DiscoveryRequest,
)
from src.product_intelligence.grounded_answer import GroundedAnswerStatus
from src.product_intelligence.models import (
    DecisionBand,
    ProductCandidateSnapshot,
    WinningProductScore,
)
from src.product_intelligence.orchestration import (
    OrchestrationError,
    OrchestrationInvalidRequestError,
    OrchestrationResult,
    PlatformDiscoveryPlan,
)
from src.product_intelligence.ranking import RankedCandidate
from src.product_intelligence.scoring import WinningProductScorer
from src.product_intelligence.source_evidence_intake import (
    SourceEvidenceIntakeError,
    SourceEvidenceInventory,
)
from src.product_intelligence.canonical_catalog import CatalogRegistrationStatus
from src.product_intelligence.canonical_catalog_sqlite import (
    CanonicalCatalogStorageError,
    create_sqlite_canonical_catalog,
    load_sqlite_canonical_catalog,
)
from src.product_intelligence.canonical_family import (
    CanonicalFamilyAdmissionError,
)
from src.product_intelligence.entity_grouping import (
    ProvisionalGroupingResult,
    ProvisionalGroupStatus,
    ProvisionalProductFamilyGroup,
)
from src.product_intelligence.entity_resolution import (
    EntityResolutionResult,
    ProductRelationship,
    ResolutionEvidence,
    SourceObservationIdentity,
)
from src.product_intelligence.entity_resolution_graph import (
    MultiObservationResolutionGraph,
    PairwiseConflictEvidence,
    ProductFamilyConsistencyConflict,
)
from src.product_intelligence.family_decision_admission import (
    DurableFamilyAdmissionResult,
    FamilyDecisionAdmissionError,
    _DURABLE_ADMISSION,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeApprovalError,
    FamilyMergeDecision,
    FamilyMergeDecisionRecord,
    FamilyMergePairEvidence,
    FamilyMergeProposal,
    create_family_merge_proposal,
)
from src.product_intelligence.family_review_planning import (
    FamilyKnowledgeReviewPlan,
    FamilyKnowledgeReviewPlanningError,
    plan_family_knowledge_review,
)
from src.product_source.models import ProductFact, ProductSourcePack
from src.product_source.serialization import serialize_source_pack


def _pack(name: str, observed_hour: int) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=f"pack-{name}",
        platform=f"market-{name}",
        source_product_id=f"listing-{name}",
        product_url=f"https://market.example/{name}",
        observed_at=datetime(2026, 9, 6, observed_hour, tzinfo=timezone.utc),
        collector="task-145-test",
        title=f"Title {name}",
    )


def _read_output(capsys: pytest.CaptureFixture[str]) -> tuple[object, str]:
    captured = capsys.readouterr()
    return json.loads(captured.out), captured.err


def test_success_renderer_is_deterministic_human_readable_json():
    document = {"z": ["Tiếng Việt", "second"], "a": 1}
    first = StringIO()
    second = StringIO()
    cli._write_json(document, first)
    cli._write_json(document, second)
    assert first.getvalue() == second.getvalue()
    assert first.getvalue().endswith("\n")
    assert "\n  " in first.getvalue()
    assert "Tiếng Việt" in first.getvalue()
    assert json.loads(first.getvalue()) == document


def test_import_is_side_effect_free(monkeypatch, capsys):
    import src.integrations.playwright.manager as playwright_manager
    import src.product_intelligence.adapters.shopee as shopee_adapter
    import src.product_intelligence.adapters.tiktok as tiktok_adapter
    import src.product_intelligence.approval as approval
    import src.product_intelligence.canonical_catalog_sqlite as catalog_sqlite
    import src.product_intelligence.family_decision_admission as decision_admission
    import src.product_intelligence.family_review_planning as review_planning
    import src.product_intelligence.orchestration as orchestration
    import src.product_intelligence.persistent_grounded_qa as persistent_qa
    import src.product_intelligence.source_evidence_intake as evidence_intake
    import src.providers.gemini as gemini

    forbidden = lambda *args, **kwargs: pytest.fail("import performed application work")
    with monkeypatch.context() as scoped:
        scoped.setattr(evidence_intake, "intake_product_source_evidence", forbidden)
        scoped.setattr(catalog_sqlite, "load_sqlite_canonical_catalog", forbidden)
        scoped.setattr(persistent_qa, "answer_persisted_grounded_question", forbidden)
        scoped.setattr(gemini, "GeminiProvider", forbidden)
        scoped.setattr(playwright_manager, "PlaywrightBrowserManager", forbidden)
        scoped.setattr(shopee_adapter, "ShopeeDiscoveryAdapter", forbidden)
        scoped.setattr(tiktok_adapter, "TikTokDiscoveryAdapter", forbidden)
        scoped.setattr(orchestration, "orchestrate_discovery", forbidden)
        scoped.setattr(approval, "create_approval_record", forbidden)
        scoped.setattr(approval, "enqueue_approval", forbidden)
        scoped.setattr(review_planning, "plan_family_knowledge_review", forbidden)
        scoped.setattr(decision_admission, "record_planned_family_decision", forbidden)
        scoped.setattr(decision_admission, "durably_admit_planned_family", forbidden)
        importlib.reload(cli)
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""
    importlib.reload(cli)


def test_parser_exposes_exact_commands_and_requires_arguments():
    parser = cli._parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    assert tuple(subparsers.choices) == (
        "evidence",
        "catalog",
        "ask",
        "discover",
        "decide",
        "family-decide",
    )
    assert {
        name: {
            option
            for action in command_parser._actions
            for option in action.option_strings
        }
        for name, command_parser in subparsers.choices.items()
    } == {
        "evidence": {"-h", "--help", "--root"},
        "catalog": {"-h", "--help", "--database"},
        "ask": {
            "-h",
            "--help",
            "--database",
            "--root",
            "--question",
            "--backend",
        },
        "discover": {
            "-h",
            "--help",
            "--query",
            "--platform",
            "--cdp-endpoint",
            "--shortlist-size",
        },
        "decide": {
            "-h",
            "--help",
            "--query",
            "--platform",
            "--cdp-endpoint",
            "--shortlist-size",
            "--actor",
            "--decided-at",
        },
        "family-decide": {
            "-h",
            "--help",
            "--root",
            "--database",
            "--actor",
            "--decided-at",
        },
    }

    invalid = (
        [],
        ["unknown"],
        ["evidence"],
        ["catalog"],
        ["ask", "--database", "db", "--root", "root", "--question", "q"],
        ["discover"],
        ["discover", "--query", "q"],
        ["discover", "--platform", "shopee"],
        ["discover", "--cdp-endpoint", "http://127.0.0.1:9222"],
        ["discover", "--query", "q", "--platform", "shopee"],
        ["discover", "--query", "q", "--cdp-endpoint", "http://127.0.0.1:9222"],
        ["discover", "--platform", "shopee", "--cdp-endpoint", "http://127.0.0.1:9222"],
        [
            "discover",
            "--query",
            "q",
            "--platform",
            "invalid",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
        ],
        [
            "discover",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--shortlist-size",
            "invalid_int",
        ],
        [
            "discover",
            "--query",
            "q1",
            "--query",
            "q2",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
        ],
        [
            "discover",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--cdp-endpoint",
            "http://127.0.0.1:9223",
        ],
        [
            "discover",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--shortlist-size",
            "5",
            "--shortlist-size",
            "10",
        ],
        ["decide"],
        ["decide", "--query", "q"],
        ["decide", "--actor", "reviewer"],
        ["decide", "--decided-at", "2026-09-06T12:00:00Z"],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--actor",
            "reviewer",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--decided-at",
            "2026-09-06T12:00:00Z",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "invalid",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--actor",
            "reviewer",
            "--decided-at",
            "2026-09-06T12:00:00Z",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--shortlist-size",
            "invalid_int",
            "--actor",
            "reviewer",
            "--decided-at",
            "2026-09-06T12:00:00Z",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--actor",
            "reviewer",
            "--decided-at",
            "not-a-datetime",
        ],
        [
            "decide",
            "--query",
            "q1",
            "--query",
            "q2",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--actor",
            "reviewer",
            "--decided-at",
            "2026-09-06T12:00:00Z",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--cdp-endpoint",
            "http://127.0.0.1:9223",
            "--actor",
            "reviewer",
            "--decided-at",
            "2026-09-06T12:00:00Z",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--shortlist-size",
            "5",
            "--shortlist-size",
            "10",
            "--actor",
            "reviewer",
            "--decided-at",
            "2026-09-06T12:00:00Z",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--actor",
            "reviewer1",
            "--actor",
            "reviewer2",
            "--decided-at",
            "2026-09-06T12:00:00Z",
        ],
        [
            "decide",
            "--query",
            "q",
            "--platform",
            "shopee",
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--actor",
            "reviewer",
            "--decided-at",
            "2026-09-06T12:00:00Z",
            "--decided-at",
            "2026-09-06T13:00:00Z",
        ],
        ["family-decide"],
        ["family-decide", "--root", "r"],
        ["family-decide", "--database", "db"],
        ["family-decide", "--actor", "act"],
        ["family-decide", "--decided-at", "2026-09-06T12:00:00Z"],
        ["family-decide", "--root", "r", "--database", "db", "--actor", "act"],
        ["family-decide", "--root", "r", "--database", "db", "--decided-at", "2026-09-06T12:00:00Z"],
        ["family-decide", "--root", "r", "--actor", "act", "--decided-at", "2026-09-06T12:00:00Z"],
        ["family-decide", "--database", "db", "--actor", "act", "--decided-at", "2026-09-06T12:00:00Z"],
        ["family-decide", "--root", "r", "--database", "db", "--actor", "act", "--decided-at", "not-a-datetime"],
        ["family-decide", "--root", "r", "--database", "db1", "--database", "db2", "--actor", "act", "--decided-at", "2026-09-06T12:00:00Z"],
        ["family-decide", "--root", "r", "--database", "db", "--actor", "act1", "--actor", "act2", "--decided-at", "2026-09-06T12:00:00Z"],
        ["family-decide", "--root", "r", "--database", "db", "--actor", "act", "--decided-at", "2026-09-06T12:00:00Z", "--decided-at", "2026-09-06T13:00:00Z"],
        ["family-decide", "--root", "r", "--database", "db", "--actor", "act", "--decided-at", "2026-09-06T12:00:00Z", "--family-id", "f1"],
        ["family-decide", "--root", "r", "--database", "db", "--actor", "act", "--decided-at", "2026-09-06T12:00:00Z", "--decision", "APPROVE"],
        ["family-decide", "--root", "r", "--database", "db", "--actor", "act", "--decided-at", "2026-09-06T12:00:00Z", "--proposal", "1"],
    )
    for argv in invalid:
        with pytest.raises(SystemExit) as error:
            parser.parse_args(argv)
        assert error.value.code == 2

    with pytest.raises(SystemExit) as error:
        parser.parse_args(
            [
                "ask",
                "--database",
                "db",
                "--root",
                "root",
                "--question",
                "q",
                "--backend",
                "automatic",
            ]
        )
    assert error.value.code == 2

    parsed = parser.parse_args(
        [
            "family-decide",
            "--root",
            "root1",
            "--root",
            "root2",
            "--database",
            "cat.db",
            "--actor",
            "operator",
            "--decided-at",
            "2026-09-06T12:00:00+00:00",
        ]
    )
    assert parsed.command == "family-decide"
    assert parsed.root == ["root1", "root2"]
    assert parsed.database == "cat.db"
    assert parsed.actor == "operator"
    assert parsed.decided_at == datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def test_evidence_delegates_once_and_preserves_aligned_inventory(monkeypatch, capsys):
    roots = ["root-z", "root-a"]
    inventory = SourceEvidenceInventory(
        ("manifest-z", "manifest-a"),
        (_pack("z", 2), _pack("a", 1)),
    )
    calls: list[object] = []

    def intake(value):
        calls.append(value)
        return inventory

    monkeypatch.setattr(cli, "_intake_product_source_evidence", intake)
    assert cli.main(["evidence", "--root", roots[0], "--root", roots[1]]) == 0
    document, error_output = _read_output(capsys)

    assert calls == [roots]
    assert error_output == ""
    assert document == {
        "manifest_paths": ["manifest-z", "manifest-a"],
        "source_packs": [
            {
                "source_pack_id": "pack-z",
                "platform": "market-z",
                "source_product_id": "listing-z",
                "product_url": "https://market.example/z",
                "observed_at": "2026-09-06T02:00:00+00:00",
                "title": "Title z",
            },
            {
                "source_pack_id": "pack-a",
                "platform": "market-a",
                "source_product_id": "listing-a",
                "product_url": "https://market.example/a",
                "observed_at": "2026-09-06T01:00:00+00:00",
                "title": "Title a",
            },
        ],
    }


def test_catalog_delegates_once_and_preserves_catalog_order(monkeypatch, capsys):
    member_z = SimpleNamespace(source_pack_id="pack-z")
    member_a = SimpleNamespace(source_pack_id="pack-a")
    state = SimpleNamespace(
        families=(
            SimpleNamespace(family_id="family-z", members=(member_z, member_a)),
            SimpleNamespace(family_id="family-a", members=(member_a,)),
        ),
        variants=(
            SimpleNamespace(
                variant_id="variant-z",
                family_id="family-z",
                members=(member_a, member_z),
            ),
        ),
    )
    calls: list[str] = []

    def load(database):
        calls.append(database)
        return state

    monkeypatch.setattr(cli, "_load_sqlite_canonical_catalog", load)
    assert cli.main(["catalog", "--database", "catalog.sqlite3"]) == 0
    document, error_output = _read_output(capsys)

    assert calls == ["catalog.sqlite3"]
    assert error_output == ""
    assert document == {
        "family_count": 2,
        "variant_count": 1,
        "families": [
            {
                "family_id": "family-z",
                "member_source_pack_ids": ["pack-z", "pack-a"],
            },
            {
                "family_id": "family-a",
                "member_source_pack_ids": ["pack-a"],
            },
        ],
        "variants": [
            {
                "variant_id": "variant-z",
                "family_id": "family-z",
                "member_source_pack_ids": ["pack-a", "pack-z"],
            }
        ],
    }


@pytest.mark.parametrize("backend", ["developer_api", "vertex_ai"])
def test_ask_uses_only_human_backend_and_exact_task_135_arguments(
    backend, monkeypatch, capsys
):
    roots = ["root-2", "root-1"]
    inventory = SimpleNamespace(manifest_paths=("path-2", "path-1"))
    intake_calls: list[object] = []
    provider_calls: list[dict[str, object]] = []
    answer_calls: list[tuple[object, ...]] = []
    provider = object()

    def intake(value):
        intake_calls.append(value)
        return inventory

    def provider_factory(*args, **kwargs):
        provider_calls.append({"args": args, "kwargs": kwargs})
        return provider

    async def answer(database, manifest_paths, *, question, provider):
        answer_calls.append((database, manifest_paths, question, provider))
        return SimpleNamespace(
            status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
            answer_text="Exact answer wording.",
            citation_ids=("H002-W001", "H001-E001"),
            limitations=("Second limitation", "First limitation"),
        )

    monkeypatch.setattr(cli, "_intake_product_source_evidence", intake)
    monkeypatch.setattr(cli, "_GeminiProvider", provider_factory)
    monkeypatch.setattr(cli, "_answer_persisted_grounded_question", answer)

    assert (
        cli.main(
            [
                "ask",
                "--database",
                "catalog.db",
                "--root",
                roots[0],
                "--root",
                roots[1],
                "--question",
                "Exact question?",
                "--backend",
                backend,
            ]
        )
        == 0
    )
    document, error_output = _read_output(capsys)

    assert intake_calls == [roots]
    assert provider_calls == [{"args": (), "kwargs": {"backend": backend}}]
    assert answer_calls == [
        ("catalog.db", ("path-2", "path-1"), "Exact question?", provider)
    ]
    assert error_output == ""
    assert document == {
        "status": "CONFLICTING_EVIDENCE",
        "answer_text": "Exact answer wording.",
        "citation_ids": ["H002-W001", "H001-E001"],
        "limitations": ["Second limitation", "First limitation"],
    }


def test_known_error_is_top_level_only_and_nested_secret_is_not_emitted(
    monkeypatch, capsys
):
    secret = "nested-provider-secret"

    def fail(_roots):
        try:
            raise RuntimeError(secret)
        except RuntimeError as cause:
            raise AgentException(
                "LLM Provider failure.",
                code="LLM_PROVIDER_ERROR",
                retryable=True,
            ) from cause

    monkeypatch.setattr(cli, "_intake_product_source_evidence", fail)
    assert cli.main(["evidence", "--root", "root"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "error": {
            "type": "AgentException",
            "message": "LLM Provider failure.",
        }
    }
    assert secret not in captured.err
    assert "Traceback" not in captured.err


def test_unexpected_error_is_generic(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_load_sqlite_canonical_catalog",
        lambda _database: (_ for _ in ()).throw(RuntimeError("sensitive detail")),
    )
    assert cli.main(["catalog", "--database", "catalog.db"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "error": {
            "type": "UnexpectedError",
            "message": "An unexpected error occurred.",
        }
    }
    assert "sensitive detail" not in captured.err
    assert "Traceback" not in captured.err


def test_cli_source_has_no_mutation_ranking_or_direct_provider_authority():
    source = Path(cli.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden_modules = {
        "src.agent_controller",
        "src.agent_loop",
        "src.product_intelligence.ranking",
        "src.product_source.serialization",
        "playwright",
        "playwright.async_api",
        "playwright.sync_api",
    }
    assert imported_modules.isdisjoint(forbidden_modules)
    assert "register_sqlite" not in source
    assert "build_ingestion_task" not in source
    assert "build_approved_ingestion_task" not in source
    assert "tasks.txt" not in source
    assert "completed.txt" not in source
    assert "open(" not in source
    assert "fsync" not in source
    assert ".generate(" not in source
    assert "google.genai" not in source
    assert "AgentController" not in source
    assert "AgentLoop" not in source
    assert "CandidateRanker" not in source
    assert "rank_candidates" not in source
    assert "WinningProductScorer" not in source
    assert "SnapshotNormalizer" not in source
    assert "playwright.async_api" not in source
    assert "playwright.sync_api" not in source


class _FakeBrowserManager:
    def __init__(self, cdp_endpoint: str | None = None):
        self.cdp_endpoint = cdp_endpoint
        self.close_all_calls = 0
        self.close_all_exc: Exception | None = None

    async def close_all(self):
        self.close_all_calls += 1
        if self.close_all_exc:
            raise self.close_all_exc


def test_discover_delegates_once_preserves_order_and_outputs_result_dict(
    monkeypatch, capsys
):
    created_managers: list[_FakeBrowserManager] = []

    def fake_manager_factory(cdp_endpoint=None):
        mgr = _FakeBrowserManager(cdp_endpoint=cdp_endpoint)
        created_managers.append(mgr)
        return mgr

    captured_orchestration: dict[str, object] = {}
    dummy_result = SimpleNamespace(
        to_dict=lambda: {
            "batches": [
                {
                    "platform": "tiktok",
                    "candidates": [],
                    "pages_examined": 1,
                    "raw_items_seen": 0,
                    "diagnostic_codes": [],
                },
                {
                    "platform": "shopee",
                    "candidates": [],
                    "pages_examined": 1,
                    "raw_items_seen": 0,
                    "diagnostic_codes": [],
                },
            ],
            "shortlist": [],
            "total_candidates_discovered": 0,
            "shortlist_count": 0,
        }
    )

    async def fake_orchestrate(
        plans, *, observed_at, evaluated_at, shortlist_size=None, policy=None
    ):
        captured_orchestration["plans"] = plans
        captured_orchestration["observed_at"] = observed_at
        captured_orchestration["evaluated_at"] = evaluated_at
        captured_orchestration["shortlist_size"] = shortlist_size
        captured_orchestration["policy"] = policy
        return dummy_result

    import src.product_intelligence.ranking as ranking_mod
    import src.product_intelligence.scoring as scoring_mod
    forbidden = lambda *args, **kwargs: pytest.fail("CLI called unauthorized M2 API directly")
    monkeypatch.setattr(ranking_mod.CandidateRanker, "rank", forbidden)
    monkeypatch.setattr(scoring_mod.WinningProductScorer, "score", forbidden)
    monkeypatch.setattr(ShopeeDiscoveryAdapter, "discover", forbidden)
    monkeypatch.setattr(TikTokDiscoveryAdapter, "discover", forbidden)

    monkeypatch.setattr(cli, "_PlaywrightBrowserManager", fake_manager_factory)
    monkeypatch.setattr(cli, "_orchestrate_discovery", fake_orchestrate)

    argv = [
        "discover",
        "--query",
        "bình giữ nhiệt",
        "--platform",
        "tiktok",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--shortlist-size",
        "5",
    ]
    exit_code = cli.main(argv)
    document, error_output = _read_output(capsys)

    assert exit_code == 0
    assert error_output == ""
    assert document == dummy_result.to_dict()

    # Manager assertions
    assert len(created_managers) == 1
    manager = created_managers[0]
    assert manager.cdp_endpoint == "http://127.0.0.1:9222"
    assert manager.close_all_calls == 1

    # Orchestration plan assertions
    plans = captured_orchestration["plans"]
    assert isinstance(plans, tuple)
    assert len(plans) == 2
    assert plans[0].platform == "tiktok"
    assert isinstance(plans[0].adapter, TikTokDiscoveryAdapter)
    assert plans[0].adapter._browser is manager
    assert plans[0].request.query == "bình giữ nhiệt"
    assert plans[0].request.max_candidates == 50
    assert plans[0].request.max_pages == 1
    assert plans[0].request.locale == "vi-VN"

    assert plans[1].platform == "shopee"
    assert isinstance(plans[1].adapter, ShopeeDiscoveryAdapter)
    assert plans[1].adapter._browser is manager
    assert plans[1].request.query == "bình giữ nhiệt"
    assert plans[1].request.max_candidates == 50
    assert plans[1].request.max_pages == 1
    assert plans[1].request.locale == "vi-VN"

    # Timestamp assertions
    observed_at = captured_orchestration["observed_at"]
    evaluated_at = captured_orchestration["evaluated_at"]
    assert isinstance(observed_at, datetime)
    assert observed_at.tzinfo == timezone.utc
    assert observed_at is evaluated_at  # exact same datetime object identity

    # Shortlist size and policy assertions
    assert captured_orchestration["shortlist_size"] == 5
    assert captured_orchestration["policy"] is None


def test_discover_shortlist_size_omitted_passes_none(monkeypatch, capsys):
    captured_orchestration: dict[str, object] = {}
    dummy_result = SimpleNamespace(to_dict=lambda: {"batches": [], "shortlist": []})

    async def fake_orchestrate(
        plans, *, observed_at, evaluated_at, shortlist_size=None, policy=None
    ):
        captured_orchestration["shortlist_size"] = shortlist_size
        return dummy_result

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(cli, "_orchestrate_discovery", fake_orchestrate)

    argv = [
        "discover",
        "--query",
        "áo sơ mi",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0
    assert captured_orchestration["shortlist_size"] is None


def test_discover_duplicate_platform_propagates_to_orchestrator_and_fails_closed(
    capsys,
):
    argv = [
        "discover",
        "--query",
        "áo len",
        "--platform",
        "shopee",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    error_doc = json.loads(captured.err)
    assert error_doc == {
        "error": {
            "type": "OrchestrationInvalidRequestError",
            "message": "Duplicate platform in discovery plans: 'shopee'",
        }
    }
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "error_instance, expected_type, expected_msg",
    [
        (DiscoveryError("Discovery failed"), "DiscoveryError", "Discovery failed"),
        (
            DiscoveryBlockedError("Captcha challenge"),
            "DiscoveryBlockedError",
            "Captcha challenge",
        ),
        (
            DiscoveryNavigationError("Page timeout"),
            "DiscoveryNavigationError",
            "Page timeout",
        ),
        (
            DiscoveryInvalidRequestError("Query too short"),
            "DiscoveryInvalidRequestError",
            "Query too short",
        ),
        (
            OrchestrationError("Orchestration broke"),
            "OrchestrationError",
            "Orchestration broke",
        ),
        (
            OrchestrationInvalidRequestError("Invalid plan"),
            "OrchestrationInvalidRequestError",
            "Invalid plan",
        ),
        (
            AgentException("Browser crashed", code="CRASH"),
            "AgentException",
            "Browser crashed",
        ),
    ],
)
def test_discover_known_errors_are_sanitized_and_clean_up(
    error_instance, expected_type, expected_msg, monkeypatch, capsys
):
    created_managers: list[_FakeBrowserManager] = []

    def fake_manager_factory(cdp_endpoint=None):
        mgr = _FakeBrowserManager(cdp_endpoint=cdp_endpoint)
        created_managers.append(mgr)
        return mgr

    async def failing_orchestrate(*args, **kwargs):
        raise error_instance

    monkeypatch.setattr(cli, "_PlaywrightBrowserManager", fake_manager_factory)
    monkeypatch.setattr(cli, "_orchestrate_discovery", failing_orchestrate)

    argv = [
        "discover",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    error_doc = json.loads(captured.err)
    assert error_doc == {
        "error": {
            "type": expected_type,
            "message": expected_msg,
        }
    }
    assert "Traceback" not in captured.err
    assert len(created_managers) == 1
    assert created_managers[0].close_all_calls == 1


def test_discover_cleanup_failure_does_not_mask_orchestration_error(
    monkeypatch, capsys
):
    created_managers: list[_FakeBrowserManager] = []

    def fake_manager_factory(cdp_endpoint=None):
        mgr = _FakeBrowserManager(cdp_endpoint=cdp_endpoint)
        mgr.close_all_exc = RuntimeError("Secret browser socket cleanup leak")
        created_managers.append(mgr)
        return mgr

    async def failing_orchestrate(*args, **kwargs):
        raise DiscoveryError("Primary discovery error message")

    monkeypatch.setattr(cli, "_PlaywrightBrowserManager", fake_manager_factory)
    monkeypatch.setattr(cli, "_orchestrate_discovery", failing_orchestrate)

    argv = [
        "discover",
        "--query",
        "test",
        "--platform",
        "tiktok",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    error_doc = json.loads(captured.err)
    assert error_doc == {
        "error": {
            "type": "DiscoveryError",
            "message": "Primary discovery error message",
        }
    }
    assert "Secret browser socket cleanup leak" not in captured.err
    assert "Traceback" not in captured.err
    assert created_managers[0].close_all_calls == 1


def test_discover_cleanup_failure_after_successful_orchestration_fails_closed(
    monkeypatch, capsys
):
    created_managers: list[_FakeBrowserManager] = []

    def fake_manager_factory(cdp_endpoint=None):
        mgr = _FakeBrowserManager(cdp_endpoint=cdp_endpoint)
        mgr.close_all_exc = AgentException(
            "CDP session disconnect failure", code="BROWSER_CLOSE_FAILED"
        )
        created_managers.append(mgr)
        return mgr

    dummy_result = SimpleNamespace(to_dict=lambda: {"batches": [], "shortlist": []})

    async def success_orchestrate(*args, **kwargs):
        return dummy_result

    monkeypatch.setattr(cli, "_PlaywrightBrowserManager", fake_manager_factory)
    monkeypatch.setattr(cli, "_orchestrate_discovery", success_orchestrate)

    argv = [
        "discover",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    error_doc = json.loads(captured.err)
    assert error_doc == {
        "error": {
            "type": "AgentException",
            "message": "CDP session disconnect failure",
        }
    }
    assert "Traceback" not in captured.err


def test_discover_empty_query_fails_closed(capsys):
    argv = [
        "discover",
        "--query",
        "   ",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    error_doc = json.loads(captured.err)
    assert error_doc == {
        "error": {
            "type": "DiscoveryInvalidRequestError",
            "message": "Discovery query cannot be empty or whitespace only",
        }
    }
    assert "Traceback" not in captured.err


def test_discover_unexpected_error_is_generic(monkeypatch, capsys):
    created_managers: list[_FakeBrowserManager] = []

    def fake_manager_factory(cdp_endpoint=None):
        mgr = _FakeBrowserManager(cdp_endpoint=cdp_endpoint)
        created_managers.append(mgr)
        return mgr

    async def failing_orchestrate(*args, **kwargs):
        raise RuntimeError("sensitive internal failure")

    monkeypatch.setattr(cli, "_PlaywrightBrowserManager", fake_manager_factory)
    monkeypatch.setattr(cli, "_orchestrate_discovery", failing_orchestrate)

    argv = [
        "discover",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    error_doc = json.loads(captured.err)
    assert error_doc == {
        "error": {
            "type": "UnexpectedError",
            "message": "An unexpected error occurred.",
        }
    }
    assert "sensitive internal failure" not in captured.err
    assert "Traceback" not in captured.err
    assert len(created_managers) == 1
    assert created_managers[0].close_all_calls == 1


@pytest.mark.parametrize(
    "duplicate_args",
    [
        ["--query", "first_query", "--query", "second_query"],
        [
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--cdp-endpoint",
            "http://127.0.0.1:9223",
        ],
        ["--shortlist-size", "5", "--shortlist-size", "10"],
    ],
)
def test_discover_rejects_repeated_single_value_options(duplicate_args, capsys):
    parser = cli._parser()
    base_args = [
        "discover",
        "--query",
        "valid_query",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
    ]
    opt_flag = duplicate_args[0]
    filtered_base = []
    i = 0
    while i < len(base_args):
        if base_args[i] == opt_flag:
            i += 2
        else:
            filtered_base.append(base_args[i])
            i += 1
    argv = filtered_base + duplicate_args

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(argv)
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info:
        cli.main(argv)
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert opt_flag in captured.err
    assert "cannot be repeated" in captured.err


def _make_candidate(
    candidate_id: str = "shopee:123:456",
    platform: str = "shopee",
    url: str = "https://shopee.vn/canonical-product-i.123.456",
    title: str = "Canonical product",
    decision_band: DecisionBand | None = None,
) -> RankedCandidate:
    observed = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
    candidate = ProductCandidateSnapshot(
        candidate_id=candidate_id,
        platform=platform,
        url=url,
        observed_at=observed,
        title=title,
        sold_count=50_000,
        review_count=5_000,
        rating=4.9,
        affiliate_commission_rate=20.0,
        discount_percent=40.0,
        sales_velocity=100.0,
        creator_velocity=10.0,
        creator_count=1,
        similar_listing_count=1,
    )
    score = WinningProductScorer.score_snapshot(candidate, evaluated_at=observed)
    if decision_band is not None:
        score = replace(score, decision_band=decision_band)
    return RankedCandidate(candidate=candidate, score=score)


def _make_orchestration_result(
    candidates: tuple[RankedCandidate, ...],
) -> OrchestrationResult:
    return OrchestrationResult(
        batches=(),
        shortlist=candidates,
    )


def _fake_orchestrator(result):
    async def _orchestrate(*args, **kwargs):
        return result

    return _orchestrate


@pytest.mark.parametrize(
    "duplicate_args",
    [
        ["--query", "first_query", "--query", "second_query"],
        [
            "--cdp-endpoint",
            "http://127.0.0.1:9222",
            "--cdp-endpoint",
            "http://127.0.0.1:9223",
        ],
        ["--shortlist-size", "5", "--shortlist-size", "10"],
        ["--actor", "user1", "--actor", "user2"],
        [
            "--decided-at",
            "2026-09-06T12:00:00Z",
            "--decided-at",
            "2026-09-06T13:00:00Z",
        ],
    ],
)
def test_decide_rejects_repeated_single_value_options(duplicate_args, capsys):
    parser = cli._parser()
    base_args = [
        "decide",
        "--query",
        "valid_query",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    opt_flag = duplicate_args[0]
    filtered_base = []
    i = 0
    while i < len(base_args):
        if base_args[i] == opt_flag:
            i += 2
        else:
            filtered_base.append(base_args[i])
            i += 1
    argv = filtered_base + duplicate_args

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(argv)
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info:
        cli.main(argv)
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert opt_flag in captured.err
    assert "cannot be repeated" in captured.err


def test_decide_performs_shared_discovery_and_cleanup_before_human_interaction(
    monkeypatch, capsys
):
    events: list[str] = []
    created_managers: list[_FakeBrowserManager] = []

    class _TracingBrowserManager(_FakeBrowserManager):
        async def close_all(self):
            events.append("close_all")
            await super().close_all()

    def fake_manager_factory(cdp_endpoint=None):
        mgr = _TracingBrowserManager(cdp_endpoint=cdp_endpoint)
        created_managers.append(mgr)
        return mgr

    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))

    async def fake_orchestrate(*args, **kwargs):
        events.append("orchestrate")
        return dummy_result

    class _TracingStdin:
        def __init__(self):
            self.lines = ["1\n", "APPROVE\n"]

        def readline(self):
            events.append("stdin_readline")
            return self.lines.pop(0) if self.lines else ""

    real_create_approval = cli._create_approval_record

    def tracing_create_approval(*args, **kwargs):
        events.append("create_approval")
        return real_create_approval(*args, **kwargs)

    real_enqueue_approval = cli._enqueue_approval

    def tracing_enqueue_approval(*args, **kwargs):
        events.append("enqueue_approval")
        return EnqueueResult(task="task", outcome=EnqueueOutcome.ENQUEUED)

    monkeypatch.setattr(cli, "_PlaywrightBrowserManager", fake_manager_factory)
    monkeypatch.setattr(cli, "_orchestrate_discovery", fake_orchestrate)
    monkeypatch.setattr(cli._sys, "stdin", _TracingStdin())
    monkeypatch.setattr(cli, "_create_approval_record", tracing_create_approval)
    monkeypatch.setattr(cli, "_enqueue_approval", tracing_enqueue_approval)

    argv = [
        "decide",
        "--query",
        "valid_query",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0
    assert events == [
        "orchestrate",
        "close_all",
        "stdin_readline",
        "stdin_readline",
        "create_approval",
        "enqueue_approval",
    ]


def test_decide_renders_exact_preview_to_stderr_before_input(monkeypatch, capsys):
    c1 = _make_candidate(
        candidate_id="shopee:1", url="https://shopee.vn/p1", title="Product 1"
    )
    c2 = _make_candidate(
        candidate_id="tiktok:2",
        platform="tiktok",
        url="https://tiktok.com/p2",
        title="Product 2",
    )
    dummy_result = _make_orchestration_result((c1, c2))

    async def fake_orchestrate(*args, **kwargs):
        return dummy_result

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(cli, "_orchestrate_discovery", fake_orchestrate)
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n"))
    monkeypatch.setattr(
        cli,
        "_enqueue_approval",
        lambda record: EnqueueResult(task="task", outcome=EnqueueOutcome.ENQUEUED),
    )

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--platform",
        "tiktok",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0
    captured = capsys.readouterr()
    preview = json.loads(captured.err)
    assert preview == dummy_result.to_dict()
    assert preview["shortlist_count"] == 2
    assert preview["shortlist"][0]["candidate"]["candidate_id"] == "shopee:1"
    assert preview["shortlist"][1]["candidate"]["candidate_id"] == "tiktok:2"


def test_decide_human_position_selects_exact_ranked_candidate_by_identity(
    monkeypatch, capsys
):
    c1 = _make_candidate(
        candidate_id="shopee:1", url="https://shopee.vn/p1", title="Product 1"
    )
    c2 = _make_candidate(
        candidate_id="tiktok:2",
        platform="tiktok",
        url="https://tiktok.com/p2",
        title="Product 2",
    )
    dummy_result = _make_orchestration_result((c1, c2))
    passed_candidates: list[RankedCandidate] = []

    def spy_create_approval_record(ranked_candidate, **kwargs):
        passed_candidates.append(ranked_candidate)
        return create_approval_record(ranked_candidate, **kwargs)

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO("2\nAPPROVE\n"))
    monkeypatch.setattr(cli, "_create_approval_record", spy_create_approval_record)
    monkeypatch.setattr(
        cli,
        "_enqueue_approval",
        lambda record: EnqueueResult(task="task", outcome=EnqueueOutcome.ENQUEUED),
    )

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0
    assert len(passed_candidates) == 1
    assert passed_candidates[0] is c2
    assert passed_candidates[0] is not c1

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert (
        doc["approval"]["ranked_candidate"]["candidate"]["candidate_id"] == "tiktok:2"
    )


def test_decide_forwards_approve_actor_and_parsed_decided_at_to_task_096_and_enqueues_once(
    monkeypatch, capsys
):
    c1 = _make_candidate(
        candidate_id="shopee:1", url="https://shopee.vn/p1", title="Product 1"
    )
    dummy_result = _make_orchestration_result((c1,))
    approval_calls: list[dict[str, object]] = []
    enqueue_calls: list[object] = []

    def spy_create_approval(ranked, *, decision, actor, decided_at):
        approval_calls.append(
            {
                "ranked": ranked,
                "decision": decision,
                "actor": actor,
                "decided_at": decided_at,
            }
        )
        return create_approval_record(
            ranked, decision=decision, actor=actor, decided_at=decided_at
        )

    def spy_enqueue(record):
        enqueue_calls.append(record)
        return EnqueueResult(
            task="Scrape product images from https://shopee.vn/p1",
            outcome=EnqueueOutcome.ENQUEUED,
        )

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n"))
    monkeypatch.setattr(cli, "_create_approval_record", spy_create_approval)
    monkeypatch.setattr(cli, "_enqueue_approval", spy_enqueue)

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "senior-operator@example.com",
        "--decided-at",
        "2026-09-06T14:30:00+07:00",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0
    assert len(approval_calls) == 1
    assert approval_calls[0]["ranked"] is c1
    assert approval_calls[0]["decision"] == ApprovalDecision.APPROVE
    assert approval_calls[0]["actor"] == "senior-operator@example.com"
    assert approval_calls[0]["decided_at"] == datetime.fromisoformat(
        "2026-09-06T14:30:00+07:00"
    )
    assert len(enqueue_calls) == 1

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert list(doc.keys()) == ["approval", "queue"]
    assert doc["approval"] == {
        "decision": "APPROVE",
        "actor": "senior-operator@example.com",
        "decided_at": "2026-09-06T14:30:00+07:00",
        "ranked_candidate": {
            "candidate": c1.candidate.to_dict(),
            "score": c1.score.to_dict(),
        },
    }
    assert doc["queue"] == {
        "task": "Scrape product images from https://shopee.vn/p1",
        "outcome": "ENQUEUED",
    }


def test_decide_reject_makes_zero_enqueue_calls_and_returns_queue_null(
    monkeypatch, capsys
):
    c1 = _make_candidate(
        candidate_id="shopee:1", url="https://shopee.vn/p1", title="Product 1"
    )
    dummy_result = _make_orchestration_result((c1,))
    enqueue_calls: list[object] = []

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nREJECT\n"))
    monkeypatch.setattr(
        cli, "_enqueue_approval", lambda record: enqueue_calls.append(record)
    )

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "rejector@example.com",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0
    assert len(enqueue_calls) == 0

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert list(doc.keys()) == ["approval", "queue"]
    assert doc["approval"]["decision"] == "REJECT"
    assert doc["approval"]["actor"] == "rejector@example.com"
    assert doc["queue"] is None


def test_decide_no_score_rank_auto_authority(monkeypatch, capsys):
    hold_candidate = _make_candidate(
        candidate_id="shopee:low",
        url="https://shopee.vn/low",
        decision_band=DecisionBand.HOLD,
    )
    recommended_candidate = _make_candidate(
        candidate_id="shopee:high",
        url="https://shopee.vn/high",
        decision_band=DecisionBand.RECOMMENDED,
    )
    dummy_result = _make_orchestration_result((hold_candidate, recommended_candidate))

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(
        cli,
        "_enqueue_approval",
        lambda record: EnqueueResult(task="task", outcome=EnqueueOutcome.ENQUEUED),
    )

    # Human approves the HOLD candidate
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n"))
    argv1 = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "human",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    assert cli.main(argv1) == 0
    doc1 = json.loads(capsys.readouterr().out)
    assert (
        doc1["approval"]["ranked_candidate"]["score"]["decision_band"]
        == "HOLD"
    )
    assert doc1["approval"]["decision"] == "APPROVE"
    assert doc1["queue"] is not None

    # Human rejects the RECOMMENDED candidate
    monkeypatch.setattr(cli._sys, "stdin", StringIO("2\nREJECT\n"))
    assert cli.main(argv1) == 0
    doc2 = json.loads(capsys.readouterr().out)
    assert (
        doc2["approval"]["ranked_candidate"]["score"]["decision_band"]
        == "RECOMMENDED"
    )
    assert doc2["approval"]["decision"] == "REJECT"
    assert doc2["queue"] is None


def test_decide_empty_shortlist_fails_closed_before_interaction_or_approval(
    monkeypatch, capsys
):
    dummy_result = _make_orchestration_result(())
    approval_called = False

    def forbidden_approval(*args, **kwargs):
        nonlocal approval_called
        approval_called = True
        raise AssertionError("Approval should not be called")

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli, "_create_approval_record", forbidden_approval)

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    assert not approval_called

    captured = capsys.readouterr()
    assert captured.out == ""
    err_doc = json.loads(captured.err)
    assert err_doc == {
        "error": {
            "type": "ValueError",
            "message": "Discovery shortlist is empty",
        }
    }
    assert "Traceback" not in captured.err


def test_decide_discovery_and_cleanup_failures_fail_closed(monkeypatch, capsys):
    mgr = _FakeBrowserManager()
    mgr.close_all_exc = AgentException("CDP disconnect failed", code="CLOSE_FAIL")

    async def fail_discovery(*args, **kwargs):
        raise DiscoveryError("Marketplace rate limit")

    monkeypatch.setattr(cli, "_PlaywrightBrowserManager", lambda *args, **kwargs: mgr)
    monkeypatch.setattr(cli, "_orchestrate_discovery", fail_discovery)

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    err_doc = json.loads(captured.err)
    assert err_doc == {
        "error": {
            "type": "DiscoveryError",
            "message": "Marketplace rate limit",
        }
    }
    assert mgr.close_all_calls == 1


@pytest.mark.parametrize(
    "stdin_content, expected_msg",
    [
        ("", "missing shortlist position"),
        ("1\n", "missing decision token"),
    ],
)
def test_decide_eof_fails_closed(stdin_content, expected_msg, monkeypatch, capsys):
    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO(stdin_content))

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error" in captured.err
    assert expected_msg in captured.err


@pytest.mark.parametrize(
    "invalid_pos",
    [
        "0\n",
        "-1\n",
        "2\n",
        "abc\n",
        "1.0\n",
        "1 2\n",
        " 1 \n",
        "\n",
    ],
)
def test_decide_invalid_position_inputs_fail_closed(invalid_pos, monkeypatch, capsys):
    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))
    approval_called = False

    def forbidden_approval(*args, **kwargs):
        nonlocal approval_called
        approval_called = True

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO(f"{invalid_pos}APPROVE\n"))
    monkeypatch.setattr(cli, "_create_approval_record", forbidden_approval)

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    assert not approval_called
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error" in captured.err
    assert "ValueError" in captured.err


@pytest.mark.parametrize(
    "invalid_decision",
    [
        "approve\n",
        "MAYBE\n",
        "APPROVE extra\n",
        " APPROVE\n",
        "APPROVE \n",
        "1\n",
        "\n",
    ],
)
def test_decide_invalid_decision_token_fails_closed(
    invalid_decision, monkeypatch, capsys
):
    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))
    approval_called = False

    def forbidden_approval(*args, **kwargs):
        nonlocal approval_called
        approval_called = True

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO(f"1\n{invalid_decision}"))
    monkeypatch.setattr(cli, "_create_approval_record", forbidden_approval)

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    assert not approval_called
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error" in captured.err
    assert "ValueError" in captured.err


def test_decide_approval_error_timezone_naive_fails_sanitized(monkeypatch, capsys):
    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n"))

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ApprovalError" in captured.err
    assert "timezone-aware" in captured.err
    assert "Traceback" not in captured.err


def test_decide_queue_oserror_fails_sanitized(monkeypatch, capsys):
    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))

    def failing_enqueue(record):
        raise OSError("Disk write failed")

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n"))
    monkeypatch.setattr(cli, "_enqueue_approval", failing_enqueue)

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "OSError" in captured.err
    assert "Disk write failed" in captured.err
    assert "Traceback" not in captured.err


def test_decide_preserves_enqueue_outcome_already_completed(monkeypatch, capsys):
    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n"))
    monkeypatch.setattr(
        cli,
        "_enqueue_approval",
        lambda record: EnqueueResult(
            task="Scrape product images from https://shopee.vn/canonical-product-i.123.456",
            outcome=EnqueueOutcome.ALREADY_COMPLETED,
        ),
    )

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "test-actor",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0
    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert doc["queue"] == {
        "task": "Scrape product images from https://shopee.vn/canonical-product-i.123.456",
        "outcome": "ALREADY_COMPLETED",
    }


def test_decide_real_task_096_approve_enqueue_and_idempotency_regression(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "real-operator@example.com",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]

    # First run: explicit APPROVE creates tasks.txt
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n"))
    exit_code = cli.main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    expected_task = (
        "Scrape product images from https://shopee.vn/canonical-product-i.123.456"
    )
    assert doc["approval"]["decision"] == "APPROVE"
    assert doc["queue"]["task"] == expected_task
    assert doc["queue"]["outcome"] == "ENQUEUED"

    tasks_path = tmp_path / "tasks.txt"
    completed_path = tmp_path / "completed.txt"
    assert tasks_path.exists()
    assert tasks_path.read_text(encoding="utf-8") == f"{expected_task}\n"
    assert not completed_path.exists()

    # Second run: repeated APPROVE returns ALREADY_QUEUED without duplicate
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n"))
    exit_code = cli.main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    doc2 = json.loads(captured.out)
    assert doc2["queue"]["outcome"] == "ALREADY_QUEUED"
    assert tasks_path.read_text(encoding="utf-8") == f"{expected_task}\n"
    assert not completed_path.exists()


def test_decide_real_task_096_reject_no_queue_mutation_regression(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    candidate = _make_candidate()
    dummy_result = _make_orchestration_result((candidate,))

    monkeypatch.setattr(
        cli,
        "_PlaywrightBrowserManager",
        lambda cdp_endpoint=None: _FakeBrowserManager(cdp_endpoint),
    )
    monkeypatch.setattr(
        cli, "_orchestrate_discovery", _fake_orchestrator(dummy_result)
    )

    argv = [
        "decide",
        "--query",
        "test",
        "--platform",
        "shopee",
        "--cdp-endpoint",
        "http://127.0.0.1:9222",
        "--actor",
        "real-rejector@example.com",
        "--decided-at",
        "2026-09-06T12:00:00Z",
    ]

    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nREJECT\n"))
    exit_code = cli.main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert doc["approval"]["decision"] == "REJECT"
    assert doc["queue"] is None

    tasks_path = tmp_path / "tasks.txt"
    completed_path = tmp_path / "completed.txt"
    assert not tasks_path.exists()
    assert not completed_path.exists()


def _make_family_plan(*, suffix: str = "", include_singleton: bool = False):
    facts = (
        ProductFact("Brand", "Acme", "specifications", "structured"),
        ProductFact("Model", "Phone X", "specifications", "structured"),
        ProductFact("Color", "Black", "specifications", "structured"),
    )
    packs = [
        ProductSourcePack(
            source_pack_id=f"pack-shopee{suffix}",
            platform="shopee",
            product_url=f"https://shopee.example/item{suffix}",
            source_product_id=f"item-shopee{suffix}",
            observed_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            collector="test",
            facts=facts,
        ),
        ProductSourcePack(
            source_pack_id=f"pack-tiktok{suffix}",
            platform="tiktok",
            product_url=f"https://tiktok.example/item{suffix}",
            source_product_id=f"item-tiktok{suffix}",
            observed_at=datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
            collector="test",
            facts=facts,
        ),
    ]
    if include_singleton:
        packs.append(
            ProductSourcePack(
                source_pack_id=f"pack-singleton{suffix}",
                platform="shopee",
                product_url=f"https://shopee.example/single{suffix}",
                source_product_id=f"item-single{suffix}",
                observed_at=datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc),
                collector="test",
                facts=(ProductFact("Brand", "OtherBrand", "specifications", "structured"),),
            )
        )
    inventory = SourceEvidenceInventory(
        tuple(f"manifest-{i}{suffix}" for i in range(len(packs))),
        tuple(packs),
    )
    plan = plan_family_knowledge_review(inventory)
    assert len(plan.proposals) == 1
    return plan


def _decode_json_documents(text: str) -> list[dict]:
    decoder = json.JSONDecoder()
    pos = 0
    docs = []
    while pos < len(text):
        match = re.search(r"\S", text[pos:])
        if not match:
            break
        pos += match.start()
        doc, end = decoder.raw_decode(text, idx=pos)
        docs.append(doc)
        pos = end
    return docs


def _make_zero_proposal_plan():
    packs = (
        ProductSourcePack(
            source_pack_id="pack-a",
            platform="shopee",
            product_url="https://shopee.example/a",
            source_product_id="item-a",
            observed_at=datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc),
            collector="test",
            facts=(ProductFact("Brand", "Acme", "specifications", "structured"),),
        ),
        ProductSourcePack(
            source_pack_id="pack-b",
            platform="shopee",
            product_url="https://shopee.example/b",
            source_product_id="item-b",
            observed_at=datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc),
            collector="test",
            facts=(ProductFact("Brand", "OtherBrand", "specifications", "structured"),),
        ),
    )
    inventory = SourceEvidenceInventory(("manifest-0", "manifest-1"), packs)
    plan = plan_family_knowledge_review(inventory)
    assert len(plan.proposals) == 0
    assert len(plan.groups) == 2
    assert all(g.status == ProvisionalGroupStatus.SINGLETON for g in plan.groups)
    return plan


def test_family_decide_offline_approve_delegation_lineage_and_preview(monkeypatch, capsys):
    plan = _make_family_plan(include_singleton=True)
    intake_calls = []
    planning_calls = []
    decision_calls = []
    admission_calls = []

    def fake_intake(roots):
        intake_calls.append(list(roots))
        return plan.inventory

    def fake_planning(inv):
        planning_calls.append(inv)
        return plan

    orig_record_decision = cli._record_planned_family_decision

    def recorded_decision(p, prop, *, decision, actor, decided_at):
        decision_calls.append((p, prop, decision, actor, decided_at))
        return orig_record_decision(p, prop, decision=decision, actor=actor, decided_at=decided_at)

    orig_durably_admit = cli._durably_admit_planned_family

    def recorded_admit(p, record, *, family_id, database_path):
        admission_calls.append((p, record, family_id, database_path))
        # Return a dummy DurableFamilyAdmissionResult using the real decision record
        from src.product_intelligence.canonical_family import create_canonical_family
        from src.product_intelligence.canonical_catalog import (
            CatalogRegistrationResult,
            CatalogRegistrationStatus,
            create_empty_canonical_catalog,
            register_canonical_family,
        )
        fam = create_canonical_family(record, family_id=family_id)
        reg = register_canonical_family(create_empty_canonical_catalog(), fam)
        return DurableFamilyAdmissionResult(
            decision_record=record,
            family=fam,
            registration=reg,
            _lineage=_DURABLE_ADMISSION,
        )

    monkeypatch.setattr(cli, "_intake_product_source_evidence", fake_intake)
    monkeypatch.setattr(cli, "_plan_family_knowledge_review", fake_planning)
    monkeypatch.setattr(cli, "_record_planned_family_decision", recorded_decision)
    monkeypatch.setattr(cli, "_durably_admit_planned_family", recorded_admit)

    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\ncanonical-fam-1\n"))

    argv = [
        "family-decide",
        "--root",
        "/path/root-a",
        "--root",
        "/path/root-b",
        "--database",
        "sqlite:///test.db",
        "--actor",
        "reviewer-alice@example.com",
        "--decided-at",
        "2026-09-06T12:00:00+00:00",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0

    # Delegation checks
    assert len(intake_calls) == 1
    assert intake_calls[0] == ["/path/root-a", "/path/root-b"]
    assert len(planning_calls) == 1
    assert planning_calls[0] is plan.inventory

    # Preview check on stderr
    captured = capsys.readouterr()
    preview = json.loads(captured.err)
    assert list(preview.keys()) == ["groups", "proposals"]
    assert len(preview["groups"]) == len(plan.groups)
    assert [g["status"] for g in preview["groups"]] == [g.status.value for g in plan.groups]
    # Check proposal projection in preview
    assert len(preview["proposals"]) == 1
    proposal_doc = preview["proposals"][0]
    assert len(proposal_doc["members"]) == 2
    assert len(proposal_doc["pair_evidence"]) == 1
    pair = proposal_doc["pair_evidence"][0]
    assert "left" in pair and "right" in pair
    assert "relationship" in pair and "confidence" in pair
    assert "reasons" in pair and "evidence" in pair
    assert pair["evidence"][0]["code"] is not None

    # Decision call check: exact proposal object identity
    assert len(decision_calls) == 1
    dec_plan, dec_prop, dec_decision, dec_actor, dec_time = decision_calls[0]
    assert dec_plan is plan
    assert dec_prop is plan.proposals[0]
    assert dec_decision is FamilyMergeDecision.APPROVE
    assert dec_actor == "reviewer-alice@example.com"
    assert dec_time == datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)

    # Admission call check
    assert len(admission_calls) == 1
    adm_plan, adm_rec, adm_fam_id, adm_db = admission_calls[0]
    assert adm_plan is plan
    assert adm_rec.proposal is plan.proposals[0]
    assert adm_fam_id == "canonical-fam-1"
    assert adm_db == "sqlite:///test.db"

    # Stdout check
    doc = json.loads(captured.out)
    assert list(doc.keys()) == ["decision", "admission"]
    assert doc["decision"]["decision"] == "APPROVE"
    assert doc["decision"]["actor"] == "reviewer-alice@example.com"
    assert doc["decision"]["decided_at"] == "2026-09-06T12:00:00+00:00"
    assert doc["decision"]["proposal"] == proposal_doc

    assert doc["admission"]["family_id"] == "canonical-fam-1"
    assert doc["admission"]["member_source_pack_ids"] == [
        m.source_pack_id for m in plan.proposals[0].members
    ]
    assert doc["admission"]["registration_status"] == "INSERTED"


def test_family_decide_offline_reject_no_family_id_and_no_durable_call(monkeypatch, capsys):
    plan = _make_family_plan()

    monkeypatch.setattr(cli, "_intake_product_source_evidence", lambda roots: plan.inventory)
    monkeypatch.setattr(cli, "_plan_family_knowledge_review", lambda inv: plan)

    def forbidden_admit(*args, **kwargs):
        raise AssertionError("durably_admit_planned_family must not be called on REJECT")

    monkeypatch.setattr(cli, "_durably_admit_planned_family", forbidden_admit)
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nREJECT\n"))

    argv = [
        "family-decide",
        "--root",
        "/path/root-a",
        "--database",
        "sqlite:///test.db",
        "--actor",
        "rejector@example.com",
        "--decided-at",
        "2026-09-06T12:00:00+00:00",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert list(doc.keys()) == ["decision", "admission"]
    assert doc["decision"]["decision"] == "REJECT"
    assert doc["decision"]["actor"] == "rejector@example.com"
    assert doc["admission"] is None


def test_family_decide_zero_proposals_shows_preview_and_fails_before_stdin(monkeypatch, capsys):
    plan = _make_zero_proposal_plan()

    monkeypatch.setattr(cli, "_intake_product_source_evidence", lambda roots: plan.inventory)
    monkeypatch.setattr(cli, "_plan_family_knowledge_review", lambda inv: plan)

    def forbidden_decision(*args, **kwargs):
        raise AssertionError("record_planned_family_decision must not be called when zero proposals")

    monkeypatch.setattr(cli, "_record_planned_family_decision", forbidden_decision)
    # Stdin should never be read
    def forbidden_readline():
        raise AssertionError("stdin must not be read when zero proposals")

    monkeypatch.setattr(cli._sys.stdin, "readline", forbidden_readline)

    argv = [
        "family-decide",
        "--root",
        "/path/root-a",
        "--database",
        "sqlite:///test.db",
        "--actor",
        "operator@example.com",
        "--decided-at",
        "2026-09-06T12:00:00+00:00",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    # Preview must still be rendered before error
    lines = captured.err.strip().split("\n")
    # stderr contains preview JSON followed by error JSON
    assert "SINGLETON" in captured.err
    assert "No actionable family merge proposals in review plan" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "stdin_content, expected_error_fragment",
    [
        ("", "Unexpected end of input: missing proposal position"),
        ("abc\n", "Invalid proposal position: 'abc'"),
        ("0\n", "Proposal position out of range: 0"),
        ("2\n", "Proposal position out of range: 2"),
        (" 1\n", "Invalid proposal position: ' 1'"),
        ("1 \n", "Invalid proposal position: '1 '"),
        ("1 extra\n", "Invalid proposal position: '1 extra'"),
        ("1\n", "Unexpected end of input: missing decision token"),
        ("1\nMAYBE\n", "Invalid decision token: 'MAYBE'"),
        ("1\napprove\n", "Invalid decision token: 'approve'"),
        ("1\n APPROVE\n", "Invalid decision token: ' APPROVE'"),
        ("1\nAPPROVE \n", "Invalid decision token: 'APPROVE '"),
        ("1\nAPPROVE now\n", "Invalid decision token: 'APPROVE now'"),
        ("1\nAPPROVE\n", "Unexpected end of input: missing family_id"),
    ],
)
def test_family_decide_input_validation_failures(
    stdin_content, expected_error_fragment, monkeypatch, capsys
):
    plan = _make_family_plan()
    monkeypatch.setattr(cli, "_intake_product_source_evidence", lambda roots: plan.inventory)
    monkeypatch.setattr(cli, "_plan_family_knowledge_review", lambda inv: plan)

    argv = [
        "family-decide",
        "--root",
        "/path/root-a",
        "--database",
        "sqlite:///test.db",
        "--actor",
        "operator@example.com",
        "--decided-at",
        "2026-09-06T12:00:00+00:00",
    ]
    monkeypatch.setattr(cli._sys, "stdin", StringIO(stdin_content))
    exit_code = cli.main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert expected_error_fragment in captured.err
    assert "Traceback" not in captured.err


def test_family_decide_family_id_whitespace_not_trimmed_by_cli(monkeypatch, capsys):
    plan = _make_family_plan()
    monkeypatch.setattr(cli, "_intake_product_source_evidence", lambda roots: plan.inventory)
    monkeypatch.setattr(cli, "_plan_family_knowledge_review", lambda inv: plan)

    received_family_id = None
    orig_durably_admit = cli._durably_admit_planned_family

    def inspect_admit(p, record, *, family_id, database_path):
        nonlocal received_family_id
        received_family_id = family_id
        return orig_durably_admit(p, record, family_id=family_id, database_path=database_path)

    monkeypatch.setattr(cli, "_durably_admit_planned_family", inspect_admit)
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\n  has-spaces  \n"))

    argv = [
        "family-decide",
        "--root",
        "/path/root-a",
        "--database",
        "sqlite:///test.db",
        "--actor",
        "operator@example.com",
        "--decided-at",
        "2026-09-06T12:00:00+00:00",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 1
    # Check that CLI forwarded untrimmed string
    assert received_family_id == "  has-spaces  "

    captured = capsys.readouterr()
    assert captured.out == ""
    docs = _decode_json_documents(captured.err)
    assert len(docs) == 2
    err_doc = docs[1]
    assert err_doc["error"]["type"] == "CanonicalFamilyAdmissionError"
    assert "whitespace" in err_doc["error"]["message"]
    assert "Traceback" not in captured.err


def test_family_decide_already_present_registration_status_pass_through(monkeypatch, capsys):
    plan = _make_family_plan()
    monkeypatch.setattr(cli, "_intake_product_source_evidence", lambda roots: plan.inventory)
    monkeypatch.setattr(cli, "_plan_family_knowledge_review", lambda inv: plan)

    def fake_admit(p, record, *, family_id, database_path):
        from src.product_intelligence.canonical_family import create_canonical_family
        from src.product_intelligence.canonical_catalog import (
            CatalogRegistrationResult,
            CatalogRegistrationStatus,
            create_empty_canonical_catalog,
            register_canonical_family,
        )
        fam = create_canonical_family(record, family_id=family_id)
        cat = create_empty_canonical_catalog()
        # Create a result with ALREADY_PRESENT status
        result = CatalogRegistrationResult(catalog=cat, status=CatalogRegistrationStatus.ALREADY_PRESENT)
        return DurableFamilyAdmissionResult(
            decision_record=record,
            family=fam,
            registration=result,
            _lineage=_DURABLE_ADMISSION,
        )

    monkeypatch.setattr(cli, "_durably_admit_planned_family", fake_admit)
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\ncanonical-fam-1\n"))

    argv = [
        "family-decide",
        "--root",
        "/path/root-a",
        "--database",
        "sqlite:///test.db",
        "--actor",
        "operator@example.com",
        "--decided-at",
        "2026-09-06T12:00:00+00:00",
    ]
    exit_code = cli.main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert doc["admission"]["registration_status"] == "ALREADY_PRESENT"


def test_family_decide_upstream_errors_sanitized(monkeypatch, capsys):
    # 1. Intake error
    def fail_intake(roots):
        raise SourceEvidenceIntakeError("Unreadable root directory")

    monkeypatch.setattr(cli, "_intake_product_source_evidence", fail_intake)

    argv = [
        "family-decide",
        "--root",
        "/invalid/root",
        "--database",
        "test.db",
        "--actor",
        "operator",
        "--decided-at",
        "2026-09-06T12:00:00+00:00",
    ]
    assert cli.main(argv) == 1
    captured = capsys.readouterr()
    assert "SourceEvidenceIntakeError" in captured.err
    assert "Unreadable root directory" in captured.err
    assert "Traceback" not in captured.err

    # 2. Planning error
    plan = _make_family_plan()
    monkeypatch.setattr(cli, "_intake_product_source_evidence", lambda roots: plan.inventory)

    def fail_planning(inv):
        raise FamilyKnowledgeReviewPlanningError("Corrupt observation graph")

    monkeypatch.setattr(cli, "_plan_family_knowledge_review", fail_planning)
    assert cli.main(argv) == 1
    captured = capsys.readouterr()
    assert "FamilyKnowledgeReviewPlanningError" in captured.err
    assert "Corrupt observation graph" in captured.err
    assert "Traceback" not in captured.err

    # 3. Timezone-naive datetime fails in TASK-112 decision authority
    monkeypatch.setattr(cli, "_plan_family_knowledge_review", lambda inv: plan)
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\ncanonical-fam-1\n"))
    argv_naive = [
        "family-decide",
        "--root",
        "/path/root",
        "--database",
        "test.db",
        "--actor",
        "operator",
        "--decided-at",
        "2026-09-06T12:00:00",  # Naive ISO datetime
    ]
    assert cli.main(argv_naive) == 1
    captured = capsys.readouterr()
    assert "FamilyMergeApprovalError" in captured.err
    assert "timezone-aware" in captured.err
    assert "Traceback" not in captured.err

    # 4. Storage error on non-existent database during durable admission
    monkeypatch.setattr(cli._sys, "stdin", StringIO("1\nAPPROVE\ncanonical-fam-1\n"))
    argv_nonexistent_db = [
        "family-decide",
        "--root",
        "/path/root",
        "--database",
        "/nonexistent/directory/database.sqlite3",
        "--actor",
        "operator",
        "--decided-at",
        "2026-09-06T12:00:00+00:00",
    ]
    assert cli.main(argv_nonexistent_db) == 1
    captured = capsys.readouterr()
    assert "CanonicalCatalogStorageError" in captured.err
    assert "Traceback" not in captured.err


def test_family_decide_real_approve_durable_registration_and_reopen_regression(tmp_path, capsys):
    # Persist real source packs in tmp_path
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    facts = (
        ProductFact("Brand", "Acme", "specifications", "structured"),
        ProductFact("Model", "Phone X", "specifications", "structured"),
        ProductFact("Color", "Black", "specifications", "structured"),
    )
    pack1 = ProductSourcePack(
        source_pack_id="pack-shopee-real",
        platform="shopee",
        product_url="https://shopee.example/real-item",
        source_product_id="real-shopee-123",
        observed_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
        collector="test-collector",
        facts=facts,
    )
    pack2 = ProductSourcePack(
        source_pack_id="pack-tiktok-real",
        platform="tiktok",
        product_url="https://tiktok.example/real-item",
        source_product_id="real-tiktok-456",
        observed_at=datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
        collector="test-collector",
        facts=facts,
    )
    serialize_source_pack(pack1, str(evidence_root / "dir1"))
    serialize_source_pack(pack2, str(evidence_root / "dir2"))

    # Create pre-existing canonical SQLite catalog via TASK-120 authority
    db_path = str(tmp_path / "catalog.sqlite3")
    create_sqlite_canonical_catalog(db_path)

    # Provide stdin for APPROVE with explicit family_id
    import sys
    orig_stdin = sys.stdin
    sys.stdin = StringIO("1\nAPPROVE\ncanonical-family-real-1\n")
    try:
        argv = [
            "family-decide",
            "--root",
            str(evidence_root),
            "--database",
            db_path,
            "--actor",
            "real-human-operator@example.com",
            "--decided-at",
            "2026-09-06T14:30:00+00:00",
        ]
        exit_code = cli.main(argv)
        assert exit_code == 0
    finally:
        sys.stdin = orig_stdin

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert doc["decision"]["decision"] == "APPROVE"
    assert doc["decision"]["actor"] == "real-human-operator@example.com"
    assert doc["decision"]["decided_at"] == "2026-09-06T14:30:00+00:00"
    assert doc["admission"]["family_id"] == "canonical-family-real-1"
    assert doc["admission"]["member_source_pack_ids"] == ["pack-shopee-real", "pack-tiktok-real"]
    assert doc["admission"]["registration_status"] == "INSERTED"

    # Reopen the SQLite catalog to verify durable persistence and preserved lineage
    reopened = load_sqlite_canonical_catalog(db_path)
    assert len(reopened.families) == 1
    saved_family = reopened.families[0]
    assert saved_family.family_id == "canonical-family-real-1"
    assert saved_family.approval.actor == "real-human-operator@example.com"
    assert saved_family.approval.decision == FamilyMergeDecision.APPROVE
    assert saved_family.approval.decided_at == datetime(2026, 9, 6, 14, 30, tzinfo=timezone.utc)
    assert tuple(m.source_pack_id for m in saved_family.members) == ("pack-shopee-real", "pack-tiktok-real")


def test_family_decide_real_reject_no_write_regression(tmp_path, capsys):
    # Persist real source packs in tmp_path
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    facts = (
        ProductFact("Brand", "Acme", "specifications", "structured"),
        ProductFact("Model", "Phone X", "specifications", "structured"),
        ProductFact("Color", "Black", "specifications", "structured"),
    )
    pack1 = ProductSourcePack(
        source_pack_id="pack-shopee-reject",
        platform="shopee",
        product_url="https://shopee.example/reject-item",
        source_product_id="reject-shopee-123",
        observed_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
        collector="test-collector",
        facts=facts,
    )
    pack2 = ProductSourcePack(
        source_pack_id="pack-tiktok-reject",
        platform="tiktok",
        product_url="https://tiktok.example/reject-item",
        source_product_id="reject-tiktok-456",
        observed_at=datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
        collector="test-collector",
        facts=facts,
    )
    serialize_source_pack(pack1, str(evidence_root / "dir1"))
    serialize_source_pack(pack2, str(evidence_root / "dir2"))

    # Create pre-existing canonical SQLite catalog via TASK-120 authority
    db_path = str(tmp_path / "catalog.sqlite3")
    create_sqlite_canonical_catalog(db_path)
    bytes_before = Path(db_path).read_bytes()

    # Provide stdin for REJECT (no family_id line)
    import sys
    orig_stdin = sys.stdin
    sys.stdin = StringIO("1\nREJECT\n")
    try:
        argv = [
            "family-decide",
            "--root",
            str(evidence_root),
            "--database",
            db_path,
            "--actor",
            "real-human-rejector@example.com",
            "--decided-at",
            "2026-09-06T15:00:00+00:00",
        ]
        exit_code = cli.main(argv)
        assert exit_code == 0
    finally:
        sys.stdin = orig_stdin

    captured = capsys.readouterr()
    doc = json.loads(captured.out)
    assert doc["decision"]["decision"] == "REJECT"
    assert doc["decision"]["actor"] == "real-human-rejector@example.com"
    assert doc["admission"] is None

    # Prove database bytes are identical and reopened catalog has 0 families
    bytes_after = Path(db_path).read_bytes()
    assert bytes_after == bytes_before
    reopened = load_sqlite_canonical_catalog(db_path)
    assert len(reopened.families) == 0


def test_family_decide_source_has_no_direct_task_109_111_112_114_118_119_120_semantic_authority():
    source = Path(cli.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    forbidden_semantic_functions = {
        "resolve_product_entities",
        "resolve_multi_observations",
        "group_resolution_graph",
        "create_family_merge_proposal",
        "create_canonical_family",
        "register_canonical_family",
        "create_empty_canonical_catalog",
        "create_sqlite_canonical_catalog",
        "register_sqlite_canonical_family",
    }
    assert imported_names.isdisjoint(forbidden_semantic_functions)
    assert "sqlite3" not in source
