"""TASK-168 offline replay of the accepted P6.1b real-evidence corpus.

The committed fixtures are immutable Human-reviewed benchmark input.  This test
composes published authorities only; it defines no production capture, identity,
retrieval, persistence, or benchmark-label behavior.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from src.product_intelligence.canonical_catalog import CatalogRegistrationStatus
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
    FamilyMergeProposal,
)
from src.product_intelligence.family_review_planning import (
    plan_family_knowledge_review,
)
from src.product_intelligence.grounded_qa import answer_grounded_context
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


_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "p6_1b_real_evidence"
)
_BENCHMARK_PATH = _FIXTURE_ROOT / "benchmark.json"
_ACTOR = "p6-benchmark"
_DECIDED_AT = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
_LIMIT = 3
_VARIANT_IDS = tuple(
    f"p6-benchmark-variant-{cohort:03d}-{member:03d}"
    for cohort in range(1, 4)
    for member in range(1, 3)
)
_FIXTURE_TARGETS = tuple(
    f"case-{cohort:03d}/observation-{observation:03d}/source_pack.json"
    for cohort in range(1, 4)
    for observation in range(1, 3)
)
_CASE_RECORDS = (
    {
        "case_id": "p6-1b-001",
        "question": (
            "Which frozen benchmark variants match the Human intent "
            "bình giữ nhiệt inox?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[0:2]),
        "retrieval_query": "bình giữ nhiệt inox",
    },
    {
        "case_id": "p6-1b-002",
        "question": (
            "Which frozen benchmark variants match the Human intent bàn phím cơ?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[2:4]),
        "retrieval_query": "bàn phím cơ",
    },
    {
        "case_id": "p6-1b-003",
        "question": (
            "Which frozen benchmark variants match the Human intent chuột không dây?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[4:6]),
        "retrieval_query": "chuột không dây",
    },
    {
        "case_id": "p6-1b-004",
        "question": "Which frozen benchmark variants contain persisted Shopee evidence?",
        "relevant_variant_ids": list(_VARIANT_IDS),
        "retrieval_query": "shopee",
    },
)


class _BooleanOnlyProvider(LLMProvider):
    """Zero-network provider whose sole branch input is an explicit boolean."""

    def __init__(self, *, has_hits: bool) -> None:
        assert type(has_hits) is bool
        self._has_hits = has_hits
        self.generate_calls = 0

    async def generate(self, messages, tools) -> LLMResponse:
        self.generate_calls += 1
        if self._has_hits:
            payload = {
                "answer_text": "The frozen benchmark context contains retrieval evidence.",
                "citation_ids": ["H001-W001"],
                "limitations": [],
                "status": "ANSWERED",
            }
        else:
            payload = {
                "answer_text": "No frozen benchmark evidence was retrieved.",
                "citation_ids": [],
                "limitations": ["No benchmark retrieval hits."],
                "status": "INSUFFICIENT_EVIDENCE",
            }
        return LLMResponse(
            provider="task-168-zero-network",
            provider_response_id="task-168-deterministic-response",
            content=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_and_verify_descriptor() -> dict:
    raw = _BENCHMARK_PATH.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    descriptor = json.loads(raw.decode("utf-8"))
    expected = (
        json.dumps(
            descriptor,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert raw == expected
    assert descriptor["schema"] == "p6_1b_real_evidence_benchmark"
    assert descriptor["version"] == 2
    assert descriptor["evaluator_limit"] == _LIMIT
    assert descriptor["cases"] == list(_CASE_RECORDS)
    assert descriptor["human_decision"] == {
        "actor": _ACTOR,
        "decided_at": "2026-09-08T00:00:00+00:00",
    }
    return descriptor


def _verify_frozen_capture(descriptor: dict) -> tuple[dict, tuple[Path, ...]]:
    bundle_record = descriptor["capture_bundle"]
    assert bundle_record["fixture"] == "capture_bundle.json"
    bundle_path = _FIXTURE_ROOT / bundle_record["fixture"]
    assert bundle_path.is_file() and not bundle_path.is_symlink()
    assert _sha256(bundle_path) == bundle_record["sha256"]
    bundle = json.loads(bundle_path.read_bytes().decode("utf-8"))
    assert bundle["schema"] == "product_intelligence_live_capture_bundle"
    assert bundle["version"] == 1
    assert tuple(cohort["query"] for cohort in bundle["cohorts"]) == (
        "bình giữ nhiệt inox",
        "bàn phím cơ",
        "chuột không dây",
    )
    assert len({cohort["product_url"] for cohort in bundle["cohorts"]}) == 3

    fixture_paths = []
    descriptor_cohorts = descriptor["cohorts"]
    assert len(descriptor_cohorts) == len(bundle["cohorts"]) == 3
    for cohort_ordinal, (bundle_cohort, benchmark_cohort) in enumerate(
        zip(bundle["cohorts"], descriptor_cohorts, strict=True), start=1
    ):
        assert all(
            isinstance(bundle_cohort[field], str) and bundle_cohort[field].strip()
            for field in ("candidate_id", "title", "product_url")
        )
        assert benchmark_cohort["cohort_ordinal"] == cohort_ordinal
        assert benchmark_cohort["query"] == bundle_cohort["query"]
        assert benchmark_cohort["family_id"] == (
            f"p6-benchmark-family-{cohort_ordinal:03d}"
        )
        assert benchmark_cohort["human_accepted_candidate"] == {
            "candidate_id": bundle_cohort["candidate_id"],
            "product_url": bundle_cohort["product_url"],
            "title": bundle_cohort["title"],
        }
        expected_variant_ids = list(
            _VARIANT_IDS[(cohort_ordinal - 1) * 2 : cohort_ordinal * 2]
        )
        assert benchmark_cohort["variant_ids_in_canonical_member_order"] == (
            expected_variant_ids
        )
        assert len(bundle_cohort["observations"]) == 2
        assert len(benchmark_cohort["source_manifests"]) == 2

        for observation_ordinal, (bundle_observation, manifest_record) in enumerate(
            zip(
                bundle_cohort["observations"],
                benchmark_cohort["source_manifests"],
                strict=True,
            ),
            start=1,
        ):
            bundle_relative_path = bundle_observation["manifest_path"]
            assert isinstance(bundle_relative_path, str) and bundle_relative_path
            assert not Path(bundle_relative_path).is_absolute()
            assert not {".", ".."}.intersection(
                bundle_relative_path.replace("\\", "/").split("/")
            )
            target = _FIXTURE_TARGETS[(cohort_ordinal - 1) * 2 + observation_ordinal - 1]
            assert manifest_record == {
                "bundle_manifest_path": bundle_observation["manifest_path"],
                "fixture_target": target,
                "sha256": bundle_observation["sha256"],
            }
            fixture_path = (_FIXTURE_ROOT / target).resolve()
            assert fixture_path.is_relative_to(_FIXTURE_ROOT.resolve())
            assert fixture_path.is_file() and not fixture_path.is_symlink()
            assert _sha256(fixture_path) == bundle_observation["sha256"]
            fixture_paths.append(fixture_path)

    assert tuple(fixture_paths) == tuple(
        (_FIXTURE_ROOT / target).resolve() for target in _FIXTURE_TARGETS
    )
    return bundle, tuple(fixture_paths)


def _benchmark_cases(descriptor: dict) -> tuple[RetrievalBenchmarkCase, ...]:
    return tuple(
        RetrievalBenchmarkCase(
            case_id=case["case_id"],
            question=case["question"],
            retrieval_query=case["retrieval_query"],
            relevant_variant_ids=tuple(case["relevant_variant_ids"]),
        )
        for case in descriptor["cases"]
    )


def _fraction(value: Fraction | None) -> list[int] | None:
    if value is None:
        return None
    return [value.numerator, value.denominator]


def _snapshot(report, fidelities) -> dict:
    return {
        "aggregate": {
            "false_negative_count": report.false_negative_count,
            "false_positive_count": report.false_positive_count,
            "micro_precision": _fraction(report.micro_precision),
            "micro_recall": _fraction(report.micro_recall),
            "true_positive_count": report.true_positive_count,
        },
        "cases": [
            {
                "case_id": evaluation.case.case_id,
                "false_negative_variant_ids": list(
                    evaluation.false_negative_variant_ids
                ),
                "false_positive_variant_ids": list(
                    evaluation.false_positive_variant_ids
                ),
                "precision": _fraction(evaluation.precision),
                "recall": _fraction(evaluation.recall),
                "true_positive_variant_ids": list(
                    evaluation.true_positive_variant_ids
                ),
            }
            for evaluation in report.case_evaluations
        ],
        "citation_fidelity": [
            {
                "case_id": fidelity.case_evaluation.case.case_id,
                "fidelity": _fraction(fidelity.fidelity),
            }
            for fidelity in fidelities
        ],
    }


def _run_offline_benchmark(descriptor: dict, database_path: Path):
    trace = {
        "answer_grounded_context": 0,
        "build_canonical_rag_context": 0,
        "build_canonical_variant_profile": 0,
        "create_sqlite_canonical_catalog": 0,
        "durably_admit_planned_family": 0,
        "durably_admit_reviewed_sellable_variant": 0,
        "evaluate_grounded_answer_citation_fidelity": 0,
        "evaluate_lexical_retrieval_quality": 0,
        "intake_product_source_evidence": 0,
        "load_sqlite_canonical_catalog": 0,
        "plan_family_knowledge_review": 0,
        "prepare_sellable_variant_review": 0,
        "record_planned_family_decision": 0,
        "record_reviewed_sellable_variant_decision": 0,
    }

    trace["create_sqlite_canonical_catalog"] += 1
    empty_catalog = create_sqlite_canonical_catalog(database_path)
    assert empty_catalog.families == () and empty_catalog.variants == ()

    packs_by_identity = {}
    for cohort_ordinal, cohort in enumerate(descriptor["cohorts"], start=1):
        cohort_root = _FIXTURE_ROOT / f"case-{cohort_ordinal:03d}"
        trace["intake_product_source_evidence"] += 1
        inventory = intake_product_source_evidence((str(cohort_root),))
        expected_paths = tuple(
            str(
                (
                    _FIXTURE_ROOT
                    / f"case-{cohort_ordinal:03d}"
                    / f"observation-{observation:03d}"
                    / "source_pack.json"
                ).resolve()
            )
            for observation in range(1, 3)
        )
        assert inventory.manifest_paths == expected_paths
        assert len(inventory.source_packs) == 2

        cohort_identities = tuple(
            SourceObservationIdentity.from_pack(pack)
            for pack in inventory.source_packs
        )
        assert len(set(cohort_identities)) == 2
        for identity, pack in zip(
            cohort_identities, inventory.source_packs, strict=True
        ):
            assert identity not in packs_by_identity
            packs_by_identity[identity] = pack

        trace["plan_family_knowledge_review"] += 1
        plan = plan_family_knowledge_review(inventory)
        assert len(plan.proposals) == 1
        proposal = plan.proposals[0]
        assert type(proposal) is FamilyMergeProposal
        assert set(proposal.members) == set(cohort_identities)

        trace["record_planned_family_decision"] += 1
        family_decision = record_planned_family_decision(
            plan,
            proposal,
            decision=FamilyMergeDecision.APPROVE,
            actor=_ACTOR,
            decided_at=_DECIDED_AT,
        )
        trace["durably_admit_planned_family"] += 1
        family_admission = durably_admit_planned_family(
            plan,
            family_decision,
            family_id=cohort["family_id"],
            database_path=database_path,
        )
        assert (
            family_admission.registration.status
            is CatalogRegistrationStatus.INSERTED
        )
        assert len(family_admission.family.members) == 2
        assert set(family_admission.family.members) == set(cohort_identities)

        variant_ids = cohort["variant_ids_in_canonical_member_order"]
        for member, variant_id in zip(
            family_admission.family.members, variant_ids, strict=True
        ):
            # Revision 2 intentionally requests only this explicit singleton.
            trace["prepare_sellable_variant_review"] += 1
            review = prepare_sellable_variant_review(
                family_admission.family,
                (member,),
            )
            assert review.proposal.members == (member,)
            trace["record_reviewed_sellable_variant_decision"] += 1
            variant_decision = record_reviewed_sellable_variant_decision(
                review,
                decision=SellableVariantDecision.APPROVE,
                actor=_ACTOR,
                decided_at=_DECIDED_AT,
            )
            trace["durably_admit_reviewed_sellable_variant"] += 1
            variant_admission = durably_admit_reviewed_sellable_variant(
                review,
                variant_decision,
                variant_id=variant_id,
                database_path=database_path,
            )
            assert (
                variant_admission.registration.status
                is CatalogRegistrationStatus.INSERTED
            )
            assert variant_admission.variant.members == (member,)

    trace["load_sqlite_canonical_catalog"] += 1
    catalog = load_sqlite_canonical_catalog(database_path)
    assert tuple(family.family_id for family in catalog.families) == tuple(
        cohort["family_id"] for cohort in descriptor["cohorts"]
    )
    assert tuple(variant.variant_id for variant in catalog.variants) == _VARIANT_IDS

    profiles = []
    for variant in catalog.variants:
        assert len(variant.members) == 1
        pack = packs_by_identity[variant.members[0]]
        assert SourceObservationIdentity.from_pack(pack) == variant.members[0]
        trace["build_canonical_variant_profile"] += 1
        profile = build_canonical_variant_profile(
            catalog,
            variant_id=variant.variant_id,
            source_packs=(pack,),
        )
        assert profile.members == variant.members
        assert len(profile.observations) == 1
        profiles.append(profile)
    profiles = tuple(profiles)

    cases = _benchmark_cases(descriptor)
    trace["evaluate_lexical_retrieval_quality"] += 1
    report = evaluate_lexical_retrieval_quality(profiles, cases, limit=_LIMIT)

    fidelities = []
    for case_evaluation in report.case_evaluations:
        case = case_evaluation.case
        trace["build_canonical_rag_context"] += 1
        context = build_canonical_rag_context(
            profiles,
            question=case.question,
            retrieval_query=case.retrieval_query,
            max_hits=_LIMIT,
        )
        has_hits = bool(context.hits)
        provider = _BooleanOnlyProvider(has_hits=has_hits)
        trace["answer_grounded_context"] += 1
        answer = asyncio.run(answer_grounded_context(context, provider))
        assert provider.generate_calls == 1
        trace["evaluate_grounded_answer_citation_fidelity"] += 1
        fidelities.append(
            evaluate_grounded_answer_citation_fidelity(case_evaluation, answer)
        )

    assert trace == {
        "answer_grounded_context": 4,
        "build_canonical_rag_context": 4,
        "build_canonical_variant_profile": 6,
        "create_sqlite_canonical_catalog": 1,
        "durably_admit_planned_family": 3,
        "durably_admit_reviewed_sellable_variant": 6,
        "evaluate_grounded_answer_citation_fidelity": 4,
        "evaluate_lexical_retrieval_quality": 1,
        "intake_product_source_evidence": 3,
        "load_sqlite_canonical_catalog": 1,
        "plan_family_knowledge_review": 3,
        "prepare_sellable_variant_review": 6,
        "record_planned_family_decision": 3,
        "record_reviewed_sellable_variant_decision": 6,
    }
    return report, tuple(fidelities)


def test_real_evidence_baseline_matches_frozen_snapshot(tmp_path, monkeypatch):
    monkeypatch.delenv("PI_P6_1B_CAPTURE_ROOT", raising=False)
    descriptor = _load_and_verify_descriptor()
    _verify_frozen_capture(descriptor)
    report, fidelities = _run_offline_benchmark(
        descriptor, tmp_path / "task-168-baseline.sqlite"
    )
    assert _snapshot(report, fidelities) == descriptor["baseline"]


def test_real_evidence_baseline_is_repeatedly_deterministic(tmp_path, monkeypatch):
    monkeypatch.delenv("PI_P6_1B_CAPTURE_ROOT", raising=False)
    descriptor = _load_and_verify_descriptor()
    _, fixture_paths = _verify_frozen_capture(descriptor)
    fixture_hashes_before = tuple(_sha256(path) for path in fixture_paths)
    first = _run_offline_benchmark(descriptor, tmp_path / "first.sqlite")
    second = _run_offline_benchmark(descriptor, tmp_path / "second.sqlite")
    assert first == second
    assert _snapshot(*first) == descriptor["baseline"]
    assert tuple(_sha256(path) for path in fixture_paths) == fixture_hashes_before


def test_singletons_are_evidence_conservative_not_product_truth():
    """The fixture representation is not a real-world sibling-difference claim."""

    descriptor = _load_and_verify_descriptor()
    assert descriptor["identity_semantics"] == {
        "complete_family_variant_partition_claimed": False,
        "product_truth_created": False,
        "sibling_observations_proven_different_real_world_variants": False,
        "singleton_reason": (
            "No direct EXACT_VARIANT_MATCH evidence authorizes sibling collapse; "
            "each canonical family member is represented conservatively as a singleton."
        ),
    }
