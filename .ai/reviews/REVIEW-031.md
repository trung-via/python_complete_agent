# REVIEW-031 — TASK-031 M7 Third Executor Portability Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 1 — Initial Full Semantic Review / Stage 0
- Base main: `8a1550b40692798fe0c049aa2ad74d55c54618ee`
- Reviewed branch head: `a9e37746c0cedee269138686ff5aa76c4a235c3f`
- Branch relation: ahead 1 / behind 0; exact merge-base main.
- Authoritative contracts: ADR-021 + TASK-031.

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
M7_PROOF_REQUIRED: BLOCKED_UNTIL_SEMANTIC_FIXES
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Positive Findings

The implementation is structurally close to the locked M7 design:

- runtime allowlist is exactly `antigravity,codex,claude-code`;
- Claude-specific logic was not added to Continuity Core;
- branch delta is limited to `bridge.py`, `tests/test_bridge.py`, and `RESULT-031.md`;
- M6 stable-boundary lease/failover machinery is reused instead of redesigned;
- TASK-031 proof progress uses exact predecessor SHA provenance rather than arbitrary history scans;
- Antigravity -> Claude Code, Claude Code -> Antigravity, and Claude Code -> Claude Code flows are exercised through existing M6 authorization/lease semantics;
- current initial RESULT truthfully leaves both real proof directions PENDING;
- Antigravity reports a fresh full repository run of `752 passed, 0 failed`.

These positives are not sufficient to open the real Claude Code proof while the findings below remain open.

## Findings

### R1-1 HIGH — M7 portability/scope attestations are emitted as unconditional constants instead of being fail-closed against the repository delta

TASK-031 C2 and the Expected Implementation Boundary require Continuity Core to remain unchanged, and explicitly require the run to STOP/escalate if those files change rather than claim completion. C1/C12 likewise require exactly three runtime executors and forbid a fourth executor.

Current `cmd_publish()` emits TASK-031 fields equivalent to:

```text
CONTINUITY_CORE_CHANGED: NO
M5_LEASE_SEMANTICS_CHANGED: NO
M6_FAILOVER_CONTRACT_CHANGED: NO
FOURTH_EXECUTOR_ADDED: NO
```

unconditionally whenever `task_id == 31`.

The current Round-1 branch happens to satisfy those claims, but Bridge does not enforce them. A later Stage-A/Stage-B/repair Executor could modify a forbidden Continuity Core file or widen the runtime executor set and Bridge would still generate the same `NO` attestations. That weakens the canonical evidence layer for the portability proof.

Required remediation:

1. Add a narrow TASK-031 portability-scope validation before tests / RESULT mutation.
2. Compare the task branch/worktree against the locked M7 base `8a1550b40692798fe0c049aa2ad74d55c54618ee` (or an equivalently immutable M7 baseline) and fail closed if any C2-forbidden Continuity Core file differs.
3. Require `SUPPORTED_RUNTIME_EXECUTORS` to remain exactly `("antigravity", "codex", "claude-code")` before emitting the M7 manifest.
4. Add deterministic regression tests proving a forbidden core-file change and a fourth-executor widening cannot publish a successful M7 RESULT.
5. Do not redesign M5/M6; this is only an M7 evidence/scope gate.

### R1-2 MEDIUM — Initial formal RESULT manifest is incomplete versus the locked TASK-031 minimum schema

TASK-031 requires the initial RESULT manifest to report at minimum:

```text
BRIDGE_TESTS: <count/pass>
CONTINUITY_TESTS: <count/pass>
FULL_REPO_TESTS: <count/pass>
REGRESSIONS: 0
```

Current RESULT-031 contains the full pytest transcript and proves `752 passed`, but those required fields are absent from the formal YAML Review Manifest.

Required remediation:

- make the Bridge-published TASK-031 manifest contain these four fields with truthful evidence;
- run the relevant Bridge and Continuity suites plus the full repository suite as needed to support the reported counts;
- keep proof progress fields Bridge-generated and do not accept worker-authored proof text as authority.

### R1-3 MEDIUM — Required explicit Claude Code RUN-path portability test is missing

TASK-031 Required Automated Tests item 4 requires proof that an initial Human RUN explicitly selecting `claude-code` persists the exact Claude Code executor identity into the M5 authorization/lease.

The new tests cover:

- Antigravity -> Claude Code FIX through `cmd_handoff()`;
- Claude Code -> Antigravity FIX through legacy `cmd_approve()`;
- Claude Code -> Claude Code ordinary FIX;
- TASK-031 proof-progress generation/preservation/forgery resistance.

But the Round-1 delta does not add a test for the distinct RUN activation path with `executor=claude-code`.

Required remediation:

- add a deterministic temp-repo test for explicit Claude Code RUN through the Bridge activation path;
- assert ACTIVE authorization `executor_id == "claude-code"`, exact active lease `executor_id == "claude-code"`, correct RUN operation/binding, and no fabricated failover metadata;
- preferably exercise both direct handoff RUN and legacy approve RUN if that can be done without duplicating large fixtures.

## Test Evidence Reviewed

Reported by Antigravity / Bridge RESULT:

```text
full repository: 752 passed, 0 failed
paid external API calls: 0 (reported)
live external calls in automated tests: 0 (reported)
```

The full repository test result is accepted as execution evidence, but it does not waive the missing formal manifest fields or the missing required RUN-path test.

## Controlled Proof Gate

Do NOT start Claude Code Proof A yet.

After R1-1 through R1-3 are closed and the semantic delta is clean, Primary Brain may issue:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M7_PROOF_REQUIRED: ANTIGRAVITY_TO_CLAUDE_CODE
```

Until then both real-proof fields remain:

```text
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
```

## Next Step

Run an ordinary Antigravity FIX:

```text
/aios-worker FIX TASK-031 --executor antigravity
```

Keep the fix narrow to `bridge.py`, `tests/test_bridge.py`, and `RESULT-031.md`. Do not modify Continuity Core, M5 lease semantics, M6 failover proof schema, router/quota behavior, or add any fourth executor.

After publish, return with `Review TASK-031`.

## Decision

`CHANGES_REQUIRED`
