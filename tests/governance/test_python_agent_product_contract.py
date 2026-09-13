"""Structural regression for the canonical Python Agent Product Contract."""

from pathlib import Path
import re


PRODUCT_CONTRACT = (
    Path(__file__).parents[2] / "docs" / "PYTHON_AGENT_PRODUCT_CONTRACT.md"
)


def _load_product_contract() -> str:
    raw = PRODUCT_CONTRACT.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), (
        "Product Contract must not contain a UTF-8 BOM"
    )
    assert b"\r" not in raw, "Product Contract must use LF line endings"
    return raw.decode("utf-8")


def test_product_contract_has_exact_ordered_articles() -> None:
    text = _load_product_contract()

    assert text.startswith("# Python Agent Product Contract\n")
    article_headings = re.findall(
        r"^## (PC\d+) ([A-Z_]+)$", text, flags=re.MULTILINE
    )
    assert article_headings == [
        ("PC1", "PRODUCT_IDENTITY_SCOPE_AND_NORTH_STAR"),
        ("PC2", "OBSERVATION_EVIDENCE_UNCERTAINTY_AND_TIME"),
        ("PC3", "KNOWLEDGE_IDENTITY_PERSISTENCE_AND_TRUTH_BOUNDARIES"),
        ("PC4", "HYPOTHESIS_INTELLIGENCE_AND_DISCONFIRMATION"),
        ("PC5", "DISCOVERY_SCORING_RANKING_RECOMMENDATION_AND_APPROVAL"),
        ("PC6", "RETRIEVAL_CONTEXT_GROUNDED_ANSWERS_AND_TRUTH"),
        ("PC7", "DECISION_QUALITY_VALUE_OF_INFORMATION_AND_CALIBRATION"),
        ("PC8", "AUTHORIZED_ACTION_OUTCOME_LEARNING_AND_BOUNDED_AUTOMATION"),
        ("PC9", "COMPOSABLE_COMMERCE_INTELLIGENCE_AND_SUBSTRATE_NEUTRALITY"),
        ("PC10", "CAPABILITY_HONESTY_EVOLUTION_AND_NON_CLAIMS"),
    ]
    assert re.findall(r"^## PC\d+\b", text, flags=re.MULTILINE) == [
        f"## PC{number}" for number in range(1, 11)
    ]


def test_product_contract_preserves_governance_layers() -> None:
    text = _load_product_contract()

    layer_labels = [
        "Manifesto = WHY",
        "Constitution = highest enforceable governance",
        "Product Contract = WHAT",
        "ChatGPT Project Contract = HOW",
    ]
    for label in layer_labels:
        assert text.count(label) == 1


def test_product_contract_names_each_durable_boundary_once() -> None:
    text = _load_product_contract()

    boundary_labels = [
        "EVIDENCE_IS_NOT_KNOWLEDGE",
        "EVIDENCE_IS_NOT_PRODUCT_TRUTH",
        "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
        "KNOWLEDGE_IS_NOT_INTELLIGENCE",
        "HYPOTHESIS_IS_NOT_TRUTH",
        "INTELLIGENCE_IS_NOT_DECISION",
        "PREDICTION_IS_NOT_TRUTH",
        "SCORE_IS_NOT_APPROVAL",
        "RETRIEVAL_IS_NOT_RANKING",
        "CONTEXT_IS_NOT_TRUTH",
        "RECOMMENDATION_IS_NOT_DECISION",
        "CONFIDENCE_IS_NOT_CERTAINTY",
        "SNAPSHOT_IS_NOT_TREND",
        "AUTOMATION_IS_NOT_INTELLIGENCE",
        "MEASUREMENT_IS_NOT_AUTHORITY",
        "OUTCOME_IS_NOT_RETROACTIVE_PROOF",
        "CERTIFICATION_IS_BOUNDED",
    ]
    for label in boundary_labels:
        assert text.count(label) == 1

