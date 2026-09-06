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
from src.product_intelligence.grounded_answer import GroundedAnswerStatus
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
    import src.product_intelligence.canonical_catalog_sqlite as catalog_sqlite
    import src.product_intelligence.persistent_grounded_qa as persistent_qa
    import src.product_intelligence.source_evidence_intake as evidence_intake
    import src.providers.gemini as gemini

    forbidden = lambda *args, **kwargs: pytest.fail("import performed application work")
    with monkeypatch.context() as scoped:
        scoped.setattr(evidence_intake, "intake_product_source_evidence", forbidden)
        scoped.setattr(catalog_sqlite, "load_sqlite_canonical_catalog", forbidden)
        scoped.setattr(persistent_qa, "answer_persisted_grounded_question", forbidden)
        scoped.setattr(gemini, "GeminiProvider", forbidden)
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
    assert tuple(subparsers.choices) == ("evidence", "catalog", "ask")
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
    }

    invalid = (
        [],
        ["unknown"],
        ["evidence"],
        ["catalog"],
        ["ask", "--database", "db", "--root", "root", "--question", "q"],
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


def test_cli_source_has_no_mutation_discovery_or_direct_provider_authority():
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
        "src.product_intelligence.discovery",
        "src.product_intelligence.ranking",
        "src.product_source.serialization",
    }
    assert imported_modules.isdisjoint(forbidden_modules)
    assert "register_sqlite" not in source
    assert "enqueue" not in source
    assert ".generate(" not in source
    assert "google.genai" not in source
    assert "AgentController" not in source
