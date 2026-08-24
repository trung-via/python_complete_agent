# REVIEW-088 — Codex No-Op Outcome Observability Diagnostic Gate
PUBLISHER_PROFILE: CANONICAL_E4

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-088
REVIEW_ROUND: 1
REVIEWED_TASK_HEAD_SHA: 700606b452b44969d473ed854d2d1f50ccf0e3dc
REVIEWED_BASE_MAIN_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
TASK_ARTIFACT_BLOB_SHA: 7b1be526612484effd27912132d7f77cf76fe725
RESULT_BLOB_SHA: a7a0f24a05e867c85136ac604fecf2a559b1eacd
EXECUTOR_ID: antigravity
FIX_EXECUTION_MODE: IMPLEMENTATION
BLOCKERS_REMAINING: 1
CODE_AUDIT: PASS_WITH_CANONICAL_EVENT_SCHEMA_BLOCKER
CANONICAL_TESTS: PASS_REPORTED_WITH_RESULT_NOTE_INCONSISTENCY
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.1
ROADMAP_BLOB_SHA: cae51de4db517dd452c260076a1daa521c1e3a4c
ROADMAP_FINGERPRINT: 4bcbb10e1e8e02169ccb5a516801abd1ce01b0b5edd348d90abcac7d0887404f
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
DIAGNOSTIC_GATE_ADR: ADR-063
TASK_086_REMAINS_PAUSED: YES
TASK_087_REMAINS_RESERVED: YES
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO

## Reviewed Snapshot

```text
BRANCH: ai/task-088
BASE_MAIN_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
REVIEWED_TASK_HEAD_SHA: 700606b452b44969d473ed854d2d1f50ccf0e3dc
STATUS_VS_MAIN: AHEAD
AHEAD_BY: 1
BEHIND_BY: 0
MERGE_BASE_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
SCOPE: EXACT
```

Reviewed implementation paths are authorized by TASK-088. No TASK-086 worker-flow implementation, TASK-087 failure-classification work, P2/P3, or H5-H8 capability was opened.

Canonical RESULT reports one AIOS-managed T2 and a passing captured full-suite run. The captured pytest output ends with:

```text
2561 passed, 7 skipped, 1540 warnings in 476.83s
```

The later human-authored Risks/Notes subsection still says `2510 passed`; this is inconsistent with the captured canonical test output and must be corrected on the next publication. The detailed captured command/exit-code evidence is treated as authoritative for this review round.

## Accepted / Do Not Reopen Without Regression

```text
OUTCOME_VOCABULARY_CLOSED: PASS
TERMINAL_MARKER_ADDED_TO_CONTEXT: PASS
NO_RAW_STDOUT_PERSISTENCE: PASS
NO_REASONING_CONTENT_PERSISTENCE: PASS
DIAGNOSTIC_SERIALIZATION_BOUNDED: PASS
DIAGNOSTIC_FINGERPRINT_INCLUDES_NEW_FIELDS: PASS
CLEAN_NOOP_REMAINS_FAIL_CLOSED: PASS
CLEAN_NOOP_REPORT_SURFACES_OUTCOME_FIELDS: PASS
P0_VALIDATION_OWNERSHIP_PRESERVED: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_086_PAUSED: PASS
TASK_087_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
```

## Finding B1 — Parser does not recognize canonical Codex JSON event shape and can fabricate zero activity

STATUS: BLOCKING
SEVERITY: DIAGNOSTIC_CORRECTNESS

TASK-088 exists specifically so the next bounded Codex run can explain an opaque clean no-op. The reviewed parser does not yet satisfy that goal for the canonical Codex event stream.

### B1.1 Canonical final agent message is currently missed

Current Codex JSON/SDK event semantics represent the assistant response as an item event equivalent to:

```json
{"type":"item.completed","item":{"id":"item_1","type":"agent_message","text":"..."}}
```

Command and file-change activity are item types equivalent to:

```json
{"type":"item.completed","item":{"id":"item_2","type":"command_execution", ...}}
{"type":"item.completed","item":{"id":"item_3","type":"file_change", ...}}
```

The reviewed code derives `item_type`, but `is_agent_msg` accepts `item_type == "message"` and does not accept the canonical `item_type == "agent_message"`; `_extract_text_from_content()` also does not read the canonical `item.text` path in that branch. Therefore a real successful Codex final response carrying `AIOS_EXECUTOR_OUTCOME: ...` can still produce:

```text
FINAL_AGENT_MESSAGE_OBSERVED: NO
EXECUTOR_OUTCOME: UNKNOWN
```

The synthetic TASK-088 tests use invented top-level shapes such as `{"type":"message","role":"assistant","content":"..."}` rather than the canonical `item.completed / item.type=agent_message / item.text` shape, so they do not catch this defect.

### B1.2 Activity counts are not fail-conservative for ambiguous JSON streams

`has_observable_activity_stream` becomes true for any parsed JSON object. As a result, an arbitrary or structurally unrecognized JSON stream can produce:

```text
command_activity_count = 0
file_change_activity_count = 0
```

instead of `UNKNOWN`.

TASK-088 explicitly requires:

```text
AMBIGUOUS_EVENT_SHAPE: UNKNOWN
UNOBSERVABLE_COUNT: UNKNOWN, not 0
```

Also, canonical Codex command/file activity may emit lifecycle events for the same item. Counts must use a defined canonical rule (preferred: unique observable item IDs for recognized `command_execution` / `file_change` items) so one activity is not accidentally double-counted merely because both started/completed events are present.

## Required Repair — bounded only

1. Preserve the accepted outcome vocabulary, context terminal-marker contract, no-raw-output rule, and clean-noop fail-closed semantics.
2. Parse canonical Codex JSON item events conservatively:

```text
item.completed + item.type=agent_message + item.text
item.started/completed + item.type=command_execution
item.started/completed + item.type=file_change
reasoning item content ignored for outcome extraction
```

3. Final outcome marker may be extracted only from a structurally identified agent-message item. Do not scan reasoning/error/command/file payload content for the marker.
4. Add synthetic regressions using the canonical nested Codex event shapes above. Existing invented top-level-message tests may remain as compatibility tests but cannot be the primary proof.
5. Define bounded activity counting over recognized canonical item events. Prefer unique item IDs when available. Ambiguous/unrecognized JSON event structures must leave activity count `UNKNOWN`, not exact zero.
6. Add regressions proving:

```text
CANONICAL_AGENT_MESSAGE_MARKER_EXTRACTED: PASS
CANONICAL_REASONING_MARKER_IGNORED: PASS
CANONICAL_COMMAND_ACTIVITY_OBSERVED: PASS
CANONICAL_FILE_CHANGE_ACTIVITY_OBSERVED: PASS
STARTED_COMPLETED_SAME_ITEM_NOT_DOUBLE_COUNTED: PASS
ARBITRARY_JSON_ACTIVITY_COUNTS_UNKNOWN: PASS
```

7. Correct the RESULT full-suite summary inconsistency on publication; the new RESULT must report one internally consistent canonical count.
8. Keep TASK-086 paused. Do not implement worker_flow/EVIDENCE_REFRESH, TASK-087, P2/P3, H5-H8, retry/reroute, session persistence, shell interception, or timeout changes.

## Acceptance for B1

```text
CANONICAL_CODEX_EVENT_SCHEMA_SUPPORTED: PASS
FINAL_AGENT_ONLY_MARKER_EXTRACTION: PASS
REASONING_CONTENT_IGNORED: PASS
RAW_STDOUT_NOT_PERSISTED: PASS
ACTIVITY_COUNTS_FAIL_CONSERVATIVE: PASS
ACTIVITY_DEDUP_SEMANTICS_DEFINED: PASS
CLEAN_NOOP_SURFACES_CANONICAL_OUTCOME: PASS
CLEAN_NOOP_REMAINS_BLOCKING: PASS
RESULT_TEST_COUNT_SELF_CONSISTENT: PASS
CANONICAL_T2: PASS
```

## Decision

```text
TASK-088: CHANGES_REQUIRED
APPROVED: NO
MERGE_AUTHORIZED: NO
BLOCKERS_REMAINING: 1
NEXT_ACTION: FIX TASK-088
TASK_086_REMAINS_PAUSED: YES
TASK_087_REMAINS_RESERVED: YES
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
```

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-088.md","blob_sha":"7b1be526612484effd27912132d7f77cf76fe725"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md","blob_sha":"cae51de4db517dd452c260076a1daa521c1e3a4c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.completions.json","blob_sha":"b7256b572469ac89db8808c88b8cd880e67cd7b6"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"52f4f24a6b0af719886c6524ade8e19f8cc8984c"},{"path":".ai/decisions/ADR-063-AIOS-CODEX-NOOP-OUTCOME-OBSERVABILITY-GATE.md","blob_sha":"471067d090d76488ebb760266082aba745eb5a06"},{"path":".ai/decisions/ADR-062-AIOS-P1.0-BOUNDED-SLICE-DECOMPOSITION-AFTER-CLEAN-NOOP.md","blob_sha":"bcdb4f148d731292c776802d858448e99469abe1"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/executor_outcome.py","src/aios_bridge/executor_context.py","src/aios_bridge/executor_transports/codex_local.py","src/aios_bridge/executor_transports/__init__.py","tests/aios_bridge/test_codex_local_transport.py","tests/aios_bridge/test_executor_context_pack.py","tests/test_bridge_executor_automation.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}
