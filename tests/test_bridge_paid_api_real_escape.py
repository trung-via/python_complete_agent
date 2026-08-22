from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.dispatch import CapacityState, DispatchActorKind
from src.aios_bridge.continuity.state import BrainOperation
from src.aios_bridge.minimax_m3_proof_lock import (
    CHAT_TEMPLATE_PATH,
    MiniMaxM3ProofLock,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    TOKENIZER_PATH,
)
from src.aios_bridge.paid_api_grant import PaidApiGrant
from src.aios_bridge import paid_api_real_escape as real_escape_module
from src.aios_bridge.runtime_dispatch import RuntimeCapacityRecord
from src.aios_bridge.runtime_paid_api_grant import AtomicPaidApiGrantStore


TASK_NUM = 62
TASK_ID = "TASK-062"
GRANT_ID = "grant-task-062-bridge-offline"
WORKSPACE_ID = "1" * 64
MAIN_SHA = "2" * 40
CONTROL_SHA = "3" * 40
PROOF_LOCK_PATH = ".ai/context/TASK-062-PROOF-LOCK.json"
PROOF_LOCK_BLOB = "4" * 40
ARTIFACT_PATH = ".ai/tasks/TASK-062.md"
ARTIFACT_CONTENT = "# TASK-062\n\nOffline Bridge command context.\n"
SUBSCRIPTION_BRAIN = "subscription-brain"
PAID_BRAIN = "minimax-paid-brain"
TEMPLATE_SHA = hashlib.sha256(b"template").hexdigest()
TOKENIZER_SHA = hashlib.sha256(b"tokenizer").hexdigest()
COUNTER_ID = (
    f"minimax-m3-local:{SOURCE_REVISION}:{TEMPLATE_SHA}:{TOKENIZER_SHA}"
)


def _git_blob_sha(content: str) -> str:
    raw = content.encode("utf-8")
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _proof_lock() -> MiniMaxM3ProofLock:
    return MiniMaxM3ProofLock(
        schema_version="1",
        provider_id="minimax",
        model_id="MiniMax-M3",
        endpoint_url="https://api.minimax.io/v1/chat/completions",
        credential_env_name="MINIMAX_API_KEY",
        source_repository=SOURCE_REPOSITORY,
        source_revision=SOURCE_REVISION,
        chat_template_path=CHAT_TEMPLATE_PATH,
        chat_template_sha256=TEMPLATE_SHA,
        tokenizer_path=TOKENIZER_PATH,
        tokenizer_sha256=TOKENIZER_SHA,
        jinja2_version="3.1.6",
        tokenizers_version="0.23.1",
        requests_version="2.32.3",
    )


def _grant() -> PaidApiGrant:
    return PaidApiGrant(
        schema_version="1",
        grant_id=GRANT_ID,
        task_id=TASK_ID,
        actor_kind=DispatchActorKind.BRAIN,
        brain_id=PAID_BRAIN,
        provider_id="minimax",
        model_id="MiniMax-M3",
        brain_operation=BrainOperation.PLAN,
        authorized_artifact_path=ARTIFACT_PATH,
        authorized_artifact_blob_sha=_git_blob_sha(ARTIFACT_CONTENT),
        max_input_tokens=256,
        max_output_tokens=64,
        max_calls=1,
        expires_at_epoch_seconds=2_000_000_000,
        workspace_id=WORKSPACE_ID,
    )


def _args(subscription_fingerprint: str = "5" * 64, paid_fingerprint: str = "6" * 64):
    return SimpleNamespace(
        task_id=TASK_NUM,
        grant_id=GRANT_ID,
        proof_lock_path=PROOF_LOCK_PATH,
        proof_lock_blob_sha=PROOF_LOCK_BLOB,
        subscription_brain_id=SUBSCRIPTION_BRAIN,
        subscription_capacity_fingerprint=subscription_fingerprint,
        paid_capacity_fingerprint=paid_fingerprint,
    )


def _mock_local_git(monkeypatch: pytest.MonkeyPatch, *, branch: str = "main") -> None:
    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        bridge,
        "load_config",
        lambda: {"remote": "origin", "control_branch": "ai-control"},
    )

    def forbidden_fetch(*_args, **_kwargs):
        raise AssertionError("paid-proof-execute must not fetch")

    monkeypatch.setattr(bridge, "fetch_control", forbidden_fetch)

    def fake_git(*args, **_kwargs):
        if args[0] == "fetch":
            raise AssertionError("paid-proof-execute must not run git fetch")
        if args[:2] == ("status", "--porcelain"):
            return SimpleNamespace(stdout="", returncode=0)
        if args[:3] == ("rev-parse", "--abbrev-ref", "HEAD"):
            return SimpleNamespace(stdout=branch, returncode=0)
        if args[0] == "rev-parse":
            target = args[1]
            if target in {"HEAD", "main", "origin/main"}:
                return SimpleNamespace(stdout=MAIN_SHA, returncode=0)
            if target == "refs/remotes/origin/ai-control":
                return SimpleNamespace(stdout=CONTROL_SHA, returncode=0)
        return SimpleNamespace(stdout="", returncode=1)

    monkeypatch.setattr(bridge, "git", fake_git)


def test_parser_exposes_exact_paid_proof_execute_surface_without_overrides():
    parser = bridge.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if hasattr(action, "choices") and action.choices
    )
    execute_parser = subparsers.choices["paid-proof-execute"]
    options = {
        option
        for action in execute_parser._actions
        for option in action.option_strings
    }
    assert options == {
        "-h",
        "--help",
        "--grant-id",
        "--proof-lock-path",
        "--proof-lock-blob-sha",
        "--subscription-brain-id",
        "--subscription-capacity-fingerprint",
        "--paid-capacity-fingerprint",
    }
    for forbidden in (
        "--api-key",
        "--provider-id",
        "--model-id",
        "--endpoint",
        "--asset-dir",
        "--ledger-path",
        "--allow-paid-api",
        "--retry",
        "--executor",
    ):
        assert forbidden not in options


def test_replay_is_rejected_before_assets_credential_or_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
):
    _mock_local_git(monkeypatch)
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path / "grants", WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=10)
    store.consume(grant, now_epoch_seconds=20)
    monkeypatch.setattr(bridge, "get_paid_api_grant_store", lambda: store)
    monkeypatch.setattr(
        bridge,
        "resolve_git_blob_sha",
        lambda _ref, path: PROOF_LOCK_BLOB if path == PROOF_LOCK_PATH else "f" * 40,
    )
    monkeypatch.setattr(
        bridge,
        "read_git_blob_bytes",
        lambda _ref, path: _proof_lock().to_canonical_json().encode("utf-8")
        if path == PROOF_LOCK_PATH
        else b"",
    )
    monkeypatch.setenv("MINIMAX_API_KEY", "REPLAY_SECRET_MUST_NOT_BE_READ")

    with pytest.raises(SystemExit):
        bridge.cmd_paid_proof_execute(_args())

    error = capsys.readouterr().err
    assert "GRANT_ALREADY_CONSUMED / NO_PROVIDER_CALL" in error
    assert "REPLAY_SECRET_MUST_NOT_BE_READ" not in error
    assert not (tmp_path / "paid_api_assets").exists()


def test_r0_requires_current_main_and_never_fetches(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
):
    _mock_local_git(monkeypatch, branch="ai/task-062")
    monkeypatch.setattr(
        bridge,
        "get_paid_api_grant_store",
        lambda: (_ for _ in ()).throw(AssertionError("grant store reached")),
    )

    with pytest.raises(SystemExit):
        bridge.cmd_paid_proof_execute(_args())
    assert "R0 requires current branch main" in capsys.readouterr().err


def test_successful_bridge_orchestration_is_offline_in_test_and_secret_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
):
    _mock_local_git(monkeypatch)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("MINIMAX_API_KEY", "BRIDGE_DUMMY_SECRET_MUST_NOT_LEAK")
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: WORKSPACE_ID)
    grant = _grant()
    store = AtomicPaidApiGrantStore(runtime_root / "paid_api_grants", WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=1_000_000_000)
    monkeypatch.setattr(bridge, "get_paid_api_grant_store", lambda: store)

    subscription = RuntimeCapacityRecord(
        actor_kind=DispatchActorKind.BRAIN,
        actor_id=SUBSCRIPTION_BRAIN,
        capacity_state=CapacityState.UNAVAILABLE,
        observed_at_epoch_seconds=1_000_000_000,
        ttl_seconds=100,
    )
    paid = RuntimeCapacityRecord(
        actor_kind=DispatchActorKind.BRAIN,
        actor_id=PAID_BRAIN,
        capacity_state=CapacityState.AVAILABLE,
        observed_at_epoch_seconds=1_000_000_000,
        ttl_seconds=100,
    )

    class CapacityStore:
        def load(self, _kind, actor_id):
            return subscription if actor_id == SUBSCRIPTION_BRAIN else paid

    monkeypatch.setattr(bridge, "get_runtime_capacity_store", lambda: CapacityStore())
    monkeypatch.setattr(
        bridge,
        "resolve_git_blob_sha",
        lambda _ref, path: {
            PROOF_LOCK_PATH: PROOF_LOCK_BLOB,
            ARTIFACT_PATH: grant.authorized_artifact_blob_sha,
        }[path],
    )
    monkeypatch.setattr(
        bridge,
        "read_git_blob_bytes",
        lambda _ref, path: (
            _proof_lock().to_canonical_json().encode("utf-8")
            if path == PROOF_LOCK_PATH
            else ARTIFACT_CONTENT.encode("utf-8")
        ),
    )

    import importlib.metadata

    versions = {"Jinja2": "3.1.6", "tokenizers": "0.23.1", "requests": "2.32.3"}
    monkeypatch.setattr(importlib.metadata, "version", lambda name: versions[name])

    class Counter:
        counter_id = COUNTER_ID

        def __init__(self, _asset_directory, _lock):
            pass

    monkeypatch.setattr(
        "src.aios_bridge.minimax_m3_input_counter.MiniMaxM3LocalProviderInputCounter",
        Counter,
    )

    proof_receipt = SimpleNamespace(
        task_id=TASK_ID,
        runtime_main_sha=MAIN_SHA,
        control_commit_sha=CONTROL_SHA,
        proof_lock_fingerprint=_proof_lock().fingerprint(),
        subscription_capacity_fingerprint=subscription.record_fingerprint,
        paid_capacity_fingerprint=paid.record_fingerprint,
        preflight_fingerprint="7" * 64,
        operational_proof_fingerprint="8" * 64,
        proposal_logical_path=f"paid_api_proofs/{TASK_ID}/hash/proposal.md",
        proposal_sha256="9" * 64,
        proof_logical_path=f"paid_api_proofs/{TASK_ID}/hash/proof.json",
    )
    calls = {"count": 0}

    async def offline_execute(**kwargs):
        calls["count"] += 1
        assert kwargs["provider_factory"] is not None
        assert kwargs["subscription_brain_id"] == SUBSCRIPTION_BRAIN
        assert kwargs["subscription_capacity_fingerprint"] == subscription.record_fingerprint
        assert kwargs["paid_capacity_fingerprint"] == paid.record_fingerprint
        return SimpleNamespace(proof_receipt=proof_receipt)

    monkeypatch.setattr(
        real_escape_module,
        "execute_paid_api_real_escape",
        offline_execute,
    )
    args = _args(subscription.record_fingerprint, paid.record_fingerprint)

    bridge.cmd_paid_proof_execute(args)

    output = capsys.readouterr().out
    assert calls["count"] == 1
    assert "[PAID API REAL ESCAPE PROOF PASS]" in output
    assert "PROVIDER_CALL_COUNT: 1" in output
    assert "RETRY_COUNT: 0" in output
    assert "EXECUTOR_AUTHORITY_CREATED: NO" in output
    assert "BRIDGE_DUMMY_SECRET_MUST_NOT_LEAK" not in output
    assert str(runtime_root) not in output
def test_r0_r7_proves_credential_presence_without_accessing_secret_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Prove secret VALUE is never accessed during R0-R7, only key presence."""
    import os
    _mock_local_git(monkeypatch)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: WORKSPACE_ID)
    grant = _grant()
    store = AtomicPaidApiGrantStore(runtime_root / "paid_api_grants", WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=1_000_000_000)
    monkeypatch.setattr(bridge, "get_paid_api_grant_store", lambda: store)

    subscription = RuntimeCapacityRecord(
        actor_kind=DispatchActorKind.BRAIN,
        actor_id=SUBSCRIPTION_BRAIN,
        capacity_state=CapacityState.UNAVAILABLE,
        observed_at_epoch_seconds=1_000_000_000,
        ttl_seconds=100,
    )
    paid = RuntimeCapacityRecord(
        actor_kind=DispatchActorKind.BRAIN,
        actor_id=PAID_BRAIN,
        capacity_state=CapacityState.AVAILABLE,
        observed_at_epoch_seconds=1_000_000_000,
        ttl_seconds=100,
    )

    class CapacityStore:
        def load(self, _kind, actor_id):
            return subscription if actor_id == SUBSCRIPTION_BRAIN else paid

    monkeypatch.setattr(bridge, "get_runtime_capacity_store", lambda: CapacityStore())
    monkeypatch.setattr(
        bridge,
        "resolve_git_blob_sha",
        lambda _ref, path: {
            PROOF_LOCK_PATH: PROOF_LOCK_BLOB,
            ARTIFACT_PATH: grant.authorized_artifact_blob_sha,
        }[path],
    )
    monkeypatch.setattr(
        bridge,
        "read_git_blob_bytes",
        lambda _ref, path: (
            _proof_lock().to_canonical_json().encode("utf-8")
            if path == PROOF_LOCK_PATH
            else ARTIFACT_CONTENT.encode("utf-8")
        ),
    )

    import importlib.metadata
    versions = {"Jinja2": "3.1.6", "tokenizers": "0.23.1", "requests": "2.32.3"}
    monkeypatch.setattr(importlib.metadata, "version", lambda name: versions[name])

    class Counter:
        counter_id = COUNTER_ID
        def __init__(self, _asset_directory, _lock):
            pass

    monkeypatch.setattr(
        "src.aios_bridge.minimax_m3_input_counter.MiniMaxM3LocalProviderInputCounter",
        Counter,
    )

    secret_value_reads = {"count": 0}
    original_environ = os.environ.copy()
    original_environ["MINIMAX_API_KEY"] = "SECRET_VALUE_SENTINEL"

    class GuardedEnviron(dict):
        def __contains__(self, key):
            return key in original_environ
        def get(self, key, default=None):
            if key == "MINIMAX_API_KEY":
                secret_value_reads["count"] += 1
            return original_environ.get(key, default)
        def __getitem__(self, key):
            if key == "MINIMAX_API_KEY":
                secret_value_reads["count"] += 1
            return original_environ[key]

    monkeypatch.setattr(os, "environ", GuardedEnviron(original_environ))

    factory_holder = {}
    async def capture_execute(**kwargs):
        factory_holder["provider_factory"] = kwargs["provider_factory"]
        assert secret_value_reads["count"] == 0
        return SimpleNamespace(proof_receipt=SimpleNamespace(
            task_id=TASK_ID,
            runtime_main_sha=MAIN_SHA,
            control_commit_sha=CONTROL_SHA,
            proof_lock_fingerprint=_proof_lock().fingerprint(),
            subscription_capacity_fingerprint=subscription.record_fingerprint,
            paid_capacity_fingerprint=paid.record_fingerprint,
            preflight_fingerprint="7" * 64,
            operational_proof_fingerprint="8" * 64,
            proposal_logical_path=f"paid_api_proofs/{TASK_ID}/hash/proposal.md",
            proposal_sha256="9" * 64,
            proof_logical_path=f"paid_api_proofs/{TASK_ID}/hash/proof.json",
        ))

    monkeypatch.setattr(
        real_escape_module,
        "execute_paid_api_real_escape",
        capture_execute,
    )
    args = _args(subscription.record_fingerprint, paid.record_fingerprint)
    bridge.cmd_paid_proof_execute(args)

    assert secret_value_reads["count"] == 0, "Secret value was read before provider factory invocation!"
