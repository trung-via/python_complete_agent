"""TASK-170 offline planner-assisted replay over the published stress corpus.

The planner inputs and relevance labels come byte-for-byte from TASK-169.  This
test composes published authorities only: TASK-134 plans each query once, then
TASK-164 evaluates the complete six-case corpus once through TASK-122.
"""

from __future__ import annotations

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
from src.product_intelligence.canonical_profile import build_canonical_variant_profile
from src.product_intelligence.entity_resolution import SourceObservationIdentity
from src.product_intelligence.family_decision_admission import (
    durably_admit_planned_family,
    record_planned_family_decision,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision,
    FamilyMergeProposal,
)
from src.product_intelligence.family_review_planning import plan_family_knowledge_review
from src.product_intelligence.grounded_query_planning import (
    plan_grounded_retrieval_query,
)
from src.product_intelligence.retrieval_quality_evaluation import (
    RetrievalBenchmarkCase,
    evaluate_lexical_retrieval_quality,
)
from src.product_intelligence.sellable_variant_approval import SellableVariantDecision
from src.product_intelligence.sellable_variant_review_admission import (
    durably_admit_reviewed_sellable_variant,
    prepare_sellable_variant_review,
    record_reviewed_sellable_variant_decision,
)
from src.product_intelligence.source_evidence_intake import (
    intake_product_source_evidence,
)


_TESTS_ROOT = Path(__file__).resolve().parents[1]
_REPOSITORY_ROOT = _TESTS_ROOT.parent
_SOURCE_FIXTURE_ROOT = _TESTS_ROOT / "fixtures" / "p6_1b_real_evidence"
_SOURCE_DESCRIPTOR_PATH = _SOURCE_FIXTURE_ROOT / "benchmark.json"
_STRESS_DESCRIPTOR_PATH = (
    _TESTS_ROOT / "fixtures" / "p6_1c_retrieval_stress" / "benchmark.json"
)
_DESCRIPTOR_PATH = (
    _TESTS_ROOT
    / "fixtures"
    / "p6_1d_planner_assisted_stress"
    / "benchmark.json"
)
_SOURCE_DESCRIPTOR_RELATIVE_PATH = "tests/fixtures/p6_1b_real_evidence/benchmark.json"
_SOURCE_DESCRIPTOR_SHA256 = (
    "ad742b54f827441b42f9162dfccd34f0241adbbbcb0991e4d692614e54835e08"
)
_STRESS_DESCRIPTOR_RELATIVE_PATH = (
    "tests/fixtures/p6_1c_retrieval_stress/benchmark.json"
)
_STRESS_DESCRIPTOR_SHA256 = (
    "1710f775860e3d715e535795aecef45d460cd58bf2a923628f1e1a26a0034c5f"
)
_ACTOR = "p6-benchmark"
_DECIDED_AT = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
_LIMIT = 3
_VARIANT_IDS = tuple(
    f"p6-benchmark-variant-{cohort:03d}-{member:03d}"
    for cohort in range(1, 4)
    for member in range(1, 3)
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compact_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _load_descriptor() -> tuple[dict, dict]:
    raw = _DESCRIPTOR_PATH.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    descriptor = json.loads(raw.decode("utf-8"))
    assert raw == _compact_json_bytes(descriptor)
    assert set(descriptor) == {
        "cases",
        "evaluator_limit",
        "lexical_snapshot",
        "schema",
        "source_stress",
        "version",
    }
    assert descriptor["schema"] == "p6_1d_planner_assisted_retrieval_stress"
    assert descriptor["version"] == 1
    assert descriptor["source_stress"] == {
        "benchmark_fixture": _STRESS_DESCRIPTOR_RELATIVE_PATH,
        "benchmark_sha256": _STRESS_DESCRIPTOR_SHA256,
    }
    assert descriptor["evaluator_limit"] == _LIMIT

    stress_path = (_REPOSITORY_ROOT / _STRESS_DESCRIPTOR_RELATIVE_PATH).resolve()
    assert stress_path == _STRESS_DESCRIPTOR_PATH.resolve()
    assert stress_path.is_file() and not stress_path.is_symlink()
    stress_raw = stress_path.read_bytes()
    assert hashlib.sha256(stress_raw).hexdigest() == _STRESS_DESCRIPTOR_SHA256
    stress = json.loads(stress_raw.decode("utf-8"))
    assert stress_raw == _compact_json_bytes(stress)
    assert stress["schema"] == "p6_1c_retrieval_stress_benchmark"
    assert stress["version"] == 1
    assert stress["evaluator_limit"] == _LIMIT
    assert len(stress["cases"]) == 6

    assert len(descriptor["cases"]) == 6
    for ordinal, (case, stress_case) in enumerate(
        zip(descriptor["cases"], stress["cases"], strict=True), start=1
    ):
        assert set(case) == {
            "case_id",
            "planned_query",
            "question",
            "relevant_variant_ids",
        }
        assert case["case_id"] == f"p6-1d-{ordinal:03d}"
        assert case["question"] == stress_case["retrieval_query"]
        assert case["relevant_variant_ids"] == stress_case["relevant_variant_ids"]
        assert type(case["planned_query"]) is str
    return descriptor, stress


def _load_and_verify_published_source(
    stress: dict,
) -> tuple[dict, tuple[Path, ...]]:
    source_record = stress["source_baseline"]
    assert source_record == {
        "benchmark_fixture": _SOURCE_DESCRIPTOR_RELATIVE_PATH,
        "benchmark_sha256": _SOURCE_DESCRIPTOR_SHA256,
    }
    source_path = (_REPOSITORY_ROOT / source_record["benchmark_fixture"]).resolve()
    assert source_path == _SOURCE_DESCRIPTOR_PATH.resolve()
    assert source_path.is_file() and not source_path.is_symlink()
    source_raw = source_path.read_bytes()
    assert hashlib.sha256(source_raw).hexdigest() == source_record["benchmark_sha256"]
    source = json.loads(source_raw.decode("utf-8"))
    assert source_raw == _compact_json_bytes(source)
    assert source["schema"] == "p6_1b_real_evidence_benchmark"
    assert source["version"] == 2
    assert len(source["cohorts"]) == 3

    capture_record = source["capture_bundle"]
    capture_path = (_SOURCE_FIXTURE_ROOT / capture_record["fixture"]).resolve()
    assert capture_path.is_relative_to(_SOURCE_FIXTURE_ROOT.resolve())
    assert capture_path.is_file() and not capture_path.is_symlink()
    assert _sha256(capture_path) == capture_record["sha256"]

    fixture_paths = [source_path, capture_path]
    for cohort_ordinal, cohort in enumerate(source["cohorts"], start=1):
        assert cohort["cohort_ordinal"] == cohort_ordinal
        assert cohort["family_id"] == f"p6-benchmark-family-{cohort_ordinal:03d}"
        assert cohort["variant_ids_in_canonical_member_order"] == list(
            _VARIANT_IDS[(cohort_ordinal - 1) * 2 : cohort_ordinal * 2]
        )
        assert len(cohort["source_manifests"]) == 2
        for observation_ordinal, manifest in enumerate(
            cohort["source_manifests"], start=1
        ):
            expected_target = (
                f"case-{cohort_ordinal:03d}/"
                f"observation-{observation_ordinal:03d}/source_pack.json"
            )
            assert manifest["fixture_target"] == expected_target
            fixture_path = (_SOURCE_FIXTURE_ROOT / expected_target).resolve()
            assert fixture_path.is_relative_to(_SOURCE_FIXTURE_ROOT.resolve())
            assert fixture_path.is_file() and not fixture_path.is_symlink()
            assert _sha256(fixture_path) == manifest["sha256"]
            fixture_paths.append(fixture_path)

    actual_files = {
        path.resolve() for path in _SOURCE_FIXTURE_ROOT.rglob("*") if path.is_file()
    }
    assert actual_files == set(fixture_paths)
    return source, tuple(fixture_paths)


def _fraction(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _snapshot(report) -> dict:
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
    }


def _run_offline_planner_assisted_benchmark(
    descriptor: dict,
    stress: dict,
    database_path: Path,
):
    source, _ = _load_and_verify_published_source(stress)
    empty_catalog = create_sqlite_canonical_catalog(database_path)
    assert empty_catalog.families == () and empty_catalog.variants == ()

    packs_by_identity = {}
    for cohort_ordinal, cohort in enumerate(source["cohorts"], start=1):
        cohort_root = _SOURCE_FIXTURE_ROOT / f"case-{cohort_ordinal:03d}"
        inventory = intake_product_source_evidence((str(cohort_root),))
        expected_paths = tuple(
            str(
                (
                    cohort_root
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

        plan = plan_family_knowledge_review(inventory)
        assert len(plan.proposals) == 1
        proposal = plan.proposals[0]
        assert type(proposal) is FamilyMergeProposal
        assert set(proposal.members) == set(cohort_identities)
        family_decision = record_planned_family_decision(
            plan,
            proposal,
            decision=FamilyMergeDecision.APPROVE,
            actor=_ACTOR,
            decided_at=_DECIDED_AT,
        )
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

        for member, variant_id in zip(
            family_admission.family.members,
            cohort["variant_ids_in_canonical_member_order"],
            strict=True,
        ):
            review = prepare_sellable_variant_review(
                family_admission.family,
                (member,),
            )
            assert review.proposal.members == (member,)
            variant_decision = record_reviewed_sellable_variant_decision(
                review,
                decision=SellableVariantDecision.APPROVE,
                actor=_ACTOR,
                decided_at=_DECIDED_AT,
            )
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

    catalog = load_sqlite_canonical_catalog(database_path)
    assert tuple(family.family_id for family in catalog.families) == tuple(
        cohort["family_id"] for cohort in source["cohorts"]
    )
    assert tuple(variant.variant_id for variant in catalog.variants) == _VARIANT_IDS

    profiles = []
    for variant in catalog.variants:
        assert len(variant.members) == 1
        pack = packs_by_identity[variant.members[0]]
        assert SourceObservationIdentity.from_pack(pack) == variant.members[0]
        profile = build_canonical_variant_profile(
            catalog,
            variant_id=variant.variant_id,
            source_packs=(pack,),
        )
        assert profile.members == variant.members
        assert len(profile.observations) == 1
        profiles.append(profile)
    profile_corpus = tuple(profiles)

    planned_queries = []
    for stress_case in stress["cases"]:
        question = stress_case["retrieval_query"]
        planned_queries.append(
            plan_grounded_retrieval_query(profile_corpus, question=question)
        )
    assert len(planned_queries) == 6

    cases = tuple(
        RetrievalBenchmarkCase(
            case_id=f"p6-1d-{ordinal:03d}",
            question=stress_case["retrieval_query"],
            retrieval_query=planned_query,
            relevant_variant_ids=tuple(stress_case["relevant_variant_ids"]),
        )
        for ordinal, (stress_case, planned_query) in enumerate(
            zip(stress["cases"], planned_queries, strict=True), start=1
        )
    )
    assert len(cases) == 6
    report = evaluate_lexical_retrieval_quality(
        profile_corpus,
        cases,
        limit=_LIMIT,
    )
    assert [case["planned_query"] for case in descriptor["cases"]] == planned_queries
    return tuple(planned_queries), report


def test_planner_assisted_stress_matches_committed_snapshot(tmp_path):
    descriptor, stress = _load_descriptor()
    _, report = _run_offline_planner_assisted_benchmark(
        descriptor,
        stress,
        tmp_path / "task-170-planner-assisted.sqlite",
    )
    assert _snapshot(report) == descriptor["lexical_snapshot"]


def test_planner_assisted_stress_is_repeatedly_deterministic(tmp_path):
    descriptor_bytes_before = _DESCRIPTOR_PATH.read_bytes()
    stress_bytes_before = _STRESS_DESCRIPTOR_PATH.read_bytes()
    descriptor, stress = _load_descriptor()
    _, fixture_paths = _load_and_verify_published_source(stress)
    fixture_bytes_before = tuple(path.read_bytes() for path in fixture_paths)

    first_queries, first_report = _run_offline_planner_assisted_benchmark(
        descriptor, stress, tmp_path / "first.sqlite"
    )
    second_queries, second_report = _run_offline_planner_assisted_benchmark(
        descriptor, stress, tmp_path / "second.sqlite"
    )

    assert first_queries == second_queries
    assert first_report == second_report
    assert _snapshot(first_report) == descriptor["lexical_snapshot"]
    assert tuple(path.read_bytes() for path in fixture_paths) == fixture_bytes_before
    assert _STRESS_DESCRIPTOR_PATH.read_bytes() == stress_bytes_before
    assert _DESCRIPTOR_PATH.read_bytes() == descriptor_bytes_before
