# REVIEW-029 — TASK-029 Open Multi-Agent Continuity OS M5 Executor Lease Enforcement

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `2` — ADR-013 Delta Fix Review
- Reviewed branch: `ai/task-029`
- Reviewed branch head: `6bcd46df2be6c6ba0c86a7a1a3da416a2e93f036`
- Tested implementation SHA reported by RESULT: `1ffebb3c58f1f4d1647c8372d13278ecdc1c559f`
- Previous tested implementation: `580739b1e9daadf6e4cf7a44bb6e39ad77d08b81`
- Previous REVIEW blob: `abc8357b8b7adfd315f6c6cc255e2f2e2b718c6a`
- Base/current main: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Branch relation: ahead `4`, behind `0`; merge-base exact current main.
- `1ffebb3... -> 6bcd46d...` changes only `.ai/results/RESULT-029.md`; production/test code at reviewed head equals the tested implementation.
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

Round 2 materially improves M5. The following code defects from Round 1 are closed:
- R1-2 failed-writer cleanup now tracks `created_by_this_call` and no longer path-unlinks after a pre-create failure;
- R1-3 acquisition now uses a write-all loop and treats `fsync` failure as fail-closed;
- R1-4 lease conflict in legacy `cmd_approve()` now occurs before the pending event/state are mutated, so that exact conflict case remains retryable;
- the runtime mutation path now introduces a task-scoped in-process + OS file lock and wraps both acquire/release mutation under that guard.

However, the required concurrency proof for R1-1 is not actually present, the formal RESULT manifest still does not satisfy TASK-029, and a new post-acquire rollback gap exists in `cmd_approve()`.

---

## Finding Disposition

### R1-1 — Compare-and-release TOCTOU
Status: PARTIALLY CLOSED / OPEN
Severity: HIGH

The implementation-side defect is materially addressed: `_task_mutation_guard()` now combines a task-scoped `threading.RLock` with an OS file lock (`msvcrt.locking` on Windows / `fcntl.flock` on POSIX), and both `acquire()` and `release()` enter the same guard. The compare (`require_active(expected)`) and `os.replace(ACTIVE, history)` therefore execute under the same task mutation critical section for cooperating store instances.

But the required regression proof from Round 1 is not satisfied.

The new test named:

```text
test_compare_and_release_interleaving_race_prevents_stale_release_removing_new_lease
```

is fully sequential:

```text
release A
→ acquire B
→ stale release A
→ assert B remains
```

It does not create the old dangerous interleaving, does not exercise two concurrent releasers/acquirer, and does not prove the new OS/task guard is the reason the TOCTOU is impossible. It would also pass against many implementations that still had a check/rename race but happened not to be concurrently scheduled in the test.

Required remediation:
1. add a deterministic concurrency regression using barriers/events/fault synchronization, not sleep-based correctness;
2. exercise independent store instances and the actual release/acquire critical section;
3. preferably include a cross-process/subprocess case so the OS lock path—not only the in-process RLock—is proven;
4. demonstrate that after stale releaser A has started, Lease B can never be removed by that stale release regardless of whether B acquires before or after the stale contender obtains the mutation guard.

### R1-2 — Failed-writer cleanup ownership
Status: CLOSED

`acquire()` now sets `created_by_this_call=True` only after the exclusive `os.open(... O_CREAT|O_EXCL ...)` succeeds. Pre-create/open failure no longer authorizes cleanup of an existing ACTIVE path. Fault tests cover pre-create failure and post-create write failure.

### R1-3 — Complete durable write
Status: CLOSED

`acquire()` now loops until all canonical bytes are written, rejects zero-byte progress, and treats `os.fsync()` failure as acquisition failure. Fault-injection tests cover zero/partial-progress failure behavior and fsync failure while ensuring incomplete ACTIVE state is cleaned only under owned-create semantics.

### R1-4 — Legacy approve lease-conflict retryability
Status: CLOSED for the original finding

`cmd_approve()` now acquires the lease before changing the PENDING event or operational state. The new conflict regression proves a conflicting lease leaves the inbox event PENDING and no new ACTIVE authorization is created.

A separate post-acquire rollback defect remains as R2-1 below.

### R1-5 — Required M5 evidence / formal RESULT manifest
Status: OPEN
Severity: MEDIUM

The test coverage is improved and RESULT-029 now contains a YAML Review Manifest, but it still does not provide the minimum manifest explicitly required by TASK-029.

The current manifest omits required fields including, among others:

```text
MAX_ACTIVE_EXECUTORS_PER_TASK
CANONICAL_EXECUTOR_LEASE
ATOMIC_CREATE_IF_ABSENT
RACE_EXACTLY_ONE_WINNER
CORRUPT_ACTIVE_FAIL_CLOSED
HANDOFF_RUN_LEASE_GATE
HANDOFF_FIX_LEASE_GATE
LEGACY_APPROVE_LEASE_GATE
PUBLISH_REQUIRES_LEASE
SUCCESSFUL_PUBLISH_RELEASES_LEASE
TEST_FAILURE_RETAINS_LEASE
HUMAN_RECOVERY_RELEASE
EXECUTOR_FAILOVER_ADDED
LEASE_TTL_OR_HEARTBEAT_ADDED
LEASE_STEAL_ADDED
DISPATCH_ROUTER_ADDED
REGRESSIONS
EXECUTOR_RUNS
EXECUTOR_FIX_RUNS
```

Additionally:

```text
PREVIOUS_REVIEW_SHA: 682f8436c43dcdc73bb048c10732f34f1b2445b9
```

is not a REVIEW-029 SHA; it is the previous `ai/task-029` branch head. The previous authoritative REVIEW artifact blob is:

```text
abc8357b8b7adfd315f6c6cc255e2f2e2b718c6a
```

Use the project’s chosen REVIEW-artifact SHA convention consistently and do not substitute the old implementation/result branch head.

Required remediation:
- regenerate RESULT-029 with the complete required manifest;
- bind PREVIOUS_REVIEW_SHA to the actual previous REVIEW artifact identity;
- include updated focused/runtime/Bridge/Continuity/full-suite counts and executor RUN/FIX counts;
- do not claim RACE_EXACTLY_ONE_WINNER / compare-and-release proof PASS until the R1-1 concurrent regression above exists and passes.

---

## New Round-2 Finding

### R2-1 — `cmd_approve()` still has a post-acquire rollback/stranding window
Severity: MEDIUM

After successful lease acquisition, `cmd_approve()` currently performs:

```text
acquire lease
→ save inbox event as APPROVED
→ update operational state
→ save ACTIVE authorization (inside try/rollback)
```

Two failure classes remain:

1. if inbox `save_json()` or `update_state()` raises after lease acquisition but before `save_authorization()`, there is no surrounding rollback and the newly acquired lease can remain ACTIVE without a usable authorization;
2. if `save_authorization()` raises, the catch releases the lease, but the inbox event has already become APPROVED and the operational state has already advanced, so the legacy approval is again non-retryable/stranded even though no ACTIVE authorization exists.

This is fail-closed for execution authority, but it violates the intended AIP-8 activation rollback discipline and preservation of the legacy approval workflow.

Required remediation:
- treat the post-acquire activation sequence as a rollback-aware unit;
- on any failure before durable ACTIVE authorization is established, release only the exact newly acquired lease and restore/retain the approval event in a retryable PENDING state plus a non-executable operational state;
- if rollback itself cannot be proven, remain fail-closed and surface explicit recovery evidence;
- add fault-injection tests for event persistence failure, state persistence failure, and authorization persistence failure after lease acquisition.

---

## Test / Evidence Status

RESULT-029 reports against implementation `1ffebb3c58f1f4d1647c8372d13278ecdc1c559f`:

```text
Focused M5/Bridge set: 56 passed
Full repository:      703 passed
LIVE_EXTERNAL_CALLS:    0
PAID_EXTERNAL_API_CALLS: 0
```

The suites are green, but R1-1 remains unproven by a real interleaving/concurrency regression and R2-1 is not covered.

## Required FIX Scope

Keep Round 3 narrow:

```text
src/aios_bridge/runtime_lease.py        # only if needed for deterministic proof/testability
tests/aios_bridge/test_runtime_lease.py
bridge.py                               # rollback-aware cmd_approve only
tests/test_bridge.py
.ai/results/RESULT-029.md
```

Do not modify `continuity/lease.py`, M4 `executor.py`, state/Brain/failover/provider semantics unless a new locked-contract defect is proven. Do not add TTL, heartbeat, steal, alternate Executor activation or M6 failover.

## Final Independent Audit

`NOT_RUN`.

ADR-017 requires known findings to close first. Round 3 should be delta-first over R1-1, R1-5 and R2-1. Only if all close should the mandatory fresh Final Independent Audit be performed.

## Decision

`CHANGES_REQUIRED`
