# REVIEW-043 — E4 Result Collection + Auto Publication

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO

## Review Round

Round 2 — close-condition audit for R1-1 through R1-3 plus fresh lineage, scope, publication-trust, recovery, adversarial-test, and regression verification.

## Authoritative Anchors

```text
TASK_ID: TASK-043
BASELINE_MAIN_SHA: 91813c04160cb664af47c5f0b04fea37ef9aa076
TASK_BRANCH: ai/task-043
ROUND_1_TASK_HEAD_SHA: 14d39006f370dd8e14406a4416dfde91ac7ecba2
ROUND_2_TASK_HEAD_SHA: c323d532d49e8ca7505971108cd011924b3734bf
TASK_BLOB_SHA: 2160c87fed9e23c582eb47cd8ae0e8358fb3a13e
ADR_032_BLOB_SHA: 22c300f882327aa812ad5e3250bf53ba8cf85eb5
BLUEPRINT_BLOB_SHA: 2c938752f70fd22070baaf5b1b22aa6f68f7f3b6
RESULT_BLOB_SHA: 72873f9f960ab28ddd58f3896b3c2c457f39c873
BRIDGE_BLOB_SHA: b0f8595330a96c37f127fce0df4717f92dda196e
EXECUTOR_AUTOMATION_BLOB_SHA: cc0deba1e92177b0ffc669a07d93c38294c5123e
UNIT_TEST_BLOB_SHA: cbd929389f055aa69c725091b056d85b207adb0b
BRIDGE_INTEGRATION_TEST_BLOB_SHA: 10b52d31b874fb4b0988606cbabd8018239505e1
```

Fresh final drift check:

```text
c323d532d49e8ca7505971108cd011924b3734bf -> ai/task-043
STATUS: identical
AHEAD: 0
BEHIND: 0
```

Fresh main / lineage check:

```text
main: 91813c04160cb664af47c5f0b04fea37ef9aa076
COMMITS_AHEAD_OF_BASELINE: 2
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: 91813c04160cb664af47c5f0b04fea37ef9aa076
```

Round-2 delta from the reviewed Round-1 head is exactly:

```text
.ai/results/RESULT-043.md
bridge.py
tests/test_bridge_executor_automation.py
```

No E1/E2/E3/M1/M4/M5/M10 contract module, provider, docs, E5, M11, H-Series, or unrelated Python Agent path changed in Round 2.

```text
SCOPE_AUDIT: PASS
ROUND_2_ALLOWED_FILES_ONLY: PASS
```

## Full Repository Gate

Bridge FIX publication reports:

```text
1408 passed, 7 skipped, 1533 warnings in 122.63s
exit code 0
```

```text
FULL_REPO_TESTS: PASS
REGRESSIONS_OBSERVED: 0
```

---

# R1-2 — CLOSED

Round 2 removes the post-spawn `SystemExit` recovery hole.

E4 now has bounded non-exiting Git observation helpers (`observe_e4_branch()` / `observe_e4_head()` through ordinary validation errors), and post-Executor / post-publication observation failures are converted into the E4 recovery path rather than escaping before state repair.

Executable tests now prove:

```text
post-executor branch observation failure -> RECOVERY_REQUIRED / zero publish / invoke count 1
post-executor HEAD observation failure   -> RECOVERY_REQUIRED / zero publish / invoke count 1
post-publish HEAD observation failure    -> RECOVERY_REQUIRED / exactly one publish / no retry
```

```text
R1-2: CLOSED
```

---

# R1-3 — CLOSED

Round 2 materially completes the locked Bridge-edge adversarial matrix.

Executable deterministic coverage now includes the previously missing behaviors:

```text
wrong workspace                       -> zero invoke
missing/wrong active lease            -> zero invoke
wrong authorized/current branch       -> zero invoke
non-codex authorization               -> zero invoke
dispatch operation mismatch           -> zero invoke
selected executor absent/ineligible   -> zero invoke
Executor HEAD advance                 -> zero publish + RECOVERY_REQUIRED
post-publish integrity mismatch       -> RECOVERY_REQUIRED
bounded publication notes             -> no raw TASK/ADR/context payload
cmd_publish full-test failure          -> fail closed
Git-admin drift tests                  -> zero publish
single fake E2 invocation              -> preserved
```

The unit/helper matrix from Round 1 remains unchanged and green.

```text
R1-3: CLOSED
```

---

# R1-1 — STILL OPEN

FINDING_ID: R1-1
SEVERITY: HIGH
TITLE: Pre-existing custom `core.hooksPath` hook contents are not included in the publication-trust snapshot

## Round-2 Progress

Round 2 correctly adds an `E4PublicationTrustSnapshot` and verifies it immediately after E2 returns, before worktree Git evidence and before `cmd_publish()`.

The snapshot now protects, with bounded filesystem identity:

```text
.git locator identity
common/worktree config files
$GIT_DIR-derived hooks directory
common/worktree info/attributes
common/worktree info/exclude
effective Git config fingerprint
publication remote identity
```

It also handles linked-worktree / external-gitdir layouts and correctly blocks mutations to the default hook directory, local remote config, changes to `core.hooksPath` itself, and info attributes/exclude.

This is substantial progress, but it does not yet satisfy the original R1-1 close condition.

## Residual Root Cause

The active hooks directory is currently resolved as:

```text
git rev-parse --path-format=absolute --git-path hooks
```

and that path is stored as `hooks_path` / `active_hooks` in the protected snapshot.

That command resolves the Git-directory hooks location (`$GIT_DIR/hooks`, accounting for Git path relocation). It does not make the snapshot follow a pre-existing `core.hooksPath` override to the directory from which Git will actually load hooks.

The effective-config fingerprint does include the `core.hooksPath` configuration value, so changing that value after E2 is detected. However, if `core.hooksPath` was already configured before E2 and remains unchanged, the contents of that custom active hook directory are not part of `protected_entries`.

Therefore this sequence remains possible under the current trust model:

```text
pre-existing core.hooksPath -> custom hook directory
E4 captures snapshot
Executor changes a hook file inside that pre-existing custom directory
core.hooksPath value itself remains unchanged
protected default $GIT_DIR/hooks remains unchanged
E4 trust verification can pass
Bridge later calls cmd_publish()
Git commit/push can execute the modified active hook outside the E2 sandbox
```

This is exactly the original close-condition requirement:

```text
active hooks path AND hook contents must be publication-trust-bound
```

and therefore R1-1 cannot be closed yet.

## BROKEN_INVARIANT

```text
ADR-032 Decision 4:
.git/** is forbidden Executor scope and out-of-scope mutation must block publication.

ADR-032 Decision 12:
EXITED_ZERO may proceed only after all Git/scope gates.

R1-1 CLOSE CONDITION:
Executor must not be able to mutate publication-relevant Git administration invisibly and still reach cmd_publish().
```

## REQUIRED_BEHAVIOR

Extend the existing bounded publication-trust snapshot; do not redesign E4.

Before E2 invocation:

1. Determine whether an effective `core.hooksPath` is configured.
2. Resolve the actual active hooks directory using Git's `core.hooksPath` semantics.
   - If no override exists, keep the existing resolved default Git hooks directory.
   - If an absolute override exists, bind that exact directory.
   - If a relative override exists, resolve it against the correct non-bare working-tree hook execution base; if E4 cannot prove the semantics safely, fail closed before invocation rather than guess.
3. Snapshot the actual active hook directory contents with the existing bounded filesystem hashing rules.
4. Store the resolved active hook path in the immutable pre-E2 trust snapshot.

Immediately after E2 and before any publication:

```text
actual active hook path identity unchanged
actual active hook contents unchanged
```

must be mechanically proven from the pre-E2 snapshot.

Changing the config value OR changing any content in the already-configured active hook directory must independently block publication.

The verification must remain bounded and must preserve the user's pre-existing hooks/configuration; do not disable hooks or rewrite configuration as a shortcut.

## FORBIDDEN_IMPLEMENTATIONS

- Do not simply keep hashing `$GIT_DIR/hooks` when `core.hooksPath` points elsewhere.
- Do not treat a stable config fingerprint as proof that referenced hook contents are stable.
- Do not disable hooks via temporary config or environment mutation as a substitute for trust binding.
- Do not add custom hook paths to `EXECUTOR_ALLOWED_PATHS_JSON` as a workaround.
- Do not reset, clean, stash, revert, delete, or repair Executor/admin state.
- Do not modify E1/E2/E3/M1/M4/M5/M10 contracts.
- Do not implement E5, M11, or H-Series.

## REQUIRED_TESTS

Use temporary repositories and fake transport only; no real Codex invocation.

1. Configure a custom `core.hooksPath` **before** E4 snapshot capture, place an executable `pre-commit` hook there, then have fake E2 modify only that hook plus one otherwise-allowed worktree file. Require:

```text
invoke count = 1
publisher calls = 0
state = RECOVERY_REQUIRED
```

2. Repeat with a custom hooks path located under Git administration (for example a non-default hook directory under the resolved common Git directory), proving the non-default Git-admin hook content is protected.

3. Cover a relative `core.hooksPath` fixture and prove E4 resolves/protects the same directory Git would use for this non-bare repository.

4. Pre-existing custom hooks path unchanged + allowed worktree mutation must preserve the E4 happy path.

5. Linked-worktree fixture with a pre-existing custom hooks path must either resolve/protect the exact active hook directory or fail closed before fake E2 invocation; it must never silently fall back to the default hooks directory.

6. Every post-spawn trust failure remains bounded, preserves work/admin state, invokes fake E2 at most once, and never retries or publishes.

## CLOSE_CONDITIONS

R1-1 closes only when independent review can prove all of the following:

```text
DEFAULT_HOOKS_DIRECTORY_BOUND: YES
CUSTOM_CORE_HOOKSPATH_VALUE_BOUND: YES
CUSTOM_CORE_HOOKSPATH_CONTENT_BOUND: YES
RELATIVE_HOOKSPATH_SEMANTICS_PROVEN_OR_FAIL_CLOSED: YES
LINKED_WORKTREE_CUSTOM_HOOKS_PROVEN_OR_FAIL_CLOSED: YES
GIT_ADMIN_DRIFT -> RECOVERY_REQUIRED: YES
ZERO_AUTO_PUBLICATION_ON_DRIFT: YES
NO_RETRY: YES
```

## ALLOWED_FILES

```text
bridge.py
tests/test_bridge_executor_automation.py
```

`src/aios_bridge/executor_automation.py` and its unit test remain allowed only if a pure model change is genuinely required; no change is currently expected.

## FORBIDDEN_SCOPE

All locked contract modules, providers, docs, E5, M11, H-Series, and unrelated Python Agent code.

---

## Round-2 Decision

```text
BLOCKING_FINDINGS: 1
HIGH: 1
MEDIUM: 0
R1-1: OPEN
R1-2: CLOSED
R1-3: CLOSED
FINAL_INDEPENDENT_AUDIT: CHANGES_REQUIRED
E4: NOT_YET_PASS
E5_PROVEN: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
```

Human must explicitly authorize another FIX. Executor never decides that R1-1 is closed.