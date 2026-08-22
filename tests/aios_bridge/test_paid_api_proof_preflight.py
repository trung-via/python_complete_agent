"""Unit tests for PaidApiProofPreflightReceipt and preflight logic (TASK-059 / M11.3B)."""
import hashlib
import json
import os
from pathlib import Path
import pytest

from src.aios_bridge.continuity.dispatch import DispatchActorKind
from src.aios_bridge.continuity.state import BrainOperation
from src.aios_bridge.minimax_m3_proof_lock import MiniMaxM3ProofLock
from src.aios_bridge.paid_api_grant import PaidApiGrant
from src.aios_bridge.paid_api_proof_preflight import (
    PaidApiProofPreflightReceipt,
    PaidApiProofPreflightError,
    PREFLIGHT_SCHEMA_VERSION,
    probe_ledger_durability,
    build_paid_api_proof_preflight_receipt,
)


def _valid_receipt_dict() -> dict[str, object]:
    return {
        "schema_version": "1",
        "task_id": "TASK-059",
        "grant_id": "grant-task-059-abc123",
        "grant_fingerprint": "a" * 64,
        "workspace_id": "e" * 64,
        "brain_id": "minimax",
        "provider_id": "minimax",
        "model_id": "MiniMax-M3",
        "runtime_main_sha": "1" * 40,
        "control_commit_sha": "2" * 40,
        "authorized_artifact_path": ".ai/tasks/TASK-059.md",
        "authorized_artifact_blob_sha": "3" * 40,
        "proof_lock_path": ".ai/context/proof_lock.json",
        "proof_lock_blob_sha": "4" * 40,
        "proof_lock_fingerprint": "b" * 64,
        "endpoint_url": "https://api.minimax.io/v1/text/chatcompletion_v2",
        "credential_env_name": "MINIMAX_API_KEY",
        "credential_present": True,
        "source_revision": "3a41b311ffa5719cef48fed3974ccf2cc03733ea",
        "chat_template_sha256": "c" * 64,
        "tokenizer_sha256": "d" * 64,
        "counter_id": f"minimax-m3-local:3a41b311ffa5719cef48fed3974ccf2cc03733ea:{'c' * 64}:{'d' * 64}",
        "jinja2_version": "3.1.6",
        "tokenizers_version": "0.23.1",
        "requests_version": "2.32.3",
        "ledger_logical_path": "paid_api_usage/TASK-059/grant_hash.jsonl",
        "ledger_ready": True,
        "grant_active": True,
        "grant_consumed": False,
        "paid_dispatch_enabled": False,
        "provider_call_started": False,
    }


def _valid_grant() -> PaidApiGrant:
    return PaidApiGrant(
        schema_version="1",
        grant_id="grant-task-059-abc123",
        task_id="TASK-059",
        actor_kind=DispatchActorKind.BRAIN,
        brain_id="minimax",
        provider_id="minimax",
        model_id="MiniMax-M3",
        brain_operation=BrainOperation.PLAN,
        authorized_artifact_path=".ai/tasks/TASK-059.md",
        authorized_artifact_blob_sha="3" * 40,
        max_input_tokens=1000,
        max_output_tokens=1000,
        max_calls=1,
        expires_at_epoch_seconds=2000000000,
        workspace_id="e" * 64,
    )


def _valid_proof_lock() -> MiniMaxM3ProofLock:
    return MiniMaxM3ProofLock(
        schema_version="1",
        provider_id="minimax",
        model_id="MiniMax-M3",
        endpoint_url="https://api.minimax.io/v1/text/chatcompletion_v2",
        credential_env_name="MINIMAX_API_KEY",
        source_repository="MiniMaxAI/MiniMax-M3",
        source_revision="3a41b311ffa5719cef48fed3974ccf2cc03733ea",
        chat_template_path="chat_template.jinja",
        chat_template_sha256="c" * 64,
        tokenizer_path="tokenizer.json",
        tokenizer_sha256="d" * 64,
        jinja2_version="3.1.6",
        tokenizers_version="0.23.1",
        requests_version="2.32.3",
    )


class TestPaidApiProofPreflightReceipt:
    def test_valid_receipt_construction(self):
        data = _valid_receipt_dict()
        receipt = PaidApiProofPreflightReceipt.from_dict(data)
        assert receipt.schema_version == PREFLIGHT_SCHEMA_VERSION
        assert receipt.task_id == "TASK-059"
        assert receipt.grant_id == "grant-task-059-abc123"
        assert receipt.credential_present is True
        assert receipt.ledger_ready is True
        assert receipt.grant_active is True
        assert receipt.grant_consumed is False
        assert receipt.paid_dispatch_enabled is False
        assert receipt.provider_call_started is False

    def test_canonical_json_and_fingerprint_deterministic(self):
        data = _valid_receipt_dict()
        receipt = PaidApiProofPreflightReceipt.from_dict(data)
        fp1 = receipt.fingerprint()
        fp2 = receipt.fingerprint()
        assert fp1 == fp2
        assert len(fp1) == 64

        json_str = receipt.to_canonical_json()
        receipt2 = PaidApiProofPreflightReceipt.from_json(json_str)
        assert receipt == receipt2
        assert receipt.fingerprint() == receipt2.fingerprint()

    def test_rejects_duplicate_json_keys(self):
        raw = '{"schema_version":"1","schema_version":"1"}'
        with pytest.raises(PaidApiProofPreflightError, match="duplicate"):
            PaidApiProofPreflightReceipt.from_json(raw)

    def test_rejects_absolute_path_in_ledger_logical_path(self):
        data = _valid_receipt_dict()
        data["ledger_logical_path"] = r"C:\Users\TRUNG\AppData\Local\aios-bridge\ledger.jsonl"
        with pytest.raises(PaidApiProofPreflightError, match="ledger_logical_path"):
            PaidApiProofPreflightReceipt.from_dict(data)

        data["ledger_logical_path"] = "/home/user/aios-bridge/ledger.jsonl"
        with pytest.raises(PaidApiProofPreflightError, match="ledger_logical_path"):
            PaidApiProofPreflightReceipt.from_dict(data)

    def test_rejects_invalid_proof_lock_path(self):
        data = _valid_receipt_dict()
        data["proof_lock_path"] = "outside/proof_lock.json"
        with pytest.raises(PaidApiProofPreflightError, match="proof_lock_path"):
            PaidApiProofPreflightReceipt.from_dict(data)

    def test_rejects_consumed_or_dispatch_enabled(self):
        data = _valid_receipt_dict()
        data["grant_consumed"] = True
        with pytest.raises(PaidApiProofPreflightError, match="grant_consumed"):
            PaidApiProofPreflightReceipt.from_dict(data)

        data = _valid_receipt_dict()
        data["paid_dispatch_enabled"] = True
        with pytest.raises(PaidApiProofPreflightError, match="paid_dispatch_enabled"):
            PaidApiProofPreflightReceipt.from_dict(data)

        data = _valid_receipt_dict()
        data["provider_call_started"] = True
        with pytest.raises(PaidApiProofPreflightError, match="provider_call_started"):
            PaidApiProofPreflightReceipt.from_dict(data)

    def test_builder_constructs_valid_receipt(self):
        grant = _valid_grant()
        lock = _valid_proof_lock()
        receipt = build_paid_api_proof_preflight_receipt(
            task_id="TASK-059",
            grant=grant,
            runtime_main_sha="1" * 40,
            control_commit_sha="2" * 40,
            proof_lock_path=".ai/context/proof_lock.json",
            proof_lock_blob_sha="4" * 40,
            proof_lock=lock,
            counter_id=f"minimax-m3-local:3a41b311ffa5719cef48fed3974ccf2cc03733ea:{'c' * 64}:{'d' * 64}",
            ledger_logical_path="paid_api_usage/TASK-059/grant_hash.jsonl",
            ledger_ready=True,
            credential_present=True,
        )
        assert receipt.task_id == "TASK-059"
        assert receipt.grant_id == grant.grant_id
        assert receipt.grant_fingerprint == grant.fingerprint()
        assert receipt.proof_lock_fingerprint == lock.fingerprint()
        assert receipt.ledger_ready is True
        assert receipt.grant_active is True
        assert receipt.grant_consumed is False
        assert receipt.paid_dispatch_enabled is False
        assert receipt.provider_call_started is False

    def test_builder_rejects_subclass_proof_lock(self):
        grant = _valid_grant()

        class SubclassProofLock(MiniMaxM3ProofLock):
            pass

        lock = SubclassProofLock(**_valid_proof_lock().to_dict())
        with pytest.raises(PaidApiProofPreflightError, match="exact MiniMaxM3ProofLock"):
            build_paid_api_proof_preflight_receipt(
                task_id="TASK-059",
                grant=grant,
                runtime_main_sha="1" * 40,
                control_commit_sha="2" * 40,
                proof_lock_path=".ai/context/proof_lock.json",
                proof_lock_blob_sha="4" * 40,
                proof_lock=lock,
                counter_id=f"minimax-m3-local:3a41b311ffa5719cef48fed3974ccf2cc03733ea:{'c' * 64}:{'d' * 64}",
                ledger_logical_path="paid_api_usage/TASK-059/grant_hash.jsonl",
                ledger_ready=True,
                credential_present=True,
            )

    def test_probe_ledger_durability(self, tmp_path: Path):
        ledger_path = tmp_path / "paid_api_usage" / "TASK-059" / "ledger.jsonl"
        assert probe_ledger_durability(ledger_path) is True
        # Verify ledger file itself was NOT created / touched
        assert not ledger_path.exists()
        # Verify parent dir exists
        assert ledger_path.parent.is_dir()

    def test_probe_ledger_durability_failure_is_sanitized(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        ledger_path = tmp_path / "paid_api_usage" / "TASK-059" / "ledger.jsonl"
        sentinel_path = "/secret/internal/absolute/user/runtime/path/never_leak"

        def failing_open(*args, **kwargs):
            raise OSError(f"Permission denied: {sentinel_path}")

        import builtins
        monkeypatch.setattr(builtins, "open", failing_open)
        with pytest.raises(PaidApiProofPreflightError) as exc_info:
            probe_ledger_durability(ledger_path)

        assert sentinel_path not in str(exc_info.value)
        assert "cannot write probe file or fsync directory" in str(exc_info.value)
