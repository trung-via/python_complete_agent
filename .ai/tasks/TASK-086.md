# TASK-086 — P1.0A Transactional RUN/FIX + Evidence Refresh

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1.0A BOUNDED FLOW
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
IMPLEMENTATION_REFINEMENT_ADR: ADR-061
DECOMPOSITION_ADR: ADR-062

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.1","roadmap_blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c","roadmap_fingerprint":"4bcbb10e1e8e02169ccb5a516801abd1ce01b0b5edd348d90abcac7d0887404f","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R1"],"scope_in":["bounded prerequisite hardening for one-command worker transactions before capability batching","latest exact review synchronization and binding within FIX transaction","closed FIX execution mode IMPLEMENTATION or EVIDENCE_REFRESH","evidence refresh continuation through normal worker surface without bounded executor invocation","provider-neutral Codex and Antigravity operator semantics while preserving P0 validation ownership"],"scope_out":["timeout and recovery classification deferred to TASK-087 after this task merges","P1 capability batch container or integration lane","impact dependency engine","Python Agent fast-lane pilot","P2 persistent sessions checkpoint resume shell interception or capacity suspension","P3 Claude transport or adaptive routing","automatic retry or automatic reroute","H5-H8 implementation","roadmap requirement identity changes","authorization lease or reviewed-head merge redesign"]}

## Baseline

```text
MAIN_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
TARGET_BRANCH: ai/task-086
P0_FORMAL_COMPLETION: YES
TASK_085_DISPOSITION: SUPERSEDED_NO_IMPLEMENTATION
TASK_085_OBSERVED_RUN_WITHOUT_STATUS: PASS
TASK_085_EXECUTOR_OUTCOME: CLEAN_NO_WORKTREE_DELTA
P2_P3_STATUS: NOT_AUTHORIZED
H5_STATUS: PAUSED_NOT_AUTHORIZED
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"b7256b572469ac89db8808c88b8cd880e67cd7b6"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"52f4f24a6b0af719886c6524ade8e19f8cc8984c"},{"path":".ai/decisions/ADR-061-AIOS-P1.0-TRANSACTIONAL-WORKER-FLOW-FIX-RECOVERY-CONTRACT.md","blob_sha":"b456d80befff7aeec0d3a0217e03a9834f71d7f8"},{"path":".ai/decisions/ADR-062-AIOS-P1.0-BOUNDED-SLICE-DECOMPOSITION-AFTER-CLEAN-NOOP.md","blob_sha":"bcdb4f148d731292c776802d858448e99469abe1"},{"path":".ai/reviews/REVIEW-083.md","blob_sha":"767af7217ad6679f02bec83ec380c80098b4374f"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_flow.py",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/skills/aios-worker/SKILL.md",".agents/workflows/aios-worker.md","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Implement only the first bounded slice of ADR-061. After this task, the normal operator contract must be:

```text
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N
```

No prior `$aios-worker STATUS TASK-N` is required. FIX must consume the latest exact synchronized REVIEW and choose a closed execution mode. Explicit EVIDENCE_REFRESH must skip the bounded executor and perform canonical certification/publication through the same normal worker surface.

Timeout/no-op recovery classification beyond existing fail-closed behavior is NOT part of this task; that is TASK-087 after TASK-086 PASS/merge.

## 1. Baseline-Proven Missing Implementation — No-Op Guard

At the bound baseline, these concepts are absent:

```text
src/aios_bridge/worker_flow.py: ABSENT
FixExecutionMode: ABSENT
EVIDENCE_REFRESH: ABSENT
```

Therefore an `EXITED_ZERO + CLEAN_NO_WORKTREE_DELTA` executor outcome CANNOT satisfy this RUN.

Required implementation guard:

```text
MUST_CREATE: src/aios_bridge/worker_flow.py
MUST_DEFINE_CLOSED_FIX_MODE: YES
MUST_ADD_EVIDENCE_REFRESH_NORMAL_SURFACE: YES
NOOP_SUCCESS_ALLOWED: NO
```

If the executor cannot implement these inside authorized paths, it must report a blocker rather than claim completion.

## 2. One Operator Intent / Shared Transaction Contract

Preserve existing Bridge `handoff` synchronization as the read-only pre-authority mechanism. Do not add an independent sync authority.

Create a small provider-neutral worker-flow model/coordinator sufficient to represent:

```text
operator intent
latest synchronized work artifact
handoff/preflight result
selected FIX mode when action=FIX
mode-appropriate continuation
```

Required semantics:

```text
STATUS_REQUIRED_BEFORE_RUN: NO
STATUS_REQUIRED_BEFORE_FIX: NO
SYNC_BEFORE_AUTHORITY: YES
SYNC_CREATES_AUTHORITY: NO
HANDOFF_REMAINS_AUTHORITY_BOUNDARY: YES
```

The unified adapter must expose one normal RUN/FIX command; it must not tell the operator to run STATUS as a preparation step.

## 3. Latest REVIEW Re-resolution

For FIX, the same operator transaction must bind the latest exact REVIEW after synchronization.

Regression:

```text
review revision A exists
ChatGPT replaces it with revision B on ai-control
operator runs only: $aios-worker FIX TASK-N
→ handoff synchronization observes B
→ authorization binds exact B blob
→ no STATUS command is required
```

Artifact drift between sync and authority must still fail closed.

## 4. Closed FIX Mode

Add a closed type equivalent to:

```text
FixExecutionMode:
  IMPLEMENTATION
  EVIDENCE_REFRESH
```

Review marker:

```text
FIX_EXECUTION_MODE: IMPLEMENTATION
or
FIX_EXECUTION_MODE: EVIDENCE_REFRESH
```

Compatibility:

```text
marker missing → IMPLEMENTATION
unknown marker → FAIL_CLOSED
multiple conflicting markers → FAIL_CLOSED
```

Mode is bound to exact REVIEW evidence and persisted with authorization/worker-flow evidence. Do not infer EVIDENCE_REFRESH from a clean executor result.

## 5. IMPLEMENTATION Continuation

For IMPLEMENTATION:

```text
Codex → bounded executor continuation as today
Antigravity → interactive attached continuation as today
```

Existing clean-noop and timeout fail-closed behavior may remain unchanged in this task. Do not implement TASK-087 concerns here.

## 6. EVIDENCE_REFRESH Continuation

For explicit EVIDENCE_REFRESH:

```text
fresh FIX handoff/authorization
exact reviewed task head required
clean worktree required
bounded executor invocation count = 0
canonical T2 certification = exactly 1
RESULT publication = normal canonical Bridge publication
```

The normal operator command must be sufficient:

```text
$aios-worker FIX TASK-N
```

The user must NOT need to manually compose:

```text
bridge.py handoff
bridge.py publish
```

Provider-neutral requirement: EVIDENCE_REFRESH skips implementation executor work for both Codex-selected and Antigravity-selected FIX transactions because the review explicitly declares there is no implementation work.

## 7. P0 Validation Preservation

Required evidence for evidence refresh:

```text
FIX_EXECUTION_MODE: EVIDENCE_REFRESH
EXECUTOR_INVOCATION_COUNT: 0
FULL_CANONICAL_OWNER: CERTIFICATION_BOUNDARY
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
```

Unavailable ad-hoc/global/targeted observations remain UNKNOWN per ADR-060. Do not reintroduce ambiguous counts.

## 8. Required Targeted / Impact Tests

Executor runs only targeted/impact tests and diff check. Certification boundary owns T2 once.

Required proofs:

```text
BASELINE_MISSING_GUARD_PROVEN: PASS
WORKER_FLOW_MODULE_CREATED: PASS
RUN_WITHOUT_STATUS_AUTO_SYNCS: PASS
FIX_WITHOUT_STATUS_AUTO_SYNCS: PASS
LATEST_REVIEW_REVISION_CONSUMED: PASS
SYNC_FAILURE_PREVENTS_AUTHORIZATION: PASS
STATUS_REMAINS_NON_AUTHORIZING: PASS
FIX_MODE_CLOSED: PASS
LEGACY_FIX_DEFAULT_IMPLEMENTATION: PASS
UNKNOWN_FIX_MODE_FAILS_CLOSED: PASS
CONFLICTING_FIX_MODE_FAILS_CLOSED: PASS
FIX_MODE_BOUND_TO_EXACT_REVIEW: PASS
IMPLEMENTATION_MODE_CODEX_CONTINUATION_PRESERVED: PASS
IMPLEMENTATION_MODE_ANTIGRAVITY_CONTINUATION_PRESERVED: PASS
EVIDENCE_REFRESH_SKIPS_EXECUTOR: PASS
EVIDENCE_REFRESH_REQUIRES_CLEAN_REVIEWED_HEAD: PASS
EVIDENCE_REFRESH_T2_EXACTLY_ONCE: PASS
EVIDENCE_REFRESH_PUBLISHES_THROUGH_NORMAL_WORKER_SURFACE: PASS
P0_SCOPED_VALIDATION_EVIDENCE_PRESERVED: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_087_CONCERNS_NOT_IMPLEMENTED: PASS
P2_P3_NOT_IMPLEMENTED: PASS
H5_NOT_OPENED: PASS
```

## 9. Explicit Out of Scope

```text
CLEAN_TIMEOUT classification
DIRTY_TIMEOUT_RECOVERY_REQUIRED classification
new timeout values
persistent sessions
checkpoint/resume
shell interception
capacity suspension
capability batches
integration lane
impact dependency engine
Claude transport
adaptive routing
automatic retry
automatic reroute
H5-H8
```

## Certification

```text
VALIDATION_PROFILE: CONTROL_PLANE_STRICT_COMPAT
T2_OWNER: CERTIFICATION_BOUNDARY
FULL_REPOSITORY: .\venv\Scripts\python.exe -m pytest tests/ -q
AIOS_MANAGED_T2_EXPECTED: 1
```

## Acceptance

TASK-086 passes only if:

```text
P1_0A_TRANSACTIONAL_RUN_FIX: PASS
STATUS_NOT_PREREQUISITE: PASS
LATEST_REVIEW_BINDING: PASS
CLOSED_FIX_MODE: PASS
EVIDENCE_REFRESH_NORMAL_SURFACE: PASS
HUMAN_MANUAL_HANDOFF_PUBLISH_RECIPE_REMOVED_FOR_EVIDENCE_REFRESH: PASS
P0_VALIDATION_SEMANTICS_PRESERVED: PASS
CONTROL_PLANE_AUTHORITY_UNCHANGED: PASS
TASK_087_NOT_IMPLEMENTED: PASS
P1_CAPABILITY_BATCH_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_NOT_OPENED: PASS
```

Passing TASK-086 does not complete P1. TASK-087 may be authored only after TASK-086 PASS/merge and exact-baseline rebinding.
