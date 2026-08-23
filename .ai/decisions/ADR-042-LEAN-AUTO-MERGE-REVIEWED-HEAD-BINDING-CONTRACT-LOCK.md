# ADR-042 — Lean Auto-Merge / Reviewed-Head Binding Contract Lock

STATUS: LOCKED
CLASS: AIOS REVIEW/MERGE AUTHORITY REFINEMENT
DATE: 2026-08-23
BASELINE_MAIN_SHA: bd4cc149352683de02884cb6da6b55074c74e205
APPLIES_AFTER: TASK-068 PASS + HUMAN MERGE / DUAL EXECUTOR OPERATIONAL BASELINE PROVEN
H1_STARTED: NO
M12_CREATED: NO

## Context

AIOS currently uses an explicit Human merge step after ChatGPT review PASS. Recent merges already use a lean gate operationally: bind the exact reviewed task head, verify main has not drifted, require fast-forward lineage, update main without force, and verify post-merge identity.

The Human has now explicitly granted standing authorization to remove the redundant second confirmation step. After a valid ChatGPT PASS review, the ChatGPT review boundary may automatically perform the lean merge transaction without waiting for a separate `Merge TASK-N` command.

This reduces operator friction but MUST NOT reduce assurance. Worker executors remain unable to merge. Review remains mandatory. Exact-SHA binding remains mandatory. Force updates remain forbidden.

---

## Decision 1 — Standing Human Merge Authorization

The Human grants a standing, revocable authorization:

```text
AUTO_MERGE_AFTER_CHATGPT_PASS: ENABLED
SECOND_HUMAN_MERGE_CONFIRMATION_REQUIRED: NO
```

This authorization applies by default to AIOS task branches after a current exact-SHA ChatGPT review returns PASS, unless the task/ADR explicitly declares:

```text
AUTO_MERGE_ALLOWED: NO
```

or a stronger manual-merge requirement.

The Human may revoke or narrow this standing authorization at any time.

---

## Decision 2 — Merge Authority Remains at the Review Boundary

Authority separation becomes:

```text
Human              = standing policy authorization + RUN/FIX selection + policy revocation
ChatGPT reviewer    = exact-SHA review + PASS/CHANGES_REQUIRED + lean auto-merge transaction
Worker executors    = implementation only; never merge
AIOS Bridge         = deterministic merge-gate support / evidence; never self-approves review
```

Codex and Antigravity worker surfaces MUST NOT gain merge authority.

A worker may not infer PASS, mutate review status, merge main, force-push, or bypass the ChatGPT review boundary.

---

## Decision 3 — PASS Is Necessary but Not Sufficient

Auto-merge may execute only when all required review facts are bound and current:

```text
STATUS: PASS
APPROVED: YES
REVIEWED_TASK_HEAD_SHA: exact 40-hex SHA
REVIEWED_BASE_MAIN_SHA: exact 40-hex SHA
AUTO_MERGE_ELIGIBLE: YES
```

Equivalent legacy field names may be accepted only through an explicit compatibility parser with deterministic precedence and tests. Ambiguous or conflicting fields fail closed.

`CHANGES_REQUIRED`, missing review, malformed review, stale review, or unknown eligibility MUST NOT merge.

---

## Decision 4 — Exact Reviewed-Head Binding

Immediately before merge, the control boundary MUST verify:

```text
current_task_branch_head == REVIEWED_TASK_HEAD_SHA
current_main_head == REVIEWED_BASE_MAIN_SHA
merge_base(current_main_head, current_task_branch_head) == current_main_head
task_branch behind main == 0
task_branch ahead main >= 1
```

If task head changed after review, the review is stale and auto-merge is blocked.

If main changed after review, auto-merge is blocked. Do not silently rebase, reinterpret, or merge against a new main baseline. A fresh review/reconciliation is required.

---

## Decision 5 — Fast-Forward Only / No Force

The only permitted merge mutation is an exact fast-forward of `main` to `REVIEWED_TASK_HEAD_SHA`.

Locked:

```text
MERGE_METHOD: FAST_FORWARD_ONLY
FORCE_UPDATE: FORBIDDEN
MERGE_COMMIT: FORBIDDEN
SQUASH: FORBIDDEN
REBASE_DURING_MERGE: FORBIDDEN
CHERRY_PICK_DURING_MERGE: FORBIDDEN
```

If Git/GitHub rejects the fast-forward, stop. Do not weaken the operation.

---

## Decision 6 — Post-Merge Identity Verification

After the update, verify:

```text
main == REVIEWED_TASK_HEAD_SHA
main vs task branch == IDENTICAL
```

Only then may the review record advance to merged status.

Required merged review fields:

```text
MERGE_AUTHORIZED: YES
MERGED_TO_MAIN: YES
AUTO_MERGE_EXECUTED: YES
POST_MERGE_MAIN_SHA: <reviewed task head>
MERGE_METHOD: FAST_FORWARD
FORCE_UPDATE: NO
```

A failed post-check is a merge-integrity incident and must stop further task progression.

---

## Decision 7 — Auto-Merge Does Not Re-Run Review Work

Lean merge MUST NOT re-audit implementation source, rerun the full test suite, or repeat the entire scope review solely because merge is occurring.

The merge gate checks only facts that can change after PASS:

```text
review status/currentness
task head identity
main head identity
fast-forward lineage
post-merge identity
```

Implementation/test/scope assurance belongs to the PASS review and remains bound to its exact reviewed SHA.

---

## Decision 8 — Fail-Closed Reason Codes

A deterministic merge gate shall expose stable reason codes at minimum:

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

Unknown/ambiguous states fail closed.

---

## Decision 9 — No New Paid/Network Authority

This policy does not authorize model/provider calls, paid API use, retries, failover, network-enabled tools, or external provider credentials.

```text
LIVE_PAID_API_AUTHORIZED: NO
PAID_API_FALLBACK: NO
AUTO_RETRY: NO
EXECUTOR_REROUTE: NO
```

Repository/GitHub control-plane operations needed for review/merge remain distinct from provider-call authority.

---

## Decision 10 — H-Series Boundary

This refinement occurs before H1 and is not H-Series implementation work.

```text
H0_CHANGED: NO
H1_STARTED: NO
M12_CREATED: NO
```

Once TASK-069 implements this contract and receives PASS, the standing authorization permits TASK-069 itself to be auto-merged by the current ChatGPT review boundary using the same lean exact-SHA procedure. H1 may proceed afterward.

---

## Decision 11 — Expected Bridge Capability

TASK-069 should add a small deterministic review-merge gate rather than a broad merge subsystem.

Preferred shape:

```text
src/aios_bridge/review_merge.py
```

with pure validation types/functions plus a narrow `bridge.py` command surface such as:

```text
bridge.py merge-reviewed TASK-N
```

The local command may perform the exact fast-forward transaction only after loading a PASS review and validating all locked gates. It must not create review authority or infer PASS.

The existing ChatGPT/GitHub review boundary may independently execute the same locked transaction after PASS; the local capability exists to make the policy reproducible and repository-owned.

---

## Acceptance

ADR-042 is implemented when:

```text
STANDING_AUTO_MERGE_AUTHORIZATION: ENABLED
SECOND_HUMAN_MERGE_CONFIRMATION_REQUIRED: NO
CHATGPT_PASS_REVIEW_REQUIRED: YES
WORKER_MERGE_AUTHORITY: NO
EXACT_REVIEWED_HEAD_BINDING: YES
EXACT_REVIEWED_MAIN_BINDING: YES
MAIN_DRIFT_FAIL_CLOSED: YES
TASK_HEAD_DRIFT_FAIL_CLOSED: YES
FAST_FORWARD_ONLY: YES
FORCE_UPDATE_ALLOWED: NO
POST_MERGE_IDENTITY_REQUIRED: YES
MERGE_REAUDIT_REQUIRED: NO
STABLE_BLOCK_REASON_CODES: YES
PAID_API_AUTHORITY_CHANGED: NO
H0_CHANGED: NO
H1_STARTED: NO
TARGETED_TESTS: PASS
FULL_REPOSITORY_TESTS: PASS
REGRESSIONS: 0
```
