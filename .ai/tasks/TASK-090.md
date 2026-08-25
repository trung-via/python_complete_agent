# TASK-090 — Review-First Certification + Deterministic Certification Job Integration

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1 LEAN REVIEW SLICE B
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
IMPLEMENTATION_REFINEMENT_ADR: ADR-064
DECOMPOSITION_ADR: ADR-065
CUTOVER_SLICE: REVIEW_FIRST_CERTIFICATION_INTEGRATION
TASK_087_REMAINS_RESERVED: YES
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R6","P1.R9"],"scope_in":["explicit review-first pipeline mode for future tasks with legacy compatibility by default","candidate publication before T2 for review-first tasks","non-authoritative semantic acceptance bound to exact candidate head and base main","deterministic certification job persisted in external runtime and bound to exact candidate identity","T2 exactly once only after semantic acceptance for review-first tasks","single blocking machine wait for T2 with no model or executor completion polling","final merge authority derived only from semantic acceptance plus exact certification PASS","legacy reviewed-head roadmap lease scope and fast-forward merge safety preserved"],"scope_out":["Proof Carry-Forward integration","dependency impact engine","invalidation-based targeted testing","Delta plus Impact Review orchestration","Finding Registry persistence or orchestration","risk-router integration into live reviewer routing","compact RESULT cutover","single-source-of-truth RESULT redesign","review or certification supersession cancellation integration beyond exact-head fail-closed detection","finding-to-guardrail promotion","background service or daemon","automatic retry","automatic reroute","TASK-087 implementation","P1 capability batch integration lane","Python Agent fast-lane pilot","P2 persistent executor sessions","P3 adaptive executor selection","H5-H8 implementation"]}

## Baseline

```text
MAIN_SHA: bb4a30775c2deb2a37ebe763d1a74ce7e64d6ebe
TARGET_BRANCH: ai/task-090
TASK_089: PASS_MERGED
TASK_089_FOUNDATION_ON_MAIN: YES
ROADMAP_V1_2: LOCKED_REGISTERED
ADR_065_SLICE_B_AUTHORITY: YES
TASK_087: RESERVED_NOT_EXECUTED
P1_FORMAL_COMPLETION: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

TASK-090 itself is the cutover implementation task and MUST still complete under the pre-cutover compatibility path. It MUST NOT activate review-first behavior for itself. Review-first behavior becomes active only for later tasks that contain the new exact top-level mode marker defined below.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-065-AIOS-LEAN-REVIEW-PIPELINE-ACTIVATION-BOUNDED-SLICES.md","blob_sha":"947b3ec5b63ddd628838a533822e37499a837a74"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/validation.py","src/aios_bridge/review_pipeline.py","src/aios_bridge/certification_job.py","tests/aios_bridge/test_validation.py","tests/aios_bridge/test_review_pipeline.py","tests/aios_bridge/test_certification_job.py","tests/aios_bridge/test_lean_review_integration.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Cut over future Lean Review tasks from the current implementation-first/full-T2-before-review flow to Review-First Certification without weakening any existing authority boundary.

Required future flow after TASK-090 merges:

```text
EXECUTOR
  -> T0 / impacted T1 / diff check
  -> publish exact candidate WITHOUT T2
  -> semantic review
      -> CHANGES_REQUIRED -> FIX -> publish new exact candidate WITHOUT T2
      -> SEMANTICALLY_ACCEPTED_PENDING_T2
  -> deterministic certify-reviewed job
      -> T2 full canonical exactly once for exact accepted candidate
  -> CERTIFICATION_PASS
  -> deterministic merge-reviewed gate
  -> main
```

The long-running T2 wait is owned by one deterministic Bridge process. The model and executor do not repeatedly ask whether T2 has finished.

## 1. Explicit Review-First Pipeline Mode With Legacy Compatibility

Extend `src/aios_bridge/review_pipeline.py` with a closed task pipeline mode and strict parser.

Future review-first tasks opt in with one exact top-level task marker shown here only as an example inside this fenced block:

```text
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION
```

Required semantics:

```text
marker missing -> LEGACY_CERTIFY_ON_PUBLISH
exact single marker -> REVIEW_FIRST_CERTIFICATION
multiple markers -> FAIL_CLOSED
unknown marker -> FAIL_CLOSED
marker inside fenced prose/example -> MUST_NOT_ACTIVATE_MODE
TASK-090 itself -> LEGACY_CERTIFY_ON_PUBLISH
```

Do not reinterpret previously authored tasks. Legacy tasks keep current certification/publication behavior unchanged.

## 2. Review-First Candidate Publication

For a task explicitly in `REVIEW_FIRST_CERTIFICATION` mode, change the Bridge publication path so implementation/FIX publication produces a semantic-review candidate and does not execute T2.

Required behavior:

```text
executor mutation + existing scope/diff checks: PRESERVED
candidate branch commit/push: PRESERVED
lease release after successful candidate push: PRESERVED
authorization consumption: PRESERVED
T2 during candidate publication: 0
candidate RESULT status: READY_FOR_SEMANTIC_REVIEW
expected final T2 count: 1
observed candidate-stage AIOS-managed T2 count: 0
semantic review required before certification: YES
```

If the legacy caller supplies a full-canonical test command while the task is review-first, the candidate publication path MUST NOT execute that T2 command. It must record certification as deferred rather than falsely claiming certification occurred.

Add a deterministic validation helper in `src/aios_bridge/validation.py` that proves a review-first candidate publication has zero AIOS-managed T2 executions. Do not weaken the existing final certification helper.

For legacy-mode tasks, current `require_certification_for_publication()` and exactly-one T2 behavior remain unchanged.

### EVIDENCE_REFRESH compatibility during Slice B

Review-first tasks MUST fail closed if a pre-certification `EVIDENCE_REFRESH` attempt would cause the legacy direct-T2 continuation. Do not allow EVIDENCE_REFRESH to bypass semantic acceptance. Slice C will define optimized FIX proof reuse semantics.

Legacy tasks retain their existing EVIDENCE_REFRESH behavior.

## 3. Semantic Acceptance Contract

A review-first candidate may proceed to certification only when the authoritative control review is exactly:

```text
STATUS: SEMANTICALLY_ACCEPTED_PENDING_T2
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
```

plus the existing exact reviewed task head, reviewed base main, task artifact blob, roadmap audit, milestone, capability, and requirement-binding evidence required by the deterministic review parser/gates.

Important authority rule:

```text
SEMANTICALLY_ACCEPTED_PENDING_T2 + APPROVED YES + AUTO_MERGE_ELIGIBLE YES
    WITHOUT certification PASS
    -> MERGE AUTHORITY = NO
```

`APPROVED` and `AUTO_MERGE_ELIGIBLE` in this state mean the semantic content is conditionally acceptable if certification succeeds. `STATUS` remains non-final and blocks merge until certification completes.

`CHANGES_REQUIRED` continues to authorize only the existing bounded FIX flow. Plain `PASS` remains the legacy final-review format for legacy tasks.

## 4. Deterministic `certify-reviewed` Command

Add one new Bridge CLI command:

```text
bridge.py certify-reviewed <task_id>
```

This command is provider-neutral and does not invoke an executor or model.

Before any T2 execution it MUST fail closed unless all of the following are true:

```text
task exists on frozen control commit
pipeline mode == REVIEW_FIRST_CERTIFICATION
authoritative review exists on frozen control commit
review status == SEMANTICALLY_ACCEPTED_PENDING_T2
review approved == YES
review auto-merge-eligible == YES
reviewed task head == current remote task head
reviewed base main == current remote main
local current branch == exact task branch
local HEAD == exact reviewed task head
local worktree is clean
merge base == current main
task is not behind main
roadmap binding/current locked roadmap remains exact
validation plan resolves exactly one certification-owned T2
```

Any head/main/roadmap/worktree drift MUST fail before T2 starts.

## 5. Runtime Certification Job Persistence

Use the TASK-089 `CertificationJob` foundation. Extend it only as needed with pure deterministic helpers for candidate fingerprint and bounded terminal evidence.

Add an external-runtime certification-job location through Bridge runtime paths. Do not persist certification state into the Git worktree.

Minimum persisted authority evidence:

```text
job_id
task_id
candidate_head_sha
candidate_fingerprint
validation_profile
certification_command_identity
status
started_at
terminal_result_digest
AIOS-managed T2 execution count
T2 exit status / success fact
bounded duration evidence
```

Candidate fingerprint must be deterministic from exact machine inputs and must not depend on prose or model output.

Raw pytest stdout, model reasoning, or executor reasoning MUST NOT be persisted in the certification job file.

## 6. Exactly-Once Certification Semantics

`certify-reviewed` owns the final T2 process for review-first tasks.

Required behavior:

```text
PENDING -> RUNNING -> PASS | FAILED
T2 owner: CERTIFICATION_BOUNDARY
T2 execution count for this exact certification job: exactly 1
model invocation count while T2 waits: 0
executor invocation count while T2 waits: 0
normal wait mechanism: one blocking deterministic machine process
```

Repeated command behavior MUST NOT create hidden retries:

```text
existing PASS for exact same candidate -> report existing PASS, T2 rerun count = 0
existing FAILED for exact same candidate -> fail closed, automatic retry = NO
existing RUNNING/PENDING for exact same candidate -> fail closed, second T2 = NO
job bound to different candidate -> fail closed; Slice D owns explicit supersession integration
```

On T2 failure, persist `CERTIFICATION_FAILED`, create no merge authority, and do not retry/reroute automatically.

## 7. Final Authority Without Changing Candidate Head

Certification MUST NOT commit an evidence-only change to the task branch. The reviewed candidate head must remain unchanged from semantic acceptance through T2 and merge.

After exact certification PASS, extend `src/aios_bridge/review_pipeline.py` with a pure deterministic finalization decision equivalent to:

```text
SEMANTICALLY_ACCEPTED_PENDING_T2
+ exact CertificationJob PASS
+ exact candidate head/fingerprint match
-> FINAL_PASS
```

Without exact PASS evidence the state cannot reach FINAL_PASS.

This final state may be derived by Bridge from the immutable semantic review plus runtime certification evidence; it does not require a second model review of deterministic T2 output.

## 8. `merge-reviewed` Integration

Preserve the current reviewed-head merge gate and legacy PASS behavior.

For legacy tasks:

```text
STATUS: PASS
-> existing merge-reviewed behavior unchanged
```

For review-first tasks:

```text
STATUS: SEMANTICALLY_ACCEPTED_PENDING_T2
+ exact runtime CertificationJob == CERTIFICATION_PASS
+ exact head/fingerprint/profile/command binding
-> derive FINAL_PASS
-> feed existing deterministic reviewed-head/roadmap/fast-forward merge gate
```

Required fail-closed cases:

```text
semantic acceptance with no certification job -> NO MERGE
FAILED certification -> NO MERGE
PENDING/RUNNING certification -> NO MERGE
certification head mismatch -> NO MERGE
certification fingerprint mismatch -> NO MERGE
current task head drift -> NO MERGE
current main drift -> NO MERGE
roadmap drift -> NO MERGE
```

Do not weaken `evaluate_merge_gate()` safety precedence. Prefer deriving effective final authority before invoking the existing pure merge gate rather than duplicating a second permissive merge implementation.

## 9. Sync / Operator State

When Bridge sync receives a review-first semantic acceptance, represent it distinctly in runtime state, for example:

```text
SEMANTICALLY_ACCEPTED_PENDING_T2
next_step = run deterministic certify-reviewed for exact candidate
```

After certification PASS:

```text
CERTIFIED
next_step = merge-reviewed exact certified candidate
```

After certification failure:

```text
CERTIFICATION_FAILED
next_step = no automatic retry or reroute
```

Do not add a watcher that repeatedly invokes a model or executor.

## 10. Required Tests

Add `tests/aios_bridge/test_lean_review_integration.py` and extend only the existing bounded unit tests listed in allowed paths.

Required proof matrix:

```text
PIPELINE_MODE_MISSING_IS_LEGACY: PASS
PIPELINE_MODE_EXACT_OPT_IN: PASS
PIPELINE_MODE_DUPLICATE_OR_UNKNOWN_FAILS_CLOSED: PASS
FENCED_MODE_EXAMPLE_DOES_NOT_ACTIVATE: PASS
LEGACY_PUBLICATION_STILL_REQUIRES_T2_EXACTLY_ONCE: PASS
REVIEW_FIRST_CANDIDATE_PUBLICATION_RUNS_ZERO_T2: PASS
REVIEW_FIRST_CANDIDATE_STATUS_READY_FOR_SEMANTIC_REVIEW: PASS
REVIEW_FIRST_EVIDENCE_REFRESH_CANNOT_RUN_EARLY_T2: PASS
SEMANTIC_ACCEPTANCE_ALONE_CANNOT_MERGE: PASS
CERTIFY_REVIEWED_REJECTS_NON_SEMANTIC_REVIEW: PASS
CERTIFY_REVIEWED_HEAD_DRIFT_FAILS_BEFORE_T2: PASS
CERTIFY_REVIEWED_MAIN_DRIFT_FAILS_BEFORE_T2: PASS
CERTIFY_REVIEWED_DIRTY_WORKTREE_FAILS_BEFORE_T2: PASS
CERTIFICATION_JOB_EXACT_CANDIDATE_BINDING: PASS
CERTIFICATION_JOB_T2_EXACTLY_ONCE: PASS
CERTIFICATION_PASS_IDEMPOTENT_NO_RERUN: PASS
CERTIFICATION_FAILED_NO_AUTO_RETRY: PASS
CERTIFICATION_WAIT_HAS_ZERO_MODEL_POLLS: PASS
CERTIFICATION_WAIT_HAS_ZERO_EXECUTOR_POLLS: PASS
RAW_T2_STDOUT_NOT_PERSISTED_IN_JOB: PASS
FINAL_PASS_REQUIRES_EXACT_CERTIFICATION_PASS: PASS
REVIEW_FIRST_MERGE_REJECTS_MISSING_OR_FAILED_CERTIFICATION: PASS
REVIEW_FIRST_MERGE_REJECTS_CERTIFICATION_HEAD_OR_FINGERPRINT_MISMATCH: PASS
REVIEW_FIRST_EXACT_CERTIFICATION_PASS_USES_EXISTING_MERGE_GATE: PASS
LEGACY_PASS_MERGE_BEHAVIOR_UNCHANGED: PASS
ROADMAP_REVIEWED_HEAD_LEASE_SCOPE_INVARIANTS_PRESERVED: PASS
TASK_087_NOT_IMPLEMENTED: PASS
```

Tests must mock/stub the full canonical process where practical. Do not make the targeted test suite spend five minutes running the real full repository suite repeatedly.

## 11. Executor Validation Contract For TASK-090

TASK-090 is still pre-cutover and therefore its own final certification uses the current legacy certification boundary exactly once.

Executor must run targeted/impact tests only, including at minimum:

```text
venv\Scripts\python.exe -m pytest tests/aios_bridge/test_review_pipeline.py tests/aios_bridge/test_certification_job.py tests/aios_bridge/test_validation.py tests/aios_bridge/test_lean_review_integration.py -q
```

Also run bounded existing regression tests covering merge/worker semantics if affected by the implementation, but DO NOT run `pytest tests/ -q` as executor T0/T1 work.

Final TASK-090 publication under the pre-cutover path remains responsible for exactly one canonical T2:

```text
venv\Scripts\python.exe -m pytest tests/ -q
```

Required TASK-090 evidence:

```text
EXECUTOR_AD_HOC_FULL_T2: NO
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
TARGETED_TESTS: PASS
FULL_CANONICAL: PASS
```

## 12. Forbidden Scope

Do not implement any of the following in TASK-090:

```text
Proof Carry-Forward live integration
invalidation-based test selection
dependency-impact graph selection
Delta + Impact FIX review orchestration
persistent Finding Registry
risk-adaptive live model routing
compact RESULT redesign
raw-log external artifact redesign
full supersession/cancellation workflow
finding-to-guardrail promotion
TASK-087
P1 capability integration lane
Python Agent pilot
P2
P3
H5-H8
automatic retry
automatic reroute
paid API calls
background daemon/service
```

## 13. Completion Boundary

TASK-090 PASS means Slice B is implemented and certified on its exact final head.

It does NOT mean:

```text
ADR-064 fully complete
P1 complete
TASK-087 executable
P2/P3 open
H5-H8 open
```

After TASK-090 PASS and merge, the next exact-baseline task is Slice C — FIX Proof Carry-Forward + Invalidation + Delta/Impact Review.