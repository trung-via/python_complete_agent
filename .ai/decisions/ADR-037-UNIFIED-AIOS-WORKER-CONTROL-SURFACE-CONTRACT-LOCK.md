# ADR-037 — Unified AIOS Worker Control Surface Contract Lock

STATUS: LOCKED
CLASS: OPERATOR UX / CONTROL ADAPTER
BASELINE_MAIN_SHA: 22a05d1f4880daf3a9f964e0564c658b051039cd
TARGET_BOOTSTRAP_TASK: TASK-048

## Context

AIOS Bridge already defines the shared authority/state layer and historically exposes the Antigravity operator semantic:

```text
/aios-worker RUN TASK-N
/aios-worker FIX TASK-N
```

The merged E-Series now allows a Human-authorized Codex execution to proceed through `bridge.py execute N` with automatic E3 context delivery and E4 publication.

The remaining operator problem is UI parity: a Human should not have to manually reproduce `sync -> pending -> approve/handoff -> execute` in PowerShell merely because Codex is the selected UI.

Codex supports repository-scoped Skills under `.agents/skills`, so the operator surface can be adapted without creating a second authority system.

## Decision

There is exactly one AIOS Worker semantic protocol:

```text
RUN TASK-N
FIX TASK-N
STATUS TASK-N
```

UI adapters expose that same semantic protocol:

```text
Antigravity: /aios-worker RUN TASK-N
Antigravity: /aios-worker FIX TASK-N
Antigravity: /aios-worker STATUS TASK-N

Codex: $aios-worker RUN TASK-N
Codex: $aios-worker FIX TASK-N
Codex: $aios-worker STATUS TASK-N
```

A natural-language `RUN TASK-N`, `FIX TASK-N`, or `STATUS TASK-N` inside Codex may trigger the same repo skill implicitly, but `$aios-worker ...` is the deterministic explicit form.

## Single Source of Truth

Neither Antigravity nor Codex may own task state.

Authoritative state remains:

```text
GitHub ai-control artifacts
AIOS Bridge external runtime authorization
ExecutorLease state
Bridge task branch state
Bridge RESULT publication
```

The adapters are thin front ends only.

```text
UI adapter != authority
UI adapter != task state store
UI adapter != publication authority
```

## Human Authorization Semantics

The Human action of invoking the mutating worker command from the chosen UI is the explicit actor-selection and RUN/FIX authorization intent:

```text
Human enters $aios-worker RUN TASK-049 in Codex
=> Human selected executor = codex
=> Human requested RUN for exact TASK-049
```

Likewise `/aios-worker RUN TASK-N` in Antigravity selects `antigravity`.

The adapter MUST show/echo exact task ID, action, and selected executor before or while invoking the Bridge boundary. If Codex presents a command/skill approval prompt, Human approval of that prompt remains part of the same explicit operator action.

The adapter MUST NOT silently choose another executor.

## Canonical Control Behavior

### STATUS

`STATUS TASK-N` is non-authorizing. It may synchronize control artifacts and display Bridge/task status, but MUST NOT create authorization, acquire a lease, invoke an executor, publish, or merge.

### RUN

Codex adapter:

```text
$aios-worker RUN TASK-N
  -> validate exact command/task
  -> Bridge handoff TASK-N action=RUN executor=codex
  -> existing Bridge ACTIVE authorization + lease
  -> bridge.py execute N exactly once
  -> existing E3/E2/E4 path
  -> RESULT + commit + push
  -> STOP and instruct Human: Review TASK-N in ChatGPT
```

Antigravity adapter continues to use the same Bridge handoff/authorization semantics with executor `antigravity`; its interactive executor path remains unchanged by this ADR.

### FIX

Codex adapter:

```text
$aios-worker FIX TASK-N
  -> Bridge handoff TASK-N action=FIX executor=codex
  -> handoff must validate authoritative CHANGES_REQUIRED review
  -> existing ACTIVE authorization + lease
  -> bridge.py execute N exactly once
  -> existing E3/E2/E4 path
  -> RESULT + commit + push
  -> STOP and instruct Human: Review TASK-N in ChatGPT
```

No FIX may be invented without the Bridge-valid authoritative review boundary.

## Shared Adapter Script

TASK-048 creates one repo-owned adapter script used by the Codex skill and reusable by other UI adapters:

```text
.agents/skills/aios-worker/scripts/aios_worker.py
```

The script is an operator adapter, not a second control plane.

It MUST invoke existing Bridge CLI boundaries using the current Python interpreter. It MUST NOT reimplement authorization, lease validation, E3 packing, E2 transport, E4 publication, Git publication, review logic, or merge logic.

For Codex RUN/FIX it composes only:

```text
bridge.py handoff <N> --action <run|fix> --executor codex
bridge.py execute <N>
```

Each downstream command is invoked at most once. No retry/fallback/reroute.

STATUS may compose existing synchronization/status commands only.

## Codex Skill

Repository path:

```text
.agents/skills/aios-worker/SKILL.md
```

The skill MUST:
- declare exact RUN/FIX/STATUS TASK-N trigger semantics;
- default its adapter identity to `codex`;
- call only the shared adapter script for mutating worker commands;
- never edit implementation files itself during RUN/FIX;
- never manually reconstruct task context;
- never call `bridge.py context` as a substitute for E3;
- never call `codex exec` directly;
- never call `bridge.py publish` directly;
- never retry a failed `execute`;
- never authorize or perform merge;
- after successful publication, tell the Human to return to ChatGPT for `Review TASK-N`.

The parent Codex session is an operator UI. The E2 Codex process invoked by Bridge remains the executor for automated Codex RUN/FIX.

## Synchronization Invariants

Both adapters MUST converge on the same Bridge state.

```text
same TASK control blob
same REVIEW control blob
same target task branch
same external authorization namespace
same lease namespace
same publication path
```

A second UI attempting RUN/FIX after authorization has been consumed or while an incompatible active lease exists must fail through existing Bridge rules. The adapter MUST surface that failure and MUST NOT repair/recreate authority itself.

## PowerShell Boundary

After TASK-048 is merged, routine operator use MUST NOT require the Human to manually type the prior PowerShell sequence:

```text
bridge.py sync
bridge.py pending
bridge.py approve ...
bridge.py execute ...
bridge.py publish ...
```

PowerShell remains available for diagnosis/recovery/bootstrap, not the normal Human UI.

## Merge Boundary

`MERGE TASK-N` is intentionally NOT part of the worker skill.

ChatGPT independent review and explicit Human merge authorization remain separate. Codex/Antigravity worker adapters must never merge.

## Failure Semantics

Any Bridge/adaptor failure:
- stop immediately;
- surface the failure;
- no automatic retry;
- no fallback executor;
- no manual publication substitute;
- no reset/stash/clean/revert;
- no authority reconstruction.

## Bootstrap

TASK-048 creates the Codex skill and shared adapter. Because the new Codex surface does not yet exist before TASK-048 lands, TASK-048 should be executed through the already-established Antigravity `/aios-worker RUN TASK-048` workflow (or another explicitly Human-authorized existing workflow).

After TASK-048 PASS + merge, the previously designed M11.1 work is reissued under a fresh task ID/baseline and becomes the first normal real task to validate:

```text
$aios-worker RUN TASK-<new>
```

No manual PowerShell sequence should be required for that proof.

## Scope Boundary

TASK-048 MUST NOT change E1-E5 behavior, M11 architecture, executor selection policy, authorization semantics, lease semantics, publication semantics, or H-Series status.

H-Series remains DEFERRED.
