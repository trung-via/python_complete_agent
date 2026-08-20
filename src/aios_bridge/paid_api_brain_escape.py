"""One-shot Human-granted paid API Brain escape coordination.

This module only composes the existing grant, dispatch, and External Brain
contracts.  It grants no Executor authority and performs no repository or
credential discovery.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .continuity.dispatch import (
    BrainDispatchRequest,
    CapacityClass,
    DispatchActorKind,
    DispatchResult,
    DispatchStatus,
    dispatch_brain,
)
from .continuity.state import ArtifactRef, BrainOperation as ContinuityBrainOperation
from .external_brain.context import ContextBuildResult
from .external_brain.contracts import (
    BrainOperation as ExternalBrainOperation,
    ModelRequest,
)
from .external_brain.gateway import GatewayResult, ModelGateway
from .paid_api_grant import (
    PaidApiGrant,
    validate_paid_api_grant_binding,
    validate_paid_api_grant_budget,
)
from .runtime_paid_api_grant import AtomicPaidApiGrantStore


_OPERATION_MAP: dict[ContinuityBrainOperation, ExternalBrainOperation] = {
    ContinuityBrainOperation.PLAN: ExternalBrainOperation.PLAN,
    ContinuityBrainOperation.DIAGNOSIS: ExternalBrainOperation.DIAGNOSE_FAILURE,
    ContinuityBrainOperation.PATCH_PROPOSAL: ExternalBrainOperation.GENERATE_PATCH,
    ContinuityBrainOperation.REVIEW: ExternalBrainOperation.REVIEW_PATCH,
}


class PaidApiBrainEscapeError(ValueError):
    """Raised when paid API Brain enablement cannot be proven exactly."""


@dataclass(frozen=True)
class PaidApiBrainEscapeResult:
    """Evidence returned by a completed grant-aware dispatch attempt."""

    effective_dispatch_request: BrainDispatchRequest
    dispatch_result: DispatchResult
    paid_candidate_selected: bool
    grant_consumed: bool
    gateway_result: GatewayResult | None

    def __post_init__(self) -> None:
        if type(self.effective_dispatch_request) is not BrainDispatchRequest:
            raise PaidApiBrainEscapeError(
                "effective_dispatch_request must be an exact BrainDispatchRequest"
            )
        if type(self.dispatch_result) is not DispatchResult:
            raise PaidApiBrainEscapeError("dispatch_result must be an exact DispatchResult")
        if type(self.paid_candidate_selected) is not bool:
            raise PaidApiBrainEscapeError("paid_candidate_selected must be an exact bool")
        if type(self.grant_consumed) is not bool:
            raise PaidApiBrainEscapeError("grant_consumed must be an exact bool")
        if self.gateway_result is not None and type(self.gateway_result) is not GatewayResult:
            raise PaidApiBrainEscapeError("gateway_result must be an exact GatewayResult or None")
        if self.grant_consumed != self.paid_candidate_selected:
            raise PaidApiBrainEscapeError(
                "grant_consumed must exactly track paid candidate selection"
            )
        if not self.paid_candidate_selected and self.gateway_result is not None:
            raise PaidApiBrainEscapeError(
                "gateway_result is forbidden when no paid candidate was selected"
            )


def _require_exact_inputs(
    *,
    base_dispatch_request: object,
    grant: object,
    grant_store: object,
    authorized_artifact: object,
    model_request: object,
    context_build: object,
    gateway: object,
    now_epoch_seconds: object,
) -> None:
    exact_types = (
        (base_dispatch_request, BrainDispatchRequest, "base_dispatch_request"),
        (grant, PaidApiGrant, "grant"),
        (grant_store, AtomicPaidApiGrantStore, "grant_store"),
        (authorized_artifact, ArtifactRef, "authorized_artifact"),
        (model_request, ModelRequest, "model_request"),
        (context_build, ContextBuildResult, "context_build"),
        (gateway, ModelGateway, "gateway"),
    )
    for value, expected_type, name in exact_types:
        if type(value) is not expected_type:
            raise PaidApiBrainEscapeError(
                f"{name} must be an exact {expected_type.__name__}"
            )
    if type(now_epoch_seconds) is not int or now_epoch_seconds < 0:
        raise PaidApiBrainEscapeError(
            "now_epoch_seconds must be an exact non-negative integer"
        )


def _require_exact_nonempty_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise PaidApiBrainEscapeError(
            f"{field_name} must be an exact non-empty unpadded string"
        )
    return value


def _git_blob_sha(content: str) -> str:
    payload = content.encode("utf-8")
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    ).hexdigest()


async def execute_paid_api_brain_escape(
    *,
    base_dispatch_request: BrainDispatchRequest,
    grant: PaidApiGrant,
    grant_store: AtomicPaidApiGrantStore,
    authorized_artifact: ArtifactRef,
    model_request: ModelRequest,
    context_build: ContextBuildResult,
    gateway: ModelGateway,
    now_epoch_seconds: int,
) -> PaidApiBrainEscapeResult:
    """Dispatch and, only when selected, spend one paid API Brain grant.

    All authorization and correlation checks complete before a fresh request
    with ``allow_paid_api=True`` is created.  The grant is durably consumed
    before the sole gateway invocation and is never restored here.
    """

    _require_exact_inputs(
        base_dispatch_request=base_dispatch_request,
        grant=grant,
        grant_store=grant_store,
        authorized_artifact=authorized_artifact,
        model_request=model_request,
        context_build=context_build,
        gateway=gateway,
        now_epoch_seconds=now_epoch_seconds,
    )

    if base_dispatch_request.allow_paid_api is not False:
        raise PaidApiBrainEscapeError(
            "base_dispatch_request.allow_paid_api must be exactly False"
        )

    paid_candidates = tuple(
        candidate
        for candidate in base_dispatch_request.candidates
        if candidate.capacity_class is CapacityClass.PAID_API
    )
    if len(paid_candidates) != 1:
        raise PaidApiBrainEscapeError("exactly one PAID_API Brain candidate is required")
    paid_candidate = paid_candidates[0]
    if paid_candidate.brain_id != grant.brain_id:
        raise PaidApiBrainEscapeError(
            "the PAID_API Brain candidate must exactly match grant.brain_id"
        )

    # ACTIVE must be proven before any paid-enabled request exists.
    grant_store.require_active(grant, now_epoch_seconds=now_epoch_seconds)

    mapped_operation = _OPERATION_MAP.get(base_dispatch_request.operation)
    if mapped_operation is None:
        raise PaidApiBrainEscapeError(
            "continuity Brain operation has no authorized External Brain mapping"
        )

    provider = gateway.provider
    provider_id = _require_exact_nonempty_string(
        getattr(provider, "provider_id", None), "gateway provider_id"
    )
    model_id = _require_exact_nonempty_string(
        getattr(provider, "model_name", None), "gateway model_name"
    )

    validate_paid_api_grant_binding(
        grant,
        task_id=model_request.task_id,
        workspace_id=grant_store.workspace_id,
        brain_id=paid_candidate.brain_id,
        provider_id=provider_id,
        model_id=model_id,
        brain_operation=base_dispatch_request.operation,
        authorized_artifact_path=authorized_artifact.path,
        authorized_artifact_blob_sha=authorized_artifact.blob_sha,
    )

    if model_request.provider != grant.provider_id:
        raise PaidApiBrainEscapeError(
            "model_request.provider must exactly match the grant provider"
        )
    if model_request.model != grant.model_id:
        raise PaidApiBrainEscapeError(
            "model_request.model must exactly match the grant model"
        )
    if model_request.operation is not mapped_operation:
        raise PaidApiBrainEscapeError(
            "model_request.operation does not match the continuity operation mapping"
        )
    if model_request.context != context_build.selected:
        raise PaidApiBrainEscapeError(
            "model_request.context must exactly equal context_build.selected"
        )

    if (
        authorized_artifact.path != grant.authorized_artifact_path
        or authorized_artifact.blob_sha != grant.authorized_artifact_blob_sha
    ):
        raise PaidApiBrainEscapeError(
            "authorized artifact pointer must exactly match the grant"
        )
    matching_items = tuple(
        item
        for item in context_build.selected
        if item.path == grant.authorized_artifact_path
    )
    if len(matching_items) != 1:
        raise PaidApiBrainEscapeError(
            "exactly one selected context item must match the authorized artifact path"
        )
    if _git_blob_sha(matching_items[0].content) != grant.authorized_artifact_blob_sha:
        raise PaidApiBrainEscapeError(
            "authorized artifact selected-context bytes do not match the Git blob SHA"
        )

    if context_build.token_count_is_exact is not True:
        raise PaidApiBrainEscapeError("an exact token counter is required")
    _require_exact_nonempty_string(context_build.counter_id, "context counter_id")
    if (
        type(model_request.max_input_tokens) is not int
        or model_request.max_input_tokens <= 0
    ):
        raise PaidApiBrainEscapeError(
            "model_request.max_input_tokens must be an exact positive integer"
        )
    if (
        type(model_request.max_output_tokens) is not int
        or model_request.max_output_tokens <= 0
    ):
        raise PaidApiBrainEscapeError(
            "model_request.max_output_tokens must be an exact positive integer"
        )
    if context_build.max_context_tokens != model_request.max_input_tokens:
        raise PaidApiBrainEscapeError(
            "context max tokens must exactly match request max_input_tokens"
        )
    if (
        context_build.counted_tokens + context_build.protocol_reserve_tokens
        > context_build.max_context_tokens
    ):
        raise PaidApiBrainEscapeError(
            "selected context and protocol reserve exceed the exact context budget"
        )
    validate_paid_api_grant_budget(
        grant,
        input_tokens=model_request.max_input_tokens,
        output_tokens=model_request.max_output_tokens,
    )

    effective_request = BrainDispatchRequest(
        operation=base_dispatch_request.operation,
        candidates=base_dispatch_request.candidates,
        required_context_bytes=base_dispatch_request.required_context_bytes,
        allow_paid_api=True,
        schema_version=base_dispatch_request.schema_version,
    )
    dispatch_result = dispatch_brain(effective_request)

    if dispatch_result.actor_kind is not DispatchActorKind.BRAIN:
        raise PaidApiBrainEscapeError("dispatch result must be restricted to BRAIN actors")

    paid_selected = (
        dispatch_result.status is DispatchStatus.SELECTED
        and dispatch_result.selected_actor_id == paid_candidate.brain_id
    )
    if not paid_selected:
        return PaidApiBrainEscapeResult(
            effective_dispatch_request=effective_request,
            dispatch_result=dispatch_result,
            paid_candidate_selected=False,
            grant_consumed=False,
            gateway_result=None,
        )

    if dispatch_result.selected_actor_id != grant.brain_id:
        raise PaidApiBrainEscapeError(
            "selected paid Brain does not exactly match the grant"
        )

    # Terminal transition first.  No exception path below restores ACTIVE.
    grant_store.consume(grant, now_epoch_seconds=now_epoch_seconds)
    gateway_result = await gateway.invoke(model_request, context_build=context_build)
    return PaidApiBrainEscapeResult(
        effective_dispatch_request=effective_request,
        dispatch_result=dispatch_result,
        paid_candidate_selected=True,
        grant_consumed=True,
        gateway_result=gateway_result,
    )


__all__ = [
    "PaidApiBrainEscapeError",
    "PaidApiBrainEscapeResult",
    "execute_paid_api_brain_escape",
]
