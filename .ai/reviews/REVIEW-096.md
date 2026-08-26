# REVIEW-096 — Codex Interactive Executor Parity Recovery

PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
FINAL_PASS: NO
TASK_ID: TASK-096
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: c1c5cd882e092fd6f894feb37eb56765e3169cb7
REVIEWED_BASE_MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
TASK_ARTIFACT_BLOB_SHA: c3581ea89cb937314fa97c10b7124e844ffba080
RESULT_BLOB_SHA: dd083bb22b383d9275b192ff8bb66428d5dbd2a7
EXECUTOR_ID: antigravity
BLOCKERS_REMAINING: 1
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
FIX_EXECUTION_MODE: IMPLEMENTATION
TASK_095_RESUME_AUTHORIZED: NO
PYTHON_AGENT_FAST_LANE_PILOT_AUTHORIZED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

## Review summary

The core recovery direction is correct and materially achieves the intended architecture:

- normal Codex RUN no longer invokes `bridge.py execute`;
- normal Codex FIX/IMPLEMENTATION no longer invokes nested execution;
- both Codex and Antigravity return `AUTHORIZED` with `executor_invocations=0`;
- handoff still invokes `cmd_context(args)`, so the visible session receives the compact Slim interactive context;
- Codex compact context is no longer suppressed;
- machine-only roadmap prose remains omitted;
- legacy `CodexLocalTransport` remains available but is not the normal worker happy path;
- targeted validation is reported PASS and candidate-stage T2 count remains 0.

One blocker remains before Codex can be used as the real TASK-095 smoke proof.

## Finding B096.1 — AUTHORIZED adapter guidance is hard-coded to Antigravity

Severity: BLOCKING

The shared adapter `.agents/skills/aios-worker/scripts/aios_worker.py` still prints this line for every `AUTHORIZED` result:

```text
NEXT: continue in the authorized Antigravity worker session
```

That output is wrong when `--adapter codex` was explicitly selected. It violates the locked cross-surface identity contract and can instruct the visible Codex worker to hand work to the wrong surface immediately after successful authorization.

### Required fix

Make the `AUTHORIZED` continuation guidance provider-neutral and exact to the selected adapter, for example:

```text
NEXT: continue in the authorized codex worker session
```

for Codex and:

```text
NEXT: continue in the authorized antigravity worker session
```

for Antigravity.

Do not infer or substitute another executor. Do not introduce retry/reroute behavior.

Add focused tests at the adapter/control-surface level proving both outputs bind to the explicitly selected adapter and that Codex output never contains the Antigravity continuation string.

## Non-blocking note

Some comments/test module prose still describe the historical Codex `handoff -> execute` behavior. These are not runtime blockers, but if touched by the focused fix they should be aligned to the new parity model without widening scope.

## Re-review acceptance

```text
CODEX_AUTHORIZED_GUIDANCE_BINDS_CODEX: PASS
ANTIGRAVITY_AUTHORIZED_GUIDANCE_BINDS_ANTIGRAVITY: PASS
CROSS_SURFACE_GUIDANCE_CONFUSION: NONE
NORMAL_CODEX_NESTED_EXECUTE: REMOVED
CODEX_INTERACTIVE_IMPLEMENTATION: ENABLED
CODEX_COMPACT_CONTEXT: ENABLED
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_095_RESUME_AUTHORIZED: NO
```

After the focused FIX is republished, semantic re-review is required. Full canonical T2 remains deferred to `certify-reviewed 96` only after semantic acceptance.