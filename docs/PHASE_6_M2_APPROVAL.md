# Phase 6 M2.4 — Human Approval and Ingestion Queue Bridge

## Purpose

M2.4 is the authority boundary between advisory Product Intelligence ranking and
the Phase 6 M1 file-backed ingestion queue. A score, confidence value, decision
band, or shortlist position can recommend operator attention, but none of those
values authorizes ingestion.

The bridge has no UI and performs no discovery, scoring, ranking, network,
browser, LLM, Google Drive, ingestion, or `AgentController` operation.

## Explicit decision contract

`create_approval_record` accepts the canonical immutable `RankedCandidate` plus
three mandatory operator inputs:

- `decision`: an explicit `ApprovalDecision.APPROVE` or
  `ApprovalDecision.REJECT`;
- `actor`: an explicit non-empty, single-line operator identifier; and
- `decided_at`: an explicit timezone-aware `datetime` (there is no wall-clock
  default).

The resulting frozen `ApprovalRecord` retains the exact `RankedCandidate`
object, and therefore the exact candidate snapshot and `WinningProductScore`
used for the decision. Candidate identity is not rescored, reranked, copied, or
reconstructed at this boundary.

`RECOMMENDED` and `NEEDS_REVIEW` remain advisory. The API does not infer a
decision from `final_score`, confidence, decision band, rank, or any threshold.

## Canonical M1 task

Only a record whose decision is explicitly `APPROVE` can be passed to
`build_ingestion_task`. For an approved URL `https://example.test/product`, the
canonical one-line M1 prompt is:

```text
Scrape product images from https://example.test/product
```

The prompt is a fixed prefix plus the candidate URL. The bridge does not ask an
LLM to interpret or rewrite it. URLs must be absolute HTTP(S) URLs without
credentials, whitespace, or control characters. `REJECT` cannot produce a task
and fails before queue paths are touched.

## Queue semantics

`enqueue_approval` accepts an approved record and optional `tasks_file` and
`completed_file` paths (defaulting to `tasks.txt` and `completed.txt`). It:

1. validates the approval, URL, and distinct queue paths before opening files;
2. reads `completed.txt` and returns `ALREADY_COMPLETED` if the canonical task
   is present;
3. reads `tasks.txt` and returns `ALREADY_QUEUED` if the canonical task is
   present; or
4. appends exactly one non-comment, non-blank UTF-8 task line, flushes it, calls
   `fsync`, and only then returns `ENQUEUED`.

Blank lines and comment lines are ignored when checking both files, matching the
M1 queue reader. An existing unterminated final line is separated before the
new task is appended. `completed.txt` is never opened for writing and is never
created or modified by this bridge.

The V1 contract assumes a single process. Distributed locking and queue worker
execution remain outside M2.4; enqueueing does not start ingestion.

## Example

```python
from datetime import datetime, timezone

from src.product_intelligence import (
    ApprovalDecision,
    create_approval_record,
    enqueue_approval,
)

record = create_approval_record(
    ranked_candidate,
    decision=ApprovalDecision.APPROVE,
    actor="operator@example.com",
    decided_at=datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc),
)
result = enqueue_approval(record)
```

The caller may later start the existing Phase 6 M1 queue processor through its
separate lifecycle. This bridge never does so.
