"""Focused adversarial tests for the TASK-035 Bridge hot-handoff lifecycle."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.executor import ExecutionOperation
from src.aios_bridge.continuity.state import ContinuityStateValidationError


TASK_ID = 35
TASK = "TASK-035"
BRANCH = "ai/task-035"
WORKSPACE = "1" * 64
ARTIFACT = ".ai/tasks/TASK-035.md"
BLOB = "a" * 40
CHECKPOINT_FP = "b" * 64


class FakeStore:
    def __init__(self, active=None):
        self.active = active
        self.acquired = []
        self.released = []

    def load_active(self, task_id):
        assert task_id == TASK
        return self.active

    def require_active(self, lease):
        if self.active != lease:
            raise ContinuityStateValidationError("active lease mismatch")
        return self.active

    def acquire(self, lease):
        if self.active is not None:
            raise ContinuityStateValidationError("lease collision")
        self.active = lease
        self.acquired.append(lease)
        return lease

    def release(self, lease):
        if self.active != lease:
            raise ContinuityStateValidationError("compare-and-release mismatch")
        self.active = None
        self.released.append(lease)


def _lease(executor: str = "codex"):
    return bridge.build_executor_lease_candidate(
        task_id=TASK,
        workspace_id=WORKSPACE,
        operation=ExecutionOperation.RUN,
        target_branch=BRANCH,
        authorized_artifact_path=ARTIFACT,
        authorized_artifact_blob_sha=BLOB,
        executor_id=executor,
        lease_id=f"lease-task-035-{executor.replace('-', '')}123",
    )


def _active_auth(source=None):
    source = source or _lease()
    return {
        "task_id": TASK,
        "action": "RUN",
        "kind": "TASK",
        "artifact_path": ARTIFACT,
        "artifact_blob_sha": BLOB,
        "approved_at": "2026-08-18T10:00:00+07:00",
        "branch": BRANCH,
        "status": "ACTIVE",
        "executor_id": source.executor_id,
        "lease_id": source.lease_id,
        "lease_fingerprint": source.fingerprint(),
        "workspace_id": WORKSPACE,
        "execution_fingerprint": source.execution_fingerprint,
    }


def _metadata(source=None):
    source = source or _lease()
    return {
        "checkpoint_fingerprint": CHECKPOINT_FP,
        "allowed_paths": ["work.txt"],
        "source_executor_id": source.executor_id,
        "source_lease_id": source.lease_id,
        "source_lease_fingerprint": source.fingerprint(),
        "source_execution_fingerprint": source.execution_fingerprint,
        "authorized_artifact_path": ARTIFACT,
        "authorized_artifact_blob_sha": BLOB,
        "prepared_at": "2026-08-18T10:01:00+07:00",
    }


def _prepared_auth(source=None):
    source = source or _lease()
    auth = _active_auth(source)
    auth["status"] = "HANDOFF_PREPARED"
    auth["hot_handoff"] = _metadata(source)
    return auth


def _checkpoint(source=None):
    source = source or _lease()
    return SimpleNamespace(
        checkpoint_fingerprint=CHECKPOINT_FP,
        task_id=TASK,
        target_branch=BRANCH,
        workspace_id=WORKSPACE,
        source_executor_id=source.executor_id,
        source_lease_fingerprint=source.fingerprint(),
        source_execution_fingerprint=source.execution_fingerprint,
        allowed_paths=("work.txt",),
    )


def _base(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(
        bridge,
        "load_config",
        lambda: {"task_branch_prefix": "ai/task-", "remote": "origin", "control_branch": "ai-control"},
    )
    monkeypatch.setattr(bridge, "current_branch", lambda: BRANCH)
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: WORKSPACE)
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: BLOB)
    monkeypatch.setattr(
        bridge,
        "read_remote_file",
        lambda cfg, path: 'HOT_HANDOFF_ALLOWED_PATHS_JSON: ["work.txt"]\n',
    )
    monkeypatch.setattr(bridge, "changed_files", lambda: ["work.txt"])


@pytest.mark.parametrize(
    "content",
    [
        "no marker\n",
        "HOT_HANDOFF_ALLOWED_PATHS_JSON: [\"a\"]\nHOT_HANDOFF_ALLOWED_PATHS_JSON: [\"b\"]",
        "HOT_HANDOFF_ALLOWED_PATHS_JSON: not-json",
        "HOT_HANDOFF_ALLOWED_PATHS_JSON: {}",
        "HOT_HANDOFF_ALLOWED_PATHS_JSON: []",
        "HOT_HANDOFF_ALLOWED_PATHS_JSON: [1]",
        "HOT_HANDOFF_ALLOWED_PATHS_JSON: [\"a\", \"a\"]",
        " HOT_HANDOFF_ALLOWED_PATHS_JSON: [\"a\"]",
    ],
)
def test_scope_marker_rejects_missing_duplicate_malformed_empty_and_duplicate_items(content):
    with pytest.raises(ContinuityStateValidationError):
        bridge.parse_hot_handoff_allowed_paths(content)


def test_scope_marker_returns_exact_unwidened_tuple():
    assert bridge.parse_hot_handoff_allowed_paths(
        'text\nHOT_HANDOFF_ALLOWED_PATHS_JSON: ["src/a.py", "tests/a.py"]\n'
    ) == ("src/a.py", "tests/a.py")


def test_prepare_requires_explicit_quiescent_confirmation(monkeypatch):
    _base(monkeypatch)
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: pytest.fail("must not load auth"))
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_prepare(SimpleNamespace(task_id=TASK_ID, confirm_quiescent=False))


def test_prepare_requires_active_authorization(monkeypatch):
    _base(monkeypatch)
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: None)
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_prepare(SimpleNamespace(task_id=TASK_ID, confirm_quiescent=True))


def test_prepare_requires_exact_source_lease(monkeypatch):
    _base(monkeypatch)
    source = _lease()
    auth = _active_auth(source)
    store = FakeStore(active=_lease("antigravity"))
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: auth)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_prepare(SimpleNamespace(task_id=TASK_ID, confirm_quiescent=True))
    assert store.active.executor_id == "antigravity"


def test_prepare_control_blob_drift_leaves_source_active(monkeypatch):
    _base(monkeypatch)
    source = _lease()
    auth = _active_auth(source)
    store = FakeStore(active=source)
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: auth)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: "c" * 40)
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_prepare(SimpleNamespace(task_id=TASK_ID, confirm_quiescent=True))
    assert store.active == source


def test_prepare_rejects_protected_dirty_control_plane_path(monkeypatch):
    _base(monkeypatch)
    source = _lease()
    auth = _active_auth(source)
    store = FakeStore(active=source)
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: auth)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "changed_files", lambda: ["bridge.py"])
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_prepare(SimpleNamespace(task_id=TASK_ID, confirm_quiescent=True))
    assert store.active == source


@pytest.mark.parametrize("failure_seam", ["capture", "verify"])
def test_pre_release_checkpoint_failure_preserves_source_authority(monkeypatch, failure_seam):
    _base(monkeypatch)
    source = _lease()
    auth = _active_auth(source)
    store = FakeStore(active=source)
    saved = []
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: auth)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "save_authorization", lambda *args: saved.append(args))
    if failure_seam == "capture":
        monkeypatch.setattr(
            bridge, "capture_hot_handoff_checkpoint", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("capture"))
        )
    else:
        monkeypatch.setattr(bridge, "capture_hot_handoff_checkpoint", lambda *args, **kwargs: _checkpoint(source))
        monkeypatch.setattr(
            bridge, "verify_hot_handoff_checkpoint", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("verify"))
        )
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_prepare(SimpleNamespace(task_id=TASK_ID, confirm_quiescent=True))
    assert store.active == source
    assert not store.released
    assert not saved


def test_successful_prepare_releases_source_and_persists_prepared(monkeypatch):
    _base(monkeypatch)
    source = _lease()
    auth = _active_auth(source)
    store = FakeStore(active=source)
    saved = {}
    states = []
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: auth)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "capture_hot_handoff_checkpoint", lambda *args, **kwargs: _checkpoint(source))
    monkeypatch.setattr(bridge, "verify_hot_handoff_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr(bridge, "save_authorization", lambda task_id, value: saved.update({task_id: value}))
    monkeypatch.setattr(bridge, "update_state", lambda *args: states.append(args))

    bridge.cmd_hot_handoff_prepare(SimpleNamespace(task_id=TASK_ID, confirm_quiescent=True))
    assert store.active is None
    assert store.released == [source]
    assert saved[TASK_ID]["status"] == "HANDOFF_PREPARED"
    assert saved[TASK_ID]["hot_handoff"]["source_executor_id"] == "codex"
    assert states[-1][1] == "HANDOFF_PREPARED"


def test_post_release_verify_failure_restores_exact_source(monkeypatch):
    _base(monkeypatch)
    source = _lease()
    original = _active_auth(source)
    store = FakeStore(active=source)
    auth_box = {"value": original.copy()}
    verify_calls = {"count": 0}
    states = []
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: auth_box["value"])
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "capture_hot_handoff_checkpoint", lambda *args, **kwargs: _checkpoint(source))

    def verify(*args, **kwargs):
        verify_calls["count"] += 1
        if verify_calls["count"] == 2:
            raise RuntimeError("post-release drift")

    monkeypatch.setattr(bridge, "verify_hot_handoff_checkpoint", verify)
    monkeypatch.setattr(bridge, "save_authorization", lambda task_id, value: auth_box.update(value=value.copy()))
    monkeypatch.setattr(bridge, "load_authorization", lambda task_id: auth_box["value"])
    monkeypatch.setattr(bridge, "update_state", lambda *args: states.append(args))

    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_prepare(SimpleNamespace(task_id=TASK_ID, confirm_quiescent=True))
    assert store.active == source
    assert auth_box["value"] == original
    assert states[-1][1] == "IN_PROGRESS"


def test_activate_parser_requires_explicit_executor_and_checkpoint():
    parser = bridge.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["hot-handoff-activate", "35", "--checkpoint", CHECKPOINT_FP])
    with pytest.raises(SystemExit):
        parser.parse_args(["hot-handoff-activate", "35", "--executor", "antigravity"])


@pytest.mark.parametrize(
    "executor,checkpoint",
    [("codex", CHECKPOINT_FP), ("antigravity", "c" * 64)],
)
def test_activate_rejects_same_source_or_wrong_checkpoint_before_acquire(monkeypatch, executor, checkpoint):
    _base(monkeypatch)
    source = _lease()
    prepared = _prepared_auth(source)
    store = FakeStore()
    monkeypatch.setattr(bridge, "load_authorization", lambda task_id: prepared)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_activate(
            SimpleNamespace(task_id=TASK_ID, executor=executor, checkpoint=checkpoint)
        )
    assert store.active is None
    assert not store.acquired


def _activation_seams(monkeypatch, *, store=None):
    _base(monkeypatch)
    source = _lease()
    prepared = _prepared_auth(source)
    checkpoint = _checkpoint(source)
    store = store or FakeStore()
    auth_box = {"value": prepared.copy()}
    states = []
    monkeypatch.setattr(bridge, "load_authorization", lambda task_id: auth_box["value"])
    monkeypatch.setattr(bridge, "save_authorization", lambda task_id, value: auth_box.update(value=value.copy()))
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(bridge, "load_persisted_hot_handoff_checkpoint", lambda *args: checkpoint)
    monkeypatch.setattr(bridge, "verify_hot_handoff_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr(bridge, "update_state", lambda *args: states.append(args))
    return source, prepared, checkpoint, store, auth_box, states


def test_workspace_drift_before_activation_acquires_no_lease(monkeypatch):
    _, _, _, store, _, _ = _activation_seams(monkeypatch)
    monkeypatch.setattr(
        bridge, "verify_hot_handoff_checkpoint", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("drift"))
    )
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_activate(
            SimpleNamespace(task_id=TASK_ID, executor="antigravity", checkpoint=CHECKPOINT_FP)
        )
    assert store.active is None
    assert not store.acquired


def test_active_lease_collision_blocks_activation(monkeypatch):
    collision = _lease("claude-code")
    _, _, _, store, _, _ = _activation_seams(monkeypatch, store=FakeStore(active=collision))
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_activate(
            SimpleNamespace(task_id=TASK_ID, executor="antigravity", checkpoint=CHECKPOINT_FP)
        )
    assert store.active == collision
    assert not store.acquired


def test_successful_activation_creates_new_lease_and_retains_source_provenance(monkeypatch):
    source, _, _, store, auth_box, states = _activation_seams(monkeypatch)
    bridge.cmd_hot_handoff_activate(
        SimpleNamespace(task_id=TASK_ID, executor="antigravity", checkpoint=CHECKPOINT_FP)
    )
    active = auth_box["value"]
    assert store.active is not None
    assert store.active.executor_id == "antigravity"
    assert store.active.lease_id != source.lease_id
    assert active["status"] == "ACTIVE"
    assert active["executor_id"] == "antigravity"
    assert active["hot_handoff"]["source_executor_id"] == "codex"
    assert active["hot_handoff"]["replacement_lease_id"] == store.active.lease_id
    assert "failover_proof" not in active
    assert states[-1][1] == "IN_PROGRESS"


def test_post_acquire_verify_failure_releases_replacement_and_restores_prepared(monkeypatch):
    _, prepared, _, store, auth_box, states = _activation_seams(monkeypatch)
    calls = {"count": 0}

    def verify(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("post-acquire drift")

    monkeypatch.setattr(bridge, "verify_hot_handoff_checkpoint", verify)
    with pytest.raises(SystemExit):
        bridge.cmd_hot_handoff_activate(
            SimpleNamespace(task_id=TASK_ID, executor="antigravity", checkpoint=CHECKPOINT_FP)
        )
    assert store.active is None
    assert len(store.acquired) == 1
    assert store.released == store.acquired
    assert auth_box["value"] == prepared
    assert states[-1][1] == "HANDOFF_PREPARED"


def test_context_surfaces_nested_hot_handoff(monkeypatch, tmp_path, capsys):
    _base(monkeypatch)
    prepared = _prepared_auth()
    paths = {
        "root": tmp_path / "runtime",
        "state": tmp_path / "runtime" / "state.json",
    }
    monkeypatch.setattr(bridge, "latest_approved", lambda task_id: None)
    monkeypatch.setattr(bridge, "load_authorization", lambda task_id: prepared)
    monkeypatch.setattr(bridge, "get_runtime_paths", lambda: paths)
    monkeypatch.setattr(bridge, "get_artifact_path", lambda path: tmp_path / path.replace("/", "_"))
    monkeypatch.setattr(bridge, "get_lease_store", lambda: FakeStore())
    bridge.cmd_context(SimpleNamespace(task_id=TASK_ID))
    output = json.loads(capsys.readouterr().out)
    assert output["hot_handoff"] == prepared["hot_handoff"]


def test_publish_rejects_partial_hot_handoff_before_tests_or_result(monkeypatch, tmp_path):
    _base(monkeypatch)
    source = _lease("antigravity")
    auth = _active_auth(source)
    auth["executor_id"] = "antigravity"
    auth["lease_id"] = source.lease_id
    auth["lease_fingerprint"] = source.fingerprint()
    auth["execution_fingerprint"] = source.execution_fingerprint
    auth["hot_handoff"] = {"checkpoint_fingerprint": CHECKPOINT_FP}
    store = FakeStore(active=source)
    monkeypatch.setattr(bridge, "AI", tmp_path / ".ai")
    monkeypatch.setattr(bridge, "get_active_authorization", lambda task_id: auth)
    monkeypatch.setattr(bridge, "get_lease_store", lambda: store)
    monkeypatch.setattr(
        bridge,
        "get_remote_blob_sha",
        lambda cfg, path: BLOB if path == ARTIFACT else None,
    )
    monkeypatch.setattr(bridge, "run", lambda *args, **kwargs: pytest.fail("tests must not run"))
    with pytest.raises(SystemExit):
        bridge.cmd_publish(
            SimpleNamespace(
                task_id=TASK_ID,
                action="RUN",
                test="should-not-run",
                summary=None,
                notes=None,
                message=None,
            )
        )
    assert not (tmp_path / ".ai" / "results" / "RESULT-035.md").exists()


def test_ordinary_authorization_has_no_hot_handoff_provenance():
    lease = _lease()
    assert bridge.validate_active_hot_handoff_provenance(TASK_ID, _active_auth(lease), lease) is None
