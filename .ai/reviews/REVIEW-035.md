# REVIEW-035 — M9.2 Human-Authorized Hot Local Handoff Bridge Lifecycle

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO

## Review Round

Round 1 — independent semantic audit.

## Authoritative Anchors

```text
TASK_ID: TASK-035
BASELINE_MAIN_SHA: 6d9222523fa24ac7b456299f37655b6c544523a9
TASK_BRANCH: ai/task-035
TASK_BLOB_SHA: 7bed4597fb91d41d6f3719f573c67de7f097a15c
ADR_024_BLOB_SHA: 701e5a29bce56d6eed18d24095076db4dcdfe93c
BLUEPRINT_BLOB_SHA: f4a18ab4ec663c80dbcba2bc4d2e7ab76a182491
BRIDGE_BLOB_SHA: b3063ea65d97b024205d313aa23e7a54a731cc3d
M9_2_TEST_BLOB_SHA: b1e41715ae639a5293eb4ceee53a1276244b7ff7
RESULT_035_BLOB_SHA: f3478caa4e3a4788f8412bef4c6b25cb9fa0699f
```

## Publication / Scope Audit

```text
COMMITS_AHEAD_OF_BASELINE: 1
COMMITS_BEHIND_BASELINE: 0
CHANGED_PATHS:
  .ai/results/RESULT-035.md
  bridge.py
  tests/test_bridge_hot_handoff.py
SCOPE_AUDIT: PASS
EXECUTOR_ID: codex
EXECUTOR_FAILOVER: NO
HOT_HANDOFF: NO
FULL_REPO_TESTS: 849 passed, 1 skipped
```

The implementation is structurally bounded and the full repository suite is green. Final PASS is blocked by the semantic findings below.

---

## FINDING R1-1

FINDING_ID: R1-1
SEVERITY: HIGH
ROOT_CAUSE: `cmd_hot_handoff_prepare()` deep-copies the entire source ACTIVE authorization into `HANDOFF_PREPARED`, and `cmd_hot_handoff_activate()` deep-copies it again into the replacement ACTIVE authorization. Any pre-existing M6/M8 stable-failover keys (`failover_source_lease`, `failover_proof`, `failover_proof_fingerprint`) therefore survive the hot-handoff lifecycle unchanged. `cmd_publish()` later interprets those retained keys as the CURRENT stable-boundary failover proof and validates that old proof against the new hot-handoff replacement lease. The old proof is bound to the prior source Executor lease, so the hot-handoff path can enter a publication dead-end and also violates the contract that M9 hot handoff must not create/reuse StableExecutorFailoverProof semantics.
BROKEN_INVARIANT: M9.2 hot handoff and M6/M8 stable-boundary failover are semantically separate; hot handoff must not reuse a StableExecutorFailoverProof as current handoff authority, and every successfully activated M9.2 lifecycle must retain a valid path to normal Bridge publication.
REQUIRED_BEHAVIOR: For M9.2 v1, fail closed BEFORE checkpoint capture/source release if the source ACTIVE authorization contains ANY stable-failover marker. The minimal safe behavior is to reject the unsupported composition explicitly. Do not silently strip, reinterpret, regenerate, or migrate a stable failover proof during hot handoff. Ordinary non-failover ACTIVE authorization must remain supported exactly as now.
FORBIDDEN_IMPLEMENTATIONS:
- Do not rewrite or regenerate `StableExecutorFailoverProof` for the hot-handoff replacement.
- Do not delete stable-failover fields after checkpoint/source release.
- Do not make `cmd_publish()` ignore malformed/mismatched failover proof globally.
- Do not change M6/M8 proof contracts.
- Do not modify `executor_failover.py`, `lease.py`, `runtime_lease.py`, or M9.1 checkpoint semantics.
REQUIRED_TESTS:
- ACTIVE source authorization with a complete stable-failover metadata triplet -> `hot-handoff-prepare` fails before capture, before source lease release, and leaves authorization/lease unchanged.
- ACTIVE source authorization with any partial stable-failover marker -> same fail-closed behavior.
- Ordinary ACTIVE authorization without failover markers -> existing successful prepare path remains green.
ADVERSARIAL_CHECKS:
- Assert checkpoint capture function is not called on rejected stable-failover source authorization.
- Assert no source lease release occurs.
- Assert no `HANDOFF_PREPARED` authorization is persisted.
CLOSE_CONDITIONS:
1. `cmd_hot_handoff_prepare()` deterministically rejects any source auth containing one or more stable-failover marker keys before any checkpoint/lease mutation.
2. New adversarial tests above pass.
3. Existing stable failover tests and ordinary M9.2 tests remain green.
ALLOWED_FILES:
- bridge.py
- tests/test_bridge_hot_handoff.py
FORBIDDEN_SCOPE:
- M6/M8 proof redesign
- executor_failover.py
- runtime_lease.py
- continuity/lease.py
- continuity/hot_handoff.py

---

## FINDING R1-2

FINDING_ID: R1-2
SEVERITY: HIGH
ROOT_CAUSE: Activation validates checkpoint-bound source executor/fingerprint fields from nested `hot_handoff` metadata, but it does not reconstruct and bind the source lease represented by the top-level `HANDOFF_PREPARED` authorization to that nested source provenance before overwriting top-level lease fields with the replacement lease. In particular, `hot_handoff.source_lease_id` is only checked as a non-empty string and is not bound to the source authorization's `lease_id` or to an exact reconstructed source lease. A tampered prepared authorization can therefore alter source lease identity/provenance without activation detecting it.
BROKEN_INVARIANT: `HANDOFF_PREPARED` must preserve exact source authorization and exact source lease provenance across the zero-active-executor gap; replacement activation may proceed only from that exact prepared provenance.
REQUIRED_BEHAVIOR: During activation, before checkpoint verification or replacement acquisition, reconstruct the source `ExecutorLease` from the top-level prepared authorization using the existing `reconstruct_expected_executor_lease()` primitive, then require exact equality between that reconstructed source lease and nested source provenance:
- executor_id == `hot_handoff.source_executor_id`
- lease_id == `hot_handoff.source_lease_id`
- fingerprint() == `hot_handoff.source_lease_fingerprint`
- execution_fingerprint == `hot_handoff.source_execution_fingerprint`
Also retain existing checkpoint provenance checks. Any mismatch must fail before replacement lease acquisition.
FORBIDDEN_IMPLEMENTATIONS:
- Do not infer or repair source fields from checkpoint/history.
- Do not overwrite mismatched prepared metadata with top-level values.
- Do not accept source lease ID as unanchored audit text.
- Do not loosen `reconstruct_expected_executor_lease()`.
REQUIRED_TESTS:
- Tamper top-level prepared `lease_id` only -> activation fails before replacement acquire.
- Tamper nested `source_lease_id` only -> activation fails before replacement acquire.
- Tamper top-level source executor/lease fingerprint/execution fingerprint independently -> activation fails before replacement acquire.
- Untampered prepared authorization -> successful activation remains green.
ADVERSARIAL_CHECKS:
- For every tamper case, assert replacement `store.acquire()` is never called and prepared authorization remains unchanged.
- Assert no state transition to ACTIVE occurs.
CLOSE_CONDITIONS:
1. Exact reconstructed source lease is mechanically bound to nested prepared provenance before replacement acquisition.
2. All requested tamper tests pass.
3. Existing checkpoint provenance and activation rollback tests remain green.
ALLOWED_FILES:
- bridge.py
- tests/test_bridge_hot_handoff.py
FORBIDDEN_SCOPE:
- new lease schema
- M9.1 checkpoint schema change
- history scanning/fuzzy recovery
- unrelated Bridge refactor

---

## Non-blocking Observation

`RESULT-035` Diff Stat still reports only the already-tracked `bridge.py` change while `Files Changed` correctly lists the newly-added test file. This is the pre-existing Bridge diff-stat presentation limitation for untracked files and is explicitly outside TASK-035 scope. It does not affect this review decision.

## Round-1 Decision

```text
SCOPE_AUDIT: PASS
FULL_REPO_TESTS: PASS
M9_2_LIFECYCLE_CORE: PARTIAL_PASS
R1-1: OPEN
R1-2: OPEN
SEMANTIC_FINDINGS: 2
FINAL_INDEPENDENT_AUDIT: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
```

Do not merge TASK-035. Human may authorize a FIX with Codex only after synchronizing this exact REVIEW-035 artifact. The Executor must close only R1-1 and R1-2 within the allowed files, run focused tests, then stop for Bridge publication and another independent review.
