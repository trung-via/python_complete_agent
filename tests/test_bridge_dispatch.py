"""Focused Bridge tests for M10.2 read-only recommendation surfaces."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.dispatch import CapacityClass, CapacityState, DispatchActorKind
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionCapability, ExecutionOperation
from src.aios_bridge.runtime_dispatch import (
    ExecutorDispatchPolicySpec,
    ExecutorPolicyCandidateSpec,
    RuntimeCapacityRecord,
)


TASK_ID = 38
BLOB = "a" * 40
NOW = 1_700_000_000
REQUIRED = (
    ExecutionCapability.REPOSITORY_READ,
    ExecutionCapability.FILESYSTEM_WRITE,
    ExecutionCapability.SHELL,
    ExecutionCapability.TEST_EXECUTION,
    ExecutionCapability.LOCAL_GIT,
)


def _candidate(
    actor_id: str,
    *,
    preference: int,
    capacity_class: CapacityClass = CapacityClass.SUBSCRIPTION,
) -> ExecutorPolicyCandidateSpec:
    return ExecutorPolicyCandidateSpec(
        executor_id=actor_id,
        supported_operations=(ExecutionOperation.FIX, ExecutionOperation.RUN),
        supported_capabilities=REQUIRED,
        capacity_class=capacity_class,
        preference_rank=preference,
    )


def _policy(
    operation: ExecutionOperation = ExecutionOperation.RUN,
    *,
    candidates=None,
    allow_paid_api: bool = False,
) -> ExecutorDispatchPolicySpec:
    return ExecutorDispatchPolicySpec(
        operation=operation,
        required_capabilities=REQUIRED,
        candidates=tuple(
            candidates
            or (
                _candidate("antigravity", preference=0),
                _candidate("codex", preference=1),
            )
        ),
        allow_paid_api=allow_paid_api,
    )


def _content(policy=None, *, review_status=None) -> str:
    prefix = f"STATUS: {review_status}\n" if review_status else ""
    return prefix + "DISPATCH_EXECUTOR_POLICY_JSON: " + (policy or _policy()).to_canonical_json() + "\n"


@pytest.fixture
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    runtime = tmp_path / "runtime"
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(bridge, "PROJECT", worktree)
    monkeypatch.setattr(bridge.time, "time", lambda: NOW)
    return runtime, worktree


def _record(actor_id: str, state: CapacityState, observed: int = NOW, ttl: int = 3600):
    return RuntimeCapacityRecord(
        actor_kind=DispatchActorKind.EXECUTOR,
        actor_id=actor_id,
        capacity_state=state,
        observed_at_epoch_seconds=observed,
        ttl_seconds=ttl,
    )


def test_capacity_set_writes_outside_worktree_without_auth_lease_or_state(isolated, capsys):
    runtime, worktree = isolated
    bridge.cmd_capacity_set(
        SimpleNamespace(
            kind="executor",
            actor="codex",
            state="AVAILABLE",
            ttl_seconds=3600,
            source="HUMAN_DECLARED",
        )
    )
    record_path = runtime / "dispatch" / "capacity" / "EXECUTOR" / "codex.json"
    assert record_path.is_file()
    assert not list(worktree.rglob("*"))
    assert not list((runtime / "auth").glob("*.json"))
    assert not list((runtime / "leases").rglob("*.json"))
    assert not (runtime / "state" / "CURRENT_STATE.json").exists()
    output = capsys.readouterr().out
    assert "AUTHORIZATION_CHANGED: NO" in output
    assert "LEASE_CHANGED: NO" in output


def test_capacity_show_is_read_only_and_missing_is_unknown(isolated, capsys):
    runtime, _ = isolated
    store = bridge.get_runtime_capacity_store()
    store.write(_record("codex", CapacityState.AVAILABLE))
    path = store.record_path(DispatchActorKind.EXECUTOR, "codex")
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    bridge.cmd_capacity_show(SimpleNamespace(kind="executor", actor="codex"))
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    bridge.cmd_capacity_show(SimpleNamespace(kind="executor", actor="missing"))
    output = capsys.readouterr().out
    assert "EFFECTIVE_STATE: UNKNOWN" in output
    assert not list((runtime / "auth").glob("*.json"))
    assert not list((runtime / "leases").rglob("*.json"))


def test_capacity_show_rejects_actor_without_kind(isolated):
    with pytest.raises(SystemExit):
        bridge.cmd_capacity_show(SimpleNamespace(kind=None, actor="codex"))


def test_resolve_run_uses_exact_task_blob_and_double_checks(monkeypatch):
    calls = []
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: calls.append("fetch"))
    monkeypatch.setattr(
        bridge,
        "get_remote_blob_sha",
        lambda cfg, path: calls.append(("blob", path)) or BLOB,
    )
    monkeypatch.setattr(
        bridge,
        "read_remote_file",
        lambda cfg, path: calls.append(("read", path)) or _content(),
    )
    path, blob, content = bridge.resolve_dispatch_control_artifact({}, TASK_ID, "RUN")
    assert path == ".ai/tasks/TASK-038.md"
    assert blob == BLOB
    assert content == _content()
    assert calls.count(("blob", path)) == 2


def test_resolve_fix_requires_exact_changes_required_review(monkeypatch):
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: BLOB)
    monkeypatch.setattr(
        bridge,
        "read_remote_file",
        lambda cfg, path: _content(_policy(ExecutionOperation.FIX), review_status="CHANGES_REQUIRED"),
    )
    path, _, _ = bridge.resolve_dispatch_control_artifact({}, TASK_ID, "FIX")
    assert path == ".ai/reviews/REVIEW-038.md"

    monkeypatch.setattr(
        bridge,
        "read_remote_file",
        lambda cfg, path: _content(_policy(ExecutionOperation.FIX), review_status="APPROVED"),
    )
    with pytest.raises(ContinuityStateValidationError, match="CHANGES_REQUIRED"):
        bridge.resolve_dispatch_control_artifact({}, TASK_ID, "FIX")


def test_resolve_control_artifact_drift_fails_closed(monkeypatch):
    blobs = iter((BLOB, "b" * 40))
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: next(blobs))
    monkeypatch.setattr(bridge, "read_remote_file", lambda cfg, path: _content())
    with pytest.raises(ContinuityStateValidationError, match="drifted"):
        bridge.resolve_dispatch_control_artifact({}, TASK_ID, "RUN")


def _recommend_seams(monkeypatch, content):
    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        bridge,
        "load_config",
        lambda: {"remote": "origin", "control_branch": "ai-control"},
    )
    monkeypatch.setattr(
        bridge,
        "resolve_dispatch_control_artifact",
        lambda cfg, task_id, action: (".ai/tasks/TASK-038.md", BLOB, content),
    )
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: BLOB)


def test_operational_recommendation_selects_codex_and_never_mutates_authority(
    isolated, monkeypatch, capsys
):
    runtime, _ = isolated
    _recommend_seams(monkeypatch, _content())
    store = bridge.get_runtime_capacity_store()
    store.write(_record("antigravity", CapacityState.QUOTA_EXHAUSTED))
    store.write(_record("codex", CapacityState.AVAILABLE))
    forbidden_calls = []
    monkeypatch.setattr(bridge, "save_authorization", lambda *args: forbidden_calls.append("authorization"))
    monkeypatch.setattr(bridge, "get_lease_store", lambda: forbidden_calls.append("lease"))
    monkeypatch.setattr(bridge, "cmd_approve", lambda *args: forbidden_calls.append("approve"))
    monkeypatch.setattr(bridge, "cmd_handoff", lambda *args: forbidden_calls.append("handoff"))
    monkeypatch.setattr(bridge, "cmd_publish", lambda *args: forbidden_calls.append("publish"))
    monkeypatch.setattr(bridge, "run", lambda *args, **kwargs: forbidden_calls.append("run"))

    bridge.cmd_recommend(SimpleNamespace(task_id=TASK_ID, kind="executor", action="RUN"))
    output = capsys.readouterr().out
    assert "STATUS: SELECTED" in output
    assert "SELECTED_EXECUTOR: codex" in output
    assert "HUMAN_APPROVAL_REQUIRED: YES" in output
    assert "AUTHORIZATION_CHANGED: NO" in output
    assert "LEASE_CHANGED: NO" in output
    assert not forbidden_calls
    assert not list((runtime / "auth").glob("*.json"))
    assert not list((runtime / "leases").rglob("*.json"))


def test_recommend_calls_m10_1_dispatch_exactly_once(isolated, monkeypatch):
    _recommend_seams(monkeypatch, _content())
    store = bridge.get_runtime_capacity_store()
    store.write(_record("antigravity", CapacityState.QUOTA_EXHAUSTED))
    store.write(_record("codex", CapacityState.AVAILABLE))
    original = bridge.dispatch_executor
    calls = []

    def wrapped(request):
        calls.append(request)
        return original(request)

    monkeypatch.setattr(bridge, "dispatch_executor", wrapped)
    bridge.cmd_recommend(SimpleNamespace(task_id=TASK_ID, kind="executor", action="RUN"))
    assert len(calls) == 1


@pytest.mark.parametrize(
    "content",
    [
        "no marker",
        "DISPATCH_EXECUTOR_POLICY_JSON: {}",
        _content() + _content(),
    ],
)
def test_recommend_rejects_zero_malformed_or_multiple_markers(isolated, monkeypatch, content):
    _recommend_seams(monkeypatch, content)
    with pytest.raises(SystemExit):
        bridge.cmd_recommend(SimpleNamespace(task_id=TASK_ID, kind="executor", action="RUN"))


def test_recommend_rejects_policy_operation_action_mismatch(isolated, monkeypatch):
    _recommend_seams(monkeypatch, _content(_policy(ExecutionOperation.FIX)))
    with pytest.raises(SystemExit):
        bridge.cmd_recommend(SimpleNamespace(task_id=TASK_ID, kind="executor", action="RUN"))


def test_recommend_rechecks_remote_blob_after_dispatch(isolated, monkeypatch):
    _recommend_seams(monkeypatch, _content())
    store = bridge.get_runtime_capacity_store()
    store.write(_record("antigravity", CapacityState.QUOTA_EXHAUSTED))
    store.write(_record("codex", CapacityState.AVAILABLE))
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: "b" * 40)
    with pytest.raises(SystemExit):
        bridge.cmd_recommend(SimpleNamespace(task_id=TASK_ID, kind="executor", action="RUN"))


@pytest.mark.parametrize("mode", ["missing", "expired"])
def test_missing_or_expired_capacity_becomes_unknown_wait(isolated, monkeypatch, capsys, mode):
    _recommend_seams(monkeypatch, _content())
    if mode == "expired":
        store = bridge.get_runtime_capacity_store()
        store.write(_record("antigravity", CapacityState.AVAILABLE, observed=NOW - 11, ttl=10))
        store.write(_record("codex", CapacityState.AVAILABLE, observed=NOW - 11, ttl=10))
    bridge.cmd_recommend(SimpleNamespace(task_id=TASK_ID, kind="executor", action="RUN"))
    output = capsys.readouterr().out
    assert "STATUS: WAIT" in output
    assert "SELECTED_EXECUTOR: NONE" in output
    assert '"effective_state":"UNKNOWN"' in output


def test_forbidden_paid_api_does_not_bypass_wait(isolated, monkeypatch, capsys):
    policy = _policy(
        candidates=(
            _candidate("subscription", preference=0),
            _candidate("paid", preference=0, capacity_class=CapacityClass.PAID_API),
        ),
        allow_paid_api=False,
    )
    _recommend_seams(monkeypatch, _content(policy))
    store = bridge.get_runtime_capacity_store()
    store.write(_record("subscription", CapacityState.QUOTA_EXHAUSTED))
    store.write(_record("paid", CapacityState.AVAILABLE))
    bridge.cmd_recommend(SimpleNamespace(task_id=TASK_ID, kind="executor", action="RUN"))
    output = capsys.readouterr().out
    assert "STATUS: WAIT" in output
    assert "SELECTED_EXECUTOR: NONE" in output


def test_existing_executor_validation_and_approve_parser_defaults_remain_unchanged():
    assert bridge.validate_runtime_executor_id(None) == "antigravity"
    assert bridge.validate_runtime_executor_id("codex") == "codex"
    parsed = bridge.build_parser().parse_args(["approve", "38", "--kind", "task"])
    assert parsed.executor is None


def test_capacity_and_recommend_parser_contracts():
    parser = bridge.build_parser()
    capacity = parser.parse_args(
        [
            "capacity-set",
            "--kind",
            "executor",
            "--actor",
            "codex",
            "--state",
            "AVAILABLE",
            "--ttl-seconds",
            "3600",
        ]
    )
    assert capacity.source == "HUMAN_DECLARED"
    recommendation = parser.parse_args(
        ["recommend", "38", "--kind", "executor", "--action", "RUN"]
    )
    assert recommendation.func is bridge.cmd_recommend
