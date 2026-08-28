from __future__ import annotations

import os
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.product_intelligence.approval import (
    ApprovalDecision,
    ApprovalError,
    EnqueueOutcome,
    build_ingestion_task,
    create_approval_record,
    enqueue_approval,
)
from src.product_intelligence.models import DecisionBand, ProductCandidateSnapshot
from src.product_intelligence.ranking import RankedCandidate
from src.product_intelligence.scoring import WinningProductScorer


DECIDED_AT = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)
URL = "https://shopee.vn/canonical-product-i.123.456"
TASK = f"Scrape product images from {URL}"


def _ranked_candidate(
    *,
    url: str = URL,
    decision_band: DecisionBand | None = None,
) -> RankedCandidate:
    candidate = ProductCandidateSnapshot(
        candidate_id="shopee:123:456",
        platform="shopee",
        url=url,
        observed_at=DECIDED_AT,
        title="Canonical product",
        sold_count=50_000,
        review_count=5_000,
        rating=4.9,
        affiliate_commission_rate=20.0,
        discount_percent=40.0,
        sales_velocity=100.0,
        creator_velocity=10.0,
        creator_count=1,
        similar_listing_count=1,
    )
    score = WinningProductScorer.score_snapshot(candidate, evaluated_at=DECIDED_AT)
    if decision_band is not None:
        score = replace(score, decision_band=decision_band)
    return RankedCandidate(candidate=candidate, score=score)


def _record(
    decision: ApprovalDecision = ApprovalDecision.APPROVE,
    *,
    ranked: RankedCandidate | None = None,
):
    return create_approval_record(
        ranked or _ranked_candidate(),
        decision=decision,
        actor="operator@example.com",
        decided_at=DECIDED_AT,
    )


@pytest.mark.parametrize(
    "decision", [ApprovalDecision.APPROVE, ApprovalDecision.REJECT]
)
def test_explicit_decisions_create_frozen_records_preserving_exact_identity(
    decision: ApprovalDecision,
) -> None:
    ranked = _ranked_candidate()

    record = create_approval_record(
        ranked,
        decision=decision,
        actor="operator-42",
        decided_at=DECIDED_AT,
    )

    assert record.ranked_candidate is ranked
    assert record.candidate is ranked.candidate
    assert record.score is ranked.score
    assert record.decision is decision
    assert record.actor == "operator-42"
    assert record.decided_at is DECIDED_AT
    with pytest.raises(FrozenInstanceError):
        record.actor = "different-actor"  # type: ignore[misc]


@pytest.mark.parametrize("band", [DecisionBand.RECOMMENDED, DecisionBand.NEEDS_REVIEW])
def test_advisory_score_band_has_no_approval_or_queue_authority(
    tmp_path: Path,
    band: DecisionBand,
) -> None:
    ranked = _ranked_candidate(decision_band=band)
    tasks = tmp_path / "tasks.txt"
    completed = tmp_path / "completed.txt"

    assert ranked.score.decision_band is band
    assert not tasks.exists()
    assert not completed.exists()

    rejected = _record(ApprovalDecision.REJECT, ranked=ranked)
    with pytest.raises(ApprovalError, match="explicit APPROVE"):
        build_ingestion_task(rejected)
    with pytest.raises(ApprovalError, match="explicit APPROVE"):
        enqueue_approval(rejected, tasks_file=tasks, completed_file=completed)

    assert not tasks.exists()
    assert not completed.exists()


def test_approved_record_builds_deterministic_canonical_task() -> None:
    record = _record()

    first = build_ingestion_task(record)
    second = build_ingestion_task(record)

    assert first == TASK
    assert second == first
    assert URL in first
    assert "\r" not in first and "\n" not in first


def test_first_enqueue_appends_one_utf8_line_and_flushes_before_fsync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks = tmp_path / "tasks.txt"
    completed = tmp_path / "completed.txt"
    observations: list[bytes] = []

    def observe_fsync(file_descriptor: int) -> None:
        assert file_descriptor >= 0
        observations.append(tasks.read_bytes())

    monkeypatch.setattr(os, "fsync", observe_fsync)

    result = enqueue_approval(
        _record(), tasks_file=tasks, completed_file=completed
    )

    assert result.outcome is EnqueueOutcome.ENQUEUED
    assert result.appended is True
    assert result.enqueued is True
    assert result.task == TASK
    assert tasks.read_bytes() == f"{TASK}\n".encode("utf-8")
    assert observations == [f"{TASK}\n".encode("utf-8")]
    assert not completed.exists()


def test_existing_queued_task_is_explicit_idempotent_noop(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks.txt"
    completed = tmp_path / "completed.txt"
    initial = f"# retained comment\n\n{TASK}\n"
    tasks.write_text(initial, encoding="utf-8")

    result = enqueue_approval(_record(), tasks_file=tasks, completed_file=completed)

    assert result.outcome is EnqueueOutcome.ALREADY_QUEUED
    assert result.appended is False
    assert tasks.read_text(encoding="utf-8") == initial
    assert not completed.exists()


def test_completed_task_is_explicit_noop_and_completed_file_is_never_modified(
    tmp_path: Path,
) -> None:
    tasks = tmp_path / "tasks.txt"
    completed = tmp_path / "completed.txt"
    tasks.write_text("# queue stays unchanged\n", encoding="utf-8")
    initial_completed = f"# completion record\n{TASK}\n"
    completed.write_text(initial_completed, encoding="utf-8")

    result = enqueue_approval(_record(), tasks_file=tasks, completed_file=completed)

    assert result.outcome is EnqueueOutcome.ALREADY_COMPLETED
    assert result.appended is False
    assert tasks.read_text(encoding="utf-8") == "# queue stays unchanged\n"
    assert completed.read_text(encoding="utf-8") == initial_completed


def test_append_keeps_existing_unterminated_task_as_a_separate_line(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks.txt"
    completed = tmp_path / "completed.txt"
    tasks.write_text("existing task", encoding="utf-8")

    result = enqueue_approval(_record(), tasks_file=tasks, completed_file=completed)

    assert result.outcome is EnqueueOutcome.ENQUEUED
    assert tasks.read_text(encoding="utf-8").splitlines() == ["existing task", TASK]


@pytest.mark.parametrize("actor", ["", "   ", "operator\nother", None])
def test_invalid_actor_fails_without_queue_mutation(
    tmp_path: Path,
    actor: object,
) -> None:
    tasks = tmp_path / "tasks.txt"
    completed = tmp_path / "completed.txt"

    with pytest.raises(ApprovalError, match="actor"):
        create_approval_record(
            _ranked_candidate(),
            decision=ApprovalDecision.APPROVE,
            actor=actor,  # type: ignore[arg-type]
            decided_at=DECIDED_AT,
        )

    assert not tasks.exists()
    assert not completed.exists()


@pytest.mark.parametrize("decided_at", [None, datetime(2026, 8, 28, 15, 0)])
def test_missing_or_naive_timestamp_fails_without_queue_mutation(
    tmp_path: Path,
    decided_at: object,
) -> None:
    tasks = tmp_path / "tasks.txt"

    with pytest.raises(ApprovalError, match="decided_at"):
        create_approval_record(
            _ranked_candidate(),
            decision=ApprovalDecision.APPROVE,
            actor="operator",
            decided_at=decided_at,  # type: ignore[arg-type]
        )

    assert not tasks.exists()


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "ftp://shopee.vn/item",
        "https:///missing-host",
        "https://user:password@shopee.vn/item",
        "https://shopee.vn/item\nsecond-task",
        " https://shopee.vn/item",
    ],
)
def test_malformed_url_fails_before_any_queue_write(tmp_path: Path, url: str) -> None:
    tasks = tmp_path / "tasks.txt"
    tasks.write_text("original\n", encoding="utf-8")

    with pytest.raises(ApprovalError, match="URL"):
        _record(ranked=_ranked_candidate(url=url))

    assert tasks.read_text(encoding="utf-8") == "original\n"
    assert not (tmp_path / "completed.txt").exists()


def test_non_decision_and_non_ranked_inputs_fail_closed() -> None:
    ranked = _ranked_candidate()

    with pytest.raises(ApprovalError, match="decision"):
        create_approval_record(
            ranked,
            decision="APPROVE",  # type: ignore[arg-type]
            actor="operator",
            decided_at=DECIDED_AT,
        )
    with pytest.raises(ApprovalError, match="RankedCandidate"):
        create_approval_record(
            ranked.candidate,  # type: ignore[arg-type]
            decision=ApprovalDecision.APPROVE,
            actor="operator",
            decided_at=DECIDED_AT,
        )


def test_reject_and_invalid_same_queue_paths_leave_existing_file_unchanged(
    tmp_path: Path,
) -> None:
    queue = tmp_path / "queue.txt"
    queue.write_text("original\n", encoding="utf-8")

    with pytest.raises(ApprovalError, match="explicit APPROVE"):
        enqueue_approval(
            _record(ApprovalDecision.REJECT),
            tasks_file=queue,
            completed_file=queue,
        )
    assert queue.read_text(encoding="utf-8") == "original\n"

    with pytest.raises(ApprovalError, match="different paths"):
        enqueue_approval(_record(), tasks_file=queue, completed_file=queue)
    assert queue.read_text(encoding="utf-8") == "original\n"
