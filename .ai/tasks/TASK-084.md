# TASK-084 — Canonical Roadmap Registry Bootstrap

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS CONTROL PLANE / ONE-TIME ROADMAP REGISTRY BOOTSTRAP
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
H5_H8_AUTHORIZED: NO
BOOTSTRAP_EXCEPTION_ID: ADR-058
BOOTSTRAP_EXCEPTION_ONE_TIME: YES

## Baseline

```text
MAIN_SHA: 6aa75b88a1a6009afc0310ca3f8093f2d00bef5a
TARGET_BRANCH: ai/task-084
TASK_083_STATE: BLOCKED_BY_ROADMAP_REGISTRY_BOOTSTRAP
LEAN_ROADMAP_V1_1: HUMAN_APPROVED_CANONICAL
BOOTSTRAP_SCOPE: ROADMAP_REGISTRY_ONLY
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-058-AIOS-CANONICAL-ROADMAP-REGISTRY-BOOTSTRAP-CONTRACT.md","blob_sha":"41578383d4a9e7054631bc2c3ebfaeace910a452"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"52f4f24a6b0af719886c6524ade8e19f8cc8984c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/decisions/ADR-057-AIOS-BRIDGE-LEAN-EXECUTION-V1.1-CANONICAL-ROADMAP-NORMALIZATION.md","blob_sha":"3270fca0fb723c49a67eba5586d6a6714bcb2bfa"},{"path":".ai/tasks/TASK-083.md","blob_sha":"fff8fb673707391e2129cf06f0c7c898c68b22cd"},{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/roadmap_governance.py","src/aios_bridge/task_authoring.py","tests/aios_bridge/test_roadmap_governance.py","tests/test_bridge_task_authoring.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Authority Boundary

This TASK is the exact one-time bootstrap task authorized by ADR-058. It intentionally carries no canonical roadmap binding because the capability being implemented is the mechanism that makes a newly approved roadmap family discoverable by preflight before its first roadmap-bound TASK can execute.

This exception grants no additional authority. All normal publisher, executor-selection, scope, lease, publication, independent review, reviewed-head, and merge controls remain active.

No other TASK may copy or inherit this bootstrap exception.

## Objective

Remove the roadmap-registration chicken-and-egg failure without weakening roadmap governance.

Current behavior:

```text
new canonical roadmap exists on ai-control
        ↓
roadmap-bound TASK reaches preflight
        ↓
source-code DEFAULT_ROADMAP_REGISTRY does not know identity
        ↓
ROADMAP_BINDING_FAILED
        ↓
executor can never run the task that would register it
```

Target behavior after TASK-084:

```text
Human-approved canonical roadmap
        ↓
canonical registry manifest updated on ai-control
        ↓
Bridge strictly parses registry manifest
        ↓
exact roadmap artifact/blob parsed and validated
        ↓
roadmap-bound TASK preflight proceeds normally
```

## 1. Strict Canonical Registry Parser

Implement a deterministic bounded parser for the canonical control-plane registry manifest equivalent to:

```text
.ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json
```

The parser must require the exact envelope concepts:

```text
schema_version
AUTHORITY == CANONICAL
entries
```

Every entry must contain exactly:

```text
roadmap_id
roadmap_version
artifact_path
roadmap_blob_sha
```

Reject at minimum:

```text
unknown top-level fields
unknown entry fields
missing fields
duplicate (roadmap_id, roadmap_version)
duplicate/conflicting artifact identity
malformed IDs / versions / paths / blob SHAs
non-list entries
non-string scalars
unbounded registry size / entry count
```

No network, filesystem, Git, model, executor, lease, review, or merge side effects belong inside the pure parser.

## 2. Bridge Registry Resolution

Wire normal executable-artifact preflight so Bridge obtains the canonical registry manifest from the exact `ai-control` control-plane snapshot used for authorization and supplies the parsed registry to roadmap preflight.

Requirements:

```text
registry source is canonical control-plane evidence
missing registry -> fail closed for roadmap-bound tasks
malformed registry -> fail closed
unknown roadmap identity -> fail closed
registered roadmap exact blob still required
canonical roadmap parse still required
task roadmap fingerprint/requirements/scope validation still required
```

Do not allow registry presence alone to authorize a task or milestone.

The existing H-Series registration must remain compatible. A source-code fallback may exist only as a bounded migration safeguard if required; future roadmap onboarding must not require a source-code patch.

## 3. Prove Lean v1.1 Recognition

Using exact test fixtures/evidence, prove that the registry manifest containing:

```text
AIOS-ENGINEERING-H-SERIES / 1.0
AIOS-BRIDGE-LEAN-EXECUTION / 1.1
```

allows the normal roadmap preflight engine to resolve and validate TASK-083's Lean v1.1 binding once TASK-084 code is present.

This proof must use normal preflight behavior, not a TASK-083-specific bypass, task-ID special case, environment flag, or hard-coded Lean-only condition.

## 4. Preserve Governance

Required invariants:

```text
TASK_AUTHORITY_UNCHANGED: YES
ROADMAP_EXACT_BLOB_REQUIRED: YES
ROADMAP_FINGERPRINT_REQUIRED: YES
REQUIREMENT_BINDING_REQUIRED: YES
SCOPE_BINDING_REQUIRED: YES
LEASE_SEMANTICS_UNCHANGED: YES
REVIEW_AUTHORITY_UNCHANGED: YES
MERGE_AUTHORITY_UNCHANGED: YES
AUTO_RETRY: NO
AUTO_REROUTE: NO
H5_OPENED: NO
```

TASK-084 must not implement any P0 validation ownership/dedup/telemetry feature. That remains TASK-083.

## Explicit Out of Scope

```text
ValidationPlan or validation tiers
full-suite deduplication
execution telemetry
P1 capability batching
P2 sessions/checkpoint/resume/capacity suspension
P3 Claude integration/adaptive routing
H5-H8 implementation
paid API use
automatic retry
automatic reroute
roadmap semantic changes
TASK-083 implementation
```

## Required Targeted Tests

Targeted tests must prove at minimum:

```text
REGISTRY_VALID_MANIFEST_PARSE: PASS
REGISTRY_UNKNOWN_FIELD_REJECTED: PASS
REGISTRY_MISSING_FIELD_REJECTED: PASS
REGISTRY_DUPLICATE_ID_VERSION_REJECTED: PASS
REGISTRY_MALFORMED_ENTRY_REJECTED: PASS
REGISTRY_HARD_BOUNDS: PASS
H_SERIES_RESOLUTION_COMPATIBLE: PASS
LEAN_V1_1_RESOLUTION: PASS
TASK_083_NORMAL_PREFLIGHT_AFTER_BOOTSTRAP: PASS
UNKNOWN_ROADMAP_FAILS_CLOSED: PASS
MISSING_REGISTRY_FAILS_CLOSED: PASS
MALFORMED_REGISTRY_FAILS_CLOSED: PASS
EXACT_ROADMAP_BLOB_STILL_ENFORCED: PASS
NO_TASK_ID_SPECIFIC_BYPASS: PASS
NO_AUTO_RETRY_REROUTE: PASS
```

## Validation Commands

Executor phase runs targeted tests and diff check only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_roadmap_governance.py tests/test_bridge_task_authoring.py tests/test_bridge.py -q
git diff --check
```

Do NOT run `pytest tests/ -q` inside the Codex implementation session. Current Bridge certification remains responsible for the canonical full repository suite after executor completion. This avoids knowingly paying the existing duplicate-full-suite tax during the bootstrap task.

## Acceptance Boundary

TASK-084 passes only if:

```text
ADR_058_ONE_TIME_EXCEPTION_RESPECTED: PASS
CANONICAL_REGISTRY_STRICT: PASS
GENERIC_FUTURE_ROADMAP_ONBOARDING: PASS
H_SERIES_COMPATIBILITY: PASS
LEAN_V1_1_NORMAL_PREFLIGHT: PASS
TASK_083_PREFLIGHT_DEADLOCK_REMOVED: PASS
CONTROL_PLANE_AUTHORITY_UNCHANGED: PASS
P0_NOT_IMPLEMENTED: PASS
H5_NOT_OPENED: PASS
```

After independent PASS + merge, TASK-084's bootstrap exception is exhausted. TASK-083 must be rebound/revalidated against the resulting main before its next RUN.
