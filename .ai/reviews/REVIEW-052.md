# REVIEW-052 — TASK-052 M11.2B Human Paid API Grant Command + Exact Runtime Binding

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Review Anchors

```text
TASK_ID: TASK-052
MILESTONE: M11.2B — Human Paid API Grant Command + Exact Runtime Binding
BASELINE_MAIN_SHA: 15a26f7a2810a5540bed0a3f7ad8f662b04533d4
TASK_BRANCH: ai/task-052
REVIEWED_TASK_HEAD_SHA: 8a0b7f4a916c3c8127c01c750ddb9bb86ae0f42f
TASK_BLOB_SHA: 64b28033fde9ec273246928eb185120756e93714
BLUEPRINT_BLOB_SHA: c50d2acb153356c3e35609101302bf2cf650b735
RESULT_052_BLOB_SHA: de051d20be7755a47561daef36c1914f7a2fd5d8
BRIDGE_BLOB_SHA: 262f1140da682a00681ecd3c86e3846933b910c7
TEST_BLOB_SHA: 85df56ae0dff5a6c5174e25c087edc3b696aacfc
E4_CONTROL_COMMIT_SHA: 55893fbe00e5ca128bc19718490a65309aa6bfbe
```

## Machine-Readable FIX Executor Contract

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-052.md","blob_sha":"64b28033fde9ec273246928eb185120756e93714"},{"path":".ai/context/TASK-052-M11.2B-HUMAN-PAID-API-GRANT-COMMAND-BLUEPRINT.md","blob_sha":"c50d2acb153356c3e35609101302bf2cf650b735"},{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"}]

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","tests/test_bridge_paid_api_grant.py"]

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

These markers authorize only the bounded FIX described below. They do not authorize merge, paid Executor use, paid Brain dispatch, or any provider call.

## Lineage / Scope

Independent GitHub comparison proves:

```text
main: 15a26f7a2810a5540bed0a3f7ad8f662b04533d4
ai/task-052: 8a0b7f4a916c3c8127c01c750ddb9bb86ae0f42f
status: ahead
commits_ahead: 1
commits_behind: 0
merge_base: 15a26f7a2810a5540bed0a3f7ad8f662b04533d4
```

Changed files versus baseline are exactly:

```text
.ai/results/RESULT-052.md
bridge.py
tests/test_bridge_paid_api_grant.py
```

Executor write scope is therefore exact: the two authorized implementation/test files plus Bridge-generated RESULT.

## Independent Audit — Passing Areas

The following TASK-052 requirements are implemented correctly at the reviewed head:

- external `paid_api_grants` runtime path is added and created by `ensure_dirs()`;
- `get_paid_api_grant_store()` binds the current deterministic workspace;
- `paid-grant-create` requires explicit `--confirm-paid-api-spend` before runtime/control side effects;
- provider/model/operation/artifact/budgets/TTL are explicit and required;
- Human cannot supply grant ID, artifact blob SHA, workspace ID, actor kind, max calls, or credential flags;
- TTL is exactly bounded to 1..900 seconds with one create-time wall-clock observation;
- grant ID is Bridge-generated exactly once with no automatic collision retry;
- grant actor kind is fixed BRAIN and `max_calls` fixed to 1;
- exact task/workspace/brain/provider/model/operation/token bounds are bound into immutable `PaidApiGrant`;
- successful create activates once and exact-requires readback;
- safe output explicitly reports `PAID_API_DISPATCH_ENABLED: NO` and `PROVIDER_CALL_STARTED: NO`;
- no credential values are persisted or printed;
- no dispatch, ModelGateway/provider call, paid Executor authority, authorization/lease mutation, or publish flow is invoked by grant creation;
- `paid-grant-status` is read-only and reports ACTIVE/EXPIRED/CONSUMED/NONE without refresh/delete/revoke/consume;
- corrupt dual ACTIVE+CONSUMED state fails closed;
- M11.2C, M11.3, and H-Series remain out of scope.

## Blocking Finding B1 — Artifact resolver does not prove Git object type is `blob`

### Contract

The locked blueprint requires `paid-grant-create` to:

```text
resolve --artifact-path only from canonical ai-control
require an exact existing Git blob SHA
fail before store activation if the artifact is absent or invalid
```

### Observed implementation

`cmd_paid_grant_create()` calls the existing helper:

```python
artifact_blob_sha = resolve_git_blob_sha(
    remote_ref(cfg),
    args.artifact_path,
)
```

But `resolve_git_blob_sha()` currently performs only:

```python
git rev-parse <ref>:<path>
```

and then validates that stdout is lowercase 40-hex.

It does **not** verify that the resolved Git object type is `blob`.

### Why this violates the security contract

Git tree/directory objects also have valid 40-hex object IDs. The existing M11.1 `PaidApiGrant` path validator accepts canonical `.ai/...` paths such as `.ai/tasks`; it validates path syntax and SHA shape, not Git object type.

Therefore a Human command can supply a canonical directory path such as:

```text
--artifact-path .ai/tasks
```

and the Bridge resolver can accept the resulting tree object ID as `authorized_artifact_blob_sha`, then construct and activate a paid API grant whose supposedly authorized artifact is not a blob/file at all.

For a security-critical spend authorization, `40-hex` is insufficient evidence of `blob` identity.

### Severity

```text
BLOCKING: YES
SECURITY_CONTRACT_VIOLATION: YES
MERGE_ALLOWED: NO
```

## Required Fix Contract

Keep the fix bounded to TASK-052. Do not redesign M11.

### F1 — Enforce exact Git blob type

Strengthen the exact resolver used by `paid-grant-create` so successful resolution mechanically proves the object type is exactly:

```text
blob
```

Acceptable implementations include:

- resolve SHA, then run a binary-safe Git object-type check such as `git cat-file -t <sha>` and require exact `blob`; or
- use an equivalent Git primitive that fails closed unless `<ref>:<path>` resolves as a blob.

Requirements:

```text
MISSING_OBJECT: FAIL_CLOSED
TREE_OBJECT: FAIL_CLOSED
TAG_OR_OTHER_NON_BLOB_OBJECT: FAIL_CLOSED
MALFORMED_TYPE_OUTPUT: FAIL_CLOSED
BLOB_OBJECT: PASS
```

Do not use filesystem fallback, working-tree inspection, or Human-supplied object type.

### F2 — Add regression tests

Add focused tests in the existing TASK-052 test file proving at minimum:

1. a valid blob path succeeds;
2. a directory/tree path is rejected before `AtomicPaidApiGrantStore.activate()`;
3. malformed/non-blob object-type evidence fails closed;
4. no grant state is created after tree/non-blob rejection.

The test must exercise the real resolver/type-verification behavior rather than monkeypatching `resolve_git_blob_sha()` to always return a fake 40-hex SHA.

### F3 — Preserve all currently passing boundaries

No change to:

```text
confirmation semantics
TTL contract
grant ID semantics
Brain-only authority
max_calls=1
safe receipt
status read-only semantics
M11.1 grant contract
M11.2A runtime store
M10 dispatch
External Brain gateway/provider code
allow_paid_api default=false
M11.2C / M11.3 boundary
```

## Allowed FIX Scope

Executor may modify only:

```text
bridge.py
tests/test_bridge_paid_api_grant.py
```

Bridge may update `.ai/results/RESULT-052.md` during FIX publication.

No other implementation scope is authorized by this review.

## Test Evidence at Reviewed Head

Bridge-owned repository suite is green before the required fix:

```text
1684 passed, 7 skipped, 1533 warnings in 143.18s
EXIT_CODE: 0
```

E4 evidence:

```text
E4_AUTO_EXECUTION: YES
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 2
E4_PRE_EXECUTION_HEAD: 15a26f7a2810a5540bed0a3f7ad8f662b04533d4
```

A green suite does not override B1 because the current TASK-052 tests mock `resolve_git_blob_sha()` in grant-creation paths and do not prove rejection of a tree Git object.

## Findings

```text
BLOCKING_FINDINGS: 1
B1: exact Git blob object type is not verified
REGRESSIONS_OBSERVED: 0
```

## Decision

TASK-052 is **not approved for merge** at reviewed head:

```text
8a0b7f4a916c3c8127c01c750ddb9bb86ae0f42f
```

Human may authorize the bounded fix with:

```text
FIX TASK-052
```

After FIX publication, return to ChatGPT with:

```text
Review TASK-052
```

Do not merge TASK-052 and do not begin M11.2C until this review reaches PASS.
