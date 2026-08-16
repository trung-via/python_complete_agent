# ADR-017 — AIOS Uniform Assurance Pipeline & Final Independent Audit Policy Lock

STATUS: LOCKED

## Context

ADR-015 established balanced Brain/Executor workload allocation and, from TASK-021 onward, removed a separate Primary-Brain implementation plan by default. It also made Round-1 review delta-first by default.

TASK-022 provided stronger operational evidence that this policy can save a small amount of Brain reasoning early while creating materially more review/fix work later. TASK-022 required multiple Executor FIX cycles and twice reached an `APPROVED` verdict before a human-requested full re-audit discovered new contract-level defects that were outside the known-finding set.

The lesson is not that delta-first review is wrong. Delta-first remains the correct default for FIX rounds. The lesson is that:

1. every engineering task benefits from an explicit Brain-owned implementation-assurance pass before execution;
2. resolving all known findings is not sufficient evidence for final approval;
3. a final independent audit must search for unknown findings against the final implementation state before `APPROVED` is emitted.

This ADR changes assurance-stage policy while preserving all existing execution-authority and Bridge semantics.

---

## Decision 1 — Uniform Assurance Pipeline

All engineering work classes SHALL use the same assurance stages:

```text
Primary Brain — Contract
        ↓
Primary Brain — Architecture Implementation Plan
        ↓
Primary Brain — Adversarial Checklist
        ↓
Human — explicit RUN authorization
        ↓
Active Executor — Detailed Implementation Plan
        ↓
Active Executor — Code + Tests + Self-Audit
        ↓
RESULT / deterministic evidence
        ↓
Primary Brain — Full Semantic Review
        ↓
CHANGES_REQUIRED → Human FIX authorization → Executor FIX → Delta Fix Review
        ↓
Primary Brain — Final Independent Audit
        ↓
APPROVED
        ↓
Human — explicit MERGE authorization
```

L1, L2 and L3 differ only in **depth, context budget, and adversarial coverage**. They do not differ in whether a stage exists.

This is the **Uniform Assurance Pipeline**.

---

## Decision 2 — Work Classes Control Depth, Not Stage Presence

### L1 — MECHANICAL

Architecture Implementation Plan and Adversarial Checklist SHALL be very small and bounded.

Typical plan depth:
- exact mechanical change;
- compatibility surface;
- expected direct call sites;
- deterministic regression evidence.

Typical adversarial coverage:
- stale call site/import;
- old/new serialized name mismatch where relevant;
- backward compatibility;
- obvious scope leakage;
- regression suite.

### L2 — ENGINEERING

Architecture Implementation Plan SHALL cover:
- subsystem boundaries;
- data/control flow;
- invariants;
- compatibility and failure behavior;
- expected modules/interfaces;
- test strategy and likely edge cases.

Adversarial Checklist SHALL include relevant malformed, missing, stale, duplicate, mismatch, boundary and regression cases.

### L3 — ARCHITECTURE / HIGH-RISK

Architecture Implementation Plan SHALL decompose the contract into explicit proof obligations before execution.

Where applicable it SHALL cover:
- identity and canonicalization;
- state/snapshot anchors;
- content-addressing and freshness;
- authority boundaries;
- fail-closed behavior;
- collisions/duplicates/ambiguity;
- cross-component consistency;
- serialization/fingerprinting;
- concurrency/lease/failover semantics;
- migration/backward compatibility;
- negative/adversarial test matrix.

The plan SHOULD make hidden architectural assumptions explicit before the Executor chooses local implementation details.

---

## Decision 3 — Primary-Brain Architecture Implementation Plan Is Mandatory

ADR-015 Decision 3 is superseded.

Every L1/L2/L3 task SHALL receive a bounded Primary-Brain **Architecture Implementation Plan** before RUN.

The plan owns architectural HOW at the level of:
- invariant decomposition;
- implementation boundaries;
- permitted design space;
- failure policy;
- proof obligations;
- test obligations.

It SHALL NOT duplicate the Executor's repository-heavy detailed plan.

The Active Executor still owns:
- repository inspection;
- exact file/local-code choices within the contract;
- detailed edit sequence;
- implementation mechanics;
- test implementation;
- self-audit.

If the Executor discovers that the Brain plan conflicts with actual repository constraints or a locked invariant, it MUST stop/escalate rather than silently reinterpret the contract.

### Default persistence

To minimize artifact and Bridge complexity, the Architecture Implementation Plan and Adversarial Checklist SHOULD be embedded as explicit sections of the authoritative TASK artifact by default.

A separate plan artifact MAY be used when size/reuse justifies it, but this ADR does not require a new Bridge lifecycle or handoff semantic.

---

## Decision 4 — Adversarial Checklist Is Mandatory

Every TASK SHALL contain a Brain-authored adversarial checklist before RUN.

The checklist is not merely a list of acceptance tests. It SHALL ask how the implementation could incorrectly satisfy the happy path while violating the contract.

Depending on criticality, checks SHOULD include applicable cases such as:
- omitted required input;
- malformed but superficially valid input;
- canonicalization/whitespace/case ambiguity;
- stale or mismatched identity;
- duplicate/collision/aliasing;
- missing content identity;
- wrong-but-well-formed SHA/fingerprint/ref;
- unknown-field/schema drift;
- wrong lifecycle phase;
- retry/duplicate-output behavior;
- unsafe authority widening;
- inconsistent cross-object metadata;
- size/bound violations;
- backward-compatibility regressions;
- evidence/test mismatch.

L1 checklists may be short. L3 checklists SHALL be explicit enough to act as a pre-implementation threat/proof matrix.

---

## Decision 5 — Full Semantic Review Is Mandatory Before Approval Eligibility

ADR-015 Decision 6 Round-1 policy is superseded.

The first review of a new implementation SHALL be a **Full Semantic Review**, not a known-delta-only review.

The Primary Brain SHALL reconstruct correctness from:
- authoritative TASK/ADR clauses relevant to the implementation;
- complete changed implementation files or complete relevant implementation boundaries;
- directly coupled interfaces/validators when needed;
- RESULT/test evidence;
- branch/SHA relation.

Whole-repository loading remains prohibited by default. “Full” means full semantic coverage of the changed contract boundary, not indiscriminate repository dumping.

The Full Semantic Review SHALL search for both:
- violations already anticipated by the Adversarial Checklist; and
- new defects or assumptions not listed in the checklist.

If findings exist, the top-level REVIEW status is `CHANGES_REQUIRED`.

---

## Decision 6 — Delta-First Remains Mandatory for FIX Reviews

ADR-013 remains authoritative for correction rounds.

After a `CHANGES_REQUIRED` review:
- inspect previous REVIEW;
- inspect new RESULT;
- inspect implementation/test delta from the previously reviewed implementation;
- verify each unresolved finding;
- escalate to unchanged files/full contract only when required by correctness.

Known-finding closure SHOULD be maximally delta-first.

However, a successful Delta Fix Review does **not** itself authorize `APPROVED`.

---

## Decision 7 — No Approval by Incremental Convergence

The invariant is:

```text
all known findings resolved != final correctness established
```

A review MUST NOT emit `APPROVED` solely because every finding from prior rounds is closed.

Before final approval, the final implementation state SHALL pass a **Final Independent Audit**.

---

## Decision 8 — Final Independent Audit Is Mandatory

The Final Independent Audit SHALL reconstruct the verdict from the final state using:
- authoritative Contract/TASK/ADR;
- final implementation at the tested implementation SHA;
- final test/evidence manifest;
- relevant coupled boundary code when needed.

Previous REVIEW findings MAY be read as supplementary evidence but MUST NOT define or limit the audit search space.

The audit SHALL deliberately search for **unknown unknowns**: contract violations, ambiguity, missing anchors, canonicalization bugs, collisions, state inconsistencies, authority leakage, or evidence gaps not raised in previous rounds.

For no-fix tasks, Full Semantic Review and Final Independent Audit MAY occur as two explicitly separated logical passes in one Brain review operation using the same bounded context.

For tasks with FIX rounds, the Final Independent Audit occurs after known-finding delta closure against the final implementation state.

Criticality controls audit depth:
- L1: lightweight independent boundary audit;
- L2: full feature-boundary audit;
- L3: deep adversarial/security/integrity audit.

---

## Decision 9 — `APPROVED` Is Reserved for Final Independent Audit Success

To preserve Bridge v0.4 semantics, this ADR does not introduce a new top-level REVIEW status.

Top-level review status remains:

```text
CHANGES_REQUIRED
APPROVED
```

`APPROVED` SHALL be emitted only when:
1. Full Semantic Review has passed for the implementation lineage;
2. all known findings are closed;
3. Final Independent Audit has passed against the final tested implementation;
4. SHA/evidence relation is valid.

A REVIEW MAY record internal stage markers such as:

```text
SEMANTIC_REVIEW: PASS
KNOWN_FINDINGS: CLOSED
FINAL_INDEPENDENT_AUDIT: PASS
```

but these markers grant no authority by themselves.

Human MERGE authorization remains separate and mandatory.

---

## Decision 10 — Token / Context Budget

This ADR intentionally spends a small amount of Brain reasoning earlier to reduce repeated late-stage remediation.

Budget discipline remains:
- Architecture Implementation Plan is bounded by criticality;
- Adversarial Checklist is compact and contract-focused;
- FIX rounds remain delta-first;
- Final Independent Audit reloads only the semantic boundary needed to independently establish correctness;
- no whole-repo dump by default;
- no paid external API call required by this policy.

Correctness outranks quota minimization.

The optimization target is **total task workload**, not minimum Brain tokens in the first turn.

---

## Decision 11 — Telemetry

ADR-014 remains authoritative. Future task telemetry SHOULD distinguish, when observable:

```text
BRAIN_CONTRACT_TURNS
BRAIN_ARCH_PLAN_TURNS
BRAIN_SEMANTIC_REVIEW_TURNS
BRAIN_DELTA_REVIEW_TURNS
BRAIN_FINAL_AUDIT_TURNS
EXECUTOR_RUNS
EXECUTOR_FIX_RUNS
FULL_BOUNDARY_READS
PATCH_BYTES
EXTERNAL_API_CALLS
```

Reported provider token usage remains `REPORTED` only when supplied by a provider/tool. Byte-derived or manually reconstructed token-equivalent estimates MUST remain `ESTIMATED` and MUST NOT be presented as exact subscription quota.

---

## Decision 12 — Relationship to ADR-015

ADR-015 remains authoritative for:
- role allocation;
- Brain vs Executor authority separation;
- importance-over-quota principle;
- Executor plan constraints;
- ADR creation discipline;
- human RUN/FIX/MERGE authority.

This ADR supersedes ADR-015 only where they conflict, specifically:
- Decision 2 work-class stage allocation;
- Decision 3 no-default-Brain-implementation-plan policy;
- Decision 6 review allocation;
- any interpretation that allows approval after known-finding closure without a final independent audit.

ADR-013 remains authoritative for delta-first FIX review context.
ADR-014 remains authoritative for usage telemetry.
ADR-016 and task-specific architecture contracts remain authoritative for their domain invariants.

---

## Decision 13 — No Control-Plane Authority Change

This ADR changes reasoning/review policy only.

It does NOT change:
- Bridge v0.4 handoff/sync/authorization/publish semantics;
- Antigravity execution authority;
- Human RUN/FIX/MERGE gates;
- Canonical State lifecycle;
- BrainAdapter/ExecutorAdapter runtime implementation;
- router/fallback/failover automation;
- provider behavior.

---

## Effective Scope

The Uniform Assurance Pipeline applies to all newly authored engineering TASKs after this ADR is locked.

Merged historical tasks MAY be retrospectively audited under this policy when risk or evidence warrants it. A post-merge finding SHALL be remediated through a new TASK; historical merged commits SHALL NOT be rewritten merely to simulate a pre-merge review.

---

## Success Criterion

AIOS succeeds under this policy when:
- L1/L2/L3 all receive the same assurance stages at appropriate depth;
- known defects converge cheaply through delta-first FIX rounds;
- `APPROVED` is never issued solely from incremental finding closure;
- final approval includes an independent search for previously unknown defects;
- Executor detailed planning remains distinct from Brain architectural planning;
- total Brain + Executor task workload decreases without weakening human authority or correctness.
