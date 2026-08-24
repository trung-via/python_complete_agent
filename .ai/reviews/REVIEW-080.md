# REVIEW-080 — H2 Canonical Structural + Experience Graph Completion Implementation

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO

TASK_ID: TASK-080
REVIEW_ROUND: 2
REVIEWED_TASK_HEAD_SHA: e587c3f6c254d9edd17706f689e7d4e4065fa2cd
REVIEWED_BASE_MAIN_SHA: a2fe1e7273503d6dc1863ae00ac3c026192bb2a2
PREVIOUS_REVIEWED_HEAD_SHA: 20c228c29843b3eee90935e74ad648dd1339a18b
TASK_ARTIFACT_BLOB_SHA: c53f846f6cf3478bcc2fe0f59f92a71f36a41b00
RESULT_BLOB_SHA: 9efd9494f79861cee7b5cc1077dfb6ee88fd778d
EXECUTOR_ID: antigravity
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: codex
FAILOVER_TO_EXECUTOR: antigravity
BLOCKERS_REMAINING: 1
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: PASS
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-ENGINEERING-H-SERIES
ROADMAP_VERSION: 1.0
ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
MILESTONE: H2
CAPABILITY_ID: H2_STRUCTURAL_EXPERIENCE_GRAPH
H2_R1_STRUCTURAL_GRAPH: PASS
H2_R2_EXPERIENCE_GRAPH: BLOCKED_BY_ONE_RESIDUAL_GRAMMAR_DEFECT
H2_R3_COMBINED_IDENTITY: PASS_FOR_CURRENT_SLICE
H2_R4_RANKING_BOUNDARY: PASS
H2_FORMAL_COMPLETION: NO
H3_NEW_WORK_AUTHORIZED: NO
H4_H8_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
BASE_MAIN_SHA: a2fe1e7273503d6dc1863ae00ac3c026192bb2a2
BRANCH: ai/task-080
REVIEWED_TASK_HEAD_SHA: e587c3f6c254d9edd17706f689e7d4e4065fa2cd
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 2
BEHIND_BY: 0
FIX_DELTA_VS_PREVIOUS_HEAD: 1 commit
```

Round-2 FIX delta is limited to the two authorized implementation/test paths plus Bridge-generated RESULT update:

```text
src/aios_engineering/harness/structural_experience_graph.py
tests/aios_engineering/harness/test_structural_experience_graph.py
.ai/results/RESULT-080.md
```

Validation evidence:

```text
TARGETED_H2_SUITE: 154 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2472 passed, 7 skipped, 0 failed
GIT_DIFF_CHECK: PASS
NETWORK/LLM/PAID_API: NONE
```

## Previous Findings

### B1 — Top-level Markdown machine evidence boundary

STATUS: CLOSED

The FIX adds a bounded fence-aware top-level scanner for TASK/invariant markers and makes REVIEW finding/component-path parsing fence-aware. The required fenced-example and duplicate-top-level regression cases are present.

### B2 — RESULT Review Manifest CRLF grammar

STATUS: PARTIALLY CLOSED

LF/CRLF handling is now line-ending safe and the tests preserve real CRLF bytes in Git fixtures. TASK_ID/path matching, bounded EXECUTOR_ID, duplicate manifest rejection, and malformed scalar rejection remain fail-closed.

However one residual closed-grammar defect remains and blocks H2.R2.

## Blocking Finding

### B3 — CRLF rewrite weakened the RESULT Review Manifest top-level evidence boundary

The previous RESULT grammar was anchored to a column-0 heading (`^## Review Manifest`). The new line-ending-safe parser discovers headings with:

```python
line.strip() == "## Review Manifest"
```

and similarly strips the following fence/scalar lines before validating them.

This accepts content that is not a canonical top-level Review Manifest. For example an indented Markdown code block can be interpreted as executor evidence:

```text
    ## Review Manifest
    ```yaml
    TASK_ID: TASK-080
    EXECUTOR_ID: example-executor
    ```
```

A heading-shaped line inside another fenced example can also be counted as the unique Review Manifest because heading discovery is not fence-aware.

That violates ADR-053's evidence-only rule: `TASK EXECUTED_BY EXECUTOR` must come from the canonical closed Review Manifest, not from example/test/log text that happens to contain the same grammar.

#### Required FIX

Keep the CRLF-safe `splitlines()` approach, but restore a closed top-level Markdown boundary for RESULT evidence:

```text
Review Manifest heading must be exact column-0 outside fenced code
its opening/closing fence must belong to that top-level section
indented code-block headings must not count
heading-shaped text inside fenced examples must not count
one genuine top-level Review Manifest remains required when present
LF and CRLF remain semantically equivalent
TASK_ID/EXECUTOR_ID validation remains unchanged
exact Git blob verification remains before parsing
```

Prefer reusing or generalizing the local bounded fence-aware scanner/state logic already introduced in this module; do not import Bridge authority parsing.

#### Required regression tests

Add tests proving at minimum:

```text
RESULT_TOP_LEVEL_MANIFEST_LF: PASS
RESULT_TOP_LEVEL_MANIFEST_CRLF: PASS
RESULT_INDENTED_MANIFEST_EXAMPLE: IGNORED
RESULT_MANIFEST_HEADING_INSIDE_FENCE: IGNORED
REAL_TOP_LEVEL_PLUS_FENCED_MANIFEST_EXAMPLE: EXACTLY_ONE_REAL_MANIFEST
TWO_REAL_TOP_LEVEL_MANIFESTS: FAIL_CLOSED
```

For the ignored-only cases, zero `TASK_EXECUTED_BY_EXECUTOR` edges is valid and preferable to invented evidence.

## FIX Scope

Permitted paths only:

```text
src/aios_engineering/harness/structural_experience_graph.py
tests/aios_engineering/harness/test_structural_experience_graph.py
```

Do not modify:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/graph.py
src/aios_engineering/harness/roles.py
src/aios_engineering/harness/ranking.py
src/aios_engineering/harness/experience.py
src/aios_engineering/harness/discovery.py
Bridge/runtime/governance code
roadmap/completion records
H3-H8 capability code
```

No structural-graph redesign is authorized.

## Machine-Readable FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-080.md","blob_sha":"c53f846f6cf3478bcc2fe0f59f92a71f36a41b00"},{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/decisions/ADR-053-AIOS-ENGINEERING-H2-CANONICAL-STRUCTURAL-EXPERIENCE-GRAPH-COMPLETION-CONTRACT-LOCK.md","blob_sha":"5f484356baf69aaf0f5426c0dbb150c04a9d22f9"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/structural_experience_graph.py","tests/aios_engineering/harness/test_structural_experience_graph.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_structural_experience_graph.py tests/aios_engineering/harness/test_graph.py tests/aios_engineering/harness/test_roles.py tests/aios_engineering/harness/test_ranking.py tests/aios_engineering/harness/test_experience.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Publish only through the canonical Bridge FIX flow.

## Decision

```text
TASK-080: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
BLOCKERS_REMAINING: 1
B1_TOP_LEVEL_TASK_REVIEW_EVIDENCE_BOUNDARY: CLOSED
B2_RESULT_CRLF_GRAMMAR: CLOSED_EXCEPT_B3_TOP_LEVEL_BOUNDARY
B3_RESULT_TOP_LEVEL_REVIEW_MANIFEST_BOUNDARY: OPEN
H2_R1: PASS
H2_R2: BLOCKED
H2_R3: PASS_FOR_CURRENT_SLICE
H2_R4: PASS
H2_FORMAL_COMPLETION: NO
H3_NEW_WORK_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```
