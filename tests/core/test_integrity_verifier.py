import json
import os
import tempfile
import pytest

from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import RunState
from src.core.idempotency_contract import RecordKey
from src.core.idempotency_store_v2 import JsonlIdempotencyStore
from src.core.integrity_verifier import RunIntegrityReport, RunIntegrityVerifier
from src.core.recovery_diagnostics import RecoveryPotential
from src.core.types import ToolCall, ToolResult, ToolStatus


def test_valid_run_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)

        run_id = manager.log_task_start("test context")
        manager.log_llm_requested(run_id, iteration=1)
        manager.log_llm_responded(run_id, iteration=1, content="hello", num_tool_calls=0)
        manager.log_task_end(run_id, success=True, retry_count=0)

        report = RunIntegrityVerifier.verify(db_path, run_id)

        assert isinstance(report, RunIntegrityReport)
        assert report.valid is True
        assert report.run_id == run_id
        assert report.state == RunState.COMPLETED
        assert report.checkpoint_count == 4
        assert report.pending_tool_calls == 0
        assert report.completed_tool_calls == 0
        assert report.recovery_potential == RecoveryPotential.COMPLETED
        assert report.issues == ()
        assert report.to_dict()["valid"] is True


def test_sequence_gap_detected():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {
                "run_id": "run_1",
                "sequence_id": 1,
                "timestamp": 100.0,
                "event_type": "TASK_START",
                "payload": {"task_context": "x"},
            },
            {
                "run_id": "run_1",
                "sequence_id": 3,  # GAP: expected 2
                "timestamp": 101.0,
                "event_type": "LLM_REQUESTED",
                "payload": {"iteration": 1},
            },
        ]
        with open(db_path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        report = RunIntegrityVerifier.verify(db_path, "run_1")
        assert report.valid is False
        assert len(report.issues) > 0
        assert any("Sequence_id gap" in issue for issue in report.issues)


def test_timestamp_rollback_detected():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {
                "run_id": "run_1",
                "sequence_id": 1,
                "timestamp": 200.0,
                "event_type": "TASK_START",
                "payload": {"task_context": "x"},
            },
            {
                "run_id": "run_1",
                "sequence_id": 2,
                "timestamp": 100.0,  # ROLLBACK: 100 < 200
                "event_type": "LLM_REQUESTED",
                "payload": {"iteration": 1},
            },
        ]
        with open(db_path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        report = RunIntegrityVerifier.verify(db_path, "run_1")
        assert report.valid is False
        assert any("Timestamp rollback" in issue for issue in report.issues)


def test_invalid_state_transition_detected():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {
                "run_id": "run_1",
                "sequence_id": 1,
                "timestamp": 100.0,
                "event_type": "TASK_START",
                "payload": {"task_context": "x"},
            },
            {
                "run_id": "run_1",
                "sequence_id": 2,
                "timestamp": 101.0,
                "event_type": "RUN_COMPLETED",
                "payload": {},
            },
            {
                "run_id": "run_1",
                "sequence_id": 3,
                "timestamp": 102.0,
                "event_type": "LLM_REQUESTED",  # Invalid transition from COMPLETED -> LLM_WAITING
                "payload": {"iteration": 1},
            },
        ]
        with open(db_path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        report = RunIntegrityVerifier.verify(db_path, "run_1")
        assert report.valid is False
        assert any("State transition error" in issue for issue in report.issues)


def test_terminal_inconsistency_completed_with_pending_tools():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {
                "run_id": "run_1",
                "sequence_id": 1,
                "timestamp": 100.0,
                "event_type": "TASK_START",
                "payload": {"task_context": "x"},
            },
            {
                "run_id": "run_1",
                "sequence_id": 2,
                "timestamp": 101.0,
                "event_type": "LLM_REQUESTED",
                "payload": {"iteration": 1},
            },
            {
                "run_id": "run_1",
                "sequence_id": 3,
                "timestamp": 102.0,
                "event_type": "LLM_RESPONDED",
                "payload": {
                    "content": "call tool",
                    "num_tool_calls": 1,
                    "tool_calls": [{"call_id": "call_1", "name": "dummy", "arguments": {}}],
                },
            },
            {
                "run_id": "run_1",
                "sequence_id": 4,
                "timestamp": 103.0,
                "event_type": "RUN_COMPLETED",  # COMPLETED state while call_1 is still pending!
                "payload": {},
            },
        ]
        with open(db_path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        report = RunIntegrityVerifier.verify(db_path, "run_1")
        assert report.valid is False
        assert any("unhandled pending tool call" in issue for issue in report.issues)


def test_corrupt_json_detected():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        with open(db_path, "w", encoding="utf-8") as f:
            f.write('{"run_id": "run_1", "sequence_id": 1, "timestamp": 100.0, "event_type": "TASK_START"}\n')
            f.write("NOT_VALID_JSON_STRING\n")

        report = RunIntegrityVerifier.verify(db_path, "run_1")
        assert report.valid is False
        assert any("Invalid JSON syntax" in issue for issue in report.issues)


def test_idempotency_store_cross_verification():
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

        # Missing record in IdempotencyStore -> valid is False
        report = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report.valid is False
        assert any("missing" in issue and "IdempotencyStore" in issue for issue in report.issues)

        # Complete record in IdempotencyStore
        call = ToolCall(name="dummy_tool", arguments={}, call_id="c1", run_id=run_id)
        key = RecordKey("tool:dummy_tool", call.idempotency_key)
        store.claim(key, "worker-1")
        res = ToolResult(call_id="c1", run_id=run_id, tool_name="dummy_tool", status=ToolStatus.SUCCESS)
        store.complete(key, "worker-1", data={"result": res.to_dict()})

        # Re-verify -> valid is True
        report2 = RunIntegrityVerifier.verify(cp_path, run_id, idempotency_store=store)
        assert report2.valid is True


def test_read_only_invariant():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)

        run_id = manager.log_task_start("test context")
        manager.log_task_end(run_id, success=True, retry_count=0)

        with open(db_path, "rb") as f:
            before_content = f.read()

        report = RunIntegrityVerifier.verify(db_path, run_id)
        assert report.valid is True

        with open(db_path, "rb") as f:
            after_content = f.read()

        assert before_content == after_content, "IntegrityVerifier mutated file content!"


def test_determinism_repeated_verify_identical_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)

        run_id = manager.log_task_start("test context")
        manager.log_llm_requested(run_id, iteration=1)

        report1 = RunIntegrityVerifier.verify(db_path, run_id)
        report2 = RunIntegrityVerifier.verify(db_path, run_id)

        assert report1 == report2
        assert report1.to_dict() == report2.to_dict()


def test_interleaved_runs_isolation():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {"run_id": "run_A", "sequence_id": 1, "timestamp": 100.0, "event_type": "TASK_START", "payload": {}},
            {"run_id": "run_B", "sequence_id": 1, "timestamp": 100.5, "event_type": "TASK_START", "payload": {}},
            {"run_id": "run_A", "sequence_id": 2, "timestamp": 101.0, "event_type": "LLM_REQUESTED", "payload": {}},
            {"run_id": "run_B", "sequence_id": 2, "timestamp": 101.5, "event_type": "LLM_REQUESTED", "payload": {}},
            {"run_id": "run_A", "sequence_id": 3, "timestamp": 102.0, "event_type": "LLM_RESPONDED", "payload": {"num_tool_calls": 0}},
        ]
        with open(db_path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        report_a = RunIntegrityVerifier.verify(db_path, "run_A")
        assert report_a.valid is True
        assert report_a.checkpoint_count == 3
        assert report_a.state == RunState.COMPLETED

        report_b = RunIntegrityVerifier.verify(db_path, "run_B")
        assert report_b.valid is True
        assert report_b.checkpoint_count == 2
        assert report_b.state == RunState.LLM_WAITING


def test_infrastructure_io_error_propagates():
    db_path = "/non_existent_directory_xxx/checkpoints.jsonl"
    with pytest.raises(FileNotFoundError):
        RunIntegrityVerifier.verify(db_path, "run_1")
