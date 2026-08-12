import pytest

from src.core.checkpoint_contract import FailureDomain, RunState
from src.core.retry_policy import (
    RetryContext,
    RetryDecision,
    RetryOperation,
    RetryPolicyEngine,
    RetryReason,
)


def test_precedence_1_corruption_never_retry():
    ctx = RetryContext(
        operation=RetryOperation.TOOL,
        attempt=1,
        max_attempts=3,
        failure_domain=FailureDomain.CORRUPTION_INTEGRITY,
        transient=True,  # Even if transient is set True!
    )
    decision = RetryPolicyEngine.decide(ctx)

    assert decision.should_retry is False
    assert decision.reason == RetryReason.CORRUPTION
    assert decision.next_attempt == 1


def test_precedence_2_checkpoint_store_failure_never_retry():
    ctx = RetryContext(
        operation=RetryOperation.LLM,
        attempt=1,
        max_attempts=3,
        failure_domain=FailureDomain.CHECKPOINT_STORE,
        transient=True,
    )
    decision = RetryPolicyEngine.decide(ctx)

    assert decision.should_retry is False
    assert decision.reason == RetryReason.NON_RETRYABLE
    assert decision.next_attempt == 1


def test_precedence_3_cancellation_never_retry():
    ctx = RetryContext(
        operation=RetryOperation.TOOL,
        attempt=1,
        max_attempts=3,
        failure_domain=FailureDomain.TOOL_EXECUTION,
        transient=True,
        cancelled=True,
    )
    decision = RetryPolicyEngine.decide(ctx)

    assert decision.should_retry is False
    assert decision.reason == RetryReason.CANCELLED


def test_precedence_4_terminal_state_never_retry():
    for state in (RunState.HALTED, RunState.FAILED, RunState.COMPLETED):
        ctx = RetryContext(
            operation=RetryOperation.LLM,
            attempt=1,
            max_attempts=3,
            failure_domain=FailureDomain.LLM_PROVIDER,
            transient=True,
            run_state=state,
        )
        decision = RetryPolicyEngine.decide(ctx)

        assert decision.should_retry is False
        assert decision.reason == RetryReason.TERMINAL_STATE


def test_precedence_5_boundary_attempt_equals_max_attempts_stops():
    # attempt == max_attempts (3 == 3) MUST STOP
    ctx = RetryContext(
        operation=RetryOperation.TOOL,
        attempt=3,
        max_attempts=3,
        failure_domain=FailureDomain.TOOL_EXECUTION,
        transient=True,
    )
    decision = RetryPolicyEngine.decide(ctx)

    assert decision.should_retry is False
    assert decision.reason == RetryReason.MAX_ATTEMPTS_EXCEEDED
    assert decision.next_attempt == 3


def test_precedence_5_attempt_exceeds_max_attempts_stops():
    ctx = RetryContext(
        operation=RetryOperation.LLM,
        attempt=4,
        max_attempts=3,
        failure_domain=FailureDomain.LLM_PROVIDER,
        transient=True,
    )
    decision = RetryPolicyEngine.decide(ctx)

    assert decision.should_retry is False
    assert decision.reason == RetryReason.MAX_ATTEMPTS_EXCEEDED


def test_precedence_6_non_transient_error_never_retry():
    ctx = RetryContext(
        operation=RetryOperation.TOOL,
        attempt=1,
        max_attempts=3,
        failure_domain=FailureDomain.TOOL_EXECUTION,
        transient=False,
    )
    decision = RetryPolicyEngine.decide(ctx)

    assert decision.should_retry is False
    assert decision.reason == RetryReason.NON_RETRYABLE


def test_precedence_7_transient_error_retries_with_exponential_backoff():
    ctx1 = RetryContext(
        operation=RetryOperation.LLM,
        attempt=1,
        max_attempts=3,
        failure_domain=FailureDomain.LLM_PROVIDER,
        transient=True,
        error_code="RATE_LIMIT_429",
    )
    d1 = RetryPolicyEngine.decide(ctx1, base_delay=2.0)

    assert d1.should_retry is True
    assert d1.next_attempt == 2
    assert d1.delay_seconds == 2.0  # 2.0 * (2^0) = 2.0
    assert d1.reason == RetryReason.RETRYABLE_RATE_LIMIT

    ctx2 = RetryContext(
        operation=RetryOperation.LLM,
        attempt=2,
        max_attempts=3,
        failure_domain=FailureDomain.LLM_PROVIDER,
        transient=True,
        error_code="RATE_LIMIT_429",
    )
    d2 = RetryPolicyEngine.decide(ctx2, base_delay=2.0)

    assert d2.should_retry is True
    assert d2.next_attempt == 3
    assert d2.delay_seconds == 4.0  # 2.0 * (2^1) = 4.0


def test_backoff_capped_at_max_delay():
    delay = RetryPolicyEngine.calculate_backoff(attempt=10, base_delay=1.0, max_delay=15.0)
    assert delay == 15.0


def test_decision_immutability_and_determinism():
    ctx = RetryContext(
        operation=RetryOperation.TOOL,
        attempt=1,
        max_attempts=2,
        failure_domain=FailureDomain.TOOL_EXECUTION,
        transient=True,
    )
    d1 = RetryPolicyEngine.decide(ctx)
    d2 = RetryPolicyEngine.decide(ctx)

    assert d1 == d2
    assert d1.to_dict() == d2.to_dict()


def test_failure_classifier_checkpoint_corruption():
    from src.core.checkpoint_contract import CheckpointCorruptionError
    from src.core.retry_policy import FailureClassifier

    domain, transient, code = FailureClassifier.classify(CheckpointCorruptionError("r1", "corrupt"))
    assert domain == FailureDomain.CORRUPTION_INTEGRITY
    assert transient is False
    assert code == "CORRUPTION_INTEGRITY"


def test_failure_classifier_system_state_error():
    from src.core.errors import SystemStateError
    from src.core.retry_policy import FailureClassifier

    domain, transient, code = FailureClassifier.classify(SystemStateError("checkpoint write failed"))
    assert domain == FailureDomain.CHECKPOINT_STORE
    assert transient is False
    assert code == "CHECKPOINT_STORE_FAILURE"


def test_failure_classifier_timeout():
    from src.core.retry_policy import FailureClassifier

    domain, transient, code = FailureClassifier.classify(TimeoutError("request timeout"), operation=RetryOperation.LLM)
    assert domain == FailureDomain.LLM_PROVIDER
    assert transient is True
    assert code == "TIMEOUT"

