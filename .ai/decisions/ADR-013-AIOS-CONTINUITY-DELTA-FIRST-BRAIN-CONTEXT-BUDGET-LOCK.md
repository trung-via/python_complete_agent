# ADR-013 — AIOS Continuity Delta-First Brain Context Budget Lock

STATUS: LOCKED

## Context

TASK-019 proved that Chat-first execution can reduce paid External Brain API usage, but the review path still loaded more repository context than necessary. That undermines the quota-efficiency goal of ADR-010.

AIOS therefore SHALL optimize not only Brain turns per task, but also the amount of context loaded into each Brain operation.

This ADR applies prospectively from TASK-020 onward. It does not invalidate TASK-019 approval and does not require TASK-019 to be re-reviewed.

## Decision 1 — Delta First Is the Default

For REVIEW, DIAGNOSIS, PATCH_PROPOSAL, and follow-up validation, the Brain SHALL start from the smallest sufficient evidence set.

Default escalation order:

```text
CURRENT-STATE / task identity
        ↓
RESULT / review manifest
        ↓
previous REVIEW findings, if any
        ↓
compare metadata + changed-file list
        ↓
patch/delta for relevant changed files
        ↓
relevant function/range only if patch is insufficient
        ↓
full file only if still necessary
        ↓
full TASK/ADR only when the decision cannot be made from bounded clauses/evidence
```

The Brain MUST NOT begin by reloading whole source files, whole tests, whole TASK, whole ADR, or whole repository by default.

## Decision 2 — Review Round 1 Budget Policy

Round-1 review SHOULD normally use:

- current Continuity State or equivalent task identity snapshot;
- TASK acceptance criteria, preferably only relevant sections;
- relevant locked ADR clauses, preferably only relevant sections;
- RESULT;
- base→implementation compare metadata;
- changed-file patches/deltas.

Full source-file reads are escalation-only.

## Decision 3 — Review Round 2+ Budget Policy

Round-2 and later reviews SHALL be delta-first and finding-scoped.

Default evidence:

- previous REVIEW;
- new RESULT;
- previous tested implementation SHA;
- new tested implementation SHA;
- delta between those implementation SHAs;
- only evidence needed to close outstanding findings.

Round-2+ review MUST NOT reload the full TASK, full ADR, or unchanged full source/test files unless a specific unresolved issue requires it.

## Decision 4 — Patch Before File

When source inspection is needed:

```text
patch → relevant range/function → full file
```

A full-file read without first considering the patch is considered an escalation and SHOULD be justified by review needs.

## Decision 5 — No Whole-Repo Default

No Brain operation may dump or crawl the whole repository by default.

ContextBuilder principles from ADR-006 remain valid: explicit, relevant, bounded context only.

## Decision 6 — Review Manifest

Future RESULT artifacts SHOULD include a compact `Review Manifest` sufficient to minimize Brain retrieval.

Preferred fields:

```text
BASE_SHA
IMPLEMENTATION_SHA
PREVIOUS_REVIEW_SHA (if applicable)
CHANGED_SINCE_PREVIOUS_REVIEW
FINDING_FIX_MAP
TEST_SUMMARY
AUTHORITY_WIDENED
LIVE_EXTERNAL_CALLS
```

`FINDING_FIX_MAP` SHOULD map each requested finding to the smallest relevant file/range/test evidence available. It is evidence/navigation metadata only and does not replace independent review.

## Decision 7 — Brain Context Metrics

AIOS SHALL treat these as first-class efficiency metrics:

```text
BRAIN_TURNS_PER_TASK
BRAIN_CONTEXT_LOAD_PER_TASK
FULL_FILE_READS_PER_REVIEW
PATCH_BYTES_PER_REVIEW
EXTERNAL_API_CALLS_PER_TASK
HUMAN_COPY_PASTE_BYTES
```

Exact token accounting is optional when a chat surface does not expose reliable token telemetry. In that case, use deterministic proxies such as bytes/lines/artifacts fetched.

## Decision 8 — Normal-Task Targets

Targets, not authorization rules:

```text
Normal task:
- Primary Brain turns: <= 2 when no fix is required
- External paid Brain API calls: 0 by default
- Whole-repo loads: 0

Round-1 review:
- full source reads: 0 by default

Round-2+ review:
- full TASK reload: 0 by default
- full ADR reload: 0 by default
- unchanged full source/test reads: 0 by default
- inspect implementation delta first
```

A task may exceed these targets when correctness requires escalation, but the escalation must remain bounded and evidence-driven.

## Decision 9 — Correctness Outranks Budget

Context minimization MUST NOT cause shallow approval.

If bounded evidence is insufficient, the Brain SHALL escalate to the smallest additional context needed. Fail closed rather than approving without enough evidence.

Quota efficiency means avoiding redundant context, not weakening review quality.

## Decision 10 — Brain Neutrality

This policy applies equally to:

- ChatGPT Chat;
- Claude Chat;
- Gemini Chat;
- future chat/subscription Brains;
- optional API Brains when used.

No vendor-specific branch belongs in the Continuity Core.

## Decision 11 — No Chat Transcript Persistence

AIOS SHALL persist decisions, findings, state pointers, RESULT evidence, and compact manifests — not full chat transcripts or hidden reasoning.

Canonical project memory remains Git/AIOS artifacts, not Brain conversation history.

## Decision 12 — Relationship to Existing ADRs

- ADR-010 remains the Open Multi-Agent Continuity OS architecture authority.
- ADR-011 remains the Canonical Project State authority.
- ADR-012 remains the zero-mandatory-sync/pending happy-path authority.
- ADR-013 adds Brain context-budget policy and does not modify RUN/FIX/MERGE authority.
- Existing External Brain ContextBuilder remains an optional bounded-context mechanism, not the default paid path.

## Decision 13 — TASK-019 Is Not Reopened

TASK-019 Round 2 approval remains valid.

ADR-013 is a process/architecture refinement learned from TASK-019 and is normative for TASK-020 and later work unless explicitly superseded by a future ADR.

## Success Criterion

AIOS context handling is successful when ordinary work trends toward:

```text
paid API calls ↓
Brain turns ↓
Brain context load ↓
human copy/paste → 0
review correctness preserved
```

The system SHALL prefer evidence deltas over repeated full-state rehydration whenever correctness permits.
