# REVIEW-031 — TASK-031 M7 Third Executor Portability Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 3 — Semantic Re-review after Antigravity FIX
- Base main: `8a1550b40692798fe0c049aa2ad74d55c54618ee`
- Reviewed branch head: `e5a364e9ea641bf819a29be3b086b29df34903ca`
- Prior review blob: `ad692efc2f054c37c44f82dc3747ed3d3e5e92ed`
- Authoritative contracts: ADR-021 + TASK-031 + prior REVIEW-031 rounds.

```text
FULL_SEMANTIC_REVIEW: FAIL
R2_1: CLOSED
R2_2: OPEN
M7_PROOF_REQUIRED: BLOCKED_UNTIL_SEMANTIC_FIXES
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Closed Finding

### R2-1 HIGH — CLOSED
`_validate_task_031_portability_scope()` now fails closed when either baseline diff or working-tree diff returns a non-zero status. Error context is surfaced, and deterministic regression tests cover both an invalid/unresolvable baseline and a simulated working-tree Git failure.

This satisfies the Round-2 fail-closed requirement without altering Continuity Core or M5/M6 semantics.

## Remaining Finding

### R2-2 HIGH — Test evidence still contains hard-coded suite PASS fallbacks

The new `_parse_task_031_test_evidence()` is directionally better: subset Bridge tests no longer fabricate Continuity or Full Repo PASS, subset Continuity tests no longer fabricate Bridge or Full Repo PASS, and Full Repo is only populated when the command is classified as a full repository run.

However, for a full repository execution the parser currently does:

```python
v_matches = len(re.findall(r"tests[/\\]test_bridge\.py[^\n]*PASSED", test_output))
if v_matches > 0:
    bridge_str = f"{v_matches}/{v_matches} pass"
else:
    bridge_str = "80/80 pass"
```

and equivalently for Continuity:

```python
v_matches = len(re.findall(r"tests[/\\]aios_bridge[/\\]continuity[^\n]*PASSED", test_output))
if v_matches > 0:
    continuity_str = f"{v_matches}/{v_matches} pass"
else:
    continuity_str = "152/152 pass"
```

The actual full-repository pytest transcript at this branch head uses normal progress-dot output rather than per-test `PASSED` lines. Therefore those regexes do not establish the Bridge or Continuity counts; the manifest's `80/80` and `152/152` values are still produced by hard-coded fallbacks.

That leaves the central Round-2 requirement unresolved: a PASS count must be derived from authoritative execution evidence for that specific suite, not from a known current count baked into Bridge.

### Why this still matters

If Bridge or Continuity gains/removes tests while the full repository remains green, these fallback constants can become stale while the RESULT continues to claim a successful exact count. The current RESULT is internally plausible and the full repository transcript reports `755 passed`, but the two sub-suite counts are not actually proven by the parser's full-repo evidence path.

## Required Remediation

1. Remove hard-coded PASS fallbacks for Bridge and Continuity from `_parse_task_031_test_evidence()`.
2. Derive sub-suite counts from evidence that really identifies the tests executed. Acceptable narrow approaches include:
   - run the required Bridge and Continuity suites separately and bind their own pytest summaries; or
   - make the full-repo command emit machine/verbose evidence sufficient to count those suites deterministically.
3. If authoritative sub-suite evidence is absent, emit `NOT_RUN`/`UNVERIFIED` rather than a guessed PASS count, or fail publication if TASK-031 requires those fields to be proven before review.
4. Add a regression test where a normal progress-dot full-repo transcript has no `PASSED` tokens and prove the parser does not fall back to hard-coded `80/80` or `152/152`.
5. Add a count-drift test proving changing the number of Bridge/Continuity tests cannot leave an old hard-coded PASS value in the manifest.
6. Keep `FULL_REPO_TESTS` bound to the actual full-repository pytest summary as it is now.

## Positive Evidence Reviewed

Branch head `e5a364e9ea641bf819a29be3b086b29df34903ca` reports:

```text
BRIDGE_TESTS: 80/80 pass
CONTINUITY_TESTS: 152/152 pass
FULL_REPO_TESTS: 755/755 pass
REGRESSIONS: 0
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
```

The full-repository execution itself is green: `755 passed, 0 failed`. This is accepted as evidence that the current commit has no observed test regression, but it does not close the sub-suite evidence-binding flaw above.

## Controlled Proof Gate

Do NOT start Claude Code Proof A yet.

Both real-proof fields remain:

```text
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
```

Once R2-2 is fully closed, and no new semantic finding appears, the next review may open the controlled Antigravity -> Claude Code real-proof step.

## Next Step

Run another narrow Antigravity FIX:

```text
/aios-worker FIX TASK-031 --executor antigravity
```

Allowed scope remains `bridge.py`, `tests/test_bridge.py`, and `RESULT-031.md`. Do not modify Continuity Core, M5 lease semantics, M6 failover proof schema, router/quota behavior, or add a fourth executor.

After publish, return with `Review TASK-031`.

## Decision

`CHANGES_REQUIRED`
