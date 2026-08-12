from __future__ import annotations

import json
import os
import tempfile

import pytest

from src.agent.integrity_verifier import RunIntegrityVerifier
from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import RunState
from src.core.idempotency_contract import RecordKey
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.types import ToolCall, ToolResult, ToolStatus


def test_verify_valid_session_report() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        cm = CheckpointManager(db_path=db_path)
        run_id = "run-valid-verify"

        cm.log_run_started(run_id, "sys", "user")
        cm.log_llm_requested(run_id, iteration=1)
        cm.log_llm_responded(run_id, iteration=1, content="final answer", num_tool_calls=0)

        report = RunIntegrityVerifier.verify(db_path, run_id)
        assert report.valid is True
        assert report.run_id == run_id
        assert report.state == RunState.COMPLETED
        assert report.checkpoint_count == 3
        assert report.issues == []


def test_verify_sequence_gap_detected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        run_id = "run-seq-gap"

        events = [
            {
                "run_id": run_id,
                "sequence_id": 1,
                "timestamp": 100.0,
                "event_type": "RUN_STARTED",
                "payload": {},
            },
            {
                "run_id": run_id,
                "sequence_id": 3,  # Sequence gap 1 -> 3
                "timestamp": 101.0,
                "event_type": "LLM_REQUESTED",
                "payload": {},
            },
        ]
        with open(db_path, "w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt) + "\n")

        report = RunIntegrityVerifier.verify(db_path, run_id)
        assert report.valid is False
        assert any("Sequence_id gap" in issue for issue in report.issues)


def test_verify_corrupt_json_line() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        run_id = "run-corrupt-json"

        with open(db_path, "w", encoding="utf-8") as f:
            f.write(f'{{"run_id": "{run_id}", "sequence_id": 1, "timestamp": 100.0, "event_type": "RUN_STARTED"}}\n')
            f.write("NOT_VALID_JSON_LINE\n")

        report = RunIntegrityVerifier.verify(db_path, run_id)
        assert report.valid is False
        assert any("Invalid JSON syntax" in issue for issue in report.issues)


def test_verify_idempotency_store_consistency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cp_path = os.path.join(tmpdir, "checkpoints.jsonl")
        idem_path = os.path.join(tmpdir, "idempotency.jsonl")

        cm = CheckpointManager(db_path=cp_path)
        store = JsonlIdempotencyStore(db_path=idem_path)
        run_id = "run-idem-check"

        cm.log_run_started(run_id, "sys", "usr")
        cm.log_llm_requested(run_id, iteration=1)
        cm.log_llm_responded(
            run_id,
            iteration=1,
            content="tooling",
            num_tool_calls=1,
            tool_calls=[{"call_id": "c1", "name": "dummy_tool", "arguments": {}}],
        )
        cm.log_tool_result_received(
            run_id, "c1", status="success", tool_name="dummy_tool", result={"res": 1}
        )

        # In checkpoints, c1 is marked completed, but store does NOT have record!
        report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report.valid is False
        assert any("missing" in issue and "IdempotencyStore" in issue for issue in report.issues)

        # Now complete record in store
        call = ToolCall(name="dummy_tool", arguments={}, call_id="c1", run_id=run_id)
        key = RecordKey("tool:dummy_tool", call.idempotency_key)
        store.claim(key, "worker-1")
        res = ToolResult(call_id="c1", run_id=run_id, tool_name="dummy_tool", status=ToolStatus.SUCCESS)
        store.complete(key, "worker-1", data={"result": res.to_dict()})

        # Re-verify -> valid is True!
        report2 = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report2.valid is True


def test_read_only_invariant() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        cm = CheckpointManager(db_path=db_path)
        run_id = "run-ro-verify"

        cm.log_run_started(run_id, "sys", "usr")
        cm.log_llm_requested(run_id, iteration=1)

        size_before = os.path.getsize(db_path)
        mtime_before = os.path.getmtime(db_path)

        report = RunIntegrityVerifier.verify(db_path, run_id)
        assert report.valid is True

        size_after = os.path.getsize(db_path)
        mtime_after = os.path.getmtime(db_path)

        # Read-only invariant: file size and mtime are 100% identical!
        assert size_after == size_before
        assert mtime_after == mtime_before
