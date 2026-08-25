# TASK-087 — P1.0B Failure Classification + Deterministic Next Action

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1.0B FAILURE RECOVERY CLASSIFICATION
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
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

## Baseline

```text
MAIN_SHA: ac0ae79e85e30a80410380188578db1993720b5b
TARGET_BRANCH: ai/task-087
TASK_086: PASS_MERGED
TASK_089: PASS_MERGED
TASK_090: PASS_MERGED
TASK_091: PASS_CERTIFIED_MERGED
TASK_092: PASS_CERTIFIED_MERGED
LEAN_REVIEW_SLICES_A_D: COMPLETE
REVIEW_FIRST_CERTIFICATION_ON_MAIN: YES
FIX_PROOF_REUSE_DELTA_IMPACT_ON_MAIN: YES
COMPACT_RESULT_AND_SUPERSESSION_ON_MAIN: YES
ROADMAP_V1_2: LOCKED_REGISTERED
P1_FORMAL_COMPLETION: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

TASK-087 is the previously reserved P1.0B slice from ADR-062, rebound only after the Human-approved Lean Review implementation slices completed and merged. ADR-061/062 are implementation-refinement context; roadmap v1.2 is the sole canonical roadmap authority.

Passing TASK-087 does NOT complete P1. After TASK-087, remaining P1 work still includes capability-batch/integration-lane implementation and the Python Agent Time-to-Trusted-Capability pilot required by roadmap v1.2.

Required delivery lifecycle:

```text
RUN executor
  -> T0 / bounded targeted T1 / diff check
  -> publish candidate with AIOS-managed T2 count = 0
  -> ChatGPT semantic review
      -> CHANGES_REQUIRED: use FIX_REVIEW_MODE=PROOF_REUSE_DELTA_IMPACT + bounded FIX_CONTEXT_PACK_JSON; next candidate still T2=0
      -> SEMANTICALLY_ACCEPTED_PENDING_T2: continue
  -> bridge.py certify-reviewed 87
      -> full canonical T2 exactly once for exact accepted candidate
  -> bridge.py merge-reviewed 87
```

No full canonical T2 is authorized during RUN/FIX candidate publication.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-061-AIOS-P1.0-TRANSACTIONAL-WORKER-FLOW-FIX-RECOVERY-CONTRACT.md","blob_sha":"b456d80befff7aeec0d3a0217e03a9834f71d7f8"},{"path":".ai/decisions/ADR-062-AIOS-P1.0-BOUNDED-SLICE-DECOMPOSITION-AFTER-CLEAN-NOOP.md","blob_sha":"bcdb4f148d731292c776802d858448e99469abe1"},{"path":".ai/decisions/ADR-065-AIOS-LEAN-REVIEW-PIPELINE-ACTIVATION-BOUNDED-SLICES.md","blob_sha":"947b3ec5b63ddd628838a533822e37499a837a74"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_flow.py","src/aios_bridge/worker_failure.py","src/aios_bridge/executor_outcome.py",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/skills/aios-worker/SKILL.md",".agents/workflows/aios-worker.md","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Complete the second bounded P1.0 worker-flow slice authorized by ADR-061/062. The operator should receive one trustworthy classification and one deterministic next action after a blocked executor transaction, without manually inspecting Git state merely to discover what happened.

The principle is:

```text
OBSERVE EXECUTION TERMINAL FACTS
        +
OBSERVE EXACT HEAD / WORKTREE DELTA
        +
PRESERVE AUTHORITY / LEASE / PROVENANCE
        ↓
ONE CLOSED FAILURE CLASS
        ↓
ONE BOUNDED NEXT ACTION
```

Classification creates no retry, reroute, merge, or recovery authority by itself.

## 1. Closed Provider-Neutral Failure Classification

Introduce one pure/closed classification contract, preferably isolated in `src/aios_bridge/worker_failure.py`, that is independent of Codex-specific prose or UI behavior.

Minimum closed implementation classifications:

```text
CLEAN_NO_WORKTREE_DELTA
CLEAN_TIMEOUT
DIRTY_TIMEOUT_RECOVERY_REQUIRED
PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE
```

Existing preauthorization/certification failures may retain their current dedicated gates; do not broaden this task into redesigning those subsystems.

Required inputs must be bounded deterministic facts, such as:

```text
invocation terminal status
pre-execution head
post-execution head
tracked/untracked dirty paths
whether dirty paths are within authorized scope
whether executor process is known terminal/stopped
existing structured executor diagnostic/outcome metadata where available
```

Raw model reasoning is never an input to authority.

## 2. CLEAN_NO_WORKTREE_DELTA

Preserve the clean-no-op safety already implemented on main by TASK-092.

Required semantics:

```text
executor reached terminal state
post head == pre head
worktree delta == empty
classification = CLEAN_NO_WORKTREE_DELTA
no RESULT publication
no auto retry
no auto reroute
lease cleanup only through existing proven-safe boundary
structured blocked evidence retained
```

Do not regress explicit-Human blocked-executor replacement semantics from TASK-092.

## 3. CLEAN_TIMEOUT

For an invocation terminally classified `TIMED_OUT`, classify CLEAN_TIMEOUT only when the executor is known stopped/terminal and the exact repository subject remains clean:

```text
post head == pre head
worktree delta == empty
```

Required semantics:

```text
classification = CLEAN_TIMEOUT
no RESULT publication
no silent reuse of stale execution authority
no auto retry
no auto reroute
one deterministic next action requiring Human choice
```

Do not infer CLEAN_TIMEOUT from elapsed wall clock alone; use the transport's bounded terminal timeout status.

## 4. DIRTY_TIMEOUT_RECOVERY_REQUIRED

For terminal timeout with preserved repository mutation:

```text
worktree delta != empty OR post head != pre head
```

classify:

```text
DIRTY_TIMEOUT_RECOVERY_REQUIRED
```

Required semantics:

```text
preserve exact worktree/head evidence
preserve authorized-path/scope facts
block fresh executor execution until explicit Human recovery decision
no automatic reset/clean/stash/commit
no automatic retry/reroute
no fabricated CONSUMED/PUBLISHED boundary
NEXT ACTION identifies preserved-delta recovery requirement
```

This task does not create public checkpoint/resume/session semantics.

## 5. PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE Compatibility

An executor nonzero exit with a bounded preserved implementation delta may be classified as `PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE` only when existing strict preserved-delta safety checks succeed.

Required:

```text
nonzero alone is insufficient
delta must exist
delta must be inside exact authorized scope
head/branch/worktree provenance must remain valid
existing publication/recovery safety is not weakened
classification creates zero merge/publication authority by itself
```

Malformed/out-of-scope/uncertain cases remain fail-closed under existing recovery behavior.

## 6. One Deterministic Next Action

Define one closed next-action vocabulary. Exact names may be implementation-specific, but semantics must cover at least:

```text
HUMAN_DECISION_REQUIRED_CLEAN_TIMEOUT
RECOVERY_REQUIRED_PRESERVED_DELTA
HUMAN_SELECT_REPLACEMENT_EXECUTOR_IF_PROVEN_SAFE
REVIEW_TASK_AFTER_SUCCESSFUL_PUBLICATION
CORRECT_CONTROL_ARTIFACT
```

For every blocked classification owned by this task, exactly one machine-readable `next_action` is emitted. Human-readable text is derived from that same value and must not independently create a second authority source.

Do not emit two competing instructions such as both `retry` and `switch executor`.

## 7. Worker / UI Integration

Integrate the closed classification into normal `$aios-worker RUN/FIX` handling for both Codex and Antigravity where terminal execution facts are available.

Required operator behavior:

```text
no manual git status/diff inspection required as the normal discovery path
classification visible in bounded worker output/state
next_action visible in bounded worker output/state
provider-specific transport details may differ
classification semantics remain provider-neutral
```

Antigravity interactive execution must not fabricate terminal timeout facts that Bridge cannot observe. Unknown/uncertain terminal state remains fail-closed.

## 8. Review-First / Slice-C Preservation

TASK-087 must preserve the post-TASK-092 pipeline:

```text
candidate RUN/FIX publication T2 = 0
semantic review before certification
FIX uses Proof Carry-Forward + Delta/Impact when CHANGES_REQUIRED
final exact candidate alone receives T2 exactly once
no model polling while T2 executes
compact RESULT remains single machine authority
certification supersession remains exact-head bound
```

## 9. Required Targeted / Impact Proofs

At minimum prove:

```text
CLEAN_NO_WORKTREE_DELTA_CLASSIFIED: PASS
CLEAN_NO_WORKTREE_DELTA_NEXT_ACTION_SINGLE: PASS
CLEAN_TIMEOUT_CLASSIFIED_FROM_TERMINAL_TIMEOUT: PASS
CLEAN_TIMEOUT_REQUIRES_ZERO_DELTA: PASS
CLEAN_TIMEOUT_NO_RESULT_PUBLICATION: PASS
CLEAN_TIMEOUT_NO_AUTO_RETRY: PASS
CLEAN_TIMEOUT_NO_AUTO_REROUTE: PASS
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

Executor runs targeted/impact tests and diff check only. Certification boundary owns final full canonical T2.

## 10. Explicit Out of Scope

```text
changing canonical roadmap v1.2
marking P1 complete
capability batch container
integration lane
Python Agent pilot
persistent sessions
checkpoint/resume
capacity scheduler
shell interception
cross-executor automatic continuation
automatic retry/reroute
Claude Code integration
P2/P3
H5-H8
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
NO_MANUAL_GIT_DISCOVERY_AS_NORMAL_PATH: PASS
PROVIDER_NEUTRAL_CLASSIFICATION: PASS
REVIEW_FIRST_CERTIFICATION_PRESERVED: PASS
SLICE_C_FIX_PRESERVED: PASS
TASK_PASS != P1 COMPLETE
P1_CAPABILITY_BATCH_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```
