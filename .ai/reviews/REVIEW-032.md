# REVIEW-032 — TASK-032 M8 Real Multi-Agent Continuity Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 6 — Stage-C Final Composite Audit / Proof-Verifier Repair
- Baseline main: `08508e48f6ffda70d1891dad461f6fd1b893b24b`
- Frozen Executor-A boundary S0: `38356f100563da420c488ee6362917fd4f81b48b`
- Historical Stage-B Executor-B publication S1: `22f2339eaa9acfdf30f5cf0f112172542362ecc3`
- Executor A: `antigravity`
- Executor B: `claude-code`
- Stage-A Brain proof bundle commit: `62263aa3a28ab56cc856fa6f980f39dec49163a1`
- Exact Stage-B authorization REVIEW commit: `781ea59a470d7850cb99c91d1f83914d886e94de`
- Exact Stage-B authorization REVIEW blob: `6ea95987983a06b066fc31789bedad5d4c954ff6`

```text
FULL_SEMANTIC_REVIEW: PASS
R1-1: CLOSED
R1-2: CLOSED
R1-3: CLOSED
R1-4: CLOSED
SEMANTIC_FINDINGS: NONE
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF: PASS_EVIDENCE_VALIDATED
M8_COMPOSITE_CHAIN: BLOCKED_BY_R6_1
FINAL_INDEPENDENT_AUDIT: FAIL
APPROVED: NO
```

## Preserved C7 Provenance

```text
M8_SOURCE_EXECUTOR_PUBLISHED_SHA: 38356f100563da420c488ee6362917fd4f81b48b
M8_BRAIN_SOURCE_ID: chatgpt-chat
M8_BRAIN_REPLACEMENT_ID: claude-chat
M8_BRAIN_FAILOVER_PROOF_FINGERPRINT: 16682e6cbf04180ec4624c8395a531f7574cfe7b43bf747ac862f5ce0b680a65
M8_BRAIN_SUCCESS_ARTIFACT_PATH: .ai/context/proofs/TASK-032-M8/brain/BRAIN-DIAGNOSIS.md
M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA: 9ec543c0a70bff1c5088a1940075b5c711cf2374
M8_CANONICAL_STATE_FINGERPRINT: eac54ad486491164289a0187f16e83e228c624d76e8c58b58f6cf5633231e9ac
M8_BRAIN_PROOF_BUNDLE_COMMIT: 62263aa3a28ab56cc856fa6f980f39dec49163a1
```

## Stage-B Evidence Accepted

The historical Stage-B publication is a direct child of S0:

```text
S0 = 38356f100563da420c488ee6362917fd4f81b48b
S1 = 22f2339eaa9acfdf30f5cf0f112172542362ecc3
S1 parent = S0
```

S1 changes only `.ai/results/RESULT-032.md` and records:

```text
EXECUTOR_ID: claude-code
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: antigravity
FAILOVER_TO_EXECUTOR: claude-code
FAILOVER_SOURCE_PUBLISHED_SHA: 38356f100563da420c488ee6362917fd4f81b48b
FAILOVER_PROOF_FINGERPRINT: 9ae77dfef922bc860cf5c423a242961a08060163972a6a329e7e69fa2df2a1d7
FAILOVER_REVIEW_BLOB_SHA: 6ea95987983a06b066fc31789bedad5d4c954ff6
M8_EXECUTOR_PROOF: PASS
M8_COMPOSITE_CHAIN: PENDING
```

The exact Stage-B REVIEW remained unchanged during activation/publish. Bridge's guarded publish path reconstructs the actual `StableExecutorFailoverProof`, recomputes its fingerprint, validates it relationally against source/replacement leases, verifies the authoritative control commit and exact REVIEW blob, and only then constructs `failover_info`. RESULT failover fields are generated from that validated object rather than copied from arbitrary worker text.

Therefore the real Executor A -> Executor B transition is accepted as valid evidence. The blocker below concerns the final composite verifier, not the historical failover itself.

---

# FINDING R6-1 — OPEN

## SEVERITY
`CRITICAL`

## ROOT_CAUSE
`verify_composite_chain(...)` does not mechanically verify the Executor half of the M8 causal chain required by C9/C10/AIP-7.

Current behavior:

1. It verifies the Brain proof bundle and C7 fields in REVIEW.
2. For S1, it accepts an arbitrary `s1_sha` string without resolving that commit or binding the supplied RESULT text to `S1:.ai/results/RESULT-032.md`.
3. It does not accept, parse, recompute, or validate the actual `StableExecutorFailoverProof`.
4. It does not validate `FAILOVER_PROOF_FINGERPRINT` at all.
5. It does not validate exact source/replacement Executor IDs against the failover proof.
6. It does not validate the proof's exact `review_ref.ref`, `review_ref.blob_sha`, or `source_result_ref` against S0.
7. It requires `M8_COMPOSITE_CHAIN: PASS` to already exist in RESULT before returning composite PASS, creating a circular self-attestation.
8. It also requires `M8_BRAIN_PROOF: PASS` in S1 RESULT even though Round-4 deliberately chose the conservative authority model where Bridge may keep Brain proof `PENDING` and Primary Brain is the authority for Brain acceptance.

The existing positive unit test demonstrates the false-positive path directly: it uses `s1 = "1" * 40`, supplies no StableExecutorFailoverProof, writes `M8_COMPOSITE_CHAIN: PASS` into synthetic RESULT text, and expects `verify_composite_chain(...)` to PASS.

## BROKEN_INVARIANT
TASK-032 C9/C10/AIP-7 requires the independently verified chain:

```text
exact S0
-> exact verified BrainFailoverProof
-> exact Brain-B artifact
-> exact immutable Stage-B REVIEW blob/ref
-> actual StableExecutorFailoverProof
-> exact source/replacement Executor IDs
-> exact S1 publication / RESULT
```

No worker/RESULT-authored `PASS` string is proof authority.

## REQUIRED_BEHAVIOR
Repair only the proof-local composite verifier. Do not redo Stage A or Stage B.

`verify-composite` MUST consume or resolve exact immutable evidence including at least:

```text
S0
historical Stage-B REVIEW ref/commit = 781ea59a470d7850cb99c91d1f83914d886e94de
historical Stage-B REVIEW blob = 6ea95987983a06b066fc31789bedad5d4c954ff6
Brain proof bundle
actual StableExecutorFailoverProof JSON
historical Stage-B S1 = 22f2339eaa9acfdf30f5cf0f112172542362ecc3
```

It MUST mechanically prove:

1. `S0` and `S1` are real Git commits.
2. Historical S1 is the Stage-B Executor-B publication anchored to S0; for this proof, require `S1^ == S0`.
3. `S1:.ai/results/RESULT-032.md` is resolved from Git directly; arbitrary caller-supplied RESULT text cannot substitute unless its exact Git blob identity is mechanically matched.
4. `StableExecutorFailoverProof.from_json(...)` succeeds and its canonical fingerprint equals exact `FAILOVER_PROOF_FINGERPRINT` in historical S1 RESULT.
5. Proof `task_id == TASK-032` and `target_branch == ai/task-032`.
6. Proof `source_published_sha == S0`.
7. Proof `source_executor_id == antigravity` and `replacement_executor_id == claude-code`; source/replacement must differ.
8. Proof `source_result_ref` is exact `.ai/results/RESULT-032.md` at S0 with the exact source RESULT blob.
9. Proof `review_ref.path == .ai/reviews/REVIEW-032.md`.
10. Proof `review_ref.ref == 781ea59a470d7850cb99c91d1f83914d886e94de` and `review_ref.blob_sha == 6ea95987983a06b066fc31789bedad5d4c954ff6`.
11. Computed Git blob of that historical REVIEW equals the proof/ref/S1 RESULT review blob.
12. REVIEW C7 Brain provenance matches the mechanically verified Brain proof bundle exactly.
13. Historical S1 RESULT's `EXECUTOR_ID`, `FAILOVER_FROM_EXECUTOR`, `FAILOVER_TO_EXECUTOR`, source SHA, proof fingerprint, and review blob all match the actual proof.
14. Composite verifier returns PASS from these relationships. It MUST NOT require a pre-existing `M8_COMPOSITE_CHAIN: PASS` string.
15. `M8_BRAIN_PROOF` / `M8_COMPOSITE_CHAIN` fields in RESULT remain evidence summaries, not proof authority. A conservative `PENDING` must not prevent mechanically correct independent verification.

The real Stage-B proof currently resides in the consumed runtime authorization. Preserve/export only the sanitized `failover_proof` JSON before starting another FIX. Preferred durable proof location:

```text
ai-control:.ai/context/proofs/TASK-032-M8/executor/stable-executor-failover-proof.json
```

Do not persist authorization tokens, full runtime auth, leases, secrets, prompts, or transcripts.

## FORBIDDEN_IMPLEMENTATIONS
- No PASS based on `M8_COMPOSITE_CHAIN: PASS` text.
- No fake/nonexistent S1 accepted.
- No arbitrary RESULT file supplied from working tree as authority.
- No reconstructing Executor proof from only RESULT strings.
- No history scan for a plausible proof/review/result.
- No modification to locked Continuity Core.
- No new Brain proof.
- No second cross-executor failover merely to make the verifier pass.
- No M9/M10/M11 scope leakage.

## REQUIRED_TESTS
1. Existing synthetic success test must be replaced; nonexistent/fabricated S1 (`"1" * 40`) => fail.
2. Missing actual StableExecutorFailoverProof => fail.
3. Tampered proof canonical field with unchanged claimed fingerprint => fail.
4. RESULT `FAILOVER_PROOF_FINGERPRINT` mismatch => fail.
5. Proof source SHA != S0 => fail.
6. Proof source/replacement Executor IDs wrong or equal => fail.
7. Proof source RESULT ref/blob mismatch => fail.
8. Proof REVIEW ref commit mismatch => fail.
9. Proof REVIEW blob mismatch => fail.
10. S1 RESULT review blob/failover IDs mismatch => fail.
11. S1 not direct child of S0 for this historical Stage-B proof => fail.
12. Caller-supplied RESULT text differing from exact S1 Git blob => fail.
13. Exact chain with `M8_BRAIN_PROOF: PENDING` and `M8_COMPOSITE_CHAIN: PENDING` in historical RESULT may still return verifier PASS when all authoritative proof relationships pass.
14. Brain proof/C7 negative tests remain green.
15. Full Bridge/Continuity/repository suites remain green with execution-derived evidence.

## ADVERSARIAL_TESTS
The following must never PASS:

```text
s1_sha = 1111111111111111111111111111111111111111
no StableExecutorFailoverProof provided
synthetic RESULT says:
  M8_BRAIN_PROOF: PASS
  M8_EXECUTOR_PROOF: PASS
  M8_COMPOSITE_CHAIN: PASS
```

A syntactically convincing RESULT is not a causal proof.

## CLOSE_CONDITIONS
```text
[ ] actual StableExecutorFailoverProof is an explicit verifier input/evidence object
[ ] proof fingerprint is recomputed and matches historical S1 RESULT
[ ] exact historical Stage-B REVIEW commit/blob is bound
[ ] source RESULT is exact S0 artifact
[ ] source/replacement Executor identities are verified from proof
[ ] S1 is real and exact RESULT is resolved from S1 Git tree
[ ] fabricated/nonexistent S1 cannot pass
[ ] composite PASS no longer depends on pre-existing PASS text
[ ] conservative PENDING summary fields do not block exact independent verification
[ ] real historical chain S0 -> REVIEW -> failover proof -> S1 passes repaired verifier
[ ] full repository remains green
```

## ALLOWED_FILES
- `scripts/aios_m8_multi_agent_continuity_proof.py`
- `tests/aios_bridge/continuity/test_m8_multi_agent_proof.py`
- proof-local documentation/helper only if strictly necessary to consume the exact sanitized Executor proof

## FORBIDDEN_SCOPE
- `src/aios_bridge/continuity/*`
- `src/aios_bridge/runtime_lease.py`
- M5/M6/M7 behavior
- Executor routing/selection
- new failover
- Brain proof regeneration

---

## Next Execution Contract

Before any new `/aios-worker FIX`, preserve the historical Stage-B sanitized failover proof from the consumed TASK-032 authorization. `bridge.py context 32` loads the consumed authorization and exposes the proof data; extract only `authorization.failover_proof` to a bounded proof JSON file.

After that evidence is preserved, repair R6-1 using the same current Executor B (`claude-code`). This is a verifier repair continuation, not another cross-executor proof.

Expected command after proof preservation:

```text
/aios-worker FIX TASK-032 --executor claude-code
```

The subsequent repair publication is not a replacement for historical Stage-B S1. Final composite verification must continue to anchor the original:

```text
S0 = 38356f100563da420c488ee6362917fd4f81b48b
Stage-B REVIEW commit = 781ea59a470d7850cb99c91d1f83914d886e94de
Stage-B REVIEW blob = 6ea95987983a06b066fc31789bedad5d4c954ff6
Stage-B failover fingerprint = 9ae77dfef922bc860cf5c423a242961a08060163972a6a329e7e69fa2df2a1d7
Historical S1 = 22f2339eaa9acfdf30f5cf0f112172542362ecc3
```

## Decision

`CHANGES_REQUIRED — STAGE A PASS — STAGE B FAILOVER EVIDENCE VALID — R6-1 CRITICAL COMPOSITE-VERIFIER DEFECT — FINAL PASS BLOCKED`
