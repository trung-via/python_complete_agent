# REVIEW-027 — TASK-027 Open Multi-Agent Continuity OS M3B Real Cross-Chat Brain Failover Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `3` — ADR-013 Delta Fix Review after REVIEW-027 Round 2
- Reviewed branch: `ai/task-027`
- Reviewed branch head: `7a0de4e682e24d86c8c22d5e986f58d7fca1766f`
- Tested implementation SHA reported by RESULT: `0c487e6016f1e6228d99ce842d52950ff9fa0d0c`
- Previous tested implementation: `fb671cb1deb5b08a77856d798e063585dfc2473e`
- Previous REVIEW blob: `be727fb6cd3897c655f7310e4e42d41b546244ab`
- Base/current main: `44436c59eb42dbdbffaee28a738d11694958a4ea`
- Branch relation: ahead `6`, behind `0`; merge-base exact current main.
- `0c487e6... -> 7a0de4e...` changes only `.ai/results/RESULT-027.md`; runner/tests/proof bundle at reviewed head equal the tested implementation.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: FAIL
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Positive Delta / Closed Findings

Round 3 materially strengthens the proof runner:
- staged commands now exist as `prepare-source -> validate-source -> verify-replacement -> audit-bundle`;
- Stage 1 emits only state + source request in a fresh directory case;
- source `SUCCESS` is rejected by M3A before normal Stage-2 replacement emission;
- `audit_persisted_bundle()` is non-mutating and reloads persisted state/requests/results/capability/proof/attestation/diagnosis;
- synthetic tests use `worktree_root=tmp_path` and explicitly snapshot/assert the real repository diagnosis is untouched;
- attestation Brain IDs are cross-bound to the source/replacement requests;
- token-usage metadata is constrained to bounded safe grammar;
- diagnosis normalization now changes line endings only and preserves spaces/tabs;
- the committed final bundle is internally consistent for the fingerprints manually inspected by review: state, source request/result, replacement request, failover proof and replacement result fingerprints match RESULT; diagnosis Git blob `b93511b04ab7cdcee4f3c1cc8c3f9966929dace0` matches replacement-result artifact_ref;
- Continuity Core remains unchanged.

Finding status from prior rounds:

```text
R1-2  CLOSED for test isolation + existence of non-mutating bundle audit
R1-3  CLOSED
R1-4  CLOSED
R2-1  CLOSED
R1-1  OPEN — staged proof provenance still not fully fail-closed
```

## Remaining / New Findings

### R1-1 — Staged source gate is still replay/stale-artifact permissive and Stage-2 proof is not bound through Stage 3
Severity: HIGH
Status: OPEN

The new command split is correct in the fresh-directory happy path, but TASK-027 requires the replacement interaction to become actionable only after the exact source-validation gate passes.

Two remaining defects prevent that guarantee.

**A. Stale downstream artifacts survive `prepare-source` and failed source validation.**

`command_prepare_source(output_dir)` writes only:
- `TASK-027-M3B-STATE.json`
- `TASK-027-M3B-SOURCE-REQUEST.json`

but it neither requires a fresh proof directory nor rejects/removes pre-existing:
- replacement request;
- replacement capability;
- failover proof;
- source result;
- replacement result;
- live attestation.

This matters in the actual TASK-027 workflow because the default `.ai/context/proofs/` directory already contains evidence from earlier rounds. Running the corrected `prepare-source` in that directory can therefore leave a stale Brain-B pack visible before the current Brain-A result has passed `validate-source`. If `validate-source` later rejects source `SUCCESS` or another invalid result, those stale replacement artifacts still remain.

The existing test proves a fresh `tmp_path` does not create replacement artifacts, but does not cover a pre-populated/replayed proof directory.

**B. Stage 3 does not cryptographically bind to the exact Stage-2 eligibility proof.**

`command_validate_source()` creates and persists the Stage-2 `BrainFailoverProof`. However `command_verify_replacement()` does not load and require that exact persisted proof as its gate receipt. It loads state/source/replacement/capability and calls `verify_and_bind_m3b_proof()`, which recomputes a failover proof and writes `TASK-027-M3B-FAILOVER-PROOF.json` again.

Therefore a permitted identity mutation/replacement-pack substitution between stages can be recomputed and overwrite the Stage-2 receipt instead of failing because the exact already-approved Stage-2 request/proof changed. Round 2 explicitly required final verification to prove it uses the exact replacement request/proof produced by the successful source-validation stage.

Required fix:
1. Use a fresh per-proof-run directory/run identity, or make `prepare-source` fail closed if any Stage-2/Stage-3 artifact already exists. Do not silently reuse a contaminated evidence directory.
2. On failed `validate-source`, guarantee no current-run replacement pack/proof is emitted and stale downstream artifacts cannot be mistaken for current-run output.
3. Treat the Stage-2 proof/receipt as immutable input to Stage 3. `verify-replacement` must load it, validate its exact state/source/replacement request fingerprints, and fail on mismatch rather than silently recomputing/overwriting it.
4. Add tests with a deliberately pre-populated stale replacement pack and with a tampered Stage-2 replacement request/proof.

### R3-1 — TASK-027 controlled source boundary is not enforced beyond generic M3A non-success eligibility
Severity: MEDIUM

ADR-016 generic failover correctly allows a missing result or `REJECTED`, `FAILED`, or `INCOMPLETE` source result. TASK-027 intentionally narrows its proof protocol further: C6 requires exactly:

```text
status: INCOMPLETE
error_code: M3B-CONTROLLED-HANDOFF
artifact_ref: null
evidence_ref: null
```

Current `command_validate_source()` delegates to `validate_brain_failover_eligibility()` but does not enforce the TASK-027-specific `INCOMPLETE / M3B-CONTROLLED-HANDOFF` contract. A syntactically valid `FAILED`/`REJECTED` source result, or an `INCOMPLETE` result with another error code, may pass the generic M3A gate and cause a replacement pack to be emitted.

The currently persisted source result is correct, but the task-local acceptance runner is not fail-closed to the proof mode it claims (`CONTROLLED_INCOMPLETE_SOURCE`).

Required fix:
- before emitting Stage-2 replacement artifacts, require source status exactly `INCOMPLETE`, error code exactly `M3B-CONTROLLED-HANDOFF`, and no payload pointers;
- repeat this task-specific check in `audit-bundle`;
- add negative tests for `FAILED`, `REJECTED`, wrong/missing error code and any forbidden payload.

### R3-2 — Final non-mutating bundle audit does not fully cross-bind replacement BrainResult to replacement BrainRequest
Severity: HIGH

TASK-027 C10 requires mechanical verification that the final replacement `BrainResult` matches the replacement request on:
- task_id;
- request_id;
- brain_id;
- operation;
- expected output type;
- exact output target path;
- persisted artifact ref/blob;
- output bound.

`audit_persisted_bundle()` currently verifies diagnosis size/semantic anchors/blob, artifact path, recomputed M3A proof and attestation/request Brain IDs. It does **not** compare the persisted replacement result's task/request/brain/operation/output-type/status identities to the replacement request.

Because `BrainResult.from_json()` validates only the result's internal schema, a later valid-looking drift such as a different `request_id` or `brain_id` can survive parsing and is not caught by the final bundle audit as long as the artifact path/blob still match.

Required fix:
- final bundle audit must require `rep_res.status == SUCCESS` and exact equality of `task_id`, `request_id`, `brain_id`, `operation` and `output_type` against `rep_req` / its output contract;
- require exact artifact path/ref/blob and absence of incompatible payload/error fields;
- preferably reconstruct the expected replacement result (or its canonical fingerprint) from the replacement request + final diagnosis blob and compare it to the persisted result;
- add negative tests for drift in request_id, brain_id, operation/status/output type in addition to blob corruption.

## Final Independent Audit Status

`NOT_RUN`.

ADR-017 Final Independent Audit is intentionally withheld because R1-1 remains open and R3-1/R3-2 are new blocking proof-integrity findings. The review did independently recompute the canonical SHA-256 fingerprints from the final persisted JSON for sanity:

```text
STATE_FINGERPRINT:
3ad86f80e693d4cc8fbab8dee502a0de1c60b581216c7ea2bbfa233b88cdb9db

SOURCE_REQUEST_FINGERPRINT:
61b3722900d9ee0fded5e7b999b08f6871681fa8d33a53d0c668775381db0cca

SOURCE_RESULT_FINGERPRINT:
073a5806e5c0a16366a80b38f01f21afb94a919130d30b86af6e2d225d21b5cf

REPLACEMENT_REQUEST_FINGERPRINT:
97dfd75384bb9bad13c563974adfdd2ffbfbd4cf3dcf6559837185fcdc95b4d4

REPLACEMENT_RESULT_FINGERPRINT:
bae9f7ba490e655a12ac8653e2f900de92bf72f372b7a888ead1e9962b4ca072

FAILOVER_PROOF_FINGERPRINT:
6eae90cdd36e650ccd96c862387cd211a2ff3437b01d1d2a7df168c5b1c191aa
```

These values agree with RESULT-027 and the diagnosis blob currently matches `b93511b04ab7cdcee4f3c1cc8c3f9966929dace0`. This confirms the current bundle's visible values are coherent; it does not waive the fail-closed protocol/validator defects above.

## Test Evidence

RESULT reports against implementation `0c487e6016f1e6228d99ce842d52950ff9fa0d0c`:

```text
Continuity: 90 passed
AIOS Bridge: 176 passed
Full repository: 650 passed
Regressions: 0
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 2
CONTINUITY_CORE_CHANGED: NO
AUTHORITY_WIDENED: NO
PAID_EXTERNAL_API_CALLS: 0
```

These are useful regression evidence, but do not close the proof-integrity findings above.

## Required FIX Scope

Keep remediation task-local:

```text
scripts/aios_m3b_cross_brain_proof.py
tests/aios_bridge/continuity/test_m3b_proof_runner.py
.ai/context/proofs/TASK-027-M3B-*.json   # only if re-proof produces changed evidence
.ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md # only if live artifact changes
.ai/results/RESULT-027.md
```

Do NOT modify Continuity Core, Bridge v0.4, providers, executor authority, or M3A semantics to satisfy these findings.

## Next Review

After explicit Human FIX authorization:
1. inspect this Round-3 REVIEW + new RESULT + delta;
2. verify stale/replay-safe staged gate and immutable Stage-2 receipt binding;
3. verify exact TASK-027 source-mode enforcement;
4. verify complete replacement-result/request cross-binding in final bundle audit;
5. if all known findings close, perform a fresh ADR-017 Final Independent Audit over the final tested M3B bundle;
6. emit `APPROVED` only if that audit passes.

## Decision

`CHANGES_REQUIRED`

M3A remains valid. TASK-027/M3B is not yet accepted as complete.