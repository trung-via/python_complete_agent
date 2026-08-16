# ADR-009 — AIOS Bridge v0.5-M3.0.1 MiniMax Request Timeout Configurability Contract Lock

## Status
LOCKED

## Date
2026-08-16

## Preconditions
- ADR-005 / M1, ADR-006 / M2, ADR-007 / M3 are LOCKED and merged.
- Canonical `main`: `6fd3cb155c9edf6aaebbf85c5ad0812e7e737abb`.
- M3 synthetic MiniMax-M3 live smoke succeeded.
- M3.1 real-task attempt #1 reached MiniMax and was rejected as `INVALID_RESPONSE / TRUNCATED_OUTPUT` at the 2048 completion ceiling.
- M3.1 real-task attempt #2 used a reduced bounded context and returned `TIMEOUT` at `30106 ms` with no provider usage metadata.
- Current `TransportRequest.timeout_seconds` default is `30.0`.
- Current `MiniMaxOpenAIProvider` creates `TransportRequest` without supplying `timeout_seconds`, therefore MiniMax requests inherit 30 seconds even though `OpenAICompatibleTransport` has its own longer constructor default.

## Objective
Remove the accidental hard coupling between MiniMax inference and the `TransportRequest` 30-second default, while preserving all M3 authority, safety, and single-call semantics.

This is a narrow prerequisite for continuing TASK-017 real-task proof.

## Decision 1 — Provider-Level Finite Timeout Configuration

Extend `MiniMaxOpenAIProvider.__init__` additively with:

```python
timeout_seconds: float = 30.0
```

Requirements:
- validate it is a positive finite number;
- reject bool, zero, negative, NaN, and infinity before any network call;
- store it as private provider configuration;
- pass it explicitly to `TransportRequest(timeout_seconds=...)` for every MiniMax invocation;
- keep the default `30.0` so existing behavior remains backward-compatible;
- no environment-variable inference is required in this milestone.

## Decision 2 — No Generic Transport Redesign

Do not change `ModelTransport`, `TransportRequest`, or `OpenAICompatibleTransport` semantics except where a test-only compatibility adjustment is strictly necessary.

`TransportRequest` remains the single wire-level timeout authority for a specific request.

`OpenAICompatibleTransport` must continue to perform:
- exactly one POST;
- finite HTTP timeout;
- finite outer async timeout;
- no retry.

## Decision 3 — No Retry / Fallback

A longer configured timeout MUST NOT introduce:
- retry;
- fallback;
- polling;
- provider switching;
- repeated model invocation;
- LLM-driven timeout decisions.

One `ModelGateway.invoke()` still results in at most one provider call.

## Decision 4 — Safe Representation

Provider `repr`/`str` may expose the configured timeout value, but MUST NOT expose the API key or Authorization header.

## Decision 5 — M3.1 Operational Value

After this change is approved and merged, the next TASK-017 live PLAN attempt may instantiate:

```python
MiniMaxOpenAIProvider(
    api_key=...,
    timeout_seconds=90.0,
)
```

The 90-second value is an explicit manual M3.1 evaluation choice, not a new global default.

If the provider still times out or returns truncated output, stop repeated live attempts and reassess model/endpoint strategy rather than adding retries.

## Required Tests

Focused tests must prove:
1. default provider timeout remains `30.0` at `TransportRequest`;
2. explicit timeout (e.g. `90.0`) is forwarded exactly to `TransportRequest`;
3. invalid timeout values fail before transport invocation;
4. one-call/no-retry behavior is unchanged;
5. provider repr/str do not expose the API key;
6. existing MiniMax payload, model matching, response normalization, reasoning filtering, and usage behavior remain unchanged.

## Non-Goals
- changing MiniMax model;
- changing MiniMax endpoint;
- increasing `max_completion_tokens` beyond provider limits;
- retries;
- fallback;
- router/provider registry;
- task classifier;
- automatic timeout tuning;
- workspace/shell/browser/Git authority;
- changes to `bridge.py`;
- changes to Python Agent runtime `src/providers/`.

## Acceptance
- focused External Brain tests green;
- full repository tests green;
- no regressions;
- exact changed-file summary in RESULT;
- no live MiniMax call required for TASK-018 automated acceptance.
