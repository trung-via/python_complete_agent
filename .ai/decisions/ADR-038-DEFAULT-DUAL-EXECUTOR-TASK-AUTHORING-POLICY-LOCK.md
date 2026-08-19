# ADR-038 — Default Dual-Executor Task Authoring Policy Lock

STATUS: LOCKED
CLASS: TASK AUTHORING / EXECUTOR ELIGIBILITY / HUMAN CHOICE
APPLIES_AFTER: TASK-048 PASS + MERGE
BASELINE_CONTROL_CONTEXT: ADR-037 / TASK-048

## Context

TASK-048 unifies the operator semantics used from Antigravity and Codex around one AIOS Worker protocol and one shared Bridge state.

However, UI parity alone does not make executors interchangeable. Existing Bridge execution validation requires the Human-authorized executor to appear exactly once in the active work artifact's `DISPATCH_EXECUTOR_POLICY_JSON` and to support the active operation.

Therefore, if ChatGPT authors a TASK or CHANGES_REQUIRED REVIEW containing only one executor candidate, the Human cannot freely choose another executor at that authorization boundary even after TASK-048 is merged.

## Decision

After TASK-048 PASS + merge, ChatGPT task/review authoring defaults to a dual-executor eligibility policy whenever both Antigravity and Codex satisfy the required operation and capabilities.

Default eligible subscription executors:

```text
antigravity
codex
```

The Human remains the final actor selector at each RUN or FIX authorization boundary.

```text
eligible != selected
recommended != authorized
Human selection != automatic dispatch
```

## Default RUN Policy

For an ordinary RUN task compatible with both executors, `DISPATCH_EXECUTOR_POLICY_JSON` MUST contain both candidates.

Canonical semantic shape:

```json
{
  "allow_paid_api": false,
  "candidates": [
    {
      "capacity_class": "SUBSCRIPTION",
      "executor_id": "antigravity",
      "preference_rank": 0,
      "supported_capabilities": [
        "FILESYSTEM_WRITE",
        "LOCAL_GIT",
        "REPOSITORY_READ",
        "SHELL",
        "TEST_EXECUTION"
      ],
      "supported_operations": ["RUN"]
    },
    {
      "capacity_class": "SUBSCRIPTION",
      "executor_id": "codex",
      "preference_rank": 1,
      "supported_capabilities": [
        "FILESYSTEM_WRITE",
        "LOCAL_GIT",
        "REPOSITORY_READ",
        "SHELL",
        "TEST_EXECUTION"
      ],
      "supported_operations": ["RUN"]
    }
  ],
  "operation": "RUN",
  "required_capabilities": [
    "FILESYSTEM_WRITE",
    "LOCAL_GIT",
    "REPOSITORY_READ",
    "SHELL",
    "TEST_EXECUTION"
  ]
}
```

Candidate order/preference is recommendation metadata only. It MUST NOT silently authorize or select an executor.

## Default FIX Policy

When ChatGPT publishes `CHANGES_REQUIRED`, the REVIEW artifact MUST permit both Antigravity and Codex for FIX whenever both can satisfy the required capability/scope contract.

This allows a new Human authorization boundary to select a different executor from the one used for RUN.

Example:

```text
RUN TASK-N with Antigravity
        ↓
ChatGPT REVIEW-N = CHANGES_REQUIRED
        ↓
FIX TASK-N with Codex
```

or the reverse.

Changing executor at a fresh RUN/FIX authorization boundary is ordinary Human actor selection, not automatic failover and not hot handoff.

## Exceptions

ChatGPT MUST restrict a TASK/REVIEW to one executor only when there is a concrete capability or operational reason.

Examples include:

```text
executor-specific proof
executor-specific transport compatibility task
UI/bootstrap task that requires one specific environment
capability unavailable on the other executor
locked real-world operational evidence requiring one actor
```

Any single-executor policy MUST be intentional and explain the reason in the artifact.

Do not single-lock merely because one executor was used on the previous task.

## Human Selection UX

After TASK-048 is merged and both candidates are eligible:

```text
Antigravity:
/aios-worker RUN TASK-N
/aios-worker FIX TASK-N

Codex:
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N
```

Invoking the command in the selected UI expresses the Human's actor-selection intent for that exact boundary.

The adapter and Bridge MUST NOT reroute silently to the other executor.

## Synchronization

Both executor choices converge on the same:

```text
TASK/REVIEW control artifact
exact artifact blob
ai/task-N branch
external authorization namespace
ExecutorLease namespace
RESULT publication path
ChatGPT review boundary
```

There is no Codex-specific task state and no Antigravity-specific task state.

## Review Invariance

ChatGPT independent review criteria do not depend on which eligible executor performed the work.

Review continues to validate, at minimum:

```text
fresh baseline/head lineage
exact task/review/control blobs
allowed scope
actual Git delta
RESULT/test evidence
contract invariants
authorization/lease/executor binding
drift before PASS/merge
```

Executor identity is evidence to verify, not a reason to relax or change review standards.

## Active-Execution Boundary

This policy does NOT permit casual actor switching while an authorization/lease is ACTIVE.

```text
new RUN/FIX authorization boundary -> Human may select either eligible executor
ACTIVE execution -> no silent switch
```

Switching during active work remains governed by existing failover/hot-handoff contracts where applicable.

## M11 Independence

Dual-executor Human choice is an Executor control-plane capability and does not depend on completion of M11 External API Escape Hatch.

Therefore:

```text
TASK-048 PASS + MERGE
        ↓
Dual-executor task authoring becomes default immediately
        ↓
M11 may continue normally
```

M11 does not need to finish before the Human can choose Antigravity or Codex for eligible tasks.

## TASK-048 Boundary

TASK-048 itself remains intentionally Antigravity-only because it bootstraps the Codex repo skill.

This ADR MUST NOT alter ADR-037, TASK-048, or their locked blob references.

The first task issued after TASK-048 PASS + merge should be authored under this dual-executor default unless a documented exception applies.

## H-Series Boundary

H-Series remains DEFERRED. This policy does not activate H1-H5.

## Completion Rule

This ADR is a task-authoring policy, not a runtime implementation milestone.

It becomes operational after TASK-048 PASS + merge when ChatGPT issues the next TASK/REVIEW with both eligible candidates and the Human successfully chooses one through the unified worker UI.
