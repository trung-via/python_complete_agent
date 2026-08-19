"""Focused Bridge tests for TASK-052 Human paid API grant commands."""
from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.dispatch import DispatchActorKind
from src.aios_bridge.continuity.state import BrainOperation, ContinuityStateValidationError
from src.aios_bridge.paid_api_grant import PaidApiGrant


TASK_NUMBER = 52
TASK_ID = "TASK-052"
BLOB_SHA = "a" * 40
NOW = 1_700_000_000
TOKEN_HEX = "b" * 24


@pytest.fixture
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    runtime = tmp_path / "runtime"
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(bridge, "PROJECT", worktree)
    return runtime, worktree


def _args(**overrides):
    values = {
        "task_id": TASK_NUMBER,
        "brain_id": "minimax-brain",
        "provider_id": "minimax",
        "model_id": "MiniMax-M3",
        "operation": BrainOperation.PLAN.value,
        "artifact_path": ".ai/tasks/TASK-052.md",
        "max_input_tokens": 12_000,
        "max_output_tokens": 4_000,
        "ttl_seconds": 600,
        "confirm_paid_api_spend": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _mock_create_control(monkeypatch: pytest.MonkeyPatch, calls: list | None = None):
    calls = calls if calls is not None else []
    monkeypatch.setattr(bridge, "ensure_git", lambda: calls.append("ensure_git"))
    monkeypatch.setattr(
        bridge,
        "load_config",
        lambda: {"remote": "origin", "control_branch": "ai-control"},
    )
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: calls.append(("fetch", cfg)))
    monkeypatch.setattr(
        bridge,
        "resolve_git_blob_sha",
        lambda ref, path: calls.append(("resolve", ref, path)) or BLOB_SHA,
    )
    return calls


def _grant(
    workspace_id: str,
    *,
    grant_id: str = f"grant-task-052-{TOKEN_HEX}",
    expires_at: int = NOW + 60,
) -> PaidApiGrant:
    return PaidApiGrant(
        schema_version="1",
        grant_id=grant_id,
        task_id=TASK_ID,
        actor_kind=DispatchActorKind.BRAIN,
        brain_id="minimax-brain",
        provider_id="minimax",
        model_id="MiniMax-M3",
        brain_operation=BrainOperation.PLAN,
        authorized_artifact_path=".ai/tasks/TASK-052.md",
        authorized_artifact_blob_sha=BLOB_SHA,
        max_input_tokens=12_000,
        max_output_tokens=4_000,
        max_calls=1,
        expires_at_epoch_seconds=expires_at,
        workspace_id=workspace_id,
    )


def _runtime_snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_runtime_path_is_external_and_store_binds_current_workspace(isolated):
    runtime, worktree = isolated
    paths = bridge.get_runtime_paths()
    assert paths["paid_api_grants"] == runtime / "paid_api_grants"
    bridge.ensure_dirs()
    assert paths["paid_api_grants"].is_dir()
    assert not paths["paid_api_grants"].is_relative_to(worktree)

    store = bridge.get_paid_api_grant_store()
    assert store.grant_root == paths["paid_api_grants"].resolve()
    assert store.workspace_id == bridge.get_workspace_id()


def test_confirmation_gate_fails_before_any_runtime_or_control_side_effect(
    isolated, monkeypatch
):
    runtime, _ = isolated
    forbidden = []
    for name in ("ensure_git", "ensure_dirs", "load_config", "fetch_control"):
        monkeypatch.setattr(bridge, name, lambda *args, _name=name: forbidden.append(_name))
    monkeypatch.setattr(
        bridge,
        "get_paid_api_grant_store",
        lambda: forbidden.append("store"),
    )

    with pytest.raises(SystemExit):
        bridge.cmd_paid_grant_create(_args(confirm_paid_api_spend=False))

    assert forbidden == []
    assert not runtime.exists()


@pytest.mark.parametrize("ttl_seconds", [0, 901, True, 1.5])
def test_invalid_ttl_fails_before_activation(isolated, monkeypatch, ttl_seconds):
    forbidden = []
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: forbidden.append("dirs"))
    monkeypatch.setattr(
        bridge,
        "get_paid_api_grant_store",
        lambda: forbidden.append("store"),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_paid_grant_create(_args(ttl_seconds=ttl_seconds))
    assert forbidden == []


@pytest.mark.parametrize("ttl_seconds", [1, 900])
def test_ttl_boundaries_and_exact_grant_binding(
    isolated, monkeypatch, capsys, ttl_seconds
):
    runtime, worktree = isolated
    calls = _mock_create_control(monkeypatch)
    wall_clock_calls = []
    token_calls = []
    monkeypatch.setattr(
        bridge.time,
        "time",
        lambda: wall_clock_calls.append("time") or NOW,
    )
    monkeypatch.setattr(
        bridge.secrets,
        "token_hex",
        lambda: token_calls.append("token") or TOKEN_HEX,
    )

    bridge.cmd_paid_grant_create(_args(ttl_seconds=ttl_seconds))

    assert wall_clock_calls == ["time"]
    assert token_calls == ["token"]
    assert calls.count(("fetch", {"remote": "origin", "control_branch": "ai-control"})) == 1
    assert (
        "resolve",
        "refs/remotes/origin/ai-control",
        ".ai/tasks/TASK-052.md",
    ) in calls

    store = bridge.get_paid_api_grant_store()
    grant_id = f"grant-task-052-{TOKEN_HEX}"
    grant = store.load_active(TASK_ID, grant_id)
    assert grant is not None
    assert grant.task_id == TASK_ID
    assert grant.grant_id == grant_id
    assert grant.actor_kind is DispatchActorKind.BRAIN
    assert grant.brain_id == "minimax-brain"
    assert grant.provider_id == "minimax"
    assert grant.model_id == "MiniMax-M3"
    assert grant.brain_operation is BrainOperation.PLAN
    assert grant.authorized_artifact_path == ".ai/tasks/TASK-052.md"
    assert grant.authorized_artifact_blob_sha == BLOB_SHA
    assert grant.max_input_tokens == 12_000
    assert grant.max_output_tokens == 4_000
    assert grant.max_calls == 1
    assert grant.expires_at_epoch_seconds == NOW + ttl_seconds
    assert grant.workspace_id == bridge.get_workspace_id()
    assert not list(worktree.rglob("*.json"))
    assert not list((runtime / "auth").glob("*.json"))
    assert not list((runtime / "leases").rglob("*.json"))

    output = capsys.readouterr().out
    for expected in (
        "[PAID API GRANT ACTIVE]",
        "TASK_ID: TASK-052",
        f"GRANT_ID: {grant_id}",
        "ACTOR_KIND: BRAIN",
        "BRAIN_ID: minimax-brain",
        "PROVIDER_ID: minimax",
        "MODEL_ID: MiniMax-M3",
        "BRAIN_OPERATION: PLAN",
        "AUTHORIZED_ARTIFACT_PATH: .ai/tasks/TASK-052.md",
        f"AUTHORIZED_ARTIFACT_BLOB_SHA: {BLOB_SHA}",
        "MAX_INPUT_TOKENS: 12000",
        "MAX_OUTPUT_TOKENS: 4000",
        "MAX_CALLS: 1",
        f"EXPIRES_AT_EPOCH_SECONDS: {NOW + ttl_seconds}",
        f"WORKSPACE_ID: {grant.workspace_id}",
        f"GRANT_FINGERPRINT: {grant.grant_fingerprint}",
        "HUMAN_SPEND_AUTHORIZATION: YES",
        "PAID_API_DISPATCH_ENABLED: NO",
        "PROVIDER_CALL_STARTED: NO",
    ):
        assert expected in output


def test_parser_requires_all_spend_fields_and_exposes_no_authority_overrides():
    parser = bridge.build_parser()
    command = [
        "paid-grant-create",
        "52",
        "--brain-id",
        "brain",
        "--provider-id",
        "provider",
        "--model-id",
        "model",
        "--operation",
        "PLAN",
        "--artifact-path",
        ".ai/tasks/TASK-052.md",
        "--max-input-tokens",
        "100",
        "--max-output-tokens",
        "50",
        "--ttl-seconds",
        "60",
        "--confirm-paid-api-spend",
    ]
    parsed = parser.parse_args(command)
    assert parsed.func is bridge.cmd_paid_grant_create
    assert parsed.confirm_paid_api_spend is True

    required_flags = (
        "--brain-id",
        "--provider-id",
        "--model-id",
        "--operation",
        "--artifact-path",
        "--max-input-tokens",
        "--max-output-tokens",
        "--ttl-seconds",
        "--confirm-paid-api-spend",
    )
    for flag in required_flags:
        reduced = list(command)
        index = reduced.index(flag)
        del reduced[index : index + (1 if flag == "--confirm-paid-api-spend" else 2)]
        with pytest.raises(SystemExit):
            parser.parse_args(reduced)

    forbidden_flags = (
        "--grant-id",
        "--artifact-blob-sha",
        "--workspace-id",
        "--actor-kind",
        "--max-calls",
        "--api-key",
        "--authorization-header",
        "--token",
        "--cookie",
    )
    for flag in forbidden_flags:
        with pytest.raises(SystemExit):
            parser.parse_args(command + [flag, "forbidden"])


def test_missing_artifact_and_invalid_contract_fail_before_activation(
    isolated, monkeypatch
):
    calls = _mock_create_control(monkeypatch)
    monkeypatch.setattr(bridge.time, "time", lambda: NOW)
    monkeypatch.setattr(bridge.secrets, "token_hex", lambda: TOKEN_HEX)
    forbidden = []
    monkeypatch.setattr(
        bridge,
        "get_paid_api_grant_store",
        lambda: forbidden.append("store"),
    )
    monkeypatch.setattr(
        bridge,
        "resolve_git_blob_sha",
        lambda ref, path: (_ for _ in ()).throw(
            ContinuityStateValidationError("Unable to resolve Git blob")
        ),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_paid_grant_create(_args())
    assert forbidden == []

    monkeypatch.setattr(bridge, "resolve_git_blob_sha", lambda ref, path: BLOB_SHA)
    with pytest.raises(SystemExit):
        bridge.cmd_paid_grant_create(_args(artifact_path="not/.ai/canonical"))
    assert forbidden == []
    assert "ensure_git" in calls


def test_activation_failure_has_no_id_or_activation_retry(isolated, monkeypatch):
    _mock_create_control(monkeypatch)
    monkeypatch.setattr(bridge.time, "time", lambda: NOW)
    token_calls = []
    monkeypatch.setattr(
        bridge.secrets,
        "token_hex",
        lambda: token_calls.append("token") or TOKEN_HEX,
    )

    class FailingStore:
        def __init__(self):
            self.activate_calls = []
            self.require_calls = []

        def activate(self, grant, *, now_epoch_seconds):
            self.activate_calls.append((grant, now_epoch_seconds))
            raise ContinuityStateValidationError("collision")

        def require_active(self, grant, *, now_epoch_seconds):
            self.require_calls.append((grant, now_epoch_seconds))

    store = FailingStore()
    monkeypatch.setattr(bridge, "get_paid_api_grant_store", lambda: store)
    with pytest.raises(SystemExit):
        bridge.cmd_paid_grant_create(_args())
    assert token_calls == ["token"]
    assert len(store.activate_calls) == 1
    assert store.require_calls == []


def test_success_activates_once_then_requires_exact_same_grant(
    isolated, monkeypatch, capsys
):
    _mock_create_control(monkeypatch)
    monkeypatch.setattr(bridge.time, "time", lambda: NOW)
    monkeypatch.setattr(bridge.secrets, "token_hex", lambda: TOKEN_HEX)

    class RecordingStore:
        def __init__(self):
            self.activate_calls = []
            self.require_calls = []

        def activate(self, grant, *, now_epoch_seconds):
            self.activate_calls.append((grant, now_epoch_seconds))
            return grant

        def require_active(self, grant, *, now_epoch_seconds):
            self.require_calls.append((grant, now_epoch_seconds))
            return grant

    store = RecordingStore()
    monkeypatch.setattr(bridge, "get_paid_api_grant_store", lambda: store)
    bridge.cmd_paid_grant_create(_args())
    capsys.readouterr()
    assert len(store.activate_calls) == 1
    assert len(store.require_calls) == 1
    assert store.activate_calls[0] == store.require_calls[0]


def test_credentials_never_persist_or_print_and_no_other_control_plane_runs(
    isolated, monkeypatch, capsys
):
    runtime, _ = isolated
    _mock_create_control(monkeypatch)
    monkeypatch.setattr(bridge.time, "time", lambda: NOW)
    monkeypatch.setattr(bridge.secrets, "token_hex", lambda: TOKEN_HEX)
    secret = "task-052-super-secret-value"
    for name in ("API_KEY", "AUTHORIZATION", "TOKEN", "COOKIE"):
        monkeypatch.setenv(name, secret)
    forbidden = []
    for name in (
        "save_authorization",
        "get_lease_store",
        "cmd_approve",
        "cmd_handoff",
        "cmd_publish",
        "dispatch_executor",
        "run",
    ):
        monkeypatch.setattr(
            bridge,
            name,
            lambda *args, _name=name, **kwargs: forbidden.append(_name),
        )

    bridge.cmd_paid_grant_create(_args())
    output = capsys.readouterr().out
    persisted = b"".join(
        path.read_bytes()
        for path in (runtime / "paid_api_grants").rglob("*.json")
    ).decode("utf-8")
    assert secret not in output
    assert secret not in persisted
    assert forbidden == []
    source = inspect.getsource(bridge.cmd_paid_grant_create)
    assert "allow_paid_api" not in source
    assert ".consume(" not in source


@pytest.mark.parametrize(
    ("mode", "expected_state", "expected_usability"),
    [
        ("active", "ACTIVE", "UNEXPIRED"),
        ("expired", "ACTIVE", "EXPIRED"),
        ("consumed", "CONSUMED", None),
        ("none", "NONE", None),
    ],
)
def test_status_reports_exact_state_without_mutation(
    isolated, monkeypatch, capsys, mode, expected_state, expected_usability
):
    runtime, _ = isolated
    bridge.ensure_dirs()
    workspace_id = bridge.get_workspace_id()
    store = bridge.get_paid_api_grant_store()
    grant_id = f"grant-task-052-{TOKEN_HEX}"
    if mode != "none":
        expires_at = NOW - 1 if mode == "expired" else NOW + 60
        grant = _grant(workspace_id, expires_at=expires_at)
        activation_time = NOW - 100 if mode == "expired" else NOW
        store.activate(grant, now_epoch_seconds=activation_time)
        if mode == "consumed":
            store.consume(grant, now_epoch_seconds=NOW)

    before = _runtime_snapshot(runtime)
    monkeypatch.setattr(bridge.time, "time", lambda: NOW)
    forbidden = []
    for name in ("activate", "consume", "cmd_recommend", "dispatch_executor"):
        if hasattr(bridge, name):
            monkeypatch.setattr(
                bridge,
                name,
                lambda *args, _name=name, **kwargs: forbidden.append(_name),
            )
    bridge.cmd_paid_grant_status(
        SimpleNamespace(task_id=TASK_NUMBER, grant_id=grant_id)
    )
    after = _runtime_snapshot(runtime)
    output = capsys.readouterr().out
    assert f"RUNTIME_STATE: {expected_state}" in output
    if expected_usability is not None:
        assert f"USABILITY: {expected_usability}" in output
    else:
        assert "USABILITY:" not in output
    assert before == after
    assert forbidden == []


def test_status_none_does_not_create_missing_runtime_namespace(
    isolated, monkeypatch, capsys
):
    runtime, _ = isolated
    monkeypatch.setattr(
        bridge,
        "get_paid_api_grant_store",
        lambda: pytest.fail("missing namespace must not instantiate a mutating store"),
    )
    bridge.cmd_paid_grant_status(
        SimpleNamespace(task_id=TASK_NUMBER, grant_id=f"grant-task-052-{TOKEN_HEX}")
    )
    assert "RUNTIME_STATE: NONE" in capsys.readouterr().out
    assert not runtime.exists()


def test_corrupt_dual_status_fails_closed(isolated, monkeypatch):
    runtime, _ = isolated
    bridge.ensure_dirs()
    workspace_id = bridge.get_workspace_id()
    store = bridge.get_paid_api_grant_store()
    grant = _grant(workspace_id)
    store.activate(grant, now_epoch_seconds=NOW)
    active_path, consumed_path = store._state_paths(grant.task_id, grant.grant_id)
    consumed_path.write_bytes(active_path.read_bytes())
    monkeypatch.setattr(bridge.time, "time", lambda: NOW)
    before = _runtime_snapshot(runtime)
    with pytest.raises(SystemExit):
        bridge.cmd_paid_grant_status(
            SimpleNamespace(task_id=TASK_NUMBER, grant_id=grant.grant_id)
        )
    assert _runtime_snapshot(runtime) == before


def test_status_parser_is_minimal_and_read_only_surface():
    parser = bridge.build_parser()
    parsed = parser.parse_args(
        ["paid-grant-status", "52", "--grant-id", f"grant-task-052-{TOKEN_HEX}"]
    )
    assert parsed.func is bridge.cmd_paid_grant_status
    for forbidden in ("--refresh", "--delete", "--revoke", "--ttl-seconds"):
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "paid-grant-status",
                    "52",
                    "--grant-id",
                    f"grant-task-052-{TOKEN_HEX}",
                    forbidden,
                    "1",
                ]
            )
    source = inspect.getsource(bridge.cmd_paid_grant_status)
    for forbidden_call in (".activate(", ".consume(", ".unlink(", ".replace("):
        assert forbidden_call not in source
