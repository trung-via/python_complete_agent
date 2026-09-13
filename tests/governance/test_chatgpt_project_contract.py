"""Regressions for the suspended transitional Project Contract HOW slot."""

from pathlib import Path
import re


PROJECT_CONTRACT = (
    Path(__file__).parents[2] / "docs" / "CHATGPT_PROJECT_CONTRACT.md"
)


def _load_project_contract() -> str:
    raw = PROJECT_CONTRACT.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    return raw.decode("utf-8")


def test_project_contract_remains_the_suspended_constitutional_how_slot() -> None:
    text = _load_project_contract()
    normalized = " ".join(text.split())

    assert text.startswith(
        "# ChatGPT Project Contract — Python Agent / Product Intelligence\n"
    )
    assert "Status: SUSPENDED AND SUPERSEDED TRANSITIONAL NOTICE" in text
    assert (
        "Project Contract = HOW slot required by the Python Agent Constitution"
        in normalized
    )
    assert "explicit Human Principal intent" in normalized
    assert (
        "previous detailed ChatGPT Project Contract is superseded and suspended"
        in normalized
    )
    assert "no longer has active HOW authority" in normalized


def test_transitional_notice_preserves_subordination_without_detailed_rules() -> None:
    text = _load_project_contract()
    normalized = " ".join(text.split())

    assert "Constitution remains the highest enforceable governance" in normalized
    assert "Product Contract remains the authoritative WHAT layer" in normalized
    assert "remain subordinate to both" in normalized
    assert "contains no durable detailed operating rules" in normalized
    assert "creates no new precedence system or product semantics" in normalized
    assert len(re.findall(r"^## ", text, flags=re.MULTILINE)) <= 3
    assert not re.search(r"^## \d+\.", text, flags=re.MULTILINE)
    assert len(text.split()) < 300


def test_exact_pin_continuity_is_separately_adopted_capability_only() -> None:
    text = _load_project_contract()
    normalized = " ".join(text.split())

    assert (
        "Exact pinned AIOS mechanics remain available only through separately adopted"
        in normalized
    )
    assert "Their availability is capability, not authority" in normalized
    assert (
        "does not grant or change review, execution, canonical mutation, roadmap, "
        "publication, or domain authority"
        in normalized
    )
    assert (
        "no local carrier is designated as the exclusive Brain authoring transport"
        in normalized
    )
    assert "Brain authoring for this repository must use the checked-in" not in text


def test_full_replacement_requires_complete_text_and_explicit_human_approval() -> None:
    text = _load_project_contract()
    normalized = " ".join(text.split())

    assert "Before any later durable replacement is canonicalized" in normalized
    assert "complete proposed replacement text must be freshly audited" in normalized
    assert "presented in full to the Human Principal" in normalized
    assert "explicitly approved by the Human Principal" in normalized
    assert "partial draft" in normalized
    assert "is not approval of the full replacement" in normalized
