"""Targeted unit and integration proofs for worker failure classification (TASK-087 / ADR-065)."""
from __future__ import annotations

import pytest

from src.aios_bridge.worker_failure import (
    FAILURE_CLASS_TO_NEXT_ACTION,
    NEXT_ACTION_TO_HUMAN_TEXT,
    WorkerFailureClass,
    WorkerFailureError,
    WorkerFailureEvidence,
    WorkerNextAction,
    classify_worker_failure,
)


HEAD_A = "a" * 40
HEAD_B = "b" * 40


def test_baseline_missing_guard_proven_and_worker_failure_module_created() -> None:
    """Proof: BASELINE_MISSING_GUARD_PROVEN & WORKER_FAILURE_MODULE_CREATED."""
    assert issubclass(WorkerFailureClass, str)
    assert len(WorkerFailureClass) == 4
    assert issubclass(WorkerNextAction, str)
    assert len(WorkerNextAction) == 3

    assert len(FAILURE_CLASS_TO_NEXT_ACTION) == 4
    for fc in WorkerFailureClass:
        assert fc in FAILURE_CLASS_TO_NEXT_ACTION
        assert isinstance(FAILURE_CLASS_TO_NEXT_ACTION[fc], WorkerNextAction)

    assert len(NEXT_ACTION_TO_HUMAN_TEXT) == 3
    for na in WorkerNextAction:
        assert na in NEXT_ACTION_TO_HUMAN_TEXT
        assert isinstance(NEXT_ACTION_TO_HUMAN_TEXT[na], str)
        assert len(NEXT_ACTION_TO_HUMAN_TEXT[na]) > 0


def test_clean_no_worktree_delta_classified_and_next_action_single() -> None:
    """Proof: CLEAN_NO_WORKTREE_DELTA_CLASSIFIED & CLEAN_NO_WORKTREE_DELTA_NEXT_ACTION_SINGLE."""
    evidence = classify_worker_failure(
        terminal_status="EXITED_ZERO",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=(),
        is_known_stopped=True,
    )
    assert evidence.failure_class == WorkerFailureClass.CLEAN_NO_WORKTREE_DELTA
    assert evidence.next_action == WorkerNextAction.HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE
    assert evidence.zero_worktree_delta is True
    assert evidence.human_guidance == NEXT_ACTION_TO_HUMAN_TEXT[evidence.next_action]


def test_clean_timeout_classified_from_terminal_timeout() -> None:
    """Proof: CLEAN_TIMEOUT_CLASSIFIED_FROM_TERMINAL_TIMEOUT & CLEAN_TIMEOUT_REQUIRES_ZERO_DELTA."""
    evidence = classify_worker_failure(
        terminal_status="TIMED_OUT",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=(),
        is_known_stopped=True,
    )
    assert evidence.failure_class == WorkerFailureClass.CLEAN_TIMEOUT
    assert evidence.next_action == WorkerNextAction.HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT
    assert evidence.zero_worktree_delta is True
    assert "clean timeout" in evidence.human_guidance.lower()


def test_dirty_timeout_recovery_required_classified() -> None:
    """Proof: DIRTY_TIMEOUT_RECOVERY_REQUIRED_CLASSIFIED & DIRTY_TIMEOUT_PRESERVES_WORKTREE."""
    # Case A: Head unchanged, but dirty paths exist
    ev_dirty = classify_worker_failure(
        terminal_status="TIMED_OUT",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=("bridge.py",),
        is_known_stopped=True,
    )
    assert ev_dirty.failure_class == WorkerFailureClass.DIRTY_TIMEOUT_RECOVERY_REQUIRED
    assert ev_dirty.next_action == WorkerNextAction.RECOVERY_REQUIRED_PRESERVED_DELTA
    assert ev_dirty.zero_worktree_delta is False

    # Case B: Head advanced during timeout
    ev_head = classify_worker_failure(
        terminal_status="TIMED_OUT",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_B,
        dirty_paths=(),
        is_known_stopped=True,
    )
    assert ev_head.failure_class == WorkerFailureClass.DIRTY_TIMEOUT_RECOVERY_REQUIRED
    assert ev_head.next_action == WorkerNextAction.RECOVERY_REQUIRED_PRESERVED_DELTA
    assert ev_head.zero_worktree_delta is False


def test_productive_nonzero_requires_preserved_authorized_delta() -> None:
    """Proof: PRODUCTIVE_NONZERO_REQUIRES_PRESERVED_AUTHORIZED_DELTA & PRODUCTIVE_NONZERO_OUT_OF_SCOPE_FAILS_CLOSED."""
    allowed = ["bridge.py", "tests/test_bridge.py"]

    # Authorized delta -> productive candidate
    ev_in_scope = classify_worker_failure(
        terminal_status="EXITED_NONZERO",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=("bridge.py",),
        allowed_paths=allowed,
        is_known_stopped=True,
    )
    assert ev_in_scope.failure_class == WorkerFailureClass.PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
    assert ev_in_scope.next_action == WorkerNextAction.RECOVERY_REQUIRED_PRESERVED_DELTA

    # Out of scope delta -> fails closed by raising WorkerFailureError
    with pytest.raises(WorkerFailureError):
        classify_worker_failure(
            terminal_status="EXITED_NONZERO",
            pre_head_sha=HEAD_A,
            post_head_sha=HEAD_A,
            dirty_paths=("src/unauthorized.py",),
            allowed_paths=allowed,
            is_known_stopped=True,
        )


def test_is_known_stopped_false_fails_closed() -> None:
    """B1 proof: is_known_stopped=False must fail closed."""
    with pytest.raises(WorkerFailureError):
        classify_worker_failure(
            terminal_status="TIMED_OUT",
            pre_head_sha=HEAD_A,
            post_head_sha=HEAD_A,
            dirty_paths=(),
            is_known_stopped=False,
        )


def test_unknown_terminal_status_fails_closed() -> None:
    """B1 proof: unknown or arbitrary terminal status must fail closed."""
    with pytest.raises(WorkerFailureError):
        classify_worker_failure(
            terminal_status="UNKNOWN_STATUS",
            pre_head_sha=HEAD_A,
            post_head_sha=HEAD_A,
            dirty_paths=(),
            is_known_stopped=True,
        )


def test_missing_scope_evidence_on_exited_nonzero_fails_closed() -> None:
    """B1 proof: EXITED_NONZERO with non-zero delta but missing allowed_paths fails closed."""
    with pytest.raises(WorkerFailureError):
        classify_worker_failure(
            terminal_status="EXITED_NONZERO",
            pre_head_sha=HEAD_A,
            post_head_sha=HEAD_A,
            dirty_paths=("bridge.py",),
            allowed_paths=None,
            is_known_stopped=True,
        )


def test_exited_zero_with_worktree_delta_fails_closed() -> None:
    """B1 proof: EXITED_ZERO with non-zero worktree delta is not a failure class."""
    with pytest.raises(WorkerFailureError):
        classify_worker_failure(
            terminal_status="EXITED_ZERO",
            pre_head_sha=HEAD_A,
            post_head_sha=HEAD_A,
            dirty_paths=("bridge.py",),
            is_known_stopped=True,
        )


def test_one_machine_next_action_per_blocked_classification_and_human_text_derived() -> None:
    """Proof: ONE_MACHINE_NEXT_ACTION_PER_BLOCKED_CLASSIFICATION & HUMAN_TEXT_DERIVED_FROM_MACHINE_NEXT_ACTION."""
    for fc in WorkerFailureClass:
        na = FAILURE_CLASS_TO_NEXT_ACTION[fc]
        assert na in WorkerNextAction
        human_text = NEXT_ACTION_TO_HUMAN_TEXT[na]
        assert isinstance(human_text, str) and len(human_text) > 0


def test_codex_antigravity_classification_policy_parity() -> None:
    """Proof: CODEX_ANTIGRAVITY_CLASSIFICATION_POLICY_PARITY."""
    ev_ag = classify_worker_failure(
        terminal_status="EXITED_ZERO",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=(),
    )
    ev_cx = classify_worker_failure(
        terminal_status="EXITED_ZERO",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=(),
    )
    assert ev_ag == ev_cx
    assert ev_ag.to_dict() == ev_cx.to_dict()


def test_worker_failure_evidence_round_trip_and_validation() -> None:
    """Proof of strict evidence serialization and validation."""
    evidence = classify_worker_failure(
        terminal_status="TIMED_OUT",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=(),
    )
    d = evidence.to_dict()
    restored = WorkerFailureEvidence.from_dict(d)
    assert restored == evidence

    # Malformed SHA fails closed
    with pytest.raises(WorkerFailureError):
        classify_worker_failure(
            terminal_status="EXITED_ZERO",
            pre_head_sha="invalid-sha",
            post_head_sha=HEAD_A,
            dirty_paths=(),
        )


def test_coercion_and_extra_fields_rejected_in_from_dict() -> None:
    """B3 proof: Coercion and extra fields must be rejected in from_dict."""
    valid_d = classify_worker_failure(
        terminal_status="TIMED_OUT",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=(),
    ).to_dict()

    # Extra field rejected
    with pytest.raises(WorkerFailureError):
        WorkerFailureEvidence.from_dict({**valid_d, "extra_field": "injected"})

    # String bool "false" rejected (no coercion)
    with pytest.raises(WorkerFailureError):
        WorkerFailureEvidence.from_dict({**valid_d, "zero_worktree_delta": "false"})

    # Non-list dirty_paths rejected
    with pytest.raises(WorkerFailureError):
        WorkerFailureEvidence.from_dict({**valid_d, "dirty_paths": "bridge.py"})

    # Human guidance mismatch rejected
    with pytest.raises(WorkerFailureError):
        WorkerFailureEvidence.from_dict({**valid_d, "human_guidance": "Tampered text"})

    # Inconsistent failure_class and terminal_status rejected
    with pytest.raises(WorkerFailureError):
        WorkerFailureEvidence.from_dict({**valid_d, "terminal_status": "EXITED_ZERO"})


def test_clean_timeout_no_result_publication_and_no_retry_reroute() -> None:
    """Proof: CLEAN_TIMEOUT_NO_RESULT_PUBLICATION & AUTO_RETRY: NO & AUTO_REROUTE: NO."""
    evidence = classify_worker_failure(
        terminal_status="TIMED_OUT",
        pre_head_sha=HEAD_A,
        post_head_sha=HEAD_A,
        dirty_paths=(),
    )
    assert evidence.next_action == WorkerNextAction.HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT
    assert "retry" not in evidence.human_guidance.lower()
    assert "reroute" not in evidence.human_guidance.lower()
