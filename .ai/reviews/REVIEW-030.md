# REVIEW-030 — TASK-030 M6 Stable-Boundary Executor Failover

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 7 — Controlled Real Proof B review + Final Independent Audit
- Proof-B source boundary: `4b9827b85955dcde14d852bfbeb7aaadaf66ddef`
- Proof-B published head: `acf0205728756f6ff8b1134bcdbfdccf25e92820`
- Base main: `f36432c953fd84b8a38288f3d8580d2057a15cfc`
- Branch: ahead 9 / behind 0; exact merge-base main.

```text
FULL_SEMANTIC_REVIEW: PASS AFTER REMEDIATION
KNOWN_PREVIOUS_FINDINGS: CLOSED
DELTA_FIX_REVIEW: PASS
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PASS
FINAL_INDEPENDENT_AUDIT: FAIL
APPROVED: NO
```

## Proof B Decision

Proof B is accepted.

The Proof-B commit is the direct child of the exact Codex source boundary and changes only `.ai/results/RESULT-030.md`; no production or test code changed in the reverse proof round.

Bridge-generated RESULT binds:

```text
EXECUTOR_ID: antigravity
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: codex
FAILOVER_TO_EXECUTOR: antigravity
FAILOVER_SOURCE_PUBLISHED_SHA: 4b9827b85955dcde14d852bfbeb7aaadaf66ddef
FAILOVER_REVIEW_BLOB_SHA: f93e416f3ad93759d51ef471b6c2da95e9847bb2
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PASS
```

Focused Bridge + executor-failover tests report `75 passed, 0 failed`. The semantically identical production/test code at `9e07edc16690e2549a377e596c05089b3331fd97` previously ran the full repository suite with `749 passed, 0 failed`; the two later proof commits changed only RESULT evidence.

## Final Independent Audit Finding

### R7-1 HIGH — Stable-boundary precondition does not explicitly assert current task branch before replacement lease acquisition

TASK-030 C13 requires all three final stable-boundary assertions before replacement acquisition:

```text
current_branch == expected task branch
git HEAD == prior_auth.published_sha
remote task branch == prior_auth.published_sha
```

and explicitly says existing branch reconciliation does not remove the need to assert the final boundary.

Current `_validate_stable_failover_preconditions()` validates the latter two conditions, but it never checks `current_branch() == branch` inside the final failover gate. It proceeds from source-auth reconstruction directly to `git rev-parse HEAD`, then remote-task-ref equality.

A different local branch can point at the same source commit. In that state HEAD and remote task SHA checks can both pass while the workspace is not actually on the authorized task branch. Bridge could then acquire the replacement lease and expose execution authority on the wrong branch; `cmd_publish()` would reject later, but that is after the Executor may already have mutated the workspace. For an L3 authority-safety contract, publish-time detection is too late.

Required remediation is intentionally narrow:

1. In `_validate_stable_failover_preconditions()`, before the HEAD equality check, resolve `current_branch()` and fail closed unless it equals the exact `branch` argument.
2. The assertion must occur before `store.acquire()` can be reached through either `cmd_handoff()` or legacy `cmd_approve()`.
3. Add a deterministic regression where another branch points to the same exact source published SHA; failover activation must reject and no replacement lease may be acquired.
4. Because handoff and approve share the helper, one helper-level/integration proof may cover both only if it mechanically demonstrates the shared pre-acquire gate; otherwise cover both activation paths.
5. Do not modify M5 lease semantics, proof schema, proof-progress logic, or real-proof evidence.

## Final Audit Areas That Passed

- canonical `StableExecutorFailoverProof` remains immutable, strict, bounded, role-specific and vendor-neutral;
- pure relational validation binds task/executor/operation/execution and lease fingerprints plus same workspace;
- runtime executor set remains exactly `antigravity,codex` with no router or third executor;
- prior FIX authorization classification is fail-closed and strict;
- source RESULT and REVIEW are content-addressed at immutable Git anchors;
- no ACTIVE lease is allowed before replacement acquisition;
- cross-executor activation rollback restores prior control state and releases only the exact replacement lease;
- legacy approve uses the same failover precondition gate;
- publish requires exact replacement lease and revalidates strict failover proof + current immutable REVIEW before tests;
- successful publish retains M5 ordering: push -> exact lease release -> auth CONSUMED + published SHA -> IN_REVIEW;
- proof progress uses exact predecessor anchors rather than arbitrary history;
- Stage A and Stage B real repository proofs are both accepted;
- no runtime_lease/executor/state/Brain/provider semantics were widened;
- no hot handoff, TTL/heartbeat/steal, quota routing, auto failover, paid API path, or merge authority widening was introduced.

## Next Step

Run one ordinary same-executor Antigravity FIX. This is a semantic repair after both proofs are already complete; it is not another failover proof.

Expected command:

```text
/aios-worker FIX TASK-030 --executor antigravity
```

The resulting RESULT must preserve:

```text
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PASS
```

Run focused Bridge/failover tests and a fresh full repository suite. After publish, return with `Review TASK-030`; Primary Brain will delta-review R7-1 and rerun the Final Independent Audit before APPROVED.

## Decision

`CHANGES_REQUIRED`
