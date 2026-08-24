# ADR-052 — AIOS Engineering H2 Static Import Graph Rebind / Salvage Contract Lock

STATUS: LOCKED
DATE: 2026-08-24
SCOPE: AIOS Engineering H-Series canonical H2 recovery
HUMAN_APPROVED: YES
ROADMAP_ID: AIOS-ENGINEERING-H-SERIES
ROADMAP_VERSION: 1.0
ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
H1_COMPLETION_ARTIFACT: .ai/roadmaps/H-SERIES-v1.0.completions.json
H1_COMPLETION_ARTIFACT_BLOB_SHA: 864072a7444dd8d0ffdb234f0d03a323d898bf11
H1_COMPLETION_RECORD_FINGERPRINT: 6a93ae900dc9d1702d829cd378414291ffba3eaec572a7eac42118424165d8f1
BASELINE_MAIN_SHA: a51e9c33cd66dc262f13063747295609d7b7df97
PRESERVED_TASK_076_HEAD: fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
H2_AUTHORIZED: YES
H3_NEW_WORK_AUTHORIZED: NO
H4_H8_AUTHORIZED: NO

## 1. Decision

Canonical H1 is formally COMPLETE under the machine-validated completion artifact. Canonical H2 is therefore open.

The first H2 recovery step is to salvage the useful static Python import-dependency implementation preserved on `ai/task-076`, but rebind it to the locked canonical capability:

```text
H2 — Structural + Experience Graph
CAPABILITY_ID: H2_STRUCTURAL_EXPERIENCE_GRAPH
```

This is an **IMPLEMENTATION_REFINEMENT / governance rebinding**, not a roadmap version change. H-Series remains on roadmap v1.0.

## 2. Historical Authority Correction

ADR-049 and TASK-076 remain immutable historical evidence of the implementation that produced the static import graph. Their claim that the graph is canonical H4 is superseded for roadmap authority by the locked roadmap and ADR-050.

Canonical interpretation is:

```text
ADR-049 / TASK-076 H4 milestone label: CONFLICTING / NON-AUTHORITATIVE
TASK-076 static import graph code: MISCLASSIFIED_BUT_USEFUL
Canonical reuse target: H2.R1 + H2.R3, with H2.R4 supporting integration
Canonical H4 Knowledge Registry: NOT STARTED
```

Do not edit history to pretend ADR-049/TASK-076 were originally H2.

## 3. Branch Recovery Strategy

`ai/task-076` is now diverged from `main` and must not be merged, rebased, reset, or force-updated into canonical progression.

Locked strategy:

```text
current main (post TASK-078)
        ↓
new ai/task-079 branch
        ↓
read preserved TASK-076 head by exact Git SHA only
        ↓
port only authorized graph implementation/test surface
        ↓
rename H4-bound public policy identity to H2 static-import-graph identity
        ↓
fresh E4 publication + independent roadmap-aware review
```

The old branch remains preserved as audit evidence.

## 4. H2 Requirement Binding

This salvage step may bind only to:

```text
H2.R1 — partial structural graph: file/import-target relationships
H2.R3 — exact provenance, deterministic graph identity, boundedness, conservative unresolved/ambiguous states
H2.R4 — consume existing deterministic ranking/selection only as supporting graph-construction input; never treat ranking as the graph itself
```

It MUST NOT claim:

```text
H2.R1 COMPLETE
H2.R2 implemented
H2 COMPLETE
H3 executor tendencies
H4 Knowledge Registry
H5-H8 capability
```

H2.R2 (component/invariant/task/review-finding/executor experience relationships) remains entirely open after this salvage step.

## 5. Required Identifier Correction

The recovered implementation must contain no public or policy-bound statement that the static import graph is H4.

At minimum replace/rebind all historical graph-specific identities equivalent to:

```text
H4_GRAPH_POLICY_VERSION / h4-v1
MAX_H4_*
H4-labelled graph docstrings/errors
H4 operation/receipt labels
H4-labelled tests/exports
```

Use an unambiguous H2 supporting-capability identity, for example:

```text
H2_IMPORT_GRAPH_POLICY_VERSION = "h2-import-graph-v1"
MAX_H2_IMPORT_GRAPH_*
```

Neutral domain types may remain when semantically correct:

```text
RepositoryImportDependency
RepositoryDependencyGraphResult
```

## 6. Functional Behavior to Preserve

Preserve the previously reviewed useful behavior where compatible with current main:

- exact H2 ranking / H3 role-summary cross-binding before body reads;
- exact local Git commit/tree/blob provenance;
- selected Python blobs only;
- static AST import extraction without executing repository code;
- deterministic exact internal target resolution;
- conservative unresolved/ambiguous external/internal resolution states;
- deterministic canonical ordering and fingerprints;
- finite hard bounds;
- zero-authority receipt;
- no network, LLM, provider, dispatch, retry, lease, review, or merge authority.

Any incompatibility with current main must be repaired within the authorized H2 graph surface; do not weaken current H1/H2/H3 evidence contracts to make old code fit.

## 7. Current Canonical Progression

```text
H0: FORMALLY COMPLETE
H1: FORMALLY COMPLETE
H2: OPEN / PARTIAL
H3: HISTORICALLY PARTIAL BUT NEW H3 WORK NOT AUTHORIZED UNTIL H2 FORMALLY COMPLETE
H4-H8: NOT STARTED CANONICALLY
```

TASK PASS does not complete H2. A formal H2 completion record remains mandatory after all H2.R1-H2.R4 requirements have reviewed evidence.

## 8. Acceptance Boundary

This ADR authorizes one bounded H2 salvage implementation task only. It creates no authority to merge `ai/task-076`, start H3/H4/H5, change roadmap v1.0, or infer H2 completion.
