# REVIEW-029 — TASK-029 Open Multi-Agent Continuity OS M5 Executor Lease Enforcement

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `4` — ADR-013 Delta Fix Review
- Reviewed branch: `ai/task-029`
- Reviewed branch head: `f98db24ff94c49417f7cb6185d60c71a60f4c2df`
- Tested implementation SHA reported by RESULT: `2be2b37f051917583b122215e0fa7654e377dc3e`
- Previous tested implementation: `3603828f847c32bdad8e68dafb250b8865947f28`
- Previous REVIEW blob: `c43506ee4abf2eca5ccb08672034c3af90083bb7`
- Base/current main: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Branch relation: ahead `8`, behind `0`; merge-base exact current main.
- `2be2b37... -> f98db24...` changes only `.ai/results/RESULT-029.md`; production/test code at reviewed branch head equals the tested implementation.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: FAIL in Round 1
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: FAIL
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Delta Summary

Round 4 closes the formal RESULT-manifest finding and materially improves rollback evidence. The release implementation now exposes a test seam exactly inside the compare-to-rename critical section, and `cmd_approve()` now records rollback outcomes instead of silently swallowing all failures.

Two acceptance gaps remain: the new compare-and-release test still uses a sleep/timing assumption to infer that the contender is blocked, contrary to the explicit deterministic-proof requirement; and rollback state classification does not enter `RECOVERY_REQUIRED` when exact lease release fails but inbox restoration succeeds, even though ownership remains unresolved.

---

## Finding Disposition

### R1-1 — Compare-and-release TOCTOU proof
Status: PARTIALLY CLOSED / OPEN
Severity: HIGH

Implementation-side remediation is now strong. `release()` holds the task mutation guard across:

```text
require_active(expected)
→ optional test seam
→ os.replace(ACTIVE, history)
```

and the new test seam `_test_pre_replace_hook` is located in the correct dangerous window.

However, `test_deterministic_compare_and_release_toctou_interleaving_proof` still establishes contender blocking with:

```python
contender_blocked.wait(...)
time.sleep(0.05)
assert not contender_finished.is_set()
```

The `contender_blocked` event is set immediately before `store2.acquire(lease_b)`; it does not prove that the contender has actually attempted and blocked on the task mutation guard. The subsequent sleep is therefore the correctness mechanism used to infer scheduler progress. Round 3 explicitly required a deterministic proof with **no sleep-based timing assumption**.

The separate cross-process test still proves acquisition exclusion while an ACTIVE lease exists, not the compare-to-rename release critical section.

Required remediation:
1. retain the pre-replace seam if useful;
2. replace the sleep-based assertion with a deterministic lock-attempt proof, e.g. an instrumented guard/lock attempt event or a non-blocking probe against the exact held task/OS lock;
3. prove that while Releaser A is paused after `require_active()` and before `os.replace()`, the competing mutation cannot enter the protected critical section;
4. after A linearizes, B may acquire and stale A release must fail without removing B;
5. no sleep or scheduler-delay assumption may be necessary for correctness.

Until that proof exists, `COMPARE_AND_RELEASE: PASS` is not yet accepted as M5 acceptance evidence.

### R1-2 — Failed-writer cleanup ownership
Status: CLOSED

No regression identified.

### R1-3 — Complete durable write
Status: CLOSED

No regression identified.

### R1-4 — Legacy approve lease-conflict retryability
Status: CLOSED

No regression identified.

### R1-5 — Required M5 evidence / formal RESULT manifest
Status: CLOSED

Round 4 RESULT now contains the exact minimum TASK-029 schema, including:

```text
M5_EXECUTOR_LEASE
FOCUSED_LEASE_TESTS
RUNTIME_LEASE_TESTS
BRIDGE_TESTS
CONTINUITY_TESTS
FULL_REPO_TESTS
```

and correctly binds:

```text
PREVIOUS_REVIEW_SHA: c43506ee4abf2eca5ccb08672034c3af90083bb7
```

The reported test counts are internally consistent with the focused suite (`13 + 14 + 35 = 62`).

### R2-1 — `cmd_approve()` post-acquire rollback
Status: PARTIALLY CLOSED / OPEN
Severity: MEDIUM

The previous gaps are mostly closed:
- real inbox `save_json()` failure is now injected separately;
- state-update and authorization-save failures have separate tests;
- rollback failures are reported through explicit diagnostics;
- inbox-restore failure produces `RECOVERY_REQUIRED` rather than claiming a successful restore.

One ownership-recovery gap remains. State selection currently uses only `inbox_restored`:

```python
state_label = "PENDING_APPROVAL" if inbox_restored else "RECOVERY_REQUIRED"
```

If `store.release(acquired_lease)` fails but inbox restoration succeeds, the runtime can still have an unresolved ACTIVE lease while operational state is set to `PENDING_APPROVAL`. Execution remains fail-closed because usable authorization is absent/invalid, but the state incorrectly implies ordinary retryability rather than unresolved ownership recovery.

Required remediation:
- explicitly track `lease_released` as well as `inbox_restored`;
- use `PENDING_APPROVAL` only when both exact lease release and inbox restoration are proven successful;
- otherwise use `RECOVERY_REQUIRED` (or the existing equivalent non-executable recovery state) and preserve bounded diagnostics;
- add a fault-injection test where activation fails and the exact rollback `store.release()` also fails, proving the task remains non-executable and is marked/reported as recovery-required.

Do not broaden this into TTL, stale reclaim, lease stealing or M6 failover.

---

## Test / Evidence Status

RESULT-029 reports against implementation `2be2b37f051917583b122215e0fa7654e377dc3e`:

```text
Focused combined:      62 passed
Lease core:            13/13 passed
Runtime lease:         14/14 passed
Bridge:                35/35 passed
Continuity:           127/127 passed
Full repository:      709/709 passed
Regressions:            0
LIVE_EXTERNAL_CALLS:    0
PAID_EXTERNAL_API_CALLS: 0
EXECUTOR_RUNS:          1
EXECUTOR_FIX_RUNS:      3
```

The suites are green; remaining blockers are deterministic proof quality and rollback-state correctness.

## Required FIX Scope

Keep Round 5 narrow:

```text
src/aios_bridge/runtime_lease.py        # only if needed for deterministic lock proof/test seam
tests/aios_bridge/test_runtime_lease.py
bridge.py                               # lease_released-aware recovery state only
tests/test_bridge.py
.ai/results/RESULT-029.md
```

Do not modify `continuity/lease.py`, M4 `executor.py`, canonical state, Brain/failover/provider semantics. Do not add TTL, heartbeat, stealing, alternate Executor activation, routing or M6 failover.

## Final Independent Audit

`NOT_RUN`.

Known findings remain open. ADR-017 Final Independent Audit must wait until R1-1 and R2-1 are fully closed.

## Decision

`CHANGES_REQUIRED`
