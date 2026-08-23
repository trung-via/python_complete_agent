# TASK-077 — Canonical Roadmap Lock Enforcement + H-Series Reconciliation

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L3 — AIOS ENGINEERING GOVERNANCE
MILESTONE: ROADMAP-GOVERNANCE-BOOTSTRAP
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity
ROADMAP_BOOTSTRAP_EXCEPTION: ADR-050

## Baseline

```text
MAIN_SHA: 60f18b3be650725f097305e38c1c36b6b434e62b
TARGET_BRANCH: ai/task-077
TASK_076_BRANCH_HEAD: fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
TASK_076_MERGE_AUTHORIZED: NO
H_SERIES_ADVANCEMENT: FROZEN_PENDING_RECONCILIATION
CANONICAL_H_SERIES_ROADMAP: .ai/roadmaps/H-SERIES-v1.0.md
CANONICAL_H_SERIES_ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
GOVERNANCE_ADR: ADR-050
GOVERNANCE_ADR_BLOB_SHA: 334b610b2c221ac20b2b9946142a0baed8952690
REVIEW_076_BLOB_SHA: cf4dfc7253bc252746a6bfee1dd275784add416e
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
H5_IMPLEMENTATION_AUTHORIZED: NO
```

TASK-077 is the one-time bootstrap task that installs the governance mechanism which future governed tasks must obey. It is not an H0-H8 capability milestone and must not be counted as H-Series progression.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-050-AIOS-ENGINEERING-CANONICAL-ROADMAP-LOCK-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md","blob_sha":"334b610b2c221ac20b2b9946142a0baed8952690"},{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/reviews/REVIEW-076.md","blob_sha":"cf4dfc7253bc252746a6bfee1dd275784add416e"},{"path":".ai/decisions/ADR-044-EXECUTABLE-TASK-AUTHORING-PREFLIGHT-ZERO-TOUCH-START-CONTRACT-LOCK.md","blob_sha":"24b212d96d5fa650241a71049ce114f7a3a85489"},{"path":".ai/decisions/ADR-042-LEAN-AUTO-MERGE-REVIEWED-HEAD-BINDING-CONTRACT-LOCK.md","blob_sha":"33018c96ad941618f11ce1bfc48d569b94cfad72"},{"path":".ai/decisions/ADR-038-AIOS-ENGINEERING-H-SERIES-H0-AUTHORITY-BOUNDARY-CONTRACT-LOCK.md","blob_sha":"be56f92eef5dcffdc37cebafea280399730b151f"},{"path":".ai/decisions/ADR-031-E3-BOUNDED-EXECUTOR-CONTEXT-PACK-CONTRACT-LOCK.md","blob_sha":"5ee1d936f17f1b3530cbe23d6a0157f6d1116fd9"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/roadmap_governance.py","src/aios_bridge/task_authoring.py","src/aios_bridge/review_merge.py","tests/aios_bridge/test_roadmap_governance.py","tests/test_bridge_task_authoring.py","tests/aios_bridge/test_review_merge.py","tests/test_bridge.py","docs/AIOS_H_SERIES_RECONCILIATION_V1.md"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

These markers authorize only bounded governance implementation under ADR-050. They create no H5 authority, no TASK-076 merge authority, no retry/reroute authority, and no paid-provider authority.

## Objective

Implement ADR-050 as deterministic, fail-closed AIOS Engineering roadmap governance and produce the first H-Series reconciliation report against the locked canonical H0-H8 baseline.

The implementation must prevent the exact failure class that produced current H2/H3/H4 drift:

```text
recent implementation state
    -> inferred next H-number
    -> new ADR/TASK silently redefines milestone
```

After TASK-077, a governed H-Series task cannot be author/execution-ready unless it is exactly bound to the locked canonical roadmap and valid canonical requirement(s).

## 1. New Roadmap Governance Module

Create `src/aios_bridge/roadmap_governance.py` as a deterministic local-only governance module.

Required public concepts should be equivalent to:

```python
ROADMAP_FINGERPRINT_ALGORITHM_VERSION = "roadmap-sha256-v1"

class RoadmapStatus(...):
    DRAFT = "DRAFT"
    LOCKED = "LOCKED"
    SUPERSEDED = "SUPERSEDED"

@dataclass(frozen=True)
class CanonicalRoadmap: ...

@dataclass(frozen=True)
class RoadmapTaskBinding: ...

@dataclass(frozen=True)
class MilestoneCompletionRecord: ...

@dataclass(frozen=True)
class RoadmapPreflightDecision: ...
```

Narrower internal dataclasses/enums are allowed when needed, but the module must have one deterministic authority for roadmap parsing, fingerprinting, task binding validation, milestone completion validation, and controlled-evolution state semantics.

No network, LLM, provider, executor selection, lease, dispatch, merge, or paid-API authority may be created here.

## 2. Exact Canonical Roadmap Identity

Lock fingerprint semantics as:

```text
roadmap_blob_sha = exact Git blob SHA-1 provenance
roadmap_fingerprint = SHA-256(exact Git blob bytes)
algorithm_version = roadmap-sha256-v1
```

Do not fingerprint worktree-normalized text when exact Git blob bytes are available.

Roadmap validation must reject at minimum:

```text
missing/duplicate ROADMAP_ID
missing/duplicate ROADMAP_VERSION
STATUS != LOCKED for executable task binding
missing/duplicate AUTHORITY
AUTHORITY != CANONICAL
malformed/duplicate milestone identity
malformed/duplicate CAPABILITY_ID
malformed/duplicate requirement IDs
requirement attached to wrong milestone
H9 or another undeclared milestone
blob SHA mismatch
fingerprint mismatch
unsupported fingerprint algorithm version
```

The current H-Series canonical roadmap identity must be test-bound to blob:

```text
41775383879c86dc68a7d87c0d705cfc8512f62d
```

## 3. Canonical TASK Binding Marker

Introduce one unambiguous top-level machine-readable marker for governed tasks:

```text
ROADMAP_BINDING_JSON: {...}
```

Its schema must contain at minimum:

```text
roadmap_id
roadmap_version
roadmap_blob_sha
roadmap_fingerprint
roadmap_fingerprint_algorithm_version
milestone
capability_id
requirement_bindings[]
scope_in[]
scope_out[]
```

Requirements:

- exact one marker only;
- strict JSON object, no duplicate semantic fields;
- bounded strings/list counts/serialized size;
- no bool accepted where integer is expected;
- roadmap/milestone/capability/requirement comparisons are exact and case-sensitive;
- requirement bindings are non-empty and unique;
- all requirement IDs belong to the declared milestone;
- `scope_in`/`scope_out` are bounded, duplicate-free advisory scope declarations and create no authority beyond the bound canonical requirements.

## 4. H-Series Missing-Binding Fail-Closed Rule

After this task lands, H-Series executable TASKs must not evade governance by omitting `ROADMAP_BINDING_JSON`.

At minimum, an executable artifact is H-Series-governed when either is true:

```text
CLASS contains exact semantic token "AIOS ENGINEERING H-SERIES"
OR
MILESTONE is exact H0..H8 / matches H<digits> in the H-Series task header
```

For such a TASK:

```text
missing ROADMAP_BINDING_JSON -> ROADMAP_BINDING_FAILED
H9 or undeclared H milestone  -> ROADMAP_BINDING_FAILED
```

The TASK-077 bootstrap exception is allowed only because ADR-050 explicitly names this task as governance bootstrap. Do not create a generic executor-controlled bypass marker.

## 5. Roadmap Preflight Integration

Integrate roadmap validation into the existing executable authoring preflight (`src/aios_bridge/task_authoring.py`) and the Bridge call path that invokes it.

Ordering must be fail-closed and side-effect free before worker authorization:

```text
existing publisher/automation/dispatch validation
        ↓
identify whether roadmap governance is required
        ↓
resolve exact canonical roadmap from control-plane Git evidence
        ↓
verify exact blob SHA and compute exact-byte SHA-256
        ↓
validate ROADMAP_BINDING_JSON
        ↓
validate milestone/capability/requirements
        ↓
validate progression/completion precondition where applicable
        ↓
only then continue existing Human-selected executor authorization path
```

Roadmap preflight must occur before executor launch and before productive task work.

Do not weaken ADR-044 authoring preflight, E4 allowed-path checks, dispatch policy, lease, or authorization semantics.

## 6. Canonical Roadmap Must Be in Executor Context

For a governed task, the exact canonical roadmap artifact must appear in `EXECUTOR_CONTEXT_REFS_JSON` with the same `roadmap_blob_sha` declared in `ROADMAP_BINDING_JSON`.

Preflight must reject:

```text
roadmap context ref missing
roadmap context path mismatch
roadmap context blob mismatch
duplicate conflicting roadmap context refs
```

This guarantees the executor bootstrap pack carries the canonical roadmap instead of depending on conversation memory.

Do not increase existing E3 context-ref limits. The roadmap consumes one existing bounded context ref.

## 7. Milestone Completion Contract

Implement deterministic validation for a milestone completion record containing at minimum:

```text
roadmap identity/fingerprint
milestone
capability_id
requirement_evidence mapping
unresolved_requirements exact tuple
unresolved_blockers exact tuple
status
record_fingerprint
```

Completion is valid only when:

```text
status == COMPLETE
all canonical requirements for milestone have evidence
no extra/wrong-milestone requirements
unresolved_requirements == empty
unresolved_blockers == empty
record fingerprint valid
```

Lock invariant:

```text
TASK PASS != MILESTONE COMPLETE
```

The implementation must expose a pure decision function for whether a target milestone may be opened from supplied completion evidence. It must not auto-create completion evidence from a PASS review.

## 8. Controlled Evolution Semantics

Implement validation semantics for roadmap lifecycle and change class:

```text
DRAFT
LOCKED
SUPERSEDED

IMPLEMENTATION_REFINEMENT
CAPABILITY_EXTENSION
ARCHITECTURAL_UPGRADE
```

Rules:

- implementation refinement may stay on the same locked roadmap when canonical requirement identity does not change;
- capability extension requires an explicit Human-approved amendment identity before it can bind new requirement scope;
- architectural upgrade requires a different approved roadmap version / superseding identity;
- agents cannot silently mutate a LOCKED roadmap;
- a task bound to a superseded/non-current roadmap fails closed unless an explicit Human-approved migration/revalidation artifact authorizes it.

Implement an impact-cone helper over explicit milestone dependencies. If no narrower dependency graph is supplied for H-Series, treat H0→H1→...→H8 as the conservative linear dependency chain.

## 9. Independent Review / Merge Roadmap Gate

Extend `src/aios_bridge/review_merge.py` so a PASS review for a roadmap-governed task cannot become merge-eligible without exact roadmap audit evidence.

Required review fields for governed tasks must bind at least:

```text
ROADMAP_AUDIT: PASS
ROADMAP_ID
ROADMAP_VERSION
ROADMAP_BLOB_SHA
ROADMAP_FINGERPRINT
MILESTONE
CAPABILITY_ID
REQUIREMENT_BINDINGS_FINGERPRINT
```

The merge gate must fail closed when:

```text
ROADMAP_AUDIT != PASS
review roadmap identity != task-bound roadmap identity
reviewed milestone/capability mismatch
binding fingerprint mismatch
current locked roadmap blob/fingerprint drifted from reviewed binding
```

Add a closed merge-gate reason vocabulary for roadmap failures; do not overload unrelated merge reasons.

This gate is additional to ADR-042 reviewed-head/main-head/fast-forward checks, not a replacement.

## 10. Deterministic Drift Detector

Implement deterministic roadmap drift checks that can be proven without an LLM.

At minimum detect:

```text
task header milestone != ROADMAP_BINDING_JSON milestone
task title/header claims undeclared H milestone
capability ID not canonical for milestone
requirement ID belongs to another milestone
roadmap artifact omitted from context
roadmap blob/fingerprint mismatch
review claims another milestone/capability
PASS review omits roadmap audit evidence
milestone advancement without valid completion evidence
```

Do not pretend deterministic code can fully semantically classify arbitrary source diffs. Human/ChatGPT semantic review remains responsible for catching novel out-of-scope behavior; the deterministic gate must make that review result machine-bindable before merge.

## 11. H-Series Reconciliation Report

Create `docs/AIOS_H_SERIES_RECONCILIATION_V1.md` by auditing the actual repository/control-plane history through TASK-076 against `.ai/roadmaps/H-SERIES-v1.0.md`.

The report must not infer roadmap identity from TASK numbering. For each canonical H0-H8 milestone report:

```text
canonical capability + requirements
implemented evidence / TASKs / ADRs
classification:
  COMPLETE
  PARTIAL
  MISSING
  MISCLASSIFIED_BUT_USEFUL
  CONFLICTING
missing canonical requirements
safe reuse/rebinding notes
```

At minimum explicitly evaluate these known drift artifacts:

```text
ADR-045 — labeled H2 relevance ranking / bounded selection
ADR-048 — labeled H3 role + Python symbol intelligence; executor tendency absent
ADR-049 / TASK-076 — labeled H4 static import dependency graph; knowledge registry explicitly non-goal
TASK-076 branch head fea85a8bc7f696c50fd5457b0cea3b5d8032b24f
```

The report must conclude the **true earliest incomplete canonical milestone** and the safe next canonical capability to implement after governance is installed.

Do not mark TASK-076 code for deletion merely because it is misnumbered. Classify whether it is reusable under canonical H2 structural graph or as another supporting capability, and state any exact rename/rebinding work required before it can merge.

## 12. TASK-076 Preservation Boundary

TASK-077 must not modify or merge `ai/task-076`.

It may inspect the exact branch/read-only Git evidence for reconciliation.

Locked outcome while TASK-077 is executing:

```text
TASK_076_BRANCH: PRESERVE
TASK_076_MERGE: NO
H5_START: NO
ROLLBACK_USEFUL_GRAPH_CODE: NO
```

After TASK-077 PASS, ChatGPT review will use the reconciliation result to issue the correct superseding/rebinding path for TASK-076.

## 13. Backward Compatibility

Non-roadmap-governed legacy tasks and completed historical artifacts must continue to parse under existing Bridge contracts unless they are actively re-opened under roadmap governance.

Do not retroactively make historical merged TASKs unparseable merely because they lack `ROADMAP_BINDING_JSON`.

The new missing-binding fail-closed rule applies to newly executable H-Series work after ADR-050/TASK-077 rollout and to any future subsystem explicitly registered/adopted for canonical roadmap governance.

## 14. No Authority Expansion

The governance layer is a validation/gating layer only.

Forbidden:

```text
automatic executor selection
automatic executor substitution
retry/failover authority
worker lease mutation outside existing Bridge path
merge authority beyond existing review gate
paid API calls
network calls from governance unit logic
LLM calls from governance unit logic
H-Series knowledge/retrieval/context milestone implementation
H5 implementation
```

## Mandatory Tests

Add/extend tests proving at minimum:

```text
ROADMAP_EXACT_BLOB_SHA_BOUND: PASS
ROADMAP_EXACT_BYTE_SHA256: PASS
ROADMAP_LOCKED_REQUIRED: PASS
ROADMAP_DRAFT_REJECTED_FOR_EXECUTION: PASS
ROADMAP_SUPERSEDED_REJECTED_WITHOUT_MIGRATION: PASS
DUPLICATE_MILESTONE: REJECTED
DUPLICATE_CAPABILITY: REJECTED
WRONG_MILESTONE_REQUIREMENT: REJECTED
UNDECLARED_H9: REJECTED

H_SERIES_TASK_MISSING_BINDING: REJECTED
TASK_BINDING_EXACT: PASS
TASK_BINDING_BLOB_MISMATCH: REJECTED
TASK_BINDING_FINGERPRINT_MISMATCH: REJECTED
TASK_CAPABILITY_MISMATCH: REJECTED
TASK_REQUIREMENT_MISMATCH: REJECTED
ROADMAP_CONTEXT_REF_REQUIRED: PASS
ROADMAP_CONTEXT_REF_BLOB_MISMATCH: REJECTED

TASK_PASS_IMPLIES_MILESTONE_COMPLETE: NO
MILESTONE_COMPLETE_ALL_REQUIREMENTS: PASS
MILESTONE_COMPLETE_MISSING_REQUIREMENT: REJECTED
MILESTONE_COMPLETE_UNRESOLVED_BLOCKER: REJECTED
MILESTONE_OPEN_WITHOUT_PREVIOUS_COMPLETION: REJECTED

IMPLEMENTATION_REFINEMENT_SAME_VERSION: PASS
CAPABILITY_EXTENSION_WITHOUT_APPROVED_CHANGE: REJECTED
ARCHITECTURAL_UPGRADE_SAME_LOCKED_VERSION: REJECTED
IMPACT_CONE_LINEAR_H4: H4,H5,H6,H7,H8

PASS_REVIEW_WITHOUT_ROADMAP_AUDIT: NOT_MERGE_ELIGIBLE
PASS_REVIEW_WRONG_ROADMAP: NOT_MERGE_ELIGIBLE
PASS_REVIEW_WRONG_CAPABILITY: NOT_MERGE_ELIGIBLE
PASS_REVIEW_EXACT_ROADMAP_BINDING: EXISTING_MERGE_GATES_STILL_APPLY

LEGACY_NON_GOVERNED_TASK_COMPATIBILITY: PASS
TASK_076_BRANCH_MUTATED: NO
H5_STARTED: NO
NETWORK_USED_BY_GOVERNANCE: NO
LLM_USED_BY_GOVERNANCE: NO
PAID_API_USED_BY_GOVERNANCE: NO
```

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_roadmap_governance.py tests/test_bridge_task_authoring.py tests/aios_bridge/test_review_merge.py tests/test_bridge.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Use canonical Bridge E4 publication only.

## Acceptance Boundary

TASK-077 passes only if:

```text
CANONICAL_ROADMAP_LOCK: MACHINE_ENFORCED
ROADMAP_FINGERPRINT_BINDING: MACHINE_ENFORCED
TASK_ROADMAP_BINDING: MACHINE_ENFORCED
ROADMAP_PREFLIGHT: FAIL_CLOSED
MILESTONE_COMPLETION_CONTRACT: MACHINE_VALIDATED
ROADMAP_VS_TASK_AUTHORITY: SEPARATED
CONTROLLED_EVOLUTION: MACHINE_VALIDATED
IMPACT_CONE_REVALIDATION: SUPPORTED
ROADMAP_DRIFT_REVIEW_GATE: MACHINE_ENFORCED
CANONICAL_ROADMAP_IN_EXECUTOR_CONTEXT: REQUIRED
H_SERIES_RECONCILIATION: COMPLETE
CROSS_PROJECT_MODEL: REUSABLE
TASK_076: PRESERVED_AND_UNMERGED
H5_IMPLEMENTATION: NOT_STARTED
NETWORK/LLM/PAID_API: NONE
```

Passing TASK-077 installs governance and establishes the reconciled next step. It does not itself authorize H5 or declare H0-H8 complete.
