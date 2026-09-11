from __future__ import annotations

import json
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import src.product_intelligence.winning_product_quality_evaluation as evaluation_module
from src.product_intelligence.models import ProductCandidateSnapshot


_FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "p7_1_winning_product_coverage"
    / "baseline.json"
)
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


def _load_fixture() -> dict[str, object]:
    payload = _FIXTURE_PATH.read_bytes()
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
    return document


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


def _project_report(report: object) -> dict[str, object]:
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


def test_frozen_real_evidence_baseline_replays_exactly_offline() -> None:
    document = _load_fixture()
    assert set(document) == {
        "schema",
        "version",
        "methodology",
        "batches",
        "evaluated_at",
        "report",
    }
    assert document["schema"] == "p7_1_winning_product_coverage_baseline"
    assert document["version"] == 1
    assert document["methodology"] == {
        "platform": "shopee",
        "discovery_authority": "ShopeeDiscoveryAdapter",
        "candidate_projection": "DiscoveryBatch.to_dict",
        "evaluation_authority": "evaluate_winning_product_coverage",
        "policy": None,
        "query_order": list(_QUERIES),
        "request": {
            "max_candidates": 5,
            "max_pages": 1,
            "locale": "vi-VN",
        },
        "selection": "bounded_search_card_order_without_score_or_ranker_selection",
        "source_candidate": "9e835ed2c551c2fa3a8b66b82caa238bd41b152c",
    }

    batches = document["batches"]
    assert isinstance(batches, list)
    assert len(batches) == 3
    cohort: list[ProductCandidateSnapshot] = []
    batch_observed_at: list[datetime] = []
    all_candidate_ids: list[str] = []
    all_candidate_urls: list[str] = []

    for expected_query, batch in zip(_QUERIES, batches, strict=True):
        assert isinstance(batch, dict)
        assert set(batch) == _BATCH_KEYS
        assert batch["platform"] == "shopee"
        assert batch["query"] == expected_query
        assert batch["pages_examined"] == 1
        assert batch["candidate_count"] == 5
        assert isinstance(batch["observed_at"], str)
        observed_at = datetime.fromisoformat(batch["observed_at"])
        assert observed_at.tzinfo is not None
        batch_observed_at.append(observed_at)

        projections = batch["candidates"]
        assert isinstance(projections, list)
        assert len(projections) == 5
        reconstructed = tuple(
            _candidate_from_projection(projection) for projection in projections
        )
        assert all(candidate.platform == "shopee" for candidate in reconstructed)
        assert all(candidate.observed_at == observed_at for candidate in reconstructed)
        batch_ids = [candidate.candidate_id for candidate in reconstructed]
        assert len(batch_ids) == len(set(batch_ids))
        cohort.extend(reconstructed)
        all_candidate_ids.extend(batch_ids)
        all_candidate_urls.extend(candidate.url for candidate in reconstructed)

    assert len(cohort) == 15
    assert len(all_candidate_ids) == len(set(all_candidate_ids)) == 15
    assert len(all_candidate_urls) == len(set(all_candidate_urls)) == 15
    evaluated_at = max(batch_observed_at)
    assert document["evaluated_at"] == evaluated_at.isoformat()

    with patch.object(
        evaluation_module,
        "evaluate_winning_product_coverage",
        wraps=evaluation_module.evaluate_winning_product_coverage,
    ) as evaluator:
        report = evaluation_module.evaluate_winning_product_coverage(
            tuple(cohort),
            evaluated_at=evaluated_at,
            policy=None,
        )

    evaluator.assert_called_once_with(
        tuple(cohort),
        evaluated_at=evaluated_at,
        policy=None,
    )
    assert _project_report(report) == document["report"]
