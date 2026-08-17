# REVIEW-031 — TASK-031 M7 Third Executor Portability Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 4 — Review Protocol v2 / Semantic Closure + Controlled Proof Gate
- Base main: `8a1550b40692798fe0c049aa2ad74d55c54618ee`
- Reviewed branch head: `258e1c220542e9d493480d6884c23d965bf79230`
- Previous semantic-review head: `e5a364e9ea641bf819a29be3b086b29df34903ca`
- Authoritative contracts: ADR-021 + TASK-031 + prior REVIEW-031 rounds.

```text
FULL_SEMANTIC_REVIEW: PASS
R1_1: CLOSED
R1_2: CLOSED
R1_3: CLOSED
R2_1: CLOSED
R2_2: CLOSED
KNOWN_SEMANTIC_FINDINGS: NONE
M7_PROOF_REQUIRED: ANTIGRAVITY_TO_CLAUDE_CODE
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Semantic Closure

### R2-2 HIGH — CLOSED

#### ROOT_CAUSE
The prior parser emitted hard-coded Bridge/Continuity PASS counts when a full-repository pytest transcript did not contain per-test `PASSED` evidence.

#### BROKEN_INVARIANT
Canonical RESULT evidence must never claim a suite PASS/count unless that claim is derived from authoritative execution evidence for the corresponding test scope.

#### REMEDIATION VERIFIED
Current `_parse_task_031_test_evidence()` now:

- contains no hard-coded fallback PASS count for Bridge or Continuity;
- returns `UNVERIFIED` for Bridge/Continuity when a full-repo progress-dot transcript cannot prove per-suite counts;
- derives exact Bridge/Continuity counts from verbose per-test `PASSED` lines when available;
- derives `FULL_REPO_TESTS` only from a command classified as a full repository execution and its pytest summary;
- keeps subset runs isolated so Bridge-only cannot claim Continuity/Full Repo and Continuity-only cannot claim Bridge/Full Repo.

Regression coverage now includes:

- no-test evidence => NOT_RUN;
- failing execution => no PASS evidence;
- Bridge-only subset binding;
- Continuity-only subset binding;
- full-repo progress-dot transcript => sub-suite UNVERIFIED, not fabricated PASS;
- verbose full-repo transcript => dynamically counted sub-suite PASS;
- count-drift scenario => changed synthetic counts automatically change emitted evidence with zero source constant update.

Current RESULT reports:

```text
BRIDGE_TESTS: 56/56 pass
CONTINUITY_TESTS: 152/152 pass
FULL_REPO_TESTS: 755/755 pass
REGRESSIONS: 0
```

The branch also reports a fresh full repository run of `755 passed, 0 failed`.

### R2-1 HIGH — CLOSED
The portability scope validator remains fail-closed on both baseline and working-tree Git diff failures.

### R1-1 / R1-2 / R1-3 — CLOSED
No regression found in the previously closed M7 portability scope gate, formal manifest requirements, or explicit Claude Code RUN activation path.

## Scope Audit

Compared with the previous semantic-review head `e5a364e9...`, the repair remains limited to:

- `bridge.py`
- `tests/test_bridge.py`
- `.ai/results/RESULT-031.md`

No Continuity Core redesign, M5 lease semantic change, M6 failover schema change, automatic routing, hot handoff, or fourth executor was introduced.

---

# PROOF-A CONTRACT — ANTIGRAVITY -> CLAUDE CODE

This is no longer a semantic code-repair request. The next operation is a controlled real-executor portability proof.

## FINDING_ID
`M7-PROOF-A`

## SEVERITY
`PROOF_REQUIRED`

## ROOT_CAUSE
None. Semantic implementation is accepted. TASK-031 still requires real proof that execution can cross the existing stable M6 boundary from Antigravity to Claude Code without weakening lease, authorization, review provenance, or result evidence invariants.

## BROKEN_INVARIANT
No invariant is currently known broken. Completion is blocked solely because the required real portability proof has not yet been produced.

## REQUIRED_BEHAVIOR

1. Start from the currently published Antigravity TASK-031 state and this exact authoritative REVIEW-031 artifact.
2. Activate a FIX for TASK-031 with explicit executor `claude-code` through the existing Bridge handoff/failover path.
3. Bridge must create/activate the Claude Code replacement lease through existing M5/M6 mechanisms; no manual fabrication of authorization, lease, or failover metadata is allowed.
4. Claude Code must execute a real bounded TASK-031 FIX/proof operation against the same `ai/task-031` branch.
5. Publish must validate the stable failover proof before RESULT mutation/push.
6. RESULT-031 must be Bridge-generated and must record, at minimum:

```text
EXECUTOR_ID: claude-code
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: antigravity
FAILOVER_TO_EXECUTOR: claude-code
FAILOVER_SOURCE_PUBLISHED_SHA: <exact prior Antigravity published SHA>
FAILOVER_PROOF_FINGERPRINT: <non-empty canonical fingerprint>
FAILOVER_REVIEW_BLOB_SHA: <exact blob of this REVIEW-031>
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
```

7. Stage A may become PASS only through the validated active failover publication; worker-authored local RESULT text, arbitrary git history, or unanchored commits must not qualify.
8. Existing test/scope gates must remain green.

## FORBIDDEN_IMPLEMENTATIONS

- Do NOT edit Continuity Core to make Claude Code work.
- Do NOT modify M5 lease semantics.
- Do NOT modify M6 failover proof schema/validation.
- Do NOT manually write `M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS` into RESULT as proof authority.
- Do NOT synthesize/fake failover metadata, fingerprints, source SHA, review blob SHA, or executor identity.
- Do NOT bypass `require_active()` / authorization validation / stable failover validation.
- Do NOT change executor to Codex for this proof.
- Do NOT add a fourth executor.
- Do NOT perform automatic executor routing or hot handoff.
- Do NOT start Proof B (`claude-code -> antigravity`) before Proof A has been independently reviewed and accepted.

## REQUIRED_TESTS

Before publishing Proof A, preserve the existing automated coverage and run the TASK-031-required evidence tests. At minimum:

- Bridge tests green;
- Continuity tests green;
- full repository tests green;
- zero observed regressions;
- no paid/live external API calls from automated tests unless TASK contract explicitly permits them.

The real Claude Code executor handoff itself is the proof event and must not be replaced by a mocked unit test.

## ADVERSARIAL_CHECKS

The publication must still fail closed if any of the following occurs:

- authoritative REVIEW blob changes after handoff;
- control-branch review commit/ref no longer matches proof provenance;
- active lease does not exactly match reconstructed expected Claude Code lease;
- failover proof fingerprint mismatches;
- source executor is not Antigravity;
- replacement executor is not Claude Code;
- source published SHA is absent/unresolvable;
- locked Continuity Core changed;
- test gate fails.

## CLOSE_CONDITIONS

`M7-PROOF-A` is CLOSED only if ALL are true:

```text
[ ] real replacement executor == claude-code
[ ] source executor == antigravity
[ ] active authorization action == FIX
[ ] exact Claude Code replacement lease validated
[ ] stable failover proof validated
[ ] source published SHA anchored to the prior real Antigravity publication
[ ] review blob SHA equals this authoritative REVIEW-031 blob
[ ] RESULT generated by Bridge, not worker-authored authority
[ ] EXECUTOR_FAILOVER == YES
[ ] FAILOVER_FROM_EXECUTOR == antigravity
[ ] FAILOVER_TO_EXECUTOR == claude-code
[ ] M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE == PASS
[ ] M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY == PENDING
[ ] locked Continuity Core unchanged
[ ] no fourth executor / auto-routing / hot handoff added
[ ] required tests green
[ ] regressions == 0
```

If any item is false or cannot be proven from canonical artifacts, Proof A remains OPEN.

## ALLOWED_FILES

For the real proof, ordinary executor output may update only artifacts already allowed by TASK-031 and the Bridge publication flow. A code change is NOT expected merely to perform Proof A. If Claude Code discovers that a code change is required to make the proof work, STOP and publish/escalate the failure rather than expanding scope autonomously.

## FORBIDDEN_SCOPE

- `src/aios_bridge/continuity/executor.py`
- `src/aios_bridge/continuity/lease.py`
- `src/aios_bridge/continuity/executor_failover.py`
- `src/aios_bridge/continuity/state.py`
- `src/aios_bridge/runtime_lease.py`
- `src/aios_bridge/continuity/brain.py`
- `src/aios_bridge/continuity/failover.py`
- M5 lease contract redesign
- M6 failover contract redesign
- routing/quota redesign
- fourth executor support

## EXECUTION INSTRUCTION

Proceed with the controlled real failover using the existing worker command/path, explicitly selecting Claude Code:

```text
/aios-worker FIX TASK-031 --executor claude-code
```

This command must consume this REVIEW-031 as the authoritative `CHANGES_REQUIRED` artifact and produce the real Antigravity -> Claude Code stable-boundary proof.

After Claude Code publishes the result, return to Primary Brain with:

```text
Review TASK-031
```

Do not start the return-direction proof until that review explicitly authorizes it.

## Decision

`CHANGES_REQUIRED — SEMANTIC_FINDINGS_NONE — M7_PROOF_REQUIRED: ANTIGRAVITY_TO_CLAUDE_CODE`
