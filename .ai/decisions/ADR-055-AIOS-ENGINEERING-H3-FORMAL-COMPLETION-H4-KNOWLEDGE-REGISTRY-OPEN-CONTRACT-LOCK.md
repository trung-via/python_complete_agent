# ADR-055 — AIOS Engineering H3 Formal Completion + H4 Knowledge Registry Open Contract Lock

STATUS: ACCEPTED
DATE: 2026-08-24
SCOPE: AIOS Engineering H-Series / H3→H4 canonical progression
HUMAN_APPROVED: YES
CANONICAL_ROADMAP: .ai/roadmaps/H-SERIES-v1.0.md
CANONICAL_ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
CANONICAL_ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
COMPLETION_ARTIFACT: .ai/roadmaps/H-SERIES-v1.0.completions.json
COMPLETION_ARTIFACT_BLOB_SHA: 43659eb156dcd17845572e4d224dcbca7a114ad6
H3_COMPLETION_RECORD_FINGERPRINT: 4c2fe5cf07b9dcfc636c1fad80d80d6910dbe7b3d9547dc1d89dd4fb40b85df7
CURRENT_MAIN_SHA: 8f887f828ad765f74073636f7e5ff887603fb56b
H0_STATUS: FORMALLY_COMPLETE
H1_STATUS: FORMALLY_COMPLETE
H2_STATUS: FORMALLY_COMPLETE
H3_STATUS: FORMALLY_COMPLETE
H4_STATUS: OPEN_MISSING
H5_H8_AUTHORIZED: NO

## 1. Decision

Canonical H3 is formally complete because the canonical completion artifact contains one validated H3 record covering exactly H3.R1-H3.R4 with no unresolved requirement or blocker.

Canonical H4 is therefore opened under the unchanged locked roadmap v1.0:

```text
H4 — Knowledge Registry
CAPABILITY_ID: H4_KNOWLEDGE_REGISTRY
```

This is normal roadmap progression, not a roadmap amendment or version change.

## 2. H4 Canonical Scope

H4 is a long-lived technical-memory registry for exactly four canonical knowledge kinds:

```text
INVARIANT
FINDING
LESSON
SKILL
```

H4 must manage durable/persistable registry state and deterministic lifecycle operations over explicitly supplied evidence. It does not discover new truth, infer lessons, promote knowledge kinds, route executors, or acquire Bridge/Human authority.

## 3. Registry State Model

The canonical H4 result should be an immutable, deterministically serializable registry state equivalent in capability to:

```text
KnowledgeRegistryState
  schema/policy identity
  source repository/control provenance identity where supplied
  ordered KnowledgeItem records
  ordered lifecycle/audit events or equivalent deterministic operation evidence
  registry fingerprint
  zero-authority receipt
```

The registry must be persistable through deterministic bytes/JSON owned by the caller. H4 itself should remain pure with respect to filesystem/Git/network side effects.

A later layer may store the bytes. The H4 contract is responsible for validating and fingerprinting the registry state, not for owning storage authority.

## 4. Knowledge Item Identity

Every item must have one stable deterministic `knowledge_id` and exactly one `KnowledgeKind`.

Identity must not be inferred from free-text similarity. Duplicate IDs fail closed unless an explicit lifecycle operation references the exact current item fingerprint and contractually replaces permitted metadata.

Changing `KnowledgeKind` is not an H4 lifecycle update. It is a promotion/reclassification concern reserved for H8 or explicit Human-governed controlled evolution.

## 5. Provenance Contract

Every knowledge item must carry exact provenance sufficient to identify why the item exists.

At minimum provenance should bind bounded records equivalent to:

```text
source artifact path
source artifact blob SHA
source artifact/evidence kind
source evidence fingerprint or exact graph/result fingerprint where applicable
optional exact repository/control snapshot identity when available
```

H4 may consume exact H2/H3 identities/fingerprints as provenance inputs but must not reparse repository structure or executor history.

No knowledge item may be created from path-name guessing, keyword similarity, LLM judgment, branch-name inference, recommended executor text, or unbound prose.

## 6. Validation / Confidence State

Validation/confidence is explicit metadata, not inferred quality scoring.

Use a closed enum contract equivalent to:

```text
UNVALIDATED
EVIDENCE_BACKED
HUMAN_APPROVED
```

An implementation may refine names without changing semantics.

Transitions must be explicit operations with exact prior-state/fingerprint preconditions and new provenance/evidence where required.

H4 must not automatically upgrade validation state because an item has many references, because a test passed, or because an executor/model produced it.

## 7. Lifecycle State

Lifecycle is orthogonal to validation/confidence.

Use a closed lifecycle contract equivalent to:

```text
PROPOSED
ACTIVE
RETIRED
```

No physical deletion is required for normal lifecycle; retirement preserves auditability.

An item cannot silently transition lifecycle state. Every transition must be explicit, deterministic, fingerprint-bound, and represented in the resulting state/audit evidence.

## 8. Canonical H4 Operations

H4 may implement pure deterministic operations equivalent to:

```text
REGISTER
SET_VALIDATION_STATE
SET_LIFECYCLE_STATE
AMEND_METADATA
```

Each operation must:

```text
name exact target knowledge_id
bind expected prior registry/item fingerprint where applicable
validate allowed transition
produce a new immutable registry state
produce deterministic before/after fingerprints
preserve provenance/audit evidence
```

Forbidden H4 operations:

```text
PROMOTE_KIND
FINDING_TO_LESSON
LESSON_TO_SKILL
SKILL_TO_GUARD
AUTO_MERGE_KNOWLEDGE
AUTO_RETIRE_BY_HEURISTIC
AUTO_CONFIDENCE_SCORE
```

Finding → Lesson → Skill → Guard promotion belongs to H8.

## 9. Invariant Boundary

`KnowledgeKind.INVARIANT` represents an invariant knowledge record; it does not itself create invariant authority.

If an invariant item claims Human/ADR-backed authority, its provenance must explicitly bind that authority source. H4 may preserve the reference and precedence metadata, but H4 cannot manufacture or upgrade Human/TASK/ADR/invariant authority.

A non-authoritative finding/lesson/skill can never override:

```text
Human explicit direction
TASK authority
ADR authority
canonical invariant authority
Bridge control authority
```

## 10. Precedence / Authority Contract

Every H4 item must carry a closed precedence/authority class consistent with its kind and provenance.

At minimum the registry must make it impossible for advisory `Finding`, `Lesson`, or `Skill` items to be serialized or interpreted as Bridge/Human/TASK/ADR authority.

Required global zero-authority facts remain:

```text
authority_created = False
network_used = False
llm_used = False
paid_api_used = False
```

H4 has no task/review/lease/dispatch/retry/reroute/merge/provider authority.

## 11. Determinism and Bounds

H4 must use stable ordering, immutable records, canonical serialization, and deterministic fingerprints.

Hard limits must exist for at least:

```text
knowledge items per registry
provenance refs per item
metadata keys/value bytes
knowledge ID/title/summary/body lengths as applicable
lifecycle/audit events
serialized registry bytes
fingerprint payload bytes
```

Boolean values must not silently satisfy integer fields. Duplicate identities and unsupported enum/state transitions fail closed.

## 12. Parse / Serialize Contract

H4 should expose deterministic round-trip support equivalent to:

```text
serialize_registry(state) -> canonical bytes
parse_registry(bytes) -> validated immutable state
```

Parsing must revalidate every item, enum, provenance ref, lifecycle record, bound, canonical identity, and registry fingerprint before returning a valid state.

Malformed, oversized, duplicate, tampered, or non-canonical input fails closed.

No filesystem/Git/network access is required inside this contract.

## 13. H2 / H3 Composition Boundary

H4 may register items that cite H2/H3 evidence, for example:

```text
review finding provenance
structural component identity
executor tendency profile fingerprint
explicit invariant evidence
```

But H4 must not:

```text
rebuild H2 graph
recompute H3 executor tendencies
infer executor quality
choose an executor
perform H5 retrieval
compile H6 context packs
perform H7 working-memory/preflight
perform H8 evaluation/gardening/promotion
```

## 14. Completion Rule

A PASS implementation under this ADR may provide canonical H4.R1-H4.R4 implementation evidence.

It does not itself make H4 COMPLETE.

After independent PASS review, a separate formal H4 milestone-completion record must bind all canonical requirements exactly. Only then may H5 Hybrid Retrieval open.

## 15. Locked Outcome

```text
H3: FORMALLY_COMPLETE
H4: OPEN_MISSING
H4_KINDS: INVARIANT/FINDING/LESSON/SKILL
H4_REGISTRY: IMMUTABLE_PERSISTABLE_DETERMINISTIC
H4_VALIDATION: EXPLICIT_ONLY
H4_LIFECYCLE: EXPLICIT_ONLY
H4_KIND_PROMOTION: FORBIDDEN
H4_AUTO_GARDENING: FORBIDDEN
H4_ROUTING_AUTHORITY: NONE
H4_BRIDGE_AUTHORITY: NONE
H5_H8: NOT_AUTHORIZED
TASK_PASS_IMPLIES_H4_COMPLETE: NO
NETWORK_LLM_PAID_API: NONE
```
