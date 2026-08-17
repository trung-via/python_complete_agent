# REVIEW-030 — TASK-030 M6 Stable-Boundary Executor Failover

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 2 — Delta Fix Review / Stage 0
- Previous reviewed head: `1ffb9f10eb4363b1455d9fcdacba4ff1914bd2fe`
- Tested implementation: `c0a89818d8ec08b0de0b986a549d2e7f6134b95c`
- Reviewed branch head: `8a909d16eaba0f7ae796ed95a4cde63c11f5a683`
- Base main: `f36432c953fd84b8a38288f3d8580d2057a15cfc`
- Branch: ahead 4 / behind 0; exact merge-base main.

```text
FULL_SEMANTIC_REVIEW: FAIL in Round 1
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: FAIL
M6_PROOF_REQUIRED: BLOCKED_UNTIL_SEMANTIC_FIXES
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Round-1 Finding Status

- `R1-1` CLOSED — shared stable-boundary helper now enforces local HEAD, remote task branch, fresh REVIEW blob/status and no active lease for both handoff/approve.
- `R1-2` CLOSED — failover proof uses authoritative remote control commit only; publish revalidates exact control commit + REVIEW blob/status.
- `R1-3` CLOSED — actual executor switch requires explicit user-supplied `--executor`.
- `R1-4` CLOSED — exact role paths, required schema_version and canonical size bound are enforced.
- `R1-5` PARTIAL / OPEN — post-acquire block now covers proof/auth/state, but rollback does not restore authorization after authorization persistence succeeds and a later step fails.

## Remaining / New Findings

### R1-5 HIGH — Handoff rollback can leave replacement ACTIVE authorization after releasing replacement lease
Cross-executor `cmd_handoff()` performs:

```text
acquire replacement lease
-> build/validate proof
-> save replacement ACTIVE authorization (overwrites prior CONSUMED source auth)
-> update_state
```

If `update_state()` fails after `save_authorization()` succeeds, the exception handler releases the replacement lease but does not restore the prior CONSUMED source authorization. This leaves an ACTIVE replacement authorization with no active lease and loses the authoritative prior auth record. A retry with the same replacement executor can then be classified as ordinary same-executor FIX and bypass the intended failover proof path.

Required:
- preserve an exact copy of prior authorization before replacement persistence;
- on any post-save failure, restore prior CONSUMED authorization (or fail into explicit `RECOVERY_REQUIRED` if restoration cannot be proven);
- rollback diagnostics must report lease/auth/state recovery independently;
- add fault injection specifically for `update_state()` failure after successful replacement `save_authorization()` and verify prior CONSUMED auth is restored and no replacement lease remains.

### R2-1 HIGH — Missing source executor identity can downgrade cross-executor FIX into ordinary FIX
Current classification is effectively:

```text
is_failover = prior_auth exists
              and prior_auth.executor_id is not None
              and prior_auth.executor_id != selected_executor
```

Therefore a prior/pre-M5/malformed authorization with missing `executor_id` makes `is_failover = False`. An explicit `--executor codex` FIX can then enter the ordinary same-executor path without source stable-boundary proof. This violates C12 and the adversarial requirement that missing/pre-M5 source authorization cannot authorize a cross-executor replacement.

Required:
- FIX classification must fail closed when a prior authorization exists but source executor identity / M5 lease binding is missing or malformed;
- do not treat unknown source identity as "same executor";
- explicit Codex FIX with missing prior auth/source identity must reject before lease acquisition;
- add missing-auth, missing-executor-id and missing-lease-binding tests.

### R2-2 MEDIUM — Bridge RESULT generator cannot yet emit mandatory Stage-A/Stage-B proof-progress evidence
TASK-030 requires Stage-A RESULT to contain:

```text
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

and Stage-B RESULT to contain both PASS. `cmd_publish()` currently overwrites `RESULT-030.md` and emits only the immediate failover manifest (`EXECUTOR_FAILOVER`, from/to, source SHA, proof fingerprint, review blob). A worker-authored proof-progress manifest is therefore discarded during publish.

Required:
- make Bridge-generated RESULT capable of carrying the TASK-030 real-proof progress fields deterministically;
- Stage A must record A=PASS/B=PENDING only for a validated `antigravity -> codex` failover;
- Stage B must record B=PASS and preserve/prove A=PASS from prior immutable repository/review evidence rather than merely assuming it from executor direction;
- ordinary same-executor FIX must keep both proof directions pending/unchanged and must not fabricate PASS;
- add tests proving worker-prepared RESULT cannot be the source of truth and Bridge emits the required canonical proof-progress fields.

## Evidence Note
The implementation commit reports 25 failover tests, 47 Bridge tests, 152 Continuity tests and 746 full-repository tests green. The final Bridge-generated RESULT at reviewed head records the focused command as 72 passed. Next RESULT should preserve bounded review-manifest evidence needed for the proof stages.

## Scope Check
Still clean:
- M5 lease semantics unchanged;
- no Claude Code;
- no dirty/hot handoff;
- no TTL/heartbeat/steal;
- no quota/router/automatic executor selection;
- no paid external API path;
- no merge authority widening.

## Next Stage
Do **not** start Codex proof A yet.

Run one more ordinary same-executor Antigravity FIX to close `R1-5`, `R2-1`, and `R2-2`. Keep both real proof directions PENDING. If Round 3 closes these findings, Primary Brain will issue the controlled proof review:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M6_PROOF_REQUIRED: ANTIGRAVITY_TO_CODEX
```

## Decision
`CHANGES_REQUIRED`
