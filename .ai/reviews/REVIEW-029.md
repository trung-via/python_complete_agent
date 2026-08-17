# REVIEW-029 — TASK-029 Open Multi-Agent Continuity OS M5 Executor Lease Enforcement

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1` — ADR-017 Full Semantic Review
- Reviewed branch: `ai/task-029`
- Reviewed branch head: `682f8436c43dcdc73bb048c10732f34f1b2445b9`
- Tested implementation SHA reported by RESULT: `580739b1e9daadf6e4cf7a44bb6e39ad77d08b81`
- Base/current main: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Branch relation: ahead `2`, behind `0`; merge-base exact current main.
- `580739b... -> 682f843...` adds only `.ai/results/RESULT-029.md`; production/test code at reviewed branch head equals the tested implementation.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: NOT_RUN
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## What Passed

The implementation is correctly scoped to the intended M5 boundary:
- new vendor-neutral `continuity/lease.py`;
- new runtime-only `runtime_lease.py`;
- additive Continuity exports;
- Bridge lease integration and explicit human recovery commands;
- no changes to M4 `executor.py`, canonical state, Brain/failover/provider code;
- no Codex/Claude Code activation, TTL, heartbeat, stealing, routing or M6 failover.

The canonical `ExecutorLease` model itself is materially aligned with ADR-019/TASK-029: strict schema, RUN/FIX only, frozen record, bounded canonical JSON, exact workspace/execution fingerprints, forbidden authority/timing/secret keys, and a pure lease-binding validator.

Atomic acquisition also uses `O_CREAT | O_EXCL`, and the focused two-store acquisition race proves one winner for simultaneous acquisition.

These positive points are not sufficient for approval because the runtime release/acquisition failure paths do not yet satisfy the locked concurrency contract.

---

## Findings

### R1-1 — Compare-and-release has a TOCTOU race that can remove a newer lease
Severity: HIGH

`AtomicExecutorLeaseStore.release()` currently performs:

```text
require_active(expected)
→ create history destination
→ os.replace(ACTIVE.json, history)
```

The equality check and the rename are separate operations with no cross-process/task-scoped synchronization or compare-and-swap primitive tying the renamed file to the exact record that was validated.

A valid interleaving is:

```text
ACTIVE = Lease A

Releaser 1: require_active(A) PASS
Releaser 2: require_active(A) PASS
Releaser 1: rename ACTIVE(A) -> history
Acquirer B:  acquire Lease B -> ACTIVE(B)
Releaser 2: rename ACTIVE(B) -> history  # stale A release removes B
```

The second releaser then returns `expected A` even though it actually moved Lease B out of ACTIVE.

This directly violates TASK-029 C11 / Acceptance Criterion 6 / adversarial checklist:

```text
stale old lease cannot release newer lease
```

Required remediation:
1. make acquire/release ownership mutation linearizable across independent store/process instances, not merely within one Python call;
2. use a task-scoped cross-process mutation guard or another mechanism providing a true compare-and-release property;
3. corruption/guard failure must remain fail-closed; no timeout/steal semantics may be introduced;
4. add a deterministic interleaving regression test (barriers/events/fault hook, no sleep-based correctness) proving an old release can never remove newly acquired Lease B.

### R1-2 — Failed-writer cleanup can unlink an ACTIVE lease not proven to belong to this acquire call
Severity: HIGH

`acquire()` catches a broad non-`FileExistsError` exception and then does:

```python
if active_file.exists():
    active_file.unlink()
```

The implementation does not track whether this call successfully passed the exclusive `os.open()` linearization point before cleanup. Therefore cleanup is based on path existence rather than proven ownership of the file created by this call.

This violates TASK-029 C9 and the explicit adversarial requirement:

```text
failed writer cleanup cannot delete somebody else’s lease
```

Required remediation:
1. track `created_by_this_call` only after successful exclusive create;
2. cleanup may target ACTIVE only when this call demonstrably created the file and the cleanup target is still that same created object/identity;
3. an ambiguous failure before ownership must never unlink ACTIVE;
4. add fault-injection regression tests covering failure before successful create and failure after this call created the file.

### R1-3 — Acquisition may report success without proving complete durable record write
Severity: HIGH

The acquisition write path currently issues one `os.write(fd, canonical_bytes)` and ignores every `OSError` from `os.fsync(fd)`.

Problems:
- `os.write()` is not contractually guaranteed to write all requested bytes in one call; its return value is ignored;
- a short write can therefore leave truncated `ACTIVE.json` while `acquire()` still returns success;
- `fsync` failure is swallowed, even though C9 requires the complete record to be flushed/fsync'd before success where supported;
- the next strict read may see corruption after the caller already persisted ACTIVE authorization.

Required remediation:
1. implement write-all semantics and verify all canonical bytes were persisted before success;
2. treat durable-write/fsync failures as acquisition failure except only narrowly documented platform-not-supported cases, if any;
3. cleanup must follow R1-2 ownership-safe rules;
4. add deterministic fault-injection tests for partial writes and fsync failure.

### R1-4 — Legacy `cmd_approve()` mutates approval/state before lease acquisition and becomes non-retryable on conflict
Severity: MEDIUM

`cmd_approve()` currently:

```text
load PENDING event
→ mark event APPROVED + save
→ update operational state to IN_PROGRESS / CHANGES_REQUIRED
→ attempt lease acquisition
→ save ACTIVE authorization
```

If lease acquisition conflicts/fails, no new ACTIVE authorization is persisted, which is fail-closed for execution authority; however the inbox event is already `APPROVED` and therefore no longer returned by `pending_events()` / `find_latest_event()` on retry. The operational state was also advanced before ownership was acquired.

This can strand the legacy/manual approval workflow after a legitimate lease conflict and is contrary to the intended activation ordering/rollback discipline of C17/AIP-8 and the requirement to preserve Bridge behavior outside the M5 gate.

Required remediation:
- acquire the exact lease before making the pending approval/event operationally consumed/approved, or restore the event/state exactly if acquisition fails;
- successful path must still acquire before ACTIVE authorization;
- add a Bridge regression test proving a lease conflict leaves the legacy approval retryable and creates no new ACTIVE authorization.

### R1-5 — Required M5 evidence cases are not demonstrated by the submitted tests/RESULT manifest
Severity: MEDIUM

The focused runtime suite contains seven tests and does not exercise the two critical failure classes above: ownership-safe failed-writer cleanup or concurrent stale-release/new-acquire interleaving. The Bridge test list also does not provide explicit evidence for several required M5 lifecycle cases such as legacy `cmd_approve()` lease conflict/rollback and commit/push-failure lease retention.

Additionally, RESULT-029 contains useful prose/test output but does not provide the explicit minimum Review Manifest requested by TASK-029 (`BASE_SHA`, `IMPLEMENTATION_SHA`, `PREVIOUS_REVIEW_SHA`, `M5_EXECUTOR_LEASE`, `COMPARE_AND_RELEASE`, `BRIDGE_V0_4_BEHAVIOR_CHANGED: YES — ADR-019-authorized M5 lease gate only`, `AUTHORITY_WIDENED`, etc.) in the required audit-friendly form.

Required remediation:
- add the missing adversarial/failure-injection tests required by R1-1 through R1-4 and TASK-029 checklist;
- explicitly prove test failure, commit failure and push failure retain the exact lease, and successful push releases it;
- regenerate RESULT-029 with the required formal manifest and updated test counts.

---

## Test / Evidence Status

RESULT-029 reports against implementation `580739b1e9daadf6e4cf7a44bb6e39ad77d08b81`:

```text
Focused M5/Bridge set: 49 passed
Full repository:      696 passed
Regressions:            0
LIVE_EXTERNAL_CALLS:    0
PAID_EXTERNAL_API_CALLS: 0
EXECUTOR_RUNS:          1
EXECUTOR_FIX_RUNS:      0
```

The suites are green, but the findings above identify missing concurrency/failure interleavings not represented by the current tests.

## Required FIX Scope

Expected narrow scope:

```text
src/aios_bridge/runtime_lease.py
tests/aios_bridge/test_runtime_lease.py
bridge.py
tests/test_bridge.py
.ai/results/RESULT-029.md
```

`continuity/lease.py` and `continuity/__init__.py` should remain unchanged unless the Executor proves a genuine lease-contract defect requiring them.

Do not modify M4 `executor.py`, state/Brain/failover/provider semantics, introduce TTL/heartbeat/steal, activate another Executor, or implement M6 failover.

## Required Re-Test

At minimum after FIX:

```text
Focused lease core
Focused runtime lease including fault/race tests
Focused Bridge tests
Full Continuity
Full AIOS Bridge
Full repository
```

All green, zero external/model/API calls.

## Final Independent Audit

`NOT_RUN`.

ADR-017 requires all known findings to close before the mandatory fresh Final Independent Audit. Round 2 should be delta-first over R1-1 through R1-5; if all close, perform the independent contract-to-final-code audit before `APPROVED`.

## Decision

`CHANGES_REQUIRED`
