# REVIEW-029 — TASK-029 Open Multi-Agent Continuity OS M5 Executor Lease Enforcement

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `3` — ADR-013 Delta Fix Review
- Reviewed branch: `ai/task-029`
- Reviewed branch head: `2437cd71e44edc81ef7ae2a6c88bd20b6c6978f9`
- Tested implementation SHA reported by RESULT: `3603828f847c32bdad8e68dafb250b8865947f28`
- Previous tested implementation: `1ffebb3c58f1f4d1647c8372d13278ecdc1c559f`
- Previous REVIEW blob: `cd4f8680c33ac8362b07ce861b214c8025a9ff0c`
- Base/current main: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Branch relation: ahead `6`, behind `0`; merge-base exact current main.
- `3603828... -> 2437cd7...` changes only `.ai/results/RESULT-029.md`; production/test code at reviewed branch head equals the tested implementation.
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

Round 3 improves both rollback handling and evidence structure. The previous REVIEW identity is now correctly bound, the majority of required M5 manifest fields are present, and `cmd_approve()` now wraps the normal post-acquire activation sequence in rollback handling.

However, three acceptance gaps remain. The concurrency tests still do not reproduce the dangerous compare/rename interleaving, the RESULT manifest is still incomplete relative to TASK-029's exact minimum schema, and rollback failure evidence in `cmd_approve()` is still silently discarded.

---

## Finding Disposition

### R1-1 — Compare-and-release TOCTOU proof
Status: PARTIALLY CLOSED / OPEN
Severity: HIGH

The production implementation remains materially improved: both `acquire()` and `release()` execute under the same task-scoped in-process + OS mutation guard, so the intended cooperating-store design is plausible.

The new test `test_concurrent_compare_and_release_interleaving_race_protection` is concurrent in implementation but its events force the critical operations into this order:

```text
release A completes
→ acquire B completes
→ stale release A starts
```

Therefore it still does not create the original dangerous window:

```text
stale releaser validates A
→ stale releaser pauses before rename
→ another actor attempts release/acquire transition
→ stale releaser resumes
```

The cross-process test also does not test compare-and-release. It starts a process that acquires Lease A, then proves a second process/current process cannot acquire Lease B while A remains active. That proves cross-process acquisition exclusion, not that the OS mutation guard protects the compare-to-rename critical section in `release()`.

Required remediation:
1. provide a deterministic fault/synchronization hook or equivalent test seam inside the release critical section, after exact `require_active(expected)` has passed but before `os.replace()`;
2. start a competing release/acquire path from an independent store while the first release is paused and prove it cannot pass the same mutation guard until the first release linearizes;
3. then prove a stale A release cannot remove a subsequently acquired B;
4. add a cross-process release/acquire proof if practical; if not, the in-process deterministic proof must at least directly exercise the compare-to-rename window and the OS-lock behavior should be separately demonstrated without mislabeling an acquire-conflict test as compare-and-release proof;
5. no sleep-based timing assumption as the correctness mechanism.

Do not mark `COMPARE_AND_RELEASE`/the related race evidence PASS until this proof exists.

### R1-2 — Failed-writer cleanup ownership
Status: CLOSED

No regression identified in Round 3.

### R1-3 — Complete durable write
Status: CLOSED

No regression identified in Round 3.

### R1-4 — Legacy approve lease-conflict retryability
Status: CLOSED

No regression identified in Round 3.

### R1-5 — Required M5 evidence / formal RESULT manifest
Status: PARTIALLY CLOSED / OPEN
Severity: MEDIUM

Round 3 correctly fixes `PREVIOUS_REVIEW_SHA` to the authoritative Round-2 REVIEW blob:

```text
cd4f8680c33ac8362b07ce861b214c8025a9ff0c
```

and adds most semantic PASS/NO fields.

But TASK-029 explicitly requires a minimum manifest containing these exact additional entries, which are still absent:

```text
M5_EXECUTOR_LEASE: PASS|FAIL
FOCUSED_LEASE_TESTS: <count/pass>
RUNTIME_LEASE_TESTS: <count/pass>
BRIDGE_TESTS: <count/pass>
CONTINUITY_TESTS: <count/pass>
FULL_REPO_TESTS: <count/pass>
```

Current aliases `FOCUSED_TESTS` and `TOTAL_REPO_TESTS` do not satisfy the explicit audit schema, and they do not distinguish lease/runtime/Bridge/Continuity evidence.

Required remediation:
- emit the complete TASK-029 manifest exactly or additively;
- retain the correct previous REVIEW blob;
- do not claim `RACE_EXACTLY_ONE_WINNER` / `COMPARE_AND_RELEASE` acceptance evidence as fully sufficient until R1-1 is proven.

### R2-1 — `cmd_approve()` post-acquire rollback
Status: PARTIALLY CLOSED / OPEN
Severity: MEDIUM

The main control-flow defect is improved: event mutation, operational-state update and authorization persistence are now inside one `try`, and failures trigger exact lease release plus attempts to restore the event to PENDING and state to a non-executable status.

Two gaps remain:

1. the test named `test_cmd_approve_post_acquire_inbox_save_failure_rolls_back_lease` does not inject an inbox `save_json()` failure; it injects `update_state()` failure. Round 2 explicitly required separate fault evidence for event persistence, state persistence and authorization persistence failures. Event persistence failure therefore remains untested;
2. rollback operations (`store.release`, event restore, state restore) each use `except Exception: pass`. If any rollback step fails, the user receives only the original activation error and no evidence identifying which recovery step is unproven. That contradicts the Round-2 requirement: if rollback cannot be proven, remain fail-closed **and surface explicit recovery evidence**.

Required remediation:
- add a real event-persistence fault test targeting the first post-acquire inbox save;
- track rollback outcomes explicitly;
- if exact lease release/event restore/state restore cannot be proven, include bounded recovery diagnostics in the failure message without secrets/raw file contents;
- do not falsely state `restored to PENDING` unless the restore actually succeeded;
- add a rollback-failure test proving the system remains non-executable/fail-closed and reports the unresolved recovery condition.

---

## Test / Evidence Status

RESULT-029 reports against implementation `3603828f847c32bdad8e68dafb250b8865947f28`:

```text
Focused M5/Bridge set: 59 passed
Full repository:      706 passed
Regressions:            0
LIVE_EXTERNAL_CALLS:    0
PAID_EXTERNAL_API_CALLS: 0
EXECUTOR_RUNS:          1
EXECUTOR_FIX_RUNS:      2
```

The suites are green, but the remaining findings are proof/rollback-contract gaps not closed by those counts.

## Required FIX Scope

Keep Round 4 narrow:

```text
src/aios_bridge/runtime_lease.py        # only if a deterministic release test seam is required
tests/aios_bridge/test_runtime_lease.py
bridge.py                               # rollback diagnostics only
tests/test_bridge.py
.ai/results/RESULT-029.md
```

Do not modify `continuity/lease.py`, M4 `executor.py`, state/Brain/failover/provider semantics. Do not add TTL, heartbeat, stealing, alternate Executor activation, routing or M6 failover.

## Final Independent Audit

`NOT_RUN`.

Known findings remain open. ADR-017 Final Independent Audit must wait until R1-1, R1-5 and R2-1 are fully closed.

## Decision

`CHANGES_REQUIRED`
