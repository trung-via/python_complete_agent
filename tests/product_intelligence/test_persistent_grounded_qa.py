"""Tests for Phase 6 M4.6 persistent grounded QA application boundary."""

import ast
import asyncio
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import socket
from unittest.mock import patch

import pytest

import src.product_intelligence as product_intelligence
import src.product_intelligence.persistent_grounded_qa as persistent_grounded_qa
from src.product_intelligence.canonical_catalog_sqlite import (
    CanonicalCatalogStorageError,
    create_sqlite_canonical_catalog,
    register_sqlite_canonical_family,
    register_sqlite_canonical_variant,
)
from src.product_intelligence.canonical_family import create_canonical_family
from src.product_intelligence.canonical_profile import CanonicalVariantProfileError
from src.product_intelligence.canonical_rag_context import CanonicalRagContextError
from src.product_intelligence.canonical_variant import create_canonical_sellable_variant
from src.product_intelligence.entity_grouping import group_resolution_graph
from src.product_intelligence.entity_resolution import (
    EntityResolutionResult,
    ProductRelationship,
    ResolutionEvidence,
    SourceObservationIdentity,
)
from src.product_intelligence.entity_resolution_graph import (
    MultiObservationResolutionGraph,
)
from src.product_intelligence.family_merge_approval import (
    FamilyMergeDecision,
    create_family_merge_decision_record,
    create_family_merge_proposal,
)
from src.product_intelligence.grounded_answer import (
    GroundedAnswer,
    GroundedAnswerError,
    GroundedAnswerStatus,
)
from src.product_intelligence.grounded_query_planning import GroundedQueryPlanningError
from src.product_intelligence.persistent_grounded_qa import (
    PersistentGroundedQaError,
    answer_persisted_grounded_question,
)
from src.product_intelligence.sellable_variant_approval import (
    SellableVariantDecision,
    create_sellable_variant_decision_record,
    create_sellable_variant_proposal,
)
from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
    ProductSourcePack,
)
from src.product_source.serialization import serialize_source_pack
from src.providers.base import LLMProvider, LLMResponse


OBSERVED_AT = datetime(2026, 8, 31, 9, 45, tzinfo=timezone.utc)


def _source_pack(name: str, *, title: str, color: str) -> ProductSourcePack:
    return ProductSourcePack(
        source_pack_id=f"pack-{name}",
        platform=f"market-{name}",
        product_url=f"https://market.example/{name}/listing",
        observed_at=OBSERVED_AT,
        collector=f"collector-{name}",
        title=title,
        source_product_id=f"listing-{name}",
        shop_name=f"shop-{name}",
        brand="Brand X",
        model_sku="SKU-100",
        description_text=f"Persisted {color} product evidence description",
        facts=(
            ProductFact(
                key="Color",
                value=color,
                unit=None,
                source_section="specs",
                provenance="table",
            ),
        ),
        media=(
            OriginalMediaRef(
                source_url=f"https://cdn.example/{name}/img.webp",
                platform=f"market-{name}",
                role=MediaRole.PRIMARY,
                provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
                ordinal=0,
                alt_text=f"{color} product photo",
                variant_label=color,
                content_type="image/webp",
                byte_size=256,
                sha256_hash="0" * 64,
                local_filename=f"img_{name}.webp",
            ),
        ),
        diagnostic_codes=(f"CODE_{name.upper()}",),
    )


def _setup_multi_variant_catalog_and_sources(tmp_path):
    """Create two variants across two families with four source packs."""
    pack_a = _source_pack("a", title="Alpha Blue Product", color="Blue")
    pack_b = _source_pack("b", title="Beta Blue Product", color="Blue")
    pack_c = _source_pack("c", title="Gamma Red Product", color="Red")
    pack_d = _source_pack("d", title="Delta Red Product", color="Red")

    path_a = serialize_source_pack(pack_a, str(tmp_path / "source-a"))
    path_b = serialize_source_pack(pack_b, str(tmp_path / "source-b"))
    path_c = serialize_source_pack(pack_c, str(tmp_path / "source-c"))
    path_d = serialize_source_pack(pack_d, str(tmp_path / "source-d"))

    member_a = SourceObservationIdentity.from_pack(pack_a)
    member_b = SourceObservationIdentity.from_pack(pack_b)
    member_c = SourceObservationIdentity.from_pack(pack_c)
    member_d = SourceObservationIdentity.from_pack(pack_d)

    # Family 1 / Variant 1 (members: a, b)
    pair_ab = EntityResolutionResult(
        relationship=ProductRelationship.EXACT_VARIANT_MATCH,
        confidence=0.99,
        left=member_b,
        right=member_a,
        reasons=("match ab",),
        evidence=(ResolutionEvidence("EV_AB", "Exact match a b"),),
    )
    graph_1 = MultiObservationResolutionGraph(
        observations=(member_b, member_a),
        pairwise_results=(pair_ab,),
        conflicts=(),
    )
    fam_prop_1 = create_family_merge_proposal(
        graph_1, group_resolution_graph(graph_1).groups[0]
    )
    fam_dec_1 = create_family_merge_decision_record(
        fam_prop_1,
        decision=FamilyMergeDecision.APPROVE,
        actor="reviewer-1",
        decided_at=datetime(2026, 8, 31, 10, tzinfo=timezone.utc),
    )
    family_1 = create_canonical_family(fam_dec_1, family_id="family-1")
    var_prop_1 = create_sellable_variant_proposal(family_1, (member_a, member_b))
    var_dec_1 = create_sellable_variant_decision_record(
        var_prop_1,
        decision=SellableVariantDecision.APPROVE,
        actor="reviewer-1",
        decided_at=datetime(2026, 8, 31, 11, tzinfo=timezone.utc),
    )
    variant_1 = create_canonical_sellable_variant(
        var_dec_1, variant_id="variant-blue"
    )

    # Family 2 / Variant 2 (members: c, d)
    pair_cd = EntityResolutionResult(
        relationship=ProductRelationship.EXACT_VARIANT_MATCH,
        confidence=0.99,
        left=member_d,
        right=member_c,
        reasons=("match cd",),
        evidence=(ResolutionEvidence("EV_CD", "Exact match c d"),),
    )
    graph_2 = MultiObservationResolutionGraph(
        observations=(member_d, member_c),
        pairwise_results=(pair_cd,),
        conflicts=(),
    )
    fam_prop_2 = create_family_merge_proposal(
        graph_2, group_resolution_graph(graph_2).groups[0]
    )
    fam_dec_2 = create_family_merge_decision_record(
        fam_prop_2,
        decision=FamilyMergeDecision.APPROVE,
        actor="reviewer-2",
        decided_at=datetime(2026, 8, 31, 10, tzinfo=timezone.utc),
    )
    family_2 = create_canonical_family(fam_dec_2, family_id="family-2")
    var_prop_2 = create_sellable_variant_proposal(family_2, (member_c, member_d))
    var_dec_2 = create_sellable_variant_decision_record(
        var_prop_2,
        decision=SellableVariantDecision.APPROVE,
        actor="reviewer-2",
        decided_at=datetime(2026, 8, 31, 11, tzinfo=timezone.utc),
    )
    variant_2 = create_canonical_sellable_variant(
        var_dec_2, variant_id="variant-red"
    )

    catalog_path = tmp_path / "canonical-catalog.sqlite"
    create_sqlite_canonical_catalog(catalog_path)
    register_sqlite_canonical_family(catalog_path, family_1)
    register_sqlite_canonical_variant(catalog_path, variant_1)
    register_sqlite_canonical_family(catalog_path, family_2)
    register_sqlite_canonical_variant(catalog_path, variant_2)

    return catalog_path, (path_a, path_b, path_c, path_d)


class _DeterministicFakeProvider(LLMProvider):
    def __init__(self, response_json: str):
        self.response_json = response_json
        self.calls = 0

    async def generate(self, messages, tools):
        self.calls += 1
        return LLMResponse(
            provider="fake",
            provider_response_id=f"resp-{self.calls}",
            content=self.response_json,
        )


def test_public_api_and_actual_namespace():
    assert persistent_grounded_qa.__all__ == [
        "PersistentGroundedQaError",
        "answer_persisted_grounded_question",
    ]
    assert {
        name for name in vars(persistent_grounded_qa) if not name.startswith("_")
    } == {"PersistentGroundedQaError", "answer_persisted_grounded_question"}
    assert (
        product_intelligence.PersistentGroundedQaError
        is persistent_grounded_qa.PersistentGroundedQaError
    )
    assert (
        product_intelligence.answer_persisted_grounded_question
        is persistent_grounded_qa.answer_persisted_grounded_question
    )
    assert (
        product_intelligence.__all__.count("PersistentGroundedQaError") == 1
    )
    assert (
        product_intelligence.__all__.count("answer_persisted_grounded_question")
        == 1
    )
    assert inspect.iscoroutinefunction(
        persistent_grounded_qa.answer_persisted_grounded_question
    )
    assert issubclass(PersistentGroundedQaError, ValueError)


@pytest.mark.parametrize(
    "invalid_paths",
    [
        "single/path.json",
        b"single/path.json",
        None,
        123,
        [""],
        [123],
        [Path("some/path.json")],
        ["valid/path.json", ""],
    ],
)
def test_invalid_manifest_paths_shape(tmp_path, invalid_paths):
    catalog_path = tmp_path / "catalog.sqlite"
    create_sqlite_canonical_catalog(catalog_path)
    provider = _DeterministicFakeProvider("{}")

    with pytest.raises(PersistentGroundedQaError):
        asyncio.run(
            answer_persisted_grounded_question(
                catalog_path,
                invalid_paths,
                question="What colors are available?",
                provider=provider,
            )
        )


def test_deterministic_multi_variant_restart_and_permutation_invariance(
    tmp_path,
):
    catalog_path, (path_a, path_b, path_c, path_d) = (
        _setup_multi_variant_catalog_and_sources(tmp_path)
    )

    orig_connect = socket.socket.connect

    def _forbid_network(self, address, *args, **kwargs):
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "localhost", "::1"):
            return orig_connect(self, address, *args, **kwargs)
        raise AssertionError("Network access is strictly forbidden")

    response_content = json.dumps(
        {
            "status": "ANSWERED",
            "answer_text": "The available colors include Blue and Red.",
            "citation_ids": ["H001-E001"],
            "limitations": [],
        }
    )

    with patch.object(socket.socket, "connect", _forbid_network):
        # Order 1: [path_a, path_b, path_c, path_d]
        provider_1 = _DeterministicFakeProvider(response_content)
        answer_1 = asyncio.run(
            answer_persisted_grounded_question(
                catalog_path,
                [path_a, path_b, path_c, path_d],
                question="Which Blue product is available?",
                provider=provider_1,
            )
        )

        # Order 2: Permuted order [path_d, path_c, path_b, path_a]
        provider_2 = _DeterministicFakeProvider(response_content)
        answer_2 = asyncio.run(
            answer_persisted_grounded_question(
                catalog_path,
                [path_d, path_c, path_b, path_a],
                question="Which Blue product is available?",
                provider=provider_2,
            )
        )

    assert isinstance(answer_1, GroundedAnswer)
    assert answer_1.status is GroundedAnswerStatus.ANSWERED
    assert answer_1.answer_text == "The available colors include Blue and Red."
    assert answer_1.citation_ids == ("H001-E001",)
    assert provider_1.calls == 1

    # Permutation invariance: both produce equivalent results and identical hit order
    assert answer_1.answer_text == answer_2.answer_text
    assert answer_1.citation_ids == answer_2.citation_ids
    assert len(answer_1.context.hits) == len(answer_2.context.hits)
    for h1, h2 in zip(answer_1.context.hits, answer_2.context.hits):
        assert h1.hit.profile.variant_id == h2.hit.profile.variant_id


def test_empty_catalog_and_empty_manifests(tmp_path):
    catalog_path = tmp_path / "empty-catalog.sqlite"
    create_sqlite_canonical_catalog(catalog_path)

    response_content = json.dumps(
        {
            "status": "INSUFFICIENT_EVIDENCE",
            "answer_text": "No evidence available.",
            "citation_ids": [],
            "limitations": ["No matches in catalog."],
        }
    )
    provider = _DeterministicFakeProvider(response_content)

    answer = asyncio.run(
        answer_persisted_grounded_question(
            catalog_path,
            [],
            question="What is the price?",
            provider=provider,
        )
    )

    assert answer.status is GroundedAnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.context.hits == ()
    assert provider.calls == 1


def test_input_completeness_validation_failures(tmp_path):
    catalog_path, (path_a, path_b, path_c, path_d) = (
        _setup_multi_variant_catalog_and_sources(tmp_path)
    )
    empty_catalog_path = tmp_path / "empty-catalog.sqlite"
    create_sqlite_canonical_catalog(empty_catalog_path)
    provider = _DeterministicFakeProvider("{}")

    # 1. Unbound manifest with empty catalog
    with pytest.raises(PersistentGroundedQaError) as exc_info:
        asyncio.run(
            answer_persisted_grounded_question(
                empty_catalog_path,
                [path_a],
                question="Color?",
                provider=provider,
            )
        )
    assert "not bound" in str(exc_info.value).lower()

    # 2. Missing manifest: only 3 of 4 manifests provided
    with pytest.raises(PersistentGroundedQaError) as exc_info:
        asyncio.run(
            answer_persisted_grounded_question(
                catalog_path,
                [path_a, path_b, path_c],
                question="Color?",
                provider=provider,
            )
        )
    assert "missing manifest" in str(exc_info.value).lower()

    # 3. Duplicate supplied manifest identity
    with pytest.raises(PersistentGroundedQaError) as exc_info:
        asyncio.run(
            answer_persisted_grounded_question(
                catalog_path,
                [path_a, path_a, path_b, path_c, path_d],
                question="Color?",
                provider=provider,
            )
        )
    assert "duplicate" in str(exc_info.value).lower()

    # 4. Extra unbound manifest: pack_e not registered in catalog
    pack_e = _source_pack("e", title="Extra Green Product", color="Green")
    path_e = serialize_source_pack(pack_e, str(tmp_path / "source-e"))
    with pytest.raises(PersistentGroundedQaError) as exc_info:
        asyncio.run(
            answer_persisted_grounded_question(
                catalog_path,
                [path_a, path_b, path_c, path_d, path_e],
                question="Color?",
                provider=provider,
            )
        )
    assert "not bound" in str(exc_info.value).lower()


def test_exact_call_order_and_delegation(tmp_path, monkeypatch):
    catalog_path, (path_a, path_b, path_c, path_d) = (
        _setup_multi_variant_catalog_and_sources(tmp_path)
    )

    calls = []

    orig_load = persistent_grounded_qa._load_sqlite_canonical_catalog
    orig_deser = persistent_grounded_qa._deserialize_product_source_pack
    orig_build_prof = persistent_grounded_qa._build_canonical_variant_profile
    orig_plan = persistent_grounded_qa._plan_grounded_retrieval_query
    orig_build_ctx = persistent_grounded_qa._build_canonical_rag_context
    orig_qa = persistent_grounded_qa._answer_grounded_context

    def mock_load(db_path):
        calls.append(("load_catalog", db_path))
        return orig_load(db_path)

    def mock_deser(path):
        calls.append(("deserialize", path))
        return orig_deser(path)

    def mock_build_prof(catalog, *, variant_id, source_packs):
        calls.append(("build_profile", variant_id))
        return orig_build_prof(catalog, variant_id=variant_id, source_packs=source_packs)

    def mock_plan(profiles, *, question):
        calls.append(("plan_query", question))
        return orig_plan(profiles, question=question)

    def mock_build_ctx(profiles, *, question, retrieval_query, max_hits, max_context_utf8_bytes):
        calls.append(("build_context", question, retrieval_query, max_hits, max_context_utf8_bytes))
        return orig_build_ctx(
            profiles,
            question=question,
            retrieval_query=retrieval_query,
            max_hits=max_hits,
            max_context_utf8_bytes=max_context_utf8_bytes,
        )

    async def mock_qa(context, provider):
        calls.append(("answer_qa", context.question))
        return await orig_qa(context, provider)

    monkeypatch.setattr(persistent_grounded_qa, "_load_sqlite_canonical_catalog", mock_load)
    monkeypatch.setattr(persistent_grounded_qa, "_deserialize_product_source_pack", mock_deser)
    monkeypatch.setattr(persistent_grounded_qa, "_build_canonical_variant_profile", mock_build_prof)
    monkeypatch.setattr(persistent_grounded_qa, "_plan_grounded_retrieval_query", mock_plan)
    monkeypatch.setattr(persistent_grounded_qa, "_build_canonical_rag_context", mock_build_ctx)
    monkeypatch.setattr(persistent_grounded_qa, "_answer_grounded_context", mock_qa)

    provider = _DeterministicFakeProvider(
        json.dumps(
            {
                "status": "ANSWERED",
                "answer_text": "Blue and Red.",
                "citation_ids": ["H001-E001"],
                "limitations": [],
            }
        )
    )

    asyncio.run(
        answer_persisted_grounded_question(
            catalog_path,
            [path_a, path_b, path_c, path_d],
            question="Which Blue product exists?",
            provider=provider,
            max_hits=3,
            max_context_utf8_bytes=16384,
        )
    )

    # Verify exact call stages
    call_stages = [c[0] for c in calls]
    assert call_stages == [
        "load_catalog",
        "deserialize",
        "deserialize",
        "deserialize",
        "deserialize",
        "build_profile",
        "build_profile",
        "plan_query",
        "build_context",
        "answer_qa",
    ]

    # Verify context construction arguments passed through unchanged
    ctx_call = next(c for c in calls if c[0] == "build_context")
    assert ctx_call[1] == "Which Blue product exists?"
    assert ctx_call[3] == 3
    assert ctx_call[4] == 16384


@pytest.mark.parametrize(
    "failure_point,expected_exception",
    [
        ("load", CanonicalCatalogStorageError),
        ("deserialize", FileNotFoundError),
        ("plan", GroundedQueryPlanningError),
        ("context", CanonicalRagContextError),
        ("qa", GroundedAnswerError),
        ("cancel", asyncio.CancelledError),
    ],
)
def test_predecessor_error_propagation(
    tmp_path, monkeypatch, failure_point, expected_exception
):
    catalog_path, (path_a, path_b, path_c, path_d) = (
        _setup_multi_variant_catalog_and_sources(tmp_path)
    )
    provider = _DeterministicFakeProvider("{}")

    if failure_point == "load":
        non_existent_db = tmp_path / "non-existent.sqlite"
        with pytest.raises(expected_exception):
            asyncio.run(
                answer_persisted_grounded_question(
                    non_existent_db,
                    [path_a, path_b, path_c, path_d],
                    question="Color?",
                    provider=provider,
                )
            )
        return

    if failure_point == "deserialize":
        with pytest.raises(expected_exception):
            asyncio.run(
                answer_persisted_grounded_question(
                    catalog_path,
                    [path_a, path_b, path_c, str(tmp_path / "missing.json")],
                    question="Color?",
                    provider=provider,
                )
            )
        return

    if failure_point == "plan":
        # Question with no alphanumeric tokens fails in plan_grounded_retrieval_query
        with pytest.raises(expected_exception):
            asyncio.run(
                answer_persisted_grounded_question(
                    catalog_path,
                    [path_a, path_b, path_c, path_d],
                    question="??? !!!",
                    provider=provider,
                )
            )
        return

    if failure_point == "context":
        # max_hits=0 fails in build_canonical_rag_context
        with pytest.raises(expected_exception):
            asyncio.run(
                answer_persisted_grounded_question(
                    catalog_path,
                    [path_a, path_b, path_c, path_d],
                    question="Color?",
                    provider=provider,
                    max_hits=0,
                )
            )
        return

    if failure_point == "qa":
        async def failing_qa(context, p):
            raise GroundedAnswerError("QA rejected answer")

        monkeypatch.setattr(
            persistent_grounded_qa, "_answer_grounded_context", failing_qa
        )
        with pytest.raises(expected_exception):
            asyncio.run(
                answer_persisted_grounded_question(
                    catalog_path,
                    [path_a, path_b, path_c, path_d],
                    question="Color?",
                    provider=provider,
                )
            )
        return

    if failure_point == "cancel":
        async def cancelling_qa(context, p):
            raise asyncio.CancelledError

        monkeypatch.setattr(
            persistent_grounded_qa, "_answer_grounded_context", cancelling_qa
        )
        with pytest.raises(expected_exception):
            asyncio.run(
                answer_persisted_grounded_question(
                    catalog_path,
                    [path_a, path_b, path_c, path_d],
                    question="Color?",
                    provider=provider,
                )
            )
        return


def test_no_direct_provider_call_and_no_forbidden_operations():
    source = inspect.getsource(persistent_grounded_qa.answer_persisted_grounded_question)
    tree = ast.parse(source)

    called_attributes = []
    called_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                called_attributes.append(node.func.attr)
            elif isinstance(node.func, ast.Name):
                called_names.append(node.func.id)

    # Must not call provider.generate directly
    assert "generate" not in called_attributes
    # Must not call forbidden I/O or exec functions
    for forbidden in ("open", "sqlite3", "eval", "exec", "system", "popen"):
        assert forbidden not in called_names
        assert forbidden not in called_attributes
