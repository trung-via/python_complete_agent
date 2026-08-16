# ADR-014 — AIOS Continuity Usage & Efficiency Telemetry Contract Lock

STATUS: LOCKED

## Context

TASK-019 showed that counting only Brain turns is insufficient. A small number of turns can still consume excessive context when whole TASK/ADR/source/test artifacts are repeatedly loaded. ADR-013 therefore locked delta-first Brain context handling. AIOS now needs compact, deterministic telemetry so later tasks can measure whether quota/context efficiency is actually improving.

This telemetry MUST remain cheaper than the work it measures. It MUST NOT create extra model turns merely to estimate usage.

## Decision 1 — Measure Facts First, Estimates Second

Every token/quota-like value SHALL declare one source class:

```text
REPORTED   provider/agent supplied an actual usage value
ESTIMATED  AIOS derived a bounded estimate from deterministic observable inputs
UNKNOWN    reliable measurement is unavailable
```

AIOS MUST NOT present ESTIMATED or UNKNOWN values as exact provider quota consumption.

Where chat surfaces do not expose per-turn token telemetry, exact deterministic proxies are preferred:

```text
input_bytes
output_bytes
patch_bytes
full_file_reads
artifact_reads
brain_turns
executor_runs
external_api_calls
test_runs
human_actions
human_copy_paste_bytes
```

An optional token-equivalent estimate may be derived from bytes, but its method/version MUST be recorded.

## Decision 2 — Actor-Neutral Telemetry

Telemetry applies to any Brain or Executor. Core schema MUST NOT contain vendor-specific branches.

Examples:

```text
Brains: chatgpt-chat, claude-chat, gemini-chat, optional API brains
Executors: antigravity, codex, claude-code, future executors
```

Actor identity is descriptive only and does not grant authority.

## Decision 3 — Per-Task Usage Record

Preferred canonical artifact:

```text
.ai/metrics/TASK-NNN-USAGE.json
```

A task usage record SHOULD contain bounded sections equivalent to:

```text
schema_version
task_id
brain_usage[]
executor_usage[]
human_usage
efficiency
```

Brain records SHOULD support:

```text
brain_id
operation
round
turns
input_bytes
output_bytes
patch_bytes
full_file_reads
artifact_reads
external_api_calls
token_value
token_source
token_estimation_method
```

Executor records SHOULD support:

```text
executor_id
action            RUN | FIX
runs
input_bytes
output_bytes
test_runs
external_api_calls
token_value
token_source
token_estimation_method
```

Human records SHOULD support:

```text
approvals
manual_sync
manual_pending
manual_watch
human_copy_paste_bytes
```

All counts SHALL be non-negative integers and bounded.

## Decision 4 — Efficiency / Waste Signals

AIOS SHALL measure not only total usage but also avoidable work.

Preferred efficiency fields:

```text
brain_context_bytes
useful_context_bytes
redundant_context_bytes
escalated_context_bytes
context_efficiency_ratio
full_file_read_rate
```

Definitions:

```text
brain_context_bytes = useful + redundant + escalated
context_efficiency_ratio = useful / brain_context_bytes
```

If useful/redundant classification is unavailable, those fields SHALL be UNKNOWN rather than guessed.

`escalated_context_bytes` means additional context intentionally loaded after a smaller evidence set proved insufficient. Escalation is not automatically waste.

## Decision 5 — Delta-First Review Metrics

For REVIEW operations, telemetry SHALL support the ADR-013 metrics:

```text
BRAIN_TURNS_PER_TASK
BRAIN_CONTEXT_LOAD_PER_TASK
FULL_FILE_READS_PER_REVIEW
PATCH_BYTES_PER_REVIEW
EXTERNAL_API_CALLS_PER_TASK
HUMAN_COPY_PASTE_BYTES
```

Round 2+ SHOULD additionally record whether unchanged full TASK/ADR/source/test artifacts were reloaded.

Normal target:

```text
round-2+ full TASK reload = 0
round-2+ full ADR reload = 0
round-2+ unchanged full source/test reads = 0
```

## Decision 6 — Review Manifest Integration

Future RESULT artifacts SHOULD expose a compact Review Manifest so Brain retrieval can be measured and minimized:

```text
BASE_SHA
IMPLEMENTATION_SHA
PREVIOUS_REVIEW_SHA
CHANGED_SINCE_PREVIOUS_REVIEW
FINDING_FIX_MAP
TEST_SUMMARY
```

Deterministic facts such as SHA, diffstat, changed-file list, byte counts and test counts SHOULD be computed by code or Git tooling, not by model reasoning when practical.

## Decision 7 — Collection Without Write Conflicts

Brain and Executor SHALL NOT concurrently mutate the same metrics file.

Preferred flow:

```text
Executor RESULT -> Executor Usage Manifest
Brain REVIEW    -> Brain Usage Manifest
                         ↓
              deterministic collector
                         ↓
            .ai/metrics/TASK-N-USAGE.json
```

A future collector may aggregate records into `.ai/metrics/USAGE-SUMMARY.json`, but aggregation MUST be deterministic and must not require an LLM.

## Decision 8 — Telemetry Overhead Budget

Telemetry itself SHALL target:

```text
additional model turns = 0
external API calls for telemetry = 0
telemetry context overhead < 1% of task context when measurable
```

If collection would materially increase Brain/Executor workload, collect fewer exact proxies rather than richer speculative estimates.

## Decision 9 — Security / Privacy

Telemetry MUST NOT persist:

```text
prompt bodies
chat transcripts
hidden/separated reasoning
API keys
OAuth/session tokens
cookies
Authorization headers
private keys
raw HTTP bodies
browser profile data
arbitrary free-form context dumps
```

Store counts, identifiers, hashes, bounded classifications and deterministic measurements only.

## Decision 10 — No Authority Widening

Usage telemetry is observability only.

It MUST NOT:

```text
authorize RUN/FIX/MERGE
select a Brain or Executor by itself
invoke models
invoke tools
change Bridge handoff semantics
change existing human approval gates
```

## Decision 11 — TASK-019 Historical Baseline

TASK-019 SHALL be preserved as the first historical baseline, clearly marked estimated because neither ChatGPT Chat nor Antigravity exposed authoritative per-task token telemetry.

Current audit estimate to preserve as a non-authoritative baseline:

```text
ChatGPT task-specific token-equivalent: ~80k–120k
Antigravity token-equivalent:          ~60k–100k
Round-2 ChatGPT review:                ~30k–45k
Delta-first Round-2 target:            ~6k–10k
```

These are ranges, not provider-reported quota values. Future measurements SHOULD prefer exact bytes/proxies and reported usage whenever available.

## Decision 12 — Relationship to Existing ADRs

- ADR-010 remains the Open Multi-Agent Continuity OS architecture authority.
- ADR-011 remains Canonical Project State authority.
- ADR-012 keeps `sync/pending/watch` out of the mandatory happy path.
- ADR-013 remains the Delta-First Brain Context Budget authority.
- ADR-014 adds measurement/efficiency telemetry only.

## Success Criterion

AIOS can answer, from compact evidence rather than guesswork:

```text
How much work did each Brain/Executor process?
Which usage is REPORTED vs ESTIMATED vs UNKNOWN?
Where was context redundant?
Did delta-first review reduce context load?
Which workflow step is the current quota bottleneck?
Can a step be removed without weakening correctness or authority?
```

Telemetry is successful only if it helps reduce future usage while adding essentially no model-turn overhead.