# ADR-019 — AIOS Continuity M5 Executor Lease & Single-Active-Executor Lock

STATUS: LOCKED

## Context

ADR-010 Decision 12 requires a future Executor Lease with the invariant:

```text
MAX_ACTIVE_EXECUTORS_PER_TASK = 1
```

M4 / ADR-018 / TASK-028 is now merged. The repository has a vendor-neutral Executor contract (`ExecutionRequest`, `ExecutionResult`, `ExecutorCapabilities`, `PreparedExecution`, `ExecutorAdapter`) but there is still no runtime mechanism preventing two execution activations from mutating the same task/workspace concurrently.

The current Bridge v0.4 creates ACTIVE RUN/FIX authorization records in a user-local runtime directory outside the Git worktree. `handoff` / legacy `approve` activate an Executor workflow and `publish` consumes authorization after a successful stable-boundary publish. Nothing currently provides an atomic single-owner lease.

M5 must therefore do more than define a dataclass: it must introduce a real fail-closed local lease primitive and wire it into every current Bridge execution-activation path.

M5 is still NOT Executor failover. M6 owns stable-boundary replacement Executor semantics. M5 only establishes exclusive active execution ownership and safe release.

---

## Decision 1 — Core Invariant

For the current single-workspace Bridge execution domain:

```text
MAX_ACTIVE_EXECUTORS_PER_TASK = 1
```

At most one ACTIVE Executor lease may exist for a task in the current AIOS runtime workspace.

A second activation MUST fail closed before Executor authorization becomes usable for execution.

M5 does not authorize controlled parallel worktrees. A future explicitly-scoped ADR is required before parallel execution is allowed.

---

## Decision 2 — Two-Layer Architecture

M5 SHALL separate canonical lease semantics from persistence/enforcement mechanics.

### Continuity Core

Introduce:

```text
src/aios_bridge/continuity/lease.py
```

This module owns vendor-neutral canonical lease records and pure validators only.

### Runtime Enforcement

Introduce a small runtime persistence module, expected at:

```text
src/aios_bridge/runtime_lease.py
```

or an equivalently narrow non-Continuity module.

It owns local atomic file creation/read/release under the existing external runtime directory.

`bridge.py` is the integration edge only. It SHALL NOT absorb the whole lease implementation.

---

## Decision 3 — Canonical ExecutorLease Record

M5 SHALL define an immutable, bounded, deterministic `ExecutorLease` record.

Required identity includes at minimum:

- `schema_version` = existing Continuity schema version;
- exact canonical `lease_id`;
- exact canonical `task_id`;
- exact lowercase 64-hex `workspace_id`;
- exact canonical `executor_id`;
- `operation: ExecutionOperation` (`RUN` or `FIX` only);
- exact lowercase 64-hex `execution_fingerprint` binding the lease to the activation context.

The canonical lease MUST be strict-schema, `frozen=True`, canonical-JSON serializable and SHA-256 fingerprintable.

The lease MUST NOT contain:

- API keys/tokens/cookies/auth headers;
- raw filesystem paths;
- chat transcripts / hidden reasoning;
- shell commands or terminal output;
- lease TTL/expiry timestamps;
- automatic failover target;
- vendor-specific transport/session secrets;
- merge authority;
- self-approval flags.

Presence of the ACTIVE lease file, not a mutable `status` field inside the record, defines active ownership.

---

## Decision 4 — Workspace Identity

Bridge runtime lease enforcement SHALL derive a deterministic `workspace_id` from the current repository/workspace root without persisting the raw local path.

The persisted value is only a lowercase SHA-256 fingerprint.

The raw Windows/POSIX path MUST NOT be stored in the canonical lease.

M5 makes no claim of distributed locking across machines or separately configured AIOS runtime roots.

---

## Decision 5 — Execution Fingerprint

`execution_fingerprint` is an opaque canonical SHA-256 binding supplied by the integration edge.

For the current Bridge v0.4 integration it SHALL deterministically cover the execution activation facts required to distinguish one authorized execution boundary from another, including at minimum:

- task identity;
- workspace identity;
- Executor identity;
- RUN/FIX operation;
- target task branch;
- exact authorized TASK/REVIEW artifact path;
- exact authorized artifact Git blob SHA.

It MUST NOT include secrets or mutable chat/session state.

Future M6/M7 adapter integrations MAY bind this field directly or indirectly to the M4 `ExecutionRequest` / `PreparedExecution` identity, but M5 does not require Bridge to synthesize a fake canonical ContinuityState or fake ExecutionRequest merely to acquire a lease.

---

## Decision 6 — Atomic Runtime Lease Store

The runtime store SHALL keep active leases outside the Git worktree under the existing per-repository AIOS runtime directory, conceptually:

```text
<AIOS_RUNTIME_DIR>/leases/TASK-NNN/ACTIVE.json
```

History/released records MAY be stored under a sibling history directory if useful, but history is not authority.

Acquisition MUST use an operating-system atomic create-if-absent primitive (`O_CREAT | O_EXCL` or an equivalently strong atomic primitive).

Forbidden implementation:

```text
if not path.exists():
    write(path)
```

because that is race-prone.

A successful acquisition SHALL write the complete canonical lease, flush the file and fsync it before returning success where supported by the platform.

If creation succeeds but durable write fails, the store SHALL best-effort remove only the lease file it just created. If cleanup cannot be proven, the state remains fail-closed as an occupied/corrupt lease rather than being treated as free.

---

## Decision 7 — Corruption Is Occupied, Never Free

If `ACTIVE.json` exists but is:

- empty;
- malformed JSON;
- invalid UTF-8;
- wrong schema;
- oversized;
- noncanonical;
- wrong task/workspace identity;
- otherwise unparsable;

then acquisition MUST fail closed.

The runtime MUST NOT overwrite or auto-delete a corrupt active lease and MUST NOT reinterpret corruption as “no active executor”.

This follows the project’s corruption/integrity precedence discipline.

---

## Decision 8 — No Lease Stealing, Timeout or Automatic Expiry in M5

M5 SHALL NOT implement:

- TTL expiration;
- heartbeat timeout;
- automatic stale detection;
- automatic lease steal;
- quota-triggered replacement;
- process-liveness guessing;
- replacement Executor selection;
- Executor failover.

Clock time is not authority.

An ACTIVE lease remains active until an exact safe release occurs.

M6 may define the stop/release/acquire sequence required for failover.

---

## Decision 9 — Release Is Compare-And-Release

Release MUST require the caller to present exact expected lease identity, at minimum the canonical lease fingerprint or exact `lease_id` plus the other binding fields.

The store SHALL re-read and validate the current ACTIVE record before removal.

A stale/wrong release request MUST NOT remove a newer/different active lease.

Release SHALL be implemented as an atomic move/rename out of the ACTIVE path where practical, or another mechanism that ensures a wrong lease cannot be removed after a comparison race.

A missing active lease is not silently interpreted as successful release unless the caller explicitly uses an idempotent status-only path defined by the implementation. Bridge stable-boundary release should be strict.

---

## Decision 10 — Human Recovery Release

M5 SHALL provide a narrow explicit operator recovery path because a fail-closed lease may survive an Executor crash.

Expected Bridge command shape:

```text
python bridge.py lease-status [TASK-N]
python bridge.py lease-release TASK-N --lease-id <exact-id> --confirm-stopped
```

Exact CLI spelling may vary slightly.

Recovery release requirements:

1. user must explicitly invoke it;
2. exact current `lease_id` must match;
3. an explicit `--confirm-stopped` (or equally explicit confirmation flag) is mandatory;
4. the associated ACTIVE authorization SHALL be made non-active before releasing the lease, so an old Executor cannot later publish with stale authorization;
5. no replacement Executor is automatically started;
6. no failover selection occurs.

This is manual safety recovery, not M6 failover.

---

## Decision 11 — Bridge Activation Gate

ADR-019 narrowly supersedes ADR-010 Decision 18 only to add a lease gate around existing execution activation.

Both current execution activation paths MUST participate:

- `cmd_handoff()` RUN/FIX;
- legacy `cmd_approve()` TASK/REVIEW.

A Bridge activation MUST acquire the task lease before making a new ACTIVE authorization usable.

If a conflicting ACTIVE lease already exists, activation fails closed and no new Executor execution may start.

The active authorization record SHALL persist non-secret lease binding metadata sufficient for later publish validation, expected to include:

- `executor_id`;
- `lease_id`;
- `lease_fingerprint`;
- `workspace_id`;
- `execution_fingerprint`.

Current Bridge integration MUST continue to use `antigravity` as the only proven runtime Executor identity. M5 MUST NOT add a user-selectable `--executor codex` / `--executor claude-code` switch or otherwise activate an alternate Executor.

---

## Decision 12 — Activation Transaction / Rollback

Lease acquisition and authorization activation form one safety transaction.

Required ordering:

1. validate control artifact / branch / worktree as today;
2. construct exact lease candidate;
3. atomically acquire lease;
4. persist ACTIVE authorization containing exact lease binding;
5. expose execution context to Antigravity.

If step 4 fails after a newly-created lease was acquired, Bridge MUST attempt compare-and-release of exactly that newly-created lease before surfacing failure.

It MUST NOT release a pre-existing lease belonging to another activation.

No execution context should be emitted as successful before both lease and authorization are valid.

---

## Decision 13 — Publish Requires Exact Active Lease

`cmd_publish()` SHALL require BOTH:

- current ACTIVE authorization under existing v0.4 rules; and
- exact ACTIVE lease matching the authorization’s lease binding.

Publish MUST fail closed before tests/commit/push if:

- no lease exists;
- lease is corrupt;
- lease task/workspace/executor/operation differs;
- lease_id/fingerprint differs;
- execution_fingerprint differs.

This prevents a stale authorization from publishing after its lease has been released or replaced.

---

## Decision 14 — Release Boundary After Successful Stable-Boundary Publish

A successful publish creates the stable boundary for the current execution activation.

After commit + successful push:

1. Bridge SHALL compare-and-release the exact active lease;
2. then mark the authorization non-active/consumed and persist publish metadata;
3. then update operational state to `IN_REVIEW` as today.

If tests fail before commit/push, the lease remains ACTIVE because the same authorized Executor may continue repairing the current execution attempt.

If pre-publish contract validation fails, M5 defaults to retaining the lease (fail-closed) rather than guessing that execution has stopped.

If release after push fails, Bridge SHALL surface an error and preserve safety; it MUST NOT pretend the lease is free.

---

## Decision 15 — Existing Bridge Semantics Preserved Except Lease Gate

ADR-019 authorizes only the minimal changes needed for Decisions 10–14.

Preserved invariants:

- TASK/REVIEW exact control-blob authorization;
- human RUN approval mandatory;
- human FIX approval mandatory;
- human MERGE approval mandatory;
- safe main reconciliation;
- fail-closed branch reconciliation;
- dirty worktree blocking;
- no force push;
- publish test gate;
- RESULT generation/push semantics;
- runtime state outside worktree;
- Antigravity remains the sole proven Executor;
- no auto-merge.

Bridge version text MAY note M5 lease enforcement, but this ADR does not authorize unrelated Bridge redesign.

---

## Decision 16 — M4 Contract Remains Authoritative

M5 SHALL reuse `ExecutionOperation` from M4 rather than creating a third RUN/FIX execution enum.

M5 SHALL NOT mutate M4 `ExecutionRequest`, `ExecutionResult`, `ExecutorCapabilities`, `PreparedExecution`, or `ExecutorAdapter` semantics merely to implement lease storage.

`PreparedExecution != ExecutorLease` remains true:

- PreparedExecution = request-binding preparation receipt;
- ExecutorLease = exclusive active execution ownership record.

Later milestones may mechanically bind both at integration edges.

---

## Decision 17 — Public Lease Core API

Expected public Continuity API includes equivalents of:

```python
MAX_ACTIVE_EXECUTORS_PER_TASK = 1

@dataclass(frozen=True)
class ExecutorLease: ...

def validate_executor_lease_binding(...): ...
```

Runtime API may include equivalents of:

```python
class AtomicExecutorLeaseStore:
    def acquire(self, lease: ExecutorLease) -> ExecutorLease: ...
    def load_active(self, task_id: str) -> ExecutorLease | None: ...
    def require_active(self, expected: ExecutorLease) -> ExecutorLease: ...
    def release(self, expected: ExecutorLease) -> ExecutorLease: ...
```

Exact names may vary, but semantics must remain obvious and narrow.

---

## Decision 18 — Deterministic Strictness and Bounds

Lease canonical records SHALL follow hardened Continuity conventions:

- exact case-sensitive `TASK-<digits>`;
- exact conservative lowercase lease/executor identifiers;
- exact 64-hex workspace/execution fingerprints;
- unknown fields rejected;
- input bytes bounded before JSON parse;
- invalid UTF-8 wrapped in `ContinuityStateValidationError`;
- canonical JSON deterministic;
- fingerprint SHA-256 over canonical UTF-8 JSON;
- serialized canonical record <= existing 16 KiB limit;
- no arbitrary iterables/mutable nested metadata;
- no huge raw payloads in diagnostics.

Runtime lease files SHALL have an explicit maximum read size and reject oversize before parsing.

---

## Decision 19 — Required Concurrency / Adversarial Proof

M5 tests SHALL prove at minimum:

1. valid canonical lease round-trip/fingerprint;
2. second lease for same task/runtime workspace cannot be acquired while first is ACTIVE;
3. two independent store instances racing to acquire the same task produce exactly one winner;
4. corrupt/empty/oversized ACTIVE lease fails closed and is not overwritten;
5. wrong/stale lease ID or fingerprint cannot release current lease;
6. successful exact release frees the task for a later acquisition;
7. handoff/approve cannot activate without acquiring a lease;
8. publish rejects missing/mismatched/released lease before mutation/push;
9. test failure retains lease;
10. successful publish releases lease and consumes authorization;
11. human recovery release requires exact ID + explicit stopped confirmation and deactivates authorization;
12. no alternate Executor is activated;
13. no lease TTL/steal/failover/router behavior exists;
14. existing Continuity/Bridge/full repository suites remain green.

The concurrency proof should exercise the atomic create primitive using independent store instances and a coordinated thread/process race rather than merely asserting `path.exists()` logic.

---

## Decision 20 — Scope / Expected Implementation Boundary

Expected production changes are narrowly bounded to:

```text
src/aios_bridge/continuity/lease.py          # new canonical lease contract
src/aios_bridge/continuity/__init__.py       # additive exports
src/aios_bridge/runtime_lease.py             # new atomic local runtime store
bridge.py                                    # minimal lease integration + diagnostics/recovery CLI
```

Expected tests:

```text
tests/aios_bridge/continuity/test_lease.py
tests/aios_bridge/test_runtime_lease.py      # or equivalent narrow location
tests/test_bridge.py                         # integration regressions
```

Changes to canonical `state.py`, `brain.py`, `failover.py`, M4 `executor.py`, provider/model code, Python Agent runtime execution code or authorization control artifacts are NOT expected.

If implementation requires widening these boundaries, STOP and escalate before code.

---

## Decision 21 — Non-Goals

M5 does NOT implement:

- Executor failover (M6);
- Codex adapter/invocation;
- Claude Code adapter/invocation;
- third Executor proof (M7);
- distributed lock service;
- cloud lock backend;
- lock heartbeat / TTL;
- automatic stale-process detection;
- automatic lease steal;
- dirty-workspace hot handoff (M9);
- deterministic Executor dispatch/router (M10);
- smart/LLM routing;
- automatic API fallback;
- autonomous RUN/FIX/MERGE;
- controlled parallel worktrees.

---

## Acceptance Criteria

M5 is complete only when all are true:

1. `ExecutorLease` exists as a strict deterministic vendor-neutral Continuity contract;
2. `MAX_ACTIVE_EXECUTORS_PER_TASK = 1` is explicit and tested;
3. runtime acquisition uses atomic create-if-absent and fails closed on conflicts/corruption;
4. stale/wrong release cannot free another lease;
5. every current Bridge activation path requires lease acquisition before usable ACTIVE authorization;
6. publish requires exact active lease and releases it only at successful stable boundary;
7. explicit human crash-recovery release is safe, exact and non-automatic;
8. Antigravity remains the only activated runtime Executor;
9. no M6 failover semantics are introduced;
10. existing authorization/branch/test/publish/human-merge invariants remain intact;
11. focused Continuity lease tests, runtime lease tests, Bridge tests and full repository suite are green;
12. ADR-017 Full Semantic Review + Final Independent Audit pass before merge.

---

## Supersession / Relationship

- ADR-010 remains architecture authority. ADR-019 implements its Decision 12 / M5 milestone.
- ADR-018 remains M4 Executor-neutral contract authority.
- ADR-019 narrowly supersedes ADR-010 Decision 18 only where necessary to add lease acquisition/validation/release gates to Bridge v0.4.
- It does not supersede human RUN/FIX/MERGE authority, TASK/REVIEW authorization semantics, branch safety, publish test gates or Antigravity’s current sole-executor status.
- M6 requires a separate ADR before replacement Executor failover can be implemented.
