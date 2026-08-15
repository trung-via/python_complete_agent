# Phase 5.6 Production Readiness & Reliability Manual

## 1. Scope & Completed Milestones

Phase 5.6 hardens the AI Agent runtime control plane with deterministic reliability, recovery, concurrency safety, and operational verification across six milestones:

- **M1 Cancellation (`src/core/cancellation.py`)**: Durable cooperative cancellation protocol with run-level tokens, atomic cancellation transitions, and fail-closed continuation blocking.
- **M2 Retry Policy Engine (`src/core/retry_policy.py`)**: Granular policy-based retry engine supporting maximum attempts, jittered exponential backoff, and strict separation between retry attempts and logical tool calls.
- **M3 Retry Timeline & Failure Classification (`src/core/retry_timeline.py`)**: Timeline logging of attempt lifecycle (`TOOL_ATTEMPT_STARTED`, `TOOL_ATTEMPT_ENDED`, `RETRY_SCHEDULED`) with comprehensive error classification (transient network/rate-limit vs fatal schema/auth failures).
- **M4 Run Budget Enforcement (`src/agent/policy.py`, `src/agent/loop.py`)**: Durable budget tracking for iterations and tool calls across crash/resume cycles, preventing infinite loops and runaway costs.
- **M5 Fault Injection & Concurrency Verification (`tests/support/fault_injection.py`, `tests/integration/test_phase56_fault_injection.py`, `tests/integration/test_phase56_concurrency.py`)**: Deterministic test harness and integration suite covering crash boundaries, cancellation races, multi-worker same-run/same-call contention, and storage corruption fail-closed invariants.
- **M6 Production Readiness Gate (`src/agent/production_readiness.py`, `tests/integration/test_phase56_production_readiness.py`, `tests/integration/test_phase56_soak.py`)**: Preflight readiness verification contract and bounded deterministic reliability soak test suite.

---

## 2. Runtime Safety Invariants

1. **Durable Cancellation Authority**: A durably cancelled or halted run (`RUN_HALTED`) immediately blocks subsequent LLM iterations, pending tool calls on resume, and scheduled retry attempts.
2. **Terminal State Immutability**: Once a run reaches a terminal state (`COMPLETED`, `HALTED`, `FAILED`), no further checkpoint events can be appended, and the run cannot be resumed as active work.
3. **Storage Fail-Closed**: Any checkpoint syntax error, malformed JSON, corrupted idempotency record, or invalid state transition results in immediate fail-closed execution (`CORRUPT` classification or `SystemStateError`) without automatic modification or silent repair of the store file.
4. **Logical Tool Call Accounting**: Retried tool attempts for the same logical `call_id` count as exactly 1 tool call against the run's configured `max_tool_calls` budget.
5. **Durable Budget Persistence**: Consumed iterations and tool calls are reconstructed from durable checkpoints on resume, preventing budget resets after crashes.
6. **Contention Convergence & Idempotency**: Concurrent contenders for the same stable `(run_id, call_id)` converge through `JsonlIdempotencyStore`, guaranteeing at most one external side effect.
7. **Error Domain Separation**: Application-level tool exceptions (including `OSError` such as `FileNotFoundError`) produce standard `ToolResult(status=FAILURE)` results, while storage/persistence I/O failures raise `SystemStateError`.

---

## 3. Production Readiness API (`ProductionReadinessChecker`)

The `ProductionReadinessChecker` provides a deterministic, strictly read-only preflight gate to verify that the runtime is safely configured before beginning autonomous execution.

### Usage

```python
from src.agent.policy import RunPolicy
from src.agent.production_readiness import ProductionReadinessChecker
from src.core.retry import RetryPolicy

# Evaluate configuration and stores
report = ProductionReadinessChecker.evaluate(
    policy=RunPolicy(max_iterations=20, max_tool_calls=30, timeout_seconds=300),
    retry_policy=RetryPolicy(max_attempts=3, base_delay=2.0, max_delay=30.0),
    checkpoint_path="data/checkpoints.jsonl",
    idempotency_path="data/idempotency.jsonl",
)

if not report.ready:
    for check in report.checks:
        if not check.passed:
            print(f"FAILED CHECK: {check.name} - {check.reason}")
    raise SystemExit("Agent runtime is NOT READY for autonomous execution")

print("Agent runtime is READY")
```

### Readiness Checks Executed

| Check Name | Target | Success Condition |
| :--- | :--- | :--- |
| `run_policy_validity` | `RunPolicy` | `max_iterations >= 0`, `max_tool_calls >= 0`, `timeout_seconds > 0` |
| `retry_policy_sanity` | `RetryPolicy` | `max_attempts >= 1`, `base_delay >= 0`, `max_delay >= base_delay` |
| `checkpoint_store_health` | `checkpoints.jsonl` | File missing (fresh ready), empty, or 100% valid JSON with valid event sequences & transitions |
| `idempotency_store_health` | `idempotency.jsonl` | File missing (fresh ready), empty, or 100% valid JSONL with consistent timestamp ordering |
| `cross_store_consistency` | Checkpoint + Idempotency | `RunIntegrityVerifier` audits all active/recoverable runs across both stores |
| `terminal_run_immutability` | Recovery Analysis | All persisted terminal runs are classified as non-recoverable or completed |

### READY vs. NOT_READY Semantics

- **`READY`**: All configuration parameters are strictly valid, and all persistent store files are structurally sound and internally consistent.
- **`NOT_READY`**: One or more safety-critical checks failed. Autonomous execution must not start.

### What Readiness Does NOT Test
- Upstream LLM provider uptime or live API reachability.
- Network / internet connectivity.
- Third-party API quotas, credentials, or balances.
- Business logic correctness of user-defined tools.

---

## 4. Operational Behaviors & Semantics

### Crash & Resume
- Resuming an interrupted run inspects durable checkpoints via `RecoveryAnalyzer`.
- If the last state is `TOOL_EXECUTING` with pending tool calls, pending tools with existing stable `call_id`s are executed or replayed from idempotency cache before continuing the LLM reasoning loop.
- Consumed iteration and tool call counts are restored from checkpoint history.

### Retry Continuation Cancellation Guard
- When `RetryManager` schedules a backoff delay, it invokes `before_retry_attempt(next_attempt)` before executing attempt $N+1$.
- If the run has been cancelled, halted, completed, or if the checkpoint store is corrupted, the guard fails closed and prevents attempt $N+1$ from running.

### Timeout Limitations
- The `timeout_seconds` parameter in `RunPolicy` is enforced per active session invocation via `asyncio.wait_for`. In the current release, it applies to each continuous process execution rather than spanning cumulative clock time across offline restart intervals.

---

## 5. Verification Commands

### Run Focused Phase 5.6 Test Suite
```powershell
.\venv\Scripts\python -m pytest tests/integration/test_phase56_production_readiness.py tests/integration/test_phase56_soak.py tests/integration/test_phase56_fault_injection.py tests/integration/test_phase56_concurrency.py -v
```

### Run Complete Repository Suite
```powershell
.\venv\Scripts\python -m pytest tests/ -q -W ignore
```
