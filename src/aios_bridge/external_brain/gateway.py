"""ModelGateway implementation orchestrating external inference, validation, and usage telemetry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import ContextBuildResult
from .contracts import (
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
    validate_request_response_correlation,
)
from .errors import ContractValidationError, CorrelationError, OutputContractError
from .provider import ProviderAdapter
from .usage import UsageLedger, UsageRecord
from .validation import validate_artifact_structure


@dataclass(frozen=True)
class GatewayResult:
    """
    Immutable result returned by ModelGateway.
    Bundles the final validated ModelResponse with execution telemetry and ledger status.
    """

    response: ModelResponse
    usage_record: UsageRecord
    ledger_persisted: bool
    ledger_error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.response, ModelResponse):
            raise ContractValidationError(f"response must be a ModelResponse, got: {type(self.response)}")
        if not isinstance(self.usage_record, UsageRecord):
            raise ContractValidationError(f"usage_record must be a UsageRecord, got: {type(self.usage_record)}")
        if not isinstance(self.ledger_persisted, bool):
            raise ContractValidationError("ledger_persisted must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        """Returns a deterministic JSON-serializable dictionary representation."""
        return {
            "response": self.response.to_dict(),
            "usage_record": self.usage_record.to_dict(),
            "ledger_persisted": self.ledger_persisted,
            "ledger_error": self.ledger_error,
        }


class ModelGateway:
    """
    Single-provider execution gateway.
    Enforces pre-call compatibility, single-call dispatch, post-call validation, and telemetry recording.
    """

    def __init__(self, provider: ProviderAdapter, ledger: UsageLedger | None = None) -> None:
        if not hasattr(provider, "provider_id") or not hasattr(provider, "invoke"):
            raise ContractValidationError("provider must implement ProviderAdapter protocol")
        self._provider = provider
        self._ledger = ledger

    @property
    def provider(self) -> ProviderAdapter:
        return self._provider

    @property
    def ledger(self) -> UsageLedger | None:
        return self._ledger

    async def invoke(
        self,
        request: ModelRequest,
        *,
        context_build: ContextBuildResult | None = None,
    ) -> GatewayResult:
        """
        Executes a ModelRequest against the configured provider with strict correlation and artifact checks.
        """
        if not isinstance(request, ModelRequest):
            raise ContractValidationError(f"request must be a ModelRequest instance, got: {type(request)}")

        # 1. Pre-call Provider Compatibility Check
        if request.provider != self._provider.provider_id:
            raise ContractValidationError(
                f"Provider mismatch: request.provider={request.provider!r} "
                f"does not match gateway configured provider={self._provider.provider_id!r}"
            )

        # 2. Pre-call ContextBuild Correlation Check
        if context_build is not None:
            if not isinstance(context_build, ContextBuildResult):
                raise ContractValidationError(
                    f"context_build must be ContextBuildResult or None, got: {type(context_build)}"
                )
            if request.context != context_build.selected:
                raise ContractValidationError(
                    "request.context does not match context_build.selected items"
                )

        # 3. Single Provider Execution (No Retries)
        response: ModelResponse = await self._provider.invoke(request)

        # 4. Request-Response Correlation Validation
        try:
            validate_request_response_correlation(request, response)
        except CorrelationError as e:
            response = ModelResponse(
                schema_version="1",
                request_id=request.request_id,
                task_id=request.task_id,
                provider=self._provider.provider_id,
                model=response.model if response else "unknown",
                status=ModelResponseStatus.INVALID_RESPONSE,
                output_type=None,
                content=None,
                latency_ms=response.latency_ms if response else 0,
                provider_request_id=response.provider_request_id if response else None,
                input_tokens=response.input_tokens if response else None,
                output_tokens=response.output_tokens if response else None,
                error_code="CORRELATION_ERROR",
                error_message=str(e),
            )

        # 5. Output Artifact Structure Validation (on SUCCESS)
        if response.status == ModelResponseStatus.SUCCESS:
            try:
                validate_artifact_structure(request.output_format, response.content or "")
            except (OutputContractError, ContractValidationError) as e:
                response = ModelResponse(
                    schema_version="1",
                    request_id=request.request_id,
                    task_id=request.task_id,
                    provider=self._provider.provider_id,
                    model=response.model,
                    status=ModelResponseStatus.INVALID_RESPONSE,
                    output_type=None,
                    content=None,
                    latency_ms=response.latency_ms,
                    provider_request_id=response.provider_request_id,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    error_code="INVALID_ARTIFACT_STRUCTURE",
                    error_message=f"Artifact structural validation failed: {str(e)}",
                )

        # 6. Build Immutable UsageRecord
        usage_record = UsageRecord(
            request_id=request.request_id,
            task_id=request.task_id,
            provider=self._provider.provider_id,
            model=response.model,
            operation=request.operation.value,
            status=response.status.value,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
            provider_request_id=response.provider_request_id,
            context_fingerprint=context_build.context_fingerprint if context_build else None,
            context_token_count=context_build.counted_tokens if context_build else None,
            context_counter_id=context_build.counter_id if context_build else None,
            context_token_count_is_exact=context_build.token_count_is_exact if context_build else None,
            error_code=response.error_code,
        )

        # 7. Append to UsageLedger (if configured)
        ledger_persisted = False
        ledger_error = None
        if self._ledger is not None:
            try:
                await self._ledger.append(usage_record)
                ledger_persisted = True
            except Exception as e:
                ledger_persisted = False
                ledger_error = f"{type(e).__name__}: {str(e)}"
                # Note: failure in ledger persistence MUST NOT repeat provider invocation

        return GatewayResult(
            response=response,
            usage_record=usage_record,
            ledger_persisted=ledger_persisted,
            ledger_error=ledger_error,
        )
