# TASK-019 — Open Multi-Agent Continuity OS M1 Canonical Project State

## Objective

Implement **#12-M1 Canonical Project State** exactly as locked by:

```text
.ai/decisions/ADR-010-OPEN-MULTI-AGENT-CONTINUITY-OS-ARCHITECTURE-LOCK.md
.ai/decisions/ADR-011-AIOS-CONTINUITY-M1-CANONICAL-PROJECT-STATE-CONTRACT-LOCK.md
```

Canonical implementation baseline when authored:

```text
main = 689c2c6dd8e41fe0f735b822118ba6530379b7dd
```

TASK-017 / M3.1 is merged and proven. ADR-010 supersedes the old API-first #12 direction while preserving External Brain as an optional fallback.

This TASK starts the new **Open Multi-Agent Continuity OS** implementation.

The goal is to create a small, deterministic, vendor-neutral Continuity State contract that a future ChatGPT / Claude / Gemini Brain or Antigravity / Codex / Claude Code Executor integration can parse without needing prior conversation history.

## Critical Existing-State Observation

`bridge.py` already has a local external-runtime state file:

```text
get_runtime_paths()["state"] -> .../state/CURRENT_STATE.json
```

and an existing `update_state(...)` helper.

That file is **Bridge Runtime State**, not the new shared Continuity State.

Do NOT repurpose it.

M1 must keep these two concepts separate.

## Implementation Scope

Preferred production namespace:

```text
src/aios_bridge/continuity/
    __init__.py
    state.py
```

Preferred focused tests:

```text
tests/aios_bridge/continuity/
    __init__.py
    test_state.py
```

Optional small CLI if useful and kept narrow:

```text
scripts/aios_continuity_state.py
```

Avoid touching `bridge.py`. If any Bridge production change appears necessary, STOP and report why before implementing it because ADR-011 expects M1 to preserve Bridge v0.4 behavior unchanged.

## Required Data Contract

Implement strict immutable/bounded types equivalent to the following logical concepts. Exact internal class names may vary if semantics are identical.

### Lifecycle enums

```text
ContinuityPhase:
- TASK_DEFINED
- READY_FOR_RUN
- RUNNING
- READY_FOR_REVIEW
- CHANGES_REQUIRED
- FIXING
- APPROVED
- MERGED

NextOperation:
- PLAN
- RUN_APPROVAL
- WAIT_FOR_RESULT
- REVIEW
- FIX_APPROVAL
- MERGE_APPROVAL
- NONE
```

Locked compatibility mapping:

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

### Git branch/ref pointer

Conceptually:

```python
BranchState(
    branch: str,
    sha: str | None,
)
```

Rules:
- main SHA always exact lowercase 40-hex;
- task branch SHA may be `None` before branch creation;
- task branch SHA required from `RUNNING` onward;
- no local filesystem path semantics.

### Artifact pointer

Conceptually:

```python
ArtifactRef(
    path: str,
    ref: str,
    blob_sha: str,
)
```

Rules locked by ADR-011:
- repo-relative POSIX path only;
- under `.ai/` only;
- no absolute path;
- no `..` traversal;
- no backslashes;
- no sensitive/secret-bearing artifact paths;
- exact lowercase 40-hex Git blob SHA;
- pointer only, never file body.

### Artifact set

Conceptually:

```python
ContinuityArtifacts(
    task: ArtifactRef,
    contracts: tuple[ArtifactRef, ...],
    plan: ArtifactRef | None,
    result: ArtifactRef | None,
    review: ArtifactRef | None,
)
```

Enforce task identity consistency:

```text
TASK-NNN
RESULT-NNN
REVIEW-NNN
```

must match the active `task_id` exactly when present.

Contract references must be deterministic and duplicate-free.

### Descriptive actor metadata

Conceptually:

```python
BrainState(
    last_id: str | None,
    last_operation: BrainOperation | None,
)

ExecutorState(
    last_id: str | None,
)
```

Brain operations must be bounded and include at least:

```text
TASK
TASK_AND_PLAN
PLAN
DIAGNOSIS
PATCH_PROPOSAL
REVIEW
```

Actor IDs use conservative lowercase identifiers suitable for:

```text
chatgpt-chat
claude-chat
gemini-chat
antigravity
codex
claude-code
```

These fields are metadata only. They do not select vendors or grant authority.

### Top-level state

Conceptually:

```python
ContinuityState(
    schema_version="1",
    task_id="TASK-019",
    phase=ContinuityPhase.READY_FOR_RUN,
    next_operation=NextOperation.RUN_APPROVAL,
    main=...,
    task_branch=...,
    artifacts=...,
    brain=...,
    executor=...,
)
```

Prefer frozen dataclasses / immutable tuples where practical.

## Strict Validation

Parser/constructor validation must fail closed for:

- unsupported schema version;
- missing required fields;
- unknown fields at every locked object layer;
- wrong types, including bool masquerading as int-like data where relevant;
- task ID not matching exact case-sensitive `^TASK-\d+$`;
- SHA not exact lowercase 40-hex;
- unsafe artifact paths;
- invalid phase/next-operation pair;
- missing task branch SHA in phases requiring it;
- mismatched TASK/RESULT/REVIEW identity;
- duplicate contracts;
- phase-required result/review omissions;
- invalid actor IDs/operations;
- state larger than 16 KiB UTF-8.

Do not normalize invalid lowercase task IDs into uppercase.

Do not silently drop unknown fields.

## Phase Artifact Requirements

At minimum enforce:

```text
READY_FOR_REVIEW -> result required
CHANGES_REQUIRED -> result + review required
FIXING           -> result + review required
APPROVED         -> result + review required
MERGED           -> result + review required
```

Structural validation does not need to parse REVIEW markdown status in M1.

## Serialization

Provide deterministic canonical JSON serialization.

Requirements:

```text
schema_version = "1"
MAX_SERIALIZED_BYTES = 16384
```

- UTF-8;
- stable key ordering/format;
- no injected timestamp;
- no truncation;
- oversize -> fail closed.

Provide a deterministic SHA-256 fingerprint of canonical serialized bytes.

Same semantic state -> same fingerprint.
Any semantic field change -> different fingerprint.

## Freshness Contract

Implement a pure explicit-observation freshness check.

It must not call Git, network, filesystem discovery, GitHub, Brain, or Executor.

The caller supplies observed facts.

At minimum detect:

```text
FRESH
STALE
INCOMPLETE
```

for:
- main SHA;
- task branch SHA when state records one;
- artifact blob SHAs when explicit observations are supplied.

Return bounded machine-readable reasons rather than free-form hidden context.

A stale state may help locate artifacts but must never become authority.

## Optional CLI

If implemented, CLI may only:

```text
validate <explicit-json-path>
fingerprint <explicit-json-path>
```

or an equally narrow interface.

It may print safe bounded metadata.

It MUST NOT:
- discover the repo implicitly;
- call Git/network/API;
- mutate source/Git/control branch;
- execute tools;
- accept credentials;
- invoke MiniMax or another Brain;
- invoke Antigravity/Codex/Claude Code.

## Forbidden Scope

Do NOT implement in TASK-019:

- BrainAdapter invocation;
- Claude Chat integration;
- Gemini Chat integration;
- Codex integration;
- Claude Code integration;
- ExecutorAdapter;
- Executor Lease;
- Executor failover;
- Brain failover;
- quota routing;
- model routing;
- API fallback logic;
- retries;
- MCP;
- browser automation;
- automatic GitHub/control-branch state writes;
- changes to existing External Brain provider semantics;
- changes to Python Agent `src/providers/`;
- human RUN/FIX/MERGE authority changes.

## Security Invariants

Continuity State must not persist:

```text
API keys
OAuth/session tokens
cookies
Authorization headers
private keys
raw HTTP
hidden/separated reasoning
chat transcripts
prompt bodies
local absolute paths
browser profile paths
```

Do not add generic `notes`, `context`, `metadata`, `extra`, or arbitrary free-form dict escape hatches to schema v1.

## Required Tests

Implement at least the semantic coverage locked by ADR-011, including:

1. valid schema-v1 parse;
2. deterministic canonical round-trip;
3. deterministic fingerprint;
4. fingerprint changes with semantic change;
5. strict case-sensitive TASK ID;
6. SHA validation;
7. path safety validation;
8. sensitive path rejection;
9. strict unknown-field rejection;
10. phase/next-operation compatibility;
11. task branch SHA requirement from RUNNING onward;
12. TASK/RESULT/REVIEW task identity consistency;
13. duplicate contract rejection;
14. phase-required artifacts;
15. 16 KiB cap/no truncation;
16. freshness FRESH;
17. stale main SHA;
18. stale task SHA;
19. stale artifact blob;
20. incomplete observations;
21. actor ID and operation validation;
22. secret/reasoning/free-form fields rejected;
23. optional CLI success/failure if CLI exists;
24. all existing AIOS Bridge / External Brain tests green;
25. full repository tests green.

No live provider/network call in tests.

## Test Commands

At minimum run:

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

Use the repository's actual venv/python invocation if required on Windows.

## RESULT-019 Required Evidence

RESULT must include:

```text
IMPLEMENTATION_HEAD: <exact tested commit SHA>
SCHEMA_VERSION: 1
MAX_SERIALIZED_BYTES: 16384
SAMPLE_STATE_FINGERPRINT: <sha256 from non-secret fixture>
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
LIVE_EXTERNAL_CALLS: 0
AUTHORITY_WIDENED: NO
SECRETS_OR_REASONING_PERSISTED: NO
```

Also include:
- exact changed-file list;
- focused Continuity test result;
- full `tests/aios_bridge/` result;
- full repository result;
- any deviation from the ChatGPT PLAN and why.

## ChatGPT PLAN

A ChatGPT-authored advisory implementation plan for this task is published separately at:

```text
.ai/context/TASK-019-CHATGPT-PLAN.md
```

The TASK + ADR contract is authoritative. The PLAN is implementation guidance and does not authorize execution.

## Completion Gate

Do not claim M1 complete until:

- strict state contract exists;
- canonical serialization/fingerprint works;
- freshness checking works from explicit observations;
- state contains pointers rather than context bodies;
- Bridge runtime state remains separate;
- no vendor-specific routing exists;
- all required tests pass;
- ChatGPT review approves RESULT-019.
