# TASK-019 — ChatGPT PLAN

STATUS: ADVISORY
BRAIN_ID: chatgpt-chat
BRAIN_OPERATION: TASK_AND_PLAN
TASK_ID: TASK-019
TASK_BLOB: adc44f449f2a991a455b8039d8e8978fe4643146
ARCHITECTURE_CONTRACT: ADR-010 / 504630c25f37c83819ae951076704765609105c7
M1_CONTRACT: ADR-011 / 0ce561b1de5c964bb93ea0a5a127b48d86a65839
BASE_MAIN: 689c2c6dd8e41fe0f735b822118ba6530379b7dd
AUTHORIZATION: NONE — human RUN approval remains required

## SUMMARY

Implement the M1 Continuity State as a **pure, strict, dependency-light contract layer** separate from both `bridge.py` runtime state and `external_brain`.

The implementation should be boring and deterministic: frozen data objects/enums, strict JSON parsing, semantic validation, canonical serialization/fingerprint, and pure freshness comparison. Avoid introducing a state machine engine, publisher, router, Git wrapper, or vendor integration.

The central design test is that the same JSON state can later be consumed by ChatGPT, Claude, Gemini, Antigravity, Codex, or Claude Code integrations without any vendor-specific branch in Continuity Core.

## STEPS

### 1. Create the continuity namespace

Add:

```text
src/aios_bridge/continuity/__init__.py
src/aios_bridge/continuity/state.py
```

Keep this namespace independent from:

```text
src/aios_bridge/external_brain/
src/providers/
bridge.py runtime state
```

Use only standard-library dependencies unless an already-required repository dependency gives a clearly safer solution. Prefer standard library for portability.

### 2. Define bounded enums and immutable records

In `state.py`, define enums equivalent to:

```text
ContinuityPhase
NextOperation
BrainOperation
FreshnessStatus
```

Define frozen/immutable records equivalent to:

```text
BranchState
ArtifactRef
ContinuityArtifacts
BrainState
ExecutorState
ContinuityState
StateObservation
FreshnessIssue / FreshnessReport
```

Do not include generic `extra`, `metadata`, `notes`, `context`, or arbitrary dict payloads.

Keep descriptive actor state minimal. Do not model Executor Lease yet.

### 3. Centralize strict primitive validators

Implement narrow helpers for:

```text
TASK ID
40-hex lowercase SHA
safe actor ID
safe Git ref/branch label
safe .ai artifact path
sensitive artifact-path rejection
```

Canonical TASK ID regex must remain case-sensitive:

```regex
^TASK-\d+$
```

Artifact path validation should operate on repository-relative POSIX strings and reject absolute paths, `..`, backslashes, empty segments where unsafe, and secret-bearing path patterns.

Do not reuse a permissive parser from another subsystem if it changes these semantics.

### 4. Implement strict schema-v1 parsing

Provide one explicit parser entry point such as:

```python
parse_continuity_state(text: str) -> ContinuityState
```

or:

```python
ContinuityState.from_json(text)
```

Requirements:

- UTF-8 JSON object semantics;
- exact schema version `"1"`;
- exact allowed keys at each locked layer;
- reject unknown fields rather than ignoring them;
- reject wrong types;
- reject invalid phase/next-operation combination;
- enforce phase-required artifacts;
- enforce task identity consistency;
- enforce contract uniqueness;
- enforce 16 KiB input/canonical serialization bound without truncation.

Prefer explicit field extraction/validation over magical coercion.

### 5. Implement semantic state validation

Keep phase rules in a single deterministic table, for example:

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

Keep artifact requirements in one bounded mapping/table as well.

Require `task_branch.sha` from `RUNNING` onward.

Do not parse REVIEW markdown body in M1; pointer identity/presence is sufficient.

### 6. Implement canonical serialization and fingerprint

Provide deterministic functions/methods equivalent to:

```python
to_canonical_json(state) -> str
state_fingerprint(state) -> str
```

Canonical serialization should use a stable primitive representation, stable key ordering, UTF-8, and one consistent final-newline policy.

Fingerprint:

```text
sha256(canonical_utf8_bytes)
```

No current time, random ID, machine path, or process state may affect serialization/fingerprint.

### 7. Implement pure freshness checking

Implement a function equivalent to:

```python
check_freshness(
    state: ContinuityState,
    observation: StateObservation,
) -> FreshnessReport
```

Observation is explicit input; no Git/network/filesystem access inside this function.

At minimum compare:

```text
main commit SHA
task branch commit SHA when state has one
artifact blob SHAs for observed artifact identities
```

Use bounded machine-readable issue codes such as:

```text
MAIN_SHA_MISMATCH
TASK_SHA_MISMATCH
ARTIFACT_BLOB_MISMATCH
MISSING_MAIN_OBSERVATION
MISSING_TASK_OBSERVATION
MISSING_ARTIFACT_OBSERVATION
```

Equivalent names are acceptable if stable and tested.

Recommended precedence:

```text
any mismatch -> STALE
otherwise any required observation missing -> INCOMPLETE
otherwise -> FRESH
```

Freshness checking never repairs state and never authorizes action.

### 8. Add a narrow CLI only if it remains cheap and clear

Preferred optional file:

```text
scripts/aios_continuity_state.py
```

Useful commands:

```text
validate <path>
fingerprint <path>
```

The CLI should be a thin wrapper around the contract module.

It must not perform repo discovery, Git calls, network access, API calls, mutation, or vendor execution.

If adding the CLI creates unnecessary complexity, omit it and explain in RESULT; the core state contract is mandatory, the CLI is not.

### 9. Build focused tests from the ADR matrix

Add:

```text
tests/aios_bridge/continuity/__init__.py
tests/aios_bridge/continuity/test_state.py
```

A small test fixture/helper file is acceptable if it keeps tests readable.

Test invalid inputs independently rather than combining many failure causes into one fixture.

Include at least one valid fixture matching the intended first shared state shape:

```text
TASK-019
READY_FOR_RUN
RUN_APPROVAL
main = 689c2c6...
task branch SHA = null
ChatGPT TASK_AND_PLAN
```

Use fake hexadecimal SHAs or repository-safe real public SHAs only; never secrets.

### 10. Protect Bridge compatibility explicitly

Do not edit `bridge.py` during normal implementation.

Before publish, verify changed files do not include `bridge.py` unless a previously approved exception exists.

Run existing Bridge/External Brain tests to prove no regression.

### 11. Produce bounded RESULT evidence

RESULT-019 must identify the exact tested implementation commit, test counts, state schema constants, sample non-secret fixture fingerprint, and the locked safety confirmations from TASK-019.

No live MiniMax/OpenAI/Claude/Gemini call is needed or allowed for M1 implementation/tests.

## FILES

Expected production changes:

```text
src/aios_bridge/continuity/__init__.py
src/aios_bridge/continuity/state.py
```

Expected tests:

```text
tests/aios_bridge/continuity/__init__.py
tests/aios_bridge/continuity/test_state.py
```

Optional:

```text
scripts/aios_continuity_state.py
```

Expected unchanged high-risk files:

```text
bridge.py
src/aios_bridge/external_brain/*
src/providers/*
```

## TESTS

Run, at minimum:

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

Focused semantic expectations:

- exact schema-v1 acceptance/rejection;
- strict unknown-field behavior at nested levels;
- exact case-sensitive TASK ID behavior;
- exact SHA/path validation;
- lifecycle compatibility;
- phase artifact requirements;
- size cap;
- deterministic serialization/fingerprint;
- freshness FRESH/STALE/INCOMPLETE;
- actor metadata bounds;
- no generic secret/reasoning/free-form escape fields.

Automated external calls must remain zero.

## RISKS

1. **Accidentally conflating runtime state and shared continuity state.**
   Mitigation: separate namespace; no `bridge.py` change in M1.

2. **Over-designing a state machine too early.**
   Mitigation: M1 defines snapshot contract and pure validation only; no transition engine/lease/router.

3. **Schema becoming an arbitrary metadata dump.**
   Mitigation: strict keys, bounded enums, 16 KiB cap, no free-form extension map.

4. **Stale state being mistaken for authority.**
   Mitigation: explicit freshness contract and non-authorizing invariant.

5. **Vendor leakage into core.**
   Mitigation: actor IDs are data only; no vendor `if/elif` behavior.

6. **Future need for schema evolution.**
   Mitigation: exact `schema_version="1"`; later changes require schema version/ADR rather than silent widening.

7. **Sensitive path leakage through artifact references.**
   Mitigation: conservative `.ai/` path restriction + secret-bearing path deny rules.

## ADOPTION

PLAN_ADOPTION: ACCEPTED_AS_CHATGPT_PRIMARY_BRAIN_PLAN
CHATGPT_REPLAN_REQUIRED: NO

This PLAN is advisory. TASK-019 + ADR-010 + ADR-011 remain authoritative, and human `/aios-worker RUN TASK-019` approval remains mandatory before Antigravity implementation.
