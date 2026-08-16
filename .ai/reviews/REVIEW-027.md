# REVIEW-027 — TASK-027 Open Multi-Agent Continuity OS M3B Real Cross-Chat Brain Failover Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1` — ADR-017 Full Semantic Review
- Reviewed branch: `ai/task-027`
- Reviewed branch head: `b6baaaf3093e3317095c0aa97899685b4bb5bd2f`
- Tested implementation SHA reported by RESULT: `1b65819fac5aad49b6be2a4a9bb55659613660e3`
- Base main: `44436c59eb42dbdbffaee28a738d11694958a4ea`
- Branch relation: ahead `2`, behind `0`; merge-base exact current main.
- `1b65819... -> b6baaaf...` changes only `.ai/results/RESULT-027.md`; production runner/tests/proof evidence at reviewed head equal the tested implementation.
- Review basis: TASK-027 C1-C15, ADR-016 real-proof requirements, M3A failover contract, proof-local state/requests/results/capability/proof/attestation, diagnosis artifact, proof runner, tests, RESULT and SHA relation.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: FAIL
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: NOT_RUN
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Positive Findings

The deterministic M3A-facing portion is structurally sound:
- proof-local `ContinuityState` uses TASK-027 and the expected ADR-010/011/016/017 blobs with baseline main `44436c59...`;
- source/replacement BrainRequests preserve task, operation, objective, ordered context refs/blob identities and output contract, changing only `brain_id` / `request_id`;
- replacement capability declares DIAGNOSIS support;
- source result shape is a valid non-success `INCOMPLETE / M3B-CONTROLLED-HANDOFF` BrainResult;
- M3A validation is reused rather than modified;
- Continuity Core production files remain unchanged;
- branch/base relation is clean.

However, M3B is specifically a **real two-Brain proof**, and the current operational/evidence layer does not establish that contract fail-closed.

## Findings

### R1-1 — Real cross-chat provenance can be synthesized entirely by the proof runner
Severity: HIGH

TASK-027 C4-C7/C12 and ADR-016 require two distinct real human-triggered Brain surfaces, fresh-session isolation, Brain A controlled non-success, and Brain B real replacement output. Human attestation is allowed only for facts that cannot be mechanically observed; it must not be invented by deterministic tooling.

Current `scripts/aios_m3b_cross_brain_proof.py` violates this proof boundary:
- `main()` directly calls `build_m3b_controlled_source_result(...)` instead of requiring the normalized result returned from a human-triggered Brain A interaction;
- `main()` embeds diagnosis content in source code under the comment that it was produced by the real replacement Brain, rather than requiring externally supplied Brain-B final artifact bytes;
- `verify_and_bind_m3b_proof()` creates a default attestation with `distinct_real_brain_surfaces=True`, `fresh_source_session=True`, `fresh_replacement_session=True`, `transcript_transferred=False`, `chat_ui_automation=False`, and `paid_external_api_calls=0` without requiring human-provided evidence;
- executing the script alone can therefore emit a bundle that claims a real cross-chat proof without any mandatory Human checkpoint or real Brain input.

This makes `DISTINCT_REAL_BRAIN_SURFACES_ATTESTED: YES` and `M3B_REAL_CROSS_BRAIN_PROOF_COMPLETE: YES` non-probative in the current bundle. The review does **not** assert that no human interactions occurred; it finds that the persisted proof cannot distinguish a real interaction from a fully synthetic runner execution.

Required fix:
1. Separate deterministic `prepare` and live-input `verify` boundaries (or equivalent fail-closed phases).
2. `prepare` may create state, source/replacement requests, capability and bounded packs, then MUST stop before producing source result/live attestation/diagnosis/replacement result.
3. Brain A normalized source result must be supplied as explicit external/human-returned bounded input and validated; do not auto-create the acceptance source result in the live path.
4. Brain B final diagnosis bytes must be supplied as explicit external/human-returned bounded input; remove hard-coded acceptance diagnosis from `main()`.
5. Human-only facts must be supplied explicitly in an attestation input; no acceptance fact may default to the passing value.
6. The runner must fail closed when live inputs/attestation are absent.
7. Re-run the two real fresh Brain interactions after the corrected preparation checkpoint. Do not reuse a synthetic output as live evidence.

### R1-2 — Replacement artifact Git-blob binding is false in the committed proof; synthetic tests can overwrite live evidence
Severity: HIGH

TASK-027 C7/C10 and Acceptance #7 require the replacement SUCCESS BrainResult to be mechanically bound to the **exact persisted diagnosis Git blob**.

Current committed evidence is internally inconsistent:

```text
REPLACEMENT-RESULT artifact_ref.blob_sha:
cbeb9ed7fb155dc3365c491c784521629202e0c5

actual Git blob of .ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md
at tested implementation 1b65819...:
ae61f71dfe00f75792618c0b32d2de07621e0c70
```

Therefore the replacement result does not point to the artifact actually committed in the reviewed implementation.

The proof-runner/test design exposes a direct corruption path: `verify_and_bind_m3b_proof(..., output_dir=tmp_path)` writes proof JSON under `tmp_path` but still writes the diagnosis to `REPO_DIR / target_path`. The synthetic success test calls this function with its fixture diagnosis, so running tests can mutate/overwrite the repository proof artifact while leaving the previously computed replacement-result blob pointer stale.

Required fix:
1. Tests MUST NOT write any proof/live artifact into the real repository worktree.
2. Inject/use a proof/worktree root so diagnosis and all evidence writes are isolated under the test temporary directory.
3. Add a regression test proving the real repository target is untouched by synthetic tests.
4. Add a final-bundle verifier that reads the persisted diagnosis bytes and rejects any replacement-result `artifact_ref.blob_sha` mismatch.
5. After tests are fixed, re-run the live proof/binding and commit a bundle where Git contents blob, replacement result, RESULT manifest and byte-count evidence all agree.

### R1-3 — Persisted replacement diagnosis does not satisfy the mandatory Brain-B semantic anchors
Severity: HIGH

Controlled Live Proof Phase 3 says Brain B's diagnosis SHALL demonstrate at least:
- exact same canonical state fingerprint requirement;
- request semantics identical except Brain/request IDs;
- source SUCCESS blocks duplicate failover;
- no transcript/hidden reasoning is required;
- capability gate must pass;
- Brain is advisory and Human RUN/FIX/MERGE authority remains unchanged.

The diagnosis actually committed at `1b65819...` contains only generic statements:

```text
CAUSE: Cross-brain failover required.
EVIDENCE: ADR-010 and ADR-016 invariants.
FIX: Apply deterministic failover rules.
TESTS: Run pytest suites.
RISKS: None.
```

It does not demonstrate the required semantic anchors and therefore cannot establish C7 / Acceptance #6 even if its provenance were otherwise valid.

Required fix:
- obtain a real Brain-B bounded diagnosis in a fresh session from the corrected replacement pack;
- require the six mandatory semantic anchors in the acceptance validator/test;
- persist that Brain-B final artifact byte-for-byte except only explicitly documented deterministic newline normalization;
- no Antigravity/ChatGPT/Human semantic editing after Brain B output.

### R1-4 — Live-attestation evidence is not strict or bounded and can override safety/provenance facts
Severity: MEDIUM

TASK-027 C11 requires every JSON proof artifact to be bounded/deterministic and prohibits transcript/reasoning/secrets/session material. C12 limits attestation to human-observed facts.

Current runner builds a plain dict and then does:

```python
if attestation_metadata:
    default_attestation.update(attestation_metadata)
```

There is no strict allowed-key schema, no required-field/type validation, no 16 KiB (or other explicit bounded) write check, no rejection of forbidden keys such as raw transcript/prompt/response/cookie/token/session material, and no fail-closed enforcement that acceptance values are exactly the required values. Arbitrary metadata can also override the generated safety booleans.

Required fix:
- introduce a small task-local strict attestation validator/dataclass (no Continuity Core change);
- exact allowed keys + required types/values;
- reject unknown/forbidden fields;
- enforce bounded canonical serialization before persistence;
- require `distinct_real_brain_surfaces=true`, both fresh-session facts=true, `transcript_transferred=false`, `chat_ui_automation=false`, `paid_external_api_calls=0` for acceptance;
- require explicit human input for human-only facts rather than passing defaults;
- add negative tests for unknown fields, unsafe boolean values, oversized data and forbidden transcript/secret/session-like fields.

## Required FIX Scope

Expected changes remain task-local:

```text
scripts/aios_m3b_cross_brain_proof.py
tests/aios_bridge/continuity/test_m3b_proof_runner.py
.ai/context/proofs/TASK-027-M3B-*.json
.ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md
.ai/results/RESULT-027.md
```

Do NOT modify:

```text
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/failover.py
src/aios_bridge/continuity/usage.py
bridge.py
providers/executor authority
```

If a core defect is discovered while fixing these proof-layer defects, stop and escalate to a separate remediation TASK as C13 requires.

## Required Re-Proof Sequence

1. Correct runner/test isolation and strict attestation handling.
2. Run deterministic synthetic tests; confirm they cannot mutate repository live-evidence paths.
3. Run `prepare` and capture exact state/request fingerprints.
4. Human triggers Brain A fresh session with source pack only; return only normalized controlled `INCOMPLETE` result.
5. Deterministically validate source result + M3A eligibility **before** Brain B interaction.
6. Human triggers distinct Brain B fresh session with replacement pack only; no Brain-A transcript/result as reasoning context.
7. Return only Brain-B final bounded diagnosis artifact + explicit human attestation.
8. Verify/persist byte-preserved artifact, compute exact Git blob, construct replacement result, proof and evidence.
9. Run final non-mutating verification against committed/staged evidence.
10. Re-run required suites and publish new RESULT with exact SHA/evidence relation.

## Required Tests

At minimum retain/run:

```text
pytest tests/aios_bridge/continuity/test_m3b_proof_runner.py -q
pytest tests/aios_bridge/continuity/test_failover.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

Add focused regression evidence for the findings above, especially test isolation, final artifact blob mismatch, strict attestation, absent live inputs, and mandatory diagnosis semantic anchors.

## Evidence Status

RESULT reports against tested implementation `1b65819fac5aad49b6be2a4a9bb55659613660e3`:

```text
Continuity: 84 passed
AIOS Bridge: 170 passed
Full repository: 644 passed
Regressions: 0
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 0
```

Those green suites are useful regression evidence but do not override the proof-integrity failures above. In particular, the current tests themselves expose the repository-write side effect described in R1-2.

The following RESULT claims are **not accepted** in Round 1:

```text
M3B_REAL_CROSS_BRAIN_PROOF_COMPLETE: YES
DISTINCT_REAL_BRAIN_SURFACES_ATTESTED: YES
FRESH_SOURCE_SESSION_ATTESTED: YES
FRESH_REPLACEMENT_SESSION_ATTESTED: YES
REPLACEMENT_ARTIFACT_BLOB_SHA: cbeb9ed7...
```

They must be re-established by the corrected fail-closed live protocol and internally consistent final evidence.

## Decision

`CHANGES_REQUIRED`

M3A deterministic mechanics remain valid. M3B is **not yet accepted as complete**. After R1-1 through R1-4 are remediated, perform ADR-013 delta verification, then a fresh ADR-017 Final Independent Audit over the final proof bundle before emitting `APPROVED`.