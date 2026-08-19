# ADR-030 — E2 Codex Local Transport Contract Lock

STATUS: LOCKED

## Context

E1 / ADR-029 established the pure vendor-neutral `ExecutionTransport` seam and canonical `ExecutorInvocation` / `InvocationReceipt` contracts. E1 deliberately performs zero real Executor invocation.

E2 is the first concrete transport milestone:

```text
E1 — Executor Invocation Contract                 COMPLETE
E2 — Codex Local Transport                        THIS ADR
E3 — Bounded Context Pack Delivery
E4 — Result Collection + Auto Publication
E5 — Zero-Copy/Paste Operational Proof
```

The objective is to make one already-authorized Codex Executor invokable programmatically from the local AIOS runtime without changing Human RUN/FIX/MERGE authority.

E2 is NOT Bridge integration. It does not yet make `bridge.py approve` automatically launch Codex. That orchestration belongs to E4 after E3 supplies the bounded context payload.

The separate H-Series backlog remains DEFERRED and is not renamed or implemented by E2.

---

## Decision 1 — Concrete Transport Lives Outside Continuity Core

E2 SHALL add a concrete Codex implementation under:

```text
src/aios_bridge/executor_transports/codex_local.py
```

with package export:

```text
src/aios_bridge/executor_transports/__init__.py
```

The E1 pure contract remains in:

```text
src/aios_bridge/continuity/executor_transport.py
```

E2 MUST NOT modify the E1 contract merely to fit Codex.

The concrete transport SHALL implement the E1 `ExecutionTransport` Protocol with:

```text
executor_id  = codex
transport_id = codex-local-v1
```

No provider switch, dispatcher branch, or generic H5 Driver framework is introduced.

---

## Decision 2 — Exact Codex Headless Invocation Shape

E2 SHALL invoke Codex through its supported non-interactive `exec` surface.

The command contract SHALL be equivalent to:

```text
codex exec
  --ephemeral
  --json
  --color never
  --sandbox workspace-write
  --ask-for-approval never
  -C <exact-workspace-root>
  -
```

with exact additional config overrides that disable tool-side network/web search where supported by the installed Codex CLI:

```text
-c sandbox_workspace_write.network_access=false
-c web_search="disabled"
```

The final `-` means the E1 payload bytes are supplied through stdin rather than interpolated into a command line.

E2 SHALL NOT use:

```text
--dangerously-bypass-approvals-and-sandbox
--sandbox danger-full-access
--skip-git-repo-check
--add-dir
--full-auto
shell=True
```

E2 SHALL NOT silently retry with a weaker sandbox or a bypass mode when the requested sandbox fails.

If an installed Codex build cannot complete under the locked safe command shape, E2 fails closed. Safety is not weakened to preserve convenience.

---

## Decision 3 — Human Authorization Remains External and Mandatory

`CodexLocalTransport.invoke(...)` is not an authority gate.

The transport MUST NOT:
- create or mutate Human authorization;
- acquire/release an ExecutorLease;
- call deterministic dispatch;
- choose itself;
- approve RUN/FIX;
- authorize MERGE;
- publish RESULT;
- commit/push/merge.

A future E4 caller may invoke E2 only after independently proving exact ACTIVE Human authorization + exact active lease + exact current branch/workspace/artifact binding.

E2 itself receives an already-constructed E1 `ExecutorInvocation` and exact payload bytes.

`recommendation != authorization != lease != invocation != receipt != result != publication != merge` remains locked.

---

## Decision 4 — Reuse E1 Validation Before Process Start

Before any Codex process is created, E2 SHALL call:

```python
validate_transport_binding(self, invocation)
validate_invocation_payload(invocation, payload)
```

Identity/payload validation errors are contract violations and SHALL propagate as `ContinuityStateValidationError` without spawning Codex.

The transport SHALL never decode, trim, normalize, append to, prepend to, or otherwise rewrite the payload bytes.

Exact payload bytes are written to stdin.

E3 later owns payload composition semantics.

---

## Decision 5 — Exact Workspace Preflight Is Read-Only and Fail-Closed

E2 SHALL be configured with one exact workspace root.

Before Codex launch it SHALL perform bounded read-only local checks equivalent to:

```text
workspace exists and is a directory
workspace is the exact Git toplevel
current branch == invocation.target_branch
git status --porcelain is empty
```

The Git checks SHALL use argument-vector subprocess calls with `shell=False`.

E2 SHALL NOT:
- checkout/switch branches;
- fetch/pull/reset/stash/clean;
- create a task branch;
- mutate Git config;
- stage/commit/push;
- discard dirty work.

A dirty worktree or branch mismatch is a startup refusal, not something the transport repairs.

A future E4 caller remains responsible for authority/artifact/lease reconciliation before this transport boundary.

---

## Decision 6 — Codex Executable Discovery Is Bounded

E2 MAY accept an explicit Codex executable path/name from its constructor for deterministic tests/operator configuration.

Otherwise it SHALL resolve `codex` using bounded local executable discovery such as `shutil.which`.

Requirements:
- no recursive filesystem search;
- no npm registry/network lookup;
- no auto-install/auto-upgrade;
- no shell command used merely to locate the executable;
- missing/unlaunchable Codex maps to `FAILED_TO_START`.

E2 MUST NOT mutate Codex installation or authentication state.

---

## Decision 7 — Subscription-First Environment Hygiene

E2 SHALL inherit only a minimal OS/Codex environment allowlist required to launch the already-authenticated local Codex CLI.

It MUST NOT forward arbitrary parent environment variables.

At minimum E2 MUST explicitly strip common paid-API/application-secret variables including:

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
```

No API key or application credential may be injected into the prompt or canonical receipt.

E2 relies on the user's existing Codex local sign-in state. If that state is unavailable, invocation fails; E2 does not fall through to an API key.

This preserves the subscription-first direction locked before M11.

---

## Decision 8 — Tool-Side Network Is Disabled

The Codex model service itself necessarily communicates through the Codex client, but shell/tool execution within the selected workspace SHALL be requested with network access disabled.

E2 SHALL also request Codex web search disabled.

E2 MUST NOT add MCP servers, browser tools, external network clients, or provider API calls.

If the installed CLI rejects the locked network/web-search configuration, invocation fails closed rather than removing those controls automatically.

---

## Decision 9 — Output Is Not Canonical Result

E2 SHALL NOT interpret Codex stdout/final prose as task success.

For E2 v1:
- stdin = exact payload bytes;
- stdout = discarded or bounded non-authoritative diagnostic sink;
- stderr = discarded or bounded non-authoritative diagnostic sink;
- no stdout/stderr body is stored in `InvocationReceipt`;
- no model final message becomes an `ExecutionResult`;
- no RESULT artifact is created by E2.

The process exit code maps only to E1 transport status.

`EXITED_ZERO` means only that the local Codex process exited with code 0.

E4 later owns result/worktree/test/publication semantics.

---

## Decision 10 — Status Mapping Is Exact

E2 SHALL produce an E1 `InvocationReceipt` bound to the exact invocation.

Required mapping:

```text
process exit 0
  -> EXITED_ZERO, exit_code=0, error_code=None

process non-zero within supported int range
  -> EXITED_NONZERO, error_code=CODEX_EXIT_NONZERO

executable missing
  -> FAILED_TO_START, error_code=CODEX_NOT_FOUND

other spawn/preflight failure
  -> FAILED_TO_START, error_code=CODEX_START_FAILED or WORKSPACE_PRECONDITION_FAILED

timeout
  -> TIMED_OUT, error_code=CODEX_TIMEOUT

caller interruption
  -> INTERRUPTED, error_code=CALLER_INTERRUPTED
```

An out-of-domain process return code SHALL fail closed as a startup/runtime failure rather than fabricating a valid canonical exit code.

Receipt identity MUST be validated mechanically with `validate_invocation_receipt(...)` before returning.

---

## Decision 11 — Timeout and Process Cleanup

E2 SHALL use synchronous invocation for E-Series v1, matching E1.

Constructor timeout shall be an exact bounded integer with a documented default.

On timeout or caller interruption, E2 SHALL terminate the Codex process and make a best-effort attempt to terminate its process group/tree before returning a timeout/interrupted receipt.

No automatic retry is permitted.

E2 does not implement H4 Provider Lifecycle, background sessions, resume, streaming, callbacks, or detached workers.

---

## Decision 12 — No Persistent Session / Resume

E2 SHALL pass `--ephemeral` and starts one fresh headless Codex execution per invocation.

E2 v1 MUST NOT:
- resume previous Codex threads;
- search latest sessions;
- select session history;
- persist a transport conversation ID;
- infer task state from Codex history.

Continuity identity remains AIOS-owned, not Codex-session-owned.

---

## Decision 13 — Native Windows Safety Rule

E2 targets the user's native Windows workflow but SHALL NOT encode an unsafe bypass for platform-specific sandbox problems.

The locked behavior is:

```text
request workspace-write
request approval policy never
never request danger-full-access
never use dangerously-bypass-approvals-and-sandbox
never weaken policy automatically after a sandbox failure
```

A native Windows Codex sandbox defect may therefore cause E2 to fail to perform writes on a particular Codex build. That outcome is acceptable and must remain observable as non-task-success.

E5 real operational proof must verify actual safe workspace mutation on the user's installed Codex build before zero-copy/paste execution can be declared production-proven.

No E2 unit test may claim that CLI exit code 0 proves a workspace edit occurred.

---

## Decision 14 — No Bridge Integration Yet

E2 MUST NOT modify:

```text
bridge.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/dispatch.py
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/executor_transport.py
src/aios_bridge/continuity/lease.py
```

E2 does not add `bridge.py run`, auto-approve, auto-publish, or dispatcher-to-transport wiring.

Those would collapse milestones and make E2 impossible to review independently.

---

## Decision 15 — H-Series Remains Deferred

E2 MUST NOT introduce:
- Event Journal framework;
- generic Capability Seams;
- generic Execution Envelope;
- Provider Lifecycle manager;
- generic Driver Contract.

A single concrete `CodexLocalTransport` implementing the already-locked E1 Protocol is not H5.

Any pressure to generalize based on one Codex transport SHALL be deferred until real Python Agent workload evidence triggers H-Series.

---

## Decision 16 — Required Tests

E2 tests SHALL avoid consuming Codex/model quota.

Use monkeypatched/fake process and Git preflight boundaries to prove command construction and status behavior without a real model call.

Required positive coverage:
- concrete class satisfies `ExecutionTransport`;
- exact `codex` executor/transport IDs;
- exact argv contains `exec`, `--ephemeral`, `--json`, `--color never`, `--sandbox workspace-write`, `--ask-for-approval never`, exact `-C`, final `-`;
- payload bytes are passed through stdin exactly;
- `shell=False`;
- process exit 0 -> valid EXITED_ZERO receipt;
- non-zero -> valid EXITED_NONZERO receipt;
- exact workspace/branch/clean-tree preflight;
- minimal environment is used;
- API key/secret environment variables are not forwarded;
- E1 receipt binding validation passes.

Required adversarial coverage:
- wrong transport ID/executor ID rejected before spawn;
- mutated payload rejected before spawn;
- missing workspace;
- non-Git workspace;
- Git toplevel mismatch;
- wrong branch;
- dirty worktree;
- Codex not found;
- spawn OSError;
- timeout;
- caller interrupt;
- non-zero process exit;
- bool/zero/negative/oversized timeout rejected;
- no `danger-full-access`;
- no dangerous bypass flag;
- no `--skip-git-repo-check`;
- no `--add-dir`;
- no positional payload text;
- no raw payload in argv;
- no API keys in child environment;
- no auto retry/fallback;
- no Bridge/runtime/dispatch/lease mutation imports/calls;
- no Codex session resume/history lookup;
- no task-success inference from exit 0.

Full repository suite remains the Bridge publication gate.

---

## Decision 17 — Expected Implementation Boundary

Allowed production files:

```text
src/aios_bridge/executor_transports/__init__.py
src/aios_bridge/executor_transports/codex_local.py
```

Expected tests:

```text
tests/aios_bridge/test_codex_local_transport.py
```

Bridge publication may generate:

```text
.ai/results/RESULT-041.md
```

No other file is expected.

If implementation requires a change to E1, Bridge, dispatch, lease, failover, hot handoff, providers, or H-Series abstractions, STOP and escalate instead of widening scope.

---

## E2 Acceptance

E2 is complete only when:

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
NO_BRIDGE_INTEGRATION: PASS
H_SERIES_REMAINS_DEFERRED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E2: PASS
```

E2 PASS does NOT mean zero-copy/paste workflow is complete.

After E2 merges, E3 may define the bounded content-addressed context payload delivered through this transport.