# ADR-058 — AIOS Canonical Roadmap Registry Bootstrap Contract

STATUS: ACCEPTED
DECISION_TYPE: GOVERNANCE_BOOTSTRAP_REFINEMENT
HUMAN_APPROVED: YES
ONE_TIME_BOOTSTRAP_EXCEPTION: YES
AUTHORIZED_BOOTSTRAP_TASK: TASK-084
AUTHORITY_CHANGE: NO
AUTO_RETRY_CHANGE: NO
AUTO_REROUTE_CHANGE: NO
H5_OPENED: NO

CANONICAL_REGISTRY: .ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json
CANONICAL_REGISTRY_BLOB_SHA: 52f4f24a6b0af719886c6524ade8e19f8cc8984c
LEAN_ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
LEAN_ROADMAP_VERSION: 1.1
LEAN_ROADMAP_BLOB_SHA: cae51de4db517dd452c260076a1daa521c1e3a4c
BASELINE_MAIN_SHA: 6aa75b88a1a6009afc0310ca3f8093f2d00bef5a

## Context

TASK-083 is correctly bound to the Human-approved canonical Lean Execution roadmap v1.1, but current Bridge roadmap preflight resolves roadmap identity through a source-code `DEFAULT_ROADMAP_REGISTRY` that contains only H-Series. Because preflight executes before lease/executor authorization, TASK-083 cannot run to add its own roadmap registration. The observed failure is a genuine governance bootstrap deadlock, not an executor failure.

The failed TASK-083 RUN performed no retry, no reroute, no implementation mutation, and no task branch creation. The fail-closed behavior is preserved.

## Decision

Authorize exactly one bootstrap task, TASK-084, to establish a generic canonical roadmap registry mechanism without itself carrying a `ROADMAP_BINDING_JSON` marker.

TASK-084 is not exempt from normal executable-artifact, publisher-profile, dispatch-policy, executor-selection, scope, lease, publication, review, reviewed-head, or merge controls. Its only exception is the absence of roadmap binding, because the capability being implemented is the mechanism required to make new roadmap families enforceable before their first roadmap-bound task can execute.

No other task inherits this exception.

## Canonical Registry Model

The control plane now owns the exact manifest:

```text
.ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json
```

The manifest is an index, not a substitute for roadmap authority. Every entry binds:

```text
roadmap_id
roadmap_version
artifact_path
roadmap_blob_sha
```

Each executable roadmap-bound task must still bind the exact roadmap fingerprint/blob/requirements, and Bridge must still parse and validate the exact canonical roadmap artifact itself.

## Required TASK-084 Outcome

TASK-084 must replace roadmap-family hard-coding as the normal discovery mechanism with a bounded, strict, fail-closed canonical registry path.

Required properties:

```text
REGISTRY_SCHEMA_STRICT: YES
REGISTRY_DUPLICATE_ID_VERSION_REJECTED: YES
REGISTRY_UNKNOWN_FIELDS_REJECTED: YES
REGISTRY_MALFORMED_ENTRY_REJECTED: YES
EXACT_ROADMAP_BLOB_STILL_REQUIRED: YES
EXACT_ROADMAP_PARSE_STILL_REQUIRED: YES
TASK_ROADMAP_BINDING_STILL_REQUIRED_AFTER_BOOTSTRAP: YES
H_SERIES_COMPATIBILITY_PRESERVED: YES
LEAN_V1_1_RECOGNIZED: YES
MISSING_OR_INVALID_REGISTRY_FAILS_CLOSED: YES
NO_NETWORK_LLM_PAID_API: YES
```

Bridge may retain the old source-code registry only as a tightly bounded migration fallback if needed for existing H-Series compatibility during TASK-084 implementation. It must not remain the required way to onboard future roadmap families.

## Future Roadmap Onboarding

After TASK-084 is merged, a new roadmap family/version is onboarded by controlled evolution of control-plane artifacts:

```text
Human approves roadmap / roadmap amendment
        ↓
canonical roadmap artifact created/versioned
        ↓
canonical registry manifest updated with exact blob identity
        ↓
Bridge preflight recognizes the roadmap
        ↓
first roadmap-bound TASK may execute normally
```

No source-code patch should be required merely to add a new roadmap identity.

Updating the registry does not itself authorize a milestone/task. Normal task authority and exact roadmap binding remain mandatory.

## One-Time Exception Guard

The bootstrap exception is valid only for:

```text
TASK_ID: TASK-084
BASE_MAIN_SHA: 6aa75b88a1a6009afc0310ca3f8093f2d00bef5a
PURPOSE: canonical roadmap registry bootstrap
```

TASK-084 must explicitly reference this ADR and the exact canonical registry manifest. It must not contain `ROADMAP_BINDING_JSON` and must not claim P0/H-Series milestone completion.

After TASK-084 PASS + merge, this exception is exhausted. TASK-083 must then be rebound/validated against the newly enforced Lean Execution v1.1 registry before RUN.

## Explicitly Out of Scope

```text
P0 validation-plan implementation
full-suite deduplication
P1 capability batching
P2 executor sessions
P3 Claude adapter
H5-H8 work
authorization redesign
lease redesign
merge redesign
automatic retry
automatic reroute
```

## Completion

ADR-058 is satisfied only when TASK-084 independently reviews PASS, main contains the generic registry enforcement mechanism, H-Series remains compatible, Lean v1.1 is recognized by normal roadmap preflight, and TASK-083 can pass preflight without any bootstrap bypass.
