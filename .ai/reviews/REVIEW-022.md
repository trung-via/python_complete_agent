# REVIEW-022 — TASK-022 M3A Brain Failover Contract & Proof Harness

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `7` — finding-scoped delta review after Round-6 full re-audit
- Reviewed branch: `ai/task-022`
- Reviewed branch head: `ab489a0c281a98dd62b96f0b57ee1e1752c45556`
- Tested implementation SHA reported by RESULT: `b1cb97d41f40f26bdfb8faa3ddd048838da6e9b0`
- Previous reviewed head: `fcec3e8bb2bfe826e231849b77afd115a6d6e016`
- Base main: `4978e426f3445c086c017c07c844943ac841e4de`
- Branch relation: ahead `10`, behind `0`; merge-base exact current main.
- `fcec3e8... -> b1cb97d...` changes only `src/aios_bridge/continuity/failover.py` and `tests/aios_bridge/continuity/test_failover.py` for R6-1.
- `b1cb97d... -> ab489a0...` changes only `.ai/results/RESULT-022.md`; production code/tests at final head equal the tested implementation.
- Review mode: ADR-013 delta-first restricted to Round-6 finding, new RESULT, implementation/test delta, and SHA relation.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository test suite.

## Round-6 Finding Closure

### R6-1 — Context references content-anchored to canonical state snapshot
PARTIALLY RESOLVED; normal-path behavior is correct, but one fail-closed edge remains.

The fix correctly adds `_validate_context_refs_content_anchored()` and now:
- requires every failover ContextRef to carry a non-null exact 40-char lowercase blob SHA;
- rejects leading/trailing whitespace in ContextRef paths;
- compares a context ref against the matching state artifact blob when the path is present in state artifacts;
- permits non-state ContextRefs only when they are independently content-addressed by explicit blob SHA;
- updates the valid task ContextRef fixture to use the exact state task blob;
- preserves the existing ordered source/replacement ContextRef equality requirement.

Regression coverage now includes valid exact anchoring, missing task blob, wrong task blob, missing non-state blob, padded path rejection, and the existing semantic-drift checks.

## New Blocking Finding

### R7-1 — Authoritative state artifact path collisions can silently overwrite blob identity in the failover anchor map

The new helper builds an authoritative map as a plain dictionary:

```python
state_artifact_blobs = {state_artifacts.task.path: state_artifacts.task.blob_sha}
...
state_artifact_blobs[contract.path] = contract.blob_sha
```

This assumes every authoritative artifact path is globally unique across `task`, `contracts`, `plan`, `result`, and `review`.

The current Continuity state contract does not guarantee that assumption. `ContinuityArtifacts` rejects duplicate paths only *within* the `contracts` tuple. It does not reject a contract path that equals the task path, nor a plan path that collides with task/contract paths. `ContinuityState` gives task/result/review some role-specific checks, but there is no global cross-role artifact-path uniqueness rule.

Therefore a syntactically valid state can contain, for example:

```text
artifacts.task:
  path = .ai/tasks/TASK-022.md
  blob = A

artifacts.contracts[0]:
  path = .ai/tasks/TASK-022.md
  blob = B
```

When the failover helper builds its dict, blob `B` silently overwrites blob `A`. A ContextRef for `.ai/tasks/TASK-022.md` carrying blob `B` can then pass the new anchor check even though it conflicts with the canonical task artifact in the same state snapshot.

This violates the R6 requirement that a context path matching an authoritative state artifact must match that artifact's content identity, and it weakens the fail-closed continuity proof.

### Required fix

Keep the fix local to TASK-022/failover validation; do not widen into a ContinuityState migration.

While constructing the authoritative path/blob view:
- detect a repeated authoritative path before assignment;
- if the same path is already present, fail closed on ambiguity rather than silently overwriting;
- rejecting all cross-role duplicate paths is the simplest/safest policy; alternatively, at minimum reject duplicates whose blob SHA differs;
- do not mutate `ContinuityState` or its lifecycle contract in this task.

### Required regression tests

At minimum add:

```text
- state task path duplicated by a contract with a different blob -> fail closed
- state task path duplicated by plan/another authoritative role -> fail closed (or one representative cross-role collision if helper policy is generic)
- normal unique-path state continues to pass
```

The test should prove failure occurs in the failover context-anchor boundary, not from unrelated state construction validation.

## Positive Evidence

All earlier boundaries remain intact in the reviewed delta:
- canonical Brain/request IDs and same-Brain rejection;
- exact state/request fingerprints;
- mandatory caller state fingerprint and replacement capability;
- source-result identity checks and SUCCESS duplicate-output blocking;
- semantic drift rejection;
- strict bounded proof schema;
- no transcript/reasoning/secrets/authority fields;
- no provider/router/Bridge/Git/model side effects;
- M3B remains explicitly incomplete.

RESULT reports against `b1cb97d41f40f26bdfb8faa3ddd048838da6e9b0`:

```text
Continuity: 63 passed
AIOS Bridge: 149 passed
Full repository: 623 passed
Regressions: 0
LIVE_EXTERNAL_CALLS: 0
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
M3_REAL_CROSS_BRAIN_PROOF_COMPLETE: NO
```

## FIX Scope Guidance

Expected change remains tiny:

```text
src/aios_bridge/continuity/failover.py
tests/aios_bridge/continuity/test_failover.py
.ai/results/RESULT-022.md
```

No Bridge/provider/state-lifecycle/router/executor/authority changes.

## Required Re-Test

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## Next Review Budget

Round 8 should inspect only:
- this Round-7 REVIEW;
- new RESULT;
- authoritative-artifact collision delta and regression test;
- SHA/branch relation.

## Decision

`CHANGES_REQUIRED`

R6-1 is substantially fixed, but TASK-022 must not be merged until ambiguous/colliding authoritative artifact paths fail closed instead of being silently overwritten in the state artifact blob map.