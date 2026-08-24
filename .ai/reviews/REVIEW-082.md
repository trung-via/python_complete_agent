# REVIEW-082 — H4 Canonical Knowledge Registry + Explicit Lifecycle

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-082
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 1e2574bccb8944ff31709ce7ba8349229e327df9
REVIEWED_BASE_MAIN_SHA: 8f887f828ad765f74073636f7e5ff887603fb56b
TASK_ARTIFACT_BLOB_SHA: 4b0fa4d4fbaa6064c6be66eda4a997eca83f4893
RESULT_BLOB_SHA: 999ac3fdc744543474ad15a10e11eb3448cbb10e
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 1
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: PASS_REPORTED
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-ENGINEERING-H-SERIES
ROADMAP_VERSION: 1.0
MILESTONE: H4
CAPABILITY_ID: H4_KNOWLEDGE_REGISTRY
H4_FORMAL_COMPLETION: NO
H5_H8_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
BRANCH: ai/task-082
BASE_MAIN_SHA: 8f887f828ad765f74073636f7e5ff887603fb56b
REVIEWED_TASK_HEAD_SHA: 1e2574bccb8944ff31709ce7ba8349229e327df9
STATUS_VS_BASE: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 8f887f828ad765f74073636f7e5ff887603fb56b
CUMULATIVE_SCOPE: EXACT
```

Observed cumulative task delta is limited to the three TASK-authorized implementation/test paths plus Bridge-generated RESULT:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/knowledge_registry.py
tests/aios_engineering/harness/test_knowledge_registry.py
.ai/results/RESULT-082.md
```

Reported validation evidence:

```text
TARGETED_H4_SUITE: 50 passed, 0 skipped, 0 failed
FULL_REPOSITORY_TESTS: 2505 passed, 7 skipped, 0 failed
GIT_DIFF_CHECK: PASS
NETWORK/LLM/PAID_API: NONE
```

## Finding B1 — KnowledgeItem metadata is not deeply immutable

STATUS: BLOCKING
SEVERITY: CONTRACT_INTEGRITY

TASK-082 explicitly requires registry content to be immutable after construction and fingerprints to remain tamper-sensitive for metadata. The implementation declares `KnowledgeItem` as `@dataclass(frozen=True)`, but its public `metadata` field is a mutable `dict[str, str]` and the constructed object stores that dict directly.

Therefore code can mutate a successfully constructed item in place, for example conceptually:

```python
item = KnowledgeItem.create(..., metadata={"domain": "harness"})
old_fp = item.item_fingerprint
item.metadata["domain"] = "tampered"
assert item.item_fingerprint == old_fp
```

The same mutable item may already be contained by an otherwise frozen `KnowledgeRegistryState`, so registry content can change without changing either `item_fingerprint` or `registry_fingerprint`. This violates the H4 immutable persistable registry contract and deterministic fingerprint integrity.

The current immutability regression only proves frozen attribute assignment (`item.title = ...` and `reg.items = ...`) and does not attempt nested metadata mutation, which is why the defect is not detected by the reported green test suite.

### Required repair

1. Make exposed knowledge metadata structurally/deeply immutable after construction. Use a deterministic immutable representation or a read-only mapping that cannot be mutated through the public object.
2. Preserve canonical serialization, deterministic metadata ordering, equality semantics, and `AMEND_METADATA` behavior by creating a new immutable item/state rather than mutating existing content.
3. Add direct regressions proving:
   - direct mutation of `KnowledgeItem.metadata` is impossible;
   - registry-contained item metadata cannot be mutated through `state.items` / `get_item()`;
   - caller-owned input metadata mutation after construction cannot alter the constructed item;
   - failed mutation cannot change serialized bytes, `item_fingerprint`, or `registry_fingerprint`;
   - `amend_knowledge_metadata()` remains the only supported metadata-change path and returns a new item/state with new fingerprints.
4. Keep the FIX strictly within TASK-082 authorized paths. Do not open H5, alter Bridge authority, add promotion/gardening, or broaden H4 semantics.

## Non-blocking audit results

The following reviewed boundaries are acceptable at this snapshot and must remain preserved by the FIX:

```text
KNOWLEDGE_KIND_EXACT_FOUR: PASS
EXACT_PROVENANCE_REQUIRED: PASS
VALIDATION_FORWARD_ONLY: PASS
LIFECYCLE_FORWARD_ONLY: PASS
FINDING_LESSON_SKILL_ADVISORY_ONLY: PASS
CANONICAL_INVARIANT_REFERENCE_BOUNDARY: PASS
KIND_PROMOTION: NONE
AUTO_GARDENING: NONE
CANONICAL_PARSE_SERIALIZE: PASS
ZERO_BRIDGE_AUTHORITY: PASS
NETWORK_LLM_PAID_API: NONE
CUMULATIVE_SCOPE: EXACT
```

## Decision

```text
TASK-082: CHANGES_REQUIRED
APPROVED: NO
MERGE_AUTHORIZED: NO
BLOCKERS_REMAINING: 1
NEXT_ACTION: FIX TASK-082
H4_FORMAL_COMPLETION: NO
H5_H8_AUTHORIZED: NO
```
