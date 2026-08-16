# REVIEW-028 — TASK-028 Open Multi-Agent Continuity OS M4 Executor-Neutral Contract

STATUS: APPROVED

## Review Scope
- Review round: `2` — ADR-013 Delta Fix Review + ADR-017 Final Independent Audit
- Reviewed branch: `ai/task-028`
- Reviewed branch head: `de556e5065ab1aea08fc832d2541532fe7085e33`
- Tested implementation SHA reported by RESULT: `b398ca2978f2db117b05058c04e6dd324b9c17e9`
- Previous tested implementation: `e69c06ae2ef2e9f74b9a4aaceaeda53a22c1bcea`
- Previous REVIEW blob: `7d5d522db5b1c7088f12aae524b956298c97428a`
- Base/current main: `b4178d283d451054dca51964771053d9e0de2b5c`
- Branch relation: ahead `4`, behind `0`; merge-base exact current main.
- `b398ca2... -> de556e5...` changes only `.ai/results/RESULT-028.md`; production/test code at reviewed head equals tested implementation.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: PASS after remediation
KNOWN_FINDINGS: CLOSED
DELTA_FIX_REVIEW: PASS
FINAL_INDEPENDENT_AUDIT: PASS
APPROVED: YES
```

## Delta Fix Review

### R1-1 — Mutable / unrestricted `capacity_metadata`
Status: CLOSED

`capacity_metadata` was removed from the M4 ExecutorCapabilities schema. The capability record now contains only exact executor identity, closed supported operations/capabilities, and `declarative_only=True`. The schema rejects `capacity_metadata` as an unknown field, eliminating the mutable nested metadata/fingerprint drift and secret/vendor metadata channel identified in Round 1.

### R1-2 — `from_dict()` arbitrary iterable laundering
Status: CLOSED

External `from_dict()` boundaries now validate raw sequence types before conversion:
- ExecutionRequest context_refs / required_capabilities;
- ExecutorCapabilities supported_operations / supported_capabilities;
- ExecutionResult evidence_refs.

Only list/tuple are accepted; generator/set/arbitrary iterable inputs fail before parsing/canonicalization. Regression tests cover generator/set cases.

### R1-3 — PreparedExecution request binding
Status: CLOSED

A pure public validator now exists:

```python
validate_prepared_execution_against_request(prepared, request)
```

It mechanically requires exact schema version, task ID, request ID, executor ID, and `prepared.request_fingerprint == request.fingerprint()`. A syntactically valid but wrong 64-hex fingerprint fails closed. The receipt remains binding-only and gains no lease/authorization/transport semantics.

### R1-4 — Invalid UTF-8 bytes leak raw decode error
Status: CLOSED

All four M4 external `from_json(bytes)` parsers now catch UnicodeDecodeError and raise ContinuityStateValidationError. Regression tests cover ExecutionRequest, ExecutorCapabilities, PreparedExecution, and ExecutionResult.

## Final Independent Audit

The Final Independent Audit was performed as a fresh ADR-018/TASK-028 contract-to-final-code pass, not merely as confirmation of prior fixes.

### 1. Execution operation / authority boundary — PASS

ExecutionOperation remains exactly RUN/FIX. MERGE is not representable. ExecutionRequest is descriptive intent only; no approval, merge permission, credential or authorization field exists. Existing Human RUN/FIX/MERGE authority and Bridge v0.4 behavior are unchanged.

### 2. Canonical ExecutionRequest — PASS

ExecutionRequest is frozen, bounded, deterministic and fingerprintable. It binds exact task/request/executor identity, state fingerprint, task branch/head, content-addressed work_ref, ordered content-addressed context refs, required capabilities and exact RESULT path. RUN -> TASK and FIX -> REVIEW role binding is exact; task substring aliases fail closed.

### 3. Canonical state anchoring — PASS

`validate_execution_request_against_state()` is pure and checks exact task ID, state fingerprint, task branch, task-head SHA/null semantics, authoritative TASK/REVIEW identity and authoritative context ref/blob consistency. It performs no Git/filesystem/Bridge mutation.

### 4. ExecutorCapabilities / eligibility — PASS

ExecutorCapabilities is now an immutable closed declarative record. Supported operations/capabilities are duplicate-safe and canonically sorted. `validate_executor_eligibility()` is a pure eligibility primitive only: same executor identity, operation support and required-capability subset. No ranking, quota, invocation, fallback, lease or authorization behavior exists.

### 5. PreparedExecution — PASS

PreparedExecution remains a small request-binding receipt with no lease owner/expiry/generation, credentials, command body, transport secret or workspace snapshot. The new relational validator mechanically binds it to one exact ExecutionRequest fingerprint.

### 6. ExecutionResult / request binding — PASS

ExecutionResult preserves the stable-boundary payload matrix:
- SUCCESS requires exact implementation SHA + RESULT ArtifactRef and no error_code;
- FAILED/REJECTED/INCOMPLETE prohibit implementation_sha/result_ref and require bounded error_code;
- evidence refs are bounded/content-addressed/duplicate-safe.

`validate_execution_result_against_request()` requires exact schema/task/request/executor/operation identity and, on SUCCESS, exact expected RESULT path and target branch ref.

### 7. Adapter neutrality / portability — PASS

ExecutorAdapter remains a logical typing.Protocol with executor_id, capabilities(), prepare(), and collect_result(). There is no product/vendor branching, concrete Antigravity/Codex/Claude-Code adapter, ExecutionTransport or runtime invocation in M4. Three neutral test adapters (`executor-a`, `executor-b`, `executor-c`) conform without Continuity Core redesign.

### 8. Determinism / parsing / evidence hygiene — PASS

Canonical records use deterministic JSON + SHA-256 fingerprints, strict schemas, bounded record/input sizes, exact identity validators and strict sequence handling. Invalid UTF-8 is wrapped into the Continuity error domain. No transcript, hidden reasoning, raw source bodies, shell transcript, credentials or unrestricted vendor metadata is added to the canonical M4 records.

### 9. Scope / regression evidence — PASS

Production scope remains exactly the intended M4 boundary:

```text
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/__init__.py
```

with task-local tests and RESULT only. No state.py, brain.py, failover.py, usage.py, Bridge, provider/runtime executor, lease, failover, transport or dispatch changes are present.

RESULT reports against implementation `b398ca2978f2db117b05058c04e6dd324b9c17e9`:

```text
Focused M4 Executor: 23 passed
Continuity:          114 passed
AIOS Bridge:         200 passed
Full repository:     674 passed
Regressions:           0
EXECUTOR_RUNS:         1
EXECUTOR_FIX_RUNS:     1
PAID_EXTERNAL_API_CALLS: 0
```

## Known Findings Closure

```text
R1-1 CLOSED
R1-2 CLOSED
R1-3 CLOSED
R1-4 CLOSED
```

No new blocking finding was found by the Final Independent Audit.

## Decision

`APPROVED`

TASK-028 satisfies ADR-018 and the locked M4 Executor-Neutral Contract. M4 establishes the canonical vendor-neutral execution request/result/capability/adapter boundary required for later Executor milestones while preserving current authority and runtime semantics.

Approval grants merge eligibility only. Human MERGE authorization remains separate and mandatory.