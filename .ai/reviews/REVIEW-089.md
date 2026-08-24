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
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-089.md","blob_sha":"21b9dee64040c8289be49a33230af9e1b1b7480b"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-065-AIOS-LEAN-REVIEW-PIPELINE-ACTIVATION-BOUNDED-SLICES.md","blob_sha":"947b3ec5b63ddd628838a533822e37499a837a74"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/review_pipeline.py","src/aios_bridge/certification_job.py","tests/aios_bridge/test_review_pipeline.py","tests/aios_bridge/test_certification_job.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: 24cc46839f4bbd8043b0dc15a9426f7658c66064
BASE_MAIN: 90b381d3be78b68a8e7b25c42c66e539486a44e2
CURRENT_MAIN: 90b381d3be78b68a8e7b25c42c66e539486a44e2
AHEAD: 1
BEHIND: 0
MERGE_BASE: 90b381d3be78b68a8e7b25c42c66e539486a44e2
EXECUTOR: codex
T2: 2617 passed, 7 skipped, 0 failed
T2_WARNINGS: 1540
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
```

Scope audit is clean. The executor changed only the four task-authorized implementation/test paths; RESULT-089 was added by the publication boundary. Existing Bridge publication, worker-flow, validation ownership, merge gate, TASK-087, P2/P3, and H5-H8 remain untouched.

## Findings

### B1 — Finding lifecycle conflates failed verification with regression reopening

`review_pipeline.py` currently permits:

```text
VERIFYING -> CLOSED | REOPENED
CLOSED -> REOPENED
```

The locked ADR-064 lifecycle is:

```text
NEW -> OPEN -> FIX_SUBMITTED -> VERIFYING -> CLOSED
                              -> OPEN on failed verification
CLOSED -> REOPENED only on evidence-backed regression/impact
```

`REOPENED` therefore has a distinct meaning: a previously CLOSED finding regressed. A FIX that fails verification has never closed and must return to OPEN, not REOPENED. The current transition graph collapses those two semantic states and would make later Delta/Impact review and finding history ambiguous.

Also make CLOSED records state-consistent: when a finding becomes CLOSED, it must carry closure evidence sufficient to identify the fixing change and closure review (`fixed_by_sha` and `closure_review_round`). The fields may be optional for non-closed lifecycle states, but authoritative CLOSED state must not be constructible without its closure evidence.

Required repair/proofs:

```text
VERIFYING_FAILED -> OPEN
VERIFYING_SUCCESS -> CLOSED
CLOSED -> REOPENED requires explicit reopen evidence
CLOSED requires fixed_by_sha
CLOSED requires closure_review_round
failed verification is not labelled REOPENED
```

Add regression tests for both the transition function and direct/from-dict CLOSED construction.

### B2 — Certification PASS can create authority without terminal certification evidence

`CertificationJob.terminal_result_digest` is accepted as `None` for terminal states. Consequently this succeeds today:

```text
PENDING -> RUNNING -> CERTIFICATION_PASS
```

without supplying any `terminal_result_digest`, after which `creates_certification_authority` is `True`.

That is not fail-closed enough for the certification foundation. ADR-064 defines `terminal_result_digest` as minimum deterministic certification-job evidence; final certification must not create authority when the terminal result proving that certification is absent.

Required repair/proofs:

```text
CERTIFICATION_PASS without terminal_result_digest -> REJECT
CERTIFICATION_PASS with exact 64-hex terminal_result_digest -> ALLOW
from_dict/direct construction cannot create evidence-free PASS authority
CERTIFICATION_FAILED terminal evidence is state-consistent as well
SUPERSEDED remains non-authoritative and cannot PASS
```

Keep the task's general field optionality for pre-terminal states; enforce the stronger invariant when a terminal certification result is claimed.

### B3 — FindingRecord.from_dict is not strict for machine-readable sequence fields

`FindingRecord.from_dict()` currently performs:

```python
affected_surfaces=tuple(data["affected_surfaces"])
required_proof_ids=tuple(data["required_proof_ids"])
```

without first requiring JSON-array/list input. A string with unique valid characters can therefore be coerced into a tuple of one-character surfaces/proof IDs instead of failing closed. This is unsafe for the future authoritative machine-readable finding registry.

Required repair/proofs:

```text
affected_surfaces must be an exact JSON/list sequence before tuple conversion
required_proof_ids must be an exact JSON/list sequence before tuple conversion
string/scalar/mapping inputs -> REJECT
canonical to_dict -> from_dict round trip -> PASS
```

Apply the same strict sequence-input discipline to any new machine-readable sequence parser in these two foundation modules where coercion could silently change meaning.

## Accepted / Do Not Reopen Without Regression

The following surfaces are accepted in Round 1 and should remain closed unless the FIX changes or regresses them:

```text
A1 ReviewState closed vocabulary: ACCEPTED
A2 semantic acceptance is non-authoritative: ACCEPTED
A3 FINAL_PASS transition only from CERTIFIED: ACCEPTED
A4 SUPERSEDED review cannot reach FINAL_PASS: ACCEPTED
A5 ProofRecord immutable fingerprint validation: ACCEPTED
A6 unchanged VALID proof carry-forward: ACCEPTED
A7 changed subject/dependency invalidation: ACCEPTED
A8 malformed current proof fingerprint fail-closed: ACCEPTED
A9 ReviewEffort closed vocabulary and deterministic routing: ACCEPTED
A10 authority/security escalation to CRITICAL_SECOND_REVIEW: ACCEPTED
A11 unknown impact routes DEEP or stronger: ACCEPTED
A12 exact certification candidate head+fingerprint matcher: ACCEPTED
A13 terminal certification state reentry blocked: ACCEPTED
A14 SUPERSEDED certification non-authoritative: ACCEPTED
A15 provider-neutral no-model-polling wait contract: ACCEPTED
A16 pure modules introduce no Git/filesystem/network/model execution: ACCEPTED
A17 current live Bridge/publication/validation/merge flow unchanged: ACCEPTED
A18 TASK-087/P2/P3/H5-H8 remain unopened: ACCEPTED
A19 roadmap v1.2 binding and registered blob identity: ACCEPTED
A20 exact base/main lineage and allowed-path scope: ACCEPTED
```

## Validation / Evidence Audit

The certification boundary ran the full canonical suite exactly once for this candidate:

```text
2617 passed
7 skipped
0 failed
1540 warnings
pytest-reported duration: 284.60s
RESULT telemetry duration: 285.9504485999987s
```

`TARGETED_TEST_EXECUTION_COUNT` is `UNKNOWN` in RESULT-089. Do not invent a targeted count during FIX. This is not the Round-1 blocker because the full canonical run proves the new tests on this exact candidate and current P0 telemetry explicitly permits unavailable executor ad-hoc observability. Preserve truthful `UNKNOWN` until the later evidence/telemetry slice provides a stronger source of truth.

The large raw pytest payload in RESULT-089 is also not reopened here: compact RESULT evidence is explicitly a later ADR-065 slice. Likewise, runtime Review-First T2 ordering and no-model-polling cutover are not required from TASK-089; this slice is contract foundation only.

## FIX Contract

Fix only B1-B3. Keep the delta bounded to the existing four authorized paths.

```text
OPEN_FINDINGS: B1 B2 B3
PROTECTED_ACCEPTED_SURFACES: A1-A20
AUTO_RETRY: NO
AUTO_REROUTE: NO
LIVE_FLOW_CUTOVER: NO
TASK_087_IMPLEMENTATION: NO
P1_COMPLETE: NO
```

Executor should run the focused tests for the two changed contract modules plus any directly impacted tests, then allow the existing certification boundary to perform the canonical T2 under the current live flow.

## Decision

```text
TASK-089: CHANGES_REQUIRED
APPROVED: NO
MERGE_AUTHORIZED: NO
BLOCKERS_REMAINING: 3
NEXT: FIX TASK-089
TASK PASS != P1 COMPLETE
```
