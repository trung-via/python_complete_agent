# TASK-098 — AIOS Bridge Kernel v1 Bootstrap

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS BRIDGE KERNEL REBUILD / EXECUTION PATH BOOTSTRAP
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
P1_FORMAL_COMPLETION: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R6","P1.R10"],"scope_in":["implement a new minimal AIOS Bridge Kernel v1 alongside the legacy Bridge","one canonical AUTHORIZE-EXECUTE-VERIFY-PUBLISH-REVIEW-CERTIFY-MERGE lifecycle","same visible Codex/Antigravity executor-session shape","authoritative targeted T0/T1 exactly once at deterministic VERIFY boundary","full canonical T2 exactly once at CERTIFY boundary","synchronous process waiting with zero model-driven polling","machine-derived exact scope and publication authority","minimal atomic runtime authorization/certification records","parallel kernel worker surfaces for smoke testing without default cutover"],"scope_out":["patching TASK-097 bridge.py wrapper","TASK-095 implementation","PRODUCT_DELIVERY_FAST implementation","capability lane/certification implementation","Python Agent pilot","default cutover of existing $aios-worker or /aios-worker","legacy Bridge deletion","historical migration","EVIDENCE_REFRESH mode","nested Codex transport","automatic retry/reroute/rebase/conflict resolution","persistent model sessions","heartbeat/checkpoint/resume","workflow database","P2","P3","H5-H8","canonical roadmap mutation"]}

## Exact baseline

```text
MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TARGET_BRANCH: ai/task-098
TASK_094: PASS_CERTIFIED_MERGED
TASK_095: BLOCKED_PENDING_KERNEL_REBUILD
TASK_096: SUPERSEDED
TASK_097: SUPERSEDED_FOR_NORMAL_PATH
ADR_068: ACCEPTED
ROADMAP_V1_2: LOCKED_REGISTERED
KERNEL_DEFAULT_CUTOVER: NO
```

## Machine-readable E4 inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-068-AIOS-BRIDGE-KERNEL-V1-EXECUTION-LIFECYCLE-LOCK.md","blob_sha":"1778dde9dc5efcb43ad8b07053436696cec5d1bb"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py","src/aios_bridge/kernel/__init__.py","src/aios_bridge/kernel/model.py","src/aios_bridge/kernel/gitops.py","src/aios_bridge/kernel/authority.py","src/aios_bridge/kernel/context.py","src/aios_bridge/kernel/verify.py","src/aios_bridge/kernel/publish.py","src/aios_bridge/kernel/review.py","src/aios_bridge/kernel/certify.py","src/aios_bridge/kernel/merge.py","src/aios_bridge/kernel/cli.py",".agents/skills/aios-kernel-worker/SKILL.md",".agents/skills/aios-kernel-worker/scripts/aios_kernel_worker.py",".agents/workflows/aios-kernel-worker.md","docs/AIOS_BRIDGE_KERNEL_V1.md",".gitignore","tests/aios_bridge/kernel/test_model.py","tests/aios_bridge/kernel/test_authority.py","tests/aios_bridge/kernel/test_context.py","tests/aios_bridge/kernel/test_verify.py","tests/aios_bridge/kernel/test_publish.py","tests/aios_bridge/kernel/test_review.py","tests/aios_bridge/kernel/test_certify.py","tests/aios_bridge/kernel/test_merge.py","tests/aios_bridge/kernel/test_cli.py","tests/test_aios_kernel.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

KERNEL_VERIFY_COMMAND_JSON: {"t0":["venv/Scripts/python.exe","-m","pytest","tests/aios_bridge/kernel/test_model.py","tests/aios_bridge/kernel/test_authority.py","tests/aios_bridge/kernel/test_context.py","-q"],"t1":["venv/Scripts/python.exe","-m","pytest","tests/aios_bridge/kernel/test_verify.py","tests/aios_bridge/kernel/test_publish.py","tests/aios_bridge/kernel/test_review.py","tests/aios_bridge/kernel/test_certify.py","tests/aios_bridge/kernel/test_merge.py","tests/aios_bridge/kernel/test_cli.py","tests/test_aios_kernel.py","-q"]}

## Purpose

Stop patching the existing Bridge normal execution path. Implement a new minimal Kernel v1 beside it, following ADR-068 exactly. The old Bridge is used only as the bootstrap transport to execute/review/certify this task. Kernel v1 does not become the default worker until later real smoke proofs pass.

## Hard architecture contract

Kernel v1 normal lifecycle is exactly:

```text
AUTHORIZE
-> EXECUTE
-> VERIFY
-> PUBLISH
-> REVIEW
-> CERTIFY
-> MERGE
```

No executor-specific orchestration branch may alter this lifecycle.

### Ownership

```text
AUTHORIZE = Kernel
EXECUTE   = visible selected Codex/Antigravity session
VERIFY    = Kernel deterministic subprocess
PUBLISH   = Kernel
REVIEW    = ChatGPT semantic review only
CERTIFY   = Kernel deterministic full T2
MERGE     = Kernel exact fast-forward
```

## A. New isolated package

Create `src/aios_bridge/kernel/` as an independent bounded implementation. It may reuse small pure helpers or Git primitives only where that reduces code without inheriting old worker-flow state machines.

Do NOT import or call normal-path orchestration from:

```text
src/aios_bridge/worker_flow.py
src/aios_bridge/executor_transports/codex_local.py
src/aios_bridge/legacy_bridge.py
root bridge.py command wrappers
```

Compatibility Bridge remains untouched by this task except as the external bootstrap runner.

Root entry point:

```text
aios_kernel.py
```

must delegate to `src.aios_bridge.kernel.cli` and contain no orchestration logic.

## B. Closed Kernel commands

Implement only these normal commands:

```text
status TASK-N
authorize TASK-N --action run|fix --executor codex|antigravity
context TASK-N
complete TASK-N
certify-reviewed TASK-N
merge-reviewed TASK-N
cancel TASK-N
```

No `execute` command exists in Kernel v1. No command may launch a model.

### `authorize`

Must:

```text
fetch exact ai-control artifact(s)
require exact TASK; require exact CHANGES_REQUIRED REVIEW for FIX
require Human-selected executor exactly
require remote main exact current base
create/prepare exact ai/task-N from main only when safe
parse exact allowed_paths from TASK authority
parse exact KERNEL_VERIFY_COMMAND_JSON from TASK authority
persist one minimal atomic authorization record outside Git tracking
emit compact context
```

RUN and FIX differ only in authority input. After authorization they share all downstream behavior.

### `context`

Read-only. Emit exactly:

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

No manifest JSON, lease/request/execution fingerprints, roadmap body, byte counts or transport diagnostics.

### `complete`

This is the only authoritative VERIFY+PUBLISH boundary.

It must:

```text
require exact AUTHORIZED record
require exact selected executor/branch/base/artifact identities
require changed paths non-empty and subset of exact allowed_paths
run authoritative T0 then T1 from exact TASK marker exactly once each
run commands with synchronous foreground subprocess waiting
never create timers or polling loops
if any test fails -> BLOCKED, preserve work, no commit/push
if tests pass -> recheck branch/head/scope/main/remote trust
create compact RESULT
commit once
push once
post-fetch exact published branch identity
terminalize PUBLISHED
```

The visible executor MUST NOT run the canonical T0/T1 command before `complete`. Optional ad-hoc micro tests during debugging are allowed only when narrower than the canonical suite and are non-authoritative.

`complete` must itself own the exact authoritative count, making duplicate canonical targeted execution structurally impossible in the normal path.

## C. Long-running process behavior

Kernel invokes pytest/Git subprocesses synchronously and waits on the same process. No model-level timer is involved.

Tests must prove command invocation count, not merely final PASS state.

```text
CANONICAL_T0_INVOCATION_COUNT_PER_COMPLETE: 1
CANONICAL_T1_INVOCATION_COUNT_PER_COMPLETE: 1
MODEL_POLLING_LOOP: 0
```

## D. Minimal runtime state

Use one ignored workspace-local runtime directory, preferably `.aios_runtime/kernel/`, with atomic write/replace semantics.

One task record may contain only:

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
certified_head_sha optional
```

No lease subsystem, scheduler, heartbeat, session store, event bus or workflow database.

Status vocabulary is closed:

```text
AUTHORIZED
BLOCKED
PUBLISHED
SEMANTICALLY_ACCEPTED_PENDING_T2
CERTIFIED
MERGED
CANCELLED
```

If a command fails after authorization, it must end in BLOCKED or CANCELLED; no orphan ACTIVE/uncertain state exists.

## E. Review boundary

Kernel review parser accepts only an exact canonical REVIEW binding:

```text
TASK_ID exact
REVIEWED_TASK_HEAD_SHA exact published head
REVIEWED_BASE_MAIN_SHA exact base
STATUS = SEMANTICALLY_ACCEPTED_PENDING_T2
APPROVED = YES
BLOCKERS_REMAINING = 0
TASK_ARTIFACT_BLOB_SHA exact
RESULT_BLOB_SHA exact
```

ChatGPT review runs zero tests.

For FIX authorization, exact CHANGES_REQUIRED REVIEW is the additional authority input; downstream lifecycle remains identical to RUN.

## F. Certification boundary

`certify-reviewed` must:

```text
require exact semantic acceptance
require candidate T2 count == 0
freeze exact candidate/review/task/result/base identity
run only `venv/Scripts/python.exe -m pytest tests/ -q`
run it exactly once synchronously
on PASS persist CERTIFIED exact head
on FAIL persist BLOCKED exact head
never retry automatically
```

No model polling. No second T2 in merge.

## G. Merge boundary

`merge-reviewed` must require exact CERTIFIED state and revalidate:

```text
remote task head == certified head
remote main == certified base main
fast-forward ancestry only
review/task/result identities still exact
```

Then fast-forward main once, push once and post-fetch exact main identity. No tests run here.

## H. Parallel worker surfaces

Create parallel smoke-only surfaces, without changing current defaults:

```text
Codex:       $aios-kernel-worker
Antigravity: /aios-kernel-worker
```

Both must have the same instructions:

```text
invoke Kernel authorize
continue in same visible session
edit only compact allowed_paths
DO NOT run canonical T0/T1 suite manually
DO NOT spawn nested model
DO NOT poll timers for command completion
invoke Kernel complete once when implementation is done
report Review TASK-N
```

These surfaces are for post-merge smoke proofs only. Existing `$aios-worker` and `/aios-worker` remain unchanged until explicit cutover.

## I. Bootstrap-task execution discipline

TASK-098 itself still runs through the old Antigravity Bridge because Kernel v1 does not exist yet.

For this final bootstrap execution:

- do not run the broad TASK-098 targeted suite manually before publish;
- during implementation, run only exact micro/node tests needed to debug a failing unit;
- canonical targeted suite should be supplied once to old Bridge publication as the authoritative candidate validation;
- do not create model-driven 30s/60s timers to poll pytest or publish completion; use foreground/synchronous terminal execution where the Antigravity tool permits it;
- if the old UI cannot wait synchronously, wait on the same terminal/process without generating repeated model reasoning turns.

## Required tests

Prove at minimum:

```text
KERNEL_HAS_NO_EXECUTE_MODEL_COMMAND
RUN_FIX_SHARE_ONE_DOWNSTREAM_LIFECYCLE
CODEX_VISIBLE_SESSION_ONLY: PASS
ANTIGRAVITY_VISIBLE_SESSION_ONLY: PASS
NESTED_CODEX_INVOCATION: 0
AUTO_REROUTE: 0
AUTHORIZE_EXACT_TASK_REVIEW_BINDING: PASS
CONTEXT_FIELD_SET_BOUNDED: PASS
ALLOWED_PATHS_MACHINE_DERIVED: PASS
OUT_OF_SCOPE_COMPLETE_REJECTED_BEFORE_TEST: PASS
EMPTY_DELTA_COMPLETE_REJECTED: PASS
T0_AUTHORITATIVE_INVOCATION_COUNT: 1
T1_AUTHORITATIVE_INVOCATION_COUNT: 1
DUPLICATE_CANONICAL_TARGETED_EXECUTION_PATH: NONE
LONG_RUNNING_MODEL_POLLING: 0
VERIFY_FAILURE_NO_PUBLISH: PASS
PUBLISH_EXACT_HEAD_POST_VERIFY: PASS
FAILURE_TERMINALIZES_BLOCKED: PASS
ORPHAN_ACTIVE_STATE: IMPOSSIBLE
REVIEW_RUNS_TESTS: 0
CERTIFY_T2_INVOCATION_COUNT: 1
CERTIFY_AUTO_RETRY: 0
MERGE_RUNS_TESTS: 0
MERGE_FAST_FORWARD_ONLY: PASS
DEFAULT_OLD_WORKER_SURFACES_CHANGED: NO
LEGACY_BRIDGE_DELETED: NO
PRODUCT_DELIVERY_FAST_IMPLEMENTED: NO
TASK_095_IMPLEMENTED: NO
```

## Candidate-stage validation ownership for TASK-098

TASK-098 is still a CONTROL_PLANE_STRICT bootstrap task under the old Bridge. Candidate T2 remains 0. Full canonical T2 remains exclusively at old `bridge.py certify-reviewed 98` after semantic acceptance.

The executor must avoid duplicate broad targeted execution: use micro tests during coding only; let publication own the one authoritative focused suite.

## Acceptance

```text
KERNEL_V1_IMPLEMENTED_ALONGSIDE_LEGACY: YES
NORMAL_LIFECYCLE_STAGES: 7
NORMAL_EXECUTOR_SPECIFIC_BRANCHES: 0
NORMAL_NESTED_MODEL_INVOCATIONS: 0
AUTHORITATIVE_T0_T1_OWNER: KERNEL_VERIFY
AUTHORITATIVE_T0_COUNT: 1
AUTHORITATIVE_T1_COUNT: 1
REVIEW_TEST_COUNT: 0
CERTIFICATION_T2_OWNER: KERNEL_CERTIFY
CERTIFICATION_T2_COUNT: 1
MERGE_TEST_COUNT: 0
MODEL_TIMER_POLLING_REQUIRED: NO
RUN_FIX_DOWNSTREAM_PARITY: PASS
MINIMAL_RUNTIME_STATE: PASS
DEFAULT_CUTOVER: NO
TASK_095_RESUME_AUTHORIZED: NO
P1_FORMAL_COMPLETION: NO
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

## Delivery lifecycle

```text
Antigravity RUN TASK-098 via old Bridge
-> implement Kernel v1 alongside old Bridge
-> one authoritative focused publication validation
-> ChatGPT semantic review (zero tests)
-> old bridge.py certify-reviewed 98 (T2 exactly once)
-> old bridge.py merge-reviewed 98
-> create bounded smoke tasks for kernel surfaces
-> only after 3 real smoke proofs consider default cutover
-> redesign/rebind TASK-095 against Kernel v1
```
