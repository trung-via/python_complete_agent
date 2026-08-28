from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Union
from urllib.parse import urlsplit

from src.product_intelligence.models import ProductCandidateSnapshot, WinningProductScore
from src.product_intelligence.ranking import RankedCandidate


INGESTION_TASK_PREFIX = "Scrape product images from "


class ApprovalError(ValueError):
    """Raised when an approval or approval-to-queue request is invalid."""


class ApprovalDecision(str, Enum):
    """The explicit decisions available at the human approval boundary."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


class EnqueueOutcome(str, Enum):
    """Deterministic outcomes from attempting to append an approved task."""

    ENQUEUED = "ENQUEUED"
    ALREADY_QUEUED = "ALREADY_QUEUED"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"


@dataclass(frozen=True)
class ApprovalRecord:
    """Immutable record of one explicit human decision on one ranked value."""

    ranked_candidate: RankedCandidate
    decision: ApprovalDecision
    actor: str
    decided_at: datetime

    def __post_init__(self) -> None:
        _validate_ranked_candidate(self.ranked_candidate)
        if not isinstance(self.decision, ApprovalDecision):
            raise ApprovalError("decision must be an explicit ApprovalDecision")
        _validate_actor(self.actor)
        _validate_decided_at(self.decided_at)
        _validate_candidate_url(self.ranked_candidate.candidate.url)

    @property
    def candidate(self) -> ProductCandidateSnapshot:
        """Return the exact candidate snapshot held by the ranked input."""

        return self.ranked_candidate.candidate

    @property
    def score(self) -> WinningProductScore:
        """Return the exact score held by the ranked input."""

        return self.ranked_candidate.score


@dataclass(frozen=True)
class EnqueueResult:
    """Immutable report of an append or an explicit idempotent no-op."""

    task: str
    outcome: EnqueueOutcome

    @property
    def appended(self) -> bool:
        return self.outcome is EnqueueOutcome.ENQUEUED

    @property
    def enqueued(self) -> bool:
        """Compatibility spelling for callers interested in queue mutation."""

        return self.appended


PathLike = Union[str, os.PathLike[str]]


def create_approval_record(
    ranked_candidate: RankedCandidate,
    *,
    decision: ApprovalDecision,
    actor: str,
    decided_at: datetime,
) -> ApprovalRecord:
    """Create an approval record from explicit inputs, with no side effects."""

    return ApprovalRecord(
        ranked_candidate=ranked_candidate,
        decision=decision,
        actor=actor,
        decided_at=decided_at,
    )


def build_ingestion_task(record: ApprovalRecord) -> str:
    """Build the canonical Phase 6 M1 task for an explicit approval."""

    _validate_approval_record(record)
    if record.decision is not ApprovalDecision.APPROVE:
        raise ApprovalError("only an explicit APPROVE record can become an ingestion task")
    url = record.ranked_candidate.candidate.url
    _validate_candidate_url(url)
    return f"{INGESTION_TASK_PREFIX}{url}"


def enqueue_approval(
    record: ApprovalRecord,
    *,
    tasks_file: PathLike = "tasks.txt",
    completed_file: PathLike = "completed.txt",
) -> EnqueueResult:
    """
    Append one canonical M1 task, or return an explicit idempotent no-op.

    All approval, URL, and path validation occurs before either queue file is
    opened. The completed queue is read-only. This function never starts or
    constructs an AgentController and performs no ingestion work.
    """

    task = build_ingestion_task(record)
    tasks_path, completed_path = _validate_queue_paths(tasks_file, completed_file)

    completed_tasks = _read_queue_tasks(completed_path)
    if task in completed_tasks:
        return EnqueueResult(task=task, outcome=EnqueueOutcome.ALREADY_COMPLETED)

    queued_tasks = _read_queue_tasks(tasks_path)
    if task in queued_tasks:
        return EnqueueResult(task=task, outcome=EnqueueOutcome.ALREADY_QUEUED)

    needs_separator = _needs_line_separator(tasks_path)
    with tasks_path.open("a", encoding="utf-8", newline="") as queue:
        if needs_separator:
            queue.write("\n")
        queue.write(f"{task}\n")
        queue.flush()
        os.fsync(queue.fileno())

    return EnqueueResult(task=task, outcome=EnqueueOutcome.ENQUEUED)


def _validate_ranked_candidate(ranked_candidate: object) -> None:
    if not isinstance(ranked_candidate, RankedCandidate):
        raise ApprovalError("ranked_candidate must be a RankedCandidate")
    if not isinstance(ranked_candidate.candidate, ProductCandidateSnapshot):
        raise ApprovalError("ranked candidate must contain a ProductCandidateSnapshot")
    if not isinstance(ranked_candidate.score, WinningProductScore):
        raise ApprovalError("ranked candidate must contain a WinningProductScore")
    if ranked_candidate.candidate.candidate_id != ranked_candidate.score.candidate_id:
        raise ApprovalError("ranked candidate and score identities must match")
    if ranked_candidate.candidate.platform != ranked_candidate.score.platform:
        raise ApprovalError("ranked candidate and score platforms must match")


def _validate_approval_record(record: object) -> None:
    if not isinstance(record, ApprovalRecord):
        raise ApprovalError("record must be an ApprovalRecord")
    _validate_ranked_candidate(record.ranked_candidate)
    if not isinstance(record.decision, ApprovalDecision):
        raise ApprovalError("decision must be an explicit ApprovalDecision")
    _validate_actor(record.actor)
    _validate_decided_at(record.decided_at)
    _validate_candidate_url(record.ranked_candidate.candidate.url)


def _validate_actor(actor: object) -> None:
    if not isinstance(actor, str) or not actor.strip():
        raise ApprovalError("actor must be an explicit non-empty string")
    if any(character in actor for character in ("\r", "\n", "\x00")):
        raise ApprovalError("actor must be a single-line identifier")


def _validate_decided_at(decided_at: object) -> None:
    if not isinstance(decided_at, datetime):
        raise ApprovalError("decided_at must be an explicit datetime")
    try:
        offset = decided_at.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise ApprovalError("decided_at must be timezone-aware") from exc
    if decided_at.tzinfo is None or offset is None:
        raise ApprovalError("decided_at must be timezone-aware")


def _validate_candidate_url(url: object) -> None:
    if not isinstance(url, str) or not url:
        raise ApprovalError("candidate URL must be a non-empty string")
    if url != url.strip() or any(character.isspace() for character in url):
        raise ApprovalError("candidate URL must not contain whitespace")
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise ApprovalError("candidate URL must not contain control characters")

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ApprovalError("candidate URL is malformed") from exc

    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise ApprovalError("candidate URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ApprovalError("candidate URL must not contain credentials")
    if port is not None and not 1 <= port <= 65535:
        raise ApprovalError("candidate URL port is invalid")


def _validate_queue_paths(
    tasks_file: PathLike,
    completed_file: PathLike,
) -> tuple[Path, Path]:
    try:
        tasks_path = Path(tasks_file)
        completed_path = Path(completed_file)
        resolved_tasks = tasks_path.resolve(strict=False)
        resolved_completed = completed_path.resolve(strict=False)
    except (OSError, TypeError, ValueError) as exc:
        raise ApprovalError("queue paths must be valid filesystem paths") from exc

    if resolved_tasks == resolved_completed:
        raise ApprovalError("tasks_file and completed_file must be different paths")
    try:
        if (
            tasks_path.exists()
            and completed_path.exists()
            and tasks_path.samefile(completed_path)
        ):
            raise ApprovalError("tasks_file and completed_file must be different paths")
    except OSError as exc:
        raise ApprovalError("queue paths must be valid filesystem paths") from exc
    return tasks_path, completed_path


def _read_queue_tasks(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8") as queue:
        return {
            stripped
            for line in queue
            if (stripped := line.strip()) and not stripped.startswith("#")
        }


def _needs_line_separator(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("rb") as queue:
        queue.seek(-1, os.SEEK_END)
        return queue.read(1) not in {b"\n", b"\r"}


# Clear aliases for callers that name the operation by its queue destination.
build_approved_ingestion_task = build_ingestion_task
enqueue_approved_candidate = enqueue_approval


__all__ = [
    "INGESTION_TASK_PREFIX",
    "ApprovalDecision",
    "ApprovalError",
    "ApprovalRecord",
    "EnqueueOutcome",
    "EnqueueResult",
    "build_approved_ingestion_task",
    "build_ingestion_task",
    "create_approval_record",
    "enqueue_approval",
    "enqueue_approved_candidate",
]
