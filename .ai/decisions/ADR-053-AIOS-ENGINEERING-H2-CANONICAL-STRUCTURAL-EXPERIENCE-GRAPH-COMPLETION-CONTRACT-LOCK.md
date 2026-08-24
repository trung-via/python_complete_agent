# ADR-053 — AIOS Engineering H2 Canonical Structural + Experience Graph Completion Contract Lock

STATUS: ACCEPTED
DATE: 2026-08-24
SCOPE: AIOS Engineering H-Series / canonical H2
HUMAN_APPROVED: YES
CANONICAL_ROADMAP: .ai/roadmaps/H-SERIES-v1.0.md
CANONICAL_ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
CANONICAL_ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
CURRENT_MAIN_SHA: a2fe1e7273503d6dc1863ae00ac3c026192bb2a2
H0_STATUS: FORMALLY_COMPLETE
H1_STATUS: FORMALLY_COMPLETE
H2_STATUS: OPEN_PARTIAL
H3_NEW_WORK_AUTHORIZED: NO
H4_H8_AUTHORIZED: NO

## 1. Decision

Canonical H2 will be completed by composing already reviewed supporting evidence with one bounded deterministic **Structural + Experience Graph** capability.

The implementation must consume, not redefine:

```text
H1 repository discovery
H1 dual-provenance experience manifest
H2 deterministic ranking/selection
historical H3-labeled role/symbol summaries as supporting H2.R1 evidence
H2 static import graph from TASK-079
```

TASK-079 established a valid static-import slice but did not complete H2. The remaining work is:

```text
H2.R1 — complete file → symbol → structural component representation
H2.R2 — component/invariant/task/review-finding/executor experience relationships where evidence exists
H2.R3 — one combined provenance-bound deterministic graph identity over the complete H2 graph surface
```

H2.R4 remains satisfied only as a supporting ranking boundary; ranking must not be renamed or treated as the graph itself.

## 2. Structural Component Semantics

H2 components are **structural identities**, not semantic ownership claims.

For Python source evidence, component identity is determined only from exact repository structure:

```text
selected Python file
    ↓
nearest/deepest enclosing Python package directory evidenced by __init__.py
    ↓
PYTHON_PACKAGE component
```

If no enclosing package exists:

```text
selected Python file
    ↓
STANDALONE_PYTHON_MODULE component keyed by exact path
```

A component identifier must be deterministic, bounded, path-derived, and fingerprint-bound.

H2 may state:

```text
FILE CONTAINS SYMBOL
SYMBOL BELONGS_TO COMPONENT
FILE BELONGS_TO COMPONENT
```

H2 may **not** infer:

```text
business/domain ownership
"must own" / "must not own"
responsibility boundaries
executor suitability
```

Those are H3 semantics.

## 3. Symbol Source of Truth

H2 must reuse exact-snapshot top-level Python symbols already produced by `RepositoryRoleSummaryResult`.

Do not add another independent Python symbol parser merely to complete H2.

Before graph creation, exact cross-binding must prove the symbol summaries, ranking result, import graph, repository discovery, and H1 experience manifest all refer to the same repository snapshot and upstream identities required by their contracts.

Historical names such as `H3_ROLE_POLICY_VERSION` may remain in the already-merged supporting implementation. H2 must not relabel those historical APIs or claim H3 completion.

## 4. Experience Graph Entity Contract

The canonical H2 experience graph supports these bounded entity classes:

```text
COMPONENT
INVARIANT
TASK
REVIEW_FINDING
EXECUTOR
```

Additional internal evidence-node types are allowed only when they preserve provenance and do not create H3/H4 semantics.

At minimum, the graph must be capable of representing relations equivalent to:

```text
TASK TOUCHES_COMPONENT
TASK EXECUTED_BY EXECUTOR
TASK HAS_REVIEW_FINDING REVIEW_FINDING
REVIEW_FINDING RELATES_TO_COMPONENT
TASK REFERENCES_INVARIANT INVARIANT
INVARIANT RELATES_TO_COMPONENT
```

Every edge must cite exact evidence identity/fingerprint sufficient to explain why it exists.

## 5. Evidence-Only / No Semantic Guessing Rule

Experience edges are emitted only from exact machine-readable or closed-grammar evidence.

Allowed examples:

```text
TASK id derived from canonical artifact path
EXECUTOR_ALLOWED_PATHS_JSON from canonical TASK
Review Manifest TASK_ID / EXECUTOR_ID from canonical RESULT
closed REVIEW finding headings such as B1/B2 under exact REVIEW artifact
explicit invariant marker/record supported by the H2 parser contract
```

Forbidden:

```text
LLM inference from prose
keyword similarity
free-form ownership inference
assuming an executor from branch name
assuming a component from a finding title
turning roadmap requirements into invariants by analogy
inventing invariant nodes when no invariant evidence exists
```

If exact evidence is absent or ambiguous, H2 must represent absence/unresolved state conservatively rather than invent a relation.

This is the meaning of canonical H2.R2 phrase **"where evidence exists"**.

## 6. Invariant Boundary

H2 is not the H4 Knowledge Registry.

H2 may represent an invariant node only when supplied by exact bounded invariant evidence under a closed grammar. The graph stores identity + provenance relationship only.

H2 must not add:

```text
invariant lifecycle
confidence promotion
Finding → Lesson → Skill → Guard promotion
knowledge precedence engine
knowledge mutation
```

Those remain H4/H8 work.

Legacy prose containing the word "invariant" is insufficient by itself. When no explicit invariant evidence exists, zero invariant nodes is valid and preferable to semantic invention; synthetic/local fixtures must still prove the graph contract can represent invariant relationships when valid evidence exists.

## 7. Control-Plane Experience Parsing

The graph may read bodies only for evidence already enumerated by the exact H1 `RepositoryExperienceManifest`.

For CONTROL_PLANE evidence, exact body reads must be bound to:

```text
control_plane_snapshot
artifact path
artifact blob SHA
artifact kind
```

For REPOSITORY experience evidence, exact body reads remain bound to the repository snapshot and exact blob SHA.

No network fetch fallback is allowed. Missing Git objects fail closed.

Body reads and parser outputs must have hard aggregate/per-artifact bounds.

## 8. Canonical Combined Graph

Introduce one top-level immutable result equivalent to:

```python
RepositoryStructuralExperienceGraphResult
```

It must bind at minimum:

```text
repository snapshot
control-plane snapshot
repository discovery fingerprint
H1 experience manifest fingerprint
H2 ranking/result fingerprint
role-summary result fingerprint
H2 import-graph result fingerprint
structural components
file/symbol/component edges
experience entities/edges
explicit unresolved/omitted accounting
combined graph fingerprint
zero-authority receipt
```

Canonical ordering must be stable and independent of input tuple iteration order where the upstream contract allows reordering.

Tampering with any node, edge, upstream fingerprint, snapshot identity, or exact evidence identity must change/reject the combined fingerprint.

## 9. Structural ↔ Experience Linking

TASK → component relationships must be based only on exact task scope paths that can be deterministically mapped to an H2 structural component.

A REVIEW finding may relate to a component only when closed-grammar review evidence or exact referenced path identity provides that relation. A finding title alone is not enough.

An executor node may be linked to a task only from exact RESULT/review-manifest evidence, not from preferred/recommended executor text in TASK prose.

Ambiguous or unmatched paths must be recorded conservatively and must not create false component edges.

## 10. Bounds

The implementation must define hard limits for at least:

```text
components
symbols
structural edges
experience artifacts parsed
per-artifact body bytes
total experience body bytes
tasks
review findings
executors
invariants
experience edges
unresolved records
fingerprint payload bytes / canonical serialized result size where applicable
```

Bound violations fail closed before returning a complete graph/receipt.

## 11. Zero Authority

The graph is repository intelligence only.

Forbidden:

```text
Bridge task/review/state/lease mutation
executor selection/substitution
retry/failover
merge authority
provider/model calls
network calls
paid API use
knowledge-registry mutation
H3 ownership/tendency inference
```

Receipt must report zero authority and local-only construction.

## 12. Completion Rule

A PASS implementation under this ADR may provide the remaining implementation evidence for H2.R1, H2.R2, and combined H2.R3.

It does **not** itself make H2 COMPLETE.

After independent review PASS, a separate formal H2 milestone-completion record must bind all canonical requirements:

```text
H2.R1 — file → symbol → component structural graph evidence
H2.R2 — bounded evidence-only experience relationship graph evidence
H2.R3 — exact provenance/determinism/bounds/combined graph fingerprint evidence
H2.R4 — TASK-072 ranking/selection supporting-boundary evidence + later H2 review confirmation
```

Only then may H3 canonical progression open.

## 13. Locked Outcome

```text
H2_COMPONENT_SEMANTICS: STRUCTURAL_ONLY
H2_EXPERIENCE_RELATIONSHIPS: EVIDENCE_ONLY
H2_INVARIANT_NODES: EXPLICIT_EVIDENCE_ONLY
H2_COMBINED_GRAPH: REQUIRED
H3_OWNERSHIP_INFERENCE: FORBIDDEN
H3_EXECUTOR_TENDENCIES: FORBIDDEN
H4_KNOWLEDGE_REGISTRY: NOT_STARTED
NETWORK_LLM_PAID_API: NONE
TASK_PASS_IMPLIES_H2_COMPLETE: NO
```