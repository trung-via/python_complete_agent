# REVIEW-022 — TASK-022 M3A Brain Failover Contract & Proof Harness

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1`
- Reviewed branch: `ai/task-022`
- Reviewed branch head: `1631c8eb7376dc5db9976305c67e4fca9de189ab`
- Tested implementation SHA: `56d9b68cbeb25203d010600b264c859cbf134c18`
- Base main: `4978e426f3445c086c017c07c844943ac841e4de`
- Branch relation: ahead `2`, behind `0`; merge-base is exact current main.
- Implementation-to-reviewed-head relation: one evidence-only commit adds `.ai/results/RESULT-022.md`; production code/tests at reviewed head equal tested implementation.
- Review mode: ADR-013 delta-first. Reviewed RESULT/Review Manifest, compare metadata, implementation patch, targeted ADR-016/TASK-022 clauses, and finding-scoped tests only. No whole-repo/full-source reload.

## Positive Evidence
- Antigravity owned detailed implementation planning; no separate ChatGPT implementation PLAN was used.
- Scope is isolated to Continuity failover contract + tests + RESULT.
- Pure replacement request derivation preserves task/schema/operation/objective/context refs/output contract and rejects same-Brain pseudo-failover.
- Source SUCCESS duplicate-output blocking and source-result identity validation are implemented.
- Neutral fixture Brain IDs are used; no vendor routing/invocation exists.
- RESULT reports Continuity `60 passed`, Bridge `146 passed`, full repository `620 passed`, zero regressions.
- No live external calls, Bridge behavior change, authority widening, transcript/reasoning/secret persistence, or claim that real M3 cross-Brain proof is complete.

## Required Changes

### R1-1 — Canonical state fingerprint anchor is optional, but ADR-016 requires it to be supplied and verified

ADR-016 Decision 6 and TASK-022 Canonical State Anchor require failover proof to fail closed unless the caller/proof state fingerprint exactly equals `ContinuityState.fingerprint()`.

Current validator signature uses:

```python
expected_state_fingerprint: str | None = None
```

and only validates the fingerprint when it is provided. Therefore this succeeds without any externally supplied canonical-state anchor:

```python
validate_brain_failover_eligibility(src, rep, state)
```

The validator then computes `state.fingerprint()` itself and writes it into the proof. That proves internal self-consistency of the object passed to the function, but does not prove that the caller intended/authorized that exact canonical snapshot. A stale or different `ContinuityState` object can therefore become the proof anchor simply by omission.

Required fix:
- make caller-supplied expected/canonical state fingerprint mandatory for eligibility/proof creation;
- require exact lowercase SHA-256 validation and exact equality to `state.fingerprint()` on every successful path;
- no default that silently substitutes the current in-memory state's fingerprint;
- update all valid-path tests to supply the anchor explicitly;
- add/retain negative tests for missing, malformed, and stale/wrong fingerprint.

Do not add repository reads or Bridge integration; keep this pure.

### R1-2 — Replacement capability gate is optional, allowing eligibility without proving replacement capability

TASK-022 states that a replacement `BrainCapability` MUST belong to the replacement Brain and support the pending operation. ADR-016 defines this as the deterministic eligibility gate before a replacement request is considered eligible.

Current validator accepts:

```python
replacement_capability: BrainCapability | None = None
```

and skips the entire gate when omitted. Several valid-path tests intentionally call the validator with no capability and still receive a `BrainFailoverProof`.

That means a replacement Brain with unknown/unsupported capability can be declared eligible by omission, which defeats the capability-gated failover contract.

Required fix:
- require `replacement_capability` for eligibility/proof creation;
- fail closed when it is missing or not a `BrainCapability`;
- preserve existing checks that `brain_id` matches and operation is supported;
- keep capability descriptive-only; do not add ranking, routing, invocation, or fallback.

### R1-3 — Required source-result identity test matrix is incomplete

TASK-022 Required Test #14 explicitly requires wrong `task/request/brain/operation` source-result identities to be rejected.

The implementation contains checks for all four identities, but the focused test currently exercises only wrong `brain_id` and wrong `request_id`; there is no explicit wrong-`task_id` or wrong-`operation` test before the suite moves to state-anchor tests.

Required fix:
- add focused negative tests for source-result `task_id` mismatch and `operation` mismatch;
- no production-code change is required for R1-3 if existing checks already pass those tests.

## Required Re-Test

At minimum:

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## FIX Scope Guidance

Expected FIX should normally remain limited to:

```text
src/aios_bridge/continuity/failover.py
tests/aios_bridge/continuity/test_failover.py
.ai/results/RESULT-022.md
```

`src/aios_bridge/continuity/__init__.py` should not require change unless a public signature/export genuinely changes.

Do not modify `brain.py`, `state.py`, `bridge.py`, provider layers, routing/fallback, executor contracts, or RUN/FIX/MERGE authority.

## Round-2 Review Budget

Round 2 is finding-scoped only:
- this REVIEW;
- new RESULT/Review Manifest;
- `56d9b68... -> FIX implementation` delta;
- tests for mandatory state anchor, mandatory capability gate, and missing source-result mismatch cases.

No full TASK/ADR/unchanged source/test reload by default.

## Decision

`CHANGES_REQUIRED`

The M3A mechanics are structurally strong, but proof creation must not succeed by omitting either the canonical-state anchor or replacement capability gate. Close those fail-closed boundaries and complete the explicit identity-test matrix before merge.