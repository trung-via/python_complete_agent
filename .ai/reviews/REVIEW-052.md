# REVIEW-052 — TASK-052 M11.2B Human Paid API Grant Command + Exact Runtime Binding

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: YES
MERGED_TO_MAIN: YES

## Review Anchors

```text
TASK_ID: TASK-052
MILESTONE: M11.2B — Human Paid API Grant Command + Exact Runtime Binding
BASELINE_MAIN_SHA: 15a26f7a2810a5540bed0a3f7ad8f662b04533d4
TASK_BRANCH: ai/task-052
INITIAL_REVIEWED_HEAD_SHA: 8a0b7f4a916c3c8127c01c750ddb9bb86ae0f42f
FINAL_REVIEWED_TASK_HEAD_SHA: d3f66189431755cc8c188ab5bc9866c069f0e3e3
TASK_BLOB_SHA: 64b28033fde9ec273246928eb185120756e93714
BLUEPRINT_BLOB_SHA: c50d2acb153356c3e35609101302bf2cf650b735
RESULT_052_BLOB_SHA: aab7ba4f6c3a06adfbf995408914c9572cc9542e
BRIDGE_BLOB_SHA: 1870351fb18bb9224e5a91524b72d612205617f2
TEST_BLOB_SHA: 14fb86c85a071dda08d78415073121fcb4bf3f52
FIX_AUTH_REVIEW_BLOB_SHA: 71d22b32dc0d7cc088721d74eba3e20942b2342c
E4_FIX_CONTROL_COMMIT_SHA: 8a2973c472fb0622f345addb1987546f23ee2bcf
POST_MERGE_MAIN_SHA: d3f66189431755cc8c188ab5bc9866c069f0e3e3
MERGE_METHOD: FAST_FORWARD_REF_UPDATE
FORCE: FALSE
POST_MERGE_EXACT_HEAD: PASS
FAST_FORWARD_MERGE: PASS
```

## Lineage / Scope

Independent GitHub comparison after FIX proved:

```text
main_before_merge: 15a26f7a2810a5540bed0a3f7ad8f662b04533d4
ai/task-052: d3f66189431755cc8c188ab5bc9866c069f0e3e3
status: ahead
commits_ahead: 2
commits_behind: 0
merge_base: 15a26f7a2810a5540bed0a3f7ad8f662b04533d4
```

Pre-merge exact-head verification also proved:

```text
compare d3f66189431755cc8c188ab5bc9866c069f0e3e3..ai/task-052
status: identical
```

Cumulative changed files versus baseline remained exactly:

```text
.ai/results/RESULT-052.md
bridge.py
tests/test_bridge_paid_api_grant.py
```

The bounded FIX from the initial reviewed head was exactly one additional commit and modified only:

```text
.ai/results/RESULT-052.md
bridge.py
tests/test_bridge_paid_api_grant.py
```

Executor implementation scope therefore remained exact: `bridge.py` plus the TASK-052 test file; RESULT is Bridge publication output.

## Initial Blocking Finding B1 — RESOLVED

Initial review found that `resolve_git_blob_sha()` proved only lowercase 40-hex identity and did not prove the resolved Git object type was a blob.

The FIX now performs:

```text
rev-parse <ref>:<path>
→ exact lowercase 40-hex SHA
→ git cat-file -t <sha>
→ require stdout bytes exactly b"blob\n"
```

Fail-closed behavior is explicit:

```text
missing/type-check command failure → REJECT
TREE                         → REJECT
COMMIT / other non-blob      → REJECT
malformed type output        → REJECT
non-ASCII/malformed evidence → REJECT
exact blob                   → ACCEPT
```

No filesystem fallback, working-tree authority, Human-supplied object type, or provider side effect is introduced.

### Regression proof

Focused tests use a real temporary Git repository/control ref and prove:

1. a real file/blob resolves and can create the bounded grant;
2. `.ai/tasks` resolves as a tree and is rejected before store activation;
3. non-blob/malformed type evidence (`commit`, extra output, invalid bytes) fails closed before activation;
4. tree/non-blob rejection creates no paid grant JSON.

B1 is closed.

## Independent Contract Audit — PASS

### Human authorization boundary
- `paid-grant-create` requires explicit `--confirm-paid-api-spend` before runtime/control side effects.
- Provider/model/operation/artifact/token budgets/TTL are explicit required inputs.
- Human cannot supply grant ID, artifact blob SHA, workspace ID, actor kind, max calls, or credentials.
- Grant ID is Bridge-generated once; activation failure has no automatic retry.

### Exact canonical binding
- Artifact identity is resolved only from the configured canonical control ref.
- Resolved object must be an exact Git blob.
- Grant binds exact task, workspace, Brain ID, provider ID, model ID, Brain operation, artifact path/blob and token bounds.
- Actor kind is fixed BRAIN and `max_calls` is fixed to 1.

### TTL / runtime state
- TTL is explicit and bounded to 1..900 seconds.
- Create observes wall clock once and persists exact absolute expiry.
- State persists under external `paid_api_grants` runtime storage bound to current workspace.
- Create activates once and exact-requires the same grant readback.

### Safe output / secrets
- Success receipt contains bounded non-secret metadata.
- It explicitly states `PAID_API_DISPATCH_ENABLED: NO` and `PROVIDER_CALL_STARTED: NO`.
- Credential environment values are neither persisted nor printed.

### Read-only status
- `paid-grant-status` reports ACTIVE / CONSUMED / NONE and ACTIVE usability UNEXPIRED / EXPIRED.
- Status does not activate, consume, delete, revoke, refresh or extend grant state.
- Malformed/dual runtime state fails closed.

### Authority boundary preserved
TASK-052 still does not:

```text
set BrainDispatchRequest.allow_paid_api = true
dispatch a Brain
select a paid candidate
invoke ModelGateway
invoke a provider
read provider credentials
create paid Executor authority
perform a real paid API call
implement M11.2C
implement M11.3
activate H-Series
```

## Test Evidence

Bridge-owned full repository suite after FIX:

```text
1689 passed, 7 skipped, 1533 warnings in 247.68s
EXIT_CODE: 0
```

E4 FIX evidence:

```text
ACTION: FIX
EXECUTOR_ID: codex
E4_AUTO_EXECUTION: YES
E4_CONTROL_COMMIT_SHA: 8a2973c472fb0622f345addb1987546f23ee2bcf
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: 8a0b7f4a916c3c8127c01c750ddb9bb86ae0f42f
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 2
```

## Findings

```text
BLOCKING_FINDINGS: 0
NON_BLOCKING_FINDINGS: 0
REGRESSIONS: 0
B1: RESOLVED
```

## Acceptance

```text
HUMAN_CONFIRMATION_GATE: PASS
BRIDGE_GENERATED_GRANT_ID: PASS
CANONICAL_CONTROL_BLOB_BINDING: PASS
EXACT_GIT_OBJECT_TYPE_BLOB: PASS
TREE_OBJECT_REJECTED: PASS
NON_BLOB_MALFORMED_TYPE_REJECTED: PASS
CURRENT_WORKSPACE_BINDING: PASS
BRAIN_ONLY_GRANT: PASS
MAX_CALLS_ONE: PASS
EXPLICIT_TOKEN_BOUNDS: PASS
SHORT_EXPLICIT_TTL: PASS
EXTERNAL_RUNTIME_PERSISTENCE: PASS
STRICT_READBACK: PASS
READ_ONLY_STATUS: PASS
NO_CREDENTIAL_PERSISTENCE: PASS
NO_DISPATCH_ENABLEMENT: PASS
NO_PROVIDER_CALL: PASS
NO_EXECUTOR_AUTHORITY: PASS
NO_RETRY_OR_REROUTE: PASS
M11_2C_NOT_IMPLEMENTED: PASS
M11_3_NOT_IMPLEMENTED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
FAST_FORWARD_MERGE: PASS
POST_MERGE_EXACT_HEAD: PASS
```

## Decision

TASK-052 was approved for Human merge at exact reviewed head:

```text
d3f66189431755cc8c188ab5bc9866c069f0e3e3
```

Human explicitly authorized merge. `main` was fast-forwarded with `force=false` to the exact reviewed head and independently verified identical afterward.

TASK-052 / M11.2B is complete.

Do not begin M11.2C automatically.