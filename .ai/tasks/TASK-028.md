# TASK-028 — Open Multi-Agent Continuity OS M4 Executor-Neutral Contract

## Work Class

`L3 — ARCHITECTURE / HIGH-RISK CONTRACT`

This task follows ADR-017 Uniform Assurance Pipeline.

Primary Brain owns:
- Contract;
- Architecture Implementation Plan;
- Adversarial Checklist;
- Full Semantic Review;
- Final Independent Audit.

Antigravity owns:
- repository inspection;
- detailed implementation plan;
- exact local code choices within this contract;
- code;
- tests;
- self-audit;
- RESULT evidence.

Human remains sole RUN / FIX / MERGE authority.

---

## Baseline

Canonical `main` at authoring:

```text
b4178d283d451054dca51964771053d9e0de2b5c
```

M3B / TASK-027 is merged and M3 is complete.

Authoritative architecture/contracts:
- ADR-010 Open Multi-Agent Continuity OS Architecture Lock;
- ADR-011 Canonical Project State;
- ADR-013 Delta-First Brain Context Budget for FIX reviews;
- ADR-014 Usage & Efficiency Telemetry;
- ADR-017 Uniform Assurance Pipeline;
- ADR-018 AIOS Continuity M4 Executor-Neutral Contract Lock.

ADR-018 exact control blob at authoring:

```text
13d73a4d36a31288c3e55499c90f4dfa56993064
```

Relevant current code boundary:

```text
src/aios_bridge/continuity/
  __init__.py
  brain.py
  errors.py
  failover.py
  state.py
  usage.py
```

There is no canonical Executor-neutral execution module yet.

Existing `usage.ExecutorAction(RUN, FIX)` is telemetry vocabulary only and MUST NOT be treated as the M4 execution authority contract.

---

## Objective

Implement M4 as a **pure, vendor-neutral, transport-neutral Executor contract** that can describe and validate execution intent/result/capability across future Executor implementations without granting any new authority or implementing failover.

The finished M4 boundary must make this architectural statement true:

> Antigravity, Codex, Claude Code, or a future Executor can be represented by the same canonical execution request/result/capability contract; adding another compatible Executor does not require changing Continuity Core semantics.

TASK-028 is a contract/data-model milestone, not an Executor integration milestone.

---

# Primary Brain Contract

## C1 — New sibling contract module only

Introduce:

```text
src/aios_bridge/continuity/executor.py
```

as the canonical M4 Executor-neutral contract.

Expected public types/functions include at minimum:

```text
ExecutionOperation
ExecutionCapability
ExecutionRequest
ExecutionResultStatus
ExecutionResult
ExecutorCapabilities
PreparedExecution
ExecutorAdapter
validate_executor_eligibility(...)
validate_execution_request_against_state(...)
validate_execution_result_against_request(...)
```

Equivalent naming is allowed only when semantic meaning remains obvious and ADR-018 is satisfied.

Do NOT create concrete vendor/product adapters in this task.

---

## C2 — ExecutionOperation is RUN/FIX only

Canonical M4 operation domain:

```text
RUN
FIX
```

Requirements:
- `MERGE` is not representable as a valid Executor operation;
- unknown operation values fail closed;
- parsing enum errors are wrapped as `ContinuityStateValidationError`, not leaked raw `ValueError`;
- canonical serialization uses exact uppercase operation values.

`ExecutionOperation` SHALL be independent of telemetry's `usage.ExecutorAction` so execution core does not depend on usage telemetry.

Regression test SHALL assert the currently intended semantic alignment:

```text
ExecutionOperation.RUN.value == ExecutorAction.RUN.value == "RUN"
ExecutionOperation.FIX.value == ExecutorAction.FIX.value == "FIX"
```

without moving or changing `usage.ExecutorAction`.

---

## C3 — ExecutionRequest schema-v1

`ExecutionRequest` SHALL be an immutable/frozen canonical record representing execution intent, not authorization.

Required identity/anchor fields:
- `schema_version` = existing Continuity schema version;
- `task_id` exact canonical `TASK-<digits>`;
- `request_id` exact canonical bounded lowercase identifier;
- `executor_id` exact canonical bounded actor identifier;
- `operation: ExecutionOperation`;
- `state_fingerprint` exact lowercase 64-hex;
- `target_branch` exact safe canonical Git ref;
- optional `expected_task_head_sha` exact lowercase 40-hex or null if the state boundary has no task-head SHA;
- `work_ref: ArtifactRef` exact content-addressed control/work artifact;
- `context_refs` bounded ordered content-addressed `ArtifactRef` sequence;
- `required_capabilities` bounded deterministic set-like capability sequence;
- `expected_result_path` exact canonical `.ai/results/RESULT-NNN.md` for the active task.

The object MUST support deterministic:
- `to_dict()`;
- canonical JSON serialization;
- `from_dict()`;
- `from_json()`;
- SHA-256 `fingerprint()`.

Unknown fields fail closed.

Serialized/input representation MUST obey `MAX_SERIALIZED_BYTES` (16 KiB).

---

## C4 — ExecutionRequest is never authority

No field may create self-authorization.

Forbidden concepts include:

```text
approved = true
human_approved = true
authorization_token
api_key
cookie
auth_header
session_secret
merge_allowed
```

Do not add a boolean that allows an adapter to decide that Human RUN/FIX authorization exists.

The M4 contract assumes the existing control plane decides whether a request may be presented to an active Executor.

M4 itself SHALL perform zero Bridge authorization reads/writes.

---

## C5 — Exact work_ref role binding

`work_ref` SHALL use existing `ArtifactRef` safety/canonicalization and must be exact content identity.

For:

```text
operation = RUN
```

require exact:

```text
.ai/tasks/TASK-NNN.md
```

for the active task.

For:

```text
operation = FIX
```

require exact:

```text
.ai/reviews/REVIEW-NNN.md
```

for the active task.

Rules:
- no substring matching such as TASK-0280 satisfying TASK-028;
- no case folding;
- no padded/trimmed aliases;
- no task-number integer normalization that aliases `TASK-028` with another representation;
- `ref` and `blob_sha` mandatory and canonical.

A RUN request pointing to a REVIEW and a FIX request pointing to a TASK both fail closed.

---

## C6 — Ordered context refs are content-addressed and collision-safe

`context_refs` are repository artifact pointers, not embedded content.

Every context ref SHALL have exact:
- path;
- Git ref;
- 40-hex blob SHA.

Requirements:
- explicit deterministic sequence types only (`list` / `tuple` or an even narrower documented set);
- reject `set`, generator and arbitrary iterable inputs where ordering can be nondeterministic;
- defensively copy/freeze to tuple;
- preserve order in canonical identity;
- bounded count;
- duplicate exact path rejected;
- `work_ref.path` collision with context refs rejected;
- unsafe/sensitive paths continue to fail under existing path policy.

M4 MUST NOT embed source bodies or whole-repo dumps in ExecutionRequest.

---

## C7 — Canonical state anchoring

Implement pure validation equivalent to:

```python
validate_execution_request_against_state(
    request: ExecutionRequest,
    state: ContinuityState,
) -> None | deterministic proof/value
```

It MUST fail closed unless:
- `request.task_id == state.task_id`;
- `request.state_fingerprint == state.fingerprint()`;
- `request.target_branch == state.task_branch.branch`;
- `request.expected_task_head_sha == state.task_branch.sha` using exact null/SHA semantics;
- RUN `work_ref` equals the authoritative state TASK artifact on path/ref/blob;
- FIX requires `state.artifacts.review is not None` and exact path/ref/blob equality with the authoritative REVIEW;
- any context path overlapping state TASK/PLAN/RESULT/REVIEW/contracts carries the exact authoritative ref/blob;
- no authoritative path collision/ambiguity is accepted.

This validator must be pure:
- no Git reads;
- no filesystem reads;
- no Bridge calls;
- no state mutation.

Do not change `state.py` lifecycle or freshness semantics.

---

## C8 — ExecutionCapability and ExecutorCapabilities

Define a small closed capability vocabulary sufficient for current architecture, expected to include equivalents of:

```text
REPOSITORY_READ
FILESYSTEM_WRITE
SHELL
TEST_EXECUTION
LOCAL_GIT
BROWSER
```

Exact names may vary, but meanings must be deterministic and vendor-neutral.

`ExecutorCapabilities` SHALL be frozen, bounded and strict-schema with at least:
- exact `executor_id`;
- supported `ExecutionOperation` values;
- supported `ExecutionCapability` values;
- `declarative_only = True` invariant;
- optional bounded descriptive capacity metadata only if truly required.

Set-like fields:
- reject duplicate values;
- canonicalize deterministically under one documented ordering rule;
- do not preserve arbitrary caller set iteration order;
- reject unknown enum values with `ContinuityStateValidationError`.

Capability declaration grants zero execution authority.

---

## C9 — Pure executor eligibility gate

Implement:

```python
validate_executor_eligibility(
    request: ExecutionRequest,
    capabilities: ExecutorCapabilities,
) -> None | deterministic proof/value
```

It MUST fail closed on:
- executor ID mismatch;
- operation unsupported;
- any missing required capability;
- non-declarative capability record;
- malformed identity/schema.

It MUST NOT:
- rank executors;
- choose a vendor;
- inspect quota;
- invoke an executor;
- acquire a lease;
- perform fallback;
- authorize RUN/FIX.

This is the M4 capability eligibility primitive that later M10 dispatch may consume.

---

## C10 — PreparedExecution is request binding, not lease

`PreparedExecution` SHALL be a minimal frozen record that can bind adapter preparation to one exact request.

Expected fields:
- schema version;
- task ID;
- request ID;
- executor ID;
- exact canonical `execution_id`;
- exact request fingerprint.

It SHALL be bounded, strict-schema, canonical and fingerprintable if persisted/exchanged.

It MUST NOT contain:
- lease owner/expiry/generation;
- auth tokens;
- vendor session secret;
- shell command bodies;
- dirty workspace snapshot;
- transport credentials.

Tests must explicitly establish:

```text
PreparedExecution != Executor Lease
```

M5 owns lease semantics.

---

## C11 — ExecutionResult schema-v1 and stable-boundary payload matrix

Define closed statuses:

```text
SUCCESS
FAILED
REJECTED
INCOMPLETE
```

`ExecutionResult` required identity:
- schema version;
- task ID;
- request ID;
- executor ID;
- operation;
- status.

Additional fields:
- `implementation_sha` optional by schema but required only for SUCCESS;
- `result_ref: ArtifactRef | None`;
- bounded ordered optional evidence refs;
- bounded `error_code | None`.

SUCCESS invariant:

```text
implementation_sha = exact lowercase 40-hex
result_ref = exact .ai/results/RESULT-NNN.md
result_ref.ref = request.target_branch when bound to request
error_code = null
```

Non-success invariant (`FAILED/REJECTED/INCOMPLETE`):

```text
implementation_sha = null
result_ref = null
error_code = required bounded identifier
```

Optional evidence refs are non-authoritative and must remain bounded/content-addressed.

This task SHALL NOT encode dirty-workspace checkpoint/hot-handoff semantics.

---

## C12 — Mechanical request/result binding

Implement pure validation equivalent to:

```python
validate_execution_result_against_request(
    result: ExecutionResult,
    request: ExecutionRequest,
) -> None | deterministic proof/value
```

Require exact match:
- schema version;
- task ID;
- request ID;
- executor ID;
- operation.

For SUCCESS additionally require:
- exact result path = request.expected_result_path;
- exact result ref = request.target_branch;
- valid implementation SHA;
- no error code;
- output payload matrix exact.

A syntactically valid result from another request/executor/task/operation must fail closed.

No I/O is permitted.

---

## C13 — ExecutorAdapter Protocol

Define a vendor-neutral `typing.Protocol` equivalent to:

```python
class ExecutorAdapter(Protocol):
    @property
    def executor_id(self) -> str: ...

    def capabilities(self) -> ExecutorCapabilities: ...

    def prepare(self, request: ExecutionRequest) -> PreparedExecution: ...

    def collect_result(self, execution_id: str) -> ExecutionResult: ...
```

Protocol-level contract only.

Requirements:
- no vendor branching in Continuity Core;
- no concrete Antigravity/Codex/Claude-Code class in TASK-028;
- no transport implementation;
- no implicit execute/approve/merge method;
- neutral stub adapters in tests only.

Tests must demonstrate `executor-a`, `executor-b`, and a third `executor-c` can conform without modifying core code.

---

## C14 — Serialization, exact-canonical identity and bounded diagnostics

Follow the hardened Continuity conventions established by TASK-023/TASK-025/TASK-026:
- external identity is exact, not accepted after whitespace trimming;
- enum parse failures wrapped as `ContinuityStateValidationError`;
- no raw huge values in exception messages where that could cause unbounded diagnostics;
- input JSON byte size checked before parsing;
- unknown fields rejected;
- bool must not pass as int;
- tuples/list inputs copied and frozen;
- all canonical JSON uses deterministic key ordering/separators;
- fingerprints use SHA-256 over canonical UTF-8 JSON;
- every canonical record remains <=16 KiB.

Do NOT broaden generic helper semantics in `state.py` merely to make executor tests pass.

Prefer small Executor-local exact-canonical wrappers around safe existing validators.

---

## C15 — Preserve architecture boundaries

TASK-028 MUST NOT implement or change:
- Bridge v0.4 behavior;
- Human RUN/FIX/MERGE authority;
- runtime authorization artifacts;
- canonical state lifecycle;
- Brain contract/failover semantics;
- provider/model behavior;
- usage telemetry semantics;
- concrete Executor adapters;
- ExecutionTransport;
- Executor Lease;
- Executor failover;
- hot handoff;
- deterministic dispatch/router;
- concurrent executor mutation.

Antigravity remains the currently proven sole Executor after M4.

M4 only makes future Executors **representable and mechanically validatable**.

---

# Primary Brain Architecture Implementation Plan

This section owns architectural HOW. Antigravity owns repo-heavy exact edit sequencing.

## AIP-1 — Mirror successful Brain-neutral contract shape without coupling roles

Use `brain.py` as a structural reference for:
- frozen dataclasses;
- strict `from_dict/from_json`;
- canonical JSON;
- fingerprints;
- bounded identities/capabilities;
- local exact-canonical wrappers.

Do NOT import Brain request/result types into Executor request/result semantics.

`brain.py` and `executor.py` are sibling contracts.

---

## AIP-2 — Reuse safe state primitives only

Preferred imports from `state.py` where semantically safe:

```text
SCHEMA_VERSION
MAX_SERIALIZED_BYTES
ArtifactRef
ContinuityState
_validate_actor_id
_validate_artifact_path
_validate_safe_git_ref
_validate_exact_hex_sha
```

Use local wrappers to enforce exact raw==canonical behavior.

Do not modify generic state validators unless a genuine locked-state defect is discovered; if so STOP and escalate.

---

## AIP-3 — Keep task-role validation local and exact

Implement one local helper mapping:

```text
RUN -> .ai/tasks/TASK-NNN.md
FIX -> .ai/reviews/REVIEW-NNN.md
```

Do not infer role from arbitrary substrings.

Build expected paths from the exact active task ID.

Expected result path similarly derives exactly:

```text
.ai/results/RESULT-NNN.md
```

---

## AIP-4 — Canonical sequence policy

For ordered context/evidence:
- accept only list/tuple;
- copy to tuple;
- preserve exact order;
- reject duplicate paths.

For set-like capability/operation declarations:
- accept only list/tuple;
- parse to enum values;
- reject duplicates;
- canonicalize to deterministic enum-value order before serialization.

Do not accept set/generator.

This avoids repeating TASK-025's arbitrary-iterable nondeterminism class.

---

## AIP-5 — State validator is separate from object construction

`ExecutionRequest.__post_init__` validates intrinsic request structure only.

`validate_execution_request_against_state()` validates relational facts requiring an actual `ContinuityState`.

Do not make request construction perform repository I/O or silently build state.

This separation keeps the data contract reusable and testable.

---

## AIP-6 — Capability gate has zero selection policy

Eligibility should be a small pure function:

```text
same executor identity?
operation supported?
required capabilities subset?
declarative_only true?
→ eligible
```

No ordering/ranking/scoring/quota logic belongs here.

---

## AIP-7 — Centralize ExecutionResult payload matrix

Use one explicit status/payload validation block rather than scattered success-only checks.

Conceptual:

```text
SUCCESS
  implementation_sha yes
  result_ref yes
  error_code no

FAILED / REJECTED / INCOMPLETE
  implementation_sha no
  result_ref no
  error_code yes
```

Then the request/result binding validator adds relational checks such as exact target path/ref.

---

## AIP-8 — Adapter Protocol contains no transport logic

Protocol resides in `executor.py` but no concrete implementation is added.

Use `typing.Protocol` and optionally `runtime_checkable` only if it improves deterministic structural tests without broad runtime behavior.

Neutral test stubs may return synthetic PreparedExecution/ExecutionResult objects.

No subprocess/network/browser invocation in tests.

---

## AIP-9 — Public exports are additive only

Update:

```text
src/aios_bridge/continuity/__init__.py
```

to expose the M4 public contract.

Do not rename/remove existing exports.

Update module docstring to include M4 only if useful and non-disruptive.

---

## AIP-10 — Tests stay pure and task-local

Primary test file:

```text
tests/aios_bridge/continuity/test_executor.py
```

Tests should construct synthetic `ContinuityState` snapshots and `ArtifactRef` values directly.

No test may:
- call GitHub;
- call models/providers;
- call Bridge commands;
- invoke shell/browser;
- mutate real repo state.

Use `tmp_path` only if absolutely necessary; ideal M4 contract tests require no filesystem at all.

---

# Primary Brain Adversarial Checklist

Antigravity MUST explicitly self-audit these before publishing RESULT.

### Identity / canonicalization
- [ ] ` TASK-028`, `TASK-028 `, `task-028` rejected.
- [ ] padded executor/request/execution IDs rejected.
- [ ] uppercase/malformed/padded 40-hex SHA rejected.
- [ ] uppercase/malformed/padded 64-hex state fingerprint rejected.
- [ ] padded/unsafe branch ref rejected.
- [ ] bool values do not pass integer/bool-sensitive fields.

### Operation / authority
- [ ] RUN and FIX pass.
- [ ] MERGE fails closed.
- [ ] unknown operation fails with ContinuityStateValidationError.
- [ ] no field or Protocol method grants approval/merge authority.
- [ ] no concrete Executor adapter exists in production after task.

### Work artifact role
- [ ] RUN + exact TASK path passes.
- [ ] RUN + REVIEW fails.
- [ ] FIX + exact REVIEW passes.
- [ ] FIX + TASK fails.
- [ ] TASK-0280 substring alias fails for TASK-028.
- [ ] wrong review/task number fails.
- [ ] missing work_ref blob/ref fails.

### Context determinism
- [ ] list/tuple accepted and frozen.
- [ ] set/generator rejected.
- [ ] context order affects canonical identity intentionally.
- [ ] duplicate context path fails.
- [ ] work_ref/context path collision fails.
- [ ] authoritative state path with wrong blob fails.
- [ ] authoritative state path with wrong ref fails.

### State anchoring
- [ ] exact state fingerprint passes.
- [ ] stale/wrong fingerprint fails.
- [ ] wrong task fails.
- [ ] wrong target branch fails.
- [ ] expected task-head SHA exact/null semantics tested.
- [ ] RUN work_ref must equal authoritative TASK.
- [ ] FIX requires authoritative REVIEW and exact ref/blob.
- [ ] path collisions/ambiguity fail closed.

### Capabilities
- [ ] supported RUN/FIX operation set deterministic.
- [ ] duplicate capability fails.
- [ ] set/generator capability input rejected.
- [ ] executor ID mismatch fails.
- [ ] missing required capability fails.
- [ ] declarative_only false fails.
- [ ] unknown capability enum fails with wrapped Continuity error.
- [ ] capability declaration cannot authorize execution.

### PreparedExecution
- [ ] exact request fingerprint binding tested.
- [ ] wrong request fingerprint rejected when validated/constructed.
- [ ] execution ID exact canonical.
- [ ] record contains no lease/secret/transport fields.

### ExecutionResult
- [ ] SUCCESS requires implementation SHA + result_ref.
- [ ] SUCCESS rejects error_code.
- [ ] FAILED requires error_code and rejects implementation_sha/result_ref.
- [ ] REJECTED same.
- [ ] INCOMPLETE same.
- [ ] result task/request/executor/operation drift fails binding.
- [ ] SUCCESS result path must equal request expected result path.
- [ ] SUCCESS result ref must equal request target branch.
- [ ] result for another task fails even if otherwise valid.
- [ ] evidence refs bounded/content-addressed/duplicate-safe.

### Serialization / bounds
- [ ] canonical JSON deterministic across repeated construction.
- [ ] fingerprint deterministic.
- [ ] unknown fields fail in all `from_dict` parsers.
- [ ] malformed JSON wraps error.
- [ ] >16 KiB input JSON rejected before parsing.
- [ ] oversized serialized record rejected.
- [ ] no unbounded/raw huge diagnostic values.

### Adapter neutrality
- [ ] executor-a stub conforms.
- [ ] executor-b stub conforms.
- [ ] executor-c third stub conforms with no Continuity Core modification.
- [ ] no string branching on `antigravity`, `codex`, `claude-code` in production M4 module.
- [ ] no transport/routing/lease/failover behavior exists.

### Regression / scope
- [ ] existing M1/M2/M3 tests green.
- [ ] TASK-027 M3B proof code remains untouched unless import-only compatibility absolutely requires otherwise.
- [ ] `state.py` unchanged.
- [ ] `brain.py` unchanged.
- [ ] `failover.py` unchanged.
- [ ] `usage.py` unchanged.
- [ ] Bridge v0.4 unchanged.
- [ ] providers/runtime executor unchanged.
- [ ] external/model calls = 0.

---

# Expected Implementation Boundary

Expected production delta:

```text
src/aios_bridge/continuity/executor.py        # NEW
src/aios_bridge/continuity/__init__.py        # additive exports
```

Expected test delta:

```text
tests/aios_bridge/continuity/test_executor.py # NEW
```

No other production file is expected.

If Antigravity determines a different production file must change, STOP and explain the locked invariant/repository constraint before widening scope.

---

# Required Test Evidence

At minimum run:

```text
Focused M4 executor tests
Full Continuity suite: tests/aios_bridge/continuity/
Full AIOS Bridge suite: tests/aios_bridge/
Full repository suite: tests/
```

All must be green.

No live Brain/provider/API calls are required.

---

# Required RESULT-028 Manifest

`RESULT-028.md` MUST report at minimum:

```text
STATUS: READY_FOR_REVIEW
BASE_SHA: b4178d283d451054dca51964771053d9e0de2b5c
IMPLEMENTATION_SHA: <tested implementation sha>
PREVIOUS_REVIEW_SHA: NONE

M4_EXECUTOR_NEUTRAL_CONTRACT: PASS|FAIL
EXECUTION_REQUEST_SCHEMA_V1: PASS|FAIL
EXECUTION_RESULT_SCHEMA_V1: PASS|FAIL
EXECUTOR_CAPABILITY_GATE: PASS|FAIL
CANONICAL_STATE_BINDING: PASS|FAIL
REQUEST_RESULT_BINDING: PASS|FAIL
EXECUTOR_ADAPTER_PROTOCOL: PASS|FAIL
THIRD_NEUTRAL_EXECUTOR_STUB: PASS|FAIL

CONCRETE_EXECUTOR_ADAPTERS_ADDED: 0
EXECUTION_TRANSPORT_ADDED: NO
EXECUTOR_LEASE_ADDED: NO
EXECUTOR_FAILOVER_ADDED: NO
DISPATCH_ROUTER_ADDED: NO
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
CANONICAL_STATE_LIFECYCLE_CHANGED: NO
AUTHORITY_WIDENED: NO
LIVE_EXTERNAL_CALLS: 0
PAID_EXTERNAL_API_CALLS: 0

FOCUSED_M4_TESTS: <count/pass>
CONTINUITY_TESTS: <count/pass>
BRIDGE_TESTS: <count/pass>
FULL_REPO_TESTS: <count/pass>
REGRESSIONS: 0

EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 0   # update if fixes occur
```

Test counts are Executor-reported evidence; Primary Brain review may inspect but does not claim independent execution unless it actually runs them.

---

# Acceptance Criteria

TASK-028 is eligible for `APPROVED` only when all are true:

1. ADR-018 is implemented without semantic drift.
2. `executor.py` provides strict bounded deterministic vendor-neutral M4 contracts.
3. ExecutionRequest is canonical-state/content anchored but does not authorize anything.
4. RUN/FIX only; MERGE impossible as Executor operation.
5. work_ref RUN/FIX role/task identity is exact.
6. context refs are content-addressed, bounded, deterministic and collision-safe.
7. ExecutorCapabilities is declarative only and capability eligibility is pure.
8. PreparedExecution does not become a lease.
9. ExecutionResult stable-boundary payload matrix is strict.
10. request/result binding is exact and fail-closed.
11. ExecutorAdapter Protocol is vendor/transport neutral.
12. a third neutral test Executor can conform without core changes.
13. no concrete alternate Executor is activated.
14. no Bridge/state lifecycle/provider/telemetry/Brain/failover behavior changes.
15. no lease/failover/router/transport is added.
16. focused + Continuity + Bridge + full repo tests pass.
17. Full Semantic Review passes.
18. all findings, if any, are closed through explicit Human FIX cycles.
19. Final Independent Audit passes on the final tested implementation.
20. Human MERGE remains separately required.

---

## Next Milestone

After TASK-028/M4 is merged and independently approved, proceed to:

```text
M5 — Executor Lease
```

M5 will enforce the `MAX_ACTIVE_EXECUTORS_PER_TASK = 1` invariant using M4 execution identities, without redefining ExecutionRequest as authorization.
