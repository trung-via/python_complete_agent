"""Adversarial unit tests for external M10.2 runtime capacity evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.aios_bridge.continuity.dispatch import (
    CapacityClass,
    CapacityState,
    DispatchActorKind,
    DispatchStatus,
    dispatch_executor,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionCapability, ExecutionOperation
from src.aios_bridge.continuity.state import MAX_SERIALIZED_BYTES
from src.aios_bridge.runtime_dispatch import (
    AtomicRuntimeCapacityStore,
    ExecutorDispatchPolicySpec,
    ExecutorPolicyCandidateSpec,
    ObservationSource,
    RuntimeCapacityRecord,
    build_executor_dispatch_request_from_runtime,
    classify_capacity_freshness,
    effective_capacity_state,
    parse_executor_dispatch_policy_marker,
)
import src.aios_bridge.runtime_dispatch as runtime_dispatch


NOW = 1_700_000_000
REQUIRED = (
    ExecutionCapability.REPOSITORY_READ,
    ExecutionCapability.FILESYSTEM_WRITE,
    ExecutionCapability.SHELL,
    ExecutionCapability.TEST_EXECUTION,
    ExecutionCapability.LOCAL_GIT,
)


def _record(
    actor_id: str = "codex",
    *,
    kind: DispatchActorKind = DispatchActorKind.EXECUTOR,
    state: CapacityState = CapacityState.AVAILABLE,
    observed: int = NOW,
    ttl: int = 3600,
) -> RuntimeCapacityRecord:
    return RuntimeCapacityRecord(
        actor_kind=kind,
        actor_id=actor_id,
        capacity_state=state,
        observed_at_epoch_seconds=observed,
        ttl_seconds=ttl,
    )


def _candidate(
    actor_id: str,
    *,
    capacity_class: CapacityClass = CapacityClass.SUBSCRIPTION,
    preference: int = 0,
) -> ExecutorPolicyCandidateSpec:
    return ExecutorPolicyCandidateSpec(
        executor_id=actor_id,
        supported_operations=(ExecutionOperation.RUN, ExecutionOperation.FIX),
        supported_capabilities=REQUIRED,
        capacity_class=capacity_class,
        preference_rank=preference,
    )


def _policy(candidates=None, *, allow_paid_api=False) -> ExecutorDispatchPolicySpec:
    return ExecutorDispatchPolicySpec(
        operation=ExecutionOperation.RUN,
        required_capabilities=REQUIRED,
        candidates=tuple(candidates or (_candidate("antigravity"), _candidate("codex", preference=1))),
        allow_paid_api=allow_paid_api,
    )


def _marker(policy=None) -> str:
    policy = policy or _policy()
    return "DISPATCH_EXECUTOR_POLICY_JSON: " + policy.to_canonical_json() + "\n"


def _capacity_json_at_size(target_size: int) -> str:
    semantic = _record("a").semantic_dict()
    semantic["actor_id"] = "a"

    def render() -> str:
        fingerprint = hashlib.sha256(
            json.dumps(
                semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        return json.dumps(
            {**semantic, "record_fingerprint": fingerprint},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    initial = render()
    semantic["actor_id"] = "a" * (1 + target_size - len(initial.encode("utf-8")))
    result = render()
    assert len(result.encode("utf-8")) == target_size
    return result


def test_record_canonical_serialization_and_fingerprint_are_deterministic():
    first = _record()
    second = _record()
    assert first == second
    assert first.fingerprint() == second.fingerprint() == first.record_fingerprint
    assert RuntimeCapacityRecord.from_json(first.to_canonical_json()) == first
    assert list(first.to_dict()) != []


def test_atomic_write_read_round_trip_and_per_actor_files_do_not_overwrite(tmp_path):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    codex = _record("codex")
    antigravity = _record("antigravity", state=CapacityState.LIMITED)
    store.write(codex)
    store.write(antigravity)
    assert store.load(DispatchActorKind.EXECUTOR, "codex") == codex
    assert store.load(DispatchActorKind.EXECUTOR, "antigravity") == antigravity
    assert store.record_path(DispatchActorKind.EXECUTOR, "codex") != store.record_path(
        DispatchActorKind.EXECUTOR, "antigravity"
    )
    assert store.record_path(DispatchActorKind.EXECUTOR, "codex").read_bytes().endswith(b"\n")


def test_generic_brain_record_round_trip_and_deterministic_listing(tmp_path):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    executor = _record("codex")
    brain = _record("primary-brain", kind=DispatchActorKind.BRAIN)
    store.write(executor)
    store.write(brain)
    assert store.load(DispatchActorKind.BRAIN, "primary-brain") == brain
    assert [(item.actor_kind.value, item.actor_id) for item in store.list_records()] == [
        ("BRAIN", "primary-brain"),
        ("EXECUTOR", "codex"),
    ]


@pytest.mark.parametrize(
    "actor_id",
    ["../codex", "codex/child", "codex\\child", ".", "..", " codex", "Codex"],
)
def test_actor_path_traversal_alias_and_noncanonical_ids_reject(actor_id):
    with pytest.raises(ContinuityStateValidationError):
        _record(actor_id)


@pytest.mark.parametrize("ttl", [True, False, 0, -1, 86401, 1.5])
def test_bool_negative_zero_and_oversized_ttl_reject(ttl):
    with pytest.raises(ContinuityStateValidationError, match="ttl_seconds"):
        _record(ttl=ttl)


@pytest.mark.parametrize("observed", [True, -1, 1.5])
def test_invalid_observed_time_rejects(observed):
    with pytest.raises(ContinuityStateValidationError, match="observed_at"):
        _record(observed=observed)


def test_future_observation_fails_freshness_closed():
    record = _record(observed=NOW + 1)
    with pytest.raises(ContinuityStateValidationError, match="future"):
        classify_capacity_freshness(record, NOW)
    with pytest.raises(ContinuityStateValidationError, match="future"):
        effective_capacity_state(record, NOW)


def test_record_fingerprint_tamper_rejects_on_parse():
    data = _record().to_dict()
    data["capacity_state"] = "LIMITED"
    with pytest.raises(ContinuityStateValidationError, match="fingerprint"):
        RuntimeCapacityRecord.from_dict(data)


def test_missing_observation_is_unknown_and_does_not_create_storage(tmp_path):
    root = tmp_path / "missing"
    store = AtomicRuntimeCapacityStore(root)
    assert store.load(DispatchActorKind.EXECUTOR, "codex") is None
    assert effective_capacity_state(None, NOW) is CapacityState.UNKNOWN
    assert not root.exists()


def test_expired_observation_becomes_unknown_without_rewrite(tmp_path):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    record = _record(observed=NOW - 11, ttl=10)
    store.write(record)
    path = store.record_path(DispatchActorKind.EXECUTOR, "codex")
    before_bytes = path.read_bytes()
    before_mtime = path.stat().st_mtime_ns
    assert classify_capacity_freshness(record, NOW) == "EXPIRED"
    assert effective_capacity_state(record, NOW) is CapacityState.UNKNOWN
    request, evidence = build_executor_dispatch_request_from_runtime(_policy((_candidate("codex"),)), store, NOW)
    assert request.candidates[0].capacity_state is CapacityState.UNKNOWN
    assert evidence[0].freshness == "EXPIRED"
    assert path.read_bytes() == before_bytes
    assert path.stat().st_mtime_ns == before_mtime


def test_fresh_available_state_is_preserved():
    record = _record(observed=NOW, ttl=1)
    assert classify_capacity_freshness(record, NOW) == "FRESH"
    assert classify_capacity_freshness(record, NOW + 1) == "FRESH"
    assert effective_capacity_state(record, NOW + 1) is CapacityState.AVAILABLE


@pytest.mark.parametrize(
    "content",
    [
        "no marker",
        _marker() + _marker(),
        "DISPATCH_EXECUTOR_POLICY_JSON: not-json",
        "DISPATCH_EXECUTOR_POLICY_JSON: []",
        " DISPATCH_EXECUTOR_POLICY_JSON: {}",
    ],
)
def test_exact_single_policy_marker_is_required(content):
    with pytest.raises(ContinuityStateValidationError):
        parse_executor_dispatch_policy_marker(content)


def test_policy_marker_rejects_unknown_and_missing_fields():
    data = _policy().to_dict()
    data["unknown"] = True
    with pytest.raises(ContinuityStateValidationError, match="fields"):
        parse_executor_dispatch_policy_marker(
            "DISPATCH_EXECUTOR_POLICY_JSON: " + json.dumps(data)
        )
    del data["unknown"]
    del data["operation"]
    with pytest.raises(ContinuityStateValidationError, match="fields"):
        parse_executor_dispatch_policy_marker(
            "DISPATCH_EXECUTOR_POLICY_JSON: " + json.dumps(data)
        )


def test_duplicate_policy_actor_ids_reject():
    with pytest.raises(ContinuityStateValidationError, match="Duplicate executor"):
        ExecutorDispatchPolicySpec(
            operation=ExecutionOperation.RUN,
            required_capabilities=REQUIRED,
            candidates=(_candidate("codex"), _candidate("codex")),
        )


def test_duplicate_policy_operations_and_capabilities_reject():
    with pytest.raises(ContinuityStateValidationError, match="duplicates"):
        ExecutorPolicyCandidateSpec(
            executor_id="codex",
            supported_operations=(ExecutionOperation.RUN, ExecutionOperation.RUN),
            supported_capabilities=REQUIRED,
            capacity_class=CapacityClass.SUBSCRIPTION,
            preference_rank=0,
        )
    with pytest.raises(ContinuityStateValidationError, match="duplicates"):
        ExecutorDispatchPolicySpec(
            operation=ExecutionOperation.RUN,
            required_capabilities=(ExecutionCapability.SHELL, ExecutionCapability.SHELL),
            candidates=(_candidate("codex"),),
        )


@pytest.mark.parametrize("preference", [True, -1])
def test_policy_preference_validation_fails_closed(preference):
    with pytest.raises(ContinuityStateValidationError, match="preference_rank"):
        _candidate("codex", preference=preference)


def test_policy_capacity_class_validation_fails_closed():
    with pytest.raises(ContinuityStateValidationError, match="capacity_class"):
        _candidate("codex", capacity_class="FREE_TIER")  # type: ignore[arg-type]


def test_policy_canonical_order_and_fingerprint_are_input_order_independent():
    first = _policy((_candidate("codex", preference=1), _candidate("antigravity")))
    second = _policy((_candidate("antigravity"), _candidate("codex", preference=1)))
    assert first.to_canonical_json() == second.to_canonical_json()
    assert first.fingerprint() == second.fingerprint()
    assert parse_executor_dispatch_policy_marker(_marker(first)) == first


def test_record_and_policy_serialization_byte_caps():
    with pytest.raises(ContinuityStateValidationError, match="size limit"):
        _record("actor-" + "a" * 17000)
    candidates = tuple(_candidate(f"actor-{index:04d}") for index in range(220))
    with pytest.raises(ContinuityStateValidationError, match="size limit"):
        _policy(candidates)


def test_exact_max_minus_newline_capacity_record_round_trips(tmp_path, monkeypatch):
    canonical = _capacity_json_at_size(MAX_SERIALIZED_BYTES - 1)
    record = RuntimeCapacityRecord.from_json(canonical)
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    boundary_path = tmp_path / "capacity" / "EXECUTOR" / "boundary.json"
    monkeypatch.setattr(store, "record_path", lambda actor_kind, actor_id: boundary_path)

    store.write(record)

    assert len(boundary_path.read_bytes()) == MAX_SERIALIZED_BYTES
    assert boundary_path.read_bytes() == canonical.encode("utf-8") + b"\n"
    assert store.load(record.actor_kind, record.actor_id) == record


def test_exact_max_canonical_record_is_rejected_before_persistence(tmp_path):
    canonical = _capacity_json_at_size(MAX_SERIALIZED_BYTES)
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")

    with pytest.raises(ContinuityStateValidationError, match="persisted size limit"):
        RuntimeCapacityRecord.from_json(canonical)

    assert not store.root.exists()


def test_writer_size_guard_preserves_preexisting_valid_final(tmp_path, monkeypatch):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    original = _record()
    store.write(original)
    final_path = store.record_path(original.actor_kind, original.actor_id)
    before = final_path.read_bytes()
    oversized_canonical = _capacity_json_at_size(MAX_SERIALIZED_BYTES)
    monkeypatch.setattr(
        RuntimeCapacityRecord,
        "to_canonical_json",
        lambda self: oversized_canonical,
    )

    with pytest.raises(ContinuityStateValidationError, match="persisted payload"):
        store.write(original)

    assert final_path.read_bytes() == before
    assert not list(final_path.parent.glob("*.tmp-*"))


def test_oversized_persisted_payload_remains_rejected(tmp_path):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    path = store.record_path(DispatchActorKind.EXECUTOR, "codex")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"{" + b"x" * MAX_SERIALIZED_BYTES)

    with pytest.raises(ContinuityStateValidationError, match="oversized"):
        store.load(DispatchActorKind.EXECUTOR, "codex")


def test_temp_file_is_cleaned_when_atomic_replace_fails(tmp_path, monkeypatch):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(runtime_dispatch.os, "replace", fail_replace)
    with pytest.raises(ContinuityStateValidationError, match="Atomic runtime capacity write failed"):
        store.write(_record())
    parent = store.record_path(DispatchActorKind.EXECUTOR, "codex").parent
    assert not list(parent.glob("*.tmp-*"))
    assert not store.record_path(DispatchActorKind.EXECUTOR, "codex").exists()


@pytest.mark.parametrize("failure_point", ["write", "flush", "fsync"])
def test_temp_io_failure_cleans_temp_and_preserves_valid_final(
    tmp_path, monkeypatch, failure_point
):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    original = _record()
    store.write(original)
    final_path = store.record_path(original.actor_kind, original.actor_id)
    before = final_path.read_bytes()
    real_open = Path.open

    class FailingTempHandle:
        def __init__(self, path):
            self.handle = real_open(path, "xb")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.handle.close()

        def write(self, payload):
            if failure_point == "write":
                raise OSError("simulated write failure")
            return self.handle.write(payload)

        def flush(self):
            if failure_point == "flush":
                raise OSError("simulated flush failure")
            return self.handle.flush()

        def fileno(self):
            return self.handle.fileno()

    def failing_temp_open(path, mode="r", *args, **kwargs):
        if mode == "xb" and ".tmp-" in path.name:
            return FailingTempHandle(path)
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_temp_open)
    if failure_point == "fsync":
        monkeypatch.setattr(
            runtime_dispatch.os,
            "fsync",
            lambda file_descriptor: (_ for _ in ()).throw(
                OSError("simulated fsync failure")
            ),
        )

    with pytest.raises(ContinuityStateValidationError, match="Atomic runtime capacity write failed"):
        store.write(_record(state=CapacityState.LIMITED))

    assert final_path.read_bytes() == before
    assert store.load(original.actor_kind, original.actor_id) == original
    assert not list(final_path.parent.glob("*.tmp-*"))


def test_corrupt_discovered_record_fails_closed_instead_of_skip(tmp_path):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    path = store.record_path(DispatchActorKind.EXECUTOR, "codex")
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ContinuityStateValidationError):
        store.list_records()


def test_runtime_request_uses_unknown_for_missing_and_existing_m10_1_dispatch():
    store = AtomicRuntimeCapacityStore(Path("unused-missing-runtime-root"))
    request, evidence = build_executor_dispatch_request_from_runtime(
        _policy((_candidate("codex"),)), store, NOW
    )
    assert request.candidates[0].capacity_state is CapacityState.UNKNOWN
    assert evidence[0].freshness == "MISSING"
    assert dispatch_executor(request).status is DispatchStatus.WAIT


def test_required_operational_shape_selects_codex(tmp_path):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    store.write(_record("antigravity", state=CapacityState.QUOTA_EXHAUSTED))
    store.write(_record("codex", state=CapacityState.AVAILABLE))
    request, evidence = build_executor_dispatch_request_from_runtime(_policy(), store, NOW)
    result = dispatch_executor(request)
    assert result.status is DispatchStatus.SELECTED
    assert result.selected_actor_id == "codex"
    assert [item.actor_id for item in evidence] == ["antigravity", "codex"]


def test_forbidden_paid_api_does_not_bypass_wait(tmp_path):
    store = AtomicRuntimeCapacityStore(tmp_path / "capacity")
    store.write(_record("subscription", state=CapacityState.QUOTA_EXHAUSTED))
    store.write(_record("paid", state=CapacityState.AVAILABLE))
    policy = _policy(
        (
            _candidate("subscription"),
            _candidate("paid", capacity_class=CapacityClass.PAID_API),
        ),
        allow_paid_api=False,
    )
    request, _ = build_executor_dispatch_request_from_runtime(policy, store, NOW)
    result = dispatch_executor(request)
    assert result.status is DispatchStatus.WAIT
    assert result.selected_actor_id is None
