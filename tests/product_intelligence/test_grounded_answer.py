"""Focused regressions for TASK-129 Grounded Answer contract."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
import pytest

import src.product_intelligence as pi
from src.product_intelligence import (
    CanonicalProfileFactEvidence,
    CanonicalProfileMediaEvidence,
    CanonicalProfileObservation,
    CanonicalRagContext,
    CanonicalVariantProfile,
    GroundedAnswer,
    GroundedAnswerError,
    GroundedAnswerStatus,
    SourceObservationIdentity,
    build_canonical_rag_context,
    create_grounded_answer,
)
from src.product_source.models import ProductFact

OBSERVED_AT = datetime(2026, 8, 31, tzinfo=timezone.utc)


def make_member(name: str, platform: str = "Shopee") -> SourceObservationIdentity:
    return SourceObservationIdentity(
        source_pack_id=f"pack-{name}",
        platform=platform,
        source_product_id=f"prod-{name}",
        product_url=f"https://example.com/p/{name}",
        observed_at=OBSERVED_AT,
    )


def make_profile(
    variant_id: str,
    family_id: str = "fam-1",
    *,
    members: tuple[SourceObservationIdentity, ...] | None = None,
    observations: tuple[CanonicalProfileObservation, ...] | None = None,
    fact_evidence: tuple[CanonicalProfileFactEvidence, ...] | None = None,
    media_evidence: tuple[CanonicalProfileMediaEvidence, ...] | None = None,
) -> CanonicalVariantProfile:
    if members is None:
        m = make_member(f"m-{variant_id}")
        members = (m,)
    if observations is None:
        observations = tuple(
            CanonicalProfileObservation(
                member=m,
                collector="collector",
                title=f"Gadget Title for {variant_id}",
                shop_name="Official Shop",
                brand="TopBrand",
                model_sku="SKU-100",
                description_text="High performance gadget",
            )
            for m in members
        )
    if fact_evidence is None:
        fact_evidence = ()
    if media_evidence is None:
        media_evidence = ()

    return CanonicalVariantProfile(
        variant_id=variant_id,
        family_id=family_id,
        members=members,
        observations=observations,
        fact_evidence=fact_evidence,
        media_evidence=media_evidence,
    )


def make_test_context() -> CanonicalRagContext:
    m = make_member("m1")
    obs = CanonicalProfileObservation(
        member=m,
        collector="collector",
        title="Gaming Laptop 16GB RAM",
        shop_name="Official Shop",
        brand="TopBrand",
        model_sku="SKU-100",
        description_text="High performance gaming laptop",
    )
    fact1 = CanonicalProfileFactEvidence(
        member=m,
        fact=ProductFact(key="RAM", value="16GB", source_section="Specs", provenance="listing_specs"),
    )
    fact2 = CanonicalProfileFactEvidence(
        member=m,
        fact=ProductFact(key="Weight", value="2.1kg", source_section="Specs", provenance="listing_specs"),
    )
    prof = make_profile(
        "var-1",
        members=(m,),
        observations=(obs,),
        fact_evidence=(fact1, fact2),
    )
    return build_canonical_rag_context(
        [prof],
        question="What is the RAM size and weight?",
        retrieval_query="RAM Weight",
    )


def test_public_exports():
    # AC1: Public exports add exactly GroundedAnswerError, GroundedAnswerStatus,
    # GroundedAnswer, and create_grounded_answer
    expected_symbols = [
        "GroundedAnswerError",
        "GroundedAnswerStatus",
        "GroundedAnswer",
        "create_grounded_answer",
    ]
    for sym in expected_symbols:
        assert hasattr(pi, sym)
        assert sym in pi.__all__

    # AC2: GroundedAnswerStatus contains exactly ANSWERED, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE
    assert set(GroundedAnswerStatus.__members__.keys()) == {
        "ANSWERED",
        "INSUFFICIENT_EVIDENCE",
        "CONFLICTING_EVIDENCE",
    }


def test_dataclass_fields_and_immutability():
    # AC3: GroundedAnswer is frozen/immutable, contains exactly the five required fields,
    # and retains the exact supplied CanonicalRagContext object without copying
    ctx = make_test_context()
    answer = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="The laptop has 16GB RAM.",
        citation_ids=("H001-W001",),
        limitations=(),
    )

    answer_fields = [f.name for f in fields(GroundedAnswer)]
    assert answer_fields == ["context", "status", "answer_text", "citation_ids", "limitations"]

    # Exact context identity retained
    assert answer.context is ctx

    # Frozen / immutability
    with pytest.raises(FrozenInstanceError):
        answer.answer_text = "new text"  # type: ignore
    with pytest.raises(FrozenInstanceError):
        answer.status = GroundedAnswerStatus.INSUFFICIENT_EVIDENCE  # type: ignore
    with pytest.raises(FrozenInstanceError):
        answer.citation_ids = ()  # type: ignore
    with pytest.raises(FrozenInstanceError):
        answer.limitations = ("new limitation",)  # type: ignore
    with pytest.raises(FrozenInstanceError):
        answer.context = ctx  # type: ignore


def test_exact_type_validation():
    # AC4: create_grounded_answer strictly validates exact context/status/value types
    ctx = make_test_context()

    # Invalid context
    class SubclassedContext(CanonicalRagContext):
        pass

    sub_ctx = SubclassedContext(
        question=ctx.question,
        retrieval_query=ctx.retrieval_query,
        max_hits=ctx.max_hits,
        max_context_utf8_bytes=ctx.max_context_utf8_bytes,
        hits=ctx.hits,
        truncated=ctx.truncated,
        omitted_evidence_blocks=ctx.omitted_evidence_blocks,
    )
    for bad_ctx in [None, 123, True, False, "context", {}, sub_ctx]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                bad_ctx,  # type: ignore
                status=GroundedAnswerStatus.ANSWERED,
                answer_text="valid answer",
                citation_ids=("H001-W001",),
            )
        assert "context must be an exact CanonicalRagContext" in str(exc.value)

    # Invalid status
    for bad_status in [None, "ANSWERED", 1, True, False, {}]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=bad_status,  # type: ignore
                answer_text="valid answer",
                citation_ids=("H001-W001",),
            )
        assert "status must be an exact GroundedAnswerStatus" in str(exc.value)

    # Invalid answer_text type
    for bad_text in [None, 123, True, False, ["text"], {"text": "val"}]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=GroundedAnswerStatus.ANSWERED,
                answer_text=bad_text,  # type: ignore
                citation_ids=("H001-W001",),
            )
        assert "answer_text must be an exact str" in str(exc.value)

    # Invalid citation_ids type (must be exact tuple)
    for bad_citations in [None, ["H001-W001"], {"H001-W001"}, "H001-W001", 123, True]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=GroundedAnswerStatus.ANSWERED,
                answer_text="valid answer",
                citation_ids=bad_citations,  # type: ignore
            )
        assert "citation_ids must be an exact tuple" in str(exc.value)

    # Invalid citation_ids items type
    for bad_item in [None, 123, True, False, ("nested",)]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=GroundedAnswerStatus.ANSWERED,
                answer_text="valid answer",
                citation_ids=(bad_item,),  # type: ignore
            )
        assert "citation_id at index 0 must be an exact str" in str(exc.value)

    # Invalid limitations type (must be exact tuple)
    for bad_lims in [None, ["limitation"], {"limitation"}, "limitation", 123, True]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
                answer_text="valid answer",
                citation_ids=(),
                limitations=bad_lims,  # type: ignore
            )
        assert "limitations must be an exact tuple" in str(exc.value)

    # Invalid limitations items type
    for bad_item in [None, 123, True, False, ("nested",)]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
                answer_text="valid answer",
                citation_ids=(),
                limitations=(bad_item,),  # type: ignore
            )
        assert "limitation item at index 0 must be an exact str" in str(exc.value)


def test_answer_text_bounds_and_exact_preservation():
    # AC4: nonblank answer_text, 32768-byte UTF-8 answer bound, preserves accepted answer text exactly
    ctx = make_test_context()

    # Blank / whitespace-only answer_text
    for blank_text in ["", " ", "   ", "\t\n\r", "\n"]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=GroundedAnswerStatus.ANSWERED,
                answer_text=blank_text,
                citation_ids=("H001-W001",),
            )
        assert "answer_text must contain at least one non-whitespace character" in str(exc.value)

    # Exactly 32768 UTF-8 bytes succeeds
    exact_bound_text = "a" * 32768
    ans_bound = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text=exact_bound_text,
        citation_ids=("H001-W001",),
    )
    assert len(ans_bound.answer_text.encode("utf-8")) == 32768
    assert ans_bound.answer_text == exact_bound_text

    # Exceeding 32768 UTF-8 bytes fails
    oversized_text = "a" * 32769
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text=oversized_text,
            citation_ids=("H001-W001",),
        )
    assert "exceeds UTF-8 bound of 32768 bytes" in str(exc.value)

    # Multi-byte UTF-8 text bound: 'é' is 2 UTF-8 bytes
    two_byte_char = "é"
    assert len(two_byte_char.encode("utf-8")) == 2
    exact_32768_multibyte = two_byte_char * 16384  # exactly 32768 bytes
    ans_mb = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text=exact_32768_multibyte,
        citation_ids=("H001-W001",),
    )
    assert len(ans_mb.answer_text.encode("utf-8")) == 32768

    oversized_multibyte = two_byte_char * 16385  # 32770 bytes
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text=oversized_multibyte,
            citation_ids=("H001-W001",),
        )
    assert "exceeds UTF-8 bound of 32768 bytes" in str(exc.value)

    # Byte-for-byte preservation: leading and trailing whitespace preserved
    untrimmed_text = "  Leading and trailing whitespace preserved exactly.  \n"
    ans_untrimmed = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text=untrimmed_text,
        citation_ids=("H001-W001",),
    )
    assert ans_untrimmed.answer_text == untrimmed_text


def test_citation_resolution_valid_addresses_and_order():
    # AC5: accepts hit, witness, and retained supplemental-evidence addresses from exact supplied context;
    # preserves accepted citation order
    ctx = make_test_context()
    # In ctx:
    # Hit: H001
    # Witnesses: H001-W001, H001-W002
    # Supplemental: H001-E001 (obs), H001-E002 (fact1), H001-E003 (fact2)
    assert ctx.hits[0].citation_id == "H001"
    assert len(ctx.hits[0].hit.witnesses) == 2
    assert len(ctx.hits[0].supplemental_evidence) == 3

    ordered_citations = (
        "H001-E003",
        "H001",
        "H001-W002",
        "H001-E001",
        "H001-W001",
    )
    ans = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="16GB RAM and 2.1kg.",
        citation_ids=ordered_citations,
    )
    # Exact tuple and caller order preserved
    assert ans.citation_ids == ordered_citations


def test_citation_resolution_rejections_and_omitted_evidence():
    # AC5 & AC8: fabricated, duplicate, cross-context, omitted-evidence, malformed citations fail closed
    ctx = make_test_context()

    # Fabricated hit citation
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Answer",
            citation_ids=("H999", "H001-W001"),
        )
    assert "does not resolve in supplied context" in str(exc.value)

    # Fabricated witness citation
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Answer",
            citation_ids=("H001-W999",),
        )
    assert "does not resolve in supplied context" in str(exc.value)

    # Fabricated supplemental evidence citation
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Answer",
            citation_ids=("H001-E999",),
        )
    assert "does not resolve in supplied context" in str(exc.value)

    # Empty string citation
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Answer",
            citation_ids=("",),
        )
    assert "non-empty string" in str(exc.value)

    # Duplicate citations
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Answer",
            citation_ids=("H001-W001", "H001-W001"),
        )
    assert "duplicate citation_id: H001-W001" in str(exc.value)

    # Malformed citation strings
    for malformed in ["random", "H01", "H001_W001", "H001-W01", "H001-E01"]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=GroundedAnswerStatus.ANSWERED,
                answer_text="Answer",
                citation_ids=(malformed,),
            )
        assert "does not resolve in supplied context" in str(exc.value)

    # Cross-context citation:
    # Context 2 has variant 2 which will produce hit H002 in a 2-hit context
    m2 = make_member("m2")
    obs2 = CanonicalProfileObservation(
        member=m2,
        collector="c",
        title="Gaming Laptop 32GB RAM",
        shop_name="Shop2",
        brand="TopBrand",
        model_sku="SKU-200",
        description_text="High performance gaming laptop pro",
    )
    prof2 = make_profile("var-2", members=(m2,), observations=(obs2,))
    ctx_two_hits = build_canonical_rag_context(
        [ctx.hits[0].hit.profile, prof2],
        question="What is this?",
        retrieval_query="Gaming Laptop",
        max_hits=5,
    )
    assert len(ctx_two_hits.hits) == 2
    # ctx_two_hits has H002
    assert "H002" in [h.citation_id for h in ctx_two_hits.hits]

    # Trying to use H002 with ctx (which only has H001) must fail closed
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Answer",
            citation_ids=("H002-W001",),
        )
    assert "does not resolve in supplied context" in str(exc.value)

    # AC8: Omitted evidence due to M3 byte budgeting cannot be cited
    # Build a context with a very tight budget where some facts are omitted
    m3 = make_member("m3")
    obs3 = CanonicalProfileObservation(
        member=m3,
        collector="c",
        title="Compact Laptop",
        shop_name="Shop",
        brand="Brand",
        model_sku="SKU",
        description_text="Desc",
    )
    large_facts = tuple(
        CanonicalProfileFactEvidence(
            member=m3,
            fact=ProductFact(key=f"Key{i}", value="Val" * 400, source_section="S", provenance="P"),
        )
        for i in range(10)
    )
    prof3 = make_profile("var-budget", members=(m3,), observations=(obs3,), fact_evidence=large_facts)
    ctx_budget = build_canonical_rag_context(
        [prof3],
        question="What are features?",
        retrieval_query="Compact Laptop",
        max_context_utf8_bytes=4096,
    )
    assert ctx_budget.truncated is True
    assert ctx_budget.omitted_evidence_blocks > 0
    admitted_citation_ids = {
        block.citation_id for block in ctx_budget.hits[0].supplemental_evidence
    }
    omitted_id = "H001-E011"
    assert omitted_id not in admitted_citation_ids
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx_budget,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Features",
            citation_ids=(omitted_id,),
        )
    assert f"citation_id '{omitted_id}' does not resolve in supplied context" in str(exc.value)


def test_leaf_citation_rules_per_status():
    # AC6: ANSWERED requires >=1 valid leaf citation; CONFLICTING_EVIDENCE requires >=2 distinct valid leaf citations;
    # hit headers alone cannot satisfy those rules; INSUFFICIENT_EVIDENCE permits zero valid citations
    ctx = make_test_context()

    # --- ANSWERED ---
    # 0 citations fails
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Answer",
            citation_ids=(),
        )
    assert "ANSWERED status requires at least one valid witness or supplemental evidence leaf citation" in str(exc.value)

    # Hit header alone fails
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.ANSWERED,
            answer_text="Answer",
            citation_ids=("H001",),
        )
    assert "ANSWERED status requires at least one valid witness or supplemental evidence leaf citation" in str(exc.value)

    # 1 witness leaf succeeds
    ans_ans_w = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Answer",
        citation_ids=("H001-W001",),
    )
    assert ans_ans_w.citation_ids == ("H001-W001",)

    # 1 supplemental evidence leaf succeeds
    ans_ans_e = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Answer",
        citation_ids=("H001-E001",),
    )
    assert ans_ans_e.citation_ids == ("H001-E001",)

    # Hit header accompanying a leaf succeeds
    ans_ans_hw = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="Answer",
        citation_ids=("H001", "H001-W001"),
    )
    assert ans_ans_hw.citation_ids == ("H001", "H001-W001")

    # --- CONFLICTING_EVIDENCE ---
    # 0 citations fails
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
            answer_text="Answer with conflict",
            citation_ids=(),
            limitations=("Conflicting specs",),
        )
    assert "CONFLICTING_EVIDENCE status requires at least two distinct valid witness or supplemental evidence leaf citations" in str(exc.value)

    # Hit header alone fails
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
            answer_text="Answer with conflict",
            citation_ids=("H001",),
            limitations=("Conflicting specs",),
        )
    assert "CONFLICTING_EVIDENCE status requires at least two distinct valid witness or supplemental evidence leaf citations" in str(exc.value)

    # 1 leaf citation alone fails
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
            answer_text="Answer with conflict",
            citation_ids=("H001-W001",),
            limitations=("Conflicting specs",),
        )
    assert "CONFLICTING_EVIDENCE status requires at least two distinct valid witness or supplemental evidence leaf citations" in str(exc.value)

    # 1 hit header + 1 leaf citation fails
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
            answer_text="Answer with conflict",
            citation_ids=("H001", "H001-W001"),
            limitations=("Conflicting specs",),
        )
    assert "CONFLICTING_EVIDENCE status requires at least two distinct valid witness or supplemental evidence leaf citations" in str(exc.value)

    # 2 witness leaf citations succeeds
    ans_conf_w = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
        answer_text="Answer with conflict",
        citation_ids=("H001-W001", "H001-W002"),
        limitations=("Conflicting specs",),
    )
    assert ans_conf_w.citation_ids == ("H001-W001", "H001-W002")

    # 1 witness + 1 supplemental evidence leaf succeeds
    ans_conf_we = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
        answer_text="Answer with conflict",
        citation_ids=("H001-W001", "H001-E001"),
        limitations=("Conflicting specs",),
    )
    assert ans_conf_we.citation_ids == ("H001-W001", "H001-E001")

    # 2 supplemental evidence leaves + 1 hit header succeeds
    ans_conf_h_ee = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
        answer_text="Answer with conflict",
        citation_ids=("H001", "H001-E001", "H001-E002"),
        limitations=("Conflicting specs",),
    )
    assert ans_conf_h_ee.citation_ids == ("H001", "H001-E001", "H001-E002")

    # --- INSUFFICIENT_EVIDENCE ---
    # 0 citations succeeds
    ans_ins_0 = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="No sufficient evidence available.",
        citation_ids=(),
        limitations=("No evidence for query",),
    )
    assert ans_ins_0.citation_ids == ()

    # 1 hit header succeeds
    ans_ins_h = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="Listing found but details insufficient.",
        citation_ids=("H001",),
        limitations=("Listing lacks weight detail",),
    )
    assert ans_ins_h.citation_ids == ("H001",)

    # 1 leaf citation succeeds
    ans_ins_leaf = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="Listing found but details insufficient.",
        citation_ids=("H001-W001",),
        limitations=("Listing lacks weight detail",),
    )
    assert ans_ins_leaf.citation_ids == ("H001-W001",)


def test_no_hit_abstention():
    # AC6 & AC10: no-hit abstention permits zero valid citations
    prof = make_profile("var-nohit")
    ctx_nohit = build_canonical_rag_context(
        [prof],
        question="What is the price of the nonexistent gadget?",
        retrieval_query="NonexistentGadgetQuery999",
    )
    assert len(ctx_nohit.hits) == 0

    ans_nohit = create_grounded_answer(
        ctx_nohit,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="No matching products found in canonical knowledge base.",
        citation_ids=(),
        limitations=("Lexical retrieval returned zero hits for query.",),
    )
    assert ans_nohit.status == GroundedAnswerStatus.INSUFFICIENT_EVIDENCE
    assert ans_nohit.citation_ids == ()
    assert ans_nohit.limitations == ("Lexical retrieval returned zero hits for query.",)


def test_limitations_bounds_and_requirements():
    # AC7: limitations are bounded immutable ordered strings; non-answer statuses require >=1;
    # invalid/blank/oversized/excess fail closed; ANSWERED may have 0
    ctx = make_test_context()

    # ANSWERED with 0 limitations succeeds
    ans_ans = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="16GB RAM",
        citation_ids=("H001-W001",),
        limitations=(),
    )
    assert ans_ans.limitations == ()

    # ANSWERED with valid limitations succeeds
    ans_ans_lim = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="16GB RAM",
        citation_ids=("H001-W001",),
        limitations=("Only one listing checked",),
    )
    assert ans_ans_lim.limitations == ("Only one listing checked",)

    # INSUFFICIENT_EVIDENCE with 0 limitations fails closed
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
            answer_text="Cannot answer",
            citation_ids=(),
            limitations=(),
        )
    assert "INSUFFICIENT_EVIDENCE status requires at least one limitation" in str(exc.value)

    # CONFLICTING_EVIDENCE with 0 limitations fails closed
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
            answer_text="Conflict observed",
            citation_ids=("H001-W001", "H001-W002"),
            limitations=(),
        )
    assert "CONFLICTING_EVIDENCE status requires at least one limitation" in str(exc.value)

    # Blank / whitespace-only limitation item fails closed
    for bad_lim in ["", " ", "   ", "\t\n"]:
        with pytest.raises(GroundedAnswerError) as exc:
            create_grounded_answer(
                ctx,
                status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
                answer_text="Cannot answer",
                citation_ids=(),
                limitations=(bad_lim,),
            )
        assert "limitation item at index 0 must contain at least one non-whitespace character" in str(exc.value)

    # Exactly 2048 UTF-8 bytes limitation succeeds
    exact_2048_lim = "x" * 2048
    ans_2048 = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="Cannot answer",
        citation_ids=(),
        limitations=(exact_2048_lim,),
    )
    assert len(ans_2048.limitations[0].encode("utf-8")) == 2048

    # Oversized limitation (> 2048 bytes) fails closed
    oversized_lim = "x" * 2049
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
            answer_text="Cannot answer",
            citation_ids=(),
            limitations=(oversized_lim,),
        )
    assert "exceeds UTF-8 bound of 2048 bytes" in str(exc.value)

    # Exactly 16 limitation items succeeds
    lims_16 = tuple(f"Limitation {i}" for i in range(16))
    ans_16 = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="Cannot answer",
        citation_ids=(),
        limitations=lims_16,
    )
    assert len(ans_16.limitations) == 16
    assert ans_16.limitations == lims_16

    # Excess limitations (> 16 items) fails closed
    lims_17 = tuple(f"Limitation {i}" for i in range(17))
    with pytest.raises(GroundedAnswerError) as exc:
        create_grounded_answer(
            ctx,
            status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
            answer_text="Cannot answer",
            citation_ids=(),
            limitations=lims_17,
        )
    assert "limitations cannot contain more than 16 items, got 17" in str(exc.value)

    # Caller order is preserved and duplicate limitation strings are NOT deduplicated or normalized
    duplicate_lims = ("Same limitation", "Different limitation", "Same limitation")
    ans_dup_lims = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
        answer_text="Cannot answer",
        citation_ids=(),
        limitations=duplicate_lims,
    )
    assert ans_dup_lims.limitations == duplicate_lims


def test_context_immutability_and_source_evidence_unmutated():
    # AC8: Equal-looking/conflicting source values are not deduplicated or interpreted,
    # and answer construction does not mutate the canonical context or any source evidence
    m1 = make_member("m1")
    m2 = make_member("m2")

    fact1 = CanonicalProfileFactEvidence(
        member=m1,
        fact=ProductFact(key="Weight", value="1.5kg", source_section="S1", provenance="P1"),
    )
    fact2 = CanonicalProfileFactEvidence(
        member=m2,
        fact=ProductFact(key="Weight", value="2.0kg", source_section="S2", provenance="P2"),
    )
    fact3 = CanonicalProfileFactEvidence(
        member=m2,
        fact=ProductFact(key="Weight", value="1.5kg", source_section="S3", provenance="P3"),
    )

    prof = make_profile("var-conflict", members=(m1, m2), fact_evidence=(fact1, fact2, fact3))
    ctx = build_canonical_rag_context(
        [prof],
        question="What is the weight?",
        retrieval_query="Weight",
    )

    # Pre-checks
    original_hits = ctx.hits
    original_supplemental = ctx.hits[0].supplemental_evidence
    # 2 observations (1 per member) + 3 facts = 5 blocks
    assert len(original_supplemental) == 5

    ans = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.CONFLICTING_EVIDENCE,
        answer_text="Weight conflicts: 1.5kg vs 2.0kg.",
        citation_ids=("H001-E002", "H001-E004"),
        limitations=("Conflict between listings",),
    )

    # Context and evidence unmutated
    assert ctx.hits is original_hits
    assert ctx.hits[0].supplemental_evidence is original_supplemental
    assert ctx.hits[0].supplemental_evidence[1].source_evidence is fact1
    assert ctx.hits[0].supplemental_evidence[3].source_evidence is fact2
    assert ctx.hits[0].supplemental_evidence[4].source_evidence is fact3
    assert ans.context is ctx


def test_repeated_determinism_and_no_io():
    # AC9 & AC10: repeated determinism, pure in-memory validation, zero I/O or model calls
    ctx = make_test_context()

    ans1 = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="The laptop has 16GB RAM.",
        citation_ids=("H001-W001", "H001-E002"),
        limitations=("Advisory observation only",),
    )
    ans2 = create_grounded_answer(
        ctx,
        status=GroundedAnswerStatus.ANSWERED,
        answer_text="The laptop has 16GB RAM.",
        citation_ids=("H001-W001", "H001-E002"),
        limitations=("Advisory observation only",),
    )

    # Identical values and equality
    assert ans1 == ans2
    assert ans1.context is ans2.context is ctx
    assert ans1.status == ans2.status == GroundedAnswerStatus.ANSWERED
    assert ans1.answer_text == ans2.answer_text == "The laptop has 16GB RAM."
    assert ans1.citation_ids == ans2.citation_ids == ("H001-W001", "H001-E002")
    assert ans1.limitations == ans2.limitations == ("Advisory observation only",)
    assert hash(ans1) == hash(ans2)
