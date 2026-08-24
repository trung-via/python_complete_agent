# ADR-061 — AIOS P1.0 Transactional Worker Flow & Fix Recovery Contract

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

TASK-083/P0 exposed two operator-flow defects even though the underlying fail-closed governance remained safe:

1. the operator experience made `STATUS`/sync appear to be a prerequisite before RUN/FIX when control artifacts changed; and
2. FIX execution treated all CHANGES_REQUIRED reviews as implementation work, so evidence-only refreshes, clean no-op outcomes, and timeout outcomes could fall into repeated manual recovery steps.

P0 already enforces read-only synchronization in the Bridge `handoff` authority path. P1.0 MUST preserve that mechanism and make the operator contract transactional; it MUST NOT add a second independent synchronization authority or weaken exact artifact binding.

## Decision

### D1 — One operator intent is one transaction

The supported operator contract is:

```text
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N
```

RUN/FIX MUST internally perform all required read-only synchronization, exact artifact resolution, preflight, authorization, and executor/certification continuation appropriate to the selected mode. `STATUS` is diagnostic only and MUST NOT be a prerequisite for RUN/FIX.

```text
STATUS_CREATES_AUTHORITY: NO
STATUS_REQUIRED_BEFORE_RUN: NO
STATUS_REQUIRED_BEFORE_FIX: NO
SYNC_BEFORE_AUTHORITY: YES
SYNC_FAILURE_BLOCKS_AUTHORITY: YES
```

### D2 — Closed FIX execution modes

A CHANGES_REQUIRED review may declare a closed FIX mode:

```text
IMPLEMENTATION
EVIDENCE_REFRESH
```

Compatibility rule: absence of an explicit mode is fail-conservatively interpreted as `IMPLEMENTATION`; evidence-only execution is never inferred from a clean worktree or from executor behavior alone.

`IMPLEMENTATION`:
- bounded executor execution is required;
- a clean successful executor result remains `CLEAN_NO_WORKTREE_DELTA` unless the review itself has been superseded by a newer exact artifact;
- certification/publish occurs only after valid implementation/recovery evidence.

`EVIDENCE_REFRESH`:
- requires explicit authoritative review marker;
- requires exact reviewed head and clean worktree;
- MUST NOT invoke a bounded executor;
- acquires fresh FIX authorization/lease;
- runs canonical certification at the certification boundary;
- republishes RESULT using the currently loaded Bridge implementation.

### D3 — FIX must re-resolve the latest exact REVIEW atomically

RUN/FIX must synchronize and resolve the latest exact control artifact before authority is minted. If the review changes between synchronization and authorization, the transaction fails closed and returns one deterministic next action. The operator must not need to run STATUS merely to refresh the review cache.

### D4 — Bounded failure classification

The worker flow must distinguish at least:

```text
CLEAN_NO_WORKTREE_DELTA
CLEAN_TIMEOUT
DIRTY_TIMEOUT_RECOVERY_REQUIRED
PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
PREAUTH_ARTIFACT_INVALID
CERTIFICATION_FAILED
```

Rules:
- no automatic retry;
- no automatic reroute;
- `CLEAN_TIMEOUT` means no preserved implementation delta exists and stale execution authority must not be silently reused;
- `DIRTY_TIMEOUT_RECOVERY_REQUIRED` preserves the exact worktree and blocks a fresh executor start until an explicit Human recovery action is taken;
- productive non-zero recovery keeps the existing ADR-047 strict preserved-delta checks;
- evidence refresh is not classified as implementation recovery.

### D5 — One deterministic next action

Every blocked RUN/FIX transaction must emit one machine-readable and one human-readable next action. The normal operator must not need to compose `sync -> handoff -> execute -> publish` manually.

Examples:

```text
NEXT_ACTION: FIX TASK-N
NEXT_ACTION: Review TASK-N
NEXT_ACTION: RECOVERY_REQUIRED_PRESERVED_DELTA
NEXT_ACTION: CORRECT_CONTROL_ARTIFACT
```

P1.0 does not create public resume/checkpoint/session semantics. A preserved dirty timeout may still require a separately governed recovery step; P1.0 only makes that state explicit and non-ambiguous.

### D6 — Provider-neutral semantics

Antigravity and Codex may retain different transport/session mechanics, but RUN/FIX synchronization, FIX-mode parsing, failure classification, next-action semantics, validation ownership, and RESULT evidence are shared. Future Claude Code must consume the same contract.

### D7 — Authority invariants remain unchanged

P1.0 MUST NOT redesign:

```text
TASK authority
REVIEW authority
roadmap authority
executor lease cardinality
scope enforcement
publication trust
reviewed-head merge safety
Human executor selection
automatic retry/reroute policy
```

## Out of Scope

```text
P1 capability batching/integration lane itself
P2 persistent sessions
checkpoint/resume
capacity suspension
shell interception
cross-executor automatic continuation
P3 Claude adapter/adaptive selection
H5-H8
```

## Acceptance

P1.0 is accepted only when evidence proves:

```text
RUN_SINGLE_COMMAND_TRANSACTION: PASS
FIX_SINGLE_COMMAND_TRANSACTION: PASS
STATUS_NOT_PREREQUISITE: PASS
SYNC_FAILURE_BLOCKS_PREAUTH: PASS
LATEST_REVIEW_EXACTLY_BOUND: PASS
FIX_MODE_CLOSED: PASS
LEGACY_FIX_DEFAULTS_IMPLEMENTATION: PASS
EVIDENCE_REFRESH_SKIPS_EXECUTOR: PASS
EVIDENCE_REFRESH_CERTIFIES_AND_PUBLISHES: PASS
IMPLEMENTATION_CLEAN_NOOP_BLOCKS: PASS
CLEAN_TIMEOUT_CLASSIFIED: PASS
DIRTY_TIMEOUT_PRESERVED: PASS
NO_AUTO_RETRY: PASS
NO_AUTO_REROUTE: PASS
ONE_DETERMINISTIC_NEXT_ACTION: PASS
ANTIGRAVITY_CODEX_POLICY_PARITY: PASS
P2_P3_NOT_OPENED: PASS
H5_NOT_OPENED: PASS
```

## Rationale

This refinement reduces Human Attention and Time-to-Trusted-Capability without moving session-resume complexity into P1. It directly addresses the operator friction observed during TASK-083 while preserving the fail-closed control plane proven by P0.