# REVIEW-032 — TASK-032 M8 Real Multi-Agent Continuity Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 5 — Stage-A Independent Brain-Proof Audit / C7 Gate
- Baseline main: `08508e48f6ffda70d1891dad461f6fd1b893b24b`
- Frozen Executor-A boundary S0: `38356f100563da420c488ee6362917fd4f81b48b`
- Executor A: `antigravity`
- Verified Brain proof bundle commit: `62263aa3a28ab56cc856fa6f980f39dec49163a1`
- Prior REVIEW blob: `97eb38522d59d6bf6829d4e49f0538300fd2844a`

```text
FULL_SEMANTIC_REVIEW: PASS
R1-1: CLOSED
R1-2: CLOSED
R1-3: CLOSED
R1-4: CLOSED
SEMANTIC_FINDINGS: NONE
M8_BRAIN_PROOF_REQUIRED: YES
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF_REQUIRED: YES
M8_EXECUTOR_PROOF: PENDING
M8_COMPOSITE_CHAIN: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

## Authoritative C7 Provenance

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

---

# Stage-A Independent Audit

Primary Brain independently inspected the persisted proof bundle at exact control commit `62263aa3a28ab56cc856fa6f980f39dec49163a1` rather than relying on terminal declarations.

## Canonical state

The persisted canonical state binds:

```text
task_id = TASK-032
main.sha = 08508e48f6ffda70d1891dad461f6fd1b893b24b
task_branch.sha = 38356f100563da420c488ee6362917fd4f81b48b
executor.last_id = antigravity
brain.last_id = chatgpt-chat
TASK blob = 4881d7bdf0f425912aada88914f3461293f6d19f
ADR-022 blob = 45ddeeec7a497f49cda011f2fd0eb3b3684e0110
RESULT-032 blob = 3a86327d096dd90c6f2c46f56d88d346581a6a46
```

Recomputed SHA-256 of the canonical state JSON is exactly:

```text
eac54ad486491164289a0187f16e83e228c624d76e8c58b58f6cf5633231e9ac
```

## Source Brain boundary

Persisted source result is exactly:

```text
brain_id = chatgpt-chat
request_id = req-task-032-diag-001
operation = DIAGNOSIS
status = INCOMPLETE
error_code = M8-CONTROLLED-BRAIN-HANDOFF
artifact_ref = null
evidence_ref = null
```

This satisfies the controlled M8 Brain-A boundary; it is not represented as a real outage/quota event.

## Replacement Brain identity and request equivalence

Replacement request keeps the same task, objective, operation, output contract and ordered context identities/blobs as the source request. Only the permitted Brain/request identities differ:

```text
source brain = chatgpt-chat
source request = req-task-032-diag-001
replacement brain = claude-chat
replacement request = req-task-032-diag-002
```

Primary Brain recomputed the request fingerprints:

```text
source_request_fingerprint = 5fab7981fede9e515a52dcfb2d33c6edfdfbefdc058fd8ce0d55fd9b8697c227
replacement_request_fingerprint = 1d31ad2094016ae43f27d08feb2820b89f626eb209b6597e6bb4d8e3ef942045
```

They exactly match the persisted `BrainFailoverProof`.

## BrainFailoverProof

The persisted proof binds exact task/operation/state/source/replacement identities and source result status. Primary Brain recomputed its canonical SHA-256 fingerprint using the locked `BrainFailoverProof.fingerprint()` semantics:

```text
16682e6cbf04180ec4624c8395a531f7574cfe7b43bf747ac862f5ce0b680a65
```

This equals the mechanically verified Stage-A result.

## Brain-B success artifact

Replacement result is exactly bound to:

```text
brain_id = claude-chat
request_id = req-task-032-diag-002
operation = DIAGNOSIS
status = SUCCESS
output_type = DIAGNOSIS_ARTIFACT
artifact path = .ai/context/proofs/TASK-032-M8/brain/BRAIN-DIAGNOSIS.md
artifact ref = 6eab012a4d84bbacf683a141913a6777c2b423a5
artifact blob = 9ec543c0a70bff1c5088a1940075b5c711cf2374
```

The same diagnosis artifact exists unchanged in the verified proof-bundle tree at commit `62263aa3a28ab56cc856fa6f980f39dec49163a1` with exact blob `9ec543c0a70bff1c5088a1940075b5c711cf2374`.

## Bounded-transfer attestation

Persisted attestation records:

```text
human_bounded_artifact_transfer = YES
human_bounded_artifact_transfer_bytes = 7710
token_usage = UNKNOWN
```

No transcript, raw prompt/response, cookie, session, auth, hidden-reasoning or equivalent forbidden evidence field is present in the persisted attestation/proof bundle.

## Advisory diagnosis disposition

Brain B raised concerns about `M8_SHARED_BOUNDARY_SHA: PENDING_SELF_REFERENCE` and the final semantic-repair publication carrying `ACTION: FIX`. Those concerns are retained verbatim in the immutable Brain-B artifact and were independently considered by Primary Brain.

They do not reopen a semantic finding at this gate:

1. TASK-032's Initial RESULT manifest explicitly permits `M8_SHARED_BOUNDARY_SHA: <S0 after Bridge publication or PENDING_SELF_REFERENCE as appropriate>`, and declares M8 status fields to be evidence summaries rather than independent proof authority.
2. Semantic repair rounds occurred before the live Brain proof. Round-4 Primary-Brain review explicitly froze the final accepted Executor-A publication `38356f100563da420c488ee6362917fd4f81b48b` as `M8_EFFECTIVE_S0` for both the live Brain proof and later Executor failover.
3. The authoritative task branch still resolves exactly to that frozen S0 after Stage-A proof persistence.

Therefore the Brain-B artifact is accepted as a successful advisory DIAGNOSIS artifact while its asserted blocker is not adopted as an authoritative semantic finding.

---

# Stage-A Decision

```text
SEMANTIC_FINDINGS: NONE
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF_REQUIRED: YES
M8_EXECUTOR_PROOF: PENDING
M8_COMPOSITE_CHAIN: PENDING
APPROVED: NO
```

Stage A is CLOSED/PASS.

The exact REVIEW-032 blob produced by this update becomes the mandatory review anchor for Stage-B Executor failover. If this REVIEW changes after Executor-B activation, or the StableExecutorFailoverProof/RESULT references a different review blob, Stage B fails closed.

---

# Stage-B Authorization Gate

Human must explicitly select a replacement Executor distinct from Executor A. Recommended proof path remains:

```text
antigravity -> claude-code
```

Expected Human command:

```text
/aios-worker FIX TASK-032 --executor claude-code
```

Before activation, the existing M5/M6/M7 path must independently enforce:

```text
source executor == antigravity
replacement executor == claude-code
source published sha == 38356f100563da420c488ee6362917fd4f81b48b
local task HEAD == S0
remote task HEAD == S0
source RESULT resolves exactly at S0
this exact REVIEW blob == activation review blob
prior authorization strict + CONSUMED
no ACTIVE lease
replacement lease exact
StableExecutorFailoverProof valid
```

No M5/M6/M7 contract modification is authorized.

Executor B must publish S1 through the existing Bridge path. `M8_COMPOSITE_CHAIN` remains PENDING until explicit composite verification and Primary Brain Stage-C independent audit.

## Decision

`STAGE A PASS — EXACT C7 PROVENANCE LOCKED — STAGE B EXECUTOR FAILOVER UNLOCKED FOR EXPLICIT HUMAN SELECTION — FINAL APPROVAL NOT YET GRANTED`
