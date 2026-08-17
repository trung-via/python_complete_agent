# REVIEW-032 — TASK-032 M8 Real Multi-Agent Continuity Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 7 — R6-1 Targeted Composite-Verifier Re-audit
- Baseline main: `08508e48f6ffda70d1891dad461f6fd1b893b24b`
- Frozen Executor-A boundary S0: `38356f100563da420c488ee6362917fd4f81b48b`
- Historical Stage-B S1: `22f2339eaa9acfdf30f5cf0f112172542362ecc3`
- Current repair head: `a40dd1236543a4b90a4c4d392e9ae89bb66f519c`
- Historical Stage-B REVIEW commit: `781ea59a470d7850cb99c91d1f83914d886e94de`
- Historical Stage-B REVIEW blob: `6ea95987983a06b066fc31789bedad5d4c954ff6`
- Historical StableExecutorFailoverProof fingerprint: `9ae77dfef922bc860cf5c423a242961a08060163972a6a329e7e69fa2df2a1d7`

```text
FULL_SEMANTIC_REVIEW: PASS
R1-1: CLOSED
R1-2: CLOSED
R1-3: CLOSED
R1-4: CLOSED
R6-1: PARTIALLY_CLOSED
SEMANTIC_FINDINGS: NONE
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF: PASS_EVIDENCE_VALIDATED
M8_COMPOSITE_CHAIN: BLOCKED_BY_R6_1
FINAL_INDEPENDENT_AUDIT: FAIL
APPROVED: NO
```

## Round-7 Accepted Repairs

The repair correctly moved the composite verifier toward authoritative evidence:

```text
[x] S0 is required to resolve as a real Git commit
[x] when S1 is supplied, S1 must resolve as a real Git commit
[x] historical S1 is required to be a direct child of S0
[x] RESULT-032 is resolved from S1 Git tree
[x] caller-supplied RESULT cannot substitute unless exact blob matches S1 RESULT
[x] StableExecutorFailoverProof is parsed as the executor evidence object
[x] proof canonical fingerprint is recomputed
[x] proof task/branch/source-SHA/source-result-ref are checked
[x] source/replacement executor IDs are checked and must differ
[x] S1 RESULT failover IDs/source SHA/review blob/proof fingerprint are matched to proof
[x] verifier no longer requires pre-existing M8_COMPOSITE_CHAIN: PASS
[x] conservative M8_BRAIN_PROOF/PENDING and M8_COMPOSITE_CHAIN/PENDING in historical S1 do not block proof-derived PASS
[x] fabricated/nonexistent S1 test now fails closed
[x] historical S0/S1 test path was added
[x] locked Continuity Core was not modified in this repair
[x] full repository evidence reports 784/784 pass, 0 regressions
```

These close most of R6-1, but two exact Round-6 requirements remain open.

---

# FINDING R6-1 — PARTIALLY_CLOSED

## SEVERITY
`CRITICAL`

## ROOT_CAUSE
The repaired function still has an optional Brain+Review-only success path and does not mechanically resolve the historical REVIEW from `StableExecutorFailoverProof.review_ref.ref`.

### Gap A — composite verification can PASS with no S1 and no Executor proof

`verify_composite_chain(...)` executes the Executor half only under:

```python
if s1_sha:
    ...
```

and then unconditionally returns:

```python
{"status": "PASS", ...}
```

Therefore `s1_sha=None` skips all StableExecutorFailoverProof/S1 validation and still returns PASS.

The test suite explicitly preserves this behavior in:

```text
test_m8_composite_chain_verification_success_brain_and_review
```

which calls `verify_composite_chain(...)` with only S0 + REVIEW + Brain bundle and asserts:

```text
status == PASS
s1_sha is None
```

This violates Round-6 REQUIRED_BEHAVIOR: `verify-composite` MUST consume the historical S1 and actual StableExecutorFailoverProof before returning composite PASS.

### Gap B — exact historical REVIEW commit is not resolved from Git

The repaired verifier checks:

```text
exec_proof.review_ref.path
exec_proof.review_ref.blob_sha == hash(caller review_content)
```

but it does not require/resolve:

```text
exec_proof.review_ref.ref == 781ea59a470d7850cb99c91d1f83914d886e94de
```

nor execute the equivalent of:

```text
git cat-file -e 781ea59a...^{commit}
git rev-parse 781ea59a...:.ai/reviews/REVIEW-032.md
git show 781ea59a...:.ai/reviews/REVIEW-032.md
```

Thus the verifier has not mechanically proven Round-6 requirement #10/#11: the exact historical REVIEW commit/ref must exist and contain the exact blob/content used by C7 and the executor proof.

## BROKEN_INVARIANT
Final M8 composite PASS must mean the whole chain was mechanically verified:

```text
S0
-> verified Brain proof/artifact
-> exact historical REVIEW commit/blob
-> actual StableExecutorFailoverProof
-> historical S1/result
```

A Brain+Review-only verification is not a composite proof, and caller REVIEW text alone is not proof that `review_ref.ref` contains that artifact.

## REQUIRED_BEHAVIOR
Keep all accepted Round-7 checks. Make only these final changes:

1. `verify_composite_chain` MUST fail closed when `s1_sha` is absent.
2. `verify_composite_chain` MUST fail closed when actual `executor_failover_proof` evidence is absent.
3. CLI `verify-composite` MUST require `--s1` and `--executor-proof-file` for composite mode; do not expose a PASS-capable partial mode under the same command/function.
4. If Brain+Review-only checking is still useful, make it a separately named verifier/helper whose result cannot be represented as composite PASS.
5. Resolve `exec_proof.review_ref.ref` as an exact Git commit.
6. For TASK-032 historical acceptance, require:

```text
exec_proof.review_ref.ref == 781ea59a470d7850cb99c91d1f83914d886e94de
```

or equivalently require an explicit expected historical-review-commit input and compare exact equality.
7. Resolve `.ai/reviews/REVIEW-032.md` directly at that commit and require its Git blob SHA equals:

```text
exec_proof.review_ref.blob_sha
6ea95987983a06b066fc31789bedad5d4c954ff6
historical S1 RESULT FAILOVER_REVIEW_BLOB_SHA
```

8. Caller `review_content`, if retained, must exact-match the REVIEW resolved from that immutable Git ref; it cannot be the authority by itself.
9. Historical chain `38356f10 -> 781ea59a REVIEW -> 9ae77d proof -> 22f2339e S1` must continue to PASS with S1 summary fields still PENDING where appropriate.

## FORBIDDEN_IMPLEMENTATIONS
- Do not treat missing S1 as successful composite verification.
- Do not treat missing Executor proof as successful composite verification.
- Do not hash caller REVIEW text and call that sufficient review-ref verification.
- Do not inspect current `ai-control` as a substitute for historical REVIEW commit `781ea59a...`.
- Do not rewrite historical S1.
- Do not redo Brain proof or Executor failover.
- Do not modify locked Continuity Core/M5/M6/M7 semantics.
- Do not add automatic routing/failover or M9+ scope.

## REQUIRED_TESTS
Add/adjust exact assertions:

```text
1. no S1 supplied => FAIL, never composite PASS
2. S1 supplied but no StableExecutorFailoverProof => FAIL
3. historical REVIEW ref commit missing/nonexistent => FAIL
4. proof review_ref.ref != expected historical REVIEW commit => FAIL
5. git blob at review_ref.ref:path != proof review_ref.blob_sha => FAIL
6. caller review text != exact historical Git REVIEW => FAIL
7. fabricated/nonexistent S1 => FAIL
8. tampered proof/source/result/review/fingerprint/executor IDs remain FAIL
9. real historical chain with S1 M8_BRAIN_PROOF:PENDING and M8_COMPOSITE_CHAIN:PENDING => verifier PASS
10. full Bridge/Continuity/repository suites remain green with execution-derived counts
```

The old positive test:

```text
test_m8_composite_chain_verification_success_brain_and_review
```

must no longer assert composite PASS. Replace it with a failure assertion or move the behavior into a separately named non-composite Brain/C7 verifier.

## ADVERSARIAL_TESTS
These inputs must all return non-zero/raise:

```text
S0 + valid Brain bundle + valid-looking REVIEW + s1=None + executor_proof=None
S0 + real S1 + no executor proof
real proof + caller-copied REVIEW text but nonexistent/wrong review_ref.ref
real-looking review blob but review_ref.ref does not resolve that blob from Git
```

## CLOSE_CONDITIONS
```text
[x] actual StableExecutorFailoverProof can be consumed and fingerprinted
[x] proof fingerprint binds to historical S1 RESULT
[ ] composite PASS is impossible without S1
[ ] composite PASS is impossible without actual Executor proof
[ ] exact historical REVIEW commit is equality-checked
[ ] exact REVIEW blob/content is resolved from review_ref.ref Git tree
[x] source RESULT is exact S0 artifact
[x] source/replacement Executor identities are verified
[x] S1 is real and exact RESULT is resolved from S1 Git tree
[x] fabricated/nonexistent S1 cannot pass
[x] pre-existing M8_COMPOSITE_CHAIN:PASS is not required
[x] conservative PENDING summary fields do not block authoritative verification
[x] historical chain has a positive test path
[x] full repository remains green
```

## ALLOWED_FILES
- `scripts/aios_m8_multi_agent_continuity_proof.py`
- `tests/aios_bridge/continuity/test_m8_multi_agent_proof.py`

## FORBIDDEN_SCOPE
- `src/aios_bridge/continuity/*`
- `src/aios_bridge/runtime_lease.py`
- `bridge.py` semantic changes
- M5/M6/M7 behavior
- new Brain proof
- new Executor failover
- historical S1 mutation

---

## Historical Proof Anchors — DO NOT CHANGE

```text
S0: 38356f100563da420c488ee6362917fd4f81b48b
Brain proof bundle: 62263aa3a28ab56cc856fa6f980f39dec49163a1
BrainFailoverProof fingerprint: 16682e6cbf04180ec4624c8395a531f7574cfe7b43bf747ac862f5ce0b680a65
Brain diagnosis blob: 9ec543c0a70bff1c5088a1940075b5c711cf2374
Stage-B REVIEW commit: 781ea59a470d7850cb99c91d1f83914d886e94de
Stage-B REVIEW blob: 6ea95987983a06b066fc31789bedad5d4c954ff6
StableExecutorFailoverProof fingerprint: 9ae77dfef922bc860cf5c423a242961a08060163972a6a329e7e69fa2df2a1d7
Historical S1: 22f2339eaa9acfdf30f5cf0f112172542362ecc3
Current repair head: a40dd1236543a4b90a4c4d392e9ae89bb66f519c
```

## Decision

`CHANGES_REQUIRED — R6-1 PARTIALLY_CLOSED — ONLY MISSING-S1/PARTIAL-PASS AND HISTORICAL-REVIEW-REF BINDING REMAIN — FINAL M8 PASS BLOCKED`
