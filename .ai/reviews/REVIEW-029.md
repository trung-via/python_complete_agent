# REVIEW-029 — TASK-029 Open Multi-Agent Continuity OS M5 Executor Lease Enforcement

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `5` — ADR-013 Delta Fix Review + ADR-017 Final Independent Audit
- Reviewed branch: `ai/task-029`
- Reviewed branch head: `43c675d93ebe37e41ad1200bf7d7daeabe729a99`
- Tested implementation SHA reported by RESULT: `bb84e0facb6b24d4c5fdd0eb636b45b9d89ab0b5`
- Previous tested implementation: `2be2b37f051917583b122215e0fa7654e377dc3e`
- Previous REVIEW blob: `1b975d9972fee5a929de6374f7aee9740b47ba09`
- Base/current main: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Branch relation: ahead `10`, behind `0`; merge-base exact current main.
- `bb84e0f... -> 43c675d...` changes only `.ai/results/RESULT-029.md`; production/test code at reviewed branch head equals the tested implementation.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: FAIL in Round 1
KNOWN_FINDINGS: OPEN (new Final Independent Audit finding R5-1)
DELTA_FIX_REVIEW: PASS for Round-4 findings
FINAL_INDEPENDENT_AUDIT: FAIL
APPROVED: NO
```

## Round-5 Delta Result

The two findings carried from Round 4 are closed.

### R1-1 — Compare-and-release TOCTOU proof
Status: CLOSED

The release test seam remains exactly between `require_active(expected)` and `os.replace()`. Round 5 removes the prior sleep-based correctness inference and directly probes both protection layers while the releaser is paused:

- a separate probe thread cannot non-blockingly acquire the task `RLock`;
- a separate file descriptor cannot non-blockingly acquire the OS `.lease_mutation.lock`;
- after the protected release linearizes, Lease B can acquire;
- a stale Lease-A release then fails closed and cannot remove Lease B.

The remaining immediate `contender_finished` assertion is supplementary; the lock-ownership proof no longer depends on scheduler delay or sleep.

### R2-1 — `cmd_approve()` post-acquire rollback state
Status: CLOSED

Rollback now treats ordinary retryability as proven only when BOTH exact lease release and inbox restoration succeed:

```text
lease_released && inbox_restored -> PENDING_APPROVAL
otherwise                         -> RECOVERY_REQUIRED
```

A dedicated fault test injects rollback `store.release()` failure and verifies bounded diagnostics include `lease_release_failed` and state update reports `RECOVERY_REQUIRED`.

### R1-5 — Required M5 RESULT manifest
Status: CLOSED

The formal manifest remains complete and is correctly rebound to the Round-4 REVIEW blob.

---

## Final Independent Audit

A fresh audit was performed from ADR-019 / TASK-029 architecture and acceptance criteria through the final tested implementation, rather than only checking prior findings.

Most M5 boundaries pass: canonical lease strictness, atomic create-if-absent, compare-and-release, RUN/FIX/legacy activation gating, publish-before-test lease validation, test/push retention behavior, successful-publish release ordering, manual recovery, current Antigravity-only executor scope, no TTL/steal/failover/router leakage, and expected file-boundary scope.

The independent audit found one new blocking contract defect.

### R5-1 — ACTIVE authorization reconstruction is not fully fail-closed
Severity: HIGH
Status: OPEN

TASK-029 AIP-7 explicitly requires strict authorization-to-lease reconstruction:

```text
Add one Bridge helper to reconstruct the expected ExecutorLease from authorization binding fields.
Missing/malformed new lease fields in an ACTIVE M5 authorization fail closed.
```

ADR-019 Decision 11 also defines `executor_id` as part of the lease binding metadata that ACTIVE authorization SHALL persist, and Decision 13 requires publish to match the exact ACTIVE lease against the authorization binding.

Current `cmd_publish()` validates only:

```python
["lease_id", "lease_fingerprint", "workspace_id", "execution_fingerprint"]
```

and then reconstructs with:

```python
executor_id=auth.get("executor_id", "antigravity")
```

This means an otherwise M5-shaped ACTIVE authorization with the `executor_id` binding missing does **not** fail closed. Instead, Bridge invents the current executor identity and may accept the authorization if the active lease is also `antigravity`.

That is weaker than exact authorization/lease binding and directly violates the AIP-7 rule that missing M5 lease fields fail closed. It also bypasses the intended architecture of one strict authorization-to-lease reconstruction helper.

#### Required remediation
Keep the fix narrow:

1. introduce one strict helper equivalent to `expected_lease_from_authorization(auth)` / `reconstruct_expected_executor_lease(auth)`;
2. require all binding fields without defaults, including at minimum:

```text
task_id
action
executor_id
lease_id
lease_fingerprint
workspace_id
execution_fingerprint
```

3. validate/canonicalize through `ExecutorLease` + `ExecutionOperation`; do not infer `executor_id="antigravity"` when missing;
4. verify the reconstructed canonical lease fingerprint equals `lease_fingerprint`;
5. use that helper in `cmd_publish()`; use it at any authorization-to-lease recovery/status boundary where AIP-7 applies rather than duplicating weaker reconstruction semantics;
6. add a regression test: remove `executor_id` from an otherwise valid ACTIVE M5 authorization while the matching Antigravity lease exists, then assert publish fails **before test/RESULT/commit/push** and the lease remains ACTIVE;
7. add malformed `executor_id` coverage if not naturally covered by the same helper test.

Do not broaden into M6, alternate Executor activation, TTL, heartbeat, stealing, dispatch or router behavior.

---

## Final Audit Notes

No other new blocking defect was identified in the audited M5 boundary.

The following observations are non-blocking for TASK-029:
- handoff authorization-persistence rollback remains fail-closed if exact lease release itself errors, although diagnostics could be improved in a later hardening task;
- Continuity package docstring still names milestones only through M4; this is documentation staleness, not an M5 authority defect.

## Test / Evidence Status

RESULT-029 reports against implementation `bb84e0facb6b24d4c5fdd0eb636b45b9d89ab0b5`:

```text
Focused combined:      63 passed
Lease core:            13/13 passed
Runtime lease:         14/14 passed
Bridge:                36/36 passed
Continuity:           127/127 passed
Full repository:      710/710 passed
Regressions:            0
LIVE_EXTERNAL_CALLS:    0
PAID_EXTERNAL_API_CALLS: 0
EXECUTOR_RUNS:          1
EXECUTOR_FIX_RUNS:      4
```

The suites are green, but R5-1 is a semantic fail-closed gap not covered by those tests.

## Required FIX Scope

Round 6 should be very small:

```text
bridge.py
 tests/test_bridge.py
 .ai/results/RESULT-029.md
```

`runtime_lease.py`, `continuity/lease.py`, M4 `executor.py`, canonical state, Brain/failover/provider semantics should not need changes.

## Decision

`CHANGES_REQUIRED`
