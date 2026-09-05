"""Focused regressions for TASK-134 grounded retrieval query planning."""

from datetime import datetime, timezone
from inspect import Parameter, signature
import sys
from unittest.mock import patch

import pytest

import src.product_intelligence as product_intelligence_module
import src.product_intelligence.grounded_query_planning as query_planning_module
from src.product_intelligence import (
    CanonicalProfileFactEvidence,
    CanonicalProfileMediaEvidence,
    CanonicalProfileObservation,
    CanonicalProfileRetrievalError,
    CanonicalRetrievalField,
    CanonicalVariantProfile,
    GroundedQueryPlanningError,
    SourceObservationIdentity,
    plan_grounded_retrieval_query,
)
from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    ProductFact,
)

OBSERVED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _member(name: str, platform: str = "Shopee") -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform=platform,
        source_product_id=f"prod-{name}",
        product_url=f"https://example.com/p/{name}",
        observed_at=OBSERVED_AT,
    )


def _profile(
    variant_id: str,
    *,
    title: str | None = None,
    brand: str | None = None,
    model_sku: str | None = None,
    description_text: str | None = None,
    shop_name: str | None = None,
    fact_key: str | None = None,
    fact_value: str | None = None,
    media_alt_text: str | None = None,
    media_variant_label: str | None = None,
) -> CanonicalVariantProfile:
    source_member = _member(variant_id)
    obs = CanonicalProfileObservation(
        member=source_member,
        collector="opaque-collector",
        title=title,
        brand=brand,
        model_sku=model_sku,
        description_text=description_text,
        shop_name=shop_name,
    )
    facts: list[CanonicalProfileFactEvidence] = []
    if fact_key is not None and fact_value is not None:
        facts.append(
            CanonicalProfileFactEvidence(
                member=source_member,
                fact=ProductFact(
                    key=fact_key,
                    value=fact_value,
                    unit=None,
                    source_section="specs",
                    provenance="opaque",
                ),
            )
        )
    media: list[CanonicalProfileMediaEvidence] = []
    if media_alt_text is not None or media_variant_label is not None:
        media.append(
            CanonicalProfileMediaEvidence(
                member=source_member,
                media=OriginalMediaRef(
                    source_url=f"https://example.com/media/{variant_id}.jpg",
                    platform="Shopee",
                    role=MediaRole.VARIANT,
                    provenance=MediaProvenance.SEMANTIC_VARIANT_MEDIA,
                    ordinal=0,
                    alt_text=media_alt_text,
                    variant_label=media_variant_label,
                    sha256_hash="hash",
                    local_filename="img.jpg",
                ),
            )
        )
    return CanonicalVariantProfile(
        variant_id=variant_id,
        family_id=f"family-{variant_id}",
        members=(source_member,),
        observations=(obs,),
        fact_evidence=tuple(facts),
        media_evidence=tuple(media),
    )


def test_public_surface_and_exports_are_bounded():
    """AC1: Exports add exactly GroundedQueryPlanningError and plan_grounded_retrieval_query."""
    assert query_planning_module.__all__ == [
        "GroundedQueryPlanningError",
        "plan_grounded_retrieval_query",
    ]
    assert {
        name for name in vars(query_planning_module) if not name.startswith("_")
    } == {
        "GroundedQueryPlanningError",
        "plan_grounded_retrieval_query",
    }
    assert issubclass(GroundedQueryPlanningError, ValueError)
    assert getattr(product_intelligence_module, "GroundedQueryPlanningError") is GroundedQueryPlanningError
    assert getattr(product_intelligence_module, "plan_grounded_retrieval_query") is plan_grounded_retrieval_query

    params = tuple(signature(plan_grounded_retrieval_query).parameters.values())
    assert len(params) == 2
    assert params[0].name == "profiles"
    assert params[0].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].name == "question"
    assert params[1].kind is Parameter.KEYWORD_ONLY


def test_question_input_validation_fails_closed():
    """AC2: Validates exact nonblank <=4096-byte question input."""
    p = _profile("v1", title="Widget A")

    class SubStr(str):
        pass

    for invalid_q in (None, 123, ["question"], SubStr("valid text"), object()):
        with pytest.raises(GroundedQueryPlanningError, match="exact str"):
            plan_grounded_retrieval_query([p], question=invalid_q)  # type: ignore[arg-type]

    for blank_q in ("", "   ", "\t\r\n  "):
        with pytest.raises(GroundedQueryPlanningError, match="at least one non-whitespace"):
            plan_grounded_retrieval_query([p], question=blank_q)

    # UTF-8 byte boundary: 4096 bytes is valid, 4097 bytes fails
    exact_4096 = "a" * 4096
    res = plan_grounded_retrieval_query((), question=exact_4096)
    assert res == exact_4096

    too_large = "a" * 4097
    with pytest.raises(GroundedQueryPlanningError, match="4096 UTF-8 bytes"):
        plan_grounded_retrieval_query([p], question=too_large)

    # Multi-byte UTF-8 test (4-byte characters)
    emoji_str = "🛒" * 1025  # 1025 * 4 = 4100 bytes
    with pytest.raises(GroundedQueryPlanningError, match="4096 UTF-8 bytes"):
        plan_grounded_retrieval_query([p], question=emoji_str)


def test_lexical_segmentation_rules_and_run_bounds():
    """AC2: Maximal original str.isalnum() runs in source order, rejects 0 or >24 runs."""
    p = _profile("v1", title="Widget A")

    # Zero alphanumeric runs (all punctuation/symbols)
    with pytest.raises(GroundedQueryPlanningError, match="at least one alphanumeric token"):
        plan_grounded_retrieval_query([p], question="??? --- !!! @@@")

    # Maximal runs preserve original casing, bytes, and order without normalization
    q = "What is the Price of Café-Wireless_Pro.v2??"
    runs = query_planning_module._segment_question(q)
    assert runs == ("What", "is", "the", "Price", "of", "Café", "Wireless", "Pro", "v2")

    # Exactly 24 runs is accepted (if hit found, returns planned query; if no hit, fails closed because > 12 runs)
    q_24_hit = " ".join(f"word{i}" for i in range(23)) + " Widget"
    res_24_hit = plan_grounded_retrieval_query([p], question=q_24_hit)
    assert res_24_hit == "Widget"

    q_24_nohit = " ".join(f"word{i}" for i in range(24))
    with pytest.raises(GroundedQueryPlanningError, match="exceeds 12 tokens"):
        plan_grounded_retrieval_query((), question=q_24_nohit)

    # More than 24 runs fails closed immediately during question segmentation
    q_25 = " ".join(f"word{i}" for i in range(25))
    with pytest.raises(GroundedQueryPlanningError, match="at most 24 alphanumeric tokens"):
        plan_grounded_retrieval_query([p], question=q_25)


def test_candidate_generation_and_evaluation_order():
    """AC3 & AC4: Evaluates candidate spans length 1..12 descending, then ascending start with limit=2."""
    probed_candidates: list[str] = []

    real_retrieve = query_planning_module._retrieve_canonical_variant_profiles

    def spy_retrieve(profiles, *, query, limit):
        probed_candidates.append(query)
        assert limit == 2
        assert isinstance(profiles, tuple)
        return real_retrieve(profiles, query=query, limit=limit)

    question = "one two three four"
    with patch(
        "src.product_intelligence.grounded_query_planning._retrieve_canonical_variant_profiles",
        side_effect=spy_retrieve,
    ):
        plan_grounded_retrieval_query((), question=question)

    expected_probe_order = [
        # Length 4
        "one two three four",
        # Length 3
        "one two three",
        "two three four",
        # Length 2
        "one two",
        "two three",
        "three four",
        # Length 1
        "one",
        "two",
        "three",
        "four",
    ]
    assert probed_candidates == expected_probe_order


def test_candidate_span_length_capped_at_12():
    """AC3: Candidates spans are at most 12 tokens even when question has up to 24 tokens."""
    probed_lengths: list[int] = []

    def fake_retrieve(profiles, *, query, limit):
        probed_lengths.append(len(query.split()))
        return ()

    question = " ".join(f"tok{i}" for i in range(15))
    with patch(
        "src.product_intelligence.grounded_query_planning._retrieve_canonical_variant_profiles",
        side_effect=fake_retrieve,
    ):
        with pytest.raises(GroundedQueryPlanningError, match="exceeds 12 tokens"):
            plan_grounded_retrieval_query((), question=question)

    assert max(probed_lengths) == 12
    assert min(probed_lengths) == 1
    for i in range(len(probed_lengths) - 1):
        assert probed_lengths[i] >= probed_lengths[i + 1] or probed_lengths[i] == 1


def test_preference_ordering_identity_bearing_over_any_field_over_multiple():
    """AC5: Preference class 1 (single hit identity) > class 2 (single hit any) > class 3 (multiple)."""
    p1 = _profile("p1", title="Logitech MX Master 3S")
    p2 = _profile("p2", title="Logitech G Pro")
    p3 = _profile("p3", description_text="wireless ergonomic office")

    corpus = (p1, p2, p3)

    # Class 1 (logitech mx -> title) beats Class 2 (ergonomic office -> description) and Class 3 (logitech -> multiple)
    q1 = "is there a logitech mx wireless ergonomic office mouse"
    result = plan_grounded_retrieval_query(corpus, question=q1)
    assert result == "logitech mx"

    # When no class 1 hit exists, class 2 beats class 3 even if class 3 has a longer span:
    # "logitech" (len 1, 2 hits -> class 3)
    # "wireless ergonomic office" (len 3, 1 hit on DESCRIPTION_TEXT -> class 2)
    q2 = "find logitech wireless ergonomic office"
    result2 = plan_grounded_retrieval_query(corpus, question=q2)
    assert result2 == "wireless ergonomic office"

    # When only class 3 (multiple) hits exist:
    q3 = "looking for logitech"
    result3 = plan_grounded_retrieval_query(corpus, question=q3)
    assert result3 == "logitech"


def test_identity_bearing_witness_fields_coverage():
    """AC5: Identity-bearing fields are exactly TITLE, BRAND, MODEL_SKU, MEDIA_VARIANT_LABEL."""
    # Test TITLE
    p_title = _profile("v_title", title="AlphaTitleUnique")
    assert plan_grounded_retrieval_query((p_title,), question="find AlphaTitleUnique") == "AlphaTitleUnique"

    # Test BRAND
    p_brand = _profile("v_brand", brand="AlphaBrandUnique")
    assert plan_grounded_retrieval_query((p_brand,), question="find AlphaBrandUnique") == "AlphaBrandUnique"

    # Test MODEL_SKU
    p_sku = _profile("v_sku", model_sku="AlphaSkuUnique")
    assert plan_grounded_retrieval_query((p_sku,), question="find AlphaSkuUnique") == "AlphaSkuUnique"

    # Test MEDIA_VARIANT_LABEL
    p_media = _profile("v_media", media_variant_label="AlphaLabelUnique")
    assert plan_grounded_retrieval_query((p_media,), question="find AlphaLabelUnique") == "AlphaLabelUnique"

    # Test non-identity witness field (e.g. SHOP_NAME):
    # Two distinct profiles: p_shop has shop_name only, p_title has title only.
    # Candidate "Super Store Seller" (3 tokens) hits p_shop via SHOP_NAME (class 2).
    # Candidate "NanoCore" (1 token) hits p_title via TITLE (class 1).
    # "NanoCore" (class 1) must win despite shorter span!
    p_shop = _profile("v_shop", shop_name="Super Store Seller")
    p_core = _profile("v_core", title="NanoCore")
    q = "check Super Store Seller NanoCore"
    result = plan_grounded_retrieval_query((p_shop, p_core), question=q)
    assert result == "NanoCore"


def test_immediate_return_on_first_identity_bearing_candidate():
    """AC5: First observed class 1 candidate is returned immediately without probing further."""
    probed: list[str] = []
    p = _profile("v1", title="Alpha Beta Gamma")

    real_retrieve = query_planning_module._retrieve_canonical_variant_profiles

    def spy_retrieve(profiles, *, query, limit):
        probed.append(query)
        return real_retrieve(profiles, query=query, limit=limit)

    q = "find Alpha Beta Gamma please"
    # tokens: ('find', 'Alpha', 'Beta', 'Gamma', 'please') - 5 tokens
    # Length 5: "find Alpha Beta Gamma please" -> 0 hits
    # Length 4: "find Alpha Beta Gamma" -> 0 hits, "Alpha Beta Gamma please" -> 0 hits
    # Length 3: "find Alpha Beta" -> 0 hits, "Alpha Beta Gamma" -> 1 hit on TITLE (class 1)!
    # Evaluation stops immediately at "Alpha Beta Gamma" and does not probe remaining spans.
    with patch(
        "src.product_intelligence.grounded_query_planning._retrieve_canonical_variant_profiles",
        side_effect=spy_retrieve,
    ):
        res = plan_grounded_retrieval_query((p,), question=q)

    assert res == "Alpha Beta Gamma"
    assert "Alpha Beta Gamma" in probed
    for query in probed:
        assert len(query.split()) >= 3


def test_tie_breaking_within_same_class():
    """AC5: Within same class: longer span > earlier start position."""
    p = _profile("v1", description_text="super high efficiency cooling")
    q = "need high efficiency cooling"
    # "high efficiency cooling" (len 3) -> 1 hit on DESCRIPTION_TEXT (class 2)
    # "high efficiency" (len 2) -> 1 hit on DESCRIPTION_TEXT (class 2)
    res = plan_grounded_retrieval_query((p,), question=q)
    assert res == "high efficiency cooling"

    # Same length, earlier start:
    p1 = _profile("p1", description_text="termA other termB")
    p2 = _profile("p2", description_text="termA other termB")
    q_tie = "termA check termB"
    res_tie = plan_grounded_retrieval_query((p1, p2), question=q_tie)
    assert res_tie == "termA"


def test_no_hit_fallback_and_length_failure():
    """AC6: If all candidates are no-hit: <=12 runs returns full question; >12 runs fails closed."""
    p = _profile("v1", title="Completely Unrelated Product")

    # <= 12 runs: returns complete lexical question joined with single space
    q_short = "where is my missing widget device"
    res = plan_grounded_retrieval_query((p,), question=q_short)
    assert res == "where is my missing widget device"

    # Exactly 12 runs with no hits: returns complete lexical question
    q_12 = "one two three four five six seven eight nine ten eleven twelve"
    res_12 = plan_grounded_retrieval_query((p,), question=q_12)
    assert res_12 == q_12

    # > 12 runs (e.g. 13 runs) with no hits: fails closed with GroundedQueryPlanningError
    q_13 = "one two three four five six seven eight nine ten eleven twelve thirteen"
    with pytest.raises(GroundedQueryPlanningError, match="exceeds 12 tokens"):
        plan_grounded_retrieval_query((p,), question=q_13)


def test_empty_corpus_behavior():
    """AC7: Empty corpus follows no-hit fallback without inventing evidence."""
    # <= 12 runs: returns complete question
    q_short = "what is the price of shoes"
    assert plan_grounded_retrieval_query((), question=q_short) == "what is the price of shoes"

    # > 12 runs: fails closed
    q_14 = " ".join(f"word{i}" for i in range(14))
    with pytest.raises(GroundedQueryPlanningError, match="exceeds 12 tokens"):
        plan_grounded_retrieval_query((), question=q_14)


def test_corpus_error_propagation_under_task_122_authority():
    """AC4: Propagates CanonicalProfileRetrievalError unchanged for invalid corpus."""
    q = "valid question"
    p = _profile("v1", title="Valid")

    # None corpus
    with pytest.raises(CanonicalProfileRetrievalError):
        plan_grounded_retrieval_query(None, question=q)  # type: ignore[arg-type]

    # Non-profile objects in corpus
    with pytest.raises(CanonicalProfileRetrievalError):
        plan_grounded_retrieval_query([p, object()], question=q)  # type: ignore[list-item]

    # Duplicate variant_id in corpus
    p_dup = _profile("v1", title="Duplicate Variant ID")
    with pytest.raises(CanonicalProfileRetrievalError, match="duplicate variant_id"):
        plan_grounded_retrieval_query([p, p_dup], question=q)


def test_determinism_corpus_permutation_and_input_immutability():
    """AC7: Corpus permutations, repeated calls, and generators are deterministic and immutable."""
    p1 = _profile("v1", title="Camera Sony A7")
    p2 = _profile("v2", title="Camera Nikon Z6")
    q = "where can I buy a Camera"

    # Permutations [p1, p2] vs [p2, p1]
    res1 = plan_grounded_retrieval_query([p1, p2], question=q)
    res2 = plan_grounded_retrieval_query([p2, p1], question=q)
    assert res1 == res2 == "Camera"

    # Generator input is consumed once into a tuple and safely probed repeatedly
    gen = (p for p in [p1, p2])
    res_gen = plan_grounded_retrieval_query(gen, question=q)
    assert res_gen == "Camera"

    # Profile objects are not mutated
    assert p1.variant_id == "v1"
    assert p2.variant_id == "v2"


def test_no_model_network_or_storage_dependencies():
    """AC8: Module performs pure in-memory work with no model, storage, or network I/O."""
    assert "src.providers" not in sys.modules or "src.providers.base" not in query_planning_module.__dict__
    assert "sqlite3" not in query_planning_module.__dict__
    assert "urllib" not in query_planning_module.__dict__
    assert "requests" not in query_planning_module.__dict__
    assert "uuid" not in query_planning_module.__dict__
    assert "random" not in query_planning_module.__dict__
    assert "time" not in query_planning_module.__dict__
