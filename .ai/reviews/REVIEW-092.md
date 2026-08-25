# REVIEW-092 — Lean Review Slice D: Compact Evidence, Supersession, Guardrail Learning & Blocked Recovery
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-092
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 65abd6f6f39c6103a29d925f618927f22de42aa0
REVIEWED_BASE_MAIN_SHA: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
TASK_ARTIFACT_BLOB_SHA: 8031684cf59cc6259b8d870b0ceacd47a7d767c3
RESULT_BLOB_SHA: d93eeadd41b39e98af1b55f3cab414ee4d8c33b2
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 3
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: DEFERRED_PENDING_SEMANTIC_ACCEPTANCE
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
REQUIREMENT_BINDINGS_FINGERPRINT: 82ada616254ac56f89c78c05c9c01f4707b923aa4db8804ed5a18067a3e05ec3
FIX_EXECUTION_MODE: IMPLEMENTATION
TASK_087_PREREQUISITE_ELIGIBLE: NO
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-092.md","blob_sha":"8031684cf59cc6259b8d870b0ceacd47a7d767c3"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/result_evidence.py","tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
FIX_CONTEXT_PACK_JSON: {"schema_version":"1","previous_reviewed_head_sha":"65abd6f6f39c6103a29d925f618927f22de42aa0","impact_confidence":"KNOWN","open_finding_ids":["B1","B2","B3"],"affected_paths":["bridge.py","src/aios_bridge/result_evidence.py","tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"protected_accepted_paths":["src/aios_bridge/blocked_recovery.py","src/aios_bridge/review_learning.py","src/aios_bridge/review_pipeline.py","tests/aios_bridge/test_blocked_recovery.py","tests/aios_bridge/test_review_learning.py","tests/aios_bridge/test_review_pipeline.py"],"required_test_paths":["tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"unknown_impact_fallback_test_paths":["tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/aios_bridge/test_certification_job.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"proof_bindings":[]}

## Snapshot

```text
HEAD: 65abd6f6f39c6103a29d925f618927f22de42aa0
BASE_MAIN: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
MERGE_BASE: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
AHEAD: 1
BEHIND: 0
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
```

Round 1 is the semantic blocker sweep for Slice D. Final canonical T2 remains forbidden until all blockers close and this review becomes `SEMANTICALLY_ACCEPTED_PENDING_T2`.

## Blocking Findings

### B1 — Compact RESULT subject identity is self-referential / currently misbound, and the authority parser is not truly top-level strict

`cmd_publish()` constructs `ResultEvidence` before RESULT is written and before the publication commit is created. It assigns `candidate_head_sha=post_test_head`, then writes/stages RESULT, commits, and only afterwards obtains the actual published SHA. Therefore the serialized `candidate_head_sha` identifies the pre-publication parent, not the reviewed/published commit containing the RESULT.

Do not try to solve this by predicting or iterating a Git commit SHA. A commit cannot safely contain its own final SHA as ordinary content because that creates a content-addressed self-reference.

Required repair:

```text
RESULT machine evidence must never label the pre-publication parent as the final candidate head.
Exact reviewed-head authority remains externally bound by Git/ref + REVIEWED_TASK_HEAD_SHA.
The compact RESULT must use a non-self-referential candidate identity contract.
```

Use a bounded versioned schema such as:

```text
candidate_parent_sha = exact pre-publication HEAD
candidate_head_binding = EXTERNAL_GIT_COMMIT
candidate_content_fingerprint = deterministic fingerprint over the bounded candidate evidence/content subject excluding the RESULT self-reference
```

Equivalent naming is acceptable if the semantics are exact. The parser/caller must accept the externally observed published head as the reviewed subject where exact-head verification is needed. Do not weaken existing REVIEW/certification/merge exact-head checks.

Also harden `parse_result_evidence()` so `RESULT_EVIDENCE_JSON:` is accepted only as the single true top-level authority marker; a marker inside a fenced example/body must not become authority. Strict JSON parsing must reject duplicate object keys rather than silently taking the last value.

Required regressions:

```text
COMPACT_RESULT_NEVER_MISLABELS_PARENT_AS_FINAL_HEAD
COMPACT_RESULT_EXTERNAL_HEAD_BINDING_PRESERVES_EXACT_REVIEW_AUTHORITY
FENCED_RESULT_EVIDENCE_MARKER_IS_NOT_AUTHORITY
DUPLICATE_JSON_KEY_FAILS_CLOSED
REVIEW_FIRST_RESULT_HAS_ONE_MACHINE_AUTHORITY
```

### B2 — Stale terminal certification becomes a permanent dead-end for a legitimate new candidate

`cmd_certify_reviewed()` correctly detects that an existing certification job belongs to a different candidate. A stale PENDING job is transitioned to SUPERSEDED and the new candidate can proceed. But a stale terminal PASS/FAILED job is archived and then the command fails while leaving the same stale terminal `job.json` as the current pointer. The next call loads it again and fails again. A new FIX candidate can therefore never obtain its own certification after an older terminal job exists for the same task.

Required repair:

```text
exact current PASS -> idempotent return; T2 rerun = 0
exact current FAILED -> fail; no automatic retry
stale PENDING -> SUPERSEDED + archive/non-current -> new candidate may create PENDING
stale PASS/FAILED -> archive as immutable non-current provenance -> clear/replace current pointer -> new candidate may create its own PENDING
stale RUNNING -> no invented cancellation; fail closed / recovery until safe terminal handling
```

Do not mutate a terminal PASS/FAILED into a transition its contract forbids. Preserve it exactly in history, but it must cease to be the current authority pointer after candidate supersession. Old PASS must never authorize the new head, and old FAILED must not prohibit certification of a different exact candidate.

Update the existing integration test that currently expects every different-candidate terminal job to block forever.

Required regressions:

```text
OLD_CERT_PASS_CANNOT_AUTHORIZE_NEW_HEAD
STALE_TERMINAL_PASS_ARCHIVED_THEN_NEW_CANDIDATE_CAN_CERTIFY
STALE_TERMINAL_FAILED_ARCHIVED_THEN_NEW_CANDIDATE_CAN_CERTIFY
EXACT_FAILED_CANDIDATE_STILL_CANNOT_AUTO_RETRY
EXACT_PASS_REMAINS_IDEMPOTENT_WITH_ZERO_SECOND_T2
STALE_RUNNING_REMAINS_FAIL_CLOSED_WITHOUT_FAKE_CANCELLATION
```

### B3 — Pre-start lease rollback is Codex-execute-only; handoff can still leak a lease before any executor starts

The new `_rollback_proven_pre_start_failure()` is called from Codex `cmd_execute()` pre-invocation validation. However `cmd_handoff()` still acquires a lease, persists ACTIVE authorization, updates state, and then calls `cmd_context(args)` with no rollback wrapper. If context construction/rendering fails there, the executor has not started, yet the lease/auth can remain active — the same stale-lease failure class Slice D was intended to close, including the Antigravity path.

Required repair:

```text
validate everything possible before lease acquisition
then acquire/persist lease
then perform any unavoidable post-acquire pre-start step
if that step fails AND executor is provably not started:
    release exact new lease
    restore exact prior authorization/state
    prove read-back
    no stale lease
if start state is uncertain:
    RECOVERY_REQUIRED; no unsafe auto-release
```

At minimum, the final handoff context/rendering boundary must be covered for both Codex and Antigravity. Prefer one shared provider-neutral pre-start transaction boundary rather than duplicating recovery logic.

Required regression must exercise the real `cmd_handoff()` post-acquire failure path, not `_rollback_proven_pre_start_failure()` in isolation:

```text
HANDOFF_CONTEXT_FAILURE_BEFORE_START_RELEASES_NEW_LEASE
HANDOFF_CONTEXT_FAILURE_RESTORES_PRIOR_AUTH_AND_STATE
ANTIGRAVITY_PRE_START_FAILURE_HAS_NO_STALE_LEASE
CODEX_PRE_START_FAILURE_HAS_NO_STALE_LEASE
UNCERTAIN_EXECUTOR_START_STATE_STILL_REQUIRES_RECOVERY
NO_AUTO_RETRY_OR_REROUTE
```

## Accepted / Protected Unless Impact Evidence Reopens

```text
A1 Review-first publication remains T2=0 before semantic acceptance.
A2 Compact ResultEvidence has a bounded exact schema, canonical JSON and no raw model/executor reasoning fields.
A3 FindingRegistry reuses the closed FindingRecord lifecycle and binds exact review round/head.
A4 Risk evidence remains deterministic and can produce CRITICAL_SECOND_REVIEW evidence without auto-invoking a model.
A5 Guardrail promotion is recommendation-only; no repository mutation or authority expansion.
A6 Structured CLEAN_NO_WORKTREE_DELTA blocker evidence contains bounded facts and no raw final-agent prose/reasoning.
A7 Blocked-executor replacement requires explicit Human selection, a different executor, zero delta, exact head, clean worktree and no active lease; it does not fake CONSUMED or synthesize a source RESULT.
A8 Existing allowed-path, roadmap v1.2, lease and publication trust gates remain fail-closed.
A9 Review-first exact-head merge safety and terminal digest verification remain intact.
A10 TASK-087, P2/P3 and H5-H8 remain unopened.
```

The fact that TASK-092's own RESULT was emitted in the pre-Slice-D legacy review-first format is not itself a blocker: the publishing process was already running the pre-change Bridge code. The FIX candidate must be published by the newly loaded code and therefore becomes the first useful live proof of the corrected compact RESULT path.

## Delta / Impact FIX Contract

This review intentionally activates Slice C for TASK-092's FIX round.

```text
FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
impact confidence: KNOWN
open findings: B1 B2 B3
proof_bindings: empty (no unsupported proof carry-forward claims)
protected accepted surfaces: review learning + finding/risk contracts + blocked-recovery pure contract
required T1: compact-result + lean-review integration + bridge automation/bridge tests
unknown fallback: same plus certification-job contract tests
```

Actual changes escaping the declared affected envelope must expand impact fail-conservatively. Existing TASK write scope remains the hard authority boundary; this pack never expands it.

## Validation / Scope Audit

Candidate `65abd6f6...` is one commit ahead of exact main `5570e64b...`, behind count zero. The implementation changed eight authorized files plus generated RESULT; no TASK-087/P2/P3/H5-H8 scope was opened.

Candidate publication correctly deferred final certification:

```text
STATUS: READY_FOR_SEMANTIC_REVIEW
AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
SEMANTIC_REVIEW_REQUIRED: YES
```

Do not run `certify-reviewed 92` while B1-B3 remain open.

## Decision

```text
TASK-092: CHANGES_REQUIRED
OPEN: B1 B2 B3
FINAL_T2_NOW: NO
CERTIFICATION_NOW: NO
MERGE: NO
NEXT: $aios-worker FIX TASK-092
TASK_087: DO_NOT_RUN
P1_FORMAL_COMPLETION: NO
```
