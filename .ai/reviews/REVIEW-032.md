# REVIEW-032 — TASK-032 M8 Real Multi-Agent Continuity Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 3 — Review Protocol v2 / Machine-Checkable Repair Audit
- Baseline main: `08508e48f6ffda70d1891dad461f6fd1b893b24b`
- Prior reviewed head: `1ff3d0dff20bd6408b33ec5c3f15ed87bbeb1345`
- Current reviewed head: `e7191b6d7d28b970cf1088e3a9ae6258b9ecb948`
- Prior REVIEW blob: `afaa9e61521bf7eaa9b1176e48a4672599f964a1`

```text
FULL_SEMANTIC_REVIEW: FAIL
R1-1: OPEN
R1-2: OPEN
R1-3: CLOSED
R1-4: CLOSED
M8_BRAIN_PROOF_REQUIRED: BLOCKED
M8_EXECUTOR_PROOF_REQUIRED: BLOCKED
M8_COMPOSITE_CHAIN: BLOCKED
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

Current repository evidence is green at:

```text
BRIDGE_TESTS: 58/58 pass
CONTINUITY_TESTS: 173/173 pass
FULL_REPO_TESTS: 778/778 pass
REGRESSIONS: 0
```

No locked Continuity Core change is required by this round.

---

# FINDING R1-1 — OPEN / CRITICAL

## ROOT_CAUSE
Round-2 repair correctly added exact REVIEW blob equality and correctly keeps `M8_COMPOSITE_CHAIN` PENDING. However `_evaluate_task_032_proof_progress(...)` still returns:

```text
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF: PASS
M8_COMPOSITE_CHAIN: PENDING
```

when an exact authoritative REVIEW blob merely contains six syntactically valid C7 fields, the source SHA matches, and Brain IDs differ.

The evaluator does not mechanically validate that the C7 proof fingerprint/artifact/state values correspond to an actually verified M8 Brain proof bundle. The current test explicitly encodes arbitrary values (`'1'*64`, `'2'*40`, `'3'*64`) and expects Brain PASS.

## BROKEN_INVARIANT
TASK-032 C7/C10/C13 requires Brain PASS to represent an accepted, mechanically verified Brain proof, not only structurally valid provenance text.

## REQUIRED_BEHAVIOR
Choose one fail-closed authority model and implement it consistently:

### Preferred
Persist a compact mechanically generated Brain-proof acceptance artifact on `ai-control`, containing exact:

```text
S0
state_fingerprint
brain_source_id
brain_replacement_id
brain_failover_proof_fingerprint
diagnosis_artifact_path
diagnosis_artifact_blob_sha
verification_status = PASS
```

The acceptance artifact must be generated only after `verify_brain_proof(...)` succeeds against the real proof bundle. REVIEW-032 must reference that exact immutable acceptance artifact/blob, and Bridge may emit `M8_BRAIN_PROOF: PASS` only when the exact REVIEW provenance matches that verified acceptance artifact.

### Acceptable alternative
If Bridge cannot mechanically resolve/verify Brain proof evidence at publish time, Bridge MUST keep:

```text
M8_BRAIN_PROOF: PENDING
```

and allow Primary Brain Final/Proof Audit to mark the Brain proof accepted outside Bridge. It must not promote Brain PASS from regex/C7 fields alone.

Executor proof may only PASS when the exact stable failover anchors the exact authoritative M8 review blob. Composite remains PENDING until explicit `verify_composite_chain` succeeds.

## FORBIDDEN_IMPLEMENTATIONS
- Do NOT treat six C7 regex matches as Brain-proof verification.
- Do NOT accept arbitrary syntactically valid 40/64-hex fingerprints.
- Do NOT trust worker-authored RESULT text.
- Do NOT scan history for plausible proof data.
- Do NOT change M3/M5/M6/M7 Continuity Core contracts.

## REQUIRED_TESTS
1. Exact REVIEW blob with syntactically valid but nonexistent/fake Brain proof fingerprint => Brain PASS must NOT occur.
2. Exact REVIEW blob with syntactically valid but fake artifact blob => Brain PASS must NOT occur.
3. Exact REVIEW blob with syntactically valid but fake state fingerprint => Brain PASS must NOT occur.
4. REVIEW blob mismatch => all M8 publish proof states stay non-PASS.
5. Valid executor failover with accepted Brain provenance => executor proof may PASS, composite remains PENDING.
6. Composite PASS is established only by successful explicit `verify_composite_chain` audit.

## ADVERSARIAL_TEST
The following must NOT be sufficient:

```text
M8_BRAIN_FAILOVER_PROOF_FINGERPRINT: 1111...(64 hex)
M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA: 2222...(40 hex)
M8_CANONICAL_STATE_FINGERPRINT: 3333...(64 hex)
```

even when the REVIEW blob itself is exact and immutable.

## CLOSE_CONDITIONS
```text
[ ] no code path promotes Brain PASS from C7 syntax alone
[ ] fake-but-well-formed proof/artifact/state values stay non-PASS
[ ] exact REVIEW blob binding remains enforced
[ ] Executor PASS remains dependent on exact stable failover + exact M8 review
[ ] Composite PASS cannot be emitted before explicit composite verification
```

## ALLOWED_FILES
- `bridge.py`
- `tests/test_bridge.py`
- `scripts/aios_m8_multi_agent_continuity_proof.py`
- `tests/aios_bridge/continuity/test_m8_multi_agent_proof.py`

## FORBIDDEN_SCOPE
Locked Continuity Core, router/dispatch, hot handoff, fourth executor, M9/M10/M11.

---

# FINDING R1-2 — OPEN / HIGH

## ROOT_CAUSE
The resolver is much improved: RESULT is now S0-only and TASK/ADR are bound to an exact `control_commit_sha`. However control commit resolution still performs:

```text
origin/ai-control
  -> if missing/fails
ai-control
```

This violates the Round-2 close condition that stale/divergent local `ai-control` must never silently substitute for the authoritative remote control ref.

## BROKEN_INVARIANT
Canonical proof identity must come from an explicit authoritative control commit, not whichever local/ref candidate happens to resolve.

## REQUIRED_BEHAVIOR
Production `prepare-brain` must use one explicit authoritative source:

```text
origin/ai-control
```

or an explicit immutable `--control-commit-sha` supplied by the caller after authoritative resolution.

Recommended contract:

```text
--source-published-sha <S0>
--control-commit-sha <exact 40-hex authoritative control commit>
```

Then resolve:

```text
RESULT-032 -> exact S0
TASK-032   -> exact control_commit_sha
ADR-022    -> exact control_commit_sha
```

If `origin/ai-control` cannot resolve in normal automatic mode, fail closed. Test-only environments may inject an explicit control commit parameter; production code must not silently fall back to local `ai-control`.

## FORBIDDEN_IMPLEMENTATIONS
- No `origin/ai-control -> ai-control` fallback in production resolution.
- No HEAD/latest/nearest/history fallback.
- No working-tree fallback.
- No control-branch fallback for RESULT-032.

## REQUIRED_TESTS
1. authoritative remote control ref absent while local `ai-control` exists => fail closed;
2. explicit immutable control commit parameter works in isolated test repo;
3. stale/divergent local `ai-control` cannot alter generated pack;
4. canonical state records exact control commit SHA for TASK/ADR refs;
5. RESULT remains exact S0-only.

## ADVERSARIAL_TEST
Create:

```text
origin/ai-control = unavailable
local ai-control  = valid-looking stale branch
```

`prepare-brain` must fail, not consume local control artifacts.

## CLOSE_CONDITIONS
```text
[ ] no production fallback from origin/ai-control to local ai-control
[ ] exact control commit is explicit and immutable
[ ] stale local control branch cannot substitute
[ ] TASK/ADR refs use exact control commit SHA
[ ] RESULT ref remains exact S0
```

## ALLOWED_FILES
- `scripts/aios_m8_multi_agent_continuity_proof.py`
- `tests/aios_bridge/continuity/test_m8_multi_agent_proof.py`

---

# FINDING R1-3 — CLOSED

Persisted `BrainFailoverProof` remains exactly bound to the proof derived by `validate_brain_failover_eligibility(...)`. No regression observed.

---

# FINDING R1-4 — CLOSED

Replacement BrainResult now validates task/request/brain/operation/output type/path/blob and rejects task/main/unapproved artifact ref domains. Negative tests cover task-branch and unrelated refs. Close conditions are satisfied.

---

## Positive Evidence

Round-3 repair correctly:
- enforces exact REVIEW blob equality;
- keeps composite proof PENDING until independent verification;
- separates S0 RESULT provenance from control-plane TASK/ADR provenance;
- records exact control commit SHA in the generated state pack;
- validates replacement artifact ref/storage domain;
- keeps full repository green at 778 tests.

Two machine-checkable gaps remain. Live Brain A -> Brain B proof stays BLOCKED until both close.

## Execution Instruction

```text
/aios-worker FIX TASK-032 --executor antigravity
```

Then return with:

```text
Review TASK-032
```

## Decision

`CHANGES_REQUIRED — R1-1 OPEN/CRITICAL, R1-2 OPEN/HIGH, R1-3 CLOSED, R1-4 CLOSED — LIVE BRAIN PROOF BLOCKED`
