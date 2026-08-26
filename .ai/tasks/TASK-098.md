# TASK-098 — AIOS Bridge Kernel v1 Candidate Path Bootstrap

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS BRIDGE KERNEL REBUILD / CANDIDATE PATH BOOTSTRAP
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
VALIDATION_PROFILE: CONTROL_PLANE_STRICT
EXECUTOR_MODE: ANTIGRAVITY_ONLY
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
KERNEL_ADR: ADR-068
SUPERSEDES_NORMAL_RECOVERY_WORK: TASK-096,TASK-097
BLOCKED_WORK: TASK-095
TASK_095_RESUME_AUTHORIZED: NO
KERNEL_DEFAULT_CUTOVER_AUTHORIZED: NO
NEXT_KERNEL_TASK: TASK-099_REVIEW_CERTIFY_MERGE
P1_FORMAL_COMPLETION: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R6","P1.R10"],"scope_in":["implement Kernel v1 candidate path AUTHORIZE-EXECUTE-VERIFY-PUBLISH alongside legacy Bridge","same visible Codex/Antigravity executor shape","authoritative T0/T1 exactly once at Kernel complete boundary","synchronous command wait with zero model-driven polling","machine-derived exact scope and publication authority","minimal atomic authorization state","parallel kernel worker surfaces for later smoke testing"],"scope_out":["Kernel REVIEW/CERTIFY/MERGE commands","patching TASK-097","TASK-095 implementation","PRODUCT_DELIVERY_FAST implementation","Python Agent pilot","default worker cutover","legacy Bridge deletion","EVIDENCE_REFRESH","nested Codex transport","automatic retry/reroute/rebase/conflict resolution","persistent sessions","heartbeat/checkpoint/resume","workflow database","P2","P3","H5-H8","roadmap mutation"]}

## Exact baseline

```text
MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TARGET_BRANCH: ai/task-098
TASK_094: PASS_CERTIFIED_MERGED
TASK_095: BLOCKED_PENDING_KERNEL_REBUILD
TASK_096: SUPERSEDED
TASK_097: SUPERSEDED
ADR_068: ACCEPTED
ROADMAP_V1_2: LOCKED_REGISTERED
KERNEL_DEFAULT_CUTOVER: NO
```

## Machine-readable E4 inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-068-AIOS-BRIDGE-KERNEL-V1-EXECUTION-LIFECYCLE-LOCK.md","blob_sha":"1778dde9dc5efcb43ad8b07053436696cec5d1bb"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py","src/aios_bridge/kernel/__init__.py","src/aios_bridge/kernel/model.py","src/aios_bridge/kernel/gitops.py","src/aios_bridge/kernel/authority.py","src/aios_bridge/kernel/context.py","src/aios_bridge/kernel/verify.py","src/aios_bridge/kernel/publish.py","src/aios_bridge/kernel/cli.py",".agents/skills/aios-kernel-worker/SKILL.md",".agents/skills/aios-kernel-worker/scripts/aios_kernel_worker.py",".agents/workflows/aios-kernel-worker.md","docs/AIOS_BRIDGE_KERNEL_V1.md",".gitignore","tests/aios_bridge/kernel/test_model.py","tests/aios_bridge/kernel/test_authority.py","tests/aios_bridge/kernel/test_context.py","tests/aios_bridge/kernel/test_verify.py","tests/aios_bridge/kernel/test_publish.py","tests/aios_bridge/kernel/test_cli.py","tests/test_aios_kernel.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

KERNEL_VERIFY_COMMAND_JSON: {"t0":["venv/Scripts/python.exe","-m","pytest","tests/aios_bridge/kernel/test_model.py","tests/aios_bridge/kernel/test_authority.py","tests/aios_bridge/kernel/test_context.py","-q"],"t1":["venv/Scripts/python.exe","-m","pytest","tests/aios_bridge/kernel/test_verify.py","tests/aios_bridge/kernel/test_publish.py","tests/aios_bridge/kernel/test_cli.py","tests/test_aios_kernel.py","-q"]}

## Purpose

Implement only the first four stages of ADR-068 as a small independent kernel:

```text
AUTHORIZE -> EXECUTE -> VERIFY -> PUBLISH
```

Do not implement REVIEW/CERTIFY/MERGE in this task. Those become TASK-099 only after TASK-098 is reviewed, certified and merged through the old Bridge.

The old Bridge is bootstrap transport only. Do not patch its normal execution path.

## A. Isolated Kernel package

Create `src/aios_bridge/kernel/` without importing normal orchestration from:

```text
src/aios_bridge/worker_flow.py
src/aios_bridge/executor_transports/codex_local.py
src/aios_bridge/legacy_bridge.py
root bridge.py wrappers
```

Small pure parsing/Git helpers may be reused only if they do not import the old state machine.

`aios_kernel.py` is a thin entry point to `src.aios_bridge.kernel.cli`.

## B. Closed commands in TASK-098

Implement exactly:

```text
status TASK-N
authorize TASK-N --action run|fix --executor codex|antigravity
context TASK-N
complete TASK-N
cancel TASK-N
```

No `execute` command. No model launch command. No certify or merge command yet.

## C. AUTHORIZE

`authorize` must:

```text
fetch exact ai-control TASK
for FIX also fetch exact CHANGES_REQUIRED REVIEW
require Human-selected executor exact
require clean/safe branch preparation from exact remote main
parse allowed_paths only from exact TASK
parse KERNEL_VERIFY_COMMAND_JSON only from exact TASK
persist one minimal atomic authorization record outside Git tracking
emit compact context
```

RUN and FIX differ only in authority input. After authorization both use identical downstream behavior.

## D. EXECUTE

The selected visible session is the executor.

```text
Codex       = same visible Codex session
Antigravity = same visible Antigravity session
```

Executor may edit only allowed paths. It must not launch another model, merge, reroute, or run the canonical T0/T1 suite manually.

Optional ad-hoc debugging tests are allowed only when strictly narrower than the canonical suite and are non-authoritative.

## E. VERIFY + PUBLISH = `complete`

`complete` is the only authoritative candidate verification/publication boundary.

Before any test:

```text
require exact AUTHORIZED record
require exact executor/action/task/review/base/branch binding
require non-empty worktree delta
require every changed path subset of exact TASK allowed_paths
require remote main still equals authorized base
```

Then run:

```text
canonical T0 exactly once
canonical T1 exactly once
```

Commands come only from exact `KERNEL_VERIFY_COMMAND_JSON` captured at AUTHORIZE.

Use synchronous foreground subprocess waiting:

```text
launch once -> wait same process -> collect exit once
```

No timer, polling loop, periodic model wake-up or repeated completion prompt exists in Kernel.

If T0/T1 fails:

```text
status -> BLOCKED
preserve work
commit = 0
push = 0
auto retry = 0
```

If PASS, revalidate exact branch/head/main/scope/remote publication trust, then:

```text
create compact RESULT
commit once
push once
post-fetch remote task head
require exact published identity
status -> PUBLISHED
```

Missing/unknown/stale scope or publication evidence fails closed. No exception-message whitelist and no model/session/CLI scope fallback.

## F. Minimal runtime

Use ignored `.aios_runtime/kernel/` with atomic file replacement.

A task record may contain only:

```text
task_id
action
executor_id
base_main_sha
target_branch
authorized_artifact_sha
review_sha optional
allowed_paths
allowed_paths_fingerprint
verify_command_fingerprint
pre_execution_head
status
published_head_sha optional
```

Closed statuses for this task:

```text
AUTHORIZED
BLOCKED
PUBLISHED
CANCELLED
```

No lease subsystem, session store, scheduler, heartbeat, checkpoint, event bus or workflow database.

Any failure after AUTHORIZE must terminate in BLOCKED or CANCELLED. Orphan ACTIVE state is structurally absent.

## G. Compact context

`context` emits only:

```text
task_id
action
executor_id
target_branch
base_main_sha
task_file
review_file when FIX
allowed_paths
bounded semantic refs
```

No request/lease/execution fingerprints, MANIFEST JSON, roadmap body, byte counts or transport diagnostics.

## H. Parallel worker surfaces

Create smoke-only surfaces without altering current defaults:

```text
Codex:       $aios-kernel-worker
Antigravity: /aios-kernel-worker
```

Both surfaces have identical lifecycle instructions:

```text
Kernel authorize
-> same visible session edits
-> DO NOT run canonical T0/T1 manually
-> Kernel complete once
-> Review TASK-N
```

Explicitly forbid nested model invocation, automatic reroute, merge and 30s/60s timer polling.

Current `$aios-worker` and `/aios-worker` must remain unchanged in TASK-098.

## I. Bootstrap execution discipline

TASK-098 itself runs through old `/aios-worker` once because Kernel does not exist yet.

For this bootstrap task:

```text
broad targeted suite manually before publish = FORBIDDEN
canonical focused suite execution owner = old Bridge publish ONCE
manual debugging tests = exact narrow micro tests only
model-driven timer polling = FORBIDDEN
```

If Antigravity launches the old Bridge publish/test command, use foreground terminal waiting. Do not create recurring timer prompts to check completion.

## Required proofs

```text
KERNEL_MODEL_LAUNCH_COMMAND: NONE
RUN_FIX_DOWNSTREAM_CODEPATH: SAME
NESTED_CODEX_INVOCATION: 0
AUTO_REROUTE: 0
AUTHORIZE_EXACT_TASK_REVIEW_BINDING: PASS
CONTEXT_FIELD_SET_BOUNDED: PASS
ALLOWED_PATHS_MACHINE_DERIVED: PASS
EMPTY_DELTA_COMPLETE_REJECTED_BEFORE_TEST: PASS
OUT_OF_SCOPE_COMPLETE_REJECTED_BEFORE_TEST: PASS
T0_AUTHORITATIVE_INVOCATION_COUNT_PER_COMPLETE: 1
T1_AUTHORITATIVE_INVOCATION_COUNT_PER_COMPLETE: 1
DUPLICATE_CANONICAL_TARGETED_PATH: NONE
KERNEL_MODEL_POLLING_LOOP: 0
VERIFY_FAILURE_TERMINAL_STATE: BLOCKED
VERIFY_FAILURE_COMMIT_PUSH_COUNT: 0
PUBLISH_COMMIT_COUNT: 1
PUBLISH_PUSH_COUNT: 1
PUBLISH_REMOTE_HEAD_POST_VERIFY: PASS
ORPHAN_ACTIVE_STATE: IMPOSSIBLE
DEFAULT_OLD_WORKER_SURFACES_CHANGED: NO
LEGACY_BRIDGE_CHANGED: NO
KERNEL_CERTIFY_MERGE_IMPLEMENTED: NO
PRODUCT_DELIVERY_FAST_IMPLEMENTED: NO
TASK_095_IMPLEMENTED: NO
```

## Candidate-stage ownership for TASK-098 itself

TASK-098 remains CONTROL_PLANE_STRICT under the old Bridge bootstrap:

```text
candidate T2 = 0
semantic review = ChatGPT
full canonical T2 = old bridge.py certify-reviewed 98 exactly once
merge = old bridge.py merge-reviewed 98
```

Do not duplicate the broad candidate suite before old Bridge publication.

## Acceptance

```text
KERNEL_CANDIDATE_PATH_IMPLEMENTED: YES
IMPLEMENTED_STAGES: AUTHORIZE,EXECUTE,VERIFY,PUBLISH
NORMAL_EXECUTOR_SPECIFIC_BRANCHES_AFTER_AUTHORIZE: 0
NORMAL_NESTED_MODEL_INVOCATIONS: 0
AUTHORITATIVE_T0_T1_OWNER: KERNEL_COMPLETE
AUTHORITATIVE_T0_COUNT: 1
AUTHORITATIVE_T1_COUNT: 1
MODEL_TIMER_POLLING_REQUIRED: NO
RUN_FIX_PARITY: PASS
MINIMAL_RUNTIME_STATE: PASS
DEFAULT_CUTOVER: NO
TASK_099_REQUIRED: YES
TASK_095_RESUME_AUTHORIZED: NO
P1_FORMAL_COMPLETION: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

## Delivery lifecycle

```text
Antigravity RUN TASK-098 via old Bridge
-> implement small candidate-path Kernel
-> old Bridge publication runs focused suite once
-> ChatGPT semantic review (zero tests)
-> old bridge.py certify-reviewed 98 (T2 exactly once)
-> old bridge.py merge-reviewed 98
-> author TASK-099 for Kernel REVIEW/CERTIFY/MERGE
-> then real smoke tasks
-> only after smoke proof consider default cutover
-> redesign/rebind TASK-095 against Kernel
```
