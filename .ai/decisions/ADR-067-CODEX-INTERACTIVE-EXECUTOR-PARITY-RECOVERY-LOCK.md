# ADR-067 — Codex Interactive Executor Parity Recovery Lock

STATUS: ACCEPTED
CHANGE_CLASS: IMPLEMENTATION_REFINEMENT
HUMAN_APPROVED_SOURCE: USER_APPROVAL_2026-08-26
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
BASE_MAIN_SHA: 558e666cc5808f5574862feaa8562a7d8c70e86f
CANONICAL_REQUIREMENT_IDENTITY_CHANGED: NO
ROADMAP_MUTATION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
TASK_095_STATUS: BLOCKED_PENDING_CODEX_PARITY_RECOVERY
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO

## Problem

The normal Codex worker path is not execution-parity with Antigravity.

Current Codex happy path:

```text
visible Codex session
-> $aios-worker operator wrapper
-> Bridge handoff
-> bridge.py execute
-> spawn second `codex exec --ephemeral` child
-> stdin context pack
-> temp-file stdout/stderr capture
-> transport diagnostic/classifier
-> publish
```

Current Antigravity happy path:

```text
visible Antigravity session
-> /aios-worker
-> Bridge handoff
-> same visible Antigravity session implements/tests
-> publish
```

Observed TASK-095 evidence on 2026-08-26:

```text
attempt 1: ~7m48s, zero code delta, zero publication, executor disappeared while ACTIVE authorization + ACTIVE lease remained; Human recovery release required
attempt 2: ~1m27s, CLEAN_NO_WORKTREE_DELTA, zero publication; structured replacement guidance emitted
```

Two consecutive zero-product Codex attempts are sufficient to stop treating the nested Codex transport as a reliable default happy path.

## Decision

Make Codex use the same interactive execution shape as Antigravity for normal RUN/FIX work.

Canonical happy path after this refinement:

```text
Human selects executor
-> Bridge sync + exact handoff
-> ACTIVE authorization + lease
-> SAME selected interactive executor session performs bounded implementation
-> targeted T0/T1
-> canonical publish under exact authorization/lease/scope/trust checks
-> semantic review
```

For Codex specifically:

```text
$aios-worker RUN/FIX
-> handoff --executor codex
-> return AUTHORIZED to the visible Codex session
-> visible Codex session reads only the exact authorized task/review + compact semantic context
-> visible Codex session edits allowed paths and runs targeted tests
-> visible Codex session invokes canonical Bridge publication
```

The default RUN/FIX worker transaction MUST NOT call `bridge.py execute` or spawn nested `codex exec --ephemeral`.

`CodexLocalTransport` and `bridge.py execute` may remain temporarily for explicit legacy/recovery compatibility, but they are not the normal `$aios-worker` happy path and must not be invoked implicitly.

## Authority invariants preserved

This refinement changes execution transport shape only. Preserve exactly:

```text
Human executor selection
exact TASK/REVIEW artifact binding
roadmap binding/preflight
allowed-path enforcement
one active executor lease
publication trust
candidate identity
Review-First semantics
T0/T1 executor ownership
T2 certification ownership
no automatic retry
no automatic reroute
no automatic rebase
no automatic merge authority for worker
```

Interactive Codex does not gain authority from chat/session memory. Bridge authorization remains the sole execution authority.

## Context rule

Because the visible Codex session becomes the executor, Slim context suppression for normal Codex must be removed.

Codex and Antigravity should receive the same compact interactive context surface after authorization:

```text
task id/action/executor
current + expected branch
exact task artifact location
exact review artifact location for FIX
allowed paths
semantic context refs excluding machine-only roadmap prose
interactive FIX context when applicable
```

Machine provenance remains enforced out-of-band. Do not restore MANIFEST_JSON, request/execution fingerprints, roadmap body, or other removed model-visible bookkeeping.

The executor may read the exact cached authorized TASK/REVIEW and the bounded semantic refs named by Bridge. It must not reconstruct authority from arbitrary repository history or chat memory.

## Publication rule

Do not add a second publish subsystem merely to avoid a direct Bridge command.

After bounded implementation/testing, the same interactive executor may invoke the existing canonical `bridge.py publish` surface using the exact active authorization. Publication still reruns/validates the authorized targeted test command and all existing trust/scope/head checks.

## Failure terminalization

A known-stopped executor transaction must not remain indefinitely as ACTIVE authorization + ACTIVE lease.

Normal interactive mode reduces this failure surface because Bridge no longer owns a hidden child-process lifecycle. Existing fail-closed lease recovery remains available for abnormal operator/session termination.

No new watchdog, polling loop, workflow database, session store, or automatic retry machinery is authorized by this ADR.

## Proof requirement

Unit tests are necessary but insufficient. Recovery is not accepted until a real post-merge `$aios-worker RUN` using Codex reaches a non-empty authorized implementation delta and publication without nested `codex exec`.

TASK-095 will serve as the first real Codex proof after the parity refinement is certified and merged. Before that proof, TASK-095 remains blocked.

## Out of scope

```text
P2 provider-neutral persistent executor sessions
checkpoint/resume
heartbeat/session lifecycle
capacity suspension
Claude Code integration
adaptive executor selection
automatic executor substitution
removal of CodexLocalTransport compatibility code
Slim R2 broad cleanup
Python Agent pilot
P2/P3
H5-H8
roadmap v1.3
```

## Consequence

This is a subtractive reliability refinement:

```text
DELETE from happy path: nested Codex process + ephemeral transport dependency
KEEP: authorization + lease + scope + trust + publication + review/certification boundaries
MEASURE: real TASK-095 Codex publication after merge
```
