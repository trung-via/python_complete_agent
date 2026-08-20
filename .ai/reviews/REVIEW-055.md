# REVIEW-055 — TASK-055 M11.2C.1 Full Provider Input Budget Proof Hardening

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Review Anchors

```text
TASK_ID: TASK-055
MILESTONE: M11.2C.1 — FULL PROVIDER INPUT TOKEN BOUND HARDENING
BASELINE_MAIN_SHA: 439f073da2a112531dc78669dfb4aea53f88439b
TASK_BRANCH: ai/task-055
REVIEWED_TASK_HEAD_SHA: 42357e7e4dcfd1be7ad6e636e589c14f305ecb51
TASK_BLOB_SHA: dd46a3615601ed871a7cd73ae80fcc17c8e4c143
BLUEPRINT_BLOB_SHA: ee17d57a47c2a315877dae91ff448733e29347d8
RESULT_055_BLOB_SHA: 1fe6711220c4333c930d0b1fc87e0a666a38368d
PROVIDER_INPUT_BUDGET_BLOB_SHA: 8166dc0d08c54708d081107db97290d6050c81fb
PAID_API_BRAIN_ESCAPE_BLOB_SHA: b97439c10cc67466b01dc3dc25ca7c9741d5ab98
TEST_BLOB_SHA: 829b2e6711b1578cf479ad4740ac8289d084975a
E4_CONTROL_COMMIT_SHA: 68c3f86b1682db0015fe8edd11a1d1e0a8e432e9
```

## Lineage / Scope — PASS

Independent comparison proves:

```text
main: 439f073da2a112531dc78669dfb4aea53f88439b
ai/task-055: 42357e7e4dcfd1be7ad6e636e589c14f305ecb51
status: ahead
commits_ahead: 1
commits_behind: 0
merge_base: 439f073da2a112531dc78669dfb4aea53f88439b
```

Changed files are exactly:

```text
.ai/results/RESULT-055.md
src/aios_bridge/paid_api_brain_escape.py
src/aios_bridge/provider_input_budget.py
tests/aios_bridge/test_paid_api_brain_escape.py
```

Executor scope therefore matches the three authorized implementation/test files plus Bridge-generated RESULT publication.

## What Is Correct

The implementation correctly closes the original context-only budget gap in several respects:

- `provider_input_counter` is mandatory and keyword-only; no permissive default exists.
- `ProviderInputCountEvidence` is immutable and stores no prompt/request body or credentials.
- `fingerprint_model_request()` binds evidence to canonical `ModelRequest.to_dict()` semantics.
- Counter provider/model/counter IDs are checked before counting.
- Counter `is_exact` must be exactly `True`.
- `count_request(model_request)` is called once before paid dispatch enablement.
- Evidence exact type, provider/model/counter identity, exactness, and ModelRequest fingerprint are validated.
- `counted_input_tokens <= model_request.max_input_tokens` is enforced.
- Existing M11.1 grant budget check still enforces `model_request.max_input_tokens <= grant.max_input_tokens` and output bound.
- Existing ACTIVE grant, artifact proof, M10 subscription preference, consume-before-gateway, replay closure, and no-retry invariants remain intact.

Full repository suite is green:

```text
1749 passed, 7 skipped, 1533 warnings in 197.19s
EXIT_CODE: 0
```

E4 reports:

```text
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_PRE_EXECUTION_HEAD: 439f073da2a112531dc78669dfb4aea53f88439b
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 3
```

## Blocking Finding B1 — Local/No-Network Counter Authority Is Not Mechanically Enforced

The locked blueprint requires:

```text
No counter accepted by the paid coordinator may perform network I/O.
NO_NETWORK_COUNTER_SURFACE
```

The current implementation defines `ProviderInputTokenCounter` as a structural Protocol and the coordinator accepts any object exposing:

```text
provider_id
model_id
counter_id
is_exact == True
count_request(...)
```

The coordinator then directly executes:

```python
provider_input_evidence = count_request(model_request)
```

There is no trusted-local counter authority, sealed local execution classification, allowlisted concrete implementation identity, or other runtime proof that this caller-supplied method is local/offline.

Therefore a counter can mechanically satisfy every current precondition while performing an HTTP/provider token-count request inside `count_request()`, then return a syntactically valid `ProviderInputCountEvidence`. The coordinator would accept that evidence and may construct `allow_paid_api=True`.

This violates the locked TASK-055 boundary because a network token-count call can itself consume provider quota or create an additional external call before the one-shot generation grant is consumed. Self-asserted `is_exact=True` does not prove local execution.

The existing `NO_NETWORK_COUNTER_SURFACE` test is insufficient. It checks that `provider_input_budget.py` and `paid_api_brain_escape.py` do not import common network modules, but it does not test the actual supplied counter implementation. The test fake is structurally accepted solely because it conforms to the Protocol.

### Required FIX for B1

Preserve the current full-input evidence contract, but make local/offline counter authority fail-closed before `count_request()`.

The FIX must provide a mechanically enforced trusted-local counter boundary with these semantics:

```text
ARBITRARY_STRUCTURAL_COUNTER: REJECT
SELF_ASSERTED_IS_EXACT_ONLY: INSUFFICIENT
NETWORK_CAPABLE_OR_UNTRUSTED_COUNTER: REJECT BEFORE count_request
TRUSTED_LOCAL_COUNTER: REQUIRED BEFORE count_request
PROVIDER/MODEL/REQUEST/EVIDENCE BINDING: PRESERVED
```

A suitable design may use a sealed/trusted local counter authority or exact trusted implementation registration seam intended for TASK-056. The key requirement is that trust cannot be granted merely by a caller implementing Protocol properties or returning a valid evidence object.

TASK-055 does not need to implement the real MiniMax tokenizer. It is acceptable for the production trusted counter registry/factory to contain no real MiniMax counter until TASK-056, provided tests can exercise the trust seam deterministically without opening arbitrary production authority.

Required regression tests must prove at minimum:

```text
ARBITRARY_PROTOCOL_CONFORMING_COUNTER_REJECTED_BEFORE_COUNT
UNTRUSTED_COUNTER_WITH_IS_EXACT_TRUE_REJECTED_BEFORE_COUNT
UNTRUSTED_COUNTER_CANNOT_TRIGGER_NETWORK_OR_SIDE_EFFECT_CALLBACK
TRUSTED_LOCAL_TEST_COUNTER_ACCEPTED
TRUST_DECISION_PRECEDES_COUNT_REQUEST
COUNTER_CALLED_EXACTLY_ONCE_AFTER_TRUST
ALL_EXISTING_PROVIDER_MODEL_REQUEST_FINGERPRINT_BOUNDS_PRESERVED
ALL_FAILURES_BEFORE_ALLOW_PAID_ENABLEMENT
ALL_FAILURES_BEFORE_CONSUME
ALL_FAILURES_BEFORE_GATEWAY
FULL_REPO_TESTS_PASS
```

Do not solve this by adding another self-reported boolean such as `network_access=False`; that would have the same authority problem.

## Non-Blocking Evidence Note N1

`RESULT-055.md` lists all three implementation files under `Files Changed`, but its `Diff Stat` omits the new `src/aios_bridge/provider_input_budget.py` and reports only two files / 325 insertions. Independent GitHub comparison proves the actual scoped delta correctly, so this is not a code blocker, but Bridge RESULT diff-stat generation should not be treated as complete evidence for this run.

## FIX Machine-Readable Contract

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/tasks/TASK-055.md","blob_sha":"dd46a3615601ed871a7cd73ae80fcc17c8e4c143"},{"path":".ai/context/TASK-055-M11.2C1-FULL-PROVIDER-INPUT-BUDGET-PROOF-HARDENING-BLUEPRINT.md","blob_sha":"ee17d57a47c2a315877dae91ff448733e29347d8"},{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"}]

EXECUTOR_ALLOWED_PATHS_JSON: ["src/aios_bridge/provider_input_budget.py","src/aios_bridge/paid_api_brain_escape.py","tests/aios_bridge/test_paid_api_brain_escape.py"]

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["FIX"]}],"operation":"FIX","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

These markers authorize only the bounded FIX above. They do not authorize merge, a paid Executor, M11.3, tokenizer download, token-count network calls, or any real provider call.

## Decision

```text
BLOCKING_FINDINGS: 1
B1: local/no-network counter authority is not mechanically enforced
NON_BLOCKING_FINDINGS: 1
N1: RESULT diff stat is incomplete but independently recoverable
REGRESSIONS: 0 observed in full suite
FINAL_INDEPENDENT_AUDIT: CHANGES_REQUIRED
```

Do not merge TASK-055.

Human FIX gate:

```text
$aios-worker FIX TASK-055
```

or

```text
/aios-worker FIX TASK-055
```

After Bridge republishes a fresh FIX head:

```text
Review TASK-055
```

M11.3 remains blocked and no real paid API call is authorized.