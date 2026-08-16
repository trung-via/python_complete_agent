# TASK-024 — Usage & Efficiency Telemetry Hardening After TASK-020 Post-Merge Audit

## Work Class

`L2 — ENGINEERING`

This task follows ADR-017 Uniform Assurance Pipeline.

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
f47cc9d7e2d954413918ef7b7a2ab7a90bb1a6d8
```

TASK-020 historical implementation is merged and SHALL NOT be rewritten.

Authoritative retrospective evidence:

```text
.ai/context/audits/TASK-020-POSTMERGE-AUDIT.md
```

Relevant locked contracts/policy:
- ADR-013 Delta-First Brain Context Budget;
- ADR-014 Usage & Efficiency Telemetry Contract;
- ADR-017 Uniform Assurance Pipeline & Final Independent Audit Policy.

TASK-023 Brain-Neutral Contract Hardening is already merged. TASK-024 must not alter Brain/Failover/Bridge authority semantics.

---

## Objective

Harden M1.5 Usage & Efficiency Telemetry so telemetry identities, numeric measurements, efficiency ratios, and task-level aggregation are strict, bounded, canonical, and deterministic.

TASK-024 SHALL close all findings P20-1 through P20-5 from the TASK-020 post-merge audit without changing provider, Bridge, Executor, Brain failover, or human-approval semantics.

---

# Primary Brain Contract

## C1 — Exact canonical actor identity at Usage boundaries

For `BrainUsageRecord.brain_id` and `ExecutorUsageRecord.executor_id`:
- leading/trailing whitespace SHALL fail closed;
- actor identifiers SHALL satisfy the existing conservative lowercase actor grammar;
- do not silently normalize ambiguous external input;
- padded/unpadded forms SHALL NOT produce distinct valid telemetry fingerprints for the same logical actor.

Prefer a Usage-local exact-canonical wrapper around the shared actor validator. Do NOT change `state.py` in this task unless a Brain-local/Usage-local solution is proven impossible and escalated before editing.

## C2 — Explicit bounded numeric telemetry

Every numeric count/byte/token measurement in Usage schema v1 SHALL have a deterministic semantic upper bound in addition to its existing lower bound.

Covered categories include:
- `TokenMeasurement.min_tokens/max_tokens`;
- Brain `round`, `turns`, `input_bytes`, `output_bytes`, `patch_bytes`, `full_file_reads`, `artifact_reads`, `external_api_calls`;
- Executor `runs`, `input_bytes`, `output_bytes`, `test_runs`, `external_api_calls`;
- Human `approvals`, `manual_sync`, `manual_pending`, `manual_watch`, `human_copy_paste_bytes`;
- Efficiency byte fields;
- `estimate_tokens_from_bytes(byte_count)` input.

Required properties:
- bool remains rejected;
- negative remains rejected;
- exact maximum passes;
- maximum + 1 fails closed;
- token ranges still obey min <= max and provenance rules;
- bounds are observability safety limits, not claims about provider quotas.

Preferred compatibility rule:
- use one broad deterministic integer ceiling where practical, e.g. signed-64-bit-safe `2**63 - 1`, unless Antigravity demonstrates a narrower field-specific bound is necessary.

Do not lower existing valid historical TASK-019 values below their current ranges.

## C3 — UNKNOWN efficiency remains UNKNOWN

`context_efficiency_ratio` is derived from:

```text
useful_context_bytes / brain_context_bytes
```

A non-null ratio SHALL be valid only when:
- `useful_context_bytes` is known;
- `brain_context_bytes` is known;
- `brain_context_bytes > 0`;
- supplied ratio equals the deterministic helper result.

If either required input is unknown or total is zero:

```text
context_efficiency_ratio MUST be None
```

Do not guess a ratio from partial classification.

This rule does not require all useful/redundant/escalated components to be known merely to store their individual byte fields; existing partial partition safety may remain.

## C4 — Canonical ratio representation

Ratio fields SHALL have one deterministic persisted numeric representation.

Covered:
- `context_efficiency_ratio`;
- `full_file_read_rate`.

Requirements:
- semantically equal inputs such as `1` and `1.0` SHALL serialize identically after validation;
- negative zero SHALL not create a second valid fingerprint representation;
- non-finite values fail closed;
- values remain in `[0, 1]`;
- context efficiency retains the existing deterministic 4-decimal helper convention.

Prefer canonicalizing accepted numeric inputs to a single float representation and canonical zero, rather than widening the JSON schema.

## C5 — Deterministic token aggregation by actor class

Keep the existing generic `aggregate_token_ranges()` helper for compatibility.

Add a pure task/class-level helper that deterministically aggregates token ranges separately for:

```text
BRAIN
EXECUTOR
```

Equivalent return shapes are acceptable if bounded and explicit.

Required semantics:
- Brain aggregate considers all `brain_usage[].tokens`;
- Executor aggregate considers all `executor_usage[].tokens`;
- UNKNOWN in Brain makes Brain aggregate UNKNOWN without erasing a known Executor aggregate;
- UNKNOWN in Executor makes Executor aggregate UNKNOWN without erasing a known Brain aggregate;
- empty actor class deterministically aggregates to `(0, 0)`;
- no vendor ranking, routing, selection, or authority semantics.

## C6 — Preserve existing valid telemetry behavior

Preserve:
- REPORTED exact min=max semantics;
- ESTIMATED bounded range + method;
- UNKNOWN with no token values/method;
- historical `historical-audit-estimate-v1` method validity;
- current `utf8-bytes-div4-v1` estimator semantics unless a correctness defect is proven;
- exact partition equality when all efficiency components are known;
- 16 KiB TaskUsageRecord top-level/parser limit;
- deterministic canonical JSON + SHA-256 fingerprint;
- strict unknown-field rejection;
- TASK-019 historical baseline values and ESTIMATED provenance;
- zero telemetry model/API calls;
- no authority widening.

---

# Primary Brain Architecture Implementation Plan

This section is authoritative architectural guidance under ADR-017. Antigravity still owns detailed repository/edit planning.

## AIP-1 — Keep production change local to `usage.py`

Expected production scope:

```text
src/aios_bridge/continuity/usage.py
src/aios_bridge/continuity/__init__.py   # only to export a new public aggregation helper/constant if needed
```

Expected tests:

```text
tests/aios_bridge/continuity/test_usage.py
```

Historical baseline artifact `.ai/metrics/TASK-019-USAGE.json` SHOULD remain byte-for-byte unchanged unless a new stricter parser requires a representation-only correction that preserves all historical values/provenance. Escalate before changing it.

No `state.py`, `brain.py`, `failover.py`, Bridge, provider or executor production files should change.

## AIP-2 — One bounded integer validator path

Extend or wrap `_validate_non_negative_int()` with an explicit maximum parameter or introduce a Usage-specific bounded integer helper.

Avoid scattered field-specific ad hoc checks.

Conceptual shape:

```text
validate_usage_int(value, min, max)
```

Apply it consistently to all Usage schema numeric integer fields and estimator byte input.

## AIP-3 — Exact-canonical actor wrapper

Reuse `_validate_actor_id()` grammar, then require:

```text
raw == canonical_return
```

Reject padded identities. Do not silently rewrite them.

## AIP-4 — Centralize ratio normalization

Use a small helper for ratio fields:
1. reject bool/non-number/non-finite;
2. enforce `[0, 1]`;
3. normalize to canonical float representation;
4. normalize any negative zero to `0.0`.

For `context_efficiency_ratio`, independently enforce C3 derivation/UNKNOWN rules after numeric normalization.

## AIP-5 — Actor-class aggregation should reuse generic range aggregation

Do not duplicate token-range math.

Preferred structure:

```text
task/class helper
  -> extract Brain TokenMeasurements
  -> aggregate_token_ranges(...)
  -> extract Executor TokenMeasurements
  -> aggregate_token_ranges(...)
```

This preserves existing mixed-UNKNOWN behavior within each actor class while preventing one class from contaminating the other.

## AIP-6 — Preserve fingerprint compatibility for already-canonical valid records

A current valid TASK-020 record whose actors, integers and ratios already use canonical representations SHOULD serialize identically after hardening.

Only previously ambiguous/unbounded/contract-invalid inputs should change acceptance behavior or canonical representation.

---

# Primary Brain Adversarial Checklist

## Actor identity

1. `chatgpt-chat` passes.
2. ` chatgpt-chat`, `chatgpt-chat ` and equivalent padded Brain IDs fail.
3. `antigravity` passes.
4. padded Executor IDs fail.
5. canonical actor TaskUsageRecord JSON/fingerprint remains stable after round-trip.

## Numeric bounds

6. token maximum exact boundary passes.
7. token max+1 fails.
8. Brain count/byte exact boundary passes where semantically valid.
9. Brain boundary+1 fails.
10. Executor boundary+1 fails.
11. Human boundary+1 fails.
12. Efficiency byte boundary+1 fails.
13. estimator byte_count boundary passes.
14. estimator byte_count boundary+1 fails.
15. negative and bool cases remain rejected.
16. historical TASK-019 token ranges remain valid.

## Efficiency UNKNOWN semantics

17. known useful + known positive total + exact ratio passes.
18. useful=None + ratio=None passes.
19. useful=None + non-null ratio fails.
20. total=None + non-null ratio fails.
21. total=0 + ratio=None passes where partition is otherwise valid.
22. total=0 + ratio=0/0.0 fails.
23. supplied ratio differing from deterministic helper fails.

## Ratio canonicalization

24. `1` and `1.0` produce the same canonical persisted representation.
25. `0`, `0.0`, and `-0.0` do not create distinct fingerprints.
26. NaN/Infinity/-Infinity fail closed.
27. full_file_read_rate follows the same canonical numeric rule.

## Actor-class aggregation

28. known Brain + known Executor ranges aggregate separately.
29. Brain UNKNOWN leaves Executor known aggregate intact.
30. Executor UNKNOWN leaves Brain known aggregate intact.
31. empty Brain class -> `(0, 0)`.
32. empty Executor class -> `(0, 0)`.
33. invalid input type fails closed.

## Existing contract regression

34. REPORTED exact semantics remain green.
35. ESTIMATED method/range semantics remain green.
36. UNKNOWN semantics remain green.
37. unsupported estimator method remains rejected.
38. exact efficiency partition checks remain green.
39. 16 KiB top-level record/parser protection remains green.
40. unknown free-form fields remain rejected.
41. TASK-019 historical artifact validates unchanged and remains ESTIMATED.
42. deterministic canonical JSON/fingerprint remains green.
43. no live external calls.
44. no Bridge/provider/Brain/Executor/authority changes.
45. Continuity, Bridge and full repository suites remain green.

---

## Executor Detailed Planning Requirement

After explicit `/aios-worker RUN TASK-024`, Antigravity SHALL create its own bounded detailed implementation plan before editing.

It SHALL state:
- exact numeric bound constant(s) and why they are safe/compatible;
- exact helpers/functions to modify;
- canonical ratio representation rule;
- actor-class aggregation return shape;
- compatibility effect on TASK-019 baseline;
- focused and full regression tests.

The Executor plan MUST NOT weaken this TASK/ADR contract.

---

## Required Test Suites

At minimum run:

```text
pytest tests/aios_bridge/continuity/test_usage.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

---

## RESULT / Usage Manifest

`RESULT-024.md` SHALL include:

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
EXECUTOR_RUNS
EXECUTOR_FIX_RUNS
TASK_019_BASELINE_VALID
TASK_019_BASELINE_CHANGED
```

Do not invent exact token values.

---

## Review Protocol — ADR-017

### First review

Perform a Full Semantic Review of the complete Usage-contract change boundary.

Do not issue APPROVED merely because P20-1 through P20-5 appear fixed.

### FIX rounds

Use ADR-013 delta-first reviews for known findings.

### Final approval

Before APPROVED, Primary Brain SHALL perform a Final Independent Audit against:
- this TASK contract;
- final tested implementation;
- final Usage tests and TASK-019 baseline compatibility;
- relevant shared validator assumptions.

Previous findings are supplementary only and SHALL NOT bound the final search space.

---

## Non-Goals / Prohibited Changes

Do NOT implement or change:
- provider/model invocation;
- BrainAdapter or ExecutorAdapter;
- model routing/ranking/fallback;
- automatic Brain/Executor switching;
- Bridge v0.4 handoff/sync/publish semantics;
- Canonical State lifecycle;
- TASK-022 failover semantics;
- RUN/FIX/MERGE authority;
- prompt/chat/transcript/reasoning persistence;
- provider quota claims derived from estimates.

---

## Acceptance Criteria

1. P20-1 through P20-5 are closed.
2. Usage actor IDs are exact-canonical.
3. All Usage integer measurements have explicit deterministic semantic upper bounds.
4. UNKNOWN efficiency inputs cannot coexist with a guessed context efficiency ratio.
5. ratio fields have one canonical serialized numeric representation.
6. token aggregation by Brain vs Executor class is provided and UNKNOWN is isolated per class.
7. valid current canonical telemetry remains compatible.
8. TASK-019 historical baseline remains valid, ESTIMATED, and un-fabricated.
9. no telemetry model/API turns are introduced.
10. focused Usage, Continuity, Bridge and full repository tests pass with zero regressions.
11. no authority or Bridge/provider/Brain/Executor semantic widening.
12. Full Semantic Review passes.
13. after any FIX rounds, Final Independent Audit passes before APPROVED.
