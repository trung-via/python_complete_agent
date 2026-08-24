# TASK-088 — Codex No-Op Outcome Observability Diagnostic Gate

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1 DIAGNOSTIC GATE
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: antigravity
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
DIAGNOSTIC_GATE_ADR: ADR-063

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.1","roadmap_blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c","roadmap_fingerprint":"4bcbb10e1e8e02169ccb5a516801abd1ce01b0b5edd348d90abcac7d0887404f","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R1"],"scope_in":["bounded diagnostic prerequisite for P1 worker-flow implementation","safe explicit bounded Codex executor outcome observability","safe command/file-change activity counts when structurally observable","clean-noop report surfaces bounded executor outcome without changing fail-closed publication semantics","provider-neutral outcome vocabulary with Codex-local extraction only in this slice"],"scope_out":["TASK-086 worker-flow implementation","TASK-087 timeout and failure classification","P1 capability batching or integration lane","persistent sessions checkpoint resume shell interception capacity suspension","Claude transport adaptive routing","automatic retry automatic reroute","raw stdout persistence","chain-of-thought or reasoning-content capture","H5-H8 implementation"]}

## Baseline

```text
MAIN_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
TARGET_BRANCH: ai/task-088
P0_FORMAL_COMPLETION: YES
TASK_085_STATUS: SUPERSEDED_NO_IMPLEMENTATION
TASK_086_STATUS: PAUSED_DIAGNOSTIC_REQUIRED
TASK_085_CODEX_OUTCOME: EXITED_ZERO_CLEAN_NO_WORKTREE_DELTA
TASK_086_CODEX_OUTCOME: EXITED_ZERO_CLEAN_NO_WORKTREE_DELTA
TASK_087_STATUS: RESERVED_NOT_AUTHORED
P2_P3_STATUS: NOT_AUTHORIZED
H5_STATUS: PAUSED_NOT_AUTHORIZED
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"b7256b572469ac89db8808c88b8cd880e67cd7b6"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"52f4f24a6b0af719886c6524ade8e19f8cc8984c"},{"path":".ai/decisions/ADR-061-AIOS-P1.0-TRANSACTIONAL-WORKER-FLOW-FIX-RECOVERY-CONTRACT.md","blob_sha":"b456d80befff7aeec0d3a0217e03a9834f71d7f8"},{"path":".ai/decisions/ADR-062-AIOS-P1.0-BOUNDED-SLICE-DECOMPOSITION-AFTER-CLEAN-NOOP.md","blob_sha":"bcdb4f148d731292c776802d858448e99469abe1"},{"path":".ai/decisions/ADR-063-AIOS-CODEX-NOOP-OUTCOME-OBSERVABILITY-GATE.md","blob_sha":"471067d090d76488ebb760266082aba745eb5a06"},{"path":".ai/reviews/REVIEW-083.md","blob_sha":"767af7217ad6679f02bec83ec380c80098b4374f"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/executor_outcome.py","src/aios_bridge/executor_context.py","src/aios_bridge/executor_transports/codex_local.py","src/aios_bridge/executor_transports/__init__.py","tests/aios_bridge/test_codex_local_transport.py","tests/aios_bridge/test_executor_context_pack.py","tests/test_bridge_executor_automation.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Make the bounded Codex clean-noop outcome observable before TASK-086 is attempted again.

This task does NOT fix P1.0 worker flow itself. It only closes the diagnostic gap that currently reduces two materially different cases to the same opaque terminal state:

```text
Codex intentionally reports NO_WORK_REQUIRED
Codex reports BLOCKED/INSTRUCTION_CONFLICT
Codex executes commands but never edits
Codex does essentially nothing
        ↓
current Bridge sees only:
EXITED_ZERO + CLEAN_NO_WORKTREE_DELTA
```

After TASK-088, Bridge must retain a safe bounded terminal outcome when structurally available, while preserving `UNKNOWN` when it is not.

## 1. Provider-Neutral Bounded Outcome Type

Create a small closed immutable outcome model equivalent to:

```text
ExecutorOutcomeCode:
  IMPLEMENTED
  BLOCKED
  NO_WORK_REQUIRED
  INSTRUCTION_CONFLICT
  UNKNOWN
```

The model may live in `src/aios_bridge/executor_outcome.py` or an equally bounded authorized location.

Rules:

```text
unknown value → fail closed at parser boundary or normalize only through an explicit UNKNOWN path
no free-form outcome identity
no authority creation
no PASS/merge semantics
```

## 2. Executor Context Terminal Marker

Extend the thin executor instruction contract to require the worker's final explicit response to include exactly one terminal marker equivalent to:

```text
AIOS_EXECUTOR_OUTCOME: IMPLEMENTED
AIOS_EXECUTOR_OUTCOME: BLOCKED
AIOS_EXECUTOR_OUTCOME: NO_WORK_REQUIRED
AIOS_EXECUTOR_OUTCOME: INSTRUCTION_CONFLICT
AIOS_EXECUTOR_OUTCOME: UNKNOWN
```

The worker must choose:

```text
IMPLEMENTED           → implementation delta was intentionally produced
BLOCKED               → task cannot be completed inside current authorized constraints
NO_WORK_REQUIRED      → worker explicitly believes requested work is already satisfied
INSTRUCTION_CONFLICT  → worker detects contradictory/unexecutable instructions
UNKNOWN               → none of the above can be stated safely
```

This marker is diagnostic only. `IMPLEMENTED` does not bypass Git-delta validation and `NO_WORK_REQUIRED` does not make a clean no-op publishable.

## 3. Safe Codex JSON Event Extraction

Extend Codex diagnostic parsing conservatively.

Allowed observations:

```text
closed AIOS_EXECUTOR_OUTCOME marker from an explicitly identifiable final/agent-message event
presence/absence of an explicitly identifiable final agent message
command activity count when event structure identifies command activity
file-change activity count when event structure identifies file-change activity
existing bounded top-level event-type set
```

Hard safety rules:

```text
DO_NOT_PERSIST_CHAIN_OF_THOUGHT: YES
DO_NOT_PERSIST_REASONING_EVENT_CONTENT: YES
DO_NOT_PERSIST_RAW_STDOUT: YES
DO_NOT_PERSIST_ARBITRARY_EVENT_TEXT: YES
DO_NOT_EXPAND_ENVIRONMENT_ALLOWLIST: YES
MAX_FINAL_MESSAGE_SCAN_BYTES: bounded constant required
AMBIGUOUS_EVENT_SHAPE: UNKNOWN
UNOBSERVABLE_COUNT: UNKNOWN, not 0
```

The implementation may inspect a bounded candidate final-agent message in memory solely to extract the exact terminal marker; it must not persist the rest of that message unless a separate short bounded user-visible field is demonstrably safe. Preferred minimal implementation persists the marker and presence/count metadata only.

## 4. Diagnostic Evidence Schema

`CodexTransportDiagnostic` or an associated bounded diagnostic object must expose equivalent fields:

```text
executor_outcome: IMPLEMENTED | BLOCKED | NO_WORK_REQUIRED | INSTRUCTION_CONFLICT | UNKNOWN
final_agent_message_observed: YES | NO | UNKNOWN
command_activity_count: integer | UNKNOWN
file_change_activity_count: integer | UNKNOWN
```

Existing fields remain bounded and compatible.

Serialization/fingerprint must include the new evidence deterministically.

## 5. Clean-Noop Reporting

When `cmd_execute` reaches the existing `EXITED_ZERO + CLEAN_NO_WORKTREE_DELTA` gate, preserve the current fail-closed behavior but include safe outcome evidence in its terminal diagnostic.

Examples:

```text
E4 execution blocked: CLEAN_NO_WORKTREE_DELTA; executor_outcome=NO_WORK_REQUIRED; final_agent_message_observed=YES; no publication, no retry, no reroute
```

or:

```text
E4 execution blocked: CLEAN_NO_WORKTREE_DELTA; executor_outcome=UNKNOWN; final_agent_message_observed=NO; no publication, no retry, no reroute
```

Do not reinterpret any clean no-op as success in TASK-088.

## 6. Synthetic Regression Coverage

Add bounded synthetic JSON-event fixtures covering at least:

```text
final agent message with IMPLEMENTED marker
final agent message with BLOCKED marker
final agent message with NO_WORK_REQUIRED marker
final agent message with INSTRUCTION_CONFLICT marker
no terminal marker → UNKNOWN
reasoning-like event content containing fake marker → MUST NOT COUNT
arbitrary non-final message containing fake marker → MUST NOT COUNT
command activity observable → exact bounded count
file-change activity observable → exact bounded count
activity unavailable → UNKNOWN rather than fabricated 0
oversized/malformed event content → bounded/UNKNOWN
```

Tests must not depend on a live Codex call.

## 7. Antigravity Execution Choice

This task is intentionally dispatched only to Antigravity in the machine-readable dispatch policy because bounded Codex execution is the component under diagnosis.

Antigravity implementation still obeys the same task authority, allowed paths, P0 validation plan, and canonical publication rules.

## 8. Explicit Out of Scope

```text
implementing TASK-086 worker_flow.py
EVIDENCE_REFRESH worker-flow behavior
timeout classification
changing Codex timeout
persistent session
checkpoint/resume
shell interception
capacity suspension
P1 capability batching
integration lane
Claude transport
adaptive routing
automatic retry
automatic reroute
H5-H8
```

## Required Targeted / Impact Tests

Executor runs targeted/impact tests plus diff check only. Certification boundary owns T2 exactly once.

Required proofs:

```text
OUTCOME_VOCABULARY_CLOSED: PASS
TERMINAL_MARKER_REQUIRED_BY_CONTEXT: PASS
FINAL_AGENT_ONLY_MARKER_EXTRACTION: PASS
REASONING_CONTENT_IGNORED: PASS
NONFINAL_MARKER_IGNORED: PASS
RAW_STDOUT_NOT_PERSISTED: PASS
OUTCOME_UNKNOWN_FAIL_CONSERVATIVE: PASS
COMMAND_ACTIVITY_BOUNDED: PASS
FILE_CHANGE_ACTIVITY_BOUNDED: PASS
UNOBSERVABLE_ACTIVITY_STAYS_UNKNOWN: PASS
DIAGNOSTIC_FINGERPRINT_STABLE: PASS
CLEAN_NOOP_SURFACES_OUTCOME: PASS
CLEAN_NOOP_REMAINS_BLOCKING: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_086_NOT_IMPLEMENTED: PASS
TASK_087_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_NOT_OPENED: PASS
```

## Certification

```text
VALIDATION_PROFILE: CONTROL_PLANE_STRICT_COMPAT
T2_OWNER: CERTIFICATION_BOUNDARY
FULL_REPOSITORY: .\venv\Scripts\python.exe -m pytest tests/ -q
AIOS_MANAGED_T2_EXPECTED: 1
```

## Acceptance

TASK-088 passes only if:

```text
CODEX_NOOP_OUTCOME_OBSERVABLE: PASS
NO_REASONING_CONTENT_PERSISTED: PASS
CLEAN_NOOP_STILL_FAILS_CLOSED: PASS
SAFE_DIAGNOSTIC_EVIDENCE_PERSISTED: PASS
P0_VALIDATION_SEMANTICS_PRESERVED: PASS
CONTROL_PLANE_AUTHORITY_UNCHANGED: PASS
TASK_086_REMAINS_PAUSED: PASS
TASK_087_REMAINS_RESERVED: PASS
P2_P3_NOT_AUTHORIZED: PASS
H5_NOT_OPENED: PASS
```