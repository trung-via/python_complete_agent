# TASK-019 — Post-Merge Independent Audit

STATUS: FINDINGS_REQUIRE_REMEDIATION

## Audit Basis

Retrospective Full Semantic Review + Final Independent Audit under ADR-017.

TASK-019 remains historically MERGED. This audit does not rewrite REVIEW-019 or merge history.

Reviewed boundary:
- `.ai/tasks/TASK-019.md`
- ADR-011 Canonical Project State Contract
- `.ai/results/RESULT-019.md`
- historical `.ai/reviews/REVIEW-019.md`
- `src/aios_bridge/continuity/state.py`
- `tests/aios_bridge/continuity/test_state.py`
- coupled M2/M3A assumptions that consume Continuity State

Historical merged head:

```text
5484462208dd47b9fbb3fd5ad382f423301c468a
```

Current `state.py` still carries the M1 representation/freshness behaviors audited below.

---

## P19-1 — Core state identifiers validate canonicalized values but persist raw representations

Severity: HIGH

Several shared validators strip surrounding whitespace and return a canonical value, but M1 dataclasses do not store that returned value or require raw input to equal it:

- `BranchState.branch` -> `_validate_safe_git_ref()`;
- `ArtifactRef.path` -> `_validate_artifact_path()`;
- `ArtifactRef.ref` -> `_validate_safe_git_ref()`;
- `BrainState.last_id` -> `_validate_actor_id()`;
- `ExecutorState.last_id` -> `_validate_actor_id()`.

Consequences:
- values such as `" main "`, `" ai-control "`, padded contract/plan paths, or padded actor IDs can validate against a stripped form while remaining raw in the frozen object;
- serialization/fingerprint can therefore encode a representation that is not itself the validated safe Git ref/path/actor identity;
- semantically equivalent raw/canonical inputs can produce different fingerprints;
- task/result/review exact-role path checks happen to reject padded role paths later, but contracts/plan paths and all Git refs/actor IDs remain exposed to the ambiguity.

This violates ADR-011 safe-ref/path semantics and the deterministic semantic-fingerprint goal.

Required remediation:
- state-boundary identities must be exact-canonical;
- prefer fail-closed `raw == canonical_return` for external input rather than silently rewriting it;
- apply consistently to BranchState, ArtifactRef, BrainState and ExecutorState;
- preserve already-canonical current artifacts/states.

---

## P19-2 — Cross-role authoritative artifact path collisions are allowed

Severity: HIGH

`ContinuityArtifacts` rejects duplicate paths only inside `contracts`. It does not reject a contract path colliding with `task`, `plan`, `result`, or `review`, nor collisions among those roles where namespace rules do not already make them impossible.

This creates an internally ambiguous canonical state because freshness observations are keyed only by `artifact.path`:

```text
observation.artifact_blobs[path] -> one blob SHA
```

If two authoritative pointers reuse one path with different blob/ref identities, a single explicit observation cannot represent both identities. Even same-blob duplicate roles make role ownership ambiguous.

TASK-022 later added defense-in-depth rejection of all duplicate authoritative state paths at the failover boundary; the canonical state contract itself should not emit such ambiguous state.

Required remediation:
- collect task + contracts + optional plan/result/review and reject every duplicate authoritative path across roles;
- fail closed regardless of whether duplicate paths point to the same or different blob/ref;
- keep existing within-contract duplicate protection;
- do not change TASK-022 failover semantics; its check may remain defense in depth.

---

## P19-3 — StateObservation default cannot represent omitted artifact observations

Severity: MEDIUM

`StateObservation.artifact_blobs` is declared with default `()`, but `__post_init__()` requires a `Mapping`.

Therefore a caller constructing an otherwise valid observation while omitting artifact observations can fail during observation construction instead of reaching `check_freshness()` and receiving the contractually meaningful `INCOMPLETE` result.

Required remediation:
- use a valid empty observation mapping default or an equivalent explicit `None -> empty immutable mapping` rule;
- absence of observed artifact blobs must be representable and should lead to `INCOMPLETE` when the state contains artifacts and no mismatches are known;
- no implicit filesystem/Git/network discovery.

---

## P19-4 — StateObservation is not deeply immutable

Severity: MEDIUM

`StateObservation` is a frozen dataclass, but a caller-supplied mutable dict is stored directly as `artifact_blobs`. The dict can be changed after construction, changing freshness results for the same observation object.

That contradicts the observation's own immutable-fact semantics and weakens deterministic freshness evidence.

Required remediation:
- validate, copy, and freeze artifact observations at construction;
- do not retain caller-owned mutable mapping state;
- preserve deterministic key/value semantics and exact lowercase blob SHA validation.

---

## P19-5 — BrainState parser can leak raw enum ValueError

Severity: MEDIUM

`BrainState.from_dict()` constructs `BrainOperation(...)` before entering `BrainState.__post_init__()`. An unknown operation therefore raises raw `ValueError` instead of the Continuity validation error domain used by the rest of the strict parser.

Required remediation:
- route raw parsed operation through the dataclass validator or wrap enum conversion;
- invalid operation must fail deterministically with `ContinuityStateValidationError`;
- keep the same bounded BrainOperation enum.

---

## Positive Findings

The audit reconfirms that M1 correctly established:
- separate Bridge Runtime State vs shared Continuity State;
- exact schema version and phase/next-operation mapping;
- exact lowercase 40-hex commit/blob validation;
- canonical TASK/RESULT/REVIEW role paths;
- sensitive `.ai/` path rejection;
- task-branch SHA requirement from RUNNING onward;
- phase-required result/review pointers;
- strict unknown-field rejection;
- 16 KiB constructor/parser/canonical-serialization cap;
- canonical JSON + SHA-256 fingerprint machinery;
- pure explicit-observation freshness evaluation with STALE > INCOMPLETE > FRESH precedence;
- no Bridge authority/routing/failover/provider widening.

Historical RESULT reports 23 Continuity, 109 AIOS Bridge and 583 full-repository tests passing at tested implementation `26c0c5d66921ea8dae2412e312343632067a1b83`. This retrospective audit did not independently execute that historical suite.

---

## Decision

```text
REMEDIATION_REQUIRED
```

Create a bounded Canonical State hardening task before treating schema-v1 state as the fully hardened identity/freshness anchor for additional continuity milestones.

This does not invalidate merged TASK-021/022/023/024 behavior; TASK-022's failover path already contains local duplicate-path defense in depth. The remediation should strengthen the shared foundation without widening authority or altering Bridge v0.4 semantics.
