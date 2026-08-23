# TASK-074 — Codex Terminal Diagnostic Tail Capture & Productive Nonzero Recovery Hardening

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: SUPPORTING BRIDGE REFINEMENT BEFORE H3
MILESTONE: E2.3 / E4.2
EXECUTOR_MODE: ANTIGRAVITY_ONLY
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
TARGET_BRANCH: ai/task-074
H0_STATUS: COMPLETE
H1_STATUS: COMPLETE
H2_STATUS: COMPLETE
H3_IMPLEMENTATION_AUTHORIZED: NO
ADR: ADR-047
ADR_BLOB_SHA: dfe872e4e2d6ad021ec0c338ed46d730c3c95c26
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
REAL_CODEX_REQUIRED: NO
REAL_ANTIGRAVITY_REQUIRED: YES
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-032-E4-APPROVED-EXECUTOR-AUTOMATION-AND-AUTO-PUBLICATION-CONTRACT-LOCK.md","blob_sha":"22c300f882327aa812ad5e3250bf53ba8cf85eb5"},{"path":".ai/decisions/ADR-040-CODEX-LOCAL-TRANSPORT-BOUNDED-DIAGNOSTIC-OBSERVABILITY-CONTRACT-LOCK.md","blob_sha":"04937776829675e77a1651152bba16e7e7f31426"},{"path":".ai/decisions/ADR-046-CODEX-E4-IMPLEMENTATION-INTENT-CLEAN-NOOP-RECOVERY-CONTRACT-LOCK.md","blob_sha":"de5b63eb0c23681ec3feb427f44b91d8f44151c0"},{"path":".ai/decisions/ADR-047-CODEX-TERMINAL-DIAGNOSTIC-TAIL-PRODUCTIVE-NONZERO-RECOVERY-CONTRACT-LOCK.md","blob_sha":"dfe872e4e2d6ad021ec0c338ed46d730c3c95c26"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/executor_transports/codex_local.py","src/aios_bridge/executor_transports/__init__.py","tests/aios_bridge/test_codex_local_transport.py","tests/test_bridge_executor_automation.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The publisher profile and three E4 marker lines above are the complete executable authoring inputs. They create no retry, reroute, Codex invocation, paid-provider, merge, or H3 authority.

## Objective

Implement ADR-047 as a narrow Codex/E4 hardening refinement so a long Codex JSON stream retains bounded terminal-event observability and a non-zero Codex process that nevertheless produced a fully authorized, exact-scope, test-green delta can be submitted automatically for ChatGPT review without rerunning the executor.

This task MUST NOT attempt to infer the historical semantic cause of TASK-072's exit code 1. That cause is unavailable from surviving evidence.

## Proven Failure Class to Fix

Current transport behavior mechanically does:

```text
measure total stdout bytes
seek stdout to byte 0
read at most first 65536 bytes
parse only that prefix
```

Therefore a terminal `turn.failed`, `error`, or `turn.completed` after the first 64 KiB can be invisible even though `stdout_scan_truncated = true`.

Current E4 behavior also does:

```text
persist receipt + diagnostic + dirty paths
if receipt.status != EXITED_ZERO:
    RECOVERY_REQUIRED / stop
```

before the exact Git/scope gate and canonical publication tests. TASK-072 proved this can preserve valuable code but force manual recovery.

## Writable Scope

Executor may modify only:

```text
bridge.py
src/aios_bridge/executor_transports/codex_local.py
src/aios_bridge/executor_transports/__init__.py
                        # only if a new public constant/type export is actually required
tests/aios_bridge/test_codex_local_transport.py
tests/test_bridge_executor_automation.py
```

Bridge-generated `.ai/results/RESULT-074.md` is publication output, not executor writable scope.

Explicitly forbidden:

```text
src/aios_bridge/continuity/**
src/aios_bridge/executor_context.py
src/aios_bridge/executor_automation.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/task_authoring.py
src/aios_engineering/**
.agents/**
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
requirements.txt
```

No dependency change.

## Part A — Bounded Head + Tail Terminal Diagnostics

Keep the existing per-stream total analysis budget at **65536 bytes maximum**.

Required behavior:

```text
stream <= 65536 bytes
    -> analyze complete stream

stream > 65536 bytes
    -> analyze deterministic bounded HEAD + TAIL
    -> combined analyzed raw bytes <= 65536
```

Recommended split is 32768 head + 32768 tail.

For truncated stdout NDJSON:

- parse complete records from the head and tail only;
- ignore boundary fragments caused solely by slicing in the middle of one line;
- preserve chronological head-before-tail event order;
- maintain bounded unique event-type vocabulary;
- terminal valid event in tail determines `last_stdout_event_type` when present;
- safe tail `error` or `turn.failed` must mechanically produce `JSON_ERROR_EVENT`;
- tail `turn.completed` must be observable;
- no arbitrary JSON field/message/body may be retained.

Do not increase raw-output persistence. Temporary sinks remain ephemeral and outside worktree/runtime persistence.

## Part B — Productive Nonzero Recovery Predicate

Add a pure/bounded predicate or equivalent clearly testable logic for Codex productive-nonzero recovery consideration.

It may be true only when:

```text
receipt.status == EXITED_NONZERO
receipt.error_code == CODEX_EXIT_NONZERO
pre_branch == post_branch == authorized target branch
pre_head_sha == post_head_sha
dirty_paths non-empty
protected publication/Git trust snapshot valid
existing exact allowed-scope validation passes
ACTIVE authorization/lease/execution bindings remain exact
```

Do not rewrite or replace the canonical `InvocationReceipt`. Exit 1 remains EXITED_NONZERO.

## Part C — Canonical Review Publication Without Executor Rerun

Refactor `cmd_execute()` only as needed so a productive-nonzero candidate is not rejected before the exact Git/scope validator.

Required order for Codex nonzero with dirty work:

```text
persist canonical invocation evidence
    -> verify protected publication trust
    -> observe branch/head/dirty paths
    -> exact Git/scope validation
    -> if productive-nonzero predicate passes
         run canonical full repository suite exactly once in the E4 publication transaction
         if suite PASS -> canonical publish preserved delta for ChatGPT review
         if suite FAIL -> no commit/push; preserve work; RECOVERY_REQUIRED
```

Normal EXITED_ZERO path must remain unchanged.

Productive-nonzero publication must use existing canonical publisher. It must not create a parallel publisher or custom task RESULT schema.

Safe Bridge-generated publication notes/evidence must make clear that:

```text
transport remained EXITED_NONZERO
error remained CODEX_EXIT_NONZERO
bounded diagnostic code was preserved
productive-nonzero recovery was used
executor rerun = NO
scope/trust validation = PASS
```

Do not write `E4_TRANSPORT_STATUS: EXITED_ZERO` for this recovery path.

## Part D — Failure / Safety Semantics

Productive-nonzero recovery MUST NOT activate for:

```text
FAILED_TO_START
TIMED_OUT
INTERRUPTED
empty worktree delta
branch drift
HEAD drift
out-of-scope dirty path
protected Git administration drift
authorization/lease mismatch
publication trust mismatch
canonical full-suite failure
```

Those states remain fail-closed and preserve work where appropriate.

Absolutely forbidden:

```text
automatic retry
automatic reroute
second executor invocation
Codex self-retry
paid API fallback
weaker sandbox/network policy
force push
reset/checkout/rebase/cherry-pick recovery
automatic merge
```

## Mandatory Tests

Extend focused tests to prove at minimum:

```text
TAIL_FAILURE_AFTER_64K: JSON_ERROR_EVENT
TAIL_ERROR_AFTER_64K: JSON_ERROR_EVENT
TAIL_TURN_COMPLETED_AFTER_64K: OBSERVED_AS_LAST_EVENT
TOTAL_ANALYSIS_BYTES_PER_STREAM: <= 65536
HEAD_SLICE_PARTIAL_FINAL_LINE: NOT_FALSE_NON_JSON
TAIL_SLICE_PARTIAL_FIRST_LINE: NOT_FALSE_NON_JSON
RAW_FAILURE_MESSAGE_PERSISTED: NO
RAW_STDOUT_STDERR_PERSISTED: NO

PRODUCTIVE_NONZERO_EXACT_SCOPE: ACCEPT_RECOVERY_CANDIDATE
PRODUCTIVE_NONZERO_RECEIPT_REWRITTEN: NO
PRODUCTIVE_NONZERO_SCOPE_GATE_RUNS: YES
PRODUCTIVE_NONZERO_FULL_SUITE_PASS: PUBLISHED_FOR_REVIEW
PRODUCTIVE_NONZERO_FULL_SUITE_FAIL: NOT_PUBLISHED
PRODUCTIVE_NONZERO_OUT_OF_SCOPE: NOT_PUBLISHED
PRODUCTIVE_NONZERO_BRANCH_DRIFT: NOT_PUBLISHED
PRODUCTIVE_NONZERO_HEAD_DRIFT: NOT_PUBLISHED
PRODUCTIVE_NONZERO_RETRY: NO
PRODUCTIVE_NONZERO_REROUTE: NO
PRODUCTIVE_NONZERO_SECOND_EXECUTOR: NO
```

Regression tests must also prove:

```text
EXITED_ZERO_NORMAL_PUBLICATION: PRESERVED
EXITED_ZERO_CLEAN_NOOP_TASK_073_BEHAVIOR: PRESERVED
TIMEOUT_INTERRUPT_BEHAVIOR: PRESERVED
SAFE_CODEX_ARGV: UNCHANGED
CLOSED_CHILD_ENVIRONMENT: UNCHANGED
NETWORK_DISABLED: UNCHANGED
```

Use fake/monkeypatched Codex subprocesses only. Do not launch a real Codex model during automated tests.

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_codex_local_transport.py tests/test_bridge_executor_automation.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Pre-task full-suite baseline:

```text
2302 passed, 7 skipped, 0 failed
```

## Acceptance Boundary

TASK-074 passes only if:

```text
BOUNDED_HEAD_TAIL_DIAGNOSTIC: PASS
TAIL_TERMINAL_FAILURE_VISIBLE: PASS
TAIL_TERMINAL_COMPLETION_VISIBLE: PASS
TOTAL_DIAGNOSTIC_SCAN_BOUND_INCREASED: NO
RAW_OUTPUT_PERSISTED: NO
PRODUCTIVE_NONZERO_REVIEW_RECOVERY: PASS
CANONICAL_RECEIPT_EXIT_NONZERO_PRESERVED: YES
FULL_SUITE_REQUIRED_BEFORE_RECOVERY_PUBLICATION: YES
AUTO_RETRY: NO
AUTO_REROUTE: NO
SECOND_EXECUTOR: NO
PAID_API: NO
FORCE_PUSH: NO
H_SERIES_CODE_CHANGED: NO
TARGETED_TESTS: PASS
FULL_REPOSITORY_TESTS: PASS
GIT_DIFF_CHECK: PASS
```

Completion of TASK-074 does not itself authorize H3 implementation. H3 resumes only after ChatGPT review and merge of this refinement.