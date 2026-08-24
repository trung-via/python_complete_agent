# TASK-082 — H4 Canonical Knowledge Registry + Explicit Lifecycle

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: AIOS ENGINEERING H-SERIES
MILESTONE: H4
CAPABILITY_ID: H4_KNOWLEDGE_REGISTRY
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
H5_H8_AUTHORIZED: NO

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-ENGINEERING-H-SERIES","roadmap_version":"1.0","roadmap_blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d","roadmap_fingerprint":"449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"H4","capability_id":"H4_KNOWLEDGE_REGISTRY","requirement_bindings":["H4.R1","H4.R2","H4.R3","H4.R4"],"scope_in":["immutable persistable Invariant/Finding/Lesson/Skill registry","exact provenance plus explicit validation and lifecycle state","precedence-safe advisory/invariant-reference authority classes","deterministic fingerprint-guarded lifecycle operations and canonical parse/serialize"],"scope_out":["automatic Finding-to-Lesson-to-Skill-to-Guard promotion","automatic knowledge gardening merge retirement or confidence inference","H5 retrieval","H6 context compilation","H7 task working memory or preflight","H8 evaluation promotion","Bridge task review lease dispatch retry reroute merge or paid-provider authority","filesystem Git network LLM provider or paid API calls"]}

## Baseline

```text
MAIN_SHA: 8f887f828ad765f74073636f7e5ff887603fb56b
TARGET_BRANCH: ai/task-082
H0_STATUS: FORMALLY_COMPLETE
H1_STATUS: FORMALLY_COMPLETE
H2_STATUS: FORMALLY_COMPLETE
H3_STATUS: FORMALLY_COMPLETE
H3_COMPLETION_RECORD_FINGERPRINT: 4c2fe5cf07b9dcfc636c1fad80d80d6910dbe7b3d9547dc1d89dd4fb40b85df7
H4_STATUS: OPEN_MISSING
H5_H8_AUTHORIZED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/H-SERIES-v1.0.md","blob_sha":"41775383879c86dc68a7d87c0d705cfc8512f62d"},{"path":".ai/roadmaps/H-SERIES-v1.0.completions.json","blob_sha":"43659eb156dcd17845572e4d224dcbca7a114ad6"},{"path":".ai/decisions/ADR-055-AIOS-ENGINEERING-H3-FORMAL-COMPLETION-H4-KNOWLEDGE-REGISTRY-OPEN-CONTRACT-LOCK.md","blob_sha":"7f5efd995e312f510f87dddb825ba312e8affbaa"},{"path":".ai/reviews/REVIEW-081.md","blob_sha":"8d733df3bc253d4b8fdcc9a2a74036bc46dec7f3"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_engineering/harness/knowledge_registry.py","src/aios_engineering/harness/__init__.py","tests/aios_engineering/harness/test_knowledge_registry.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Objective

Implement canonical H4 as a pure deterministic long-lived technical-memory registry.

The registry must manage exactly these knowledge kinds:

```text
INVARIANT
FINDING
LESSON
SKILL
```

It must preserve exact provenance, explicit validation/lifecycle state, precedence boundaries, deterministic identity, and auditable lifecycle operations without creating any authority or later-milestone capability.

## 1. New Canonical H4 Module

Create:

```text
src/aios_engineering/harness/knowledge_registry.py
```

Public capability should be equivalent to:

```python
H4_KNOWLEDGE_REGISTRY_POLICY_VERSION = "h4-knowledge-registry-v1"
H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION = "1"

class KnowledgeKind(...): ...
class KnowledgeValidationState(...): ...
class KnowledgeLifecycleState(...): ...
class KnowledgeAuthorityClass(...): ...
class KnowledgeProvenanceKind(...): ...
class KnowledgeRegistryOperation(...): ...

@dataclass(frozen=True)
class KnowledgeProvenanceRef: ...

@dataclass(frozen=True)
class KnowledgeItem: ...

@dataclass(frozen=True)
class KnowledgeRegistryEvent: ...

@dataclass(frozen=True)
class KnowledgeRegistryState: ...

def create_empty_knowledge_registry(...): ...
def register_knowledge_item(...): ...
def set_knowledge_validation_state(...): ...
def set_knowledge_lifecycle_state(...): ...
def amend_knowledge_metadata(...): ...
def serialize_knowledge_registry(...)->bytes: ...
def parse_knowledge_registry(...)->KnowledgeRegistryState: ...
```

Exact names may be refined only when semantics remain unambiguous and tests bind the public API.

Do not introduce repository discovery, H2 graph parsing, H3 tendency recomputation, storage writes, or control-plane authority.

## 2. H4.R1 — Knowledge Kinds and Registry

`KnowledgeKind` must contain exactly:

```text
INVARIANT
FINDING
LESSON
SKILL
```

Every `KnowledgeItem` must bind at least:

```text
knowledge_id
kind
title
summary
ordered exact provenance refs
validation_state
lifecycle_state
authority_class
bounded metadata
item fingerprint
```

`knowledge_id` is stable and immutable. Free-text similarity, title similarity, path similarity, or model judgment must never create/merge/substitute an identity.

Registry item ordering must be canonical and independent of caller tuple/list iteration order for unique items.

Duplicate `knowledge_id` fails closed.

## 3. Exact Provenance

Every knowledge item requires at least one exact provenance reference.

A provenance reference must bind fields equivalent to:

```text
source_path
source_blob_sha
provenance/evidence kind
source_evidence_fingerprint
optional exact source snapshot SHA when supplied
```

Use closed provenance kinds sufficient for reviewed H-Series evidence, for example:

```text
TASK
RESULT
REVIEW
DECISION
LEARNING
H2_GRAPH
H3_ROLE_TENDENCY
INVARIANT_AUTHORITY
OTHER_EXACT
```

Exact naming may be refined but the grammar must remain closed and deterministic.

Path, blob SHA, fingerprint, optional snapshot SHA, and enum validity are all revalidated. Duplicate provenance identities fail closed.

No provenance may be synthesized from branch names, recommended executor fields, unbound prose, keyword matching, or LLM inference.

## 4. H4.R2 — Validation State

Use a closed validation contract equivalent to:

```text
UNVALIDATED
EVIDENCE_BACKED
HUMAN_APPROVED
```

Validation is explicit metadata, not an inferred score.

Allowed forward transitions should be deterministic and explicit, for example:

```text
UNVALIDATED -> EVIDENCE_BACKED
UNVALIDATED -> HUMAN_APPROVED
EVIDENCE_BACKED -> HUMAN_APPROVED
```

Same-state updates and unsupported downgrade transitions fail closed unless a more conservative equivalent contract is explicitly tested.

Every validation transition must require:

```text
exact knowledge_id
expected current item fingerprint
expected current registry fingerprint
new validation state
exact transition provenance/evidence
```

No automatic validation upgrade from test count, occurrence count, executor identity, review count, or model output.

## 5. H4.R2 — Lifecycle State

Use a closed lifecycle contract equivalent to:

```text
PROPOSED
ACTIVE
RETIRED
```

Lifecycle is orthogonal to validation.

Allowed forward transitions should be explicit and deterministic, for example:

```text
PROPOSED -> ACTIVE
PROPOSED -> RETIRED
ACTIVE -> RETIRED
```

No silent transition and no normal physical deletion.

A lifecycle transition must require the same exact registry/item fingerprint preconditions and transition provenance used by validation operations.

Unsupported resurrection/downgrade or same-state transitions fail closed under this task unless explicitly justified by ADR-055 without changing milestone semantics.

## 6. H4.R3 — Precedence / Authority Classes

Use a closed authority class that makes H4 precedence safe.

A minimal acceptable contract is equivalent to:

```text
ADVISORY
CANONICAL_INVARIANT_REFERENCE
```

Rules:

```text
FINDING -> ADVISORY only
LESSON  -> ADVISORY only
SKILL   -> ADVISORY only
INVARIANT -> ADVISORY or CANONICAL_INVARIANT_REFERENCE
```

`CANONICAL_INVARIANT_REFERENCE` means the item references an external authoritative invariant source. The H4 item itself still creates no authority.

If this class is used, require explicit invariant/decision authority provenance and an explicit validation state consistent with Human-approved evidence. Do not infer Human approval from artifact names.

No H4 item may carry Bridge task/review/lease/dispatch/retry/reroute/merge/provider authority.

## 7. H4.R4 — Deterministic Lifecycle Operations

Implement pure operations equivalent to:

```text
REGISTER
SET_VALIDATION_STATE
SET_LIFECYCLE_STATE
AMEND_METADATA
```

Each successful operation returns a new immutable `KnowledgeRegistryState` and deterministic operation evidence.

Operation evidence must bind at least:

```text
sequence/index
operation kind
knowledge_id
prior registry fingerprint
prior item fingerprint where applicable
new item fingerprint where applicable
transition/evidence fingerprint
operation/event fingerprint
```

The registry/state fingerprint must change whenever an item or event changes.

Stale expected item/registry fingerprints fail closed.

Duplicate registration fails closed.

`AMEND_METADATA` may modify only bounded advisory metadata fields under exact fingerprint preconditions. It must not change:

```text
knowledge_id
KnowledgeKind
authority class
validation state
lifecycle state
```

Those fields use their explicit contracts or are immutable.

## 8. No Kind Promotion in H4

There must be no H4 operation or result field equivalent to:

```text
PROMOTE_KIND
FINDING_TO_LESSON
LESSON_TO_SKILL
SKILL_TO_GUARD
AUTO_PROMOTE
PROMOTION_SCORE
```

An existing Finding remains a Finding for its identity in H4.

Finding → Lesson → Skill → Guard belongs to H8 and is not authorized by TASK-082.

## 9. No Automatic Gardening

H4 must not automatically:

```text
merge duplicate-looking knowledge
retire stale-looking knowledge
downgrade confidence
upgrade confidence
select best knowledge
rank knowledge
infer conflicts by semantic similarity
```

Exact duplicate IDs are validation errors, not a gardening opportunity.

H8 owns later gardening/evaluation semantics.

## 10. Canonical Parse / Serialize

Provide deterministic canonical serialization:

```text
serialize_knowledge_registry(state) -> bytes
```

and strict parsing:

```text
parse_knowledge_registry(bytes) -> validated state
```

Requirements:

```text
canonical JSON/bytes
stable key/item/event ordering
bounded input size before parsing
closed top-level/item/event/provenance schema
all nested fingerprints revalidated
registry fingerprint revalidated
unsupported enum/field/type rejected
bool-as-int rejected
malformed/oversized/tampered input rejected
non-canonical serialized bytes rejected or canonicalized only under an explicitly tested closed rule
```

Preferred strict contract: parsed bytes must equal canonical reserialization before returning a valid state.

No filesystem read/write is required.

## 11. Deterministic Identity and Fingerprints

Use existing harness canonical JSON/fingerprint helpers where semantically appropriate.

Fingerprints must cover all semantically relevant fields.

At minimum prove tamper sensitivity for:

```text
knowledge kind
knowledge ID
title/summary
provenance membership
validation state
lifecycle state
authority class
metadata
item fingerprint
event fingerprint
registry fingerprint
```

Registry content must be immutable after construction.

## 12. Hard Bounds

Define explicit hard limits for at least:

```text
knowledge items per registry
provenance refs per item
knowledge ID length
title length
summary length
metadata pairs per item
metadata key length
metadata value length / total metadata bytes
registry events
serialized registry input/output bytes
fingerprint payload bytes
source path length where not already bounded upstream
```

Every public constructor/factory/parser must enforce the relevant limits.

Boundary and overflow tests are required for every bound family. Use monkeypatched small bounds where appropriate; do not allocate giant payloads.

## 13. Pure Composition / Zero Authority

TASK-082 implementation must not:

```text
open/read/write repository files
run Git subprocesses
read control-plane artifact bodies
make network calls
call an LLM/provider
use paid API credentials
import Bridge task/review/lease/dispatch/retry/reroute/merge authority modules
```

Required receipt facts:

```text
authority_created = False
network_used = False
llm_used = False
paid_api_used = False
```

If an operation returns a receipt, it must preserve these facts exactly.

## 14. Public Exports

Update `src/aios_engineering/harness/__init__.py` only to export intentional H4 public API and bound constants.

Do not rename/remove H0-H3 public exports.

## 15. Mandatory Tests

Create:

```text
tests/aios_engineering/harness/test_knowledge_registry.py
```

Prove at minimum:

```text
H4_POLICY_SCHEMA_IDENTITY: PASS
KNOWLEDGE_KIND_EXACT_FOUR: PASS
IMMUTABLE_ITEM_AND_REGISTRY: PASS
EXACT_PROVENANCE_REQUIRED: PASS
PROVENANCE_TAMPER: REJECTED
DUPLICATE_PROVENANCE: REJECTED
DUPLICATE_KNOWLEDGE_ID: REJECTED

VALIDATION_STATE_CLOSED: PASS
VALIDATION_FORWARD_TRANSITIONS: PASS
VALIDATION_STALE_FINGERPRINT: REJECTED
VALIDATION_UNSUPPORTED_TRANSITION: REJECTED
NO_AUTOMATIC_VALIDATION_UPGRADE: PASS

LIFECYCLE_STATE_CLOSED: PASS
LIFECYCLE_FORWARD_TRANSITIONS: PASS
LIFECYCLE_STALE_FINGERPRINT: REJECTED
LIFECYCLE_UNSUPPORTED_TRANSITION: REJECTED
NO_PHYSICAL_DELETE_REQUIRED: PASS

FINDING_LESSON_SKILL_ADVISORY_ONLY: PASS
INVARIANT_REFERENCE_REQUIRES_EXPLICIT_AUTHORITY_PROVENANCE: PASS
INVARIANT_REFERENCE_CREATES_AUTHORITY: NO
BRIDGE_AUTHORITY_SURFACE: NONE

REGISTER_EVENT_AUDIT: PASS
VALIDATION_EVENT_AUDIT: PASS
LIFECYCLE_EVENT_AUDIT: PASS
METADATA_AMEND_EVENT_AUDIT: PASS
STALE_REGISTRY_FINGERPRINT: REJECTED
KIND_CHANGE_OPERATION: NONE
PROMOTION_OPERATION: NONE
AUTO_GARDENING: NONE

CANONICAL_ORDERING: PASS
CANONICAL_SERIALIZE_PARSE_ROUND_TRIP: PASS
NONCANONICAL_OR_MALFORMED_BYTES: REJECTED
UNKNOWN_FIELDS_OR_ENUMS: REJECTED
ITEM_EVENT_REGISTRY_TAMPER: REJECTED
DUPLICATE_PUBLIC_FACTORY_INPUTS: REJECTED
ALL_HARD_BOUNDS: ENFORCED
BOOL_AS_INT: REJECTED

WORKTREE_READ: NO
GIT_SUBPROCESS: NO
NETWORK: NO
LLM: NO
PAID_API: NO
BRIDGE_AUTHORITY_IMPORT: NO
H5_H8_IMPLEMENTATION: NO
ZERO_AUTHORITY_RECEIPT: PASS
```

## 16. Validation Commands

Run exactly:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_engineering/harness/test_knowledge_registry.py tests/aios_engineering/harness/test_role_tendencies.py tests/aios_engineering/harness/test_structural_experience_graph.py -q
.\venv\Scripts\python.exe -m pytest tests/ -q
git diff --check
```

Publish only through canonical Bridge E4.

## Acceptance Boundary

TASK-082 passes implementation review only if:

```text
H4_R1_KNOWLEDGE_REGISTRY: PASS
H4_R2_PROVENANCE_VALIDATION_LIFECYCLE: PASS
H4_R3_PRECEDENCE_BOUNDARY: PASS
H4_R4_DETERMINISTIC_LIFECYCLE_OPERATIONS: PASS
KIND_PROMOTION: NONE
AUTO_GARDENING: NONE
ROUTING_SELECTION_AUTHORITY: NONE
BRIDGE_AUTHORITY: NONE
H5_H8_NEW_CAPABILITY: NONE
NETWORK_LLM_PAID_API: NONE
```

Invariant remains:

```text
TASK-082 PASS != H4 COMPLETE
```

After independent PASS review, a separate formal H4 completion record is required before H5 Hybrid Retrieval may open.
