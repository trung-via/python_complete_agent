# ADR-032 — E4 Approved Executor Automation & Auto Publication Contract Lock

STATUS: LOCKED

## Context

E1 / ADR-029 established the vendor-neutral invocation contract.
E2 / ADR-030 established the local Codex transport.
E3 / ADR-031 established deterministic bounded context-pack composition.

E4 connects those proven pieces to the existing Bridge lifecycle without weakening Human authority.

```text
E1 — Executor Invocation Contract                  COMPLETE
E2 — Codex Local Transport                         COMPLETE
E3 — Bounded Context Pack Delivery                 COMPLETE
E4 — Result Collection + Auto Publication          THIS ADR
E5 — Zero-Copy/Paste Operational Proof
```

E4 is operational integration, not a new dispatcher, provider framework, event journal, execution envelope, or driver framework.
H-Series remains DEFERRED.

---

## Decision 1 — Explicitly Authorized Execution Only

E4 SHALL add a Bridge command conceptually:

```text
bridge.py execute <task_id>
```

`execute` is NOT an approval command.

Before any Executor process may start, E4 MUST require all of the following to already exist and match exactly:

- ACTIVE Human-created Bridge authorization;
- exact active `ExecutorLease` reconstructed from that authorization;
- current workspace ID;
- expected task branch;
- exact authorized RUN/FIX control artifact blob;
- current branch HEAD captured before execution;
- clean worktree.

E4 MUST NOT:
- create approval;
- infer approval from recommendation;
- select an executor;
- acquire a lease;
- alter RUN/FIX/MERGE authority;
- auto-merge.

The authority chain remains:

```text
recommendation != authorization != lease != invocation != receipt != publication != merge
```

---

## Decision 2 — E4 v1 Automated Transport Is Codex Local Only

E4 v1 SHALL automatically invoke only when:

```text
authorization.executor_id == "codex"
```

using the already-proven:

```text
CodexLocalTransport
transport_id = codex-local-v1
```

For `antigravity`, `claude-code`, or any executor without a proven E-Series transport, `execute` fails closed before mutation.

There is no fallback transport and no silent actor switch.

This limitation is intentional and does not modify M10 dispatch semantics.

---

## Decision 3 — Exact Machine-Readable Executor Context Refs

Every control artifact intended for E4 automatic execution MUST contain exactly one marker:

```text
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/...","blob_sha":"<40-lower-hex>"}, ...]
```

The marker is part of the exact Human-authorized work artifact blob and therefore transitively binds the allowed executor context.

Rules:
- JSON root is a non-empty ordered list;
- maximum context refs = 7, preserving E3 total artifact maximum of 8 including WORK;
- every object contains exactly `path` and `blob_sha`;
- path must be a canonical safe `.ai/` artifact path;
- blob SHA must be exact lowercase 40-hex;
- paths unique;
- marker refs cannot duplicate the active work artifact path;
- no scan, glob, nearest-match, inferred ADR, inferred blueprint, history fallback, or arbitrary repo context.

For RUN, WORK is the exact TASK and the marker normally names ADR/blueprint/context artifacts.

For FIX, WORK is the exact REVIEW and its marker MUST include the exact original TASK ref plus every other context ref needed for the bounded fix.

A CHANGES_REQUIRED review intended for E4 auto-FIX must therefore carry its own exact context marker.

---

## Decision 4 — Exact Machine-Readable Worktree Scope

Every control artifact intended for E4 automatic execution MUST also contain exactly one marker:

```text
EXECUTOR_ALLOWED_PATHS_JSON: ["path/one", "path/two", ...]
```

Rules:
- non-empty ordered list;
- exact unique repository-relative POSIX paths;
- no absolute paths, `..`, empty components, or backslashes;
- `.git/**` forbidden;
- Bridge/runtime control paths such as `.ai/results/**`, `.ai/auth/**`, `.ai/inbox/**`, `.ai/state/**`, and external runtime paths are forbidden;
- RESULT is Bridge-generated and MUST NOT be granted to the Executor.

After Codex exits and before any test/publication step, E4 SHALL mechanically collect the complete dirty-path set from Git using tracked/staged/unstaged plus untracked evidence and require:

```text
dirty_paths != empty
dirty_paths subset_of exact allowed paths
```

Rename/copy evidence MUST account for both source and destination paths when Git reports both.

Any out-of-scope mutation blocks publication.

---

## Decision 5 — Freeze One Exact Control Snapshot and Read Raw Bytes

E4 SHALL:
1. fetch the configured control branch;
2. resolve one exact 40-hex control commit SHA;
3. revalidate the authorized work artifact blob against that snapshot;
4. resolve every context marker path against that same snapshot;
5. require every resolved blob SHA to equal the marker's exact expected blob SHA;
6. read artifact contents as exact raw bytes from Git object storage.

Raw artifact loading MUST preserve BOM, CRLF, trailing spaces, and all other bytes.

E4 MUST NOT use the existing text-mode `read_remote_file()` path to build E3 payload bytes.

UTF-8 / NUL / Git-blob verification remains E3's final fail-closed authority for the bytes themselves.

---

## Decision 6 — Reuse M1 State and M4 Request Semantics

E4 SHALL NOT invent a second execution-state model.

Before E3 composition, E4 SHALL build one immutable M1 `ContinuityState` launch snapshot from exact observed facts.

For RUN:

```text
phase = RUNNING
next_operation = WAIT_FOR_RESULT
artifacts.task = exact authorized TASK
artifacts.contracts = exact context refs
result = None
review = None
```

For FIX:

```text
phase = FIXING
next_operation = WAIT_FOR_RESULT
artifacts.task = exact TASK ref declared by REVIEW context marker
artifacts.contracts = remaining exact context refs
artifacts.result = exact prior RESULT blob at pre-execution task HEAD
artifacts.review = exact authorized REVIEW
```

The state also binds:
- exact configured main branch SHA;
- exact task branch + pre-execution HEAD;
- selected executor ID as descriptive executor state only.

E4 SHALL create an explicit `StateObservation` from independently gathered Git facts and require `check_freshness(...).status == FRESH`.

Then E4 SHALL construct M4 `ExecutionRequest` and `PreparedExecution`, and call `validate_execution_request_against_state()` plus `validate_prepared_execution_against_request()`.

No production modification to M1 or M4 contracts is allowed.

---

## Decision 7 — Reuse M10 Policy Only as Capability Contract

E4 SHALL parse the existing exact:

```text
DISPATCH_EXECUTOR_POLICY_JSON
```

from the active authorized work artifact.

Requirements:
- policy operation equals active authorization action;
- exact active executor appears exactly once in policy candidates;
- candidate supports the requested operation;
- M4 `ExecutionRequest.required_capabilities` comes from the policy required-capability set;
- `validate_executor_eligibility()` passes for the exact selected candidate.

This does NOT run a new recommendation and does NOT change the Human-selected executor.

If the authorized executor is not automation-compatible with the artifact policy, E4 fails closed and leaves the existing manual path available.

---

## Decision 8 — Deterministic Runtime IDs

Within one ACTIVE lease, E4 SHALL derive deterministic bounded IDs from exact `task_id` + `lease_fingerprint`, with no clock/random values:

```text
request_id
execution_id
invocation_id
```

Repeated construction from the same active authorization/lease and exact repository/control snapshot MUST yield the same request/prepared/invocation identities and E3 payload.

No invocation ID may encode secrets, host paths, usernames, or timestamps.

---

## Decision 9 — Build E3 Pack, Then Invoke E2 Exactly Once

E4 SHALL construct:
- exact `ExecutorAuthorizationBinding` from ACTIVE Bridge authorization;
- exact M4 request/prepared objects;
- exact context bytes mapping;
- E3 `ExecutorContextPack`;

then call:

```text
CodexLocalTransport.invoke(pack.invocation, pack.payload)
```

at most once per `execute` call.

No automatic retry is allowed.

E4 MUST NOT use:
- danger-full-access;
- sandbox bypass;
- alternate Codex argv;
- API-key fallback;
- paid API fallback.

E2 remains the sole process-transport authority.

---

## Decision 10 — Post-Invocation Git Integrity Gate

Capture before invocation:

```text
pre_branch
pre_head_sha
```

After E2 returns, before publication, E4 SHALL require:

```text
post_branch == pre_branch == authorized target branch
post_head_sha == pre_head_sha
```

Thus the Executor may edit permitted worktree files but MUST NOT commit, switch branches, rebase, merge, or advance HEAD.

If branch/HEAD changed, auto-publication is forbidden and runtime state becomes recovery-required.

---

## Decision 11 — Invocation Receipt Evidence Is External and Non-Authoritative

E4 SHALL persist a bounded, non-secret execution evidence record outside the Git worktree after E2 returns and before auto-publication.

The record may contain only deterministic/non-secret identities such as:
- task ID;
- action;
- executor/transport ID;
- control snapshot SHA;
- pre-execution HEAD;
- E3 manifest fingerprint;
- invocation fingerprint;
- payload SHA-256 and size;
- E1 `InvocationReceipt` dictionary/fingerprint;
- observed post-execution dirty paths.

It MUST NOT contain:
- raw context payload;
- prompts;
- stdout/stderr;
- secrets;
- API keys/tokens/cookies;
- chain-of-thought;
- approval tokens.

This is a single E4 execution receipt, NOT H1 Event Journal.

If evidence persistence/read-back fails after Executor execution, E4 MUST NOT auto-publish.

---

## Decision 12 — Transport Success Is Not Task Success

Only:

```text
InvocationStatus.EXITED_ZERO
```

may proceed toward publication.

Even then, EXITED_ZERO means transport success only.

Before publication E4 must still pass:
- unchanged branch/HEAD gate;
- allowed dirty-path gate;
- non-empty executor delta;
- existing Bridge publish authorization/lease/control/failover/hot-handoff revalidation;
- full repository test gate.

All non-zero/timeout/interrupted/start-failure receipts block automatic publication.

No receipt status may imply review PASS or merge authority.

---

## Decision 13 — Reuse Existing Bridge Publisher

E4 MUST NOT create a second commit/push implementation.

After all E4 gates pass, `execute` SHALL call the existing `cmd_publish()` path internally with:

```text
action = exact ACTIVE authorization action
full test command = current Python interpreter + -m pytest tests/ -q
summary = E4 automatic Codex execution summary
notes = bounded E4 fingerprints/status evidence
```

The full-suite command is fixed by E4 v1 for this Python Agent repository and MUST NOT be taken from TASK/REVIEW prose or arbitrary caller input.

This repository-specific test-driver choice does NOT activate H5 Driver Contract.

`cmd_publish()` remains responsible for:
- final active authorization/lease validation;
- control artifact revalidation;
- failover/hot-handoff validation;
- full tests;
- RESULT generation;
- commit;
- non-force push;
- exact lease release after push;
- authorization transition ACTIVE -> CONSUMED;
- published SHA persistence;
- IN_REVIEW state.

No auto-merge is added.

---

## Decision 14 — Post-Publication Canonical Result Verification

After `cmd_publish()` returns successfully, E4 SHALL:
- reload authorization and require `status == CONSUMED`;
- require exact 40-hex `published_sha`;
- resolve exact `.ai/results/RESULT-NNN.md` blob at that published SHA;
- build a canonical M4 `ExecutionResult(status=SUCCESS)` using the exact published SHA and RESULT `ArtifactRef`;
- call `validate_execution_result_against_request()`.

A failure here is a post-publication integrity failure and MUST be surfaced as recovery-required; E4 cannot rewrite history or force-push to undo an already successful publication.

The RESULT remains review evidence, not review approval.

---

## Decision 15 — Failure Semantics

Before Executor spawn: any E4 validation failure causes zero Executor invocation and zero publication.

After Executor spawn but before publication:
- FAILED_TO_START: no publication;
- EXITED_NONZERO: no publication;
- TIMED_OUT: no publication;
- INTERRUPTED: no publication;
- receipt persistence failure: no publication;
- branch/HEAD drift: no publication;
- no worktree changes: no publication;
- out-of-scope changes: no publication.

Authorization and lease are not silently consumed or released by E4 failure handling.
Human recovery remains explicit through existing diagnostics/release tools.

E4 never automatically retries, resets, cleans, stashes, reverts, or deletes Executor work.

---

## Decision 16 — CLI / UX Boundary

After E4, the intended Codex flow becomes:

```powershell
bridge.py approve N --kind task --executor codex
bridge.py execute N
```

or for FIX:

```powershell
bridge.py approve N --kind review --executor codex
bridge.py execute N
```

No manual `bridge.py context`, no manual prompt assembly/copy-paste, and no manual `bridge.py publish` are required on the E4 happy path.

E4 does NOT merge these two Human/Execution commands into one authorization command. E5 proves the operational zero-copy/paste path; any future convenience UX must preserve the same authority boundary.

---

## Decision 17 — Required Tests

All TASK-043 implementation tests MUST use fake/mocked transport invocation. TASK-043 MUST NOT recursively launch a real Codex process through E2.

Required positive tests include:
- RUN launch-plan construction from exact ACTIVE evidence;
- FIX launch-plan construction with prior RESULT + exact TASK context;
- exact binary Git blob loading helper behavior through mocks/temporary Git repo;
- M1 state freshness PASS;
- M4 request/state/prepared validation PASS;
- M10 capability eligibility PASS;
- E3 pack validation PASS;
- E2 fake EXITED_ZERO -> scope gate -> existing publisher invoked exactly once;
- auto-publish arguments fixed to full repo suite;
- bounded E4 evidence propagated into RESULT notes;
- successful post-publish M4 ExecutionResult validation;
- no manual context/prompt/publish required in happy-path integration test.

Required adversarial tests include:
- no ACTIVE auth;
- wrong branch/workspace/lease;
- non-codex executor;
- missing/duplicate/malformed context marker;
- context blob drift;
- missing/duplicate/malformed allowed-path marker;
- work artifact path leaked into context marker;
- FIX marker missing exact TASK ref;
- dispatch policy action mismatch;
- selected executor absent/ineligible;
- control snapshot/blob drift;
- text-normalization cannot satisfy binary artifact identity tests;
- E2 FAILED_TO_START/NONZERO/TIMEOUT/INTERRUPTED -> zero publish;
- Executor branch switch -> zero publish;
- Executor HEAD advance/commit -> zero publish;
- empty Executor delta -> zero publish;
- out-of-scope tracked mutation -> zero publish;
- out-of-scope untracked file -> zero publish;
- rename touching forbidden source/destination -> zero publish;
- evidence persistence failure -> zero publish;
- full test failure -> existing publish fail-closed behavior preserved;
- no automatic retry;
- no auto merge;
- no authority/lease acquisition in execute;
- E1/E2/E3/M1/M4/M5/M10 production contracts unchanged.

---

## Decision 18 — Expected Implementation Boundary

Allowed expected production changes:

```text
bridge.py
src/aios_bridge/executor_automation.py
```

Expected tests:

```text
tests/aios_bridge/test_executor_automation.py
tests/test_bridge_executor_automation.py
```

Bridge publication may generate:

```text
.ai/results/RESULT-043.md
```

Forbidden production changes:

```text
src/aios_bridge/continuity/**
src/aios_bridge/executor_transports/**
src/aios_bridge/executor_context.py
src/aios_bridge/runtime_dispatch.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/external_brain/**
src/providers/**
```

No E5, M11, or H1-H5 implementation.

---

## E4 Acceptance

```text
HUMAN_AUTHORITY_UNCHANGED: PASS
EXECUTE_REQUIRES_ACTIVE_AUTH: PASS
EXECUTE_ACQUIRES_LEASE: NO
CODEX_LOCAL_ONLY_V1: PASS
EXACT_CONTEXT_REFS_MARKER: PASS
EXACT_ALLOWED_PATHS_MARKER: PASS
RAW_GIT_BLOB_BYTES: PASS
CONTROL_SNAPSHOT_BOUND: PASS
M1_STATE_REUSED: PASS
M1_FRESHNESS_GATE: PASS
M4_REQUEST_REUSED: PASS
M4_PREPARED_REUSED: PASS
M10_CAPABILITY_GATE_REUSED: PASS
E3_CONTEXT_PACK_REUSED: PASS
E2_TRANSPORT_REUSED: PASS
AUTOMATIC_RETRY: NO
POST_EXEC_BRANCH_HEAD_UNCHANGED: PASS
DIRTY_SCOPE_GATE: PASS
INVOCATION_RECEIPT_PERSISTED_EXTERNAL: PASS
TRANSPORT_EXIT_ZERO_IS_NOT_TASK_SUCCESS: PASS
EXISTING_PUBLISHER_REUSED: PASS
FULL_REPO_GATE: PASS
AUTO_RESULT_COMMIT_PUSH: PASS
POST_PUBLISH_M4_RESULT_VALIDATION: PASS
AUTO_MERGE: NO
E1_E2_E3_CORE_CHANGED: NO
H_SERIES_REMAINS_DEFERRED: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E4: PASS
```

E4 PASS does not itself prove a real zero-copy/paste Codex run. E5 is reserved for that operational proof.
