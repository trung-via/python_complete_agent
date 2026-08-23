# AIOS Engineering H-Series Canonical Roadmap v1.0

ROADMAP_ID: AIOS-ENGINEERING-H-SERIES
ROADMAP_VERSION: 1.0
STATUS: LOCKED
AUTHORITY: CANONICAL
HUMAN_APPROVED: YES
DATE_LOCKED: 2026-08-23
NO_IMPLICIT_MILESTONE_CREATION: YES
NO_IMPLICIT_RENUMBERING: YES
NEXT_MILESTONE_AFTER_H8: NONE

## 1. Normative Authority

This file is the canonical milestone identity and scope baseline for AIOS Engineering H-Series.

For roadmap semantics, scoped authority is:

```text
Human explicit direction
    > Canonical locked roadmap
    > Human-approved roadmap change ADR / amendment
    > TASK milestone binding
    > implementation inference / executor hint / conversation memory
```

This scoped roadmap precedence does not replace the H0 execution/control authority boundary. AIOS Bridge remains the authority plane for authorization, lease, dispatch, execution state, review/merge mechanics, and paid-provider authority.

A TASK or ADR may refine implementation inside a canonical capability, but it may not silently redefine, reorder, renumber, extend, or complete the roadmap.

## 2. Canonical H0-H8 Baseline

### H0 — Harness & Learning Boundary Contract

ROLE: Lock H-Series boundary and precedence.

CAPABILITY_ID: H0_BOUNDARY_CONTRACT

REQUIREMENTS:
- H0.R1 — Define what H-Series may read, prepare, organize, learn, and propose.
- H0.R2 — Preserve zero Bridge authority capture: no task/review/lease/dispatch/retry/merge/paid-provider authority.
- H0.R3 — Preserve deterministic provenance and bounded local intelligence foundations.
- H0.R4 — Lock scoped precedence and extension/reopen conditions.

### H1 — Repository + Experience Manifest

ROLE: High-level map of repository and engineering experience.

CAPABILITY_ID: H1_REPOSITORY_EXPERIENCE_MANIFEST

REQUIREMENTS:
- H1.R1 — Inventory repository modules, components, artifacts, and provenance-bearing repository evidence.
- H1.R2 — Inventory TASK/RESULT/review/decision/learning evidence relevant to engineering experience.
- H1.R3 — Bind manifest evidence to exact repository/control-plane provenance without creating authority.

### H2 — Structural + Experience Graph

ROLE: Architecture graph plus engineering-experience graph.

CAPABILITY_ID: H2_STRUCTURAL_EXPERIENCE_GRAPH

REQUIREMENTS:
- H2.R1 — Represent file → symbol → component structural relationships.
- H2.R2 — Represent component/invariant/task/review-finding/executor experience relationships where evidence exists.
- H2.R3 — Preserve exact provenance, deterministic graph identity, boundedness, and conservative unresolved/ambiguous states.
- H2.R4 — Structural ranking/selection may support graph construction but cannot replace the graph capability itself.

### H3 — Role Summaries + Executor Tendencies

ROLE: Role-aware summaries plus evidence-based executor tendency intelligence.

CAPABILITY_ID: H3_ROLE_SUMMARIES_EXECUTOR_TENDENCIES

REQUIREMENTS:
- H3.R1 — Summarize what modules/components own and what they must not own.
- H3.R2 — Produce bounded role-aware repository summaries from exact evidence.
- H3.R3 — Represent evidence-based executor tendencies (for example Antigravity/Codex/Claude strengths, weaknesses, repeated defect patterns) without granting routing authority.
- H3.R4 — Executor tendency evidence remains advisory and provenance-bound; no identity substitution or autonomous dispatch authority.

### H4 — Knowledge Registry

ROLE: Long-lived technical memory.

CAPABILITY_ID: H4_KNOWLEDGE_REGISTRY

REQUIREMENTS:
- H4.R1 — Manage Invariant, Finding, Lesson, and Skill knowledge entities.
- H4.R2 — Every knowledge item carries provenance, confidence/validation state as applicable, and lifecycle state.
- H4.R3 — Preserve precedence boundaries: knowledge cannot override Human/TASK/ADR/invariant authority according to its class.
- H4.R4 — Support deterministic lifecycle operations needed by later retrieval and gardening without silently promoting knowledge.

### H5 — Hybrid Retrieval

ROLE: Retrieve the right repository and experience knowledge for a task.

CAPABILITY_ID: H5_HYBRID_RETRIEVAL

REQUIREMENTS:
- H5.R1 — Prefer exact/graph/provenance retrieval for deterministic matches.
- H5.R2 — Use semantic retrieval only as bounded fallback/augmentation where exact structure is insufficient.
- H5.R3 — Avoid whole-repository prompt stuffing; retrieval must be task-relevant, bounded, and explainable.
- H5.R4 — Bind retrieved knowledge to source provenance and canonical knowledge lifecycle state.

### H6 — Context + Learning Budget Compiler

ROLE: Compile bounded Execution/Learning Packs.

CAPABILITY_ID: H6_CONTEXT_LEARNING_BUDGET_COMPILER

REQUIREMENTS:
- H6.R1 — Compile selected repository evidence, contracts, lessons, and skills into a bounded token/context budget.
- H6.R2 — Preserve authority and provenance while compressing context.
- H6.R3 — Render executor-appropriate views for Antigravity/Codex/Claude without changing executor identity or task authority.
- H6.R4 — Deterministically account for included/excluded context and budget decisions.

### H7 — Task Working Memory + Preflight

ROLE: Active task memory plus executor self-preflight.

CAPABILITY_ID: H7_TASK_WORKING_MEMORY_PREFLIGHT

REQUIREMENTS:
- H7.R1 — Track bounded current-task context, active contracts, skills, lessons, and evidence.
- H7.R2 — Require executor self-preflight before publish against task scope, active knowledge, and critical invariants.
- H7.R3 — Working memory is task-local/advisory and cannot mutate Bridge authority state.
- H7.R4 — Persist only provenance-safe learning evidence needed for later evaluation/promotion.

### H8 — Evaluation + Gardening + Promotion

ROLE: Measure engineering quality and improve the learning system.

CAPABILITY_ID: H8_EVALUATION_GARDENING_PROMOTION

REQUIREMENTS:
- H8.R1 — Measure review rounds, repeated defects, executor quality signals, context efficiency, and learning effectiveness.
- H8.R2 — Detect duplicate/stale/conflicting knowledge and merge, retire, or downgrade it through explicit lifecycle rules.
- H8.R3 — Support controlled promotion path Finding → Lesson → Skill → Guard when evidence thresholds and authority requirements are satisfied.
- H8.R4 — Evaluation/promotion remains auditable, provenance-bound, and incapable of silently acquiring Bridge/Human authority.

## 3. Milestone Progression Invariants

```text
TASK PASS != MILESTONE COMPLETE
```

A milestone is COMPLETE only when every canonical requirement for that milestone has an explicit completion record with evidence and no unresolved blocker.

A later milestone may not be opened merely because the previous TASK number completed. TASK numbering is implementation history, not roadmap progression.

No H9 exists in this roadmap. A new milestone requires Controlled Evolution and a new/amended Human-approved roadmap artifact.

## 4. Controlled Evolution

Roadmap locking prevents accidental evolution, not innovation.

Allowed change classes:

```text
IMPLEMENTATION_REFINEMENT
  - stays inside an existing canonical capability
  - may be implemented immediately under normal TASK authority

CAPABILITY_EXTENSION
  - extends an existing milestone capability or requirement surface
  - requires explicit Human-approved roadmap amendment/change record

ARCHITECTURAL_UPGRADE
  - changes milestone identity/order/dependencies or adds/removes capabilities
  - requires impact analysis, Human approval, ADR, and roadmap version bump
```

Roadmap lifecycle:

```text
DRAFT → LOCKED → SUPERSEDED
```

A locked roadmap is never silently edited into a different architecture. Evolution produces an auditable amendment or a new version.

If an earlier milestone changes after downstream milestones exist, revalidation is limited to the dependency impact cone demonstrated by the roadmap/structural graph. Unaffected milestones do not need to be rebuilt.

## 5. Anti-Drift Invariants

1. A canonical roadmap must exist and be LOCKED before implementation begins.
2. Every implementation TASK must bind to one exact roadmap version and explicit canonical requirement(s).
3. TASK completion cannot imply milestone completion.
4. No agent may redefine, reorder, extend, renumber, or silently reinterpret a locked roadmap.
5. Roadmap changes require explicit Human-approved controlled evolution.
6. Roadmap identity/version/provenance must be fingerprint-bound by the governance implementation.
7. Task authoring/execution must fail closed on roadmap binding mismatch.
8. Review must detect roadmap drift independently of code/test success.
9. Architect/bootstrap context must load the canonical roadmap; conversation memory is not roadmap authority.
10. The mechanism applies to H-Series and is designed for reuse by AIOS Bridge, Python Agent, Product Intelligence, Commerce AI System, and future subsystems.
11. Existing implementation created before this lock must be reconciled against this baseline before H-Series progression resumes.

## 6. Reconciliation Rule for Existing H-Series Work

Existing H0-H4-labeled artifacts remain historical evidence and potentially useful implementation. Their milestone labels do not override this canonical baseline.

Reconciliation classifies each implemented capability as:

```text
CANONICAL_IN_SCOPE
SUPPORTING_CAPABILITY
MISCLASSIFIED_BUT_USEFUL
CONFLICTING
MISSING
```

Misclassified but useful code is preserved and rebound to the correct canonical capability where safe. Rollback is required only for actual contract/authority conflict, not merely for numbering drift.
