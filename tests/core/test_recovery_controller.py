import json
import os
import tempfile
import pytest

from src.core.checkpoint import CheckpointManager
from src.core.checkpoint_contract import CheckpointCorruptionError, RunState
from src.core.errors import RecoveryStateError
from src.core.recovery_controller import RecoveryController, RecoveryInspection
from src.core.recovery_diagnostics import RecoveryPotential


def test_inspect_valid_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)

        run_id = manager.log_task_start("test prompt")
        manager.log_llm_requested(run_id, iteration=1)
        manager.log_llm_responded(run_id, iteration=1, content="final response", num_tool_calls=0)

        inspection = RecoveryController.inspect(db_path, run_id)

        assert isinstance(inspection, RecoveryInspection)
        assert inspection.valid is True
        assert inspection.can_resume is True
        assert inspection.diagnostics.recovery_potential == RecoveryPotential.COMPLETED
        assert inspection.integrity_report.state == RunState.COMPLETED
        assert inspection.to_dict()["valid"] is True


def test_inspect_corrupt_run_returns_invalid():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {"run_id": "run_c", "sequence_id": 1, "timestamp": 100.0, "event_type": "TASK_START", "payload": {}},
            {"run_id": "run_c", "sequence_id": 3, "timestamp": 101.0, "event_type": "LLM_REQUESTED", "payload": {}},  # Gap!
        ]
        with open(db_path, "w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        inspection = RecoveryController.inspect(db_path, "run_c")

        assert inspection.valid is False
        assert inspection.can_resume is False
        assert len(inspection.integrity_report.issues) > 0


def test_inspect_io_error_propagates():
    db_path = "/non_existent_directory_abc/checkpoints.jsonl"
    with pytest.raises(FileNotFoundError):
        RecoveryController.inspect(db_path, "run_1")


@pytest.mark.asyncio
async def test_resume_completed_returns_cached_result():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)

        run_id = manager.log_task_start("test prompt")
        manager.log_llm_requested(run_id, iteration=1)
        manager.log_llm_responded(run_id, iteration=1, content="cached answer", num_tool_calls=0)

        class DummyLoop:
            def __init__(self, db):
                self.checkpoints = manager
                self.executed = False

            async def resume(self, rid):
                self.executed = True
                return "fresh answer"

        loop = DummyLoop(db_path)
        res = await RecoveryController.resume(loop, run_id)

        assert res == "cached answer"
        assert loop.executed is False, "Should not execute loop.resume for COMPLETED run!"


@pytest.mark.asyncio
async def test_resume_non_recoverable_raises_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)

        run_id = manager.log_task_start("test prompt")
        manager.log_run_failed(run_id, "fatal error")

        class DummyLoop:
            def __init__(self, db):
                self.checkpoints = manager

            async def resume(self, rid):
                pass

        loop = DummyLoop(db_path)
        with pytest.raises(RecoveryStateError, match="terminal state"):
            await RecoveryController.resume(loop, run_id)


@pytest.mark.asyncio
async def test_resume_corrupt_raises_checkpoint_corruption_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        with open(db_path, "w", encoding="utf-8") as f:
            f.write('{"run_id": "r1", "sequence_id": 1, "timestamp": 100.0, "event_type": "TASK_START"}\n')
            f.write("CORRUPT_JSON\n")

        class DummyLoop:
            def __init__(self, db):
                self.checkpoints = CheckpointManager(db_path=db_path)

            async def resume(self, rid):
                pass

        loop = DummyLoop(db_path)
        with pytest.raises(CheckpointCorruptionError, match="integrity verification failed"):
            await RecoveryController.resume(loop, "r1")


@pytest.mark.asyncio
async def test_resume_recoverable_delegates_to_agent_loop():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)

        run_id = manager.log_task_start("test prompt")
        manager.log_llm_requested(run_id, iteration=1)

        class DummyLoop:
            def __init__(self, db):
                self.checkpoints = manager
                self.resumed_id = None

            async def resume(self, rid):
                self.resumed_id = rid
                return "resumed success"

        loop = DummyLoop(db_path)
        res = await RecoveryController.resume(loop, run_id)

        assert res == "resumed success"
        assert loop.resumed_id == run_id
