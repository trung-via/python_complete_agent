# REVIEW-032 — TASK-032 M8 Real Multi-Agent Continuity Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 1 — Review Protocol v2 / Full Semantic Review
- Baseline main: `08508e48f6ffda70d1891dad461f6fd1b893b24b`
- Reviewed branch head: `42dfd52dc9a0c54a9673c9ebcb6c23c7bf00dc4d`
- Authoritative contracts: ADR-022 + TASK-032 + carried-forward M3/M5/M6/M7 contracts.

```text
FULL_SEMANTIC_REVIEW: FAIL
M8_BRAIN_PROOF_REQUIRED: BLOCKED
M8_EXECUTOR_PROOF_REQUIRED: BLOCKED
M8_COMPOSITE_CHAIN: BLOCKED
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

Current implementation is green at `767/767` full-repository tests, but test success does not close the contract violations below.

---

# FINDING R1-1

## FINDING_ID
`R1-1`

## SEVERITY
`CRITICAL`

## ROOT_CAUSE
TASK-032 publication logic in `bridge.py` sets all three M8 proof states to PASS solely when generic `failover_info` exists:

```python
if failover_info:
    brain_proof_val = "PASS"
    executor_proof_val = "PASS"
    composite_chain_val = "PASS"
```

This does not validate the M8 Brain proof, Brain success artifact, C7 REVIEW provenance block, or composite causal chain.

## BROKEN_INVARIANT
TASK-032 C7/C9/C10 requires:

```text
BrainFailoverProof
 -> Brain B artifact blob
 -> exact REVIEW-032 blob containing Brain provenance
 -> StableExecutorFailoverProof
 -> Executor B publication
```

No worker-authored status string and no executor failover by itself may establish `M8_BRAIN_PROOF: PASS` or `M8_COMPOSITE_CHAIN: PASS`.

## REQUIRED_BEHAVIOR
1. Initial RUN must emit `PENDING/PENDING/PENDING`.
2. A generic cross-executor failover that lacks independently verified Brain proof provenance MUST NOT make Brain or composite state PASS.
3. `M8_BRAIN_PROOF: PASS` may be emitted only from exact authoritative M8 Brain proof evidence accepted through the Review gate.
4. `M8_EXECUTOR_PROOF: PASS` may be emitted only when the existing M6/M7 stable failover is valid AND its exact review blob is the authoritative M8 REVIEW containing the accepted Brain provenance block.
5. `M8_COMPOSITE_CHAIN: PASS` may be emitted only after exact composite verification proves the complete chain. If Bridge is not itself the correct authority to perform the final composite verification, keep this field `PENDING` until Primary Brain/final proof stage; do not infer it from `failover_info`.

## FORBIDDEN_IMPLEMENTATIONS
- Do not set any M8 PASS field from `bool(failover_info)`.
- Do not trust current working-tree RESULT/REVIEW text as proof authority.
- Do not scan arbitrary history for a plausible Brain proof.
- Do not hard-code Brain IDs/fingerprints/artifact SHAs.
- Do not modify M5/M6/M7 failover contracts merely to carry M8 status.
- Do not let Executor-generated data fabricate Primary Brain approval.

## REQUIRED_TESTS
1. TASK-032 cross-executor failover with no Brain provenance => `M8_BRAIN_PROOF != PASS` and `M8_COMPOSITE_CHAIN != PASS`.
2. Valid executor failover anchored to a normal/non-M8 review => Brain/composite remain non-PASS.
3. Tampered C7 Brain fingerprint in review => publication fails closed or M8 proof stays non-PASS.
4. Tampered Brain artifact blob in review => fail closed/non-PASS.
5. Correct Brain provenance + exact review blob + valid executor failover => executor proof can PASS according to contract.
6. Composite PASS requires explicit exact composite verification, not mere failover presence.

## ADVERSARIAL_TESTS
- forged `M8_BRAIN_PROOF: PASS` in task-branch RESULT;
- valid M6 failover using REVIEW-032 without C7 block;
- review blob changed after activation;
- valid executor failover with fake Brain proof fingerprint;
- same-executor FIX must never satisfy M8 executor boundary.

## CLOSE_CONDITIONS
```text
[ ] no code path assigns all M8 PASS states merely because failover_info exists
[ ] Brain PASS requires exact accepted Brain proof provenance
[ ] Executor PASS requires exact stable failover + exact M8 review binding
[ ] Composite PASS requires explicit full-chain verification
[ ] negative tests prove generic failover cannot fabricate Brain/composite PASS
[ ] existing M5/M6/M7 tests remain green
```

## ALLOWED_FILES
- `bridge.py` only if needed to remove/replace the unsafe TASK-032 status derivation;
- `tests/test_bridge.py`;
- `scripts/aios_m8_multi_agent_continuity_proof.py` only if shared proof-status helper logic belongs there;
- TASK-032 proof-local tests.

## FORBIDDEN_SCOPE
All locked Continuity Core files from TASK-032 C11; M5/M6/M7 semantic redesign; auto-routing; M9/M10/M11 features.

---

# FINDING R1-2

## FINDING_ID
`R1-2`

## SEVERITY
`HIGH`

## ROOT_CAUSE
`prepare_brain_pack()` attempts to resolve this path:

```text
.ai/decisions/ADR-022-AIOS-CONTINUITY-M8-MULTI-AGENT-CONTINUITY-PROOF-CONTRACT-LOCK.md
```

but the authoritative ADR created for TASK-032 is:

```text
.ai/decisions/ADR-022-M8-MULTI-AGENT-CONTINUITY-PROOF-CONTRACT-LOCK.md
```

Worse, `_get_blob()` silently falls back to current filesystem content and, if missing, returns `"0" * 40`.

## BROKEN_INVARIANT
TASK-032 C1/C12/C13 requires exact immutable TASK/ADR/source RESULT refs at S0. Missing/mismatched exact evidence must fail closed. Working-tree fallback and all-zero synthetic blob IDs are explicitly incompatible with that contract.

## REQUIRED_BEHAVIOR
1. Resolve the exact authoritative ADR-022 path.
2. Resolve TASK-032, ADR-022 and RESULT-032 strictly from exact S0 Git objects.
3. If any `git rev-parse <S0>:<path>` fails, `prepare-brain` must fail non-zero.
4. No filesystem fallback for canonical proof identity.
5. No synthetic zero SHA fallback.
6. Validate SHA syntax/non-zero where practical before constructing `ArtifactRef`/`ContextRef`.

## FORBIDDEN_IMPLEMENTATIONS
- No current-filesystem fallback.
- No `0 * 40` or placeholder SHA accepted as evidence.
- No `HEAD` substitution when caller explicitly supplies S0.
- No nearest/latest plausible artifact lookup.

## REQUIRED_TESTS
1. exact real ADR path resolves successfully;
2. nonexistent ADR path => fail closed;
3. missing source RESULT at S0 => fail closed;
4. supplied unresolvable S0 => fail closed;
5. working-tree file exists but is absent at S0 => still fail closed;
6. generated canonical state contains exact non-placeholder blob SHAs.

## ADVERSARIAL_TESTS
- create a working-tree fake ADR while S0 lacks it; prepare must reject;
- force `git rev-parse` failure; no pack may be emitted;
- pass a valid-looking but nonexistent 40-char commit SHA.

## CLOSE_CONDITIONS
```text
[ ] exact ADR-022 path is used
[ ] no filesystem fallback exists for canonical artifact resolution
[ ] no zero-SHA fallback exists
[ ] missing exact S0 artifact fails non-zero
[ ] tests cover working-tree fallback attack
```

## ALLOWED_FILES
- `scripts/aios_m8_multi_agent_continuity_proof.py`
- `tests/aios_bridge/continuity/test_m8_multi_agent_proof.py`

## FORBIDDEN_SCOPE
Continuity Core; Bridge authority semantics unrelated to R1-1; routing/failover redesign.

---

# FINDING R1-3

## FINDING_ID
`R1-3`

## SEVERITY
`HIGH`

## ROOT_CAUSE
`verify_brain_proof()` parses `brain-failover-proof.json` into `proof`, but the semantic validation call separately invokes `validate_brain_failover_eligibility(...)` and does not bind the parsed `proof` object to the validated source request, replacement request, state fingerprint and source result. The returned summary then reports `proof.fingerprint()` from the unbound parsed object.

A structurally valid but semantically different proof artifact can therefore supply the fingerprint later anchored into REVIEW while eligibility was validated against different in-memory inputs.

## BROKEN_INVARIANT
TASK-032 C4/C7/C13 requires the exact BrainFailoverProof fingerprint in REVIEW to identify the exact proof that was mechanically validated for the S0 requests/state.

## REQUIRED_BEHAVIOR
1. Construct/obtain the canonical expected BrainFailoverProof from the same validated inputs using the existing M3 primitive.
2. Compare the persisted proof artifact against that exact canonical proof (canonical JSON/fingerprint and relevant fields).
3. Any mismatch must fail closed.
4. The fingerprint returned by `verify_brain_proof()` must be the fingerprint of the exact validated persisted proof, not merely any parseable proof file.

## FORBIDDEN_IMPLEMENTATIONS
- Do not validate one proof and report another proof's fingerprint.
- Do not compare only actor names.
- Do not accept a proof merely because it parses.
- Do not hard-code expected proof fingerprint.

## REQUIRED_TESTS
Tamper individually and require failure for at least:
- `state_fingerprint`;
- `source_request_fingerprint`;
- `replacement_request_fingerprint`;
- `source_brain_id`;
- `replacement_brain_id`;
- request IDs/operation where schema permits.

## ADVERSARIAL_TESTS
A fully parseable proof with one changed field and recomputed own fingerprint must still be rejected because it does not equal the proof derived from validated inputs.

## CLOSE_CONDITIONS
```text
[ ] persisted BrainFailoverProof is exactly bound to validated inputs
[ ] verifier rejects semantic proof drift even when JSON is structurally valid
[ ] returned proof fingerprint belongs to the exact validated persisted proof
[ ] tamper tests cover proof-field drift
```

## ALLOWED_FILES
- `scripts/aios_m8_multi_agent_continuity_proof.py`
- `tests/aios_bridge/continuity/test_m8_multi_agent_proof.py`

## FORBIDDEN_SCOPE
M3 Continuity Core failover semantics; new proof type; provider-specific branches.

---

# FINDING R1-4

## FINDING_ID
`R1-4`

## SEVERITY
`MEDIUM`

## ROOT_CAUSE
Replacement Brain result validation checks status, request ID, brain ID, artifact presence and blob SHA, but does not fully bind the result to all TASK-032 output identity requirements, including exact task/operation/output type and exact artifact target path/ref semantics.

## BROKEN_INVARIANT
TASK-032 AIP-4 requires exact replacement result identity and exact success artifact path/blob, not just a matching blob hash.

## REQUIRED_BEHAVIOR
Verify at minimum:
```text
repl_res.task_id == repl_req.task_id
repl_res.request_id == repl_req.request_id
repl_res.brain_id == repl_req.brain_id
repl_res.operation == repl_req.operation
repl_res.output_type == repl_req.output_contract.expected_output_type
repl_res.artifact_ref.path == repl_req.output_contract.target_artifact_path
repl_res.artifact_ref.blob_sha == exact normalized diagnosis blob
```
Also validate artifact ref/ref-domain according to the exact proof storage contract rather than accepting arbitrary unrelated refs.

## FORBIDDEN_IMPLEMENTATIONS
- Do not accept matching blob with wrong artifact path.
- Do not accept correct request_id with wrong task/operation/output type.
- Do not weaken `BrainResult` schema.

## REQUIRED_TESTS
One negative test per identity field above.

## ADVERSARIAL_TESTS
Use the same diagnosis blob but point `artifact_ref.path` at a different proof artifact; verifier must reject.

## CLOSE_CONDITIONS
```text
[ ] replacement result is fully bound to replacement request/output contract
[ ] wrong path/task/operation/output type each fail closed
[ ] exact diagnosis blob still required
```

## ALLOWED_FILES
- `scripts/aios_m8_multi_agent_continuity_proof.py`
- `tests/aios_bridge/continuity/test_m8_multi_agent_proof.py`

## FORBIDDEN_SCOPE
Continuity Core schema redesign; provider-specific logic.

---

## Positive Evidence

Current HEAD is a direct child of the locked M8 baseline. Initial RESULT truthfully keeps the M8 proof states PENDING and reports a fresh full-repository execution of `767 passed`. Locked Continuity Core files were not observed in the implementation commit diff. The proof-local runner/tests are directionally aligned with ADR-022.

However, live Brain proof MUST NOT begin while R1-1 through R1-4 remain open.

## Execution Instruction

Run a narrow repair with the current Executor:

```text
/aios-worker FIX TASK-032 --executor antigravity
```

Do NOT start Brain A / Brain B live interactions yet.

After Antigravity publishes the repair, return to Primary Brain with:

```text
Review TASK-032
```

## Decision

`CHANGES_REQUIRED — R1-1 CRITICAL, R1-2 HIGH, R1-3 HIGH, R1-4 MEDIUM — M8 LIVE BRAIN PROOF BLOCKED`
