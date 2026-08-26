# TASK-097 — Codex Interactive Parity + Publication Safety Lock

STATUS: SUPERSEDED
PUBLISHER_PROFILE: CANONICAL_E4
TASK_ID: TASK-097
SUPERSEDED_BY_ADR: ADR-068
SUPERSEDED_BY_TASK: TASK-098
EXECUTION_AUTHORIZED: NO
FIX_AUTHORIZED: NO
CERTIFICATION_AUTHORIZED: NO
MERGE_AUTHORIZED: NO
TASK_095_RESUME_AUTHORIZED: NO

## Supersession reason

TASK-097 was a bounded recovery patch for the existing Bridge normal execution path. Its candidate demonstrated that continuing to patch the current worker/publish stack would preserve architectural ambiguity around validation ownership, provider-specific orchestration, fail-open publication fallbacks and long-running command polling.

Human + Architect authority therefore supersedes the TASK-096/TASK-097 normal-path recovery design with ADR-068 and TASK-098.

Do not RUN, FIX, certify or merge TASK-097.

Historical candidate remains evidence only:

```text
CANDIDATE_HEAD: 2d1e321154c038fff01bd83ace319fa38ef2895c
BASE_MAIN: 558e666cc5808f5574862feaa8562a7d8c70e86f
RESULT: .ai/results/RESULT-097.md
REVIEW_ROUND_1: CHANGES_REQUIRED
```

## Replacement path

```text
ADR-068 — AIOS Bridge Kernel v1 Execution Lifecycle Lock
TASK-098 — AIOS Bridge Kernel v1 Bootstrap
```

TASK-098 builds a new execution kernel alongside the legacy Bridge. The old Bridge remains compatibility/bootstrap only until real Kernel smoke proofs pass.

This superseded artifact intentionally contains no executable dispatch or allowed-path markers. Any attempt to execute it must fail closed.
