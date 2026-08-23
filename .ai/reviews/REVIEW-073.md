# REVIEW-073 — Codex E4 Implementation Intent & Clean No-Op Recovery Hardening

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-073
REVIEWED_TASK_HEAD_SHA: a31fa5855e00dfea5e402094b1c36c88101abcf9
REVIEWED_BASE_MAIN_SHA: 0f803c2d66244147734c5b8f5ea3670c6f57c6cc
TASK_ARTIFACT_BLOB_SHA: e7ae0512772c3b2a456201363821f838f9ee10b7
RESULT_BLOB_SHA: 96080be61c4f4e787da98860fb23cd4e5e75ec98
EXECUTOR_ID: antigravity
TASK_073_PASS: NO
TASK_072_RERUN_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Machine-Readable FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-073.md","blob_sha":"e7ae0512772c3b2a456201363821f838f9ee10b7"},{"path":".ai/decisions/ADR-044-EXECUTABLE-TASK-AUTHORING-PREFLIGHT-ZERO-TOUCH-START-CONTRACT-LOCK.md","blob_sha":"24b212d96d5fa650241a71049ce114f7a3a85489"},{"path":".ai/decisions/ADR-046-CODEX-E4-IMPLEMENTATION-INTENT-CLEAN-NOOP-RECOVERY-CONTRACT-LOCK.md","blob_sha":"de5b63eb0c23681ec3feb427f44b91d8f44151c0"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/executor_context.py","tests/aios_bridge/test_executor_context_pack.py","tests/test_bridge_executor_automation.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The publisher profile and three marker lines above are the complete E4 FIX inputs. They create no retry, reroute, paid-provider, merge, Codex rerun, or TASK-072 execution authority.

## Reviewed Snapshot

```text
BASE_MAIN_SHA: 0f803c2d66244147734c5b8f5ea3670c6f57c6cc
BRANCH: ai/task-073
REVIEWED_TASK_HEAD_SHA: a31fa5855e00dfea5e402094b1c36c88101abcf9
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 0f803c2d66244147734c5b8f5ea3670c6f57c6cc
```

Cumulative implementation scope is exact: `bridge.py`, `src/aios_bridge/executor_context.py`, `tests/aios_bridge/test_executor_context_pack.py`, `tests/test_bridge_executor_automation.py`, plus Bridge-generated `.ai/results/RESULT-073.md`.

## Passing Findings

### A — Executor-facing implementation intent

PASS.

The canonical thin executor instructions now explicitly state that RUN/FIX is implementation execution, an authorized non-empty worktree delta is required, a no-op turn is protocol failure, blocked executors must report a blocker, and commit/push/publish/merge remain forbidden.

### B — Exact clean no-op predicate

PASS.

`is_exact_clean_noop()` requires `EXITED_ZERO`, exact authorized branch identity, unchanged HEAD, and zero dirty paths. It is reached only after publication-trust verification has succeeded. Branch/head drift, transport failure, and dirty executions do not enter this path.

### C — No-op lease/auth cleanup core behavior

PASS WITH ONE PERSISTENCE-PROOF BLOCKER BELOW.

The implementation releases the already-verified exact lease, writes authorization status `EXECUTION_BLOCKED`, does not fabricate a published SHA, does not publish, does not retry/reroute, and routes dirty/drift/transport failures through existing fail-closed behavior.

### D — Tests / scope

PASS.

```text
TARGETED_TESTS: 103 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2253 passed, 7 skipped, 0 failed
AUTO_RETRY_INTRODUCED: NO
AUTO_REROUTE_INTRODUCED: NO
PAID_API_AUTHORITY_CHANGED: NO
```

## Blocker B1 — Cleanup persistence proof is not fully fail-closed

STATUS: FAIL / BLOCKER

ADR-046 requires that clean-no-op cleanup be considered successful only when lease release **and authorization/state persistence are proven**. If authorization/state persistence cannot be proven, the operational outcome must be `RECOVERY_REQUIRED` rather than pretending the blocked cleanup is complete.

Two concrete gaps remain in `bridge.py`:

### B1.1 Authorization read-back verifies only `status`

Current logic writes a full copied authorization record with `status = EXECUTION_BLOCKED`, then treats persistence as proven when the reloaded object is merely a dict whose `status` equals `EXECUTION_BLOCKED`.

That does not prove preservation of the exact original task/artifact/executor/lease/workspace/execution fingerprint audit bindings required by ADR-046.

Required fix:

```text
expected_blocked_auth = exact original auth copy with only status changed
save_authorization(..., expected_blocked_auth)
read_back = load_authorization(...)
SUCCESS only if read_back == expected_blocked_auth exactly
otherwise cleanup is unproven -> RECOVERY_REQUIRED
```

Do not silently repair or reconstruct mismatched fields.

Add a regression test where read-back returns `EXECUTION_BLOCKED` status but one preserved binding (for example lease_fingerprint or artifact_blob_sha) is changed; cleanup must not be classified successful.

### B1.2 Operational-state persistence failure has no RECOVERY_REQUIRED fallback attempt

The clean-no-op path computes `final_status = EXECUTION_BLOCKED` after lease/auth cleanup, then calls the generic `_e4_operational_failure()`. That helper attempts `update_state(EXECUTION_BLOCKED, ...)`; if that write throws, it only appends `operational state update also failed` to the message and exits.

For this cleanup transaction, ADR-046 requires the system to treat an unproven state write as recovery-required. The clean-no-op path needs an explicit bounded state-persistence transaction or dedicated helper:

```text
try persist EXECUTION_BLOCKED
  -> success: fail command with blocked diagnostic
except:
  -> attempt persist RECOVERY_REQUIRED with bounded cleanup-failure reason
  -> if RECOVERY_REQUIRED persistence also fails, fail with explicit unproven-state diagnostic
```

This is not executor retry and must not rerun or reroute anything.

Add tests proving:

```text
EXECUTION_BLOCKED_STATE_WRITE_FAILS -> RECOVERY_REQUIRED attempted
RECOVERY_REQUIRED_FALLBACK_SUCCEEDS -> final persisted state RECOVERY_REQUIRED
BOTH_STATE_WRITES_FAIL -> command fails with explicit unproven cleanup/state diagnostic
NO_SECOND_EXECUTOR_INVOCATION
NO_PUBLICATION
NO_RETRY
NO_REROUTE
```

## Required Validation

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_executor_context_pack.py tests/test_bridge_executor_automation.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

## Decision

```text
TASK-073: CHANGES_REQUIRED
IMPLEMENTATION_INTENT: PASS
EXACT_CLEAN_NOOP_PREDICATE: PASS
NOOP_LEASE_RELEASE: PASS
NOOP_AUTH_NON_REUSABLE: PASS
B1_EXACT_AUTH_READBACK: FAIL
B1_STATE_PERSISTENCE_FALLBACK: FAIL
BLOCKERS_REMAINING: 1
AUTO_MERGE: NO
TASK_072_RERUN: NOT_AUTHORIZED_YET
```

Apply only B1 inside the existing writable scope. Do not alter worker identity, task authoring markers, H-Series code, dispatch/failover semantics, paid-provider gates, RESULT schema, or Lean Auto-Merge authority.
