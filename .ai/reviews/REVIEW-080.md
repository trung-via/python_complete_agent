# REVIEW-080 — H2 Canonical Structural + Experience Graph Completion Implementation

STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO

TASK_ID: TASK-080
REVIEWED_TASK_HEAD_SHA: 20c228c29843b3eee90935e74ad648dd1339a18b
REVIEWED_BASE_MAIN_SHA: a2fe1e7273503d6dc1863ae00ac3c026192bb2a2
TASK_ARTIFACT_BLOB_SHA: c53f846f6cf3478bcc2fe0f59f92a71f36a41b00
RESULT_BLOB_SHA: a9042443ddceee5275d235876c88a88c68afd729
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 2
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
H2_R2_EXPERIENCE_GRAPH: BLOCKED
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
REVIEWED_TASK_HEAD_SHA: 20c228c29843b3eee90935e74ad648dd1339a18b
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
CUMULATIVE_IMPLEMENTATION_SCOPE: EXACT
```

Published delta is limited to:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/structural_experience_graph.py
tests/aios_engineering/harness/test_structural_experience_graph.py
.ai/results/RESULT-080.md
```

Recovery publication is accepted as valid evidence. Codex timed out before publication, but the preserved worktree stayed exactly inside TASK-080 allowed paths; targeted validation passed before recovery publication and Bridge subsequently ran the full canonical suite before commit/push.

Validation evidence:

```text
TARGETED_H2_SUITE: 152 passed, 1 warning
FULL_REPOSITORY_TESTS: 2470 passed, 7 skipped, 0 failed
RECOVERY_PUBLICATION: YES
EXECUTOR_RERUN: NO
ORIGINAL_TRANSPORT: TIMED_OUT
TASK_BRANCH_REMOTE_PUBLICATION: PASS
```

The timeout itself is not a review blocker.

## Passing Areas

```text
H2_CANONICAL_POLICY_IDENTITY: PASS
UPSTREAM_EXACT_CROSS_BINDING: PASS
FILE_TO_SYMBOL_TO_COMPONENT: PASS
DEEPEST_PACKAGE_COMPONENT_RULE: PASS
STANDALONE_MODULE_COMPONENT_RULE: PASS
STATIC_IMPORT_GRAPH_BOUND_NOT_REPARSED: PASS
AMBIGUOUS_UNRESOLVED_IMPORTS: CONSERVATIVE
EXACT_LOCAL_GIT_BLOB_IDENTITY: PASS
WORKTREE_EXPERIENCE_BYTES_USED: NO
BODY_AND_TOTAL_BOUNDS: PASS
NODE_EDGE_ORDERING: PASS
NODE_EDGE_GRAPH_FINGERPRINTS: PASS
ZERO_AUTHORITY_RECEIPT: PASS
NO_SECOND_SYMBOL_AST_PARSE: PASS
NO_H3_OWNERSHIP_SEMANTICS: PASS
NO_H3_EXECUTOR_TENDENCY: PASS
NO_H4_KNOWLEDGE_LIFECYCLE: PASS
NETWORK_LLM_PAID_API: NONE
```

These areas must remain unchanged unless a minimal parser fix requires an internal helper adjustment.

## Blocking Findings

### B1 — Machine evidence parser does not enforce the locked top-level Markdown boundary

TASK-080 authorizes task scope evidence only from an **exact top-level** machine marker. The implementation currently resolves marker values by splitting the entire Markdown body and accepting any line that begins with the marker token.

Current behavior is equivalent to:

```python
values = [
    line[len(prefix):].strip()
    for line in text.splitlines()
    if line.startswith(prefix)
]
```

This is not a top-level Markdown evidence parser. A marker-shaped line inside a fenced code example is indistinguishable from authoritative evidence. It can therefore:

```text
create a false TASK_TOUCHES_COMPONENT edge
create a false INVARIANT node/edge
or cause a false duplicate-marker hard failure
```

This is not theoretical: TASK-080 itself already exposed the same failure class at Bridge preflight when prose repeated a machine-marker-shaped example. H2 must not reproduce that failure class inside its long-lived experience graph.

#### Required FIX

Implement one local, pure, bounded Markdown evidence scanner for H2 machine markers that at minimum:

```text
accepts only column-0 marker lines outside fenced code blocks
ignores marker-shaped text inside fenced code blocks
continues to ignore blockquotes/indented prose because they are not column-0 markers
supports the exact EXECUTOR_ALLOWED_PATHS and H2 invariant marker grammars already locked
rejects multiple genuine top-level occurrences
preserves strict JSON / duplicate-key / path validation
uses no Bridge authority parser import
```

The scanner must be bounded by the already-read bounded artifact body; do not add another unbounded body read.

Also make REVIEW finding heading/path parsing fence-aware enough that a heading or H2 component-path evidence line inside a fenced example cannot create a review-finding/component relationship.

#### Required tests

Add tests proving at minimum:

```text
TOP_LEVEL_TASK_MARKER: PARSED
TASK_MARKER_INSIDE_FENCE: IGNORED
TOP_LEVEL_PLUS_FENCED_EXAMPLE: EXACTLY_ONE_REAL_MARKER
TWO_TOP_LEVEL_TASK_MARKERS: FAIL_CLOSED
INVARIANT_MARKER_INSIDE_FENCE: IGNORED
REVIEW_FINDING_HEADING_INSIDE_FENCE: IGNORED
REVIEW_COMPONENT_PATH_INSIDE_FENCE: IGNORED
```

### B2 — RESULT Review Manifest parser rejects Bridge-generated CRLF artifacts

The implementation's RESULT parser uses LF-only regular-expression structure around `## Review Manifest` and its fenced block. Exact Bridge publication evidence is not guaranteed to be LF-only.

The reviewed `RESULT-080` itself is concrete counter-evidence: its Git diff/body uses CRLF line endings, while it contains a valid closed Review Manifest with:

```text
TASK_ID: TASK-080
EXECUTOR_ID: codex
```

Under the current parser, the LF-only heading/fence expressions do not recognize that block. The artifact is therefore capable of falling through as no executor machine evidence instead of emitting:

```text
TASK-080 -> TASK_EXECUTED_BY_EXECUTOR -> codex
```

That violates canonical H2.R2's requirement to represent task/executor experience relationships **where evidence exists**.

#### Required FIX

Make the closed RESULT Review Manifest grammar line-ending safe after exact blob verification.

Allowed approaches include:

```text
bounded parsing over splitlines()
or an equivalent exact grammar supporting LF and CRLF
```

Requirements:

```text
exact Git blob SHA remains verified before parsing
line-ending normalization/parsing must not replace provenance identity
one closed Review Manifest only
TASK_ID must still equal RESULT path identity
EXECUTOR_ID remains bounded/closed
malformed/duplicate scalar evidence remains fail-closed
```

#### Required tests

Add tests proving:

```text
RESULT_REVIEW_MANIFEST_LF: PASS
RESULT_REVIEW_MANIFEST_CRLF: PASS
LF_AND_CRLF_SEMANTIC_RELATION: EQUIVALENT
RESULT_TASK_ID_MISMATCH_CRLF: FAIL_CLOSED
DUPLICATE_REVIEW_MANIFEST_CRLF: FAIL_CLOSED
```

At least one fixture must use bytes/text that actually preserve CRLF into the committed Git blob, not merely a Python string later rewritten as LF by the fixture helper.

## FIX Scope

The FIX is intentionally narrow.

Permitted production/test paths:

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

No redesign of the structural graph is requested. Fix only the closed evidence grammar and regression tests.

## Machine-Readable FIX Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-080.md","blob_sha":"c53f846f6cf3478bcc2fe0f59f92a71f36a41b00"},{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/decisions/ADR-053-AIOS-ENGINEERING-H2-CANONICAL-STRUCTURAL-EXPERIENCE-GRAPH-COMPLETION-CONTRACT-LOCK.md","blob_sha":"5f484356baf69aaf0f5426c0dbb150c04a9d22f9"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/structural_experience_graph.py","tests/aios_engineering/harness/test_structural_experience_graph.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_structural_experience_graph.py tests/aios_engineering/harness/test_graph.py tests/aios_engineering/harness/test_roles.py tests/aios_engineering/harness/test_ranking.py tests/aios_engineering/harness/test_experience.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Publish only through canonical Bridge E4 FIX flow.

## Decision

```text
TASK-080: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
BLOCKERS_REMAINING: 2
B1_TOP_LEVEL_MARKDOWN_EVIDENCE_BOUNDARY: OPEN
B2_RESULT_CRLF_GRAMMAR: OPEN
H2_R1: PASS
H2_R2: BLOCKED
H2_R3: PASS_FOR_CURRENT_SLICE
H2_R4: PASS
H2_FORMAL_COMPLETION: NO
H3_NEW_WORK_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```
