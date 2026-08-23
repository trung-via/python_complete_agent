# REVIEW-077 — Canonical Roadmap Governance Bootstrap Review — Round 2

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
TASK_ID: TASK-077
REVIEWED_TASK_HEAD_SHA: 04632a59084f09da547a9a5582c24e72ee5132c8
REVIEWED_BASE_MAIN_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
TASK_ARTIFACT_BLOB_SHA: df59bfd21ad5bb70cb2297a7280994f7c696dd87
RESULT_BLOB_SHA: 494e43a7cb415a050d092b9e61aad33d33628d4f
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 1
CODE_AUDIT: CHANGES_REQUIRED
GOVERNANCE_AUDIT: CHANGES_REQUIRED
PRIOR_BLOCKERS_B1_B4: CLOSED
TASK_076_MERGE_AUTHORIZED: NO
H_SERIES_ADVANCEMENT: FROZEN
LIVE_PAID_API_AUTHORIZED: NO

## Machine-Readable E4 FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-077.md","blob_sha":"df59bfd21ad5bb70cb2297a7280994f7c696dd87"},{"path":".ai/decisions/ADR-050-AIOS-ENGINEERING-CANONICAL-ROADMAP-LOCK-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md","blob_sha":"334b610b2c221ac20b2b9946142a0baed8952690"},{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/decisions/ADR-044-EXECUTABLE-TASK-AUTHORING-PREFLIGHT-ZERO-TOUCH-START-CONTRACT-LOCK.md","blob_sha":"24b212d96d5fa650241a71049ce114f7a3a85489"},{"path":".ai/decisions/ADR-042-LEAN-AUTO-MERGE-REVIEWED-HEAD-BINDING-CONTRACT-LOCK.md","blob_sha":"33018c96ad941618f11ce1bfc48d569b94cfad72"},{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/roadmap_governance.py","src/aios_bridge/task_authoring.py","src/aios_bridge/review_merge.py","tests/aios_bridge/test_roadmap_governance.py","tests/test_bridge_task_authoring.py","tests/aios_bridge/test_review_merge.py","tests/test_bridge.py","docs/AIOS_H_SERIES_RECONCILIATION_V1.md"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This review authorizes only repair of the blocker below after a fresh Human FIX command. It creates no milestone completion record, H-Series progression, TASK-076 merge, retry/reroute, or paid-provider authority.

## Reviewed Snapshot

```text
BASE_MAIN_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
BRANCH: ai/task-077
REVIEWED_TASK_HEAD_SHA: 04632a59084f09da547a9a5582c24e72ee5132c8
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 2
BEHIND_BY: 0
MERGE_BASE_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
FULL_REPOSITORY_SUITE: 2382 passed, 7 skipped, 0 failed
```

## Prior Blocker Closure

The four Round-1 blockers are materially closed:

- B1 CLOSED: governed milestone progression now requires exact authoritative completion-artifact resolution before later milestones may open.
- B2 CLOSED: merge review freezes `ai-control`, resolves canonical TASK from that frozen control commit, and resolves the registered roadmap from the same control-plane provenance surface.
- B3 CLOSED: FIX preflight resolves and validates the original canonical TASK separately from the CHANGES_REQUIRED REVIEW and binds governed review evidence back to that exact TASK.
- B4 CLOSED: reconciliation correctly classifies H1 as PARTIAL and identifies H1 as the true earliest incomplete canonical milestone.

## Blocking Finding

### B5 — Legacy `bridge.py approve` remains an authority-bearing governance bypass

Severity: BLOCKER

`build_parser()` still exposes the legacy command:

```text
bridge.py approve <task_id> [--kind task|review] [--executor ...]
```

and routes it to `cmd_approve`.

`cmd_approve` currently:

1. accepts a pending TASK/REVIEW event;
2. checks out/prepares the task branch;
3. builds/acquires an Executor lease;
4. marks the inbox event APPROVED;
5. writes ACTIVE authorization;
6. moves runtime state to IN_PROGRESS / CHANGES_REQUIRED;

without invoking the canonical executable-artifact roadmap preflight, without resolving the frozen canonical roadmap, and without requiring milestone-completion evidence.

This is not merely a dormant helper: the CLI parser exposes it as a Human command. For the Antigravity executor, ACTIVE authorization is sufficient to begin productive work in the interactive executor session, and `cmd_publish` currently trusts the ACTIVE authorization plus artifact/status revalidation without independently rerunning roadmap progression preflight.

Therefore a future governed H-Series task can evade the new fail-closed progression gate by using the legacy `approve` surface instead of `handoff`. That violates the TASK-077 invariant that a governed H-Series task cannot become execution-ready without exact roadmap binding and valid progression/completion preconditions.

Documentation saying worker surfaces must not call `bridge.py approve` is not a deterministic governance boundary; the executable authority path itself must fail closed.

## Required Repair

Close every authority-bearing path, with one of these acceptable designs:

1. **Preferred:** deprecate the legacy authority function and make `cmd_approve` fail closed before branch switching, lease acquisition, authorization persistence, or state mutation, directing users to the canonical `handoff` / `$aios-worker` / `/aios-worker` path; or
2. Route `cmd_approve` through the same exact frozen-control preflight used by `cmd_handoff`, including governed RUN roadmap binding, governed FIX original-TASK binding, and milestone completion resolver, before any authority-bearing mutation.

Required tests must prove at minimum:

- governed RUN cannot obtain ACTIVE authorization through `approve` when roadmap binding is missing/invalid;
- H1+ RUN cannot obtain ACTIVE authorization through `approve` when predecessor completion evidence is missing/invalid;
- governed FIX cannot obtain ACTIVE authorization through `approve` without the exact canonical TASK/review binding;
- failure occurs before lease/state/inbox authority mutation;
- if legacy non-governed `approve` compatibility is intentionally retained, it cannot weaken the governed path.

Defense-in-depth publication revalidation may be added, but it does not replace closing the authorization bypass itself.

## Review Decision

```text
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
BLOCKERS_REMAINING: 1
B1_B4: CLOSED
B5_LEGACY_APPROVE_BYPASS: OPEN
TASK_076_MERGE_AUTHORIZED: NO
H_SERIES_ADVANCEMENT: FROZEN
```

TASK-077 is close to PASS, but merge remains blocked until the legacy authority surface cannot bypass roadmap governance.
