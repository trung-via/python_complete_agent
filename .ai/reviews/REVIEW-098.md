# REVIEW-098 — AIOS Bridge Kernel v1 Candidate Path Bootstrap

PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
FINAL_PASS: NO
TASK_ID: TASK-098
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: f333fd2559b4e6ec46a6c775c43f1b4d02f808b1
REVIEWED_BASE_MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TASK_ARTIFACT_BLOB_SHA: 381434e362960cfa2ab0bab2c117767042aa3327
RESULT_BLOB_SHA: 93b2ab04e7d99e8114bc87e0f25a40b6917655dd
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 5
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: NOT_RUN_AT_REVIEW
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
RECONCILIATION_ADR: ADR-068
RECONCILIATION_ADR_BLOB_SHA: 1778dde9dc5efcb43ad8b07053436696cec5d1bb
FIX_EXECUTION_MODE: IMPLEMENTATION
TASK_095_RESUME_AUTHORIZED: NO
KERNEL_DEFAULT_CUTOVER_AUTHORIZED: NO
NEXT_KERNEL_TASK_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-098.md","blob_sha":"381434e362960cfa2ab0bab2c117767042aa3327"},{"path":".ai/decisions/ADR-068-AIOS-BRIDGE-KERNEL-V1-EXECUTION-LIFECYCLE-LOCK.md","blob_sha":"1778dde9dc5efcb43ad8b07053436696cec5d1bb"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["aios_kernel.py","src/aios_bridge/kernel/__init__.py","src/aios_bridge/kernel/model.py","src/aios_bridge/kernel/gitops.py","src/aios_bridge/kernel/authority.py","src/aios_bridge/kernel/context.py","src/aios_bridge/kernel/verify.py","src/aios_bridge/kernel/publish.py","src/aios_bridge/kernel/cli.py",".agents/skills/aios-kernel-worker/SKILL.md",".agents/skills/aios-kernel-worker/scripts/aios_kernel_worker.py",".agents/workflows/aios-kernel-worker.md","docs/AIOS_BRIDGE_KERNEL_V1.md",".gitignore","tests/aios_bridge/kernel/test_model.py","tests/aios_bridge/kernel/test_authority.py","tests/aios_bridge/kernel/test_context.py","tests/aios_bridge/kernel/test_verify.py","tests/aios_bridge/kernel/test_publish.py","tests/aios_bridge/kernel/test_cli.py","tests/test_aios_kernel.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Review summary

The rebuild direction is accepted: Kernel v1 is isolated beside legacy Bridge; no legacy normal-path files are modified; there is no model-launch command; visible Codex/Antigravity surfaces are structurally provider-parallel; VERIFY uses synchronous subprocess waiting; RESULT reports bootstrap targeted validation PASS with candidate-stage T2=0.

The first candidate is not yet safe enough for merge. Five bounded blockers remain, all inside the new Kernel candidate path.

## B098.1 — AUTHORIZE is not yet exact-control / exact-branch fail-closed

`read_control_file()` falls back from `origin/ai-control` to a local workspace file. `authorize_kernel_task()` ignores control fetch failure, accepts either known executor without validating the TASK dispatch policy, does not bind/revalidate the exact remote Git blob identity, and does not prepare/switch the exact task branch from exact remote main. `pre_execution_head` can therefore be whatever branch/head happened to be current when authorize ran.

Required fix:

- production authority must come from exact fetched remote `ai-control`; no local workspace fallback in the authority path;
- fetch/read failures fail closed;
- bind exact Git blob identity of TASK, and exact REVIEW blob for FIX;
- validate the selected executor against exact TASK/FIX dispatch authority rather than merely checking `codex|antigravity` vocabulary;
- FIX must validate exact CHANGES_REQUIRED review binding to task/candidate, not a substring alone;
- fetch exact remote main freshly, require safe/clean state, and create/reset/switch `ai/task-N` from that exact main only under the task contract;
- `pre_execution_head` must equal the exact prepared task head;
- `complete` must revalidate the authorized TASK/REVIEW blob identities before VERIFY.

## B098.2 — VERIFY can PASS without executing both canonical T0 and T1

AUTHORIZE permits empty/missing `t0` or `t1` arrays. `run_kernel_verify()` skips an empty tier and can return `passed=True`; PUBLISH then writes both `VERIFY_T0_STATUS: PASS` and `VERIFY_T1_STATUS: PASS` unconditionally.

Required fix:

- exact TASK marker must contain one non-empty argv array for T0 and one non-empty argv array for T1;
- malformed, empty, extra/unknown canonical tier shapes fail authorization;
- VERIFY success requires `t0_executed is True` and `t1_executed is True` with both exit codes 0;
- RESULT must derive tier status from actual verify evidence, never hard-code PASS;
- tests must prove missing T0, missing T1 and empty tier commands cannot produce PUBLISHED.

## B098.3 — COMPLETE preflight/trust errors can leave AUTHORIZED state behind

Only an ordinary T0/T1 test failure transitions the record to BLOCKED. Branch mismatch, empty delta, out-of-scope delta, fingerprint mismatch, main drift, publication-trust failure and other exceptions raise while leaving the record AUTHORIZED.

This violates the explicit Kernel invariant: every failure after AUTHORIZE terminates in BLOCKED or CANCELLED; orphan ACTIVE/authorized ambiguity must be structurally absent.

Required fix:

- one bounded COMPLETE failure boundary must terminalize BLOCKED for every failure after loading an exact AUTHORIZED record;
- preserve work; commit/push count stays zero on all pre-publication failures;
- do not swallow the original reason; persist/return a bounded reason if needed without adding a generalized failure subsystem;
- tests must cover branch mismatch, scope failure, main drift and trust failure and assert stored status == BLOCKED.

## B098.4 — Post-VERIFY publication revalidation is incomplete

After T0/T1 pass, current code revalidates publication trust only, then writes RESULT and runs `git add .`. It does not revalidate branch, HEAD, main, or changed-path scope after tests. A test process could mutate files/HEAD/branch and those changes could be staged and published.

Required fix:

After VERIFY PASS and before RESULT/commit:

- require current branch still exact target branch;
- require HEAD still exact pre-VERIFY head (tests must not commit/move HEAD);
- freshly re-observe remote main and require it still equals authorized base;
- recompute changed paths and require the exact post-test set is non-empty and subset of allowed paths;
- RESULT path itself is the only Kernel-generated addition permitted after this scope check;
- revalidate publication trust;
- stage exact intended paths, not unrestricted `git add .`;
- push once, then freshly observe remote task ref and require exact published identity.

Remote ref checks used for authority must be fresh observations, not silently stale remote-tracking refs.

## B098.5 — Kernel worker script resolves the wrong repository root

`.agents/skills/aios-kernel-worker/scripts/aios_kernel_worker.py` uses `Path(__file__).resolve().parents[3]`. From this file location, that resolves to `.agents/`, not repository root. The real `$aios-kernel-worker` / `/aios-kernel-worker` surface can therefore fail imports or store runtime state under the wrong directory.

Required fix:

- resolve the actual repository root deterministically (for the current layout this is one level above `.agents`);
- add a real-layout control-surface test proving the script imports Kernel modules and targets the repository root, not `.agents`;
- do not rely on ambient PYTHONPATH/cwd to mask the path bug.

## Accepted surfaces — do not reopen

```text
LEGACY_BRIDGE_CHANGED: NO
KERNEL_MODEL_LAUNCH_COMMAND: NONE
NESTED_CODEX_INVOCATION: 0
PROVIDER_PARALLEL_VISIBLE_SESSION_SHAPE: ACCEPTED
KERNEL_SYNC_SUBPROCESS_WAIT: ACCEPTED
MODEL_TIMER_POLLING_REQUIRED: NO
DEFAULT_CUTOVER: NO
TASK_095_RESUME_AUTHORIZED: NO
KERNEL_REVIEW_CERTIFY_MERGE_IMPLEMENTED: NO
```

## Re-review acceptance

```text
AUTHORIZE_REMOTE_CONTROL_ONLY: PASS
TASK_REVIEW_GIT_BLOB_BINDING: EXACT
TASK_BRANCH_PREPARED_FROM_FRESH_REMOTE_MAIN: PASS
DISPATCH_EXECUTOR_AUTHORITY: EXACT
T0_REQUIRED_NONEMPTY: PASS
T1_REQUIRED_NONEMPTY: PASS
T0_AUTHORITATIVE_COUNT: 1
T1_AUTHORITATIVE_COUNT: 1
FALSE_TIER_PASS_EVIDENCE: FORBIDDEN
ALL_COMPLETE_FAILURES_TERMINALIZE_BLOCKED: PASS
POST_VERIFY_BRANCH_HEAD_MAIN_SCOPE_REVALIDATION: PASS
UNRESTRICTED_GIT_ADD_DOT: REMOVED
REMOTE_POST_PUBLISH_IDENTITY_FRESH: PASS
KERNEL_WORKER_REPO_ROOT: EXACT
TARGETED_TEST_STATUS: PASS
CANDIDATE_STAGE_T2: 0
```

After focused FIX publication, semantic re-review is required. Full canonical T2 remains exclusively old `bridge.py certify-reviewed 98` after semantic acceptance. TASK-099 is not authorized until TASK-098 is certified and merged.