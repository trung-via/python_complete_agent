# TASK-097 — Codex Interactive Parity + Publication Safety Lock

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS BRIDGE LEAN EXECUTION / BLOCKING EXECUTOR RELIABILITY RECOVERY
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
VALIDATION_PROFILE: CONTROL_PLANE_STRICT
EXECUTOR_MODE: ANTIGRAVITY_ONLY
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
RECOVERY_CONTRACT_ADR: ADR-067
SUPERSEDES_TASK: TASK-096
BLOCKED_WORK: TASK-095
TASK_095_RESUME_AUTHORIZED: NO
P1_FORMAL_COMPLETION: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R6","P1.R10"],"scope_in":["make normal Codex RUN/FIX use the same visible interactive executor session shape as Antigravity","remove nested bridge.py execute/codex exec from the normal Codex worker happy path","restore compact Slim interactive context for authorized Codex sessions","bind AUTHORIZED continuation guidance to the explicitly selected adapter","make interactive publish derive exact allowed paths from machine-verified active authorization/control evidence","make interactive publish establish and verify publication trust without caller/model authority","preserve exact authorization/lease/review/certification semantics while adding pre-commit scope enforcement","tests proving direct interactive publication rejects out-of-scope dirty paths and protected Git-admin drift"],"scope_out":["TASK-095 implementation","Python Agent pilot","P1 completion","persistent executor session lifecycle","heartbeat/checkpoint/resume/capacity suspension","Claude Code integration","adaptive selection","automatic retry/reroute/rebase","task_authoring preflight relaxation","removal of CodexLocalTransport compatibility code","broad Slim R2 cleanup","P2","P3","H5-H8","canonical roadmap mutation"]}

## Exact baseline

```text
MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TARGET_BRANCH: ai/task-097
TASK_094: PASS_CERTIFIED_MERGED
TASK_095: BLOCKED_PENDING_CODEX_PARITY_RECOVERY
TASK_096: REJECTED_SUPERSEDED
ADR_067: ACCEPTED
ROADMAP_V1_2: LOCKED_REGISTERED
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

## Machine-readable E4 inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-067-CODEX-INTERACTIVE-EXECUTOR-PARITY-RECOVERY-LOCK.md","blob_sha":"db17c1b3f4a359c97f2dd59b8c90f7b7acdd7810"},{"path":".ai/reviews/REVIEW-096.md","blob_sha":"a74493cfd301e463d58fa5cfe1ace9ec2a848357"}]
EXECUTOR_ALLOWED_PATHS_JSON: [".agents/skills/aios-worker/SKILL.md",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/workflows/aios-worker.md","docs/AIOS_UNIFIED_WORKER_WORKFLOW.md","bridge.py","src/aios_bridge/worker_flow.py","src/aios_bridge/slim_runtime.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/aios_bridge/test_slim_context_cache.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Replace contaminated TASK-096 with a clean implementation from certified main. Codex must work like Antigravity on the normal interactive happy path, but this parity must not weaken scope or publication-trust enforcement.

This is a bounded P1 implementation refinement under ADR-067, not P2 executor-session work.

## Required implementation

### A. Clean worker-flow parity

Normal RUN/FIX implementation behavior must be:

```text
Codex:       handoff -> AUTHORIZED -> same visible Codex session implements/tests/publishes
Antigravity: handoff -> AUTHORIZED -> same visible Antigravity session implements/tests/publishes
```

The shared worker coordinator MUST NOT invoke `bridge.py execute` for normal Codex RUN or FIX/IMPLEMENTATION.

EVIDENCE_REFRESH may remain non-interactive and unchanged.

`bridge.py execute` / `CodexLocalTransport` remain explicit compatibility/recovery surfaces only; do not delete them.

### B. Codex skill is the executor

The Codex `$aios-worker` skill must:

```text
1. invoke shared adapter with --adapter codex
2. require AUTHORIZED before implementation
3. continue in the same visible Codex session
4. consume compact canonical interactive context exactly once
5. edit only allowed paths
6. run bounded targeted T0/T1 tests
7. invoke existing canonical bridge.py publish
8. never merge, auto-retry, auto-reroute, or invoke raw/nested codex exec
9. report Review TASK-N after publication
```

### C. Adapter guidance identity

For `AUTHORIZED`, output must bind the selected adapter exactly:

```text
--adapter codex       -> NEXT: continue in the authorized codex worker session
--adapter antigravity -> NEXT: continue in the authorized antigravity worker session
```

No cross-surface wording or executor substitution.

### D. Slim interactive context parity

Both visible executors receive the same compact context shape:

```text
task_id
action
executor_id
current_branch
expected_branch
task_file
review_file when FIX
allowed_paths
semantic_context_files excluding machine-only roadmap prose
interactive_fix_context when applicable
```

Do not restore MANIFEST_JSON/MANIFEST_SHA256, request/execution/lease fingerprints, roadmap prose/body, blob/byte bookkeeping, or duplicate machine context.

Cross-task cache protection remains fail-closed.

### E. Interactive publication scope must be machine-derived

Removing normal Codex `bridge.py execute` removes the old executor-side allowed-path gate. The direct interactive publication path must therefore establish scope itself before commit/push.

For a normal interactive `publish`, Bridge must:

```text
load exact ACTIVE authorization for TASK/action
reconstruct exact expected lease from authorization
require the exact lease ACTIVE
resolve the exact current control snapshot from the authorized artifact
obtain allowed_paths ONLY from that machine-verified snapshot
collect current dirty paths
validate dirty paths against exact allowed_paths before running/committing publication
pass the same exact allowed_paths into the existing post-test publication scope check
fail closed on missing/stale/drifted authorization, lease, artifact, policy, roadmap, branch/head, or scope evidence
```

Do not accept model prose, session state, CLI free-form scope, or caller-supplied path lists as authority.

The implementation should be subtractive/minimal: prefer a root Slim façade wrapper around existing canonical `cmd_publish` / existing helpers rather than duplicating publication logic or mutating `legacy_bridge.py`.

### F. Interactive publication trust must be machine-established

Direct interactive publish must not merely label `publication_trust_status=VERIFIED` without a verified snapshot.

Before tests/commit/push, Bridge must establish the existing publication-trust snapshot using exact Git-admin evidence, then pass it into the existing canonical publish path so the post-test trust revalidation runs.

Required behavior:

```text
capture exact publication trust before publication tests
verify via existing canonical trust checker after tests
Git-admin drift -> fail closed, preserve work, no commit/push
RESULT may say publication_trust_status=VERIFIED only when this path actually ran successfully
```

Reuse existing trust primitives. Do not create a new trust model.

### G. Do not relax task/review authoring

`src/aios_bridge/task_authoring.py` is intentionally NOT authorized.

The TASK-096 Round-2 mutation of task-authoring preflight was compensation for a malformed REVIEW-096 Round 1 and must not be recreated. Canonical FIX reviews must carry their own required machine markers and FIX dispatch policy; reviewer authoring is responsible for that.

### H. Failure behavior

No nested fallback, retry, reroute, rebase, conflict resolution, watchdog, polling loop, workflow database, or new session store.

If the visible executor cannot implement, it stops with bounded blocker evidence; Human replacement remains explicit.

## Required tests

At minimum prove:

```text
CODEX_RUN_HANDOFF_RETURNS_AUTHORIZED_WITH_EXECUTOR_INVOCATIONS_0
CODEX_RUN_DOES_NOT_CALL_BRIDGE_EXECUTE
CODEX_FIX_IMPLEMENTATION_RETURNS_AUTHORIZED_WITH_EXECUTOR_INVOCATIONS_0
CODEX_FIX_IMPLEMENTATION_DOES_NOT_CALL_BRIDGE_EXECUTE
ANTIGRAVITY_RUN_BEHAVIOR_UNCHANGED
EVIDENCE_REFRESH_BEHAVIOR_UNCHANGED
CODEX_AUTHORIZED_GUIDANCE_BINDS_CODEX
ANTIGRAVITY_AUTHORIZED_GUIDANCE_BINDS_ANTIGRAVITY
CROSS_SURFACE_GUIDANCE_CONFUSION: NONE
CODEX_COMPACT_CONTEXT_AVAILABLE_AFTER_AUTHORIZATION
CODEX_CONTEXT_EQUALS_ANTIGRAVITY_SHAPE_FOR_EQUIVALENT_AUTH
ROADMAP_MACHINE_CONTEXT_STILL_OMITTED_FROM_MODEL
CROSS_TASK_CONTEXT_CACHE_GUARD_PRESERVED
INTERACTIVE_PUBLISH_DERIVES_ALLOWED_PATHS_FROM_EXACT_AUTH_SNAPSHOT
INTERACTIVE_PUBLISH_REJECTS_OUT_OF_SCOPE_DIRTY_PATH
INTERACTIVE_PUBLISH_REJECTS_STALE_OR_MISSING_LEASE
INTERACTIVE_PUBLISH_REJECTS_AUTH_ARTIFACT_DRIFT
INTERACTIVE_PUBLISH_PASSES_EXACT_SCOPE_TO_POST_TEST_GATE
INTERACTIVE_PUBLISH_CAPTURES_PUBLICATION_TRUST
INTERACTIVE_PUBLISH_REJECTS_POST_TEST_GIT_ADMIN_DRIFT
PUBLICATION_TRUST_VERIFIED_NOT_UNCONDITIONAL
CODEX_SKILL_NO_LONGER_REQUIRES_NESTED_EXECUTOR
CODEX_SKILL_STILL_FORBIDS_MERGE_AND_AUTO_REROUTE
TASK_AUTHORING_UNCHANGED
LEGACY_CODEX_LOCAL_TRANSPORT_TESTS_REMAIN_GREEN
```

Executor runs focused tests only. TASK-097 is CONTROL_PLANE_STRICT; candidate-stage T2 must remain 0. Full canonical T2 is exclusively `bridge.py certify-reviewed 97` after semantic acceptance.

## Acceptance

```text
NORMAL_CODEX_NESTED_EXECUTE: REMOVED
NORMAL_CODEX_CHILD_CODEX_EXEC: REMOVED
CODEX_INTERACTIVE_IMPLEMENTATION: ENABLED
CODEX_COMPACT_CONTEXT: ENABLED
CODEX_CANONICAL_PUBLISH: ENABLED
INTERACTIVE_ALLOWED_PATH_AUTHORITY: MACHINE_DERIVED
OUT_OF_SCOPE_INTERACTIVE_PUBLICATION: REJECTED
INTERACTIVE_PUBLICATION_TRUST: VERIFIED_BY_EXISTING_PRIMITIVES
FALSE_VERIFIED_PUBLICATION_TRUST: FORBIDDEN
ANTIGRAVITY_PARITY: PASS
AUTHORITY_BOUNDARIES_WEAKENED: NO
TASK_AUTHORING_RELAXATION: NO
AUTO_RETRY: NO
AUTO_REROUTE: NO
P2_SESSION_LIFECYCLE_IMPLEMENTED: NO
TASK_095_IMPLEMENTED: NO
TASK_095_RESUME_AUTHORIZED_AFTER_097_PASS_MERGE: YES
PYTHON_AGENT_PILOT_IMPLEMENTED: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

## Delivery lifecycle

```text
Antigravity RUN TASK-097
-> focused T0/T1
-> publish with candidate T2=0
-> ChatGPT semantic review
-> certify-reviewed 97 (full canonical T2 exactly once)
-> merge-reviewed 97
-> rebind TASK-095 to new main
-> $aios-worker RUN TASK-095 with Codex as real smoke proof
```

TASK-095 remains blocked until TASK-097 is PASS_CERTIFIED_MERGED.
