# TASK-032 — Open Multi-Agent Continuity OS M8 Real Multi-Agent Continuity Proof

## Work Class

`L3 — CONTROL PLANE / CROSS-DOMAIN CONTINUITY / AUTHORITY-SAFETY`

This task follows the locked Uniform Assurance pipeline and ADR-022.

Primary Brain owns:
- contract;
- Architecture Implementation Plan;
- live Brain-proof gating;
- Review Protocol v2 from Round 1;
- Full Semantic Review;
- controlled cross-domain proof review gates;
- Final Independent Audit.

Active Executor owns:
- repository inspection;
- detailed implementation plan;
- proof-runner/tests within locked scope;
- self-audit;
- execution evidence;
- RESULT publication through existing Bridge authority.

Human remains sole authority for:
- RUN;
- FIX;
- MERGE;
- explicit live Brain selection;
- explicit replacement Executor selection.

---

# Baseline

Canonical `main`:

```text
08508e48f6ffda70d1891dad461f6fd1b893b24b
```

M7 / TASK-031 is APPROVED and merged.

Authoritative architecture/contracts:

```text
ADR-010 — Open Multi-Agent Continuity OS Architecture Lock
ADR-011 — Canonical Project State Contract Lock
ADR-013 — Delta-First Brain Context Budget Lock
ADR-016 — M3 Brain Failover Proof Contract Lock
ADR-017 — Uniform Assurance Pipeline
ADR-018 — M4 Executor-Neutral Contract Lock
ADR-019 — M5 Executor Lease / Single-Active-Executor Lock
ADR-020 — M6 Stable-Boundary Executor Failover Contract Lock
ADR-021 — M7 Third Executor Portability Proof Contract Lock
ADR-022 — M8 Multi-Agent Continuity Proof Contract Lock
```

ADR-022 exact control blob at authoring:

```text
45ddeeec7a497f49cda011f2fd0eb3b3684e0110
```

M8 MUST compose the existing Brain and Executor continuity contracts. It MUST NOT redesign them.

---

# Objective

Prove one real TASK-032 lifecycle can cross both:

```text
Brain boundary
AND
Executor boundary
```

while preserving:

```text
canonical task state
exact artifact provenance
Human RUN/FIX/MERGE authority
single-active Executor ownership
stable-boundary safety
transcript-free Brain continuity
truthful test/evidence reporting
```

The acceptance proof MUST be a causally linked chain, not two independent demonstrations.

The target evidence chain is:

```text
Initial Executor A publishes S0
        ↓
Brain A controlled non-success
        ↓
Brain B reconstructs from same canonical S0 state
        ↓
BrainFailoverProof + Brain B success artifact
        ↓
Primary Brain writes exact REVIEW-032 containing Brain proof/artifact anchors
        ↓
Human explicitly selects Executor B
        ↓
existing M5/M6/M7 stable-boundary Executor failover
        ↓
Executor failover proof anchors exact REVIEW-032 blob
        ↓
Executor B publishes S1
        ↓
Primary Brain verifies complete composite chain
        ↓
Final Independent Audit
```

---

# Locked Contracts

## C1 — One shared source boundary S0

The initial TASK-032 RUN SHALL be published by an explicitly authorized supported Executor, recommended:

```text
antigravity
```

Call the exact Bridge-published commit:

```text
S0
```

Both the Brain proof and later Executor failover MUST anchor to S0.

The Brain proof canonical snapshot SHALL include at minimum:

```text
task_id = TASK-032
base_main_sha = 08508e48f6ffda70d1891dad461f6fd1b893b24b
task_branch = ai/task-032
task_head = S0
source_executor_published_sha = S0
source RESULT blob sha at S0
TASK-032 blob sha
ADR-022 blob sha
canonical state fingerprint
```

If Brain proof state and Executor source publication do not resolve to the same S0, M8 fails.

---

## C2 — Brain operation is bounded and advisory

Use one vendor-neutral advisory operation over the S0 state.

Required logical operation:

```text
operation: DIAGNOSIS
objective: independently diagnose whether S0 is safe and contract-complete for a cross-executor M8 continuation, and identify any invariant that would block the continuation
output_type: DIAGNOSIS_ARTIFACT
```

The successful Brain artifact SHALL be compact and structured as:

```text
CAUSE
EVIDENCE
FIX
TESTS
RISKS
```

It MUST NOT contain:
- hidden reasoning / chain-of-thought;
- source chat transcript;
- secrets;
- auth/session material;
- unrestricted prompt dumps.

---

## C3 — Real Brain boundary

Human SHALL explicitly select two distinct real interactive Brain surfaces:

```text
SOURCE_BRAIN_ID
REPLACEMENT_BRAIN_ID
```

Allowed actor IDs MUST be canonical IDs already compatible with the locked Brain architecture, for example:

```text
chatgpt-chat
claude-chat
gemini-chat
```

Requirements:
- source and replacement differ;
- both are real interactive Brain surfaces;
- no chat-web browser automation;
- no paid API Brain required for acceptance;
- replacement supports the bounded DIAGNOSIS operation.

Do not hard-code provider behavior into Continuity Core.

---

## C4 — Reuse M3/M3B failover semantics exactly

Brain A SHALL produce a controlled normalized non-success result:

```text
status: INCOMPLETE
error_code: M8-CONTROLLED-BRAIN-HANDOFF
```

This MUST be described as a controlled proof boundary, not a real outage/quota event.

Brain B SHALL receive an equivalent replacement request tied to the exact same canonical S0 state fingerprint and ordered context identities.

Only actor/request identity fields permitted by the existing Brain failover contract may differ.

Reuse existing Brain failover primitives and validation. Do not create a new Brain failover type for M8.

---

## C5 — No transcript transfer

Brain B MUST reconstruct from bounded canonical artifacts/context only.

Brain B MUST NOT receive:
- Brain A transcript;
- Brain A hidden reasoning;
- Brain A prompt history;
- screenshots/session cookies;
- chat-memory dump.

If the interactive Brain cannot write the success artifact directly to GitHub/control storage, a bounded Human transfer of only the final normalized artifact is permitted.

If used, record truthfully:

```text
HUMAN_BOUNDED_ARTIFACT_TRANSFER: YES
HUMAN_BOUNDED_ARTIFACT_TRANSFER_BYTES: <actual>
```

Do not claim zero-copy automation when a manual bounded transfer occurred.

---

## C6 — Brain proof artifacts live off the task branch before Executor failover

After S0 is published, the task branch/remote HEAD MUST remain exactly S0 until the cross-executor FIX is authorized.

Therefore Brain proof/control artifacts created between S0 and Executor failover MUST NOT create new commits on `ai/task-032`.

Preferred location:

```text
ai-control:.ai/context/proofs/TASK-032-M8/brain/
```

Allowed proof artifacts include bounded deterministic forms of:

```text
canonical-state.json
source-request.json
source-result.json
replacement-request.json
replacement-capability.json
brain-failover-proof.json
replacement-result.json
BRAIN-DIAGNOSIS.md
brain-proof-attestation.json
```

No transcripts/secrets.

---

## C7 — Brain B output must causally bind the Executor transition

This is the central M8 composition invariant.

After validating Brain B success, Primary Brain SHALL create the authoritative `REVIEW-032.md` on `ai-control`.

That review MUST contain an exact machine-readable provenance block:

```text
M8_SOURCE_EXECUTOR_PUBLISHED_SHA: <S0>
M8_BRAIN_SOURCE_ID: <exact source brain id>
M8_BRAIN_REPLACEMENT_ID: <exact replacement brain id>
M8_BRAIN_FAILOVER_PROOF_FINGERPRINT: <exact fingerprint>
M8_BRAIN_SUCCESS_ARTIFACT_PATH: <exact path>
M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA: <exact blob sha>
M8_CANONICAL_STATE_FINGERPRINT: <exact fingerprint>
```

The REVIEW decision at this gate SHALL be:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF_REQUIRED: YES
APPROVED: NO
```

unless an actual semantic finding is discovered.

Brain B's artifact is advisory evidence. Primary Brain remains responsible for independent validation before publishing the authoritative REVIEW.

---

## C8 — Executor failover reuses M5/M6/M7 unchanged

Human explicitly selects a replacement Executor distinct from Executor A.

Recommended proof path:

```text
antigravity -> claude-code
```

Alternative currently supported cross-executor pairs are allowed if explicitly selected and already valid under M6/M7.

The normal command form is expected to be:

```text
/aios-worker FIX TASK-032 --executor <replacement-executor>
```

Existing stable-boundary failover requirements remain exact:

```text
prior auth strict + CONSUMED
source published SHA == S0
local task HEAD == S0
remote task branch == S0
source RESULT resolves at S0
authoritative REVIEW == CHANGES_REQUIRED
no ACTIVE lease
Human explicitly selected replacement
replacement lease exact
StableExecutorFailoverProof valid
publish revalidates exact lease/proof/review before tests/result/push
```

Do not modify M5/M6/M7 semantics to make M8 pass.

---

## C9 — Executor proof must anchor exact M8 REVIEW blob

The cross-executor StableExecutorFailoverProof/RESULT MUST contain the exact authoritative `REVIEW-032` blob used for activation.

That exact REVIEW blob MUST contain the C7 Brain provenance block.

This creates the required causal chain:

```text
BrainFailoverProof
  -> Brain B artifact blob
  -> exact REVIEW-032 blob
  -> StableExecutorFailoverProof
  -> Executor B publication S1
```

If the REVIEW changes after activation or its blob does not match the executor proof, M8 fails closed.

---

## C10 — Proof A and Proof B terminology

For TASK-032:

```text
M8_BRAIN_PROOF
```
means the real Brain A -> Brain B controlled stable-boundary proof over S0.

```text
M8_EXECUTOR_PROOF
```
means the real Executor A -> Executor B stable-boundary failover from S0 using the exact M8 REVIEW.

```text
M8_COMPOSITE_CHAIN
```
means independent verification that the two proofs are causally linked through the exact artifact/review/proof chain.

No individual worker-authored PASS string is sufficient authority for these states.

---

## C11 — No Continuity Core redesign

Expected semantic changes to the following are:

```text
NONE
```

Locked files:

```text
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/failover.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/runtime_lease.py
```

If a genuine contract defect is discovered, STOP and escalate through a separate remediation task.

---

## C12 — Thin proof-local verifier only

TASK-032 MAY add a thin deterministic verifier/runner, preferred:

```text
scripts/aios_m8_multi_agent_continuity_proof.py
```

It MAY support bounded modes such as:

```text
prepare-brain
verify-brain
verify-composite
```

It MUST NOT:
- invoke a model/chat API;
- automate a chat UI;
- choose/rank Brains or Executors;
- authorize RUN/FIX/MERGE;
- mutate Continuity Core semantics;
- store secrets/transcripts;
- scan history heuristically for evidence.

It SHALL consume exact refs/SHAs supplied by the proof contract or resolved from authoritative current control/task refs.

---

## C13 — Exact proof resolution only

All proof verification MUST use exact immutable references.

Forbidden evidence resolution:

```text
nearest matching commit
latest plausible RESULT
arbitrary history scan
working-tree proof text
actor-name inference
hard-coded expected proof fingerprints
hard-coded test counts
```

Missing or mismatched exact evidence must fail closed.

---

## C14 — Evidence/test claims must be execution-derived

No test PASS count may be hard-coded.

Suite-specific PASS may be reported only when derived from authoritative execution evidence for that suite.

If a full-repo transcript does not prove a sub-suite count, report `UNVERIFIED`/`NOT_RUN` rather than inventing a count.

This invariant applies from Round 1 and is a direct carry-forward of TASK-031 evidence hardening.

---

## C15 — Review Protocol v2 applies from Round 1

Every finding SHALL contain:

```text
FINDING_ID
SEVERITY
ROOT_CAUSE
BROKEN_INVARIANT
REQUIRED_BEHAVIOR
FORBIDDEN_IMPLEMENTATIONS
REQUIRED_TESTS
ADVERSARIAL_TESTS
CLOSE_CONDITIONS
ALLOWED_FILES
FORBIDDEN_SCOPE
```

A finding is CLOSED only when its declared close conditions are mechanically/evidentially satisfied.

If a finding survives one repair round, the next review MUST tighten it into executable/machine-checkable acceptance assertions.

---

## C16 — No M9/M10/M11 leakage

Do not implement:

```text
dirty-workspace hot handoff
checkpoint transfer
parallel worktrees/executors
quota polling
availability polling
smart router/scoring/ranking
automatic Brain selection
automatic Executor selection
automatic failover
LLM routing
autonomous merge
new paid API fallback policy
fourth Executor
```

---

# Primary Brain Architecture Implementation Plan

## AIP-1 — Treat existing continuity contracts as system under test

Do not refactor M3/M5/M6/M7 for elegance during M8.

M8 is primarily proof orchestration and deterministic verification.

## AIP-2 — Add thin M8 proof verifier

Expected implementation delta:

```text
ADD scripts/aios_m8_multi_agent_continuity_proof.py
ADD tests/aios_bridge/continuity/test_m8_multi_agent_proof.py
```

Small helper/test-fixture additions are allowed only if they remain proof-local and do not alter locked core semantics.

No `bridge.py` semantic change is expected merely to perform M8.

## AIP-3 — Prepare exact S0-bound Brain pack

The verifier's prepare mode SHOULD:

1. require current task branch and exact published S0;
2. resolve TASK/ADR/source RESULT exact blobs;
3. build/reuse canonical `ContinuityState` and fingerprint;
4. build source BrainRequest;
5. derive replacement BrainRequest through existing Brain failover primitives;
6. validate equivalence before live Human Brain interaction;
7. emit only bounded proof inputs outside the task branch or for persistence on `ai-control`.

## AIP-4 — Verify Brain proof mechanically

Brain verification SHOULD validate:

```text
source controlled INCOMPLETE
source/replacement request equivalence
same canonical state fingerprint
replacement capability
valid BrainFailoverProof
replacement result identity
exact success artifact path/blob
bounded evidence/no forbidden transcript fields
```

## AIP-5 — REVIEW becomes the cross-domain link

Primary Brain MUST independently review Brain proof and persist the exact C7 provenance block in `REVIEW-032`.

Do not let a worker fabricate this review link.

## AIP-6 — Existing Bridge performs Executor failover

No new Executor handoff mechanism.

Executor B SHALL use the existing task branch, authorization, lease, failover proof and publish path.

If no semantic fix is required, an evidence/result-only Executor-B continuation is acceptable, provided the live failover itself is real and validated.

## AIP-7 — Composite verifier validates causal linkage

After Executor B publication S1, `verify-composite` SHOULD require exact:

```text
S0
Brain proof fingerprint
Brain success artifact blob
M8 REVIEW blob
Executor failover proof fingerprint
Executor source/replacement IDs
S1
```

and prove:

```text
Brain proof state task_head == S0
REVIEW provenance source sha == S0
REVIEW references exact Brain proof/artifact
Executor failover source sha == S0
Executor failover review blob == exact M8 REVIEW blob
Executor replacement publication == S1
```

Any mismatch returns non-zero/fail-closed.

---

# Required Automated Tests

At minimum cover:

1. M8 shared-boundary validator accepts exact S0 chain;
2. Brain state task head != Executor source SHA fails;
3. wrong TASK/ADR/source RESULT blob fails;
4. source/replacement Brain request drift fails;
5. source SUCCESS where controlled non-success is required fails;
6. replacement Brain identity equal to source fails;
7. replacement result/request mismatch fails;
8. missing/mismatched Brain artifact blob fails;
9. transcript/forbidden evidence field is rejected if represented in persisted proof schema;
10. M8 REVIEW missing provenance block fails composite validation;
11. M8 REVIEW Brain proof fingerprint mismatch fails;
12. M8 REVIEW Brain artifact blob mismatch fails;
13. M8 REVIEW source SHA mismatch fails;
14. Executor failover proof review blob mismatch fails;
15. Executor failover source SHA != S0 fails;
16. Executor source == replacement is not accepted as M8 cross-executor proof;
17. unsupported/fourth Executor cannot satisfy M8;
18. forged working-tree RESULT/REVIEW cannot satisfy exact evidence resolution;
19. arbitrary history/nearest-match evidence is not used;
20. locked Continuity Core diff detection fails closed on modifications;
21. git diff command failure in scope validation fails closed;
22. no hard-coded Bridge/Continuity/full-repo PASS counts in M8 evidence path;
23. missing sub-suite evidence yields UNVERIFIED/NOT_RUN, not fabricated PASS;
24. existing M3 Brain failover tests remain green;
25. existing M5/M6/M7 Executor lease/failover tests remain green;
26. full Bridge suite green;
27. full Continuity suite green;
28. full repository suite green;
29. automated tests perform zero live/paid model calls.

Tests MUST use dynamic evidence counts; do not encode the current number of tests as semantic constants.

---

# Expected Implementation Boundary

Expected source additions:

```text
scripts/aios_m8_multi_agent_continuity_proof.py
tests/aios_bridge/continuity/test_m8_multi_agent_proof.py
```

Expected task result:

```text
.ai/results/RESULT-032.md
```

Expected control proof artifacts after S0:

```text
.ai/context/proofs/TASK-032-M8/brain/*
.ai/reviews/REVIEW-032.md
```

No expected semantic changes to Continuity Core or M5/M6/M7 runtime contracts.

If proof execution appears to require a locked core change, STOP rather than widening scope.

---

# Initial RESULT-032 Manifest

The initial Executor-A RUN publication at S0 SHALL report at minimum:

```text
TASK_ID: TASK-032
ACTION: RUN
BASE_SHA: 08508e48f6ffda70d1891dad461f6fd1b893b24b
M8_MULTI_AGENT_CONTINUITY_HARNESS: IMPLEMENTED
M8_SHARED_BOUNDARY_SHA: <S0 after Bridge publication or PENDING_SELF_REFERENCE as appropriate>
M8_BRAIN_PROOF: PENDING
M8_EXECUTOR_PROOF: PENDING
M8_COMPOSITE_CHAIN: PENDING
CONTINUITY_CORE_CHANGED: NO
M5_LEASE_SEMANTICS_CHANGED: NO
M6_FAILOVER_CONTRACT_CHANGED: NO
M7_EXECUTOR_SET_CHANGED: NO
AUTOMATIC_BRAIN_ROUTING: NO
AUTOMATIC_EXECUTOR_ROUTING: NO
HOT_HANDOFF_ADDED: NO
FOURTH_EXECUTOR_ADDED: NO
CHAT_UI_AUTOMATION: NO
PAID_EXTERNAL_API_CALLS: 0
LIVE_EXTERNAL_CALLS_AUTOMATED_TESTS: 0
BRIDGE_TESTS: <execution-derived evidence or NOT_RUN/UNVERIFIED>
CONTINUITY_TESTS: <execution-derived evidence or NOT_RUN/UNVERIFIED>
FULL_REPO_TESTS: <execution-derived evidence>
REGRESSIONS: 0
EXECUTOR_ID: <actual Executor A>
```

These M8 status fields are declarations/evidence summaries, not independent proof authority. Final PASS requires exact artifact verification and Primary Brain Final Independent Audit.

---

# Controlled Real Proof Protocol

## Stage 0 — Executor A implementation / S0 publication

Human authorizes:

```text
/aios-worker RUN TASK-032 --executor antigravity
```

(or equivalent explicit supported Executor A selection).

Executor A:
- implements only the proof-local verifier/tests;
- runs required tests;
- publishes RESULT-032 through Bridge.

The resulting exact published task SHA becomes:

```text
S0
```

Primary Brain performs Full Semantic Review using Review Protocol v2.

If semantic findings exist, they take precedence and are repaired before the live Brain proof.

If semantic review is clean:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M8_BRAIN_PROOF_REQUIRED: YES
APPROVED: NO
```

---

## Stage A — Real Brain A -> Brain B proof over S0

Human explicitly selects:

```text
SOURCE_BRAIN_ID
REPLACEMENT_BRAIN_ID
```

Primary Brain/proof tooling prepares exact S0-bound canonical Brain request/context.

Brain A returns the controlled normalized non-success.

Brain B receives only equivalent bounded canonical context and produces the successful diagnosis artifact.

Proof artifacts are persisted on `ai-control`, not the task branch.

Primary Brain independently validates the Brain proof.

If valid, Primary Brain writes `REVIEW-032.md` with the exact C7 provenance block and decision:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF_REQUIRED: YES
APPROVED: NO
```

Do not start Executor B before this review exists and is authoritative.

---

## Stage B — Real Executor A -> Executor B failover

Human explicitly authorizes a different supported Executor, recommended:

```text
/aios-worker FIX TASK-032 --executor claude-code
```

The existing M6/M7 failover path MUST:

```text
source executor == Executor A
replacement executor == Executor B
source published sha == S0
review blob == exact M8 REVIEW-032 blob
single active lease preserved
StableExecutorFailoverProof valid
```

Executor B runs the composite verifier and required tests, then publishes through Bridge.

Call the resulting exact publication:

```text
S1
```

The post-failover RESULT SHALL expose the existing canonical Executor failover metadata plus truthful M8 evidence, including at minimum:

```text
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: <Executor A>
FAILOVER_TO_EXECUTOR: <Executor B>
FAILOVER_SOURCE_PUBLISHED_SHA: <S0>
FAILOVER_PROOF_FINGERPRINT: <exact>
FAILOVER_REVIEW_BLOB_SHA: <exact M8 REVIEW blob>
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF: PASS
M8_COMPOSITE_CHAIN: <PASS only if exact composite verifier succeeds; otherwise PENDING/FAIL>
```

Worker-authored PASS text alone is never sufficient; Primary Brain must independently verify the exact chain.

---

## Stage C — Final Independent Composite Audit

Primary Brain reviews exact S1 and the complete chain:

```text
baseline
-> TASK/ADR
-> S0
-> Brain canonical state/requests
-> Brain A controlled non-success
-> BrainFailoverProof
-> Brain B artifact blob
-> exact M8 REVIEW blob
-> Executor failover proof
-> S1 RESULT
-> test evidence
```

Final audit MUST verify all ADR-022 close conditions and adversarial invariants.

Only then may REVIEW-032 become:

```text
STATUS: PASS
FULL_SEMANTIC_REVIEW: PASS
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF: PASS
M8_COMPOSITE_CHAIN: PASS
FINAL_INDEPENDENT_AUDIT: PASS
APPROVED: YES
```

Human MERGE remains a separate explicit action.

---

# Adversarial Checklist

M8 MUST fail closed if any of the following occurs:

```text
Brain proof state task_head != S0
Brain source == replacement
Brain request/context drift
source Brain SUCCESS instead of controlled non-success
Brain B receives transcript/history
Brain success artifact path/blob mismatch
M8 REVIEW lacks exact Brain provenance block
M8 REVIEW source SHA != S0
M8 REVIEW proof/artifact fingerprint mismatch
Executor source published SHA != S0
Executor source == replacement
Executor failover review blob != exact M8 REVIEW blob
active lease conflict/corruption
local or remote task branch moved away from S0 before failover
forged working-tree RESULT/REVIEW attempts to claim PASS
arbitrary history scan used as evidence authority
Continuity Core changed
M5/M6/M7 contract weakened
unsupported fourth Executor used
chat UI automation used
paid API substituted as acceptance path
hard-coded test PASS counts used
failed Git scope command treated as clean
```

---

# Round-1 Review Protocol v2 Contract

From the first review, every finding must be written as:

```text
FINDING_ID: ...
SEVERITY: ...
ROOT_CAUSE: ...
BROKEN_INVARIANT: ...
REQUIRED_BEHAVIOR: ...
FORBIDDEN_IMPLEMENTATIONS: ...
REQUIRED_TESTS: ...
ADVERSARIAL_TESTS: ...
CLOSE_CONDITIONS: ...
ALLOWED_FILES: ...
FORBIDDEN_SCOPE: ...
```

Primary Brain MUST define `CLOSE_CONDITIONS` before authorizing a repair.

Antigravity/other Executor does not define its own meaning of "fixed".

A finding surviving a repair round must receive tighter machine-checkable assertions in the next review.

---

# Stop Conditions

STOP and escalate rather than widening TASK-032 if M8 appears to require:

- modifying Brain failover semantics merely for composition;
- modifying Executor lease semantics;
- modifying StableExecutorFailoverProof schema/validation;
- changing canonical state machine semantics;
- dirty-workspace transfer;
- automatic process termination;
- automatic routing/scoring;
- quota/availability polling;
- chat-browser automation;
- paid API keys/tokens as the normal proof path;
- fourth Executor;
- concurrency > 1 active Executor;
- autonomous merge.

---

# Definition of Done

TASK-032 is done only when:

```text
proof-local M8 verifier/tests implemented
+ all semantic findings CLOSED
+ exact S0 stable boundary established
+ real Brain A -> Brain B proof PASS over S0
+ no transcript transfer
+ Brain B artifact exact blob proven
+ authoritative REVIEW-032 contains exact Brain provenance block
+ real Executor A -> Executor B stable-boundary failover PASS from same S0
+ Executor failover proof anchors exact M8 REVIEW blob
+ composite causal chain independently verified
+ Continuity Core unchanged
+ MAX_ACTIVE_EXECUTORS_PER_TASK == 1 preserved
+ no M9/M10/M11 leakage
+ execution-derived test evidence green
+ paid external API calls == 0 for acceptance path
+ Final Independent Audit PASS
+ REVIEW-032 APPROVED
```

Do not merge before explicit Human MERGE authorization.
