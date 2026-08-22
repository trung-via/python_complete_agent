# REVIEW-062 — M11.3C Real Operational Escape Harness

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Independent Review Binding

```text
TASK_ID: TASK-062
BASELINE_MAIN_SHA: d6f51f14188ffc56fd06bc887b68d9cad550c9e0
REVIEWED_TASK_HEAD_SHA: 82f461f5373f70d03f3035b021ae0fe1fc7c03d0
TARGET_BRANCH: ai/task-062
TASK_BLOB_SHA: 550add135a201c627aaac98b8fce26b1c9c93ace
BLUEPRINT_BLOB_SHA: 5b9a6a366a390a2f9f0735ebeff022cf62c9b551
RESULT_BLOB_SHA: 514c797febcbb2093e00eab237b9d89bb0492251
BRIDGE_BLOB_SHA: 8ded432ba05d3bc9ff1d293d772cac15cef07196
INPUT_COUNTER_BLOB_SHA: 28928665d71e0bb818a8e4ff41281dd39d29105a
REAL_ESCAPE_BLOB_SHA: b3e7326ff462b92a8690a797570c97e95ea9dc5d
INPUT_COUNTER_TEST_BLOB_SHA: a293817b9a9e8a40fad5a1f354b52fc5f6da8021
REAL_ESCAPE_TEST_BLOB_SHA: 2a8f41eadafe7df5fc9cc8c5def95e13cefd7032
BRIDGE_REAL_ESCAPE_TEST_BLOB_SHA: 94c13df5982c9dd4fd090e3d7025806f09d157fb
```

GitHub comparison proves:

```text
main -> ai/task-062: ahead 1 / behind 0
merge-base: d6f51f14188ffc56fd06bc887b68d9cad550c9e0
scope: exact six authorized implementation/test paths + RESULT-062 publication output
executor: codex
executor failover: NO
hot handoff: NO
```

## What Passed

The implementation has a strong core and should be FIXED, not discarded.

```text
LINEAGE: PASS
WRITABLE_SCOPE: PASS
CODEX_EXECUTOR_IDENTITY: PASS
NO_EXECUTOR_FAILOVER: PASS
CONTEXT_COUNTER_SEAM: PASS
BASE_M10_DEFAULT_DENY_PROOF: PASS
CONSUME_BEFORE_CALL_REUSE: PASS
DEFERRED_REAL_PROVIDER_CONSTRUCTION: PASS SUBJECT TO B1
ONE_PROVIDER_CALL_GUARD: PASS
NO_RETRY: PASS
OPERATIONAL_PROOF_REUSE: PASS
REPLAY_REJECTS_CONSUMED_GRANT: PASS
NO_EXECUTOR_AUTHORITY: PASS
FULL_REPOSITORY_SUITE: PASS (1914 passed, 7 skipped, 0 failed)
```

## B1 — CRITICAL — Real credential value is read before R5-R7

The locked blueprint says:

```text
Real credential value may exist only in provider process memory/environment after R0-R7 pass.
```

The Bridge live command currently does this during R4, before capacity validation (R5), dispatch proof (R6), and full input budget proof (R7):

```python
credential_value = os.environ.get(proof_lock.credential_env_name, "")
if type(credential_value) is not str or not credential_value.strip():
    ...
del credential_value
```

This retrieves the real secret value too early even though it does not print or persist it. Provider construction itself is correctly deferred, but secret-value access is still outside the locked R0-R7 boundary.

### Required fix

Before R7, credential handling may prove PRESENCE ONLY without retrieving the value. Use a key-presence check or an equivalent bounded helper that cannot read the value. The actual value may be retrieved only inside the deferred provider factory after the full pre-call gates and durable consume transition permit the one call.

Add a regression test that makes credential VALUE access fatal before provider factory invocation while allowing presence inspection. Prove replay and every R0-R7 failure reach zero credential-value reads.

## B2 — HIGH — External proof persistence can escape runtime root through symlink/junction parents

`persist_paid_api_real_escape_artifacts()` resolves `runtime_root`, then constructs:

```text
<root>/paid_api_proofs/<TASK>/<grant-hash>/...
```

but it does not reject symlink/junction/reparse-point parent components or re-prove resolved containment before creating/writing the staging namespace. A pre-existing `paid_api_proofs` or task directory that redirects outside the runtime root can cause proposal/proof artifacts to be written outside the required external-runtime boundary.

This violates:

```text
Persist two external-runtime artifacts ... under the exact task/grant namespace.
No worktree mutation.
```

### Required fix

Add bounded safe-path construction for every existing parent component from runtime root through `paid_api_proofs` and `TASK-N`. Reject symlink/junction/path-escape components fail-closed. Re-check containment before write/rename and after final publication as appropriate. Do not expose absolute paths in errors.

Add regression tests for at least:

```text
symlink paid_api_proofs parent -> outside => reject before artifact write
symlink TASK-N parent -> outside => reject
normal real directory path => persists successfully
```

On Windows, account for junction/reparse semantics where supported; tests may skip only when the platform genuinely cannot create the required link type.

## B3 — MEDIUM — Absolute-path proposal sanitizer has a POSIX single-component gap

The current POSIX absolute-path regex requires at least one internal slash after the root slash. Therefore valid absolute paths such as:

```text
/tmp
/etc
/Users
```

can pass `_validate_proposal_content()`, although the locked proof artifact contract forbids absolute machine paths.

The existing regression covers `/home/user/private/...` but not single-component root paths.

### Required fix

Harden absolute-path rejection so all canonical absolute POSIX paths, including a single component after `/` and root-like variants relevant to the parser, fail closed without creating false permission for machine-path output. Preserve URL/non-path behavior as intended by the fixed PLAN prompt.

Add regression tests for at least `/tmp` and `/etc` (and any additional delimiter forms needed by the chosen parser).

## B4 — MEDIUM — RESULT-062 evidence is incomplete/inaccurate for the locked acceptance contract

`RESULT-062.md` correctly lists six changed implementation/test paths, but its `Diff Stat` includes only three tracked-at-the-time paths:

```text
bridge.py
src/aios_bridge/minimax_m3_input_counter.py
tests/aios_bridge/test_minimax_m3_input_counter.py
```

It omits the three large newly-added paths:

```text
src/aios_bridge/paid_api_real_escape.py
tests/aios_bridge/test_paid_api_real_escape.py
tests/test_bridge_paid_api_real_escape.py
```

The RESULT records the full repository suite (`1914 passed, 7 skipped`) but does not record a separate targeted TASK-062 test command/result even though TASK-062 explicitly requires targeted tests plus full repository tests.

For this security-critical no-spend task the RESULT also should carry explicit execution-boundary evidence for:

```text
REAL_PAID_API_CALL_DURING_TASK: NO
REAL_API_KEY_USE_DURING_TASK: NO
REAL_GRANT_CONSUME_DURING_TASK: NO
```

### Required fix

On FIX publication, record truthful cumulative TASK-062 scope/diff evidence (or clearly distinguish FIX-delta from cumulative task delta), plus:

```text
exact targeted test command + exit code + pass/fail/skip counts
exact full test command + exit code + pass/fail/skip counts
explicit no-spend/no-real-secret/no-real-grant-consume markers
```

Do not fabricate evidence. If the executor cannot prove a marker, fail closed rather than claiming it.

## Required FIX Scope

Use the existing TASK-062 branch and exact Human FIX authorization. Do not RUN from scratch and do not use a second executor.

Preserve all already-correct semantics. Change only within the existing TASK-062 writable scope:

```text
bridge.py
src/aios_bridge/minimax_m3_input_counter.py
src/aios_bridge/paid_api_real_escape.py
tests/aios_bridge/test_minimax_m3_input_counter.py
tests/aios_bridge/test_paid_api_real_escape.py
tests/test_bridge_paid_api_real_escape.py
```

Bridge may update `.ai/results/RESULT-062.md` as publication output.

Do not modify M11.2C authority, grant semantics, ModelGateway, MiniMax provider, dispatch engine, executor transport, H-Series, TASK-061, or M11.3B contracts.

## Required Verification After FIX

At minimum run a focused TASK-062 suite covering the three TASK-062 test paths (and any directly modified counter tests), then the canonical full repository suite:

```text
venv/Scripts/python.exe -m pytest tests/ -q
```

Review must verify fresh branch lineage/scope and exact result evidence before PASS.

## Verdict

```text
TASK-062: CHANGES_REQUIRED
MERGE: FORBIDDEN
LIVE_MINIMAX_PROOF: FORBIDDEN
NEXT: Human may authorize `$aios-worker FIX TASK-062` on the Codex surface.
```

No real paid MiniMax call may occur until TASK-062 reaches PASS, is Human-merged, and a separate fresh Human paid-spend/live-proof authorization is issued.
