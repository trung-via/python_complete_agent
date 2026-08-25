# REVIEW-091 — FIX Proof Carry-Forward + Invalidation + Delta/Impact Review Integration
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-091
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: b1aa4bd9e7532fed0dca8abe384c63a1e781f5a7
REVIEWED_BASE_MAIN_SHA: 5a609040030a140c0b10be58f4c351dc17cbfb23
TASK_ARTIFACT_BLOB_SHA: 86cd8ded4a3d8cdf6b571098242a8f0f28aba38b
RESULT_BLOB_SHA: 0075853398d9667feba2abe19aa2699c21e0f6fe
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 4
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: DEFERRED_PENDING_SEMANTIC_ACCEPTANCE
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
REQUIREMENT_BINDINGS_FINGERPRINT: 11ed8d59df71c670f5264eff4f7fb6756828a0c83090b36d3998b21b1047c694
FIX_EXECUTION_MODE: IMPLEMENTATION
TASK_087_PREREQUISITE_ELIGIBLE: NO
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-091.md","blob_sha":"86cd8ded4a3d8cdf6b571098242a8f0f28aba38b"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/fix_review.py","src/aios_bridge/executor_context.py","src/aios_bridge/executor_automation.py","tests/aios_bridge/test_fix_review.py","tests/aios_bridge/test_executor_context_pack.py","tests/aios_bridge/test_lean_review_integration.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: b1aa4bd9e7532fed0dca8abe384c63a1e781f5a7
BASE_MAIN: 5a609040030a140c0b10be58f4c351dc17cbfb23
MERGE_BASE: 5a609040030a140c0b10be58f4c351dc17cbfb23
AHEAD: 1
BEHIND: 0
SCOPE_DRIFT: NO
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
SEMANTIC_REVIEW_REQUIRED: YES
```

Review-first cutover is functioning correctly: TASK-091 reached semantic review without paying final T2. This review therefore evaluates Slice-C semantics only. No certification is authorized while blockers remain.

## Accepted / Do Not Reopen Without Regression

The following surfaces are accepted for Round 1 and should remain protected unless this FIX touches them or a new regression invalidates them:

```text
A1 Slice-C mode is explicit opt-in and compatibility remains the default.
A2 FIX Context Pack uses a strict bounded closed schema and exact prior reviewed-head binding.
A3 Reviewer subject/dependency fingerprints are recomputed from exact Git blob evidence before optimization authority is accepted.
A4 Missing/unresolvable proof evidence becomes UNKNOWN rather than silently VALID.
A5 Known subject/dependency changes invalidate proof and select proof T1; unchanged VALID proof can carry forward.
A6 Actual delta outside the declared affected envelope expands impact conservatively.
A7 Existing executor allowed-path authority remains separate from impact evidence and still fails closed.
A8 Codex bounded executor context can carry a derived provider-neutral FIX Context Pack without changing authorization authority.
A9 TASK-091 candidate publication correctly deferred final T2: AIOS-managed candidate-stage T2 count = 0.
A10 TASK-090 certification/merge safety, no-auto-retry, no-auto-reroute, and TASK-087 reservation remain unchanged.
```

## Blocking Findings

### B1 — A proof can carry forward even when its own test/evidence path changed

`analyze_fix_impact()` recomputes the proof's subject and dependency fingerprints and additionally invalidates when `actual_changed_paths` intersects `subject_paths` or `dependency_paths`. It does not include the proof binding's `test_paths` in the invalidation surface. Therefore a FIX can modify the test/evidence source associated with a previously VALID proof while leaving subject/dependency blobs unchanged, and the machine can still report `CARRY_FORWARD_ALLOWED` and skip re-proofing that surface.

This is unsafe for Proof Carry-Forward: a proof whose evidence source changed is not the same reusable proof.

Required repair:

```text
actual delta touches proof.test_paths
-> proof MUST NOT carry forward
-> mark INVALIDATE (or UNKNOWN if evidence cannot be established)
-> include the proof's impacted tests in selected T1
-> next semantic review treats the proof/affected test envelope as invalidated
```

If `evidence_fingerprint` is intended to bind exact test-source evidence, recompute and verify it consistently; otherwise at minimum treat any actual change to a bound `test_paths` entry as deterministic invalidation. Do not invent a new proof registry in this task.

Required regression: a VALID proof with unchanged subject/dependency but a changed bound test path cannot appear in `carried_forward_proof_ids`.

### B2 — Delta + Impact evidence is computed before targeted T1, but final candidate may change during T1

`cmd_publish()` computes `slice_c_analysis` from the pre-test dirty worktree, derives `selected_test_paths`, runs the targeted T1 command, and later emits RESULT evidence from that original analysis. Existing post-test publication checks re-collect dirty paths for allowed-scope safety, but Slice-C impact analysis is not recomputed against the post-test/final worktree before the candidate is committed.

A test or hook that mutates a tracked allowed path can therefore make the final candidate differ from the delta that selected T1 and from the `actual_changed_paths`/proof state persisted in Delta + Impact evidence. This can create stale proof/review evidence even though the generic allowed-path gate still passes.

Required repair:

```text
pre-T1 impact analysis
-> run selected T1
-> collect final tracked worktree delta
-> deterministically revalidate Slice-C impact against final delta/blobs
-> final evidence MUST describe the exact candidate that will be committed
```

If targeted T1 itself changes tracked candidate content in a way that changes impact/test selection, fail closed rather than silently publishing stale evidence, unless a bounded deterministic re-selection/re-test loop can be proven without hidden retry semantics. The simplest safe rule is to reject tracked candidate mutation caused during T1.

Required regression: simulate targeted T1 changing an allowed tracked path after pre-test analysis and prove no candidate can publish with stale Delta + Impact evidence.

### B3 — Derived FIX Context Pack is delivered through the Codex execute path but not through the Antigravity implementation surface

The implementation augments `ExecutorContextPack` inside the automated launch plan used by `bridge.py execute`, which is the Codex path. The Antigravity worker contract intentionally does not invoke `bridge.py execute`; after handoff it returns `AUTHORIZED` and continues implementation in the same interactive Antigravity session. Consequently the recomputed proof decisions/selected impacted tests in the derived FIX Context Pack are not deterministically surfaced to Antigravity by this Slice-C implementation.

This does not expand authority, but it violates TASK-091's provider-neutral requirement that Codex and Antigravity receive the same semantic FIX pack contract. Requiring Antigravity to reconstruct proof state from raw review prose/JSON would also defeat the deterministic analysis performed by Bridge.

Required repair within the existing TASK-091 allowed implementation scope:

```text
Slice-C handoff + selected executor = antigravity
-> surface the same validated derived FIX Context Pack semantics to the interactive Antigravity session
-> no model call, no retry/reroute, no authority expansion
```

For example, Bridge may emit a bounded deterministic handoff context block produced from the same validated `FixContextPack + FixImpactAnalysis`; the exact transport can differ, but the semantic content and proof decisions must be the same. Codex may continue receiving the pack through its bounded executor invocation payload.

Required regression must cover both executor surfaces semantically; merely asserting that the rendered pack contains no provider name is insufficient to prove provider-neutral delivery.

### B4 — Fenced-marker parser can activate a marker that is still inside a valid outer fence

`_top_level_values()` tracks only the fence character (` or ~), not the opening fence length. A valid four-backtick fenced block may contain an inner triple-backtick sequence as literal content. The current parser treats that shorter inner sequence as closing the outer fence, so a subsequent `FIX_REVIEW_MODE` or `FIX_CONTEXT_PACK_JSON` line that is still inside the Markdown outer fence can be misclassified as top-level authority input.

This violates the explicit requirement that markers inside fenced prose/examples MUST NOT activate Slice C.

Required repair:

```text
opening fence -> remember delimiter character AND run length
closing fence -> same delimiter and run length >= opening length
shorter inner fence -> remains content
```

Add a regression with a four-backtick outer fence containing a triple-backtick example and Slice-C markers; mode must remain compatibility and no pack may activate. Preserve the existing simple triple-backtick/tilde behavior.

## Validation / Scope Audit

Observed candidate diff is restricted to TASK-091 authorized implementation paths plus generated RESULT. Main remains the exact bound base and the task branch is one commit ahead / zero behind.

Review-first publication evidence is correct and important:

```text
STATUS: READY_FOR_SEMANTIC_REVIEW
EXPECTED_AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_EXECUTION_COUNT: 0
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
CERTIFICATION_DEFERRED: YES
SEMANTIC_REVIEW_REQUIRED: YES
```

Do NOT run final canonical T2 for this CHANGES_REQUIRED candidate.

## FIX Contract

TASK-091 explicitly permits its own first semantic-review FIX to use the TASK-090 compatibility FIX path. Therefore this review intentionally does NOT opt into the newly implemented Slice-C FIX mode. Close B1-B4 using the existing review-first FIX path; candidate publication must still execute final T2 count = 0.

Required targeted/impact tests include at minimum:

```text
venv\Scripts\python.exe -m pytest tests/aios_bridge/test_fix_review.py tests/aios_bridge/test_executor_context_pack.py tests/aios_bridge/test_lean_review_integration.py -q
```

Run additional bounded existing impacted tests only if required by touched shared helpers. Do not run `pytest tests/ -q` during FIX. Final canonical T2 remains owned only by `certify-reviewed` after semantic acceptance.

## Decision

```text
TASK-091: CHANGES_REQUIRED
OPEN: B1 B2 B3 B4
FINAL_T2_NOW: NO
CERTIFICATION_NOW: NO
MERGE: NO
NEXT: $aios-worker FIX TASK-091
TASK_087: DO_NOT_RUN
```
