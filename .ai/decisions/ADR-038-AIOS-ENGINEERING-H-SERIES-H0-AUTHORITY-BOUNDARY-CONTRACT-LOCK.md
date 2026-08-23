# ADR-038 — AIOS Engineering H-Series H0 Authority Boundary & Harness Foundation Contract Lock

STATUS: ACCEPTED
DATE: 2026-08-23
SCOPE: AIOS Engineering H-Series H0
BASELINE_MAIN_SHA: bb6e57ca6ba69b1a613430b3903d032c58cfdcd4
M11_STATUS: OPERATIONALLY_PROVEN / CLOSED

## 1. Decision

H-Series is a new AIOS Engineering **repository-intelligence and engineering-experience layer**. It is not an extension of the AIOS Bridge authority plane and must never become a second control plane.

The architectural boundary is locked as:

```text
AIOS Bridge = authority / continuity / authorization / lease / dispatch / execution boundary
H-Series    = repository intelligence / evidence organization / skill intelligence / context preparation
Worker      = authorized implementation execution
Human + ChatGPT review boundary = approval / review / merge authority
```

H-Series may produce deterministic advisory artifacts and bounded repository evidence, but those outputs create **zero execution authority**.

There is no M12 implied by H-Series. TASK-066 begins H-Series H0 after M11 closure.

## 2. Existing-System Compatibility

The existing External Brain `ContextBuilder` remains authoritative for bounded packaging of explicit `ContextItem` candidates. H-Series does not replace it. H-Series sits upstream and improves which repository evidence becomes a candidate.

The existing E4 executor automation contract remains unchanged, including its bounded `.ai/` context-ref surface and allowed-path authorization. H-Series must not broaden `MAX_AUTOMATION_CONTEXT_REFS`, bypass executor context packs, or inject unbound repository data directly into execution.

The existing worker identity contract remains unchanged:

```text
$aios-worker  -> Codex skill          -> executor_id = codex
/aios-worker  -> Antigravity workflow -> executor_id = antigravity
```

H-Series must not infer, substitute, reroute, or merge executor identities.

## 3. Authority Boundary

### H-Series MAY

```text
READ_REPOSITORY: YES
READ_GIT_METADATA: YES
HASH_CONTENT: YES
PARSE_LOCAL_SOURCE: YES
BUILD_REPOSITORY_EVIDENCE: YES
RANK_OR_ORDER_EVIDENCE: YES (future H milestones)
BUILD_REPOSITORY_MAP: YES (future H milestones)
COMPILE_SKILL_INTELLIGENCE: YES (future H milestones)
RENDER_EXECUTOR_SPECIFIC_SKILL_OUTPUT: YES (future H milestones)
PROPOSE_CONTEXT: YES
EMIT_ADVISORY_RECEIPT: YES
```

### H-Series MUST NOT

```text
TASK_STATE_AUTHORITY: FORBIDDEN
REVIEW_STATE_AUTHORITY: FORBIDDEN
APPROVAL_AUTHORITY: FORBIDDEN
EXECUTOR_SELECTION_AUTHORITY: FORBIDDEN
LEASE_AUTHORITY: FORBIDDEN
DISPATCH_AUTHORITY: FORBIDDEN
RETRY_OR_FAILOVER_AUTHORITY: FORBIDDEN
PAID_API_AUTHORITY: FORBIDDEN
PROVIDER_CALL_AUTHORITY: FORBIDDEN
MERGE_AUTHORITY: FORBIDDEN
BRIDGE_STATE_MUTATION: FORBIDDEN
WORKER_IDENTITY_MUTATION: FORBIDDEN
```

No H-Series object, file, receipt, plan, ranking score, skill output, or fingerprint can satisfy or replace a Bridge/Human authorization gate.

## 4. Namespace Boundary

H-Series implementation lives outside `src/aios_bridge/`:

```text
src/
└── aios_engineering/
    └── harness/
```

This namespace separation is intentional. H-Series may consume stable public contracts from elsewhere in the repository in later milestones, but H0 does not change AIOS Bridge runtime code.

H0 is forbidden from modifying:

```text
bridge.py
src/aios_bridge/**
.agents/skills/aios-worker/**
.agents/workflows/aios-worker.md
```

## 5. H0 Foundation Primitive Contracts

H0 establishes immutable, local-only foundation primitives. These primitives contain no network behavior, no model invocation, and no state mutation.

### 5.1 RepositorySnapshotRef

Represents the exact Git repository snapshot against which harness intelligence was produced.

Required semantic fields:

```text
schema_version
repository_commit_sha   # exact lowercase 40-hex
repository_tree_sha     # exact lowercase 40-hex
```

A harness plan generated for snapshot A must not claim validity for snapshot B.

### 5.2 RepositoryEvidenceRef

Represents one provenance-bearing repository evidence reference.

Required semantic fields:

```text
path                   # canonical repository-relative POSIX path
blob_sha               # exact lowercase 40-hex
evidence_kind          # explicit enum
reason_code            # bounded machine-readable reason
priority               # exact bounded integer
symbol_locator         # optional bounded symbol/span locator
```

Path safety is fail-closed:

```text
ABSOLUTE_PATH: REJECT
BACKSLASH_PATH: REJECT
EMPTY_SEGMENT: REJECT
DOT_SEGMENT: REJECT
PARENT_TRAVERSAL: REJECT
CONTROL_CHARACTERS: REJECT
.git NAMESPACE: REJECT
```

Evidence is provenance, not truth-by-inference. Source text may be evidence; H-Series must not silently promote inferred facts into observed facts.

### 5.3 HarnessIntelligencePlan

Represents an advisory intelligence plan bound to a task and exact repository snapshot.

Required semantic fields:

```text
schema_version
task_id
snapshot
selected_evidence      # ranked tuple, order is semantically meaningful
excluded_evidence      # deterministic exclusions / reasons
candidate_set_fingerprint
plan_fingerprint
```

Rules:

- task id is canonical `TASK-<positive digits>`;
- duplicate/ambiguous evidence identities are rejected rather than silently merged;
- the candidate-set fingerprint is order-independent;
- selected-evidence rank order is semantically meaningful, so plan fingerprint changes when selected ranking changes;
- all fingerprints use canonical deterministic serialization;
- no plan field may encode executor approval, lease, dispatch, retry, merge, or paid-provider authority.

### 5.4 HarnessReceipt

Represents a safe local audit receipt for deterministic harness work.

Required semantic fields:

```text
schema_version
task_id
repository_commit_sha
input_fingerprint
output_fingerprint
generator_version
candidate_count
selected_count
excluded_count
authority_created
network_used
llm_used
paid_api_used
```

H0 locks the following exact values:

```text
authority_created: FALSE
network_used: FALSE
llm_used: FALSE
paid_api_used: FALSE
```

Receipt data must contain no secret values, raw credentials, cookies, browser profile stores, or raw provider bodies.

## 6. Deterministic Fingerprinting Contract

H0 uses canonical UTF-8 JSON serialization with deterministic key ordering and separators before SHA-256 hashing.

Two distinct fingerprint semantics are locked:

```text
CANDIDATE_SET_FINGERPRINT:
  order-independent over canonical evidence identities

PLAN_FINGERPRINT:
  order-sensitive for ranked selected evidence
  deterministic for identical semantic input
```

This avoids the incorrect tradeoff between reproducibility and ranking semantics.

## 7. Evidence Identity and Duplicate Ambiguity

An evidence identity is derived from its canonical provenance-bearing fields. H0 must reject duplicates that would make plan provenance ambiguous.

At minimum, exact duplicate evidence references in the same plan are rejected. Conflicting references for the same canonical path/symbol with incompatible blob identity must also fail closed rather than being silently reconciled.

H0 performs contract validation only; full Git object existence/content verification is reserved for later repository-intelligence milestones unless explicitly added under a future locked contract.

## 8. H-Series Extension Points

H0 declares, but does not implement, the following future extension points:

```text
SKILL_COMPILER
SKILL_PRECEDENCE
EXECUTOR_SPECIFIC_RENDERING
```

Their future direction is:

```text
semantic skill sources
        ↓
Skill Compiler
        ↓
Skill Precedence
        ↓
canonical skill plan
        ↓
┌──────────────────┬────────────────────┐
│                  │                    │
Codex rendering    Antigravity rendering
```

Executor-specific rendering must preserve the already-locked worker identity boundary; it must not unify the two operator surfaces into an identity-ambiguous prompt.

## 9. Bounded Integration Strategy

H-Series should reduce repository context before it reaches existing Bridge context packaging.

Preferred future pattern:

```text
many repository candidates
        ↓
H-Series discovery/ranking/compression
        ↓
one or few bounded, provenance-bearing harness intelligence artifacts
        ↓
existing Bridge context refs / ContextBuilder
        ↓
authorized worker
```

H-Series must not solve repository intelligence by simply increasing Bridge context-ref limits or dumping the repository into model context.

## 10. H0 Runtime / Cost Boundary

H0 is local deterministic infrastructure only:

```text
NETWORK_CALL: FORBIDDEN
LLM_CALL: FORBIDDEN
PAID_API_CALL: FORBIDDEN
PROVIDER_CREDENTIAL_VALUE_READ: FORBIDDEN
```

Permitted H0 work is limited to pure/local operations such as validation, canonicalization, hashing, sorting, immutable contract construction, and serialization.

## 11. H0 Acceptance Invariants

H0 implementation is acceptable only if tests prove:

```text
H_SERIES_AUTHORITY_CREATED: NO
BRIDGE_RUNTIME_CHANGED: NO
BRIDGE_STATE_CHANGED: NO
DISPATCH_CHANGED: NO
WORKER_IDENTITY_CHANGED: NO

REPOSITORY_SNAPSHOT_BINDING: EXACT
EVIDENCE_BLOB_BINDING_SHAPE: EXACT
ABSOLUTE_PATH_ACCEPTED: NO
PATH_TRAVERSAL_ACCEPTED: NO
DUPLICATE_EVIDENCE_AMBIGUITY: REJECTED

CANONICAL_SERIALIZATION: YES
CANDIDATE_SET_FINGERPRINT_ORDER_INDEPENDENT: YES
SELECTED_RANK_ORDER_FINGERPRINT_SENSITIVE: YES
DETERMINISTIC_PLAN_FINGERPRINT: YES

NETWORK_REQUIRED: NO
LLM_REQUIRED: NO
PAID_API_REQUIRED: NO

SKILL_COMPILER_EXTENSION_POINT: PRESENT
SKILL_PRECEDENCE_EXTENSION_POINT: PRESENT
EXECUTOR_RENDERING_EXTENSION_POINT: PRESENT
```

## 12. H-Series Sequence Boundary

The approved engineering sequence remains:

```text
M11 CLOSED
   ↓
H0 Foundation / Authority Boundary
   ↓
H1 → H8
   ↓
Final AIOS Completion Audit
   ↓
AIOS Engineering v1.0 / LTS
```

H0 does not authorize implementation of H1-H8. Each later H milestone requires its own explicit task/review/merge cycle.

## 13. Reopen Conditions

This authority boundary may be reopened only by explicit Human direction and a new architecture decision. A later H milestone may extend intelligence capabilities, but it may not silently acquire Bridge authority.
