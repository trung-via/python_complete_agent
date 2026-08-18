# REVIEW-036 — M9.3 Real Two-Executor Hot Local Handoff Proof

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO

## Review Round

Round 2 — independent close-condition audit after authorized verifier-hardening FIX.

## Authoritative Anchors

```text
TASK_ID: TASK-036
BASELINE_MAIN_SHA: 6b698eca9be428d3043a2e13064a19f1f4dd2faf
TASK_BRANCH: ai/task-036
ROUND1_TASK_HEAD_SHA: dbba0a8eca609a92462d2afd91b7c82e4a4f7295
ROUND2_TASK_HEAD_SHA: 9ab6f658b8311a9432368b43784bc8379c40e42f
TASK_BLOB_SHA: 0f2c3b4c3a4a86b75c2f99382757c69ceb0c9784
ADR_025_BLOB_SHA: fd02c610bbe47312292df61e5ba87ab72e5dd585
BLUEPRINT_BLOB_SHA: d8f82ea11c568999ab3506c5f7e5350c179b0560
ROUND1_REVIEW_BLOB_SHA: c6a7b31e60b66f366be22e6be9f696464d794249
ROUND1_REAL_RESULT_BLOB_SHA: 2634fb01822e0572a49daca3ebb1b694f334b92b
ROUND2_FIX_RESULT_BLOB_SHA: 6e5ccbe9de1dff556e2cc8dd01572d793e31b8f4
PROOF_JSON_BLOB_SHA: c242b40029b3f2d41d7b3ea734a2262b3d4ebc4f
SOURCE_STAGE_BLOB_SHA: e804119b8d51311c30ef292fd097578115ef6020
REPLACEMENT_STAGE_BLOB_SHA: 16281dadc0ba92c8a577b3ee6a99751347a8ecce
VERIFIER_BLOB_SHA: 928af50498a71591352c38c49a6975ced85b1297
TEST_BLOB_SHA: 1060c3bc579772789e4e7ff6ece54dd71dc780da
```

## Round-2 Scope / Preservation Audit

```text
COMMITS_AHEAD_OF_BASELINE: 2
COMMITS_BEHIND_BASELINE: 0
ROUND2_FIX_COMMITS_AFTER_REAL_PROOF: 1
ROUND2_FIX_CHANGED_PATHS:
  .ai/results/RESULT-036.md
  scripts/aios_m9_real_hot_handoff_proof.py
  tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
ROUND2_SCOPE_AUDIT: PASS
```

The three immutable real-proof artifacts remain byte-identical to Round 1:

```text
PROOF_JSON_BLOB_UNCHANGED: PASS
SOURCE_STAGE_BLOB_UNCHANGED: PASS
REPLACEMENT_STAGE_BLOB_UNCHANGED: PASS
PROOF_FINGERPRINT: b6bd39c0ed5514861871d78eb911872bbbd4d0fed9e025b6a3cd0279ef5e5b51
CHECKPOINT_FINGERPRINT: 884cfc307ee36ae46249af1e01b08d0acc0e2c042f336ad33ee10b34a31b3ff9
SOURCE_WITNESS_SHA256: bcc965f2bf837f1b4433ef5b94e0240b5726bd33db0bf69d6ce79be799b2871d
REPLACEMENT_WITNESS_SHA256: 7a305d9c399c60d7c0279a514b26ba0e05f21400e65fcf6f06cc192f336440d5
REAL_CHAIN_PRESERVED: PASS
```

The Bridge-generated FIX result is expected to describe the FIX authorization (`ACTION: FIX`, `EXECUTOR_ID: antigravity`, `HOT_HANDOFF: NO`). The immutable Round-1 real publication remains anchored by `ROUND1_REAL_RESULT_BLOB_SHA` and is not replaced as the evidence for the actual codex -> antigravity handoff event.

## Test Evidence

Round-2 Bridge publication executed:

```text
.\venv\Scripts\python.exe -m pytest tests/ -q
888 passed, 3 skipped, 1533 warnings
exit code 0
```

Full suite is green. Final PASS is blocked by incomplete regression-lock coverage, not by a failing happy-path proof.

---

## FINDING R1-1 — STILL OPEN

FINDING_ID: R1-1
SEVERITY: HIGH
STATUS: OPEN

### What the FIX closed

The FIX added direct coverage for the previously missing seams:

```text
non-ACTIVE auth
partial/malformed auth
missing hot_handoff metadata
inactive/mismatched replacement lease
missing exact checkpoint
checkpoint loader fingerprint/tamper failure
checkpoint task/branch/workspace/source provenance mismatches
source absent from checkpoint
source incorrectly tracked instead of untracked
proof semantic fingerprint tamper
one exact authorization-bound checkpoint lookup
```

The production verifier also gained an explicit proof-fingerprint integrity helper and retains exact checkpoint loading.

### Why the finding is not closed

While adding the new tests, the FIX deleted several pre-existing tests that were already required by ADR-025 Decision 14. Therefore the complete proof trust boundary is still not mechanically regression-locked.

The deleted required cases include at minimum:

```text
source actor != codex
replacement actor != antigravity
source actor == replacement actor
checkpoint head_sha != exact baseline
source-stage current hash/content drift
replacement-stage already present in source checkpoint
replacement-stage missing after activation
replacement-stage checkpoint-fingerprint mismatch
```

These are not optional legacy tests; they are explicit ADR-025 proof requirements. Removing them while adding new cases trades one coverage gap for another.

CLOSE_CONDITIONS_NOT_MET:
1. All ADR-025 Decision-14 seams must coexist in the focused suite.
2. Existing previously-green proof-boundary tests must not be deleted when adding new coverage.

### Required behavior for next FIX

Restore the deleted required adversarial cases without weakening the newly-added Round-2 cases. Prefer restoring the old tests from the Round-1 test artifact semantics and adapting only names/fixtures if necessary.

For every rejection that occurs before proof emission, continue asserting no new `PROOF.json` is emitted/overwritten where practical.

ALLOWED_FILES:
- tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
- .ai/results/RESULT-036.md (Bridge-generated publication only)

FORBIDDEN_FILES:
- scripts/aios_m9_real_hot_handoff_proof.py
- proofs/TASK-036-M9/PROOF.json
- proofs/TASK-036-M9/source-stage.txt
- proofs/TASK-036-M9/replacement-stage.txt
- bridge.py
- src/aios_bridge/**

---

## FINDING R1-2 — PARTIAL, STILL OPEN

FINDING_ID: R1-2
SEVERITY: MEDIUM
STATUS: OPEN

### What the FIX closed

The production verifier now uses `validate_safe_repository_path()` before trusting witness bytes. It walks existing path components using `lstat`, rejects symlink components, enforces repository-relative canonical path text, and verifies resolved confinement under `repo_root`.

A platform-independent mocked-parent-symlink test was also added, so Windows environments without symlink privileges still exercise parent-component rejection.

The semantic implementation defect from Round 1 is therefore fixed.

### Remaining close-condition gap

Round-1 REQUIRED_TESTS explicitly required all of:

```text
symlink leaf -> reject
symlink parent pointing inside repo -> reject
symlink parent pointing outside repo -> reject
ordinary nested regular path -> accept
platform-independent parent-component validation test
```

Current Round-2 tests cover leaf symlink, one parent symlink pointing to a directory inside the temp repo, and the deterministic mocked-parent test. They do not directly cover:

```text
parent symlink whose target is outside repo
ordinary nested regular path acceptance
```

CLOSE_CONDITIONS_NOT_MET:
1. Add a parent-symlink-to-outside-repo rejection test.
2. Add an ordinary nested regular path acceptance test.
3. Preserve the deterministic mocked-parent test for Windows.

No production verifier change is required unless these two tests expose a real defect.

ALLOWED_FILES:
- tests/aios_bridge/continuity/test_m9_real_hot_handoff_proof.py
- .ai/results/RESULT-036.md (Bridge-generated publication only)

FORBIDDEN_FILES:
- scripts/aios_m9_real_hot_handoff_proof.py unless a newly-added test proves an actual production bug; if so STOP and report blocker rather than broadening scope
- proof artifacts
- Bridge/M9 core

---

## Round-2 Decision

```text
LINEAGE_AUDIT: PASS
ROUND2_SCOPE_AUDIT: PASS
REAL_CHAIN_PRESERVED: PASS
PROOF_ARTIFACTS_BYTE_IDENTICAL: PASS
PRODUCTION_PATH_HARDENING: PASS
PROOF_FINGERPRINT_HELPER: PASS
FULL_REPO_TESTS: PASS
R1-1: OPEN
R1-2: OPEN (implementation fixed; exact test close conditions incomplete)
NEW_PRODUCTION_SEMANTIC_FINDINGS: NONE
FINAL_INDEPENDENT_AUDIT: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
```

Do not merge TASK-036 yet.

The next FIX is intentionally test-only. Restore the removed ADR-025 adversarial tests, add the two missing path-safety tests, run focused M9.3 + M9.2 regression tests, then let Bridge run the full suite once. Do not rerun the real hot-handoff lifecycle and do not regenerate or modify the real proof artifacts.