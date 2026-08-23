# ADR-047 — Codex Terminal Diagnostic Tail Capture & Productive Nonzero Recovery Contract Lock

STATUS: LOCKED
CLASS: E2.3 / E4.2 SUPPORTING REFINEMENT — CODEX TERMINAL OBSERVABILITY & REVIEWABLE RECOVERY
BASELINE_MAIN_SHA: c6bd8943b0e2420391961fe2d3203ec0b65068c9
APPLIES_BEFORE: H3 IMPLEMENTATION
RELATED: ADR-030 / ADR-032 / ADR-040 / ADR-042 / ADR-044 / ADR-046
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO

## Context

TASK-072 exposed a second Codex operational failure class after TASK-073 had already fixed clean no-op behavior.

Observed TASK-072 facts were:

```text
Codex bounded process: invoked once
worktree delta: non-empty
changed implementation paths: exactly inside TASK-072 writable scope
adapter/transport exit code: 1
persistent diagnostic shape: JSON_EVENT_STREAM
terminal diagnostic cause: not available
executor rerun during recovery: NO
recovered implementation: targeted tests PASS, full suite PASS, ChatGPT code audit PASS
```

The exact semantic reason for the historical Codex exit code 1 is not recoverable because ADR-040 intentionally forbids persistent raw stdout/stderr and the temporary capture has already been deleted. This ADR MUST NOT fabricate a root cause such as quota exhaustion, context limit, authentication failure, sandbox failure, or provider outage without mechanical evidence.

A concrete observability defect is nevertheless proven in the current transport: `_analyze_diagnostic_stream()` records exact total output size but analyzes only the first `MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM = 65536` bytes of each stream. A long JSON event stream can therefore place its terminal `turn.failed`, `error`, or `turn.completed` event outside the scanned prefix. The transport then retains `stdout_scan_truncated = true` but may classify only the early event shape and lose terminal-state evidence.

The existing test suite proves truncation is flagged, but does not prove a terminal event beyond the first 64 KiB is observed.

TASK-072 also exposed an operational gap in E4. `cmd_execute()` persists diagnostic and dirty-path evidence, then rejects every non-zero transport status before running the Git/scope gate or canonical publication tests. Consequently, a non-zero process that produced a useful exact-scope delta requires manual preservation/testing/publication. That recovery is safe but unnecessarily burdens the Human and can allow branch ancestry to drift while a separate hardening task is merged.

---

## Decision 1 — Historical Root Cause Remains UNKNOWN

For the historical TASK-072 invocation:

```text
CODEX_EXIT_CODE: 1
EXACT_SEMANTIC_ROOT_CAUSE: UNKNOWN / NOT RECOVERABLE
```

The system may state only mechanically proven facts from receipt/diagnostic/Git/test evidence.

`diagnostic.code` remains an observed-shape code, never an inferred semantic root cause.

---

## Decision 2 — Keep the Existing 64 KiB Per-Stream Analysis Budget

ADR-040 privacy/resource bounds remain intact.

For each stdout/stderr stream:

```text
MAX_TOTAL_DIAGNOSTIC_ANALYSIS_BYTES_PER_STREAM = 65536
```

No implementation may increase unbounded Python-memory capture or persist raw output.

If total stream size is at or below the bound, analyze the complete stream.

If total stream size exceeds the bound, analyze bounded head and tail slices whose combined maximum is no greater than 65536 bytes. Recommended split:

```text
HEAD_BYTES = 32768
TAIL_BYTES = 32768
HEAD_BYTES + TAIL_BYTES <= 65536
```

Equivalent deterministic splits are acceptable only if the total bound remains exact and tested.

---

## Decision 3 — Terminal-Aware Head + Tail NDJSON Parsing

For truncated Codex `--json` stdout:

1. analyze complete NDJSON records from the bounded head;
2. analyze complete NDJSON records from the bounded tail;
3. preserve chronological head-before-tail ordering;
4. deduplicate event-type vocabulary without changing terminal ordering;
5. ignore only boundary fragments caused by slice cuts;
6. never promote a partial JSON fragment to a non-JSON failure signal merely because the bounded slice begins/ends mid-record.

The final safe `last_stdout_event_type` must represent the last complete valid recognized event in the analyzed tail when one exists.

Mechanically recognized failure event types remain exactly the closed vocabulary already locked by the transport, including:

```text
error
turn.failed
```

If either appears in a complete analyzed head/tail event, diagnostic code must be `JSON_ERROR_EVENT`.

A terminal `turn.completed` in the tail must remain observable as `last_stdout_event_type = turn.completed`.

No free-form error message, model prose, command, path, source content, reasoning, provider body, or nested arbitrary JSON value may persist.

---

## Decision 4 — Raw Diagnostic Privacy Remains Unchanged

Still forbidden:

```text
RAW_STDOUT_IN_WORKTREE
RAW_STDERR_IN_WORKTREE
RAW_STDOUT_IN_RUNTIME_RECEIPT
RAW_STDERR_IN_RUNTIME_RECEIPT
RAW_OUTPUT_IN_RESULT_ARTIFACT
RAW_PROVIDER_OR_MODEL_MESSAGE_PERSISTENCE
```

Temporary full capture sinks must still be outside the worktree and persistent AIOS runtime, and must be closed/deleted before the transport outcome returns.

No credential-value logging is introduced.

---

## Decision 5 — Define Productive Nonzero as a Recovery Class, Not Success

A Codex invocation is eligible for **productive-nonzero recovery consideration** only when all of the following are mechanically true:

```text
receipt.status == EXITED_NONZERO
receipt.error_code == CODEX_EXIT_NONZERO
pre_branch == post_branch == authorized target branch
pre_head_sha == post_head_sha
dirty_paths is non-empty
all dirty paths pass the existing exact E4 allowed-scope validator
protected Git administration trust snapshot remains valid
ACTIVE authorization/lease/execution bindings remain exact
no executor rerun occurred
```

This classification MUST NOT change the E1 `InvocationReceipt` status. Exit code 1 remains `EXITED_NONZERO`.

It MUST NOT be called executor success, transport success, task PASS, review PASS, or merge approval.

---

## Decision 6 — Productive Nonzero May Enter Canonical Review Publication

ADR-032's blanket `EXITED_NONZERO -> no publication` rule is narrowly refined for Codex productive-nonzero recovery only.

After the exact productive-nonzero predicate passes, E4 may continue through the same canonical publication path used for normal execution, provided:

```text
existing Git/scope validation: PASS
canonical full repository test command: exit 0
publisher authorization/control artifact checks: PASS
publication trust checks: PASS
```

If all pass, Bridge may publish the preserved work to `ai/task-N` for ChatGPT review **without rerunning Codex**.

Publication in this mode means only:

```text
REVIEWABLE_PRESERVED_DELTA
```

It does not convert the transport outcome to `EXITED_ZERO`.

Canonical publication notes/receipt evidence must retain safe facts equivalent to:

```text
E4_TRANSPORT_STATUS: EXITED_NONZERO
E4_TRANSPORT_ERROR: CODEX_EXIT_NONZERO
E4_TRANSPORT_DIAGNOSTIC: <bounded diagnostic code>
E4_PRODUCTIVE_NONZERO_RECOVERY: YES
EXECUTOR_RERUN: NO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
```

These are Bridge-generated operational facts, not task-authored custom RESULT schema requirements.

---

## Decision 7 — Full Tests Are the Recovery Boundary

Productive-nonzero publication is permitted only after the canonical full repository suite returns exit code 0.

If canonical tests fail:

```text
publish: NO
commit/push: NO
auto retry: NO
auto reroute: NO
worktree: PRESERVE
state: RECOVERY_REQUIRED
```

The Human must receive only bounded safe diagnostic/test status, not raw Codex output.

No targeted-test-only bypass is allowed.

---

## Decision 8 — Unsafe Nonzero Outcomes Still Fail Closed

The productive-nonzero path MUST NOT activate when any of these are observed:

```text
FAILED_TO_START
TIMED_OUT
INTERRUPTED
branch drift
HEAD drift
empty dirty path set
out-of-scope dirty path
protected Git administration drift
authorization/lease mismatch
publication trust mismatch
diagnostic/receipt integrity failure
```

Those outcomes retain existing `EXECUTION_BLOCKED` / `RECOVERY_REQUIRED` semantics.

No automatic reset, checkout, rebase, cherry-pick, force-push, retry, reroute, or second executor invocation is authorized.

---

## Decision 9 — Avoid the TASK-072 Ancestry Drift Failure Class

When productive-nonzero work is valid and full tests pass, publication should occur in the same E4 execution/recovery transaction before unrelated task work is started.

The Bridge must bind publication to the exact authorization base/current branch state and existing Git/scope validators. If main/task ancestry or protected state has drifted, fail closed rather than synthesizing a branch repair.

No automatic branch-alignment merge commit is authorized by this ADR.

---

## Decision 10 — Worker Surface Remains Thin

`.agents/skills/aios-worker/scripts/aios_worker.py` remains a thin adapter.

It must not implement retry, reroute, Git recovery, test recovery, or publication policy itself. The recovery decision belongs to Bridge E4.

The Codex worker still launches at most one bounded Codex process per Human RUN/FIX authorization.

---

## Decision 11 — Required Regression Coverage

Focused tests must prove at minimum:

```text
LONG_JSON_STREAM_TAIL_TURN_FAILED: JSON_ERROR_EVENT
LONG_JSON_STREAM_TAIL_ERROR: JSON_ERROR_EVENT
LONG_JSON_STREAM_TAIL_TURN_COMPLETED: last event observed
TOTAL_ANALYZED_BYTES_PER_STREAM: <= 65536
HEAD_TAIL_BOUNDARY_PARTIAL_JSON: safely ignored as boundary fragment
RAW_ERROR_MESSAGE_PERSISTED: NO
RAW_STDOUT_STDERR_PERSISTED: NO

EXITED_NONZERO_WITH_EXACT_AUTHORIZED_DELTA: productive recovery candidate
PRODUCTIVE_NONZERO_FULL_SUITE_PASS: canonical publication allowed
PRODUCTIVE_NONZERO_FULL_SUITE_FAIL: no publication / work preserved
PRODUCTIVE_NONZERO_OUT_OF_SCOPE: no publication
PRODUCTIVE_NONZERO_BRANCH_OR_HEAD_DRIFT: no publication
PRODUCTIVE_NONZERO_SECOND_EXECUTOR: NO
PRODUCTIVE_NONZERO_RETRY: NO
PRODUCTIVE_NONZERO_REROUTE: NO
PRODUCTIVE_NONZERO_FORCE_PUSH: NO
CANONICAL_RECEIPT_STATUS_REWRITTEN_TO_ZERO: NO
```

Normal EXITED_ZERO publication, clean-no-op TASK-073 behavior, timeout/interruption behavior, and existing diagnostic privacy tests must remain green.

---

## Decision 12 — Implementation Scope / Executor

Because this refinement changes Codex transport/E4 failure handling, implementation must use:

```text
executor_id = antigravity
```

Codex must not implement the task that repairs its own transport path.

Expected production/test scope is limited to:

```text
bridge.py
src/aios_bridge/executor_transports/codex_local.py
src/aios_bridge/executor_transports/__init__.py   # only if public exports require it
tests/aios_bridge/test_codex_local_transport.py
tests/test_bridge_executor_automation.py
```

No H-Series implementation, dispatcher, paid API, worker-surface, dependency, or E1 receipt schema change is authorized.

---

## Acceptance

ADR-047 is implemented only when:

```text
HISTORICAL_TASK_072_ROOT_CAUSE_OVERCLAIMED: NO
DIAGNOSTIC_TOTAL_SCAN_BOUND_INCREASED: NO
BOUNDED_HEAD_TAIL_SCAN: PASS
TAIL_TERMINAL_EVENT_VISIBLE: PASS
RAW_OUTPUT_PERSISTED: NO
E1_RECEIPT_SCHEMA_CHANGED: NO
EXIT_NONZERO_REWRITTEN_TO_SUCCESS: NO
PRODUCTIVE_NONZERO_EXACT_SCOPE_REQUIRED: YES
PRODUCTIVE_NONZERO_FULL_SUITE_REQUIRED: YES
PRODUCTIVE_NONZERO_REVIEW_PUBLICATION: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
SECOND_EXECUTOR: NO
FORCE_PUSH: NO
PAID_API: NO
TARGETED_TESTS: PASS
FULL_REPOSITORY_TESTS: PASS
REGRESSIONS: 0
```

H3 remains implementation-unauthorized until this supporting refinement is reviewed and merged.