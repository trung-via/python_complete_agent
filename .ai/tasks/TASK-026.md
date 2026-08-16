# TASK-026 — MiniMax Timeout Validation Hardening After TASK-018 Audit

## Work Class

`L1 — MECHANICAL / BOUNDED HARDENING`

This task follows ADR-017 Uniform Assurance Pipeline. All assurance stages exist; depth is intentionally small.

Primary Brain owns Contract, Architecture Implementation Plan, Adversarial Checklist, Full Semantic Review and Final Independent Audit. Antigravity owns detailed plan/code/tests/self-audit. Human remains sole RUN/FIX/MERGE authority.

---

## Baseline

Canonical `main` at authoring:

```text
47dbde428169bb003d010b9ded79c9528bb40fba
```

Authoritative audit:

```text
.ai/context/audits/TASK-018-POSTMERGE-AUDIT.md
```

Relevant locked contract:
- ADR-009 MiniMax Request Timeout Configurability Contract;
- ADR-017 Uniform Assurance Pipeline.

TASK-018 remains historically merged and SHALL NOT be rewritten.

---

## Objective

Close P18-1 by making `MiniMaxOpenAIProvider(timeout_seconds=...)` deterministically reject non-normalizable extreme integer inputs with `ContractValidationError`, while preserving all ordinary ADR-009 timeout behavior exactly.

---

# Primary Brain Contract

## C1 — Guarded normalized-float timeout validation

`MiniMaxOpenAIProvider.__init__` timeout validation SHALL:
1. reject bool and non-`int|float` input;
2. convert accepted numeric input to float inside a guarded conversion boundary;
3. if conversion raises overflow/value/type-related numeric conversion failure, raise `ContractValidationError` with bounded diagnostics;
4. reject normalized NaN, infinity, zero and negatives;
5. store the validated normalized float in `_timeout_seconds`.

Do not render an arbitrarily large integer verbatim in the error path.

## C2 — Preserve ADR-009 semantics

Preserve exactly:
- default timeout `30.0`;
- integer `90` and float `90.0` normalize to/forward `90.0`;
- every MiniMax `TransportRequest` receives `timeout_seconds=self._timeout_seconds` explicitly;
- API key remains absent from repr/str;
- model, endpoint, path and payload unchanged;
- no retry/fallback/router/automatic tuning;
- no generic TransportRequest/OpenAICompatibleTransport redesign.

---

# Primary Brain Architecture Implementation Plan

## AIP-1 — Provider-local change only

Expected production file:

```text
src/aios_bridge/external_brain/providers/minimax.py
```

Expected test file:

```text
tests/aios_bridge/external_brain/test_minimax_provider.py
```

Do not change generic transport production code.

## AIP-2 — Normalize first under try/except

Conceptual flow:

```text
if bool or wrong type -> ContractValidationError
try:
    normalized = float(timeout_seconds)
except (OverflowError, ValueError, TypeError):
    -> ContractValidationError with bounded type/value category
if not finite(normalized) or normalized <= 0:
    -> ContractValidationError
self._timeout_seconds = normalized
```

Avoid formatting the full original integer when its representation may itself be unbounded/problematic.

---

# Primary Brain Adversarial Checklist

1. default -> `30.0`.
2. explicit `90.0` -> forwarded exactly.
3. integer `90` -> stored/forwarded `90.0`.
4. `0`, `0.0` rejected.
5. negative int/float rejected.
6. bool rejected.
7. NaN rejected.
8. +Inf/-Inf rejected.
9. huge positive int such as `10**10000` -> `ContractValidationError`, not `OverflowError`/`ValueError`.
10. huge negative int -> same contract error domain.
11. invalid construction causes zero transport calls.
12. API key absent from repr/str.
13. exactly one transport call on valid invoke.
14. TransportRequest timeout equals normalized provider timeout.
15. payload/model/path/endpoint tests remain green.
16. reasoning filtering/response normalization tests remain green.
17. no live external calls.
18. full External Brain, AIOS Bridge and repository suites green.

---

## Executor Detailed Planning Requirement

After `/aios-worker RUN TASK-026`, Antigravity SHALL create a short detailed plan identifying the exact constructor validation delta and test additions before editing.

---

## Required Tests

```text
pytest tests/aios_bridge/external_brain/test_minimax_provider.py -q
pytest tests/aios_bridge/external_brain/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live provider calls.

---

## RESULT Manifest

`RESULT-026.md` SHALL include:

```text
BASE_SHA
IMPLEMENTATION_SHA
PREVIOUS_REVIEW_SHA
CHANGED_FILES
TEST_SUMMARY
DEFAULT_TIMEOUT: 30.0
EXPLICIT_TIMEOUT_90_FORWARDED: YES
EXTREME_INT_FAILS_WITH_CONTRACT_ERROR: YES
LIVE_EXTERNAL_CALLS: 0
RETRY_ADDED: NO
FALLBACK_ADDED: NO
BRIDGE_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
EXECUTOR_PLAN_OWNER: antigravity
BRAIN_CONTRACT_OWNER: primary-brain
BRAIN_ARCH_IMPLEMENTATION_PLAN: YES
BRAIN_ADVERSARIAL_CHECKLIST: YES
EXECUTOR_RUNS
EXECUTOR_FIX_RUNS
```

---

## Review Protocol

First review = Full Semantic Review, even though L1 and expected delta is tiny. If findings require FIX, use delta-first. Final Independent Audit is mandatory before APPROVED.

---

## Prohibited Changes

Do NOT change:
- generic transport semantics;
- MiniMax model/endpoint/payload policy;
- retries/fallback/router;
- Bridge v0.4;
- runtime `src/providers/`;
- TASK-017 proof artifacts;
- RUN/FIX/MERGE authority.

---

## Acceptance Criteria

1. P18-1 closed.
2. arbitrary extreme integer timeout fails deterministically with `ContractValidationError`.
3. ordinary ADR-009 timeout behavior remains exact.
4. no live external calls or retry/fallback changes.
5. required suites green with zero regressions.
6. Full Semantic Review passes.
7. Final Independent Audit passes before APPROVED.
