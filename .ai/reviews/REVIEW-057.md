# REVIEW-057 — TASK-057 M11.2C.2 Pinned Local MiniMax-M3 Asset Renderer + Exact Input Counter

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Review Anchors

```text
TASK_ID: TASK-057
MILESTONE: M11.2C.2 — PINNED LOCAL MINIMAX-M3 PROVIDER-INPUT COUNTER
BASELINE_MAIN_SHA: 867cb5cdb730639db93a1f184f065dbb97230cd0
TASK_BRANCH: ai/task-057
REVIEWED_TASK_HEAD_SHA: 17f62d3670e1b3a7cbe75f3444969cf51a85bc74
TASK_BLOB_SHA: 64eff17cebe59b267d73d6da9e652cdf3f28458d
BLUEPRINT_BLOB_SHA: 9405f9823b613dd976f8bff6ffe4e9a7bdc85878
RESULT_057_BLOB_SHA: 787f62902ad9b13875be2e3ff3f0db48fd5a1ec5
MINIMAX_COUNTER_BLOB_SHA: 7921b0132fba3b4e6846a0806e03337016ae938c
PROVIDER_INPUT_BUDGET_BLOB_SHA: ed9af7080af623ea7b6d8d802a5f43c591d74f9d
REQUIREMENTS_BLOB_SHA: fa6c2618417bbd962f5927c305798a0a08917910
TEST_BLOB_SHA: f8b6d85a484e5318fcbf081ce21f2ee79f4e0b0b
E4_CONTROL_COMMIT_SHA: 55837e11ec9595f449525a2310b209b6250b553e
OFFICIAL_MINIMAX_REVISION: 3a41b311ffa5719cef48fed3974ccf2cc03733ea
```

## Lineage / Scope — PASS

Independent GitHub comparison proves:

```text
main: 867cb5cdb730639db93a1f184f065dbb97230cd0
ai/task-057: 17f62d3670e1b3a7cbe75f3444969cf51a85bc74
status: ahead
commits_ahead: 1
commits_behind: 0
merge_base: 867cb5cdb730639db93a1f184f065dbb97230cd0
```

Changed files are exactly:

```text
.ai/results/RESULT-057.md
requirements.txt
src/aios_bridge/minimax_m3_input_counter.py
src/aios_bridge/provider_input_budget.py
tests/aios_bridge/test_minimax_m3_input_counter.py
```

Executor scope therefore matches the four authorized implementation/test/dependency paths plus Bridge-generated RESULT publication.

## What Is Correct

The implementation correctly establishes most of the intended local/offline proof chain:

- `tokenizers==0.23.1` and `Jinja2==3.1.6` are pinned.
- Runtime asset bundle requires exactly manifest + chat template + tokenizer.
- Manifest JSON rejects duplicate keys and missing/extra fields.
- Repository/revision/path constants are exact and immutable in the manifest contract.
- Manifest/template/tokenizer are required to be regular non-symlink local files.
- Bundle path escape and extra files are rejected.
- Template/tokenizer size ceilings are checked before engine parse.
- Actual template/tokenizer bytes are SHA-256 rehashed and compared with manifest digests.
- Template UTF-8 is strict.
- No runtime asset download/provider/token-count endpoint is present.
- Existing AIOS `render_messages(ModelRequest)` is reused.
- Exact `[system:str, user:str]` two-message shape is enforced before template/tokenizer execution.
- Template render passes `tools=None` and `add_generation_prompt=True` and does not explicitly pass `thinking_mode`.
- Tokenizer uses `add_special_tokens=False`.
- Evidence is bound to canonical `ModelRequest` fingerprint and contains no prompt/template/tokenizer bytes.
- Production trusted-local registry contains exactly `MiniMaxM3LocalProviderInputCounter`; exact-type semantics still reject subclasses/wrappers/Protocol-only objects.
- Network/provider/credential surfaces are absent from the production counter module.

Full repository suite is green:

```text
1784 passed, 7 skipped, 1533 warnings in 209.95s
EXIT_CODE: 0
```

E4 reports:

```text
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: 867cb5cdb730639db93a1f184f065dbb97230cd0
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 4
```

## Blocking Finding B1 — Sandbox Removes a Global Required by the Pinned Official Template

TASK-057 requires the production counter to render the actual pinned local `chat_template.jinja`, not merely synthetic test templates.

The production loader currently creates a `SandboxedEnvironment`, then executes:

```python
environment.globals.clear()
environment.globals["raise_exception"] = _template_raise_exception
```

This removes Jinja's built-in `namespace` global.

However the exact official MiniMax-M3 chat template at pinned revision `3a41b311ffa5719cef48fed3974ccf2cc03733ea` unconditionally contains the equivalent of:

```jinja2
{% set last_tool_call = namespace(name=none) %}
```

before the conversation loop. This path is reached even for the exact AIOS two-message `[system,user]` shape with `tools=None`.

Therefore the real pinned template will encounter `namespace` as undefined under the current `StrictUndefined` sandbox and fail rendering before tokenization. The production counter cannot yet produce the promised exact MiniMax-M3 input count from the real pinned asset bundle.

This is a functional/security blocker because `MiniMaxM3LocalProviderInputCounter` is already registered as the sole production trusted counter type, while its real official-template path is not executable.

### Why the Green Tests Do Not Catch B1

Current tests mostly monkeypatch `_load_jinja_template()` with `FakeTemplate`, and the synthetic template fixture is only:

```text
{{ messages[0].content }}|{{ messages[1].content }}
```

It does not exercise the production Jinja loader against a required `namespace(...)` expression. The missing-dependency test exercises import failure only. Thus the test suite proves generic render/tokenize plumbing but not compatibility of the sandbox global allowlist with the pinned official template's required Jinja primitives.

### Required FIX for B1

Preserve the sandbox and fail-closed posture. Do NOT restore the complete default Jinja global namespace.

The production Jinja environment must explicitly allowlist only the safe Jinja global(s) required by the pinned template for the supported AIOS path, including `namespace`, plus the already bounded `raise_exception` helper.

Suitable semantics:

```text
SANDBOXED_ENVIRONMENT: REQUIRED
STRICT_UNDEFINED: REQUIRED
FILESYSTEM_LOADER: NONE
DEFAULT_GLOBALS_BROADLY_EXPOSED: NO
REQUIRED_SAFE_NAMESPACE_GLOBAL: ALLOWLISTED
RAISE_EXCEPTION: BOUNDED
NETWORK/FILESYSTEM/PROVIDER GLOBALS: NONE
```

The FIX must add regression coverage that uses the REAL production `_load_jinja_template()` path with a synthetic template that calls `namespace(name=none)` and proves it renders successfully under the sandbox. It must also prove the global surface remains narrowly allowlisted rather than restoring all Jinja defaults.

Required regression tests at minimum:

```text
PRODUCTION_JINJA_LOADER_SUPPORTS_NAMESPACE_GLOBAL
NAMESPACE_RENDER_WORKS_WITH_STRICT_UNDEFINED
SANDBOX_GLOBALS_ARE_EXACT_BOUNDED_ALLOWLIST
NO_FILESYSTEM_LOADER
RAISE_EXCEPTION_REMAINS_BOUNDED
UNAUTHORIZED_GLOBAL_REMAINS_UNDEFINED
EXISTING_ASSET_DIGEST_AND_MESSAGE_SHAPE_TESTS_PASS
FULL_REPO_TESTS_PASS
```

Do not solve this by disabling `StrictUndefined`, disabling the sandbox, or restoring all default globals.

## Non-Blocking Evidence Note N1 — RESULT Diff Stat Is Incomplete

`RESULT-057.md` correctly lists all four implementation/dependency/test files under `Files Changed`, but its `Diff Stat` reports only:

```text
requirements.txt
src/aios_bridge/provider_input_budget.py
```

and omits both newly added `src/aios_bridge/minimax_m3_input_counter.py` and `tests/aios_bridge/test_minimax_m3_input_counter.py`.

Independent GitHub comparison proves the actual scoped delta correctly, so this is not a TASK-057 code blocker. As with the earlier TASK-055 evidence issue, Bridge RESULT diff-stat output should not be treated as complete publication evidence for this run.

## FIX Machine-Readable Contract

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-057.md","blob_sha":"64eff17cebe59b267d73d6da9e652cdf3f28458d"},{"path":".ai/context/TASK-057-M11.2C2-PINNED-LOCAL-MINIMAX-M3-ASSET-RENDERER-REISSUE-BLUEPRINT.md","blob_sha":"9405f9823b613dd976f8bff6ffe4e9a7bdc85878"},{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"}]

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/minimax_m3_input_counter.py","src/aios_bridge/provider_input_budget.py","requirements.txt","tests/aios_bridge/test_minimax_m3_input_counter.py"]

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

These markers authorize only the bounded FIX above. They do not authorize merge, asset download/provisioning, a token-count network call, a paid Executor, M11.3, or any real MiniMax/provider call.

## Decision

```text
BLOCKING_FINDINGS: 1
B1: pinned official template requires namespace(), but production sandbox removes it
NON_BLOCKING_FINDINGS: 1
N1: RESULT diff stat is incomplete but independently recoverable
REGRESSIONS_OBSERVED: 0 in current synthetic/full-suite coverage
FINAL_INDEPENDENT_AUDIT: CHANGES_REQUIRED
```

Do not merge TASK-057.

Human FIX gate:

```text
$aios-worker FIX TASK-057
```

or

```text
/aios-worker FIX TASK-057
```

After Bridge republishes a fresh FIX head:

```text
Review TASK-057
```

M11.3 remains blocked. No asset provisioning and no real paid API call is authorized by this review.
