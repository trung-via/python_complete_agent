# REVIEW-022 — TASK-022 M3A Brain Failover Contract & Proof Harness

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `6` — SECOND FULL RE-AUDIT requested by human
- Reviewed branch: `ai/task-022`
- Reviewed branch head: `fcec3e8bb2bfe826e231849b77afd115a6d6e016`
- Tested implementation SHA reported by RESULT: `f3480d46b40507f0f76b015a8c4d9113455b2fe6`
- Base main: `4978e426f3445c086c017c07c844943ac841e4de`
- Branch relation: ahead `8`, behind `0`; merge-base is exact current main.
- Review mode: independent full audit. Re-read TASK-022, ADR-016, relevant ADR-010 continuity requirement, complete `failover.py`, complete `test_failover.py`, M2 `BrainRequest`/`ContextRef`/`BrainResult`/`BrainCapability`, Continuity artifact/state/fingerprint contracts, RESULT, current REVIEW, and branch compare.
- This review does not rely on Round-5 APPROVED.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the repository test suite.

## Findings Rechecked

The following previously identified boundaries remain correctly closed:
- mandatory caller-supplied state fingerprint;
- mandatory replacement capability gate;
- canonical Brain IDs / same-Brain whitespace bypass;
- exact proof fingerprints;
- canonical proof request IDs;
- semantic drift across task/operation/objective/context tuple/output contract/schema;
- source-result task/request/brain/operation identity checks;
- SUCCESS source-result duplicate-output blocking;
- strict unknown proof fields;
- deterministic proof serialization/fingerprinting;
- Continuity 16 KiB bound;
- zero provider/Bridge/router/authority side effects.

## New Blocking Finding

### R6-1 — Context references are not content-anchored to the canonical state snapshot

M3A exists to prove that Brain B reconstructs the same pending operation from the exact canonical inputs used by Brain A. ADR-016 requires the replacement request to preserve the ordered bounded context refs **and their blob identities**, while the failover proof is anchored to an exact `ContinuityState.fingerprint()`.

The current validator checks only:

```python
source_request.context_refs == replacement_request.context_refs
```

and separately checks the state fingerprint. It never validates that the request context refs are content-consistent with the authoritative artifacts inside that state snapshot.

M2 intentionally allows:

```python
ContextRef(blob_sha=None)
```

which is acceptable for the generic Brain-neutral navigation contract. But M3 failover needs a stronger boundary because continuity requires reproducible input bytes.

The TASK-022 test fixture currently demonstrates the gap directly:
- `ContinuityState.artifacts.task` anchors `.ai/tasks/TASK-022.md` to blob `92494bcd...`;
- the supposedly valid source `BrainRequest` also references `.ai/tasks/TASK-022.md` but sets `blob_sha=None`;
- the failover validator accepts this and produces a proof.

The same validator would also accept a context ref for the canonical task path carrying a **different** syntactically-valid blob SHA, as long as source and replacement requests carry the same wrong value.

It can additionally accept an arbitrary AIOS context path that is not represented in `ContinuityState.artifacts` and has no blob identity at all.

Therefore the proof currently establishes equality of two metadata objects, but not equality of the bytes a replacement Brain would reconstruct. Between Brain A and Brain B, a path-only context ref can resolve to changed content while all existing M3A validation still passes.

This violates the core M3 continuity invariant:

```text
same canonical snapshot + same canonical task semantics
```

and the ADR-010 requirement that a replacement Brain reconstruct context from canonical artifacts rather than mutable chat/session state.

### Required fix

Keep the fix pure and local to the M3A failover boundary. Do NOT change the generic M2 `ContextRef` contract unless separately necessary.

Add deterministic context anchoring validation equivalent to:

1. Build an authoritative `path -> blob_sha` view from the supplied `ContinuityState.artifacts` (`task`, `contracts`, and any present `plan/result/review`).
2. For every source/replacement context ref, preserve current exact ordered equality requirement.
3. Every context ref used for failover MUST be content-addressed:
   - if its path matches an authoritative state artifact, its `blob_sha` MUST be present and exactly equal to that state's artifact blob;
   - if its path is not represented in state artifacts, its own `blob_sha` MUST be present so the context remains content-addressed independently.
4. Missing blob identity at the failover boundary MUST fail closed.
5. A context ref using the same path as a state artifact but a different blob MUST fail closed.
6. Prefer also requiring the raw context path to equal the existing artifact-path validator's canonical return, so padded/non-canonical path representations cannot enter a proof.
7. No filesystem/Git/network lookup is needed or allowed; metadata comparison is sufficient.

### Required regression tests

At minimum add:

```text
- canonical task ContextRef with exact state task blob -> allowed
- canonical task ContextRef with blob_sha=None -> rejected
- canonical task ContextRef with wrong 40-char blob -> rejected
- non-state ContextRef with blob_sha=None -> rejected
- non-state ContextRef with explicit valid blob -> allowed
- source/replacement ordered ContextRef equality remains enforced
- state fingerprint behavior remains unchanged
```

Update the current valid fixture so the task ContextRef carries the exact task blob from the state snapshot.

## Why this is blocking

M3A is specifically a continuity proof, not merely a request-copy helper. If context bytes are not bound to either the canonical state artifact blob or an explicit context-ref blob, two Brains can receive different effective inputs while the proof says the failover is semantically equivalent. That defeats the central objective of TASK-022.

## Positive Evidence

The remainder of the implementation remains strong:
- pure replacement request derivation;
- mandatory state fingerprint and capability gates;
- canonical identity hardening from Round 4;
- strict bounded proof schema;
- no transcript/reasoning/secrets/authority fields in the proof;
- no Brain/provider invocation, router/fallback, Bridge mutation, Git mutation, or authority widening;
- branch scope remains RESULT + Continuity failover/export/tests only;
- M3B remains explicitly incomplete.

RESULT currently reports:

```text
Continuity: 62 passed
AIOS Bridge: 148 passed
Full repository: 622 passed
Regressions: 0
LIVE_EXTERNAL_CALLS: 0
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
M3_REAL_CROSS_BRAIN_PROOF_COMPLETE: NO
```

## FIX Scope Guidance

Expected fix should normally remain limited to:

```text
src/aios_bridge/continuity/failover.py
tests/aios_bridge/continuity/test_failover.py
.ai/results/RESULT-022.md
```

`__init__.py` should not require modification unless a public helper is intentionally exported.

Do NOT change Bridge lifecycle/authorization, state lifecycle, provider layers, router/fallback, Executor contracts, or RUN/FIX/MERGE authority.

## Required Re-Test

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## Next Review Budget

Round 7 may return to delta-first and inspect only:
- this Round-6 REVIEW;
- new RESULT;
- context-anchor implementation delta;
- new context-ref regression tests;
- SHA/branch relation.

## Decision

`CHANGES_REQUIRED`

Round-5 APPROVED is superseded by this second human-requested full re-audit. TASK-022 must not be merged until every failover context ref is deterministically bound to exact content under the canonical state snapshot or its own explicit blob identity, and all required suites remain green.