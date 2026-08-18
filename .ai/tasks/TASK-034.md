# TASK-034 — M9.1 Hot Local Handoff Checkpoint Primitive

## Work Class

`L3 — CONTROL PLANE / DIRTY-WORKSPACE CONTINUITY / FAIL-CLOSED SAFETY`

Primary Brain owns:
- ADR-023 contract interpretation;
- review protocol;
- semantic findings;
- final PASS / CHANGES_REQUIRED decision.

Active Executor owns:
- repository inspection;
- implementation only within allowed files;
- adversarial tests;
- truthful test evidence;
- RESULT publication only through existing AIOS Bridge authority.

Human remains sole authority for:
- RUN;
- FIX;
- MERGE;
- Executor selection.

---

# Baseline

Canonical `main` at task authoring:

```text
2f754ff69bc13b8d5253102810d49e5200388de3
```

TASK-033 is PASS and merged.

Authoritative M9 contract:

```text
.ai/decisions/ADR-023-M9-HOT-LOCAL-HANDOFF-CONTRACT-LOCK.md
```

ADR-023 authoring commit:

```text
c0e819571441a36bf40fdadcc5574d9a0b17f15a
```

ADR-023 blob:

```text
2ef63caeb85f039a9647acbb973dc7cc105767c9
```

TASK-034 implements only M9.1 checkpoint capture/verify primitives.

It MUST NOT integrate a live hot-handoff command into Bridge yet.

---

# Objective

Implement a deterministic, fail-closed primitive that can:

1. inspect an explicitly identified task workspace;
2. reject unsupported/ambiguous Git state;
3. capture exact unpublished dirty-workspace evidence into an immutable `HotHandoffCheckpoint`;
4. persist checkpoint evidence outside the repository worktree;
5. verify later that the same workspace still exactly matches that checkpoint;
6. detect tampering/drift before any future replacement Executor is allowed to mutate.

This task proves the primitive only.

It does NOT transfer an Executor lease and does NOT perform a real cross-Executor handoff.

---

# Locked Contracts

## C1 — New primitive is continuity-local

Preferred implementation module:

```text
src/aios_bridge/continuity/hot_handoff.py
```

The implementation SHALL be vendor-neutral and executor-neutral.

No branching such as:

```python
if executor == "codex": ...
elif executor == "antigravity": ...
```

is allowed.

---

## C2 — Immutable checkpoint contract

Implement an immutable checkpoint representation, preferably frozen dataclasses, containing at minimum:

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

Each untracked manifest entry SHALL include:

```text
path
size_bytes
sha256
```

Checkpoint fingerprint MUST be deterministic canonical serialization of semantic fields.

Do not include timestamps in the semantic fingerprint.

---

## C3 — Capture must not mutate repository state

Checkpoint capture MUST NOT execute or emulate:

```text
git commit
git stash
git reset
git clean
git add
```

Capture SHALL leave:

- HEAD unchanged;
- branch unchanged;
- index unchanged;
- worktree bytes unchanged;
- untracked files unchanged.

Tests MUST prove this.

---

## C4 — Exact Git state binding

Capture SHALL bind exact current state including:

- current HEAD SHA;
- current branch;
- deterministic `git status --porcelain=v2` evidence;
- tracked workspace diff evidence;
- deterministic untracked-file manifest;
- normalized allowed paths.

Use exact byte/content hashes, not heuristic summaries.

No history scanning, nearest-match, fuzzy matching, or fallback to another commit is allowed.

---

## C5 — Fail closed on unsupported Git state

Capture MUST reject at minimum:

- detached HEAD;
- branch mismatch;
- staged changes;
- unmerged/conflicted paths;
- merge in progress;
- rebase in progress;
- cherry-pick in progress;
- revert in progress;
- out-of-scope modified/untracked paths;
- path traversal outside repository root;
- unsupported symlink/special file state;
- unsupported binary file payload unless exact binary support is explicitly implemented and tested.

Do not auto-fix, auto-reset, auto-clean, or auto-stash unsupported state.

---

## C6 — Allowed path boundary

The API SHALL receive an explicit allowed-path scope for the task.

Every changed/untracked payload path MUST resolve to a normalized repository-relative path inside that scope.

Path checks MUST reject:

```text
..
absolute paths
repository escape
symlink escape
```

The checkpoint MUST bind the normalized allowed-path set.

---

## C7 — Checkpoint storage outside worktree

Persist checkpoint evidence only under an explicitly supplied/runtime checkpoint directory outside the repository worktree.

The primitive MUST fail closed if the requested checkpoint storage directory resolves inside the worktree.

The persisted evidence SHOULD include a canonical checkpoint JSON plus any minimal exact payload evidence required by ADR-023.

Do not add checkpoint files to Git.

---

## C8 — Verification must be exact

Provide a verifier that re-inspects the workspace and fails closed if any checkpoint-bound state changed.

At minimum detect:

- HEAD drift;
- branch drift;
- tracked diff change;
- untracked byte change;
- untracked file added/removed;
- allowed-path mismatch;
- workspace ID mismatch;
- checkpoint fingerprint mismatch.

Successful verification MUST not mutate the worktree/index.

---

## C9 — Transcript/session exclusion

Checkpoint payload/evidence MUST NOT include:

- Executor transcript;
- hidden reasoning;
- browser cookies/session data;
- unrestricted environment dump;
- runtime authorization secrets;
- unrelated secret files.

This primitive is repository-state continuity only.

---

## C10 — No Bridge lifecycle integration in M9.1

Forbidden semantic modifications:

```text
bridge.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_failover.py
```

M9.1 SHALL NOT:

- add a hot-handoff CLI command;
- transfer/release/acquire leases;
- change approval semantics;
- change publish semantics;
- change M6/M8 failover proof contracts;
- change executor routing/defaults.

Those belong to later M9.2 after independent review PASS.

---

# Required Tests

Create focused tests in:

```text
tests/aios_bridge/continuity/test_m9_hot_handoff_checkpoint.py
```

Required coverage:

1. identical workspace state -> deterministic identical checkpoint fingerprint;
2. valid tracked text edit captured and verified;
3. valid untracked text file captured and verified;
4. tracked-file tamper -> verification fails;
5. untracked-file byte tamper -> verification fails;
6. untracked-file add/remove -> verification fails;
7. HEAD drift -> verification fails;
8. branch drift -> verification fails;
9. staged changes -> capture fails;
10. conflicted/unmerged state -> capture fails;
11. out-of-scope changed path -> capture fails;
12. traversal/absolute path -> fails;
13. symlink/special file -> fails;
14. binary payload -> fails unless exact binary support is implemented and adversarially tested;
15. checkpoint storage inside worktree -> fails;
16. checkpoint fingerprint tamper -> fails;
17. workspace ID mismatch -> fails;
18. allowed-path mismatch -> fails;
19. capture leaves HEAD/index/worktree/status unchanged;
20. verify leaves HEAD/index/worktree/status unchanged;
21. no history/nearest-match fallback.

Tests MUST use temporary Git repositories/workspaces where practical and MUST NOT depend on a real external Executor provider.

---

# Allowed Files

Implementation:

```text
src/aios_bridge/continuity/hot_handoff.py
```

Optional compatibility/export-only change if required:

```text
src/aios_bridge/continuity/__init__.py
```

Tests:

```text
tests/aios_bridge/continuity/test_m9_hot_handoff_checkpoint.py
```

Bridge-generated publication artifact:

```text
.ai/results/RESULT-034.md
```

No other repository files are authorized.

---

# Forbidden Scope

```text
bridge.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_failover.py
product/scraper code
browser automation
provider-specific integration
executor routing
automatic quota detection
M9.2 lifecycle integration
M9.3 real cross-Executor proof
M10/M11 work
```

---

# Test Gate

Executor SHALL run targeted tests first:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_m9_hot_handoff_checkpoint.py -q
```

Then continuity regression tests as appropriate.

Final publication MUST use the full repository suite through Bridge:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 34 --action RUN --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

No hard-coded expected test count in implementation logic.

---

# Completion Contract

TASK-034 is complete only when all are true:

```text
[ ] implementation stays within allowed files
[ ] immutable deterministic HotHandoffCheckpoint exists
[ ] capture is exact and non-mutating
[ ] verification is exact and non-mutating
[ ] staged/ambiguous Git state fails closed
[ ] path/scope escape fails closed
[ ] unsupported payload types fail closed
[ ] checkpoint storage is outside worktree
[ ] no Bridge/lease/failover semantics changed
[ ] all required adversarial tests pass
[ ] full repository suite passes via Bridge publish gate
[ ] RESULT-034 is Bridge-generated
[ ] Primary Brain independent review PASS
```

M9.1 PASS does not authorize M9.2 automatically. M9.2 requires a separate task/review boundary.