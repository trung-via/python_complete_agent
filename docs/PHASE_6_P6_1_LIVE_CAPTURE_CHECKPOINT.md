# P6.1 Live Capture Checkpoint Boundary — Session/Access Continuity V2

TASK-166 adds one explicit Product Intelligence `capture` operation for staging real Shopee
evidence outside the repository. It composes the existing TASK-137 CDP manager, TASK-146
discovery/ranking path, and `ShopeeScrapeTool`; it does not replace or extend any of those
authorities. TASK-189 hardens only its session/access continuity checkpoint boundary.

AIOS engineering RUNs and their Runtime verification remain deterministic and offline. Live
capture is a separate, Human-invoked Product Intelligence operation and is never a verification
step, executor wait state, or AIOS interaction. Capture artifacts, including checkpoints, media,
source packs, and the final bundle, remain under an explicit external job root and are not
automatically imported into Git.

Shopee CAPTCHA and security challenges remain Human-owned. The operation does not log in, solve,
bypass, retry, wait, restart the browser, change navigation, or alter a query. The V2 checkpoint
uses exactly `NEW`, `SESSION_READY`, `RUNNING`, `HUMAN_ACTION_REQUIRED`, `VERIFY_SESSION`,
`SESSION_LOST`, `READY`, and `FAILED`; its capture phase remains exactly `DISCOVERY`, `ACQUIRE_1`,
`ACQUIRE_2`, or `COMPLETE`. Status owns operational/session control while phase preserves the exact
unfinished marketplace work.

V2 stores only lowercase SHA-256 receipts for the supplied CDP endpoint and the exact borrowed page
target selected by TASK-137 browser authority. It never stores the raw endpoint or raw browser,
context, page, or target identity. Deriving the receipt does not discover, reorder, create, or
navigate a page. A normal resume from `HUMAN_ACTION_REQUIRED` compares endpoint and binding receipts,
enters `VERIFY_SESSION`, and performs one non-mutating generic liveness probe before returning through
`SESSION_READY` and `RUNNING` to the exact unfinished phase. A repeated authoritative access gate
returns to `HUMAN_ACTION_REQUIRED` without progress.

A mismatched binding or specifically closed, disconnected, or unavailable borrowed resource produces
`SESSION_LOST` and performs no unfinished marketplace work. Continuation then requires the Human's
explicit `capture --resume --rebind-session` with a newly supplied endpoint. Rebind establishes the
new receipt, performs the same one liveness probe, and continues the preserved phase; ordinary capture,
evidence, navigation, ranking, storage, and checkpoint failures remain terminal `FAILED`. A valid V1
`CHALLENGE_REQUIRED` checkpoint may resume only with its exact stored endpoint and is atomically
upgraded without retaining that endpoint. Other V1 states gain no mutation authority.

Completion exclusively creates the immutable `capture_bundle.json`, then marks the checkpoint
`READY`. The bundle records ordered Human-query cohort provenance and two byte-digest manifest
references per cohort. It contains no CDP endpoint, credentials, session state, or absolute paths.
Its V1 shape and evidence semantics are unchanged by checkpoint V2. Browser lifecycle/page selection,
Shopee discovery/access-gate detection, extraction, ranking, and product truth remain with their
existing TASK-137, TASK-151, TASK-162, and TASK-166 authorities.

TASK-165 remains unpublished, blocked P6.1b evidence. REVIEW-165-003 F1 and its failed
remediation/repair continuation lineage demonstrated that live capture inside an AIOS engineering
lineage is the wrong operational boundary. TASK-166 is the blocker correction, not P6.1b
completion. Only after TASK-166 Runtime PASS, semantic PASS, publication, and Human review of one
external READY bundle may a fresh P6.1b successor consume that bundle. P6.2 remains blocked until
reviewed empirical P6.1b metrics exist.
