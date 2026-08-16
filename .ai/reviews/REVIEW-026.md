# REVIEW-026 — TASK-026 MiniMax Timeout Validation Hardening

STATUS: APPROVED

## Review Scope
- Review round: `1` — ADR-017 Full Semantic Review + Final Independent Audit
- Reviewed branch: `ai/task-026`
- Reviewed branch head: `44436c59eb42dbdbffaee28a738d11694958a4ea`
- Tested implementation SHA reported by RESULT: `5c34f49f86d2db9298dbef00f99ff3278349c859`
- Current execution base/main: `6b984b2cd74366708dc52011288f00fadd740743`
- TASK authoring baseline: `47dbde428169bb003d010b9ded79c9528bb40fba`
- Branch relation to current main: ahead `2`, behind `0`; merge-base exact current main.
- `5c34f49... -> 44436c5...` changes only `.ai/results/RESULT-026.md`; production code/tests at reviewed head equal the tested implementation.
- Review mode: complete TASK-026 Contract + Architecture Implementation Plan + Adversarial Checklist, MiniMax provider timeout boundary, provider tests, ADR-009 transport coupling, post-merge TASK-018 finding P18-1, RESULT evidence, and SHA/base relation.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: PASS
KNOWN_FINDINGS: CLOSED
FINAL_INDEPENDENT_AUDIT: PASS
APPROVED: YES
```

## Full Semantic Review

P18-1 is closed correctly.

`MiniMaxOpenAIProvider.__init__()` now:
1. rejects bool and non-`int|float` values before numeric conversion;
2. converts accepted numeric input through guarded `float(timeout_seconds)`;
3. catches `OverflowError`, `ValueError`, and `TypeError` and maps them to bounded `ContractValidationError` diagnostics;
4. validates the normalized float is finite and strictly positive;
5. stores the normalized float in `_timeout_seconds`.

This removes the historical path where an extreme Python integer such as `10**10000` could escape as raw `OverflowError` or require rendering the original unbounded integer.

The normal ADR-009 behavior remains intact:
- default `30.0` remains `30.0`;
- explicit `90.0` remains exact;
- integer `90` normalizes to float `90.0`;
- each provider invocation passes `self._timeout_seconds` explicitly into `TransportRequest`;
- model, endpoint, path and payload semantics are unchanged;
- API key remains excluded from provider `repr`/`str`;
- no retry, fallback, router or automatic timeout policy was introduced;
- generic transport production code was not modified.

## Final Independent Audit

The final audit rechecked the complete affected boundary rather than only P18-1.

PASS evidence:
- production delta is confined to `src/aios_bridge/external_brain/providers/minimax.py`;
- test delta is confined to `tests/aios_bridge/external_brain/test_minimax_provider.py`;
- huge positive and negative integer timeouts are covered and map to `ContractValidationError`;
- ordinary invalid zero/negative/bool/NaN/infinity/string/null cases remain rejected during construction;
- valid integer timeout is normalized and forwarded as float;
- `TransportRequest` remains the wire-level timeout authority;
- `OpenAICompatibleTransport.send()` still performs one POST, uses the request timeout for HTTP timeout, and uses `timeout + 5.0` as the outer async safety timeout;
- the provider constructor performs no transport send/scheduling; transport invocation occurs only from `invoke()`, so invalid construction cannot issue a model request;
- no credentials are added to diagnostics or representations;
- no live external call is required or reported;
- Bridge/runtime provider/executor/RUN-FIX-MERGE authority is unchanged.

### Authoring-baseline advancement

TASK-026 was authored when main was `47dbde4...`; before RUN, TASK-025 was approved and merged, advancing main to `6b984b2...`. The intervening delta changes only Canonical State and its tests/RESULT and does not touch MiniMax provider, External Brain transport, or TASK-026 test boundary. The TASK-026 execution branch was created from current main `6b984b2...` and is currently ahead 2 / behind 0, so this advancement does not invalidate the task contract or review.

### Non-blocking test-strength note

TASK-026 does not add a separate MockTransport assertion specifically for “invalid constructor => zero transport calls”. This is not blocking because the constructor source contains no transport call or task scheduling, and `send()` is reached only inside `invoke()`. The semantic requirement is therefore directly established by the reviewed production boundary. A future test-cleanup task may add an explicit spy assertion if desired, but no remediation is required for TASK-026.

## Evidence Accepted

RESULT reports against tested implementation `5c34f49f86d2db9298dbef00f99ff3278349c859`:

```text
External Brain: 86 passed
AIOS Bridge: 164 passed
Full repository: 638 passed
Regressions: 0
LIVE_EXTERNAL_CALLS: 0
DEFAULT_TIMEOUT: 30.0
EXPLICIT_TIMEOUT_90_FORWARDED: YES
EXTREME_INT_FAILS_WITH_CONTRACT_ERROR: YES
RETRY_ADDED: NO
FALLBACK_ADDED: NO
BRIDGE_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 0
```

`PREVIOUS_REVIEW_SHA: null` is correct because this is the first review round.

## Decision

`APPROVED`

TASK-026 satisfies its remediation contract, closes TASK-018 post-merge finding P18-1, and passes the ADR-017 assurance pipeline at reviewed branch head:

```text
44436c59eb42dbdbffaee28a738d11694958a4ea
```

This approval grants merge eligibility only. MERGE remains a separate explicit human action.
