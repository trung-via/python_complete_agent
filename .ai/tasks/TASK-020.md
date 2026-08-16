# TASK-020 — #12-M1.5 Quota & Efficiency Telemetry

## Objective

Implement a small deterministic **Usage & Efficiency Telemetry** layer locked by:

```text
ADR-013 — Delta-First Brain Context Budget
ADR-014 — Usage & Efficiency Telemetry Contract
```

The purpose is to measure where Brain/Executor quota/context is spent and where workflow steps are redundant, without adding model turns or widening authority.

## Dependency / Execution Gate

`TASK-019` is APPROVED but is not yet merged when this task is authored. Current `main` is:

```text
689c2c6dd8e41fe0f735b822118ba6530379b7dd
```

TASK-019 reviewed head is:

```text
5484462208dd47b9fbb3fd5ad382f423301c468a
```

**DO NOT RUN TASK-020 until TASK-019 is explicitly merged by human authorization.** TASK-020 requires the Continuity package introduced by TASK-019. After merge, reconcile from the resulting current main before creating/executing `ai/task-020`.

## Scope

Preferred production addition:

```text
src/aios_bridge/continuity/usage.py
```

Preferred tests:

```text
tests/aios_bridge/continuity/test_usage.py
```

Historical baseline artifact:

```text
.ai/metrics/TASK-019-USAGE.json
```

Do not modify `bridge.py` behavior in this task.

## Required Contract

Implement immutable/bounded types equivalent to:

```text
UsageSource = REPORTED | ESTIMATED | UNKNOWN

TokenMeasurement:
- source
- min_tokens | null
- max_tokens | null
- method | null

BrainUsageRecord:
- brain_id
- operation
- round
- turns
- input_bytes
- output_bytes
- patch_bytes
- full_file_reads
- artifact_reads
- external_api_calls
- tokens

ExecutorUsageRecord:
- executor_id
- action: RUN | FIX
- runs
- input_bytes
- output_bytes
- test_runs
- external_api_calls
- tokens

HumanUsage:
- approvals
- manual_sync
- manual_pending
- manual_watch
- human_copy_paste_bytes

EfficiencyMetrics:
- brain_context_bytes
- useful_context_bytes | null
- redundant_context_bytes | null
- escalated_context_bytes | null
- context_efficiency_ratio | null
- full_file_read_rate | null

TaskUsageRecord:
- schema_version = "1"
- task_id
- brain_usage[]
- executor_usage[]
- human_usage
- efficiency
```

Exact internal class names may vary if semantics remain equivalent.

## Validation Rules

Fail closed for:

- unknown fields at locked schema layers;
- unsupported schema version;
- invalid `TASK-NNN` identity;
- invalid actor IDs;
- negative counts/bytes/tokens;
- bool accepted as integer;
- invalid UsageSource or Executor action;
- token range `min > max`;
- REPORTED without exact range (`min == max` required);
- ESTIMATED without a bounded range and method;
- UNKNOWN with token values or estimation method;
- impossible efficiency partition when all components are known;
- ratio outside `[0, 1]`;
- unbounded/free-form payload fields.

No timestamps are required in schema v1; identical semantic records should serialize deterministically.

## Deterministic Helpers

Provide pure helpers for at least:

1. canonical JSON serialization;
2. deterministic record fingerprint;
3. optional byte-based token-equivalent estimate with an explicit versioned method such as `utf8-bytes-div4-v1`;
4. deterministic aggregation of min/max token ranges by actor class;
5. efficiency ratio calculation only when required exact byte components are known.

The byte estimator is a proxy only. It MUST return `ESTIMATED`, never `REPORTED`.

No helper may call network, Git, filesystem discovery, model/API, Browser, Bridge RUN/FIX, or external services.

## TASK-019 Historical Baseline

Create `.ai/metrics/TASK-019-USAGE.json` using **ESTIMATED** values only, with methods identifying them as historical audit estimates.

Preserve bounded stage estimates from the TASK-019 audit approximately as:

```text
ChatGPT TASK_AND_PLAN: 22k–30k
ChatGPT REVIEW R1:     28k–38k
ChatGPT REVIEW R2:     30k–45k
Antigravity RUN:       35k–60k
Antigravity FIX:       23k–38k
```

Do not pretend these are provider-reported values. Where exact byte/context counts were not captured historically, use `null`/UNKNOWN for those exact proxy fields rather than fabricating them.

## Review Manifest Requirement

`RESULT-020.md` MUST contain a compact Review Manifest:

```text
BASE_SHA
IMPLEMENTATION_SHA
PREVIOUS_REVIEW_SHA: null
CHANGED_FILES
TEST_SUMMARY
BRIDGE_BEHAVIOR_CHANGED
AUTHORITY_WIDENED
LIVE_EXTERNAL_CALLS
```

This is the first task required to follow ADR-013/014 delta-first review evidence.

## Forbidden Scope

Do NOT implement:

- automatic ChatGPT/Claude/Gemini UI telemetry;
- browser automation of chat surfaces;
- model invocation;
- provider routing;
- BrainAdapter/ExecutorAdapter;
- Executor Lease;
- quota-based dispatch;
- automatic executor switching;
- Bridge handoff/sync/publish semantic changes;
- RUN/FIX/MERGE authority changes;
- prompt/chat/reasoning persistence;
- secrets/credentials capture.

## Required Tests

At minimum cover:

1. valid schema-v1 record;
2. REPORTED/ESTIMATED/UNKNOWN token semantics;
3. estimate range validation;
4. non-negative integer and bool rejection;
5. actor/task/action validation;
6. unknown-field rejection;
7. deterministic canonical JSON/fingerprint;
8. byte-estimator source/method correctness;
9. token-range aggregation;
10. efficiency ratio calculation;
11. unknown efficiency values remain unknown rather than guessed;
12. impossible efficiency partition rejection;
13. TASK-019 baseline validates and remains ESTIMATED;
14. no secret/free-form transcript fields accepted;
15. existing Continuity/Bridge tests remain green;
16. full repository tests remain green.

No live external calls in tests.

## Test Commands

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

## RESULT-020 Evidence

Include:

```text
IMPLEMENTATION_HEAD: <exact tested SHA>
USAGE_SCHEMA_VERSION: 1
TASK_019_BASELINE_VALID: YES
TELEMETRY_MODEL_TURNS_ADDED: 0
LIVE_EXTERNAL_CALLS: 0
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
SECRETS_OR_REASONING_PERSISTED: NO
```

Also include exact changed files, test results, and the Review Manifest above.

## Completion Gate

TASK-020 is complete only when telemetry can distinguish REPORTED/ESTIMATED/UNKNOWN, preserve a clearly estimated TASK-019 baseline, calculate deterministic usage/efficiency summaries, and do so without any additional model/API authority or Bridge behavior change.