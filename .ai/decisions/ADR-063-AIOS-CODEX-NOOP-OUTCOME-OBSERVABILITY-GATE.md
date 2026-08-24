# ADR-063 — AIOS Codex No-Op Outcome Observability Gate

STATUS: ACCEPTED
CHANGE_CLASS: IMPLEMENTATION_REFINEMENT
HUMAN_APPROVED: YES
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.1
MILESTONE: P1
CANONICAL_REQUIREMENT_IDENTITY_CHANGED: NO
ROADMAP_VERSION_BUMP_REQUIRED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

## Context

Two consecutive Human-authorized bounded Codex RUNs ended with `EXITED_ZERO + CLEAN_NO_WORKTREE_DELTA` while the requested baseline work was demonstrably absent:

```text
TASK-085 → CLEAN_NO_WORKTREE_DELTA
TASK-086 → CLEAN_NO_WORKTREE_DELTA
```

TASK-086 explicitly required creation of `src/aios_bridge/worker_flow.py`; that file was absent on its bound baseline. Therefore the second clean no-op cannot be interpreted as valid completion or as evidence that the task was already satisfied.

Audit of the current execution path shows:

```text
canonical WORK artifact is present in ExecutorContextPack
WORK artifact is role=WORK and exact-blob verified
context payload is passed byte-for-byte to `codex exec -` via stdin
Codex sandbox is workspace-write
Bridge observes exit status, stream byte counts, and event-type names
Bridge does NOT preserve a bounded explicit executor outcome/reason for a clean no-op
```

The current diagnostic therefore answers "what transport status happened" but not "what explicit terminal outcome did the executor report". Blindly retrying TASK-086 would repeat an opaque failure mode and increase TTTC.

## Decision

Insert one bounded diagnostic gate before resuming TASK-086.

```text
TASK-088 — Codex No-Op Outcome Observability
    ↓ PASS / merge
re-author + rebind TASK-086 on new canonical main
    ↓
TASK-086 — P1.0A Transactional RUN/FIX + Evidence Refresh
    ↓ PASS / merge
TASK-087 — P1.0B Failure Classification + Deterministic Next Action
```

TASK-087 remains reserved for the ADR-062 failure-classification slice and MUST NOT be repurposed.

TASK-086 is paused and MUST NOT be rerun until TASK-088 is PASS/merged and TASK-086 is rebound to the then-current main.

## Bounded Executor Outcome Contract

The diagnostic gate must expose only safe terminal execution evidence. It MUST NOT persist model chain-of-thought, hidden reasoning, unrestricted stdout, or arbitrary long text.

Introduce a closed bounded outcome vocabulary equivalent to:

```text
IMPLEMENTED
BLOCKED
NO_WORK_REQUIRED
INSTRUCTION_CONFLICT
UNKNOWN
```

The executor context must request one explicit terminal machine-readable outcome marker from the bounded worker. Example semantic shape:

```text
AIOS_EXECUTOR_OUTCOME: IMPLEMENTED | BLOCKED | NO_WORK_REQUIRED | INSTRUCTION_CONFLICT | UNKNOWN
```

A short bounded explicit reason code/message may be captured only from the worker's final user-visible/agent-message output when the transport can identify that output without ambiguity. If final-message identification is unavailable, preserve `UNKNOWN`; do not infer from hidden reasoning or unrelated events.

## Safe Diagnostic Requirements

At minimum persist:

```text
executor_outcome
final_agent_message_observed: YES | NO | UNKNOWN
command_activity_count: observed integer or UNKNOWN
file_change_activity_count: observed integer or UNKNOWN
stdout_event_types: existing bounded set
```

Rules:

```text
NO_CHAIN_OF_THOUGHT_CAPTURE: YES
NO_REASONING_EVENT_CONTENT_CAPTURE: YES
NO_RAW_STDOUT_PERSISTENCE: YES
NO_SECRET_ENVIRONMENT_EXPANSION: YES
BOUNDED_FINAL_MESSAGE_BYTES: REQUIRED
UNKNOWN_IS_ALLOWED: YES
UNKNOWN_MUST_NOT_BE_FABRICATED_AS_ZERO_OR_SUCCESS: YES
```

## Clean No-Op Diagnostic Semantics

Until ADR-062/TASK-087 implements final failure classification, existing `CLEAN_NO_WORKTREE_DELTA` fail-closed behavior remains unchanged.

However, when a clean no-op occurs after TASK-088, the Bridge/user-facing terminal report must include the bounded executor outcome evidence when available, for example:

```text
CLEAN_NO_WORKTREE_DELTA
EXECUTOR_OUTCOME: NO_WORK_REQUIRED
FINAL_AGENT_MESSAGE_OBSERVED: YES
```

or:

```text
CLEAN_NO_WORKTREE_DELTA
EXECUTOR_OUTCOME: UNKNOWN
FINAL_AGENT_MESSAGE_OBSERVED: NO
```

This task does not automatically retry, reroute, reinterpret no-op as success, or implement session recovery.

## Executor Choice

TASK-088 SHOULD be executed by Antigravity because the bounded Codex path itself is the component under diagnosis. This is not an executor policy change; it is a one-task diagnostic choice.

## Authority Preservation

```text
TASK authority: unchanged
roadmap authority: unchanged
review authority: unchanged
handoff authority boundary: unchanged
lease semantics: unchanged
P0 validation ownership: unchanged
auto retry: NO
auto reroute: NO
P2/P3: NOT AUTHORIZED
H5-H8: NOT AUTHORIZED
```

## Completion Condition

TASK-088 may PASS only when tests prove that a synthetic Codex JSON event stream can produce bounded safe executor-outcome evidence without persisting reasoning content, and clean-noop reporting can surface that evidence without changing fail-closed publication semantics.