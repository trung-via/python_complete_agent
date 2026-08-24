# ADR-062 — AIOS P1.0 Bounded Slice Decomposition After CLEAN_NO_WORKTREE_DELTA

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

The first bounded Codex RUN of TASK-085 completed transport execution with `EXITED_ZERO` but produced `CLEAN_NO_WORKTREE_DELTA`, so no RESULT was published and no implementation commit exists.

The operator-level proof from that run is still useful:

```text
STATUS command before RUN: NOT USED
handoff synchronization/preflight: PASSED
TASK-085 authorization: PASSED
bounded Codex invocation: STARTED
publication: BLOCKED_CLEAN_NO_WORKTREE_DELTA
```

The no-op was not a valid indication that P1.0 work was already complete. On the reviewed baseline, the following requested concepts are absent:

```text
src/aios_bridge/worker_flow.py: ABSENT
FixExecutionMode: ABSENT
EVIDENCE_REFRESH: ABSENT
CLEAN_TIMEOUT: ABSENT
```

TASK-085 combined transaction orchestration, latest-review rebinding, closed FIX modes, evidence-only publication, timeout classification, next-action vocabulary, and provider parity in one bounded executor task. That breadth is unnecessary and increases executor ambiguity.

## Decision

TASK-085 is dispositioned as a non-productive execution probe and is superseded before any implementation publication.

P1.0 is decomposed into ordered bounded slices:

```text
TASK-086 — P1.0A Transactional RUN/FIX + Evidence Refresh
    ↓ review + merge
TASK-087 — P1.0B Failure Classification + Deterministic Next Action
    ↓ review + merge
then continue normal P1 capability-batch work
```

TASK-087 MUST NOT be authored as executable work until TASK-086 is PASS/merged so its exact baseline can be bound to the then-current canonical main.

## TASK-086 Boundary

TASK-086 owns only:

```text
single-command RUN/FIX transaction semantics
STATUS not prerequisite
latest exact REVIEW re-resolution in same FIX transaction
closed FIX mode: IMPLEMENTATION | EVIDENCE_REFRESH
EVIDENCE_REFRESH skips bounded executor
EVIDENCE_REFRESH performs canonical T2 exactly once then republishes RESULT
Codex/Antigravity policy semantics for those behaviors
```

It does NOT own timeout classification beyond preserving current fail-closed behavior.

## TASK-087 Boundary

TASK-087 will own only after TASK-086 merge:

```text
CLEAN_NO_WORKTREE_DELTA terminal classification and one next action
CLEAN_TIMEOUT
DIRTY_TIMEOUT_RECOVERY_REQUIRED
PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE compatibility
bounded next-action vocabulary
no manual git inspection as normal discovery path
```

No persistent session, checkpoint/resume, shell interception, automatic retry, or automatic reroute is authorized.

## No Blind Retry Rule

The exact TASK-085 RUN that returned clean no-op MUST NOT be blindly rerun with the same executable artifact. Human-approved continuation is through the narrower TASK-086 artifact.

## Authority Preservation

```text
TASK authority: unchanged
roadmap authority: unchanged
review authority: unchanged
handoff authority boundary: unchanged
lease semantics: unchanged
auto retry: NO
auto reroute: NO
P2/P3: NOT AUTHORIZED
H5-H8: NOT AUTHORIZED
```
