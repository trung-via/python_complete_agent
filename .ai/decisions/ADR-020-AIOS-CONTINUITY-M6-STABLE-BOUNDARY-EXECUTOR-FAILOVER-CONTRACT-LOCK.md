# ADR-020 — AIOS Continuity M6 Stable-Boundary Executor Failover Contract Lock

STATUS: LOCKED

## Context

ADR-010 defines Open Multi-Agent Continuity OS and requires Executor continuity to be developed in this order:

1. stable-boundary Executor failover;
2. hot / dirty-workspace handoff only later under a separate contract.

M4 / ADR-018 / TASK-028 established the vendor-neutral Executor contract.
M5 / ADR-019 / TASK-029 established the runtime invariant:

```text
MAX_ACTIVE_EXECUTORS_PER_TASK = 1
```

and now enforces an exact active Executor lease around every current Bridge execution activation.

Canonical `main` after M5 is:

```text
f36432c953fd84b8a38288f3d8580d2057a15cfc
```

The system can therefore safely prevent two Executors from owning mutation authority at the same time, but it still cannot deliberately transfer a task from one Executor identity to another while preserving exact source RESULT / REVIEW / branch / lease evidence.

M6 closes only that gap.

M6 is NOT hot handoff, automatic routing, quota detection, distributed locking, autonomous failover, or parallel execution.

---

## Decision 1 — M6 Scope

M6 SHALL implement and prove **stable-boundary Executor failover** between the first two runtime Executor identities:

```text
antigravity
codex
```

The required real proof for TASK-030 is bidirectional:

```text
Antigravity -> Codex
Codex       -> Antigravity
```

Both transitions must occur at safe RESULT / REVIEW boundaries under the same task branch and the existing human RUN/FIX authority model.

M6 does not add Claude Code. That remains M7.

---

## Decision 2 — Stable Boundary Is Exact, Not Informal

A source execution is considered safely stopped for M6 failover only when all of the following are mechanically true:

1. the source execution successfully published to the remote task branch;
2. its authorization is `CONSUMED`;
3. its exact M5 lease has already been released by successful publish;
4. the source authorization contains a valid `published_sha`;
5. after safe branch reconciliation, local/remote task branch head equals that exact `published_sha`;
6. the source `RESULT-N.md` exists at that published commit and is content-addressed by exact blob SHA;
7. current authoritative `REVIEW-N.md` on the control branch is `CHANGES_REQUIRED` and is content-addressed by exact blob SHA / control commit;
8. no ACTIVE lease currently exists for the task/workspace;
9. worktree is clean under existing Bridge rules.

If any item is unknown, malformed, stale, conflicting, or unavailable, failover MUST fail closed.

A successful test run, local commit, local clean worktree, or human statement alone is not a stable boundary.

---

## Decision 3 — Failover Is a New FIX Activation

M6 failover occurs only as a new authorized `FIX` activation after a reviewed RESULT.

Conceptually:

```text
source Executor RUN/FIX
        |
        v
successful publish
        |
        +-- remote RESULT boundary
        +-- source lease released
        +-- source auth CONSUMED
        |
        v
ChatGPT REVIEW = CHANGES_REQUIRED
        |
        v
Human approves FIX + explicitly selects replacement Executor
        |
        v
validate source stable boundary
        |
        v
acquire replacement lease
        |
        v
persist replacement ACTIVE authorization + failover proof
        |
        v
replacement Executor FIX
```

M6 SHALL NOT transfer a RUN/FIX activation while the source lease remains ACTIVE.

Replacement operation in a failover record is therefore exactly:

```text
FIX
```

The source operation may have been RUN or FIX.

---

## Decision 4 — Explicit Human Executor Selection

M6 authorizes a narrow Bridge integration change allowing the human to explicitly choose the runtime Executor at activation time from the currently implemented set.

Expected shape:

```text
--executor antigravity
--executor codex
```

Rules:

- default remains `antigravity` for backward compatibility;
- selection is explicit/deterministic;
- no quota signal chooses the Executor;
- no model/LLM chooses the Executor;
- no automatic retry changes Executor;
- no availability ranking or router is introduced;
- human RUN approval remains mandatory;
- human FIX approval remains mandatory;
- human MERGE approval remains mandatory.

The legacy `approve` activation path MUST obey the same Executor selection / lease rules and may not bypass M6.

M6 permits Codex as a real runtime Executor identity for the controlled proof. It does not authorize Claude Code or arbitrary user-supplied Executor IDs.

---

## Decision 5 — Interactive/Subscription Executor Surfaces Are Allowed

M6 does not require every Executor to be programmatically launched by Bridge.

A compatible Executor surface MAY be human-triggered, provided:

- Bridge has already created the exact ACTIVE authorization and M5 lease for that Executor identity;
- the Executor works in the authorized repository/task branch;
- the Executor reconstructs its task from repository/control/runtime context rather than prior Executor conversation history;
- publish still goes through Bridge lease/auth/control/test gates.

For the controlled M6 proof, Codex may be entered through an official Codex client/CLI using the user's normal authenticated product access.

Bridge MUST NOT automate a web UI, scrape a chat session, copy cookies, or synthesize an API key to emulate a subscription surface.

Paid external API calls are not required for M6.

---

## Decision 6 — Canonical StableExecutorFailoverProof

Introduce a new vendor-neutral Continuity record, expected in:

```text
src/aios_bridge/continuity/executor_failover.py
```

with an immutable deterministic record equivalent to:

```python
@dataclass(frozen=True)
class StableExecutorFailoverProof:
    schema_version: str
    task_id: str
    target_branch: str

    source_executor_id: str
    source_operation: ExecutionOperation
    source_execution_fingerprint: str
    source_lease_fingerprint: str
    source_published_sha: str
    source_result_ref: ArtifactRef

    replacement_executor_id: str
    replacement_operation: ExecutionOperation
    replacement_execution_fingerprint: str
    replacement_lease_fingerprint: str

    review_ref: ArtifactRef
```

Exact naming may vary slightly, but semantics SHALL remain equivalent.

The proof is an audit/evidence record. It does not itself authorize execution.

---

## Decision 7 — Proof Identity and Role Rules

`StableExecutorFailoverProof` SHALL enforce at minimum:

- exact case-sensitive `TASK-<digits>`;
- source/replacement executor IDs are exact canonical actor IDs;
- source executor != replacement executor;
- source operation is RUN or FIX;
- replacement operation is exactly FIX;
- source/replacement execution fingerprints are exact lowercase SHA-256 hex;
- source/replacement lease fingerprints are exact lowercase SHA-256 hex;
- source published SHA is exact lowercase 40-hex Git SHA;
- target branch is an exact safe Git ref;
- `source_result_ref.path` is exactly `.ai/results/RESULT-N.md` for the same task;
- `source_result_ref.ref` is the exact source published commit SHA, not a floating branch name;
- `review_ref.path` is exactly `.ai/reviews/REVIEW-N.md` for the same task;
- review ref is content-addressed by exact blob SHA and an immutable control commit ref;
- no cross-task alias such as TASK-0300 may satisfy TASK-030;
- unknown fields fail closed;
- invalid UTF-8 and oversized input fail through existing Continuity validation conventions;
- canonical JSON and SHA-256 fingerprint are deterministic.

---

## Decision 8 — Failover Proof Contains No Authority or Transport Secrets

The canonical proof MUST NOT contain:

- `approved` / `human_approved`;
- merge permission;
- authorization token;
- API key;
- cookie/session data;
- raw local filesystem paths;
- process IDs;
- Codex/Antigravity session IDs or transcripts;
- shell command text;
- hidden reasoning;
- quota values;
- TTL/expiry/heartbeat;
- automatic next Executor choice.

The proof records what stable transition was bound; it never grants permission to perform it.

---

## Decision 9 — Pure Relational Validator

M6 SHALL provide a pure validator equivalent to:

```python
validate_stable_executor_failover(
    proof,
    *,
    source_lease: ExecutorLease,
    replacement_lease: ExecutorLease,
) -> None
```

or an equally strong relation primitive.

It MUST mechanically bind:

- task ID;
- source executor / operation / execution fingerprint / lease fingerprint;
- replacement executor / FIX operation / execution fingerprint / lease fingerprint.

It performs no filesystem, Git, Bridge, model, transport, or network I/O.

A proof with a random but syntactically valid lease or execution fingerprint must be rejected against the supplied lease objects.

---

## Decision 10 — Source Authorization Must Be Consumed Before Failover

Bridge may only classify a FIX activation as executor failover when there is a prior same-task authorization record/evidence that is:

```text
status = CONSUMED
published_sha = exact source stable boundary
executor_id = source executor
```

Bridge SHALL reconstruct the source `ExecutorLease` strictly from the prior authorization using the M5 authorization-to-lease rules.

A prior `ACTIVE`, `CANCELLED`, malformed, missing, or pre-M5 authorization is not sufficient evidence for M6 failover.

Ordinary same-executor FIX may continue to work under existing rules without being mislabeled as failover.

---

## Decision 11 — No Active Lease Before Replacement Acquisition

Before failover activation Bridge SHALL strictly inspect the M5 lease store.

Required result:

```text
load_active(TASK-N) is None
```

If a valid ACTIVE lease exists -> fail closed.
If ACTIVE exists but is corrupt -> fail closed.
If lease ownership is uncertain -> fail closed.

M6 MUST NOT call force release, steal, expiry, heartbeat, PID probing, or automatic recovery.

Human recovery remains the M5 explicit `lease-release --confirm-stopped` path.

---

## Decision 12 — Stable Branch Anchor

After existing safe task-branch reconciliation and before acquiring a replacement lease, Bridge SHALL require:

```text
current task branch HEAD == source authorization published_sha
```

and the remote task branch must resolve to the same stable boundary under the existing fail-closed reconciliation rules.

This prevents replacement Executor activation on unreviewed local commits or a branch that has moved since the source RESULT.

No rebase, merge, reset, force-push, or dirty-worktree migration is authorized by M6.

---

## Decision 13 — Exact RESULT / REVIEW Content Addressing

For a failover activation Bridge SHALL derive:

```text
source_result_ref
review_ref
```

from exact immutable Git evidence.

`source_result_ref` must point to the RESULT file as it existed in `source_published_sha`.

`review_ref` must point to the authoritative CHANGES_REQUIRED review at an exact control commit and exact review blob SHA.

Floating branch names alone are not sufficient proof identity.

If RESULT or REVIEW cannot be resolved exactly, fail closed.

---

## Decision 14 — Replacement Activation Transaction

Stable-boundary replacement activation ordering is:

```text
validate REVIEW CHANGES_REQUIRED
-> prepare/reconcile task branch
-> load and validate prior CONSUMED authorization
-> verify branch == source published SHA
-> verify exact source RESULT ref/blob
-> verify no ACTIVE lease
-> build replacement lease for explicit replacement executor
-> atomic acquire replacement lease
-> build + validate StableExecutorFailoverProof
-> persist new ACTIVE authorization containing bounded failover proof metadata
-> expose execution context
```

If any post-acquire persistence step fails, rollback may release only the exact newly-acquired replacement lease.

The source lease is already released and MUST never be touched by replacement rollback.

---

## Decision 15 — Authorization Binds Failover Evidence

When an activation is a real Executor failover, new ACTIVE authorization SHALL persist bounded non-secret failover evidence sufficient for later publish validation, at minimum:

```text
failover_proof
failover_proof_fingerprint
failover_from_executor_id
failover_source_published_sha
```

The full canonical proof may be stored as a bounded nested dict in the runtime authorization, or an equally strict runtime record referenced by fingerprint.

No failover metadata is required for an ordinary same-executor FIX.

---

## Decision 16 — Publish Revalidates Failover Before Tests

For ACTIVE authorizations containing failover evidence, `cmd_publish()` SHALL before any test command / RESULT mutation / commit / push:

1. reconstruct and validate the exact replacement M5 lease as today;
2. parse the `StableExecutorFailoverProof` strictly;
3. verify proof fingerprint;
4. bind proof to reconstructed replacement lease;
5. reconstruct/bind the source lease from the source evidence retained in authorization/proof metadata;
6. revalidate current REVIEW blob/status against control;
7. reject malformed/cross-task/cross-executor/cross-result/cross-review evidence.

A stale or tampered failover proof cannot be treated as ordinary FIX and bypass validation.

---

## Decision 17 — RESULT Carries Bounded Failover Manifest

A publish performed under a failover authorization SHALL add bounded audit evidence to RESULT, equivalent to:

```text
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: antigravity|codex
FAILOVER_TO_EXECUTOR: codex|antigravity
FAILOVER_SOURCE_PUBLISHED_SHA: <40hex>
FAILOVER_PROOF_FINGERPRINT: <64hex>
FAILOVER_REVIEW_BLOB_SHA: <40hex>
```

An ordinary same-executor activation reports:

```text
EXECUTOR_FAILOVER: NO
```

Do not include prompts, transcripts, shell output beyond existing bounded test evidence, raw runtime paths, or secrets.

---

## Decision 18 — Real M6 Proof Is Part of Task Acceptance

TASK-030 is not complete merely because unit/integration tests are green.

It MUST produce real repository evidence for both transitions:

### Proof A

```text
Antigravity source execution
-> successful RESULT / released lease / CONSUMED auth
-> CHANGES_REQUIRED review
-> Human FIX selects codex
-> Codex replacement execution
-> successful RESULT carrying Antigravity -> Codex proof
```

### Proof B

```text
Codex source execution
-> successful RESULT / released lease / CONSUMED auth
-> CHANGES_REQUIRED review
-> Human FIX selects antigravity
-> Antigravity replacement execution
-> successful RESULT carrying Codex -> Antigravity proof
```

A proof-only FIX round may make no production-code change if none is required; a new RESULT/evidence commit plus passing tests is sufficient.

Under ADR-017, ChatGPT SHALL keep review status `CHANGES_REQUIRED` while mandatory M6 proof stages remain incomplete, even if no semantic code defect exists. `CHANGES_REQUIRED` in that case means acceptance evidence is incomplete, not that a fabricated defect exists.

Only after both real transitions are proven may Final Independent Audit produce APPROVED.

---

## Decision 19 — Codex Trigger Does Not Bypass Bridge

For the Codex proof, the user may start Codex through an official supported Codex client/CLI in the authorized repository after Bridge has created the Codex ACTIVE authorization/lease.

Codex must reconstruct from:

- current task branch;
- TASK/ADR;
- REVIEW;
- `python bridge.py context TASK-N` or equivalent bounded Bridge context;
- repository/test evidence.

Codex must still publish through Bridge.

Direct `git push` that bypasses Bridge publish evidence is not accepted as M6 proof.

No browser automation of Codex/ChatGPT UI is part of M6.

---

## Decision 20 — No Hidden Automatic Failover

M6 production code MUST NOT:

- inspect quota and silently select Codex;
- detect Antigravity failure and automatically start Codex;
- retry a failed Executor under another identity;
- auto-release an ACTIVE lease;
- infer source Executor from chat history;
- run two Executors concurrently;
- launch replacement before CHANGES_REQUIRED + Human FIX approval;
- auto-merge.

The transition is explicit, deterministic, human-authorized and evidence-bound.

---

## Decision 21 — M5 Safety Remains Authoritative

M6 narrowly supersedes ADR-019 only where ADR-019 prohibited alternate Executor activation.

The following M5 invariants remain unchanged:

- `MAX_ACTIVE_EXECUTORS_PER_TASK = 1`;
- acquisition uses atomic create-if-absent;
- corruption is occupied/fail-closed;
- exact compare-and-release;
- no TTL/heartbeat/steal;
- publish requires exact ACTIVE authorization + exact ACTIVE lease;
- failed tests/commit/push retain active lease;
- successful push releases exact lease before consuming auth;
- manual recovery requires exact ID + explicit stopped confirmation.

M6 MUST reuse M5 lease semantics; it does not redesign the lease store.

---

## Decision 22 — M4 Core Remains Vendor-Neutral

M6 SHALL NOT add product names to M4 `executor.py` core decisions.

M4 remains authoritative for:

- `ExecutionOperation`;
- `ExecutionRequest` / `ExecutionResult`;
- `ExecutorCapabilities`;
- `PreparedExecution`;
- `ExecutorAdapter` conceptual boundary.

M6 failover core may reference only vendor-neutral actor IDs and existing M4/M5 primitives.

Product identity `antigravity` / `codex` belongs only in integration/proof configuration and task evidence.

---

## Decision 23 — No Transport Redesign in M6

`ExecutorAdapter != ExecutionTransport` remains true.

M6 does not need to define a universal transport protocol or automatically invoke every Executor product.

If a small Codex-specific helper is needed for the controlled proof, it must live outside Continuity Core and must not become a generic router.

A transport-wide abstraction is not required for M6 acceptance.

---

## Decision 24 — Expected Implementation Boundary

Expected production changes are narrowly bounded to:

```text
src/aios_bridge/continuity/executor_failover.py   # new stable-boundary proof contract
src/aios_bridge/continuity/__init__.py            # additive exports
bridge.py                                          # explicit executor selection + failover validation/evidence
```

A small integration-only helper module outside Continuity Core is allowed only if it materially reduces Bridge duplication.

Expected tests:

```text
tests/aios_bridge/continuity/test_executor_failover.py
tests/test_bridge.py
```

`runtime_lease.py` should not require semantic redesign. If a genuine M6 need requires changing its locking/release semantics, STOP and escalate.

No expected changes to:

```text
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/failover.py
src/aios_bridge/external_brain/
src/providers/
Python Agent runtime/provider execution code
```

---

## Decision 25 — Adversarial Acceptance Requirements

Tests/proof must demonstrate at minimum:

1. canonical failover proof round-trip/fingerprint;
2. same-executor pseudo-failover rejected;
3. replacement operation other than FIX rejected;
4. cross-task RESULT/REVIEW aliases rejected;
5. floating/wrong RESULT ref rejected;
6. random valid source/replacement lease fingerprint rejected by relational validator;
7. ACTIVE source authorization cannot fail over;
8. missing/malformed `published_sha` fails closed;
9. branch head drift from source published SHA fails closed;
10. missing/corrupt ACTIVE lease before replacement acquisition is handled according to M5 semantics;
11. replacement cannot acquire while any ACTIVE lease exists;
12. source RESULT missing/wrong blob fails closed;
13. review not CHANGES_REQUIRED fails closed;
14. review blob/control commit drift fails closed;
15. selected replacement executor must be from the implemented M6 set;
16. legacy approve path cannot bypass executor/lease/failover rules;
17. failover proof is validated before tests on publish;
18. malformed/tampered failover proof retains lease and causes no test/commit/push;
19. test/commit/push failure retains replacement lease;
20. successful replacement publish releases replacement lease and consumes replacement auth;
21. same-executor FIX still works and is not mislabeled failover;
22. no TTL/heartbeat/steal/router/quota auto-selection exists;
23. no dirty-workspace handoff exists;
24. real Antigravity -> Codex proof exists;
25. real Codex -> Antigravity proof exists;
26. full existing Continuity/Bridge/repository suites remain green;
27. paid external API calls for M6 proof = 0 unless human explicitly opts into a paid path, in which case it is outside normal M6 acceptance.

---

## Decision 26 — Non-Goals

M6 does NOT implement:

- Claude Code / third Executor (M7);
- full multi-agent cross-Brain+Executor proof (M8);
- dirty-workspace checkpoint handoff (M9);
- quota-aware deterministic dispatch (M10);
- LLM/smart routing;
- automatic API fallback (M11 path remains separate);
- distributed or cloud lock backend;
- concurrent parallel worktrees;
- automatic stop/kill of an Executor process;
- process heartbeat/liveness authority;
- autonomous RUN/FIX/MERGE;
- browser automation of subscription UIs.

---

## Acceptance Criteria

M6 is complete only when all are true:

1. stable-boundary failover has a strict deterministic vendor-neutral canonical proof contract;
2. source boundary requires CONSUMED authorization, released lease, exact published SHA, exact RESULT, exact CHANGES_REQUIRED REVIEW and clean reconciled branch;
3. replacement lease is acquired only after source ownership is absent;
4. explicit human executor selection supports `antigravity` and `codex` without automatic routing;
5. publish revalidates failover proof before tests/mutation;
6. failover RESULT evidence is bounded and content-addressed;
7. same-executor FIX remains compatible;
8. M5 lease safety remains unchanged;
9. no hot handoff / quota router / auto failover / third Executor is introduced;
10. real Antigravity -> Codex stable-boundary transition is proven;
11. real Codex -> Antigravity stable-boundary transition is proven;
12. focused + Continuity + Bridge + full repository suites are green;
13. ADR-017 Full Semantic Review and Final Independent Audit pass after the two real proof stages.

---

## Supersession / Relationship

- ADR-010 remains architecture authority.
- ADR-018 remains M4 Executor-neutral contract authority.
- ADR-019 remains M5 lease authority.
- ADR-020 narrowly supersedes ADR-019 only where M5 prohibited activating an alternate Executor identity; M6 now permits the explicit controlled set `antigravity` + `codex` for stable-boundary execution/failover proof.
- Human RUN/FIX/MERGE authority remains unchanged.
- M7 requires a new ADR before adding a third Executor.
