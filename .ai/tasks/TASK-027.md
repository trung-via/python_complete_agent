# TASK-027 — Open Multi-Agent Continuity OS M3B Real Cross-Chat Brain Failover Proof

## Work Class

`L3 — ARCHITECTURE / HIGH-RISK PROOF`

This task follows ADR-017 Uniform Assurance Pipeline.

Primary Brain owns Contract, Architecture Implementation Plan, Adversarial Checklist, Full Semantic Review and Final Independent Audit. Antigravity owns repository inspection, proof-runner implementation/mechanical evidence preparation where needed, tests and self-audit. Human remains sole RUN/FIX/MERGE authority and performs the explicitly human-triggered cross-chat interactions required by ADR-016.

---

## Baseline

Canonical `main` at authoring:

```text
44436c59eb42dbdbffaee28a738d11694958a4ea
```

Relevant locked contracts/policy:
- ADR-010 Open Multi-Agent Continuity OS Architecture;
- ADR-011 Canonical Project State;
- ADR-016 M3 Brain Failover Proof Contract;
- ADR-017 Uniform Assurance Pipeline.

Relevant proven implementation:
- TASK-022 / M3A deterministic Brain failover harness;
- TASK-023 Brain-neutral contract hardening;
- TASK-025 Canonical State hardening.

M3A is complete. M3 remains incomplete until this real two-Brain proof succeeds.

No new ADR is required because this task executes the already-locked M3B contract and does not intentionally change a reusable invariant.

---

## Objective

Prove, using **two distinct real interactive Brain surfaces**, that one pending advisory Brain operation can fail over at a stable boundary from Brain A to Brain B while preserving the exact same canonical task-state snapshot and operation semantics, without prior chat transcript/hidden reasoning, without chat-UI automation, without paid External Brain API calls, and without widening execution/merge authority.

This is a **controlled failover proof**, not a claim that a real provider outage or quota exhaustion occurred.

---

# Primary Brain Contract

## C1 — Proof-local frozen Canonical State snapshot

M3B SHALL use one immutable schema-v1 `ContinuityState` snapshot anchored to exact repository/control facts.

The proof snapshot SHALL be a canonical `ContinuityState` serialization and fingerprint, not an ad-hoc dict.

It SHALL represent the stable pre-execution TASK-027 boundary using exact:
- current canonical main SHA at execution start;
- authoritative TASK-027 blob;
- authoritative ADR-010 / ADR-011 / ADR-016 / ADR-017 blobs;
- task branch identity where required by the state schema;
- no stale TASK-019 CURRENT-STATE data.

The existing `.ai/state/CURRENT-STATE.json` is not automatically lifecycle-integrated by Bridge v0.4 and MUST NOT be silently reused if it describes another task/snapshot.

The M3B proof MAY persist a proof-local frozen state artifact under:

```text
.ai/context/proofs/TASK-027-M3B-STATE.json
```

This proof-local snapshot does not replace or mutate global Continuity lifecycle semantics.

## C2 — One pending advisory operation

Use one vendor-neutral pending Brain operation:

```text
operation: DIAGNOSIS
output_type: DIAGNOSIS_ARTIFACT
output_target: .ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md
```

The objective SHALL be bounded and task-local: diagnose the invariants required for a valid M3B stable-boundary Brain failover and identify conditions that would make the handoff invalid.

The successful diagnosis artifact SHALL use the existing advisory structure:

```text
CAUSE
EVIDENCE
FIX
TESTS
RISKS
```

It MUST NOT contain source code execution instructions, secrets, transcript dumps or hidden chain-of-thought.

## C3 — Exact source/replacement request equivalence

The source `BrainRequest` and replacement `BrainRequest` SHALL be created/validated through the existing M3A contract.

The following MUST be byte/semantic equivalent under the existing BrainRequest contract:
- schema version;
- task_id;
- operation;
- objective;
- ordered context refs;
- every context-ref blob SHA;
- output contract;
- canonical state fingerprint supplied to failover validation.

Only these request identity values may differ:
- `brain_id`;
- `request_id`.

Any drift in objective, context order/content identity, operation, output target, task or state snapshot FAILS M3B.

## C4 — Two distinct real Brain surfaces

At live-proof time the Human SHALL explicitly select:

```text
SOURCE_BRAIN_ID
REPLACEMENT_BRAIN_ID
```

Requirements:
- canonical actor IDs;
- IDs differ;
- two genuinely distinct interactive Brain surfaces, not two tabs/sessions presented as different Brain implementations;
- replacement capability declares support for DIAGNOSIS;
- no particular vendor is required;
- no paid API Brain is required or used for the acceptance proof.

Continuity Core and proof validation MUST remain vendor-neutral and MUST NOT branch on ChatGPT/Claude/Gemini names.

## C5 — Fresh-session / canonical-pack isolation

Brain A and Brain B SHALL each be human-triggered in a fresh/new interaction context for this proof.

Each Brain SHALL receive only the bounded M3B input pack required for its request:
- canonical state snapshot/fingerprint;
- its own canonical BrainRequest;
- bounded authoritative context resolved from the exact context refs/blobs;
- output-format instructions needed to normalize the result.

Brain B MUST NOT receive:
- Brain A transcript;
- Brain A hidden reasoning;
- Brain A prompt history;
- screenshots/session cookies;
- source chat-memory dump;
- source raw response beyond anything mechanically required by the failover validator (and source result is not needed as reasoning context for Brain B).

A prior conversation transcript SHALL NOT be part of either Brain context pack.

## C6 — Controlled non-success source boundary

M3B SHALL use a deliberate, transparent controlled non-success source result so the proof is repeatable and does not wait for a real outage.

Brain A SHALL receive/reconstruct the source request and return a valid normalized source `BrainResult` with:

```text
status: INCOMPLETE
error_code: M3B-CONTROLLED-HANDOFF
```

and no successful diagnosis artifact pointer.

The RESULT/REVIEW MUST describe this as **CONTROLLED_INCOMPLETE**, not as a real quota failure, outage or provider unavailability event.

A source `SUCCESS` MUST fail closed because M3A forbids competing successful outputs for the same logical operation.

## C7 — Real replacement Brain success

After source non-success is validated, Brain B SHALL receive the equivalent replacement request tied to the exact same state fingerprint and bounded context identities.

Brain B SHALL produce the diagnosis content for:

```text
.ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md
```

The final normalized replacement `BrainResult` SHALL be:
- `status: SUCCESS`;
- exact replacement task/request/brain/operation identity;
- `output_type: DIAGNOSIS_ARTIFACT`;
- an `ArtifactRef` whose path equals the request output target;
- exact branch/ref and Git blob SHA for the persisted Brain-B output.

The persisted diagnosis content MUST be the Brain-B final bounded artifact content byte-for-byte except for deterministic newline normalization explicitly documented by the proof runner. No semantic editing by Antigravity/ChatGPT/Human is allowed between Brain output and persisted artifact.

## C8 — Interactive transport is not authority

Preferred delivery is an officially supported connector/integration that can persist the final bounded artifact.

If the selected chat surface cannot write the repository, M3B MAY use a temporary human transfer of only:
- the normalized source non-success result; and/or
- Brain B's final bounded diagnosis artifact.

This proof-only transfer:
- MUST NOT include transcript/history/hidden reasoning;
- MUST be measured in bytes where practical;
- MUST be recorded as `HUMAN_BOUNDED_ARTIFACT_TRANSFER`;
- MUST NOT be described as zero-copy automation;
- MUST NOT grant the human/Brain/runner additional execution authority.

## C9 — M3A formal proof remains authoritative

Use the existing pure M3A functions/classes, including:
- `build_replacement_brain_request(...)`;
- `validate_brain_failover_eligibility(...)`;
- `BrainFailoverProof`;
- BrainRequest / BrainResult / BrainCapability / ContinuityState fingerprinting.

M3B MUST produce a valid deterministic `BrainFailoverProof` anchored to the frozen state snapshot and source/replacement request fingerprints.

Do not weaken or special-case M3A validation for the live proof.

## C10 — Replacement-result binding must be mechanically verified

Mechanical proof MUST verify that replacement `BrainResult` matches the replacement request:
- task_id;
- request_id;
- brain_id;
- operation;
- expected output type;
- exact output target path;
- committed/persisted artifact ref;
- exact artifact Git blob SHA;
- output byte bound.

M3A's failover eligibility proof does not by itself prove replacement result persistence, so TASK-027 SHALL verify this at the proof-runner/evidence layer without changing Continuity Core semantics.

## C11 — Evidence hygiene

Persist only bounded deterministic proof evidence. Allowed persisted evidence includes:
- frozen ContinuityState JSON;
- source/replacement BrainRequest JSON;
- source non-success BrainResult JSON;
- replacement BrainCapability JSON;
- BrainFailoverProof JSON;
- replacement SUCCESS BrainResult JSON;
- final diagnosis artifact;
- compact live-proof attestation/evidence manifest;
- RESULT-027.

MUST NOT persist:
- raw chat transcripts;
- hidden reasoning / chain-of-thought;
- screenshots of chat content;
- cookies/session tokens;
- API keys;
- auth headers;
- unrestricted prompt/response dumps.

Every JSON proof artifact SHALL be bounded and deterministic. Existing 16 KiB Continuity objects retain their current limit.

## C12 — Human attestation only for facts that cannot be mechanically observed

Because interactive chat products may not expose callable APIs/session IDs, M3B MAY use a compact human attestation for facts such as:
- two distinct real chat surfaces were used;
- both were fresh/new proof sessions;
- Brain B did not receive Brain A transcript/history;
- no chat-web UI automation was used;
- whether bounded manual artifact transfer was needed.

Human attestation MUST NOT substitute for mechanically verifiable:
- state fingerprint;
- request equivalence;
- capability gate;
- source non-success;
- replacement result identity;
- artifact blob identity;
- proof fingerprint.

## C13 — No core redesign during proof

Expected production Continuity Core changes:

```text
NONE
```

Do NOT modify `src/aios_bridge/continuity/brain.py`, `state.py`, `failover.py`, `usage.py`, Bridge v0.4, providers or runtime executor code merely to make M3B pass.

If the real proof reveals a genuine M3A/M2/M1 contract defect, STOP/FAIL M3B and escalate through a new remediation TASK. Do not move the goalposts inside TASK-027.

A thin task-local proof runner under `scripts/` plus tests is permitted and preferred for deterministic preparation/validation.

## C14 — Authority remains unchanged

M3B grants no execution authority.

- Brain output remains advisory.
- Antigravity remains the current sole implemented Executor.
- Human RUN approval remains mandatory.
- Human FIX approval remains mandatory.
- Human MERGE approval remains mandatory.
- no Brain may execute shell/browser/workspace mutation as Executor authority;
- no automatic Brain fallback/router is introduced;
- no autonomous merge.

## C15 — Subscription-first / zero paid API acceptance path

The acceptance proof SHALL use human-triggered interactive subscription/chat surfaces.

Required acceptance telemetry:

```text
PAID_EXTERNAL_API_CALLS: 0
CHAT_UI_AUTOMATION: NO
TRANSCRIPT_TRANSFERRED: NO
```

Provider/chat token counts SHALL be `UNKNOWN` unless a surface/tool reports them. Do not invent exact token usage.

---

# Primary Brain Architecture Implementation Plan

## AIP-1 — Keep Continuity Core frozen

Treat M1/M2/M3A as the system under test.

Repository inspection should confirm exact current APIs and use them without semantic edits. A core defect discovered during preparation is a proof failure requiring separate remediation.

## AIP-2 — Thin operational proof runner

Preferred bounded helper:

```text
scripts/aios_m3b_cross_brain_proof.py
```

The runner MAY have two deterministic modes:

```text
prepare
verify
```

`prepare` SHOULD:
1. resolve exact current main + TASK/ADR blobs;
2. construct the frozen schema-v1 proof state;
3. construct source BrainRequest;
4. derive replacement BrainRequest using M3A builder;
5. construct replacement BrainCapability from explicit human-selected identity/capability input;
6. validate request equivalence/state anchoring before any live chat interaction;
7. emit bounded runtime input packs without transcripts/secrets.

`verify` SHOULD:
1. parse the normalized source `INCOMPLETE` BrainResult;
2. run `validate_brain_failover_eligibility(...)`;
3. validate replacement output/result identity and output contract;
4. bind the exact persisted Brain-B diagnosis artifact blob;
5. serialize/fingerprint the BrainFailoverProof;
6. write compact final proof evidence artifacts and summary.

The runner MUST NOT invoke a chat/model, automate a chat UI, choose/rank vendors, authorize RUN/FIX/MERGE, or write secrets.

## AIP-3 — Stable pre-execution state anchor

Use a proof-local frozen state representing the stable TASK-027 pre-execution boundary rather than whatever stale contents happen to exist in `.ai/state/CURRENT-STATE.json`.

The runner must derive the state from exact refs and then serialize it through `ContinuityState`, never by hand-assembling an unchecked fingerprint.

## AIP-4 — Context pack is content-addressed and identical

Resolve a small ordered context set sufficient for the DIAGNOSIS objective, expected to include at least:
- TASK-027;
- ADR-016;
- ADR-010;
- ADR-017;
- only directly needed M3A/M2 contract references if the bounded task requires them.

Every ContextRef must carry its exact blob SHA.

Brain A and Brain B receive the same ordered canonical content identities. Presentation wrappers may differ only where necessary to show their distinct request_id/brain_id.

## AIP-5 — Live checkpoint 1: source Brain

After deterministic preparation, Antigravity pauses at a human checkpoint.

Human opens/uses the selected Brain A fresh session and provides only its source proof pack.

Brain A returns the controlled normalized non-success result. Human returns only that bounded result to the proof runner/executor.

No transcript is transferred.

## AIP-6 — Eligibility gate before replacement interaction

Before Brain B is triggered, the runner MUST validate:
- source result belongs to source request;
- source status is non-success;
- replacement request is semantically equivalent;
- replacement capability supports DIAGNOSIS;
- canonical state fingerprint matches;
- context refs remain content-addressed;
- source/replacement Brain IDs differ.

If any gate fails, do not trigger Brain B as a continuation of this proof.

## AIP-7 — Live checkpoint 2: replacement Brain

Human opens/uses Brain B in a fresh session and provides only the replacement proof pack.

Do not provide Brain A transcript/result as reasoning context.

Brain B produces only the bounded final diagnosis artifact/output package required by the runner.

If manual transfer is necessary, transfer only the final bounded artifact/package, not chat history.

## AIP-8 — Mechanical output binding

Persist Brain B's final diagnosis under the exact target path on the authorized task branch (or an explicitly supported control-artifact route).

Compute/resolve the exact Git blob SHA and construct/validate the replacement `BrainResult` pointer.

No semantic edits after Brain B output.

## AIP-9 — Final evidence bundle

Expected final evidence paths MAY include:

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
.ai/results/RESULT-027.md
```

File count may be reduced only if deterministic inspectability and exact fingerprints are preserved. Do not combine artifacts in a way that stores transcripts/raw chat payloads.

## AIP-10 — Proof runner test strategy

If a runner is added, tests SHALL be synthetic/deterministic and MUST NOT invoke real Brains.

Tests should verify:
- valid two-brain proof bundle passes;
- state fingerprint drift fails;
- source SUCCESS fails;
- source/result identity mismatch fails;
- same-Brain pseudo-failover fails;
- replacement capability mismatch/unsupported operation fails;
- context order/blob drift fails;
- replacement result/request ID mismatch fails;
- wrong output path fails;
- wrong artifact blob fails;
- oversized/unknown-field evidence fails where schema applies;
- no transcript/secret fields are accepted in persisted attestation/evidence schema if a schema is introduced.

---

# Controlled Live Proof Protocol

## Phase 0 — Deterministic preparation

Antigravity prepares and validates the frozen state + source/replacement requests + bounded context packs.

Before human interaction it SHALL print/report at minimum:

```text
TASK_ID
STATE_FINGERPRINT
SOURCE_BRAIN_ID
SOURCE_REQUEST_ID
SOURCE_REQUEST_FINGERPRINT
REPLACEMENT_BRAIN_ID
REPLACEMENT_REQUEST_ID
REPLACEMENT_REQUEST_FINGERPRINT
CONTEXT_REF_COUNT
OUTPUT_TARGET
```

## Phase 1 — Brain A controlled non-success

Human triggers Brain A in a fresh session with source pack only.

Expected normalized result semantics:

```text
TASK_ID: TASK-027
REQUEST_ID: <source request id>
BRAIN_ID: <source brain id>
OPERATION: DIAGNOSIS
STATUS: INCOMPLETE
OUTPUT_TYPE: DIAGNOSIS_ARTIFACT
ERROR_CODE: M3B-CONTROLLED-HANDOFF
ARTIFACT_REF: null
EVIDENCE_REF: null
```

This deliberately proves a stable non-success boundary. It does not simulate or claim a provider outage.

## Phase 2 — Failover eligibility proof

Antigravity/runner validates the source result and runs the existing M3A failover validator.

Only after it passes may Phase 3 begin.

## Phase 3 — Brain B real replacement operation

Human triggers Brain B in a fresh session with replacement pack only.

Brain B produces the bounded diagnosis artifact. Its content SHALL demonstrate at least these semantic anchors:
- same canonical state fingerprint is required;
- source/replacement request semantics must remain identical except Brain/request IDs;
- source SUCCESS would block duplicate failover;
- no transcript/hidden reasoning is required for replacement reconstruction;
- capability gate must pass;
- Brain remains advisory and Human RUN/FIX/MERGE authority is unchanged.

## Phase 4 — Mechanical binding and verification

Antigravity/runner persists the output unchanged, resolves its Git blob, constructs/validates the replacement SUCCESS BrainResult, writes the final BrainFailoverProof and proof evidence.

## Phase 5 — RESULT and independent review

RESULT-027 records proof fingerprints/evidence only, not transcripts.

Primary Brain performs ADR-017 Full Semantic Review and Final Independent Audit before `APPROVED`.

---

# Primary Brain Adversarial Checklist

1. Stale `.ai/state/CURRENT-STATE.json` for another task cannot be silently used.
2. State snapshot is built through `ContinuityState` and fingerprint recomputes exactly.
3. Wrong task_id between state/request fails.
4. Wrong/malformed state fingerprint fails.
5. Source/replacement same brain_id fails.
6. Two sessions of the same Brain implementation cannot be misreported as two distinct Brains.
7. Replacement request changes objective -> fail.
8. Replacement request changes operation -> fail.
9. Replacement request changes output target/type -> fail.
10. Replacement context refs reorder -> fail.
11. Replacement context blob differs -> fail.
12. Any required ContextRef without blob SHA -> fail.
13. State authoritative artifact blob and ContextRef blob mismatch -> fail.
14. Replacement capability brain_id mismatch -> fail.
15. Replacement capability missing DIAGNOSIS -> fail.
16. Source SUCCESS -> replacement failover rejected.
17. Source result task/request/brain/operation mismatch -> fail.
18. Controlled source status is recorded honestly as CONTROLLED_INCOMPLETE, not outage/quota evidence.
19. Brain B receives no Brain A transcript/history.
20. Brain B receives no hidden reasoning/CoT.
21. Human transfer contains only bounded result/artifact, never full transcript.
22. Chat browser/UI automation is not used.
23. Replacement output path differs from target -> fail.
24. Replacement result request_id/brain_id/task_id/operation differs -> fail.
25. Persisted diagnosis blob differs from the Brain-B output bytes -> fail.
26. Diagnosis exceeds output bound -> fail.
27. Diagnosis includes secrets/session/auth material -> fail.
28. Proof/evidence JSON contains unknown transcript/raw_prompt/raw_response/cookie/token/session fields -> fail where schema validates them.
29. BrainFailoverProof round-trip/fingerprint deterministic.
30. Changing only source/replacement identity fields yields valid request equivalence.
31. M3A failover tests remain green unchanged.
32. TASK-023 Brain-neutral tests remain green.
33. TASK-025 Canonical State tests remain green.
34. No Continuity Core production changes are made merely to satisfy proof.
35. No provider/router/fallback automation is introduced.
36. No Brain receives shell/browser/workspace execution authority.
37. Human RUN/FIX/MERGE gates remain unchanged.
38. Paid External Brain API calls remain 0 for acceptance proof.
39. Provider/chat token usage remains UNKNOWN unless actually reported.
40. Full Continuity, AIOS Bridge and repository suites remain green.
41. RESULT fingerprints/SHAs point to the exact tested/final evidence.
42. Final Independent Audit reconstructs M3B from final state/evidence rather than trusting earlier review findings.

---

## Executor Detailed Planning Requirement

After explicit `/aios-worker RUN TASK-027`, Antigravity SHALL first inspect the existing M3A API and produce a bounded detailed plan before edits/proof preparation.

The Executor plan MUST identify:
- exact existing M3A functions/classes reused;
- proof-local state construction fields and exact Git refs/blobs;
- chosen thin runner/evidence schema, if any;
- human checkpoint sequence;
- artifact byte-preservation mechanism;
- mechanical replacement-result binding checks;
- deterministic tests;
- stop/escalation behavior if a core defect is found.

Executor MUST NOT reinterpret the locked M3B contract or silently substitute mocks for the real two-chat proof.

---

## Required Tests

Before/after live proof, at minimum:

```text
pytest tests/aios_bridge/continuity/test_failover.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

If a task-local proof runner has tests, run them explicitly as well.

Synthetic tests do not replace the two real human-triggered Brain interactions.

---

## RESULT-027 Manifest

`RESULT-027.md` SHALL include at minimum:

```text
BASE_SHA
IMPLEMENTATION_SHA
PREVIOUS_REVIEW_SHA
CHANGED_FILES
TEST_SUMMARY

M3A_MECHANICS_REGRESSION: PASS/FAIL
M3B_REAL_CROSS_BRAIN_PROOF_COMPLETE: YES/NO
PROOF_MODE: CONTROLLED_INCOMPLETE_SOURCE

STATE_FINGERPRINT
SOURCE_BRAIN_ID
SOURCE_REQUEST_ID
SOURCE_REQUEST_FINGERPRINT
SOURCE_RESULT_STATUS
SOURCE_RESULT_FINGERPRINT
REPLACEMENT_BRAIN_ID
REPLACEMENT_REQUEST_ID
REPLACEMENT_REQUEST_FINGERPRINT
REPLACEMENT_RESULT_STATUS
REPLACEMENT_RESULT_FINGERPRINT
REPLACEMENT_ARTIFACT_PATH
REPLACEMENT_ARTIFACT_REF
REPLACEMENT_ARTIFACT_BLOB_SHA
FAILOVER_PROOF_FINGERPRINT

DISTINCT_REAL_BRAIN_SURFACES_ATTESTED: YES/NO
FRESH_SOURCE_SESSION_ATTESTED: YES/NO
FRESH_REPLACEMENT_SESSION_ATTESTED: YES/NO
TRANSCRIPT_TRANSFERRED: NO
CHAT_UI_AUTOMATION: NO
INTERACTION_TRANSPORT: CONNECTOR | HUMAN_BOUNDED_ARTIFACT_TRANSFER | MIXED
HUMAN_BOUNDED_TRANSFER_BYTES: <integer|UNKNOWN>
SOURCE_BRAIN_TOKEN_USAGE: REPORTED(...) | UNKNOWN
REPLACEMENT_BRAIN_TOKEN_USAGE: REPORTED(...) | UNKNOWN
PAID_EXTERNAL_API_CALLS: 0

CONTINUITY_CORE_CHANGED: NO
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
EXECUTOR_PLAN_OWNER: antigravity
BRAIN_CONTRACT_OWNER: primary-brain
BRAIN_ARCH_IMPLEMENTATION_PLAN: YES
BRAIN_ADVERSARIAL_CHECKLIST: YES
EXECUTOR_RUNS
EXECUTOR_FIX_RUNS
```

Do not invent provider token numbers.

---

## Prohibited Changes

Do NOT:
- automate ChatGPT/Claude/Gemini web UIs;
- require a particular alternate vendor;
- use paid API calls for the acceptance proof;
- persist chat transcripts or hidden reasoning;
- modify M3A/M2/M1 core contracts to make the proof pass;
- add automatic Brain ranking/router/fallback;
- add ExecutorAdapter/Lease/failover work from M4+;
- modify Bridge v0.4 handoff/authorization/publish behavior;
- grant Brain shell/browser/workspace execution authority;
- bypass Human RUN/FIX/MERGE;
- claim natural quota/outage failover when the source was deliberately `INCOMPLETE`.

---

## Acceptance Criteria

TASK-027 / M3B is acceptable only when:

1. one exact canonical state snapshot is used by both Brain requests;
2. two distinct real human-triggered Brain surfaces participate;
3. source Brain produces the controlled valid non-success result;
4. M3A eligibility validates the replacement without semantic/state drift;
5. replacement Brain reconstructs from canonical pack with no source transcript/history;
6. replacement Brain produces a valid bounded diagnosis artifact;
7. replacement SUCCESS BrainResult is mechanically bound to the exact persisted artifact blob;
8. BrainFailoverProof is valid, bounded, deterministic and fingerprinted;
9. persisted evidence contains no transcript/reasoning/secrets/session material;
10. chat-UI automation is not used;
11. paid External Brain API calls = 0;
12. Continuity Core/Bridge/authority semantics remain unchanged;
13. deterministic regression suites are green;
14. Full Semantic Review passes;
15. Final Independent Audit passes before APPROVED.

M3 shall be considered complete only after TASK-027's proof is accepted and the task is explicitly human-authorized for merge.
