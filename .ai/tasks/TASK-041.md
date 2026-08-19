# TASK-041 — E2 Codex Local Transport

STATUS: READY
CLASS: L3 — CONCRETE EXECUTOR TRANSPORT / LOCAL PROCESS SAFETY / AUTHORITY PRESERVATION
EXECUTOR_MODE: THIN_EXECUTOR

## Baseline

```text
MAIN_SHA: 1c35ce096f366d9d87250b5e8ae1759327dc5a51
TARGET_BRANCH: ai/task-041
```

## Authoritative Contract

```text
ADR_PATH: .ai/decisions/ADR-030-E2-CODEX-LOCAL-TRANSPORT-CONTRACT-LOCK.md
ADR_BLOB_SHA: e5c0dd2214ea81ae01e903847d4563ab88f983cb
BLUEPRINT_PATH: .ai/context/TASK-041-E2-IMPLEMENTATION-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: f67686829c79c3e34973a981cda9d3d2042863ad
E1_CONTRACT_PATH: src/aios_bridge/continuity/executor_transport.py
E1_CONTRACT_BLOB_SHA: bbe7b517202ea446e727752955e004d9464934bd
```

## E-Series Position

```text
E1 — Executor Invocation Contract                  COMPLETE
E2 — Codex Local Transport                         ← THIS TASK
E3 — Bounded Context Pack Delivery
E4 — Result Collection + Auto Publication
E5 — Zero-Copy/Paste Operational Proof
```

H-Series remains separate and DEFERRED.

## Objective

Implement the first concrete E1 `ExecutionTransport`: a fail-closed local Codex headless process transport that accepts an already-constructed canonical `ExecutorInvocation` plus exact payload bytes and invokes the local authenticated Codex CLI safely.

E2 proves the concrete process boundary only.

It does NOT integrate transport invocation into Bridge yet and does NOT remove Human RUN/FIX/MERGE authority.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"claude-code","preference_rank":2,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX","RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

This marker is recommendation policy only. It grants no authority.

## Allowed Files

Exactly:

```text
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
tests/aios_bridge/test_codex_local_transport.py
.ai/results/RESULT-041.md        # Bridge-generated only
```

## Forbidden Scope

Do NOT modify:

```text
bridge.py
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/hot_handoff.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/external_brain/**
src/providers/**
docs/**
```

Do NOT implement:
- Bridge auto-invoke;
- auto approval;
- auto lease acquisition/release;
- auto publication;
- context-pack composition;
- result collection;
- real operational zero-copy proof;
- M11 API fallback;
- any H-Series abstraction.

## Required Concrete Surface

Implement exactly according to ADR-030 and the locked blueprint:

```text
CODEX_EXECUTOR_ID = codex
CODEX_TRANSPORT_ID = codex-local-v1
CodexLocalTransport
minimal child environment builder
bounded Codex executable resolution
read-only exact Git workspace preflight
safe fixed codex exec argv
exact stdin payload delivery
canonical InvocationReceipt mapping
bounded timeout / interruption cleanup
```

## Safe Invocation Invariant

The production argv must request:

```text
codex exec
--ephemeral
--json
--color never
--sandbox workspace-write
--ask-for-approval never
-c sandbox_workspace_write.network_access=false
-c web_search="disabled"
-C <exact workspace>
-
```

The final `-` receives exact payload bytes via stdin.

Production code MUST NOT construct or use:

```text
--dangerously-bypass-approvals-and-sandbox
--sandbox danger-full-access
--skip-git-repo-check
--add-dir
--full-auto
shell=True
```

No fallback to a weaker mode is allowed.

## Environment Invariant

The child receives a closed minimal OS/Codex environment allowlist only.

At minimum strip:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY
GEMINI_API_KEY
DEEPSEEK_API_KEY
MINIMAX_API_KEY
GITHUB_TOKEN
GH_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
AZURE_OPENAI_API_KEY
```

E2 relies on existing local Codex sign-in state and MUST NOT inject a paid API key.

## Workspace Invariant

Before Codex process creation, read-only preflight must prove:

```text
configured workspace exists
configured workspace is exact Git toplevel
current branch == invocation.target_branch
worktree status --porcelain --untracked-files=all is empty
```

E2 repairs none of these conditions.

## Receipt Invariant

`InvocationReceipt` remains transport evidence only.

Especially:

```text
EXITED_ZERO != task success
EXITED_ZERO != tests pass
EXITED_ZERO != RESULT published
EXITED_ZERO != review PASS
EXITED_ZERO != merge approval
```

No stdout/stderr/model prose is canonicalized as result evidence in E2.

## Windows Safety Invariant

Native Windows sandbox limitations MUST NOT be worked around with unsafe bypass flags.

If `workspace-write` cannot safely perform the requested operation on the installed Codex build, the transport/task may fail. That is preferable to silently escalating to full host access.

Real safe Windows workspace mutation is not declared proven until later operational proof.

## No Recursive Codex During TASK-041

The Human-authorized Codex Executor implementing this task MUST NOT use the newly-created transport to launch a second real Codex process while still executing TASK-041.

Tests use process doubles only.

This avoids nested sessions and double quota use.

## Thin Executor Read Budget

Read only:

```text
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/continuity/errors.py
docs/AIOS_CODEX_EXECUTOR_WINDOWS.md
```

and authoritative TASK/ADR/blueprint from exact `origin/ai-control`.

Do not broad-search repository.
Do not redesign E-Series.

## Targeted Commands

Run only:

```powershell
.\venv\Scripts\python.exe -m pytest tests/aios_bridge/test_codex_local_transport.py -q

.\venv\Scripts\python.exe -m pytest tests/aios_bridge/continuity/test_executor_transport.py tests/aios_bridge/continuity/test_executor.py tests/aios_bridge/test_runtime_lease.py -q
```

Do NOT run the full repository suite.
Do NOT invoke real Codex from tests.

When targeted tests pass:
- report files changed;
- report targeted test counts;
- report blockers;
- STOP.

Do not commit.
Do not push.
Do not publish.

## Publication

Human runs:

```powershell
.\venv\Scripts\python.exe .\bridge.py publish 41 `
  --action RUN `
  --test ".\venv\Scripts\python.exe -m pytest tests/ -q"
```

Bridge owns full-suite, RESULT generation, commit, and push.

## Acceptance

PASS requires:

```text
CODEX_LOCAL_TRANSPORT_CONCRETE: PASS
E1_PROTOCOL_CONFORMANCE: PASS
EXACT_STDIN_PAYLOAD: PASS
SAFE_CODEX_EXEC_ARGV: PASS
WORKSPACE_BRANCH_PREFLIGHT: PASS
DIRTY_WORKTREE_FAIL_CLOSED: PASS
SUBSCRIPTION_FIRST_ENVIRONMENT: PASS
SECRET_ENV_STRIPPING: PASS
TOOL_NETWORK_DISABLED: PASS
DANGER_BYPASS_FORBIDDEN: PASS
PROCESS_STATUS_MAPPING: PASS
TIMEOUT_INTERRUPT_CLEANUP: PASS
EXIT_ZERO_IS_TRANSPORT_ONLY: PASS
NO_REAL_CODEX_IN_TESTS: PASS
NO_BRIDGE_INTEGRATION: PASS
H_SERIES_REMAINS_DEFERRED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E2: PASS
```

Only Human may authorize merge.