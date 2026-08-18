# REVIEW-039 — M10.3 Real Operational Dispatch Proof

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO

## Review Round

Round 1 — independent lineage, real-receipt, causal-ordering, authorization/lease, proof-fingerprint, publication-boundary, and regression audit.

## Authoritative Anchors

```text
TASK_ID: TASK-039
BASELINE_MAIN_SHA: ff5d78abd71086ecb814255d4a589370e5660332
TASK_BRANCH: ai/task-039
TASK_HEAD_SHA_REVIEWED: 46d21e1909dcdc596c548fb6e967d155c0fb84b7
TASK_BLOB_SHA: 3cd9c9dafbcb8c5bf2130e9c4386e872a09130c1
ADR_028_BLOB_SHA: 10de8fbf67bd4b0f44d4f3297da4078ff79d019d
BLUEPRINT_BLOB_SHA: a4d179dcdac3647b9dc8c65a8ec95b6aa436c9d2
RESULT_BLOB_SHA: 150a47ed4a7f8bd3b9394e3f3cf92645fc9fa368
PROOF_BLOB_SHA: 1da7f7744e398031baacefc7137347d2d000dabb
RECEIPT_COPY_BLOB_SHA: 0d5923f7d1dae8c37113f0fa3ef8f310b18db3a4
EXECUTOR_STAGE_BLOB_SHA: ab844226b1491209e288114956763687931d09d9
VERIFIER_BLOB_SHA: 2eb275aa7421dbf084cfb7c8850195c6e2513e2f
TEST_BLOB_SHA: f53521e037204f928f11bb9504c9b4d23d4b7916
```

## Lineage / Scope Audit

```text
REMOTE_MAIN_SHA: ff5d78abd71086ecb814255d4a589370e5660332
COMMITS_AHEAD_OF_BASELINE: 1
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: ff5d78abd71086ecb814255d4a589370e5660332
CHANGED_PATHS:
  .ai/results/RESULT-039.md
  proofs/TASK-039-M10/PROOF.json
  proofs/TASK-039-M10/executor-stage.txt
  proofs/TASK-039-M10/recommendation-receipt.txt
  scripts/aios_m10_real_dispatch_proof.py
  tests/aios_bridge/test_m10_real_dispatch_proof.py
SCOPE_AUDIT: PASS
```

No production M10.1/M10.2, Bridge, lease, failover, hot-handoff, provider, or External Brain implementation changed.

## Positive Real-Proof Audit

```text
REAL_CAPACITY_ANTIGRAVITY_QUOTA_EXHAUSTED: PASS
REAL_CAPACITY_CODEX_AVAILABLE: PASS
CAPACITY_SOURCE_HUMAN_DECLARED: PASS
CAPACITY_RECEIPT_FINGERPRINT_BINDING: PASS
REAL_BRIDGE_RECOMMENDATION_SELECTED_CODEX: PASS
RECOMMENDATION_HUMAN_APPROVAL_REQUIRED: PASS
RECOMMENDATION_AUTH_CHANGED_NO: PASS
RECOMMENDATION_LEASE_CHANGED_NO: PASS
EXACT_TASK_BLOB_BINDING: PASS
POLICY_FINGERPRINT_BINDING: PASS
REQUEST_FINGERPRINT_BINDING: PASS
RESULT_FINGERPRINT_BINDING: PASS
CAUSAL_CAPACITY_BEFORE_RECEIPT: PASS
CAUSAL_RECEIPT_BEFORE_AUTHORIZATION: PASS
ACTIVE_CODEX_RUN_AUTHORIZATION: PASS
ACTIVE_CODEX_EXECUTOR_LEASE: PASS
NO_FAILOVER_METADATA: PASS
NO_HOT_HANDOFF_METADATA: PASS
EXECUTOR_STAGE_EXACT_BYTES: PASS
PROOF_FINGERPRINT_RECOMPUTE: PASS
VERIFIER_REUSES_M10_1_DISPATCHER: PASS
VERIFIER_AUTHORITY_MUTATION_SURFACES: NONE
```

Independent canonical recomputation of `PROOF.json` yields exactly:

```text
73bac3049b10704e92637aa507a133a9c409530d25879c939ce4e6ec1ff86795
```

which matches the declared proof fingerprint.

The proof also binds the real operational chain:

```text
antigravity QUOTA_EXHAUSTED / FRESH
codex       AVAILABLE       / FRESH
        -> Bridge SELECTED codex
        -> recommendation changes no auth/lease
        -> Human RUN authorization for codex
        -> exact active codex ExecutorLease
        -> exact codex executor-stage witness
```

## Full Repository Test Gate

Final RUN publication reports:

```text
1108 passed, 7 skipped, 1533 warnings in 127.37s
exit code 0
```

```text
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
```

---

## FINDING R1-1

FINDING_ID: R1-1
SEVERITY: HIGH
ROOT_CAUSE: The verifier correctly copied the raw external Windows recommendation receipt byte-for-byte into the working tree and `PROOF.json` bound its SHA-256, but Git text normalization changed CRLF line endings to LF when Bridge publication staged/committed `proofs/TASK-039-M10/recommendation-receipt.txt`. The published Git blob is therefore not byte-identical to the validated external receipt.

BROKEN_INVARIANT:
- ADR-028 Decision 10 requires the validated raw external recommendation receipt to be copied byte-for-byte into `proofs/TASK-039-M10/recommendation-receipt.txt`.
- The committed proof directory is the reviewable canonical evidence after publication; its receipt blob must hash to the same SHA-256 recorded in `PROOF.json`.
- Publication must not silently mutate proof bytes after verifier validation.

MECHANICAL_EVIDENCE:

`PROOF.json` declares:

```text
recommendation.receipt_sha256 = 01e76d5d13581121e73cd2836097e5b487785468f800122c4169eae99286f935
```

The actual committed Git blob bytes for:

```text
proofs/TASK-039-M10/recommendation-receipt.txt
```

are BOM + LF line endings and independently hash to:

```text
131b0fd7d649c07f3e3a5927027b0a828962e1c70bd8559f85a80c5a824237d5
```

Converting those 17 LF separators back to CRLF yields exactly the proof-bound external receipt hash:

```text
01e76d5d13581121e73cd2836097e5b487785468f800122c4169eae99286f935
```

This mechanically identifies Git EOL normalization as the publication mutation rather than a semantic receipt mismatch.

REQUIRED_BEHAVIOR:
- Preserve the original real recommendation receipt and all current real RUN proof semantics; do NOT rerun/recreate the recommendation, capacity observations, RUN authorization, or lease.
- The final Git blob bytes of `proofs/TASK-039-M10/recommendation-receipt.txt` must be byte-for-byte identical to the original external receipt and SHA-256 to `01e76d5d13581121e73cd2836097e5b487785468f800122c4169eae99286f935`.
- `PROOF.json` semantic content and proof fingerprint `73bac304...` should remain unchanged unless an independently justified proof-semantic correction becomes necessary.
- Final review must mechanically fetch the Git blob bytes and recompute the receipt SHA-256 after publication.

FORBIDDEN_IMPLEMENTATIONS:
- Do not rewrite the external receipt after authorization or forge its mtime.
- Do not rerun `bridge.py recommend` to manufacture a replacement causal receipt.
- Do not refresh capacity solely to obtain new fingerprints.
- Do not change M10.1/M10.2 production code or Bridge publication semantics for this task.
- Do not weaken the byte-for-byte requirement to normalized-text equality.
- Do not change `PROOF.json` to the LF-normalized hash merely to make the mismatch disappear; that would no longer bind the original real receipt.
- Do not add `.gitattributes` to the tracked task scope unless Primary Brain explicitly revises the locked scope; prefer a local publication-safe Git attribute/staging mechanism.

REQUIRED_FIX / OPERATIONAL_CLOSE_PATH:
1. Keep the existing external runtime receipt untouched.
2. Restore `proofs/TASK-039-M10/recommendation-receipt.txt` from that exact external raw receipt so its working-tree SHA-256 is `01e76d5d...`.
3. Before FIX publication, configure the local repository's non-versioned `.git/info/attributes` for this exact path as `-text`, so Bridge's normal `git add` stores CRLF bytes without EOL normalization. This is local publication metadata, not a worktree artifact.
4. Add/retain bounded test coverage documenting the byte-exact receipt invariant; no production redesign.
5. Human performs the normal Bridge FIX publication.
6. Independent Round-2 review fetches the committed receipt as raw/base64 bytes and requires SHA-256 `01e76d5d...` exactly.
7. Remove the temporary local `.git/info/attributes` line after successful publication if desired; it is not part of canonical repo state.

REQUIRED_TESTS / CHECKS:
- Existing receipt-copy byte-exact/drift test remains green.
- Existing receipt parser/BOM/symlink/fuzzy-path adversarial tests remain green.
- Existing proof fingerprint tamper tests remain green.
- Add a focused regression/documentation test if useful, but the mandatory close check is post-publication raw Git-blob SHA-256 equality because ordinary pre-commit tests cannot prove Git did not normalize EOLs during staging.
- Full repo suite remains green.

CLOSE_CONDITIONS:

```text
FINAL_GIT_RECEIPT_RAW_SHA256: 01e76d5d13581121e73cd2836097e5b487785468f800122c4169eae99286f935
PROOF_RECEIPT_SHA256:         01e76d5d13581121e73cd2836097e5b487785468f800122c4169eae99286f935
RECEIPT_BYTE_IDENTITY: PASS
PROOF_FINGERPRINT_RECOMPUTE: 73bac3049b10704e92637aa507a133a9c409530d25879c939ce4e6ec1ff86795
REAL_CHAIN_RERUN: NO
M10_1_PRODUCTION_CHANGED: NO
M10_2_PRODUCTION_CHANGED: NO
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
```

ALLOWED_FILES FOR FIX:
- `proofs/TASK-039-M10/recommendation-receipt.txt`
- `tests/aios_bridge/test_m10_real_dispatch_proof.py` only if a bounded regression/documentation test is added
- `.ai/results/RESULT-039.md` only as Bridge-generated publication evidence

LOCAL NON-WORKTREE PUBLICATION METADATA ALLOWED:
- `.git/info/attributes` exact path rule for `proofs/TASK-039-M10/recommendation-receipt.txt -text`

FORBIDDEN_SCOPE:
- `bridge.py`
- `src/aios_bridge/runtime_dispatch.py`
- `src/aios_bridge/continuity/dispatch.py`
- lease/failover/hot-handoff/provider/API code
- TASK/ADR/blueprint semantics
- external runtime receipt/capacity/auth/lease mutation

---

## Final Decision

```text
R1-1: OPEN
LINEAGE_AUDIT: PASS
SCOPE_AUDIT: PASS
REAL_CHAIN_INTERNAL_CONSISTENCY: PASS
PROOF_FINGERPRINT_RECOMPUTE: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
PUBLICATION_BYTE_IDENTITY: FAIL
M10_3: CHANGES_REQUIRED
STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
```

The real dispatch chain itself is preserved and should not be rerun. The required fix is narrowly scoped to publication-time byte preservation of the already-validated real receipt.