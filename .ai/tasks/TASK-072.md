# TASK-072 — H2 Deterministic Task Relevance Ranking & Bounded Selection

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS ENGINEERING H-SERIES
MILESTONE: H2
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: 0f803c2d66244147734c5b8f5ea3670c6f57c6cc
TARGET_BRANCH: ai/task-072
H0_STATUS: COMPLETE
H1_STATUS: COMPLETE
TASK_AUTHORING_PREFLIGHT_STATUS: COMPLETE
H2_STATUS: AUTHORIZED_BY_ADR_045
H3_IMPLEMENTATION_AUTHORIZED: NO
LEAN_AUTO_MERGE: ENABLED
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
ADR: ADR-045
ADR_BLOB_SHA: 0cbb4fc90e75bff533e1fd99397f4a1470e39c72
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
REAL_CODEX_REQUIRED: NO
REAL_ANTIGRAVITY_REQUIRED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/decisions/ADR-043-AIOS-ENGINEERING-H1-REPOSITORY-SNAPSHOT-DISCOVERY-PROVENANCE-CONTRACT-LOCK.md","blob_sha":"140e1a03593e31f6681016ae45b427f9b16ee8c9"},{"path":".ai/decisions/ADR-045-AIOS-ENGINEERING-H2-DETERMINISTIC-TASK-RELEVANCE-RANKING-BOUNDED-SELECTION-CONTRACT-LOCK.md","blob_sha":"0cbb4fc90e75bff533e1fd99397f4a1470e39c72"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/ranking.py","tests/aios_engineering/harness/test_ranking.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The publisher profile and the three E4 marker lines above are the complete executable authoring inputs for TASK-072. They create no retry, reroute, paid-provider, merge, executor-substitution, or H3 authority.

## Objective

Implement ADR-045 as a pure/local H2 repository-intelligence layer that consumes one exact H1 `RepositoryDiscoveryResult` plus one bounded immutable `TaskRelevanceSpec`, deterministically scores/ranks every H1 evidence candidate, selects at most 32 relevant items, accounts for every remaining candidate through deterministic exclusions, reuses H0 `HarnessIntelligencePlan`, and emits a fingerprint-bound `RepositoryRankingResult` plus zero-authority `HarnessReceipt`.

H2 must use repository metadata/path signals only. It must not read raw repository file bodies or invoke Git/model/network/provider behavior.

## Writable Scope

Executor may modify/create only:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/ranking.py
tests/aios_engineering/harness/test_ranking.py
```

Bridge-generated `.ai/results/RESULT-072.md` is publication output, not executor writable scope.

Explicitly forbidden:

```text
bridge.py
src/aios_bridge/**
src/aios_engineering/harness/contracts.py
src/aios_engineering/harness/discovery.py
src/aios_engineering/harness/fingerprint.py
src/aios_engineering/harness/errors.py
.agents/**
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
requirements.txt
```

No dependency changes.

## Required Public Surface

Implement in `src/aios_engineering/harness/ranking.py` a repository-owned surface equivalent to:

```python
H2_RANKING_POLICY_VERSION = "h2-v1"

@dataclass(frozen=True)
class TaskRelevanceSpec: ...

@dataclass(frozen=True)
class RepositoryRankingResult: ...

def rank_repository_evidence(
    discovery: RepositoryDiscoveryResult,
    spec: TaskRelevanceSpec,
) -> tuple[RepositoryRankingResult, HarnessReceipt]: ...
```

Exact naming may vary only where necessary, but semantics from ADR-045 are locked. Export the final public H2 surface through `src/aios_engineering/harness/__init__.py`.

## TaskRelevanceSpec Contract

Required fields:

```text
task_id
exact_paths: tuple[str, ...]
path_prefixes: tuple[str, ...]
query_terms: tuple[str, ...]
preferred_kinds: tuple[EvidenceKind, ...]
max_selected: int
schema_version
```

Required validation:

```text
collection type must be exact tuple
silent list/generator coercion forbidden
duplicate exact paths rejected
duplicate prefixes rejected
duplicate query terms rejected
duplicate preferred kinds rejected
at least one relevance signal required
max_selected exact int; bool forbidden
max_selected range 1..32
exact paths canonical under H0 validation
prefixes canonical repository-relative roots
query terms canonical lowercase ASCII bounded tokens
```

Hard limits:

```text
MAX_EXACT_PATH_HINTS = 32
MAX_PATH_PREFIX_HINTS = 32
MAX_QUERY_TERMS = 64
MAX_QUERY_TERM_LENGTH = 64
MAX_SELECTED_EVIDENCE = 32
```

## Ranking Policy v1

Compute exact integer score per H1 evidence candidate:

```text
exact path match        +600
any path-prefix match   +300
query-term path match   +30 per distinct matched term; cap +180
preferred kind match    +100
final score             clamp 0..1000
```

Path query-term tokenization must be explicit and deterministic ASCII path tokenization only. Do not inspect raw blob/file content.

Ranking order:

```text
priority descending
path ascending
blob_sha ascending
```

Do not use timestamps, filesystem enumeration order, random state, environment, current branch, executor identity, or model output.

## Evidence Transformation / Accounting

For every H1 evidence item create a new immutable H2 evidence identity preserving:

```text
path
blob_sha
evidence_kind
symbol_locator
```

and setting:

```text
reason_code = H2_TASK_RELEVANCE
priority = exact computed score
```

Outcome contract:

```text
score == 0
    -> excluded with H2_ZERO_RELEVANCE

score > 0 and inside max_selected
    -> selected

score > 0 and outside max_selected
    -> excluded with H2_SELECTION_BOUND
```

Every H1 evidence candidate must appear exactly once in selected or excluded accounting. H1 input objects/results must not be mutated.

## H0 Plan Reuse

Construct H0 `HarnessIntelligencePlan` using:

```text
task_id = spec.task_id
snapshot = discovery.snapshot
selected_evidence = ranked selected tuple
excluded_evidence = deterministic HarnessEvidenceExclusion tuple
```

Do not introduce a second plan model or alter H0 fingerprint semantics.

## RepositoryRankingResult Contract

Result must immutably bind at minimum:

```text
schema_version
policy_version = h2-v1
task_id
discovery_fingerprint
input_candidate_set_fingerprint
relevance_spec_fingerprint
plan
ranking_fingerprint
```

The relevance-spec fingerprint and ranking fingerprint use existing canonical JSON + SHA-256 helpers from H0.

Result construction must verify fingerprints and cross-bindings fail-closed:

```text
result task_id == plan task_id == spec task_id
result snapshot == discovery snapshot through plan
result discovery_fingerprint == discovery.discovery_fingerprint
result input_candidate_set_fingerprint == discovery.candidate_set_fingerprint
plan selected+excluded count == len(discovery.evidence)
```

## Receipt Contract

Return H0 `HarnessReceipt` with:

```text
authority_created = false
network_used = false
llm_used = false
paid_api_used = false
candidate_count = len(discovery.evidence)
selected_count = len(plan.selected_evidence)
excluded_count = len(plan.excluded_evidence)
input_fingerprint = deterministic binding of H1 discovery + spec + H2 policy
output_fingerprint = ranking_fingerprint
```

No time-dependent fields or secret/provider values.

## Purity Boundary

The H2 implementation module must not import or call:

```text
subprocess
socket
requests/http clients
os.environ
pathlib file-reading APIs
Git helpers
AIOS Bridge runtime
model/provider clients
```

It may use pure Python standard-library validation/sorting/regex plus existing H0/H1 immutable contracts and fingerprint helpers.

## Mandatory Tests

Add `tests/aios_engineering/harness/test_ranking.py` with focused tests proving at minimum:

```text
VALID_SPEC: PASS
NON_TUPLE_SPEC_INPUT: REJECT
EMPTY_RELEVANCE_SPEC: REJECT
DUPLICATE_SIGNALS: REJECT
QUERY_TERM_BOUNDS: REJECT_WHEN_EXCEEDED
MAX_SELECTED_0_33_BOOL: REJECT

EXACT_PATH_SCORE: 600 contribution
PREFIX_SCORE: 300 contribution
TERM_SCORE: 30 each / 180 cap
PREFERRED_KIND_SCORE: 100 contribution
SCORE_CLAMP: 1000 maximum

ZERO_RELEVANCE_SELECTED: NO
MAX_SELECTED_ENFORCED: YES
TIE_BREAK_PATH_THEN_BLOB: DETERMINISTIC
ALL_H1_CANDIDATES_ACCOUNTED_EXACTLY_ONCE: YES
H1_INPUT_MUTATED: NO

HARNESS_INTELLIGENCE_PLAN_REUSED: YES
PLAN_SELECTED_ORDER_SCORE_DESCENDING: YES
PLAN_FINGERPRINT_RANK_SENSITIVE: YES
SPEC_FINGERPRINT_DETERMINISTIC: YES
RANKING_FINGERPRINT_DETERMINISTIC: YES
DISCOVERY_FINGERPRINT_CHANGE_CHANGES_RANKING_BINDING: YES
SPEC_CHANGE_CHANGES_RANKING_BINDING: YES

RECEIPT_COUNTS_EXACT: YES
AUTHORITY_CREATED: NO
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
GIT_SUBPROCESS_USED: NO
WORKTREE_BYTES_READ: NO
```

Tests must use synthetic immutable H1 discovery results. Do not create a remote, make a network call, invoke a provider, or launch a real executor.

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_contracts.py tests/aios_engineering/harness/test_discovery.py tests/aios_engineering/harness/test_ranking.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Use the canonical Bridge E4 publisher only. Implementation-specific invariants are proven through source/tests and ChatGPT review; do not expand or override RESULT publisher schema.

## Acceptance Boundary

TASK-072 passes only if H2 is deterministic, exact-snapshot-bound through H1, task-aware through bounded explicit metadata hints, fully candidate-accounting, resource-bounded, H0-plan-reusing, and zero-authority/zero-network/zero-LLM.

H2 completion does not authorize H3 implementation. H3 requires a separate architecture/task cycle.
