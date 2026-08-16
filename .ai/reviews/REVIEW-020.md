# REVIEW-020 — TASK-020 Quota & Efficiency Telemetry

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1`
- Reviewed branch: `ai/task-020`
- Reviewed branch head: `579ef1ddd6dab291492f6039357361a080709f27`
- Tested implementation SHA: `52ec609de139426ae41b6f411f4fae545e1402de`
- Base main: `5484462208dd47b9fbb3fd5ad382f423301c468a`
- Branch relation: ahead `2`, behind `0`; merge-base is exact current main.
- Implementation-to-reviewed-head relation: one evidence-only commit adds `.ai/results/RESULT-020.md`; production code/tests at reviewed head equal the tested implementation.
- Review mode: ADR-013 delta-first. Reviewed RESULT/Review Manifest, compare metadata, implementation patch, and only targeted contract/source/test ranges needed to decide the findings below. No whole-repo reload.

## Positive Evidence
- Scope remains isolated to Continuity telemetry plus the TASK-019 historical baseline and RESULT.
- `bridge.py` behavior is unchanged.
- RESULT reports: Continuity `35 passed`, Bridge `121 passed`, full repository `595 passed`.
- No live external call, no telemetry model turn, no authority widening.
- Canonical JSON/fingerprint, strict root/layer field rejection, source semantics, task/actor/action validation, 16 KiB cap, and basic deterministic helpers are present.

## Required Changes

### R1-1 — Bound `TokenMeasurement.method`; do not leave a free-form persistence escape hatch

`TokenMeasurement.method` currently accepts any non-empty string for ESTIMATED values and arbitrary strings for REPORTED values. That conflicts with TASK-020's fail-closed requirement for unbounded/free-form payload fields and ADR-014 security/privacy requirements.

It also weakens provenance integrity: `estimate_tokens_from_bytes()` accepts an arbitrary method label but applies the same byte estimator for unknown labels, so a record can claim a method that was not actually used.

Required fix:
- make `method` a bounded conservative identifier/value (length + character/pattern bound, or an equivalent bounded representation);
- preserve required values such as `utf8-bytes-div4-v1` and `historical-audit-estimate-v1`;
- `estimate_tokens_from_bytes()` must reject unsupported method labels, or otherwise ensure the stored method truthfully identifies the algorithm actually executed;
- add tests rejecting oversized/free-form method payloads and unsupported estimator method labels.

### R1-2 — Historical TASK-019 baseline must not fabricate unavailable exact proxy counts as zero

`.ai/metrics/TASK-019-USAGE.json` records `full_file_reads: 0`, `artifact_reads: 0`, and executor `test_runs: 0` even though those exact historical proxy counts were not captured. Zero means an exact observed zero, not UNKNOWN; for TASK-019 it is also inconsistent with the known workflow (artifacts/source were read and tests were run).

ADR-014/TASK-020 explicitly require unavailable historical exact proxies to remain unknown/null rather than guessed.

Required fix:
- allow the relevant exact proxy fields to represent UNKNOWN where measurement was not captured (for example nullable bounded counts, or an equally compact explicit-known/unknown representation);
- update TASK-019 baseline so unavailable `full_file_reads`, `artifact_reads`, `test_runs`, and any other uncaptured exact proxies are `null`/UNKNOWN rather than `0`;
- retain exact zeros only where zero is actually known, e.g. `external_api_calls: 0` when supported by evidence;
- add baseline tests proving unknown historical proxies remain unknown rather than silently becoming zero.

### R1-3 — Enforce the locked efficiency identity when all components are known

ADR-014 defines:

`brain_context_bytes = useful_context_bytes + redundant_context_bytes + escalated_context_bytes`

Current validation only rejects when the known component sum exceeds `brain_context_bytes`. It therefore accepts fully-known inconsistent records such as total `10000`, useful `1000`, redundant `1000`, escalated `1000`.

It also permits a supplied `context_efficiency_ratio` that disagrees with known `useful_context_bytes / brain_context_bytes`.

Required fix:
- when all partition components and total are known, require exact partition equality;
- when only a subset is known, retaining the existing partial-sum `<= total` safety check is acceptable;
- when ratio, useful bytes, and total bytes are all known, require the ratio to match the deterministic helper's result/rounding convention;
- add tests for under-filled fully-known partitions and inconsistent supplied ratios, not only the current `sum > total` case.

### R1-4 — Mixed UNKNOWN token aggregation must not silently present a partial sum as a complete total

`aggregate_token_ranges()` currently skips UNKNOWN measurements and returns the sum of known measurements. The current test explicitly treats `[REPORTED, ESTIMATED, UNKNOWN]` as a complete numeric aggregate. For an actor/task total, that can under-report usage while hiding that part of the measurement is unknown.

Required fix:
- preserve incompleteness when any included measurement is UNKNOWN (simplest acceptable behavior: return `(None, None)` for a mixed set), or return an equally bounded aggregate result that explicitly carries completeness/UNKNOWN status;
- do not silently label a known-only subtotal as the total of a sequence containing UNKNOWN usage;
- add a test for mixed known + UNKNOWN aggregation semantics.

## Required Re-Test

At minimum:

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## FIX Scope Guidance

Expected FIX scope is small and should normally remain limited to:

```text
src/aios_bridge/continuity/usage.py
tests/aios_bridge/continuity/test_usage.py
.ai/metrics/TASK-019-USAGE.json
.ai/results/RESULT-020.md
```

Do not modify Bridge handoff/sync/publish semantics or widen RUN/FIX/MERGE authority.

## Decision

`CHANGES_REQUIRED`

The telemetry foundation is structurally sound, but these integrity issues must be fixed before it becomes the measurement basis used to compare ChatGPT and Antigravity quota/workload. Inaccurate provenance, fabricated zero proxies, inconsistent efficiency partitions, or incomplete aggregates would undermine the purpose of M1.5 itself.
