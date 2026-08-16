# ADR-011 — AIOS Continuity M1 Canonical Project State Contract Lock

STATUS: LOCKED

## Context

ADR-010 locked the new #12 direction as **Open Multi-Agent Continuity OS**: Brain-neutral, Executor-neutral, vendor-neutral, subscription-first, API-optional, and canonical-state-driven.

The first milestone is M1 — Canonical Project State.

The repository already has a local Bridge runtime state primitive in `bridge.py`:

- `get_runtime_paths()["state"]` -> external runtime `state/CURRENT_STATE.json`;
- `update_state(...)` records local operational fields such as `active_task`, `status`, `last_review`, and `next_step`.

That existing file is intentionally outside the worktree and is useful for Bridge-local runtime operation. It is **not** sufficient as cross-Brain / cross-Executor canonical continuity state because ChatGPT Chat, Claude Chat, Gemini Chat, Codex, Claude Code, or another machine/session cannot rely on access to that local runtime directory.

M1 therefore introduces a separate **shared Continuity State contract** without repurposing or weakening the existing Bridge runtime state.

This ADR is a narrow M1 contract. It does not implement Brain failover, Executor failover, Executor Lease, dispatch, remote chat automation, or automatic control-branch writes.

---

## Decision 1 — Two State Domains Must Remain Separate

AIOS SHALL distinguish:

### A. Bridge Runtime State

Existing local state managed by `bridge.py`, stored outside the Git worktree.

Purpose:
- local operational convenience;
- current Bridge status;
- local handoff/publish UX.

It remains governed by Bridge v0.4 semantics.

### B. Continuity State

New compact, shareable, deterministic project-state snapshot used for cross-session / cross-Brain / future cross-Executor continuity.

Purpose:
- tell a replacement Brain what task is active;
- identify exact authoritative artifacts and Git refs;
- identify the current lifecycle phase;
- identify the next required operation;
- permit fail-closed freshness checking;
- avoid transferring whole chat histories.

The two domains MUST NOT be silently merged in M1.

`bridge.py` runtime `CURRENT_STATE.json` SHALL NOT be repurposed as the shared Continuity State in this milestone.

---

## Decision 2 — Shared State Artifact Location

The canonical shared-state artifact path is reserved as:

```text
.ai/state/CURRENT-STATE.json
```

The intended shared publication surface is the `ai-control` branch.

M1 implementation SHALL define and validate the artifact contract, but SHALL NOT add automatic GitHub/control-branch write behavior to `bridge.py`.

Initial publication/update of the shared artifact may remain an explicit control-plane action until a later ADR authorizes automated state publication.

The artifact is a navigation / continuity snapshot, not an authorization token.

---

## Decision 3 — Continuity State Does Not Grant Authority

`CURRENT-STATE.json` MUST NOT authorize:

- RUN;
- FIX;
- MERGE;
- shell execution;
- browser execution;
- source mutation;
- Git push;
- any Executor Lease.

Human RUN/FIX/MERGE authority remains unchanged.

Existing Bridge authorization records remain authoritative for execution authorization.

If Continuity State conflicts with an authoritative TASK/REVIEW/authorization/Git ref, the Continuity State is considered stale and MUST NOT override the authoritative source.

---

## Decision 4 — Schema Version 1

M1 SHALL implement schema version:

```text
schema_version = "1"
```

The logical shape is:

```json
{
  "schema_version": "1",
  "task_id": "TASK-019",
  "phase": "READY_FOR_RUN",
  "next_operation": "RUN_APPROVAL",
  "main": {
    "branch": "main",
    "sha": "<40-hex-sha>"
  },
  "task_branch": {
    "branch": "ai/task-019",
    "sha": null
  },
  "artifacts": {
    "task": {
      "path": ".ai/tasks/TASK-019.md",
      "ref": "ai-control",
      "blob_sha": "<40-hex-blob>"
    },
    "contracts": [],
    "plan": null,
    "result": null,
    "review": null
  },
  "brain": {
    "last_id": "chatgpt-chat",
    "last_operation": "TASK_AND_PLAN"
  },
  "executor": {
    "last_id": null
  }
}
```

Equivalent field ordering is irrelevant because canonical serialization controls ordering.

No arbitrary free-form context body is allowed in this structure.

---

## Decision 5 — Lifecycle Phase Enum

M1 SHALL support exactly these phase values:

```text
TASK_DEFINED
READY_FOR_RUN
RUNNING
READY_FOR_REVIEW
CHANGES_REQUIRED
FIXING
APPROVED
MERGED
```

Semantics:

- `TASK_DEFINED`: TASK exists; additional PLAN/context may still be required.
- `READY_FOR_RUN`: required pre-execution control context is ready; waiting for human RUN approval.
- `RUNNING`: RUN has been authorized and execution/result is pending.
- `READY_FOR_REVIEW`: implementation RESULT exists; Brain review is next.
- `CHANGES_REQUIRED`: authoritative review requires changes; waiting for human FIX approval.
- `FIXING`: FIX has been authorized and corrected RESULT is pending.
- `APPROVED`: authoritative review approved the task; human merge decision is next.
- `MERGED`: approved task has been merged into canonical main.

M1 does not create an Executor Lease from these phases.

---

## Decision 6 — Next Operation Enum and Compatibility

M1 SHALL support exactly:

```text
PLAN
RUN_APPROVAL
WAIT_FOR_RESULT
REVIEW
FIX_APPROVAL
MERGE_APPROVAL
NONE
```

Valid phase -> next-operation mapping is locked:

```text
TASK_DEFINED      -> PLAN
READY_FOR_RUN     -> RUN_APPROVAL
RUNNING           -> WAIT_FOR_RESULT
READY_FOR_REVIEW  -> REVIEW
CHANGES_REQUIRED  -> FIX_APPROVAL
FIXING            -> WAIT_FOR_RESULT
APPROVED          -> MERGE_APPROVAL
MERGED            -> NONE
```

Invalid combinations MUST fail validation.

This field describes the expected next control operation. It does not authorize that operation.

---

## Decision 7 — Git Reference Contract

`main` SHALL contain:

```text
branch: non-empty safe Git branch/ref label
sha: exact lowercase 40-character hexadecimal commit SHA
```

`task_branch` SHALL contain:

```text
branch: non-empty safe Git branch/ref label
sha: null before a task branch exists, otherwise exact lowercase 40-character hexadecimal commit SHA
```

From phase `RUNNING` onward, `task_branch.sha` MUST be present.

No local filesystem path belongs in Git reference fields.

---

## Decision 8 — ArtifactRef Contract

Each artifact reference SHALL contain only:

```text
path
ref
blob_sha
```

Rules:

1. `path` must be a repository-relative POSIX path.
2. Absolute paths are forbidden.
3. `..` path traversal is forbidden.
4. Backslash-based local paths are forbidden.
5. Artifact paths in Continuity State must live under `.ai/`.
6. Sensitive-path references such as `.env`, private-key material, credential stores, or equivalent secret-bearing paths are forbidden.
7. `ref` must be a non-empty safe Git ref/branch label.
8. `blob_sha` must be an exact lowercase 40-character hexadecimal Git blob SHA.

State contains pointers/identities only — never artifact body contents.

---

## Decision 9 — Artifact Role Rules

`artifacts.task` is mandatory and MUST identify the active task:

```text
.ai/tasks/TASK-NNN.md
```

`artifacts.contracts` is a deterministic ordered tuple/list of zero or more contract/ADR references. Duplicate paths or duplicate `(ref, path, blob_sha)` identities are forbidden.

If present:

```text
artifacts.result -> .ai/results/RESULT-NNN.md
artifacts.review -> .ai/reviews/REVIEW-NNN.md
```

and their NNN task identity MUST match `task_id` exactly.

A PLAN/context artifact may use an `.ai/context/...` path but, if its filename declares a TASK identifier, that identifier MUST match the active `task_id`.

Phase requirements:

- `READY_FOR_REVIEW` requires `result`.
- `CHANGES_REQUIRED` requires both `result` and `review`.
- `FIXING` requires both `result` and `review`.
- `APPROVED` requires both `result` and `review`.
- `MERGED` requires both `result` and an approved review pointer.

M1 validation checks structural presence/identity, not semantic review-body status.

---

## Decision 10 — Brain / Executor Metadata Is Descriptive Only

Optional continuity metadata may identify:

```text
brain.last_id
brain.last_operation
executor.last_id
```

These identifiers are descriptive/audit hints only.

They MUST NOT:
- grant execution authority;
- select a vendor by core branching;
- imply an active Executor Lease;
- contain prompts, reasoning, chat transcript, credential, local path, or opaque session token.

Actor identifiers must use a conservative lowercase identifier format suitable for values such as:

```text
chatgpt-chat
claude-chat
gemini-chat
antigravity
codex
claude-code
```

`brain.last_operation`, when present, SHALL use a bounded enum defined by the implementation rather than arbitrary prose. M1 MUST include at least:

```text
TASK
TASK_AND_PLAN
PLAN
DIAGNOSIS
PATCH_PROPOSAL
REVIEW
```

---

## Decision 11 — Strict Parsing / Fail Closed

M1 parser SHALL reject:

- unsupported schema version;
- missing required fields;
- unknown top-level fields;
- unknown nested fields;
- wrong field types;
- invalid task IDs;
- invalid SHAs;
- unsafe paths;
- invalid phase/next-operation pairs;
- inconsistent task identities;
- duplicate contract artifacts;
- serialized state larger than the locked maximum.

Canonical task IDs remain strict and case-sensitive:

```regex
^TASK-\d+$
```

No lowercase/mixed-case normalization is permitted.

---

## Decision 12 — Compactness Limit

Canonical serialized Continuity State SHALL be limited to:

```text
MAX_SERIALIZED_BYTES = 16384
```

measured as UTF-8 bytes.

No truncation is allowed.

Oversized state fails closed.

The state must not become a manifest of the whole repository or a substitute for bounded ContextBuilder selection.

---

## Decision 13 — Canonical Serialization and Fingerprint

M1 SHALL provide deterministic canonical JSON serialization:

- UTF-8;
- stable key ordering;
- stable separators/format;
- no timestamps injected by serialization;
- final newline allowed/required consistently by implementation.

M1 SHALL provide a SHA-256 semantic fingerprint derived from canonical serialized state bytes.

The same semantic state MUST produce the same fingerprint across repeated runs.

Any semantic field change MUST change the fingerprint.

The fingerprint is evidence/freshness metadata only; it is not authorization.

---

## Decision 14 — Freshness Checking

M1 SHALL provide a pure, side-effect-free freshness comparison against explicit observed repository facts.

At minimum it must be able to detect:

- canonical main SHA drift;
- task branch SHA drift when a task SHA is recorded;
- known artifact blob identity drift when explicit observed blobs are supplied.

Freshness result SHALL distinguish at least:

```text
FRESH
STALE
INCOMPLETE
```

No network access, Git invocation, filesystem discovery, or automatic repair belongs inside the pure state contract.

Consumers obtain observations externally and pass them in.

A stale state may be used as a navigation hint to locate canonical inputs, but it MUST NOT be treated as current authority.

---

## Decision 15 — Implementation Namespace

M1 production code SHALL live in a separate continuity namespace, preferably:

```text
src/aios_bridge/continuity/
    __init__.py
    state.py
```

It MUST NOT be added to:

```text
src/providers/
src/aios_bridge/external_brain/
```

because Continuity State is neither Python Agent runtime LLM provider state nor External Brain provider state.

A small standalone validation CLI is allowed, preferably:

```text
scripts/aios_continuity_state.py
```

Allowed CLI operations in M1:

- validate an explicit JSON file path;
- print canonical fingerprint / bounded normalized metadata.

CLI MUST NOT:

- discover a repo implicitly;
- write source files;
- mutate Git;
- push/control branches;
- call APIs;
- invoke a Brain or Executor;
- carry credentials.

---

## Decision 16 — Existing Bridge v0.4 Must Remain Behaviorally Unchanged

M1 SHALL NOT modify existing Bridge v0.4 handoff, sync, authorization, publish, branch reconciliation, or merge authority semantics.

Specifically:

- existing `get_runtime_paths()["state"]` remains local runtime state;
- existing `update_state(...)` remains untouched unless a strictly necessary compatibility-only change is separately justified and reviewed;
- `.ai/state/CURRENT-STATE.json` MUST NOT be staged into task commits merely by reusing the local runtime state;
- no new automatic control-branch writer is introduced;
- no new inbound state prefix is required in M1;
- human RUN/FIX/MERGE gates remain exact.

The safest expected M1 implementation changes no `bridge.py` production behavior.

---

## Decision 17 — No Brain/Executor Routing in M1

M1 SHALL NOT implement:

- BrainAdapter invocation;
- Claude/Gemini integration;
- Codex/Claude Code integration;
- ExecutorAdapter;
- Executor Lease;
- quota router;
- model router;
- fallback;
- retry;
- MCP;
- chat-web browser automation;
- automatic API calls.

Those remain later milestones under ADR-010.

---

## Decision 18 — Security / Privacy

Continuity State MUST NOT persist:

- API keys;
- OAuth/session tokens;
- cookies;
- Authorization headers;
- private-key material;
- raw HTTP requests/responses;
- hidden/separated reasoning;
- chat transcripts;
- arbitrary prompt bodies;
- local absolute paths;
- browser profile locations.

State is metadata and artifact identities only.

---

## Decision 19 — Required M1 Tests

Automated tests SHALL cover at minimum:

1. valid schema-v1 parse;
2. deterministic round-trip canonical serialization;
3. deterministic fingerprint;
4. semantic field change changes fingerprint;
5. strict case-sensitive task ID rejection;
6. invalid/uppercase/non-40-hex SHA rejection;
7. unsafe absolute / traversal / backslash path rejection;
8. sensitive artifact-path rejection;
9. unknown-field rejection;
10. invalid phase/next-operation pair rejection;
11. missing `task_branch.sha` from RUNNING onward rejection;
12. task/result/review identity mismatch rejection;
13. duplicate contract reference rejection;
14. phase-required result/review presence enforcement;
15. 16 KiB size cap fail-closed with no truncation;
16. FRESH observed refs case;
17. STALE main SHA case;
18. STALE task SHA case;
19. STALE artifact blob case;
20. INCOMPLETE observation case;
21. actor ID / operation bounded validation;
22. no secret/reasoning/content fields accepted;
23. CLI validation success/failure without network;
24. existing AIOS Bridge / External Brain suites remain green;
25. full repository tests remain green.

No live provider or external-network call is allowed in automated M1 tests.

---

## Decision 20 — M1 Completion Evidence

The implementing RESULT MUST record:

- exact implementation SHA tested;
- changed-file summary;
- focused Continuity State test command/result;
- full `tests/aios_bridge/` command/result;
- full repository `tests/` command/result;
- schema version;
- max serialized bytes;
- sample deterministic state fingerprint from a non-secret test fixture;
- confirmation `BRIDGE_V0_4_BEHAVIOR_CHANGED: NO` unless separately approved;
- confirmation `LIVE_EXTERNAL_CALLS: 0`;
- confirmation `AUTHORITY_WIDENED: NO`;
- confirmation `SECRETS_OR_REASONING_PERSISTED: NO`.

After M1 is approved and merged, the control plane may publish the first real `.ai/state/CURRENT-STATE.json` on `ai-control` using the locked schema and current Git/artifact identities.

---

## Decision 21 — M1 Success Gate

M1 is successful only if:

1. state is compact and deterministic;
2. state is independently parseable by any future Brain/Executor integration;
3. state identifies canonical sources without embedding their content;
4. stale state can be detected fail-closed from explicit observations;
5. state cannot authorize execution or merge;
6. existing Bridge runtime state remains separate;
7. no vendor-specific logic enters Continuity Core;
8. all tests are green.

Only after this gate may #12 proceed to M2 Brain-Neutral Contract / Context Handoff.
