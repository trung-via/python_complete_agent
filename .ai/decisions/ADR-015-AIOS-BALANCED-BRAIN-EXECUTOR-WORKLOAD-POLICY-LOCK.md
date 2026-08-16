# ADR-015 — AIOS Balanced Brain / Executor Workload Policy Lock

STATUS: LOCKED

## Context

ADR-013 proved that Brain context must be delta-first. TASK-020 added telemetry so AIOS can measure Brain/Executor workload instead of assuming chat usage is effectively unlimited.

The architectural objective is not to minimize ChatGPT involvement at all costs. The objective is to assign work according to decision value and risk while keeping scarce Brain context bounded.

## Decision 1 — Role Allocation

Default authority model:

```text
ChatGPT / Primary Brain
  = Contract Authority + Important Design Decisions + Final Semantic Reviewer

Antigravity / Active Executor
  = Implementation Planner + Repository Inspector + Coder + Tester + Self-Auditor

Bridge / deterministic tooling
  = SHA/diff/test/usage/evidence collection and control-plane enforcement

Human
  = RUN / FIX / MERGE authority
```

Self-audit never substitutes for independent Brain review or human merge authority.

## Decision 2 — Three Work Classes

AIOS SHALL classify engineering work conceptually as:

```text
L1 MECHANICAL
L2 ENGINEERING
L3 ARCHITECTURE / HIGH-RISK
```

The classification is a planning policy, not an execution authorization mechanism.

### L1 — Mechanical

Examples: bounded evidence correction, deterministic metadata changes, small compatibility/export changes.

Default allocation:
- Executor plans and implements.
- Brain receives only the minimum contract/evidence required and performs a lightweight final review.
- New ADR normally not required.

### L2 — Engineering

Examples: new bounded module, provider adapter change, normal subsystem feature with established architecture.

Default allocation:
- Brain defines objective, invariants, scope, acceptance criteria, prohibited actions.
- Executor performs repository inspection, detailed implementation planning, code, tests, and self-audit.
- Brain performs semantic/security review using delta-first evidence.
- New ADR only when an invariant or cross-task architecture rule changes.

### L3 — Architecture / High-Risk

Examples: authority boundary, security/integrity contract, canonical state model, failover semantics, execution lease, cross-provider/executor architecture.

Default allocation:
- Brain owns architecture, invariants, trade-off decisions, ADR and acceptance contract.
- Brain may provide a high-level design when necessary, but SHALL NOT duplicate the Executor's detailed implementation plan by default.
- Executor owns implementation planning, repository inspection, code, tests, and self-audit.
- Brain performs deeper semantic/security review, still using ADR-013 delta-first escalation.

## Decision 3 — No Default ChatGPT Implementation PLAN

From TASK-021 onward, ChatGPT SHALL NOT create a separate detailed implementation PLAN artifact by default.

A Brain-authored implementation PLAN is allowed only when one of these conditions is true:
- implementation strategy itself carries architectural/security risk;
- multiple viable designs have materially different invariants or migration risk;
- the Executor requests architectural clarification that cannot be resolved from the TASK/ADR contract;
- a future locked contract explicitly requires a Brain PLAN.

Otherwise the active Executor owns HOW.

## Decision 4 — Brain Context Budget Is Independent of Importance

Important work remains with the Brain even when quota is scarce. Quota efficiency SHALL be achieved by reducing redundant context, not by delegating critical decisions to a weaker authority solely to save usage.

Preferred principle:

```text
important reasoning       -> Brain
implementation reasoning  -> Executor
mechanical verification   -> deterministic tooling
execution authority       -> Human / locked control plane
```

## Decision 5 — Executor Planning Is Advisory to the Contract

Executor plans MAY choose files, sequencing, test strategy, refactoring shape and local implementation details.

Executor plans MUST NOT:
- weaken or reinterpret locked invariants;
- widen allowed scope or authority;
- introduce a new provider/router/executor policy not authorized by the task;
- bypass human RUN/FIX/MERGE gates;
- silently replace a Brain-owned architectural decision.

If implementation reveals a contract ambiguity or architecture conflict, stop and escalate to the Brain rather than inventing a new invariant.

## Decision 6 — Review Allocation

Round 1:
- Brain reviews semantics, invariants, security/authority boundaries and acceptance evidence.
- Start from RESULT/Review Manifest + compare/delta.
- Full source/test reads are escalation-only.

Round 2+:
- Brain reviews only unresolved findings + new RESULT + FIX delta by default.
- No unchanged full TASK/ADR/source/test reload unless specifically required.

## Decision 7 — ADR Creation Budget

A new ADR SHOULD be created only when the task changes a reusable invariant, architecture boundary, authority rule, security property, canonical contract, or cross-task policy.

Normal implementation details belong in TASK/RESULT, not in new ADRs.

## Decision 8 — Telemetry Feedback Loop

TASK-020 telemetry SHALL be used to compare Brain and Executor workload over time.

Metrics SHOULD include:

```text
BRAIN_TURNS_PER_TASK
BRAIN_CONTEXT_LOAD_PER_TASK
EXECUTOR_RUNS_PER_TASK
FULL_FILE_READS_PER_REVIEW
PATCH_BYTES_PER_REVIEW
EXTERNAL_API_CALLS_PER_TASK
HUMAN_ACTIONS_PER_TASK
CONTEXT_EFFICIENCY_RATIO
```

Policy changes SHOULD be based on multiple-task evidence rather than a single anecdotal task where possible.

## Decision 9 — Relationship to Existing Contracts

- ADR-010 remains Open Multi-Agent Continuity OS architecture authority.
- ADR-011 remains Canonical Project State authority.
- ADR-012 keeps sync/pending/watch out of the mandatory happy path.
- ADR-013 remains Delta-First Brain Context Budget authority.
- ADR-014 remains Usage & Efficiency Telemetry authority.
- ADR-015 changes workload allocation only; it does not modify Bridge v0.4 handoff/publish semantics or RUN/FIX/MERGE authority.

## Success Criterion

AIOS is balanced when critical design/review quality remains Brain-owned while ordinary implementation planning and repository-heavy work are Executor-owned, with measurable reduction in redundant Brain context and no weakening of correctness, safety or human authority.
