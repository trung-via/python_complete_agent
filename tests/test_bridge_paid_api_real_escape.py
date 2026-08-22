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


def _args(
    subscription_fingerprint: str = "5" * 64,
    paid_fingerprint: str = "6" * 64,
    provider_timeout_seconds: int = 120,
):
    return SimpleNamespace(
        task_id=TASK_NUM,
        grant_id=GRANT_ID,
        proof_lock_path=PROOF_LOCK_PATH,
        proof_lock_blob_sha=PROOF_LOCK_BLOB,
        subscription_brain_id=SUBSCRIPTION_BRAIN,
        subscription_capacity_fingerprint=subscription_fingerprint,
        paid_capacity_fingerprint=paid_fingerprint,
        provider_timeout_seconds=provider_timeout_seconds,
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
        "--provider-timeout-seconds",
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
class ProductionLikeEnviron:
    """Accurately mirrors os._Environ / MutableMapping semantics where membership uses __getitem__."""
    def __init__(self, initial: dict[str, str] | None = None):
        import os as _real_os
        self._data = dict(_real_os.environ)
        if initial:
            self._data.update(initial)
        self.secret_value_reads = 0

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key: str) -> str:
        if key == "MINIMAX_API_KEY":
            self.secret_value_reads += 1
        return self._data[key]

    def __setitem__(self, key: str, value: str):
        self._data[key] = value

    def __delitem__(self, key: str):
        del self._data[key]

    def __contains__(self, key: object) -> bool:
        # Standard MutableMapping fallback: invokes __getitem__
        try:
            self[key]
            return True
        except KeyError:
            return False

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def copy(self):
        return dict(self._data)


def test_r0_r7_proves_credential_presence_without_accessing_secret_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Prove secret VALUE is never accessed during R0-R7, only key presence.
    
    Prove exactly one value read is permitted when the deferred provider factory is invoked after R7.
    """
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

    env = ProductionLikeEnviron({"MINIMAX_API_KEY": "SECRET_VALUE_SENTINEL"})
    monkeypatch.setattr(os, "environ", env)

    factory_holder = {}
    async def capture_execute(**kwargs):
        factory_holder["provider_factory"] = kwargs["provider_factory"]
        assert env.secret_value_reads == 0, f"Expected 0 reads before factory, got {env.secret_value_reads}"
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

    assert env.secret_value_reads == 0, "Secret value was read during R0-R7 validation!"
    assert "provider_factory" in factory_holder
    # Now invoke the factory to prove exactly one credential value read occurs when constructed
    provider = factory_holder["provider_factory"]()
    assert env.secret_value_reads == 1, "Exactly one credential read must occur in provider factory!"
    assert provider.provider_id == "minimax" and provider.model_name == "MiniMax-M3"


def test_r0_r7_validation_failure_reaches_zero_credential_value_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Prove validation failures at R0-R7 reach zero credential-value reads under production mapping semantics."""
    import os
    _mock_local_git(monkeypatch)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: WORKSPACE_ID)
    grant = _grant()
    store = AtomicPaidApiGrantStore(runtime_root / "paid_api_grants", WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=1_000_000_000)
    monkeypatch.setattr(bridge, "get_paid_api_grant_store", lambda: store)

    env = ProductionLikeEnviron({"MINIMAX_API_KEY": "SECRET_VALUE_SENTINEL"})
    monkeypatch.setattr(os, "environ", env)

    # Missing proof lock blob failure at R1
    monkeypatch.setattr(
        bridge,
        "resolve_git_blob_sha",
        lambda _ref, _path: "0" * 40,
    )

    with pytest.raises(SystemExit):
        bridge.cmd_paid_proof_execute(_args())

    assert env.secret_value_reads == 0, "Secret value was read during validation failure!"


def test_same_grant_replay_rejection_reaches_zero_credential_value_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Prove same-grant replay rejection at R2 reaches zero credential-value reads under production mapping semantics."""
    import os
    _mock_local_git(monkeypatch)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setattr(bridge, "get_workspace_id", lambda: WORKSPACE_ID)
    grant = _grant()
    store = AtomicPaidApiGrantStore(runtime_root / "paid_api_grants", WORKSPACE_ID)
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

    env = ProductionLikeEnviron({"MINIMAX_API_KEY": "SECRET_VALUE_SENTINEL"})
    monkeypatch.setattr(os, "environ", env)

    with pytest.raises(SystemExit):
        bridge.cmd_paid_proof_execute(_args())

    assert env.secret_value_reads == 0, "Secret value was read during replay rejection!"
@pytest.mark.parametrize("valid_timeout", [60, 120, 180])
def test_paid_proof_execute_accepts_valid_timeout_seconds_range_and_wires_to_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    valid_timeout: int,
):
    """Prove 60, 120, and 180 are accepted and passed unchanged to MiniMaxOpenAIProvider."""
    _mock_local_git(monkeypatch)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("MINIMAX_API_KEY", "DUMMY_KEY")
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

    factory_holder = {}
    async def capture_execute(**kwargs):
        factory_holder["provider_factory"] = kwargs["provider_factory"]
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
    args = _args(
        subscription.record_fingerprint,
        paid.record_fingerprint,
        provider_timeout_seconds=valid_timeout,
    )
    bridge.cmd_paid_proof_execute(args)

    assert "provider_factory" in factory_holder
    provider = factory_holder["provider_factory"]()
    assert getattr(provider, "timeout_seconds", None) == float(valid_timeout) or getattr(provider, "_timeout_seconds", None) == float(valid_timeout) or getattr(getattr(provider, "_transport", None), "timeout_seconds", None) == float(valid_timeout)


@pytest.mark.parametrize("invalid_timeout", [59, 181, 0, -1, -30, "120", 120.5, True, False, None])
def test_paid_proof_execute_rejects_invalid_and_out_of_range_timeouts_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_timeout,
):
    """Prove values outside 60..180 or malformed/non-integer values fail before provider call/spend."""
    _mock_local_git(monkeypatch)
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setenv("MINIMAX_API_KEY", "DUMMY_KEY")

    factory_called = {"count": 0}
    async def forbidden_execute(**_kwargs):
        factory_called["count"] += 1
        raise AssertionError("execute_paid_api_real_escape must not be called on invalid timeout")

    monkeypatch.setattr(
        real_escape_module,
        "execute_paid_api_real_escape",
        forbidden_execute,
    )
    args = _args(provider_timeout_seconds=invalid_timeout)
    with pytest.raises(SystemExit):
        bridge.cmd_paid_proof_execute(args)

    assert factory_called["count"] == 0


def test_cli_parser_rejects_omitted_provider_timeout_seconds(capsys):
    """Prove omitting --provider-timeout-seconds fails CLI parsing."""
    parser = bridge.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "paid-proof-execute",
            "62",
            "--grant-id", "grant-1",
            "--proof-lock-path", ".ai/context/TASK-062-PROOF-LOCK.json",
            "--proof-lock-blob-sha", "4" * 40,
            "--subscription-brain-id", "sub-brain",
            "--subscription-capacity-fingerprint", "5" * 64,
            "--paid-capacity-fingerprint", "6" * 64,
        ])


def test_live_path_has_no_hardcoded_30_second_timeout():
    """Verify the live paid-proof-execute function does not contain magic 30.0."""
    import inspect
    source = inspect.getsource(bridge.cmd_paid_proof_execute)
    assert "timeout_seconds=30" not in source
    assert "timeout_seconds=30.0" not in source
