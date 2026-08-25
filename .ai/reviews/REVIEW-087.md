# REVIEW-087 — P1.0B Failure Classification + Deterministic Next Action
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: SEMANTICALLY_ACCEPTED_PENDING_T2
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-087
REVIEW_ROUND: 3
REVIEWED_TASK_HEAD_SHA: 12904cf867fe5c5fe5be901d94ece82e3523beca
REVIEWED_BASE_MAIN_SHA: ac0ae79e85e30a80410380188578db1993720b5b
TASK_ARTIFACT_BLOB_SHA: eb0d2455f6b98e6fa44a8db336dd78625e66820a
RESULT_BLOB_SHA: a7b6b0c9f7f322b381ef1f49ce653e3f5a6f1181
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 0
CODE_AUDIT: PASS
CANONICAL_TESTS: PENDING_CERTIFICATION
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
REQUIREMENT_BINDINGS_FINGERPRINT: d0c2a52e727d6042b2bf5aa22c0c4c5a94ab2229203ccfc44fb4578055523eba
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

## Snapshot

```text
HEAD: 12904cf867fe5c5fe5be901d94ece82e3523beca
PREVIOUS_REVIEWED_HEAD: a600fbab0eb2a1619b99c6e859f520954d9642b7
BASE_MAIN: ac0ae79e85e30a80410380188578db1993720b5b
MERGE_BASE: ac0ae79e85e30a80410380188578db1993720b5b
AHEAD_FROM_PREVIOUS_REVIEW: 1
AHEAD_FROM_MAIN: 3
BEHIND_MAIN: 0
MAIN_DRIFT: NO
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
TARGETED_TEST_STATUS: PASS
SLICE_C_IMPACT_CONFIDENCE: KNOWN
```

Round 3 is the Delta + Impact semantic review of the two remaining findings from Round 2. The FIX is exactly one commit on the previous reviewed head. The latest RESULT reports the bounded impacted test set PASS, protected accepted paths unchanged, and Review-First candidate-stage T2 count still equal to zero.

## Finding Closure

### B2 — CLOSED

The valid productive-nonzero path is now integrated as a blocked preserved-delta recovery boundary rather than a continuation toward testing/publication.

The Bridge still uses the existing strict deterministic gates first:

```text
EXITED_NONZERO + dirty delta
  -> validate_executor_worktree_delta
  -> branch/head/allowed-path scope proof
  -> publication-trust + authorization-binding predicate
```

Only after those gates establish a valid productive recovery candidate does Bridge construct `WorkerFailureEvidence` with:

```text
failure_class = PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
next_action = RECOVERY_REQUIRED_PRESERVED_DELTA
terminal_status = EXITED_NONZERO
```

The exact structured record is passed into the existing bounded operational-failure boundary, state becomes `RECOVERY_REQUIRED`, and execution terminates before the later targeted-test/publication continuation. Worktree/lease recovery semantics remain preserved; there is no reset, stash, commit, automatic retry, automatic reroute, or RESULT publication from the blocked execution path.

The new integration proof exercises a valid productive-nonzero candidate and verifies structured evidence persistence, exactly the required next action, `RECOVERY_REQUIRED`, and no publication. Existing negative proofs continue to reject branch drift, head drift, empty delta, out-of-scope delta, authorization drift, and exact-scope failure before productive-recovery authority can be created.

### B3 — CLOSED

`WorkerFailureEvidence` now shares a closed terminal-status vocabulary with the classifier and validates class/status/delta compatibility both on direct construction and `from_dict()` restoration.

In particular:

```text
CLEAN_NO_WORKTREE_DELTA + TIMED_OUT -> REJECT
CLEAN_NO_WORKTREE_DELTA + unsupported terminal token -> REJECT
```

The other semantic invariants remain explicit:

```text
CLEAN_TIMEOUT -> TIMED_OUT + zero delta
DIRTY_TIMEOUT_RECOVERY_REQUIRED -> TIMED_OUT + non-zero delta
PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE -> EXITED_NONZERO + non-zero delta
```

The existing exact field-set, primitive-type, no-coercion, deterministic human-guidance, SHA and dirty-path validation remains intact, and WorkerFlow continues to parse persisted evidence through the contract before surfacing machine next-action output.

### B1 / B4 — REMAIN CLOSED

Round 3 does not regress the previously accepted fail-closed classifier predicates or the integration proofs for clean timeout, dirty timeout, structured WorkerFlow delivery, TASK-092 clean-noop compatibility, provider-neutral policy parity, and Review-First candidate-stage T2=0 behavior.

## Delta / Impact Audit

The Round-3 implementation delta changes only:

```text
bridge.py
src/aios_bridge/worker_failure.py
tests/aios_bridge/test_worker_failure.py
tests/test_bridge_executor_automation.py
```

The publication boundary separately refreshes `.ai/results/RESULT-087.md`. No previously accepted worker CLI wiring or broader authority surface was modified in this FIX.

The latest RESULT reports:

```text
TARGETED_TEST_STATUS: PASS
SLICE_C_IMPACT_CONFIDENCE: KNOWN
PROTECTED_ACCEPTED_PATHS_UNCHANGED: YES
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
SEMANTIC_REVIEW_REQUIRED: YES
```

Current main remains exactly `ac0ae79e85e30a80410380188578db1993720b5b`; candidate is three commits ahead and zero behind, with merge base equal to that same main SHA.

## Accepted / Protected Surfaces

```text
A1 Four closed worker failure classes and one deterministic machine next action per class.
A2 Known-stopped / terminal evidence is required; unsupported status evidence fails closed.
A3 Productive nonzero authority requires strict existing branch/head/scope/publication-trust/authorization gates.
A4 Valid productive nonzero blocks into RECOVERY_REQUIRED with preserved delta and no publication.
A5 Clean timeout remains Human-decision-required and cannot create retry/reroute authority.
A6 Dirty timeout remains RECOVERY_REQUIRED with worktree preserved.
A7 Persisted WorkerFailureEvidence is strict, non-coercive and class/status/delta consistent.
A8 WorkerFlow/control surface derives machine output only from validated structured evidence.
A9 Codex and Antigravity share the same provider-neutral classification policy.
A10 TASK-092 clean-noop replacement compatibility remains intact.
A11 Review-First candidate publication remains T2=0.
A12 Certification remains exact-candidate, exactly-once and no-model-polling.
A13 Roadmap v1.2, lease, allowed-path, publication trust, reviewed-head and merge safety remain unchanged.
A14 P1 formal completion is not implied by TASK-087 semantic acceptance; P2/P3 and H5-H8 remain unauthorized.
```

## Semantic Decision

```text
TASK-087: SEMANTICALLY_ACCEPTED_PENDING_T2
SEMANTIC_BLOCKERS: 0
APPROVED: YES
FINAL_PASS: NO
MERGE_AUTHORIZED: NO
NEXT: bridge.py certify-reviewed 87
P1_FORMAL_COMPLETION: NO
```

Semantic acceptance is bound to exact candidate `12904cf867fe5c5fe5be901d94ece82e3523beca` and base main `ac0ae79e85e30a80410380188578db1993720b5b`. Any candidate-head or base-main drift supersedes this acceptance. Final PASS may be derived only after the certification-owned full canonical T2 passes exactly once on this exact candidate.

Operational executor preference after this review round: prioritize Codex for subsequent model-executed work; deterministic certification itself remains machine-owned and does not consume an executor model turn.