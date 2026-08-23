# TASK-078 — H1 Dual-Provenance Repository + Experience Manifest Recovery

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS ENGINEERING H-SERIES / H1 RECOVERY
MILESTONE: H1
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex

## Baseline

```text
MAIN_SHA: 8fe5724d5121e53313bfefabedd26df6e1e307c1
TARGET_BRANCH: ai/task-078
CANONICAL_ROADMAP: .ai/roadmaps/H-SERIES-v1.0.md
CANONICAL_ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
CANONICAL_ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
H0_COMPLETION_ARTIFACT: .ai/roadmaps/H-SERIES-v1.0.completions.json
H0_COMPLETION_ARTIFACT_BLOB_SHA: abcce5042bdaff7c4b0abfe676d05321adf02456
H0_COMPLETION_RECORD_FINGERPRINT: 9b5c5735b1b067ad150033af9e6536e4d87ed1d4f013c9da87f1b3dcf8f3256c
H0_STATUS: FORMALLY_COMPLETE
H1_STATUS: PARTIAL
TASK_076: PRESERVE_UNMERGED
H2_NEW_CANONICAL_WORK: NOT_AUTHORIZED
H3_NEW_CANONICAL_WORK: NOT_AUTHORIZED
H4_H8: NOT_AUTHORIZED
NETWORK_CALL_ALLOWED: NO
LLM_CALL_ALLOWED: NO
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
```

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-ENGINEERING-H-SERIES","roadmap_version":"1.0","roadmap_blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d","roadmap_fingerprint":"449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"H1","capability_id":"H1_REPOSITORY_EXPERIENCE_MANIFEST","requirement_bindings":["H1.R2","H1.R3"],"scope_in":["bounded ai-control engineering-experience manifest","exact repository plus control-plane dual provenance binding","preserve existing H1 repository discovery as H1.R1 evidence"],"scope_out":["H2 structural or experience graph","H3 executor tendencies or role expansion","H4-H8 knowledge retrieval context memory evaluation capabilities","Bridge authority or TASK-076 salvage"]}

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/roadmaps/H-SERIES-v1.0.completions.json","blob_sha":"abcce5042bdaff7c4b0abfe676d05321adf02456"},{"path":".ai/decisions/ADR-050-AIOS-ENGINEERING-CANONICAL-ROADMAP-LOCK-CONTROLLED-EVOLUTION-CONTRACT-LOCK.md","blob_sha":"334b610b2c221ac20b2b9946142a0baed8952690"},{"path":".ai/decisions/ADR-051-AIOS-ENGINEERING-H0-FORMAL-COMPLETION-H1-RECOVERY-CONTRACT-LOCK.md","blob_sha":"0a358892c628e359a8dda5db8f7b27426c156cec"},{"path":".ai/decisions/ADR-043-AIOS-ENGINEERING-H1-REPOSITORY-SNAPSHOT-DISCOVERY-PROVENANCE-CONTRACT-LOCK.md","blob_sha":"140e1a03593e31f6681016ae45b427f9b16ee8c9"},{"path":".ai/reviews/REVIEW-070.md","blob_sha":"a4e7e170cd3dbb622bcfef3827433838c549ad57"},{"path":".ai/reviews/REVIEW-077.md","blob_sha":"aedf3f69e0550d19930e1bf585b3a6aa34149ee2"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/__init__.py","src/aios_engineering/harness/experience.py","tests/aios_engineering/harness/test_experience.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

The marker set above is complete execution authority for TASK-078. It creates no H2/H3/H4-H8 authority, no TASK-076 merge/rebinding authority, and no network/model/paid-provider authority.

## Objective

Close only the missing canonical H1 surface identified by the accepted TASK-077 reconciliation:

```text
H1.R1 — existing repository manifest: preserve/reuse; do not rewrite
H1.R2 — add bounded TASK/RESULT/review/decision/learning experience inventory
H1.R3 — bind repository and control-plane provenance into one deterministic zero-authority manifest
```

The repository currently has a sound single-snapshot `RepositoryDiscoveryResult` in `discovery.py`. The defect is architectural coverage: one `main` snapshot cannot prove canonical control-plane TASK/review/decision experience that lives on `ai-control`.

TASK-078 must therefore add a second exact control-plane snapshot surface and a deterministic dual-provenance H1 result while leaving existing repository discovery behavior unchanged.

## 1. Preserve Existing H1.R1 Implementation

`src/aios_engineering/harness/discovery.py` is read-only for this task.

Do not rewrite, rename, broaden, or version-bump existing H1 repository discovery contracts. Existing exact repository commit/tree/blob discovery remains the canonical H1.R1 evidence source.

TASK-078 may import and consume:

```text
RepositoryDiscoveryResult
RepositorySnapshotRef
RepositoryEvidenceRef
canonical_json_bytes / compute_sha256
existing validation helpers where safe
```

but must not mutate an existing `RepositoryDiscoveryResult` or silently rediscover a different repository snapshot.

## 2. New Experience Manifest Module

Create:

```text
src/aios_engineering/harness/experience.py
```

The public contract should provide equivalent concepts to the following; exact names may vary only when a clearer bounded design is justified:

```python
H1_EXPERIENCE_POLICY_VERSION = "h1-experience-v1"
EXPERIENCE_SCHEMA_VERSION = "1"

class ExperienceArtifactKind(...):
    TASK = "TASK"
    RESULT = "RESULT"
    REVIEW = "REVIEW"
    DECISION = "DECISION"
    LEARNING = "LEARNING"

class ExperienceSurface(...):
    REPOSITORY = "REPOSITORY"
    CONTROL_PLANE = "CONTROL_PLANE"

@dataclass(frozen=True)
class ControlPlaneSnapshotRef: ...

@dataclass(frozen=True)
class ExperienceArtifactRef: ...

@dataclass(frozen=True)
class ControlPlaneExperienceManifest: ...

@dataclass(frozen=True)
class RepositoryExperienceManifest: ...
```

All public result contracts must be immutable, bounded, canonically ordered, provenance-bearing, and fingerprint-verified on construction.

## 3. Exact Control-Plane Snapshot Contract

Control-plane discovery must accept one exact lowercase 40-hex Git commit SHA only.

Symbolic refs, branch names (`ai-control`), abbreviated SHAs, worktree paths, and moving refs are not provenance inputs.

From that exact commit, derive and bind the exact tree SHA using local Git objects only.

The result must explicitly preserve:

```text
control_commit_sha
control_tree_sha
schema_version
```

No hidden substitution of current `origin/ai-control` is allowed after the exact commit is supplied.

## 4. Local-Only Git Boundary

Experience discovery must use local Git object access only.

Required invariants:

```text
GIT_NO_LAZY_FETCH = 1
NETWORK_FALLBACK = NO
SUBMODULE_RECURSION = NO
WORKTREE_CONTENT_PROVENANCE = NO
UNTRACKED_CONTENT = NO
CALLER_PROVIDER_CREDENTIAL_INHERITANCE = NO
CALLER_GIT_OVERRIDE_INHERITANCE = NO
```

Use a closed child-process environment equivalent in safety to existing H1 repository discovery. Do not copy the full caller environment.

If the exact control commit/tree/blob objects are unavailable locally, fail closed instead of fetching.

## 5. Bounded Experience Artifact Classification

Inventory only exact regular Git blobs relevant to H1 engineering experience.

Required path-based classes:

```text
.ai/tasks/**       -> TASK
.ai/results/**     -> RESULT
.ai/reviews/**     -> REVIEW
.ai/decisions/**   -> DECISION
```

Also support a conservative explicit set of learning-evidence prefixes when already present, for example:

```text
.ai/learning/**
.ai/lessons/**
.ai/findings/**
.ai/skills/**
.ai/knowledge/**
```

These paths are classified as `LEARNING` only by explicit path identity. H1 must not parse them into Finding/Lesson/Skill semantics; that would be H4 territory.

Unknown/non-experience paths are not experience evidence. If exclusions are represented, they must be bounded and deterministic; it is acceptable to omit irrelevant paths from the experience result as long as stream/input bounds are still enforced and malformed Git records fail closed.

## 6. Dual-Surface Experience Inventory

Canonical H1.R2 requires relevant experience from both evidence surfaces where applicable:

```text
REPOSITORY surface
  - consume the already-frozen RepositoryDiscoveryResult
  - select existing .ai/results/** and explicit learning-evidence paths when present in that exact repository snapshot

CONTROL_PLANE surface
  - discover TASK / REVIEW / DECISION / RESULT / learning paths from the independently frozen control commit/tree
```

Every `ExperienceArtifactRef` must carry enough identity to distinguish the same path appearing on both surfaces, including at minimum:

```text
surface
path
blob_sha
artifact_kind
```

Canonical ordering must be deterministic across surfaces, e.g. by `(surface, path, blob_sha, kind)` or another explicitly locked equivalent.

Duplicate exact identities may be rejected or deduplicated only under an explicit deterministic rule. Conflicting same-surface path identities must fail closed.

## 7. Repository + Control-Plane Dual-Provenance Binding

Build one immutable H1 `RepositoryExperienceManifest` that binds, at minimum:

```text
repository snapshot commit + tree
repository discovery fingerprint
repository candidate-set fingerprint
control-plane snapshot commit + tree
control-plane experience-manifest fingerprint
combined experience evidence
combined experience fingerprint
schema/policy version
```

The combined fingerprint must be sensitive to at least:

```text
repository commit change
repository tree change
repository discovery fingerprint change
control commit change
control tree change
control evidence path change
control evidence blob change
artifact kind/surface change
repository RESULT/learning evidence change
```

Changing tuple/input ordering without changing canonical content must not change the final fingerprint.

The dual manifest is evidence only and creates zero authority.

## 8. No Content-Semantic Inference

H1 is a manifest layer.

Do NOT:

```text
read artifact bodies to infer lessons/findings/skills
infer executor quality or tendencies
build symbol/component/import graphs
rank task relevance beyond existing H1 input preservation
perform semantic/vector retrieval
compile context packs
promote/garden knowledge
```

Path, Git object type/mode, exact blob SHA, exact snapshot provenance, and explicit artifact class are sufficient for TASK-078.

## 9. Hard Bounds

Add finite policy constants and enforce them while consuming Git output, including bounded equivalents for:

```text
maximum control-plane tree entries
maximum control-plane Git stream bytes
maximum individual Git tree record bytes
maximum experience evidence count
maximum serialized/fingerprint payload inputs where applicable
```

Do not capture an unbounded `git ls-tree -r` stream into memory before validating the stream bound.

Malformed NUL-delimited Git tree records, invalid modes/types/SHAs, unsafe paths, oversize records, duplicate conflicting paths, and bound overflow must fail closed.

## 10. Public API

Update `src/aios_engineering/harness/__init__.py` to export only the stable H1 experience-manifest contracts/functions needed by downstream H-Series milestones.

Do not export private Git subprocess helpers.

Do not modify `src/aios_engineering/harness/discovery.py`.

## 11. Zero-Authority Invariant

TASK-078 is repository/control-plane evidence intelligence only.

The new module must not import Bridge authority modules to obtain state, authorization, leases, dispatch policy, merge state, provider grants, or runtime authority.

It may operate on a repository path and exact local Git object identities supplied by the caller.

No network, LLM, model provider, paid API, executor routing, retry/failover, task mutation, review mutation, or branch merge is allowed.

## 12. TASK-076 and Later-Milestone Boundary

TASK-078 must not inspect or modify `ai/task-076` as an implementation dependency.

Historical references to TASK-076 in reconciliation are context only. No graph salvage, H2 rebind, H3 executor tendency, H4 Knowledge Registry, H5 retrieval, H6 compiler, H7 memory/preflight, or H8 evaluation/gardening code is authorized.

## Mandatory Tests

Create `tests/aios_engineering/harness/test_experience.py` proving at minimum:

```text
EXACT_CONTROL_COMMIT_REQUIRED: PASS
SYMBOLIC_CONTROL_REF_REJECTED: PASS
EXACT_CONTROL_TREE_BOUND: PASS
WORKTREE_BYTES_USED: NO
NETWORK_FALLBACK: NO
GIT_NO_LAZY_FETCH: EXACTLY_1
FULL_CALLER_ENV_COPIED: NO
PROVIDER_CREDENTIAL_PROPAGATED: NO
CALLER_GIT_OVERRIDE_PROPAGATED: NO

CONTROL_TASK_CLASSIFICATION: PASS
CONTROL_REVIEW_CLASSIFICATION: PASS
CONTROL_DECISION_CLASSIFICATION: PASS
CONTROL_RESULT_CLASSIFICATION: PASS
EXPLICIT_LEARNING_PATH_CLASSIFICATION: PASS
UNKNOWN_CONTROL_PATH_PROMOTED: NO
NON_REGULAR_ENTRY_PROMOTED: NO
MALFORMED_GIT_RECORD: REJECTED
UNSAFE_PATH: REJECTED
DUPLICATE_CONFLICTING_PATH: REJECTED
CONTROL_STREAM_BOUND: ENFORCED
CONTROL_ENTRY_BOUND: ENFORCED
EXPERIENCE_COUNT_BOUND: ENFORCED

REPOSITORY_RESULT_EVIDENCE_INCLUDED: PASS
REPOSITORY_LEARNING_EVIDENCE_INCLUDED_WHEN_PRESENT: PASS
CONTROL_EXPERIENCE_EVIDENCE_INCLUDED: PASS
SAME_PATH_DIFFERENT_SURFACE_UNAMBIGUOUS: PASS
CANONICAL_ORDER_PERMUTATION_INVARIANT: PASS

REPOSITORY_COMMIT_CHANGE_FINGERPRINT_SENSITIVE: PASS
REPOSITORY_TREE_CHANGE_FINGERPRINT_SENSITIVE: PASS
REPOSITORY_DISCOVERY_CHANGE_FINGERPRINT_SENSITIVE: PASS
CONTROL_COMMIT_CHANGE_FINGERPRINT_SENSITIVE: PASS
CONTROL_TREE_CHANGE_FINGERPRINT_SENSITIVE: PASS
CONTROL_BLOB_CHANGE_FINGERPRINT_SENSITIVE: PASS
ARTIFACT_KIND_CHANGE_FINGERPRINT_SENSITIVE: PASS
DUAL_PROVENANCE_MANIFEST_FINGERPRINT: PASS

EXISTING_H1_DISCOVERY_REGRESSION: PASS
BRIDGE_IMPORT_FOR_AUTHORITY: NO
NETWORK_USED: NO
LLM_USED: NO
PAID_API_USED: NO
TASK_076_MUTATED: NO
H2_H8_IMPLEMENTED: NO
```

## Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_discovery.py tests/aios_engineering/harness/test_experience.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Use canonical Bridge E4 publication only.

## Acceptance Boundary

TASK-078 is reviewable when:

```text
ROADMAP_BINDING: H1 / H1.R2 + H1.R3 EXACT
H0_FORMAL_COMPLETION_GATE: SATISFIED
EXISTING_H1_R1_DISCOVERY: PRESERVED
CONTROL_PLANE_EXPERIENCE_MANIFEST: IMPLEMENTED
REPOSITORY_PLUS_CONTROL_DUAL_PROVENANCE: IMPLEMENTED
TASK_RESULT_REVIEW_DECISION_LEARNING_INVENTORY: BOUNDED_AND_DETERMINISTIC
ZERO_AUTHORITY: PRESERVED
FULL_REPOSITORY_TESTS: PASS
TASK_076: UNCHANGED_AND_UNMERGED
H2_H8_NEW_CAPABILITY: NOT_IMPLEMENTED
NETWORK_LLM_PAID_API: NONE
```

TASK-078 PASS will provide implementation evidence for the missing H1.R2/H1.R3 surface. It does not itself create canonical H1 milestone completion. After independent review confirms H1.R1 remains valid and H1.R2/H1.R3 are complete, ChatGPT/Human governance may mint the formal H1 completion record required before canonical H2 progression resumes.
