from concurrent.futures import ThreadPoolExecutor
import os
import tempfile
import pytest

from src.core.cancellation import (
    CancellationReason,
    CancellationToken,
    ControlEvent,
    RunCancellationController,
)
from src.core.checkpoint import CheckpointManager
from src.core.errors import SystemStateError


def test_token_initial_state():
    token = CancellationToken("run_1")
    assert token.run_id == "run_1"
    assert token.is_cancelled is False
    assert token.reason is None


def test_token_cancel_and_reason():
    token = CancellationToken("run_1")
    reason = CancellationReason(event=ControlEvent.CANCEL, reason="user clicked stop")
    token._mark_cancelled(reason)

    assert token.is_cancelled is True
    assert token.reason == reason
    assert token.reason.to_dict()["control_event"] == "CANCEL"


def test_controller_cancel_commits_durable_checkpoint_first():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)
        controller = RunCancellationController(manager)

        run_id = manager.log_task_start("test prompt")
        token = controller.cancel(run_id, reason="test cancellation")

        assert token.is_cancelled is True
        assert token.reason.event == ControlEvent.CANCEL
        assert token.reason.reason == "test cancellation"

        # Verify durable checkpoint written
        with open(db_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert any("RUN_HALTED" in line and "CANCEL: test cancellation" in line for line in lines)


def test_controller_cancel_idempotency():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)
        controller = RunCancellationController(manager)

        run_id = manager.log_task_start("test prompt")
        token1 = controller.cancel(run_id, reason="first cancel")
        token2 = controller.cancel(run_id, reason="second cancel")

        assert token1 is token2
        assert token1.is_cancelled is True
        assert token1.reason.reason == "first cancel"

        # Count RUN_HALTED occurrences in file (should be exactly 1)
        with open(db_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        halted_count = sum(1 for line in lines if "RUN_HALTED" in line)
        assert halted_count == 1


def test_controller_concurrent_cancel():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        manager = CheckpointManager(db_path=db_path)
        controller = RunCancellationController(manager)

        run_id = manager.log_task_start("test prompt")

        def do_cancel(i):
            return controller.cancel(run_id, reason=f"cancel_{i}")

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(do_cancel, i) for i in range(5)]
            results = [f.result() for f in futures]

        for tok in results:
            assert tok.is_cancelled is True


def test_controller_checkpoint_write_failure_preserves_uncancelled_memory():
    manager = CheckpointManager(db_path="/invalid_dir_xxx/checkpoints.jsonl")
    controller = RunCancellationController(manager)

    with pytest.raises(SystemStateError):
        controller.cancel("run_fail", reason="error test")

    # In-memory token must NOT be marked cancelled if checkpoint write failed!
    token = controller.get_token("run_fail")
    assert token.is_cancelled is False
