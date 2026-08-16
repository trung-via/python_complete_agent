# TASK-020 — ChatGPT Advisory Plan

BRAIN_ID: chatgpt-chat
BRAIN_OPERATION: TASK_AND_PLAN
PLAN_MODE: DELTA_FIRST

## Goal

Implement ADR-014 with the smallest isolated Continuity addition. Do not touch Bridge execution semantics.

## Implementation Order

1. Add `src/aios_bridge/continuity/usage.py` with bounded enums/frozen dataclasses for usage source, token measurement, Brain/Executor/Human usage and efficiency metrics.
2. Keep all validation local and fail-closed. Reuse public Continuity conventions where appropriate, but do not couple telemetry to execution authority.
3. Add deterministic canonical JSON + SHA-256 fingerprint for `TaskUsageRecord`.
4. Add a pure byte-based token-equivalent estimator that explicitly returns `ESTIMATED` with a versioned method. Never call it provider-reported usage.
5. Add pure aggregation helpers for Brain/Executor min/max token ranges and context-efficiency calculation.
6. Add `.ai/metrics/TASK-019-USAGE.json` as the historical estimated baseline using the bounded audit ranges from TASK-020. Leave unavailable exact byte fields unknown/null.
7. Add focused `test_usage.py`; test validation boundaries first, then deterministic serialization/aggregation/baseline validation.
8. Run focused Continuity tests, Bridge tests, then one full repository suite for publish evidence.
9. Publish `RESULT-020.md` with the compact ADR-013/014 Review Manifest so ChatGPT Review can inspect compare/delta first.

## Review-Efficiency Guidance

The expected Round-1 ChatGPT review should normally need only:

```text
TASK-020 relevant acceptance clauses
ADR-014 relevant clauses
RESULT-020 Review Manifest
base -> tested implementation compare
changed-file patches
```

Do not require whole-file reads unless the patch is insufficient.

## Hard Stops

Stop rather than widening scope if implementation appears to require:

```text
bridge.py behavior changes
chat UI automation
provider/model calls
Brain/Executor routing
RUN/FIX/MERGE authority changes
prompt/transcript/reasoning persistence
```

## Dependency

Do not execute this plan until human-authorized TASK-019 merge has placed the Continuity M1 implementation on `main`.