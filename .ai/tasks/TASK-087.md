# TASK-087 — P1.0B Failure Classification + Deterministic Next Action

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1.0B FAILURE RECOVERY CLASSIFICATION
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
IMPLEMENTATION_REFINEMENT_ADR: ADR-061
DECOMPOSITION_ADR: ADR-062
LEAN_REVIEW_ACTIVATION_ADR: ADR-065
TASK_086_PREREQUISITE: PASS_MERGED
TASK_092_PREREQUISITE: PASS_CERTIFIED_MERGED
TASK_087_REBOUND_FROM_RESERVED: YES
LEAN_REVIEW_SLICES_A_D_COMPLETE: YES
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R1"],"scope_in":["P1.0B bounded worker failure classification required before capability batching","closed provider-neutral classification for clean no-op, clean timeout, dirty timeout recovery-required, and productive nonzero recovery candidate","one deterministic machine-readable next action for every classified blocked execution","preservation of exact worktree/head/provenance evidence used by recovery classification","integration with existing structured clean-no-op blocker evidence and explicit-Human replacement semantics already on main","preservation of Review-First Certification, Slice-C FIX proof reuse, roadmap/lease/scope/publication/reviewed-head/merge safety"],"scope_out":["P1 capability batch container implementation","P1 bounded integration lane implementation","Python Agent fast-lane pilot","persistent executor sessions","checkpoint/resume","shell interception","capacity suspension","automatic executor retry","automatic executor reroute","automatic continuation after timeout","cross-executor automatic failover","new background daemon","P2","P3","H5-H8","paid API calls","canonical roadmap mutation"]}

## Exact Baseline

```text
MAIN_SHA: ac0ae79e85e30a80410380188578db1993720b5b
TARGET_BRANCH: ai/task-087
TASK_086: PASS_MERGED
TASK_092: PASS_CERTIFIED_MERGED
LEAN_REVIEW_SLICES_A_D: COMPLETE
ROADMAP_V1_2: LOCKED_REGISTERED
REVIEW_FIRST_CERTIFICATION_ON_MAIN: YES
FIX_PROOF_REUSE_DELTA_IMPACT_ON_MAIN: YES
P1_FORMAL_COMPLETION: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

### Baseline missing guard

The following required P1.0B implementation is ABSENT on the exact baseline and therefore a clean no-op is not a valid successful implementation:

```text
src/aios_bridge/worker_failure.py: ABSENT
CLEAN_TIMEOUT classification contract: ABSENT
DIRTY_TIMEOUT_RECOVERY_REQUIRED classification contract: ABSENT
PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE unified classification contract: ABSENT
closed deterministic next-action model for these classifications: ABSENT
NO_WORK_REQUIRED_ALLOWED: NO
CLEAN_NO_WORKTREE_DELTA_AS_TASK_SUCCESS: NO
```

The executor MUST create a real implementation delta or report a specific blocker. It MUST NOT interpret existing TASK-092 clean-no-op recovery support as satisfying TASK-087.

## Executor Authority Clarification

This TASK is the complete normative implementation instruction for TASK-087. Historical ADR-061, ADR-062 and ADR-065 are provenance explaining why TASK-087 exists; they are NOT executor context for semantic inference and MUST NOT override the post-TASK-092 Review-First lifecycle stated here.

Current authority order for execution is:

```text
canonical roadmap v1.2
  -> exact TASK-087 artifact
  -> current main implementation contracts
```

Do not infer old pre-Review-First EVIDENCE_REFRESH/T2 behavior from historical ADR prose. Candidate RUN/FIX publication for TASK-087 has T2=0; only `certify-reviewed 87` owns final T2.

Passing TASK-087 does NOT complete P1. Capability-batch/integration-lane work and the Python Agent Time-to-Trusted-Capability pilot remain later P1 work.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_flow.py","src/aios_bridge/worker_failure.py","src/aios_bridge/executor_outcome.py",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/skills/aios-worker/SKILL.md",".agents/workflows/aios-worker.md","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Required delivery lifecycle

```text
RUN executor
  -> T0 / bounded targeted T1 / diff check
  -> publish candidate with AIOS-managed T2 count = 0
  -> ChatGPT semantic review
      -> CHANGES_REQUIRED: Slice-C FIX / Delta+Impact / next candidate T2=0
      -> SEMANTICALLY_ACCEPTED_PENDING_T2
  -> bridge.py certify-reviewed 87
      -> full canonical T2 exactly once for exact accepted candidate
  -> bridge.py merge-reviewed 87
```

## 1. Required pure failure contract

MUST create `src/aios_bridge/worker_failure.py` unless an equivalent new pure module is strictly necessary within the allowed paths. Prefer the named file.

Define closed provider-neutral types sufficient to represent:

```text
WorkerFailureClass:
  CLEAN_NO_WORKTREE_DELTA
  CLEAN_TIMEOUT
  DIRTY_TIMEOUT_RECOVERY_REQUIRED
  PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE

WorkerNextAction:
  HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE
  HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT
  RECOVERY_REQUIRED_PRESERVED_DELTA
```

A pure classifier must consume only bounded deterministic evidence such as invocation terminal status, pre/post head, dirty paths, authorized-scope result, and known-terminal/stopped status. Raw model reasoning is forbidden as authority input.

## 2. Classification semantics

### CLEAN_NO_WORKTREE_DELTA

```text
terminal/stopped execution
post_head == pre_head
worktree delta == empty
-> CLEAN_NO_WORKTREE_DELTA
-> next_action = HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE
-> no RESULT publication
-> no auto retry/reroute
```

Preserve TASK-092 structured blocker evidence and explicit-Human safe replacement semantics.

### CLEAN_TIMEOUT

Only transport terminal status `TIMED_OUT` may establish timeout classification.

```text
TIMED_OUT + known stopped/terminal
post_head == pre_head
worktree delta == empty
-> CLEAN_TIMEOUT
-> next_action = HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT
-> no RESULT publication
-> no stale authority reuse
-> no auto retry/reroute
```

Elapsed wall-clock alone is insufficient.

### DIRTY_TIMEOUT_RECOVERY_REQUIRED

```text
TIMED_OUT + known stopped/terminal
AND (dirty delta exists OR post_head != pre_head)
-> DIRTY_TIMEOUT_RECOVERY_REQUIRED
-> next_action = RECOVERY_REQUIRED_PRESERVED_DELTA
```

Preserve exact delta/head/scope evidence. Do not reset, clean, stash, commit, retry, reroute, or fabricate a published/consumed boundary.

### PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE

`EXITED_NONZERO` may produce this class only if an actual preserved delta exists and existing strict branch/head/allowed-path provenance checks pass. Nonzero alone is insufficient. Out-of-scope or uncertain evidence remains fail-closed.

## 3. Normal worker integration

Integrate the closed classification and exactly one `next_action` into the normal `$aios-worker RUN/FIX` blocked execution path where terminal facts are available.

Required:

```text
machine classification visible in bounded output/state
exactly one machine next_action for owned blocked classes
human text derived from the same next_action
no manual git status/diff needed as normal discovery
Codex and Antigravity share classification policy
Antigravity does not fabricate timeout status it cannot observe
```

Do not redesign preauthorization, certification, merge, or persistent session behavior.

## 4. Required targeted proofs

At minimum:

```text
BASELINE_MISSING_GUARD_PROVEN: PASS
WORKER_FAILURE_MODULE_CREATED: PASS
CLEAN_NO_WORKTREE_DELTA_CLASSIFIED: PASS
CLEAN_NO_WORKTREE_DELTA_NEXT_ACTION_SINGLE: PASS
CLEAN_TIMEOUT_CLASSIFIED_FROM_TERMINAL_TIMEOUT: PASS
CLEAN_TIMEOUT_REQUIRES_ZERO_DELTA: PASS
CLEAN_TIMEOUT_NO_RESULT_PUBLICATION: PASS
DIRTY_TIMEOUT_RECOVERY_REQUIRED_CLASSIFIED: PASS
DIRTY_TIMEOUT_PRESERVES_WORKTREE: PASS
DIRTY_TIMEOUT_BLOCKS_FRESH_EXECUTOR_START: PASS
DIRTY_TIMEOUT_DOES_NOT_AUTO_RESET_STASH_COMMIT: PASS
PRODUCTIVE_NONZERO_REQUIRES_PRESERVED_AUTHORIZED_DELTA: PASS
PRODUCTIVE_NONZERO_OUT_OF_SCOPE_FAILS_CLOSED: PASS
ONE_MACHINE_NEXT_ACTION_PER_BLOCKED_CLASSIFICATION: PASS
HUMAN_TEXT_DERIVED_FROM_MACHINE_NEXT_ACTION: PASS
CODEX_ANTIGRAVITY_CLASSIFICATION_POLICY_PARITY: PASS
TASK_092_BLOCKED_REPLACEMENT_NOT_REGRESSED: PASS
REVIEW_FIRST_CANDIDATE_T2_ZERO: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
P1_CAPABILITY_BATCH_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

Executor runs targeted/impact tests and diff check only. Do not run full canonical T2 during candidate publication.

## Explicit out of scope

```text
roadmap mutation
P1 completion declaration
capability batch container / integration lane
Python Agent pilot
persistent sessions / checkpoint-resume / capacity suspension / shell interception
automatic retry or reroute
cross-executor automatic continuation
Claude Code integration
P2 / P3 / H5-H8
```

## Certification

```text
VALIDATION_PROFILE: CONTROL_PLANE_STRICT_COMPAT
T2_OWNER: CERTIFICATION_BOUNDARY
FULL_REPOSITORY: .\venv\Scripts\python.exe -m pytest tests/ -q
AIOS_MANAGED_T2_EXPECTED: 1
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXPECTED: 0
```

## Acceptance

```text
P1_0B_FAILURE_CLASSIFICATION: PASS
CLEAN_NO_WORKTREE_DELTA: PASS
CLEAN_TIMEOUT: PASS
DIRTY_TIMEOUT_RECOVERY_REQUIRED: PASS
PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE: PASS
ONE_DETERMINISTIC_NEXT_ACTION: PASS
PROVIDER_NEUTRAL_CLASSIFICATION: PASS
REVIEW_FIRST_CERTIFICATION_PRESERVED: PASS
SLICE_C_FIX_PRESERVED: PASS
TASK PASS != P1 COMPLETE
P1_CAPABILITY_BATCH_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```
