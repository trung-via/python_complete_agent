"""
Unit tests for Open Multi-Agent Continuity OS M5 Executor Lease Contract (ADR-019 / TASK-029).
Validates canonical ExecutorLease schema, invariants, boundary size, UTF-8 wrapping, and relational binding.
"""
from __future__ import annotations

import json
import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionOperation, PreparedExecution
from src.aios_bridge.continuity.lease import (
    MAX_ACTIVE_EXECUTORS_PER_TASK,
    ExecutorLease,
    validate_executor_lease_binding,
)
from src.aios_bridge.continuity.state import MAX_SERIALIZED_BYTES


def _sample_lease(
    task_id: str = "TASK-029",
    lease_id: str = "lease-task-029-abc123def456",
    workspace_id: str = "1" * 64,
    executor_id: str = "antigravity",
    operation: ExecutionOperation = ExecutionOperation.RUN,
    execution_fingerprint: str = "2" * 64,
) -> ExecutorLease:
    return ExecutorLease(
        schema_version="1",
        lease_id=lease_id,
        task_id=task_id,
        workspace_id=workspace_id,
        executor_id=executor_id,
        operation=operation,
        execution_fingerprint=execution_fingerprint,
    )


# -----------------------------------------------------------------------------
# 1. Invariants and Schema Validation
# -----------------------------------------------------------------------------

def test_max_active_executors_invariant():
    """MAX_ACTIVE_EXECUTORS_PER_TASK == 1 is strictly invariant (C2 / ADR-019)."""
    assert MAX_ACTIVE_EXECUTORS_PER_TASK == 1


def test_executor_lease_valid_construction_and_fingerprint():
    """ExecutorLease constructs cleanly, produces deterministic canonical JSON and fingerprint."""
    lease = _sample_lease()
    assert lease.schema_version == "1"
    assert lease.task_id == "TASK-029"
    assert lease.executor_id == "antigravity"
    assert lease.operation == ExecutionOperation.RUN
    assert len(lease.fingerprint()) == 64

    # Canonical JSON round-trip
    canonical = lease.to_canonical_json()
    restored = ExecutorLease.from_json(canonical)
    assert lease == restored
    assert lease.fingerprint() == restored.fingerprint()


def test_executor_lease_whitespace_and_casing_rejection():
    """ExecutorLease rejects padded, unnormalized, or non-canonical identifiers."""
    lease_dict = _sample_lease().to_dict()

    # Padded task_id
    with pytest.raises(ContinuityStateValidationError, match="task_id"):
        ExecutorLease.from_dict({**lease_dict, "task_id": " TASK-029"})
    with pytest.raises(ContinuityStateValidationError, match="task_id"):
        ExecutorLease.from_dict({**lease_dict, "task_id": "task-029"})

    # Padded lease_id
    with pytest.raises(ContinuityStateValidationError, match="lease_id"):
        ExecutorLease.from_dict({**lease_dict, "lease_id": " lease-01"})

    # Padded executor_id
    with pytest.raises(ContinuityStateValidationError, match="executor_id"):
        ExecutorLease.from_dict({**lease_dict, "executor_id": " antigravity"})

    # Uppercase workspace_id
    with pytest.raises(ContinuityStateValidationError, match="workspace_id"):
        ExecutorLease.from_dict({**lease_dict, "workspace_id": ("a" * 64).upper()})

    # Uppercase execution_fingerprint
    with pytest.raises(ContinuityStateValidationError, match="execution_fingerprint"):
        ExecutorLease.from_dict({**lease_dict, "execution_fingerprint": ("b" * 64).upper()})


def test_executor_lease_forbidden_authority_and_ttl_keys_fail_closed():
    """ExecutorLease rejects any self-authorizing, timing, or secret fields (C4)."""
    lease_dict = _sample_lease().to_dict()

    for forbidden in [
        "approved",
        "human_approved",
        "merge_allowed",
        "authorization_token",
        "api_key",
        "cookie",
        "auth_header",
        "session_secret",
        "expires_at",
        "ttl",
        "heartbeat",
        "failover_target",
        "token",
        "auth",
    ]:
        bad_dict = {**lease_dict, forbidden: True if "approved" in forbidden else "secret"}
        with pytest.raises(ContinuityStateValidationError, match="Forbidden authority/secret/timing fields"):
            ExecutorLease.from_dict(bad_dict)


def test_executor_lease_operation_domain():
    """ExecutorLease accepts only RUN and FIX; MERGE and unknown operations fail (C3)."""
    lease_dict = _sample_lease().to_dict()

    # FIX is accepted
    fix_lease = ExecutorLease.from_dict({**lease_dict, "operation": "FIX"})
    assert fix_lease.operation == ExecutionOperation.FIX

    # MERGE is rejected
    with pytest.raises(ContinuityStateValidationError, match="Invalid ExecutionOperation in ExecutorLease"):
        ExecutorLease.from_dict({**lease_dict, "operation": "MERGE"})

    # Unknown operation is rejected
    with pytest.raises(ContinuityStateValidationError, match="Invalid ExecutionOperation in ExecutorLease"):
        ExecutorLease.from_dict({**lease_dict, "operation": "DISPATCH"})


def test_prepared_execution_distinct_from_executor_lease():
    """PreparedExecution is a request receipt, NOT an ExecutorLease (C26)."""
    lease = _sample_lease()
    prep = PreparedExecution(
        schema_version="1",
        task_id=lease.task_id,
        request_id="req-01",
        executor_id=lease.executor_id,
        execution_id="exec-01",
        request_fingerprint="3" * 64,
    )
    assert type(lease) is not type(prep)
    assert set(lease.to_dict().keys()) != set(prep.to_dict().keys())


# -----------------------------------------------------------------------------
# 2. Relational Lease Binding Validator Tests
# -----------------------------------------------------------------------------

def test_validate_executor_lease_binding_success():
    """Valid lease matches exact binding parameters cleanly (C7)."""
    lease = _sample_lease()
    validate_executor_lease_binding(
        lease,
        task_id=lease.task_id,
        workspace_id=lease.workspace_id,
        executor_id=lease.executor_id,
        operation=lease.operation,
        execution_fingerprint=lease.execution_fingerprint,
    )


def test_validate_executor_lease_binding_mismatches():
    """validate_executor_lease_binding fails closed on any field mismatch (C7)."""
    lease = _sample_lease()

    # 1. Task ID mismatch
    with pytest.raises(ContinuityStateValidationError, match="task_id"):
        validate_executor_lease_binding(
            lease,
            task_id="TASK-030",
            workspace_id=lease.workspace_id,
            executor_id=lease.executor_id,
            operation=lease.operation,
            execution_fingerprint=lease.execution_fingerprint,
        )

    # 2. Workspace ID mismatch
    with pytest.raises(ContinuityStateValidationError, match="workspace_id"):
        validate_executor_lease_binding(
            lease,
            task_id=lease.task_id,
            workspace_id="9" * 64,
            executor_id=lease.executor_id,
            operation=lease.operation,
            execution_fingerprint=lease.execution_fingerprint,
        )

    # 3. Executor ID mismatch
    with pytest.raises(ContinuityStateValidationError, match="executor_id"):
        validate_executor_lease_binding(
            lease,
            task_id=lease.task_id,
            workspace_id=lease.workspace_id,
            executor_id="codex",
            operation=lease.operation,
            execution_fingerprint=lease.execution_fingerprint,
        )

    # 4. Operation mismatch
    with pytest.raises(ContinuityStateValidationError, match="operation"):
        validate_executor_lease_binding(
            lease,
            task_id=lease.task_id,
            workspace_id=lease.workspace_id,
            executor_id=lease.executor_id,
            operation=ExecutionOperation.FIX,
            execution_fingerprint=lease.execution_fingerprint,
        )

    # 5. Execution fingerprint mismatch
    with pytest.raises(ContinuityStateValidationError, match="execution_fingerprint"):
        validate_executor_lease_binding(
            lease,
            task_id=lease.task_id,
            workspace_id=lease.workspace_id,
            executor_id=lease.executor_id,
            operation=lease.operation,
            execution_fingerprint="0" * 64,
        )


# -----------------------------------------------------------------------------
# 3. Serialization, Bounds & UTF-8 Tests
# -----------------------------------------------------------------------------

def test_unknown_fields_rejected():
    """ExecutorLease rejects unrecognized fields in from_dict (C3 / C14)."""
    lease_dict = _sample_lease().to_dict()
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in ExecutorLease"):
        ExecutorLease.from_dict({**lease_dict, "extra_field": "bad"})


def test_missing_required_fields_rejected():
    """ExecutorLease requires mandatory fields in from_dict."""
    lease_dict = _sample_lease().to_dict()
    bad_dict = dict(lease_dict)
    del bad_dict["task_id"]
    with pytest.raises(ContinuityStateValidationError, match="Missing required field 'task_id'"):
        ExecutorLease.from_dict(bad_dict)


def test_oversized_payload_rejected_in_from_json():
    """Payloads exceeding 16 KiB are rejected before or during JSON parsing."""
    lease = _sample_lease()
    huge_raw = json.dumps(lease.to_dict()) + (" " * 20000)
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed"):
        ExecutorLease.from_json(huge_raw)

    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed"):
        ExecutorLease.from_json(huge_raw.encode("utf-8"))


def test_malformed_json_wraps_continuity_error():
    """Malformed JSON in from_json wraps as ContinuityStateValidationError."""
    with pytest.raises(ContinuityStateValidationError, match="Malformed JSON for ExecutorLease"):
        ExecutorLease.from_json("{invalid json")


def test_invalid_utf8_bytes_wrapped_in_from_json():
    """Invalid UTF-8 bytes in from_json(bytes) wrap as ContinuityStateValidationError."""
    invalid_utf8 = b"\x80\x81\xff"
    with pytest.raises(ContinuityStateValidationError, match="Invalid UTF-8 encoding in input bytes for ExecutorLease"):
        ExecutorLease.from_json(invalid_utf8)
