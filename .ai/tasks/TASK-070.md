# TASK-070 — AIOS Engineering H1 Repository Snapshot Discovery & Provenance

STATUS: READY
CLASS: H1 — AIOS ENGINEERING / REPOSITORY INTELLIGENCE
MILESTONE: H-SERIES H1
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex

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
PRIOR_BOUNDED_EXECUTOR_INVOCATION_OCCURRED: NO
E4_AUTHORING_REPAIR_COMPLETE: YES
```

The Human selected the Codex worker surface for the current RUN attempt. A failed E4 pre-invocation validation does not authorize retry/reroute by itself. No bounded executor invocation occurred during the prior marker-validation failures.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/decisions/ADR-043-AIOS-ENGINEERING-H1-REPOSITORY-SNAPSHOT-DISCOVERY-PROVENANCE-CONTRACT-LOCK.md","blob_sha":"140e1a03593e31f6681016ae45b427f9b16ee8c9"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/discovery.py","src/aios_engineering/harness/errors.py","tests/aios_engineering/harness/test_discovery.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The three marker lines above are the complete E4 machine-readable marker set for this executable RUN task. They create no merge, retry, reroute, network, provider, or paid-API authority.

## Objective

Implement ADR-043 exactly: deterministic, bounded, local-only repository snapshot discovery that converts one exact Git commit/tree into provenance-bearing H0 `RepositoryEvidenceRef` candidates, deterministic non-regular-entry exclusions, a deterministic discovery result, and a zero-authority `HarnessReceipt`.

H1 is discovery/provenance only. Do not introduce relevance ranking, context selection, skill compilation, Bridge integration, executor authority, model calls, network access, retry/failover, or merge authority.

## Writable Scope

Executor may modify/create only:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/discovery.py
src/aios_engineering/harness/errors.py
tests/aios_engineering/harness/test_discovery.py
```

Bridge-generated publication may create/update `.ai/results/RESULT-070.md`; that path is not executor writable scope.

Explicitly forbidden:

```text
bridge.py
src/aios_bridge/**
src/aios_engineering/harness/contracts.py
src/aios_engineering/harness/fingerprint.py
.agents/**
.ai/decisions/**
.ai/reviews/**
.ai/tasks/**
requirements.txt
```

No dependency changes.

## Required H1 Surface

Implement a stable policy identity such as:

```text
H1_DISCOVERY_POLICY_VERSION = "h1-v1"
```

Add frozen immutable `RepositoryDiscoveryExclusion` with at least:

```text
path
object_sha
git_mode
object_type
reason_code
```

Add frozen immutable `RepositoryDiscoveryResult` with at least:

```text
schema_version
policy_version
snapshot: RepositorySnapshotRef
evidence: exact tuple[RepositoryEvidenceRef, ...]
exclusions: exact tuple[RepositoryDiscoveryExclusion, ...]
candidate_set_fingerprint
discovery_fingerprint
```

Provide an execution surface equivalent to:

```python
discover_repository_snapshot(
    repository_root,
    repository_commit_sha,
    *,
    task_id,
) -> tuple[RepositoryDiscoveryResult, HarnessReceipt]
```

Input commit identity must be exact lowercase 40-hex. Reject `HEAD`, symbolic refs, tags, revision expressions, abbreviated SHA, uppercase SHA, malformed SHA.

## Exact Provenance / Git Rules

Use the local Git object database, not recursive worktree scanning. Required semantics:

```text
exact commit exists locally
exact commit is a commit object
exact tree SHA resolved
tracked tree enumerated from exact commit
untracked files excluded by construction
dirty worktree bytes never substitute tree-bound blob identities
```

Use explicit argv, `shell=False`, and local Git only. No fetch/pull/clone/remote access.

Eligible evidence entries:

```text
100644 + blob
100755 + blob
```

Each eligible entry becomes:

```text
RepositoryEvidenceRef(
  path=<canonical repo-relative Git tree path>,
  blob_sha=<exact tree blob SHA>,
  evidence_kind=<deterministic classifier>,
  reason_code="DISCOVERED_GIT_BLOB",
  priority=0,
  symbol_locator=None,
)
```

Non-regular entries must not become evidence. At minimum:

```text
120000 -> NON_REGULAR_GIT_MODE
160000 -> NON_REGULAR_GIT_MODE
unexpected object type -> UNSUPPORTED_GIT_OBJECT_TYPE
```

Malformed regular-entry metadata or invalid path must fail closed, not be normalized or hidden as an exclusion.

## Deterministic Classifier

Precedence:

```text
CONTRACT > TEST > DOCUMENTATION > CONFIGURATION > SOURCE > OTHER
```

Minimum required cases:

```text
.ai/decisions/ADR-X.md -> CONTRACT
tests/test_x.py -> TEST
docs/guide.md -> DOCUMENTATION
README.md -> DOCUMENTATION
pyproject.toml -> CONFIGURATION
requirements.txt -> CONFIGURATION
src/pkg/module.py -> SOURCE
scripts/tool.ps1 -> SOURCE
assets/sample.bin -> OTHER
```

Classification is path-only; do not inspect file prose/content.

## Bounded Discovery

Define finite hard constants for at least:

```text
MAX_DISCOVERY_ENTRIES
MAX_DISCOVERY_STREAM_BYTES
MAX_GIT_TREE_RECORD_BYTES
```

Enumerate with NUL-delimited Git output or equivalent unambiguous framing. Bounds must be enforced while reading/parsing; do not capture an unbounded whole-repository stdout and check only afterward.

Any bound breach:

```text
FAIL_CLOSED: YES
PARTIAL_RESULT_RETURNED: NO
RETRY: NO
REROUTE: NO
NETWORK_FALLBACK: NO
```

## Fingerprints / Receipt

Reuse H0 canonical serialization and fingerprint helpers without modifying `contracts.py` or `fingerprint.py`.

Candidate-set fingerprint uses the emitted evidence set. Discovery fingerprint binds policy version + exact snapshot + canonically ordered evidence + deterministic exclusions + candidate-set fingerprint.

Receipt input fingerprint binds task id + exact snapshot request + policy. Receipt output fingerprint binds final discovery fingerprint.

Receipt invariants:

```text
authority_created: FALSE
network_used: FALSE
llm_used: FALSE
paid_api_used: FALSE
candidate_count == selected_count + excluded_count
```

For H1, `selected_count` means emitted evidence count only; no relevance ranking exists.

## Mandatory Tests

Tests must prove at minimum:

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

Temporary Git integration tests must remain local-only and must not add a remote.

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

## RESULT Evidence

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

Do not include raw repository source bodies, credentials, provider data, or secret material in RESULT.

## Acceptance Boundary

TASK-070 passes only if H1 produces a deterministic bounded evidence inventory from an exact local Git snapshot while preserving ADR-038/ADR-043 authority boundaries and making zero Bridge/runtime/worker changes.

H2 is not started or authorized by this task.
