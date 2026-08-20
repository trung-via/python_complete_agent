# REVIEW-057 — TASK-057 M11.2C.2 Pinned Local MiniMax-M3 Asset Renderer + Exact Input Counter

STATUS: PASS
APPROVED: YES
READY_FOR_HUMAN_MERGE: YES
MERGE_AUTHORIZED: YES
MERGED_TO_MAIN: YES

## Review Anchors

```text
TASK_ID: TASK-057
MILESTONE: M11.2C.2 — PINNED LOCAL MINIMAX-M3 PROVIDER-INPUT COUNTER
BASELINE_MAIN_SHA: 867cb5cdb730639db93a1f184f065dbb97230cd0
TASK_BRANCH: ai/task-057
INITIAL_REVIEWED_HEAD_SHA: 17f62d3670e1b3a7cbe75f3444969cf51a85bc74
FINAL_REVIEWED_TASK_HEAD_SHA: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
MERGED_MAIN_SHA: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
TASK_BLOB_SHA: 64eff17cebe59b267d73d6da9e652cdf3f28458d
BLUEPRINT_BLOB_SHA: 9405f9823b613dd976f8bff6ffe4e9a7bdc85878
FIX_AUTH_REVIEW_BLOB_SHA: 578b04bba554e7b6b0531587b7c585de1995d8e9
RESULT_057_BLOB_SHA: 6e7c2b1ee3d3a7d4ee53a019ba6d805d3837b0f4
MINIMAX_COUNTER_BLOB_SHA: 304011b037a7eec38f5d19cd4854e83cc725ed4d
PROVIDER_INPUT_BUDGET_BLOB_SHA: ed9af7080af623ea7b6d8d802a5f43c591d74f9d
REQUIREMENTS_BLOB_SHA: fa6c2618417bbd962f5927c305798a0a08917910
TEST_BLOB_SHA: 404299c6fc4fb12fc6f77120ba0b16c0e4eb9b2f
E4_FIX_CONTROL_COMMIT_SHA: 9cadc07ce90438947c564ac747b99cc38bee979e
OFFICIAL_MINIMAX_REVISION: 3a41b311ffa5719cef48fed3974ccf2cc03733ea
```

## Lineage / Scope — PASS

Independent GitHub comparison proved before merge:

```text
main: 867cb5cdb730639db93a1f184f065dbb97230cd0
ai/task-057 final: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
status: ahead
commits_ahead: 2
commits_behind: 0
merge_base: 867cb5cdb730639db93a1f184f065dbb97230cd0
```

The FIX delta from the initial reviewed head was exactly one additional commit:

```text
17f62d3670e1b3a7cbe75f3444969cf51a85bc74
  -> 1331813af4e21fa4e1769bcfe439abb1c67f7f20
```

The FIX touched only:

```text
.ai/results/RESULT-057.md
src/aios_bridge/minimax_m3_input_counter.py
tests/aios_bridge/test_minimax_m3_input_counter.py
```

This was within the authorized FIX scope. Final reviewed SHA -> `ai/task-057` compared IDENTICAL before merge.

## Original TASK-057 Contract — PASS

The final implementation preserves the intended fully local proof chain:

```text
exact ModelRequest
  -> existing AIOS render_messages()
  -> exact [system:str, user:str] shape gate
  -> validated local pinned chat_template.jinja
  -> sandboxed local Jinja render
  -> validated local pinned tokenizer.json
  -> encode(add_special_tokens=False)
  -> exact ProviderInputCountEvidence
```

Verified invariants:

- `tokenizers==0.23.1` and `Jinja2==3.1.6` remain pinned in requirements.
- Runtime bundle requires exactly manifest + template + tokenizer.
- Manifest rejects duplicate/missing/extra fields and mutable/wrong source revision/path values.
- Asset root, manifest, template, and tokenizer are local regular non-symlink objects under the supplied bundle directory.
- Template/tokenizer size ceilings precede engine parse.
- Actual local template/tokenizer bytes are SHA-256 rehashed and must equal manifest receipts.
- Template decoding is strict UTF-8.
- No runtime download, Hugging Face Hub, provider token-count endpoint, credential read, provider transport, or network client surface exists in the counter module.
- Existing AIOS `render_messages(ModelRequest)` remains the ModelRequest-to-message authority.
- Shape drift beyond exact two text messages `[system,user]` fails before Jinja/tokenizer execution.
- Template render supplies `messages`, `tools=None`, `add_generation_prompt=True`, and intentionally omits explicit `thinking_mode`.
- Tokenizer encoding uses `add_special_tokens=False`.
- Evidence binds provider/model/counter identity and canonical ModelRequest fingerprint and persists no prompt/template/tokenizer bytes.
- Production trusted-local registry contains exactly `MiniMaxM3LocalProviderInputCounter`; subclasses/wrappers/Protocol-only objects remain rejected by exact-type authority.

## B1 Re-review — RESOLVED

Original blocker:

```text
B1: pinned official MiniMax-M3 template requires namespace(),
    but the production sandbox removed all default Jinja globals.
```

The FIX imports the Jinja `Namespace` implementation and constructs the environment as:

```text
SandboxedEnvironment: YES
StrictUndefined: YES
loader: NONE
autoescape: FALSE
```

Then clears default globals and restores exactly:

```text
namespace
raise_exception
```

No broad default-global restoration occurred.

Independent inspection of the exact immutable official MiniMax-M3 template at revision `3a41b311ffa5719cef48fed3974ccf2cc03733ea` confirmed that the supported AIOS path reaches `namespace(name=none)` before iterating the conversation. The same pinned template maps the initial AIOS `system` message into the developer slot, emits default MiniMax system/thinking framing, renders the user turn, and adds the AI generation prefix when `add_generation_prompt=True`.

Regression source checks production namespace compatibility, sandbox preservation, `StrictUndefined`, `loader=None`, exact bounded globals, unauthorized global rejection, and bounded `raise_exception` behavior.

## Test / E4 Evidence

Bridge-owned full repository suite after FIX:

```text
1784 passed, 9 skipped, 1533 warnings in 189.58s
EXIT_CODE: 0
```

FIX E4 evidence:

```text
ACTION: FIX
EXECUTOR_ID: codex
AUTHORIZED_ARTIFACT: .ai/reviews/REVIEW-057.md @ 578b04bba554e7b6b0531587b7c585de1995d8e9
E4_CONTROL_COMMIT_SHA: 9cadc07ce90438947c564ac747b99cc38bee979e
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: 17f62d3670e1b3a7cbe75f3444969cf51a85bc74
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 2
```

## Evidence Note N1 — RESOLVED

The fresh FIX RESULT accurately reports its complete FIX delta and independent GitHub comparison agreed.

## Non-Blocking Runtime Prerequisite N2

The full-suite skip count increased from 7 to 9 because the two new production-Jinja regression tests use `pytest.importorskip("jinja2")`, and the E4 executor environment did not provision Jinja2 during this run.

This is not a merge blocker because TASK-057 explicitly forbids E4/runtime network installation, pins the required dependency separately, and the production counter fails closed when Jinja2 or tokenizers is unavailable. No paid enablement can proceed through a counter that failed construction.

Before M11.3 operational proof the Human/operator runtime MUST provision the exact pinned dependencies and the real pinned asset bundle. M11.3 must then execute the real local counter and compare:

```text
LOCAL_PRECALL_COUNT == PROVIDER_REPORTED_INPUT_TOKENS
```

A mismatch remains an M11.3 failure; the consumed grant is not restored and retry remains forbidden.

## Findings

```text
BLOCKING_FINDINGS: 0
B1: RESOLVED
NON_BLOCKING_FINDINGS: 1
N1: RESOLVED
N2: runtime Jinja/tokenizer provisioning required before M11.3
REGRESSIONS_OBSERVED: 0
FINAL_INDEPENDENT_AUDIT: PASS
```

## Merge Receipt

Human explicitly authorized:

```text
Merge TASK-057
```

Pre-merge gates:

```text
CANONICAL_REVIEW_STATUS: PASS
REVIEWED_TASK_HEAD_SHA: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
TASK_BRANCH_MATCHES_REVIEWED_HEAD: PASS
PRE_MERGE_MAIN_SHA: 867cb5cdb730639db93a1f184f065dbb97230cd0
PRE_MERGE_MAIN_MATCHES_BASELINE: PASS
FAST_FORWARD_ELIGIBLE: PASS
```

Merge action:

```text
MERGE_METHOD: FAST_FORWARD_REF_UPDATE
FORCE: FALSE
TARGET_MAIN_SHA: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
```

Post-merge verification must remain exact:

```text
POST_MERGE_MAIN_SHA: 1331813af4e21fa4e1769bcfe439abb1c67f7f20
POST_MERGE_COMPARE_STATUS: IDENTICAL
```

TASK-057 / M11.2C.2 is merged only at the exact reviewed head. This merge does not authorize dependency/asset provisioning, M11.3 execution, or any real MiniMax paid call.