# TASK-081 — H3 Canonical Component Role Summaries + Executor Tendencies

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: AIOS ENGINEERING H-SERIES
MILESTONE: H3
CAPABILITY_ID: H3_ROLE_SUMMARIES_EXECUTOR_TENDENCIES
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
H4_H8_AUTHORIZED: NO

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-ENGINEERING-H-SERIES","roadmap_version":"1.0","roadmap_blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d","roadmap_fingerprint":"449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"H3","capability_id":"H3_ROLE_SUMMARIES_EXECUTOR_TENDENCIES","requirement_bindings":["H3.R1","H3.R2","H3.R3","H3.R4"],"scope_in":["component-level technical role summaries from exact H2 plus reviewed artifact-role evidence","global H0 must-not-own authority boundary on every H3 component summary","bounded evidence-only executor tendency profiles from exact H2 experience edges","deterministic provenance-bound fingerprints and zero-authority receipt"],"scope_out":["executor selection routing scoring substitution or dispatch","causal quality grades or blame","H4 knowledge registry lifecycle confidence or promotion","H5-H8 capabilities","network LLM provider or paid API calls"]}

## Baseline

```text
MAIN_SHA: 4d7e5a6be68ef0aaf0ed7db6927c26c5ddbb61af
TARGET_BRANCH: ai/task-081
H0_STATUS: FORMALLY_COMPLETE
H1_STATUS: FORMALLY_COMPLETE
H2_STATUS: FORMALLY_COMPLETE
H2_COMPLETION_RECORD_FINGERPRINT: 39540b97aa785b96a19ad631ba2a041d1ce8c3473cfa4b74888cb98536e8957a
H3_STATUS: OPEN_PARTIAL
H4_H8_AUTHORIZED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/roadmaps/H-SERIES-v1.0.completions.json","blob_sha":"9b40eb601c0f92562f08a2e62b653ab253eac45c"},{"path":".ai/decisions/ADR-054-AIOS-ENGINEERING-H2-FORMAL-COMPLETION-H3-CANONICAL-OPEN-CONTRACT-LOCK.md","blob_sha":"07365dfdc4d5bee520a0edebd0f1f7258cdafe92"},{"path":".ai/reviews/REVIEW-075.md","blob_sha":"4560ec9aee6b01aaf6f0d187f31877b67149b7dc"},{"path":".ai/reviews/REVIEW-080.md","blob_sha":"08ce94f39f4cbb6901b95e8c3a1d00e77a85cd3e"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/role_tendencies.py","src/aios_engineering/harness/__init__.py","tests/aios_engineering/harness/test_role_tendencies.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Objective

Complete canonical H3 implementation by composing already-reviewed H2 structural/experience evidence with historical TASK-075 artifact-role summaries.

The result must answer, deterministically and without authority expansion:

```text
For each selected H2 structural component:
  what technical artifact surfaces are observed inside it?
  what H0 authority surfaces must it never own?

For each exactly evidenced executor:
  what tasks/components/review findings are co-observed in repository experience?
```

The result must not answer:

```text
which executor should run next?
which executor is best?
which executor caused a defect?
which component owns a business/domain concept not present in exact evidence?
```

## 1. Preserve Historical Supporting Implementation

Do not modify:

```text
src/aios_engineering/harness/roles.py
src/aios_engineering/harness/structural_experience_graph.py
src/aios_engineering/harness/graph.py
src/aios_engineering/harness/ranking.py
src/aios_engineering/harness/experience.py
src/aios_engineering/harness/discovery.py
```

`roles.py` remains historical reviewed evidence and a supporting input. Its old H3 labels do not by themselves imply canonical H3 completion.

Reuse public types such as:

```text
RepositoryRoleSummaryResult
RepositoryRoleSummary
ArtifactRole
RepositoryStructuralExperienceGraphResult
H2GraphNodeKind
H2GraphRelation
HarnessReceipt
```

Do not add another Python AST parser, repository discovery pass, H2 graph parser, or control-plane artifact parser.

## 2. New Canonical H3 Composition Module

Create:

```text
src/aios_engineering/harness/role_tendencies.py
```

The public contract should be equivalent in capability to:

```python
H3_ROLE_TENDENCY_POLICY_VERSION = "h3-role-tendency-v1"
H3_ROLE_TENDENCY_SCHEMA_VERSION = "1"

class H3MustNotOwn(...): ...

@dataclass(frozen=True)
class ComponentRoleSummary: ...

@dataclass(frozen=True)
class ExecutorComponentObservation: ...

@dataclass(frozen=True)
class ExecutorTendencyProfile: ...

@dataclass(frozen=True)
class RepositoryRoleTendencyResult: ...

def summarize_repository_roles_and_executor_tendencies(...): ...
```

Exact naming may be refined only when meaning remains unambiguous and tests bind the public API.

## 3. H3.R1 — Component Technical Role Summaries

Build one deterministic summary for each H2 structural component represented in the supplied H2 graph.

A summary must bind at least:

```text
component_id
component structural path/kind
exact member file identities represented by H2
observed ArtifactRole values for member files where TASK-075 role evidence exists
bounded symbol count / observed symbol evidence count
bounded inbound/outbound component relationship counts where represented by H2
fixed must-not-own authority tuple
summary fingerprint
```

Positive technical ownership is evidence-only:

```text
SOURCE_IMPLEMENTATION
PACKAGE_EXPORT_SURFACE
TEST_ARTIFACT
CONTRACT_ARTIFACT
DOCUMENTATION_ARTIFACT
CONFIGURATION_ARTIFACT
EXECUTABLE_ENTRYPOINT
OTHER_ARTIFACT
```

Do not translate path names into business/domain responsibilities. For example, a component path containing `payment`, `bridge`, `agent`, or `product` is not sufficient evidence to manufacture a domain ownership statement.

If an H2 member file has no matching historical role summary, represent the role as absent/unobserved according to a closed contract; do not guess.

## 4. H3.R1 — Global Must-Not-Own Boundary

Every component summary must include the exact immutable H0 negative-authority set:

```text
BRIDGE_TASK_AUTHORITY
BRIDGE_REVIEW_AUTHORITY
LEASE_AUTHORITY
EXECUTOR_DISPATCH_AUTHORITY
RETRY_REROUTE_AUTHORITY
MERGE_AUTHORITY
PAID_PROVIDER_AUTHORITY
```

The order must be canonical and stable.

No task input, component name, or repository prose may remove these boundaries.

Do not add component-specific negative responsibility unless exact Human-approved machine evidence already exists under this task's closed contract. TASK-081 does not require inventing a new free-form negative-role language.

## 5. H3.R2 — Bounded Role-Aware Composition

Before any complete H3 result is returned, revalidate exact upstream compatibility.

At minimum prove:

```text
H2 graph object is fingerprint-valid under its own contract
role-summary result is fingerprint-valid under its own contract
repository snapshot identities are compatible
ranking/role-summary identities used by H2 and TASK-075 evidence are compatible where exposed by the public contracts
member file path/blob identities match exactly before ArtifactRole is attached to a component
```

A path-only match is insufficient when both sides expose blob identity.

If the supplied upstream objects are inconsistent or tampered, fail closed before returning a result/receipt.

Canonical ordering must not depend on incidental tuple/dict/set iteration order.

## 6. H3.R3 — Evidence-Based Executor Tendencies

Construct executor profiles only from exact H2 experience graph evidence.

Allowed source relations:

```text
TASK_EXECUTED_BY_EXECUTOR
TASK_TOUCHES_COMPONENT
TASK_HAS_REVIEW_FINDING
```

For each exact executor node observed through `TASK_EXECUTED_BY_EXECUTOR`, summarize bounded evidence such as:

```text
executor_id
observed task IDs
observed task count
per-component co-observed task counts
co-observed component IDs
co-observed review finding IDs/count
source H2 graph fingerprint/provenance
profile fingerprint
```

Relationship semantics:

```text
executor E is observed on task T
T touched component C
T has review finding F
```

may produce co-observation in E's profile.

It must not be renamed or interpreted as:

```text
E caused F
E is weak at C
E should/should-not be selected for C
```

No profile may be created from `RECOMMENDED_EXECUTOR`, dispatch candidate ranking, branch name, prose, or an executor string that is not represented by exact H2 executor evidence.

## 7. Multiple Executor Observations

If H2 contains multiple exact executor observations for the same task:

```text
preserve each executor observation
build separate executor profiles
allow the same task/component/finding to be co-observed in multiple profiles
never choose a true/preferred executor
```

A profile is descriptive evidence, not causal attribution.

Tests must explicitly cover this case.

## 8. H3.R4 — Advisory-Only Contract

The H3 result and receipt must contain no authority-bearing recommendation surface.

Forbidden public result fields/concepts include equivalents of:

```text
preferred_executor
recommended_executor
routing_score
selection_score
should_route
should_retry
replacement_executor
winner
quality_grade
```

Do not add dispatch/routing methods or imports from Bridge authority modules.

Required zero-authority receipt facts:

```text
authority_created = False
network_used = False
llm_used = False
paid_api_used = False
```

## 9. Deterministic Result Identity

The top-level result must bind at minimum:

```text
policy/schema version
source H2 graph fingerprint
source role-summary fingerprint
repository snapshot identity
component role summaries
executor tendency profiles
explicit bounded accounting for omitted/unobserved role evidence where applicable
result fingerprint
```

Tampering with any component summary, executor observation/profile, upstream identity, or evidence membership must reject or alter the result fingerprint.

Canonical serialization must use existing harness deterministic fingerprint helpers where appropriate.

## 10. Bounds

Define hard bounds for at least:

```text
component summaries
member files per component
artifact roles per component
executors
observed tasks per executor
component observations per executor
review findings per executor
count pairs / observation records
result fingerprint payload or serialized result size
```

Boolean values must not silently satisfy integer fields.

Duplicate identities fail closed unless the contract explicitly defines canonical deduplication from identical upstream evidence.

Bound failure returns no complete result/receipt.

## 11. No New Body Reads / No New Git or Network Surface

TASK-081 is a pure composition layer over already-built objects.

It must not:

```text
read repository worktree files
run Git subprocesses
read control-plane artifact bodies
perform network access
call an LLM/provider
use paid API credentials
```

No new local Git plumbing is needed because exact evidence has already been verified upstream.

## 12. Public Exports

Update `src/aios_engineering/harness/__init__.py` only to export the intentional H3 public API.

Do not rename or remove historical public exports from TASK-075 or H2.

## 13. Mandatory Tests

Create:

```text
tests/aios_engineering/harness/test_role_tendencies.py
```

Prove at minimum:

```text
H3_POLICY_SCHEMA_IDENTITY: PASS
H2_AND_ROLE_INPUT_REVALIDATION: PASS
REPOSITORY_SNAPSHOT_CROSS_BINDING: PASS
PATH_BLOB_MATCH_REQUIRED_FOR_ARTIFACT_ROLE: PASS

COMPONENT_SUMMARY_FOR_EACH_H2_COMPONENT: PASS
COMPONENT_MEMBER_FILES_CANONICAL: PASS
OBSERVED_ARTIFACT_ROLES_EXACT: PASS
MISSING_ROLE_EVIDENCE_NOT_GUESSED: PASS
GLOBAL_MUST_NOT_OWN_SET_EXACT: PASS
GLOBAL_MUST_NOT_OWN_SET_CANNOT_BE_REMOVED: PASS
NO_BUSINESS_DOMAIN_ROLE_INFERENCE: PASS

EXECUTOR_PROFILE_FROM_H2_EXECUTOR_EDGE_ONLY: PASS
TASK_COMPONENT_COOBSERVATION: PASS
TASK_REVIEW_FINDING_COOBSERVATION: PASS
NO_EXECUTOR_EDGE_NO_PROFILE: PASS
MULTIPLE_EXECUTORS_ONE_TASK_PRESERVED: PASS
NO_PREFERRED_OR_TRUE_EXECUTOR_SELECTION: PASS
NO_CAUSAL_DEFECT_ATTRIBUTION_FIELD: PASS

ORDER_INDEPENDENCE: PASS
UPSTREAM_TAMPER: REJECTED
COMPONENT_PROFILE_TAMPER: REJECTED_OR_FINGERPRINT_CHANGES
EXECUTOR_PROFILE_TAMPER: REJECTED_OR_FINGERPRINT_CHANGES
DUPLICATE_IDENTITY: REJECTED
ALL_HARD_BOUNDS: ENFORCED
BOOL_AS_INT: REJECTED

WORKTREE_READ: NO
GIT_SUBPROCESS: NO
NETWORK: NO
LLM: NO
PAID_API: NO
BRIDGE_AUTHORITY_IMPORT: NO
H4_H8_IMPLEMENTATION: NO
ZERO_AUTHORITY_RECEIPT: PASS
```

## 14. Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_role_tendencies.py tests/aios_engineering/harness/test_structural_experience_graph.py tests/aios_engineering/harness/test_roles.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Publish only through canonical Bridge E4.

## Acceptance Boundary

TASK-081 passes implementation review only if:

```text
H3_R1_COMPONENT_ROLE_SUMMARIES: PASS
H3_R1_MUST_NOT_OWN_BOUNDARY: PASS
H3_R2_BOUNDED_ROLE_AWARE_SUMMARIES: PASS
H3_R3_EXECUTOR_TENDENCIES: PASS
H3_R4_ADVISORY_PROVENANCE_BOUNDARY: PASS
ROUTING_SELECTION_AUTHORITY: NONE
CAUSAL_QUALITY_JUDGMENT: NONE
H4_H8_NEW_CAPABILITY: NONE
NETWORK_LLM_PAID_API: NONE
```

Invariant remains:

```text
TASK-081 PASS != H3 COMPLETE
```

After independent PASS review, a separate formal H3 completion record is required before H4 Knowledge Registry may open.