# ADR-050 — AIOS Engineering Canonical Roadmap Lock + Controlled Evolution Contract Lock

STATUS: ACCEPTED
DATE: 2026-08-23
SCOPE: AIOS Engineering governance / reusable roadmap authority
HUMAN_APPROVED: YES
CANONICAL_H_SERIES_ROADMAP: .ai/roadmaps/H-SERIES-v1.0.md
CANONICAL_H_SERIES_ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
CURRENT_MAIN_SHA_AT_LOCK: 60f18b3be650725f097305e38c1c36b6b434e62b
TASK_076_REVIEW_HEAD: fea85a8bc7f696c50fd5457b0cea3b5d8032b24f

## 1. Problem Statement

H-Series began with a Human-approved H0→H8 conceptual baseline, but that baseline was not persisted as a canonical versioned roadmap artifact before implementation began.

As a result, later TASK/ADR authoring progressively inferred the next milestone from the most recent implementation state. This produced roadmap drift:

```text
canonical H2 = Structural + Experience Graph
implemented H2 label = Deterministic Task Relevance Ranking + Bounded Selection

canonical H3 = Role Summaries + Executor Tendencies
implemented H3 label = Exact-Snapshot Artifact Role + Python Symbol Intelligence

canonical H4 = Knowledge Registry
implemented H4 label = Exact-Snapshot Static Import Dependency Graph
```

The failure is governance/authority drift, not proof that the useful implementation itself is defective.

The core defect is:

```text
TASK/ADR implementation sequence was allowed to redefine roadmap identity
instead of being bound by a canonical roadmap identity.
```

## 2. Decision

AIOS Engineering adopts **Canonical Roadmap Lock + Controlled Evolution** as a first-class governance contract.

The lock prevents accidental roadmap evolution while preserving explicit, Human-approved mid-series innovation.

For roadmap semantics only, authority is:

```text
Human explicit direction
    > Canonical locked roadmap
    > Human-approved roadmap-change ADR/amendment
    > TASK roadmap binding
    > implementation inference / executor hint / conversation memory
```

This scoped precedence does not alter AIOS Bridge execution authority or the H0 zero-authority boundary.

## 3. Canonical Roadmap Artifact Contract

Before implementation of a governed series/project begins, a canonical roadmap artifact must exist with at least:

```text
ROADMAP_ID
ROADMAP_VERSION
STATUS = DRAFT | LOCKED | SUPERSEDED
AUTHORITY = CANONICAL
explicit milestone identities
explicit capability IDs
explicit requirement IDs
explicit progression rules
controlled-evolution rules
```

No implementation TASK is authorized against a roadmap in DRAFT state.

For current H-Series the normative baseline is:

```text
.ai/roadmaps/H-SERIES-v1.0.md
Git blob SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
```

## 4. Immutable Roadmap Fingerprint Contract

The governance implementation must compute a deterministic SHA-256 fingerprint from the exact normalized roadmap bytes/semantic payload under one locked algorithm version.

Every governed task authored after rollout must bind to:

```text
ROADMAP_ID
ROADMAP_VERSION
ROADMAP_BLOB_SHA
ROADMAP_FINGERPRINT
ROADMAP_FINGERPRINT_ALGORITHM_VERSION
```

If the task-bound roadmap identity does not equal the current locked artifact identity, authoring/execution must fail closed.

A roadmap version must never be silently mutated under the same locked identity. A material architectural change requires an amendment record or a new roadmap version.

## 5. Per-TASK Roadmap Binding Contract

Every governed implementation TASK must declare at minimum:

```text
ROADMAP_ID
ROADMAP_VERSION
ROADMAP_BLOB_SHA
ROADMAP_FINGERPRINT
MILESTONE
CAPABILITY_ID
REQUIREMENT_BINDINGS
SCOPE_IN
SCOPE_OUT
```

A task exists because explicit canonical requirement(s) authorize it. TASK numbering is implementation history only and never determines milestone progression.

A TASK may refine HOW a bounded requirement is implemented. It may not redefine WHAT the roadmap milestone means.

## 6. Roadmap Preflight Gate

Before worker authorization/execution, deterministic roadmap preflight must verify at minimum:

```text
canonical roadmap exists
roadmap status == LOCKED
task roadmap ID/version match
task roadmap blob/fingerprint match
milestone exists
capability ID belongs to milestone
requirement bindings belong to milestone
task scope does not claim a different milestone capability
milestone progression state permits the work
```

Any mismatch is fail-closed:

```text
ROADMAP_BINDING_FAILED
EXECUTION_NOT_AUTHORIZED
```

No executor/model may bypass this gate by reasoning that another milestone would be a logical next step.

## 7. Milestone Completion Contract

The following invariant is locked:

```text
TASK PASS != MILESTONE COMPLETE
```

A milestone completion record must explicitly bind every canonical requirement to reviewed evidence and prove no unresolved requirement/blocker remains.

Only a valid milestone completion record may advance canonical milestone progression.

A TASK, RESULT, executor, or review may not infer milestone completion solely from TASK numbering or local code success.

## 8. Roadmap Authority vs TASK Authority

The responsibilities are separated:

```text
ROADMAP AUTHORITY = WHAT capabilities/requirements must exist and in what canonical milestone identity
TASK AUTHORITY    = HOW one bounded authorized piece is implemented
```

A TASK may:
- refine implementation details;
- split an existing requirement into bounded work;
- add tests/evidence;
- repair implementation defects.

A TASK may not:
- redefine milestone identity;
- move a requirement to another milestone without controlled evolution;
- add/reorder/renumber milestones;
- declare a milestone complete by itself;
- silently change the locked roadmap.

## 9. Controlled Roadmap Evolution Protocol

Innovation remains allowed at any point in a series.

Change classes:

```text
IMPLEMENTATION_REFINEMENT
  -> stays inside existing capability
  -> normal TASK flow; no roadmap unlock required

CAPABILITY_EXTENSION
  -> extends an existing canonical capability/requirement surface
  -> Human-approved roadmap amendment/change record required

ARCHITECTURAL_UPGRADE
  -> changes milestone identity/order/dependency or adds/removes capability
  -> impact analysis + Human approval + ADR + roadmap version bump required
```

Roadmap lifecycle is:

```text
DRAFT → LOCKED → SUPERSEDED
```

A new good idea may be applied immediately after the applicable change protocol completes; there is no requirement to wait until H8 or project completion.

## 10. Impact-Cone Revalidation

If a previously completed milestone changes after downstream implementation exists, AIOS Engineering must compute/reason from an explicit dependency impact cone.

Only affected downstream contracts/tasks require revalidation. Unaffected upstream/downstream work is preserved.

For a linear dependency where no narrower dependency proof exists:

```text
change H4 -> revalidate H4/H5/H6/H7/H8
not H0/H1/H2/H3
```

The goal is controlled evolution without full-series rebuild.

## 11. Roadmap Drift Detection at Review

Code/tests passing is insufficient for review PASS.

Independent review must compare:

```text
declared roadmap binding
TASK scope
canonical capability/requirements
changed public surface / identifiers / docs / diff
```

At minimum, the gate must reject:
- public identifiers/documentation claiming another milestone;
- out-of-scope capability implementation;
- task/ADR text that redefines milestone semantics;
- implicit milestone advancement without completion evidence.

This produces a separate governance conclusion from ordinary functional correctness.

## 12. Architect / Executor Bootstrap Context

Canonical roadmap context must be loaded explicitly into task-authoring and relevant executor/review bootstrap context.

Conversation memory is non-authoritative for roadmap identity. Memory may help locate the canonical artifact but may not replace it.

Task authoring must never reconstruct milestone meaning from chat history when a canonical roadmap exists.

## 13. Cross-Project Applicability

The mechanism is designed as reusable AIOS Engineering governance and may be applied to:

```text
AIOS Bridge
H-Series
Python Agent
Product Intelligence
Commerce AI System
future subsystems/series
```

Each governed series/project owns its own roadmap ID/version and fingerprint; one roadmap must not silently authorize another subsystem.

## 14. Current H-Series Reconciliation Hold

Effective immediately:

```text
H5_IMPLEMENTATION_AUTHORIZED: NO
H_SERIES_ADVANCEMENT: FROZEN_PENDING_RECONCILIATION
TASK_076_AUTO_MERGE_AUTHORIZED: NO
TASK_076_IMPLEMENTATION_BRANCH: PRESERVE
```

TASK-076 has green tests and may contain useful structural-graph implementation, but its current H4 authority binding conflicts with the canonical H4 Knowledge Registry.

The branch must not be deleted or automatically rolled back. It is preserved as implementation evidence pending capability reconciliation/rebinding.

## 15. Historical ADR/TASK Treatment

ADR-045, ADR-048, ADR-049 and their associated TASKs remain historical technical design/implementation evidence.

Where their H-number/capability labels conflict with `.ai/roadmaps/H-SERIES-v1.0.md`, they are **not** authoritative for canonical milestone identity.

Their useful technical behavior may be retained as:

```text
CANONICAL_IN_SCOPE
SUPPORTING_CAPABILITY
MISCLASSIFIED_BUT_USEFUL
```

Only actual authority/contract conflict requires rollback.

## 16. Required Reconciliation

Before H-Series progression resumes, a governance task must:

1. inventory implemented H0→TASK-076 capabilities;
2. map each capability to canonical H0→H8 requirements;
3. identify COMPLETE / PARTIAL / MISSING / MISCLASSIFIED / CONFLICTING items;
4. determine the true current canonical milestone position;
5. produce a safe salvage/rebinding plan for TASK-076;
6. install deterministic roadmap enforcement so the drift cannot recur.

## 17. Locked Governance Invariants

```text
R1  Canonicalize roadmap before implementation.
R2  Bind every governed TASK to one exact roadmap version and explicit requirements.
R3  TASK completion cannot imply milestone completion.
R4  No agent may redefine/reorder/extend/renumber a locked roadmap.
R5  Roadmap changes require explicit Human-approved controlled evolution.
R6  Roadmap identity is immutable/fingerprint-bound.
R7  Roadmap preflight fails closed before execution on mismatch.
R8  Review independently detects roadmap drift even when tests pass.
R9  Architect/bootstrap loads canonical roadmap; conversation memory is not authority.
R10 Governance is reusable across AIOS subsystems/projects.
R11 Existing pre-lock implementation must be reconciled before progression resumes.
```

## 18. Acceptance Boundary

This ADR changes roadmap governance authority only. It does not grant:

```text
worker execution authority
executor reroute authority
retry authority
merge authority outside ADR-042 review boundary
paid API authority
H5 implementation authority
```

No further H-Series milestone implementation may be authored as canonical progression until the reconciliation/enforcement task passes review.
