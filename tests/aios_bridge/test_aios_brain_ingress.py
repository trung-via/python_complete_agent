"""Focused offline checks for the repository-owned pinned Brain ingress carrier."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_DIR = REPO_ROOT / ".agents" / "skills" / "aios-worker" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import aios_brain_ingress as ingress  # noqa: E402
import aios_worker as worker  # noqa: E402


def completed(command=(), *, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def test_ingress_uses_the_same_exact_provenance_authority_as_worker():
    source = (SCRIPT_DIR / "aios_brain_ingress.py").read_text(encoding="utf-8")
    assert worker.AUTHORITATIVE_COMMIT == (
        "f0237a3b98985ce6ebbaf41af1e06fa3eb4e998e"
    )
    assert "aios_renew.operator" in source
    assert "import aios_renew" not in source
    assert "subprocess.run" not in source
    assert "PATH" not in source


def test_human_worker_launcher_does_not_expose_brain_operations():
    worker_source = (SCRIPT_DIR / "aios_worker.py").read_text(encoding="utf-8")
    assert worker.ALLOWED_ACTIONS == ("CONTINUE", "FIX", "REPAIR", "RUN", "STATUS")
    for operation in (
        "AUTHOR_TASK",
        "SUBMIT_REVIEW",
        "AUTHOR_REMEDIATION",
        "AUTHOR_REPAIR",
    ):
        assert operation not in worker_source


def test_ingress_command_is_one_pinned_operator_delegation_with_fixed_repo(tmp_path):
    python = tmp_path / "runtime" / "python"
    envelope = tmp_path / "envelope.json"
    repo = tmp_path / "repo"
    assert ingress.ingress_command(python, envelope=envelope, repo=repo) == (
        str(python),
        "-m",
        "aios_renew.operator",
        "ingress",
        str(envelope),
        "--repo",
        str(repo),
    )


@pytest.mark.parametrize(
    "operation",
    ("AUTHOR_TASK", "SUBMIT_REVIEW", "AUTHOR_REMEDIATION", "AUTHOR_REPAIR"),
)
def test_every_brain_operation_uses_the_same_opaque_pinned_carrier(
    operation, tmp_path, monkeypatch
):
    envelope = tmp_path / f"{operation}.json"
    envelope.write_text(f'{{"operation": "{operation}"}}', encoding="utf-8")
    repo = tmp_path / "repo"
    python = tmp_path / "runtime" / "python"
    monkeypatch.setattr(ingress, "get_repo_root", lambda: repo)
    monkeypatch.setattr(ingress, "runtime_layout", lambda value: MagicMock())
    monkeypatch.setattr(ingress, "ensure_runtime", lambda value: python)
    invoke = MagicMock(return_value=completed())
    monkeypatch.setattr(ingress, "invoke_kernel", invoke)

    assert ingress.main([str(envelope)]) == 0
    invoke.assert_called_once_with(
        ingress.ingress_command(python, envelope=envelope, repo=repo),
        repo=repo,
    )


def test_main_proves_runtime_then_invokes_exactly_once(tmp_path, monkeypatch, capsys):
    envelope = tmp_path / "envelope.json"
    envelope.write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    python = tmp_path / "runtime" / "python"
    layout = MagicMock()
    invoke = MagicMock(return_value=completed(stdout="AIOS INGRESS PASS\n"))

    monkeypatch.setattr(ingress, "get_repo_root", lambda: repo)
    monkeypatch.setattr(ingress, "runtime_layout", lambda value: layout)
    ensure = MagicMock(return_value=python)
    monkeypatch.setattr(ingress, "ensure_runtime", ensure)
    monkeypatch.setattr(ingress, "invoke_kernel", invoke)

    assert ingress.main([str(envelope)]) == 0
    ensure.assert_called_once_with(layout)
    invoke.assert_called_once_with(
        ingress.ingress_command(python, envelope=envelope, repo=repo),
        repo=repo,
    )
    assert capsys.readouterr().out == "AIOS INGRESS PASS\n"


def test_unproven_runtime_fails_before_ingress_mutation(tmp_path, monkeypatch):
    envelope = tmp_path / "envelope.json"
    envelope.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ingress, "get_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ingress, "runtime_layout", lambda value: MagicMock())
    monkeypatch.setattr(
        ingress,
        "ensure_runtime",
        MagicMock(side_effect=worker.BootstrapError("unproven runtime")),
    )
    invoke = MagicMock()
    monkeypatch.setattr(ingress, "invoke_kernel", invoke)

    assert ingress.main([str(envelope)]) == 1
    invoke.assert_not_called()


def test_pinned_ingress_rejection_is_passed_through_without_fallback(
    tmp_path, monkeypatch
):
    envelope = tmp_path / "malformed-existing-destination.json"
    envelope.write_text("{}", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    marker = repo / "unchanged"
    marker.write_text("control", encoding="utf-8")
    python = tmp_path / "runtime" / "python"
    monkeypatch.setattr(ingress, "get_repo_root", lambda: repo)
    monkeypatch.setattr(ingress, "runtime_layout", lambda value: MagicMock())
    monkeypatch.setattr(ingress, "ensure_runtime", lambda value: python)
    invoke = MagicMock(
        return_value=completed(returncode=1, stderr="AIOS ERROR: malformed destination\n")
    )
    monkeypatch.setattr(ingress, "invoke_kernel", invoke)

    assert ingress.main([str(envelope)]) == 1
    invoke.assert_called_once()
    assert marker.read_text(encoding="utf-8") == "control"


def test_caller_cannot_select_repository_or_raw_git_destination(tmp_path, monkeypatch):
    envelope = tmp_path / "envelope.json"
    envelope.write_text("{}", encoding="utf-8")
    bootstrap = MagicMock()
    monkeypatch.setattr(ingress, "ensure_runtime", bootstrap)

    assert ingress.main([str(envelope), "--repo", str(tmp_path)]) == 2
    bootstrap.assert_not_called()
