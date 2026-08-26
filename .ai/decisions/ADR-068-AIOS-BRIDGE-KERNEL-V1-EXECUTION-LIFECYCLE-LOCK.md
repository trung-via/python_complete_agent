# ADR-068 — AIOS Bridge Kernel v1 Execution Lifecycle Lock

STATUS: ACCEPTED
DATE: 2026-08-26
DECISION_OWNER: HUMAN + CHATGPT ARCHITECT
SCOPE: AIOS Bridge execution/publish/certify/merge worker path
SUPERSEDES_NORMAL_HAPPY_PATHS: TASK-096, TASK-097 recovery design
PRESERVES: Roadmap Lock, TASK/REVIEW authority, Human executor selection, exact SHA binding, allowed-path boundary, semantic review, H-Series ownership, Python Agent roadmap

## Context

The current Bridge worker path accumulated overlapping orchestration responsibilities across worker skills, `worker_flow`, root Slim wrappers, legacy execution, publish-time validation, recovery modes and executor-specific behavior. Operational evidence from TASK-095 through TASK-097 showed:

- Codex normal execution spawned a nested ephemeral Codex process while Antigravity executed in the visible session;
- executor failure could leave orphaned ACTIVE authorization/lease state;
- direct interactive publication could lose scope/trust gates formerly supplied by nested execution;
- validation ownership was semantically defined as T0/T1 executor-owned while worker instructions could run T0/T1 before `publish`, and `publish` could run the same targeted suite again;
- Antigravity used repeated model-driven timers to poll long-running pytest and Bridge publish processes;
- RUN/FIX/EVIDENCE_REFRESH/recovery branches made it difficult to answer from one canonical contract exactly which actor performs which operation and how many times.

This is architectural drift. Continuing to add wrappers or recovery exceptions is rejected.

## Decision

Build a new **AIOS Bridge Kernel v1** alongside the existing Bridge. The existing Bridge remains frozen compatibility/recovery infrastructure until Kernel v1 passes real smoke tests and cutover is explicitly authorized.

Kernel v1 has exactly one normal lifecycle:

```text
AUTHORIZE
  -> EXECUTE
  -> VERIFY
  -> PUBLISH
  -> REVIEW
  -> CERTIFY
  -> MERGE
```

Every stage has exactly one authority owner and one normal transition to the next stage.

## Canonical ownership

| Stage | Owner | Contract |
|---|---|---|
| AUTHORIZE | Kernel | Human-selected executor, exact TASK/REVIEW, base/main/head, branch, allowed paths, minimal active authorization |
| EXECUTE | Visible Codex or Antigravity session | Read bounded context, edit only authorized paths, return DONE or BLOCKED; never merge; never spawn another model |
| VERIFY | Kernel deterministic process | Run authoritative T0/T1 exactly once after DONE; synchronous foreground wait; diff/scope checks |
| PUBLISH | Kernel | Exact authorization/scope/trust/head checks, RESULT, commit/push, terminalize execution |
| REVIEW | ChatGPT | Semantic review only; no pytest; PASS_PENDING_T2 or CHANGES_REQUIRED |
| CERTIFY | Kernel deterministic process | Full canonical T2 exactly once for the exact semantically accepted candidate |
| MERGE | Kernel | Fast-forward-only exact certified SHA after all identities revalidate |

## Validation ownership lock

```text
EXECUTOR DEVELOPMENT:
  Optional narrow ad-hoc micro-checks only when needed to debug implementation.
  These checks are NOT authoritative evidence and MUST NOT duplicate the canonical targeted suite by default.

VERIFY boundary:
  authoritative T0/T1 = EXACTLY ONCE per candidate attempt

REVIEW boundary:
  tests = ZERO

CERTIFY boundary:
  authoritative full T2 = EXACTLY ONCE per accepted candidate

MERGE boundary:
  tests = ZERO
```

No normal path may execute the same authoritative targeted suite once in the model session and again in publish.

## Long-running command lock

All Kernel-owned long-running commands use process-level synchronous waiting:

```text
launch once
-> wait on same process
-> collect exit code once
-> continue
```

Forbidden in normal worker flow:

- model-driven 30s/60s timer polling;
- recurring "check completion again" prompts;
- rerunning a command merely to discover whether the previous invocation ended;
- watchdog/polling loops implemented by the model.

One long-running command must create one process launch and one completion observation.

## Provider parity lock

Codex and Antigravity use the same worker lifecycle shape:

```text
Human selects executor
-> Kernel AUTHORIZE
-> same visible selected session receives compact context
-> same visible session edits
-> same visible session signals DONE
-> Kernel VERIFY + PUBLISH
```

Normal Codex MUST NOT launch `codex exec`, nested Codex, or another model process.
Normal Antigravity MUST NOT delegate to Codex.
No automatic executor reroute exists.

## RUN/FIX lock

RUN and FIX differ only in authority input:

```text
RUN input = exact TASK
FIX input = exact TASK + exact CHANGES_REQUIRED REVIEW
```

After AUTHORIZE they share the same EXECUTE -> VERIFY -> PUBLISH lifecycle.

Kernel v1 does NOT implement a separate EVIDENCE_REFRESH mode. If a future measured requirement proves it necessary, it requires a new explicit ADR.

## Minimal state lock

Kernel runtime state is limited to the smallest atomic authorization record necessary for fail-closed execution:

```text
task_id
action
executor_id
base_main_sha
target_branch
authorized_artifact_sha
review_sha when FIX
allowed_paths fingerprint
pre_execution_head
status
```

No workflow database, session scheduler, heartbeat system, adaptive router, generalized event bus or persistent model-session store is authorized.

Terminal states are closed and explicit:

```text
AUTHORIZED
DONE
BLOCKED
PUBLISHED
SEMANTICALLY_ACCEPTED_PENDING_T2
CERTIFIED
MERGED
CANCELLED
```

A stopped/failed executor may never leave an ambiguous ACTIVE lease/authorization without a terminal recovery state.

## Context lock

The visible executor receives only:

```text
task_id
action
executor_id
target_branch
base_main_sha
task path
review path when FIX
allowed_paths
bounded semantic refs
```

Do not expose request IDs, lease fingerprints, manifest JSON, byte counts, roadmap body, transport diagnostics or duplicated machine bookkeeping to the model.

## Publication lock

Kernel PUBLISH must prove before commit/push:

```text
exact active authorization
exact selected executor
exact task/review identity
exact target branch
head descended from authorized pre-execution head
current main == authorized base main unless task contract explicitly allows otherwise
all changed paths subset of exact allowed_paths
publication trust/current remote identity valid
VERIFY T0/T1 PASS belongs to exact current candidate
```

Any missing/unknown/stale evidence fails closed. There are no string-message exception whitelists and no model/session-provided authority fallback.

## Review and certification lock

Semantic review never executes tests. It binds exact candidate SHA + exact TASK/REVIEW/RESULT identities.

For strict control-plane work:

```text
candidate T2 = 0
semantic acceptance required
certify -> full canonical T2 exactly once
merge only exact certified candidate
```

PRODUCT_DELIVERY_FAST/capability-level certification remains deferred until Kernel v1 is proven and TASK-095 is explicitly redesigned/rebound against the new kernel. ADR-066 semantics are preserved but are not implemented by Kernel-v1 bootstrap task.

## Compatibility and migration

Kernel v1 is implemented beside the old Bridge. During bootstrap:

```text
old Bridge = compatibility path used only to implement/review/certify Kernel v1 task
Kernel v1 = no default cutover until smoke proof
```

Do not delete legacy Bridge code during bootstrap.
Do not port historical special cases unless a current smoke test requires them.

After Kernel v1 implementation is certified and merged, cutover requires three real proofs:

```text
1. simple RUN with Antigravity
2. CHANGES_REQUIRED -> FIX with Antigravity
3. real RUN with Codex visible-session executor
```

Each proof must demonstrate:

```text
nested model invocation = 0
authoritative T0/T1 execution count = 1
model-driven polling loops = 0
candidate T2 count = 0
publication exact-scope PASS
```

Only then may `$aios-worker` and `/aios-worker` default to Kernel v1 and the old execution path enter retirement planning.

## Rejected designs

Rejected for Kernel v1 bootstrap:

- patching TASK-097 root publish wrapper further;
- nested Codex transport on normal path;
- separate RUN/FIX orchestration engines;
- EVIDENCE_REFRESH special mode;
- duplicate targeted test execution;
- model-driven polling/timers;
- automatic retry/reroute/rebase/conflict resolution;
- P2 session/checkpoint/heartbeat machinery;
- capability batching or PRODUCT_DELIVERY_FAST implementation inside kernel bootstrap;
- rewriting H-Series, roadmap governance or Python Agent.

## Success condition

Kernel v1 is acceptable only if the full normal lifecycle can be explained by the ownership table in this ADR without consulting executor-specific special cases.

If a normal RUN/FIX requires more than one screen of lifecycle explanation, the implementation is rejected as too complex.
