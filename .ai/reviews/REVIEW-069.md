# REVIEW-069 — Lean Auto-Merge / Reviewed-Head Binding Implementation

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
READY_FOR_AUTO_MERGE: NO
MERGED_TO_MAIN: NO
H1_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
REVIEWED_TASK_HEAD_SHA: d8574ba6dd661ca20791f8c9fa51cc064fbb51c0
REVIEWED_BASE_MAIN_SHA: bd4cc149352683de02884cb6da6b55074c74e205

## Reviewed Snapshot

```text
TASK_ID: TASK-069
BASE_MAIN_SHA: bd4cc149352683de02884cb6da6b55074c74e205
BRANCH: ai/task-069
CURRENT_REVIEWED_HEAD: d8574ba6dd661ca20791f8c9fa51cc064fbb51c0
BRANCH_STATUS_VS_MAIN: AHEAD
AHEAD_BY: 2
BEHIND_BY: 0
MERGE_BASE_SHA: bd4cc149352683de02884cb6da6b55074c74e205
TASK_BLOB_SHA: 7f371fc934ffe00dac6bb508c636718a02d984ad
RESULT_BLOB_SHA: bbae02de18e05e6dc4f9eb07d3a7b16d6db6f0c0
REVIEW_MERGE_BLOB_SHA: 7fd49cdb9b51e98c70297729ae8d8f59a3779262
BRIDGE_BLOB_SHA: 6b4bc9e1b460c5796aa6fc90277067bf01ab246c
UNIT_TEST_BLOB_SHA: 004ea636ffef110a1cbc4beb6aeb9b31b11a796d
BRIDGE_TEST_BLOB_SHA: 3a85416152af55f7e5d021ae5d4aaccc6622c92c
```

Cumulative scope remains confined to TASK-069 authorized implementation/test/documentation paths plus Bridge-generated RESULT-069. The branch is a two-commit fast-forward descendant of the unchanged baseline main.

## Test Evidence — PASS

```text
TARGETED: 61 passed, 0 skipped, 0 failed
FULL:     2153 passed, 7 skipped, 0 failed
```

The previously reported B1-B4 are resolved on this exact head:

```text
B1_ALIAS_CONFLICT_FAIL_CLOSED: PASS
B2_CASE_SENSITIVE_AUTHORITY_TOKENS: PASS
B3_ENUM_BACKED_COMMAND_REASON_CODES_FOR_COVERED_PATHS: PASS
B4_POST_MERGE_DUAL_REF_IDENTITY: PASS
```

No paid provider execution is evidenced by TASK-069.

## Remaining Findings — CHANGES_REQUIRED

### B5 — Review parser is not actually anchored to the review header

`parse_review_header()` scans every line in the entire Markdown document. Fence delimiter lines are skipped, but lines inside fenced examples are still parsed as authoritative key/value records.

Therefore a document with no authoritative top header can still satisfy the parser if a later prose/example/code block contains the five merge keys. This violates the TASK-069 requirement for a narrow machine-readable review-header parser and the rule that PASS authority must not be inferred from non-header prose/examples.

Required fix:

- define and parse only one deterministic top-level review header region;
- never treat fenced-code/example/body sections as authority;
- required merge keys must exist in that header region itself;
- add adversarial tests where later fenced/example fields are present but the real header is missing/incomplete;
- preserve duplicate/conflict fail-closed behavior inside the authority header.

While touching this parser, do not silently normalize Markdown wrappers around authority values. Required authority tokens and SHAs should remain exact machine-readable values.

### B6 — Merge authority routing is caller-overridable instead of bound to Bridge configuration

`cmd_merge_reviewed()` loads Bridge config, but then derives `remote`, `base_branch`, `control_branch`, and task prefix from CLI arguments/defaults. The parser exposes `--remote`, `--base-branch`, `--control-branch`, and `--task-branch-prefix`.

That means the repository-owned merge capability can be pointed at a different control branch containing a different review artifact, or at a different destination branch, even though ADR-042 standing authorization is specifically for the configured AIOS control plane and `main`.

Required fix:

- bind merge routing to the configured `remote`, `base_branch`, `control_branch`, and task-branch prefix;
- preferably remove the merge-routing override flags, or fail closed unless supplied values exactly equal the configured values;
- never permit a caller-selected review branch to substitute for configured `ai-control` semantics;
- add tests proving mismatched routing overrides cause zero push attempts.

This does not reduce Human control: a Human can still change Bridge configuration explicitly through the existing setup/configuration boundary. The merge transaction itself must not redefine its authority source or destination.

### B7 — Closed failure semantics still have unguarded paths, including one after main mutation

The covered error paths now emit `MergeGateReason` values, but some command-level failures can still escape as raw exceptions. In particular, `rev-list --left-right --count` output is indexed/converted with no shape/parse guard. Malformed output can raise `IndexError`/`ValueError` outside the closed reason vocabulary.

More importantly, after a successful push and successful post-merge identity proof, receipt-directory creation / receipt-file write is unguarded. A local receipt I/O failure can therefore make the command terminate as an exception even though `main` has already been changed successfully, creating an ambiguous false-failure state and tempting an unnecessary retry.

Required fix:

- validate `rev-list` output shape/counts and map malformed output to a closed fail-closed reason before mutation;
- make post-merge receipt handling deterministic: either preflight a suitable receipt sink before mutation, or after verified merge return/emit the bounded successful receipt even if optional persistence fails, as TASK-069 explicitly permits a bounded structured result when no suitable persistent authority store is available;
- no automatic second push or retry;
- add regression tests for malformed count output and receipt persistence failure after verified merge.

## Decision

```text
TASK-069: CHANGES_REQUIRED
PRIOR_B1_B4: RESOLVED
B5_HEADER_AUTHORITY_ANCHORING: FAIL
B6_CONFIG_BOUND_MERGE_ROUTING: FAIL
B7_TOTAL_CLOSED_FAILURE_SEMANTICS: FAIL
BLOCKERS_REMAINING: 3
AUTO_MERGE_EXECUTED: NO
MAIN_CHANGED_BY_REVIEW: NO
H1_AUTHORIZED: NO
```

Because the exact reviewed head is not PASS, ADR-042 standing authorization does not permit auto-merge. Run one bounded FIX on TASK-069. On the next exact-SHA review, PASS will trigger the lean auto-merge gate automatically without a second Human confirmation.
