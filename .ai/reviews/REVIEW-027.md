# REVIEW-027 — TASK-027 Open Multi-Agent Continuity OS M3B Real Cross-Chat Brain Failover Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `4` — ADR-013 Delta Fix Review after REVIEW-027 Round 3
- Reviewed branch: `ai/task-027`
- Reviewed branch head: `d6aa62d11c77641c137e82ec62ae3484624ea6fe`
- Tested implementation SHA reported by RESULT: `a6e3ad95ee13a36d446e066c465414d842776144`
- Previous tested implementation: `0c487e6016f1e6228d99ce842d52950ff9fa0d0c`
- Previous REVIEW blob: `56fe91a5cc6199eb3657bea75ed8c220861e1463`
- Base/current main: `44436c59eb42dbdbffaee28a738d11694958a4ea`
- Branch relation: ahead `8`, behind `0`; merge-base exact current main.
- `a6e3ad9... -> d6aa62d...` changes only `.ai/results/RESULT-027.md`; runner/tests/proof bundle at reviewed head equal the tested implementation.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: PASS FOR CODE / FAIL FOR ACCEPTANCE EVIDENCE
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Round-4 Delta Findings

The Round-3 implementation findings are now closed at the code/validator layer.

### R1-1 — Stale/replay-safe staged gate + immutable Stage-2 receipt
Status: CODE CLOSED / ACCEPTANCE EVIDENCE OPEN

Closed in implementation:
- `prepare-source` purges all proof-directory Stage-2/Stage-3 JSON artifacts before emitting the new source state/request;
- `validate-source` purges downstream artifacts before validating the current source result, so failed source validation cannot leave a current replacement pack;
- `verify-replacement` requires the persisted Stage-2 `BrainFailoverProof` receipt;
- Stage 3 recomputes eligibility only as a consistency check and requires the persisted receipt fingerprint and replacement-request fingerprint to match before using that receipt;
- tests cover stale downstream artifact purge and staged source gating.

### R3-1 — Exact TASK-027 controlled source mode
Status: CLOSED

`validate_m3b_controlled_source_result(...)` now requires exactly:

```text
status = INCOMPLETE
error_code = M3B-CONTROLLED-HANDOFF
artifact_ref = null
evidence_ref = null
```

The check is applied in live verification and final non-mutating bundle audit. Negative tests cover FAILED/REJECTED/SUCCESS, wrong error code and payload presence.

### R3-2 — Full replacement BrainResult / BrainRequest cross-binding
Status: CLOSED

`audit_persisted_bundle(...)` now reconstructs the expected SUCCESS `BrainResult` from the persisted replacement request + exact diagnosis Git blob and requires canonical equality with the persisted replacement result. This binds task/request/brain/operation/status/output type/artifact path/ref/blob/error/evidence semantics. Negative tests cover request-id, brain-id and artifact-ref drift in addition to diagnosis/blob corruption.

Prior findings remain closed:

```text
R1-2 CLOSED
R1-3 CLOSED
R1-4 CLOSED
R2-1 CLOSED
R3-1 CLOSED
R3-2 CLOSED
```

## New Acceptance-Evidence Finding

### R4-1 — The live M3B proof bundle predates the corrected staged protocol and has not been re-executed through it
Severity: HIGH

M3B is not only a validator implementation task; its acceptance criterion is a **real two-Brain cross-chat proof executed through the fail-closed staged protocol**.

The current code now correctly enforces:

```text
prepare-source
    -> Brain A fresh interaction
    -> validate-source / M3A eligibility
    -> emit replacement pack
    -> Brain B fresh interaction
    -> verify-replacement
    -> audit-bundle
```

However, repository history shows the persisted live evidence was last changed at FIX Round 1 (`fb671cb1deb5b08a77856d798e063585dfc2473e`). From that commit through the current tested implementation `a6e3ad95ee13a36d446e066c465414d842776144`, the only changed files are:

```text
scripts/aios_m3b_cross_brain_proof.py
tests/aios_bridge/continuity/test_m3b_proof_runner.py
.ai/results/RESULT-027.md
```

None of the following live-proof artifacts were regenerated after the corrected staged protocol was introduced:

```text
.ai/context/proofs/TASK-027-M3B-STATE.json
.ai/context/proofs/TASK-027-M3B-SOURCE-REQUEST.json
.ai/context/proofs/TASK-027-M3B-SOURCE-RESULT.json
.ai/context/proofs/TASK-027-M3B-REPLACEMENT-REQUEST.json
.ai/context/proofs/TASK-027-M3B-REPLACEMENT-CAPABILITY.json
.ai/context/proofs/TASK-027-M3B-FAILOVER-PROOF.json
.ai/context/proofs/TASK-027-M3B-REPLACEMENT-RESULT.json
.ai/context/proofs/TASK-027-M3B-LIVE-ATTESTATION.json
.ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md
```

This matters because REVIEW-027 Round 1 explicitly required the two real fresh Brain interactions to be re-run **after** the corrected preparation/checkpoint boundary. Later rounds progressively introduced the actual enforceable gate. Retrospectively passing an older evidence bundle through the new validator proves bundle consistency, but does not prove that the real Brain-A -> eligibility gate -> Brain-B sequence was actually performed under the corrected protocol.

The current bundle remains internally coherent and may be useful as historical evidence, but it is not sufficient to close the M3B acceptance proof.

## Required Re-Proof — Evidence-Only, No Further Architecture Change Expected

Do not redesign the runner unless the fresh proof exposes a defect. Use the currently tested implementation and execute the live protocol exactly:

1. `prepare-source` against a clean/current proof output directory.
2. Human triggers Brain A in a fresh ChatGPT interaction with source pack only.
3. Return only normalized `INCOMPLETE / M3B-CONTROLLED-HANDOFF` result.
4. Run `validate-source`; verify replacement artifacts do not exist before this PASS and are emitted only after PASS.
5. Human triggers distinct Brain B in a fresh interaction with replacement pack only; no Brain-A transcript/history.
6. Return only Brain-B bounded diagnosis artifact and explicit human attestation.
7. Run `verify-replacement` using the exact Stage-2 receipt.
8. Run `audit-bundle` after the final tests, without mutating evidence.
9. Commit the newly generated proof bundle/diagnosis and publish a new RESULT with exact fingerprints/SHAs.
10. Re-run required Continuity / Bridge / full repository suites.

The fresh proof may produce identical deterministic state/request/proof fingerprints and even identical diagnosis text/blob; that is acceptable. The key evidence requirement is that the proof artifacts/attestation are regenerated and committed after executing the corrected staged live protocol, with RESULT documenting that sequence.

## Current Evidence Sanity

The current historical bundle is internally coherent:

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

DIAGNOSIS_GIT_BLOB:
b93511b04ab7cdcee4f3c1cc8c3f9966929dace0
```

The attestation currently records two distinct fresh Brain surfaces, no transcript transfer, no chat UI automation and zero paid API calls. Those facts remain human-attested; Round 4 does not claim they are false. The blocker is that the persisted acceptance evidence predates the now-correct staged enforcement and therefore does not demonstrate execution through that enforcement.

## Test Evidence

RESULT reports against implementation `a6e3ad95ee13a36d446e066c465414d842776144`:

```text
Continuity: 91 passed
AIOS Bridge: 177 passed
Full repository: 651 passed
Regressions: 0
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 3
CONTINUITY_CORE_CHANGED: NO
AUTHORITY_WIDENED: NO
PAID_EXTERNAL_API_CALLS: 0
```

## Final Independent Audit Status

`NOT_RUN`.

All known code findings are closed, but the M3B acceptance evidence itself must be regenerated through the corrected live protocol before ADR-017 Final Independent Audit can accept the milestone.

## Next Review

After explicit Human FIX authorization, this should be an **evidence-only re-proof** by default:
- no Continuity Core changes;
- no Bridge/provider/executor authority changes;
- no runner redesign unless the fresh live proof fails;
- inspect new proof artifacts + diagnosis + RESULT + SHA relation;
- confirm final `audit-bundle` PASS after tests;
- then perform the fresh ADR-017 Final Independent Audit over the newly executed final proof bundle.

## Decision

`CHANGES_REQUIRED`

The TASK-027 implementation is now materially sound, but M3B is not yet accepted until the real cross-Brain proof is re-executed through the corrected staged protocol and independently audited.