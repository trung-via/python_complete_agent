# REVIEW-029 — TASK-029 Open Multi-Agent Continuity OS M5 Executor Lease Enforcement

STATUS: APPROVED

## Review Scope
- Review round: `6` — ADR-013 Delta Fix Review + ADR-017 Final Independent Audit
- Reviewed branch: `ai/task-029`
- Reviewed branch head: `f36432c953fd84b8a38288f3d8580d2057a15cfc`
- Tested implementation SHA reported by RESULT: `95b9aa70b2f5049b2b4f6026b0c4a272e6162af7`
- Previous tested implementation: `bb84e0facb6b24d4c5fdd0eb636b45b9d89ab0b5`
- Previous REVIEW blob: `059e2d540b89493045947f4a9efb3a26fe098478`
- Base/current main: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Branch relation: ahead `12`, behind `0`; merge-base exact current main.
- `95b9aa7... -> f36432c...` changes only `.ai/results/RESULT-029.md`; production/test code at reviewed branch head equals the tested implementation.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: PASS after remediation
KNOWN_FINDINGS: CLOSED
DELTA_FIX_REVIEW: PASS
FINAL_INDEPENDENT_AUDIT: PASS
APPROVED: YES
```

## Round-6 Delta Result

### R5-1 — ACTIVE authorization reconstruction fail-closed binding
Status: CLOSED

Round 6 introduces one strict helper:

```python
reconstruct_expected_executor_lease(auth)
```

The helper requires all M5 authorization-to-lease binding fields without fallback/default inference:

```text
task_id
action
executor_id
lease_id
lease_fingerprint
workspace_id
execution_fingerprint
```

It then:
1. rejects missing, non-string, empty, or whitespace-only required fields;
2. canonicalizes/validates `action` through `ExecutionOperation`;
3. constructs canonical `ExecutorLease` with the exact authorization-provided `executor_id`;
4. verifies the reconstructed canonical lease fingerprint exactly equals authorization `lease_fingerprint`;
5. returns the exact expected lease only after all checks pass.

`cmd_publish()` now uses this helper before active-lease verification and before any test command, RESULT write, commit, or push. The prior `auth.get("executor_id", "antigravity")` fallback is removed.

Regression evidence adds:
- direct helper coverage for valid input, missing/None/empty required fields, invalid operation, malformed canonical fields and fingerprint mismatch;
- publish coverage proving an ACTIVE authorization missing `executor_id` fails before test execution while the exact active lease remains retained.

No new authority, alternate Executor, TTL, heartbeat, stealing, router, or M6 failover semantics were introduced.

---

## Known Finding Disposition

```text
R1-1  CLOSED — compare-and-release TOCTOU proof
R1-2  CLOSED — failed-writer cleanup ownership
R1-3  CLOSED — complete durable write/fsync
R1-4  CLOSED — legacy approve lease-conflict retryability
R1-5  CLOSED — formal M5 RESULT manifest/evidence
R2-1  CLOSED — cmd_approve post-acquire rollback/recovery state
R5-1  CLOSED — strict ACTIVE authorization -> lease reconstruction
```

---

## Final Independent Audit

A fresh final audit was performed against ADR-019 / TASK-029 and the final tested implementation rather than approving by incremental convergence.

### Canonical lease contract — PASS
- `MAX_ACTIVE_EXECUTORS_PER_TASK = 1` is explicit.
- `ExecutorLease` is frozen, strict-schema, bounded, canonical JSON/fingerprint capable and vendor-neutral.
- RUN/FIX reuse M4 `ExecutionOperation`; MERGE/unknown values are rejected.
- no approval, merge authority, TTL, heartbeat, failover target, secrets, raw local path or mutable metadata exist in the canonical lease.

### Runtime lease store — PASS
- active lease is outside the worktree.
- acquisition uses OS exclusive create (`O_CREAT | O_EXCL`).
- complete write loops until all bytes are written and fsync failure fails closed.
- corrupt/empty/oversized ACTIVE records are occupied/integrity failures, never treated as free.
- failed-writer cleanup is limited to the file created by that acquisition attempt.
- compare-and-release validates exact current lease while holding the task mutation guard and atomically moves ACTIVE to history.
- deterministic lock probes demonstrate the compare-to-rename critical section is protected without sleep as the correctness mechanism.
- stale Lease A cannot remove subsequently acquired Lease B.

### Bridge activation / authorization — PASS
- RUN handoff, FIX handoff and legacy approve all acquire lease before usable ACTIVE authorization.
- authorization stores exact non-secret lease binding fields.
- legacy approve conflict leaves the pending event retryable.
- post-acquire approve failures rollback exact ownership and use `RECOVERY_REQUIRED` whenever lease release or inbox restoration is unproven.
- Antigravity remains the sole activated runtime Executor.

### Publish stable-boundary gate — PASS
- ACTIVE authorization is mandatory.
- authorization-to-lease reconstruction is now strict and has no executor fallback inference.
- exact ACTIVE lease is required before test/workspace mutation.
- control-artifact drift remains fail-closed.
- test, commit and push failures retain lease ownership.
- exact lease is released only after successful remote push; authorization is then consumed and state transitions to IN_REVIEW.

### Human recovery — PASS
- lease status is diagnostic/read-only.
- recovery release requires exact lease ID and explicit `--confirm-stopped`.
- associated ACTIVE authorization is deactivated before exact release.
- no force release, lease stealing or replacement Executor selection exists.

### Scope / M6 leakage — PASS
- no Codex or Claude Code adapter/invocation.
- no executor-selection flag.
- no TTL/heartbeat/stale reclaim.
- no automatic failover or router/quota detection.
- M4 executor contract, canonical state, Brain/failover/provider semantics remain outside the M5 production change boundary.

No new blocking defect was identified in the final audited M5 boundary.

Non-blocking observations retained for later hardening only:
- handoff authorization-persistence rollback could expose richer diagnostics if exact rollback release itself fails;
- the Continuity package top-level docstring still names milestones only through M4.

---

## Test / Evidence Status

RESULT-029 reports against implementation `95b9aa70b2f5049b2b4f6026b0c4a272e6162af7`:

```text
Focused combined:      65 passed
Lease core:            13/13 passed
Runtime lease:         14/14 passed
Bridge:                38/38 passed
Continuity:           127/127 passed
Full repository:      712/712 passed
Regressions:            0
LIVE_EXTERNAL_CALLS:    0
PAID_EXTERNAL_API_CALLS: 0
EXECUTOR_RUNS:          1
EXECUTOR_FIX_RUNS:      5
```

These are Executor-reported test results in RESULT-029; ChatGPT did not independently execute pytest.

## Merge Eligibility

TASK-029 is semantically approved and merge-eligible at reviewed branch head:

```text
f36432c953fd84b8a38288f3d8580d2057a15cfc
```

Human MERGE authority remains mandatory and is not implied by this review.

## Decision

`APPROVED`
