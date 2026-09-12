"""Structural regression for the canonical Python Agent Constitution."""

from pathlib import Path
import re


CONSTITUTION = (
    Path(__file__).parents[2] / "docs" / "PYTHON_AGENT_CONSTITUTION.md"
)


def _load_constitution() -> str:
    raw = CONSTITUTION.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), (
        "Constitution must not contain a UTF-8 BOM"
    )
    assert b"\r" not in raw, "Constitution must use LF line endings"
    return raw.decode("utf-8")


def test_constitution_has_canonical_shape() -> None:
    text = _load_constitution()

    assert text.startswith("# Python Agent Constitution\n")
    article_headings = re.findall(r"^## (C\d+) ([A-Z_]+)$", text, flags=re.MULTILINE)
    assert article_headings == [
        ("C1", "CONSTITUTIONAL_SCOPE_AND_SUPREMACY"),
        ("C2", "CONSTITUTIONAL_ROLES"),
        ("C3", "HUMAN_SOVEREIGNTY_AND_BOUNDED_DELEGATION"),
        ("C4", "CANONICAL_STATE_AND_MUTATION_AUTHORITY"),
        ("C5", "ONE_CAPABILITY_ONE_AUTHORITY"),
        ("C6", "EPISTEMIC_AND_DECISION_BOUNDARY_LAW"),
        ("C7", "CONFLICT_PRECEDENCE_AND_FAIL_CLOSED"),
        ("C8", "COMPOSITION_AND_SUBSTRATE_NEUTRALITY"),
        ("C9", "COMPLIANCE_AND_ENFORCEMENT"),
        ("C10", "AMENDMENT_AND_TRANSITION"),
    ]
    assert re.findall(r"^## C\d+\b", text, flags=re.MULTILINE) == [
        f"## C{number}" for number in range(1, 11)
    ]


def test_constitution_names_each_abstract_role_once() -> None:
    text = _load_constitution()
    role_ids = [
        "HUMAN_PRINCIPAL",
        "ARCHITECT",
        "DOMAIN_AUTHORITY",
        "EXECUTION_RUNTIME",
        "EXECUTOR",
        "SEMANTIC_REVIEWER",
        "SOURCE_PUBLISHER",
    ]

    for role_id in role_ids:
        assert len(re.findall(rf"(?<![A-Z_]){role_id}(?![A-Z_])", text)) == 1


def test_constitution_names_governance_and_conflict_labels() -> None:
    text = _load_constitution()

    for label in [
        "Manifesto = WHY",
        "Constitution = highest enforceable governance",
        "Product Contract = WHAT",
        "Project Contract = HOW",
        "GOVERNANCE_CONFLICT",
        "AUTHORITY_CONFLICT",
        "EVIDENCE_CONFLICT",
        "CAPABILITY_IS_NOT_AUTHORITY",
        "ONE_CAPABILITY_ONE_AUTHORITY",
    ]:
        assert label in text


def test_constitution_contains_amendment_and_transition_sections() -> None:
    text = _load_constitution()
    sections = re.findall(r"^### (Amendment|Transition)$", text, flags=re.MULTILINE)
    assert sections == ["Amendment", "Transition"]
