# TASK-018 — AIOS Bridge v0.5-M3.0.1 MiniMax Request Timeout Configurability

## Objective
Implement the narrow prerequisite locked in:

`.ai/decisions/ADR-009-AIOS-BRIDGE-V0.5-M3.0.1-MINIMAX-TIMEOUT-CONFIG-CONTRACT-LOCK.md`

Canonical baseline when authored:
- `main`: `6fd3cb155c9edf6aaebbf85c5ad0812e7e737abb`
- M1/M2/M3: merged / APPROVED
- ADR-009: LOCKED
- TASK-017 M3.1 real-task proof remains blocked pending this prerequisite.

Observed live evidence:
- real-task attempt #2 returned `TIMEOUT` at `30106 ms`;
- `TransportRequest.timeout_seconds` defaults to `30.0`;
- `MiniMaxOpenAIProvider` currently does not pass a timeout value into `TransportRequest`.

## Implementation Scope

Primary production file:

```text
src/aios_bridge/external_brain/providers/minimax.py
```

Focused tests under:

```text
tests/aios_bridge/external_brain/
```

Only touch additional files if required for tests/exports and explain why in RESULT.

## Required Implementation

Add an explicit provider constructor option:

```python
class MiniMaxOpenAIProvider:
    def __init__(
        self,
        api_key: str,
        *,
        model_name: str = "MiniMax-M3",
        base_url: str = "https://api.minimax.io/v1",
        path: str = "/chat/completions",
        transport: ModelTransport | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        ...
```

Equivalent keyword ordering is acceptable if backward compatibility is preserved.

Rules:
1. `timeout_seconds` must be a positive finite `int|float`, excluding bool.
2. Invalid values fail during provider construction, before any transport/network call.
3. Store normalized finite float privately.
4. Every created `TransportRequest` must receive `timeout_seconds=self._timeout_seconds` explicitly.
5. Default stays `30.0`.
6. `repr`/`str` must remain credential-safe.
7. Do not change MiniMax payload fields or response normalization semantics.
8. No retry, no fallback, no second provider invocation.

## Required Tests

At minimum cover:
- default provider sends `TransportRequest.timeout_seconds == 30.0`;
- explicit `timeout_seconds=90.0` is forwarded exactly;
- rejects `0`, negative, `True/False`, `NaN`, `+Inf`, `-Inf` before transport call;
- existing one-call/no-retry behavior remains intact;
- API key absent from `repr(provider)` and `str(provider)`;
- existing MiniMax provider tests remain green.

Use fake/mock transport only. **Do not make live MiniMax calls in automated tests.**

## Forbidden Scope

Do NOT:
- modify `bridge.py` semantics;
- modify existing Python Agent runtime `src/providers/`;
- change default model or endpoint;
- change `max_completion_tokens` policy;
- add retries/fallback/router/registry/classifier;
- add automatic timeout heuristics;
- add repo discovery;
- add filesystem/shell/browser/Git execution authority;
- alter TASK-017's human approval gate.

## Acceptance Criteria

1. ADR-009 satisfied exactly.
2. Focused External Brain/MiniMax tests green.
3. Full repository `tests/` green with zero regressions.
4. RESULT-018 records:
   - tested implementation SHA;
   - focused test command/result;
   - full-suite command/result;
   - exact changed-file summary;
   - confirmation `LIVE_SMOKE: NOT_RUN`;
   - confirmation no retry/fallback/authority widening.
5. Publish task branch normally through AIOS Bridge.

## After Approval/Merge

TASK-017 remains the next milestone. Its next manual live PLAN attempt should explicitly construct:

```python
MiniMaxOpenAIProvider(
    api_key=os.environ["AIOS_MINIMAX_API_KEY"],
    timeout_seconds=90.0,
)
```

Do not retry TASK-017 live calls before TASK-018 is approved and merged.
