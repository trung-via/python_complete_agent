# REVIEW-059 — M11.3B Runtime Paid-API Proof Preflight + Canonical Provenance Lock

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Review Binding

```text
TASK_ID: TASK-059
TARGET_BRANCH: ai/task-059
CURRENT_MAIN_SHA: 2a91334876e4a60be9eb278e21ea57d55bb884d3
TASK_ARTIFACT_BLOB_SHA: e62ff217abe3e57f7de461a0c6132f6da2c78354
RESULT_BLOB_SHA: ae9ed88238782cf21740bdbe75ba072cf026b86a
PROOF_LOCK_BLOB_SHA: 455491c12c1e7099f79f373c15ca8d470b7d4ca7
INPUT_COUNTER_BLOB_SHA: d0a63f03883dac8972cdba9af2ebb6a5eddfb583
PREFLIGHT_MODULE_BLOB_SHA: 542e6207d1f7dc8e9bd5ff3005a0aa384fa8d193
COUNTER_TEST_BLOB_SHA: fdf6f8849e84d2bd152a9cda75cb5b561ad8a142
PREFLIGHT_TEST_BLOB_SHA: cf953cb8e8a522bd4001eb9dee548eb474f3f8b9
BRIDGE_PREFLIGHT_TEST_BLOB_SHA: 89f7fad201dba5d7fe7869c96a44fb3d7d65e430
```

GitHub compare at review time:

```text
main -> ai/task-059: DIVERGED
ahead_by: 1
behind_by: 11
merge_base: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
current main: 2a91334876e4a60be9eb278e21ea57d55bb884d3
```

The task artifact explicitly superseded the historical blueprint baseline and requires execution from current main `2a913348...`. The published branch does not satisfy that ancestry.

## Positive Findings

The implementation contains substantial correct M11.3B work:

- changed implementation paths match the eight authorized TASK-059 paths; `.ai/results/RESULT-059.md` is publication output;
- executor identity is `antigravity`, with no executor failover or hot handoff in RESULT;
- `MiniMaxM3ProofLock` is frozen/slotted and enforces exact field set, duplicate-key rejection, strict UTF-8 JSON, lowercase SHA-256 digests, pinned dependency/source constants, canonical JSON/fingerprint, and an explicit MiniMax HTTPS endpoint allowlist;
- local asset validation binds manifest digests and actual file digests to the proof lock before Jinja/tokenizer engine construction;
- preflight validates active grant/task/workspace/provider/model/artifact bindings, exact package versions, deterministic external asset/ledger locations, credential presence after earlier gates, and leaves paid dispatch/provider-call state false;
- no evidence of a real MiniMax call, real paid spend, grant consumption, package installation, or asset download occurred in the published execution;
- published test evidence is green on the tree that actually ran: targeted suites `40 passed`; full suite `1841 passed, 7 skipped, 0 failed`, exit 0.

These positives do not override the blockers below.

## B1 — CRITICAL: execution branch is not based on the authorized current main

TASK-059 artifact requires:

```text
MAIN_SHA: 2a91334876e4a60be9eb278e21ea57d55bb884d3
```

RESULT-059 also claims that SHA as `Base Main SHA`.

Actual Git ancestry contradicts the receipt:

```text
merge_base(main, ai/task-059) = 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
ai/task-059 is 11 commits behind current main
```

Therefore the published full-suite proof ran on a stale pre-TASK-060 tree. The `1841 passed / 7 skipped` evidence is not a valid current-main integration proof.

Root cause observed in current Bridge logic: `prepare_task_branch(..., RUN)` safely reconciles `main`, but if a local `ai/task-N` branch already exists and the remote task branch does not, it resumes that local branch without verifying that its HEAD is descended from / equal to the newly reconciled canonical main. TASK-059 had an old local branch from the earlier interrupted attempt, so the fresh RUN reused stale ancestry.

Required before any merge:

```text
1. Preserve the current published implementation and RESULT as forensic/review evidence.
2. Reconcile ai/task-059 onto exact current main 2a913348... without force-pushing or losing the published commit.
3. Only after lineage is current may the Human authorize FIX TASK-059.
4. Re-run targeted + full repository tests after reconciliation and fixes.
```

Do NOT merge the current branch and do NOT treat RESULT-059's Base Main label as ancestry proof.

The generic stale-local-RUN branch-resume weakness should be hardened separately before relying on another reissued RUN; it is a control-plane defect discovered by this execution.

## B2 — CRITICAL: `paid-proof-preflight` violates the offline / NETWORK:NO contract

The TASK-059 contract is explicit:

```text
P0 -> P7 exact order
preflight MUST NOT perform network access
NETWORK: NO
```

Current `cmd_paid_proof_preflight()` begins with:

```python
cfg = load_config()
fetch_control(cfg)
```

Current `fetch_control(cfg)` executes Git fetch operations against the configured remote. That is network-capable I/O and occurs before P0.

This violates both:

```text
OFFLINE_PREFLIGHT: REQUIRED
NETWORK: NO
P0 must be the first preflight gate
```

The current Bridge test masks this defect by monkeypatching `bridge.fetch_control` to a no-op, so the required `no ... network ... surface` proof is not actually tested.

Required fix:

```text
- paid-proof-preflight must not call fetch_control(), git fetch, HTTP, provider transport, or any other network-capable operation;
- operate only on already-present local canonical tracking/control refs and fail closed if required refs/blobs are unavailable;
- preserve exact P0 -> P7 ordering;
- add a regression test that fails if preflight invokes fetch_control / git fetch / any network-capable path.
```

No weakening of the canonical proof-lock blob requirement is allowed.

## B3 — HIGH: EXACT_LOCK_TYPE contract is not enforced

TASK-059 locks:

```text
EXACT_LOCK_TYPE: REQUIRED
```

But `MiniMaxM3LocalProviderInputCounter` and its internal lock-validation helpers currently use:

```python
isinstance(proof_lock, MiniMaxM3ProofLock)
```

`isinstance` accepts subclasses, so this is not exact-type enforcement.

The test named `test_construction_requires_exact_proof_lock_type` only rejects `None` and a mapping; it does not attempt a `MiniMaxM3ProofLock` subclass. Therefore the test name overstates the proof.

Required fix:

```text
- require `type(proof_lock) is MiniMaxM3ProofLock` at the production counter boundary and relevant internal validation boundaries;
- add a concrete MiniMaxM3ProofLock subclass rejection test;
- retain the existing exact trusted-counter registry semantics.
```

## B4 — HIGH: filesystem failure can leak an absolute runtime path into CLI output

TASK-059 locks:

```text
Only a logical runtime-relative ledger path may enter receipt/output.
Never print/persist the absolute user-specific runtime path as proof metadata.
```

`probe_ledger_durability()` currently wraps filesystem exceptions using the raw exception text:

```python
raise PaidApiProofPreflightError(
    f"ledger directory durability probe failed: {exc}"
)
```

`cmd_paid_proof_preflight()` then prints that exception through `fail(...)`.

Filesystem exceptions commonly include the absolute path that failed. Because `ledger_path` is constructed under the external absolute runtime root, a P6 failure can expose a user-specific absolute runtime path even though the success receipt is clean.

Required fix:

```text
- sanitize P6/runtime filesystem failures to bounded path-free diagnostics;
- never interpolate raw filesystem exceptions that may contain the absolute runtime path into user-visible proof output;
- add a regression test using an OSError containing a sentinel absolute path and prove the sentinel is absent from stdout/stderr/receipt.
```

## B5 — MEDIUM: canonical `.ai/` proof-lock path is not explicitly validated

The CLI contract requires:

```text
--proof-lock-path <canonical .ai/ path>
```

The current parser accepts an arbitrary string and the command resolves that path on the control ref. No explicit normalized `.ai/...` path guard was found.

Required fix:

```text
- require a normalized repository-relative POSIX path under `.ai/`;
- reject absolute paths, drive prefixes, backslashes, `.`/`..` traversal segments, empty segments, and non-`.ai/` locations;
- add parser/command regression tests for these cases.
```

## Publication Evidence Note

RESULT-059 `Files Changed` lists all eight implementation paths, which matches the independent compare. Its `Diff Stat`, however, lists only the three pre-existing tracked files because the initial publication computes `git diff --stat HEAD` before staging and therefore omits untracked new files. This is not the primary reason for rejection, but the next RESULT must not be treated as the sole scope authority; independent Git compare remains required.

## Required FIX Verification

After lineage is reconciled and Human explicitly authorizes FIX, the new publication must prove at minimum:

```text
LINEAGE_CURRENT_MAIN: PASS
OFFLINE_PREFLIGHT_NO_NETWORK: PASS
P0_TO_P7_ORDER: PASS
CANONICAL_PROOF_LOCK_BLOB: PASS
EXACT_LOCK_TYPE: PASS
COUNTER_MANIFEST_AND_BYTES_BOUND_TO_LOCK: PASS
ABSOLUTE_PATH_LEAK_ON_FAILURE: NONE
CANONICAL_DOT_AI_PROOF_LOCK_PATH: PASS
REAL_PAID_API_CALL: NO
REAL_API_KEY_LEAK: NO
GRANT_CONSUMED: NO
PAID_DISPATCH: NO
TARGETED_TESTS: PASS
FULL_REPOSITORY_TESTS_ON_RECONCILED_TREE: PASS
```

## Gate

```text
CURRENT_VERDICT: CHANGES_REQUIRED
CURRENT_BRANCH_MERGE: FORBIDDEN
IMMEDIATE_FIX_COMMAND: BLOCKED UNTIL LINEAGE RECOVERY
```

After explicit lineage recovery, the next semantic operation is Human-authorized `FIX TASK-059` with Antigravity. No Codex reroute, no paid API call, no M11.3C, and no automatic retry.