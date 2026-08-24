# REVIEW-078 — H1 Dual-Provenance Repository + Experience Manifest Recovery

STATUS: PASS
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
MERGED_TO_MAIN: NO
AUTO_MERGE_EXECUTED: NO

TASK_ID: TASK-078
REVIEWED_TASK_HEAD_SHA: a51e9c33cd66dc262f13063747295609d7b7df97
REVIEWED_BASE_MAIN_SHA: 8fe5724d5121e53313bfefabedd26df6e1e307c1
TASK_ARTIFACT_BLOB_SHA: 5b9a01ec09a105169171d85bd08ef3c6d32a03fe
RESULT_BLOB_SHA: 14bc54242979454f7a9e297cf432222f2c4719ab
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 0
CODE_AUDIT: PASS
CANONICAL_TESTS: PASS
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-ENGINEERING-H-SERIES
ROADMAP_VERSION: 1.0
ROADMAP_BLOB_SHA: 41775383879c86dc68a7d87c0d705cfc8512f62d
ROADMAP_FINGERPRINT: 449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6
MILESTONE: H1
CAPABILITY_ID: H1_REPOSITORY_EXPERIENCE_MANIFEST
REQUIREMENT_BINDINGS_FINGERPRINT: d47c2f54395e371cfc334846cac397c562c0be81f8e08c4bf9f088d9fb7a9f9f
H0_FORMAL_COMPLETION_GATE: PASS
H1_R1_EXISTING_DISCOVERY: PRESERVED
H1_R2_IMPLEMENTATION_EVIDENCE: PASS
H1_R3_IMPLEMENTATION_EVIDENCE: PASS
H1_FORMAL_COMPLETION_RECORD: PENDING
H2_IMPLEMENTATION_AUTHORIZED: NO
TASK_076_MERGE_AUTHORIZED: NO
LIVE_PAID_API_AUTHORIZED: NO

## Reviewed Snapshot

```text
BASE_MAIN_SHA: 8fe5724d5121e53313bfefabedd26df6e1e307c1
BRANCH: ai/task-078
REVIEWED_TASK_HEAD_SHA: a51e9c33cd66dc262f13063747295609d7b7df97
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: 8fe5724d5121e53313bfefabedd26df6e1e307c1
CUMULATIVE_SCOPE: EXACT
```

Changed implementation scope is exactly the three TASK-078 writable paths plus Bridge-generated RESULT-078:

```text
src/aios_engineering/harness/__init__.py
src/aios_engineering/harness/experience.py
tests/aios_engineering/harness/test_experience.py
.ai/results/RESULT-078.md
```

`src/aios_engineering/harness/discovery.py` remains unchanged, preserving the previously reviewed H1.R1 repository snapshot/discovery implementation.

## Validation

```text
FULL_REPOSITORY_TESTS: 2441 passed, 7 skipped, 0 failed
E4_AUTO_EXECUTION: YES
E4_CONTROL_COMMIT_SHA: 5f03b4090e7ed3d07c8002ba23dfaa908a37d911
E4_PRE_EXECUTION_HEAD: 8fe5724d5121e53313bfefabedd26df6e1e307c1
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 3
NETWORK_LLM_PAID_API_REQUIRED: NO
```

## Roadmap Audit

TASK-078 is exactly bound to the locked canonical roadmap:

```text
MILESTONE: H1
CAPABILITY_ID: H1_REPOSITORY_EXPERIENCE_MANIFEST
REQUIREMENTS: H1.R2, H1.R3
```

The H0 formal completion artifact was present in frozen control context before execution, satisfying the predecessor gate. No H2-H8 capability is claimed by this task.

The implementation restores the missing H1 surfaces identified by TASK-077 reconciliation without redefining H1:

```text
H1.R1 repository manifest/discovery -> reused unchanged
H1.R2 TASK/RESULT/REVIEW/DECISION/LEARNING inventory -> implemented
H1.R3 repository + control-plane provenance binding -> implemented
```

## H1.R2 Audit — PASS

`experience.py` introduces a conservative manifest-only experience inventory with explicit artifact identity classes:

```text
.ai/tasks/**     -> TASK
.ai/results/**   -> RESULT
.ai/reviews/**   -> REVIEW
.ai/decisions/** -> DECISION
explicit learning prefixes -> LEARNING
```

Evidence is classified from exact Git path/object identity only. Artifact bodies are not read for semantic inference, and the implementation does not infer Finding/Lesson/Skill semantics, executor quality, ranking, graph structure, retrieval, context compilation, or promotion.

Repository-surface experience is deliberately restricted to RESULT and explicit LEARNING evidence already present in the frozen `RepositoryDiscoveryResult`; TASK/REVIEW/DECISION control-plane evidence is taken from the independently frozen control snapshot. Same paths on different surfaces remain unambiguous because `surface` is part of canonical identity.

Hard bounds exist for control tree entries, Git stream bytes, individual records, experience evidence count, and serialized fingerprint payloads. Malformed records, unsafe paths, duplicate same-surface paths, non-regular entries, unsupported Git object types, and bound overflow fail closed.

## H1.R3 Audit — PASS

The new `RepositoryExperienceManifest` binds both exact provenance surfaces:

```text
repository commit + tree
repository discovery fingerprint
repository candidate-set fingerprint
control-plane commit + tree
control-plane manifest fingerprint
canonical combined evidence
combined experience fingerprint
manifest fingerprint
schema/policy identity
authority_created = False
```

Fingerprint construction is sensitive to repository commit/tree/discovery identity and control commit/tree/blob/evidence identity. Factories canonicalize evidence ordering before fingerprinting, so equivalent input permutations remain invariant.

Control-plane discovery accepts only an exact lowercase 40-hex commit, resolves the exact tree locally, uses `git --no-replace-objects`, forces `GIT_NO_LAZY_FETCH=1`, uses a closed child environment, ignores mutable/untracked worktree bytes, and has no network fallback.

## Authority / Boundary Audit — PASS

```text
BRIDGE_AUTHORITY_IMPORTED: NO
TASK_STATE_AUTHORITY: NO
REVIEW_STATE_AUTHORITY: NO
LEASE_OR_DISPATCH_AUTHORITY: NO
RETRY_OR_FAILOVER_AUTHORITY: NO
NETWORK_CALL: NO
LLM_CALL: NO
PAID_API_CALL: NO
TASK_076_DEPENDENCY: NO
H2_GRAPH_IMPLEMENTATION: NO
H3_TENDENCY_EXPANSION: NO
H4_H8_IMPLEMENTATION: NO
```

The module consumes repository paths and exact local Git identities supplied by the caller only. It creates advisory evidence and no execution/control authority.

## Milestone Completion Boundary

This PASS deliberately does **not** declare canonical H1 complete by itself.

Locked invariant remains:

```text
TASK PASS != MILESTONE COMPLETE
```

After the exact reviewed head is merged, a separate formal H1 milestone completion record must bind all canonical H1 requirements to reviewed evidence:

```text
H1.R1 -> TASK-070 / REVIEW-070
H1.R2 -> TASK-078 / REVIEW-078
H1.R3 -> TASK-078 / REVIEW-078
```

Only that valid completion record may open canonical H2 progression.

## Decision

```text
TASK-078: PASS
APPROVED: YES
AUTO_MERGE_ELIGIBLE: YES
BLOCKERS_REMAINING: 0
ROADMAP_AUDIT: PASS
H1_R2_R3_IMPLEMENTATION: ACCEPTED
H1_FORMAL_COMPLETION: PENDING
H2_IMPLEMENTATION_AUTHORIZED: NO
TASK_076: PRESERVE_UNMERGED
LIVE_PAID_API_AUTHORIZED: NO
```

ADR-042 reviewed-head fast-forward authorization may merge only the exact reviewed TASK-078 head if task head, main head, merge base, and current locked roadmap identity remain unchanged at merge time.
