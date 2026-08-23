from __future__ import annotations

import argparse
import inspect
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.review_merge import MergeGateReason, MergeReceipt


VALID_TASK_SHA = "a" * 40
VALID_MAIN_SHA = "b" * 40
GATE_OUTPUT_RE = re.compile(r"\[MERGE_GATE\] ([A-Z0-9_]+):")


def _make_args(task_id: int = 69) -> argparse.Namespace:
    return argparse.Namespace(
        task_id=task_id,
        remote="origin",
        base_branch="main",
        control_branch="ai-control",
        task_branch_prefix="ai/task-",
    )


def _setup_merge_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    review_status: str = "PASS",
    review_approved: bool = True,
    auto_merge_eligible: bool = True,
    reviewed_task_sha: str = VALID_TASK_SHA,
    reviewed_main_sha: str = VALID_MAIN_SHA,
    current_task_sha: str = VALID_TASK_SHA,
    current_main_sha: str = VALID_MAIN_SHA,
    merge_base_sha: str = VALID_MAIN_SHA,
    behind_by: int = 0,
    ahead_by: int = 1,
    post_main_sha: str | None = None,
    post_task_sha: str | None = None,
    push_fails: bool = False,
    post_fetch_fails: bool = False,
    review_missing: bool = False,
    raw_review_text: str | None = None,
):
    calls: dict[str, list[object]] = {
        "git": [],
        "push_args": [],
    }

    if post_main_sha is None:
        post_main_sha = current_task_sha
    if post_task_sha is None:
        post_task_sha = current_task_sha

    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: {})
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(bridge, "get_runtime_paths", lambda repo_root=None: {"root": runtime_dir})

    if raw_review_text is not None:
        review_text = raw_review_text
    else:
        review_text = f"""
STATUS: {review_status}
APPROVED: {"YES" if review_approved else "NO"}
AUTO_MERGE_ELIGIBLE: {"YES" if auto_merge_eligible else "NO"}
REVIEWED_TASK_HEAD_SHA: {reviewed_task_sha}
REVIEWED_BASE_MAIN_SHA: {reviewed_main_sha}
"""

    has_pushed = False

    def fake_git(*args: str, check: bool = True) -> SimpleNamespace:
        nonlocal has_pushed
        calls["git"].append(list(args))
        op = args[0]
        if op == "fetch":
            if has_pushed and post_fetch_fails:
                return SimpleNamespace(returncode=1, stdout="", stderr="Post fetch failed")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        elif op == "show":
            if review_missing:
                return SimpleNamespace(returncode=1, stdout="", stderr="Not found")
            return SimpleNamespace(returncode=0, stdout=review_text, stderr="")
        elif op == "rev-parse":
            target = args[1]
            if "main" in target:
                sha = post_main_sha if has_pushed else current_main_sha
                return SimpleNamespace(returncode=0, stdout=f"{sha}\n", stderr="")
            else:
                sha = post_task_sha if has_pushed else current_task_sha
                return SimpleNamespace(returncode=0, stdout=f"{sha}\n", stderr="")
        elif op == "merge-base":
            return SimpleNamespace(returncode=0, stdout=f"{merge_base_sha}\n", stderr="")
        elif op == "rev-list":
            return SimpleNamespace(returncode=0, stdout=f"{behind_by}\t{ahead_by}\n", stderr="")
        elif op == "push":
            calls["push_args"].append(list(args))
            if push_fails:
                return SimpleNamespace(returncode=1, stdout="", stderr="Push rejected")
            has_pushed = True
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bridge, "git", fake_git)

    return calls, runtime_dir


def test_merge_reviewed_cli_parser() -> None:
    parser = bridge.build_parser()
    args = parser.parse_args(["merge-reviewed", "69"])
    assert args.func is bridge.cmd_merge_reviewed
    assert args.task_id == 69
    assert args.remote == "origin"
    assert args.base_branch == "main"
    assert args.control_branch == "ai-control"
    assert args.task_branch_prefix == "ai/task-"


def test_merge_reviewed_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls, runtime_dir = _setup_merge_env(monkeypatch, tmp_path)
    receipt = bridge.cmd_merge_reviewed(_make_args(69))

    assert isinstance(receipt, MergeReceipt)
    assert receipt.task_id == "TASK-069"
    assert receipt.gate_reason == "PASS_ELIGIBLE"
    assert receipt.post_merge_identity_verified is True
    assert receipt.force_update is False
    assert receipt.merge_method == "FAST_FORWARD"

    # Verify push command was called exactly once without --force
    assert len(calls["push_args"]) == 1
    push_cmd = calls["push_args"][0]
    assert "--force" not in push_cmd
    assert "-f" not in push_cmd
    assert "--force-with-lease" not in push_cmd
    assert push_cmd == ["push", "origin", f"{VALID_TASK_SHA}:refs/heads/main"]

    # Verify receipt persisted
    receipt_file = runtime_dir / "merge_receipts" / "TASK-069" / f"{VALID_TASK_SHA}.json"
    assert receipt_file.exists()


@pytest.mark.parametrize("block_scenario,expected_reason,kwargs", [
    ("review_missing", MergeGateReason.REVIEW_MISSING, {"review_missing": True}),
    ("review_not_pass", MergeGateReason.REVIEW_NOT_PASS, {"review_status": "CHANGES_REQUIRED"}),
    ("review_not_approved", MergeGateReason.REVIEW_NOT_APPROVED, {"review_approved": False}),
    ("auto_merge_disabled", MergeGateReason.AUTO_MERGE_DISABLED, {"auto_merge_eligible": False}),
    ("task_head_drift", MergeGateReason.TASK_HEAD_DRIFT, {"current_task_sha": "c" * 40}),
    ("main_drift", MergeGateReason.MAIN_DRIFT, {"current_main_sha": "d" * 40}),
    ("branch_behind_main", MergeGateReason.BRANCH_BEHIND_MAIN, {"behind_by": 1}),
    ("merge_base_mismatch", MergeGateReason.NOT_FAST_FORWARD, {"merge_base_sha": "e" * 40}),
    ("no_task_delta", MergeGateReason.NO_TASK_DELTA, {"ahead_by": 0}),
    (
        "alias_conflict",
        MergeGateReason.AUTO_MERGE_DISABLED,
        {
            "raw_review_text": f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nAUTO_MERGE_ALLOWED: NO\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}"
        },
    ),
    (
        "invalid_head_casing",
        MergeGateReason.REVIEW_HEAD_INVALID,
        {
            "raw_review_text": f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA.upper()}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA}"
        },
    ),
    (
        "invalid_base_casing",
        MergeGateReason.REVIEW_BASE_INVALID,
        {
            "raw_review_text": f"STATUS: PASS\nAPPROVED: YES\nAUTO_MERGE_ELIGIBLE: YES\nREVIEWED_TASK_HEAD_SHA: {VALID_TASK_SHA}\nREVIEWED_BASE_MAIN_SHA: {VALID_MAIN_SHA.upper()}"
        },
    ),
])
def test_merge_reviewed_blocks_mutation_with_closed_reasons(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    block_scenario: str,
    expected_reason: MergeGateReason,
    kwargs: dict,
) -> None:
    calls, _ = _setup_merge_env(monkeypatch, tmp_path, **kwargs)
    with pytest.raises(SystemExit) as excinfo:
        bridge.cmd_merge_reviewed(_make_args(69))
    assert excinfo.value.code != 0
    # ZERO push attempts must be made
    assert len(calls["push_args"]) == 0

    out = capsys.readouterr().out
    match = GATE_OUTPUT_RE.search(out)
    assert match is not None, f"Expected [MERGE_GATE] reason prefix in output: {out}"
    reason_code = match.group(1)
    # Closed vocabulary check: every output code must be a valid MergeGateReason
    assert reason_code in set(item.value for item in MergeGateReason)
    assert reason_code == expected_reason.value


def test_merge_reviewed_post_identity_main_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    mismatched_post_sha = "f" * 40
    calls, _ = _setup_merge_env(
        monkeypatch, tmp_path, post_main_sha=mismatched_post_sha
    )
    with pytest.raises(SystemExit) as excinfo:
        bridge.cmd_merge_reviewed(_make_args(69))
    assert excinfo.value.code != 0
    assert len(calls["push_args"]) == 1
    out = capsys.readouterr().out
    assert "[MERGE_GATE] POST_MERGE_IDENTITY_FAILED:" in out


def test_merge_reviewed_post_identity_task_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    drifted_task_sha = "9" * 40
    calls, _ = _setup_merge_env(
        monkeypatch, tmp_path, post_task_sha=drifted_task_sha
    )
    with pytest.raises(SystemExit) as excinfo:
        bridge.cmd_merge_reviewed(_make_args(69))
    assert excinfo.value.code != 0
    assert len(calls["push_args"]) == 1
    out = capsys.readouterr().out
    assert "[MERGE_GATE] POST_MERGE_IDENTITY_FAILED:" in out


def test_merge_reviewed_post_fetch_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    calls, _ = _setup_merge_env(
        monkeypatch, tmp_path, post_fetch_fails=True
    )
    with pytest.raises(SystemExit) as excinfo:
        bridge.cmd_merge_reviewed(_make_args(69))
    assert excinfo.value.code != 0
    assert len(calls["push_args"]) == 1
    out = capsys.readouterr().out
    assert "[MERGE_GATE] POST_MERGE_IDENTITY_FAILED:" in out


def test_merge_reviewed_git_push_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    calls, _ = _setup_merge_env(monkeypatch, tmp_path, push_fails=True)
    with pytest.raises(SystemExit) as excinfo:
        bridge.cmd_merge_reviewed(_make_args(69))
    assert excinfo.value.code != 0
    out = capsys.readouterr().out
    assert "[MERGE_GATE] GIT_OPERATION_FAILED:" in out


def test_worker_surfaces_expose_no_merge_command() -> None:
    # 1. Skill file check
    skill_content = Path(".agents/skills/aios-worker/SKILL.md").read_text(encoding="utf-8")
    assert "$aios-worker MERGE" not in skill_content
    assert "worker executors NEVER merge" in skill_content

    # 2. Workflow file check
    workflow_content = Path(".agents/workflows/aios-worker.md").read_text(encoding="utf-8")
    assert "/aios-worker MERGE" not in workflow_content
    assert "worker executors NEVER merge" in workflow_content

    # 3. Docs check
    docs_content = Path("docs/AIOS_UNIFIED_WORKER_WORKFLOW.md").read_text(encoding="utf-8")
    assert "Worker executors **NEVER** merge" in docs_content


def test_bridge_cmd_merge_reviewed_has_no_full_test_or_provider_calls() -> None:
    source = inspect.getsource(bridge.cmd_merge_reviewed)
    assert "cmd_publish" not in source
    assert "pytest" not in source
    assert "minimax" not in source.lower()
    assert "provider" not in source.lower()
    assert "brain" not in source.lower()
