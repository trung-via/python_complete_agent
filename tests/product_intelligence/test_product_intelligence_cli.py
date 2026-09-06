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

from src.core.errors import AgentException
from src.product_intelligence import cli
from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
from src.product_intelligence.adapters.tiktok import TikTokDiscoveryAdapter
from src.product_intelligence.discovery import (
    DiscoveryBlockedError,
    DiscoveryError,
    DiscoveryInvalidRequestError,
    DiscoveryNavigationError,
    DiscoveryRequest,
)
from src.product_intelligence.grounded_answer import GroundedAnswerStatus
from src.product_intelligence.orchestration import (
    OrchestrationError,
    OrchestrationInvalidRequestError,
    OrchestrationResult,
    PlatformDiscoveryPlan,
)
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
    assert tuple(subparsers.choices) == ("evidence", "catalog", "ask", "discover")
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
        "src.product_intelligence.approval",
        "src.product_intelligence.ranking",
        "src.product_source.serialization",
        "playwright",
        "playwright.async_api",
        "playwright.sync_api",
    }
    assert imported_modules.isdisjoint(forbidden_modules)
    assert "register_sqlite" not in source
    assert "enqueue" not in source
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
