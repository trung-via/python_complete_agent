# REVIEW-096 — Codex Interactive Executor Parity Recovery

PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
FINAL_PASS: NO
TASK_ID: TASK-096
REVIEW_ROUND: 2
REVIEWED_TASK_HEAD_SHA: 6ce4df02bb37deb08b005b0c7a193adac7eabb0c
REVIEWED_BASE_MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TASK_ARTIFACT_BLOB_SHA: c3581ea89cb937314fa97c10b7124e844ffba080
RESULT_BLOB_SHA: 1df3e728f055d05d2ea67e31478dcf88a5d131b8
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 2
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: NOT_RUN_AT_REVIEW
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
RECONCILIATION_ADR: ADR-067
RECONCILIATION_ADR_BLOB_SHA: db17c1b3f4a359c97f2dd59b8c90f7b7acdd7810
SUPERSEDED_BY_TASK: TASK-097
TASK_095_RESUME_AUTHORIZED: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

## Round-2 findings

### B096.1 — Cross-surface AUTHORIZED guidance — CLOSED

The focused adapter change correctly binds the continuation message to the explicitly selected adapter:

```text
codex       -> NEXT: continue in the authorized codex worker session
antigravity -> NEXT: continue in the authorized antigravity worker session
```

Focused tests were added for both outputs.

### B096.2 — Unauthorized task_authoring mutation — BLOCKING

The FIX commit also changes `src/aios_bridge/task_authoring.py`, which is not in TASK-096 `EXECUTOR_ALLOWED_PATHS_JSON`.

This mutation was introduced to compensate for a malformed Round-1 REVIEW authored by ChatGPT: that REVIEW omitted the executable FIX machine markers required by the baseline Bridge (`EXECUTOR_CONTEXT_REFS_JSON`, `EXECUTOR_ALLOWED_PATHS_JSON`, and a FIX dispatch policy). The correct recovery is to author canonical REVIEW markers, not weaken task-authoring preflight or widen TASK authority.

Because the candidate now contains an out-of-scope committed mutation, it is not eligible for semantic acceptance.

### B096.3 — Interactive publish does not derive exact task allowed paths — BLOCKING

The parity architecture removes normal Codex execution through the nested `bridge.py execute` gate. That old gate enforced `validate_executor_worktree_delta(... allowed_paths=snapshot["allowed_paths"])` before publication.

Normal interactive `bridge.py publish` currently validates dirty-path scope only when `args.allowed_paths` is already supplied (or hot-handoff metadata supplies it). The Codex/Antigravity interactive worker flow does not supply machine-bound `allowed_paths`; therefore direct interactive publication can commit a path outside TASK scope. The presence of `src/aios_bridge/task_authoring.py` in the published RESULT proves this gap is operational, not theoretical.

Required recovery:

```text
interactive publish
-> require exact ACTIVE authorization + ACTIVE exact lease
-> derive exact control snapshot from that authorization
-> take allowed_paths only from machine-verified snapshot
-> validate dirty paths before commit/push
-> fail closed on missing/drifted scope evidence
```

Do not accept model/caller-provided scope as authority. Do not modify `legacy_bridge.py`.

## Decision

TASK-096 candidate is rejected and superseded by a clean replacement TASK-097 from exact certified main `558e666cc5808f5574862feaa8562a7d8c70e86f`.

Do not run `FIX TASK-096` again. Do not certify or merge TASK-096.

TASK-097 must reimplement the accepted parity changes from clean main, include the adapter-guidance fix, and add machine-derived interactive publication scope enforcement while preserving all existing authorization/lease/review/certification boundaries.
