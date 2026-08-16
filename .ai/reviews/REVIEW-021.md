# REVIEW-021 — TASK-021 Brain-Neutral Contract

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1`
- Reviewed branch: `ai/task-021`
- Reviewed branch head: `1e15abe3170bba4d96edfa274358f1c20bb945a5`
- Tested implementation SHA: `97a71e2673b1add7617e2cc411128fb48cc40c37`
- Base main: `5c93561bf08d7fb0ed91c9199b0ae023c8b1ea4b`
- Branch relation: ahead `2`, behind `0`; merge-base is exact current main.
- Implementation-to-reviewed-head relation: one evidence-only commit adds `.ai/results/RESULT-021.md`; production code/tests at reviewed head equal the tested implementation.
- Review mode: ADR-013 delta-first. Reviewed RESULT/Review Manifest, compare metadata, implementation patch, TASK-021 contract clauses, and only targeted source/test ranges needed for the findings below. No whole-repo reload.

## Positive Evidence
- Antigravity owned implementation planning: `EXECUTOR_PLAN_OWNER: antigravity`; no separate ChatGPT implementation PLAN was used.
- Scope is isolated to Continuity Brain-neutral contract + tests + RESULT.
- Existing runtime providers, External Brain contracts, and `bridge.py` behavior remain untouched.
- RESULT reports: Continuity `47 passed`, Bridge `133 passed`, full repository `607 passed`, zero regressions.
- No live external calls, model invocation, routing, fallback, executor switching, or authority widening.
- Closed enums, task/request/actor validation, bounded context references, sensitive path rejection, duplicate context-ref rejection, canonical JSON/fingerprint, and 16 KiB top-level limits are present.

## Required Changes

### R1-1 — BrainResult must persist pointers/metadata, not arbitrary Brain output bodies

TASK-021 requires BrainResult to support an `artifact_ref | bounded_content_ref`-style pointer and explicitly states that Continuity Core stores only the bounded result/artifact pointer plus deterministic metadata needed for continuation. It also forbids raw chat transcript / hidden-reasoning persistence and free-form persistence fields.

The current `BrainResult` instead contains:

```python
bounded_content: str | None
```

and accepts any string up to 4096 characters. A SUCCESS result can therefore persist arbitrary model prose directly inside canonical Continuity state. That creates a direct persistence channel for chat content, prompt-like text, or reasoning-like text and is not a reference/pointer contract.

Required fix:
- replace direct `bounded_content` persistence with a bounded reference/pointer representation (reuse `ContextRef`, `ArtifactRef`, or a small equivalent `ContentRef`/`EvidenceRef` if semantics require it);
- canonical BrainResult should persist only IDs/status/output metadata and artifact/evidence pointers, not raw Brain response bodies;
- reject legacy/raw fields such as `bounded_content`, `transcript`, `reasoning`, or equivalent free-form result-body fields in the locked schema;
- add tests proving raw result content is rejected and pointer-based result round-trip remains deterministic.

Do not add storage, filesystem writes, provider calls, or adapters as part of this fix.

### R1-2 — Output contract/result semantics are not fail-closed against type/payload mismatch

The current schema validates each field independently, but does not validate their meaning together.

Examples currently accepted include:
- a `BrainRequest(operation=REVIEW)` using the default `OutputContract(TASK_ARTIFACT)`;
- an artifact output type with no target artifact path;
- `BrainResult(output_type=REVIEW_ARTIFACT)` pointing at a `.ai/tasks/...` artifact;
- a SUCCESS result carrying both an artifact pointer and direct content, creating two competing result payloads.

For a continuity/failover contract, these mismatches make `output_type` and `output_contract` non-authoritative and can route a replacement Brain to the wrong artifact even though all individual fields pass validation.

Required fix:
- make request output expectations explicit and operation-compatible instead of silently defaulting every operation to `TASK_ARTIFACT`;
- define a small closed compatibility rule/table for the currently locked operations/output types. `TASK_AND_PLAN` may allow the minimal set needed by the existing contract; do not invent a router or new workflow;
- artifact output types must require a target/artifact pointer whose canonical role/path is compatible with the declared output type and active `task_id`; at minimum reject obvious role or TASK identity mismatches;
- SUCCESS must have exactly one authoritative payload pointer consistent with `output_type`;
- add focused negative tests for operation/output mismatch, output-type/artifact-role mismatch, active-task mismatch, and ambiguous/multiple result payloads.

Keep the compatibility validation pure and local to the neutral contract. No Brain invocation or Bridge integration.

## Required Re-Test

At minimum:

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## FIX Scope Guidance

Expected FIX should normally remain limited to:

```text
src/aios_bridge/continuity/brain.py
tests/aios_bridge/continuity/test_brain.py
src/aios_bridge/continuity/__init__.py   # only if public type exports change
.ai/results/RESULT-021.md
```

Do not modify `bridge.py`, runtime provider contracts, External Brain provider/gateway contracts, routing/failover, ExecutorAdapter/Lease, or RUN/FIX/MERGE authority.

## Round-2 Review Budget

Round 2 should be finding-scoped only:
- this REVIEW;
- new RESULT/Review Manifest;
- previous implementation SHA -> FIX implementation SHA delta;
- focused tests for R1-1/R1-2.

No full TASK/ADR/unchanged source/test reload by default.

## Decision

`CHANGES_REQUIRED`

The implementation is structurally clean and the new balanced workflow worked as intended, but the result-persistence and output-consistency boundaries must be fail-closed before this contract becomes the basis of M3 Brain failover.