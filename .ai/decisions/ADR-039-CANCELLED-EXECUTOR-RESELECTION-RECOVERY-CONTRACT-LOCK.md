# ADR-039 — Cancelled Executor Reselection Recovery Contract Lock

STATUS: LOCKED
CLASS: EXECUTOR RECOVERY / HUMAN RESELECTION / FAIL-CLOSED AUTHORITY
APPLIES_AFTER: TASK-048 PASS + MERGE
RELATED: ADR-019 / ADR-020 / ADR-023 / ADR-037 / ADR-038

## Context

A real operational incident exposed a gap between the existing M5 recovery path and M6 stable-boundary failover.

Current behavior is intentionally safe:

```text
ACTIVE executor attempt
    -> Human lease-release --confirm-stopped
    -> authorization becomes CANCELLED
    -> exact lease is released
```

ADR-019 requires this recovery release to deactivate the old authorization before the lease is freed.

ADR-020 separately defines stable-boundary Executor failover and explicitly requires the source authorization to be:

```text
status = CONSUMED
published_sha = exact source stable boundary
```

ADR-020 also explicitly states that a prior `ACTIVE`, `CANCELLED`, malformed, missing, or pre-M5 authorization is not sufficient evidence for M6 failover.

That rule remains correct and MUST NOT be weakened.

However, after a Human has explicitly cancelled an interrupted attempt, removed/abandoned all partial work, restored a clean task branch to the exact pre-attempt stable boundary, and confirmed that no active lease remains, the runtime currently has no legal way to let the Human select a different eligible Executor for a fresh FIX activation.

This ADR introduces that missing recovery transition without pretending that a CANCELLED attempt was successfully published.

---

## Decision 1 — New Transition Is Recovery Reselection, Not M6 Failover

The following transitions remain distinct:

```text
CONSUMED executor A -> executor B
    = ADR-020 M6 stable-boundary failover

CANCELLED executor A -> executor B
    = ADR-039 cancelled-activation recovery reselection

ACTIVE executor A -> executor B
    = FORBIDDEN

dirty/unpublished workspace A -> executor B
    = FORBIDDEN by this ADR
```

ADR-039 SHALL NOT rewrite `CANCELLED` to `CONSUMED`, SHALL NOT classify the recovery as `StableExecutorFailoverProof`, and SHALL NOT relax ADR-020's source-CON-SUMED requirement.

---

## Decision 2 — Scope Is FIX Recovery Only

ADR-039 v1 applies only to a cancelled `FIX` activation that had already been authorized from an exact authoritative `CHANGES_REQUIRED` review.

Required source operation:

```text
FIX
```

Required replacement operation:

```text
FIX
```

Cancelled RUN reselection is out of scope for v1 and remains fail-closed.

This narrow scope addresses the observed quota/crash/recovery case while minimizing authority expansion.

---

## Decision 3 — No Partial Work Transfer

Recovery reselection is allowed only after the interrupted Executor's work has been abandoned and removed from the repository worktree.

Required state before replacement authorization:

```text
worktree clean
index clean
no unpublished local commit from the cancelled attempt
no ACTIVE lease for TASK-N
current branch == exact ai/task-N
local task branch HEAD == exact stable predecessor SHA
remote task branch HEAD == exact stable predecessor SHA
```

A preserved forensic snapshot outside the Git worktree is allowed but is not implementation authority and MUST NOT be automatically imported, applied, cherry-picked, or reused.

If partial work must be transferred, ADR-023/M9 hot handoff is the relevant family; ADR-039 does not implement dirty handoff.

---

## Decision 4 — Stable Anchor Comes From Before the Cancelled Attempt

A cancelled FIX attempt has no successful publish boundary of its own.

Therefore ADR-039 SHALL anchor recovery to the exact stable predecessor that existed before the cancelled activation.

The cancelled authorization must retain a valid immutable predecessor anchor, expected as:

```text
prior_published_sha = lowercase 40-hex Git commit
```

or an equivalently strong existing field already persisted by Bridge for same-executor FIX lineage.

The recovery gate MUST verify:

```text
local ai/task-N HEAD
== remote ai/task-N HEAD
== cancelled_auth.prior_published_sha
```

The runtime MUST NOT derive a replacement anchor from dirty files, an unreviewed local commit, chat history, forensic backups, wall-clock time, or a Human-entered SHA.

---

## Decision 5 — Exact CANCELLED Authorization Is Required

Replacement reselection requires a prior same-task authorization record that is mechanically valid and exactly:

```text
status = CANCELLED
action = FIX
executor_id = source executor
```

The record must still contain the canonical M5 binding fields needed to prove which activation was cancelled, including at minimum:

```text
task_id
workspace_id
executor_id
lease_id
lease_fingerprint
execution_fingerprint
authorized artifact path/blob binding
cancellation metadata
stable predecessor anchor
```

Missing, malformed, ACTIVE, CONSUMED, unknown, pre-M5, cross-task, or cross-workspace records fail closed for this recovery path.

CONSUMED cross-executor transitions continue through ADR-020, not ADR-039.

---

## Decision 6 — Cancellation Must Be Human Recovery Cancellation

ADR-039 v1 accepts only a cancellation produced by the existing explicit M5 Human recovery path.

Required evidence includes the existing cancellation metadata written by `lease-release --confirm-stopped`, including:

```text
cancelled_at = present
cancellation_reason = bounded Human recovery release reason
lease_id in the cancellation evidence == cancelled authorization lease_id
```

The implementation MAY replace string parsing with a stricter bounded cancellation-reason enum/marker if this can be done without broad redesign, but it MUST NOT infer cancellation from process state, quota state, chat messages, or missing lease files alone.

---

## Decision 7 — No Active Lease Before Reselection

Before replacement lease acquisition:

```text
lease_store.load_active(TASK-N) is None
```

must be mechanically true.

Corruption, uncertainty, or an existing ACTIVE lease fails closed.

ADR-039 does not add force release, stale detection, TTL, heartbeat, PID probing, process termination, lease stealing, or automatic cleanup.

The existing Human `lease-release --confirm-stopped` recovery path remains authoritative for ending the source activation.

---

## Decision 8 — Exact Review Binding Must Still Be Authoritative

The replacement FIX must still be authorized by the current canonical `CHANGES_REQUIRED` review under existing Bridge control-plane rules.

For ADR-039 v1, the current review artifact MUST be the exact same review path and blob that authorized the cancelled FIX attempt.

This prevents a cancelled authorization from becoming a generic ticket for later or modified review instructions.

If ChatGPT updates the review blob after cancellation, ADR-039 v1 fails closed and a separately designed recovery path is required.

---

## Decision 9 — Human Must Explicitly Select the Replacement Executor

Recovery reselection is a fresh Human authorization boundary.

The selected replacement Executor must:

- differ from the cancelled source Executor;
- be explicitly selected through the appropriate Human UI/adapter;
- be eligible exactly once in the current review's `DISPATCH_EXECUTOR_POLICY_JSON` for FIX;
- satisfy existing required capabilities;
- never be inferred from quota, availability, ranking, model output, or previous conversation state.

No automatic retry or reroute is introduced.

---

## Decision 10 — Canonical Recovery Proof

Introduce a narrow immutable vendor-neutral record, expected at:

```text
src/aios_bridge/continuity/cancelled_reselection.py
```

with semantics equivalent to:

```python
@dataclass(frozen=True)
class CancelledExecutorReselectionProof:
    schema_version: str
    task_id: str
    target_branch: str

    cancelled_executor_id: str
    cancelled_operation: ExecutionOperation
    cancelled_execution_fingerprint: str
    cancelled_lease_fingerprint: str
    cancelled_lease_id: str

    stable_predecessor_sha: str
    review_ref: ArtifactRef

    replacement_executor_id: str
    replacement_operation: ExecutionOperation
    replacement_execution_fingerprint: str
    replacement_lease_fingerprint: str
```

Exact field names may vary slightly, but the semantics must remain equivalent.

The proof records a verified recovery transition. It grants no authority by itself.

---

## Decision 11 — Recovery Proof Validation

A pure validator SHALL bind the proof to the cancelled source lease identity and newly acquired replacement lease identity.

It must enforce at minimum:

- exact same task/workspace lineage;
- cancelled executor != replacement executor;
- cancelled operation exactly FIX;
- replacement operation exactly FIX;
- exact source/replacement execution fingerprints;
- exact source/replacement lease fingerprints;
- exact stable predecessor 40-hex SHA;
- exact `ai/task-N` target branch;
- exact authoritative `.ai/reviews/REVIEW-N.md` ArtifactRef;
- no unknown fields;
- deterministic canonical JSON/fingerprint;
- no secrets, transcripts, raw paths, quota values, process IDs or hidden reasoning.

The validator performs no filesystem, Git, network, process, provider, or model I/O.

---

## Decision 12 — Replacement Activation Ordering

The recovery activation ordering is locked as:

```text
validate current REVIEW == CHANGES_REQUIRED
-> prepare/reconcile exact task branch
-> load and validate prior CANCELLED FIX authorization
-> validate Human-recovery cancellation evidence
-> validate exact stable predecessor anchor
-> require clean worktree/index
-> require local/remote task branch == stable predecessor
-> require no ACTIVE lease
-> validate explicit replacement executor eligibility
-> build replacement lease
-> atomically acquire replacement lease
-> build + validate CancelledExecutorReselectionProof
-> persist replacement ACTIVE authorization + bounded recovery proof metadata
-> expose execution context / launch selected executor according to existing adapter rules
```

If any post-acquire persistence step fails, rollback may release only the exact newly acquired replacement lease.

The cancelled source lease is already released and MUST NOT be recreated or touched.

---

## Decision 13 — Publish Revalidates Recovery Evidence

For an ACTIVE authorization containing cancelled-reselection proof metadata, `cmd_publish()` SHALL fail closed before tests/RESULT mutation/commit/push unless it can revalidate:

- exact current replacement lease;
- exact proof fingerprint;
- exact cancelled source binding;
- exact stable predecessor SHA;
- exact authoritative review binding;
- exact task/executor/operation relations.

A malformed or stale recovery proof cannot fall back to ordinary FIX semantics.

---

## Decision 14 — RESULT Carries Bounded Recovery Manifest

A successful publish under ADR-039 SHALL record bounded non-secret evidence equivalent to:

```text
EXECUTOR_FAILOVER: NO
CANCELLED_RESELECTION: YES
RESELECTION_FROM_EXECUTOR: <source>
RESELECTION_TO_EXECUTOR: <replacement>
RESELECTION_STABLE_PREDECESSOR_SHA: <40hex>
RESELECTION_PROOF_FINGERPRINT: <64hex>
RESELECTION_REVIEW_BLOB_SHA: <40hex>
```

This must not be mislabeled as M6 stable failover.

Ordinary same-executor FIX and M6 failover retain their existing manifests.

---

## Decision 15 — Forbidden Behavior

ADR-039 MUST NOT:

- mutate CANCELLED -> CONSUMED;
- reuse or resurrect the cancelled lease;
- trust a missing lease as sufficient proof by itself;
- transfer dirty/uncommitted work;
- auto-stash, auto-restore, auto-cherry-pick, auto-reset, or auto-apply forensic diffs;
- infer that an Executor stopped from quota/error text;
- probe/kill processes;
- auto-select a replacement Executor;
- retry under another Executor automatically;
- allow two active leases;
- weaken ADR-020 stable failover;
- activate M9 hot handoff;
- modify M11 paid-API authority;
- auto-merge.

---

## Decision 16 — Relationship to ADR-020

ADR-039 narrowly extends recovery behavior without superseding the M6 stable-boundary definition.

The classification rule is:

```text
prior auth CONSUMED + different executor
    -> ADR-020 stable failover path

prior auth CANCELLED + different executor
    -> ADR-039 recovery reselection path, only if all ADR-039 gates pass

prior auth ACTIVE + different executor
    -> reject

any other prior auth state
    -> reject unless an existing same-executor rule already applies
```

`StableExecutorFailoverProof` and `CancelledExecutorReselectionProof` are distinct proof types and MUST NOT be substituted for one another.

---

## Decision 17 — Relationship to ADR-038 Human Choice

ADR-038 remains authoritative that eligible does not mean selected and Human selection does not mean automatic dispatch.

ADR-039 merely restores Human choice after an explicitly cancelled FIX attempt reaches a clean, lease-free, exact predecessor boundary.

The selected replacement must still be eligible under the canonical REVIEW policy.

---

## Decision 18 — Parallel Implementation / Merge Ordering

TASK-061 may be implemented in a separate Git worktree while TASK-060 remains unresolved because its writable implementation paths do not overlap TASK-060 operator-surface files.

However, TASK-061 MUST NOT be merged ahead of TASK-060.

Locked merge ordering:

```text
TASK-060 PASS + Human merge first
-> rebase/reconcile TASK-061 onto the new main without force-push
-> rerun focused + full tests
-> fresh independent Review TASK-061 on the rebased exact head
-> Human merge TASK-061 only after fresh PASS
```

A pre-rebase PASS is implementation evidence only and does not authorize post-TASK-060 merge.

---

## Decision 19 — M11 / TASK-059 Boundary

TASK-061 is a supporting Executor-control hardening task and does not change M11 paid-API semantics.

TASK-059 remains blocked by TASK-060 as already locked.

TASK-061 MUST NOT modify:

```text
TASK-059 artifacts
M11.3B proof-lock/preflight implementation
paid API grant contracts/store
MiniMax provider/counter/proof code
operator UI surface files
```

After TASK-060 and TASK-061 are merged, TASK-059 must be reconciled/reissued against the then-current main before execution because its original baseline predates both supporting hardening changes.

---

## Acceptance Criteria

ADR-039 is implemented only when all are proven:

1. existing ADR-020 CONSUMED failover behavior remains unchanged;
2. CANCELLED is never reclassified as CONSUMED;
3. ACTIVE cross-executor switch remains forbidden;
4. only cancelled FIX recovery is accepted in v1;
5. cancellation must originate from explicit Human recovery release evidence;
6. no ACTIVE lease exists before replacement acquisition;
7. worktree/index are clean;
8. local and remote task branch both equal exact stable predecessor SHA;
9. current review path/blob exactly matches the cancelled FIX review authorization;
10. replacement executor is explicitly Human-selected and review-eligible;
11. replacement lease is newly acquired and source lease is never reused;
12. canonical recovery proof is deterministic and strictly validated;
13. publish revalidates recovery proof before tests/mutation;
14. RESULT distinguishes `CANCELLED_RESELECTION: YES` from M6 failover;
15. no dirty-worktree transfer, process probing, auto-reroute, auto-retry or auto-merge is introduced;
16. full repository tests pass.
