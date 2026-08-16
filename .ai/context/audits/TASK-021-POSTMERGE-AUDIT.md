# TASK-021 — Post-Merge Independent Audit

STATUS: FINDINGS_REQUIRE_REMEDIATION

## Audit Basis

This is a retrospective audit of merged TASK-021 under ADR-017 Uniform Assurance Pipeline.

Historical TASK-021 merge/review history is not rewritten. Findings below SHALL be remediated by a new task.

Reviewed implementation boundary:
- `src/aios_bridge/continuity/brain.py`
- `tests/aios_bridge/continuity/test_brain.py`
- coupled Continuity validators/types in `state.py`
- TASK-021 contract
- RESULT-021
- historical REVIEW-021

TASK-021 merged head:

```text
4978e426f3445c086c017c07c844943ac841e4de
```

The Brain contract source remains unchanged on current main after TASK-022.

---

## Finding P21-1 — Brain identity/request/path validation accepts non-canonical raw representations

Severity: HIGH

Shared validators such as `_validate_actor_id()`, `_validate_artifact_path()` and Brain `_validate_request_id()` validate a stripped representation and return the canonical value. Brain contract constructors often ignore that return value and retain the original raw field.

Consequences include:
- `brain-a` and ` brain-a ` may both validate but persist/fingerprint as different identities;
- request IDs can have the same logical ambiguity;
- a ContextRef path and a whitespace-padded equivalent can both survive construction as distinct raw paths;
- duplicate ContextRef detection compares raw paths and can therefore be bypassed by non-canonical representation;
- deterministic request/result fingerprints can encode representational ambiguity instead of one strict identity.

TASK-022 had to add local failover-specific canonical guards around the same M2 objects, which is further evidence that the generic M2 boundary is too permissive.

Required remediation:
- BrainRequest, BrainResult and BrainCapability actor/request identities must be exact canonical values, not merely strip-valid;
- Brain-owned ContextRef/OutputContract boundary paths must reject leading/trailing whitespace or store one explicitly canonical representation consistently;
- duplicate ContextRef checks must operate on exact canonical path identity;
- preserve generic `ContextRef.blob_sha=None` semantics outside failover; content anchoring remains an M3A-specific stronger rule.

---

## Finding P21-2 — PLAN/DIAGNOSIS/PATCH task-role matching is substring-based and can accept the wrong task

Severity: HIGH

`_validate_artifact_role_and_task()` currently considers PLAN/DIAGNOSIS/PATCH task identity valid when either the full task ID or a normalized short token occurs anywhere in the path.

For active `TASK-021`, a path such as:

```text
.ai/plans/TASK-0210-PLAN.md
```

contains `TASK-021` as a substring and can therefore satisfy the current identity check despite belonging to a different task token.

The normalized short form also creates prefix/leading-zero ambiguity, e.g. `TASK-21` can match `TASK-210...`.

Required remediation:
- task identity in role paths must use an exact, delimiter-aware token rule;
- false prefixes/suffixes and leading-zero aliases must fail closed;
- TASK/REVIEW role path behavior must remain deterministic and compatible with the canonical project naming policy.

---

## Finding P21-3 — BrainResult status/payload invariants are incomplete

Severity: HIGH

Payload consistency/role validation currently runs only inside the `SUCCESS` branch.

Therefore a non-success result can retain artifact/evidence pointers without enforcing the same task/output-role consistency. A `FAILED` result can carry an artifact pointer for another task while still constructing successfully.

There is also an ambiguity for `BOUNDED_TEXT`: a SUCCESS result can provide `artifact_ref`; `_validate_artifact_role_and_task()` has no BOUNDED_TEXT role branch, so the artifact pointer can pass even though the implemented positive test models BOUNDED_TEXT through `evidence_ref`.

Additional contradictory state such as `SUCCESS` plus non-null `error_code` is currently accepted.

Required remediation:
- every pointer present in BrainResult must be type/role/task-consistent regardless of status;
- define and enforce one unambiguous payload policy for SUCCESS vs non-success statuses;
- BOUNDED_TEXT must not silently use an artifact-output path/pointer unless the locked contract explicitly defines that behavior;
- reject obviously contradictory SUCCESS/error metadata.

The remediation must remain advisory/pointer-only and must not persist raw Brain output.

---

## Finding P21-4 — BrainCapability is not fully bounded

Severity: MEDIUM

TASK-021 required immutable, bounded neutral types. BrainRequest/BrainResult have explicit total serialized-size bounds and other field limits, but BrainCapability has no total record size bound, no supported-operation count/duplicate constraint, and no explicit finite bound for its descriptive capacity metadata.

Required remediation:
- make BrainCapability deterministically bounded;
- reject duplicate supported operations;
- keep capabilities declarative-only and authority-free;
- do not add routing, ranking, invocation or fallback behavior.

---

## Positive Findings

The audit reconfirms that TASK-021 correctly established:
- vendor-neutral BrainRequest/BrainResult/BrainCapability concepts;
- closed operation/status/output enums;
- request/result canonical JSON + SHA-256 fingerprinting;
- 16 KiB request/result bounds;
- unknown-field rejection;
- sensitive AIOS path rejection;
- pointer-only BrainResult design rather than raw output persistence;
- no provider invocation/router/fallback/executor/Bridge authority change.

The implementation scope was limited to RESULT, Continuity exports, `brain.py`, and `test_brain.py`.

---

## Decision

TASK-021 remains historically MERGED; its history SHALL NOT be rewritten.

The post-merge audit verdict is:

```text
REMEDIATION_REQUIRED
```

Create a new hardening task before proceeding to M3B real cross-Brain proof, because TASK-022 failover semantics depend on the M2 Brain contract types.
