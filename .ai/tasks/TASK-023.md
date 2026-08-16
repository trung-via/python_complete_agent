# TASK-023 — Brain-Neutral Contract Hardening After TASK-021 Post-Merge Audit

## Work Class

`L3 — ARCHITECTURE / HIGH-RISK`

This task is the first task authored under ADR-017 Uniform Assurance Pipeline.

Primary Brain owns:
- Contract;
- Architecture Implementation Plan;
- Adversarial Checklist;
- Full Semantic Review;
- Final Independent Audit.

Antigravity owns:
- repository inspection;
- detailed implementation plan;
- code;
- tests;
- self-audit.

Human remains sole RUN / FIX / MERGE authority.

---

## Baseline

Current canonical `main` at authoring:

```text
27b8abafe9466b52e8eccc8dd68b4b5306a1fe78
```

TASK-022 M3A Brain Failover Contract & Proof Harness is merged.

TASK-021 historical implementation is merged and SHALL NOT be rewritten.

Authoritative retrospective evidence:

```text
.ai/context/audits/TASK-021-POSTMERGE-AUDIT.md
```

Relevant locked policy/contracts:
- ADR-010 Open Multi-Agent Continuity OS;
- ADR-013 Delta-First Brain Context Budget;
- ADR-014 Usage & Efficiency Telemetry;
- ADR-015 Balanced Brain/Executor Workload Policy where not superseded;
- ADR-016 M3 Brain Failover Proof Contract;
- ADR-017 Uniform Assurance Pipeline & Final Independent Audit Policy.

---

## Objective

Harden the merged M2 Brain-Neutral Contract so its identity, path, payload and capability records are strict, deterministic, bounded and safe enough to serve as the foundation for M3B real cross-Brain proof.

TASK-023 SHALL close all four findings from the TASK-021 post-merge independent audit without widening authority or changing Bridge/provider/executor semantics.

---

## Required Contract

### C1 — Exact canonical Brain and request identity

At Brain-contract boundaries, actor/request identity SHALL be exact rather than merely valid after trimming.

For BrainRequest, BrainResult and BrainCapability:
- leading/trailing whitespace in `brain_id` SHALL fail closed;
- leading/trailing whitespace in `request_id` SHALL fail closed where request_id exists;
- values SHALL remain conservative lowercase identifiers under the existing grammar;
- logically equivalent padded/unpadded identity representations SHALL NOT coexist as distinct serialized/fingerprinted records.

Do not silently normalize ambiguous external input unless a pre-existing locked contract explicitly requires normalization. Prefer reject-on-noncanonical-input.

### C2 — Exact canonical Brain-owned paths

For Brain-owned ContextRef/OutputContract/result-pointer validation:
- leading/trailing whitespace in AIOS paths SHALL fail closed;
- duplicate ContextRefs SHALL be detected using exact canonical path identity;
- unsafe/sensitive path behavior from existing Continuity validators SHALL remain intact.

Do NOT make `ContextRef.blob_sha` globally mandatory. Generic M2 navigation refs may remain path-only; TASK-022 M3A keeps its stronger content-addressing requirement at the failover boundary.

### C3 — Exact task-token matching for PLAN / DIAGNOSIS / PATCH paths

Replace substring-based active-task matching with a deterministic delimiter-aware task identity rule.

For active `TASK-021`, examples such as these MUST fail:

```text
.ai/plans/TASK-0210-PLAN.md
.ai/plans/TASK-210-PLAN.md
.ai/context/TASK-021-OTHER-TASK-099.md   # if policy treats multiple conflicting task tokens as ambiguous
```

Valid canonical task-linked role paths SHALL continue to pass.

The implementation MUST explicitly define how leading zeros in task IDs map to role paths. It must not allow two different task IDs to alias the same artifact identity accidentally.

TASK_ARTIFACT and REVIEW_ARTIFACT behavior SHALL remain deterministic and compatible with the canonical repository naming convention.

### C4 — BrainResult payload/status consistency

Every BrainResult pointer present SHALL be validated for task/output-role consistency regardless of result status.

Define a closed deterministic payload policy.

At minimum:
- `SUCCESS` requires exactly one valid result pointer;
- `SUCCESS` SHALL reject contradictory non-null `error_code`;
- artifact-producing output types SHALL use `artifact_ref` with correct task/role path;
- `BOUNDED_TEXT` SHALL use the bounded evidence-pointer representation and SHALL NOT silently accept an artifact-output pointer unless a locked contract explicitly authorizes that representation;
- non-success statuses SHALL NOT carry ambiguous competing pointers;
- a pointer for another task SHALL fail closed even when status is FAILED / REJECTED / INCOMPLETE.

Antigravity may choose the narrowest compatible non-success pointer policy, but it MUST be explicit, deterministic and tested. If existing downstream code relies on a contradictory payload form, STOP and escalate rather than silently preserve ambiguity.

### C5 — BOUNDED_TEXT request output contract must be unambiguous

A BOUNDED_TEXT request is non-artifact output.

Its OutputContract SHALL NOT silently specify a target artifact path unless a locked architecture contract explicitly defines that behavior.

Default required behavior:

```text
expected_output_type = BOUNDED_TEXT
→ target_artifact_path MUST be None
```

### C6 — BrainCapability must be bounded and declarative

BrainCapability SHALL remain immutable and descriptive-only.

It MUST become deterministically bounded.

At minimum:
- duplicate supported operations fail closed;
- operation count cannot exceed the closed BrainOperation domain;
- brain identity is exact canonical;
- descriptive numeric capacity metadata is finite/non-negative and bounded by an explicit deterministic rule;
- serialized/descriptive representation cannot grow without bound.

Do NOT add:
- Brain selection;
- ranking;
- invocation;
- routing;
- fallback;
- failover trigger authority.

### C7 — Preserve TASK-022 M3A semantics

TASK-023 SHALL NOT weaken TASK-022 failover protections.

All M3A tests must remain green, including:
- strict Brain/request identity at failover boundary;
- mandatory canonical state fingerprint;
- replacement capability gate;
- context content anchoring;
- authoritative artifact path collision rejection;
- source-result identity/status rules;
- strict bounded failover proof.

If a Brain-contract hardening makes a TASK-022 local guard redundant, do not remove it in this task unless equivalence is proven and the change is necessary. Prefer preserving M3A defense-in-depth.

---

# Primary Brain Architecture Implementation Plan

This section is authoritative architectural guidance under ADR-017. Antigravity still owns the detailed repository/edit plan.

## AIP-1 — Introduce exact-canonical boundary helpers in `brain.py`

Prefer small Brain-local helpers that wrap existing shared validators and then require:

```text
raw_value == validated_canonical_value
```

for actor IDs, request IDs and Brain-owned AIOS paths.

This avoids changing the older generic Continuity State contract while making the M2 Brain boundary strict.

Do not duplicate full validator grammars when reuse is safe.

## AIP-2 — Canonicalize validation, not persisted semantics

Reject padded/aliased representations rather than silently modifying persisted identity.

Reason:
- fingerprint identity must be stable;
- a caller should know its supplied identity was invalid;
- fail-closed semantics are clearer than hidden normalization at authority/continuity boundaries.

## AIP-3 — Replace path substring task matching with token parsing

Use one deterministic helper for role-path task identity.

Preferred shape:
1. extract task tokens from the filename/path using a delimiter-aware expression;
2. compare exact numeric/task identity according to one documented canonical convention;
3. reject zero matches when task linkage is required;
4. reject conflicting/multiple task tokens when ambiguous;
5. never use unrestricted substring containment.

Do not infer active task identity from unrelated path text.

## AIP-4 — Centralize BrainResult payload matrix

Implement a small status/output/pointer validation matrix rather than scattered SUCCESS-only checks.

Conceptual policy:

```text
SUCCESS + artifact output
  -> artifact_ref exactly one, evidence_ref none, error_code none

SUCCESS + BOUNDED_TEXT
  -> evidence_ref exactly one, artifact_ref none, error_code none

NON-SUCCESS
  -> deterministic non-output/error representation;
     no cross-task/role pointer ambiguity
```

If non-success evidence pointers are retained for diagnostic continuation, they must be explicitly allowed only for the correct bounded representation and validated independent of status.

## AIP-5 — Bound BrainCapability structurally

Because BrainOperation is a closed enum, supported operations should behave like a unique finite set represented deterministically as the existing tuple/list contract.

Add explicit capacity bounds without turning BrainCapability into a router policy.

A 16 KiB-equivalent record cap may be reused if appropriate, but Antigravity may choose a smaller deterministic bound if justified by tests and compatibility.

## AIP-6 — Preserve serialization compatibility where valid

Valid existing canonical BrainRequest/BrainResult JSON generated by TASK-021 should continue to round-trip identically unless it relied on a newly rejected ambiguous/contradictory state.

Do not rename public fields or enum values in TASK-023.

## AIP-7 — Scope

Expected production change should normally remain centered on:

```text
src/aios_bridge/continuity/brain.py
```

Expected tests:

```text
tests/aios_bridge/continuity/test_brain.py
tests/aios_bridge/continuity/test_failover.py   # only if compatibility evidence/additional regression coverage is needed
```

`state.py` SHOULD remain unchanged unless Antigravity proves a Brain-local fix is impossible. Any proposed shared-state semantic change requires stop/escalation before editing.

No Bridge/provider/executor files should change.

---

# Primary Brain Adversarial Checklist

Before implementation is considered ready, Antigravity SHALL test or otherwise deterministically prove all applicable cases below.

## Identity / canonicalization

1. `brain-a` valid; ` brain-a`, `brain-a `, and padded equivalents fail closed.
2. canonical request ID valid; leading/trailing whitespace fails closed in BrainRequest and BrainResult.
3. BrainCapability uses the same exact actor identity rule.
4. canonical/unpadded request fingerprints remain stable after JSON round-trip.

## Context/path identity

5. canonical ContextRef path valid.
6. padded ContextRef path fails closed.
7. canonical path + padded equivalent cannot bypass duplicate ContextRef rejection.
8. sensitive/traversal/backslash/absolute-path rejection remains green.
9. BOUNDED_TEXT OutputContract with non-null target path fails closed.

## Task-role path matching

10. valid PLAN/DIAGNOSIS/PATCH path for active task passes.
11. `TASK-0210` path does not satisfy active `TASK-021`.
12. normalized-short-token prefix such as `TASK-210` does not satisfy active `TASK-021` through `TASK-21` aliasing.
13. conflicting multiple task tokens fail closed when ambiguous.
14. TASK/REVIEW artifact paths continue to map deterministically to the correct active task.

## BrainResult matrix

15. SUCCESS artifact output + correct artifact_ref passes.
16. SUCCESS artifact output + evidence_ref fails.
17. SUCCESS BOUNDED_TEXT + evidence_ref passes.
18. SUCCESS BOUNDED_TEXT + artifact_ref fails.
19. SUCCESS + error_code fails.
20. SUCCESS with both/no pointer fails as before.
21. FAILED/REJECTED/INCOMPLETE cannot smuggle a cross-task artifact pointer.
22. non-success with both pointers fails closed.
23. any pointer present remains safe/sensitive-path validated.

## Capability bounds

24. valid unique capability operations pass.
25. duplicate supported operations fail.
26. oversized/unbounded capability metadata fails deterministically.
27. invalid/padded capability brain ID fails.
28. `declarative_only=False` remains rejected.

## M3A regression

29. all TASK-022 failover tests remain green.
30. context content anchoring and path-collision protection remain unchanged.
31. replacement capability gate remains descriptive only.
32. no Brain invocation/router/fallback side effects appear.

## Repository regression

33. focused Brain tests green.
34. full Continuity tests green.
35. Bridge tests green.
36. full repository tests green.
37. no live external calls.
38. no authority widening.

---

## Executor Detailed Planning Requirement

After explicit `/aios-worker RUN TASK-023`, Antigravity SHALL create its own bounded detailed implementation plan before editing.

The Executor plan SHALL cover:
- exact helper/functions to modify;
- compatibility implications for TASK-022 failover;
- exact payload matrix;
- exact task-token parsing rule;
- capability bound rule;
- focused tests and regression suites.

The Executor plan MUST NOT weaken this TASK/ADR contract.

---

## Required Test Suites

At minimum run:

```text
pytest tests/aios_bridge/continuity/test_brain.py -q
pytest tests/aios_bridge/continuity/test_failover.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

---

## RESULT / Usage Manifest

`RESULT-023.md` SHALL include:

```text
BASE_SHA
IMPLEMENTATION_SHA
PREVIOUS_REVIEW_SHA
CHANGED_FILES
TEST_SUMMARY
BRIDGE_BEHAVIOR_CHANGED
AUTHORITY_WIDENED
LIVE_EXTERNAL_CALLS
EXECUTOR_PLAN_OWNER: antigravity
BRAIN_CONTRACT_OWNER: primary-brain
BRAIN_ARCH_IMPLEMENTATION_PLAN: YES
BRAIN_ADVERSARIAL_CHECKLIST: YES
```

Also include observable ADR-017 stage telemetry when available:

```text
EXECUTOR_RUNS
EXECUTOR_FIX_RUNS
```

Do not invent exact token values.

---

## Review Protocol — ADR-017

### First review

Must be a **Full Semantic Review** of the complete Brain-contract change boundary plus relevant coupled TASK-022 compatibility boundary.

Do not issue APPROVED merely because all listed audit findings appear fixed.

### FIX rounds

Use ADR-013 delta-first review for known findings.

### Final approval

Before `APPROVED`, ChatGPT SHALL perform a **Final Independent Audit** against:
- this TASK contract;
- final tested implementation;
- final test evidence;
- relevant M3A coupled boundary.

Previous findings are supplementary only and must not limit the final audit search space.

---

## Non-Goals / Prohibited Changes

Do NOT implement or change:
- BrainAdapter invocation;
- provider/API integration;
- model/router/ranking/fallback selection;
- automatic Brain failover;
- ExecutorAdapter / lease / switching;
- Bridge v0.4 lifecycle/handoff/publish semantics;
- Canonical State lifecycle;
- RUN/FIX/MERGE authority;
- raw prompt/response/transcript/reasoning persistence;
- M3B live cross-chat proof itself.

M3B SHALL wait until TASK-023 is merged and the hardened M2 contract has passed ADR-017 final independent audit.

---

## Acceptance Criteria

1. All P21-1 through P21-4 post-merge audit findings are closed.
2. Brain identities/request IDs/Brain-owned paths are exact canonical at the M2 boundary.
3. PLAN/DIAGNOSIS/PATCH active-task path matching cannot be satisfied by substring/prefix aliasing.
4. BrainResult status/output/pointer/error states are deterministic and non-contradictory.
5. BOUNDED_TEXT cannot silently masquerade as artifact output.
6. BrainCapability is deterministically bounded, unique in operation declarations, and remains declarative-only.
7. Valid TASK-021 canonical request/result JSON compatibility is preserved unless the old form was ambiguous or contract-invalid.
8. TASK-022 M3A failover tests remain green with no weakened invariant.
9. Focused Brain, failover, Continuity, Bridge and full-repository suites pass with zero regressions.
10. No provider/Bridge/executor/authority semantics change.
11. Full Semantic Review passes.
12. After any FIX rounds, Final Independent Audit passes before APPROVED.
