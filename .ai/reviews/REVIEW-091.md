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
BLOCKERS_REMAINING: 2
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
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/fix_review.py","tests/aios_bridge/test_fix_review.py","tests/aios_bridge/test_lean_review_integration.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Snapshot

```text
HEAD: 74727d4cc97fd8ea53e10f5bc5ac4e9ca81a8c71
PREVIOUS_REVIEWED_HEAD: b1aa4bd9e7532fed0dca8abe384c63a1e781f5a7
BASE_MAIN: 5a609040030a140c0b10be58f4c351dc17cbfb23
MERGE_BASE: 5a609040030a140c0b10be58f4c351dc17cbfb23
AHEAD: 2
BEHIND: 0
FIX_DELTA_COMMITS: 1
CANDIDATE_STAGE_AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
```

Round 2 is a Delta + Impact review of B1-B4 only. Previously accepted A1-A10 remain protected unless this FIX changed or regressed them.

## Closed Findings

### B1 — CLOSED

Bound proof `test_paths` are now part of deterministic invalidation. A changed proof test/evidence path cannot remain in carried-forward proofs and its T1 is selected. Unknown-impact selection also retains invalidated proof tests rather than dropping them behind fallback expansion.

### B2 — CLOSED

Slice-C publication now fingerprints the exact tracked candidate before targeted T1, re-collects final dirty paths after T1, rejects any candidate mutation, and recomputes final impact analysis before RESULT evidence is emitted. Final analysis must equal the pre-T1 selection analysis or publication fails closed. No retry loop was introduced.

## Blocking Findings

### B3 — Antigravity still does not receive the derived FIX Context Pack in its real worker flow

The FIX added `_interactive_fix_context_for_auth()` and exposes its output only through `bridge.py context`. That helper correctly renders the same semantic pack for an Antigravity authorization, but the checked-in Antigravity `/aios-worker` workflow explicitly says `DO NOT run bridge.py context` and after handoff simply continues implementation in the same session. The shared worker adapter also returns only `AIOS_WORKER_STATUS: AUTHORIZED` plus generic metadata for Antigravity.

Therefore the new test proves renderer equality, not actual delivery through the Antigravity worker surface. The original provider-neutral delivery requirement remains unsatisfied.

Required repair within current narrowed scope:

```text
successful Slice-C FIX handoff selected_executor=antigravity
-> emit the validated derived FIX Context Pack directly on the handoff/worker-visible stdout path
-> same semantic renderer as Codex pack
-> no need for bridge.py context
-> no model call
-> no authority expansion
```

Do not modify the Antigravity workflow or worker_flow in this task. Prefer making Bridge's successful handoff output itself include the bounded derived block when and only when the active executor is Antigravity and validated Slice-C evidence exists.

Required regression must exercise the actual handoff-visible output path (or the exact Bridge function called by that path), not only `_interactive_fix_context_for_auth()` in isolation.

### B4 — Fence-length repair still permits a non-closing fenced-content line to close the outer fence

`_top_level_values()` now remembers delimiter character and opening run length, which fixes the reported shorter-inner-fence case. However it closes the fence whenever a line begins with the same delimiter and a run length >= the opening length, regardless of trailing non-whitespace text.

In Markdown, a closing fenced-code delimiter may be followed only by whitespace. For an outer four-backtick fence, a content line beginning with four backticks plus text is not a valid closing fence. The current parser nevertheless closes on that line, so a later Slice-C marker still inside the outer example can be interpreted as top-level authority input.

Required repair:

```text
opening fence -> remember delimiter character + run length
closing fence -> same delimiter + run length >= opening length + remainder is whitespace only
shorter delimiter or delimiter followed by non-whitespace content -> remain inside fence
```

Also keep the existing simple backtick and tilde cases working.

Required regression: outer four-backtick fence; inner line starts with four backticks followed by non-whitespace text; Slice-C markers after that line must remain fenced and must not activate mode/context.

## Accepted / Do Not Reopen Without Regression

```text
A1 Explicit Slice-C opt-in with compatibility default.
A2 Strict bounded FIX Context Pack schema and exact prior-head binding.
A3 Previous proof fingerprints recomputed from exact Git blob evidence.
A4 Missing/unresolvable proof evidence becomes UNKNOWN.
A5 Subject/dependency/test evidence changes invalidate proof; unchanged VALID proof carries forward.
A6 Unknown/escaped impact expands testing conservatively.
A7 Existing allowed-path authority remains independent and fail-closed.
A8 Codex receives bounded provider-neutral derived FIX pack.
A9 Pre/post targeted-T1 candidate identity now fails closed on mutation.
A10 Review-first candidate publication remains T2=0; certification/merge authority unchanged.
```

## Validation / Scope Audit

Round-2 FIX changed only four authorized implementation/test files plus generated RESULT. Candidate `74727d4c...` is one FIX commit on previous reviewed head `b1aa4bd9...`; main remains exact `5a609040...`, branch behind count is zero.

Candidate publication again correctly deferred final certification:

```text
STATUS: READY_FOR_SEMANTIC_REVIEW
AIOS_MANAGED_T2_EXECUTION_COUNT: 0
CERTIFICATION_DEFERRED: YES
SEMANTIC_REVIEW_REQUIRED: YES
```

Do not run `certify-reviewed` while B3/B4 remain open.

## FIX Contract

TASK-091 continues using the existing compatibility FIX path for its own implementation rounds. Do not add the new Slice-C opt-in markers to this review.

Required targeted tests include at minimum:

```text
venv\Scripts\python.exe -m pytest tests/aios_bridge/test_fix_review.py tests/aios_bridge/test_lean_review_integration.py -q
```

Do not run `pytest tests/ -q` during FIX. Final canonical T2 remains owned only by `certify-reviewed` after semantic acceptance.

## Decision

```text
TASK-091: CHANGES_REQUIRED
CLOSED: B1 B2
OPEN: B3 B4
FINAL_T2_NOW: NO
CERTIFICATION_NOW: NO
MERGE: NO
NEXT: $aios-worker FIX TASK-091
TASK_087: DO_NOT_RUN
```
