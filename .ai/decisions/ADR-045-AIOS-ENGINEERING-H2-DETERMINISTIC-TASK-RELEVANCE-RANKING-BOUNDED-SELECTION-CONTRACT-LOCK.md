# ADR-045 — AIOS Engineering H2 Deterministic Task Relevance Ranking & Bounded Selection Contract Lock

STATUS: LOCKED
DATE: 2026-08-23
SCOPE: AIOS Engineering H-Series H2
BASELINE_MAIN_SHA: 0f803c2d66244147734c5b8f5ea3670c6f57c6cc
H0_STATUS: COMPLETE
H1_STATUS: COMPLETE
TASK_AUTHORING_PREFLIGHT_STATUS: COMPLETE
LEAN_AUTO_MERGE: ENABLED
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
H2_AUTHORIZED: YES

## 1. Decision

H2 implements deterministic task-aware relevance ranking and bounded evidence selection over one exact H1 `RepositoryDiscoveryResult`.

H2 is an advisory repository-intelligence layer only. It does not read mutable worktree bytes, invoke Git, call a model/provider, select an executor, mutate Bridge state, create execution authority, or merge code.

Locked flow:

```text
H1 RepositoryDiscoveryResult
        +
TaskRelevanceSpec
        ↓
validate exact deterministic ranking inputs
        ↓
score each H1 evidence candidate using path/kind metadata only
        ↓
deterministic total ordering
        ↓
bounded selected evidence + deterministic exclusions
        ↓
H0 HarnessIntelligencePlan
        ↓
RepositoryRankingResult + zero-authority HarnessReceipt
```

H2 intentionally does not perform raw-source semantic analysis. Later H-Series milestones may add bounded content/symbol/graph intelligence under separate contracts.

## 2. Authority Boundary — Unchanged

ADR-038 remains authoritative.

H2 MAY:

```text
CONSUME_H1_DISCOVERY_RESULT: YES
READ_EVIDENCE_METADATA: YES
NORMALIZE_BOUNDED_TASK_HINTS: YES
SCORE_RELEVANCE_DETERMINISTICALLY: YES
RANK_EVIDENCE: YES
BOUND_SELECTION: YES
CREATE_HARNESS_INTELLIGENCE_PLAN: YES
EMIT_ZERO_AUTHORITY_RECEIPT: YES
```

H2 MUST NOT:

```text
READ_WORKTREE_FILE_BYTES: FORBIDDEN
READ_GIT_OBJECT_BODY: FORBIDDEN
GIT_SUBPROCESS: FORBIDDEN
NETWORK_CALL: FORBIDDEN
LLM_CALL: FORBIDDEN
PAID_API_CALL: FORBIDDEN
PROVIDER_CREDENTIAL_VALUE_READ: FORBIDDEN
TASK_STATE_AUTHORITY: FORBIDDEN
REVIEW_STATE_AUTHORITY: FORBIDDEN
EXECUTOR_SELECTION_AUTHORITY: FORBIDDEN
LEASE_AUTHORITY: FORBIDDEN
DISPATCH_AUTHORITY: FORBIDDEN
RETRY_OR_FAILOVER_AUTHORITY: FORBIDDEN
BRIDGE_STATE_MUTATION: FORBIDDEN
MERGE_AUTHORITY: FORBIDDEN
```

No ranking score, selected evidence item, plan, result, fingerprint, or receipt grants execution or merge authority.

## 3. Exact H1 Input Binding

H2 consumes exactly one H1 `RepositoryDiscoveryResult`.

The H2 output must bind:

```text
repository snapshot commit SHA
repository snapshot tree SHA
H1 discovery fingerprint
H1 candidate-set fingerprint
H2 policy version
TaskRelevanceSpec fingerprint
```

H2 must not re-discover the repository, substitute worktree bytes, silently add candidates, or silently drop candidates from accounting.

Every H1 evidence candidate must end in exactly one H2 outcome:

```text
SELECTED
H2_ZERO_RELEVANCE
H2_SELECTION_BOUND
```

The union of selected + excluded evidence must account for the complete H1 evidence candidate set exactly once.

## 4. TaskRelevanceSpec

H2 introduces an immutable bounded task relevance specification.

Required semantic fields:

```text
task_id
exact_paths        # exact canonical repo-relative paths
path_prefixes      # canonical repo-relative path-prefix roots
query_terms        # canonical lowercase ASCII relevance terms
preferred_kinds    # exact EvidenceKind tuple
max_selected       # bounded positive integer
schema_version
```

Rules:

- `task_id` uses H0 canonical TASK semantics;
- all collection inputs are exact tuples; silent list/generator coercion is forbidden;
- duplicates are rejected;
- exact paths use H0 path validation;
- path prefixes are canonical repo-relative paths and match `path == prefix` or `path.startswith(prefix + "/")`;
- query terms use a bounded lowercase ASCII token grammar and are deduplicated;
- preferred kinds are exact `EvidenceKind` values with no duplicates;
- at least one relevance signal must be present across exact paths, prefixes, terms, or preferred kinds;
- `max_selected` is an exact int, bool forbidden, range `1..32`.

Hard bounds:

```text
MAX_EXACT_PATH_HINTS: 32
MAX_PATH_PREFIX_HINTS: 32
MAX_QUERY_TERMS: 64
MAX_QUERY_TERM_LENGTH: 64
MAX_SELECTED_EVIDENCE: 32
```

No free-form task prose is stored or interpreted by H2.

## 5. Deterministic Ranking Policy v1

Policy identity:

```text
H2_RANKING_POLICY_VERSION = h2-v1
```

For each H1 evidence candidate, compute an integer relevance score from metadata only:

```text
EXACT_PATH_MATCH            +600
ANY_PATH_PREFIX_MATCH       +300
QUERY_TERM_PATH_MATCH       +30 per distinct matched term, capped at +180
PREFERRED_EVIDENCE_KIND     +100
```

Final score is clamped to `0..1000`.

Query-term matching is against deterministic lowercase path tokens derived only from the canonical repository path. Tokenization uses an explicit ASCII delimiter rule; it does not inspect file content.

No hidden weights, timestamps, filesystem order, random state, model output, executor identity, or ambient environment may influence scoring.

## 6. Selection and Tie-Breaking

Candidate ranking order is exact:

```text
1. higher relevance score first
2. canonical path ascending
3. blob SHA ascending
```

A candidate with score `0` is excluded with:

```text
H2_ZERO_RELEVANCE
```

Positive-score candidates beyond `max_selected` are excluded with:

```text
H2_SELECTION_BOUND
```

Selected candidates receive a new immutable H2 `RepositoryEvidenceRef` preserving:

```text
path
blob_sha
evidence_kind
symbol_locator
```

and setting:

```text
reason_code = H2_TASK_RELEVANCE
priority = computed relevance score
```

Excluded candidates are represented through H0 `HarnessEvidenceExclusion` around the same H2-ranked evidence identity, with the deterministic exclusion reason above.

H1 input evidence objects must not be mutated.

## 7. HarnessIntelligencePlan Reuse

H2 must reuse the existing H0 `HarnessIntelligencePlan`; it must not create a competing plan authority model.

Plan semantics:

```text
task_id             = TaskRelevanceSpec.task_id
snapshot            = H1 exact snapshot
selected_evidence   = ranked H2 selected tuple
excluded_evidence   = deterministic H2 exclusions
```

The existing H0 candidate-set and plan fingerprint semantics remain authoritative.

Selected ranking order is semantically meaningful and therefore plan-fingerprint-sensitive.

## 8. RepositoryRankingResult

H2 introduces an immutable result wrapper with semantic fields at minimum:

```text
schema_version
policy_version
task_id
discovery_fingerprint
input_candidate_set_fingerprint
relevance_spec_fingerprint
plan: HarnessIntelligencePlan
ranking_fingerprint
```

`ranking_fingerprint` must deterministically bind all semantic fields above, including the exact ranked plan.

The result must verify its own fingerprints during construction and fail closed on mismatch.

## 9. HarnessReceipt

H2 emits an H0 `HarnessReceipt`.

Locked values:

```text
authority_created: FALSE
network_used: FALSE
llm_used: FALSE
paid_api_used: FALSE
```

Receipt semantics:

```text
candidate_count = len(H1 evidence)
selected_count  = len(plan.selected_evidence)
excluded_count  = len(plan.excluded_evidence)
input_fingerprint binds H1 discovery + relevance spec + H2 policy
output_fingerprint = H2 ranking fingerprint
```

Counts must satisfy:

```text
candidate_count == selected_count + excluded_count
```

## 10. Determinism / Purity

For identical H1 discovery result + identical `TaskRelevanceSpec` + identical H2 policy version:

```text
scores: identical
rank order: identical
selected/excluded partition: identical
plan fingerprint: identical
ranking fingerprint: identical
receipt: identical except for no time-dependent fields (none are permitted)
```

H2 must not read wall-clock time, random state, process environment, current branch, current working tree, remote refs, or provider state.

## 11. Error / Fail-Closed Semantics

At minimum reject:

```text
non-H1 discovery input
non-tuple spec collections
empty relevance signal set
duplicate hints/terms/kinds
invalid canonical path/prefix
invalid query token
hint/term count bound exceeded
max_selected outside 1..32
fingerprint mismatch
candidate accounting mismatch
duplicate/ambiguous H1 candidate identity
```

No partial plan may be returned after validation failure.

No retry or fallback is introduced.

## 12. Namespace / Implementation Boundary

Preferred implementation:

```text
src/aios_engineering/harness/ranking.py
```

Exports may be added to:

```text
src/aios_engineering/harness/__init__.py
```

H2 must not modify:

```text
bridge.py
src/aios_bridge/**
src/aios_engineering/harness/contracts.py
src/aios_engineering/harness/discovery.py
src/aios_engineering/harness/fingerprint.py
.agents/**
```

No dependency changes.

## 13. Acceptance Tests

Tests must prove at minimum:

```text
H1_DISCOVERY_INPUT_BOUND_EXACTLY: YES
H1_INPUT_MUTATED: NO

TASK_SPEC_EXACT_TUPLES_REQUIRED: YES
EMPTY_RELEVANCE_SPEC_ACCEPTED: NO
DUPLICATE_HINT_ACCEPTED: NO
QUERY_TERM_BOUNDS_ENFORCED: YES
MAX_SELECTED_BOUND_ENFORCED: YES

EXACT_PATH_WEIGHT: EXACT
PATH_PREFIX_WEIGHT: EXACT
TERM_WEIGHT_AND_CAP: EXACT
PREFERRED_KIND_WEIGHT: EXACT
SCORE_CLAMP: EXACT

ZERO_SCORE_SELECTED: NO
SELECTION_BOUND_ENFORCED: YES
TIE_BREAK_ORDER_DETERMINISTIC: YES
ALL_H1_CANDIDATES_ACCOUNTED_ONCE: YES

H0_PLAN_REUSED: YES
PLAN_RANK_ORDER_FINGERPRINT_SENSITIVE: YES
RANKING_FINGERPRINT_DETERMINISTIC: YES
DISCOVERY_FINGERPRINT_BOUND: YES
SPEC_FINGERPRINT_BOUND: YES

NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
AUTHORITY_CREATED: NO
GIT_SUBPROCESS_USED: NO
WORKTREE_BYTES_READ: NO
BRIDGE_RUNTIME_CHANGED: NO
```

Tests use synthetic H1 discovery results only; no real Git repository, network, Codex, or Antigravity process is required for H2 unit behavior.

## 14. Sequence

```text
H0 Foundation ✅
H1 Repository Snapshot Discovery & Provenance ✅
Task Authoring Preflight Hardening ✅
        ↓
H2 Deterministic Task Relevance Ranking & Bounded Selection
        ↓
subsequent H milestones
```

H2 completion does not silently authorize H3 implementation.

## 15. Reopen Conditions

This contract may be reopened only by explicit Human direction and a new architecture decision. Later H milestones may add content/symbol/graph intelligence, compression, skill compilation, or executor-specific rendering, but they must preserve ADR-038 authority separation and exact provenance binding.
