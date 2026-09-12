"""Structural regression for the canonical Python Agent Manifesto."""

from pathlib import Path
import re


MANIFESTO = Path(__file__).parents[2] / "docs" / "PYTHON_AGENT_MANIFESTO.md"


def _load_manifesto() -> str:
    raw = MANIFESTO.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "Manifesto must not contain a UTF-8 BOM"
    assert b"\r" not in raw, "Manifesto must use LF line endings"
    return raw.decode("utf-8")


def test_manifesto_has_canonical_shape() -> None:
    text = _load_manifesto()

    assert text.startswith("# Python Agent Manifesto\n")
    expected_sections = [
        "North Star",
        "Intelligence Doctrine",
        "Principles",
        "Refusals",
        "Governance Foundation",
        "Scope and Status",
    ]
    sections = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
    assert sections == expected_sections
    assert sections.count("Intelligence Doctrine") == 1
    assert sections.count("Refusals") == 1


def test_manifesto_has_exactly_twelve_ordered_principles() -> None:
    text = _load_manifesto()

    principle_ids = re.findall(r"^### (M\d+)\b", text, flags=re.MULTILINE)
    assert principle_ids == [f"M{number}" for number in range(1, 13)]
    assert len(principle_ids) == len(set(principle_ids))


def test_manifesto_names_the_four_distinct_governance_layers() -> None:
    text = _load_manifesto()
    governance = text.split("## Governance Foundation\n", 1)[1].split(
        "\n## Scope and Status\n", 1
    )[0]

    relationships = re.findall(
        r"^- \*\*(Manifesto|Constitution|Product Contract|ChatGPT Project Contract) = "
        r"(WHY|enforceable governance|WHAT|HOW):\*\*",
        governance,
        flags=re.MULTILINE,
    )
    assert relationships == [
        ("Manifesto", "WHY"),
        ("Constitution", "enforceable governance"),
        ("Product Contract", "WHAT"),
        ("ChatGPT Project Contract", "HOW"),
    ]
