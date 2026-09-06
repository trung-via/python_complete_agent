"""TASK-145 regressions for the read-only Product Intelligence CLI."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import importlib
from io import StringIO
import json
from pathlib import Path
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
from src.product_intelligence.source_evidence_intake import SourceEvidenceInventory
from src.product_source.models import ProductSourcePack


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
