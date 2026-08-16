# REVIEW-016 — TASK-016 (AIOS Bridge v0.5-M3 ModelGateway + OpenAI-Compatible Transport + MiniMax Provider + Usage Ledger)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-016`
- Reviewed commit: `2913729541d48322113714c09a3887d7dd9a2729`
- Canonical baseline: `4f5fafc4f9c4f16413d3e4e2d13adc856509bde9`
- Branch relation to main: ahead 1, behind 0; merge base exactly canonical baseline
- RESULT-016 status: `READY_FOR_REVIEW`

## Verification Recorded in RESULT-016
- Focused External Brain suite: **67 passed**
- Full repository suite: **NOT RECORDED / NOT RUN in RESULT-016**
- Existing bridge suite: **NOT RECORDED separately**
- LIVE_SMOKE: **NOT RECORDED**
- No protected subsystem appears in the branch diff

## Overall Review
The M3 implementation is directionally strong and stays in the intended External Brain namespace:
- prompt rendering is deterministic and reuses M2 `render_context_item()` framing;
- OpenAI-compatible transport performs one POST with no retry and bounded non-JSON diagnostics;
- MiniMax payload uses `MiniMax-M3` by default, `stream=false`, `reasoning_split=true`, and `max_completion_tokens`;
- separated `reasoning_content` is not copied into `ModelResponse.content`;
- MiniMax auth/rate/timeout/unavailable/base_resp mappings and `finish_reason=length` handling are present;
- Gateway invokes one configured provider and performs post-call correlation / artifact validation;
- JsonlUsageLedger is append-only with flush/fsync and an explicit caller-supplied path;
- the branch does not add ProviderRegistry/router/fallback/retry/tool execution or Antigravity workspace authority.

However, several ADR-007 contract mismatches remain. They should be fixed together in one focused M3 correction round.

---

## Blocker 1 — Gateway provider semantics and GatewayResult ledger contract do not match ADR-007

### 1A. `request.provider=None` is incorrectly rejected
ADR-007 locks the rule:

> If `request.provider` is set, it must match the configured adapter's `provider_id`.

The current gateway instead requires equality unconditionally:

```python
if request.provider != self._provider.provider_id:
    raise ContractValidationError(...)
```

Because M1 explicitly allows `ModelRequest.provider: str | None`, a valid request with `provider=None` must be allowed to use the gateway's single trusted configured provider.

Required behavior:

```python
if request.provider is not None and request.provider != self._provider.provider_id:
    fail before provider call
```

Add a regression test proving `provider=None` invokes the configured provider exactly once.

### 1B. `GatewayResult.ledger_persisted` must be tri-state
ADR-007 locks:

```python
ledger_persisted: bool | None
```

with:
- `True` = configured ledger write succeeded;
- `False` = configured ledger write failed after provider outcome;
- `None` = no ledger configured.

Current code uses `ledger_persisted: bool` and initializes it to `False`, making "ledger disabled" indistinguishable from "ledger failed".

Required fix:
- type `bool | None`;
- no ledger => `None`;
- configured success => `True`;
- configured failure => `False`.

### 1C. Raw ledger exception text must not escape
ADR-007 locks a bounded code-only field:

```python
ledger_error_code: str | None
```

Current code returns:

```python
ledger_error = f"{type(e).__name__}: {str(e)}"
```

This can leak arbitrary filesystem paths, environment details, or secret-bearing exception text. It also violates the locked `GatewayResult` field name/semantics.

Required fix:
- use `ledger_error_code`, not raw `ledger_error`;
- return a bounded internal code such as `LEDGER_WRITE_FAILED` (or a small allowlisted code taxonomy);
- never include `str(e)` in GatewayResult, RESULT, ledger telemetry, or user-visible normalized metadata;
- ledger failure must still preserve the already completed `ModelResponse` and must not cause a second provider call.

Required tests:
1. no ledger => `ledger_persisted is None`, `ledger_error_code is None`;
2. successful ledger => `True`;
3. failing ledger => `False` + bounded code only;
4. fake exception containing a fake secret/path is not surfaced;
5. provider call count remains exactly 1.

---

## Blocker 2 — `UsageRecord` schema diverges materially from locked ADR-007

ADR-007 locks the semantic record fields:

```python
schema_version
timestamp_utc
request_id
task_id
provider
requested_model
actual_model
status: ModelResponseStatus
provider_input_tokens
provider_output_tokens
provider_reasoning_tokens
provider_cached_tokens
latency_ms
provider_request_id
context_fingerprint
context_counted_tokens
context_counter_id
context_count_is_exact
error_code
```

The current implementation instead uses a different contract:
- `recorded_at` instead of `timestamp_utc`;
- one `model` field instead of `requested_model` + `actual_model`;
- `status: str` instead of `ModelResponseStatus`;
- `input_tokens` / `output_tokens` instead of explicitly provider-labeled fields;
- `context_token_count` / `context_token_count_is_exact` instead of the locked M2 audit labels;
- no `provider_reasoning_tokens` or `provider_cached_tokens` fields;
- adds `operation` / `total_tokens` while omitting locked fields.

This is not only naming style. The M3 purpose is to prevent provider-reported usage from being confused with M2 budget estimates and to preserve requested-vs-actual model telemetry for future routing/cost work.

Required fix:
1. align the immutable `UsageRecord` with ADR-007 field names and types;
2. use `schema_version="1"` unless ADR-007 is explicitly revised;
3. generate timezone-aware UTC ISO-8601 `timestamp_utc`;
4. `requested_model = request.model` (may be `None`);
5. `actual_model = response.model`;
6. `status` is `ModelResponseStatus` internally and serializes `.value`;
7. provider token fields come only from provider-reported usage;
8. M2 context count remains separately named/labeled;
9. reasoning/cached fields exist and may remain `None` when unavailable;
10. token fields reject bool/negative values;
11. no prompt/context/output/headers/credentials/raw errors in serialized records.

Also align the `UsageLedger` protocol with ADR-007's locked append contract. If file I/O must remain non-blocking from the async gateway, keep the ledger interface synchronous and call it via `asyncio.to_thread()` from the gateway rather than silently changing the public protocol.

Required tests must prove provider usage and M2 estimate are separately labeled and that requested/actual model values are preserved.

---

## Blocker 3 — Reasoning safety is incomplete when reasoning appears inside `message.content`

The provider correctly ignores a separate `reasoning_content` field. That is good.

But current success parsing accepts `message.content` verbatim. Therefore content such as:

```text
<think>hidden reasoning...</think>
## SUMMARY
...
```

would be returned in `ModelResponse.content` and could flow into an AIOS artifact. ADR-007 explicitly forbids exposing `<think>` blocks or equivalent provider reasoning and requires conservative normalization / `INVALID_RESPONSE` if final content cannot be separated safely.

Required fix:
- before returning SUCCESS, detect provider reasoning markers in final content;
- safest V0.5 behavior is fail closed to `INVALID_RESPONSE` when `<think>` / `</think>` or an inseparable reasoning envelope appears;
- do not copy the reasoning text into `error_message`;
- separated `reasoning_content` / `reasoning_details` remain ignored.

Required tests:
1. separate `reasoning_content` + valid final content => SUCCESS and reasoning absent;
2. separate `reasoning_details` + valid final content => SUCCESS and reasoning absent;
3. `<think>...</think>` embedded in `message.content` => `INVALID_RESPONSE`, `content=None`;
4. malformed/unclosed think envelope => fail closed;
5. no reasoning text appears in ledger/error artifact.

---

## Blocker 4 — Provider failure metadata is not consistently bounded/safe

MiniMax `base_resp.status_msg` is currently interpolated directly into `ModelResponse.error_message`:

```python
error_message=f"MiniMax ...: {base_resp_msg ...}"
```

ADR-007 requires normalized provider failure metadata to be bounded and not leak credentials or full prompt/content. Provider-returned status messages are untrusted diagnostic text and should not be passed through unbounded.

Required fix:
- prefer generic code-based error messages without raw provider text; or
- sanitize and strictly bound any retained provider message;
- do not include raw provider error body, request content, headers, Authorization, or prompt fragments.

Add a regression test with an oversized/fake-secret `status_msg` proving it is not surfaced verbatim.

---

## Blocker 5 — Acceptance evidence / RESULT-016 is incomplete

TASK-016 acceptance requires:
1. focused M3 tests pass;
2. existing M1/M2 tests remain green;
3. existing bridge tests remain green;
4. **full repository suite passes with zero regressions**;
5. RESULT records exact branch head, changed files, test counts, and live-smoke status;
6. if no live smoke occurred, RESULT explicitly says `LIVE_SMOKE: NOT_RUN`.

Current RESULT-016 only records the focused External Brain run (**67 passed**) and does not record:
- full repo test count;
- bridge test evidence;
- exact reviewed branch head SHA;
- `LIVE_SMOKE: NOT_RUN` (or a real smoke outcome);
- a correct diff stat (the displayed stat only shows `__init__.py` despite the branch adding many M3 files).

Required after code fixes:
- run focused External Brain suite;
- run bridge tests;
- run full `tests/` suite;
- no automated live MiniMax call;
- update RESULT-016 with exact head SHA, complete changed-file/diff summary, exact test counts, and explicit `LIVE_SMOKE: NOT_RUN` unless a manual smoke was intentionally executed.

A manual live call is **not required** for approval.

---

## Scope Guard
This correction round MUST remain inside v0.5-M3. Do not add:
- ProviderRegistry;
- DeepSeek/Kimi/GLM adapters;
- task classifier/router;
- retry/fallback;
- quota polling;
- provider SDK dependency;
- repo crawling/context discovery;
- Antigravity MCP/tool execution;
- patch application;
- bridge.py authorization/handoff changes;
- changes to existing Python Agent `src.providers.LLMProvider` semantics.

Keep the existing good properties:
- one provider call maximum per Gateway invocation;
- no retry;
- no cross-provider fallback;
- deterministic prompt rendering;
- M2 context correlation pre-check;
- `reasoning_split=true`;
- no priority service tier;
- explicit caller-supplied ledger path;
- external model remains proposal-only.

## Decision
CHANGES_REQUIRED.

The M3 architecture is on the right path, but the gateway/ledger telemetry contracts and reasoning fail-closed boundary must match ADR-007 before the first live external-provider path is accepted.

Human fix gate:

`/aios-worker FIX TASK-016`
