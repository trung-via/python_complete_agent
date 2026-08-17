# REVIEW-030 — TASK-030 M6 Stable-Boundary Executor Failover

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 1 — Full Semantic Review / Stage 0
- Reviewed branch: `ai/task-030`
- Reviewed head: `1ffb9f10eb4363b1455d9fcdacba4ff1914bd2fe`
- Tested implementation: `3347c2433c05478ea0f9b3f1f6d4ff565370f1a8`
- Base main: `f36432c953fd84b8a38288f3d8580d2057a15cfc`
- Branch: ahead 2 / behind 0; exact merge-base main.

```text
FULL_SEMANTIC_REVIEW: FAIL
SEMANTIC_FINDINGS: OPEN
M6_PROOF_REQUIRED: BLOCKED_UNTIL_SEMANTIC_FIXES
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Findings

### R1-1 HIGH — Stable-boundary parity incomplete
`cmd_handoff()` tolerates inability to resolve the remote task branch during failover; `cmd_approve()` does not assert remote task branch == prior `published_sha` at all. `cmd_approve()` also does not freshly revalidate the current REVIEW blob/status before replacement lease acquisition. This violates C13/C16/C24.

Required: shared fail-closed validation for local HEAD, remote task branch, current REVIEW blob and `CHANGES_REQUIRED` status before replacement acquisition, with drift/missing-ref tests for both handoff and approve.

### R1-2 HIGH — REVIEW control-commit binding not exact
Failover activation falls back from the authoritative remote control ref to local control ref and then `HEAD`. Publish checks current REVIEW blob but not that current fetched control commit equals `proof.review_ref.ref`.

Required: authoritative remote control commit only; no fallback. Publish must require exact control commit ref + exact review blob/status.

### R1-3 HIGH — Replacement Executor may be selected implicitly
`executor=None` defaults to `antigravity`. After a prior consumed Codex execution, an ordinary FIX with no explicit executor selector becomes `codex -> antigravity` failover. M6 requires explicit Human replacement selection.

Required: if selected executor differs from prior consumed executor, require explicit user-supplied executor selection. Add omitted-vs-explicit regression tests.

### R1-4 MEDIUM — Canonical proof strictness gaps
`StableExecutorFailoverProof` currently:
- accepts `RESULT-30.md` / `REVIEW-30.md` aliases for `TASK-030` due integer normalization;
- accepts missing `schema_version` and defaults it;
- lacks canonical `<= MAX_SERIALIZED_BYTES` enforcement for direct/dict construction.

Required: exact task-token role paths, explicit required schema_version, canonical serialized-size enforcement on every construction path, plus regression tests.

### R1-5 MEDIUM — Handoff post-acquire rollback coverage incomplete
In cross-executor `cmd_handoff()`, failover proof construction occurs after replacement lease acquisition but outside the rollback-protected block. A post-acquire failure can escape without guaranteed exact replacement-lease rollback; rollback release errors are swallowed.

Required: one post-acquire transaction covering proof construction, relational validation, auth persistence and activation state. Exact replacement-only rollback; uncertain rollback must emit bounded recovery diagnostics. Add fault-injection coverage.

## Passing Scope Checks
- Expected M6 file boundary only.
- M5 lease store semantics unchanged.
- No Claude Code, hot handoff, TTL/heartbeat/steal, quota/router, paid API, auto launch or merge authority.
- Initial RESULT truthfully leaves both real proof directions PENDING.

## Reported Tests
```text
Failover:   22/22
Lease:      14/14
Bridge:     43/43
Continuity: 149/149
Full repo:  739/739
Regressions: 0
```

## Next Stage
Do not start Codex proof A yet. First run an ordinary same-executor Antigravity FIX to close R1-1..R1-5. Keep both real proof flags PENDING. After semantic review passes, the next controlled review will request `ANTIGRAVITY_TO_CODEX` proof.

## Decision
`CHANGES_REQUIRED`
