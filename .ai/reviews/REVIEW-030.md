# REVIEW-030 — TASK-030 M6 Stable-Boundary Executor Failover

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 3 — Delta Fix Review / Stage 0
- Previous reviewed head: `8a909d16eaba0f7ae796ed95a4cde63c11f5a683`
- Reviewed/tested branch head: `40ecab28e222df85621f092a46f5474701dd7f6c`
- Base main: `f36432c953fd84b8a38288f3d8580d2057a15cfc`
- Branch: ahead 5 / behind 0; exact merge-base main.

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

## Finding Status

- `R1-1` CLOSED
- `R1-2` CLOSED
- `R1-3` CLOSED
- `R1-4` CLOSED
- `R1-5` CLOSED — handoff rollback now restores prior CONSUMED authorization after a post-save `update_state()` failure, releases only the exact replacement lease, and reports recovery state.
- `R2-1` PARTIAL / OPEN
- `R2-2` PARTIAL / OPEN

## Remaining Findings

### R2-1 HIGH — Missing prior authorization can still downgrade a real cross-executor FIX when `--executor` is omitted
Current FIX classification does this when `prior_auth is None`:

```text
if explicit_executor or selected_executor != antigravity:
    reject
else:
    is_failover = False
```

Because omitted `--executor` defaults to `antigravity`, a missing authorization file after a prior Codex execution can still become an ordinary Antigravity FIX. The Bridge no longer has source identity, so it cannot prove this is same-executor; fail-closed semantics require rejection rather than assumption.

The new test called `test_handoff_and_approve_fix_fails_closed_when_prior_auth_missing_or_malformed` tests explicit `antigravity` and explicit `codex`, but does not test omitted executor, and it exercises handoff rather than both activation paths.

The same classification exists in `cmd_approve()`.

Additionally, existing prior M5 binding is checked only for truthiness before same-executor classification. Malformed-but-nonempty lease/workspace/fingerprint values can still be treated as ordinary same-executor FIX without strict canonical reconstruction.

Required:
- for M6 FIX activation, if prior authorization is absent, fail closed for both handoff and approve; do not infer Antigravity from the CLI default;
- when prior authorization exists, strictly reconstruct/validate its M5 lease binding before classifying same-vs-cross executor (or an equivalent strict helper);
- add handoff + approve regression cases for omitted executor with missing prior auth and malformed nonempty M5 binding;
- no lease acquisition may occur in these rejection cases.

### R2-2 MEDIUM — Proof progress is generated, but ordinary same-executor FIX can erase already-proven progress
Bridge now correctly overwrites worker-prepared RESULT content and emits:

```text
Stage A: PASS / PENDING
Stage B: PASS / PASS
```

for validated failover directions. However `_evaluate_task_030_proof_progress()` initializes both directions to `PENDING` and only promotes them when the **current** authorization is a failover.

Therefore after a valid Stage-A `antigravity -> codex` publish, any required same-executor Codex FIX before Stage B would produce:

```text
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

and erase the already-proven Stage-A progress from the canonical RESULT. This conflicts with the Round-2 requirement that ordinary same-executor FIX keep proof directions pending/**unchanged** and with C29, where semantic repair may be needed between proof stages.

Required:
- for ordinary TASK-030 FIX, preserve previously proven progress only from immutable prior repository evidence, never from the worker-prepared working-tree RESULT;
- Stage-A PASS must survive a same-executor Codex FIX;
- after both proofs PASS, any same-executor repair must preserve both PASS values;
- malformed/missing prior immutable evidence must not fabricate PASS;
- add explicit preservation tests.

## Evidence Requirement
Round 3 reports the complete Bridge + failover focused command as `75 passed`. Because this round changed 583 lines across Bridge/tests, the next semantic-fix RESULT must also include a fresh full-repository regression run before proof A is opened.

## Scope Check
Still clean:
- M5 lease-store semantics unchanged;
- no Claude Code / third executor;
- no hot or dirty handoff;
- no TTL/heartbeat/lease steal;
- no quota/router/automatic executor selection;
- no paid external API path;
- no merge authority widening.

## Next Stage
Do **not** start Codex proof A yet.

Run one more ordinary Antigravity FIX to close only `R2-1` and `R2-2`, and run the full repository suite. Keep current real-proof flags `PENDING/PENDING` for this semantic-fix publish.

If Round 4 closes both findings, Primary Brain will replace this review with the controlled proof gate:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M6_PROOF_REQUIRED: ANTIGRAVITY_TO_CODEX
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

## Decision
`CHANGES_REQUIRED`
