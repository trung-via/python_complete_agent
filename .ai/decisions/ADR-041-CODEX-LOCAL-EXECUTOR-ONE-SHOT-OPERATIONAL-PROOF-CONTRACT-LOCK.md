# ADR-041 — Codex Local Executor One-Shot Operational Proof Contract Lock

STATUS: LOCKED
CLASS: POST-H0 / POST-TASK-067 OPERATIONAL PROOF — CODEX LOCAL EXECUTOR
DATE: 2026-08-23
BASELINE_MAIN_SHA: 08d82392c807d334636a902fe3bcfa5bd70e7b26
APPLIES_AFTER: TASK-067 PASS + HUMAN MERGE
RELATED: ADR-029 / ADR-030 / ADR-031 / ADR-032 / ADR-034 / ADR-037 / ADR-040

## Context

TASK-067 hardened the local Codex transport diagnostics and was Human-merged to `main` at:

```text
08d82392c807d334636a902fe3bcfa5bd70e7b26
```

The merged path now has bounded diagnostic observability, safe temporary capture, stable diagnostic codes, exact Codex JSON event compatibility, unchanged E1 receipt semantics, unchanged safe argv, and unchanged E4 no-delta/scope gates.

What remains unproven is operational execution reliability: a real local subscription Codex process must receive the bounded AIOS execution payload, create an authorized worktree delta, survive E4 scope validation, and reach RESULT publication without retry or reroute.

This ADR locks that proof. It does not add a new AIOS Bridge milestone, does not create M12, and does not begin H1.

---

## Decision 1 — Proof Is One Real Local Subscription Codex Invocation

TASK-068 SHALL use the normal Codex worker surface and merged E1/E2/E3/E4 path.

The proof permits exactly one real local Codex process invocation after an explicit Human RUN action.

Locked runtime:

```text
executor_id: codex
transport_id: codex-local-v1
capacity_class: SUBSCRIPTION
max_real_codex_invocations_for_attempt: 1
auto_retry: NO
auto_reroute: NO
fallback_executor: NONE
paid_api_fallback: NONE
```

The Codex invocation is subscription-backed local executor usage. It is not a paid external API grant and MUST NOT read or use provider API keys.

Creating ADR-041 or TASK-068 does not itself launch Codex. The real invocation requires a separate explicit Human operator action through the Codex worker surface.

---

## Decision 2 — Existing Safe Codex Transport Contract Is Immutable During Proof

TASK-068 MUST NOT modify or weaken:

```text
bridge.py
src/aios_bridge/**
.agents/skills/aios-worker/**
.agents/workflows/aios-worker.md
requirements.txt
```

The merged safe invocation contract remains:

```text
--ask-for-approval never
exec
--ephemeral
--json
--color never
--sandbox workspace-write
sandbox_workspace_write.network_access=false
web_search="disabled"
exact bounded stdin payload
one process per invocation
subscription-first local sign-in
no API-key fallback
```

Any compatibility/auth/config/sandbox defect discovered by the real proof is evidence for a later bounded FIX task. It is not authority to weaken the transport during TASK-068.

---

## Decision 3 — Proof Work Is a Single Non-Production Artifact

The real Codex executor may create exactly one task-owned proof artifact:

```text
proofs/TASK-068-CODEX-LOCAL-EXECUTOR-PROOF.md
```

No other executor-created worktree path is authorized.

The proof artifact must contain exactly the canonical content locked in TASK-068. It is deliberately simple so the proof measures transport/context/write/E4 reliability rather than coding complexity.

Bridge-generated publication output is separately allowed:

```text
.ai/results/RESULT-068.md
```

No source code, tests, config, task, ADR, review, worker surface, dependency, or runtime-control file may be modified by the executor.

---

## Decision 4 — Proof Must Establish Exact E4 Path Success

A successful attempt requires all of the following in one authorized execution:

```text
Human RUN authorization: present
selected executor: codex
real Codex process spawn count: 1
InvocationReceipt.status: EXITED_ZERO
InvocationReceipt.exit_code: 0
auto retry count: 0
reroute count: 0
paid API count: 0
post-executor dirty path count: 1
post-executor dirty path: proofs/TASK-068-CODEX-LOCAL-EXECUTOR-PROOF.md
out-of-scope dirty paths: 0
executor HEAD advance: 0 before publication
E4 scope validation: PASS
full repository tests: PASS
RESULT-068 publication: PASS
```

Transport exit zero alone is not success. A real authorized worktree delta is mandatory.

---

## Decision 5 — Diagnostics Are Evidence, Not Authority

TASK-067 diagnostics remain supplementary evidence.

The runtime receipt should expose bounded safe diagnostic metadata such as:

```text
transport_diagnostic.code
transport_diagnostic.stdout_event_types
transport_diagnostic.last_stdout_event_type
transport_diagnostic_fingerprint
```

Raw stdout/stderr/model prose must remain non-persistent.

A successful proof does not require a particular non-failure diagnostic code name, because Codex event streams may evolve. It does require that the canonical process receipt is EXITED_ZERO and that no mechanically failure-shaped condition overrides the E4 success path.

No diagnostic may bypass Git/scope/test/publication gates.

---

## Decision 6 — Failure Is Fail-Closed and Ends the Attempt

Any of the following ends the attempt without publication success and without automatic second executor/model execution:

```text
FAILED_TO_START
EXITED_NONZERO
TIMED_OUT
INTERRUPTED
EXITED_ZERO + no worktree delta
out-of-scope delta
executor HEAD advance before publication
full test failure
publication integrity failure
lease/runtime continuity failure
```

On failure:

```text
AUTO_RETRY: NO
AUTO_REROUTE: NO
ANTIGRAVITY_FALLBACK: NO
SECOND_CODEX_CALL: NO
PAID_API_FALLBACK: NO
```

Preserve diagnostic/runtime evidence and stop for ChatGPT review/a bounded recovery decision.

---

## Decision 7 — Proof Artifact Canonical Content

TASK-068 shall lock a byte-stable UTF-8/LF proof artifact equivalent to:

```text
# TASK-068 Codex Local Executor Operational Proof

TASK_ID: TASK-068
EXECUTOR_ID: codex
TRANSPORT_ID: codex-local-v1
PROOF_KIND: REAL_LOCAL_EXECUTOR_AUTHORIZED_WRITE
BASELINE_MAIN_SHA: 08d82392c807d334636a902fe3bcfa5bd70e7b26
NETWORK_REQUIRED: NO
WEB_SEARCH_REQUIRED: NO
PAID_API_REQUIRED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
EXPECTED_DIRTY_PATH_COUNT: 1
EXPECTED_DIRTY_PATH: proofs/TASK-068-CODEX-LOCAL-EXECUTOR-PROOF.md

RESULT: CODEX_CREATED_THIS_AUTHORIZED_DELTA
```

One trailing LF is required. No timestamps, generated prose, machine-specific paths, tokens, credentials, model reasoning, or arbitrary metadata may be added.

---

## Decision 8 — E4 Full-Suite Publication Is Part of the Proof

The executor does not need to modify or add tests. E4's existing publication path shall run the canonical full repository test command before successful publication.

The proof is invalid if a RESULT is fabricated manually or if the task branch is manually committed/pushed outside the authorized E4 publication path.

Expected publication path:

```text
Human $aios-worker RUN TASK-068
  -> shared Codex adapter / Bridge handoff
  -> E4 bounded Codex process
  -> one exact proof-file delta
  -> E4 Git/scope gate
  -> full repository tests
  -> E4 publish RESULT-068
```

---

## Decision 9 — Review and Merge Are Still Required

A successful E4 publication is evidence, not final project authority.

After RESULT-068 publication:

```text
ChatGPT exact-SHA review
  -> PASS or CHANGES_REQUIRED
```

Only after REVIEW-068 PASS and explicit Human merge of the exact reviewed task head may the control record state:

```text
CODEX_LOCAL_PATH_OPERATIONALLY_PROVEN: YES
DUAL_EXECUTOR_OPERATIONAL_BASELINE: PROVEN
H1_AUTHORIZED: YES
```

TASK-068 runtime success alone does not authorize H1.

---

## Decision 10 — H-Series Boundary Remains Closed During Proof

TASK-068 MUST NOT modify:

```text
src/aios_engineering/**
```

H0 remains complete and unchanged. H1 remains blocked until TASK-068 receives PASS and is Human-merged.

---

## Acceptance

The proof may be declared complete only when:

```text
REAL_CODEX_INVOCATION_COUNT: 1
EXECUTOR_ID: codex
TRANSPORT_ID: codex-local-v1
CANONICAL_RECEIPT_STATUS: EXITED_ZERO
EXIT_CODE: 0
AUTHORIZED_DIRTY_PATH_COUNT: 1
AUTHORIZED_DIRTY_PATH_EXACT: YES
OUT_OF_SCOPE_DIRTY_PATH_COUNT: 0
E4_SCOPE_GATE: PASS
FULL_REPOSITORY_TESTS: PASS
RESULT_PUBLICATION: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
SECOND_EXECUTOR_USED: NO
PAID_API_USED: NO
RAW_STDOUT_PERSISTED: NO
RAW_STDERR_PERSISTED: NO
H0_CHANGED: NO
H1_STARTED: NO
```

Final operational status requires subsequent Review PASS + Human merge.
