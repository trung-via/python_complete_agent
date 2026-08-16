# TASK-029 — Open Multi-Agent Continuity OS M5 Executor Lease Enforcement

## Work Class

`L3 — CONTROL PLANE / CONCURRENCY / AUTHORITY-SAFETY`

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
- exact local edit sequencing within this contract;
- code;
- tests;
- self-audit;
- RESULT evidence.

Human remains sole RUN / FIX / MERGE authority.

---

## Baseline

Canonical `main` at authoring:

```text
de556e5065ab1aea08fc832d2541532fe7085e33
```

M4 / TASK-028 is merged.

Authoritative architecture/contracts:
- ADR-010 Open Multi-Agent Continuity OS Architecture Lock;
- ADR-011 Canonical Project State;
- ADR-013 Delta-First Brain Context Budget for FIX reviews;
- ADR-014 Usage & Efficiency Telemetry;
- ADR-017 Uniform Assurance Pipeline;
- ADR-018 M4 Executor-Neutral Contract Lock;
- ADR-019 M5 Executor Lease & Single-Active-Executor Lock.

ADR-019 exact control blob at authoring:

```text
fb2be56d87bb8b7c556270bd9e6e1ff21e74a570
```

Current relevant boundaries:

```text
src/aios_bridge/continuity/executor.py   # M4 neutral execution contract
bridge.py                                # current v0.4 runtime authorization/publish edge
```

Current Bridge runtime paths already live outside the worktree and include auth/state/artifact/history storage. M5 adds lease storage to that external runtime domain.

---

## Objective

Implement M5 as a real fail-closed **single-active-executor lease system** for the current Bridge execution workflow.

After TASK-029, this statement must be mechanically true for the current AIOS runtime workspace:

```text
MAX_ACTIVE_EXECUTORS_PER_TASK = 1
```

A second RUN/FIX activation cannot become usable while another active execution lease owns the task.

The current proven Executor remains Antigravity.

TASK-029 is NOT Executor failover. It establishes the ownership primitive that M6 will later use.

---

# Primary Brain Contract

## C1 — Two-layer M5 implementation

Introduce canonical Continuity lease semantics in:

```text
src/aios_bridge/continuity/lease.py
```

Introduce atomic runtime persistence/enforcement in a narrow module expected at:

```text
src/aios_bridge/runtime_lease.py
```

Update:

```text
src/aios_bridge/continuity/__init__.py
bridge.py
```

only as required for public exports and current Bridge integration.

Do not place atomic file-store implementation inside Continuity Core.

---

## C2 — Explicit invariant

Expose and test:

```python
MAX_ACTIVE_EXECUTORS_PER_TASK = 1
```

M5 MUST NOT provide a configuration option that changes this value.

Parallel Executor mutation is not configurable in this task.

---

## C3 — Canonical ExecutorLease

Implement a strict immutable `ExecutorLease` with at least:

```text
schema_version
lease_id
task_id
workspace_id
executor_id
operation
execution_fingerprint
```

Requirements:
- `schema_version` exact existing Continuity schema version;
- `lease_id` exact bounded lowercase canonical identifier;
- `task_id` exact case-sensitive `TASK-<digits>`;
- `workspace_id` exact lowercase 64-hex SHA-256;
- `executor_id` exact canonical actor ID;
- operation reuses M4 `ExecutionOperation` (`RUN`/`FIX` only);
- `execution_fingerprint` exact lowercase 64-hex SHA-256;
- `@dataclass(frozen=True)` or stronger immutable equivalent;
- strict `to_dict/from_dict/from_json`;
- deterministic canonical JSON;
- deterministic SHA-256 `fingerprint()`;
- serialized/input size <= existing `MAX_SERIALIZED_BYTES`.

Unknown fields fail closed.

Invalid UTF-8 bytes must wrap as `ContinuityStateValidationError`.

No mutable nested metadata is permitted.

---

## C4 — Lease record is ownership, not authorization

ExecutorLease MUST NOT contain:

```text
approved
human_approved
merge_allowed
authorization_token
api_key
cookie
auth_header
session_secret
expires_at
ttl
heartbeat
failover_target
```

Lease ownership does not authorize RUN/FIX by itself.

Bridge still requires existing Human-authorized ACTIVE authorization.

Publish will require BOTH authorization and lease.

---

## C5 — Workspace identity contains no local path

Implement a deterministic workspace fingerprint at the integration/runtime edge.

Expected semantics:

```text
workspace_id = SHA256(normalized current repository/workspace root identity)
```

Exact normalization may reuse the convention already used by `get_runtime_dir()` if safe.

Persist only the 64-hex fingerprint.

No raw `C:\...` / `/home/...` path may appear in ExecutorLease JSON or lease history.

---

## C6 — Deterministic execution fingerprint

Bridge must derive a deterministic `execution_fingerprint` from the exact current activation boundary.

It MUST bind at minimum:

```text
task_id
workspace_id
executor_id
operation
target branch
authorized artifact path
authorized artifact blob SHA
```

Canonical JSON + SHA-256 is preferred.

No timestamp, PID, random value, secret, session transcript or user-local raw path belongs in this fingerprint.

`lease_id` may be independently generated using a safe canonical random identifier because stale-release protection requires distinct activation identity.

---

## C7 — Pure lease binding validator

Provide a pure validator equivalent to:

```python
validate_executor_lease_binding(
    lease: ExecutorLease,
    *,
    task_id: str,
    workspace_id: str,
    executor_id: str,
    operation: ExecutionOperation,
    execution_fingerprint: str,
) -> None
```

or a similarly strong relation primitive.

It must require exact equality of all binding fields.

No filesystem/Git/Bridge/model I/O.

---

## C8 — AtomicExecutorLeaseStore

Runtime enforcement must expose a narrow store equivalent to:

```python
class AtomicExecutorLeaseStore:
    def acquire(self, lease: ExecutorLease) -> ExecutorLease: ...
    def load_active(self, task_id: str) -> ExecutorLease | None: ...
    def require_active(self, expected: ExecutorLease) -> ExecutorLease: ...
    def release(self, expected: ExecutorLease) -> ExecutorLease: ...
```

Store root is explicitly supplied or derived from Bridge runtime paths; do not rely on hidden global current-directory state inside the store.

---

## C9 — Atomic create-if-absent acquisition

Active lease path is conceptually:

```text
<runtime>/leases/TASK-NNN/ACTIVE.json
```

`acquire()` MUST use OS atomic exclusive creation (`os.open(..., O_CREAT | O_EXCL | O_WRONLY, ...)` or equivalent).

The following pattern is prohibited:

```python
if not active_path.exists():
    active_path.write_text(...)
```

Acquisition behavior:
- no active file -> exactly one caller may create lease;
- active valid file -> conflict, fail closed;
- active corrupt/empty/oversized file -> integrity error, fail closed;
- never overwrite an existing active file;
- never auto-steal.

The complete record must be flushed and fsync'd before acquisition returns success where the platform supports it.

If the creator fails while writing its own newly-created file, best-effort cleanup must only target that same file. Uncertain cleanup remains occupied/fail-closed.

---

## C10 — Strict active-file reading

Runtime lease read must:
- bound file byte size before parse;
- require UTF-8;
- use strict ExecutorLease parser;
- require file task namespace and record task ID agree;
- reject wrong workspace identity when checked by Bridge;
- surface deterministic lease/integrity errors without dumping full file content.

`load_active()` may return `None` only when the ACTIVE path truly does not exist.

Existence + corruption != None.

---

## C11 — Compare-and-release

`release(expected)` must:
1. re-read current ACTIVE lease strictly;
2. require exact `lease_id` and lease fingerprint/binding equality with `expected`;
3. refuse stale/wrong release;
4. atomically move/rename the exact active record out of the ACTIVE path, preferably into released history;
5. return the released canonical lease.

A stale old lease must never delete a newer lease.

No force-release primitive may exist in the store API.

---

## C12 — No TTL / heartbeat / steal

M5 production code must not implement:
- lease expiry;
- TTL;
- heartbeat;
- liveness polling;
- PID ownership as authority;
- automatic stale cleanup;
- lease stealing;
- auto replacement Executor.

Time may be used only for non-authoritative human-readable history if already consistent with Bridge conventions; it must not decide active ownership.

---

## C13 — Bridge runtime path integration

Add a lease path to `get_runtime_paths()`, expected:

```text
"leases": rdir / "leases"
```

`ensure_dirs()` must create it.

Lease storage remains outside worktree.

Do not move existing config/seen/inbox/auth/state/artifacts/history paths.

---

## C14 — Current Executor identity remains Antigravity

Bridge M5 integration uses the currently proven Executor identity:

```text
antigravity
```

Do NOT add:

```text
--executor codex
--executor claude-code
```

Do NOT activate alternate adapters or transports.

Vendor-neutrality belongs in lease/executor core; current Bridge integration may identify its current edge as Antigravity.

---

## C15 — Handoff RUN activation ordering

For `cmd_handoff(... RUN ...)`, preserve all existing validation/reconciliation behavior, then enforce:

```text
control artifact validated
→ local main reconciled
→ task branch safely prepared
→ build exact lease candidate
→ atomic lease acquire
→ persist ACTIVE authorization with lease binding
→ update operational state
→ emit context
```

If lease conflict/corruption occurs, no new ACTIVE authorization may be persisted.

If ACTIVE authorization persistence fails after this call created a new lease, rollback by compare-and-release of exactly that lease before returning failure.

Never release somebody else’s lease during rollback.

---

## C16 — Handoff FIX activation ordering

Apply the same lease-before-usable-authorization invariant to `cmd_handoff(... FIX ...)` after existing REVIEW `CHANGES_REQUIRED` and branch checks.

RUN and FIX are both execution activations and both require exclusive ownership.

---

## C17 — Legacy approve path must not bypass lease

`cmd_approve()` currently creates an ACTIVE authorization through a legacy/manual approval path.

It MUST acquire the same task lease before making authorization usable.

No current Bridge command may create an execution-capable ACTIVE authorization without a lease.

Tests must specifically prevent a regression where `cmd_handoff` is protected but `cmd_approve` bypasses M5.

---

## C18 — Authorization binds exact lease

ACTIVE authorization record must add non-secret binding fields sufficient for publish validation:

```text
executor_id
lease_id
lease_fingerprint
workspace_id
execution_fingerprint
```

Existing authorization fields and exact artifact blob semantics remain unchanged.

Do not place the entire lease JSON body in unrelated artifacts if simple binding fields suffice.

---

## C19 — Context exposes lease binding, not secrets

`cmd_context()` should expose enough lease metadata for audit/debugging, at minimum lease ID/fingerprint/executor identity, either through the authorization block already printed or an explicit bounded `lease` summary.

No raw runtime path beyond existing Bridge context behavior needs to be added.

No secret/session token is introduced.

---

## C20 — Publish must require exact active lease before mutation

Before tests, RESULT generation, commit or push, `cmd_publish()` must reconstruct/validate the expected lease from ACTIVE authorization and require the runtime ACTIVE lease to match exactly.

Failure cases before mutation:
- missing lease;
- corrupt lease;
- lease task mismatch;
- workspace mismatch;
- executor mismatch;
- operation mismatch;
- execution fingerprint mismatch;
- lease ID/fingerprint mismatch.

Any failure -> no tests/commit/push from that publish call.

This makes stale authorization alone insufficient.

---

## C21 — Test failure retains lease

If `cmd_publish()` runs tests and tests fail:

```text
ACTIVE authorization remains active under existing behavior
ACTIVE lease remains active
```

This permits the same authorized execution attempt to continue fixing its code.

Do not automatically release on test failure.

---

## C22 — Successful publish release ordering

After successful commit + successful push:

```text
compare-and-release exact lease
→ mark authorization CONSUMED + published SHA/time
→ update state IN_REVIEW
→ print PUBLISHED
```

If exact release fails after push, fail visibly and preserve fail-closed lease state; do not fabricate a free lease.

A subsequent publish with consumed/no authorization must still fail under existing rules.

---

## C23 — Explicit human recovery commands

Add read-only diagnostic command equivalent to:

```text
python bridge.py lease-status [TASK-N]
```

Add explicit safe recovery release equivalent to:

```text
python bridge.py lease-release TASK-N --lease-id <exact-id> --confirm-stopped
```

Recovery release contract:
- must require exact active `lease_id`;
- must require explicit stopped confirmation flag;
- must first make associated ACTIVE authorization non-active/cancelled;
- then exact compare-and-release lease;
- must not start/recommend a replacement automatically inside code;
- must not choose another Executor;
- no force flag.

If authorization deactivation succeeds but release fails, state remains safely non-executable and occupied; surface error for manual inspection.

---

## C24 — No implicit recovery on startup/sync/watch

`setup`, `sync`, `watch`, `pending`, state loading and normal startup MUST NOT auto-release or auto-repair active leases.

An ACTIVE/corrupt lease survives process restarts until safe exact release.

---

## C25 — Preserve Bridge v0.4 semantics outside lease gate

ADR-019 authorizes a Bridge behavior change only for M5 lease enforcement/recovery.

Do not change:
- control branch fetch semantics;
- inbound prefixes;
- TASK/REVIEW blob authorization;
- main reconciliation;
- branch preparation/reconciliation;
- dirty worktree policy;
- no-force-push behavior;
- RESULT formatting except additive bounded lease evidence if useful;
- human approval requirements;
- merge authority;
- watcher semantics;
- provider/runtime Python Agent behavior.

`BRIDGE_V0_4_BEHAVIOR_CHANGED` in RESULT should be reported as:

```text
YES — ADR-019-authorized M5 lease gate only
```

not incorrectly reported as `NO`.

---

## C26 — M4 contract remains unchanged

Do not modify:

```text
src/aios_bridge/continuity/executor.py
```

unless a genuine defect unrelated to M5 is discovered; if so STOP and escalate.

M5 reuses `ExecutionOperation` but does not redesign ExecutionRequest/Result/PreparedExecution.

Tests should prove:

```text
PreparedExecution != ExecutorLease
```

---

## C27 — M6 remains forbidden

TASK-029 MUST NOT implement:
- Executor replacement;
- Antigravity -> Codex handoff;
- Codex -> Antigravity handoff;
- alternate Executor CLI option;
- stable-boundary failover state machine;
- automatic stop/release/acquire sequence;
- quota detection;
- routing;
- hot dirty-workspace handoff;
- distributed lock backend.

M6 requires a new ADR/TASK after M5 merges.

---

# Primary Brain Architecture Implementation Plan

## AIP-1 — Build lease core as sibling of executor.py

`lease.py` should mirror the strict deterministic conventions already proven by `state.py`, `brain.py`, and M4 `executor.py`:
- frozen dataclass;
- local exact-canonical wrappers where needed;
- strict schema;
- bounded from_json bytes;
- invalid UTF-8 wrapping;
- deterministic JSON/fingerprint.

Reuse:

```text
SCHEMA_VERSION
MAX_SERIALIZED_BYTES
ContinuityStateValidationError
ExecutionOperation
```

and safe exact validators from state/executor only where semantics match.

Do not introduce a dependency from executor.py back to lease.py.

---

## AIP-2 — Keep runtime I/O out of Continuity Core

`runtime_lease.py` imports `ExecutorLease` and performs filesystem persistence.

`lease.py` must not import `Path`, subprocess, Git, Bridge or runtime config for ownership I/O.

This preserves vendor-neutral deterministic Continuity Core.

---

## AIP-3 — Atomic store constructor takes explicit root/workspace

Preferred shape:

```python
store = AtomicExecutorLeaseStore(
    lease_root=<Path>,
    workspace_id=<64hex>,
)
```

This makes tests deterministic with `tmp_path` and avoids accidental writes to the real user runtime.

No default constructor should silently discover and mutate the actual production runtime during unit tests.

---

## AIP-4 — Exclusive create is the linearization point

`O_EXCL` successful creation is the acquisition linearization point.

Only one contender can win.

A second contender that receives `FileExistsError` must strictly read/validate the existing lease and raise a deterministic conflict/integrity error; it must not retry by overwriting.

Use a custom narrow error type only if it materially improves caller handling; otherwise `ContinuityStateValidationError`/a small lease-specific subclass is acceptable. Keep exception hierarchy deterministic and bounded.

---

## AIP-5 — Release with exact immutable identity

Build `expected` from the exact authorization-bound lease data rather than from whatever is currently on disk.

Then:

```text
current = strict_read(ACTIVE)
validate exact current == expected/fingerprint
atomic rename ACTIVE -> history unique destination
```

The compare step must happen before removal.

Do not implement `unlink(ACTIVE)` based only on task ID.

---

## AIP-6 — Bridge helper centralizes lease construction

Add one helper that derives:
- workspace ID;
- execution fingerprint;
- random canonical lease ID;
- ExecutorLease(`executor_id="antigravity"`).

Use the same helper semantics for RUN/FIX and legacy approve.

Do not duplicate subtly different fingerprint formulas across three call sites.

---

## AIP-7 — Authorization-to-lease reconstruction is strict

Add one Bridge helper to reconstruct the expected `ExecutorLease` from authorization binding fields.

`cmd_publish()` and recovery/status paths use this exact helper.

Missing/malformed new lease fields in an ACTIVE M5 authorization fail closed.

Historical pre-M5 CONSUMED auth records do not need migration and must not be treated as active leases.

---

## AIP-8 — Activation rollback knows whether it owns newly-created lease

Do not use broad `finally: release(task)` logic.

The activation function should retain the exact lease object only after successful acquisition. If subsequent authorization persistence fails, release exactly that object.

If acquisition failed because another lease exists, no release attempt is allowed.

---

## AIP-9 — Publish checks lease before test command

The active-lease requirement must be before:

```text
args.test subprocess
RESULT write
git add/commit/push
```

so a stale authorization cannot cause even test/tool side effects under the wrong Executor ownership.

Existing control-artifact revalidation may remain before or after lease validation provided neither performs workspace mutation; prefer a clear fail-fast ordering with authorization -> lease -> control artifact -> tests.

---

## AIP-10 — Publish release is only after push success

Do not release immediately after tests or commit.

The safe stable boundary is remote push success.

Push failure leaves lease ACTIVE because ownership remains unresolved and the local branch may still require the same Executor/human to recover.

---

## AIP-11 — Human recovery deactivates auth before release

For `lease-release --confirm-stopped`, order:

```text
strict load active lease
verify exact lease-id
verify confirmation
load ACTIVE auth if any
mark auth non-active/cancelled
compare-and-release exact lease
report release
```

This guarantees that after human declares the Executor stopped, stale authorization cannot publish even if release encounters an error.

Do not delete auth evidence.

---

## AIP-12 — Race proof uses isolated tmp runtime

Add a focused race test with two independent store instances pointed at the same `tmp_path` lease root and same task.

Coordinate start with a barrier/event and assert:

```text
successes == 1
conflicts == 1
final ACTIVE lease == winner
```

No sleeps as correctness mechanism.

Threading is acceptable if it actually exercises independent open/create calls; multiprocessing may be used if stable cross-platform.

---

## AIP-13 — Bridge integration tests stay offline

Extend `tests/test_bridge.py` using existing monkeypatch/temp runtime patterns.

No GitHub/model/API calls.

Tests should mock Git subprocesses only where existing test structure already does so; do not make tests mutate the real repository or real AIOS runtime.

---

# Primary Brain Adversarial Checklist

Antigravity MUST self-audit every item before publishing RESULT.

### Canonical lease identity
- [ ] `MAX_ACTIVE_EXECUTORS_PER_TASK == 1` exactly.
- [ ] padded/lowercase task IDs rejected.
- [ ] padded/uppercase workspace fingerprint rejected.
- [ ] padded/uppercase execution fingerprint rejected.
- [ ] padded/invalid lease/executor IDs rejected.
- [ ] MERGE/unknown operation rejected with Continuity error.
- [ ] unknown fields rejected.
- [ ] invalid UTF-8 wrapped.
- [ ] >16 KiB input rejected before parse.
- [ ] canonical fingerprint stable across round-trip.
- [ ] no mutable nested metadata.

### Authority / secrets
- [ ] lease contains no approval flag.
- [ ] lease contains no TTL/expiry/heartbeat.
- [ ] lease contains no token/cookie/auth header/API key.
- [ ] lease contains no raw local path.
- [ ] lease grants no merge authority.
- [ ] Antigravity remains only runtime Executor.

### Atomic acquisition
- [ ] active path uses O_EXCL/equivalent atomic create.
- [ ] no check-then-write race.
- [ ] first acquisition succeeds.
- [ ] second acquisition fails while first active.
- [ ] independent-store race yields exactly one winner.
- [ ] existing corrupt file blocks acquisition.
- [ ] empty file blocks acquisition.
- [ ] oversized file blocks acquisition.
- [ ] failed writer cleanup cannot delete somebody else’s lease.

### Exact release
- [ ] exact lease release passes.
- [ ] wrong lease_id fails.
- [ ] stale old lease cannot release newer lease.
- [ ] wrong workspace/executor/operation/fingerprint fails.
- [ ] release is compare-and-release, not task-only unlink.
- [ ] released history is non-authoritative.

### Bridge activation
- [ ] RUN handoff acquires before ACTIVE auth usable.
- [ ] FIX handoff acquires before ACTIVE auth usable.
- [ ] legacy approve path also acquires.
- [ ] conflict produces no new ACTIVE auth.
- [ ] newly-acquired lease rolls back if auth persistence fails.
- [ ] rollback never releases pre-existing conflicting lease.
- [ ] context exposes bounded lease binding.

### Publish
- [ ] publish requires ACTIVE auth.
- [ ] publish additionally requires exact ACTIVE lease.
- [ ] missing lease fails before test execution.
- [ ] corrupt/mismatched lease fails before test execution.
- [ ] released lease + stale auth cannot publish.
- [ ] test failure retains lease.
- [ ] commit failure retains lease.
- [ ] push failure retains lease.
- [ ] successful push releases exact lease.
- [ ] successful push then consumes auth.

### Human recovery
- [ ] lease-status is read-only.
- [ ] lease-release without confirmation fails.
- [ ] wrong lease ID fails.
- [ ] recovery deactivates ACTIVE auth before release.
- [ ] recovery does not select/start replacement Executor.
- [ ] no force/steal option exists.

### Scope / no M6 leakage
- [ ] no Codex adapter/invocation.
- [ ] no Claude Code adapter/invocation.
- [ ] no --executor selection option.
- [ ] no automatic failover.
- [ ] no TTL/heartbeat/stale reclaim.
- [ ] no router/quota detection.
- [ ] no dirty-workspace handoff.
- [ ] executor.py unchanged.
- [ ] state.py unchanged.
- [ ] brain.py unchanged.
- [ ] failover.py unchanged.
- [ ] provider/model code unchanged.

### Regression
- [ ] focused lease core tests green.
- [ ] focused runtime lease tests green.
- [ ] Bridge tests green.
- [ ] Continuity tests green.
- [ ] full repository suite green.
- [ ] external/model/API calls = 0.

---

# Expected Implementation Boundary

Expected production delta:

```text
src/aios_bridge/continuity/lease.py           # NEW
src/aios_bridge/continuity/__init__.py        # additive lease exports
src/aios_bridge/runtime_lease.py              # NEW atomic store
bridge.py                                     # M5 integration only
```

Expected test delta:

```text
tests/aios_bridge/continuity/test_lease.py    # NEW
tests/aios_bridge/test_runtime_lease.py       # NEW or equivalent
tests/test_bridge.py                          # MODIFY for activation/publish/recovery integration
```

Do not modify other production boundaries unless a locked invariant makes it unavoidable; STOP and escalate first.

---

# Required Test Evidence

At minimum run:

```text
Focused lease core tests
Focused runtime lease tests
Focused Bridge tests: tests/test_bridge.py
Full Continuity suite: tests/aios_bridge/continuity/
Full AIOS Bridge suite: tests/aios_bridge/ plus tests/test_bridge.py as appropriate
Full repository suite: tests/
```

All must be green.

No live Brain/provider/API calls are required.

---

# Required RESULT-029 Manifest

`RESULT-029.md` MUST report at minimum:

```text
STATUS: READY_FOR_REVIEW
BASE_SHA: de556e5065ab1aea08fc832d2541532fe7085e33
IMPLEMENTATION_SHA: <tested implementation sha>
PREVIOUS_REVIEW_SHA: NONE

M5_EXECUTOR_LEASE: PASS|FAIL
MAX_ACTIVE_EXECUTORS_PER_TASK: 1
CANONICAL_EXECUTOR_LEASE: PASS|FAIL
ATOMIC_CREATE_IF_ABSENT: PASS|FAIL
RACE_EXACTLY_ONE_WINNER: PASS|FAIL
CORRUPT_ACTIVE_FAIL_CLOSED: PASS|FAIL
COMPARE_AND_RELEASE: PASS|FAIL
HANDOFF_RUN_LEASE_GATE: PASS|FAIL
HANDOFF_FIX_LEASE_GATE: PASS|FAIL
LEGACY_APPROVE_LEASE_GATE: PASS|FAIL
PUBLISH_REQUIRES_LEASE: PASS|FAIL
SUCCESSFUL_PUBLISH_RELEASES_LEASE: PASS|FAIL
TEST_FAILURE_RETAINS_LEASE: PASS|FAIL
HUMAN_RECOVERY_RELEASE: PASS|FAIL

ACTIVE_RUNTIME_EXECUTOR: antigravity
ALTERNATE_EXECUTORS_ACTIVATED: 0
EXECUTOR_FAILOVER_ADDED: NO
LEASE_TTL_OR_HEARTBEAT_ADDED: NO
LEASE_STEAL_ADDED: NO
DISPATCH_ROUTER_ADDED: NO
BRIDGE_V0_4_BEHAVIOR_CHANGED: YES — ADR-019-authorized M5 lease gate only
AUTHORITY_WIDENED: NO
LIVE_EXTERNAL_CALLS: 0
PAID_EXTERNAL_API_CALLS: 0

FOCUSED_LEASE_TESTS: <count/pass>
RUNTIME_LEASE_TESTS: <count/pass>
BRIDGE_TESTS: <count/pass>
CONTINUITY_TESTS: <count/pass>
FULL_REPO_TESTS: <count/pass>
REGRESSIONS: 0

EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 0   # update if fixes occur
```

Test counts are Executor-reported evidence; Primary Brain review does not claim independent execution unless it actually runs tests.

---

# Acceptance Criteria

TASK-029 is eligible for `APPROVED` only when all are true:

1. ADR-019 is implemented without semantic drift.
2. `ExecutorLease` is strict, immutable, bounded, deterministic and vendor-neutral.
3. `MAX_ACTIVE_EXECUTORS_PER_TASK = 1` is explicit and mechanically enforced in the current Bridge runtime workspace.
4. acquisition uses atomic create-if-absent rather than race-prone check/write.
5. corruption blocks acquisition rather than being auto-repaired/overwritten.
6. exact compare-and-release prevents stale release from removing a newer lease.
7. RUN, FIX and legacy approve all require lease before usable ACTIVE authorization.
8. ACTIVE authorization carries exact lease binding.
9. publish requires exact active lease before tests/mutation.
10. test/commit/push failure does not prematurely free ownership.
11. successful push releases exact lease then consumes authorization.
12. manual recovery is explicit, exact, confirmation-gated and non-failover.
13. no alternate Executor becomes executable.
14. no M6 failover/TTL/steal/router semantics appear.
15. M4 `executor.py` and canonical state/Brain/failover semantics remain unchanged.
16. focused + Bridge + Continuity + full repository tests are green.
17. ADR-017 Full Semantic Review and Final Independent Audit pass before merge.

---

## Human Execution Gate

After this TASK is received by Bridge, implementation begins only after explicit:

```text
/aios-worker RUN TASK-029
```

Antigravity must publish RESULT-029 and stop for Primary Brain review.

Human MERGE authorization remains separate even after `APPROVED`.
