"""Bridge CLI tests for TASK-059 M11.3B paid API proof preflight command."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest

import bridge
from src.aios_bridge.continuity.dispatch import DispatchActorKind
from src.aios_bridge.continuity.state import BrainOperation
from src.aios_bridge.minimax_m3_proof_lock import (
    MiniMaxM3ProofLock,
    PROVIDER_ID,
    MODEL_ID,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    CHAT_TEMPLATE_PATH,
    TOKENIZER_PATH,
)
from src.aios_bridge.paid_api_grant import PaidApiGrant
from src.aios_bridge.runtime_paid_api_grant import AtomicPaidApiGrantStore


TASK_NUM = 59
TASK_ID_STR = "TASK-059"
GRANT_ID = "grant-task-059-123456"
ARTIFACT_PATH = ".ai/tasks/TASK-059.md"
ARTIFACT_BLOB = "a" * 40
PROOF_LOCK_PATH = ".ai/context/proof_lock.json"
PROOF_LOCK_BLOB = "b" * 40
MAIN_SHA = "c" * 40
CONTROL_COMMIT_SHA = "d" * 40
WORKSPACE_ID = "e" * 64

TEMPLATE_CONTENT = b"template bytes"
TOKENIZER_CONTENT = b"tokenizer bytes"
TEMPLATE_SHA = hashlib.sha256(TEMPLATE_CONTENT).hexdigest()
TOKENIZER_SHA = hashlib.sha256(TOKENIZER_CONTENT).hexdigest()


def _valid_proof_lock() -> MiniMaxM3ProofLock:
    return MiniMaxM3ProofLock(
        schema_version="1",
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        endpoint_url="https://api.minimax.io/v1/text/chatcompletion_v2",
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


def _valid_grant() -> PaidApiGrant:
    return PaidApiGrant(
        schema_version="1",
        grant_id=GRANT_ID,
        task_id=TASK_ID_STR,
        actor_kind=DispatchActorKind.BRAIN,
        brain_id="minimax",
        provider_id="minimax",
        model_id="MiniMax-M3",
        brain_operation=BrainOperation.PLAN,
        authorized_artifact_path=ARTIFACT_PATH,
        authorized_artifact_blob_sha=ARTIFACT_BLOB,
        max_input_tokens=10000,
        max_output_tokens=8192,
        max_calls=1,
        expires_at_epoch_seconds=2000000000,
        workspace_id=WORKSPACE_ID,
    )


def _setup_assets(runtime_dir: Path):
    asset_dir = runtime_dir / "paid_api_assets" / PROVIDER_ID / MODEL_ID / SOURCE_REVISION
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / CHAT_TEMPLATE_PATH).write_bytes(TEMPLATE_CONTENT)
    (asset_dir / TOKENIZER_PATH).write_bytes(TOKENIZER_CONTENT)
    manifest = {
        "schema_version": "1",
        "source_repository": SOURCE_REPOSITORY,
        "source_revision": SOURCE_REVISION,
        "chat_template_path": CHAT_TEMPLATE_PATH,
        "chat_template_sha256": TEMPLATE_SHA,
        "tokenizer_path": TOKENIZER_PATH,
        "tokenizer_sha256": TOKENIZER_SHA,
    }
    (asset_dir / "asset-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def mock_preflight_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    runtime_dir = tmp_path / "runtime"
    worktree = tmp_path / "worktree"
    runtime_dir.mkdir()
    worktree.mkdir()

    monkeypatch.setenv("AIOS_RUNTIME_DIR", str(runtime_dir))
    monkeypatch.setenv("MINIMAX_API_KEY", "dummy-secret-key-never-printed")
    monkeypatch.setattr(bridge, "PROJECT", worktree)
    monkeypatch.setattr(bridge, "get_workspace_id", lambda *args, **kwargs: WORKSPACE_ID)

    # Setup grant in store
    store = AtomicPaidApiGrantStore(runtime_dir / "paid_api_grants", WORKSPACE_ID)
    grant = _valid_grant()
    store.activate(grant, now_epoch_seconds=1000000000)
    monkeypatch.setattr(bridge, "get_paid_api_grant_store", lambda *args, **kwargs: store)

    # Setup assets
    _setup_assets(runtime_dir)

    # Setup fake counter class to bypass actual jinja/tokenizer imports in bridge test
    class MockCounter:
        def __init__(self, asset_dir, proof_lock):
            if type(proof_lock) is not MiniMaxM3ProofLock:
                raise TypeError("not MiniMaxM3ProofLock")
            self.counter_id = f"minimax-m3-local:{SOURCE_REVISION}:{TEMPLATE_SHA}:{TOKENIZER_SHA}"

    from src.aios_bridge import minimax_m3_input_counter
    monkeypatch.setattr(minimax_m3_input_counter, "MiniMaxM3LocalProviderInputCounter", MockCounter)

    # Mock git operations (pure offline)
    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: {"remote": "origin", "control_branch": "ai-control"})
    monkeypatch.setattr(bridge, "remote_ref", lambda cfg: "refs/remotes/origin/ai-control")

    # If fetch_control is called, FAIL IMMEDIATELY (B2 offline proof)
    def forbidden_fetch(*args, **kwargs):
        raise AssertionError("cmd_paid_proof_preflight must NEVER call fetch_control() or perform network I/O")

    monkeypatch.setattr(bridge, "fetch_control", forbidden_fetch)

    def mock_git(*args, **kwargs):
        cmd = args[0]
        if cmd == "fetch":
            raise AssertionError("git fetch was called during offline preflight")
        if cmd == "status":
            return SimpleNamespace(stdout="", returncode=0)
        elif cmd == "rev-parse":
            target = args[1]
            if target in ("HEAD", "main", "origin/main"):
                return SimpleNamespace(stdout=MAIN_SHA, returncode=0)
            elif "ai-control" in target:
                return SimpleNamespace(stdout=CONTROL_COMMIT_SHA, returncode=0)
            return SimpleNamespace(stdout=MAIN_SHA, returncode=0)
        elif cmd == "show":
            target = args[1]
            if target == PROOF_LOCK_BLOB:
                return SimpleNamespace(stdout=_valid_proof_lock().to_canonical_json(), returncode=0)
            return SimpleNamespace(stdout="", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(bridge, "git", mock_git)

    def mock_resolve_blob(ref, path):
        if path == PROOF_LOCK_PATH:
            return PROOF_LOCK_BLOB
        elif path == ARTIFACT_PATH:
            return ARTIFACT_BLOB
        return "x" * 40

    monkeypatch.setattr(bridge, "resolve_git_blob_sha", mock_resolve_blob)

    # Mock package metadata versions
    import importlib.metadata
    orig_version = importlib.metadata.version

    def mock_version(pkg_name):
        mapping = {
            "Jinja2": "3.1.6",
            "tokenizers": "0.23.1",
            "requests": "2.32.3",
        }
        if pkg_name in mapping:
            return mapping[pkg_name]
        return orig_version(pkg_name)

    monkeypatch.setattr(importlib.metadata, "version", mock_version)

    return runtime_dir, worktree


def _preflight_args(**overrides):
    values = {
        "task_id": TASK_NUM,
        "grant_id": GRANT_ID,
        "proof_lock_path": PROOF_LOCK_PATH,
        "proof_lock_blob_sha": PROOF_LOCK_BLOB,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TestBridgePaidProofPreflight:
    def test_successful_preflight_output(self, mock_preflight_env, capsys):
        bridge.cmd_paid_proof_preflight(_preflight_args())
        out = capsys.readouterr().out
        assert "[PAID API PROOF PREFLIGHT PASS]" in out
        assert f"TASK_ID: {TASK_ID_STR}" in out
        assert f"GRANT_ID: {GRANT_ID}" in out
        assert f"RUNTIME_MAIN_SHA: {MAIN_SHA}" in out
        assert f"CONTROL_COMMIT_SHA: {CONTROL_COMMIT_SHA}" in out
        assert f"PROOF_LOCK_PATH: {PROOF_LOCK_PATH}" in out
        assert f"PROOF_LOCK_BLOB_SHA: {PROOF_LOCK_BLOB}" in out
        assert "CREDENTIAL_SOURCE: env:MINIMAX_API_KEY" in out
        assert "CREDENTIAL_PRESENT: YES" in out
        assert "LEDGER_READY: YES" in out
        assert "GRANT_STATE: ACTIVE" in out
        assert "GRANT_CONSUMED: NO" in out
        assert "PAID_API_DISPATCH_ENABLED: NO" in out
        assert "PROVIDER_CALL_STARTED: NO" in out
        assert "PREFLIGHT_FINGERPRINT:" in out
        # Crucial security check: secret key is NEVER printed
        assert "dummy-secret-key-never-printed" not in out

    def test_never_calls_fetch_control_or_network(self, mock_preflight_env):
        # mock_preflight_env already sets fetch_control and git fetch to raise AssertionError.
        # This test ensures successful preflight runs purely offline without invoking them.
        bridge.cmd_paid_proof_preflight(_preflight_args())

    def test_fails_if_worktree_is_dirty(self, mock_preflight_env, monkeypatch):
        def mock_dirty_git(*args, **kwargs):
            if args[0] == "status":
                return SimpleNamespace(stdout=" M modified_file.py\n", returncode=0)
            return SimpleNamespace(stdout=MAIN_SHA, returncode=0)

        monkeypatch.setattr(bridge, "git", mock_dirty_git)
        with pytest.raises(SystemExit):
            bridge.cmd_paid_proof_preflight(_preflight_args())

    def test_fails_if_head_not_equal_origin_main(self, mock_preflight_env, monkeypatch):
        def mock_divergent_git(*args, **kwargs):
            if args[0] == "status":
                return SimpleNamespace(stdout="", returncode=0)
            if args[0] == "rev-parse":
                if args[1] == "HEAD":
                    return SimpleNamespace(stdout="1" * 40, returncode=0)
                elif args[1] == "origin/main":
                    return SimpleNamespace(stdout="2" * 40, returncode=0)
            return SimpleNamespace(stdout=MAIN_SHA, returncode=0)

        monkeypatch.setattr(bridge, "git", mock_divergent_git)
        with pytest.raises(SystemExit):
            bridge.cmd_paid_proof_preflight(_preflight_args())

    def test_fails_if_proof_lock_path_is_not_canonical_ai_path(self, mock_preflight_env):
        for bad_path in [
            "outside/proof_lock.json",
            r".ai\context\proof_lock.json",
            ".ai/../proof_lock.json",
            "/.ai/context/proof_lock.json",
            ".ai",
        ]:
            args = _preflight_args(proof_lock_path=bad_path)
            with pytest.raises(SystemExit):
                bridge.cmd_paid_proof_preflight(args)

    def test_fails_if_proof_lock_blob_mismatch(self, mock_preflight_env, monkeypatch):
        monkeypatch.setattr(bridge, "resolve_git_blob_sha", lambda ref, path: "f" * 40)
        with pytest.raises(SystemExit):
            bridge.cmd_paid_proof_preflight(_preflight_args())

    def test_fails_if_grant_not_found(self, mock_preflight_env):
        args = _preflight_args(grant_id="grant-task-059-nonexistent")
        with pytest.raises(SystemExit):
            bridge.cmd_paid_proof_preflight(args)

    def test_fails_if_dependency_version_mismatched(self, mock_preflight_env, monkeypatch):
        import importlib.metadata
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.0.1")
        with pytest.raises(SystemExit):
            bridge.cmd_paid_proof_preflight(_preflight_args())

    def test_fails_if_credential_missing(self, mock_preflight_env, monkeypatch):
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        with pytest.raises(SystemExit):
            bridge.cmd_paid_proof_preflight(_preflight_args())

    def test_sanitizes_absolute_path_on_durability_probe_failure(
        self,
        mock_preflight_env,
        monkeypatch,
        capsys,
    ):
        sentinel_path = "/secret/internal/absolute/user/runtime/path/never_leak"

        def failing_probe(*args, **kwargs):
            raise OSError(f"Cannot write file: {sentinel_path}")

        from src.aios_bridge import paid_api_proof_preflight
        monkeypatch.setattr(paid_api_proof_preflight, "probe_ledger_durability", failing_probe)

        with pytest.raises(SystemExit):
            bridge.cmd_paid_proof_preflight(_preflight_args())

        err = capsys.readouterr().err
        assert sentinel_path not in err
        assert "ledger directory durability probe failed" in err

    @pytest.mark.parametrize("invalid_output_tokens", [4000, 2000, 8191, 8193, 64, 16384])
    def test_fails_if_grant_max_output_tokens_not_8192(
        self,
        mock_preflight_env,
        monkeypatch,
        tmp_path,
        capsys,
        invalid_output_tokens,
    ):
        runtime_dir = tmp_path / "runtime"
        store = AtomicPaidApiGrantStore(runtime_dir / "paid_api_grants", WORKSPACE_ID)
        bad_grant = PaidApiGrant(
            schema_version="1",
            grant_id="grant-bad-output-tokens",
            task_id=TASK_ID_STR,
            actor_kind=DispatchActorKind.BRAIN,
            brain_id="minimax",
            provider_id="minimax",
            model_id="MiniMax-M3",
            brain_operation=BrainOperation.PLAN,
            authorized_artifact_path=ARTIFACT_PATH,
            authorized_artifact_blob_sha=ARTIFACT_BLOB,
            max_input_tokens=10000,
            max_output_tokens=invalid_output_tokens,
            max_calls=1,
            expires_at_epoch_seconds=2000000000,
            workspace_id=WORKSPACE_ID,
        )
        store.activate(bad_grant, now_epoch_seconds=1000000000)
        monkeypatch.setattr(bridge, "get_paid_api_grant_store", lambda *args, **kwargs: store)

        args = SimpleNamespace(
            task_id=TASK_NUM,
            grant_id="grant-bad-output-tokens",
            proof_lock_path=PROOF_LOCK_PATH,
            proof_lock_blob_sha=PROOF_LOCK_BLOB,
        )
        with pytest.raises(SystemExit):
            bridge.cmd_paid_proof_preflight(args)

        err = capsys.readouterr().err
        assert "must be exactly 8192" in err

    def test_parser_exposes_no_security_override_flags(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        s = sub.add_parser("paid-proof-preflight")
        s.add_argument("task_id", type=int)
        s.add_argument("--grant-id", required=True)
        s.add_argument("--proof-lock-path", required=True)
        s.add_argument("--proof-lock-blob-sha", required=True)

        forbidden_flags = [
            "--api-key",
            "--token",
            "--authorization-header",
            "--cookie",
            "--endpoint",
            "--base-url",
            "--provider-id",
            "--model-id",
            "--asset-dir",
            "--ledger-path",
            "--workspace-id",
            "--max-calls",
            "--allow-paid-api",
            "--consume",
            "--dispatch",
            "--retry",
        ]
        registered_actions = [action.option_strings for action in s._actions]
        all_options = [opt for opts in registered_actions for opt in opts]
        for forbidden in forbidden_flags:
            assert forbidden not in all_options
