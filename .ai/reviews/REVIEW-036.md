# REVIEW-036 — M9.3 Real Two-Executor Hot Local Handoff Proof

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO

## Review Round

Round 3 — final independent close-condition + proof audit.

## Authoritative Anchors

```text
TASK_ID: TASK-036
BASELINE_MAIN_SHA: 6b698eca9be428d3043a2e13064a19f1f4dd2faf
TASK_BRANCH: ai/task-036
ROUND1_REAL_PROOF_HEAD_SHA: dbba0a8eca609a92462d2afd91b7c82e4a4f7295
ROUND2_FIX_HEAD_SHA: 9ab6f658b8311a9432368b43784bc8379c40e42f
FINAL_TASK_HEAD_SHA: 57a6674887b43e3e91fc01b73479964506b2283e
TASK_BLOB_SHA: 0f2c3b4c3a4a86b75c2f99382757c69ceb0c9784
ADR_025_BLOB_SHA: fd02c610bbe47312292df61e5ba87ab72e5dd585
BLUEPRINT_BLOB_SHA: d8f82ea11c568999ab3506c5f7e5350c179b0560
ROUND1_REAL_RESULT_BLOB_SHA: 2634fb01822e0572a49daca3ebb1b694f334b92b
FINAL_FIX_RESULT_BLOB_SHA: ee38fd91c9d1d8fcc2d8730fd1b2edbe111f0b05
PROOF_JSON_BLOB_SHA: c242b40029b3f2d41d7b3ea734a2262b3d4ebc4f
SOURCE_STAGE_BLOB_SHA: e804119b8d51311c30ef292fd097578115ef6020
REPLACEMENT_STAGE_BLOB_SHA: 16281dadc0ba92c8a577b3ee6a99751347a8ecce
VERIFIER_BLOB_SHA: 928af50498a71591352c38c49a6975ced85b1297
FINAL_TEST_BLOB_SHA: 93cb4daa975d587b8e11535055978343c5f4f3f9
```

## Final Lineage / Scope Audit

From exact baseline to final task branch:

```text
COMMITS_AHEAD_OF_BASELINE: 3
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: 6b698eca9be428d3043a2e13064a19f1f4dd2faf
CHANGED_PATHS:
  .ai/results/RESULT-036.md
  proofs/TASK-036-M9/PROOF.json
  proofs/TASK-036-M9/replacement-stage.txt
  proofs/TASK-036-M9/source-stage.txt
  scripts/aios_m9_real_hot_handoff_proof.py
  tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
SCOPE_AUDIT: PASS
```

Round 3 itself changed only:

```text
.ai/results/RESULT-036.md        # Bridge-generated FIX result
tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
```

No production verifier, Bridge, M9.1/M9.2 core, lease, routing, provider, or quota-policy code changed in Round 3.

## Real Proof Preservation Audit

The real proof event created in Round 1 remains byte-identical through both FIX rounds:

```text
PROOF_JSON_BLOB_UNCHANGED: PASS
SOURCE_STAGE_BLOB_UNCHANGED: PASS
REPLACEMENT_STAGE_BLOB_UNCHANGED: PASS
VERIFIER_UNCHANGED_IN_ROUND3: PASS
REAL_CHAIN_PRESERVED: PASS
```

The Round-1 Bridge publication is the authoritative lifecycle-event evidence:

```text
ACTION: RUN
EXECUTOR_ID: antigravity
EXECUTOR_FAILOVER: NO
HOT_HANDOFF: YES
HOT_HANDOFF_CHECKPOINT_FINGERPRINT: 884cfc307ee36ae46249af1e01b08d0acc0e2c042f336ad33ee10b34a31b3ff9
HOT_HANDOFF_FROM_EXECUTOR: codex
HOT_HANDOFF_TO_EXECUTOR: antigravity
```

Later FIX results correctly describe review-authorized FIX executions and do not replace or invalidate the immutable Round-1 real handoff evidence.

## Independent Cryptographic Re-Audit

Primary Brain recomputed the canonical proof and checkpoint fingerprints from the final unchanged `PROOF.json`:

```text
PROOF_FINGERPRINT_DECLARED: b6bd39c0ed5514861871d78eb911872bbbd4d0fed9e025b6a3cd0279ef5e5b51
PROOF_FINGERPRINT_RECOMPUTED: b6bd39c0ed5514861871d78eb911872bbbd4d0fed9e025b6a3cd0279ef5e5b51
PROOF_FINGERPRINT_MATCH: PASS

CHECKPOINT_FINGERPRINT_DECLARED: 884cfc307ee36ae46249af1e01b08d0acc0e2c042f336ad33ee10b34a31b3ff9
CHECKPOINT_FINGERPRINT_RECOMPUTED: 884cfc307ee36ae46249af1e01b08d0acc0e2c042f336ad33ee10b34a31b3ff9
CHECKPOINT_FINGERPRINT_MATCH: PASS
```

Final witness recomputation:

```text
SOURCE_STAGE_SIZE: 82
SOURCE_STAGE_SHA256_DECLARED: bcc965f2bf837f1b4433ef5b94e0240b5726bd33db0bf69d6ce79be799b2871d
SOURCE_STAGE_SHA256_RECOMPUTED: bcc965f2bf837f1b4433ef5b94e0240b5726bd33db0bf69d6ce79be799b2871d
SOURCE_STAGE_MATCH: PASS

REPLACEMENT_STAGE_SIZE: 186
REPLACEMENT_STAGE_SHA256_DECLARED: 7a305d9c399c60d7c0279a514b26ba0e05f21400e65fcf6f06cc192f336440d5
REPLACEMENT_STAGE_SHA256_RECOMPUTED: 7a305d9c399c60d7c0279a514b26ba0e05f21400e65fcf6f06cc192f336440d5
REPLACEMENT_STAGE_MATCH: PASS
```

The embedded checkpoint still proves:

```text
TASK_ID: TASK-036
HEAD_SHA: 6b698eca9be428d3043a2e13064a19f1f4dd2faf
TARGET_BRANCH: ai/task-036
SOURCE_EXECUTOR: codex
TRACKED_MANIFEST_COUNT: 0
UNTRACKED_MANIFEST_COUNT: 1
UNTRACKED_PATH: proofs/TASK-036-M9/source-stage.txt
REPLACEMENT_STAGE_ABSENT_FROM_SOURCE_CHECKPOINT: PASS
```

The final publication contains the replacement witness bound to the same exact checkpoint fingerprint and executor `antigravity`.

## FINDING R1-1 — CLOSED

FINDING_ID: R1-1
SEVERITY: HIGH
STATUS: CLOSED

Round 2 added the missing authority/provenance adversarial cases. Round 3 restored all ADR-025 proof-boundary tests accidentally removed during that FIX.

The focused suite now mechanically covers, together, at minimum:

```text
non-ACTIVE authorization
malformed/partial authorization
missing hot_handoff metadata
wrong source actor
wrong replacement actor
same source/replacement actor
inactive/mismatched replacement lease
missing/unreadable exact checkpoint
checkpoint fingerprint/tamper failure
checkpoint task mismatch
checkpoint branch mismatch
checkpoint workspace mismatch
checkpoint source actor mismatch
checkpoint source lease fingerprint mismatch
checkpoint source execution fingerprint mismatch
checkpoint allowed_paths mismatch
checkpoint head_sha mismatch
source-stage absent from checkpoint
source-stage tracked instead of required untracked state
source-stage current hash/content drift
replacement-stage present in source checkpoint
replacement-stage missing after activation
replacement-stage checkpoint-fingerprint mismatch
proof semantic fingerprint tamper
exact one-shot authorization-bound checkpoint lookup
no history/latest/glob/fuzzy fallback
failure-before-proof-emission checks where applicable
```

CLOSE_CONDITIONS:

```text
ALL_ADR_025_DECISION_14_SEAMS_COEXIST: PASS
ROUND2_NEW_TESTS_PRESERVED: PASS
ROUND1_REQUIRED_TESTS_RESTORED: PASS
NO_PRODUCTION_WEAKENING: PASS
R1-1: CLOSED
```

## FINDING R1-2 — CLOSED

FINDING_ID: R1-2
SEVERITY: MEDIUM
STATUS: CLOSED

Production verifier hardening from Round 2 remains unchanged. `validate_safe_repository_path()` rejects parent/leaf symlink traversal before witness bytes are trusted and preserves repository confinement.

The final focused suite covers all required path-safety cases:

```text
symlink leaf -> reject
symlink parent pointing inside repo -> reject
symlink parent pointing outside repo -> reject
ordinary nested regular path -> accept
platform-independent mocked parent-symlink rejection -> reject
absolute/traversal path -> reject
binary/NUL/non-UTF8 payload -> reject
```

The real TASK-036 witness blobs remain unchanged.

CLOSE_CONDITIONS:

```text
PARENT_SYMLINK_FAIL_CLOSED: PASS
OUTSIDE_REPO_SYMLINK_TEST: PASS
ORDINARY_NESTED_PATH_ACCEPTANCE_TEST: PASS
WINDOWS_DETERMINISTIC_PARENT_TEST_PRESERVED: PASS
REAL_WITNESS_BYTES_UNCHANGED: PASS
R1-2: CLOSED
```

## Full Repository Test Gate

Final Bridge FIX publication executed:

```text
.\venv\Scripts\python.exe -m pytest tests/ -q
897 passed, 4 skipped, 1533 warnings in 146.70s
exit code 0
```

The additional skips are platform/environment-dependent tests; there are zero failures and no regression signal.

## M9.3 Acceptance Audit

```text
REAL_SOURCE_EXECUTOR: codex
REAL_REPLACEMENT_EXECUTOR: antigravity
DISTINCT_REAL_EXECUTORS: PASS
UNPUBLISHED_DIRTY_SOURCE_BOUNDARY: PASS
EXACT_CHECKPOINT_BINDING: PASS
ZERO_ACTIVE_PREPARED_BOUNDARY: PASS (Bridge lifecycle evidence)
NEW_REPLACEMENT_MUTATION_AFTER_CHECKPOINT: PASS
SOURCE_WITNESS_PRESERVED: PASS
REPLACEMENT_WITNESS_NOVELTY: PASS
RESULT_PROOF_ACTOR_AGREEMENT: PASS
RESULT_PROOF_CHECKPOINT_AGREEMENT: PASS
EXECUTOR_FAILOVER: NO
STABLE_FAILOVER_PROOF_MANUFACTURED: NO
M6_M8_PROOF_CONFLATION: NO
M9_CORE_CHANGED_BY_PROOF_TASK: NO
HUMAN_AUTHORITY_PRESERVED: PASS
```

## Final Decision

```text
LINEAGE_AUDIT: PASS
SCOPE_AUDIT: PASS
REAL_CHAIN_INTERNAL_CONSISTENCY: PASS
REAL_CHAIN_PRESERVED_ACROSS_FIXES: PASS
PROOF_FINGERPRINT_RECOMPUTE: PASS
CHECKPOINT_FINGERPRINT_RECOMPUTE: PASS
SOURCE_WITNESS_BINDING: PASS
REPLACEMENT_WITNESS_BINDING: PASS
ADVERSARIAL_PROOF_COVERAGE: PASS
PATH_SAFETY_COVERAGE: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
R1-1: CLOSED
R1-2: CLOSED
SEMANTIC_FINDINGS: NONE
M9_3_REAL_TWO_EXECUTOR_PROOF: PASS
FINAL_INDEPENDENT_AUDIT: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: NO
```

TASK-036 proves exactly one real local unpublished dirty-workspace hot-handoff chain from `codex` to `antigravity` under explicit Human authority. This PASS does not authorize automatic routing, arbitrary executor-pair equivalence, cross-machine handoff, M10, or M11. Human remains the sole merge authority.
