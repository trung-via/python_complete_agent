# P6.1 Live Capture Checkpoint Boundary

TASK-166 adds one explicit Product Intelligence `capture` operation for staging real Shopee
evidence outside the repository. It composes the existing TASK-137 CDP manager, TASK-146
discovery/ranking path, and `ShopeeScrapeTool`; it does not replace or extend any of those
authorities.

AIOS engineering RUNs and their Runtime verification remain deterministic and offline. Live
capture is a separate, Human-invoked Product Intelligence operation and is never a verification
step, executor wait state, or AIOS interaction. Capture artifacts, including checkpoints, media,
source packs, and the final bundle, remain under an explicit external job root and are not
automatically imported into Git.

Shopee CAPTCHA and security challenges remain Human-owned. The operation does not log in, solve,
bypass, retry, wait, restart the browser, change navigation, or alter a query. A challenge produces
`CHALLENGE_REQUIRED` at the exact unfinished phase. After the Human resolves it in the same
operator-owned Chromium session, an explicit `capture --resume` with the checkpoint-frozen CDP
endpoint continues only that unfinished phase. Other failures are terminal and non-resumable.

Completion exclusively creates the immutable `capture_bundle.json`, then marks the checkpoint
`READY`. The bundle records ordered Human-query cohort provenance and two byte-digest manifest
references per cohort. It contains no CDP endpoint, credentials, session state, or absolute paths.

TASK-165 remains unpublished, blocked P6.1b evidence. REVIEW-165-003 F1 and its failed
remediation/repair continuation lineage demonstrated that live capture inside an AIOS engineering
lineage is the wrong operational boundary. TASK-166 is the blocker correction, not P6.1b
completion. Only after TASK-166 Runtime PASS, semantic PASS, publication, and Human review of one
external READY bundle may a fresh P6.1b successor consume that bundle. P6.2 remains blocked until
reviewed empirical P6.1b metrics exist.
