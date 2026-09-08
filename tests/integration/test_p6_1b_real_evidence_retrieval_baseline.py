"""Offline deterministic P6.1b real-evidence benchmark integration test.

Verifies the frozen Shopee benchmark corpus, durable intake and admission into
disposable SQLite, profile projection, and exact equality of TASK-164 lexical
retrieval metrics and citation fidelities against benchmark.json.
"""

from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import pytest

from src.product_source.models import ProductSourcePack
from src.product_intelligence.canonical_catalog_sqlite import (
    create_sqlite_canonical_catalog,
    load_sqlite_canonical_catalog,
)
from src.product_intelligence.canonical_profile import (
    build_canonical_variant_profile,
)
from src.product_intelligence.canonical_rag_context import (
    build_canonical_rag_context,
)
from src.product_intelligence.entity_resolution import SourceObservationIdentity
from src.product_intelligence.family_decision_admission import (
    durably_admit_planned_family,
    record_planned_family_decision,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision,
)
from src.product_intelligence.family_review_planning import (
    plan_family_knowledge_review,
)
from src.product_intelligence.grounded_answer import (
    GroundedAnswerStatus,
)
from src.product_intelligence.grounded_qa import (
    answer_grounded_context,
)
from src.product_intelligence.retrieval_quality_evaluation import (
    RetrievalBenchmarkCase,
    evaluate_grounded_answer_citation_fidelity,
    evaluate_lexical_retrieval_quality,
)
from src.product_intelligence.sellable_variant_approval import (
    SellableVariantDecision,
)
from src.product_intelligence.sellable_variant_review_admission import (
    durably_admit_reviewed_sellable_variant,
    prepare_sellable_variant_review,
    record_reviewed_sellable_variant_decision,
)
from src.product_intelligence.source_evidence_intake import (
    intake_product_source_evidence,
)
from src.providers.base import LLMProvider, LLMResponse

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FIXTURES_ROOT = _REPO_ROOT / "tests" / "fixtures" / "p6_1b_real_evidence"
_BENCHMARK_FILE = _FIXTURES_ROOT / "benchmark.json"

_ACTOR = "p6-benchmark"
_FIXED_TIMESTAMP = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)


class _DeterministicZeroNetworkProvider(LLMProvider):
    def __init__(self, *, has_hits: bool) -> None:
        self._has_hits = bool(has_hits)
        self.generate_calls = 0

    @property
    def has_hits(self) -> bool:
        return self._has_hits

    async def generate(self, messages, tools) -> LLMResponse:
        self.generate_calls += 1
        if self._has_hits:
            content = json.dumps(
                {
                    "status": "ANSWERED",
                    "answer_text": "The persisted context contains Shopee evidence.",
                    "citation_ids": ["H001-W001"],
                    "limitations": [],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        else:
            content = json.dumps(
                {
                    "status": "INSUFFICIENT_EVIDENCE",
                    "answer_text": "Insufficient evidence to answer.",
                    "citation_ids": [],
                    "limitations": ["No relevant variant evidence was retrieved."],
                },
                sort_keys=True,
                separators=(",", ":"),
            )

        return LLMResponse(
            provider="p6-1b-zero-network",
            provider_response_id=f"p6-1b-resp-{self.generate_calls:03d}",
            content=content,
        )


def _load_benchmark_descriptor() -> dict:
    assert _BENCHMARK_FILE.is_file()
    raw = _BENCHMARK_FILE.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    return json.loads(raw)


def test_benchmark_descriptor_schema_and_cases():
    doc = _load_benchmark_descriptor()
    assert doc["schema"] == "p6_1b_real_evidence_benchmark"
    assert doc["version"] == 1
    assert doc["metadata"]["benchmark_name"] == "p6_1b_real_evidence_retrieval_baseline"
    assert doc["metadata"]["cohort_count"] == 3
    assert doc["metadata"]["observation_count"] == 6
    assert doc["metadata"]["limit"] == 3

    cases = doc["cases"]
    assert len(cases) == 4
    assert [c["case_id"] for c in cases] == [
        "p6-1b-001",
        "p6-1b-002",
        "p6-1b-003",
        "p6-1b-004",
    ]
    assert cases[0]["retrieval_query"] == "bình giữ nhiệt inox"
    assert cases[0]["relevant_variant_ids"] == ["p6-benchmark-variant-001"]
    assert cases[1]["retrieval_query"] == "bàn phím cơ"
    assert cases[1]["relevant_variant_ids"] == ["p6-benchmark-variant-002"]
    assert cases[2]["retrieval_query"] == "chuột không dây"
    assert cases[2]["relevant_variant_ids"] == ["p6-benchmark-variant-003"]
    assert cases[3]["retrieval_query"] == "shopee"
    assert cases[3]["relevant_variant_ids"] == [
        "p6-benchmark-variant-001",
        "p6-benchmark-variant-002",
        "p6-benchmark-variant-003",
    ]


@pytest.mark.asyncio
async def test_offline_real_evidence_retrieval_baseline_exact_equality(tmp_path: Path):
    doc = _load_benchmark_descriptor()
    baseline = doc["baseline_snapshot"]

    db_path = tmp_path / "p6_1b_test_catalog.sqlite"
    create_sqlite_canonical_catalog(db_path)

    all_identities: list[SourceObservationIdentity] = []
    cohort_packs: dict[int, tuple[ProductSourcePack, ...]] = {}

    # Phase 1: Single-pass intake per cohort root and durable admission into disposable SQLite
    for cohort in doc["cohorts"]:
        cid = cohort["cohort_id"]
        cohort_root = _REPO_ROOT / cohort["case_dir"]
        inventory = intake_product_source_evidence((str(cohort_root),))
        assert len(inventory.manifest_paths) == 2
        assert len(inventory.source_packs) == 2

        for pack in inventory.source_packs:
            assert isinstance(pack, ProductSourcePack)
            assert pack.platform == "shopee"
            assert pack.source_product_id == cohort["source_product_id"]
            identity = SourceObservationIdentity.from_pack(pack)
            assert identity.platform == "shopee"
            assert identity.source_product_id == cohort["source_product_id"]
            all_identities.append(identity)

        cohort_packs[cid] = inventory.source_packs

        # Family review planning and admission
        plan = plan_family_knowledge_review(inventory)
        assert len(plan.proposals) == 1
        fam_decision = record_planned_family_decision(
            plan,
            plan.proposals[0],
            decision=FamilyMergeDecision.APPROVE,
            actor=_ACTOR,
            decided_at=_FIXED_TIMESTAMP,
        )
        fam_admission = durably_admit_planned_family(
            plan,
            fam_decision,
            family_id=f"p6-benchmark-family-{cid:03d}",
            database_path=db_path,
        )
        assert len(fam_admission.family.members) == 2

        # Variant review preparation (complete selection) and admission
        var_review = prepare_sellable_variant_review(
            fam_admission.family,
            fam_admission.family.members,
        )
        var_decision = record_reviewed_sellable_variant_decision(
            var_review,
            decision=SellableVariantDecision.APPROVE,
            actor=_ACTOR,
            decided_at=_FIXED_TIMESTAMP,
        )
        var_admission = durably_admit_reviewed_sellable_variant(
            var_review,
            var_decision,
            variant_id=f"p6-benchmark-variant-{cid:03d}",
            database_path=db_path,
        )
        assert var_admission.variant.variant_id == f"p6-benchmark-variant-{cid:03d}"

    assert len(all_identities) == 6
    assert len(set(all_identities)) == 6, "All six observations must have pairwise distinct identities"

    # Phase 2: Catalog reload and canonical profile construction
    catalog = load_sqlite_canonical_catalog(db_path)
    assert len(catalog.variants) == 3

    profiles = []
    for v in catalog.variants:
        cid = int(v.variant_id.split("-")[-1])
        prof = build_canonical_variant_profile(
            catalog,
            variant_id=v.variant_id,
            source_packs=cohort_packs[cid],
        )
        profiles.append(prof)
    assert len(profiles) == 3

    # Phase 3: Lexical retrieval quality evaluation
    benchmark_cases = tuple(
        RetrievalBenchmarkCase(
            case_id=c["case_id"],
            question=c["question"],
            retrieval_query=c["retrieval_query"],
            relevant_variant_ids=tuple(c["relevant_variant_ids"]),
        )
        for c in doc["cases"]
    )

    lexical_report = evaluate_lexical_retrieval_quality(
        profiles,
        benchmark_cases,
        limit=3,
    )

    # Verify lexical report aggregates
    assert lexical_report.limit == baseline["evaluator_limit"]
    assert len(lexical_report.case_evaluations) == baseline["total_cases"]
    assert lexical_report.true_positive_count == baseline["aggregate_true_positive_count"]
    assert lexical_report.false_positive_count == baseline["aggregate_false_positive_count"]
    assert lexical_report.false_negative_count == baseline["aggregate_false_negative_count"]
    assert lexical_report.micro_precision == Fraction(*baseline["micro_precision"])
    assert lexical_report.micro_recall == Fraction(*baseline["micro_recall"])

    # Phase 4: Grounded context, deterministic QA, citation fidelity
    for ce, expected_ce in zip(lexical_report.case_evaluations, baseline["case_evaluations"]):
        assert ce.case.case_id == expected_ce["case_id"]
        assert [h.profile.variant_id for h in ce.hits] == expected_ce["retrieved_variant_ids"]
        assert list(ce.true_positive_variant_ids) == expected_ce["true_positive_variant_ids"]
        assert list(ce.false_positive_variant_ids) == expected_ce["false_positive_variant_ids"]
        assert list(ce.false_negative_variant_ids) == expected_ce["false_negative_variant_ids"]
        assert ce.precision == Fraction(*expected_ce["precision"])
        assert ce.recall == Fraction(*expected_ce["recall"])

        rag_ctx = build_canonical_rag_context(
            profiles,
            question=ce.case.question,
            retrieval_query=ce.case.retrieval_query,
            max_hits=3,
        )

        provider = _DeterministicZeroNetworkProvider(has_hits=bool(rag_ctx.hits))

        grounded_answer = await answer_grounded_context(
            rag_ctx,
            provider=provider,
        )

        fidelity_obj = evaluate_grounded_answer_citation_fidelity(
            ce,
            grounded_answer,
        )

        if expected_ce["citation_fidelity"] is None:
            assert fidelity_obj.fidelity is None
            assert grounded_answer.status == GroundedAnswerStatus.INSUFFICIENT_EVIDENCE
            assert len(grounded_answer.citation_ids) == 0
        else:
            assert fidelity_obj.fidelity == Fraction(*expected_ce["citation_fidelity"])
            assert grounded_answer.status == GroundedAnswerStatus.ANSWERED
            assert grounded_answer.citation_ids == ("H001-W001",)
