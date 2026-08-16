# REVIEW-022 — TASK-022 M3A Brain Failover Contract & Proof Harness

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `2`
- Reviewed branch: `ai/task-022`
- Reviewed branch head: `9d558a2ca98ebc892e43a0ea2f985f050a1f1a60`
- Tested implementation SHA: `92696e61782839a25aa8c0223e79904090590bfe`
- Previous tested implementation SHA: `56d9b68cbeb25203d010600b264c859cbf134c18`
- Base main: `4978e426f3445c086c017c07c844943ac841e4de`
- Branch relation: ahead `4`, behind `0`; merge-base is exact current main.
- Implementation-to-reviewed-head relation: one evidence-only RESULT update after `92696e6...`; production code/tests at reviewed head equal tested implementation.
- Review mode: ADR-013 finding-scoped delta-first. Reviewed previous REVIEW, new RESULT, `56d9b68... -> 92696e6...` FIX delta, targeted tests, and SHA relations only. No full TASK/ADR/source/test reload.

## Finding Closure

### R1-1 — Mandatory canonical-state fingerprint anchor
SUBSTANTIVELY RESOLVED; one explicit boundary test remains.

Production contract is correct:
- `expected_state_fingerprint` is now a required function argument;
- it is validated as exact lowercase 64-char SHA-256;
- it must equal `ContinuityState.fingerprint()` on every successful path;
- there is no default that silently substitutes the in-memory state fingerprint.

Focused tests prove valid, malformed, mismatched/stale fingerprint behavior and task-state mismatch.

Remaining evidence gap:
- Round-1 explicitly required a negative test for a **missing/omitted** fingerprint;
- RESULT claims missing/malformed/mismatched fingerprint tests were added;
- current test suite does not actually call the validator while omitting `expected_state_fingerprint`.

Because the parameter is now required by the Python signature, omission currently fails closed with `TypeError`, which is acceptable behavior for this API boundary. The missing item is proof/test evidence, not production logic.

Required final fix:
- add one focused test proving omission of `expected_state_fingerprint` cannot create a proof (a `TypeError` caused by the required argument is acceptable; alternatively a bounded domain validation path is acceptable if implementation deliberately chooses one);
- do not relax the mandatory argument or add a default.

### R1-2 — Mandatory replacement capability gate
RESOLVED.

- `replacement_capability` is now mandatory;
- explicit `None`/invalid type fails closed;
- Brain identity and operation support remain enforced;
- gate remains declarative-only and introduces no routing/invocation/fallback.

### R1-3 — Complete source-result identity test matrix
RESOLVED.

Focused negative tests now cover all required identity mismatches:
- task_id;
- request_id;
- brain_id;
- operation.

## Evidence
- FIX implementation commit: `92696e61782839a25aa8c0223e79904090590bfe`.
- Final reviewed head: `9d558a2ca98ebc892e43a0ea2f985f050a1f1a60`.
- `92696e6... -> 9d558a2...` changes only `.ai/results/RESULT-022.md`; production code/tests at final head equal the tested implementation.
- RESULT reports Continuity `60 passed`, Bridge `146 passed`, full repository `620 passed`, zero regressions.
- `LIVE_EXTERNAL_CALLS: 0`.
- `BRIDGE_V0_4_BEHAVIOR_CHANGED: NO`.
- `AUTHORITY_WIDENED: NO`.
- `M3_REAL_CROSS_BRAIN_PROOF_COMPLETE: NO` remains correctly stated.

## Final FIX Scope
Expected final delta should normally be limited to:

```text
tests/aios_bridge/continuity/test_failover.py
.ai/results/RESULT-022.md
```

No production-code change is required unless the missing-fingerprint test exposes an unexpected issue.

Do not modify Brain/state contracts, Bridge, providers, routing/fallback, executor contracts, or authority semantics.

## Round-3 Review Budget
Round 3 should inspect only:
- this REVIEW;
- new RESULT;
- tiny test delta;
- test evidence / SHA relation.

## Decision

`CHANGES_REQUIRED`

The M3A production contract now satisfies the substantive fail-closed requirements. Add the single omitted-fingerprint boundary test promised by Round 1/RESULT, rerun required suites, and this should be ready for final approval.