# TASK-030 — Open Multi-Agent Continuity OS M6 Stable-Boundary Executor Failover

## Work Class

`L3 — CONTROL PLANE / MULTI-EXECUTOR / AUTHORITY-SAFETY`

This task follows ADR-017 Uniform Assurance Pipeline.

Primary Brain owns:
- contract;
- Architecture Implementation Plan;
- Adversarial Checklist;
- Full Semantic Review;
- controlled real-proof review gates;
- Final Independent Audit.

Active Executor owns:
- repository inspection;
- detailed implementation plan;
- exact local edit sequencing within this contract;
- code;
- tests;
- self-audit;
- RESULT evidence.

Human remains sole RUN / FIX / MERGE authority and explicitly selects a replacement Executor for failover proof steps.

---

## Baseline

Canonical `main` at authoring:

```text
f36432c953fd84b8a38288f3d8580d2057a15cfc
```

M5 / TASK-029 is merged.

Authoritative architecture/contracts:
- ADR-010 Open Multi-Agent Continuity OS Architecture Lock;
- ADR-011 Canonical Project State;
- ADR-013 Delta-First Brain Context Budget for FIX reviews;
- ADR-014 Usage & Efficiency Telemetry;
- ADR-017 Uniform Assurance Pipeline;
- ADR-018 M4 Executor-Neutral Contract;
- ADR-019 M5 Executor Lease & Single-Active-Executor Lock;
- ADR-020 M6 Stable-Boundary Executor Failover Contract Lock.

ADR-020 exact control blob at authoring:

```text
fbaf062a4d2938ea16b0f70b2dba76401e9396ff
```

Current relevant production boundaries:

```text
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/runtime_lease.py
bridge.py
```

M4 gives vendor-neutral execution identity/contracts.
M5 now enforces one active Executor lease per task/workspace.
M6 must use those primitives rather than weakening or replacing them.

---

# Objective

Implement and prove stable-boundary Executor failover between:

```text
antigravity
codex
```

under the invariant:

```text
MAX_ACTIVE_EXECUTORS_PER_TASK = 1
```

The task is complete only after the repository contains real evidence of both transitions under TASK-030:

```text
Antigravity -> Codex
Codex       -> Antigravity
```

Each transition must happen only after a successful RESULT/publish boundary, exact lease release, CONSUMED source authorization, CHANGES_REQUIRED REVIEW, and new human FIX authorization.

No dirty-workspace/mid-task handoff is allowed.

---

# Primary Brain Contract

## C1 — New executor-failover core is a sibling module

Add:

```text
src/aios_bridge/continuity/executor_failover.py
```

Do not add failover semantics into `executor.py` or `lease.py` merely for convenience.

Expected public symbols:

```text
StableExecutorFailoverProof
validate_stable_executor_failover
```

or equivalently small names preserving ADR-020 semantics.

Additive exports may be added to:

```text
src/aios_bridge/continuity/__init__.py
```

---

## C2 — StableExecutorFailoverProof is immutable, strict and bounded

Required conceptual fields:

```text
schema_version
task_id
target_branch
source_executor_id
source_operation
source_execution_fingerprint
source_lease_fingerprint
source_published_sha
source_result_ref
replacement_executor_id
replacement_operation
replacement_execution_fingerprint
replacement_lease_fingerprint
review_ref
```

Use `ArtifactRef` for source RESULT and REVIEW.
Reuse `ExecutionOperation` from M4.
Reuse `ExecutorLease` from M5 in relational validation.

No mutable nested metadata.
No arbitrary iterable acceptance where ordering/type is ambiguous.
Unknown fields reject.
Canonical serialization/fingerprint must be deterministic and bounded by existing Continuity limits.

---

## C3 — Exact task / role identity

Fail closed unless:

```text
task_id == ^TASK-\d+$ exact case
source_result_ref.path == .ai/results/RESULT-N.md
review_ref.path == .ai/reviews/REVIEW-N.md
```

for the exact same numeric task identity.

Reject aliases/cross-task confusion including:

```text
TASK-0300
RESULT-0300
REVIEW-0300
```

when active task is TASK-030.

---

## C4 — Source and replacement Executors must differ

A failover requires:

```text
source_executor_id != replacement_executor_id
```

Same-executor FIX is valid workflow but is not a failover and must not create a pseudo-failover proof.

Core tests use neutral IDs such as `executor-a`, `executor-b` where vendor identity is irrelevant.

Product IDs belong only in Bridge/proof integration tests.

---

## C5 — Replacement operation is FIX only

M6 stable failover occurs at RESULT -> REVIEW -> FIX boundary.

Therefore:

```text
source_operation in {RUN, FIX}
replacement_operation == FIX
```

A proof claiming replacement RUN must reject.
MERGE remains unrepresentable.

---

## C6 — Immutable Git anchors

Require exact lowercase 40-hex:

```text
source_published_sha
source_result_ref.blob_sha
review_ref.blob_sha
```

`source_result_ref.ref` MUST equal exact `source_published_sha`.
It may not be a floating task branch.

`review_ref.ref` MUST be an immutable exact control commit SHA, not merely `ai-control`.

This proof must survive later branch movement.

---

## C7 — Exact fingerprint domains

Require exact lowercase 64-hex for:

```text
source_execution_fingerprint
source_lease_fingerprint
replacement_execution_fingerprint
replacement_lease_fingerprint
```

Syntactic validity is insufficient: the relational validator must prove the values belong to the supplied source/replacement leases.

---

## C8 — Pure relational validator

Implement a pure function equivalent to:

```python
validate_stable_executor_failover(
    proof,
    *,
    source_lease: ExecutorLease,
    replacement_lease: ExecutorLease,
) -> None
```

It must bind exact equality for:

```text
task_id
source executor
source operation
source execution fingerprint
source lease fingerprint
replacement executor
replacement operation
replacement execution fingerprint
replacement lease fingerprint
```

Also require source and replacement workspace IDs to be exactly equal; M6 is same-workspace stable failover, not cross-machine/distributed migration.

No filesystem / Git / Bridge / model / network I/O.

---

## C9 — Proof is evidence, never authorization

The proof must not contain or imply:

```text
approved
human_approved
merge_allowed
authorization token
API key
cookie/session data
raw local path
PID
TTL/expiry/heartbeat
quota state
shell command
prompt/transcript/hidden reasoning
automatic next executor
```

A valid proof by itself grants zero RUN/FIX/MERGE authority.

---

## C10 — M6 runtime executor set is closed and explicit

At the Bridge integration edge, define the currently implemented runtime Executor IDs equivalent to:

```text
antigravity
codex
```

Human activation may explicitly select only those identities.

Expected CLI shape:

```text
python bridge.py handoff 30 --action fix --executor codex
python bridge.py approve 30 --executor codex
```

Exact parser placement may vary.

Requirements:
- default `antigravity` preserves current behavior;
- unknown/padded/mixed-case arbitrary IDs fail closed;
- no `claude-code` in M6;
- no user-provided arbitrary executor string;
- no automatic selection.

---

## C11 — Initial RUN may use an explicitly selected supported Executor

M6 may allow explicit supported Executor selection for RUN as well as FIX, provided Human RUN authority and M5 lease gating remain unchanged.

However TASK-030 controlled implementation RUN is expected to use Antigravity.

Executor selection must be persisted into the exact M5 authorization/lease and reflected in Bridge context/state output rather than hardcoding Antigravity text.

---

## C12 — Failover classification uses prior CONSUMED authorization

For FIX activation:

1. load prior same-task authorization before overwriting it;
2. if prior executor == selected executor, this is ordinary same-executor FIX;
3. if prior executor != selected executor, treat it as M6 failover candidate and require the complete stable-boundary contract.

Failover candidate requires prior authorization:

```text
status == CONSUMED
published_sha == exact 40-hex
executor_id present and canonical
lease binding fields complete and strict
```

Use existing `reconstruct_expected_executor_lease(prior_auth)` semantics to reconstruct source lease.

Reject failover from prior:

```text
ACTIVE
CANCELLED
missing auth
pre-M5/missing lease fields
malformed published_sha
```

Do not infer source Executor from RESULT prose or chat history.

---

## C13 — Stable branch anchor before replacement acquisition

After existing FIX branch preparation/reconciliation and before replacement lease acquisition, require:

```text
current_branch == expected task branch
git HEAD == prior_auth.published_sha
remote task branch == prior_auth.published_sha
```

Existing branch reconciliation may establish the remote/local equality; still assert the final stable boundary explicitly.

If branch is ahead/diverged/drifted or source published SHA does not match -> fail closed.

No reset/rebase/merge/force push is added.

---

## C14 — No ACTIVE lease at failover boundary

Before acquiring replacement lease:

```text
store.load_active(TASK-N) must be None
```

Valid existing ACTIVE lease -> conflict/fail closed.
Corrupt ACTIVE lease -> integrity failure/fail closed.

Do not auto-release.
Do not call recovery automatically.
Do not inspect PID/heartbeat/time.

Then build the replacement lease using selected replacement executor and normal M5 exact execution fingerprint semantics.

---

## C15 — Source RESULT must be content-addressed at source published commit

Resolve exact source RESULT from:

```text
source commit = prior_auth.published_sha
path          = .ai/results/RESULT-N.md
```

Derive its exact Git blob SHA and construct:

```text
ArtifactRef(
  path=.ai/results/RESULT-N.md,
  ref=<source published SHA>,
  blob_sha=<exact RESULT blob>
)
```

Missing RESULT, wrong task result, malformed Git object, or inability to resolve exact blob -> fail closed.

Do not use current working-tree RESULT as source proof identity.

---

## C16 — REVIEW must be exact CHANGES_REQUIRED control artifact

Current authoritative REVIEW must:

```text
status == CHANGES_REQUIRED
path   == .ai/reviews/REVIEW-N.md
```

Bind it to:

```text
review_ref.ref      = exact fetched control commit SHA
review_ref.blob_sha = exact review blob SHA
```

Do not use floating `ai-control` as canonical proof ref.

If control commit/blob moves before activation completes -> fail closed/retry from fresh control state.

---

## C17 — Replacement activation transaction

For cross-executor FIX use this order:

```text
fetch + validate REVIEW CHANGES_REQUIRED
prepare/reconcile task branch
load prior CONSUMED authorization
reconstruct exact source lease
assert branch == source published SHA
resolve exact source RESULT ArtifactRef
resolve exact immutable REVIEW ArtifactRef
require no ACTIVE lease
build replacement lease
atomic acquire replacement lease
build StableExecutorFailoverProof
validate proof(source lease, replacement lease)
persist replacement ACTIVE authorization + failover evidence
update state/context with selected executor
```

If any step after replacement acquire fails:
- release only the exact replacement lease acquired by this call;
- never touch the source lease;
- report bounded recovery diagnostics if rollback itself is uncertain.

Do not claim successful activation until new auth + new lease + failover proof are all valid.

---

## C18 — Preserve source lease for later relational revalidation

The replacement ACTIVE authorization must retain enough bounded non-secret source evidence to reconstruct the exact source lease at publish time.

Preferred safe shape:

```text
failover_source_lease: <canonical ExecutorLease.to_dict()>
failover_proof: <canonical StableExecutorFailoverProof.to_dict()>
failover_proof_fingerprint: <64hex>
```

This nested source lease is justified M6 transition evidence and remains runtime-local; it must contain only canonical M5 lease fields.

Do not copy the entire old authorization, prompt, terminal output, or runtime path into the new authorization.

---

## C19 — Failover authorization metadata is strict

If any failover marker exists in ACTIVE authorization, publish must treat the activation as failover and require the complete failover field set.

Do NOT allow partial/tampered metadata to fall back to ordinary FIX.

Conversely, ordinary same-executor FIX should contain no pseudo-failover metadata and must retain current behavior.

---

## C20 — Publish revalidates failover before test execution

For failover ACTIVE authorization, before `args.test` or RESULT/worktree mutation:

1. strict reconstruct replacement lease from authorization;
2. `store.require_active(replacement_lease)`;
3. strict parse `failover_source_lease` as `ExecutorLease`;
4. strict parse `failover_proof` as `StableExecutorFailoverProof`;
5. verify `failover_proof_fingerprint` exactly;
6. run pure relational validator against source + replacement leases;
7. verify proof task/branch matches current task/branch;
8. re-fetch/revalidate current control REVIEW and require exact proof review blob/ref identity;
9. reject any malformed/missing/cross-task/cross-executor/cross-review evidence.

Only after all pass may tests execute.

A failover validation failure retains replacement lease and ACTIVE auth fail-closed for inspection/recovery.

---

## C21 — RESULT failover manifest

When publishing under a validated failover authorization, RESULT must report at minimum:

```text
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: <source>
FAILOVER_TO_EXECUTOR: <replacement>
FAILOVER_SOURCE_PUBLISHED_SHA: <40hex>
FAILOVER_PROOF_FINGERPRINT: <64hex>
FAILOVER_REVIEW_BLOB_SHA: <40hex>
```

For ordinary same-executor activation:

```text
EXECUTOR_FAILOVER: NO
```

RESULT must also report the active executor identity for the current run.

Do not include source prompt, source chat, raw runtime path, token/key, Codex credential, or transcript.

---

## C22 — Successful replacement publish uses unchanged M5 release ordering

Keep:

```text
commit
push success
exact replacement lease release
replacement auth CONSUMED + published_sha
state IN_REVIEW
```

Test failure -> replacement lease remains ACTIVE.
Commit failure -> replacement lease remains ACTIVE.
Push failure -> replacement lease remains ACTIVE.

Source lease remains historical and is never reactivated.

---

## C23 — Same-executor FIX remains compatible

Example:

```text
Antigravity RESULT
-> CHANGES_REQUIRED
-> Human FIX selects/defaults antigravity
```

must continue to work without requiring StableExecutorFailoverProof.

M6 must not force every FIX to be a failover.

Likewise, no prior consumed authorization may be rewritten or fabricated merely to classify same-executor FIX.

---

## C24 — Legacy approve path cannot bypass M6

`cmd_approve()` may activate RUN/FIX today.

It must:
- accept/default the same supported executor selector;
- acquire lease for selected executor;
- when selected executor differs from prior consumed executor on REVIEW FIX, apply the same stable-boundary failover validation;
- never create usable cross-executor ACTIVE auth without proof.

If safely sharing one activation helper is feasible, prefer it over duplicated subtly different logic.

Do not redesign all Bridge commands beyond the required boundary.

---

## C25 — Context is executor-neutral

`cmd_context()` must expose selected active executor and bounded failover summary when present.

Any message such as:

```text
"authorized for execution by Antigravity"
```

must become selected-executor-aware where it represents actual runtime truth.

Do not add raw Codex session data or product credentials.

---

## C26 — No automatic Codex launch required

M6 proof may use a human-triggered official Codex client/CLI after Bridge authorizes `executor_id=codex`.

TASK-030 implementation must not block on defining a universal Executor transport layer.

A small integration helper is allowed only if it is bounded, optional and outside Continuity Core.

No browser automation, UI scraping, cookie reuse, unofficial pseudo-API, or paid API substitution.

---

## C27 — Real proof phase A is mandatory

After implementation RUN by Antigravity publishes its first valid RESULT-030, Full Semantic Review evaluates code normally.

Even if implementation is semantically clean, TASK-030 remains incomplete until real failover proof exists.

Primary Brain then issues a controlled REVIEW-030 with:

```text
STATUS: CHANGES_REQUIRED
M6_PROOF_REQUIRED: ANTIGRAVITY_TO_CODEX
```

This is an acceptance-evidence requirement, not a fabricated code defect.

Human then explicitly authorizes FIX for `executor=codex`.

Codex must:
- reconstruct from repo/TASK/ADR/REVIEW/Bridge context;
- run required focused/full tests;
- make only a proof-required delta if no semantic fix is needed;
- publish through Bridge;
- produce RESULT evidence with `FAILOVER_FROM_EXECUTOR=antigravity`, `FAILOVER_TO_EXECUTOR=codex`.

A RESULT-only evidence commit is acceptable if no production change is required and Bridge/test gates pass.

---

## C28 — Real proof phase B is mandatory

After valid proof A is reviewed, TASK-030 still remains incomplete until reverse direction is proven.

Primary Brain issues a second controlled REVIEW-030:

```text
STATUS: CHANGES_REQUIRED
M6_PROOF_REQUIRED: CODEX_TO_ANTIGRAVITY
```

Human explicitly authorizes FIX for `executor=antigravity`.

Antigravity must publish through Bridge and produce RESULT evidence with:

```text
FAILOVER_FROM_EXECUTOR=codex
FAILOVER_TO_EXECUTOR=antigravity
```

Only after both directions are proven and no semantic findings remain may Final Independent Audit return APPROVED.

---

## C29 — Proof rounds must not bypass review semantics

The controlled CHANGES_REQUIRED proof reviews must clearly distinguish:

```text
SEMANTIC_FINDINGS: none|...
M6_PROOF_REQUIRED: <phase>
```

Do not invent fake bugs.

If real semantic findings exist, they take precedence and must be repaired in the same authorized FIX where safe; proof status remains incomplete until valid transition evidence exists.

---

## C30 — No M7/M8/M9/M10 leakage

TASK-030 MUST NOT implement:

```text
claude-code
third Executor
Brain+Executor multi-agent end-to-end proof
dirty-workspace checkpoint handoff
hot handoff
quota polling
availability polling
automatic executor selection
router/scoring/ranking
LLM routing
automatic API fallback
distributed lease backend
parallel task worktrees
autonomous merge
```

---

# Primary Brain Architecture Implementation Plan

## AIP-1 — Add a pure executor-failover module

Model `executor_failover.py` after hardened Continuity patterns proven by `failover.py`, `executor.py`, and `lease.py`:

- frozen dataclass;
- strict exact validators;
- exact role-specific ArtifactRef validation;
- bounded JSON parsing;
- invalid UTF-8 wrapping;
- canonical deterministic fingerprint;
- no I/O.

Do not change M4 or M5 core semantics.

---

## AIP-2 — Keep product names out of Continuity Core

Core tests use neutral executor IDs.

`antigravity` / `codex` exist only at Bridge/integration tests and real proof evidence.

No vendor branch belongs in `executor_failover.py`.

---

## AIP-3 — Centralize runtime executor validation

Add one small Bridge helper for explicit supported executor selection.

Example semantics:

```text
None -> antigravity
antigravity -> antigravity
codex -> codex
anything else -> fail closed
```

No capability ranking or router.

Use the same helper from handoff and legacy approve.

---

## AIP-4 — Centralize FIX activation if practical

Current handoff and approve both create execution-capable authorization.

Avoid two independent M6 implementations if a narrow shared helper can safely perform:

```text
prior auth inspection
stable-boundary validation
lease acquisition
failover proof construction
authorization persistence
```

Do not refactor unrelated Bridge sync/branch/publish behavior merely for aesthetics.

---

## AIP-5 — Derive immutable Git evidence with Git plumbing

Prefer exact Git-object queries for source RESULT at source commit, for example semantic equivalents of:

```text
<source_sha>:.ai/results/RESULT-N.md -> blob SHA
control remote head -> immutable control commit SHA
```

Do not trust working-tree file contents or floating refs as proof identity.

All Git failures fail closed with bounded errors.

---

## AIP-6 — Reuse M5 source-lease reconstruction

Before overwriting prior consumed auth:

```text
source_auth = load prior auth
source_lease = reconstruct_expected_executor_lease(source_auth)
```

Then copy only canonical source lease dict + required proof fields into new replacement auth.

Do not retain unrestricted old authorization JSON.

---

## AIP-7 — Acquire replacement only after all source preconditions

Do as much source/result/review/branch validation as possible before acquiring the replacement lease.

Then:

```text
require no active lease
acquire replacement
build proof
validate proof
save auth
```

If save/proof persistence fails, release only replacement lease.

---

## AIP-8 — Publish treats failover metadata atomically

Implement a helper equivalent to:

```python
validate_failover_authorization_for_publish(auth, expected_replacement_lease, ...)
```

If any failover marker is present, require all fields.

Never silently downgrade a malformed failover auth into ordinary FIX.

Run this before test subprocess.

---

## AIP-9 — Add bounded RESULT evidence, not transcript evidence

Extend RESULT generation only with small executor/failover manifest fields.

Do not dump full proof JSON if fingerprint + selected identity anchors are sufficient for review.

The full proof remains in bounded runtime authorization during active execution; Git history/RESULT carries the audit anchors required for semantic review.

---

## AIP-10 — Preserve M5 failure retention

Do not release replacement lease on:

```text
failover proof validation error
test failure
commit failure
push failure
```

Only successful remote push reaches normal M5 exact release.

---

## AIP-11 — Tests use deterministic fake Git/runtime fixtures

All implementation tests remain offline.

Use temp repos/runtime dirs and deterministic source/replacement identities.

Do not call real Codex in unit/integration test suite.

Real Codex participation is a separate controlled proof stage under human FIX authorization.

---

## AIP-12 — Real proof is stage-gated

Initial Antigravity RUN implements code/tests only.

It must not self-trigger Codex or fabricate real proof evidence.

Initial RESULT must truthfully report:

```text
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

Later proof RESULTs update evidence only when the actual selected Executor/lease/auth/publish chain occurred.

---

# Primary Brain Adversarial Checklist

### Canonical proof
- [ ] strict TASK-N exact case/identity;
- [ ] strict source/replacement actor IDs;
- [ ] same-executor pseudo-failover rejected;
- [ ] replacement RUN rejected;
- [ ] MERGE/unknown operation rejected;
- [ ] exact 40-hex published SHA;
- [ ] exact 64-hex execution/lease fingerprints;
- [ ] RESULT path exact for task;
- [ ] RESULT ref equals source published SHA;
- [ ] REVIEW path exact for task;
- [ ] REVIEW ref is immutable commit SHA;
- [ ] unknown fields rejected;
- [ ] missing fields rejected;
- [ ] invalid UTF-8 wrapped;
- [ ] oversized input rejected before parse;
- [ ] fingerprint stable across round-trip;
- [ ] no authority/secret/TTL/quota/transport fields.

### Relational proof
- [ ] source lease task mismatch rejected;
- [ ] source executor mismatch rejected;
- [ ] source operation mismatch rejected;
- [ ] source execution fingerprint mismatch rejected;
- [ ] random valid source lease fingerprint rejected;
- [ ] replacement executor mismatch rejected;
- [ ] replacement operation mismatch rejected;
- [ ] replacement execution fingerprint mismatch rejected;
- [ ] random valid replacement lease fingerprint rejected;
- [ ] workspace mismatch source vs replacement rejected.

### Executor selection
- [ ] default remains antigravity;
- [ ] explicit antigravity accepted;
- [ ] explicit codex accepted;
- [ ] padded/mixed-case/unknown executor rejected;
- [ ] claude-code rejected in M6;
- [ ] no quota/router selection code.

### Stable source boundary
- [ ] cross-executor FIX with missing prior auth rejected;
- [ ] prior ACTIVE rejected;
- [ ] prior CANCELLED rejected;
- [ ] prior malformed/pre-M5 lease binding rejected;
- [ ] prior CONSUMED without published SHA rejected;
- [ ] branch head != source published SHA rejected;
- [ ] remote/local branch drift remains fail-closed;
- [ ] source RESULT missing rejected;
- [ ] source RESULT wrong task/blob rejected;
- [ ] working-tree RESULT cannot substitute immutable source RESULT;
- [ ] REVIEW not CHANGES_REQUIRED rejected;
- [ ] REVIEW wrong task rejected;
- [ ] REVIEW control commit/blob drift rejected.

### Lease transfer safety
- [ ] any ACTIVE lease blocks replacement acquisition;
- [ ] corrupt ACTIVE lease blocks replacement acquisition;
- [ ] source lease is never force released by M6;
- [ ] replacement lease acquired only after source boundary validates;
- [ ] proof persistence failure releases only exact new replacement lease;
- [ ] rollback cannot remove unrelated/newer lease;
- [ ] `MAX_ACTIVE_EXECUTORS_PER_TASK == 1` remains green.

### Authorization
- [ ] new cross-executor auth contains selected replacement executor;
- [ ] new cross-executor auth contains canonical source lease snapshot only;
- [ ] new cross-executor auth contains strict failover proof + fingerprint;
- [ ] partial failover markers rejected;
- [ ] same-executor FIX contains no pseudo-failover proof;
- [ ] legacy approve cannot bypass failover rules;
- [ ] no human authority widening.

### Publish
- [ ] replacement lease required before tests;
- [ ] source lease snapshot strictly parsed before tests;
- [ ] proof strictly parsed/fingerprint-checked before tests;
- [ ] source/replacement relational validation before tests;
- [ ] current REVIEW exact revalidation before tests;
- [ ] tampered proof blocks test command;
- [ ] missing source snapshot blocks test command;
- [ ] stale/cross-task review blocks test command;
- [ ] test failure retains replacement lease;
- [ ] commit failure retains replacement lease;
- [ ] push failure retains replacement lease;
- [ ] successful push releases exact replacement lease;
- [ ] replacement auth becomes CONSUMED with exact new published SHA;
- [ ] RESULT failover manifest reports bounded exact identities.

### Compatibility / no leakage
- [ ] ordinary Antigravity FIX still works;
- [ ] ordinary Codex FIX can work when it is the same selected executor;
- [ ] RUN/FIX human approval unchanged;
- [ ] MERGE human authority unchanged;
- [ ] no runtime_lease semantic redesign;
- [ ] executor.py unchanged;
- [ ] state.py unchanged;
- [ ] brain.py/failover.py unchanged;
- [ ] no provider/external brain changes;
- [ ] no Claude Code;
- [ ] no hot/dirty handoff;
- [ ] no auto stop/kill;
- [ ] no TTL/heartbeat/steal;
- [ ] no router/quota detection;
- [ ] no paid/live model calls in automated test suite.

### Real proof
- [ ] initial implementation RESULT truthfully marks both real proof directions PENDING;
- [ ] proof A activation uses actual selected `codex` authorization + lease;
- [ ] proof A RESULT says Antigravity -> Codex with exact proof fingerprint;
- [ ] proof A source lease was already released;
- [ ] proof B activation uses actual selected `antigravity` authorization + lease;
- [ ] proof B RESULT says Codex -> Antigravity with exact proof fingerprint;
- [ ] no two active leases existed during either transition;
- [ ] both proof stages were Human FIX authorized;
- [ ] both replacement publishes went through Bridge;
- [ ] no manual transcript/context copy is accepted as canonical proof.

---

# Expected Implementation Boundary

Expected production changes:

```text
NEW     src/aios_bridge/continuity/executor_failover.py
MODIFY  src/aios_bridge/continuity/__init__.py
MODIFY  bridge.py
```

Optional only if clearly justified by reduced duplication:

```text
NEW     src/aios_bridge/<small integration helper>.py
```

Expected tests:

```text
NEW     tests/aios_bridge/continuity/test_executor_failover.py
MODIFY  tests/test_bridge.py
```

No expected semantic changes to:

```text
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/failover.py
src/aios_bridge/external_brain/**
src/providers/**
```

If implementation needs to widen these boundaries, STOP and escalate before code.

---

# Initial Implementation Test Requirements

Before first RESULT-030, Antigravity must run at minimum:

1. focused `test_executor_failover.py`;
2. relevant lease/runtime lease tests proving M5 regression safety;
3. full Bridge test suite;
4. full Continuity test suite;
5. full repository suite.

No real Codex call is required in automated tests.
No paid External Brain/API call is required.

---

# Initial RESULT-030 Required Manifest

Initial RUN RESULT must report at minimum:

```text
TASK_ID: TASK-030
ACTION: RUN
BASE_SHA: f36432c953fd84b8a38288f3d8580d2057a15cfc
IMPLEMENTATION_SHA: <tested sha>
M6_STABLE_EXECUTOR_FAILOVER: IMPLEMENTED
MAX_ACTIVE_EXECUTORS_PER_TASK: 1
SUPPORTED_RUNTIME_EXECUTORS: antigravity,codex
AUTOMATIC_EXECUTOR_ROUTING: NO
HOT_HANDOFF_ADDED: NO
CLAUDE_CODE_ADDED: NO
PAID_EXTERNAL_API_CALLS: 0
LIVE_EXTERNAL_CALLS_AUTOMATED_TESTS: 0
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PENDING
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
FOCUSED_FAILOVER_TESTS: <count/pass>
RUNTIME_LEASE_TESTS: <count/pass>
BRIDGE_TESTS: <count/pass>
CONTINUITY_TESTS: <count/pass>
FULL_REPO_TESTS: <count/pass>
REGRESSIONS: 0
EXECUTOR_ID: antigravity
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 0
```

Do not claim M6 complete in initial RESULT.

---

# Controlled Real Proof Protocol

## Stage 0 — Implementation

Human:

```text
RUN TASK-030 with Antigravity
```

Antigravity implements code/tests and publishes RESULT-030.

Primary Brain performs Full Semantic Review.

If semantic blockers exist, normal CHANGES_REQUIRED takes precedence.
If code is semantically acceptable but proof A is absent, Primary Brain issues controlled `CHANGES_REQUIRED` with:

```text
M6_PROOF_REQUIRED: ANTIGRAVITY_TO_CODEX
SEMANTIC_FINDINGS: NONE
```

---

## Stage A — Antigravity -> Codex

Human explicitly authorizes a FIX activation selecting Codex.

Expected Bridge-level form after implementation:

```text
python bridge.py handoff 30 --action fix --executor codex
```

or equivalent approved wrapper.

Then the human triggers Codex through an official supported Codex surface in the same repository.

Codex must read canonical task/review/context, run required proof/tests, and publish through Bridge.

Stage-A RESULT must contain:

```text
EXECUTOR_ID: codex
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: antigravity
FAILOVER_TO_EXECUTOR: codex
FAILOVER_SOURCE_PUBLISHED_SHA: <exact prior Antigravity published SHA>
FAILOVER_PROOF_FINGERPRINT: <64hex>
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PENDING
```

Primary Brain reviews it.

If proof A is valid and semantic blockers are absent, Primary Brain still issues controlled CHANGES_REQUIRED for proof B:

```text
M6_PROOF_REQUIRED: CODEX_TO_ANTIGRAVITY
SEMANTIC_FINDINGS: NONE
```

---

## Stage B — Codex -> Antigravity

Human explicitly authorizes FIX selecting Antigravity.

Antigravity executes the proof-required FIX and publishes through Bridge.

Stage-B RESULT must contain:

```text
EXECUTOR_ID: antigravity
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: codex
FAILOVER_TO_EXECUTOR: antigravity
FAILOVER_SOURCE_PUBLISHED_SHA: <exact prior Codex published SHA>
FAILOVER_PROOF_FINGERPRINT: <64hex>
M6_REAL_PROOF_ANTIGRAVITY_TO_CODEX: PASS
M6_REAL_PROOF_CODEX_TO_ANTIGRAVITY: PASS
```

Primary Brain then performs:

```text
Full Semantic Review / delta confirmation
-> Final Independent Audit
-> APPROVED only if all code findings closed and both real proof directions verified
```

Human MERGE remains a separate explicit action.

---

# Stop Conditions

STOP and escalate instead of widening scope if any of these become necessary:

- modifying M5 lease atomicity/compare-and-release semantics;
- dirty-workspace transfer;
- automatic process killing;
- quota detection/routing;
- browser automation of Codex/ChatGPT;
- paid API key/token as normal M6 path;
- Claude Code integration;
- distributed lock;
- concurrency >1 active Executor;
- changes to canonical state machine purely to accommodate product-specific behavior.

---

# Definition of Done

TASK-030 is done only when:

```text
M6 contract implemented
+ focused/full tests green
+ all semantic findings closed
+ real Antigravity -> Codex proof PASS
+ real Codex -> Antigravity proof PASS
+ M5 single-active lease invariant preserved
+ no hot handoff/router/third executor leakage
+ Final Independent Audit PASS
+ REVIEW-030 APPROVED
```

Do not merge before explicit Human MERGE authorization.
