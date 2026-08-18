"""Focused adversarial tests for deterministic zero-token dispatch (ADR-026)."""
from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
import inspect
from itertools import permutations

import pytest

from src.aios_bridge.continuity import dispatch as dispatch_module
from src.aios_bridge.continuity.brain import BrainCapability
from src.aios_bridge.continuity.dispatch import (
    BrainDispatchCandidate,
    BrainDispatchRequest,
    CandidateReason,
    CapacityClass,
    CapacityState,
    DispatchActorKind,
    DispatchReason,
    DispatchStatus,
    ExecutorDispatchCandidate,
    ExecutorDispatchRequest,
    dispatch_brain,
    dispatch_executor,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
    ExecutorCapabilities,
)
from src.aios_bridge.continuity.state import BrainOperation


ALL_EXECUTOR_CAPABILITIES = tuple(ExecutionCapability)
REQUIRED_REAL_POLICY_CAPABILITIES = (
    ExecutionCapability.REPOSITORY_READ,
    ExecutionCapability.FILESYSTEM_WRITE,
    ExecutionCapability.SHELL,
    ExecutionCapability.TEST_EXECUTION,
    ExecutionCapability.LOCAL_GIT,
)


def _brain(
    brain_id: str,
    *,
    state: CapacityState = CapacityState.AVAILABLE,
    capacity_class: CapacityClass = CapacityClass.SUBSCRIPTION,
    preference: int = 0,
    operations: tuple[BrainOperation, ...] = (BrainOperation.REVIEW,),
    max_context_bytes: int | None = None,
) -> BrainDispatchCandidate:
    return BrainDispatchCandidate(
        brain_id=brain_id,
        capability=BrainCapability(
            brain_id=brain_id,
            supported_operations=operations,
            max_context_bytes=max_context_bytes,
        ),
        capacity_state=state,
        capacity_class=capacity_class,
        preference_rank=preference,
    )


def _executor(
    executor_id: str,
    *,
    state: CapacityState = CapacityState.AVAILABLE,
    capacity_class: CapacityClass = CapacityClass.SUBSCRIPTION,
    preference: int = 0,
    operations: tuple[ExecutionOperation, ...] = (ExecutionOperation.RUN,),
    capabilities: tuple[ExecutionCapability, ...] = ALL_EXECUTOR_CAPABILITIES,
) -> ExecutorDispatchCandidate:
    return ExecutorDispatchCandidate(
        executor_id=executor_id,
        capabilities=ExecutorCapabilities(
            executor_id=executor_id,
            supported_operations=operations,
            supported_capabilities=capabilities,
        ),
        capacity_state=state,
        capacity_class=capacity_class,
        preference_rank=preference,
    )


def _executor_request(candidates, **overrides) -> ExecutorDispatchRequest:
    values = {
        "operation": ExecutionOperation.RUN,
        "candidates": tuple(candidates),
        "required_capabilities": (),
        "allow_paid_api": False,
    }
    values.update(overrides)
    return ExecutorDispatchRequest(**values)


def test_identical_inputs_produce_identical_result_and_fingerprints():
    request = _executor_request((_executor("codex"), _executor("antigravity")))
    first = dispatch_executor(request)
    second = dispatch_executor(request)
    assert first == second
    assert first.request_fingerprint == request.fingerprint()
    assert first.fingerprint() == second.fingerprint()
    assert first.to_canonical_json() == second.to_canonical_json()


def test_candidate_input_order_cannot_change_selection_or_canonical_request():
    candidates = (_executor("zeta"), _executor("alpha"), _executor("middle"))
    observations = {
        (
            _executor_request(order).fingerprint(),
            dispatch_executor(_executor_request(order)).selected_actor_id,
            dispatch_executor(_executor_request(order)).fingerprint(),
        )
        for order in permutations(candidates)
    }
    assert len(observations) == 1
    assert observations.pop()[1] == "alpha"


def test_brain_operation_mismatch_is_incompatible():
    result = dispatch_brain(
        BrainDispatchRequest(
            operation=BrainOperation.REVIEW,
            candidates=(_brain("planner", operations=(BrainOperation.PLAN,)),),
        )
    )
    assert result.status is DispatchStatus.NO_COMPATIBLE_CANDIDATE
    assert result.evaluations[0].reasons == (CandidateReason.OPERATION_UNSUPPORTED,)


def test_executor_operation_and_required_capability_subset_are_enforced():
    wrong_operation = _executor(
        "fix-only", operations=(ExecutionOperation.FIX,), capabilities=(ExecutionCapability.SHELL,)
    )
    missing_capability = _executor(
        "no-tests", capabilities=(ExecutionCapability.REPOSITORY_READ, ExecutionCapability.SHELL)
    )
    result = dispatch_executor(
        _executor_request(
            (wrong_operation, missing_capability),
            required_capabilities=(ExecutionCapability.TEST_EXECUTION,),
        )
    )
    assert result.status is DispatchStatus.NO_COMPATIBLE_CANDIDATE
    by_id = {item.actor_id: item for item in result.evaluations}
    assert CandidateReason.OPERATION_UNSUPPORTED in by_id["fix-only"].reasons
    assert CandidateReason.REQUIRED_CAPABILITY_MISSING in by_id["no-tests"].reasons


def test_brain_context_too_large_excludes_candidate_but_unbounded_candidate_runs():
    result = dispatch_brain(
        BrainDispatchRequest(
            operation=BrainOperation.REVIEW,
            required_context_bytes=101,
            candidates=(
                _brain("bounded", max_context_bytes=100),
                _brain("unbounded", max_context_bytes=None),
            ),
        )
    )
    assert result.selected_actor_id == "unbounded"
    bounded = next(item for item in result.evaluations if item.actor_id == "bounded")
    assert bounded.reasons == (CandidateReason.CONTEXT_TOO_LARGE,)


def test_available_outranks_limited_even_with_worse_preference():
    result = dispatch_executor(
        _executor_request(
            (
                _executor("limited", state=CapacityState.LIMITED, preference=0),
                _executor("available", state=CapacityState.AVAILABLE, preference=99),
            )
        )
    )
    assert result.selected_actor_id == "available"
    limited = next(item for item in result.evaluations if item.actor_id == "limited")
    assert limited.runnable is True
    assert limited.reasons == (CandidateReason.CAPACITY_LIMITED,)


@pytest.mark.parametrize(
    "state,reason",
    [
        (CapacityState.QUOTA_EXHAUSTED, CandidateReason.CAPACITY_QUOTA_EXHAUSTED),
        (CapacityState.UNAVAILABLE, CandidateReason.CAPACITY_UNAVAILABLE),
        (CapacityState.UNKNOWN, CandidateReason.CAPACITY_UNKNOWN),
    ],
)
def test_non_runnable_capacity_states_are_never_selected_but_remain_compatible(state, reason):
    result = dispatch_executor(_executor_request((_executor("candidate", state=state),)))
    assert result.status is DispatchStatus.WAIT
    assert result.selected_actor_id is None
    assert result.evaluations[0].compatible is True
    assert result.evaluations[0].runnable is False
    assert result.evaluations[0].reasons == (reason,)


def test_subscription_outranks_allowed_paid_api_before_capacity_and_preference():
    result = dispatch_executor(
        _executor_request(
            (
                _executor(
                    "subscription",
                    state=CapacityState.LIMITED,
                    capacity_class=CapacityClass.SUBSCRIPTION,
                    preference=99,
                ),
                _executor(
                    "paid",
                    state=CapacityState.AVAILABLE,
                    capacity_class=CapacityClass.PAID_API,
                    preference=0,
                ),
            ),
            allow_paid_api=True,
        )
    )
    assert result.selected_actor_id == "subscription"


def test_paid_api_is_incompatible_without_explicit_gate():
    result = dispatch_executor(
        _executor_request(
            (_executor("paid", capacity_class=CapacityClass.PAID_API),),
            allow_paid_api=False,
        )
    )
    assert result.status is DispatchStatus.NO_COMPATIBLE_CANDIDATE
    assert result.evaluations[0].reasons == (CandidateReason.PAID_API_NOT_ALLOWED,)


def test_wait_does_not_fall_through_to_forbidden_paid_api():
    result = dispatch_executor(
        _executor_request(
            (
                _executor("subscription", state=CapacityState.QUOTA_EXHAUSTED),
                _executor("paid", capacity_class=CapacityClass.PAID_API),
            ),
            allow_paid_api=False,
        )
    )
    assert result.status is DispatchStatus.WAIT
    assert result.reason is DispatchReason.WAIT_CAPACITY
    assert result.selected_actor_id is None


def test_no_compatible_candidate_when_every_candidate_misses_capability():
    result = dispatch_executor(
        _executor_request(
            (_executor("shell-only", capabilities=(ExecutionCapability.SHELL,)),),
            required_capabilities=(ExecutionCapability.TEST_EXECUTION,),
        )
    )
    assert result.status is DispatchStatus.NO_COMPATIBLE_CANDIDATE
    assert result.reason is DispatchReason.NO_COMPATIBLE_CANDIDATE


def test_lower_preference_rank_wins_after_class_and_state():
    result = dispatch_brain(
        BrainDispatchRequest(
            operation=BrainOperation.REVIEW,
            candidates=(_brain("later", preference=3), _brain("preferred", preference=2)),
        )
    )
    assert result.selected_actor_id == "preferred"


def test_lexical_actor_id_is_final_deterministic_tie_break():
    result = dispatch_brain(
        BrainDispatchRequest(
            operation=BrainOperation.REVIEW,
            candidates=(_brain("zeta"), _brain("alpha")),
        )
    )
    assert result.selected_actor_id == "alpha"
    assert [item.actor_id for item in result.evaluations] == ["alpha", "zeta"]


def test_duplicate_actor_ids_reject_for_both_actor_kinds():
    with pytest.raises(ContinuityStateValidationError, match="Duplicate Brain"):
        BrainDispatchRequest(
            operation=BrainOperation.REVIEW,
            candidates=(_brain("brain"), _brain("brain")),
        )
    with pytest.raises(ContinuityStateValidationError, match="Duplicate Executor"):
        _executor_request((_executor("executor"), _executor("executor")))


def test_embedded_capability_actor_mismatch_rejects_without_aliasing():
    with pytest.raises(ContinuityStateValidationError, match="exactly match"):
        BrainDispatchCandidate(
            brain_id="brain-a",
            capability=BrainCapability(
                brain_id="brain-b", supported_operations=(BrainOperation.REVIEW,)
            ),
            capacity_state=CapacityState.AVAILABLE,
            capacity_class=CapacityClass.SUBSCRIPTION,
        )
    with pytest.raises(ContinuityStateValidationError, match="exactly match"):
        ExecutorDispatchCandidate(
            executor_id="codex",
            capabilities=ExecutorCapabilities(
                executor_id="antigravity",
                supported_operations=(ExecutionOperation.RUN,),
                supported_capabilities=(),
            ),
            capacity_state=CapacityState.AVAILABLE,
            capacity_class=CapacityClass.SUBSCRIPTION,
        )


@pytest.mark.parametrize("rank", [True, False, -1])
def test_bool_and_negative_preference_rank_reject(rank):
    with pytest.raises(ContinuityStateValidationError, match="non-negative integer"):
        _executor("executor", preference=rank)


def test_duplicate_required_capabilities_reject_before_dispatch():
    with pytest.raises(ContinuityStateValidationError, match="Duplicate required"):
        _executor_request(
            (_executor("executor"),),
            required_capabilities=(ExecutionCapability.SHELL, ExecutionCapability.SHELL),
        )


@pytest.mark.parametrize("value", [True, -1, 1.5, "10"])
def test_invalid_required_context_bytes_reject(value):
    with pytest.raises(ContinuityStateValidationError, match="required_context_bytes"):
        BrainDispatchRequest(
            operation=BrainOperation.REVIEW,
            candidates=(_brain("brain"),),
            required_context_bytes=value,
        )


def test_unknown_enum_and_noncanonical_actor_aliases_reject():
    with pytest.raises(ContinuityStateValidationError, match="Invalid"):
        _executor("executor", state="EXHAUSTED")  # type: ignore[arg-type]
    with pytest.raises(ContinuityStateValidationError):
        _executor(" Codex ")
    with pytest.raises(ContinuityStateValidationError):
        _executor("Codex")


def test_real_policy_shape_selects_codex_and_is_permutation_independent():
    candidates = (
        _executor("antigravity", state=CapacityState.QUOTA_EXHAUSTED),
        _executor("codex", state=CapacityState.AVAILABLE),
    )
    selected = set()
    fingerprints = set()
    for order in permutations(candidates):
        request = _executor_request(order, required_capabilities=REQUIRED_REAL_POLICY_CAPABILITIES)
        result = dispatch_executor(request)
        assert result.status is DispatchStatus.SELECTED
        assert result.actor_kind is DispatchActorKind.EXECUTOR
        selected.add(result.selected_actor_id)
        fingerprints.add(result.fingerprint())
    assert selected == {"codex"}
    assert len(fingerprints) == 1


def test_dispatch_result_is_immutable_evidence_not_authority():
    result = dispatch_executor(_executor_request((_executor("codex"),)))
    with pytest.raises(FrozenInstanceError):
        result.selected_actor_id = "antigravity"  # type: ignore[misc]
    result_keys = set(result.to_dict())
    assert not result_keys & {
        "authorization",
        "approved",
        "lease",
        "lease_id",
        "execution_fingerprint",
        "human_approved",
    }


def test_dispatch_module_has_no_side_effect_or_external_service_surfaces():
    source = inspect.getsource(dispatch_module)
    tree = ast.parse(source)
    forbidden_import_fragments = {
        "bridge",
        "runtime_lease",
        "lease",
        "subprocess",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "openai",
        "anthropic",
        "os",
        "time",
        "datetime",
        "pathlib",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not {
        name
        for name in imported
        if any(fragment in name.split(".") for fragment in forbidden_import_fragments)
    }
    forbidden_references = {
        "os.environ",
        "time.time",
        "datetime.now",
        "open",
        "ExecutorLease",
        "AtomicExecutorLeaseStore",
        "authorize",
        "acquire",
        "release",
    }
    assert not forbidden_references & set(source.replace("(", " ").replace(".", ".").split())


def test_public_module_exports_only_recommendation_contract_not_lease_builders():
    public_names = set(dispatch_module.__all__)
    assert {"dispatch_brain", "dispatch_executor", "DispatchResult"} <= public_names
    assert not any("Lease" in name or "Authorization" in name for name in public_names)
    for name, function in inspect.getmembers(dispatch_module, inspect.isfunction):
        assert "lease" not in name.lower()
        assert "authoriz" not in name.lower()
