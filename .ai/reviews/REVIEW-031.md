# REVIEW-031 — TASK-031 M7 Third Executor Portability Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 2 — Semantic Re-review after Antigravity FIX
- Base main: `8a1550b40692798fe0c049aa2ad74d55c54618ee`
- Reviewed branch head: `e11b55a44eba7ef5cfe5cfea7475ded29f0b3868`
- Prior review blob: `dede02ba9af7a988ebf5f615f2cd8445507f2eaa`
- Authoritative contracts: ADR-021 + TASK-031 + Round-1 REVIEW-031.

```text
FULL_SEMANTIC_REVIEW: FAIL
ROUND_1_FINDINGS: PARTIALLY_CLOSED
NEW_FINDINGS: OPEN
M7_PROOF_REQUIRED: BLOCKED_UNTIL_SEMANTIC_FIXES
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Round-1 Remediation Status

### R1-3 — CLOSED
A deterministic Claude Code RUN activation test now covers both direct `cmd_handoff()` and legacy `cmd_approve()` paths. It asserts ACTIVE authorization and lease `executor_id == "claude-code"`, RUN operation, and no fabricated failover proof metadata.

### R1-1 — PARTIALLY CLOSED
A TASK-031 portability scope gate was added and is invoked before tests / RESULT mutation. It checks the exact three-executor allowlist and blocks known Continuity Core file changes in committed history and the working tree.

However, the implementation is not fully fail-closed when the underlying Git diff operation itself fails; see R2-1.

### R1-2 — PARTIALLY CLOSED
The formal RESULT manifest now includes `BRIDGE_TESTS`, `CONTINUITY_TESTS`, `FULL_REPO_TESTS`, and `REGRESSIONS`, and the current published RESULT reports `78/78`, `152/152`, `754/754`, and `0` respectively.

However, Bridge currently hard-codes two suite counts and infers the full-repo field from any supplied test command, so the evidence layer can emit unsupported success claims; see R2-2.

## Findings

### R2-1 HIGH — TASK-031 scope validator is not actually fail-closed on Git diff failure

`_validate_task_031_portability_scope()` runs both:

```python
git("diff", "--name-only", base_sha, "HEAD", check=False)
git("diff", "--name-only", "HEAD", check=False)
```

but only inspects the changed-file sets when `returncode == 0`.

If either Git command fails — for example because the base SHA is invalid/unavailable, repository state is damaged, or Git itself errors — validation silently skips that comparison and publish can continue. That violates the Round-1 remediation requirement to fail closed before emitting the M7 scope attestations.

Required remediation:

1. Treat any non-zero return code from either scope diff command as a hard publish failure.
2. Include stderr / failing comparison context in the failure message.
3. Add deterministic tests for:
   - failure of `git diff <base_sha> HEAD`;
   - failure of `git diff HEAD` for working-tree validation;
   - both cases must prevent successful TASK-031 publication.
4. Keep this narrow; do not redesign M5/M6.

### R2-2 HIGH — TASK-031 test evidence fields are not bound to the tests actually executed

Current TASK-031 manifest generation initializes:

```text
BRIDGE_TESTS: 78/78 pass
CONTINUITY_TESTS: 152/152 pass
FULL_REPO_TESTS: 752/752 pass
```

as constants. If `args.test` runs, Bridge extracts only the first generic `<N> passed` match and rewrites `FULL_REPO_TESTS` to `<N>/<N> pass` regardless of what test command was actually executed.

Consequences:

- publishing with only `pytest tests/test_bridge.py` can still claim `CONTINUITY_TESTS: 152/152 pass` without running the Continuity suite;
- publishing any subset that reports `78 passed` can be mislabeled as `FULL_REPO_TESTS: 78/78 pass`;
- future test-count changes can leave the hard-coded Bridge/Continuity counts stale while the manifest still claims success.

This conflicts with TASK-031's requirement for truthful evidence and the Round-1 R1-2 remediation.

Required remediation:

1. Do not emit pass counts that are not derived from authoritative execution evidence for the corresponding suite.
2. Bind each field to its actual command/result, or fail publication when required evidence is absent.
3. `FULL_REPO_TESTS` must only be populated from an actual full-repository test execution, not an arbitrary `args.test` subset.
4. Add deterministic negative tests proving subset runs cannot fabricate Bridge, Continuity, or Full Repo PASS evidence.
5. Preserve Bridge-generated authority for proof-progress fields; do not accept worker-authored evidence text.

## Positive Evidence Reviewed

Current branch head `e11b55a44eba7ef5cfe5cfea7475ded29f0b3868` is a narrow FIX commit relative to the previous TASK-031 implementation and reports:

```text
BRIDGE_TESTS: 78/78 pass
CONTINUITY_TESTS: 152/152 pass
FULL_REPO_TESTS: 754/754 pass
REGRESSIONS: 0
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
```

The fresh full repository transcript reports `754 passed, 0 failed`. These execution results are useful evidence for this specific commit, but they do not repair the semantic evidence-generation flaws above.

## Controlled Proof Gate

Do NOT start Claude Code Proof A yet.

Both real-proof fields remain:

```text
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
```

After R2-1 and R2-2 are closed and the semantic delta is clean, Primary Brain may open the controlled Antigravity -> Claude Code real-proof step.

## Next Step

Run another narrow Antigravity FIX:

```text
/aios-worker FIX TASK-031 --executor antigravity
```

Allowed scope remains `bridge.py`, `tests/test_bridge.py`, and `RESULT-031.md`. Do not modify Continuity Core, M5 lease semantics, M6 failover proof schema, router/quota behavior, or add a fourth executor.

After publish, return with `Review TASK-031`.

## Decision

`CHANGES_REQUIRED`
