# TASK-035 Implementation Blueprint — Thin Executor Mode

Purpose: remove repository-discovery and architecture-design work from the Executor. The Primary Brain has already audited the relevant code paths.

## Exact baseline assumptions

Canonical main at design time:

```text
6d9222523fa24ac7b456299f37655b6c544523a9
```

Known existing primitives that MUST be reused, not redesigned:

- `bridge.get_runtime_paths()` / `get_workspace_id()`
- `bridge.load_authorization()` / `save_authorization()` / `get_active_authorization()`
- `bridge.reconstruct_expected_executor_lease()`
- `bridge.build_executor_lease_candidate()`
- `bridge.get_lease_store()`
- `AtomicExecutorLeaseStore.require_active()`
- `AtomicExecutorLeaseStore.acquire()`
- `AtomicExecutorLeaseStore.release()`
- `capture_hot_handoff_checkpoint()`
- `verify_hot_handoff_checkpoint()`
- `HotHandoffCheckpoint.from_json()`

Do NOT modify `src/aios_bridge/runtime_lease.py`, `src/aios_bridge/continuity/lease.py`, or the M9.1 primitive.

---

## File plan

Implementation:

```text
bridge.py
```

Focused tests:

```text
tests/test_bridge_hot_handoff.py
```

No other source files should be needed.

---

## Required bridge.py imports

Import from `src.aios_bridge.continuity.hot_handoff`:

```python
HotHandoffCheckpoint
HotHandoffCheckpointError
capture_hot_handoff_checkpoint
verify_hot_handoff_checkpoint
```

Do not vendor/copy M9.1 logic into Bridge.

---

## Runtime paths

Extend `get_runtime_paths()` with one external path only:

```python
"hot_handoff": rdir / "hot_handoff"
```

Add helper:

```python
def get_hot_handoff_checkpoint_dir(task_id: int) -> Path:
    return get_runtime_paths()["hot_handoff"] / f"TASK-{task_id:03d}" / "checkpoints"
```

This path is outside the worktree by construction and is passed directly to M9.1 capture/verify.

---

## Exact scope marker parser

Add a small pure helper such as:

```python
def parse_hot_handoff_allowed_paths(content: str) -> tuple[str, ...]:
```

Contract:

1. Search only exact full lines matching:

```text
HOT_HANDOFF_ALLOWED_PATHS_JSON: <json>
```

2. There must be exactly one occurrence.
3. Parse the right-hand side with `json.loads`.
4. Require a non-empty JSON list.
5. Every item must be a non-empty string.
6. Reject duplicates.
7. Do not normalize/widen here beyond converting to a tuple; M9.1 `_normalize_allowed_paths` remains the authoritative path safety validator during capture/verify.
8. Reject missing, duplicate, malformed, non-list, empty-list, non-string, or duplicate-item markers.

Do not parse Markdown `Allowed Files` headings. Do not infer scope from `git status`.

---

## Protected dirty-path helper

Define exact immutable protected path set:

```text
bridge.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/continuity/state.py
src/aios_bridge/continuity/errors.py
```

Add helper that compares current `changed_files()`/porcelain paths against this exact set and fails preparation if any protected path is dirty.

Do not broaden this into a new general policy engine.

---

## Checkpoint loader helper

Add a deterministic helper such as:

```python
def load_persisted_hot_handoff_checkpoint(task_id: int, fingerprint: str) -> HotHandoffCheckpoint:
```

Contract:

- fingerprint must be exact lowercase 64-hex;
- exact path is `<checkpoint_dir>/<fingerprint>.json`;
- no directory scanning, latest-file lookup, history fallback, prefix matching, or nearest match;
- missing/unreadable/malformed file fails closed;
- parse with `HotHandoffCheckpoint.from_json()`;
- parsed checkpoint fingerprint must equal requested fingerprint.

---

## Hot-handoff authorization metadata

Use one nested authorization object named exactly:

```python
"hot_handoff": {...}
```

Prepared metadata minimum:

```text
checkpoint_fingerprint
allowed_paths
source_executor_id
source_lease_id
source_lease_fingerprint
source_execution_fingerprint
authorized_artifact_path
authorized_artifact_blob_sha
prepared_at
```

Activated metadata additionally contains:

```text
replacement_executor_id
replacement_lease_id
replacement_lease_fingerprint
replacement_execution_fingerprint
activated_at
```

Do not place secrets, transcripts, environment dumps, or model conversation content in authorization metadata.

---

## `cmd_hot_handoff_prepare(args)` exact algorithm

Implement in this order unless a local code-shape reason requires a semantically equivalent arrangement:

1. `ensure_git()` and `cfg = load_config()`.
2. Require `args.confirm_quiescent is True`; otherwise `fail(...)` before any mutation.
3. Require current branch exactly `f"{cfg['task_branch_prefix']}{task_id:03d}"`.
4. Load exact `ACTIVE` authorization via `get_active_authorization(task_id)`; absence fails.
5. Deep-copy original authorization for rollback.
6. Reconstruct source lease with `reconstruct_expected_executor_lease(auth)`.
7. `store.require_active(source_lease)`.
8. Require authorization branch/workspace/task bindings match current expected values.
9. `fetch_control(cfg)`; resolve `get_remote_blob_sha(cfg, auth['artifact_path'])`; require exact equality with `auth['artifact_blob_sha']`.
10. Read that exact authorized control artifact with `read_remote_file`; parse exact `HOT_HANDOFF_ALLOWED_PATHS_JSON` marker.
11. Reject any dirty protected control-plane path.
12. Build `checkpoint_dir = get_hot_handoff_checkpoint_dir(task_id)`.
13. Call `capture_hot_handoff_checkpoint(PROJECT, checkpoint_dir, ...)` using exact values from authorization/source lease and parsed allowed paths.
14. Immediately call `verify_hot_handoff_checkpoint(checkpoint, PROJECT, workspace_id=..., allowed_paths=..., checkpoint_dir=checkpoint_dir)`.
15. Only after successful capture+verify, call `store.release(source_lease)`.
16. After source release, call the same exact verifier again.
17. Build updated authorization from the original source authorization:
    - `status = "HANDOFF_PREPARED"`
    - preserve original task/action/kind/artifact/branch/workspace/source top-level fields for auditability;
    - attach nested `hot_handoff` prepared metadata above.
18. `save_authorization(task_id, prepared_auth)`.
19. `update_state(task_id, "HANDOFF_PREPARED", ...)`.
20. Print checkpoint fingerprint, source executor, and explicit next command shape.

### Prepare rollback

Track whether source lease was released.

If any ordinary exception occurs before release: source auth/lease must remain untouched.

If an exception occurs after release but before successful prepared authorization persistence:

1. attempt `store.acquire(source_lease)` using the exact original source lease object;
2. restore the deep-copied original authorization;
3. if both succeed, update state back to the original execution state (`IN_PROGRESS` for RUN; `CHANGES_REQUIRED` for FIX) and fail the command;
4. if rollback cannot be proven, update state to `RECOVERY_REQUIRED` and fail with diagnostics.

Do not delete the immutable checkpoint merely to hide a failed prepare; orphaned content-addressed evidence is harmless and non-authoritative.

---

## `cmd_hot_handoff_activate(args)` exact algorithm

1. `ensure_git()` and `cfg = load_config()`.
2. Require `--executor` was explicitly supplied; call `validate_runtime_executor_id(args.executor)`.
3. Require `args.checkpoint` exact lowercase 64-hex.
4. Require current branch exactly expected task branch.
5. `auth = load_authorization(task_id)` and require `auth['status'] == 'HANDOFF_PREPARED'`.
6. Require nested `hot_handoff` dict exists and contains every prepared field exactly once/non-empty with expected types.
7. Require CLI checkpoint equals `hot_handoff['checkpoint_fingerprint']`.
8. Require replacement executor differs from `hot_handoff['source_executor_id']`.
9. Require current workspace ID equals authorization/prepared workspace ID.
10. Require `store.load_active(task_id_str) is None`; any active lease blocks activation.
11. Fetch control and require current authorized artifact blob exactly equals both top-level auth blob and prepared hot-handoff blob.
12. Load checkpoint only by exact fingerprint/path using the helper; validate checkpoint task/branch/workspace/source executor/source lease fp/source execution fp and allowed paths against prepared auth metadata.
13. Verify current workspace against exact checkpoint, including `checkpoint_dir` persisted-byte check.
14. Build a NEW replacement lease with `build_executor_lease_candidate(...)` using same task/action/branch/artifact/workspace but selected replacement executor.
15. Acquire replacement lease with `store.acquire(replacement_lease)`.
16. Immediately verify the same checkpoint again after acquisition and before ACTIVE authorization save.
17. Build replacement ACTIVE authorization:
    - preserve task/action/kind/artifact/branch/workspace;
    - `status = "ACTIVE"`;
    - top-level executor/lease/execution fields become replacement binding;
    - replace/refresh `approved_at` as this is a new Human continuation authorization;
    - retain nested prepared metadata and add replacement metadata.
18. Save authorization.
19. Update state to `IN_PROGRESS` for RUN or `CHANGES_REQUIRED` for FIX.
20. Print replacement executor + checkpoint and tell Executor to run `bridge.py context <id>` before mutation.

### Activation rollback

If any failure occurs before replacement acquire: prepared state remains unchanged.

If post-acquire verification or ACTIVE-auth persistence fails:

1. compare-and-release the just-acquired replacement lease;
2. restore exact `HANDOFF_PREPARED` authorization;
3. update state to `HANDOFF_PREPARED` if rollback proves clean;
4. otherwise `RECOVERY_REQUIRED`;
5. never reactivate the source automatically at this stage.

---

## Context integration

In `cmd_context`, add one top-level JSON field:

```python
"hot_handoff": auth.get("hot_handoff") if isinstance(auth, dict) else None
```

Do not change other context semantics.

---

## Publish integration

Before tests or RESULT generation, if authorization contains key `hot_handoff`:

1. Require it is a dict with the complete activated metadata set.
2. Require source != replacement.
3. Require replacement executor/fingerprints match current top-level ACTIVE auth and exact active lease.
4. Load exact persisted checkpoint by fingerprint.
5. Validate checkpoint semantic provenance against source metadata and task/branch/workspace/allowed paths.
6. Do NOT call workspace equality verification here: replacement continuation is expected to have changed workspace after activation.
7. Do NOT construct `StableExecutorFailoverProof`.

RESULT review manifest for a hot-handoff publication adds:

```text
HOT_HANDOFF: YES
HOT_HANDOFF_CHECKPOINT_FINGERPRINT: <fp>
HOT_HANDOFF_FROM_EXECUTOR: <source>
HOT_HANDOFF_TO_EXECUTOR: <replacement>
```

For ordinary non-hot-handoff publication, emit:

```text
HOT_HANDOFF: NO
```

Do not change `EXECUTOR_FAILOVER` behavior.

---

## Parser integration

Add exactly two subcommands:

```text
hot-handoff-prepare
  task_id: int
  --confirm-quiescent: store_true

hot-handoff-activate
  task_id: int
  --executor: required=True
  --checkpoint: required=True
```

No automatic Executor selection/default for activate.

---

## Focused test file

Create `tests/test_bridge_hot_handoff.py`.

Prefer temp Git repositories + isolated `AIOS_RUNTIME_DIR`, following patterns in `tests/test_bridge.py`.

Do NOT make real Codex/Antigravity/Claude calls.

Required tests map directly to ADR-024 Decision 15. At minimum include explicit tests for:

- marker parser missing/duplicate/malformed/duplicates;
- prepare confirmation gate;
- ACTIVE auth + exact source lease requirement;
- control blob drift;
- protected dirty path;
- capture/verify pre-release failure leaves source active;
- successful prepare => zero active lease + HANDOFF_PREPARED;
- injected second verify failure after source release => source lease/auth rollback;
- activate explicit executor + distinct actor + exact checkpoint;
- drift before activate => no replacement lease;
- active lease collision before activate;
- successful activate => replacement ACTIVE auth/new lease + source provenance retained;
- injected post-acquire verify failure => replacement lease released + HANDOFF_PREPARED retained;
- context surfaces hot_handoff metadata;
- publish rejects partial metadata;
- publish does not classify hot handoff as M6/M8 stable failover;
- ordinary non-hot-handoff bridge regression remains unchanged.

Use monkeypatch seams around capture/verify/store operations where needed to deterministically test rollback ordering. Do not weaken production validation merely to make tests easy.

---

## Token-saving Executor instructions

Executor MUST NOT perform broad repository discovery.

Read only:

```text
.ai/tasks/TASK-035.md
.ai/decisions/ADR-024-M9.2-HOT-HANDOFF-BRIDGE-LIFECYCLE-CONTRACT-LOCK.md
.ai/context/TASK-035-IMPLEMENTATION-BLUEPRINT.md
bridge.py sections named in this blueprint
tests/test_bridge.py only as a test-fixture/pattern reference
src/aios_bridge/continuity/hot_handoff.py public API only if needed
```

Do not recursively inspect `src/` or `tests/`.

Do not redesign the architecture. If the blueprint conflicts with actual code in a way that blocks safe implementation, stop and report the exact blocker.

Executor runs targeted tests only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_bridge_hot_handoff.py -q
.\venv\Scripts\python.exe -m pytest tests/test_bridge.py -q
```

Then STOP. Full repository suite belongs to Bridge publish gate.