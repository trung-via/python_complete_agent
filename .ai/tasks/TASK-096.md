# TASK-096 — Codex Interactive Executor Parity Recovery

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
BLOCKED_WORK: TASK-095
TASK_095_RESUME_AUTHORIZED: NO
P1_FORMAL_COMPLETION: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R6","P1.R10"],"scope_in":["make normal Codex RUN/FIX use the same visible interactive executor session shape as Antigravity","remove nested bridge.py execute/codex exec from the normal Codex worker happy path","restore compact Slim interactive context for authorized Codex sessions","allow the authorized visible Codex worker session to implement, targeted-test, and invoke canonical publication","preserve all existing authorization/lease/scope/publication/review/certification boundaries","tests proving no normal Codex worker transaction launches bridge execute while legacy transport remains explicit-only"],"scope_out":["TASK-095 implementation","Python Agent pilot","P1 completion","persistent executor session lifecycle","heartbeat/checkpoint/resume/capacity suspension","Claude Code integration","adaptive selection","automatic retry/reroute/rebase","removal of CodexLocalTransport compatibility code","broad Slim R2 cleanup","P2","P3","H5-H8","canonical roadmap mutation"]}

## Exact baseline

```text
MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TARGET_BRANCH: ai/task-096
TASK_094: PASS_CERTIFIED_MERGED
TASK_095: BLOCKED_PENDING_CODEX_PARITY_RECOVERY
ADR_067: ACCEPTED
ROADMAP_V1_2: LOCKED_REGISTERED
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

## Machine-readable E4 inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-067-CODEX-INTERACTIVE-EXECUTOR-PARITY-RECOVERY-LOCK.md","blob_sha":"db17c1b3f4a359c97f2dd59b8c90f7b7acdd7810"}]
EXECUTOR_ALLOWED_PATHS_JSON: [".agents/skills/aios-worker/SKILL.md",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/workflows/aios-worker.md","docs/AIOS_UNIFIED_WORKER_WORKFLOW.md","bridge.py","src/aios_bridge/worker_flow.py","src/aios_bridge/slim_runtime.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/aios_bridge/test_slim_context_cache.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Fix the Codex worker execution architecture before resuming TASK-095. This is a blocking reliability recovery, not P2 session work.

The normal `$aios-worker RUN/FIX` path must stop spawning a second ephemeral Codex process. The visible Codex session selected by the Human must become the bounded implementation executor exactly as the visible Antigravity session already is.

## Required implementation

### A. Worker-flow parity

Change normal RUN behavior from:

```text
Codex: handoff -> bridge execute -> child codex -> publish
Antigravity: handoff -> AUTHORIZED -> same session implements
```

to:

```text
Codex: handoff -> AUTHORIZED -> same visible Codex session implements
Antigravity: handoff -> AUTHORIZED -> same visible Antigravity session implements
```

The shared worker coordinator MUST NOT invoke `bridge.py execute` for a normal Codex RUN.

For FIX/IMPLEMENTATION, the same rule applies: after exact FIX handoff/mode resolution, Codex returns AUTHORIZED to the visible session instead of invoking nested execute.

EVIDENCE_REFRESH behavior may remain non-interactive and unchanged if already correct.

`bridge.py execute` / `CodexLocalTransport` may remain callable only as explicit compatibility/recovery surfaces. Do not delete them in this task.

### B. Codex skill becomes the executor

Update `.agents/skills/aios-worker/SKILL.md` so the visible Codex session:

```text
1. invokes shared adapter with --adapter codex
2. requires AUTHORIZED for RUN/FIX implementation mode
3. obtains the compact canonical interactive context exactly once
4. reads only the exact authorized TASK/REVIEW + bounded semantic refs exposed by Bridge
5. edits only authorized paths
6. runs bounded targeted T0/T1 tests
7. invokes existing canonical Bridge publish using the exact active authorization and targeted test command
8. reports Review TASK-N
```

Remove the old rule that the visible Codex session must never implement. Remove the normal-path requirement to launch a bounded child executor. Do not grant merge authority.

Do not create a new publish adapter/action merely for symmetry. Reuse existing canonical publish.

### C. Slim interactive context parity

Normal authorized Codex currently suppresses compact `cmd_context` because the nested child received its own payload. Remove that suppression.

Both Codex and Antigravity should receive the same compact interactive context fields after authorization:

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

Do NOT restore model-visible machine bookkeeping removed by Slim R0/R1:

```text
MANIFEST_JSON / MANIFEST_SHA256
request/execution/lease fingerprints
roadmap body
machine blob/byte bookkeeping
```

Cross-task context cache protection must remain fail-closed.

### D. Publication and authority

Interactive Codex publication must still pass the existing canonical checks:

```text
ACTIVE exact authorization
ACTIVE exact lease
exact task/review artifact identity
exact task branch/head
allowed paths
publication trust
review-first candidate T2 count rules
post-test branch/head stability
RESULT creation + push
lease consumption/release
```

No new authority source may come from the Codex UI/session.

### E. Failure behavior

Normal Codex worker failures must not silently invoke another Codex child, retry, or reroute.

If the visible session cannot implement, it reports a bounded blocker and stops. Existing Human recovery/replacement remains the authority path.

Do not add watchdogs, polling loops, workflow databases, persistent session stores, or automatic recovery machinery.

## Required tests

Add/update tests proving at minimum:

```text
CODEX_RUN_HANDOFF_RETURNS_AUTHORIZED_WITH_EXECUTOR_INVOCATIONS_0
CODEX_RUN_DOES_NOT_CALL_BRIDGE_EXECUTE
CODEX_FIX_IMPLEMENTATION_RETURNS_AUTHORIZED_WITH_EXECUTOR_INVOCATIONS_0
CODEX_FIX_IMPLEMENTATION_DOES_NOT_CALL_BRIDGE_EXECUTE
ANTIGRAVITY_RUN_BEHAVIOR_UNCHANGED
EVIDENCE_REFRESH_BEHAVIOR_UNCHANGED
CODEX_COMPACT_CONTEXT_AVAILABLE_AFTER_AUTHORIZATION
CODEX_CONTEXT_EQUALS_ANTIGRAVITY_SHAPE_FOR_EQUIVALENT_AUTH
ROADMAP_MACHINE_CONTEXT_STILL_OMITTED_FROM_MODEL
CROSS_TASK_CONTEXT_CACHE_GUARD_PRESERVED
CODEX_SKILL_NO_LONGER_REQUIRES_NESTED_EXECUTOR
CODEX_SKILL_STILL_FORBIDS_MERGE_AND_AUTO_REROUTE
LEGACY_CODEX_LOCAL_TRANSPORT_TESTS_REMAIN_GREEN
```

Executor runs focused tests only. TASK-096 is CONTROL_PLANE_STRICT; full canonical T2 remains exclusively at `certify-reviewed 96` after semantic acceptance.

## Acceptance

```text
NORMAL_CODEX_NESTED_EXECUTE: REMOVED
NORMAL_CODEX_CHILD_CODEX_EXEC: REMOVED
CODEX_INTERACTIVE_IMPLEMENTATION: ENABLED
CODEX_COMPACT_CONTEXT: ENABLED
CODEX_CANONICAL_PUBLISH: ENABLED
ANTIGRAVITY_PARITY: PASS
AUTHORITY_BOUNDARIES_CHANGED: NO
AUTO_RETRY: NO
AUTO_REROUTE: NO
P2_SESSION_LIFECYCLE_IMPLEMENTED: NO
TASK_095_IMPLEMENTED: NO
TASK_095_RESUME_AUTHORIZED_AFTER_096_PASS_MERGE: YES
PYTHON_AGENT_PILOT_IMPLEMENTED: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

## Post-merge real proof

After TASK-096 is reviewed, certified and merged:

1. rebind TASK-095 to the new exact main;
2. set TASK-095 back to READY;
3. run `$aios-worker RUN TASK-095` with Codex;
4. require a non-empty authorized implementation delta and successful publication;
5. if Codex still produces zero delta, stop and audit the visible Codex skill/runtime before any Python Agent pilot.

TASK-095 itself is the real post-merge Codex smoke proof. No synthetic proof runner is authorized.
