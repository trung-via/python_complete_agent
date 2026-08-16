# REVIEW-021 — TASK-021 Brain-Neutral Contract

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `2`
- Reviewed branch: `ai/task-021`
- Reviewed branch head: `556937faedc428590a932d045c25a9d523358c9a`
- Tested implementation SHA: `dbe740eed70cc2e81532cd0eb52722174164eab9`
- Previous reviewed head: `1e15abe3170bba4d96edfa274358f1c20bb945a5`
- Base main: `5c93561bf08d7fb0ed91c9199b0ae023c8b1ea4b`
- Implementation-to-reviewed-head relation: one evidence-only RESULT update after the tested implementation; production code/tests at reviewed head equal tested implementation.
- Review mode: ADR-013 Round-2 delta-first. Reviewed previous REVIEW, new RESULT, FIX implementation patch, and finding-scoped tests only. No full TASK/ADR/source/test reload.

## Finding Closure

### R1-1 — BrainResult pointer-only persistence
RESOLVED.

- Direct `bounded_content` persistence was removed.
- `BrainResult` now stores `artifact_ref` or `evidence_ref` plus deterministic metadata.
- Raw result-body fields such as `bounded_content`, `transcript`, `reasoning`, and `raw_output` are rejected as unknown schema fields.
- SUCCESS payload exclusivity is enforced and pointer-based BOUNDED_TEXT evidence is tested.

### R1-2 — Output contract/result semantic compatibility
PARTIALLY RESOLVED.

Resolved parts:
- operation/output compatibility is now closed and explicit;
- silent default `TASK_ARTIFACT` output contract was removed;
- SUCCESS requires exactly one authoritative payload pointer;
- TASK and REVIEW artifact role/task mismatches are rejected;
- result payload/type compatibility is materially stronger.

One semantic boundary remains:

#### R2-1 — Artifact-producing BrainRequest can still omit its target artifact pointer

The current BrainRequest validation only checks `target_artifact_path` **if it is not None**. Therefore requests such as `operation=REVIEW`, `expected_output_type=REVIEW_ARTIFACT`, `target_artifact_path=None` still pass even though Round-1 required artifact output types to require a target/artifact pointer.

Required fix:
- for every `*_ARTIFACT` expected output type, require a non-null `target_artifact_path`;
- BOUNDED_TEXT may remain pointer-target optional if that is the intended neutral contract;
- add a focused negative test proving an artifact-producing request with no target path fails closed.

#### R2-2 — PLAN / DIAGNOSIS / PATCH_PROPOSAL artifact role validation is task-aware but not role-aware

`_validate_artifact_role_and_task()` strictly maps TASK_ARTIFACT to `.ai/tasks/...` and REVIEW_ARTIFACT to `.ai/reviews/...`, but for PLAN_ARTIFACT / DIAGNOSIS_ARTIFACT / PATCH_PROPOSAL_ARTIFACT it only checks whether the task identity appears somewhere in the path. This still permits obvious role mismatches such as a PLAN artifact stored under `.ai/tasks/...` or `.ai/reviews/...` as long as `TASK-021` appears in the filename.

Required fix:
- make artifact-role validation deterministic for all artifact output types, not only TASK/REVIEW;
- use a conservative allowed namespace/role mapping consistent with existing AIOS conventions; `.ai/context/` is acceptable for PLAN/DIAGNOSIS/PATCH_PROPOSAL if no more specific locked namespace exists;
- at minimum fail closed on obvious cross-role namespace mismatches;
- add focused negative tests for wrong-role PLAN/DIAGNOSIS/PATCH artifact paths.

## Evidence
- FIX implementation commit: `dbe740eed70cc2e81532cd0eb52722174164eab9`.
- Final reviewed head: `556937faedc428590a932d045c25a9d523358c9a`; only `.ai/results/RESULT-021.md` changes after the tested implementation.
- RESULT reports Continuity `49 passed`, Bridge `135 passed`, full repository `609 passed`, zero regressions.
- `LIVE_EXTERNAL_CALLS: 0`.
- `TELEMETRY_MODEL_TURNS_ADDED: 0`.
- `BRIDGE_V0_4_BEHAVIOR_CHANGED: NO`.
- `AUTHORITY_WIDENED: NO`.
- `EXECUTOR_PLAN_OWNER: antigravity` and `CHATGPT_IMPLEMENTATION_PLAN_USED: NO` remain satisfied.

## Final FIX Scope
Expected delta remains small and should normally be limited to:

```text
src/aios_bridge/continuity/brain.py
tests/aios_bridge/continuity/test_brain.py
.ai/results/RESULT-021.md
```

`src/aios_bridge/continuity/__init__.py` should not need further change unless a public contract symbol genuinely changes.

No Bridge/provider/router/failover/executor/authority changes.

## Decision

`CHANGES_REQUIRED`

R1-1 is fully closed and most of R1-2 is correct. Fix only the remaining artifact-target requirement and full role-path validation. Round 3 should be a tiny delta review.