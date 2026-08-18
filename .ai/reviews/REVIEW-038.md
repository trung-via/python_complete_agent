# REVIEW-038 — M10.2 Runtime Capacity Snapshot + Bridge Recommendation Surface

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO

## Review Round

Round 1 — independent architecture, persistence-boundary, authority, control-binding, and adversarial-test audit.

## Authoritative Anchors

```text
TASK_ID: TASK-038
BASELINE_MAIN_SHA: b1f85034c1b18b3d3526f6ece85afd04cdcdc17e
TASK_BRANCH: ai/task-038
FINAL_TASK_HEAD_SHA_REVIEWED: 74c753d75226ba335e0187261a34f726390b8059
TASK_BLOB_SHA: e6711e6efd81416a053d94c336cfcb828a298b72
ADR_027_BLOB_SHA: 11674c9b5b2c3639552678f7371dba5c3d0599cd
BLUEPRINT_BLOB_SHA: df5531a590ebbe999d107cecc0cdbf6340eae506
RESULT_BLOB_SHA: 0ff83a296c5103d346bc17801670088c38d46c25
BRIDGE_BLOB_SHA: f0b28cdddc610ea330ec9403bd111bc37bc93ac1
RUNTIME_DISPATCH_BLOB_SHA: ea4a01ec774a8dc79e52080c263575ac4acba000
RUNTIME_TEST_BLOB_SHA: 17664bf942c145e66a0ca59196eed3d9944beaed
BRIDGE_DISPATCH_TEST_BLOB_SHA: 848ccc9b93066b2b18797bc0830ab36113851f51
M10_1_DISPATCH_BLOB_SHA: 9169884c079302f86bbda5f77a9a9d7ea6800dd9
```

## Lineage / Scope Audit

```text
REMOTE_MAIN_SHA: b1f85034c1b18b3d3526f6ece85afd04cdcdc17e
COMMITS_AHEAD_OF_BASELINE: 1
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: b1f85034c1b18b3d3526f6ece85afd04cdcdc17e
CHANGED_PATHS:
  .ai/results/RESULT-038.md
  bridge.py
  src/aios_bridge/runtime_dispatch.py
  tests/aios_bridge/test_runtime_dispatch.py
  tests/test_bridge_dispatch.py
SCOPE_AUDIT: PASS
```

No M10.1 ranking, Brain/Executor core contract, lease, stable failover, hot-handoff, runtime lease, provider, or External Brain implementation changed.

## Positive Audit Results

```text
RUNTIME_CAPACITY_OUTSIDE_WORKTREE: PASS
PER_ACTOR_CAPACITY_FILES: PASS
TTL_FRESHNESS_MODEL: PASS
MISSING_TO_UNKNOWN: PASS
EXPIRED_TO_UNKNOWN_WITHOUT_REWRITE: PASS
FUTURE_OBSERVATION_FAIL_CLOSED_AT_USE: PASS
RECORD_FINGERPRINT_TAMPER_REJECTED: PASS
GENERIC_BRAIN_EXECUTOR_STORE_SHAPE: PASS
EXACT_SINGLE_POLICY_MARKER: PASS
UNKNOWN_POLICY_FIELDS_REJECTED: PASS
DUPLICATE_POLICY_ACTORS_REJECTED: PASS
M10_1_DISPATCH_REUSED: PASS
M10_1_DISPATCH_BLOB_UNCHANGED: PASS
RUN_TASK_BLOB_DOUBLE_CHECK: PASS
FIX_CHANGES_REQUIRED_BINDING: PASS
CONTROL_ARTIFACT_DRIFT_REJECTION: PASS
CODEX_RECOMMENDATION_SCENARIO: PASS
FORBIDDEN_PAID_API_NO_FALLTHROUGH: PASS
RECOMMENDATION_CALLS_M10_1_ONCE: PASS
RECOMMENDATION_AUTH_MUTATION: NONE
RECOMMENDATION_LEASE_MUTATION: NONE
RECOMMENDATION_EXECUTOR_INVOCATION: NONE
HUMAN_APPROVAL_REQUIRED_OUTPUT: PASS
EXISTING_APPROVE_DEFAULT_UNCHANGED: PASS
```

Required real-shaped policy is implemented correctly:

```text
antigravity = QUOTA_EXHAUSTED
codex       = AVAILABLE
=> STATUS: SELECTED
=> SELECTED_EXECUTOR: codex
=> HUMAN_APPROVAL_REQUIRED: YES
```

This remains recommendation evidence only and does not create an authorization or ExecutorLease.

## Full Repository Test Gate

Bridge publication reports:

```text
987 passed, 4 skipped, 1533 warnings in 123.92s
exit code 0
```

There is no existing-suite regression signal.

---

## FINDING R1-1

FINDING_ID: R1-1
SEVERITY: MEDIUM
ROOT_CAUSE: `RuntimeCapacityRecord` validates canonical JSON size against `MAX_SERIALIZED_BYTES`, but `AtomicRuntimeCapacityStore.write()` appends a newline after that validation. `load()` / `RuntimeCapacityRecord.from_json()` reject persisted bytes whose total length exceeds `MAX_SERIALIZED_BYTES`. Therefore a valid record at the exact JSON size boundary can be replaced into the final path and then immediately rejected by the store's own read-back solely because of the writer-added newline.

BROKEN_INVARIANT:
- ADR-027 Decision 12 requires fail-closed atomic persistence with deterministic load validation and read-back fingerprint equality.
- The blueprint requires `canonical JSON + b"\n"` persistence plus a bounded load.
- A record accepted as valid by the runtime record contract must either round-trip through the store or be rejected before the final atomic replace; the store must not self-create an unreadable final record at its own size boundary.

MECHANICAL_COUNTEREXAMPLE:
With the current schema and ordinary values, an actor ID consisting of 16,111 lowercase `a` characters is canonical/path-safe and can produce exactly 16,384 bytes of canonical record JSON. The constructor accepts that size. `write()` then persists 16,385 bytes after appending `\n`; `load()` rejects it as oversized after `os.replace` has already installed the final file.

REQUIRED_BEHAVIOR:
- Make writer and loader size semantics consistent at the newline boundary.
- No record accepted for persistence may become unreadable solely because the store itself appends the canonical newline.
- Oversized persisted data must still fail closed.
- A failure discovered before publication of a valid final record must not leave a newly-created unreadable capacity record as successful state.
- Do not weaken fingerprint validation.

FORBIDDEN_IMPLEMENTATIONS:
- Do not increase or remove the global `MAX_SERIALIZED_BYTES` safety bound merely to hide the off-by-one.
- Do not skip the read-back validation.
- Do not silently truncate JSON or the newline.
- Do not accept arbitrary oversized trailing bytes.

REQUIRED_TESTS:
1. Exact maximum canonical-JSON boundary round-trip/rejection behavior is mechanically defined and green.
2. Writer-added newline cannot create the MAX+1 self-corruption case.
3. Oversized persisted payload remains rejected.
4. On the boundary failure path, no unreadable new final record is left behind (or a pre-existing valid final record remains intact, depending on the chosen compliant implementation).

ADVERSARIAL_CHECKS:
- Test at `MAX_SERIALIZED_BYTES - 1`, exact `MAX_SERIALIZED_BYTES`, and one byte beyond the supported persisted representation as appropriate to the chosen consistent semantics.
- Fingerprint tamper rejection must remain green.

CLOSE_CONDITIONS:
- Production store and loader agree on one explicit bounded representation.
- All boundary tests pass.
- Existing runtime-dispatch and M10.1 tests remain green.

ALLOWED_FILES:
- `src/aios_bridge/runtime_dispatch.py`
- `tests/aios_bridge/test_runtime_dispatch.py`

FORBIDDEN_SCOPE:
- `src/aios_bridge/continuity/dispatch.py`
- `bridge.py`
- lease/failover/hot-handoff/provider/API code

---

## FINDING R1-2

FINDING_ID: R1-2
SEVERITY: MEDIUM
ROOT_CAUSE: The implementation covers ADR-027 Decision 15 well, but two explicit adversarial tests required by the locked implementation blueprint are not present: simulated low-level write/flush/fsync failure cleanup for the atomic temp file, and malformed/non-actionable FIX review status rejection distinct from the existing APPROVED-review test.

BROKEN_INVARIANT:
- Blueprint section 14 requires temp files cleaned on simulated replace/write failure.
- Blueprint section 15 requires APPROVED/malformed FIX review rejection.
- For a proof-oriented control-plane milestone, code inspection is not a substitute for the explicitly locked adversarial regression tests.

REQUIRED_BEHAVIOR:
- Preserve the current production behavior unless the added tests expose a real defect.
- Add the missing adversarial coverage without deleting or weakening existing tests.

FORBIDDEN_IMPLEMENTATIONS:
- Do not mark tests xfail merely to satisfy count.
- Do not remove existing replace-failure or APPROVED-review tests.
- Do not broaden production scope unless a new test mechanically demonstrates production behavior is wrong.

REQUIRED_TESTS:
1. Simulated temp-file write/flush/fsync failure proves temp cleanup and no corrupt new final state; keep the existing `os.replace` failure test.
2. FIX control artifact with malformed/missing/unknown review status is rejected fail-closed; keep the existing APPROVED-review rejection test.

ADVERSARIAL_CHECKS:
- Existing zero/multiple/malformed dispatch-marker tests remain green.
- Existing recommendation no-auth/no-lease test remains green.

CLOSE_CONDITIONS:
- Both missing locked tests are present and pass.
- No previously required adversarial test is removed.

ALLOWED_FILES:
- `tests/aios_bridge/test_runtime_dispatch.py`
- `tests/test_bridge_dispatch.py`
- `src/aios_bridge/runtime_dispatch.py` only if the new atomic failure test exposes a production defect

FORBIDDEN_SCOPE:
- M10.1 dispatcher
- Bridge authorization/approve/publish semantics
- lease/failover/hot-handoff/provider/API code

---

## Final Decision

```text
R1-1: OPEN
R1-2: OPEN
SEMANTIC_AUTHORITY_FINDINGS: NONE
M10_1_RANKING_CHANGED: NO
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
M10_2: CHANGES_REQUIRED
M10_3_PROVEN: NO
STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
```

The fix is intentionally narrow. Do not redesign M10.2 and do not change M10.1 ranking or Human authority.