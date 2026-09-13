"""Structural regression for the canonical ChatGPT Project Contract."""

from pathlib import Path
import re


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


def test_project_contract_has_canonical_shape() -> None:
    text = _load_project_contract()

    assert text.startswith(
        "# ChatGPT Project Contract — Python Agent / Product Intelligence\n"
    )
    section_headings = re.findall(r"^## (\d+)\. (.+)$", text, flags=re.MULTILINE)
    assert [number for number, _ in section_headings] == [
        str(i) for i in range(1, 13)
    ]


def test_project_contract_preserves_governance_layers_and_precedence() -> None:
    text = _load_project_contract()

    layer_labels = [
        "Manifesto = WHY",
        "Constitution = highest enforceable governance",
        "Product Contract = WHAT",
        "Project Contract = HOW",
    ]
    for label in layer_labels:
        assert label in text

    assert "subordinate to the Constitution and Product Contract" in text
    positions = [text.index(label) for label in layer_labels]
    assert positions == sorted(positions), (
        "Governance Foundation layers must appear in order: "
        "Manifesto, Constitution, Product Contract, Project Contract"
    )
    assert "Manifesto -> Constitution" not in text
    assert (
        "Constitution -> Product Contract -> ChatGPT Project Contract" in text
    )
    normalized = " ".join(text.split())
    assert "never becomes executable conflict authority" in normalized
    assert (
        "deliberate constitutional departure from the Manifesto requires explicit Human amendment intent"
        in normalized
    )


def test_project_contract_binds_all_seven_constitutional_roles_without_merger() -> None:
    text = _load_project_contract()

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
        assert role_id in text

    assert "co-location" in text
    assert (
        "co-location does not merge their authorities" in text
        or "co-location must not merge authority" in text
    )


def test_project_contract_preserves_constitutional_authority_and_conflict_labels() -> None:
    text = _load_project_contract()

    for label in [
        "CAPABILITY_IS_NOT_AUTHORITY",
        "ONE_CAPABILITY_ONE_AUTHORITY",
        "GOVERNANCE_CONFLICT",
        "AUTHORITY_CONFLICT",
        "EVIDENCE_CONFLICT",
    ]:
        assert label in text


def test_project_contract_brain_sync_requires_full_governance_foundation() -> None:
    text = _load_project_contract()

    sync_section = text.split("## 12. Brain Sync Protocol\n", 1)[1]
    for doc in [
        "docs/PYTHON_AGENT_MANIFESTO.md",
        "docs/PYTHON_AGENT_CONSTITUTION.md",
        "docs/PYTHON_AGENT_PRODUCT_CONTRACT.md",
        "docs/CHATGPT_PROJECT_CONTRACT.md",
    ]:
        assert doc in sync_section


def test_project_contract_enforces_downstream_pin_isolation() -> None:
    text = _load_project_contract()

    assert ".agents/skills/aios-worker/requirements-aios-renew.txt" in text
    assert "active runtime must never be inferred from current AIOS-renew main" in text
    assert "improvement does not exist for Python Agent until" in text


def test_project_contract_enforces_source_only_review_and_publication() -> None:
    text = _load_project_contract()

    assert "Runtime PASS is not semantic PASS" in text
    assert "publish the reviewed source candidate only" in text
    for forbidden in [
        "review-decision commit",
        "artifact branch",
        "failure branch",
        "remediation metadata branch",
    ]:
        assert forbidden in text
