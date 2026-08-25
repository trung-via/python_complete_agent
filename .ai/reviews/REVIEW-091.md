# REVIEW-091 — FIX Proof Carry-Forward + Invalidation + Delta/Impact Review Integration
PUBLISHER_PROFILE: CANONICAL_E4
STATUS: CHANGES_REQUIRED
APPROVED: NO
AUTO_MERGE_ELIGIBLE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO
TASK_ID: TASK-091
REVIEW_ROUND: 2
REVIEWED_TASK_HEAD_SHA: 74727d4cc97fd8ea53e10f5bc5ac4e9ca81a8c71
REVIEWED_BASE_MAIN_SHA: 5a609040030a140c0b10be58f4c351dc17cbfb23
TASK_ARTIFACT_BLOB_SHA: 86cd8ded4a3d8cdf6b571098242a8f0f28aba38b
RESULT_BLOB_SHA: 36f33fb657d9f288277954b1146173b9e4b31704
EXECUTOR_ID: codex
BLOCKERS_REMAINING: 1
CODE_AUDIT: CHANGES_REQUIRED
CANONICAL_TESTS: DEFERRED_PENDING_SEMANTIC_ACCEPTANCE
ROADMAP_AUDIT: PASS
ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
ROADMAP_VERSION: 1.2
ROADMAP_BLOB_SHA: 41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c
ROADMAP_FINGERPRINT: 89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
REQUIREMENT_BINDINGS_FINGERPRINT: 11ed8d59df71c670f5264eff4f7fb6756828a0c83090b36d3998b21b1047c694
FIX_EXECUTION_MODE: IMPLEMENTATION
TASK_087_PREREQUISITE_ELIGIBLE: NO
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-091.md","blob_sha":"86cd8ded4a3d8cdf6b571098242a8f0f28aba38b"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/fix_review.py","tests/aios_bridge/test_fix_review.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: 74727d4cc97fd8ea53e10f5bc5ac4e9ca81a8c71
PREVIOUS_REVIEWED_HEAD: b1aa4bd9e7532fed0dca8abe384c63a1e781f5a7
BASE_MAIN: 5a609040030a140c0b10be58f4c351dc17cbfb23
MERGE_BASE: 5a609040030a140c0b10be58f4c351dc17cbfb23
AHEAD: 2
BEHIND: 0
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
```

This is a corrected Round-2 review. The candidate did not change. The previous B3 finding is withdrawn after tracing the real handoff call path: `cmd_handoff()` already invokes `cmd_context(args)` automatically on successful handoff, so the validated `interactive_fix_context` added by the candidate is emitted on the worker-visible Antigravity handoff stdout path without requiring the Antigravity workflow to invoke `bridge.py context` separately.

## Closed Findings

```text
B1 CLOSED — bound proof test/evidence path changes invalidate proof and select its T1.
B2 CLOSED — targeted T1 cannot mutate the candidate without fail-closed rejection; final impact is recomputed.
B3 CLOSED — successful Antigravity handoff automatically reaches cmd_context output; derived FIX Context Pack is therefore delivered on the existing handoff stdout surface.
```

B3 closure does not weaken the workflow rule forbidding a separate manual `bridge.py context` invocation. The delivery is internal to the existing handoff call path.

## Sole Blocking Finding

### B4 — fenced-marker parser accepts a non-closing fence line as a closing delimiter

`src/aios_bridge/fix_review.py::_top_level_values()` correctly remembers the opening delimiter character and run length, but while already inside a fence it still closes whenever the line begins with the same delimiter and run length >= the opening length. It does not require the remainder of the candidate closing line to be whitespace-only.

Exact required repair:

```text
WHEN fence is open:
  run = leading backtick/tilde run
  remainder = text after that run

  close ONLY IF:
    run delimiter == opening delimiter
    AND len(run) >= opening length
    AND remainder.strip() == ""

  otherwise remain inside the fence
```

Do not redesign the parser and do not touch Bridge/worker flow for this FIX.

Required regression in `tests/aios_bridge/test_fix_review.py`:

```text
outer fence: four backticks
inside line: four backticks followed by non-whitespace text
then FIX_REVIEW_MODE and FIX_CONTEXT_PACK_JSON markers
then real four-backtick closing fence

EXPECTED:
parse_fix_review_mode(...) == COMPATIBILITY
parse_fix_context_pack(...) == None
```

Also preserve the existing tests for simple triple-backtick, tilde, and shorter-inner-fence cases.

## Protected Accepted Surfaces

Do not reopen or modify B1-B3 or previously accepted A1-A10. This FIX is parser-only.

## Validation Contract

Run only:

```text
venv\Scripts\python.exe -m pytest tests/aios_bridge/test_fix_review.py -q
```

Do not run `pytest tests/ -q`. Candidate-stage T2 must remain 0. Final canonical T2 remains owned only by `certify-reviewed` after semantic acceptance.

## Operational Note

The prior Codex clean no-op left runtime authorization at `EXECUTION_BLOCKED`. Switching to Antigravity is therefore correctly rejected by the existing stable-failover contract, which requires a prior `CONSUMED` published boundary. This corrected FIX intentionally uses the same executor (`codex`) and is a new explicit Human invocation, not automatic retry/reroute.

Do not manually mutate authorization status to `CONSUMED`; the blocked lease did not publish the prior candidate and must not be represented as if it did.

## Decision

```text
TASK-091: CHANGES_REQUIRED
CLOSED: B1 B2 B3
OPEN: B4
FINAL_T2_NOW: NO
CERTIFICATION_NOW: NO
MERGE: NO
NEXT: $aios-worker FIX TASK-091
TASK_087: DO_NOT_RUN
```
