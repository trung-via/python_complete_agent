# TASK-025 — Canonical Project State Identity & Freshness Hardening After TASK-019 Audit

## Work Class

`L3 — ARCHITECTURE / HIGH-RISK`

This task follows ADR-017 Uniform Assurance Pipeline.

Primary Brain owns Contract, Architecture Implementation Plan, Adversarial Checklist, Full Semantic Review and Final Independent Audit. Antigravity owns repository inspection, detailed implementation plan, code, tests and self-audit. Human remains sole RUN/FIX/MERGE authority.

---

## Baseline

Canonical `main` at authoring:

```text
47dbde428169bb003d010b9ded79c9528bb40fba
```

Authoritative retrospective evidence:

```text
.ai/context/audits/TASK-019-POSTMERGE-AUDIT.md
```

Relevant locked contracts/policy:
- ADR-010 Open Multi-Agent Continuity OS Architecture;
- ADR-011 Canonical Project State Contract;
- ADR-016 M3 Brain Failover Proof Contract;
- ADR-017 Uniform Assurance Pipeline.

TASK-019 remains historically merged and SHALL NOT be rewritten.

---

## Objective

Harden schema-v1 Canonical Project State so all persisted identities are exact-canonical, authoritative artifact paths are globally unambiguous, explicit observations are constructible and deeply immutable, and parser failures remain inside the Continuity validation domain.

Close P19-1 through P19-5 without changing schema version, Bridge v0.4 semantics, Brain/Executor authority, failover authority, or automatic publication behavior.

---

# Primary Brain Contract

## C1 — Exact-canonical state identities

At the state boundary, the following values SHALL be exact-canonical external inputs:
- `BranchState.branch`;
- `ArtifactRef.path`;
- `ArtifactRef.ref`;
- `BrainState.last_id` when present;
- `ExecutorState.last_id` when present.

Rules:
- reuse existing conservative validators;
- require raw input to equal the canonical validator result;
- leading/trailing whitespace SHALL fail closed, not be silently persisted or normalized;
- already-canonical valid state serialization/fingerprints SHALL remain unchanged.

Do not weaken exact TASK/RESULT/REVIEW role paths or SHA rules.

## C2 — Global authoritative artifact-path uniqueness

Within one `ContinuityArtifacts`, collect:

```text
task
contracts[*]
plan? 
result?
review?
```

Every present authoritative artifact path SHALL be unique across the complete role set.

Any duplicate path SHALL fail closed regardless of same/different `ref` or `blob_sha`.

This is canonical-state integrity. TASK-022 failover duplicate-path validation may remain as defense in depth and MUST NOT be weakened/removed in this task.

## C3 — Valid empty observation semantics

`StateObservation` SHALL support omission of artifact observations without constructor failure.

An empty artifact observation set must be a valid immutable observation. When checked against a state containing artifact pointers and no known mismatch, missing observations SHALL produce `INCOMPLETE` through `check_freshness()`.

No implicit discovery is allowed.

## C4 — Deeply immutable observation facts

Caller-owned mutable mappings SHALL NOT remain mutable inside `StateObservation`.

At construction:
- validate keys/values;
- copy/freeze them into an immutable mapping representation;
- later mutation of the caller's original dict SHALL NOT change the observation or freshness result.

Blob SHAs remain exact lowercase 40-hex.

## C5 — Consistent strict parser error domain

Invalid `BrainState.last_operation` supplied through `BrainState.from_dict()` / `ContinuityState.from_dict()` SHALL fail as `ContinuityStateValidationError`, not leak raw enum `ValueError`.

Do not widen BrainOperation enum values.

## C6 — Preserve M1 and coupled M2/M3 behavior

Preserve:
- `SCHEMA_VERSION = "1"`;
- `MAX_SERIALIZED_BYTES = 16384`;
- phase/next-operation compatibility;
- task branch SHA phase rules;
- exact TASK/RESULT/REVIEW role naming;
- plan task-identity behavior unless a correctness defect is separately demonstrated;
- sensitive path rejection;
- canonical JSON/fingerprint behavior for already-canonical valid states;
- STALE > INCOMPLETE > FRESH precedence;
- pure/no-I/O freshness evaluation;
- Bridge Runtime State separation;
- TASK-022 failover semantics and defense-in-depth checks;
- human RUN/FIX/MERGE authority.

---

# Primary Brain Architecture Implementation Plan

## AIP-1 — Keep changes local to Continuity State

Expected production scope:

```text
src/aios_bridge/continuity/state.py
```

Expected test scope:

```text
tests/aios_bridge/continuity/test_state.py
tests/aios_bridge/continuity/test_failover.py   # regression only if needed
```

`__init__.py` should not need public API changes unless an immutable observation helper type must be exported; prefer no new public type.

Do not change `brain.py`, `usage.py`, `failover.py`, Bridge, providers or executor production code.

## AIP-2 — Exact-canonical wrapper, not silent normalization

Introduce a small helper or inline pattern conceptually:

```text
canonical = existing_validator(raw)
require raw == canonical
```

Use this consistently at state object boundaries. Avoid changing generic validator return semantics because later modules deliberately wrap these validators locally.

## AIP-3 — Validate artifact uniqueness after all roles are typed

Inside `ContinuityArtifacts.__post_init__()`:
1. validate types / freeze contracts;
2. build ordered role entries for task/contracts/plan/result/review;
3. reject duplicate `path` across every present entry.

Do not rely on dict insertion that could overwrite a collision before validation.

## AIP-4 — Freeze observation mapping defensively

Preferred implementation:
- use `field(default_factory=dict)` or `None` as construction input only if needed;
- copy validated entries;
- store `MappingProxyType(copy)` or an equivalently immutable Mapping.

The frozen dataclass alone is insufficient if nested mapping remains mutable.

## AIP-5 — Keep freshness API semantics unchanged

`check_freshness()` remains pure and accepts `StateObservation`.

No new I/O or repo discovery. Empty immutable artifact observations naturally cause missing-artifact issues and `INCOMPLETE`.

## AIP-6 — Parser error wrapping only

For Brain operation parsing, route the raw enum input through existing `BrainState.__post_init__()` or catch enum conversion and raise `ContinuityStateValidationError` with bounded diagnostics.

Do not create fallback values.

---

# Primary Brain Adversarial Checklist

1. `BranchState(branch="main")` passes; padded branch fails.
2. `ArtifactRef(ref="ai-control")` passes; padded ref fails.
3. canonical `.ai/decisions/...` path passes; padded contract/plan path fails.
4. canonical actor IDs pass; padded Brain/Executor IDs fail.
5. canonical state round-trip/fingerprint remains stable.
6. task path colliding with a contract path fails even same blob/ref.
7. task path colliding with contract path fails with different blob/ref.
8. contract-plan duplicate path fails.
9. contract-result duplicate path fails if a crafted role can reach validation.
10. plan/review/result duplicate path fails wherever namespace permits construction.
11. two distinct contract paths remain valid.
12. `StateObservation(main_sha=...)` with omitted artifact mapping constructs successfully.
13. empty artifact mapping + state artifacts -> `INCOMPLETE` when no mismatch exists.
14. caller dict mutated after observation construction does not mutate observation.
15. observation mapping itself rejects mutation.
16. invalid observation blob SHA remains rejected.
17. unknown Brain operation through `BrainState.from_dict()` raises `ContinuityStateValidationError`.
18. same through `ContinuityState.from_dict()` remains in Continuity validation domain.
19. strict unknown-field tests stay green.
20. path/sensitive-path tests stay green.
21. 16 KiB constructor/parser protection stays green.
22. phase/next-operation and phase-artifact tests stay green.
23. freshness FRESH/STALE/INCOMPLETE precedence stays green.
24. TASK-022 failover duplicate-path and state-fingerprint tests stay green.
25. TASK-023 Brain contract tests stay green.
26. TASK-024 Usage tests stay green.
27. no live external calls.
28. no Bridge/provider/executor/authority changes.
29. Continuity, AIOS Bridge and full repository suites green.

---

## Executor Detailed Planning Requirement

After explicit `/aios-worker RUN TASK-025`, Antigravity SHALL create its own bounded implementation plan before edits. It must identify exact validators/wrappers, immutable mapping representation, collision-validation ordering, coupled failover regression tests, and compatibility effect on existing canonical state fixtures.

Executor plan MUST NOT weaken this contract.

---

## Required Tests

At minimum:

```text
pytest tests/aios_bridge/continuity/test_state.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

---

## RESULT Manifest

`RESULT-025.md` SHALL include:

```text
BASE_SHA
IMPLEMENTATION_SHA
PREVIOUS_REVIEW_SHA
CHANGED_FILES
TEST_SUMMARY
SCHEMA_VERSION: 1
MAX_SERIALIZED_BYTES: 16384
CANONICAL_STATE_COMPATIBLE: YES/NO
TASK_022_FAILOVER_REGRESSION: PASS/FAIL
BRIDGE_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
LIVE_EXTERNAL_CALLS: 0
EXECUTOR_PLAN_OWNER: antigravity
BRAIN_CONTRACT_OWNER: primary-brain
BRAIN_ARCH_IMPLEMENTATION_PLAN: YES
BRAIN_ADVERSARIAL_CHECKLIST: YES
EXECUTOR_RUNS
EXECUTOR_FIX_RUNS
```

Do not invent provider/token usage.

---

## Review Protocol

First review = Full Semantic Review of the complete changed state boundary. FIX rounds = ADR-013 delta-first. `APPROVED` is forbidden until a fresh Final Independent Audit reconstructs the verdict from this contract, final tested implementation, state/freshness tests and coupled failover assumptions.

---

## Prohibited Changes

Do NOT:
- bump schema version;
- add automatic state publication;
- change Bridge v0.4 handoff/sync/publish;
- change BrainAdapter/ExecutorAdapter invocation;
- add routing/fallback/retry;
- weaken TASK-022 failover validation;
- add filesystem/Git/network discovery to freshness;
- persist prompt/chat/reasoning/secrets;
- widen RUN/FIX/MERGE authority.

---

## Acceptance Criteria

1. P19-1 through P19-5 closed.
2. all persisted state identities exact-canonical.
3. global authoritative artifact paths unique.
4. omitted artifact observation is valid and yields INCOMPLETE when appropriate.
5. observation mappings deeply immutable.
6. invalid Brain operation parser errors stay inside Continuity validation domain.
7. schema-v1 canonical valid states remain compatible/fingerprint-stable.
8. TASK-022 failover remains green with its duplicate-path defense intact.
9. no authority/Bridge/provider/executor widening.
10. required suites green with zero regressions.
11. Full Semantic Review passes.
12. Final Independent Audit passes before APPROVED.
