# TASK-069 — Lean Auto-Merge / Reviewed-Head Binding Implementation

STATUS: READY
CLASS: L2 — AIOS REVIEW/MERGE CONTROL-PLANE REFINEMENT
MILESTONE: PRE-H1 OPERATOR-FRICTION REDUCTION
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: bd4cc149352683de02884cb6da6b55074c74e205
TARGET_BRANCH: ai/task-069
H0_STATUS: COMPLETE
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
H1_STARTED: NO
M11_STATUS: OPERATIONALLY_PROVEN / CLOSED
M12_CREATED: NO
AUTO_MERGE_ALLOWED: YES
PAID_API_CALL_ALLOWED: NO
NETWORK_CALL_ALLOWED_BY_EXECUTOR: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
```

TASK-069 formalizes the lean merge behavior already used operationally and the new Human standing authorization from ADR-042. It must reduce the redundant second merge confirmation without weakening review, exact-SHA binding, main-drift checks, fast-forward-only semantics, or post-merge identity verification.

TASK-069 itself remains subject to normal RUN/FIX + ChatGPT exact-SHA review. If its final review is PASS, the standing authorization in ADR-042 permits ChatGPT to auto-merge the exact reviewed TASK-069 head immediately without asking for a separate Human `Merge TASK-069` command.

## Authoritative Context

```text
ADR_042_PATH: .ai/decisions/ADR-042-LEAN-AUTO-MERGE-REVIEWED-HEAD-BINDING-CONTRACT-LOCK.md
ADR_042_BLOB_SHA: 33018c96ad941618f11ce1bfc48d569b94cfad72

ADR_037_PATH: .ai/decisions/ADR-037-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-CONTRACT-LOCK.md
ADR_037_BLOB_SHA: 6c30cd6d2b9dea5dd4d20b687353471ba80dae8b
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-042-LEAN-AUTO-MERGE-REVIEWED-HEAD-BINDING-CONTRACT-LOCK.md","blob_sha":"33018c96ad941618f11ce1bfc48d569b94cfad72"},{"path":".ai/decisions/ADR-037-UNIFIED-AIOS-WORKER-CONTROL-SURFACE-CONTRACT-LOCK.md","blob_sha":"6c30cd6d2b9dea5dd4d20b687353471ba80dae8b"}]

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/review_merge.py","tests/aios_bridge/test_review_merge.py","tests/test_bridge_review_merge.py",".agents/skills/aios-worker/SKILL.md",".agents/workflows/aios-worker.md","docs/AIOS_UNIFIED_WORKER_WORKFLOW.md"]

Bridge-generated publication output:

```text
.ai/results/RESULT-069.md
```

is publication output only.

No other file may be modified. Do not touch H-Series source, provider/paid API code, continuity schemas, dispatch, lease, executor transports, dependencies, tasks, ADRs, or reviews.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN","FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN","FIX"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

One executor is selected by explicit Human RUN/FIX surface. No automatic second executor, retry, reroute, failover, or paid fallback.

## Required Implementation

### 1. Deterministic Merge Gate Module

Add:

```text
src/aios_bridge/review_merge.py
```

Use stdlib only.

Define immutable/frozen contracts equivalent to:

```text
MergeGateReason
ReviewedMergeInput
MergeGateDecision
```

`MergeGateReason` must be a closed stable vocabulary containing at minimum:

```text
PASS_ELIGIBLE
REVIEW_MISSING
REVIEW_NOT_PASS
REVIEW_NOT_APPROVED
AUTO_MERGE_DISABLED
REVIEW_HEAD_INVALID
REVIEW_BASE_INVALID
TASK_HEAD_DRIFT
MAIN_DRIFT
NOT_FAST_FORWARD
BRANCH_BEHIND_MAIN
NO_TASK_DELTA
POST_MERGE_IDENTITY_FAILED
GIT_OPERATION_FAILED
```

Exact names above are preferred.

`ReviewedMergeInput` must bind at minimum:

```text
task_id
review_status
review_approved
auto_merge_eligible
reviewed_task_head_sha
reviewed_base_main_sha
current_task_head_sha
current_main_sha
merge_base_sha
ahead_by
behind_by
```

Validation requirements:

- exact canonical `TASK-NNN` or repository-established canonical task form;
- SHA fields exact lowercase 40-hex;
- bool must be exact bool;
- counts exact non-negative int; bool forbidden;
- frozen/immutable;
- no network/provider/merge side effect in pure gate evaluation.

Evaluation precedence must fail closed and be deterministic.

PASS eligibility requires exactly:

```text
review_status == PASS
review_approved == True
auto_merge_eligible == True
current_task_head_sha == reviewed_task_head_sha
current_main_sha == reviewed_base_main_sha
merge_base_sha == current_main_sha
behind_by == 0
ahead_by >= 1
```

Everything else returns a stable non-PASS reason.

### 2. Strict Review Contract Parser

Implement a narrow parser for the machine-readable review header used by future auto-merge reviews.

Required fields:

```text
STATUS: PASS
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
REVIEWED_TASK_HEAD_SHA: <40-hex>
REVIEWED_BASE_MAIN_SHA: <40-hex>
```

Requirements:

- exact unambiguous key parsing;
- duplicate required keys rejected, even if values match;
- conflicting values rejected;
- malformed YES/NO rejected;
- unknown fields may be ignored but cannot override required keys;
- no inference of PASS from prose;
- no legacy fuzzy text search;
- no worker-generated review accepted as authority merely because a file exists.

The parser is evidence extraction only. It does not create review authority.

### 3. Narrow Bridge Command

Add a command surface equivalent to:

```text
python bridge.py merge-reviewed TASK-N
```

This command is a deterministic execution of an already-authorized reviewed-head merge. It MUST NOT review code or mark a non-PASS review as PASS.

Required preflight:

1. sync/fetch the required repository refs through the existing repository/Git control path;
2. read the review artifact for the exact task from `ai-control`;
3. parse the strict required review fields;
4. resolve current remote `main` and exact task branch head;
5. compute merge-base and ahead/behind;
6. evaluate the pure merge gate;
7. stop with stable reason code if not `PASS_ELIGIBLE`.

Required mutation when eligible:

```text
fast-forward main to exactly REVIEWED_TASK_HEAD_SHA
force = false
no squash
no rebase
no cherry-pick
no merge commit
```

Use existing safe Git command helpers where practical. Do not introduce shell interpolation.

Immediately post-mutation, refetch/re-resolve refs and verify:

```text
main == reviewed task head
main vs task branch == identical
```

If post-check fails, return `POST_MERGE_IDENTITY_FAILED` and stop.

No full test rerun and no code/scope re-review belong in this command.

### 4. Machine-Readable Merge Receipt

The merge command must emit/persist only bounded deterministic merge evidence under the existing external AIOS runtime receipt mechanism if one is already suitable; otherwise return a bounded structured result without creating a new persistent authority store.

Required safe evidence shape equivalent to:

```text
task_id
reviewed_task_head_sha
reviewed_base_main_sha
pre_merge_main_sha
post_merge_main_sha
merge_method = FAST_FORWARD
force_update = false
auto_merge = true
gate_reason
post_merge_identity_verified
```

Do not persist credentials, tokens, raw Git stderr bodies, model prose, or arbitrary review text.

### 5. Worker Surface Boundary Update

Update both worker surfaces and unified workflow documentation to replace the obsolete wording that MERGE is reserved for a fresh Human command.

New semantic lock:

```text
worker executors NEVER merge
ChatGPT review boundary may auto-merge after PASS under ADR-042 standing Human authorization
workers still stop after RESULT publication and instruct Human to Review TASK-N in ChatGPT
```

Do not add `MERGE` as a Codex or Antigravity worker command.

### 6. Review Schema Going Forward

Document that PASS reviews eligible for standing auto-merge should include:

```text
STATUS: PASS
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
REVIEWED_TASK_HEAD_SHA: <exact head>
REVIEWED_BASE_MAIN_SHA: <exact main reviewed against>
```

Before TASK-069 is merged, ChatGPT may still execute the same gate directly with GitHub controls using ADR-042. After merge, the repository-owned command becomes the reproducible local equivalent.

## Explicitly Forbidden

Do not add or permit:

```text
worker self-merge
merge without ChatGPT PASS review
review inference from RESULT
review inference from tests alone
auto-approval
force push
force-with-lease as a history-rewrite escape hatch
merge commit
squash merge
rebase/cherry-pick during merge
main drift tolerance
task-head drift tolerance
automatic re-review
automatic rebase
automatic retry
automatic executor reroute
paid API fallback
provider API call
H-Series modification
M12
```

If current Git structure makes exact reviewed-base binding impossible without broad redesign, STOP and report rather than weakening the contract.

## Tests

Add focused deterministic tests covering at minimum:

1. frozen merge input/decision contracts;
2. exact 40-hex SHA validation;
3. bool rejected as count;
4. PASS + approved + eligible + exact head/base + FF -> `PASS_ELIGIBLE`;
5. review not PASS -> blocked;
6. review not approved -> blocked;
7. auto-merge disabled -> blocked;
8. task head drift -> blocked;
9. main drift -> blocked;
10. merge-base mismatch -> blocked;
11. behind_by > 0 -> blocked;
12. ahead_by == 0 -> blocked;
13. strict review parser accepts canonical header;
14. missing required key rejected;
15. duplicate required key rejected;
16. malformed YES/NO rejected;
17. prose containing `PASS` cannot authorize;
18. bridge command does zero mutation when gate blocked;
19. bridge command performs one fast-forward-only mutation when eligible;
20. no force flag in merge mutation;
21. task branch head must equal reviewed head immediately before mutation;
22. main must equal reviewed base immediately before mutation;
23. post-merge identity verified;
24. post-merge mismatch fails closed;
25. no full test invocation is triggered by merge command;
26. no provider/paid API invocation;
27. worker surfaces expose no MERGE command;
28. existing RUN/FIX/STATUS worker identity contracts remain intact.

All Git mutation tests must use fake/monkeypatched Git runners or isolated temporary repositories. Automated tests MUST NOT push real `main`.

## Validation Commands

Executor must run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_review_merge.py tests/test_bridge_review_merge.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Also perform exact writable-scope verification.

Pre-task merged baseline:

```text
2092 passed, 7 skipped, 0 failed
```

## Required RESULT-069 Evidence

`RESULT-069.md` must report at minimum:

```text
TASK_069_CLASS: LEAN_AUTO_MERGE_REVIEWED_HEAD_BINDING
STANDING_AUTO_MERGE_AUTHORIZATION: ENABLED
SECOND_HUMAN_MERGE_CONFIRMATION_REQUIRED: NO
WORKER_MERGE_AUTHORITY: NO
CHATGPT_PASS_REVIEW_REQUIRED: YES
STRICT_REVIEW_HEADER_PARSER: PASS
EXACT_REVIEWED_HEAD_BINDING: PASS
EXACT_REVIEWED_BASE_MAIN_BINDING: PASS
TASK_HEAD_DRIFT_FAIL_CLOSED: PASS
MAIN_DRIFT_FAIL_CLOSED: PASS
FAST_FORWARD_ONLY: PASS
FORCE_UPDATE_ALLOWED: NO
POST_MERGE_IDENTITY_REQUIRED: YES
MERGE_REAUDIT_REQUIRED: NO
NO_FULL_TEST_RERUN_DURING_MERGE: YES
PAID_API_USED: NO
H0_CHANGED: NO
H1_STARTED: NO
SCOPE_EXACT: YES
```

Include exact targeted/full test commands, exit codes, pass/skip/fail counts, changed paths, implementation SHA, and branch.

## Acceptance Criteria

TASK-069 may publish READY_FOR_REVIEW only if:

```text
MERGE_GATE_PURE_DECISION: PASS
STRICT_REVIEW_PARSER: PASS
BRIDGE_MERGE_REVIEWED_COMMAND: PASS
EXACT_REVIEWED_HEAD_BINDING: PASS
EXACT_REVIEWED_BASE_MAIN_BINDING: PASS
FAST_FORWARD_ONLY: PASS
FORCE_UPDATE_ALLOWED: NO
MAIN_DRIFT_FAIL_CLOSED: PASS
TASK_HEAD_DRIFT_FAIL_CLOSED: PASS
POST_MERGE_IDENTITY: PASS
WORKER_MERGE_AUTHORITY: NO
SECOND_HUMAN_CONFIRMATION_REQUIRED: NO
NO_REVIEW_REAUDIT_ON_MERGE: YES
NO_FULL_TEST_RERUN_ON_MERGE: YES
NO_PAID_API: PASS
NO_H_SERIES_CHANGE: PASS
TARGETED_TESTS: PASS
FULL_REPOSITORY_TESTS: PASS
SCOPE_EXACT: YES
```
