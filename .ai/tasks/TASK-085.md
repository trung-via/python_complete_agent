# TASK-085 — P1.0 Transactional Worker Flow + Fix Recovery

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS BRIDGE LEAN EXECUTION / P1.0 FLOW HARDENING
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

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.1","roadmap_blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c","roadmap_fingerprint":"4bcbb10e1e8e02169ccb5a516801abd1ce01b0b5edd348d90abcac7d0887404f","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R1"],"scope_in":["P1 prerequisite hardening of the unified worker transaction before capability batching","single-command RUN/FIX control synchronization exact artifact resolution and authority continuation","closed FIX execution modes IMPLEMENTATION and EVIDENCE_REFRESH","bounded clean/no-op/timeout failure classification with deterministic next action","provider-neutral operator semantics for Codex and Antigravity while preserving P0 validation ownership"],"scope_out":["P1 capability batch container or integration lane implementation","P1 impact dependency engine","Python Agent fast-lane pilot","P2 persistent session checkpoint resume capacity suspension or shell interception","P3 Claude Code adapter adaptive executor routing","automatic retry or automatic reroute","H5-H8 implementation","roadmap requirement identity changes","authorization lease or reviewed-head merge redesign"]}

## Baseline

```text
MAIN_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
TARGET_BRANCH: ai/task-085
TASK_083_STATUS: PASS_MERGED
P0_FORMAL_COMPLETION: YES
P0_COMPLETION_RECORD_FINGERPRINT: a9b6b2c9664659ec7444f9eb8c2a05bfe9b40eb4b620ed1c00cb3cf18dd3dbfd
P1_PREREQUISITE_OPEN: YES
P2_P3_STATUS: NOT_AUTHORIZED
H5_STATUS: PAUSED_NOT_AUTHORIZED
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"b7256b572469ac89db8808c88b8cd880e67cd7b6"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"52f4f24a6b0af719886c6524ade8e19f8cc8984c"},{"path":".ai/decisions/ADR-060-AIOS-P0-MANAGED-VALIDATION-OBSERVABILITY-BOUNDARY-CONTRACT.md","blob_sha":"3a0b9bca86b0cf1aad4ec066e3e9a4089450f6ae"},{"path":".ai/decisions/ADR-061-AIOS-P1.0-TRANSACTIONAL-WORKER-FLOW-FIX-RECOVERY-CONTRACT.md","blob_sha":"b456d80befff7aeec0d3a0217e03a9834f71d7f8"},{"path":".ai/reviews/REVIEW-083.md","blob_sha":"767af7217ad6679f02bec83ec380c80098b4374f"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_flow.py","src/aios_bridge/executor_automation.py",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/skills/aios-worker/SKILL.md",".agents/workflows/aios-worker.md","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge.py","tests/test_bridge_executor_automation.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Implement ADR-061 as a bounded P1.0 prerequisite before capability batching. The user-facing invariant is:

```text
$aios-worker RUN TASK-N
or
$aios-worker FIX TASK-N
        ↓
AIOS handles required sync/preflight/continuation
```

`STATUS` must remain optional diagnostics, not an operator prerequisite.

This task hardens the transaction surrounding P0 validation semantics. It does NOT implement capability batching and does NOT claim P1 complete.

## 1. Transactional RUN/FIX

Preserve the existing P0 rule that Bridge `handoff` performs read-only synchronization before authority. Build one shared worker-flow coordinator/contract so the unified worker surface does not require a separate STATUS/sync command.

Required behavior:

```text
RUN/FIX operator intent
→ read-only control sync
→ latest exact TASK/REVIEW resolution
→ preflight
→ authorization/lease
→ mode-appropriate continuation
→ certification/publication when eligible
```

Rules:

```text
STATUS_REQUIRED_BEFORE_RUN: NO
STATUS_REQUIRED_BEFORE_FIX: NO
STATUS_CREATES_AUTHORITY: NO
SYNC_CREATES_AUTHORITY: NO
SYNC_FAILURE_BLOCKS_PREAUTH: YES
HANDOFF_REMAINS_AUTHORITY_BOUNDARY: YES
```

Do not add a second independent synchronization authority. Reuse the canonical Bridge synchronization semantics and make the outer transaction/provider adapters consume it correctly.

## 2. Exact Latest REVIEW Re-resolution

A FIX invocation after ChatGPT updates REVIEW-N must consume the latest synchronized exact REVIEW blob within the same transaction.

Regression scenario:

```text
FIX attempt A fails preauthorization because review artifact is invalid/stale
ChatGPT replaces REVIEW-N on ai-control
operator runs only: $aios-worker FIX TASK-N
→ transaction syncs
→ binds new exact review blob
→ preflight continues
```

No STATUS command may be required between those steps.

If the control artifact changes after synchronization but before authorization, fail closed and emit one deterministic next action.

## 3. Closed FIX Execution Mode

Implement a bounded closed type equivalent to:

```text
FixExecutionMode:
  IMPLEMENTATION
  EVIDENCE_REFRESH
```

Authoritative review marker should be explicit and machine-readable. Compatibility rule:

```text
missing marker → IMPLEMENTATION
unknown marker → FAIL CLOSED
EVIDENCE_REFRESH → only when explicitly authorized by exact REVIEW
```

Do not infer evidence refresh merely because the executor returns no delta.

## 4. IMPLEMENTATION Mode

For IMPLEMENTATION:

```text
bounded executor required
productive allowed delta → existing certification/publication path
EXITED_ZERO + clean delta → CLEAN_NO_WORKTREE_DELTA
failed certification → fail closed
```

`CLEAN_NO_WORKTREE_DELTA` remains a blocker in IMPLEMENTATION mode. The system must emit a deterministic next action rather than encouraging repeated blind execute calls.

## 5. EVIDENCE_REFRESH Mode

For explicitly authorized EVIDENCE_REFRESH:

```text
fresh FIX authorization
exact reviewed head required
clean worktree required
bounded executor invocation = 0
canonical T2 certification = exactly 1
RESULT republished with current Bridge renderer
```

Required evidence:

```text
FIX_EXECUTION_MODE: EVIDENCE_REFRESH
EXECUTOR_INVOCATION_COUNT: 0
FULL_CANONICAL_OWNER: CERTIFICATION_BOUNDARY
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
```

This must be reachable through the normal `$aios-worker FIX TASK-N` operator surface; the user must not manually compose `handoff` and `publish`.

## 6. Timeout / Failure Classification

Introduce deterministic bounded classifications equivalent to:

```text
PREAUTH_ARTIFACT_INVALID
CLEAN_NO_WORKTREE_DELTA
CLEAN_TIMEOUT
DIRTY_TIMEOUT_RECOVERY_REQUIRED
PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
CERTIFICATION_FAILED
```

### CLEAN_TIMEOUT

If bounded execution times out and the worktree contains no preserved implementation delta:

```text
PRESERVED_DELTA: NO
AUTO_RETRY: NO
AUTO_REROUTE: NO
STALE_EXECUTION_AUTHORITY_REUSED: NO
NEXT_ACTION: one explicit Human rerun action
```

The operator must not need to run `git status`, manually inspect three commands, or call `bridge.py execute` with a guessed timeout merely to discover that no work exists.

### DIRTY_TIMEOUT_RECOVERY_REQUIRED

If timeout leaves allowed dirty paths:

```text
PRESERVED_DELTA: YES
STATE: RECOVERY_REQUIRED
NEW_EXECUTOR_START: BLOCKED
AUTO_RETRY: NO
AUTO_REROUTE: NO
```

Preserve exact worktree evidence. Do not implement P2 resume/session semantics in this task.

Existing ADR-047 productive non-zero recovery semantics remain unchanged.

## 7. Deterministic Next Action

Every non-success terminal worker transaction must emit exactly one bounded next-action code and a human-readable action.

At minimum cover:

```text
RETRY_FIX_BY_HUMAN
CORRECT_CONTROL_ARTIFACT
RECOVERY_REQUIRED_PRESERVED_DELTA
REVIEW_TASK
```

The system may distinguish additional bounded states if needed, but must not emit ambiguous multi-step operator recipes as the normal path.

## 8. Provider-Neutral Policy Parity

Shared semantics must apply to Codex and Antigravity:

```text
sync/preflight semantics: same
latest review binding: same
fix mode parser: same
failure classification: same
next-action vocabulary: same
P0 validation ownership: same
```

Transport continuation may remain:

```text
Codex → managed bounded process
Antigravity → interactive attached session
```

Do not introduce Claude transport, persistent sessions, checkpoint/resume, or shell interception.

## 9. Required Targeted / Impact Tests

Executor runs only targeted/impact tests and diff check. Certification boundary owns T2 full repository exactly once.

Required proofs:

```text
P0_COMPLETION_PREREQUISITE: PASS
RUN_WITHOUT_STATUS_AUTO_SYNCS: PASS
FIX_WITHOUT_STATUS_AUTO_SYNCS: PASS
LATEST_REVIEW_REVISION_CONSUMED: PASS
SYNC_FAILURE_PREVENTS_AUTHORIZATION: PASS
STATUS_REMAINS_NON_AUTHORIZING: PASS
FIX_MODE_CLOSED: PASS
LEGACY_FIX_DEFAULT_IMPLEMENTATION: PASS
UNKNOWN_FIX_MODE_FAILS_CLOSED: PASS
EVIDENCE_REFRESH_SKIPS_EXECUTOR: PASS
EVIDENCE_REFRESH_REQUIRES_CLEAN_REVIEWED_HEAD: PASS
EVIDENCE_REFRESH_T2_EXACTLY_ONCE: PASS
IMPLEMENTATION_CLEAN_NOOP_BLOCKS: PASS
CLEAN_TIMEOUT_CLASSIFIED_WITHOUT_MANUAL_GIT_INSPECTION: PASS
DIRTY_TIMEOUT_PRESERVES_DELTA: PASS
PRODUCTIVE_NONZERO_RECOVERY_UNCHANGED: PASS
ONE_DETERMINISTIC_NEXT_ACTION: PASS
CODEX_ANTIGRAVITY_POLICY_PARITY: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
P2_P3_NOT_IMPLEMENTED: PASS
H5_NOT_OPENED: PASS
```

## 10. Certification

Canonical certification remains:

```text
VALIDATION_PROFILE: CONTROL_PLANE_STRICT_COMPAT
T2_OWNER: CERTIFICATION_BOUNDARY
FULL_REPOSITORY: .\venv\Scripts\python.exe -m pytest tests/ -q
AIOS_MANAGED_T2_EXPECTED: 1
```

Do not run a second executor-owned full repository suite.

## Acceptance

TASK-085 passes only if:

```text
P1_0_TRANSACTIONAL_WORKER_FLOW: PASS
STATUS_NOT_PREREQUISITE: PASS
FIX_MODE_CONTRACT: PASS
EVIDENCE_REFRESH_NORMAL_SURFACE: PASS
CLEAN_TIMEOUT_ACTIONABLE: PASS
DIRTY_TIMEOUT_FAILS_CLOSED_WITH_PRESERVATION: PASS
HUMAN_ATTENTION_REDUCED_TO_SINGLE_NORMAL_COMMAND: PASS
P0_VALIDATION_SEMANTICS_PRESERVED: PASS
CONTROL_PLANE_AUTHORITY_UNCHANGED: PASS
P1_CAPABILITY_BATCH_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_NOT_OPENED: PASS
```

Passing TASK-085 does not complete P1.R1 by itself; it is prerequisite flow hardening before the P1 validation-profile/capability-batch task.