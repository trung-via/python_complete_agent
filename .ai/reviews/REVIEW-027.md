# REVIEW-027 — TASK-027 Open Multi-Agent Continuity OS M3B Real Cross-Chat Brain Failover Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `2` — ADR-013 Delta Fix Review after REVIEW-027 Round 1
- Reviewed branch: `ai/task-027`
- Reviewed branch head: `7e6ab6441b70cb111e8ae9e36a919eb9f3b508b3`
- Tested implementation SHA reported by RESULT: `fb671cb1deb5b08a77856d798e063585dfc2473e`
- Previous reviewed implementation: `1b65819fac5aad49b6be2a4a9bb55659613660e3`
- Previous REVIEW blob: `ec78a248c8b97d6aa84961c329ebce6acb89e2e9`
- Base main: `44436c59eb42dbdbffaee28a738d11694958a4ea`
- Branch relation to current main: ahead `4`, behind `0`; merge-base exact current main.
- `fb671cb... -> 7e6ab64...` changes only `.ai/results/RESULT-027.md`; runner/tests/proof evidence at reviewed head equal the tested implementation.
- Test counts are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: FAIL
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Delta Summary

Round 2 confirms several important improvements:
- hard-coded acceptance diagnosis has been removed from the live CLI path;
- `prepare` and `verify` are distinct commands and `verify` requires explicit source-result, diagnosis and attestation files;
- passing human-only attestation facts are no longer synthesized by default;
- synthetic proof writes can be redirected with `worktree_root` and the current committed diagnosis now has a replacement-result blob pointer that matches its Git contents blob;
- the diagnosis now contains the six required M3B semantic anchors;
- a strict task-local `M3BLiveAttestation` schema now rejects unknown fields, named transcript/secret fields, unsafe acceptance booleans and oversized canonical serialization;
- Continuity Core remains unchanged.

These are meaningful fixes, but the live-proof sequencing and final evidence-integrity boundary are still not fail-closed enough to accept M3B.

## Finding Status

### R1-1 — Real cross-chat provenance / Human checkpoint sequencing
Severity: HIGH
Status: PARTIALLY CLOSED / OPEN

Closed portions:
- live `verify` no longer auto-constructs the source result;
- acceptance diagnosis is no longer hard-coded in the execution path;
- attestation must be supplied explicitly;
- missing source-result / diagnosis / attestation files fail the final verify command.

Remaining blocker:
TASK-027 AIP-6 and the required re-proof sequence require the source result and M3A failover eligibility to be validated **before Brain B is triggered**.

The current CLI does not enforce that boundary:
- `command_prepare()` emits both source and replacement request/capability artifacts immediately and prints both Human Checkpoint 1 and Human Checkpoint 2;
- there is no source-only validation/eligibility command between those checkpoints;
- `command_verify()` requires the Brain-B diagnosis and final attestation to already exist before it calls `validate_brain_failover_eligibility(...)`.

Therefore the runner can only validate source eligibility after the replacement interaction has already occurred. It cannot fail closed by preventing continuation to Brain B when Brain A returned SUCCESS, mismatched identity, invalid state, or unsupported replacement capability.

Required fix:
1. Introduce an enforceable staged boundary, for example:
   - `prepare-source` -> emit source pack only;
   - `validate-source` / `prepare-replacement` -> consume external Brain-A result, run M3A eligibility, and only on PASS emit replacement request/capability pack plus an eligibility receipt/proof;
   - `verify-replacement` -> consume Brain-B diagnosis + explicit attestation and bind final result/evidence.
2. Do not expose/announce the replacement live pack as an actionable continuation before source eligibility passes.
3. The final verification must prove it is using the exact replacement request/proof produced by the successful source-validation stage.
4. Add tests proving source SUCCESS/mismatch prevents replacement-pack emission.

A human may have followed the intended order manually, but the current persisted protocol/evidence does not establish or enforce that required ordering.

### R1-2 — Test isolation and exact final artifact binding
Severity: HIGH
Status: PARTIALLY CLOSED / OPEN

Closed portions:
- `worktree_root` now isolates diagnosis writes in synthetic tests;
- current diagnosis Git blob is `b93511b04ab7cdcee4f3c1cc8c3f9966929dace0`;
- current replacement result points to the same blob;
- the previous false `cbeb9ed...` binding is no longer present.

Remaining blockers:
1. REVIEW-027 Round 1 required a **final non-mutating bundle verifier** that reads the persisted evidence and rejects later diagnosis/result/fingerprint drift. No such final-bundle audit function/command exists. `verify_and_bind_m3b_proof()` verifies bytes while it is writing them; it does not independently reload and validate the already-persisted final bundle.
2. The requested regression proof that synthetic execution leaves the real repository target untouched is not explicit. The success test checks that the temporary diagnosis exists under `tmp_path`, but does not snapshot/assert the repository live-evidence target remains unchanged.

Required fix:
- add a non-mutating `audit-bundle` (or equivalent) that reloads the frozen state, source/replacement requests, capability, source result, failover proof, replacement result, attestation and diagnosis from persisted evidence; reconstructs/validates them; recomputes fingerprints and diagnosis Git blob; and fails on any mismatch without rewriting files;
- run this after live binding and after the final tests, against the exact final evidence being published;
- add a test that deliberately corrupts diagnosis/replacement-result evidence and proves final-bundle audit fails;
- add an explicit regression assertion that a synthetic test run cannot change `REPO_DIR / .ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md`.

### R1-3 — Mandatory Brain-B diagnosis semantic anchors
Severity: HIGH
Status: CLOSED

The committed diagnosis now explicitly demonstrates:
- canonical state fingerprint anchoring;
- source/replacement request semantic equality;
- source SUCCESS duplicate-output blocking;
- no transcript/hidden-reasoning dependency;
- replacement capability gate;
- advisory Brain role and unchanged Human RUN/FIX/MERGE authority.

`validate_diagnosis_semantic_anchors(...)` and negative tests provide bounded mechanical coverage. No further R1-3 remediation is required unless the final live artifact changes.

### R1-4 — Strict bounded live attestation
Severity: MEDIUM
Status: PARTIALLY CLOSED / OPEN

Closed portions:
- task-local immutable dataclass exists;
- exact key set is enforced;
- named forbidden transcript/secret/session fields are rejected;
- required acceptance booleans and `paid_external_api_calls == 0` are enforced;
- canonical serialized size is capped;
- human-only facts are no longer generated with passing defaults by the live verify path.

Remaining blockers:
1. The attested `source_brain_id` / `replacement_brain_id` are not cross-bound to the actual source/replacement `BrainRequest` identities. Any two distinct non-empty IDs can pass `M3BLiveAttestation` even if they name different surfaces from the requests being proved.
2. The Round-1 required oversized-attestation negative test is still absent.
3. Allowed token-usage string fields accept arbitrary non-empty text. Since C11 prohibits secret/raw content in proof evidence, constrain these fields to a small safe grammar such as exact `UNKNOWN` or bounded `REPORTED(...)`, rather than allowing arbitrary text under an otherwise allowed key.

Required fix:
- during verification require attestation source/replacement Brain IDs to exactly equal the corresponding request IDs;
- use the existing canonical actor identities from the requests as the binding authority;
- add negative tests for identity mismatch and oversized attestation;
- bound/validate token-usage value grammar so an allowed field cannot become a secret/raw-text escape hatch.

## New Finding

### R2-1 — Diagnosis byte preservation normalizes more than line endings
Severity: MEDIUM

TASK-027 C7 permits the persisted Brain-B artifact to differ from the returned artifact only by explicitly documented deterministic **newline normalization**.

Current runner uses:

```python
norm_diagnosis_text = diagnosis_content_text.replace("\r\n", "\n").strip() + "\n"
```

`.strip()` removes leading/trailing spaces, tabs and other whitespace in addition to line endings. That is broader than newline normalization and can silently change the Brain-B returned bytes/content representation before persistence.

Required fix:
- normalize only line-ending representation (`CRLF`/`CR` -> `LF`) and, if contractually desired, apply one explicitly documented terminal-newline rule;
- do not use general `.strip()` or semantic/text trimming;
- add a regression test containing intentional leading/trailing spaces/tabs proving they survive byte preservation except for the documented newline transform;
- final bundle audit must recompute the Git blob from the exact post-normalization bytes.

## Evidence Accepted in Round 2

RESULT reports against tested implementation `fb671cb1deb5b08a77856d798e063585dfc2473e`:

```text
Continuity: 86 passed
AIOS Bridge: 172 passed
Full repository: 646 passed
Regressions: 0
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 1
CONTINUITY_CORE_CHANGED: NO
AUTHORITY_WIDENED: NO
PAID_EXTERNAL_API_CALLS: 0
```

The currently persisted artifact binding is internally consistent:

```text
DIAGNOSIS Git blob:
b93511b04ab7cdcee4f3c1cc8c3f9966929dace0

REPLACEMENT-RESULT artifact_ref.blob_sha:
b93511b04ab7cdcee4f3c1cc8c3f9966929dace0
```

The current diagnosis also satisfies the six semantic-anchor content requirements.

However the following top-level claim remains **not accepted** until the staged live protocol and final non-mutating bundle audit are complete:

```text
M3B_REAL_CROSS_BRAIN_PROOF_COMPLETE: YES
```

## Required FIX Scope

Keep remediation task-local:

```text
scripts/aios_m3b_cross_brain_proof.py
tests/aios_bridge/continuity/test_m3b_proof_runner.py
.ai/context/proofs/TASK-027-M3B-*.json
.ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md
.ai/results/RESULT-027.md
```

Do NOT modify Continuity Core, Bridge v0.4, providers or executor authority to satisfy these findings.

## Next Review

After explicit Human FIX authorization:
1. inspect only this Round-2 REVIEW + new RESULT + delta by default;
2. verify R1-1, R1-2, R1-4 and R2-1;
3. if all known findings close, run a fresh ADR-017 Final Independent Audit over the complete final M3B bundle;
4. emit `APPROVED` only if that independent audit passes.

## Decision

`CHANGES_REQUIRED`

M3A remains valid. TASK-027/M3B is not yet accepted as complete.