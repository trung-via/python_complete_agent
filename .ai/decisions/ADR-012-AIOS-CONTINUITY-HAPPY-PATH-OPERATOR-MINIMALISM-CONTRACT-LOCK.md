# ADR-012 — AIOS Continuity Happy-Path Operator Minimalism Contract Lock

STATUS: LOCKED

## Context

Open Multi-Agent Continuity OS (#12) is intended to reduce quota cost, copy/paste, repeated context loading, and unnecessary operator steps.

The existing AIOS Bridge v0.4 exposes `sync`, `watch`, and `pending` commands for control-plane synchronization and observability. These are useful operational tools, but they are not execution-authority gates.

The proven `handoff` path used by `/aios-worker RUN TASK-N` already fetches the control branch, validates the exact TASK artifact, reconciles canonical main, prepares the task branch, stores the artifact in the external runtime, and records explicit authorization.

Therefore requiring the operator to run `python bridge.py sync` and `python bridge.py pending` before every RUN would add manual work without adding authority or correctness to the normal happy path.

---

## Decision 1 — Minimal Happy Path

For a normal task, the intended operator flow SHALL be:

1. Brain creates TASK + PLAN/control artifacts.
2. Human triggers `/aios-worker RUN TASK-N` in the active Executor surface.
3. AIOS Bridge handoff performs required control-branch fetch/validation/reconciliation/authorization work.
4. Executor implements and tests.
5. RESULT is published.
6. Human asks a compatible Brain to review TASK-N.
7. Brain produces REVIEW.
8. Human explicitly authorizes FIX or MERGE when required.

`sync` and `pending` SHALL NOT be mandatory prerequisites for this happy path.

---

## Decision 2 — `sync` Is Observability / Pre-Fetch Convenience

`python bridge.py sync` MAY be used to:

- proactively fetch newly published TASK/REVIEW/ADR/context artifacts;
- populate/update external runtime artifact cache;
- produce notifications;
- create pending-event observability records.

It SHALL NOT be treated as the authority boundary for RUN/FIX.

Failure to manually run `sync` before `/aios-worker RUN TASK-N` SHALL NOT by itself block a valid handoff, provided the handoff path can fetch and validate the authoritative control artifact directly.

---

## Decision 3 — `pending` Is Read-Only Observability

`python bridge.py pending` SHALL remain a read-only operator diagnostic command.

It MAY show TASK/REVIEW events waiting for human attention.

It SHALL NOT:

- authorize RUN;
- authorize FIX;
- authorize MERGE;
- be required before RUN/FIX;
- mutate canonical continuity state merely because it was invoked.

---

## Decision 4 — `watch` Is Optional Convenience

`python bridge.py watch` MAY continuously call synchronization logic and notify the operator of new control artifacts.

`watch` SHALL remain optional.

The normal workflow SHALL continue to work when no watcher is running.

---

## Decision 5 — Human Authority Remains Explicit

Removing manual `sync`/`pending` steps MUST NOT weaken human authority.

Human approval remains mandatory for:

- RUN;
- FIX;
- MERGE.

The short command `/aios-worker RUN TASK-N` is itself the explicit human RUN approval in the existing workflow, subject to the existing Bridge v0.4 authorization checks.

---

## Decision 6 — UX Target

The normal interactive target for #12 is:

```text
Human:  "Design next task"
Brain:  TASK + PLAN
Human:  /aios-worker RUN TASK-N
Executor: code + tests + RESULT
Human:  "Review TASK-N"
Brain:  REVIEW
Human:  FIX or MERGE approval
```

Target manual control-plane maintenance commands per clean task:

```text
sync    = 0 required
pending = 0 required
watch   = 0 required
```

These commands remain available for diagnostics, recovery, notifications, and operator preference.

---

## Decision 7 — Future Adapter/Executor Compatibility

The same principle SHALL apply when adding Codex, Claude Code, or future Executors.

Executor-specific handoff integrations SHOULD directly obtain the authoritative canonical task state they require rather than forcing the human to manually pre-synchronize state.

A compatible ExecutorAdapter MUST NOT require redundant manual synchronization merely because another Executor integration historically used it.

---

## Decision 8 — Compatibility

This ADR refines ADR-010 and ADR-011 without revoking existing Bridge v0.4 safety invariants.

It does NOT authorize changes to:

- fail-closed branch reconciliation;
- exact control-artifact validation;
- external runtime authorization storage;
- dirty-worktree protection;
- human RUN/FIX/MERGE authority;
- current Antigravity-only proven execution authority prior to later Executor-neutral milestones.

Any implementation change required to make a future happy path satisfy this ADR MUST be delivered through a separate TASK and reviewed normally.

---

## Acceptance Criteria

The contract is satisfied when:

1. A new TASK can be designed/published by a Brain.
2. The user can immediately issue `/aios-worker RUN TASK-N` without manually running `sync` or `pending` first.
3. Bridge handoff fetches and validates the authoritative TASK itself.
4. Explicit human RUN authorization remains recorded.
5. `sync`, `pending`, and `watch` remain useful optional diagnostic/notification tools.
6. No correctness or authorization decision depends solely on whether a pending-event record happened to exist.

This decision is LOCKED unless superseded by a future ADR.
