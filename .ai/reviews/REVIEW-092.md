# REVIEW-092 — Lean Review Slice D: Compact Evidence, Supersession, Guardrail Learning & Blocked Recovery
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-092
REVIEW_ROUND: 2
REVIEWED_TASK_HEAD_SHA: fce4526170213ae67db607bad3568330f4a12ca6
REVIEWED_BASE_MAIN_SHA: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
TASK_ARTIFACT_BLOB_SHA: 8031684cf59cc6259b8d870b0ceacd47a7d767c3
RESULT_BLOB_SHA: 09a8ad1c333f480a3d4776949b68ae6f7df9c585
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 2
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
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
FIX_CONTEXT_PACK_JSON: {"schema_version":"1","previous_reviewed_head_sha":"fce4526170213ae67db607bad3568330f4a12ca6","impact_confidence":"KNOWN","open_finding_ids":["B1","B3"],"affected_paths":["bridge.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"protected_accepted_paths":["src/aios_bridge/result_evidence.py","src/aios_bridge/certification_job.py","src/aios_bridge/blocked_recovery.py","src/aios_bridge/review_learning.py","src/aios_bridge/review_pipeline.py","tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_blocked_recovery.py","tests/aios_bridge/test_review_learning.py","tests/aios_bridge/test_review_pipeline.py"],"required_test_paths":["tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"unknown_impact_fallback_test_paths":["tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_lean_review_integration.py","tests/aios_bridge/test_certification_job.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"proof_bindings":[]}

## Snapshot

```text
HEAD: fce4526170213ae67db607bad3568330f4a12ca6
PREVIOUS_REVIEWED_HEAD: 65abd6f6f39c6103a29d925f618927f22de42aa0
BASE_MAIN: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
FIX_DELTA_COMMITS: 1
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
LATEST_EXECUTOR: antigravity
```

Round 2 is a Delta + Impact review. B2 and the accepted parts of B1/B3 are closed and MUST NOT be reopened unless this bounded FIX touches or regresses them.

## Closed Findings

### B2 — CLOSED

Stale terminal PASS/FAILED for a different candidate is now archived as non-current provenance and the new exact candidate may create its own PENDING job. Exact current PASS remains idempotent; exact current FAILED remains non-retryable; stale RUNNING still fails closed without invented cancellation.

### B1a — CLOSED: compact-head role and parser strictness

Schema v2 preserves the TASK-required `candidate_head_sha`, explicitly classifies it as `PRE_PUBLICATION_CONTENT_HEAD`, binds final published-head authority externally, ignores fenced authority markers, rejects duplicate JSON keys, and retains one compact machine source.

### B3a — CLOSED: normal Exception-path rollback and live blocked replacement

The successful Antigravity FIX proves the explicit-Human blocked-executor replacement path can recover from the prior Codex clean no-op. Handoff context construction is now inside the post-acquire transaction, and ordinary Python exceptions trigger deterministic lease/auth/state rollback.

## Remaining Blocking Findings

### B1 — Exact FIX base-main evidence is being degraded to UNKNOWN even though the exact base is available

The live compact RESULT for this candidate records:

```text
base_main_sha = UNKNOWN
```

But this FIX is bound by the authoritative review to exact base main `5570e64bec7522caf6b4ebda3b2f34ec45a11ebf`. The task allows UNKNOWN only when the value is unavailable by contract; for governed review-first FIX it is available from the exact review/base binding.

Required repair:

```text
RUN compact evidence -> exact handoff-bound base_main_sha
FIX compact evidence -> exact REVIEWED_BASE_MAIN_SHA / equivalent validated bound base
UNKNOWN -> only when the lifecycle genuinely has no exact base by contract
```

Do not change ResultEvidence schema v2. Propagate the exact already-validated base into FIX authorization/publication evidence. Add a behavioral regression proving review-first FIX RESULT emits the exact reviewed base rather than UNKNOWN.

### B3 — Handoff rollback misses SystemExit-class deterministic failures and therefore can still leak a pre-start lease

The new handoff transaction currently wraps `cmd_context(args)` with `except Exception`. However Bridge's canonical `fail()` terminates by raising `SystemExit`, which is not an `Exception`. `cmd_context()` calls `current_branch()`, and `current_branch()` uses checked Git; a deterministic Git failure reaches `fail()` and can therefore escape the rollback handler even though no executor has started.

Required repair:

```text
post-acquire pre-start deterministic CLI failure (SystemExit included)
+ executor provably not started
-> release exact newly acquired lease
-> restore prior authorization/state
-> read-back verify
-> then re-raise/fail

KeyboardInterrupt / uncertain start state
-> do not silently classify as safe deterministic rollback
```

Do not broadly swallow BaseException. Handle the Bridge's intentional SystemExit failure channel explicitly, alongside normal Exception failures.

Required regressions must exercise real handoff behavior:

```text
HANDOFF_CONTEXT_SYSTEMEXIT_BEFORE_START_RELEASES_NEW_LEASE
HANDOFF_CONTEXT_SYSTEMEXIT_RESTORES_PRIOR_AUTH_AND_STATE
ANTIGRAVITY_SYSTEMEXIT_PRE_START_HAS_NO_STALE_LEASE
CODEX_SYSTEMEXIT_PRE_START_HAS_NO_STALE_LEASE
NORMAL_EXCEPTION_PRE_START_ROLLBACK_REMAINS_GREEN
NO_AUTO_RETRY_OR_REROUTE
```

## Protected Accepted Surfaces

```text
compact ResultEvidence schema-v2 field contract and strict parser
certification supersession / exact-pass idempotency / exact-failed no-retry
finding lifecycle + risk evidence
bounded guardrail-promotion recommendation
structured clean-no-op blocker evidence
explicit-Human blocked-executor replacement
proof-reuse + Delta/Impact semantics
review-first T2=0 candidate publication
roadmap v1.2 / scope / lease / publication-trust / exact-head merge safety
TASK-087, P2/P3 and H5-H8 remain unopened
```

## Validation

Use only Slice-C selected impacted T1. Full canonical T2 remains forbidden until B1 and B3 close and semantic acceptance is issued.

## Decision

```text
TASK-092: CHANGES_REQUIRED
OPEN: B1 B3
CLOSED: B2 B1a B3a
FINAL_T2_NOW: NO
CERTIFICATION_NOW: NO
MERGE: NO
NEXT: FIX TASK-092 using the latest Round-2 review
TASK_087: DO_NOT_RUN
P1_FORMAL_COMPLETION: NO
```
