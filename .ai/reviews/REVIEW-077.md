# REVIEW-077 — Canonical Roadmap Governance Bootstrap Review

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO

TASK_ID: TASK-077
REVIEWED_TASK_HEAD_SHA: 6b1aa274502270ce83c89315143e6db981732b6c
REVIEWED_BASE_MAIN_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
TASK_ARTIFACT_BLOB_SHA: df59bfd21ad5bb70cb2297a7280994f7c696dd87
RESULT_BLOB_SHA: b8714aa0ad3ea1d5612c828d3cd868188d1e45f4
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 4
CODE_AUDIT: CHANGES_REQUIRED
GOVERNANCE_AUDIT: CHANGES_REQUIRED
TASK_076_MERGE_AUTHORIZED: NO
H_SERIES_ADVANCEMENT: FROZEN
LIVE_PAID_API_AUTHORIZED: NO

## Machine-Readable E4 FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-077.md","blob_sha":"df59bfd21ad5bb70cb2297a7280994f7c696dd87"},{"path":".ai/decisions/ADR-050-AIOS-ENGINEERING-CANONICAL-ROADMAP-LOCK-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md","blob_sha":"334b610b2c221ac20b2b9946142a0baed8952690"},{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/decisions/ADR-044-EXECUTABLE-TASK-AUTHORING-PREFLIGHT-ZERO-TOUCH-START-CONTRACT-LOCK.md","blob_sha":"24b212d96d5fa650241a71049ce114f7a3a85489"},{"path":".ai/decisions/ADR-042-LEAN-AUTO-MERGE-REVIEWED-HEAD-BINDING-CONTRACT-LOCK.md","blob_sha":"33018c96ad941618f11ce1bfc48d569b94cfad72"},{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/roadmap_governance.py","src/aios_bridge/task_authoring.py","src/aios_bridge/review_merge.py","tests/aios_bridge/test_roadmap_governance.py","tests/test_bridge_task_authoring.py","tests/aios_bridge/test_review_merge.py","tests/test_bridge.py","docs/AIOS_H_SERIES_RECONCILIATION_V1.md"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This review authorizes only repair of the four blockers below after a fresh Human FIX command. It creates no milestone progression, TASK-076 merge, H5, retry/reroute, or paid-provider authority.

## Reviewed Snapshot

```text
BASE_MAIN_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
BRANCH: ai/task-077
REVIEWED_TASK_HEAD_SHA: 6b1aa274502270ce83c89315143e6db981732b6c
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
CUMULATIVE_SCOPE: AUTHORIZED
```

RESULT-077 records canonical E4 completion and a green full repository suite:

```text
2370 passed, 7 skipped, 0 failed
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
```

Green tests do not close the governance blockers below because the failing cases are integration-boundary cases that the current tests do not exercise.

## Findings

### B1 — Milestone progression is optional at the real RUN/E4 boundary

The pure milestone completion model exists and `may_open_milestone()` correctly rejects missing predecessor completion when called directly.

However `preflight_executable_artifact()` invokes progression only when `milestone_completion_records` is truthy. The production RUN handoff and E4 control-snapshot revalidation call this preflight without supplying completion records.

Therefore a future roadmap-governed later-milestone task can carry an otherwise valid roadmap binding and pass the actual Bridge RUN/E4 boundary while predecessor milestone-completion evidence is absent.

This violates the locked acceptance invariant:

```text
TASK PASS != MILESTONE COMPLETE
MILESTONE_OPEN_WITHOUT_PREVIOUS_COMPLETION: REJECTED
ROADMAP_PREFLIGHT: FAIL_CLOSED
```

Required FIX:

1. Make progression validation mandatory for governed implementation tasks where predecessor completion is required.
2. Resolve completion records from an exact authoritative control-plane source; do not accept executor-supplied/ad hoc evidence as authority.
3. Bind those records to the same exact roadmap identity/fingerprint before `may_open_milestone()`.
4. RUN handoff and E4 revalidation must both fail closed if required completion evidence is missing, malformed, stale, duplicated, wrong-roadmap, or incomplete.
5. Preserve the bootstrap exception only for the specifically authorized governance bootstrap path; do not add a generic bypass.

Add Bridge-level tests proving a governed later-milestone task is rejected by the actual handoff/E4 path when completion evidence is absent.

### B2 — Merge roadmap gate reads canonical artifacts from the wrong Git surfaces and can fail open

`cmd_merge_reviewed()` attempts to determine roadmap governance by reading:

```text
<task_branch_head>:.ai/tasks/TASK-NNN.md
```

But canonical TASK artifacts live on the control branch, not on task branches. The reviewed TASK-077 branch itself contains `.ai/results` but no `.ai/tasks` directory.

When that lookup fails, the current code leaves:

```text
roadmap_governed = False
```

and the PASS review can be evaluated as a legacy/non-governed task, skipping the roadmap audit gate entirely.

A second surface error exists inside the governed path: the canonical roadmap is resolved from `current_main_sha`, but the locked roadmap artifact lives on the authoritative control branch. Main currently has no `.ai/roadmaps` tree.

Required FIX:

1. Freeze one exact authoritative control-branch commit for the merge transaction.
2. Resolve the TASK artifact from that control commit, and require its exact canonical blob identity.
3. Determine roadmap governance from that exact TASK artifact. Missing/unreadable canonical TASK must fail closed, never downgrade to legacy.
4. Resolve the registered canonical roadmap from the same authoritative control commit, not main/task branch.
5. Revalidate task binding/context/roadmap identity against those exact control-plane bytes before merge eligibility.
6. Only genuinely legacy tasks proven non-governed by their canonical control artifact may use the legacy merge path.

Add end-to-end `cmd_merge_reviewed` regressions proving:

```text
governed PASS without roadmap audit -> NOT MERGE ELIGIBLE
governed PASS with wrong roadmap    -> NOT MERGE ELIGIBLE
governed PASS with exact roadmap    -> reaches existing head/main/FF gates
missing canonical task artifact     -> FAIL CLOSED
```

### B3 — Governed FIX incorrectly treats REVIEW text as the TASK roadmap-binding artifact

For FIX, `cmd_handoff()` sends the CHANGES_REQUIRED review content directly through `preflight_executable_artifact()`.

Roadmap governance detection scans the title/header for an H-Series class or H-milestone claim, while `parse_roadmap_task_binding()` requires `ROADMAP_BINDING_JSON`, which is a TASK binding marker.

A normal governed review carrying roadmap/milestone audit evidence can therefore be classified as governed and then rejected because the REVIEW itself does not and should not own the TASK binding marker.

This makes the ordinary governed FIX cycle structurally unsafe: either the review contains roadmap identity and risks task-binding parsing, or it omits useful roadmap evidence and weakens the audit chain.

Required FIX:

1. Separate executable TASK preflight from executable REVIEW/FIX preflight semantics.
2. For FIX, resolve the original canonical TASK artifact and exact task roadmap binding from authoritative `ai-control` evidence.
3. Validate the CHANGES_REQUIRED review as review evidence bound to that exact TASK/roadmap/reviewed head; do not require the REVIEW to duplicate `ROADMAP_BINDING_JSON`.
4. Preserve existing review status, executor policy, allowed path, failover, lease, and E4 authority checks.
5. Add integration coverage for:

```text
governed CHANGES_REQUIRED + exact original TASK binding -> FIX may authorize
governed review + missing/or drifted original TASK       -> reject
governed review + roadmap identity mismatch              -> reject
```

### B4 — Reconciliation overstates canonical H1 as COMPLETE

The canonical roadmap requires H1 to inventory not only repository artifacts but also TASK/RESULT/review/decision/learning evidence and bind repository/control-plane provenance.

The existing H1 discovery implementation inventories one exact Git commit/tree. It has no independent control-plane snapshot/ref input. In current repository topology, `main` contains `.ai/results` but canonical `.ai/tasks`, `.ai/reviews`, and `.ai/decisions` live on `ai-control`.

Therefore the reconciliation statement that the same H1 inventory covers TASK/RESULT/review/decision/learning evidence is not supported by the implemented H1 boundary.

Required FIX to the reconciliation report:

```text
H0: COMPLETE (subject to formal completion record when progression is enforced)
H1: PARTIAL
  - repository manifest/provenance: substantial/present
  - control-plane experience manifest: missing/incomplete
H2: PARTIAL
H3: PARTIAL
H4-H8: MISSING
TRUE_EARLIEST_INCOMPLETE_CANONICAL_MILESTONE: H1
SAFE_NEXT_CANONICAL_CAPABILITY: complete H1 Repository + Experience Manifest
```

Do not discard H2/H3/TASK-076 work. It remains reusable downstream evidence, but canonical progression must close the earliest incomplete predecessor first.

The report must explicitly distinguish repository snapshot provenance from `ai-control` control-plane provenance and avoid inferring canonical completion from historical PASS/H labels.

## Passing Areas

The following implementation is valuable and should be preserved while fixing B1-B4:

```text
EXACT_ROADMAP_BLOB_BINDING: PASS
EXACT_BYTE_SHA256_FINGERPRINT: PASS
STRICT_TASK_BINDING_SCHEMA: PASS
ROADMAP_CONTEXT_REF_BINDING: PASS
PURE_MILESTONE_COMPLETION_VALIDATOR: PASS
CONTROLLED_EVOLUTION_MODEL: PASS
IMPACT_CONE_HELPER: PASS
PURE_REVIEW_ROADMAP_AUDIT_REASONS: PASS
LEGACY_COMPATIBILITY_MODEL: PRESENT
TASK_076_BRANCH_PRESERVED: YES
H5_STARTED: NO
NETWORK/LLM/PAID_API_IN_GOVERNANCE: NO
FULL_REPOSITORY_TESTS: GREEN
```

## FIX Validation

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_roadmap_governance.py tests/test_bridge_task_authoring.py tests/aios_bridge/test_review_merge.py tests/test_bridge.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

In addition, the targeted suite must include production-call-path regressions for B1-B3 rather than only pure helper tests.

## Decision

```text
TASK-077: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
BLOCKERS_REMAINING: 4
ROADMAP_GOVERNANCE_MACHINE_ENFORCED: NOT_YET
RECONCILIATION_CANONICAL_POSITION: NEEDS_CORRECTION
TASK_076_MERGE_AUTHORIZED: NO
H_SERIES_ADVANCEMENT: FROZEN
H5_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```
