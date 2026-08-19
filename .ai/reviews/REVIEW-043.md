# REVIEW-043 — E4 Result Collection + Auto Publication

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO

## Review Round

Round 1 — independent lineage, scope, authority, control-snapshot, M1/M4/E3/E2 composition, post-executor Git integrity, publication, recovery, and adversarial-test audit.

## Authoritative Anchors

```text
TASK_ID: TASK-043
BASELINE_MAIN_SHA: 91813c04160cb664af47c5f0b04fea37ef9aa076
TASK_BRANCH: ai/task-043
ROUND_1_TASK_HEAD_SHA: 14d39006f370dd8e14406a4416dfde91ac7ecba2
TASK_BLOB_SHA: 2160c87fed9e23c582eb47cd8ae0e8358fb3a13e
ADR_032_BLOB_SHA: 22c300f882327aa812ad5e3250bf53ba8cf85eb5
BLUEPRINT_BLOB_SHA: 2c938752f70fd22070baaf5b1b22aa6f68f7f3b6
RESULT_BLOB_SHA: a680e31cb686c155628c3d4e33065140fffe0d22
BRIDGE_BLOB_SHA: 45f974611032400da38034cf40a248aa034b212d
EXECUTOR_AUTOMATION_BLOB_SHA: cc0deba1e92177b0ffc669a07d93c38294c5123e
UNIT_TEST_BLOB_SHA: cbd929389f055aa69c725091b056d85b207adb0b
BRIDGE_INTEGRATION_TEST_BLOB_SHA: ef3dcc81428bd4496e52b0024993dc4f941634a0
```

Fresh branch drift check:

```text
14d39006f370dd8e14406a4416dfde91ac7ecba2 -> ai/task-043
STATUS: identical
AHEAD: 0
BEHIND: 0
```

Lineage from baseline:

```text
COMMITS_AHEAD_OF_BASELINE: 1
COMMITS_BEHIND_BASELINE: 0
MERGE_BASE: 91813c04160cb664af47c5f0b04fea37ef9aa076
```

Changed paths are exactly:

```text
.ai/results/RESULT-043.md
bridge.py
src/aios_bridge/executor_automation.py
tests/aios_bridge/test_executor_automation.py
tests/test_bridge_executor_automation.py
```

SCOPE_AUDIT: PASS

## Passing Contract Areas

The following E4 areas are implemented in the intended architecture and are not findings in Round 1:

```text
APPROVE_EXECUTE_SEPARATION: PASS
EXECUTE_REQUIRES_ACTIVE_AUTH: PASS
EXECUTE_ACQUIRES_LEASE: NO
CODEX_ONLY_AUTOMATION_V1: PASS
CONTROL_SINGLE_SNAPSHOT: PASS
RAW_GIT_BLOB_BYTES: PASS
EXACT_CONTEXT_MARKER_PARSER: PASS
EXACT_ALLOWED_PATH_MARKER_PARSER: PASS
M1_STATE_REUSED: PASS
M4_REQUEST_PREPARED_REUSED: PASS
M10_POLICY_USED_AS_CAPABILITY_CONTRACT_ONLY: PASS
E3_CONTEXT_PACK_REUSED: PASS
E2_CODEX_TRANSPORT_REUSED: PASS
SINGLE_INVOKE_PER_EXECUTE_CALL: PASS
NO_AUTOMATIC_RETRY_LOOP: PASS
NO_AUTO_MERGE: PASS
EXISTING_CMD_PUBLISH_REUSED: PASS
FIXED_FULL_SUITE_COMMAND: PASS
POST_PUBLISH_M4_RESULT_CONSTRUCTION: PASS
E1_E2_E3_M1_M4_M5_M10_CONTRACT_FILES_UNCHANGED: PASS
```

Bridge publication reports:

```text
1407 passed, 7 skipped, 1533 warnings in 131.76s
exit code 0
```

FULL_REPO_TESTS: PASS
REGRESSIONS_OBSERVED: 0

A green full suite does not close the findings below because the missing adversarial paths are not exercised by the current tests.

---

# FINDING R1-1

FINDING_ID: R1-1
SEVERITY: HIGH
TITLE: Git administrative mutation is outside the dirty-path scope gate and can influence auto-publication

## ROOT_CAUSE

E4's post-executor scope evidence is derived from:

```text
git diff --name-status -z HEAD
git ls-files --others --exclude-standard -z
```

followed by exact branch/HEAD equality and an allowed worktree-path subset check.

That proves ordinary Git worktree/index-visible paths, but it does not observe repository administrative state under the actual Git directory (`.git/**` or an external gitdir).

ADR-032 Decision 4 explicitly makes `.git/**` forbidden Executor scope and requires out-of-scope mutation to block publication. The current implementation has no independent Git-administration trust check before it delegates to `cmd_publish()`.

This matters because publication subsequently executes trusted Git operations outside the Codex sandbox. Executor-created or Executor-modified Git administration can change their behavior without appearing in the E4 dirty set. Examples of publication-relevant state include:

```text
.git/config / config.worktree
active hooks / core.hooksPath
.git/info/attributes
.git/info/exclude
remote configuration used by push
```

A modified hook can execute during Bridge commit/push outside E2's sandbox. A modified local config can redirect or alter publication behavior. `.git/info/attributes` can alter staging/clean-filter semantics. These changes are invisible to the current worktree-only dirty collector.

## BROKEN_INVARIANT

```text
ADR-032 Decision 4:
.git/** is forbidden Executor scope.
Any out-of-scope mutation blocks publication.

ADR-032 Decision 12:
EXITED_ZERO may proceed only after all Git/scope gates.

ADR-032 Decision 13:
existing cmd_publish is invoked only after E4 integrity gates are proven.
```

Current implementation proves only worktree-visible scope, not publication-critical Git administrative integrity.

## REQUIRED_BEHAVIOR

Before E2 invocation, E4 must capture a bounded publication-trust snapshot of the repository Git administration using a mechanism that does not depend on post-Executor Git configuration being trustworthy.

Immediately after E2 returns, and before running Git status/diff evidence that could be influenced by changed Git configuration and before `cmd_publish()`, E4 must prove that publication-critical Git administration is unchanged.

At minimum the protection must cover the local repository state capable of changing status/staging/commit/push behavior, including:

```text
local config / config.worktree if present
active hooks path and hook contents
info/attributes if present
info/exclude if present
configured remote identity used by Bridge publication
```

Equivalent stronger fail-closed designs are allowed if they mechanically prove the same invariant.

Git index changes do not need to be categorically forbidden if they remain safely normalized by the existing `git add -A` publication path and cannot bypass the final worktree scope proof. Branch/HEAD remain governed by the existing exact branch/HEAD gate.

If the protected Git administration drifts after Executor invocation:

```text
publication = FORBIDDEN
state = RECOVERY_REQUIRED
worktree/admin state = PRESERVED for Human recovery
retry = NO
```

## FORBIDDEN_IMPLEMENTATIONS

- Do not treat `.git` as an allowed Executor path.
- Do not rely on `git status` / `git diff` alone to prove `.git` integrity.
- Do not reset, clean, stash, revert, delete, or silently repair Executor state.
- Do not disable or rewrite a user's pre-existing Git configuration as a substitute for before/after identity proof.
- Do not add a generic H-Series Driver/Envelope/Event Journal abstraction.
- Do not modify E1/E2/E3/M1/M4/M5/M10 contracts.

## REQUIRED_TESTS

Use temporary Git repositories and fake transport only. No real Codex call.

1. Fake Codex makes one allowed worktree mutation and changes a local Git hook that would run on commit -> zero publisher calls, `RECOVERY_REQUIRED`.
2. Fake Codex makes one allowed worktree mutation and changes local Git config / remote or `core.hooksPath` -> zero publisher calls, `RECOVERY_REQUIRED`.
3. Fake Codex changes `.git/info/attributes` -> zero publisher calls, `RECOVERY_REQUIRED`.
4. Unchanged Git administration + allowed worktree mutation preserves the E4 happy path.
5. Every failure above still has exactly one fake E2 invocation and no retry.

## ADVERSARIAL_CHECKS

- Protect the actual resolved Git directory, including worktree/external-gitdir layouts; do not assume literal `<repo>/.git` is always a directory.
- Git-admin verification must happen before auto-publication and must not be bypassed by an altered local Git config.

## CLOSE_CONDITIONS

R1-1 closes only when independent review can prove that an Executor cannot mutate publication-relevant Git administrative state invisibly and still reach `cmd_publish()`.

## ALLOWED_FILES

```text
bridge.py
src/aios_bridge/executor_automation.py          # only if a pure model/helper is genuinely needed
 tests/test_bridge_executor_automation.py
 tests/aios_bridge/test_executor_automation.py  # only if helper behavior changes
```

## FORBIDDEN_SCOPE

All E1/E2/E3/M1/M4/M5/M10 contract modules, providers, docs, E5, M11, H-Series, unrelated Python Agent code.

---

# FINDING R1-2

FINDING_ID: R1-2
SEVERITY: MEDIUM
TITLE: Post-spawn Git observation failures can bypass the required RECOVERY_REQUIRED transition

## ROOT_CAUSE

After `transport.invoke()` returns, `cmd_execute()` performs:

```python
post_branch = current_branch()
post_head_sha = git("rev-parse", "HEAD").stdout.strip()
```

inside an `except Exception` recovery boundary.

The existing `git()` helper calls `fail()` on a nonzero Git command, and `fail()` raises `SystemExit`. `SystemExit` is not an `Exception`, so a post-Executor Git failure can escape the E4 recovery boundary without calling `_e4_operational_failure(..., "RECOVERY_REQUIRED", ...)`.

The same pattern is present in the post-publication HEAD verification.

This is most important after Executor spawn, where Git failure means repository state is uncertain and ADR-032 requires explicit recovery semantics.

## BROKEN_INVARIANT

```text
ADR-032 Decision 15:
branch/HEAD drift or partial uncertain execution -> RECOVERY_REQUIRED
no silent cleanup/retry

ADR-032 Decision 14:
post-publication integrity failure -> RECOVERY_REQUIRED
```

## REQUIRED_BEHAVIOR

All Git probes used after Executor spawn and in post-publication verification must report failure through a non-exiting bounded helper or be explicitly converted into the E4 recovery path.

Requirements:

```text
post-executor branch/HEAD observation failure
  -> zero auto-publication
  -> RECOVERY_REQUIRED
  -> no retry

post-publication HEAD/integrity observation failure
  -> RECOVERY_REQUIRED
  -> no history rewrite / force push
```

Do not broadly catch `BaseException` in a way that swallows `KeyboardInterrupt` or unrelated termination signals. Prefer local non-exiting Git probes returning/raising ordinary validation errors.

## FORBIDDEN_IMPLEMENTATIONS

- Do not change global `fail()` semantics for the whole Bridge merely to close E4.
- Do not swallow KeyboardInterrupt.
- Do not reset/clean the repository.
- Do not rerun Codex automatically.

## REQUIRED_TESTS

1. After one fake E2 invocation, force post-executor branch observation failure -> `RECOVERY_REQUIRED`, zero publisher, invoke count 1.
2. After one fake E2 invocation, force post-executor HEAD observation failure -> `RECOVERY_REQUIRED`, zero publisher, invoke count 1.
3. After a fake successful publisher, force post-publish HEAD observation failure -> `RECOVERY_REQUIRED`; no second publish and no history rewrite.

## CLOSE_CONDITIONS

No post-spawn Git observation error may escape as a raw `SystemExit` before E4 records the required recovery state.

## ALLOWED_FILES

```text
bridge.py
tests/test_bridge_executor_automation.py
```

## FORBIDDEN_SCOPE

Unrelated Bridge lifecycle semantics and all locked contract modules.

---

# FINDING R1-3

FINDING_ID: R1-3
SEVERITY: MEDIUM
TITLE: Locked E4 adversarial integration matrix is incomplete

## ROOT_CAUSE

The current integration file proves the binary Git helper, rename/untracked collector, one happy path, four transport statuses, no-auth, one generic control-drift path, one out-of-scope untracked path, receipt-write failure, basic no-authority-call source inspection, and CLI exposure.

However ADR-032 Decision 17 and locked blueprint section 26 explicitly require additional Bridge-edge adversarial cases before E4 acceptance. Several are currently absent as executable integration proofs.

## BROKEN_INVARIANT

```text
TASK-043 BLUEPRINT §26 — Bridge Integration Tests
MUST cover the required cases before E4 PASS.
```

## REQUIRED_BEHAVIOR / REQUIRED_TESTS

Add deterministic fake/mocked integration coverage for every currently unproven required case, including at minimum:

1. wrong authorization workspace -> zero invoke;
2. wrong/missing exact active lease -> zero invoke;
3. wrong current/authorized branch -> zero invoke;
4. non-codex active executor -> zero invoke;
5. dispatch policy operation mismatch -> zero invoke;
6. selected executor absent/ineligible -> zero invoke;
7. fake Executor commits/advances HEAD -> zero publisher + `RECOVERY_REQUIRED`;
8. post-publish integrity mismatch -> `RECOVERY_REQUIRED`;
9. fixed E4 RESULT notes remain bounded and contain no raw payload/context;
10. existing `cmd_publish` full-test failure remains fail-closed with no commit/push/lease consumption regression in the E4 call path.

R1-1 and R1-2 required tests may satisfy overlapping blueprint cases, but the full locked matrix must be mechanically accounted for.

## FORBIDDEN_IMPLEMENTATIONS

- No real Codex invocation.
- No weakening assertions to implementation-detail smoke tests when the blueprint requires behavior-level proof.
- Do not mark a required case covered solely because the implementation appears correct by inspection.

## CLOSE_CONDITIONS

Independent re-review can map each required ADR-032 / blueprint §25-26 adversarial behavior to an executable deterministic test and all targeted/full suites are green.

## ALLOWED_FILES

```text
tests/test_bridge_executor_automation.py
tests/aios_bridge/test_executor_automation.py
```

plus production files only when needed to close R1-1/R1-2.

## FORBIDDEN_SCOPE

No unrelated coverage expansion, E5, M11, H-Series, or locked contract modifications.

---

## Round-1 Decision

```text
BLOCKING_FINDINGS: 3
HIGH: 1
MEDIUM: 2
R1-1: OPEN
R1-2: OPEN
R1-3: OPEN
FINAL_INDEPENDENT_AUDIT: CHANGES_REQUIRED
E4: NOT_YET_PASS
E5_PROVEN: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
```

Human must explicitly authorize FIX. Executor does not decide that findings are closed.
