"""
Tests for Recovery Analyzer (RecoveryAnalyzer, RecoveryDiagnostics)

Test contract:
1. Read-only analysis (no filesystem mutations)
2. Deterministic (same input → same output)
3. All 4 classifications: COMPLETED, RECOVERABLE, NON_RECOVERABLE, CORRUPT
4. Fail-closed on corruption
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List

import pytest

from src.core.checkpoint_contract import (
    CheckpointEvent,
    CheckpointEventType,
    FailureDomain,
    RunState,
)
from src.core.recovery_diagnostics import (
    RecoveryAnalyzer,
    RecoveryDiagnostics,
    RecoveryPotential,
)


@pytest.fixture
def tmp_checkpoint_file():
    """Create temporary checkpoint file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp_path = f.name
    yield tmp_path
    if os.path.exists(tmp_path):
        os.remove(tmp_path)


def _write_checkpoint_events(
    file_path: str, run_id: str, events: List[Dict[str, Any]]
) -> None:
    """Helper to write checkpoint events to JSONL file."""
    with open(file_path, "a", encoding="utf-8") as f:
        for idx, event_data in enumerate(events, start=1):
            event = CheckpointEvent(
                run_id=run_id,
                sequence_id=idx,
                timestamp=float(idx),
                event_type=CheckpointEventType(event_data["event_type"]),
                payload=event_data.get("payload", {}),
            )
            f.write(json.dumps(event.to_dict()) + "\n")


class TestRecoveryAnalyzer:
    """Test RecoveryAnalyzer deterministic classification."""

    def test_analyze_completed_run(self, tmp_checkpoint_file):
        """Classify run that completed successfully."""
        run_id = "run-completed-001"

        events = [
            {"event_type": "RUN_STARTED", "payload": {}},
            {"event_type": "LLM_REQUESTED", "payload": {"iteration": 1}},
            {
                "event_type": "LLM_RESPONDED",
                "payload": {"content": "final answer", "num_tool_calls": 0},
            },
            {"event_type": "LLM_FINAL_RESPONSE", "payload": {}},
            {"event_type": "RUN_COMPLETED", "payload": {}},
        ]
        _write_checkpoint_events(tmp_checkpoint_file, run_id, events)

        # Analyze
        diag = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)

        # Assertions
        assert diag.run_id == run_id
        assert diag.current_state == RunState.COMPLETED
        assert diag.recovery_potential == RecoveryPotential.COMPLETED
        assert diag.can_resume() is True
        assert diag.is_deterministic() is True
        assert diag.error_message == ""

    def test_analyze_recoverable_run(self, tmp_checkpoint_file):
        """Classify run that can continue from current state."""
        run_id = "run-recoverable-001"

        events = [
            {"event_type": "RUN_STARTED", "payload": {}},
            {"event_type": "LLM_REQUESTED", "payload": {"iteration": 1}},
        ]
        _write_checkpoint_events(tmp_checkpoint_file, run_id, events)

        # Analyze
        diag = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)

        # Assertions
        assert diag.run_id == run_id
        assert diag.current_state == RunState.LLM_WAITING
        assert diag.recovery_potential == RecoveryPotential.RECOVERABLE
        assert diag.can_resume() is True
        assert diag.is_deterministic() is True

    def test_analyze_non_recoverable_run_failed(self, tmp_checkpoint_file):
        """Classify run that failed (terminal state)."""
        run_id = "run-failed-001"

        events = [
            {"event_type": "RUN_STARTED", "payload": {}},
            {"event_type": "LLM_REQUESTED", "payload": {"iteration": 1}},
            {
                "event_type": "RUN_FAILED",
                "payload": {"error": "LLM rate limit exceeded"},
            },
        ]
        _write_checkpoint_events(tmp_checkpoint_file, run_id, events)

        # Analyze
        diag = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)

        # Assertions
        assert diag.run_id == run_id
        assert diag.current_state == RunState.FAILED
        assert diag.recovery_potential == RecoveryPotential.NON_RECOVERABLE
        assert diag.can_resume() is False
        assert "FAILED terminal state" in diag.error_message

    def test_analyze_non_recoverable_run_halted(self, tmp_checkpoint_file):
        """Classify run that halted due to safety limit."""
        run_id = "run-halted-001"

        events = [
            {"event_type": "RUN_STARTED", "payload": {}},
            {"event_type": "LLM_REQUESTED", "payload": {"iteration": 1}},
            {"event_type": "LLM_REQUESTED", "payload": {"iteration": 2}},
            {
                "event_type": "RUN_HALTED",
                "payload": {"reason": "MAX_ITERATIONS_REACHED"},
            },
        ]
        _write_checkpoint_events(tmp_checkpoint_file, run_id, events)

        # Analyze
        diag = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)

        # Assertions
        assert diag.run_id == run_id
        assert diag.current_state == RunState.HALTED
        assert diag.recovery_potential == RecoveryPotential.NON_RECOVERABLE
        assert diag.can_resume() is False
        assert "HALTED" in diag.error_message

    def test_analyze_corrupt_checkpoint_missing_run(self, tmp_checkpoint_file):
        """Fail-closed when checkpoint for run_id missing."""
        run_id = "run-missing-001"
        other_run_id = "run-other-001"

        events = [
            {"event_type": "RUN_STARTED", "payload": {}},
            {"event_type": "RUN_COMPLETED", "payload": {}},
        ]
        _write_checkpoint_events(tmp_checkpoint_file, other_run_id, events)

        # Analyze missing run_id
        diag = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)

        # Assertions
        assert diag.run_id == run_id
        assert diag.recovery_potential == RecoveryPotential.CORRUPT
        assert diag.can_resume() is False
        assert diag.is_deterministic() is False
        assert "No checkpoint events found" in diag.error_message

    def test_analyze_deterministic_repeated_calls(self, tmp_checkpoint_file):
        """Verify repeated analysis produces identical results (deterministic)."""
        run_id = "run-deterministic-001"

        events = [
            {"event_type": "RUN_STARTED", "payload": {}},
            {"event_type": "LLM_REQUESTED", "payload": {"iteration": 1}},
            {
                "event_type": "LLM_RESPONDED",
                "payload": {"content": "answer", "num_tool_calls": 0},
            },
            {"event_type": "RUN_COMPLETED", "payload": {}},
        ]
        _write_checkpoint_events(tmp_checkpoint_file, run_id, events)

        # Analyze multiple times
        diag1 = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)
        diag2 = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)
        diag3 = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)

        # All should be identical
        assert diag1.to_dict() == diag2.to_dict() == diag3.to_dict()
        assert diag1.recovery_potential == diag2.recovery_potential
        assert diag1.current_state == diag2.current_state

    def test_analyze_no_filesystem_mutation(self, tmp_checkpoint_file):
        """Verify analyzer never mutates checkpoint file."""
        import time

        run_id = "run-mutation-test-001"

        events = [
            {"event_type": "RUN_STARTED", "payload": {}},
            {"event_type": "LLM_REQUESTED", "payload": {"iteration": 1}},
        ]
        _write_checkpoint_events(tmp_checkpoint_file, run_id, events)

        # Record original state
        with open(tmp_checkpoint_file, "r") as f:
            original_content = f.read()
        original_size = os.path.getsize(tmp_checkpoint_file)
        original_mtime = os.path.getmtime(tmp_checkpoint_file)

        # Analyze
        time.sleep(0.01)  # Ensure time passes
        diag = RecoveryAnalyzer.analyze(run_id, tmp_checkpoint_file)

        # Verify no mutation
        with open(tmp_checkpoint_file, "r") as f:
            final_content = f.read()
        final_size = os.path.getsize(tmp_checkpoint_file)
        final_mtime = os.path.getmtime(tmp_checkpoint_file)

        assert original_content == final_content, "File content changed!"
        assert original_size == final_size, "File size changed!"
        assert (
            original_mtime == final_mtime
        ), "File modification time changed (file was written to)!"


class TestRecoveryDiagnosticsContract:
    """Test RecoveryDiagnostics dataclass contract."""

    def test_can_resume_completed(self):
        """COMPLETED is resumable."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.COMPLETED,
            recovery_potential=RecoveryPotential.COMPLETED,
        )
        assert diag.can_resume() is True

    def test_can_resume_recoverable(self):
        """RECOVERABLE is resumable."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.LLM_WAITING,
            recovery_potential=RecoveryPotential.RECOVERABLE,
        )
        assert diag.can_resume() is True

    def test_cannot_resume_non_recoverable(self):
        """NON_RECOVERABLE is not resumable."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.FAILED,
            recovery_potential=RecoveryPotential.NON_RECOVERABLE,
        )
        assert diag.can_resume() is False

    def test_cannot_resume_corrupt(self):
        """CORRUPT is not resumable."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.PENDING,
            recovery_potential=RecoveryPotential.CORRUPT,
        )
        assert diag.can_resume() is False

    def test_is_deterministic_completed(self):
        """COMPLETED is deterministic."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.COMPLETED,
            recovery_potential=RecoveryPotential.COMPLETED,
        )
        assert diag.is_deterministic() is True

    def test_is_deterministic_recoverable(self):
        """RECOVERABLE is deterministic."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.LLM_WAITING,
            recovery_potential=RecoveryPotential.RECOVERABLE,
        )
        assert diag.is_deterministic() is True

    def test_is_deterministic_non_recoverable(self):
        """NON_RECOVERABLE is deterministic."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.FAILED,
            recovery_potential=RecoveryPotential.NON_RECOVERABLE,
        )
        assert diag.is_deterministic() is True

    def test_is_not_deterministic_corrupt(self):
        """CORRUPT is not deterministic (may change on retry)."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.PENDING,
            recovery_potential=RecoveryPotential.CORRUPT,
        )
        assert diag.is_deterministic() is False

    def test_to_dict_serialization(self):
        """RecoveryDiagnostics serializes to dict correctly."""
        diag = RecoveryDiagnostics(
            run_id="r1",
            current_state=RunState.FAILED,
            recovery_potential=RecoveryPotential.NON_RECOVERABLE,
            failure_domain=FailureDomain.LLM_PROVIDER,
            error_message="LLM rate limit exceeded",
            pending_tool_calls=0,
            completed_tool_calls=2,
        )

        d = diag.to_dict()

        assert d["run_id"] == "r1"
        assert d["current_state"] == "FAILED"
        assert d["recovery_potential"] == "NON_RECOVERABLE"
        assert d["failure_domain"] == "LLM_PROVIDER"
        assert d["error_message"] == "LLM rate limit exceeded"
        assert d["pending_tool_calls"] == 0
        assert d["completed_tool_calls"] == 2
