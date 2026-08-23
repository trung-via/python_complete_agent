# REVIEW-069 — Lean Auto-Merge / Reviewed-Head Binding Implementation

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
READY_FOR_AUTO_MERGE: NO
MERGED_TO_MAIN: NO
H1_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
TASK_ID: TASK-069
BASE_MAIN_SHA: bd4cc149352683de02884cb6da6b55074c74e205
BRANCH: ai/task-069
REVIEWED_TASK_HEAD_SHA: 172f3acec77fa3940ee41e20501867f334b6056f
REVIEWED_BASE_MAIN_SHA: bd4cc149352683de02884cb6da6b55074c74e205
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: bd4cc149352683de02884cb6da6b55074c74e205
TASK_BLOB_SHA: 7f371fc934ffe00dac6bb508c636718a02d984ad
RESULT_BLOB_SHA: ae333a33502e58ba980a76cddc998d6093a4d440
REVIEW_MERGE_BLOB_SHA: dcb60da22f63edd43b16069dce63d53ecf1f3e46
BRIDGE_BLOB_SHA: 0aa8b03ae5405d25ae534a5305354341b1fd8bbb
UNIT_TEST_BLOB_SHA: 656e4793602382e4524667291f379e38041ba5dd
BRIDGE_TEST_BLOB_SHA: e40e7c2c580816e0f3f2f00eaf843128c145f18a
```

The branch is a clean one-commit fast-forward descendant of the unchanged reviewed baseline. Scope is confined to TASK-069 authorized implementation/test/documentation paths plus Bridge-generated RESULT-069.

## Test Evidence — PASS

```text
TARGETED: 50 passed, 0 skipped, 0 failed
FULL:     2142 passed, 7 skipped, 0 failed
```

No paid provider execution is evidenced by TASK-069.

## Findings — CHANGES_REQUIRED

### B1 — Compatibility alias conflicts do not fail closed

`parse_review_header()` accepts compatibility aliases:

```text
AUTO_MERGE_ALLOWED
REVIEWED_HEAD_SHA
BASE_MAIN_SHA
```

but when both canonical and alias fields are present, the implementation simply prefers the canonical key. It does not reject conflicting canonical/alias values.

Examples that must fail closed but currently authorize/parse through include semantic shapes equivalent to:

```text
AUTO_MERGE_ELIGIBLE: YES
AUTO_MERGE_ALLOWED: NO
```

and conflicting reviewed-head/base aliases.

ADR-042 explicitly locks ambiguous or conflicting compatibility fields to fail closed. Add deterministic conflict/duplicate-equivalence checks and regression tests for all supported alias pairs.

### B2 — Strict authority tokens are normalized instead of validated exactly

The parser currently applies `.upper()` to STATUS / APPROVED / AUTO_MERGE values and `.lower()` to reviewed SHA values before validation.

Therefore malformed/non-canonical authority text such as lowercase `pass`, lowercase `yes`, or uppercase SHA text is silently normalized into an authoritative value.

TASK-069 requires exact machine-readable parsing, exact YES/NO semantics, and exact lowercase 40-hex SHA binding. Reject non-canonical casing rather than canonicalizing it. Add adversarial tests for lowercase/mixed-case status and YES/NO values plus uppercase/mixed-case SHAs.

### B3 — Bridge merge command emits ad-hoc reason codes outside the closed merge vocabulary

`cmd_merge_reviewed()` emits codes such as:

```text
REVIEW_PARSE_FAILED
GATE_EVALUATION_ERROR
```

but these are not members of `MergeGateReason`. At the same time required stable reasons such as `REVIEW_HEAD_INVALID` and `REVIEW_BASE_INVALID` are declared but not surfaced through command-level parse failures.

The merge control surface must expose one closed deterministic reason vocabulary. Map parse/preflight failures to explicit `MergeGateReason` values (or extend the enum only if contractually justified) and test that every command-level block reason belongs to the closed vocabulary. Unknown exceptions must fail closed without inventing a new free-form authority reason.

### B4 — Post-merge identity does not re-resolve the task branch and post-fetch failure is ignored

After the push, the command runs a fetch but does not check `p_post_fetch.returncode`. It then re-resolves only remote main. It never re-resolves the task branch.

ADR-042/TASK-069 require post-mutation verification of both:

```text
main == REVIEWED_TASK_HEAD_SHA
main vs task branch == IDENTICAL
```

A concurrent task-branch movement after the preflight can therefore go undetected, and a failed post-fetch is not itself fail-closed. Require successful post-fetch/ref resolution, re-resolve both remote main and remote task branch, and prove both equal the exact reviewed head before persisting a successful merge receipt. Add regression tests for post-fetch failure and post-merge task-head drift.

## Scope / Boundary Audit

The overall architecture direction is correct:

```text
worker merge authority: NO
ChatGPT PASS review required: YES
fast-forward-only push: YES
force flag: absent
main/task drift preflight: present
no full test rerun during merge: YES
no review re-audit during merge: YES
H-Series modified: NO
```

These PASS items do not override B1-B4 because TASK-069 changes merge authority and must remain strict/fail-closed at every authority boundary.

## Decision

```text
TASK-069: CHANGES_REQUIRED
B1_ALIAS_CONFLICT_FAIL_CLOSED: FAIL
B2_EXACT_AUTHORITY_TOKEN_PARSING: FAIL
B3_CLOSED_COMMAND_REASON_VOCABULARY: FAIL
B4_POST_MERGE_DUAL_REF_IDENTITY: FAIL
BLOCKERS_REMAINING: 4
AUTO_MERGE_EXECUTED: NO
MAIN_CHANGED_BY_REVIEW: NO
H1_AUTHORIZED: NO
```

Because this review is not PASS, ADR-042 standing authorization does not permit auto-merge. Run a bounded FIX on TASK-069 and submit the new exact task head for review. If the subsequent exact-SHA review is PASS and the lean merge gate is current, ChatGPT will auto-merge without a second Human confirmation.
