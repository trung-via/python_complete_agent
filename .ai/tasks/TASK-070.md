# TASK-070 — AIOS Engineering H1 Repository Snapshot Discovery & Provenance

STATUS: READY
CLASS: H1 — AIOS ENGINEERING / REPOSITORY INTELLIGENCE
MILESTONE: H-SERIES H1
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity

## Baseline

```text
MAIN_SHA: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
TARGET_BRANCH: ai/task-070
H0_STATUS: COMPLETE
H1_AUTHORIZED: YES
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
LEAN_AUTO_MERGE: ENABLED
ADR: ADR-043
ADR_BLOB_SHA: 140e1a03593e31f6681016ae45b427f9b16ee8c9
NETWORK_CALL_ALLOWED: NO
LLM_CALL_ALLOWED: NO
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
```

## Objective

Implement ADR-043 exactly: add deterministic, bounded, local-only repository snapshot discovery that converts one exact Git commit/tree into provenance-bearing H0 `RepositoryEvidenceRef` candidates plus deterministic non-regular-entry exclusions and a zero-authority audit receipt.

H1 must establish trustworthy repository evidence inventory without introducing ranking, context selection, skill compilation, Bridge integration, executor authority, model calls, or network behavior.

## Locked Architecture

```text
exact lowercase commit SHA
        ↓
local Git commit/tree verification
        ↓
bounded NUL-delimited ls-tree stream
        ↓
strict Git metadata/path validation
        ↓
regular tracked blob candidates
        +
deterministic non-regular exclusions
        ↓
RepositoryDiscoveryResult
        ↓
HarnessReceipt(authority/network/llm/paid_api = FALSE)
```

## Writable Scope

Implementation may modify/create only:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/discovery.py
src/aios_engineering/harness/errors.py
tests/aios_engineering/harness/test_discovery.py
```

Bridge-generated publication may additionally create/update:

```text
.ai/results/RESULT-070.md
```

No other path is writable.

## Explicitly Forbidden

```text
bridge.py
src/aios_bridge/**
src/aios_engineering/harness/contracts.py
src/aios_engineering/harness/fingerprint.py
.agents/skills/aios-worker/**
.agents/workflows/aios-worker.md
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
requirements.txt
```

No dependency changes.

## Required H1 API / Contracts

Implementation names may be minimally adjusted for Python ergonomics, but the semantic surface must include:

### 1. Discovery policy identity

A stable constant/version such as:

```text
H1_DISCOVERY_POLICY_VERSION = "h1-v1"
```

### 2. RepositoryDiscoveryExclusion

Frozen immutable bounded record containing at minimum:

```text
path
object_sha
git_mode
object_type
reason_code
```

It must validate canonical path shape, exact lowercase 40-hex object SHA, bounded machine-readable mode/type/reason fields, and deterministic serialization.

### 3. RepositoryDiscoveryResult

Frozen immutable result containing at minimum:

```text
schema_version
policy_version
snapshot: RepositorySnapshotRef
evidence: exact tuple[RepositoryEvidenceRef, ...]
exclusions: exact tuple[RepositoryDiscoveryExclusion, ...]
candidate_set_fingerprint
discovery_fingerprint
```

Requirements:

- exact tuple boundaries; no silent iterable coercion;
- deterministic path ordering;
- duplicate path/identity ambiguity rejected;
- fingerprints mechanically recomputed/verified;
- evidence candidates are priority 0 and `symbol_locator=None`;
- no field can encode executor/approval/lease/dispatch/merge/provider authority.

### 4. Discovery execution surface

Provide a deterministic local function/class equivalent to:

```python
discover_repository_snapshot(
    repository_root,
    repository_commit_sha,
    *,
    task_id,
) -> tuple[RepositoryDiscoveryResult, HarnessReceipt]
```

The implementation must require an exact lowercase 40-hex commit SHA. It must not accept symbolic refs/HEAD/tags/abbreviations as discovery identity.

## Exact Git Provenance Requirements

Use local Git object metadata, not recursive worktree scanning.

Required semantics:

```text
exact commit exists locally
exact commit resolves as commit object
exact tree SHA resolved
tracked tree enumerated from exact commit
untracked files excluded by construction
worktree dirty bytes do not replace tree-bound blob identities
```

Use explicit argv + `shell=False`.

No command used by H1 may fetch/pull/clone/contact remotes.

## Git Entry Semantics

Eligible evidence candidates:

```text
mode 100644 + type blob
mode 100755 + type blob
```

Each becomes:

```text
RepositoryEvidenceRef(
  path=<tree path>,
  blob_sha=<exact blob sha>,
  evidence_kind=<deterministic classifier>,
  reason_code="DISCOVERED_GIT_BLOB",
  priority=0,
  symbol_locator=None,
)
```

Non-regular entries must not become evidence. Deterministically account for at least:

```text
120000 → NON_REGULAR_GIT_MODE
160000 → NON_REGULAR_GIT_MODE
unexpected object type → UNSUPPORTED_GIT_OBJECT_TYPE
```

Malformed regular entry metadata must fail closed rather than be emitted as an exclusion that hides corruption.

## Evidence-Kind Classifier

Implement explicit deterministic rules with precedence:

```text
CONTRACT > TEST > DOCUMENTATION > CONFIGURATION > SOURCE > OTHER
```

Minimum cases to test:

```text
.ai/decisions/ADR-X.md        → CONTRACT
tests/test_x.py               → TEST
docs/guide.md                 → DOCUMENTATION
README.md                     → DOCUMENTATION
pyproject.toml                → CONFIGURATION
requirements.txt              → CONFIGURATION
src/pkg/module.py             → SOURCE
scripts/tool.ps1              → SOURCE
assets/sample.bin             → OTHER
```

A path matching a higher-precedence rule must not be reclassified by a lower rule.

Do not inspect prose/file contents for classification.

## Bounded Stream Requirements

Define finite hard constants for at least:

```text
MAX_DISCOVERY_ENTRIES
MAX_DISCOVERY_STREAM_BYTES
MAX_GIT_TREE_RECORD_BYTES
```

Tree enumeration must be bounded while reading/parsing. An implementation that obtains the entire unbounded `ls-tree` output via a single unrestricted capture and only checks size afterwards is not acceptable.

On any limit breach:

```text
FAIL_CLOSED: YES
PARTIAL_RESULT_RETURNED: NO
RETRY: NO
REROUTE: NO
NETWORK_FALLBACK: NO
```

Use NUL-delimited records or equivalent unambiguous framing.

## Fingerprints

Use existing H0 canonical serialization/hash helpers without modifying them.

### Candidate set fingerprint

Use H0 `compute_candidate_set_fingerprint` over the emitted H1 evidence set. Same semantic evidence set must produce the same fingerprint independent of incidental traversal mechanics.

### Discovery fingerprint

Bind at minimum:

```text
schema_version
policy_version
snapshot
evidence ordered canonically
exclusions ordered canonically
candidate_set_fingerprint
```

Changing commit/tree/blob inventory or policy version must change the discovery fingerprint.

### Receipt fingerprints

Receipt `input_fingerprint` must bind task id + exact snapshot request/policy. Receipt `output_fingerprint` must bind the final discovery result fingerprint.

Receipt invariants:

```text
authority_created: FALSE
network_used: FALSE
llm_used: FALSE
paid_api_used: FALSE
candidate_count == selected_count + excluded_count
```

For H1 only, `selected_count` means emitted discovery evidence count; it is NOT relevance ranking.

## Mandatory Tests

Tests must include pure parser/classifier tests and local temporary-Git integration tests.

At minimum prove:

```text
EXACT_COMMIT_SHA_REQUIRED: YES
HEAD_ACCEPTED_AS_INPUT: NO
ABBREVIATED_SHA_ACCEPTED: NO
UPPERCASE_SHA_ACCEPTED: NO

SNAPSHOT_TREE_SHA_EXACT: YES
TRACKED_BLOB_SHA_EXACT: YES
UNTRACKED_FILE_DISCOVERED: NO
DIRTY_WORKTREE_BYTES_SUBSTITUTED: NO

REGULAR_100644_DISCOVERED: YES
REGULAR_100755_DISCOVERED: YES
NON_REGULAR_PROMOTED_TO_EVIDENCE: NO
MALFORMED_GIT_RECORD_FAIL_CLOSED: YES
INVALID_PATH_FAIL_CLOSED: YES

CLASSIFIER_PRECEDENCE: PASS
EVIDENCE_ORDER_DETERMINISTIC: YES
PRIORITY_ALWAYS_ZERO: YES
SYMBOL_LOCATOR_ALWAYS_NULL: YES

EXACT_TUPLE_RESULT_CONTRACT: YES
DUPLICATE_AMBIGUITY_REJECTED: YES
CANDIDATE_SET_FINGERPRINT_DETERMINISTIC: YES
DISCOVERY_FINGERPRINT_DETERMINISTIC: YES
DISCOVERY_FINGERPRINT_SNAPSHOT_SENSITIVE: YES

ENTRY_BOUND_FAIL_CLOSED: YES
STREAM_BYTE_BOUND_FAIL_CLOSED: YES
RECORD_BYTE_BOUND_FAIL_CLOSED: YES
UNBOUNDED_WHOLE_STREAM_CAPTURE: NO

NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
AUTHORITY_CREATED: NO
```

Temporary Git tests must remain local-only and must not add a remote.

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_contracts.py tests/aios_engineering/harness/test_discovery.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Pre-task full repository baseline:

```text
2163 passed, 7 skipped, 0 failed
```

## Result Evidence Required

`RESULT-070.md` must report at minimum:

```text
TARGETED_TESTS
FULL_REPOSITORY_TESTS
GIT_DIFF_CHECK

EXACT_SNAPSHOT_BINDING
GIT_OBJECT_PROVENANCE_ONLY
UNTRACKED_DISCOVERED: NO
DIRTY_WORKTREE_SUBSTITUTION: NO
REGULAR_BLOB_DISCOVERY
NON_REGULAR_EVIDENCE_PROMOTION: NO
CLASSIFIER_PRECEDENCE
PRIORITY_RANKING_INTRODUCED: NO
BOUNDED_STREAM_DISCOVERY
CANDIDATE_SET_FINGERPRINT
DISCOVERY_FINGERPRINT
HARNESS_RECEIPT_ZERO_AUTHORITY
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
BRIDGE_CHANGED: NO
SCOPE_EXACT
```

Do not include raw repository source bodies or secret material in RESULT.

## Acceptance Boundary

TASK-070 is PASS only if H1 produces a deterministic bounded evidence inventory from an exact local Git snapshot while preserving every ADR-038 authority boundary and making zero Bridge/runtime/worker changes.

H2 is not started by this task.
