"""TASK-169 offline lexical stress replay over the published TASK-168 corpus.

The six cases and their relevance labels are Human-authored fixture input.  This
test only composes published intake, admission, durability, profile, and TASK-164
evaluation authorities; it defines no retrieval or product-truth semantics.
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
from src.product_intelligence.source_evidence_intake import intake_product_source_evidence


_TESTS_ROOT = Path(__file__).resolve().parents[1]
_REPOSITORY_ROOT = _TESTS_ROOT.parent
_SOURCE_FIXTURE_ROOT = _TESTS_ROOT / "fixtures" / "p6_1b_real_evidence"
_SOURCE_DESCRIPTOR_PATH = _SOURCE_FIXTURE_ROOT / "benchmark.json"
_STRESS_DESCRIPTOR_PATH = (
    _TESTS_ROOT / "fixtures" / "p6_1c_retrieval_stress" / "benchmark.json"
)
_SOURCE_DESCRIPTOR_RELATIVE_PATH = "tests/fixtures/p6_1b_real_evidence/benchmark.json"
_SOURCE_DESCRIPTOR_SHA256 = (
    "ad742b54f827441b42f9162dfccd34f0241adbbbcb0991e4d692614e54835e08"
)
_ACTOR = "p6-benchmark"
_DECIDED_AT = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
_LIMIT = 3
_VARIANT_IDS = tuple(
    f"p6-benchmark-variant-{cohort:03d}-{member:03d}"
    for cohort in range(1, 4)
    for member in range(1, 3)
)
_CASE_RECORDS = (
    {
        "case_id": "p6-1c-001",
        "question": (
            "Which published benchmark variants match the fixed Human stress intent "
            "bình nước thép không gỉ giữ nóng lạnh?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[0:2]),
        "retrieval_query": "bình nước thép không gỉ giữ nóng lạnh",
    },
    {
        "case_id": "p6-1c-002",
        "question": (
            "Which published benchmark variants match the fixed Human stress intent "
            "bình lớn có lọc trà mang đi làm?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[0:2]),
        "retrieval_query": "bình lớn có lọc trà mang đi làm",
    },
    {
        "case_id": "p6-1c-003",
        "question": (
            "Which published benchmark variants match the fixed Human stress intent "
            "keyboard gaming k550 nhiều màu?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[2:4]),
        "retrieval_query": "keyboard gaming k550 nhiều màu",
    },
    {
        "case_id": "p6-1c-004",
        "question": (
            "Which published benchmark variants match the fixed Human stress intent "
            "bàn phím chơi game có đèn?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[2:4]),
        "retrieval_query": "bàn phím chơi game có đèn",
    },
    {
        "case_id": "p6-1c-005",
        "question": (
            "Which published benchmark variants match the fixed Human stress intent "
            "mouse bluetooth sạc lại cho laptop?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[4:6]),
        "retrieval_query": "mouse bluetooth sạc lại cho laptop",
    },
    {
        "case_id": "p6-1c-006",
        "question": (
            "Which published benchmark variants match the fixed Human stress intent "
            "chuột dùng cho máy tính bảng android?"
        ),
        "relevant_variant_ids": list(_VARIANT_IDS[4:6]),
        "retrieval_query": "chuột dùng cho máy tính bảng android",
    },
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


def _load_stress_descriptor() -> dict:
    raw = _STRESS_DESCRIPTOR_PATH.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    descriptor = json.loads(raw.decode("utf-8"))
    assert raw == _compact_json_bytes(descriptor)
    assert set(descriptor) == {
        "cases",
        "evaluator_limit",
        "lexical_snapshot",
        "schema",
        "source_baseline",
        "version",
    }
    assert descriptor["schema"] == "p6_1c_retrieval_stress_benchmark"
    assert descriptor["version"] == 1
    assert descriptor["source_baseline"] == {
        "benchmark_fixture": _SOURCE_DESCRIPTOR_RELATIVE_PATH,
        "benchmark_sha256": _SOURCE_DESCRIPTOR_SHA256,
    }
    assert descriptor["evaluator_limit"] == _LIMIT
    assert descriptor["cases"] == list(_CASE_RECORDS)
    return descriptor


def _load_and_verify_published_source(descriptor: dict) -> tuple[dict, tuple[Path, ...]]:
    source_record = descriptor["source_baseline"]
    assert source_record["benchmark_fixture"] == _SOURCE_DESCRIPTOR_RELATIVE_PATH
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


def _run_offline_stress_benchmark(descriptor: dict, database_path: Path):
    source, _ = _load_and_verify_published_source(descriptor)
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
        assert family_admission.registration.status is CatalogRegistrationStatus.INSERTED
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

    cases = _benchmark_cases(descriptor)
    assert len(cases) == 6
    return evaluate_lexical_retrieval_quality(
        tuple(profiles),
        cases,
        limit=_LIMIT,
    )


def test_retrieval_stress_baseline_matches_committed_snapshot(tmp_path):
    descriptor = _load_stress_descriptor()
    report = _run_offline_stress_benchmark(
        descriptor,
        tmp_path / "task-169-stress.sqlite",
    )
    assert _snapshot(report) == descriptor["lexical_snapshot"]


def test_retrieval_stress_baseline_is_repeatedly_deterministic(tmp_path):
    descriptor_bytes_before = _STRESS_DESCRIPTOR_PATH.read_bytes()
    descriptor = _load_stress_descriptor()
    _, fixture_paths = _load_and_verify_published_source(descriptor)
    fixture_bytes_before = tuple(path.read_bytes() for path in fixture_paths)

    first = _run_offline_stress_benchmark(descriptor, tmp_path / "first.sqlite")
    second = _run_offline_stress_benchmark(descriptor, tmp_path / "second.sqlite")

    assert first == second
    assert _snapshot(first) == descriptor["lexical_snapshot"]
    assert tuple(path.read_bytes() for path in fixture_paths) == fixture_bytes_before
    assert _STRESS_DESCRIPTOR_PATH.read_bytes() == descriptor_bytes_before
