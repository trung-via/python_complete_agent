# REVIEW-097 — Codex Interactive Parity + Publication Safety Lock

PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
FINAL_PASS: NO
TASK_ID: TASK-097
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 2d1e321154c038fff01bd83ace319fa38ef2895c
REVIEWED_BASE_MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TASK_ARTIFACT_BLOB_SHA: eb05f54ab4f33a2fbe31515e00e7af134192b8df
RESULT_BLOB_SHA: 93c26c3fcac343825d3122bb75cb01c1f47b2470
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 2
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: NOT_RUN_AT_REVIEW
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
RECONCILIATION_ADR: ADR-067
RECONCILIATION_ADR_BLOB_SHA: db17c1b3f4a359c97f2dd59b8c90f7b7acdd7810
FIX_EXECUTION_MODE: IMPLEMENTATION
TASK_095_RESUME_AUTHORIZED: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-097.md","blob_sha":"eb05f54ab4f33a2fbe31515e00e7af134192b8df"},{"path":".ai/decisions/ADR-067-CODEX-INTERACTIVE-EXECUTOR-PARITY-RECOVERY-LOCK.md","blob_sha":"db17c1b3f4a359c97f2dd59b8c90f7b7acdd7810"}]
EXECUTOR_ALLOWED_PATHS_JSON: [".agents/skills/aios-worker/SKILL.md",".agents/skills/aios-worker/scripts/aios_worker.py",".agents/workflows/aios-worker.md","docs/AIOS_UNIFIED_WORKER_WORKFLOW.md","bridge.py","src/aios_bridge/worker_flow.py","src/aios_bridge/slim_runtime.py","tests/aios_bridge/test_worker_flow.py","tests/aios_bridge/test_aios_worker_control_surface.py","tests/aios_bridge/test_slim_context_cache.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Review summary

The clean parity direction is correct: normal Codex RUN/FIX no longer invokes `bridge.py execute`; the visible Codex session becomes the implementation executor; compact context is restored; adapter guidance is provider-exact; `task_authoring.py` is unchanged; RESULT reports targeted validation PASS with candidate-stage T2=0.

Two publication-safety blockers remain. They are both in the new root `bridge.py` interactive publish wrapper and must be fixed without widening scope.

## Finding B097.1 — Missing/invalid machine scope can fall through to publication

Severity: BLOCKING

The wrapper attempts to derive `allowed_paths`, but several failure paths are swallowed (`except Exception: pass`) and publication continues when `allowed_paths is None`. It also accepts fallback `auth['allowed_paths']`, which is not the exact current control-snapshot derivation required by TASK-097.

This violates the locked requirement:

```text
missing/stale/drifted authorization, lease, artifact, policy, roadmap, branch/head, or scope evidence -> FAIL CLOSED
allowed_paths authority -> exact machine-verified current control snapshot
```

Required fix:

- exact artifact blob lookup must exist and exactly equal the authorized blob; missing/empty lookup is failure, not success;
- unreadable or unparsable authorized artifact is failure;
- missing or malformed `EXECUTOR_ALLOWED_PATHS_JSON` is failure for normal interactive publication;
- remove fail-open `except ...: pass` behavior from the authoritative scope path;
- do not accept model/session/CLI or an unverified generic authorization field as replacement scope authority;
- require non-empty exact machine-derived `allowed_paths` before collecting dirty paths or entering canonical publish;
- pass that same exact scope into the existing post-test gate;
- add tests proving missing blob, unreadable artifact, malformed markers and absent scope all reject publication before legacy publish is invoked.

## Finding B097.2 — Publication trust still has a fail-open branch

Severity: BLOCKING

The wrapper catches trust errors and explicitly `pass`es when exception text contains `remote get-url` or `No such remote`. Publication then continues without a verified trust snapshot, while RESULT generation can still report `publication_trust_status=VERIFIED`.

This violates TASK-097's explicit contract:

```text
publication trust capture/verification failure -> FAIL CLOSED
RESULT VERIFIED -> only after actual successful trust path
FALSE_VERIFIED_PUBLICATION_TRUST -> FORBIDDEN
```

Required fix:

- every failure to capture or verify the publication-trust snapshot must fail closed;
- no exception-message whitelist may bypass trust authority;
- canonical publish must receive the exact verified snapshot so post-test revalidation runs;
- add a test for missing/invalid remote trust capture that proves no legacy publish/commit/push occurs;
- retain the existing protected-Git-admin drift test.

## Accepted surfaces that must remain unchanged

```text
NORMAL_CODEX_NESTED_EXECUTE: REMOVED
CODEX_INTERACTIVE_IMPLEMENTATION: ENABLED
CODEX_COMPACT_CONTEXT: ENABLED
CODEX_AUTHORIZED_GUIDANCE_BINDS_CODEX: PASS
ANTIGRAVITY_AUTHORIZED_GUIDANCE_BINDS_ANTIGRAVITY: PASS
TASK_AUTHORING_RELAXATION: NO
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_095_RESUME_AUTHORIZED: NO
```

## Re-review acceptance

```text
INTERACTIVE_ALLOWED_PATH_AUTHORITY: EXACT_MACHINE_CONTROL_SNAPSHOT
MISSING_SCOPE_EVIDENCE_FAILS_CLOSED: PASS
MALFORMED_SCOPE_EVIDENCE_FAILS_CLOSED: PASS
AUTH_ALLOWED_PATHS_FALLBACK: FORBIDDEN
INTERACTIVE_PUBLICATION_TRUST: VERIFIED_OR_FAIL_CLOSED
TRUST_EXCEPTION_WHITELIST: NONE
FALSE_VERIFIED_PUBLICATION_TRUST: FORBIDDEN
TARGETED_TEST_STATUS: PASS
CANDIDATE_STAGE_T2: 0
TASK_095_RESUME_AUTHORIZED: NO
```

After focused FIX publication, semantic re-review is required. Full canonical T2 remains exclusively `bridge.py certify-reviewed 97` after semantic acceptance.
