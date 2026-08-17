# REVIEW-030 — TASK-030 M6 Stable-Boundary Executor Failover

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 5 — Delta Fix Review / Stage 0 semantic closeout
- Previous reviewed head: `dd605785bc9450d75744fb49be3b5e6bc8c316f7`
- Reviewed/tested branch head: `9e07edc16690e2549a377e596c05089b3331fd97`
- Base main: `f36432c953fd84b8a38288f3d8580d2057a15cfc`
- Branch: ahead 7 / behind 0; exact merge-base main.

```text
FULL_SEMANTIC_REVIEW: PASS AFTER REMEDIATION
KNOWN_FINDINGS: CLOSED
DELTA_FIX_REVIEW: PASS
SEMANTIC_FINDINGS: NONE
M6_PROOF_REQUIRED: ANTIGRAVITY_TO_CODEX
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
- `R2-1` CLOSED
- `R2-2` CLOSED

## R2-2 Closure Evidence

Proof-progress inheritance no longer scans arbitrary Git history. Bridge now uses one exact predecessor anchor only:

```text
cross-executor failover -> failover proof `source_published_sha`
same-executor FIX       -> ACTIVE auth `prior_published_sha`
```

The same-executor `prior_published_sha` is copied from the immediately preceding prior authorization `published_sha`, which is written only after the prior Bridge publish succeeds. Publish reads only:

```text
<exact predecessor sha>:.ai/results/RESULT-030.md
```

for inherited proof progress. Working-tree RESULT content and unrelated/intermediate commits are not proof authority.

Regression coverage explicitly creates and commits a forged local `RESULT-030.md` containing Stage-A PASS before Bridge publish; Bridge still emits `PENDING/PENDING`. Existing tests also retain Stage-A PASS across a same-executor Codex repair and retain both PASS values across a later same-executor Antigravity repair.

## Regression Evidence

Round 5 ran the requested full repository suite:

```text
749 passed
0 failed
66.30s
```

Warnings are existing deprecation/runtime warnings and no regression failure is reported.

Current Stage-0 RESULT truthfully remains:

```text
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

## Controlled Real Proof A Gate

Semantic implementation is now clean, but TASK-030 remains incomplete because C27/C28 require real transitions.

Next authorized transition MUST be:

```text
source executor:      antigravity
source published SHA: 9e07edc16690e2549a377e596c05089b3331fd97
replacement executor: codex
replacement operation: FIX
```

Human must explicitly select `executor=codex`. Omitted/default executor selection does not satisfy this proof gate.

Before replacement lease acquisition, Bridge must revalidate the normal ADR-020 stable-boundary chain: prior authorization CONSUMED, local HEAD and remote task branch equal the exact source published SHA, source RESULT resolved from that exact SHA, this REVIEW is exact `CHANGES_REQUIRED` control evidence, and no ACTIVE lease exists.

Codex proof A may make a RESULT-only/proof-required delta if no semantic repair is necessary, but it must execute through the real Bridge lease/auth/publish chain and produce Bridge-generated evidence equivalent to:

```text
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: antigravity
FAILOVER_TO_EXECUTOR: codex
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

After Codex publishes, return to Primary Brain with `Review TASK-030`. If proof A is valid and no new semantic finding exists, the next controlled review will request `CODEX_TO_ANTIGRAVITY` proof B.

## Scope Check

Still clean:
- M5 single-active-executor lease semantics unchanged;
- no third executor / Claude Code;
- no dirty/hot handoff;
- no TTL/heartbeat/lease steal;
- no quota/router/automatic executor selection;
- no paid external API path;
- no merge authority widening.

## Decision

`CHANGES_REQUIRED` only because mandatory real proof A/B acceptance evidence is not complete. There are no open semantic code findings at this stage.
