# ADR-051 — AIOS Engineering H0 Formal Completion + Canonical H1 Recovery Contract Lock

STATUS: ACCEPTED
DATE: 2026-08-24
SCOPE: AIOS Engineering H-Series canonical progression recovery
HUMAN_APPROVED: YES
BASE_MAIN_SHA: 8fe5724d5121e53313bfefabedd26df6e1e307c1
CANONICAL_ROADMAP: .ai/roadmaps/H-SERIES-v1.0.md
CANONICAL_ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
CANONICAL_ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
GOVERNANCE_ADR: ADR-050
RECONCILIATION_REPORT: docs/AIOS_H_SERIES_RECONCILIATION_V1.md

## 1. Decision

The accepted TASK-077 reconciliation establishes the true canonical H-Series position as:

```text
H0: COMPLETE capability coverage; formal completion record still required
H1: PARTIAL
H2: PARTIAL
H3: PARTIAL
H4-H8: MISSING
```

This ADR performs no H-Series implementation work. It authorizes two governance actions only:

1. mint the first ADR-050-format formal completion record for canonical H0 from already reviewed evidence; and
2. lock the recovery scope for the next H1 task to the exact missing canonical H1 requirements.

No historical H-number declaration is treated as canonical authority. The locked roadmap remains the authority source.

## 2. H0 Formal Completion Decision

Canonical H0 capability:

```text
H0 — Harness & Learning Boundary Contract
CAPABILITY_ID: H0_BOUNDARY_CONTRACT
REQUIREMENTS: H0.R1, H0.R2, H0.R3, H0.R4
```

The following already-reviewed evidence is sufficient to create a formal H0 completion record:

```text
ADR-038
  blob: be56f92eef5dcffdc37cebafea280399730b151f

TASK-066
  blob: 3c751899554906f04560afb6f70b83a06ee4873e

REVIEW-066
  blob: 3d1377050cbb28591fcdfbdf11580783a9bf61bc
  reviewed/merged head: 75866e0e033364fbcc308904e9b8e7572e8d2f48
  H0 implementation: PASS
  blockers remaining: 0
```

Requirement evidence mapping is locked as:

```text
H0.R1
  ADR-038 + TASK-066 + REVIEW-066 establish the allowed read/prepare/organize/propose boundary and bounded Harness foundation.

H0.R2
  REVIEW-066 proves zero Bridge authority capture: Bridge runtime/state/dispatch/worker identity remain unchanged.

H0.R3
  REVIEW-066 proves exact repository snapshot/blob provenance, deterministic canonical serialization/fingerprints, finite bounds, ambiguity rejection, and no network/LLM/paid API use.

H0.R4
  ADR-038 + REVIEW-066 establish scoped precedence, namespace separation, extension points, and explicit reopen/authority boundaries.
```

There are no unresolved H0 canonical requirements or blockers.

The formal completion record must be persisted at the canonical governance path derived by TASK-077:

```text
.ai/roadmaps/H-SERIES-v1.0.completions.json
```

It must bind exactly to roadmap v1.0 blob/fingerprint and pass the machine validator introduced by TASK-077.

## 3. H1 Canonical Recovery Scope

Canonical H1 is:

```text
H1 — Repository + Experience Manifest
CAPABILITY_ID: H1_REPOSITORY_EXPERIENCE_MANIFEST
```

Canonical requirements:

```text
H1.R1 — Inventory repository modules, components, artifacts, and provenance-bearing repository evidence.
H1.R2 — Inventory TASK/RESULT/review/decision/learning evidence relevant to engineering experience.
H1.R3 — Bind manifest evidence to exact repository/control-plane provenance without creating authority.
```

The accepted reconciliation classifies H1 as PARTIAL:

```text
H1.R1: substantial / present in existing repository discovery
H1.R2: incomplete
H1.R3: partial
```

Therefore the next H1 task MUST preserve and reuse existing repository discovery. It is not authorized to rewrite H1.R1 from scratch.

The recovery task is limited to:

```text
1. freeze an exact repository snapshot identity;
2. freeze a separate exact ai-control commit/tree identity;
3. inventory bounded engineering-experience evidence from ai-control, including at minimum:
   - .ai/tasks/**
   - .ai/results/** where present on the selected control/repository evidence surfaces
   - .ai/reviews/**
   - .ai/decisions/**
   - explicit learning/knowledge artifacts where they already exist;
4. classify provenance-bearing experience artifacts deterministically;
5. bind repository-manifest provenance and control-plane-manifest provenance into one immutable H1 result/receipt;
6. preserve zero authority: no task/review/lease/dispatch/merge/provider authority.
```

## 4. Dual-Provenance Invariant

H1 completion must no longer rely on the false assumption that one Git snapshot contains both product/repository code and all canonical control artifacts.

The required model is:

```text
Repository snapshot
  exact main/repository commit + tree

Control-plane snapshot
  exact ai-control commit + tree

             ↓
H1 dual-provenance manifest
             ↓
repository evidence + engineering experience evidence
```

The two snapshot identities must remain explicit and independently fingerprinted. No path may be silently read from the worktree or from an unfrozen moving ref.

## 5. Experience Manifest Boundary

The H1 experience manifest is evidence inventory only.

It MAY:

```text
read exact local Git objects
classify TASK/RESULT/REVIEW/ADR/learning artifacts
record blob/path/type provenance
compute deterministic fingerprints
record bounded exclusions/unsupported artifact classes
```

It MUST NOT:

```text
infer Finding/Lesson/Skill entities              # H4 territory
infer executor tendencies                         # H3 territory
build semantic retrieval                          # H5 territory
compile context budgets                           # H6 territory
create task working memory                        # H7 territory
promote/garden learned knowledge                  # H8 territory
mutate Bridge/control-plane state
create authorization
select/reroute/retry executors
merge branches
call network/LLM/paid providers
```

## 6. TASK-076 Boundary

TASK-076 remains preserved and unmerged.

H1 recovery must not modify, rebase, merge, rename, or salvage TASK-076. Its useful static import graph remains future H2 rebinding work after canonical H1 completion.

## 7. Completion Boundary for H1

The next H1 implementation task may claim H1 completion only if independent review proves all three canonical requirements:

```text
H1.R1: existing repository manifest remains valid and bound to exact repository provenance
H1.R2: bounded engineering-experience manifest exists over exact control-plane evidence
H1.R3: combined result binds repository + control-plane provenance deterministically with zero authority
```

A PASS task review alone still does not create H1 milestone completion. After review, a separate formal milestone completion record must be minted under ADR-050 governance before H2 can canonically reopen.

## 8. Locked Outcome

```text
H0_FORMAL_COMPLETION_RECORD: AUTHORIZED
H1_RECOVERY_IMPLEMENTATION: AUTHORIZED AFTER H0 RECORD EXISTS
H2_NEW_CANONICAL_WORK: NOT AUTHORIZED
TASK_076_SALVAGE: NOT AUTHORIZED YET
H3_NEW_CANONICAL_WORK: NOT AUTHORIZED
H4-H8: NOT AUTHORIZED
H5_IMPLEMENTATION_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO
```
