# REVIEW-081 — H3 Canonical Component Role Summaries + Executor Tendencies

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO

TASK_ID: TASK-081
REVIEW_ROUND: 2
REVIEWED_TASK_HEAD_SHA: e1e0067f5a05f7078bce77832ba9890f9e5ac975
REVIEWED_BASE_MAIN_SHA: 4d7e5a6be68ef0aaf0ed7db6927c26c5ddbb61af
PREVIOUS_REVIEWED_HEAD_SHA: 503050df8f69ba69d016c5988e8899f85beae310
TASK_ARTIFACT_BLOB_SHA: 2ae2ad156717946ea74be659fc6cba952eceded6
RESULT_BLOB_SHA: 42ccfdd4911c8c6dac1d7acb45355801a9174d8a
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 1
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: PASS
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-ENGINEERING-H-SERIES
ROADMAP_VERSION: 1.0
ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
MILESTONE: H3
CAPABILITY_ID: H3_ROLE_SUMMARIES_EXECUTOR_TENDENCIES
REQUIREMENT_BINDINGS_FINGERPRINT: af7435d86099a94d2b64dbfd01a9f2781b02441326c868fb04bbe9158e443064
H3_R1_COMPONENT_ROLE_SUMMARIES: PASS
H3_R2_BOUNDED_ROLE_AWARE_SUMMARIES: BLOCKED_BY_B3
H3_R3_EXECUTOR_TENDENCIES: BLOCKED_BY_B3
H3_R4_ADVISORY_PROVENANCE_BOUNDARY: PASS
H3_FORMAL_COMPLETION: NO
H4_H8_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
BASE_MAIN_SHA: 4d7e5a6be68ef0aaf0ed7db6927c26c5ddbb61af
BRANCH: ai/task-081
REVIEWED_TASK_HEAD_SHA: e1e0067f5a05f7078bce77832ba9890f9e5ac975
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 2
BEHIND_BY: 0
MERGE_BASE_SHA: 4d7e5a6be68ef0aaf0ed7db6927c26c5ddbb61af
FIX_DELTA_VS_PREVIOUS_HEAD: 1 commit
CUMULATIVE_SCOPE: EXACT
```

Cumulative delta remains limited to the three authorized implementation/test paths plus Bridge-generated RESULT:

```text
src/aios_engineering/harness/role_tendencies.py
src/aios_engineering/harness/__init__.py
tests/aios_engineering/harness/test_role_tendencies.py
.ai/results/RESULT-081.md
```

Validation evidence:

```text
TARGETED_H3_SUITE: 53 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2487 passed, 7 skipped, 0 failed
GIT_DIFF_CHECK: PASS
NETWORK/LLM/PAID_API: NONE
```

## Previous Findings

### B1 — H3 scalar/count boundedness

STATUS: CLOSED

The FIX adds explicit upper bounds for component symbol counts, component relationship counts, co-observed task counts, and unobserved-role file accounting. It also enforces `coobserved_task_count <= observed_task_count` inside `ExecutorTendencyProfile`. Bool/negative/overflow cases for these newly added scalar bounds are covered.

### B2 — Mandatory regression matrix

STATUS: PARTIALLY CLOSED

The FIX now correctly proves:

```text
MULTIPLE_EXECUTORS_ONE_TASK_PRESERVED: PASS
SAME_TASK_COMPONENT_FINDING_COOBSERVATION_IN_BOTH_PROFILES: PASS
ORDER_INDEPENDENCE: PASS
MISLEADING_BUSINESS_DOMAIN_PATHS_DO_NOT_CREATE_DOMAIN_ROLES: PASS
DIRECT_DATACLASS_DUPLICATE_REJECTION: PASS
```

One residual contract/test defect remains.

## Blocking Finding

### B3 — Public factories silently deduplicate identities and the hard-bound matrix is still incomplete

TASK-081 requires duplicate identities to fail closed unless the contract explicitly defines canonical deduplication from identical upstream evidence. No such deduplication exception is defined for these H3 public factory inputs.

The current public factories still silently deduplicate:

```python
ComponentRoleSummary.create(...):
    sorted(set(observed_roles))

ExecutorTendencyProfile.create(...):
    sorted(set(observed_tasks))
    sorted(set(coobserved_review_finding_ids))
```

This means callers can submit duplicate role/task/finding identities and receive a valid canonical object/fingerprint instead of a fail-closed rejection. The new duplicate tests use `replace(...)` on already-created dataclasses, so they do not exercise this public-factory path and cannot detect the silent deduplication.

The regression named `test_all_hard_bounds_and_bool_as_int_rejection` also does not yet prove every hard-bound family required by TASK-081 / REVIEW round 1. It covers the new scalar maxima plus `MAX_H3_COMPONENT_SUMMARIES`, but does not explicitly overflow/boundary-test at least:

```text
MAX_H3_MEMBER_FILES_PER_COMPONENT
MAX_H3_ROLES_PER_COMPONENT
MAX_H3_EXECUTOR_PROFILES
MAX_H3_OBSERVED_TASKS_PER_EXECUTOR
MAX_H3_COMPONENT_OBSERVATIONS_PER_EXECUTOR
MAX_H3_REVIEW_FINDINGS_PER_EXECUTOR
MAX_H3_FINGERPRINT_PAYLOAD_BYTES
```

Production validators exist for several of these, but the locked acceptance criterion is an explicit regression matrix, not only implementation presence.

#### Required FIX

Keep the architecture unchanged and close only this contract gap:

1. Public `create(...)` factories must reject duplicate role/task/review-finding identities before canonical sorting/fingerprinting. Do not silently `set()` them away.
2. Add factory-level duplicate regression tests proving duplicate `observed_roles`, `observed_tasks`, and `coobserved_review_finding_ids` fail closed.
3. Add explicit boundary/overflow tests for every remaining H3 hard-bound family listed above. For the fingerprint payload bound, a small monkeypatched limit is sufficient; do not allocate a giant payload.
4. Preserve order independence for unique inputs.
5. Do not add routing, scoring, quality grades, causal blame, H4 lifecycle, network, LLM, or paid-provider behavior.

## FIX Scope

Permitted paths only:

```text
src/aios_engineering/harness/role_tendencies.py
tests/aios_engineering/harness/test_role_tendencies.py
```

`src/aios_engineering/harness/__init__.py` does not need further change unless a bound export required by an existing public contract is missing.

Do not modify:

```text
src/aios_engineering/harness/roles.py
src/aios_engineering/harness/structural_experience_graph.py
src/aios_engineering/harness/graph.py
src/aios_engineering/harness/ranking.py
src/aios_engineering/harness/experience.py
src/aios_engineering/harness/discovery.py
Bridge/runtime/governance code
roadmap/completion records
H4-H8 capability code
```

No H3 architectural redesign is authorized.

## Machine-Readable FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-081.md","blob_sha":"2ae2ad156717946ea74be659fc6cba952eceded6"},{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/decisions/ADR-054-AIOS-ENGINEERING-H2-FORMAL-COMPLETION-H3-CANONICAL-OPEN-CONTRACT-LOCK.md","blob_sha":"07365dfdc4d5bee520a0edebd0f1f7258cdafe92"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/role_tendencies.py","tests/aios_engineering/harness/test_role_tendencies.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_role_tendencies.py tests/aios_engineering/harness/test_structural_experience_graph.py tests/aios_engineering/harness/test_roles.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Publish only through canonical Bridge FIX flow.

## Decision

```text
TASK-081: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
BLOCKERS_REMAINING: 1
B1_H3_SCALAR_COUNT_BOUNDEDNESS: CLOSED
B2_MANDATORY_REGRESSION_MATRIX: PARTIALLY_CLOSED
B3_FACTORY_DUPLICATE_FAIL_CLOSED_AND_FULL_BOUND_MATRIX: OPEN
H3_R1: PASS
H3_R2: BLOCKED
H3_R3: BLOCKED
H3_R4: PASS
H3_FORMAL_COMPLETION: NO
H4_H8_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```
