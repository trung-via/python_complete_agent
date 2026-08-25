# REVIEW-087 — P1.0B Failure Classification + Deterministic Next Action
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-087
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: dfbca7fc9c56f9d71c4591301f32b9a49bec47ba
REVIEWED_BASE_MAIN_SHA: ac0ae79e85e30a80410380188578db1993720b5b
TASK_ARTIFACT_BLOB_SHA: eb0d2455f6b98e6fa44a8db336dd78625e66820a
RESULT_BLOB_SHA: 283249f2ec653566bb6b00ec53d505b7fdcdb27b
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 4
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: NOT_RUN_REVIEW_FIRST
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
REQUIREMENT_BINDINGS_FINGERPRINT: d0c2a52e727d6042b2bf5aa22c0c4c5a94ab2229203ccfc44fb4578055523eba
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
FIX_EXECUTION_MODE: IMPLEMENTATION
FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
FIX_CONTEXT_PACK_JSON: {"schema_version":"1","previous_reviewed_head_sha":"dfbca7fc9c56f9d71c4591301f32b9a49bec47ba","impact_confidence":"KNOWN","open_finding_ids":["B1","B2","B3","B4"],"affected_paths":["bridge.py","src/aios_bridge/worker_failure.py","src/aios_bridge/worker_flow.py",".agents/skills/aios-worker/scripts/aios_worker.py","tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"protected_accepted_paths":[],"required_test_paths":["tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"unknown_impact_fallback_test_paths":["tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"],"proof_bindings":[]}
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-087.md","blob_sha":"eb0d2455f6b98e6fa44a8db336dd78625e66820a"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/worker_failure.py","src/aios_bridge/worker_flow.py",".agents/skills/aios-worker/scripts/aios_worker.py","tests/aios_bridge/test_worker_failure.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: dfbca7fc9c56f9d71c4591301f32b9a49bec47ba
BASE_MAIN: ac0ae79e85e30a80410380188578db1993720b5b
MERGE_BASE: ac0ae79e85e30a80410380188578db1993720b5b
AHEAD_FROM_MAIN: 1
BEHIND_MAIN: 0
MAIN_DRIFT: NO
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
TARGETED_TEST_STATUS: PASS
```

The Antigravity replacement produced a real bounded implementation delta. The candidate creates the requested pure worker-failure module and integrates structured output for the existing clean no-op path. Review-First publication is operating correctly and no canonical T2 has run for this candidate.

## Blockers

### B1 — Failure classification predicates are not fail-closed enough

`classify_worker_failure()` accepts `is_known_stopped` but does not use it in the decision. A TIMED_OUT observation with `is_known_stopped=False` can therefore become CLEAN_TIMEOUT or DIRTY_TIMEOUT_RECOVERY_REQUIRED even though TASK-087 requires known stopped/terminal evidence.

The classifier also accepts arbitrary uppercase terminal tokens and can classify unknown/non-timeout dirty failures as DIRTY_TIMEOUT_RECOVERY_REQUIRED. In addition, EXITED_NONZERO with uncertain scope (`allowed_paths=None`) is currently allowed to become PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE, and an EXITED_NONZERO head delta with no dirty paths can also become productive without proving the existing strict branch/head/scope gate.

Required repair:

- timeout classes require exact TIMED_OUT plus `is_known_stopped is True`;
- unknown/unsupported terminal status must fail closed rather than manufacture one of the four semantic classes;
- DIRTY_TIMEOUT_RECOVERY_REQUIRED must never be emitted for a non-timeout terminal status;
- PRODUCTIVE_NONZERO_RECOVERY_CANDIDATE requires exact EXITED_NONZERO, an actual preserved implementation delta, exact known scope/provenance success, and known stopped/terminal evidence;
- missing/unknown scope evidence cannot create productive-recovery authority;
- preserve the existing stricter Bridge Git/branch/head/scope gate rather than duplicating it loosely.

Add negative tests for `is_known_stopped=False`, unknown terminal token, missing/unknown scope evidence, non-timeout dirty failures, and head-only/non-proven productive recovery.

### B2 — Timeout/transport classifications are not delivered as machine evidence to the worker surface

Bridge persists `worker_failure_evidence` only for the EXITED_ZERO clean-no-op path. For TIMED_OUT/FAILED_TO_START/other transport endings it computes a `failure_evidence`, interpolates the class and next action into an error string, then calls the generic operational-failure boundary. The structured evidence is not persisted into authorization or another bounded machine-readable state field.

`WorkerFlowCoordinator`, however, surfaces `failure_class` / `next_action` only by reloading authorization and reading `worker_failure_evidence` (or the older clean-no-op blocker evidence). Therefore a real CLEAN_TIMEOUT or DIRTY_TIMEOUT path can fall back to generic EXECUTION_FAILED at the unified worker surface even though Bridge internally calculated a class.

Required repair:

- persist one exact structured worker-failure evidence record for owned terminal classes before exiting the deterministic Bridge boundary, using a provenance-safe status that does not fabricate publication/consumption;
- make RUN and FIX worker-flow continuations load and validate that record and emit exactly one machine `FAILURE_CLASS` + `NEXT_ACTION`;
- state/human text may be derived from the same evidence, but text must not be the only authority source;
- preserve lease/recovery behavior: dirty timeout must remain recovery-required and must block fresh execution; clean timeout must not create retry/reroute authority;
- Antigravity must not synthesize timeout facts that Bridge did not observe.

### B3 — WorkerFailureEvidence deserialization is coercive and can change authority meaning

`WorkerFailureEvidence.from_dict()` currently accepts a superset of fields and uses coercions such as `tuple(str(p) ...)`, `bool(...)`, and `str(...)`. Thus values such as the string `"false"` become boolean true, malformed sequence/scalar values can be silently converted, and extra fields are accepted. `human_guidance` is also not required to equal the deterministic text derived from `next_action`.

`WorkerFlowCoordinator` then consumes the authorization record with raw `.get()` calls instead of parsing it through the evidence contract, so tampered/malformed failure evidence can directly reach operator output.

Required repair:

- exact field-set validation for persisted WorkerFailureEvidence;
- exact JSON/list requirement before converting dirty paths to tuple;
- exact bools for `zero_worktree_delta` and `is_known_stopped` (bool coercion forbidden);
- exact bounded strings/tokens/SHA values without generic `str(...)` coercion;
- require `human_guidance == NEXT_ACTION_TO_HUMAN_TEXT[next_action]`;
- validate internal class/status/delta consistency, preferably by recomputing or using one deterministic validation helper;
- WorkerFlow must parse/validate structured evidence before surfacing it; malformed evidence fails closed.

### B4 — Required integration proofs are missing

The candidate adds only `tests/aios_bridge/test_worker_failure.py`. The TASK requires behavior-level proof across Bridge/worker control surfaces for timeout publication blocking, preserved dirty recovery, fresh-executor blocking, no automatic reset/stash/commit, structured worker output, provider-neutral policy parity, and TASK-092 blocked-replacement non-regression.

Unit tests of the pure classifier do not establish those integration properties.

Required impacted proofs must exercise the real integration seams, at minimum:

```text
CLEAN_TIMEOUT_NO_RESULT_PUBLICATION
DIRTY_TIMEOUT_BLOCKS_FRESH_EXECUTOR_START
DIRTY_TIMEOUT_DOES_NOT_AUTO_RESET_STASH_COMMIT
ONE_MACHINE_NEXT_ACTION_PER_BLOCKED_CLASSIFICATION through WorkerFlow/control surface
CODEX classification output from persisted evidence
ANTIGRAVITY policy parity without fabricated timeout observation
TASK_092_BLOCKED_REPLACEMENT_NOT_REGRESSED
REVIEW_FIRST_CANDIDATE_T2_ZERO / no candidate-stage full T2 regression
```

Use the existing allowed test files; do not weaken canonical tests and do not run full T2 during FIX publication.

## Protected Accepted Surfaces

Do not reopen unless the FIX touches or regresses them:

- TASK-087 now has a real implementation delta; NO_WORK_REQUIRED is not valid.
- closed enum includes the four requested failure classes and deterministic next-action mapping.
- clean EXITED_ZERO no-worktree-delta retains TASK-092 structured blocker compatibility and explicit-Human replacement semantics.
- Review-First candidate publication remains T2=0.
- compact RESULT remains the candidate publication evidence source.
- no automatic retry or automatic reroute.
- roadmap v1.2, lease, allowed-path, publication trust, reviewed-head and merge safety remain unchanged.
- capability batch, integration lane, Python Agent pilot, P2/P3 and H5-H8 remain out of scope.

## Decision

```text
TASK-087: CHANGES_REQUIRED
OPEN_BLOCKERS: B1 B2 B3 B4
FINAL_T2_NOW: NO
MERGE_NOW: NO
P1_FORMAL_COMPLETION: NO
```

The next FIX must remain bounded to B1-B4 and must publish a new review-first candidate with AIOS-managed T2 count still equal to zero.