# ADR-023 — M9 Optional Hot Local Handoff Contract Lock

STATUS: LOCKED

## Context

ADR-010 locks M9 as a separately designed and audited milestone for checkpoint-based dirty-workspace Executor handoff.

M6–M8 prove only stable-boundary continuity. They do not authorize transferring ownership of an unpublished dirty workspace from one Executor to another.

A hot/local handoff is materially riskier because a replacement Executor may otherwise inherit ambiguous edits, staged state, conflicts, in-flight side effects, or workspace drift without a published Git boundary.

This ADR therefore introduces a narrow M9 v1 contract. It does not replace M6 stable-boundary failover and it does not authorize autonomous routing.

---

## Decision 1 — M9 v1 Scope

M9 v1 supports only a same-repository, same-local-workspace handoff at an explicit quiescent checkpoint while unpublished task edits exist.

The first implementation milestone SHALL prove checkpoint capture and verification primitives before any Bridge CLI activation flow is added.

M9 v1 does NOT support:

- concurrent Executors;
- automatic Executor selection;
- cross-machine transfer;
- browser/session transfer;
- in-flight external side effects;
- staged index state;
- merge/rebase/cherry-pick conflicts;
- submodule state transfer;
- symlink handoff;
- unsupported binary payloads;
- arbitrary secret/session/runtime capture.

Unsupported state MUST fail closed.

---

## Decision 2 — Human Authority Remains Mandatory

Human remains sole authority for:

- requesting a hot handoff;
- selecting the replacement Executor;
- authorizing continuation after the source Executor is quiesced;
- MERGE.

No Brain, Executor, policy engine, quota detector, or Bridge helper may silently choose a replacement Executor.

Quota exhaustion may motivate a handoff request, but quota state does not grant handoff authority.

---

## Decision 3 — Single-Active-Executor Invariant Survives Hot Handoff

The locked invariant remains:

```text
MAX_ACTIVE_EXECUTORS_PER_TASK = 1
```

Conceptual state sequence:

```text
ACTIVE(source)
    ↓ source reaches quiescent boundary
HANDOFF_PREPARED(source still owns lease)
    ↓ checkpoint captured and verified
SOURCE_RELEASED(no active Executor)
    ↓ Human selects replacement
ACTIVE(replacement, checkpoint-bound)
```

There MUST NOT be an interval in which source and replacement both hold an active mutation lease for the same task/workspace.

Checkpoint capture does not itself transfer authority.

---

## Decision 4 — Quiescent Boundary Is Required

A hot handoff may begin only when the source Executor is quiescent.

Quiescent means, at minimum:

- no shell/tool command is still executing under the source Executor for the task;
- no browser automation step is in flight;
- no external write/upload/publish operation is in flight;
- no Git operation is in progress;
- the source Executor will not mutate the workspace after checkpoint capture begins.

M9 v1 SHALL NOT infer safety from process-name heuristics.

If quiescence cannot be established truthfully, the handoff MUST stop.

---

## Decision 5 — HotHandoffCheckpoint Is Immutable Evidence

M9 SHALL introduce an immutable checkpoint representation conceptually containing at minimum:

```text
schema_version
task_id
target_branch
workspace_id
source_executor_id
source_lease_fingerprint
source_execution_fingerprint
head_sha
allowed_paths
status_porcelain_v2_sha256
tracked_diff_sha256
untracked_file_manifest
checkpoint_fingerprint
```

Each untracked manifest item SHALL contain at minimum:

```text
path
size_bytes
sha256
```

The checkpoint fingerprint SHALL be computed from deterministic canonical serialization of the semantic checkpoint fields.

Timestamps or logging metadata MUST NOT be part of the semantic fingerprint unless a future ADR explicitly requires them.

---

## Decision 6 — Exact Workspace State Must Be Bound

Checkpoint capture SHALL bind the exact dirty workspace state without committing it.

For tracked files, the implementation SHALL derive evidence from deterministic Git-visible workspace state, including a binary-capable diff representation or an equivalent exact content-addressed representation.

For untracked files, the implementation SHALL hash exact file bytes and record a deterministic manifest.

The checkpoint SHALL also bind:

- current HEAD commit;
- target branch;
- normalized repository-relative paths;
- allowed task scope;
- Git status state.

A replacement Executor MUST NOT be allowed to continue if the workspace no longer matches the checkpoint.

---

## Decision 7 — M9 v1 Rejects Staged or Ambiguous Git State

The initial M9 contract intentionally narrows supported state.

Checkpoint capture MUST fail closed if any of the following are present:

- staged changes;
- unmerged/conflicted paths;
- merge in progress;
- rebase in progress;
- cherry-pick/revert in progress;
- detached HEAD;
- branch mismatch;
- submodule dirtiness relevant to the task;
- repository paths outside the authorized task scope.

M9 v1 does not preserve index/staging semantics.

A future ADR may extend the checkpoint schema to cover them.

---

## Decision 8 — Initial Payload Safety Boundary

M9 v1 SHALL support regular repository files needed for source-code/task continuation and SHALL fail closed on unsupported special files.

At minimum, capture/verification MUST reject:

- symlinks;
- directories masquerading as files;
- device/special files;
- paths escaping repository root;
- paths escaping allowed task scope.

Binary support MAY be implemented only if exact byte-preserving verification is proven. Otherwise binary files MUST fail closed in the first implementation.

No secret/session directories or AIOS runtime-control directories may be checkpoint payloads.

---

## Decision 9 — Checkpoint Storage Lives Outside the Worktree

Checkpoint evidence and any payload copies required for reconstruction SHALL live under the existing AIOS runtime/control storage domain outside the repository worktree.

Checkpoint capture MUST NOT create repository commits merely to preserve a dirty workspace.

Forbidden preservation shortcuts include:

```text
git commit
git stash
git reset
git clean
```

unless a future explicitly-scoped ADR changes this contract.

The source workspace must remain semantically unchanged by capture/verification.

---

## Decision 10 — Verify Before Replacement Mutation

Before a replacement Executor may mutate the workspace, AIOS SHALL verify that the current workspace exactly matches the authorized checkpoint.

Verification SHALL fail closed on any mismatch, including:

- HEAD changed;
- branch changed;
- tracked diff changed;
- untracked file bytes changed;
- untracked file added/removed;
- allowed-path set mismatch;
- workspace ID mismatch;
- checkpoint fingerprint mismatch.

No nearest-match, history scan, fuzzy comparison, or best-effort recovery is allowed.

---

## Decision 11 — Checkpoint Is Not Publication

A hot-handoff checkpoint is transient continuity evidence, not a canonical task publication.

It MUST NOT be represented as:

- RESULT;
- REVIEW;
- PASS;
- merge approval;
- a stable-boundary failover publication.

M6/M8 stable-boundary evidence remains separate.

After replacement continuation completes, normal AIOS Bridge publication semantics still produce the authoritative RESULT and Git commit.

---

## Decision 12 — No Transcript or Hidden Reasoning Transfer

M9 transfers only repository/workspace continuity evidence required for execution.

It MUST NOT transfer:

- Executor conversation transcripts;
- hidden reasoning;
- chat memory dumps;
- authentication/session cookies;
- unrestricted environment dumps;
- secrets unrelated to the task.

Replacement reconstruction is based on TASK/ADR/Bridge context plus the exact checkpointed workspace state.

---

## Decision 13 — First Implementation Stage Is Primitive-Only

The first M9 implementation task SHALL introduce only checkpoint capture/verification primitives and adversarial tests.

It SHALL NOT yet change:

- `bridge.py` approval/publish flow;
- Executor Lease state machine;
- M6 stable-boundary failover semantics;
- M8 composite proof semantics;
- executor routing/default policy.

A later task may integrate the primitive into a Human-authorized Bridge handoff lifecycle after the primitive receives independent review PASS.

---

## Decision 14 — Required Adversarial Coverage

Before M9 checkpoint primitives may be considered safe, tests SHALL cover at minimum:

1. deterministic checkpoint fingerprint for identical workspace state;
2. tracked-file tampering detected;
3. untracked-file tampering detected;
4. added/removed untracked file detected;
5. HEAD drift detected;
6. branch drift detected;
7. staged changes rejected;
8. conflicted/unmerged state rejected;
9. out-of-scope path rejected;
10. path traversal rejected;
11. symlink/special file rejected;
12. unsupported binary payload rejected unless exact binary support is proven;
13. capture/verify leaves workspace contents and Git state unchanged;
14. checkpoint storage resolves outside the worktree;
15. no history/nearest-match fallback.

---

## Decision 15 — M9 Acceptance Is Incremental

M9 shall be delivered in stages:

```text
M9.1 — checkpoint capture/verify primitive + adversarial tests
M9.2 — Human-authorized Bridge lifecycle integration
M9.3 — real two-Executor hot-handoff proof
```

M9.3 requires two distinct supported real Executors and MUST NOT be simulated merely to claim cross-Executor continuity.

If a second real Executor is unavailable due quota/tooling, M9.1/M9.2 may proceed, but M9.3 remains pending rather than weakened.

---

## Locked Summary

```text
source Executor owns lease
        ↓
source becomes quiescent
        ↓
exact dirty workspace checkpoint captured
        ↓
checkpoint verified without workspace mutation
        ↓
source lease released
        ↓
Human explicitly selects replacement Executor
        ↓
replacement binds exact checkpoint
        ↓
workspace re-verified before first mutation
        ↓
replacement continues same TASK
        ↓
normal Bridge publish produces authoritative RESULT
```

M9 exists to preserve unpublished work without weakening Human authority, lease exclusivity, Git provenance, or fail-closed behavior.