from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from src.core.checkpoint_contract import FailureDomain, RunState


class RetryOperation(str, Enum):
    LLM = "LLM"
    TOOL = "TOOL"


class RetryReason(str, Enum):
    RETRYABLE_TRANSIENT = "RETRYABLE_TRANSIENT"
    RETRYABLE_RATE_LIMIT = "RETRYABLE_RATE_LIMIT"
    RETRYABLE_PROVIDER_UNAVAILABLE = "RETRYABLE_PROVIDER_UNAVAILABLE"
    RETRYABLE_TIMEOUT = "RETRYABLE_TIMEOUT"

    NON_RETRYABLE = "NON_RETRYABLE"
    MAX_ATTEMPTS_EXCEEDED = "MAX_ATTEMPTS_EXCEEDED"
    CANCELLED = "CANCELLED"
    TERMINAL_STATE = "TERMINAL_STATE"
    CORRUPTION = "CORRUPTION"


@dataclass
class RetryContext:
    """
    Normalized failure context for retry policy evaluation.

    `attempt` is 1-indexed (first execution attempt = 1).
    """

    operation: RetryOperation
    attempt: int
    max_attempts: int
    failure_domain: FailureDomain
    error_code: str = ""
    transient: bool = False
    cancelled: bool = False
    run_state: RunState = RunState.RUNNING
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class RetryDecision:
    """
    Immutable retry decision returned by RetryPolicyEngine.
    """

    should_retry: bool
    delay_seconds: float
    next_attempt: int
    reason: RetryReason
    failure_domain: FailureDomain

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_retry": self.should_retry,
            "delay_seconds": self.delay_seconds,
            "next_attempt": self.next_attempt,
            "reason": self.reason.value,
            "failure_domain": self.failure_domain.value,
        }


class RetryPolicyEngine:
    """
    Pure decision engine for retry policy enforcement.

    Guarantees:
    - Pure function: no side effects, no sleeping, no execution, no store mutation.
    - Strict 6-level precedence hierarchy:
      1. CORRUPTION_INTEGRITY -> NEVER RETRY (CORRUPTION)
      2. CHECKPOINT_STORE failure -> NEVER RETRY (NON_RETRYABLE)
      3. Cancellation requested -> NEVER RETRY (CANCELLED)
      4. HALTED / FAILED / COMPLETED state -> NEVER RETRY (TERMINAL_STATE)
      5. attempt >= max_attempts -> NEVER RETRY (MAX_ATTEMPTS_EXCEEDED)
      6. Non-transient error -> NEVER RETRY (NON_RETRYABLE)
      7. Transient retryable error -> RETRY (delay = min(base * 2^(attempt-1), max))
    """

    @staticmethod
    def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        """Deterministic 1-indexed exponential backoff math."""
        if attempt < 1:
            attempt = 1
        raw_delay = base_delay * (2 ** (attempt - 1))
        return min(raw_delay, max_delay)

    @classmethod
    def decide(
        cls,
        context: RetryContext,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> RetryDecision:
        # Precedence 1: Corruption / Integrity
        if context.failure_domain == FailureDomain.CORRUPTION_INTEGRITY:
            return RetryDecision(
                should_retry=False,
                delay_seconds=0.0,
                next_attempt=context.attempt,
                reason=RetryReason.CORRUPTION,
                failure_domain=context.failure_domain,
            )

        # Precedence 2: Checkpoint Store failure
        if context.failure_domain == FailureDomain.CHECKPOINT_STORE:
            return RetryDecision(
                should_retry=False,
                delay_seconds=0.0,
                next_attempt=context.attempt,
                reason=RetryReason.NON_RETRYABLE,
                failure_domain=context.failure_domain,
            )

        # Precedence 3: Cancellation requested
        if context.cancelled:
            return RetryDecision(
                should_retry=False,
                delay_seconds=0.0,
                next_attempt=context.attempt,
                reason=RetryReason.CANCELLED,
                failure_domain=context.failure_domain,
            )

        # Precedence 4: Terminal state (HALTED, FAILED, COMPLETED)
        if context.run_state in (RunState.HALTED, RunState.FAILED, RunState.COMPLETED):
            return RetryDecision(
                should_retry=False,
                delay_seconds=0.0,
                next_attempt=context.attempt,
                reason=RetryReason.TERMINAL_STATE,
                failure_domain=context.failure_domain,
            )

        # Precedence 5: Attempt limit exceeded (attempt >= max_attempts MUST stop)
        if context.attempt >= context.max_attempts:
            return RetryDecision(
                should_retry=False,
                delay_seconds=0.0,
                next_attempt=context.attempt,
                reason=RetryReason.MAX_ATTEMPTS_EXCEEDED,
                failure_domain=context.failure_domain,
            )

        # Precedence 6: Non-transient error
        if not context.transient:
            return RetryDecision(
                should_retry=False,
                delay_seconds=0.0,
                next_attempt=context.attempt,
                reason=RetryReason.NON_RETRYABLE,
                failure_domain=context.failure_domain,
            )

        # Precedence 7: Transient retryable error
        delay = cls.calculate_backoff(context.attempt, base_delay=base_delay, max_delay=max_delay)

        # Map error code to explicit RetryReason
        err_code_upper = context.error_code.upper()
        if "RATE_LIMIT" in err_code_upper or "429" in err_code_upper:
            reason = RetryReason.RETRYABLE_RATE_LIMIT
        elif "UNAVAILABLE" in err_code_upper or "503" in err_code_upper:
            reason = RetryReason.RETRYABLE_PROVIDER_UNAVAILABLE
        elif "TIMEOUT" in err_code_upper or "TIMED_OUT" in err_code_upper:
            reason = RetryReason.RETRYABLE_TIMEOUT
        else:
            reason = RetryReason.RETRYABLE_TRANSIENT

        return RetryDecision(
            should_retry=True,
            delay_seconds=delay,
            next_attempt=context.attempt + 1,
            reason=reason,
            failure_domain=context.failure_domain,
        )


class FailureClassifier:
    """
    Normalizes raw exceptions, ToolResult errors, and LLM errors into
    (FailureDomain, transient: bool, error_code: str).
    """

    @staticmethod
    def classify(
        exc_or_error: Any,
        operation: RetryOperation = RetryOperation.TOOL,
    ) -> tuple[FailureDomain, bool, str]:
        if exc_or_error is None:
            domain = (
                FailureDomain.LLM_PROVIDER
                if operation == RetryOperation.LLM
                else FailureDomain.TOOL_EXECUTION
            )
            return (domain, False, "")

        import asyncio
        from src.core.checkpoint_contract import (
            CheckpointCorruptionError,
            CheckpointStateError,
        )
        from src.core.errors import AgentException, SystemStateError

        if isinstance(exc_or_error, (CheckpointCorruptionError, CheckpointStateError)):
            return (FailureDomain.CORRUPTION_INTEGRITY, False, "CORRUPTION_INTEGRITY")

        if isinstance(exc_or_error, SystemStateError):
            msg = str(exc_or_error).lower()
            if "checkpoint" in msg or "idempotency" in msg or "persistence" in msg:
                return (FailureDomain.CHECKPOINT_STORE, False, "CHECKPOINT_STORE_FAILURE")
            return (FailureDomain.USER_APP, False, "SYSTEM_STATE_ERROR")

        if isinstance(exc_or_error, (TimeoutError, asyncio.TimeoutError)):
            domain = (
                FailureDomain.LLM_PROVIDER
                if operation == RetryOperation.LLM
                else FailureDomain.TOOL_EXECUTION
            )
            return (domain, True, "TIMEOUT")

        if isinstance(exc_or_error, (OSError, PermissionError, FileNotFoundError)):
            return (FailureDomain.CHECKPOINT_STORE, False, "IO_ERROR")


        if isinstance(exc_or_error, AgentException):
            domain = (
                FailureDomain.LLM_PROVIDER
                if operation == RetryOperation.LLM
                else FailureDomain.TOOL_EXECUTION
            )
            return (domain, exc_or_error.retryable, exc_or_error.code or "AGENT_ERROR")

        if hasattr(exc_or_error, "retryable") and hasattr(exc_or_error, "code"):
            domain = (
                FailureDomain.LLM_PROVIDER
                if operation == RetryOperation.LLM
                else FailureDomain.TOOL_EXECUTION
            )
            return (
                domain,
                bool(getattr(exc_or_error, "retryable", True)),
                str(getattr(exc_or_error, "code", "TOOL_ERROR")),
            )

        domain = (
            FailureDomain.LLM_PROVIDER
            if operation == RetryOperation.LLM
            else FailureDomain.TOOL_EXECUTION
        )
        return (domain, False, type(exc_or_error).__name__)

