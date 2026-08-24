# TASK-083 — P0 Lean Execution Bootstrap + Validation Ownership Foundation

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS BRIDGE LEAN EXECUTION / P0 FOUNDATION
MILESTONE: P0
CAPABILITY_ID: P0_VALIDATION_OWNERSHIP_TELEMETRY
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
H5_H8_AUTHORIZED: NO
BOOTSTRAP_ROADMAP_ENFORCEMENT: YES

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.1","roadmap_blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c","roadmap_fingerprint":"4bcbb10e1e8e02169ccb5a516801abd1ce01b0b5edd348d90abcac7d0887404f","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P0","capability_id":"P0_VALIDATION_OWNERSHIP_TELEMETRY","requirement_bindings":["P0.R1","P0.R2","P0.R3","P0.R4","P0.R5"],"scope_in":["canonical Lean Execution roadmap registration and generic roadmap-binding bootstrap","single-owner validation tiers and bounded machine-readable validation plan","full-canonical T2 deduplication across Codex and Antigravity publication semantics","bounded validation-count and duration telemetry with duplication detection","preservation of existing Bridge authority publication and fail-closed semantics"],"scope_out":["P1 capability batching or product fast lane","P2 persistent sessions checkpoint resume or capacity suspension","P3 Claude Code adapter or adaptive executor routing","automatic retry or automatic reroute","H5-H8 implementation","authorization lease merge or reviewed-head authority redesign"]}

## Baseline

```text
MAIN_SHA: 6aa75b88a1a6009afc0310ca3f8093f2d00bef5a
TARGET_BRANCH: ai/task-083
TASK_082_STATUS: PASS_MERGED
H4_IMPLEMENTATION_STATUS: PASS_MERGED
H5_STATUS: PAUSED_NOT_AUTHORIZED
LEAN_ROADMAP_V1_0: HISTORICAL_NOT_EXECUTABLE
LEAN_ROADMAP_V1_1: CANONICAL_TARGET
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"ad2ed229adcd7e0db4909a8e1f330b7836544870"},{"path":".ai/decisions/ADR-056-AIOS-BRIDGE-LEAN-EXECUTION-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md","blob_sha":"7ae9b7d518d5130d193ceb9cf981f29290014288"},{"path":".ai/decisions/ADR-057-AIOS-BRIDGE-LEAN-EXECUTION-V1.1-CANONICAL-ROADMAP-NORMALIZATION.md","blob_sha":"3270fca0fb723c49a67eba5586d6a6714bcb2bfa"},{"path":".ai/reviews/REVIEW-082.md","blob_sha":"14617f5ce355044d752ba5c409bf2989528131c4"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/roadmap_governance.py","src/aios_bridge/validation.py","src/aios_bridge/executor_automation.py",".agents/skills/aios-worker/scripts/aios_worker.py","tests/aios_bridge/test_validation.py","tests/aios_bridge/test_roadmap_governance.py","tests/test_bridge.py","tests/test_bridge_executor_automation.py","tests/aios_bridge/test_aios_worker_control_surface.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Implement the first executable P0 slice of AIOS Bridge Lean Execution Refactor without rewriting the Bridge control plane.

TASK-083 must accomplish five bounded outcomes:

```text
1. bootstrap canonical Bridge enforcement for the Lean Execution roadmap family;
2. establish one shared validation-tier / owner contract;
3. introduce a bounded machine-readable ValidationPlan;
4. remove duplicate T2 full-canonical execution where ownership is already explicit;
5. record bounded evidence proving actual versus expected validation execution counts.
```

This is a foundation task. It does not complete P1-P3 and does not open H5.

## 1. Bootstrap Lean Roadmap Enforcement

Current `roadmap_governance.py` registers only H-Series and `task_requires_roadmap_governance()` only detects H-Series-class/H-milestone tasks.

Extend the existing generic roadmap-governance mechanism so that after this task's implementation is present:

```text
AIOS-BRIDGE-LEAN-EXECUTION v1.1 is registered by exact ID/version/path/blob SHA;
ROADMAP_BINDING_JSON itself is sufficient to require roadmap governance;
H-Series behavior remains unchanged;
unknown/unregistered roadmap bindings fail closed;
exact roadmap bytes/blob/fingerprint/capability/requirements remain validated by existing canonical machinery.
```

Bootstrap nuance: the pre-task `handoff` runs on main where Lean registration does not yet exist, so this first activation is authorized by the exact Human-approved TASK-083 artifact plus ADR-056/ADR-057. Publication/review must prove that the task-branch implementation now recognizes and validates TASK-083's own `ROADMAP_BINDING_JSON` before PASS. No later Lean task may use this bootstrap exception.

Do not create a parallel roadmap authority implementation.

## 2. Validation Tier / Owner Contract

Define closed concepts equivalent to:

```text
ValidationTier:
  T0_MICRO
  T1_TARGETED_IMPACT
  T2_FULL_CANONICAL
  T3_RELEASE

ValidationOwner:
  EXECUTOR
  CERTIFICATION_BOUNDARY
  RELEASE_BOUNDARY
```

For normal canonical task execution in P0:

```text
T0/T1 -> EXECUTOR
T2    -> CERTIFICATION_BOUNDARY
T3    -> RELEASE_BOUNDARY
```

Exactly one owner may own T2 for an execution plan.

## 3. Machine-Readable ValidationPlan

Introduce a bounded immutable plan sufficient to express at least:

```text
profile_id
executor_test_tiers
certification_test_tiers
diff_check_required
expected_full_suite_execution_count
```

Required compatibility profile:

```text
CONTROL_PLANE_STRICT_COMPAT
```

Legacy task prose requesting `pytest tests/ -q` must not cause a second identical T2 when the certification boundary already owns T2. Compatibility behavior must be deterministic and fail-conservative.

If ownership cannot be proven, retain strict certification rather than silently skipping T2.

## 4. Shared Antigravity / Codex Validation Semantics

The UI surfaces may remain different, but validation ownership must be shared.

```text
Antigravity interactive execution
Codex one-shot execution
future Claude execution
        |
        v
same ValidationPlan semantics
same T2 certification owner semantics
same evidence schema
```

Remove Codex-specific duplicate full-suite behavior caused by executor instructions plus `bridge execute` hard-coded T2.

Do not remove canonical certification itself.

Antigravity publication must consume the same plan/ownership contract rather than a separate policy.

## 5. Validation Telemetry Foundation

Add bounded immutable evidence equivalent to:

```text
task_id
action
executor_id
validation_profile
full_suite_execution_count
expected_full_suite_execution_count
targeted_test_execution_count
full_suite_duration_seconds when observed
targeted_test_duration_seconds when observed
validation_duplication_detected
```

Rules:

```text
actual == expected -> normal evidence
actual > expected  -> VALIDATION_DUPLICATION_DETECTED
failed T2          -> publication denied
unknown provider token/quota data stays unknown
wall-clock test time must never be converted into provider quota/token estimates
```

Telemetry is evidence only. It cannot manufacture authority or PASS.

## 6. Authority Invariants

Must remain unchanged:

```text
TASK_AUTHORITY
REVIEW_AUTHORITY
EXECUTOR_LEASE_SEMANTICS
SCOPE_ENFORCEMENT
PUBLICATION_TRUST
REVIEWED_HEAD_MERGE_SAFETY
HUMAN_EXECUTOR_SELECTION_AUTHORITY
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
```

## 7. Explicit Out of Scope

```text
P1 capability batching
PRODUCT_DELIVERY_FAST implementation
integration lane
persistent Codex or Claude sessions
public RESUME
checkpoint/resume
capacity suspension
adaptive executor selection
Claude Code transport integration
automatic retry
automatic reroute
H5-H8 implementation
Bridge authorization redesign
lease redesign
merge redesign
```

## 8. Required Targeted / Impact Tests

Executor runs targeted/impact tests and `git diff --check`; executor must not independently run T2 when the plan assigns T2 to certification.

Required proofs:

```text
LEAN_ROADMAP_V1_1_PARSE_CANONICAL: PASS
LEAN_ROADMAP_REGISTRY_ENTRY: PASS
ROADMAP_BINDING_MARKER_TRIGGERS_GOVERNANCE: PASS
UNKNOWN_ROADMAP_FAIL_CLOSED: PASS
H_SERIES_GOVERNANCE_REGRESSION: PASS
TASK_083_SELF_BINDING_VALID_AT_PUBLICATION: PASS
VALIDATION_TIER_CLOSED: PASS
VALIDATION_OWNER_CLOSED: PASS
EXACTLY_ONE_T2_OWNER: PASS
LEGACY_FULL_SUITE_COMPATIBILITY: PASS
CODEX_FULL_SUITE_DUPLICATION_ELIMINATED: PASS
ANTIGRAVITY_VALIDATION_PARITY: PASS
CODEX_VALIDATION_PARITY: PASS
CLAUDE_CONTRACT_COMPATIBLE: PASS
FULL_SUITE_COUNT_TELEMETRY: PASS
DUPLICATION_DETECTION: PASS
FAILED_T2_CANNOT_PUBLISH: PASS
AMBIGUOUS_OWNERSHIP_FAILS_CONSERVATIVELY: PASS
TASK_AUTHORITY_UNCHANGED: PASS
LEASE_SEMANTICS_UNCHANGED: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
```

## 9. Certification Boundary

The certification boundary owns the canonical full repository suite exactly once after executor targeted/impact verification.

Required final evidence:

```text
FULL_CANONICAL_OWNER: CERTIFICATION_BOUNDARY
EXPECTED_FULL_SUITE_EXECUTION_COUNT: 1
FULL_SUITE_EXECUTION_COUNT: 1
VALIDATION_DUPLICATION_DETECTED: NO
```

If the current compatibility path cannot safely prove exactly-one T2 without weakening publication safety, fail conservatively and report the blocker; do not fake the count.

## Acceptance

TASK-083 passes only if:

```text
P0.R1_SINGLE_TEST_OWNER: PASS
P0.R2_EXPLICIT_VALIDATION_PLAN: PASS
P0.R3_FULL_SUITE_DEDUP_FOUNDATION: PASS
P0.R4_TELEMETRY_FOUNDATION: PASS
P0.R5_CONTROL_PLANE_AUTHORITY_UNCHANGED: PASS
LEAN_ROADMAP_ENFORCEMENT_BOOTSTRAPPED: PASS
ANTIGRAVITY_CODEX_POLICY_PARITY: PASS
FULL_CANONICAL_CERTIFICATION_PRESERVED: PASS
P1_P3_NOT_IMPLEMENTED: PASS
H5_NOT_OPENED: PASS
```
