# REVIEW-030 — TASK-030 M6 Stable-Boundary Executor Failover

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 6 — Controlled Real Proof A review
- Proof-A source boundary: `9e07edc16690e2549a377e596c05089b3331fd97`
- Proof-A published head: `4b9827b85955dcde14d852bfbeb7aaadaf66ddef`
- Base main: `f36432c953fd84b8a38288f3d8580d2057a15cfc`

```text
FULL_SEMANTIC_REVIEW: PASS AFTER REMEDIATION
KNOWN_FINDINGS: CLOSED
DELTA_FIX_REVIEW: PASS
SEMANTIC_FINDINGS: NONE
M6_PROOF_REQUIRED: CODEX_TO_ANTIGRAVITY
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Proof A Decision

Proof A is accepted.

The published Proof-A commit is the direct child of the exact Antigravity source boundary and changes only `.ai/results/RESULT-030.md`; no production or test code changed in the Codex proof round.

Bridge-generated RESULT evidence binds:

```text
EXECUTOR_ID: codex
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: antigravity
FAILOVER_TO_EXECUTOR: codex
FAILOVER_SOURCE_PUBLISHED_SHA: 9e07edc16690e2549a377e596c05089b3331fd97
FAILOVER_REVIEW_BLOB_SHA: f27586f4ba7c09d6e18802b7cbf35975af82e78f
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

Focused Bridge + executor-failover tests report `75 passed, 0 failed`. The immediately preceding semantic-closeout boundary had already run the full repository suite with `749 passed, 0 failed`; Proof A itself introduced no code delta.

## Controlled Real Proof B Gate

Next authorized transition MUST be:

```text
source executor:       codex
source published SHA:  4b9827b85955dcde14d852bfbeb7aaadaf66ddef
replacement executor:  antigravity
replacement operation: FIX
```

Human must explicitly select `executor=antigravity` for this reverse failover proof. The normal ADR-020 stable-boundary chain remains mandatory: prior authorization must be CONSUMED; local HEAD and remote task branch must equal the exact source published SHA; source RESULT must resolve from that exact SHA; this REVIEW must be exact CHANGES_REQUIRED control evidence; and no ACTIVE lease may exist before replacement acquisition.

Proof B may be RESULT-only if no semantic repair is needed. It must execute through the real Bridge lease/auth/publish chain and produce Bridge-generated evidence equivalent to:

```text
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: codex
FAILOVER_TO_EXECUTOR: antigravity
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PASS
```

After Antigravity publishes Proof B, return to Primary Brain with `Review TASK-030`. If Proof B is valid and no new semantic finding appears, Primary Brain will run the mandatory Final Independent Audit before APPROVED.

## Scope Check
- M5 single-active-executor semantics unchanged.
- No third executor, hot/dirty handoff, TTL/heartbeat/lease steal, router, automatic executor selection, paid API path, or merge authority widening.

## Decision

`CHANGES_REQUIRED` only because mandatory reverse real proof B is still incomplete.
