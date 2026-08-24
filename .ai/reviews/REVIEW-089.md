# REVIEW-089 — Lean Review Deterministic Contract Foundation
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
TASK_ID: TASK-089
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 24cc46839f4bbd8043b0dc15a9426f7658c66064
REVIEWED_BASE_MAIN_SHA: 90b381d3be78b68a8e7b25c42c66e539486a44e2
TASK_ARTIFACT_BLOB_SHA: 21b9dee64040c8289be49a33230af9e1b1b7480b
RESULT_BLOB_SHA: 4802e47bf74a988d45885dc346210de1a43bad2f
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 3
FIX_EXECUTION_MODE: IMPLEMENTATION
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
P1_FORMAL_COMPLETION: NO
TASK_087_PREREQUISITE_ELIGIBLE: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-089.md","blob_sha":"21b9dee64040c8289be49a33230af9e1b1b7480b"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/review_pipeline.py","src/aios_bridge/certification_job.py","tests/aios_bridge/test_review_pipeline.py","tests/aios_bridge/test_certification_job.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: 24cc46839f4bbd8043b0dc15a9426f7658c66064
BASE_MAIN: 90b381d3be78b68a8e7b25c42c66e539486a44e2
CURRENT_MAIN: 90b381d3be78b68a8e7b25c42c66e539486a44e2
AHEAD: 1
BEHIND: 0
EXECUTOR: codex
T2: 2617 passed, 7 skipped, 0 failed
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
```

## Executor Authority Clarification

This REVIEW is the complete normative FIX instruction for B1-B3. The executor does not need to inspect or infer instructions from ADR-064, ADR-065, roadmap prose, prior reviews, or RESULT-089. TASK-089 is the sole context artifact needed to preserve original scope and acceptance boundaries.

Do not redesign the contracts. Implement only the exact repairs below in the four allowed paths. Existing accepted behavior remains protected unless an exact repair below requires touching the same function.

## B1 — Finding lifecycle and CLOSED evidence

Required code behavior:

```text
_FINDING_TRANSITIONS[VERIFYING] = {CLOSED, OPEN}
_FINDING_TRANSITIONS[CLOSED] = {REOPENED}
VERIFYING -> REOPENED = INVALID
VERIFYING -> OPEN = VALID
CLOSED -> REOPENED requires reopen_evidence=True
```

`FindingRecord.__post_init__` must additionally enforce:

```text
status == CLOSED -> fixed_by_sha is required and exact lowercase 40-hex
status == CLOSED -> closure_review_round is required and valid
```

`transition_finding_status(..., target=CLOSED)` must only return a CLOSED record when the resulting record contains both closure fields. This may be achieved by normal dataclass validation after `replace()`; no new persistence layer is required.

Required tests:

```text
VERIFYING -> OPEN passes
VERIFYING -> REOPENED rejects
VERIFYING -> CLOSED without closure evidence rejects
VERIFYING -> CLOSED with fixed_by_sha + closure_review_round passes
direct FindingRecord(status=CLOSED) without either closure field rejects
FindingRecord.from_dict(status=CLOSED) without either closure field rejects
CLOSED -> REOPENED without reopen_evidence rejects
CLOSED -> REOPENED with reopen_evidence passes
```

## B2 — Terminal certification evidence

Required code behavior in `CertificationJob.__post_init__`:

```text
status == CERTIFICATION_PASS -> terminal_result_digest REQUIRED
status == CERTIFICATION_FAILED -> terminal_result_digest REQUIRED
status == SUPERSEDED -> terminal_result_digest MUST be None
pre-terminal status -> terminal_result_digest MUST be None
```

The digest remains exact lowercase 64-hex.

`creates_certification_authority` remains true only for a valid `CERTIFICATION_PASS` object; because construction is fail-closed, an evidence-free PASS object must be impossible.

`transition_certification_job()` must therefore require/provide a digest when targeting PASS or FAILED. SUPERSEDED remains non-authoritative and must not carry a terminal test-result digest.

Required tests:

```text
RUNNING -> PASS without digest rejects
RUNNING -> PASS with 64-hex digest passes
RUNNING -> FAILED without digest rejects
RUNNING -> FAILED with 64-hex digest passes
RUNNING -> SUPERSEDED with no digest passes
SUPERSEDED with digest rejects
direct/from_dict PASS without digest rejects
direct/from_dict FAILED without digest rejects
valid PASS creates authority
SUPERSEDED never creates authority
```

## B3 — Strict machine-readable sequence parsing

Before tuple conversion in `FindingRecord.from_dict()`, require:

```text
type(data["affected_surfaces"]) is list
type(data["required_proof_ids"]) is list
```

Anything else, including string, tuple, scalar, or mapping, must reject before coercion. After that, tuple conversion is allowed and existing `FindingRecord.__post_init__` validation remains authoritative.

Required tests:

```text
string/scalar/mapping affected_surfaces rejects
string/scalar/mapping required_proof_ids rejects
canonical to_dict -> from_dict round trip passes
```

Apply the same rule only where this FIX introduces or touches a machine-readable sequence parser in these two modules. Do not widen scope.

## Accepted / Protected

Preserve unless the exact repairs above necessarily touch the same local function:

```text
ReviewState vocabulary and transition authority
semantic acceptance non-authoritative
FINAL_PASS only after CERTIFIED
SUPERSEDED review cannot FINAL_PASS
ProofRecord fingerprint/carry-forward semantics
RiskEvidence and deterministic ReviewEffort routing
exact certification candidate binding
terminal-state reentry blocking
provider-neutral no-model-polling contract
pure/no-I/O module boundary
live Bridge/publication/validation/merge flow unchanged
TASK-087/P2/P3/H5-H8 unopened
roadmap v1.2 binding and exact branch lineage
```

## Validation

Run focused tests for the two changed modules and directly impacted tests. Do not run or schedule an executor-owned full canonical T2. Existing certification boundary remains the sole T2 owner under the current live flow.

Truthful telemetry only; do not invent targeted counts.

## Decision

```text
TASK-089: CHANGES_REQUIRED
OPEN_FINDINGS: B1 B2 B3
AUTO_RETRY: NO
AUTO_REROUTE: NO
LIVE_FLOW_CUTOVER: NO
TASK_087_IMPLEMENTATION: NO
P1_COMPLETE: NO
NEXT: FIX TASK-089
```
