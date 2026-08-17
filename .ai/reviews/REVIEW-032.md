# REVIEW-032 — TASK-032 M8 Real Multi-Agent Continuity Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 2 — Review Protocol v2 / Targeted Repair Audit
- Baseline main: `08508e48f6ffda70d1891dad461f6fd1b893b24b`
- Prior reviewed head: `42dfd52dc9a0c54a9673c9ebcb6c23c7bf00dc4d`
- Current reviewed head: `1ff3d0dff20bd6408b33ec5c3f15ed87bbeb1345`
- Prior REVIEW blob: `0aa75259fa6d92ee936f41d80abf50feffc62842`

```text
FULL_SEMANTIC_REVIEW: FAIL
R1-1: OPEN
R1-2: PARTIALLY_CLOSED
R1-3: CLOSED
R1-4: PARTIALLY_CLOSED
M8_BRAIN_PROOF_REQUIRED: BLOCKED
M8_EXECUTOR_PROOF_REQUIRED: BLOCKED
M8_COMPOSITE_CHAIN: BLOCKED
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

Current full repository execution is green at `776/776 pass`, but three close-condition gaps remain.

---

# FINDING R1-1 — STILL OPEN

## SEVERITY
`CRITICAL`

## VERIFIED IMPROVEMENT
The unsafe direct branch:

```python
if failover_info:
    brain_proof_val = "PASS"
    executor_proof_val = "PASS"
    composite_chain_val = "PASS"
```

has been removed and replaced by `_evaluate_task_032_proof_progress(...)`.

Generic failover without C7 provenance now remains PENDING.

## REMAINING ROOT_CAUSE
The new evaluator still returns:

```text
PASS / PASS / PASS
```

when REVIEW text merely contains six syntactically valid C7 fields whose source SHA matches the failover source and Brain IDs differ.

It does NOT:
- verify that `review_blob_sha` from validated M6/M7 `failover_info` equals the exact blob of the REVIEW content it parsed;
- mechanically verify the referenced Brain proof/artifact/state against the proof bundle;
- execute `verify_composite_chain(...)` before asserting `M8_COMPOSITE_CHAIN: PASS`.

The implementation docstring claims review-blob equality is checked, but the current code does not perform that comparison.

## BROKEN INVARIANT
M8 C7/C9/C10 requires:

```text
validated Brain proof
 -> exact Brain artifact
 -> exact REVIEW blob
 -> validated Executor failover
 -> explicit composite verification
```

C7-shaped text alone is not proof authority.

## REQUIRED BEHAVIOR
1. `M8_BRAIN_PROOF: PASS` must require exact mechanically verified Brain proof evidence, not C7 field presence alone.
2. `M8_EXECUTOR_PROOF: PASS` must require valid failover whose `review_blob_sha` exactly equals the authoritative REVIEW blob containing the already-verified Brain provenance.
3. `M8_COMPOSITE_CHAIN: PASS` must never be emitted by `_evaluate_task_032_proof_progress()` merely from metadata presence. It must remain `PENDING` until explicit `verify_composite_chain(...)` succeeds against exact S0 + proof bundle + REVIEW + S1 RESULT.
4. If Bridge cannot access the proof bundle at publish time, Bridge may emit Brain/Executor state conservatively and MUST keep composite `PENDING`; Primary Brain can close composite after independent verification.

## FORBIDDEN IMPLEMENTATIONS
- no `PASS/PASS/PASS` based on regex presence;
- no trust in REVIEW provenance fields without exact proof verification;
- no docstring-only review-blob check;
- no composite PASS before explicit composite verifier success;
- no working-tree proof authority;
- no M5/M6/M7 redesign.

## REQUIRED TESTS
- valid-looking C7 block + wrong `failover_info.review_blob_sha` => no executor/composite PASS;
- valid-looking C7 block + fake proof fingerprint => no Brain/composite PASS;
- valid-looking C7 block + fake artifact blob => no Brain/composite PASS;
- correct C7 + valid failover but composite verifier not run => `M8_COMPOSITE_CHAIN: PENDING`;
- only explicit successful composite verification may establish final composite PASS.

## ADVERSARIAL_TESTS
A forged REVIEW containing syntactically correct 40/64-hex values must not become authoritative solely because regexes match.

## CLOSE_CONDITIONS
```text
[ ] exact review blob equality is mechanically enforced
[ ] C7 field presence alone cannot establish Brain PASS
[ ] executor PASS requires exact M8 review binding
[ ] composite PASS is impossible before explicit verify_composite_chain success
[ ] adversarial forged-C7 tests pass
```

## ALLOWED_FILES
- `bridge.py`
- `tests/test_bridge.py`
- M8 proof-local runner/tests if needed for a small exact verification helper

## FORBIDDEN_SCOPE
Continuity Core, M5/M6/M7 semantics, routing, hot handoff, fourth executor.

---

# FINDING R1-2 — PARTIALLY CLOSED

## SEVERITY
`HIGH`

## VERIFIED IMPROVEMENT
- authoritative ADR path is now correct;
- filesystem fallback was removed;
- all-zero SHA fallback was removed;
- invalid/nonexistent S0 is rejected;
- source RESULT resolution still requires a Git object.

## REMAINING ROOT_CAUSE
`_get_exact_git_blob(...)` is still a multi-ref fallback resolver. For TASK/ADR it may silently move from the supplied S0 to `origin/ai-control` and then local `ai-control`.

This is acceptable only if TASK/ADR are intentionally control-plane artifacts and the exact authoritative control provenance is explicitly fixed. It is not acceptable as a generic fallback policy because a stale local `ai-control` ref or unexpected control update can silently change the proof input.

The current function also discards `task_ref_name` / `adr_ref_name` and serializes mutable `ref="ai-control"`, so the pack does not state which exact control commit supplied those blobs.

## REQUIRED BEHAVIOR
Use explicit provenance domains rather than fallback search:

```text
RESULT-032 -> exact S0 only
TASK-032 -> exact authoritative control commit/blob
ADR-022  -> exact authoritative control commit/blob
```

The control commit/ref used for TASK/ADR must be intentionally resolved and recorded; do not opportunistically try several refs until one works.

Prefer resolving/fetching the authoritative control head once and binding:

```text
control_commit_sha
TASK blob at that control commit
ADR blob at that control commit
```

The exact blob SHA remains the identity, but provenance must not depend on a stale local branch fallback.

## FORBIDDEN IMPLEMENTATIONS
- no candidate-list fallback from authoritative remote control ref to arbitrary local control branch;
- no latest/nearest/history scan;
- no working-tree fallback;
- no source RESULT from control branch.

## REQUIRED TESTS
- RESULT missing at S0 fails even if a RESULT exists elsewhere;
- stale/divergent local `ai-control` cannot substitute for authoritative control ref;
- TASK/ADR pack records exact control provenance used;
- wrong control blob/ref fails closed.

## CLOSE_CONDITIONS
```text
[ ] RESULT identity is S0-only
[ ] TASK/ADR provenance is explicit, not candidate-fallback based
[ ] stale local ai-control cannot silently substitute
[ ] emitted state/context identifies exact authoritative blobs and control provenance
```

## ALLOWED_FILES
- `scripts/aios_m8_multi_agent_continuity_proof.py`
- `tests/aios_bridge/continuity/test_m8_multi_agent_proof.py`

---

# FINDING R1-3 — CLOSED

The persisted `BrainFailoverProof` is now compared canonically with the exact proof returned by `validate_brain_failover_eligibility(...)`. Semantic drift in state/request/actor/task/operation fields is rejected, and the reported fingerprint comes from the derived validated proof.

Close conditions satisfied.

---

# FINDING R1-4 — PARTIALLY CLOSED

## SEVERITY
`MEDIUM`

## VERIFIED IMPROVEMENT
Replacement result is now bound to:
- task_id;
- request_id;
- brain_id;
- operation;
- output_type;
- exact artifact path;
- exact diagnosis blob SHA.

Negative tests were added for task/operation/output/path drift.

## REMAINING ROOT_CAUSE
Round-1 required validation of artifact `ref` / storage domain according to the proof storage contract. Current verifier does not validate `repl_res.artifact_ref.ref` at all.

A result can therefore point the correct path/blob at an arbitrary ref/domain and still pass.

## REQUIRED BEHAVIOR
For the accepted M8 Brain artifact, require the exact approved control storage domain. At minimum:

```text
artifact_ref.path == expected target
artifact_ref.blob_sha == exact diagnosis blob
artifact_ref.ref == authoritative approved control ref/commit domain
```

If the final design uses immutable control commit SHA instead of branch name, validate that exact value consistently.

## REQUIRED TESTS
- correct path/blob but `artifact_ref.ref` points to task branch => reject;
- correct path/blob but unrelated ref => reject;
- exact approved control provenance => pass.

## CLOSE_CONDITIONS
```text
[ ] artifact ref/storage domain is explicitly validated
[ ] matching blob on wrong ref cannot pass
```

## ALLOWED_FILES
- M8 proof runner/tests only.

---

## Positive Evidence

Current repair is substantial and directionally correct. R1-3 is fully closed; most of R1-2/R1-4 is fixed; full repository is green at 776 tests; no locked Continuity Core change is required.

Do not begin live Brain A -> Brain B proof yet. R1-1 remains CRITICAL and must close first.

## Execution Instruction

```text
/aios-worker FIX TASK-032 --executor antigravity
```

Then return with:

```text
Review TASK-032
```

## Decision

`CHANGES_REQUIRED — R1-1 OPEN/CRITICAL, R1-2 PARTIAL/HIGH, R1-3 CLOSED, R1-4 PARTIAL/MEDIUM — LIVE BRAIN PROOF BLOCKED`
