# REVIEW-023 — TASK-023 Brain-Neutral Contract Hardening

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1` — ADR-017 Full Semantic Review
- Reviewed branch: `ai/task-023`
- Reviewed branch head: `2ec6004da6ccd5d62259df9e35d2ff01fa7e5359`
- Tested implementation SHA reported by RESULT: `096214349b7b50739f76e673ed7a7ae1eafb1f2e`
- Base main: `27b8abafe9466b52e8eccc8dd68b4b5306a1fe78`
- Branch relation: ahead `2`, behind `0`; merge-base exact current main.
- `27b8aba... -> 0962143...` changes only `brain.py`, `test_brain.py`, and `test_failover.py`.
- `0962143... -> 2ec6004...` changes only `.ai/results/RESULT-023.md`; production code/tests at final branch head equal tested implementation.
- Review mode: ADR-017 first-review Full Semantic Review of the complete Brain-contract boundary plus coupled M3A regression boundary.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository test suite.

## Semantic Review Result

TASK-023 substantially improves the M2 contract and closes much of P21-1/P21-3, but the implementation does not yet satisfy C3, C4, and C6 completely. New pointer canonicalization ambiguity was also found while reviewing the full boundary.

## Blocking Findings

### R1-1 — C3 leading-zero/case aliases remain in task-token and REVIEW artifact identity
Severity: HIGH

`_validate_task_token_in_path()` converts both active task digits and path task tokens with `int()`. This collapses distinct valid task IDs such as `TASK-021`, `TASK-21`, and `TASK-0021` onto the same numeric value. The regex is also compiled with `re.IGNORECASE`, so lowercase `task-021` is accepted as a task token even though canonical task identity is case-sensitive.

The tests explicitly treat `.ai/plans/TASK-21-ARCHITECTURE-PLAN.md` as valid for active `TASK-021`, which directly contradicts TASK-023 C3: different task IDs must not alias the same artifact identity.

`REVIEW_ARTIFACT` has the same alias problem: for an active task it accepts `expected_standard`, `expected_exact`, and `expected_short`. As a result, `TASK-021` and `TASK-21` can both accept `.ai/reviews/REVIEW-021.md` under different aliases.

Required fix:
- define one exact, case-sensitive task-token identity rule;
- do not compare task tokens by integer equivalence;
- a role path token must match the active task identity according to one non-aliasing canonical convention;
- remove review-path aliases that permit two distinct valid task IDs to resolve to the same REVIEW artifact path;
- add regression tests for `TASK-021` vs `TASK-21`, `TASK-0021`, lowercase `task-021`, and canonical REVIEW path uniqueness.

### R1-2 — C4 BOUNDED_TEXT evidence_ref is not validated for active task / output-role consistency
Severity: HIGH

`BrainResult` validates an `evidence_ref` only for:
- type `ContextRef`;
- canonical/safe path;
- `output_type == BOUNDED_TEXT`.

It does not validate that the evidence pointer belongs to the active `task_id`, and it does not constrain the pointer to an operation-appropriate evidence namespace.

Therefore a `BrainResult(task_id="TASK-021", operation=DIAGNOSIS, output_type=BOUNDED_TEXT, ...)` can point at a canonical path carrying another task identity such as `.ai/context/TASK-099-DIAGNOSIS.md` and still pass. It can also use an unrelated AIOS role path as the BOUNDED_TEXT evidence pointer if that path is otherwise safe.

This violates C4: every BrainResult pointer present must be validated for task/output-role consistency regardless of status.

Required fix:
- add explicit BOUNDED_TEXT evidence-pointer validation;
- require exact active-task identity under the same non-aliasing C3 rule;
- constrain evidence-pointer namespaces according to the operation (`DIAGNOSIS` / `PATCH_PROPOSAL`) or another equally strict deterministic rule justified by the existing contract;
- apply the rule regardless of SUCCESS/FAILED/REJECTED/INCOMPLETE when an evidence pointer is present;
- add wrong-task, wrong-role, and valid positive tests.

### R1-3 — C6 max_context_bytes still lacks an explicit semantic upper bound
Severity: MEDIUM

`BrainCapability` now rejects duplicate operations and has a 16 KiB serialized-record cap, but `max_context_bytes` is still validated only as a non-negative integer. No explicit maximum capacity value is defined.

TASK-023 C6 explicitly requires descriptive numeric capacity metadata to be finite/non-negative **and bounded by an explicit deterministic rule**. A record-size cap bounds the number of decimal digits, not the semantic capacity value itself.

The required adversarial checklist case for oversized/unbounded capability metadata is also absent from `test_brain.py`.

Required fix:
- define an explicit deterministic upper bound for `max_context_bytes` appropriate to this descriptive contract;
- reject values above it fail-closed;
- retain `None` if it represents unknown/unspecified capacity;
- add boundary tests for max accepted, max+1 rejected, negative/bool rejected, and duplicate operation behavior.

### R1-4 — New full-boundary finding: ArtifactRef.ref can remain non-canonical inside BrainResult
Severity: MEDIUM

TASK-023 hardens Brain-owned AIOS paths but a successful artifact payload still contains a shared `ArtifactRef.ref`. The shared Git-ref validator validates a stripped representation and returns the canonical string, while `ArtifactRef` retains the raw `ref`. `BrainResult` does not add an exact-canonical check for that ref.

Thus logically equivalent values such as `"task"` and `" task "` can survive as different serialized/fingerprinted BrainResult pointer metadata even though the latter is accepted only after trimming by the shared validator.

This is inconsistent with TASK-023's objective that Brain pointer records be strict and deterministic and repeats the same representational ambiguity fixed for brain_id/request_id/path.

Required fix:
- at the BrainResult artifact-pointer boundary, require `ArtifactRef.ref` to equal the canonical value returned by the shared safe-Git-ref validator, or use an equivalent exact-canonical helper;
- do not mutate the generic Continuity State contract in this task;
- add padded-ref rejection and canonical-ref round-trip/fingerprint regression tests.

## Positive Evidence

The Full Semantic Review confirms the following improvements are correct:
- exact Brain/request ID padding rejection is now enforced in BrainRequest, BrainResult, and BrainCapability;
- ContextRef and OutputContract paths are exact-canonical at the M2 Brain boundary;
- BOUNDED_TEXT request targets are forced to `None`;
- SUCCESS result payload exclusivity and `SUCCESS + error_code` contradiction are rejected;
- artifact pointers are role/task checked independent of SUCCESS when present;
- duplicate BrainCapability operations are rejected;
- TASK-022 failover production code was not changed; adjusted tests preserve the M3A defense-in-depth boundary;
- no Bridge/provider/router/executor/authority behavior was introduced.

RESULT reports against implementation `096214349b7b50739f76e673ed7a7ae1eafb1f2e`:

```text
Continuity: 64 passed
AIOS Bridge: 150 passed
Full repository: 624 passed
Regressions: 0
LIVE_EXTERNAL_CALLS: 0
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 0
```

## Required FIX Scope

Expected production change should remain bounded to:

```text
src/aios_bridge/continuity/brain.py
tests/aios_bridge/continuity/test_brain.py
tests/aios_bridge/continuity/test_failover.py   # only if coupled compatibility tests need adjustment
.ai/results/RESULT-023.md
```

Do not modify `state.py`, Bridge, provider layers, executor authority, or M3A production failover semantics unless a new conflict is discovered and escalated before editing.

## Required Re-Test

```text
pytest tests/aios_bridge/continuity/test_brain.py -q
pytest tests/aios_bridge/continuity/test_failover.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## ADR-017 Stage Status

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
FINAL_INDEPENDENT_AUDIT: NOT_RUN
```

Final Independent Audit must not run for approval until these findings are closed. After the FIX delta review passes, perform a fresh Final Independent Audit against the final tested implementation before emitting APPROVED.

## Decision

`CHANGES_REQUIRED`
