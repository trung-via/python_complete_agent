# ADR-022 — M8 Multi-Agent Continuity Proof Contract Lock

STATUS: LOCKED

## Context

ADR-010 defines M8 as the composition milestone after Brain failover (M3) and stable-boundary Executor failover/portability (M6/M7):

> Prove a real task can cross Brain and Executor boundaries while preserving authority and evidence.

M3/M3B already proved stable-boundary Brain failover from one real interactive Brain to another using the same canonical state/request semantics without transcript transfer.

M5/M6/M7 already proved single-active Executor lease, stable-boundary Executor failover, and third-Executor portability across Antigravity, Codex and Claude Code.

M8 MUST NOT redesign either mechanism. Its purpose is composition: prove that both domains can participate in one real task lifecycle and that the evidence chain is causally linked rather than two unrelated proofs stapled together.

Canonical baseline for M8 authoring:

```text
08508e48f6ffda70d1891dad461f6fd1b893b24b
```

---

## Decision 1 — M8 is a composition proof, not a new routing architecture

M8 SHALL reuse existing locked contracts:

- ADR-010 Open Multi-Agent Continuity OS Architecture;
- ADR-011 Canonical Project State;
- ADR-013 Delta-First Brain Context Budget;
- ADR-016 M3 Brain Failover Proof Contract;
- ADR-017 Uniform Assurance Pipeline;
- ADR-018 Executor-Neutral Contract;
- ADR-019 Executor Lease;
- ADR-020 Stable-Boundary Executor Failover;
- ADR-021 Third Executor Portability Proof.

M8 SHALL NOT introduce:

- automatic Brain routing;
- automatic Executor routing;
- quota polling;
- hot/dirty-workspace handoff;
- checkpoint transfer;
- concurrent Executors;
- autonomous RUN/FIX/MERGE;
- chat UI automation;
- paid API calls as the acceptance path.

---

## Decision 2 — One shared stable boundary is mandatory

The composition proof SHALL use one exact Bridge-published task boundary `S0` produced by the initial Executor.

The Brain failover proof and the later Executor failover MUST both anchor to that same stable task state.

At minimum, the M8 proof snapshot SHALL bind:

```text
task_id
base_main_sha
task_branch
source_executor_published_sha = S0
source_result_blob_sha
TASK blob sha
canonical state fingerprint
```

The proof MUST fail if the Brain proof was prepared against one task head while the Executor failover uses another.

---

## Decision 3 — Brain failover remains advisory and transcript-free

M8 SHALL reuse the existing M3/M3B Brain failover primitives and semantics.

A Human explicitly selects two distinct real interactive Brain surfaces:

```text
SOURCE_BRAIN_ID
REPLACEMENT_BRAIN_ID
```

The source Brain SHALL end in a controlled normalized non-success boundary for one bounded advisory operation.

The replacement Brain SHALL reconstruct from canonical state/context only and produce a bounded successful artifact.

No transcript, hidden reasoning, prompt history, cookies, session state or chat-memory dump may cross the Brain boundary.

A bounded human artifact transfer is permitted only if the selected interactive surface cannot persist the artifact directly. If used, it must be explicitly measured/attested and MUST NOT be described as zero-copy automation.

---

## Decision 4 — Cross-domain causal binding is mandatory

M8 is NOT satisfied merely because a Brain failover proof and an Executor failover proof both exist.

The successful replacement-Brain artifact MUST causally bind the later Executor transition through the authoritative REVIEW artifact.

The authoritative REVIEW that gates the Executor FIX SHALL contain an immutable machine-readable M8 provenance block containing at minimum:

```text
M8_SOURCE_EXECUTOR_PUBLISHED_SHA: <S0>
M8_BRAIN_SOURCE_ID: <source brain>
M8_BRAIN_REPLACEMENT_ID: <replacement brain>
M8_BRAIN_FAILOVER_PROOF_FINGERPRINT: <exact fingerprint>
M8_BRAIN_SUCCESS_ARTIFACT_PATH: <path>
M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA: <exact blob sha>
M8_CANONICAL_STATE_FINGERPRINT: <exact fingerprint>
```

The later M6/M7 stable Executor failover proof MUST anchor the exact blob SHA of this REVIEW.

Therefore the accepted evidence chain is:

```text
S0 task/result boundary
  -> canonical Brain state/request
  -> BrainFailoverProof
  -> replacement Brain success artifact
  -> exact authoritative REVIEW blob containing Brain proof/artifact anchors
  -> StableExecutorFailoverProof anchored to that REVIEW blob
  -> replacement Executor RESULT publication
```

Any broken link fails M8.

---

## Decision 5 — Exact provenance, never history inference

M8 validators SHALL use exact immutable references only.

They MUST NOT:

- scan arbitrary Git history for a plausible artifact;
- use nearest-match heuristics;
- trust working-tree RESULT/REVIEW text as authority;
- accept an unanchored Brain artifact;
- accept an Executor proof whose review blob differs from the M8 provenance REVIEW;
- infer PASS from actor names alone.

---

## Decision 6 — Executor transition reuses M5/M6/M7 unchanged

The Executor half of M8 SHALL use an already-supported stable-boundary cross-executor FIX.

Recommended acceptance path:

```text
antigravity -> claude-code
```

but any two distinct currently supported runtime Executor IDs are acceptable if explicitly selected by the Human and already valid under M6/M7.

M8 SHALL NOT add a new failover proof type.

The existing exact lease, authorization, source published SHA, review blob, branch/head/remote and proof fingerprint rules remain authoritative.

---

## Decision 7 — No Continuity Core semantic change is expected

M8 is a system-level composition proof over already-proven contracts.

Expected semantic changes to these Continuity Core modules:

```text
NONE
```

Locked core includes at least:

```text
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/failover.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/runtime_lease.py
```

A thin proof-local verifier/runner and tests are allowed.

If M8 reveals a genuine defect in an existing locked contract, STOP and open a separate remediation task instead of changing the contract inside the proof.

---

## Decision 8 — Proof-local composite manifest

M8 MAY persist a compact deterministic proof manifest under a task-local proof directory.

The manifest SHALL reference, not duplicate, canonical artifacts.

It SHOULD contain exact identities/fingerprints for:

```text
TASK/base/S0
canonical state
source/replacement Brain requests/results
BrainFailoverProof
replacement Brain artifact
M8 authoritative REVIEW blob
source/replacement Executor identities
StableExecutorFailoverProof
replacement Executor publication SHA
final test evidence
```

The manifest MUST remain bounded and MUST NOT include transcripts, hidden reasoning or secrets.

---

## Decision 9 — Human authority remains unchanged

Human remains sole authority for:

```text
RUN
FIX
MERGE
explicit Brain selection for the live proof
explicit replacement Executor selection
```

Brains remain advisory/control-artifact producers.

Executors remain workspace mutation/tool agents only under active authorization/lease.

No M8 artifact grants autonomous merge or execution authority.

---

## Decision 10 — Subscription-first acceptance path

The acceptance proof SHALL use interactive/subscription-backed Brain surfaces and currently supported Executor surfaces.

Required telemetry intent:

```text
PAID_EXTERNAL_API_CALLS: 0
CHAT_UI_AUTOMATION: NO
TRANSCRIPT_TRANSFERRED: NO
MAX_ACTIVE_EXECUTORS_PER_TASK: 1
```

If bounded manual Brain artifact transfer is required, record it truthfully rather than claiming zero copy/paste.

---

## Decision 11 — Final approval requires independent composite audit

TASK-level completion SHALL require Primary Brain independent verification of the entire exact chain, not only the latest RESULT.

The final audit MUST verify:

1. shared S0 boundary identity;
2. exact Brain state/request equivalence;
3. valid BrainFailoverProof;
4. exact replacement Brain artifact blob;
5. exact M8 REVIEW provenance block;
6. Executor failover proof anchors that exact REVIEW blob;
7. Executor source published SHA equals S0;
8. replacement Executor publication is canonical;
9. locked Continuity Core unchanged;
10. tests/evidence green and truthful;
11. no automatic routing/hot handoff/fourth-executor leakage;
12. no transcript/secret leakage.

Only then may M8 be marked PASS.

---

## Decision 12 — Review Protocol v2 applies from Round 1

Every semantic finding from the first review round SHALL include:

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

A finding is CLOSED only by its predeclared close conditions.

If a finding survives a repair round, the next review SHALL tighten it into machine-checkable/executable acceptance assertions rather than restating broad prose.

---

## Consequence

M8 proves the architecture's most important continuity claim without adding a router or a new state machine:

```text
one canonical task
+ real Brain failover
+ Brain artifact -> REVIEW causal binding
+ real stable-boundary Executor failover
+ exact immutable provenance
+ human authority preserved
```

This is the prerequisite composition proof before M9 hot local handoff or M10 deterministic dispatch work.