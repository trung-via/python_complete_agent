# REVIEW-088 — Codex No-Op Outcome Observability Diagnostic Gate
PUBLISHER_PROFILE: CANONICAL_E4

STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

TASK_ID: TASK-088
REVIEW_ROUND: 2
REVIEWED_TASK_HEAD_SHA: e5514756374b49a5542b77aa8eb947bce4c36812
REVIEWED_BASE_MAIN_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
TASK_ARTIFACT_BLOB_SHA: 7b1be526612484effd27912132d7f77cf76fe725
RESULT_BLOB_SHA: 86d0f252987fc08c35fede79bc6ab4907c661efb
EXECUTOR_ID: antigravity
FIX_EXECUTION_MODE: IMPLEMENTATION
BLOCKERS_REMAINING: 1
CODE_AUDIT: PASS_WITH_STRICT_OBSERVABILITY_BLOCKER
CANONICAL_TESTS: PASS_REPORTED_WITH_RESULT_COUNT_INCONSISTENCY
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
PRIOR_REVIEWED_HEAD_SHA: 700606b452b44969d473ed854d2d1f50ccf0e3dc
REVIEWED_TASK_HEAD_SHA: e5514756374b49a5542b77aa8eb947bce4c36812
STATUS_VS_PRIOR_REVIEWED_HEAD: AHEAD
AHEAD_BY_PRIOR: 1
STATUS_VS_MAIN: AHEAD
AHEAD_BY_MAIN: 2
BEHIND_BY_MAIN: 0
MERGE_BASE_SHA: d55a5b168f6833558c3f9db63f46dd1817392283
FIX_SCOPE: EXACT
```

Round-2 delta is limited to the prior B1 repair plus canonical RESULT publication. No TASK-086/TASK-087/P2/P3/H5-H8 implementation was opened.

## Round-2 Accepted Repair

The reviewed head now correctly recognizes the canonical nested Codex event shapes:

```text
item.completed + item.type=agent_message + item.text
item.started/completed + item.type=command_execution
item.started/completed + item.type=file_change
```

and the new tests prove canonical agent-message marker extraction, reasoning exclusion, command/file observation, item-ID deduplication, and fully arbitrary JSON → UNKNOWN. These parts are accepted and must remain preserved.

Canonical certification captured in RESULT is green:

```text
2567 passed, 7 skipped, 1540 warnings in 432.23s
AIOS_MANAGED_T2_EXECUTION_COUNT: 1
AIOS_MANAGED_T2_DUPLICATION_DETECTED: NO
```

## Finding B2 — Strict observable-boundary semantics are still not fully fail-conservative

STATUS: BLOCKING
SEVERITY: DIAGNOSTIC_EVIDENCE_INTEGRITY

### B2.1 Outcome extraction still has generic non-canonical fallback paths

The current parser identifies an agent message when any of these are true:

```text
item_type in (agent_message, assistant_message, message)
OR role == assistant
OR top-level event type in (agent_message, assistant_message)
```

It may then read top-level `text`/`content`.

This is broader than the Round-1 repair contract, which required the outcome marker to be extracted only from a structurally identified agent-message item and explicitly prohibited scanning reasoning/error/command/file payloads for the marker.

For example, an error/tool/custom event carrying `role=assistant` and text containing `AIOS_EXECUTOR_OUTCOME: IMPLEMENTED` can still be misclassified as a terminal agent outcome even though the event is not a canonical Codex `agent_message` item.

Required semantics for Codex-local canonical extraction:

```text
canonical item event
+ item.type == agent_message
+ item.text is string
→ eligible final-agent candidate

reasoning / error / command_execution / file_change / unknown item
→ never eligible for outcome marker extraction
```

A legacy compatibility path may remain only if its event shape is itself explicitly and unambiguously identified as an agent-message event. Generic `role == assistant` must not turn arbitrary event payloads into terminal outcome evidence.

### B2.2 Incomplete/ambiguous bounded scans must not fabricate exact observation

The transport scans a bounded head/tail window. When stdout is truncated, the middle of the canonical event stream is not observed. Exact total command/file activity therefore cannot be proven from the sampled stream unless an independent exact summary exists.

Required fail-conservative behavior:

```text
stdout_scan_truncated == true
→ command_activity_count = UNKNOWN
→ file_change_activity_count = UNKNOWN
```

unless an exact canonical aggregate is structurally available (none is currently implemented).

Likewise, if a truncated scan contains no structurally identified agent message, `final_agent_message_observed` must be `UNKNOWN`, not `NO`, because the omitted region was not inspected.

For an untruncated canonical stream, exact zero is allowed when the complete recognized stream contains no command/file items. Unknown/unsupported item/event structure must not silently strengthen evidence to exact zero.

Add bounded regressions proving at minimum:

```text
ERROR_EVENT_WITH_ASSISTANT_ROLE_MARKER_IGNORED: PASS
COMMAND_EVENT_WITH_FAKE_OUTCOME_MARKER_IGNORED: PASS
UNKNOWN_ITEM_WITH_FAKE_OUTCOME_MARKER_IGNORED: PASS
TRUNCATED_ACTIVITY_COUNTS_UNKNOWN: PASS
TRUNCATED_NO_AGENT_MESSAGE_OBSERVATION_UNKNOWN: PASS
UNTRUNCATED_CANONICAL_ZERO_ACTIVITY_EXACT_ZERO: PASS
```

### B2.3 RESULT still contradicts itself on full-suite count

The same RESULT contains:

```text
canonical captured output: 2567 passed, 7 skipped
Risks / Notes:            2516 passed, 7 skipped
RESULT_TEST_COUNT_SELF_CONSISTENT: PASS
```

This does not satisfy the Round-1 acceptance requirement. The next publication must not claim a stale pre-certification full-suite count.

Preferred bounded repair:

```text
canonical captured T2 output remains authoritative
pre-certification notes do not guess a full-suite count
RESULT_TEST_COUNT_SELF_CONSISTENT may be PASS only when all stated counts agree
```

No new RESULT schema or publisher redesign is required for TASK-088.

## Acceptance for B2

```text
CANONICAL_AGENT_MESSAGE_ONLY_OUTCOME_EXTRACTION: PASS
NON_AGENT_MARKERS_IGNORED: PASS
REASONING_CONTENT_IGNORED: PASS
RAW_STDOUT_NOT_PERSISTED: PASS
TRUNCATED_COUNTS_FAIL_CONSERVATIVE: PASS
TRUNCATED_MESSAGE_OBSERVATION_FAIL_CONSERVATIVE: PASS
ACTIVITY_DEDUP_SEMANTICS_PRESERVED: PASS
CLEAN_NOOP_SURFACES_SAFE_OUTCOME: PASS
CLEAN_NOOP_REMAINS_BLOCKING: PASS
RESULT_TEST_COUNT_SELF_CONSISTENT: PASS
CANONICAL_T2: PASS
```

## Accepted / Do Not Reopen Without Regression

```text
OUTCOME_VOCABULARY_CLOSED: PASS
TERMINAL_MARKER_ADDED_TO_CONTEXT: PASS
CANONICAL_NESTED_AGENT_MESSAGE_SUPPORTED: PASS
CANONICAL_COMMAND_FILE_ITEM_SUPPORTED: PASS
ITEM_ID_ACTIVITY_DEDUP: PASS
ARBITRARY_JSON_UNKNOWN: PASS
DIAGNOSTIC_SERIALIZATION_BOUNDED: PASS
DIAGNOSTIC_FINGERPRINT_INCLUDES_NEW_FIELDS: PASS
CLEAN_NOOP_FAIL_CLOSED: PASS
P0_VALIDATION_OWNERSHIP_PRESERVED: PASS
AUTO_RETRY: NO
AUTO_REROUTE: NO
TASK_086_PAUSED: PASS
TASK_087_NOT_IMPLEMENTED: PASS
P2_P3_NOT_OPENED: PASS
H5_H8_NOT_OPENED: PASS
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
