# REVIEW-036 — M9.3 Real Two-Executor Hot Local Handoff Proof

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO

## Review Round

Round 1 — independent semantic + proof audit.

## Authoritative Anchors

```text
TASK_ID: TASK-036
BASELINE_MAIN_SHA: 6b698eca9be428d3043a2e13064a19f1f4dd2faf
TASK_BRANCH: ai/task-036
TASK_HEAD_SHA: dbba0a8eca609a92462d2afd91b7c82e4a4f7295
TASK_BLOB_SHA: 0f2c3b4c3a4a86b75c2f99382757c69ceb0c9784
ADR_025_BLOB_SHA: fd02c610bbe47312292df61e5ba87ab72e5dd585
BLUEPRINT_BLOB_SHA: d8f82ea11c568999ab3506c5f7e5350c179b0560
RESULT_036_BLOB_SHA: 2634fb01822e0572a49daca3ebb1b694f334b92b
PROOF_JSON_BLOB_SHA: c242b40029b3f2d41d7b3ea734a2262b3d4ebc4f
SOURCE_STAGE_BLOB_SHA: e804119b8d51311c30ef292fd097578115ef6020
REPLACEMENT_STAGE_BLOB_SHA: 16281dadc0ba92c8a577b3ee6a99751347a8ecce
VERIFIER_BLOB_SHA: 079742fbd51a869b22b2aa8f324b1042a39dbe13
TEST_BLOB_SHA: 1ce4398efddcf0444baecc56dd66c5b4c1a537b6
```

## Lineage / Scope / Proof Audit

```text
COMMITS_AHEAD_OF_BASELINE: 1
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: exact baseline
CHANGED_PATHS:
  .ai/results/RESULT-036.md
  proofs/TASK-036-M9/PROOF.json
  proofs/TASK-036-M9/replacement-stage.txt
  proofs/TASK-036-M9/source-stage.txt
  scripts/aios_m9_real_hot_handoff_proof.py
  tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
SCOPE_AUDIT: PASS
```

Independent Primary-Brain recomputation established:

```text
RESULT_ACTION: RUN
RESULT_EXECUTOR_ID: antigravity
RESULT_EXECUTOR_FAILOVER: NO
RESULT_HOT_HANDOFF: YES
RESULT_FROM_EXECUTOR: codex
RESULT_TO_EXECUTOR: antigravity
RESULT_CHECKPOINT_FP: 884cfc307ee36ae46249af1e01b08d0acc0e2c042f336ad33ee10b34a31b3ff9

PROOF_FINGERPRINT_DECLARED: b6bd39c0ed5514861871d78eb911872bbbd4d0fed9e025b6a3cd0279ef5e5b51
PROOF_FINGERPRINT_RECOMPUTED: b6bd39c0ed5514861871d78eb911872bbbd4d0fed9e025b6a3cd0279ef5e5b51
PROOF_FINGERPRINT_MATCH: PASS

CHECKPOINT_FINGERPRINT_DECLARED: 884cfc307ee36ae46249af1e01b08d0acc0e2c042f336ad33ee10b34a31b3ff9
CHECKPOINT_FINGERPRINT_RECOMPUTED: 884cfc307ee36ae46249af1e01b08d0acc0e2c042f336ad33ee10b34a31b3ff9
CHECKPOINT_FINGERPRINT_MATCH: PASS

CHECKPOINT_HEAD_SHA: 6b698eca9be428d3043a2e13064a19f1f4dd2faf
CHECKPOINT_SOURCE_EXECUTOR: codex
CHECKPOINT_ALLOWED_PATHS: proofs/TASK-036-M9/source-stage.txt
CHECKPOINT_TRACKED_MANIFEST_COUNT: 0
CHECKPOINT_UNTRACKED_MANIFEST_COUNT: 1

SOURCE_STAGE_SHA256_DECLARED: bcc965f2bf837f1b4433ef5b94e0240b5726bd33db0bf69d6ce79be799b2871d
SOURCE_STAGE_SHA256_RECOMPUTED: bcc965f2bf837f1b4433ef5b94e0240b5726bd33db0bf69d6ce79be799b2871d
SOURCE_STAGE_SIZE: 82
SOURCE_STAGE_MATCH: PASS

REPLACEMENT_STAGE_SHA256_DECLARED: 7a305d9c399c60d7c0279a514b26ba0e05f21400e65fcf6f06cc192f336440d5
REPLACEMENT_STAGE_SHA256_RECOMPUTED: 7a305d9c399c60d7c0279a514b26ba0e05f21400e65fcf6f06cc192f336440d5
REPLACEMENT_STAGE_SIZE: 186
REPLACEMENT_STAGE_ABSENT_FROM_SOURCE_CHECKPOINT: PASS
REPLACEMENT_STAGE_MATCH: PASS
```

The real proof chain itself is internally consistent. Final PASS is blocked only by the verifier-contract findings below.

## Test Evidence

Bridge publication executed:

```text
.\venv\Scripts\python.exe -m pytest tests/ -q
874 passed, 2 skipped, 1533 warnings
exit code 0
```

The additional skip is the platform-dependent symlink test in the M9.3 verifier suite.

---

## FINDING R1-1

FINDING_ID: R1-1
SEVERITY: HIGH
ROOT_CAUSE: ADR-025 Decision 14 and the TASK-036 implementation blueprint require explicit adversarial verifier coverage for the complete proof trust boundary, but the delivered focused test suite covers only a subset. In particular, it does not mechanically exercise several required fail-closed seams: non-ACTIVE/malformed authorization, missing hot-handoff metadata, active replacement-lease mismatch, missing/tampered exact persisted checkpoint, checkpoint fingerprint/provenance mismatches beyond `head_sha`, source witness absent/not-untracked, generated proof fingerprint tamper, and explicit no-history/no-latest/no-fuzzy checkpoint fallback. The production verifier appears to use exact runtime primitives for several of these paths, but the locked contract requires adversarial tests rather than accepting code inspection as a substitute.
BROKEN_INVARIANT: M9.3 is a proof milestone. Every authority/provenance seam enumerated in ADR-025 Decision 14 must be mechanically regression-locked so a future verifier refactor cannot silently weaken the real-proof claim.
REQUIRED_BEHAVIOR: Add focused adversarial tests that directly exercise every currently missing ADR-025 Decision-14 requirement against `verify_real_hot_handoff_proof()` or the exact helper seam it delegates to. Tests must prove failure occurs before PROOF emission where applicable and must not rely on free-form error logs as authority.
FORBIDDEN_IMPLEMENTATIONS:
- Do not weaken or delete existing checks to make tests easier.
- Do not replace exact checkpoint lookup with history scanning, globbing, latest-file selection, or caller-supplied checkpoint bytes.
- Do not modify M9.1/M9.2 core, lease semantics, Bridge lifecycle, routing, provider policy, or actor IDs.
- Do not regenerate or rewrite the real source/replacement witnesses merely to close test coverage.
REQUIRED_TESTS:
1. authorization exists but `status != ACTIVE` -> reject;
2. malformed/partial authorization required fields -> reject;
3. ACTIVE authorization with no `hot_handoff` metadata -> reject;
4. active replacement lease mismatch / `require_active()` failure -> reject;
5. exact checkpoint file missing/unreadable -> reject;
6. exact checkpoint object/fingerprint tamper -> reject;
7. checkpoint task/branch/workspace/source provenance mismatch cases -> reject;
8. source-stage absent from checkpoint -> reject;
9. source-stage present in tracked rather than the required untracked manifest -> reject;
10. generated PROOF semantic content altered while retaining old `proof_fingerprint` -> deterministic fingerprint verification must fail in a focused helper/test;
11. prove exact checkpoint lookup receives only the authorization-bound fingerprint and no history/latest/glob/fuzzy fallback is attempted.
ADVERSARIAL_CHECKS:
- In failure cases, assert `PROOF.json` is not newly emitted or overwritten.
- For lease mismatch, assert no fallback lease is accepted.
- For exact-checkpoint lookup, assert one exact fingerprint call and no alternate lookup path.
CLOSE_CONDITIONS:
1. Every missing ADR-025 Decision-14 seam above has direct automated coverage.
2. Focused M9.3 verifier tests are green.
3. Existing M9.2 hot-handoff regression tests remain green.
4. Full repository suite remains exit 0.
ALLOWED_FILES:
- tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
- scripts/aios_m9_real_hot_handoff_proof.py only if a tiny pure proof-fingerprint validation helper is required for testability
- .ai/results/RESULT-036.md (Bridge-generated FIX publication only)
FORBIDDEN_SCOPE:
- proofs/TASK-036-M9/source-stage.txt
- proofs/TASK-036-M9/replacement-stage.txt
- proofs/TASK-036-M9/PROOF.json unless Primary Brain explicitly requires regeneration (not required for this finding)
- bridge.py
- src/aios_bridge/continuity/*
- src/aios_bridge/runtime_lease.py
- routing/provider/quota changes

---

## FINDING R1-2

FINDING_ID: R1-2
SEVERITY: MEDIUM
ROOT_CAUSE: `safe_read_workspace_payload()` rejects an absolute/traversal input and rejects a symlink only at the final leaf with `os.lstat(full_path)`, but it does not reject symlinked parent path components. A hard-coded path such as `proofs/TASK-036-M9/replacement-stage.txt` can therefore resolve through a symlinked `proofs` or `TASK-036-M9` directory to a regular file outside the repository while the helper still reports a valid regular UTF-8 payload. ADR-025 requires symlink/unsafe-path rejection for replacement proof payloads.
BROKEN_INVARIANT: A repository-relative proof witness must be physically confined to the exact repository tree; path text alone is not sufficient proof if an intermediate component can redirect outside the worktree.
REQUIRED_BEHAVIOR: Before reading either proof witness, walk or resolve the hard-coded repository-relative path fail-closed so every existing parent component and the leaf are proven non-symlink and the resolved leaf remains within `repo_root`. Preserve the current regular-file, NUL, and strict UTF-8 checks. Keep the helper task-specific and small.
FORBIDDEN_IMPLEMENTATIONS:
- Do not use `resolve()` alone and then silently accept symlink traversal.
- Do not follow a symlink and validate only the final target.
- Do not broaden into a generalized filesystem framework.
- Do not change the proof paths or witness contents.
REQUIRED_TESTS:
- symlink leaf -> reject (existing test may remain platform-skipped);
- symlink parent component pointing inside repo -> reject;
- symlink parent component pointing outside repo -> reject;
- ordinary nested regular path -> accept;
- where Windows cannot create symlinks, keep a non-privileged deterministic unit test for the path-component validation helper so this invariant is still exercised on Windows CI/local runs.
ADVERSARIAL_CHECKS:
- parent-symlink rejection must occur before witness bytes are trusted or hashed into proof semantics.
- no outside-repository target may be accepted as SOURCE_PATH or REPLACEMENT_PATH.
CLOSE_CONDITIONS:
1. Parent-component symlinks/path escape are fail-closed.
2. Required tests pass on a platform-independent path where possible.
3. Existing actual TASK-036 witness bytes/hashes remain unchanged.
ALLOWED_FILES:
- scripts/aios_m9_real_hot_handoff_proof.py
- tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
- .ai/results/RESULT-036.md (Bridge-generated FIX publication only)
FORBIDDEN_SCOPE:
- proof witness content/path changes
- PROOF schema redesign
- Bridge/M9.1/M9.2 core changes

---

## Proof Preservation Rule for FIX

The already-published real proof event is independently validated by Primary Brain and MUST be preserved during this FIX:

```text
PROOF.json fingerprint: b6bd39c0ed5514861871d78eb911872bbbd4d0fed9e025b6a3cd0279ef5e5b51
checkpoint fingerprint: 884cfc307ee36ae46249af1e01b08d0acc0e2c042f336ad33ee10b34a31b3ff9
source witness SHA-256: bcc965f2bf837f1b4433ef5b94e0240b5726bd33db0bf69d6ce79be799b2871d
replacement witness SHA-256: 7a305d9c399c60d7c0279a514b26ba0e05f21400e65fcf6f06cc192f336440d5
```

Do not rerun the real handoff lifecycle merely to close R1-1/R1-2. The FIX is verifier hardening + adversarial regression coverage only. Final review will re-audit that the real proof artifacts above are byte-identical while the verifier/test contract is closed.

## Round-1 Decision

```text
LINEAGE_AUDIT: PASS
SCOPE_AUDIT: PASS
REAL_CHAIN_INTERNAL_CONSISTENCY: PASS
PROOF_FINGERPRINT_RECOMPUTE: PASS
CHECKPOINT_FINGERPRINT_RECOMPUTE: PASS
SOURCE_WITNESS_BINDING: PASS
REPLACEMENT_WITNESS_BINDING: PASS
RESULT_PROOF_AGREEMENT: PASS
FULL_REPO_TESTS: PASS
R1-1: OPEN
R1-2: OPEN
SEMANTIC_FINDINGS: 2
FINAL_INDEPENDENT_AUDIT: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
```

Do not merge TASK-036. Human may authorize a bounded FIX with the same replacement Executor after synchronizing this exact REVIEW-036 artifact. The FIX must preserve all real-proof artifacts byte-for-byte and touch only the allowed verifier/test files plus Bridge-generated RESULT.