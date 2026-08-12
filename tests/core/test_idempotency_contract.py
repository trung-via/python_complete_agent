"""
Phase 5.3-A — Idempotency Contract Test Suite

11 tests covering the 8 Definition-of-Done scenarios + 3 structural invariants.
Tests use the InMemoryIdempotencyStore reference implementation.
"""
import pytest

from src.core.idempotency_contract import (
    RecordKey,
    RecordStatus,
    ClaimStatus,
    ClaimResult,
    IdempotencyRecord,
    IdempotencyCorruptionError,
    IdempotencyOwnershipError,
    IdempotencyStateError,
)
from src.core.idempotency_store_v2 import InMemoryIdempotencyStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store() -> InMemoryIdempotencyStore:
    return InMemoryIdempotencyStore()


# ---------------------------------------------------------------------------
# Definition of Done: 8 Contract Tests
# ---------------------------------------------------------------------------

def test_same_operation_same_idempotency_is_duplicate(store):
    """
    DoD #1: same operation_key + same idempotency_key → duplicate.
    First claim succeeds, second returns ALREADY_IN_PROGRESS.
    """
    key = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")

    result1 = store.claim(key, owner_id="worker_A")
    assert result1.status == ClaimStatus.CLAIMED
    assert result1.record is not None
    assert result1.record.status == RecordStatus.IN_PROGRESS

    result2 = store.claim(key, owner_id="worker_B")
    assert result2.status == ClaimStatus.ALREADY_IN_PROGRESS
    assert result2.record.owner_id == "worker_A"


def test_same_operation_different_idempotency_is_independent(store):
    """
    DoD #2: same operation_key + different idempotency_key → independent requests.
    Both claims succeed.
    """
    key1 = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")
    key2 = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_002")

    result1 = store.claim(key1, owner_id="worker_A")
    result2 = store.claim(key2, owner_id="worker_B")

    assert result1.status == ClaimStatus.CLAIMED
    assert result2.status == ClaimStatus.CLAIMED
    # They are tracked independently
    assert store.get(key1).owner_id == "worker_A"
    assert store.get(key2).owner_id == "worker_B"


def test_different_operation_same_idempotency_is_independent(store):
    """
    DoD #3: different operation_key + same idempotency_key → independent operations.
    No collision between different operations sharing an idempotency_key.
    """
    key1 = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")
    key2 = RecordKey(operation_key="upload:sha256_xyz", idempotency_key="req_001")

    result1 = store.claim(key1, owner_id="worker_A")
    result2 = store.claim(key2, owner_id="worker_A")

    assert result1.status == ClaimStatus.CLAIMED
    assert result2.status == ClaimStatus.CLAIMED
    # Stored under different canonical keys
    assert key1.canonical != key2.canonical


def test_completed_duplicate_replays_result(store):
    """
    DoD #4: completed operation → replay existing result, no re-execution.
    """
    key = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")
    completion_data = {"drive_file_id": "file_xyz", "bytes": 1024}

    # Claim and complete
    store.claim(key, owner_id="worker_A")
    store.complete(key, owner_id="worker_A", data=completion_data)

    # Second claim should return ALREADY_COMPLETED with the stored data
    result = store.claim(key, owner_id="worker_B")
    assert result.status == ClaimStatus.ALREADY_COMPLETED
    assert result.record is not None
    assert result.record.data == completion_data
    assert result.record.status == RecordStatus.COMPLETED


def test_in_progress_duplicate_no_second_execution(store):
    """
    DoD #5: while IN_PROGRESS, second claim → ALREADY_IN_PROGRESS.
    No second execution path is opened.
    """
    key = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")

    store.claim(key, owner_id="worker_A")

    # Multiple attempts by different workers — all blocked
    for worker in ["worker_B", "worker_C", "worker_D"]:
        result = store.claim(key, owner_id=worker)
        assert result.status == ClaimStatus.ALREADY_IN_PROGRESS
        assert result.record.owner_id == "worker_A"


def test_permanent_failure_no_auto_retry(store):
    """
    DoD #6: permanent failure → no automatic re-execution.
    Re-claim returns FAILED_PERMANENT.
    """
    key = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")
    error_data = {"error": "quota_exceeded", "code": "GDRIVE_QUOTA"}

    store.claim(key, owner_id="worker_A")
    store.fail(key, owner_id="worker_A", retryable=False, data=error_data)

    result = store.claim(key, owner_id="worker_B")
    assert result.status == ClaimStatus.FAILED_PERMANENT
    assert result.record.data == error_data
    assert result.record.status == RecordStatus.FAILED


def test_retryable_failure_eligible_for_retry(store):
    """
    DoD #7: retryable failure → eligible according to retry policy.
    Re-claim returns FAILED_RETRYABLE (caller decides whether to retry).
    """
    key = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")
    error_data = {"error": "network_timeout", "code": "GDRIVE_NETWORK"}

    store.claim(key, owner_id="worker_A")
    store.fail(key, owner_id="worker_A", retryable=True, data=error_data)

    result = store.claim(key, owner_id="worker_B")
    assert result.status == ClaimStatus.FAILED_RETRYABLE
    assert result.record.data == error_data
    assert result.record.status == RecordStatus.RECOVERABLE


def test_corrupt_record_explicit_error(store):
    """
    DoD #8: malformed/corrupt record → explicit error, never silent success.
    """
    key = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")

    # Inject a corrupt non-IdempotencyRecord value via backdoor
    store._inject_raw(key.canonical, {"garbage": True})

    with pytest.raises(IdempotencyCorruptionError) as exc_info:
        store.claim(key, owner_id="worker_A")

    assert "Corrupt idempotency record" in str(exc_info.value)
    assert key.canonical in str(exc_info.value)

    # get() must also raise, not silently return None
    with pytest.raises(IdempotencyCorruptionError):
        store.get(key)


# ---------------------------------------------------------------------------
# Structural Invariant Tests
# ---------------------------------------------------------------------------

def test_ownership_enforcement(store):
    """
    Bonus #9: different owner_id cannot complete() or fail() another's claim.
    """
    key = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")

    store.claim(key, owner_id="worker_A")

    # worker_B tries to complete worker_A's claim
    with pytest.raises(IdempotencyOwnershipError) as exc_info:
        store.complete(key, owner_id="worker_B")
    assert "worker_B" in str(exc_info.value)
    assert "worker_A" in str(exc_info.value)

    # worker_B tries to fail worker_A's claim
    with pytest.raises(IdempotencyOwnershipError):
        store.fail(key, owner_id="worker_B", retryable=True)

    # worker_A can still complete their own claim
    store.complete(key, owner_id="worker_A", data={"ok": True})
    assert store.get(key).status == RecordStatus.COMPLETED


def test_record_key_canonical_uniqueness(store):
    """
    Bonus #10: RecordKey("a","b").canonical != RecordKey("b","a").canonical.
    The composite key is order-dependent.
    """
    key_ab = RecordKey(operation_key="a", idempotency_key="b")
    key_ba = RecordKey(operation_key="b", idempotency_key="a")

    assert key_ab.canonical != key_ba.canonical
    assert key_ab.canonical == "a::b"
    assert key_ba.canonical == "b::a"

    # Both can be claimed independently
    r1 = store.claim(key_ab, owner_id="w1")
    r2 = store.claim(key_ba, owner_id="w2")
    assert r1.status == ClaimStatus.CLAIMED
    assert r2.status == ClaimStatus.CLAIMED


def test_claim_returns_record_metadata(store):
    """
    Bonus #11: ClaimResult.record has correct created_at, attempt, owner_id.
    """
    key = RecordKey(operation_key="upload:sha256_abc", idempotency_key="req_001")

    result = store.claim(key, owner_id="worker_A")

    assert result.status == ClaimStatus.CLAIMED
    record = result.record
    assert record is not None
    assert record.key == key
    assert record.owner_id == "worker_A"
    assert record.attempt == 1
    assert record.status == RecordStatus.IN_PROGRESS
    assert record.created_at > 0
    assert record.updated_at >= record.created_at
    assert record.data is None
