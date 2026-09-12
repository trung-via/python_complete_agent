"""TASK-191 offline replay of the Human-accepted P7.1 real-evidence discovery cohort.

The committed discovery_capture_bundle.json and baseline.json are immutable
Human-reviewed benchmark inputs. This test composes published TASK-181 evaluator
authority only; it defines no production capture, identity, scoring, ranking,
approval, persistence, or benchmark-label behavior.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from src.product_intelligence.discovery import DiscoveryBatch
from src.product_intelligence.models import ProductCandidateSnapshot
import src.product_intelligence.winning_product_quality_evaluation as evaluation_module

_FIXTURE_DIR = (
    Path(__file__).parents[1]
    / "fixtures"
    / "p7_1_winning_product_coverage"
)
_BUNDLE_PATH = _FIXTURE_DIR / "discovery_capture_bundle.json"
_BASELINE_PATH = _FIXTURE_DIR / "baseline.json"

_ACCEPTED_BUNDLE_SHA256 = (
    "aba1cdbc0a74d591a7da6c6dce11b9ae06bb7c16b0fe151490bb74da3efc465a"
)
_ACCEPTED_BUNDLE_BYTE_COUNT = 16047
_EXPECTED_EVALUATED_AT_ISO = "2026-09-12T12:06:33.110964+00:00"

_QUERIES = (
    "bình giữ nhiệt inox",
    "bàn phím cơ",
    "chuột không dây",
)
_BATCH_KEYS = {
    "platform",
    "query",
    "observed_at",
    "candidate_count",
    "candidates",
    "pages_examined",
    "raw_items_seen",
    "diagnostic_codes",
}
_CANDIDATE_KEYS = {field.name for field in fields(ProductCandidateSnapshot)}


def _load_bundle() -> tuple[dict[str, object], bytes]:
    payload = _BUNDLE_PATH.read_bytes()
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert len(payload) == _ACCEPTED_BUNDLE_BYTE_COUNT
    assert hashlib.sha256(payload).hexdigest() == _ACCEPTED_BUNDLE_SHA256
    document = json.loads(payload.decode("utf-8"))
    return document, payload


def _load_baseline() -> tuple[dict[str, object], bytes]:
    payload = _BASELINE_PATH.read_bytes()
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert payload.endswith(b"\n")
    assert not payload.endswith(b"\n\n")
    document = json.loads(payload.decode("utf-8"))
    deterministic_payload = (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert payload == deterministic_payload
    return document, payload


def _candidate_from_projection(
    projection: dict[str, object],
) -> ProductCandidateSnapshot:
    assert set(projection) == _CANDIDATE_KEYS
    values = dict(projection)
    assert isinstance(values["observed_at"], str)
    values["observed_at"] = datetime.fromisoformat(values["observed_at"])
    candidate = ProductCandidateSnapshot(**values)
    assert candidate.to_dict() == projection
    return candidate


def _batch_from_projection(
    batch_projection: dict[str, object],
    candidates: tuple[ProductCandidateSnapshot, ...],
) -> DiscoveryBatch:
    assert set(batch_projection) == _BATCH_KEYS
    assert isinstance(batch_projection["observed_at"], str)
    batch = DiscoveryBatch(
        platform=batch_projection["platform"],
        query=batch_projection["query"],
        observed_at=datetime.fromisoformat(batch_projection["observed_at"]),
        candidates=candidates,
        pages_examined=batch_projection["pages_examined"],
        raw_items_seen=batch_projection["raw_items_seen"],
        diagnostic_codes=tuple(batch_projection.get("diagnostic_codes", ())),
    )
    assert batch.to_dict() == batch_projection
    return batch


def _project_report(
    report: evaluation_module.WinningProductCoverageReport,
) -> dict[str, object]:
    return {
        "evaluated_at": report.evaluated_at.isoformat(),
        "candidate_evaluations": [
            {
                "candidate_id": entry.candidate.candidate_id,
                "score": entry.score.to_dict(),
                "zero_coverage_categories": [
                    category.value for category in entry.zero_coverage_categories
                ],
                "partial_coverage_categories": [
                    category.value for category in entry.partial_coverage_categories
                ],
                "full_coverage_categories": [
                    category.value for category in entry.full_coverage_categories
                ],
                "missing_factual_signal_names": list(
                    entry.missing_factual_signal_names
                ),
            }
            for entry in report.candidate_evaluations
        ],
        "zero_coverage_counts_by_category": [
            [category.value, count]
            for category, count in report.zero_coverage_counts_by_category
        ],
        "partial_coverage_counts_by_category": [
            [category.value, count]
            for category, count in report.partial_coverage_counts_by_category
        ],
        "full_coverage_counts_by_category": [
            [category.value, count]
            for category, count in report.full_coverage_counts_by_category
        ],
        "decision_band_counts": [
            [band.value, count] for band, count in report.decision_band_counts
        ],
    }


def _reconstruct_cohort_and_batches(
    bundle: dict[str, object],
) -> tuple[tuple[ProductCandidateSnapshot, ...], tuple[DiscoveryBatch, ...], datetime]:
    assert set(bundle) == {"batches", "queries", "schema", "version"}
    assert bundle["schema"] == "product_intelligence_discovery_capture_bundle"
    assert bundle["version"] == 1
    assert bundle["queries"] == list(_QUERIES)

    batches_raw = bundle["batches"]
    assert isinstance(batches_raw, list)
    assert len(batches_raw) == 3

    cohort: list[ProductCandidateSnapshot] = []
    reconstructed_batches: list[DiscoveryBatch] = []
    batch_observed_at: list[datetime] = []
    all_candidate_ids: list[str] = []
    all_candidate_urls: list[str] = []

    for expected_query, batch_dict in zip(_QUERIES, batches_raw, strict=True):
        assert isinstance(batch_dict, dict)
        assert set(batch_dict) == _BATCH_KEYS
        assert batch_dict["platform"] == "shopee"
        assert batch_dict["query"] == expected_query
        assert batch_dict["pages_examined"] == 1
        assert batch_dict["candidate_count"] == 5
        assert isinstance(batch_dict["observed_at"], str)

        observed_at = datetime.fromisoformat(batch_dict["observed_at"])
        assert observed_at.tzinfo is not None and observed_at.utcoffset() is not None
        batch_observed_at.append(observed_at)

        candidates_raw = batch_dict["candidates"]
        assert isinstance(candidates_raw, list)
        assert len(candidates_raw) == 5

        batch_candidates = tuple(
            _candidate_from_projection(cand_dict) for cand_dict in candidates_raw
        )
        assert all(cand.platform == "shopee" for cand in batch_candidates)
        assert all(cand.observed_at == observed_at for cand in batch_candidates)

        batch_ids = [cand.candidate_id for cand in batch_candidates]
        assert len(batch_ids) == len(set(batch_ids)) == 5
        cohort.extend(batch_candidates)
        all_candidate_ids.extend(batch_ids)
        all_candidate_urls.extend(cand.url for cand in batch_candidates)

        reconstructed_batch = _batch_from_projection(batch_dict, batch_candidates)
        reconstructed_batches.append(reconstructed_batch)

    assert len(cohort) == 15
    assert len(all_candidate_ids) == len(set(all_candidate_ids)) == 15
    assert len(all_candidate_urls) == len(set(all_candidate_urls)) == 15

    evaluated_at = max(batch_observed_at)
    assert evaluated_at.isoformat() == _EXPECTED_EVALUATED_AT_ISO

    return tuple(cohort), tuple(reconstructed_batches), evaluated_at


def test_frozen_discovery_bundle_integrity_and_provenance() -> None:
    bundle, raw_bytes = _load_bundle()
    assert len(raw_bytes) == _ACCEPTED_BUNDLE_BYTE_COUNT
    assert hashlib.sha256(raw_bytes).hexdigest() == _ACCEPTED_BUNDLE_SHA256
    assert set(bundle) == {"batches", "queries", "schema", "version"}
    assert bundle["schema"] == "product_intelligence_discovery_capture_bundle"
    assert bundle["version"] == 1
    assert bundle["queries"] == list(_QUERIES)


def test_offline_reconstruction_and_methodology_validation() -> None:
    bundle, _ = _load_bundle()
    cohort, reconstructed_batches, evaluated_at = _reconstruct_cohort_and_batches(
        bundle
    )
    assert len(cohort) == 15
    assert len(reconstructed_batches) == 3
    assert evaluated_at.isoformat() == _EXPECTED_EVALUATED_AT_ISO


def test_frozen_real_evidence_baseline_replays_exactly_offline() -> None:
    bundle, _ = _load_bundle()
    cohort, _, evaluated_at = _reconstruct_cohort_and_batches(bundle)

    baseline, baseline_bytes = _load_baseline()
    assert set(baseline) == {
        "schema",
        "version",
        "source",
        "evaluated_at",
        "report",
    }
    assert baseline["schema"] == "p7_1_winning_product_coverage_baseline"
    assert baseline["version"] == 1
    assert baseline["source"] == {
        "fixture": "discovery_capture_bundle.json",
        "sha256": _ACCEPTED_BUNDLE_SHA256,
        "byte_count": _ACCEPTED_BUNDLE_BYTE_COUNT,
        "capture_task": "TASK-190",
        "capture_source_sha": "22d8837e5955ed78185426f293e874625a34d469",
        "human_review": "ACCEPTED",
    }
    assert baseline["evaluated_at"] == evaluated_at.isoformat()

    with patch.object(
        evaluation_module,
        "evaluate_winning_product_coverage",
        wraps=evaluation_module.evaluate_winning_product_coverage,
    ) as evaluator:
        report = evaluation_module.evaluate_winning_product_coverage(
            cohort,
            evaluated_at=evaluated_at,
            policy=None,
        )

    evaluator.assert_called_once_with(
        cohort,
        evaluated_at=evaluated_at,
        policy=None,
    )

    projected_report = _project_report(report)
    assert projected_report == baseline["report"]

    reproduced_doc = {
        "schema": baseline["schema"],
        "version": baseline["version"],
        "source": baseline["source"],
        "evaluated_at": baseline["evaluated_at"],
        "report": projected_report,
    }
    reproduced_bytes = (
        json.dumps(
            reproduced_doc,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert reproduced_bytes == baseline_bytes
