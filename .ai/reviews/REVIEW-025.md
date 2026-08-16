# REVIEW-025 — TASK-025 Canonical Project State Identity & Freshness Hardening

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1` — ADR-017 Full Semantic Review
- Reviewed branch: `ai/task-025`
- Reviewed branch head: `13c916a01c988325f693ec106e8060d43cd3c875`
- Tested implementation SHA reported by RESULT: `6c6007c5592c6eecde4aad6a7a061c64bb63be9a`
- Base main: `47dbde428169bb003d010b9ded79c9528bb40fba`
- Branch relation: ahead `2`, behind `0`; merge-base exact current main.
- `6c6007c... -> 13c916a...` changes only `.ai/results/RESULT-025.md`; production code/tests at reviewed head equal the tested implementation.
- Review mode: Full Semantic Review of TASK-025 Contract + Architecture Implementation Plan + Adversarial Checklist, complete Canonical State changed boundary, coupled TASK-022 failover assumptions, tests, RESULT and SHA relation.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository test suite.

## Semantic Review Result

P19-2 through P19-5 are substantively closed and the whitespace form of P19-1 is fixed. However exact-canonical artifact-path identity remains incomplete because POSIX dot-segment aliases are still accepted. In addition, TASK-022's failover collision defense remains in production but its direct regression proof was weakened by replacing the failover-gate test with only a state-constructor rejection.

## Blocking Findings

### R1-1 — Artifact paths still admit POSIX `.` segment aliases
Severity: HIGH

TASK-025 C1 requires persisted state identities to be exact-canonical and C2 requires authoritative artifact paths to be globally unambiguous.

The hardened `_validate_artifact_path()` now correctly rejects leading/trailing whitespace, backslashes, absolute paths, empty segments and `..` traversal. It does **not** reject a path component equal to `.`.

Therefore both of these can pass the generic ArtifactRef path validator:

```text
.ai/context/TASK-025-PLAN.md
.ai/context/./TASK-025-PLAN.md
```

For repository/POSIX resolution these are aliases of the same location, but Canonical State persists them as different strings. Consequences:
- semantically equivalent artifact identities can serialize/fingerprint differently;
- global `seen_paths` uniqueness compares raw strings and can therefore be bypassed by dot-segment aliases;
- freshness observations are keyed by the persisted string, creating representational ambiguity around one underlying repo path;
- P19-1 / C1 is therefore not fully closed.

Required fix:
- reject every artifact path segment exactly equal to `.` in `_validate_artifact_path()`;
- do not silently normalize/remove dot segments; fail closed so external identity remains exact-canonical;
- preserve already-canonical state serialization/fingerprints;
- add regression tests showing canonical path passes, `.ai/./...`, `.ai/context/./...` and equivalent embedded dot-segment forms fail;
- add a collision-oriented test proving a dot-segment alias cannot bypass C2 global path uniqueness because it is rejected at ArtifactRef construction.

Do not broaden this FIX into generic filesystem normalization or I/O.

### R1-2 — TASK-022 failover collision defense is no longer directly regression-tested
Severity: MEDIUM — assurance/evidence integrity

TASK-025 correctly moves duplicate authoritative path rejection earlier into `ContinuityArtifacts`. Production `failover.py` still retains its independent `_validate_context_refs_content_anchored()` state-artifact collision check as defense in depth, which is good.

However the TASK-025 delta removes the previous direct test path that constructed a collision state and then asserted `validate_brain_failover_eligibility(...)` failed with the failover-layer `Ambiguous state artifact path collision...` error. The replacement tests stop at `ContinuityArtifacts(...)` construction and therefore prove only the new Canonical State gate, not the retained TASK-022 defense-in-depth gate itself.

This weakens the meaning of `TASK_022_FAILOVER_REGRESSION: PASS`: the failover suite is green, but one of the specific TASK-022 proof obligations is no longer directly exercised.

Required fix:
- keep the new Canonical State collision tests;
- restore a bounded test-only proof that the independent failover collision defense still rejects a malformed/collision-bearing state if such an object reaches the failover boundary;
- use a test-only crafted malformed state fixture or equivalent isolated mechanism; do not weaken production constructors or add a production bypass;
- verify both same-blob and different-blob path collisions if practical, or at minimum one direct collision rejection plus preservation of state-fingerprint anchoring tests.

No production change to `failover.py` is required unless a genuine defect is discovered while restoring coverage.

## Positive Evidence

The Full Semantic Review confirms these TASK-025 changes are substantially correct:
- padded BranchState refs, ArtifactRef refs/paths and Brain/Executor actor IDs now fail closed;
- global authoritative path uniqueness is enforced across task/contracts/plan/result/review for exact path strings;
- `StateObservation` can be constructed with omitted artifact observations;
- caller-provided artifact observation mappings are defensively copied and wrapped in `MappingProxyType`;
- caller mutation after construction cannot change observation facts;
- invalid Brain operation parsing is wrapped in `ContinuityStateValidationError`;
- schema version remains `1` and `MAX_SERIALIZED_BYTES` remains `16384`;
- exact TASK/RESULT/REVIEW role naming and phase rules remain intact;
- `state.py` is the only production file changed;
- `brain.py`, `usage.py`, `failover.py`, Bridge, providers and executor production files are unchanged;
- TASK-022 failover collision defense remains present in production code;
- no authority widening or live external call is reported.

RESULT reports against implementation `6c6007c5592c6eecde4aad6a7a061c64bb63be9a`:

```text
Continuity: 76 passed
AIOS Bridge: 162 passed
Full repository: 636 passed
Regressions: 0
LIVE_EXTERNAL_CALLS: 0
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 0
CANONICAL_STATE_COMPATIBLE: YES
TASK_022_FAILOVER_REGRESSION: PASS
```

## Required FIX Scope

Expected delta should remain bounded to:

```text
src/aios_bridge/continuity/state.py
tests/aios_bridge/continuity/test_state.py
tests/aios_bridge/continuity/test_failover.py
.ai/results/RESULT-025.md
```

Do not change `brain.py`, `usage.py`, `failover.py` production, Bridge, provider, executor, schema version, state publication or authority semantics.

## Required Re-Test

```text
pytest tests/aios_bridge/continuity/test_state.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## ADR-017 Stage Status

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: NOT_RUN
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

Final Independent Audit must not be used for approval until R1-1 and R1-2 are closed. After the FIX delta passes, perform a fresh Final Independent Audit against the final tested Canonical State implementation and coupled M2/M3 failover assumptions before emitting APPROVED.

## Decision

`CHANGES_REQUIRED`
