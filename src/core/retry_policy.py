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
    Deterministic failure classifier that normalizes exceptions into
    (FailureDomain, transient: bool, error_code: str) for RetryPolicyEngine.
    """

    @classmethod
    def classify(
        cls,
        error: Any,
        operation: RetryOperation = RetryOperation.TOOL,
    ) -> tuple[FailureDomain, bool, str]:
        """
        Classifies an exception or error object into (FailureDomain, transient, error_code).
        """
        import asyncio
        from src.core.checkpoint_contract import (
            CheckpointCorruptionError,
            CheckpointStateError,
            FailureDomain,
        )
        from src.core.errors import AgentException, SystemStateError

        default_domain = (
            FailureDomain.TOOL_EXECUTION
            if operation == RetryOperation.TOOL
            else FailureDomain.LLM_PROVIDER
        )

        if error is None:
            return (default_domain, False, "UNKNOWN")

        # 1. Checkpoint corruption or state transition integrity error (never retry)
        if isinstance(error, (CheckpointCorruptionError, CheckpointStateError)):
            return (FailureDomain.CORRUPTION_INTEGRITY, False, type(error).__name__)

        # 2. System State / Checkpoint Store persistence error (never retry)
        if isinstance(error, SystemStateError):
            return (FailureDomain.CHECKPOINT_STORE, False, "SYSTEM_STATE_ERROR")

        # 3. AgentException (preserve exact code and retryable flag)
        if isinstance(error, AgentException):
            transient = bool(getattr(error, "retryable", False))
            code = getattr(error, "code", type(error).__name__)
            return (default_domain, transient, code)

        # 4. Timeout errors (transient)
        if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            return (default_domain, True, "TIMEOUT")

        # 5. Generic/unknown exceptions (default non-transient unless explicit metadata)
        transient = bool(getattr(error, "retryable", False))
        code = getattr(error, "code", type(error).__name__)
        return (default_domain, transient, code)

