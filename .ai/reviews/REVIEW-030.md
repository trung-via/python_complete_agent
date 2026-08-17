# REVIEW-030 — TASK-030 M6 Stable-Boundary Executor Failover

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 4 — Delta Fix Review / Stage 0
- Previous reviewed head: `40ecab28e222df85621f092a46f5474701dd7f6c`
- Reviewed/tested branch head: `dd605785bc9450d75744fb49be3b5e6bc8c316f7`
- Base main: `f36432c953fd84b8a38288f3d8580d2057a15cfc`
- Branch: ahead 6 / behind 0; exact merge-base main.

```text
FULL_SEMANTIC_REVIEW: FAIL in Round 1
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: FAIL
M6_PROOF_REQUIRED: BLOCKED_UNTIL_SEMANTIC_FIXES_AND_FULL_REGRESSION
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
- `R1-5` CLOSED
- `R2-1` CLOSED — FIX activation now fails closed when prior authorization is absent even with omitted `--executor`, strictly reconstructs prior M5 lease binding before same-vs-cross classification, and applies the same helper to handoff and approve. Rejection tests assert no lease acquisition.
- `R2-2` PARTIAL / OPEN — proof-progress preservation now survives same-executor repairs, but provenance is still too broad.

## Remaining Finding

### R2-2 HIGH — Proof progress trusts arbitrary committed RESULT history rather than an exact Bridge-controlled prior publish anchor

`_evaluate_task_030_proof_progress()` currently scans:

```text
git log -n 30 -- .ai/results/RESULT-030.md
```

and promotes proof progress when any historical RESULT contains either a PASS flag or a matching `FAILOVER_FROM_EXECUTOR` / `FAILOVER_TO_EXECUTOR` pair.

This fixes the previous working-tree reset, but it does not prove that the historical RESULT was produced by the immediately preceding successful Bridge publish. Executors have local-git capability; a worker can create and locally commit a fabricated `RESULT-030.md` containing Stage-A/B PASS or failover-direction prose before `cmd_publish()`. That commit is immutable Git history, and the current scan would accept it as proof evidence even though the real selected-executor/lease/auth/publish transition never occurred.

The arbitrary `-n 30` bound also makes valid proof progress non-monotonic: enough same-executor repair commits can push the genuine proof commit out of the scan window and regress PASS to PENDING.

This conflicts with TASK-030 AIP-12/C27/C28: real proof evidence may update only when the actual selected Executor + lease + authorization + Bridge publish chain occurred; worker-prepared evidence must never become the proof source merely by being committed.

Required:
- do not scan arbitrary RESULT history for proof authority;
- bind proof-progress inheritance to one exact prior Bridge-controlled published SHA, preferably copied in bounded form from the prior CONSUMED authorization during same-executor FIX activation;
- at publish, read only `.ai/results/RESULT-030.md` at that exact immutable prior published SHA and validate its canonical proof-progress fields;
- for cross-executor Stage B, the existing exact `source_published_sha` remains the authoritative predecessor anchor;
- malformed/missing predecessor RESULT must not fabricate PASS;
- remove the arbitrary 30-commit history dependence;
- add a regression where a worker locally commits a forged PASS RESULT before publish and Bridge still emits PENDING unless the exact predecessor anchor proves PASS;
- retain existing tests that Stage-A PASS survives same-executor Codex repair and both PASS survive same-executor Antigravity repair.

## Evidence Gate — Full repository regression still missing

Round 3 explicitly required a fresh full-repository suite before proof A could open. Round 4 RESULT reports only:

```text
75 passed
```

for `tests/test_bridge.py + tests/aios_bridge/continuity/test_executor_failover.py`.

There is no fresh full-repository result in RESULT-030 and no CI status attached to the reviewed commit. The next semantic-fix publish must run the full repository suite and report the total/zero-regression result.

## Passing Scope Checks

Still clean:
- M5 lease-store semantics unchanged;
- no Claude Code / third executor;
- no dirty/hot handoff;
- no TTL/heartbeat/lease steal;
- no quota/router/automatic executor selection;
- no paid external API path;
- no merge authority widening.

## Next Stage

Do **not** start Codex proof A yet.

Run one more ordinary same-executor Antigravity FIX. Scope should be limited to exact proof-progress provenance plus tests/evidence. Run focused tests and the full repository suite.

If Round 5 closes R2-2 and full regression is green, Primary Brain will replace this review with the controlled proof gate:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M6_PROOF_REQUIRED: ANTIGRAVITY_TO_CODEX
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

## Decision

`CHANGES_REQUIRED`
