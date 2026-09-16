"""Structural regressions for the durable Project Contract HOW layer."""

import re
from pathlib import Path


PROJECT_CONTRACT = (
    Path(__file__).parents[2] / "docs" / "CHATGPT_PROJECT_CONTRACT.md"
)


def _load_project_contract() -> str:
    raw = PROJECT_CONTRACT.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), (
        "Project Contract must not contain a UTF-8 BOM"
    )
    assert b"\r" not in raw, "Project Contract must use LF line endings"
    return raw.decode("utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_durable_identity_and_exact_pjc_order() -> None:
    text = _load_project_contract()

    assert text.startswith(
        "# ChatGPT Project Contract — Python Agent\n\n"
        "Status: DURABLE PROJECT CONTRACT\n"
    )
    headings = re.findall(r"^## (PJC\d+) — ", text, flags=re.MULTILINE)
    assert headings == [f"PJC{number}" for number in range(1, 9)]
    assert len(headings) == len(set(headings))


def test_governance_layers_and_subordinate_how_boundary() -> None:
    normalized = _normalized(_load_project_contract())

    for layer in (
        "Manifesto = WHY.",
        "Constitution = enforceable governance and authority.",
        "Product Contract = WHAT.",
        "Project Contract = HOW the Brain operates engineering work.",
    ):
        assert layer in normalized

    assert "subordinate to the Python Agent Constitution" in normalized
    assert "does not define product meaning, create product semantics" in normalized
    assert "must not become a second Product Contract, a second Constitution" in normalized
    assert "downstream copy of AIOS lifecycle semantics" in normalized


def test_canonical_context_is_progressive_minimum_sufficient_and_durable() -> None:
    normalized = _normalized(_load_project_contract())

    assert "Canonical repository state is the durable shared memory" in normalized
    assert "not canonical authority" in normalized
    assert "override current canonical repository evidence" in normalized
    assert "Context acquisition is progressive" in normalized
    assert "smallest authoritative context sufficient" in normalized
    assert "could materially change that decision" in normalized
    assert "Do not audit the entire repository" in normalized
    assert "Cross-chat continuity is reconstructed from canonical state" in normalized
    assert "affected mutation fails closed until reconciled" in normalized


def test_intelligent_decision_reuse_and_uncertainty_boundaries() -> None:
    text = _load_project_contract()
    normalized = _normalized(text)

    assert "decision-relevant information, not maximum activity" in normalized
    assert "reused until the state that supports them is materially invalidated" in normalized
    assert "Do not pay twice for unchanged work" in normalized
    assert re.findall(
        r"^### (Semantic uncertainty|Canonical-state uncertainty|Analytical uncertainty)$",
        text,
        flags=re.MULTILINE,
    ) == [
        "Semantic uncertainty",
        "Canonical-state uncertainty",
        "Analytical uncertainty",
    ]
    assert "Uncertainty does not automatically block analysis" in normalized
    assert "not to unrelated reasoning or project activity" in normalized
    assert "Prefer deterministic resolution" in normalized


def test_human_brain_and_roadmap_boundaries() -> None:
    normalized = _normalized(_load_project_contract())

    assert "The Human Principal owns product intent, priority, mandate" in normalized
    assert "The Brain owns semantic engineering judgment within that mandate" in normalized
    assert "Intelligence is not permission to enlarge scope" in normalized
    assert "already deterministically resolved by canonical state" in normalized
    assert "Roadmap state is Brain-owned planning state, not engineering-state truth" in normalized
    assert "unique current canonical NEXT commitment after reconciling" in normalized
    assert "must be canonicalized through the appropriate planning authority" in normalized
    assert "do not independently own Human/Brain roadmap priority" in normalized


def test_aios_delegation_exact_pin_isolation_and_role_separation() -> None:
    text = _load_project_contract()
    normalized = _normalized(text)

    assert "exact downstream dependency" in normalized
    assert "Mutable upstream AIOS `main` is not automatically downstream authority" in normalized
    assert "must not recreate, approximate, locally fork, or reinterpret" in normalized
    assert "Repository binding and package capability remain distinct" in normalized
    assert "Exactly one admitted Executor owns HOW" in normalized
    assert "Runtime owns deterministic coordination" in normalized
    assert "Semantic Reviewer owns independent judgment" in normalized
    assert "Publisher owns publication of the exact eligible reviewed source candidate" in normalized
    assert "Co-location of roles" in normalized
    assert not re.search(r"\b[0-9a-f]{40}\b", text, flags=re.IGNORECASE)


def test_contract_evolution_requires_complete_text_review_and_exact_publication() -> None:
    normalized = _normalized(_load_project_contract())

    required_steps = (
        "presentation of the complete proposed Project Contract text",
        "explicit Human approval of that complete text",
        "a bounded canonical change",
        "independent semantic review",
        "publication of exactly the reviewed source candidate",
    )
    positions = [normalized.index(step) for step in required_steps]
    assert positions == sorted(positions)
    assert "Approval of a summary, outline, isolated clause" in normalized
    assert "is not approval of a different complete Project Contract" in normalized
    assert "must not silently amend the Constitution or Product Contract" in normalized


def test_retired_operational_detail_is_absent() -> None:
    text = _load_project_contract()

    forbidden_patterns = (
        r"\b(?:TASK|RUN|REVIEW)-\d+(?:-\d+)?\b",
        r"\.github/workflows(?:/|\\)",
        r"\[AIOS BRAIN(?:\s|\])",
        r"\bCODE_FIX\b",
        r"\bNO_CHANGE\b",
        r"\bCONTINUE_IMPLEMENTATION\b",
    )
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text)
