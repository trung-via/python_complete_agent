# REVIEW-028 — TASK-028 Open Multi-Agent Continuity OS M4 Executor-Neutral Contract

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1` — ADR-017 Full Semantic Review
- Reviewed branch: `ai/task-028`
- Reviewed branch head: `af029ae336550ea75954bb921ac0037d7dd0b853`
- Tested implementation SHA reported by RESULT: `e69c06ae2ef2e9f74b9a4aaceaeda53a22c1bcea`
- Base/current main: `b4178d283d451054dca51964771053d9e0de2b5c`
- Branch relation: ahead `2`, behind `0`; merge-base exact current main.
- `e69c06a... -> af029ae...` adds only `.ai/results/RESULT-028.md`; production/test code at reviewed head equals the tested implementation.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: NOT_RUN
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## What Passed

The implementation is correctly scoped to the expected M4 boundary:
- new `src/aios_bridge/continuity/executor.py`;
- additive exports in `continuity/__init__.py`;
- task-local pure tests;
- no changes to state/brain/failover/usage/Bridge/providers/runtime executor;
- no concrete vendor adapter, transport, lease, failover or dispatch logic.

The main RUN/FIX execution model is also materially aligned with ADR-018:
- `ExecutionOperation` contains RUN/FIX only;
- request role binding is exact (`RUN -> TASK`, `FIX -> REVIEW`);
- request/state anchoring is pure and content-addressed;
- capability eligibility is pure/declarative;
- `ExecutionResult` uses a closed stable-boundary payload matrix;
- SUCCESS request/result identity/path/ref binding is mechanical;
- three neutral test adapters structurally conform to `ExecutorAdapter`.

These positive points are not sufficient for approval because the following canonical-identity defects remain.

---

## Findings

### R1-1 — `ExecutorCapabilities.capacity_metadata` breaks frozen canonical identity and evidence/secret hygiene
Severity: HIGH

`ExecutorCapabilities` is declared `@dataclass(frozen=True)`, but `capacity_metadata` is typed as arbitrary `Mapping[str, Any]` and is shallow-copied into a mutable `dict` in `__post_init__`.

Consequences:
1. A constructed capability record can be mutated after construction through `caps.capacity_metadata[...] = ...` even though the dataclass is frozen.
2. `to_canonical_json()` / `fingerprint()` therefore can change after construction for the same object identity.
3. Nested mutable values remain mutable even if the top-level mapping were wrapped.
4. Arbitrary keys/values can contain secret-like/vendor/session metadata forbidden by ADR-018 Decision 14.
5. Non-JSON-serializable or non-finite arbitrary values can escape the intended strict `ContinuityStateValidationError` contract through raw JSON serialization behavior.

This violates ADR-018 Decisions 7, 13 and 14 and TASK-028 C8/C14: ExecutorCapabilities must be immutable, strict-schema, deterministic, bounded and safe as a future M5/M6 identity primitive.

Required remediation:
- preferred: remove `capacity_metadata` entirely in M4 because no current M4 behavior requires it; or
- define a genuinely closed, immutable, bounded descriptive metadata contract with explicit allowed keys/value types, finite numeric validation, deep immutability, forbidden secret/authority semantics, deterministic serialization and wrapped validation failures.

Required tests must prove:
- fingerprint cannot change after construction;
- nested/top-level mutation cannot alter canonical identity;
- secret/authority-like metadata is not persistable;
- non-finite/non-serializable metadata fails with `ContinuityStateValidationError` if metadata remains supported.

### R1-2 — `from_dict()` launders arbitrary iterables into deterministic tuples
Severity: MEDIUM

TASK-028 AIP-4 explicitly requires ordered context/evidence inputs to accept only `list`/`tuple` and reject `set`/generator/arbitrary iterables.

The constructors enforce that rule, but the external parsers bypass it:
- `ExecutionRequest.from_dict()` immediately executes `tuple(ArtifactRef.from_dict(r) for r in data["context_refs"])` before calling the constructor;
- `ExecutionResult.from_dict()` does the same for `evidence_refs`.

Therefore a generator supplied to `from_dict()` is consumed and transformed into a tuple, so the constructor never sees the forbidden input type. The current tests cover generator/set rejection only through direct constructor calls, not through the external `from_dict()` parsing boundary.

Required remediation:
- validate raw `context_refs` and `evidence_refs` are only the explicitly supported sequence types before iteration/conversion;
- then parse/copy/freeze them;
- add negative `from_dict()` tests for generator/set/arbitrary iterable inputs for both request context refs and result evidence refs.

### R1-3 — `PreparedExecution` is not mechanically bound to its `ExecutionRequest`
Severity: HIGH

`PreparedExecution` is intended to be the exact request-binding receipt used by the logical `ExecutorAdapter.prepare()` boundary. It contains `task_id`, `request_id`, `executor_id` and `request_fingerprint`, but its constructor validates only that `request_fingerprint` is syntactically a 64-hex value.

There is no relational validator/factory that proves a PreparedExecution belongs to the request it claims to represent. A record with the correct task/request/executor IDs but an arbitrary valid 64-hex fingerprint is currently a valid canonical PreparedExecution.

This fails TASK-028 C10 and the explicit adversarial checklist item:

```text
wrong request fingerprint rejected when validated/constructed
```

Required remediation:
- add a pure mechanical binding primitive such as:

```python
validate_prepared_execution_against_request(prepared, request) -> None
```

or an equivalently strict construction path that requires the source `ExecutionRequest`;
- require exact schema/task/request/executor identity and `prepared.request_fingerprint == request.fingerprint()`;
- keep it purely a binding receipt: no lease, authorization, transport or execution semantics;
- export the validator if it is part of the public M4 contract;
- add positive/negative tests, especially a syntactically valid but wrong 64-hex fingerprint.

### R1-4 — Invalid UTF-8 bytes leak raw decoding exceptions from M4 `from_json()` parsers
Severity: MEDIUM

All four M4 `from_json(bytes)` implementations decode bytes directly before the JSON parse try/except. Invalid UTF-8 therefore raises raw `UnicodeDecodeError` instead of `ContinuityStateValidationError`.

The established hardened Brain-neutral parser catches `UnicodeDecodeError` and wraps it as `ContinuityStateValidationError`; TASK-028 C14 explicitly says M4 must follow the hardened Continuity parsing conventions.

Required remediation:
- catch invalid UTF-8 in `ExecutionRequest`, `ExecutorCapabilities`, `PreparedExecution`, and `ExecutionResult` byte parsers;
- wrap it in bounded `ContinuityStateValidationError` without dumping raw payload bytes;
- add invalid-UTF-8 tests for all persisted/external M4 record parsers.

---

## Test / Evidence Status

RESULT-028 reports against `e69c06ae2ef2e9f74b9a4aaceaeda53a22c1bcea`:

```text
Focused M4 Executor: 20 passed
Continuity:          111 passed
AIOS Bridge:         197 passed
Full repository:     671 passed
Regressions:           0
EXECUTOR_RUNS:         1
EXECUTOR_FIX_RUNS:     0
PAID_EXTERNAL_API_CALLS: 0
```

The test suite is green, but the four findings above identify missing adversarial cases or semantic gaps not exercised by those tests.

## Scope for FIX

Expected FIX remains narrow:

```text
src/aios_bridge/continuity/executor.py
tests/aios_bridge/continuity/test_executor.py
src/aios_bridge/continuity/__init__.py   # only if new binding validator export is added
.ai/results/RESULT-028.md
```

Do not modify state.py, brain.py, failover.py, usage.py, Bridge, provider/runtime executor code, authorization, lease, failover, transport or dispatch semantics.

## Final Independent Audit

`NOT_RUN`.

ADR-017 requires known findings to close before the Final Independent Audit. Round 2 should be delta-first over R1-1 through R1-4. If all findings close, perform the mandatory fresh Final Independent Audit against the final M4 contract state before emitting `APPROVED`.

## Decision

`CHANGES_REQUIRED`
