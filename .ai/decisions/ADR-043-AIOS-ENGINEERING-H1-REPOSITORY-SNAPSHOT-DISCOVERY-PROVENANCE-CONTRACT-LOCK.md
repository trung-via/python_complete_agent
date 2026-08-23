# ADR-043 — AIOS Engineering H1 Repository Snapshot Discovery & Provenance Contract Lock

STATUS: LOCKED
DATE: 2026-08-23
SCOPE: AIOS Engineering H-Series H1
BASELINE_MAIN_SHA: bc64de848c6ef151b4d41a31cdb9df1ebb3bb775
H0_STATUS: COMPLETE
TASK_069_LEAN_AUTO_MERGE: COMPLETE
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
H1_AUTHORIZED: YES

## 1. Decision

H1 implements the first real repository-intelligence capability above the H0 foundation: deterministic discovery of provenance-bearing repository evidence from one exact local Git snapshot.

H1 is a discovery/provenance layer only. It does not rank evidence, choose model context, compile skills, dispatch workers, mutate Bridge state, merge branches, or invoke any model/provider.

Locked flow:

```text
exact repository commit SHA
        ↓
resolve exact commit + tree
        ↓
bounded local Git tree enumeration
        ↓
validate canonical repository paths / Git object metadata
        ↓
deterministic evidence-kind classification
        ↓
RepositoryEvidenceRef candidates + deterministic exclusions
        ↓
RepositoryDiscoveryResult + zero-authority HarnessReceipt
```

H1 sits upstream of later ranking/context milestones:

```text
H1 discovery/provenance
        ↓
H2+ relevance/ranking/compression
        ↓
bounded harness intelligence artifact
        ↓
existing Bridge context packaging
        ↓
authorized worker
```

## 2. Authority Boundary — Unchanged

ADR-038 remains authoritative.

H1 MAY:

```text
READ_LOCAL_GIT_METADATA: YES
READ_LOCAL_GIT_OBJECT_IDENTITIES: YES
ENUMERATE_TRACKED_TREE_ENTRIES: YES
HASH_CANONICAL_METADATA: YES
CLASSIFY_EVIDENCE_KIND_DETERMINISTICALLY: YES
EMIT_ADVISORY_DISCOVERY_RESULT: YES
EMIT_ZERO_AUTHORITY_RECEIPT: YES
```

H1 MUST NOT:

```text
TASK_STATE_AUTHORITY: FORBIDDEN
REVIEW_STATE_AUTHORITY: FORBIDDEN
APPROVAL_AUTHORITY: FORBIDDEN
EXECUTOR_SELECTION_AUTHORITY: FORBIDDEN
LEASE_AUTHORITY: FORBIDDEN
DISPATCH_AUTHORITY: FORBIDDEN
RETRY_OR_FAILOVER_AUTHORITY: FORBIDDEN
MERGE_AUTHORITY: FORBIDDEN
BRIDGE_STATE_MUTATION: FORBIDDEN
WORKER_IDENTITY_MUTATION: FORBIDDEN
NETWORK_CALL: FORBIDDEN
LLM_CALL: FORBIDDEN
PAID_API_CALL: FORBIDDEN
PROVIDER_CREDENTIAL_VALUE_READ: FORBIDDEN
```

No H1 result can authorize execution or merge.

## 3. Exact Snapshot Binding

Discovery input MUST use an exact lowercase 40-hex commit SHA. Branch names, tags, `HEAD`, abbreviated SHAs, revision expressions supplied by the caller, and mutable symbolic refs are not accepted as discovery identity.

H1 resolves locally:

```text
repository_commit_sha
repository_tree_sha
```

The result is valid only for that exact snapshot.

Recommended local Git primitives:

```text
git rev-parse --verify <exact_sha>^{commit}
git rev-parse <exact_sha>^{tree}
git ls-tree -r -z --full-tree <exact_sha>
```

Equivalent deterministic local Git plumbing is allowed, but H1 must not fetch, pull, clone, contact a remote, or depend on the current worktree file contents for provenance.

## 4. Git Object Database Is the Provenance Source

H1 discovers evidence from the exact Git tree/object database, not by recursively walking the mutable filesystem worktree.

Consequences:

- untracked files are not evidence;
- ignored files are not evidence;
- locally modified-but-uncommitted bytes are not silently substituted for snapshot bytes;
- a tracked path is bound to the object id stored in the exact tree;
- path order and discovery result are reproducible for the same snapshot and policy version.

H1 does not need to load raw source file bodies. H1 is metadata/provenance discovery, not content summarization.

## 5. Eligible Git Entries

H1 emits `RepositoryEvidenceRef` candidates only for regular tracked blob entries with canonical modes:

```text
100644
100755
```

The evidence `blob_sha` is the exact 40-hex Git blob object id from the resolved snapshot tree.

Entries that are not eligible regular blobs must not be silently promoted. H1 introduces a bounded immutable discovery-exclusion record for deterministic accounting, including at minimum:

```text
path
object_sha
object_type
git_mode
reason_code
```

At minimum the following are exclusions, not evidence candidates:

```text
120000 symlink blob      → NON_REGULAR_GIT_MODE
160000 gitlink/submodule → NON_REGULAR_GIT_MODE
unexpected object type   → UNSUPPORTED_GIT_OBJECT_TYPE
```

Malformed/ambiguous Git metadata or a path that violates H0 path safety must fail closed rather than being silently repaired.

## 6. Repository Evidence Candidate Contract

Each eligible entry becomes an H0 `RepositoryEvidenceRef` with:

```text
path: exact canonical repo-relative POSIX path from Git tree
blob_sha: exact tree-bound blob SHA
evidence_kind: deterministic H1 classifier result
reason_code: DISCOVERED_GIT_BLOB
priority: 0
symbol_locator: null
```

`priority = 0` is deliberate. H1 does not rank relevance.

H1 MUST NOT assign task relevance scores, semantic importance, model preference, executor affinity, or selection authority.

## 7. Deterministic Evidence-Kind Classification

Classification is path-based and deterministic. It is categorization, not ranking.

Locked precedence:

```text
CONTRACT
  > TEST
  > DOCUMENTATION
  > CONFIGURATION
  > SOURCE
  > OTHER
```

Minimum H1 rules:

### CONTRACT
Repository-governance / contract artifacts under recognized contract namespaces such as:

```text
.ai/decisions/
.ai/tasks/
.ai/reviews/
.ai/context/
```

### TEST
Paths under canonical test namespaces such as:

```text
tests/
test/
```

### DOCUMENTATION
Recognized documentation namespaces/files such as:

```text
docs/
README*
CHANGELOG*
*.md
*.rst
```

except when a higher-precedence CONTRACT/TEST rule applies.

### CONFIGURATION
Bounded known configuration/build metadata names and namespaces, including common repository config files. The implementation must use an explicit allowlist/predicate rather than broad semantic guessing.

### SOURCE
Bounded explicit source-code extension allowlist and/or canonical source namespaces such as `src/`, while preserving the higher-precedence rules above.

### OTHER
Tracked regular blobs not matched by the prior deterministic classes.

Classifier rules and allowlists must be constants covered by tests. H1 must not inspect prose meaning to classify a file.

## 8. RepositoryDiscoveryResult

H1 introduces an immutable discovery result with semantic fields at minimum:

```text
schema_version
policy_version
snapshot: RepositorySnapshotRef
evidence: tuple[RepositoryEvidenceRef, ...]
exclusions: tuple[RepositoryDiscoveryExclusion, ...]
candidate_set_fingerprint
discovery_fingerprint
```

Rules:

- `evidence` order is deterministic canonical path order;
- `exclusions` order is deterministic canonical order;
- duplicate paths/identities are rejected;
- candidate-set fingerprint uses existing H0 evidence fingerprint semantics;
- discovery fingerprint binds policy version + exact snapshot + ordered evidence + deterministic exclusions;
- identical snapshot + policy produces identical fingerprints;
- changing the commit/tree/blob inventory changes the discovery fingerprint.

H1 does NOT create `HarnessIntelligencePlan`; ranking/selection semantics remain for later H milestones.

## 9. Bounded Discovery / Resource Safety

Repository discovery must be bounded before model context ever exists.

Implementation must define explicit hard limits for at least:

```text
MAX_DISCOVERY_ENTRIES
MAX_DISCOVERY_STREAM_BYTES
MAX_GIT_TREE_RECORD_BYTES
```

The Git tree stream must be parsed in a bounded manner. Do not use an unbounded whole-repository stdout capture as the only implementation strategy.

If any bound is exceeded:

```text
FAIL_CLOSED: YES
PARTIAL_RESULT_PRESENTED_AS_COMPLETE: NO
AUTO_RETRY: NO
NETWORK_FALLBACK: NO
```

The implementation may use a local subprocess only with `shell=False` and explicit argv.

## 10. Path / Parsing Safety

Use NUL-delimited Git tree output (`-z`) or an equally unambiguous local plumbing format.

H0 path invariants remain authoritative:

```text
ABSOLUTE_PATH: REJECT
BACKSLASH_PATH: REJECT
EMPTY_SEGMENT: REJECT
DOT_SEGMENT: REJECT
PARENT_TRAVERSAL: REJECT
CONTROL_CHARACTERS: REJECT
.git NAMESPACE: REJECT
```

Do not normalize an invalid Git path into an accepted path. Reject/fail closed.

Git output shape, mode, object type, SHA, record length, and record count must be mechanically validated.

## 11. Harness Receipt

H1 should reuse H0 `HarnessReceipt` for auditability.

For H1 discovery:

```text
authority_created: FALSE
network_used: FALSE
llm_used: FALSE
paid_api_used: FALSE
```

`selected_count` in this receipt means entries included in the H1 discovery evidence set only; it does not mean relevance ranking or H2 selection.

Receipt input/output fingerprints must bind the exact snapshot and H1 policy/result deterministically.

## 12. Non-Changes

H1 must not modify:

```text
bridge.py
src/aios_bridge/**
.agents/skills/aios-worker/**
.agents/workflows/aios-worker.md
```

H1 must not change:

```text
MAX_AUTOMATION_CONTEXT_REFS
ContextBuilder
executor selection / lease / dispatch
retry / failover
paid-provider gates
Lean Auto-Merge authority
worker identity surfaces
```

No new dependency is required.

## 13. Test Contract

Tests must prove at minimum:

```text
EXACT_COMMIT_SHA_REQUIRED: YES
SYMBOLIC_REF_ACCEPTED: NO
ABBREVIATED_SHA_ACCEPTED: NO
SNAPSHOT_TREE_BINDING: EXACT
WORKTREE_BYTES_USED_AS_PROVENANCE: NO
UNTRACKED_FILES_DISCOVERED: NO

REGULAR_BLOB_DISCOVERY: PASS
NON_REGULAR_MODE_PROMOTED_TO_EVIDENCE: NO
MALFORMED_GIT_RECORD_FAIL_CLOSED: YES
INVALID_REPOSITORY_PATH_NORMALIZED: NO

EVIDENCE_ORDER_DETERMINISTIC: YES
CLASSIFICATION_PRECEDENCE_DETERMINISTIC: YES
PRIORITY_RANKING_INTRODUCED: NO
CANDIDATE_SET_FINGERPRINT_DETERMINISTIC: YES
DISCOVERY_FINGERPRINT_SNAPSHOT_SENSITIVE: YES

DISCOVERY_ENTRY_BOUND_ENFORCED: YES
DISCOVERY_BYTE_BOUND_ENFORCED: YES
UNBOUNDED_STDOUT_CAPTURE_REQUIRED: NO

NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
AUTHORITY_CREATED: NO
BRIDGE_RUNTIME_CHANGED: NO
```

Unit parsing/classification tests may use synthetic Git records. Integration tests may create a local temporary Git repository and commits; they must not create/use a remote or network connection.

## 14. H-Series Sequence

```text
H0 Foundation ✅
        ↓
H1 Repository Snapshot Discovery & Provenance
        ↓
H2 relevance / ranking contract
        ↓
subsequent H milestones
```

H1 completion does not silently authorize H2 implementation; H2 receives its own contract/task cycle.

## 15. Reopen Conditions

This H1 contract may be reopened only by explicit Human direction and a new architecture decision. Later milestones may consume H1 evidence but must not retroactively give H1 execution, merge, model-call, or authority semantics.
