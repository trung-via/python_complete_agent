# REVIEW-090 — Review-First Certification + Deterministic Certification Job Integration
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-090
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 770dcbcf366fece68a379e7c59d5ef0e7773a615
REVIEWED_BASE_MAIN_SHA: bb4a30775c2deb2a37ebe763d1a74ce7e64d6ebe
TASK_ARTIFACT_BLOB_SHA: c2c633af4d7261667420908bb2d2c1eebb4e54c0
RESULT_BLOB_SHA: 5fc9ae1c96153d00d269b69546237aa7ac13bfd1
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 3
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: PASS
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
REQUIREMENT_BINDINGS_FINGERPRINT: 1a6b8cbcc76247d72de8ae1a11234a4b9a019fadeb31189cac353ccd36f06466
FIX_EXECUTION_MODE: IMPLEMENTATION
TASK_087_PREREQUISITE_ELIGIBLE: NO
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-090.md","blob_sha":"c2c633af4d7261667420908bb2d2c1eebb4e54c0"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/certification_job.py","tests/aios_bridge/test_certification_job.py","tests/aios_bridge/test_lean_review_integration.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: 770dcbcf366fece68a379e7c59d5ef0e7773a615
BASE_MAIN: bb4a30775c2deb2a37ebe763d1a74ce7e64d6ebe
MERGE_BASE: bb4a30775c2deb2a37ebe763d1a74ce7e64d6ebe
AHEAD: 1
BEHIND: 0
SCOPE_DRIFT: NO
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
FULL_CANONICAL: 2659 passed, 7 skipped, 0 failed
```

## Accepted / Do Not Reopen Without Regression

The following surfaces are accepted for this round and should remain protected unless the FIX touches them or tests prove regression:

```text
A1 task pipeline mode is explicit opt-in with legacy compatibility
A2 fenced mode examples do not activate review-first
A3 TASK-090 itself remains pre-cutover legacy
A4 candidate publication can defer certification-owned T2
A5 semantic acceptance is non-authoritative
A6 certify-reviewed is provider-neutral
A7 existing exact PASS is idempotent and does not rerun T2
A8 exact FAILED job forbids automatic retry
A9 different candidate job fails closed
A10 merge-reviewed derives FINAL_PASS before calling the existing merge gate
A11 roadmap/reviewed-head/base/fast-forward safety remains in the existing gate
A12 no model/executor polling counters are permitted in certification jobs
A13 raw T2 stdout is not persisted into the job record
A14 EVIDENCE_REFRESH cannot bypass semantic acceptance in review-first mode
A15 TASK-087 remains reserved
```

## Blocking Findings

### B1 — Deferred T2 is still rendered with a false success-looking exit code

For review-first candidate publication, `cmd_publish()` correctly defers a supplied full-canonical command and records AIOS-managed T2 count 0. However `test_rc` remains initialized to `0`, and RESULT rendering still writes the original full-suite command together with `Exit code: 0` even though that command was never executed.

This conflicts with TASK-090's requirement to record certification as deferred rather than falsely claim it occurred. The manifest is correct, but the human-facing Tests section creates contradictory evidence.

Required repair:

```text
DEFERRED_T2_COMMAND -> MUST NOT HAVE EXECUTED_EXIT_CODE_0
RESULT must distinguish NOT_EXECUTED/DEFERRED from an observed process exit code
candidate-stage authoritative T2 count remains 0
legacy mode output remains unchanged
```

Add a behavioral regression that executes the review-first candidate publication path with a supplied full-suite command and proves the generated RESULT cannot be interpreted as an executed successful T2.

### B2 — Certification can become PASS without post-T2 exact-subject revalidation

`_preflight_certify_reviewed()` proves exact task head/base/main/roadmap/local branch/worktree before T2 starts. `cmd_certify_reviewed()` then runs a long full suite and immediately persists `CERTIFICATION_PASS` from the process return code. It does not revalidate the exact candidate/worktree/control identity after the T2 wait.

During a 5–8 minute certification window, local HEAD/worktree or authoritative refs can drift. In particular, tests could run against a mutated worktree while the job remains bound to the preflight candidate SHA. `merge-reviewed` later rechecks remote merge safety, but that cannot prove the executed T2 actually observed the exact candidate throughout certification.

Required repair:

```text
T2 return
-> deterministic post-T2 trust revalidation
-> exact local branch/head still candidate
-> worktree still clean
-> remote task head/main still exact reviewed subject
-> authoritative task/review/roadmap binding still exact
-> only then CERTIFICATION_PASS authority may persist
```

If post-T2 subject/trust evidence drifted, persist no PASS authority and do not retry/reroute automatically. Reuse existing fail-closed trust helpers where practical rather than inventing a second permissive path.

Add behavioral regression coverage that mutates at least local worktree/head and one authoritative remote identity between preflight and terminalization and proves PASS cannot be created.

### B3 — `terminal_result_digest` is not verified when certification authority is loaded/consumed

`build_terminal_result_digest()` deterministically hashes bounded terminal facts, but `CertificationJob.from_dict()` currently only validates that `terminal_result_digest` is a lowercase 64-hex string. `_load_certification_job()` and `merge-reviewed` do not recompute the digest from the job's terminal facts before accepting `CERTIFICATION_PASS`.

Therefore the digest is presently decorative rather than verified machine evidence: a malformed/corrupted terminal record can carry any 64-hex digest and still satisfy finalization if the other fields are internally plausible.

Required repair:

```text
PASS/FAILED job load or authority consumption
-> recompute terminal digest from canonical bounded terminal facts
-> exact equality required
-> mismatch => fail closed
```

Prefer implementing one pure verification helper in `certification_job.py` and invoking it from the load/authority path. Add regression tests for valid digest acceptance and mismatched digest rejection before FINAL_PASS/merge authority.

## Validation / Scope Audit

Observed diff is restricted to TASK-090's authorized implementation paths plus generated RESULT. Main remains the exact bound base and task branch is one commit ahead / zero behind.

Canonical suite evidence is green and AIOS-managed T2 executed exactly once for TASK-090's pre-cutover publication. This evidence is accepted and MUST NOT be rerun merely to address prose; the FIX must run only targeted/impact tests during executor work, with final canonical certification remaining owned by the existing TASK-090 publication boundary.

## FIX Contract

Close B1–B3 only. Do not implement Slice C, Slice D, TASK-087, Proof Carry-Forward orchestration, guardrail promotion, risk-router live routing, or certification supersession beyond what is strictly necessary to fail closed on the current exact certification subject.

Required targeted tests include at minimum:

```text
venv\Scripts\python.exe -m pytest tests/aios_bridge/test_certification_job.py tests/aios_bridge/test_lean_review_integration.py -q
```

Run additional bounded impacted tests only if required by the changed surfaces. Do not run `pytest tests/ -q` as executor T0/T1 work.

## Decision

```text
TASK-090: CHANGES_REQUIRED
OPEN: B1 B2 B3
MERGE: NO
NEXT: $aios-worker FIX TASK-090
TASK_087: DO_NOT_RUN
```
