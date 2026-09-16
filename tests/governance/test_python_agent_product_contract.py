"""Structural regression for the canonical Python Agent Product Contract."""

from pathlib import Path
import re


PRODUCT_CONTRACT = (
    Path(__file__).parents[2] / "docs" / "PYTHON_AGENT_PRODUCT_CONTRACT.md"
)

ARTICLE_HEADINGS = [
    "PC1 — PRODUCT IDENTITY AND COMMERCE DECISION NORTH STAR",
    "PC2 — EVIDENCE, KNOWLEDGE, UNCERTAINTY, AND TIME",
    "PC3 — HYPOTHESIS, OPPORTUNITY, PREDICTION, AND CAUSALITY",
    "PC4 — DECISION-READY INTELLIGENCE",
    "PC5 — VALUE OF INFORMATION, MEASUREMENT, AND CALIBRATION",
    "PC6 — COMPOSABLE DOMAIN INTELLIGENCE AND COMMERCE INTELLIGENCE",
    "PC7 — AUTHORIZED ACTION, OUTCOME, ATTRIBUTION, AND LEARNING",
    "PC8 — CAPABILITY HONESTY, SUBSTRATE NEUTRALITY, AND PRODUCT EVOLUTION",
]

GOVERNANCE_FOUNDATION_LABELS = [
    "Manifesto = WHY",
    "Constitution = enforceable governance and authority",
    "Product Contract = WHAT",
    "Project Contract = HOW the Brain operates engineering work",
]

DURABLE_BOUNDARY_LABELS = [
    "INTELLIGENCE_IS_DECISION_RELATIVE",
    "EVIDENCE_IS_NOT_KNOWLEDGE",
    "EVIDENCE_IS_NOT_PRODUCT_TRUTH",
    "SOURCE_IDENTITY_IS_NOT_CANONICAL_IDENTITY",
    "SNAPSHOT_IS_NOT_TREND",
    "PREDICTION_IS_NOT_TRUTH",
    "HYPOTHESIS_IS_NOT_TRUTH",
    "OPPORTUNITY_IS_CONTEXTUAL",
    "RANKING_IS_CONTEXTUAL",
    "CORRELATION_IS_NOT_CAUSATION",
    "KNOWLEDGE_IS_NOT_INTELLIGENCE",
    "SCORE_IS_NOT_INTELLIGENCE",
    "RECOMMENDATION_IS_NOT_DECISION",
    "INTELLIGENCE_IS_NOT_DECISION",
    "MORE_DATA_IS_NOT_MORE_INTELLIGENCE",
    "MEASUREMENT_IS_NOT_AUTHORITY",
    "CONFIDENCE_IS_NOT_CERTAINTY",
    "EXPECTED_VALUE_IS_NOT_GUARANTEE",
    "DOMAIN_SCORE_IS_NOT_COMMERCE_DECISION",
    "AUTOMATION_IS_NOT_INTELLIGENCE",
    "ACTION_CHANGES_EVIDENCE",
    "OUTCOME_IS_NOT_ATTRIBUTION",
    "OUTCOME_IS_NOT_RETROACTIVE_PROOF",
    "LEARNING_IS_NOT_SELF_AUTHORIZATION",
    "CERTIFICATION_IS_BOUNDED",
]


def _load_product_contract() -> str:
    raw = PRODUCT_CONTRACT.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), (
        "Product Contract must not contain a UTF-8 BOM"
    )
    assert b"\r" not in raw, "Product Contract must use LF line endings"
    return raw.decode("utf-8")


def test_product_contract_has_exact_identity_and_article_order() -> None:
    text = _load_product_contract()

    assert text.splitlines()[:4] == [
        "# Python Agent Product Contract",
        "",
        "Status: DURABLE PRODUCT CONTRACT",
        "Scope: Durable product semantics for `trung-via/python_complete_agent`",
    ]
    assert text.count("# Python Agent Product Contract") == 1
    assert text.count("Status: DURABLE PRODUCT CONTRACT") == 1
    assert text.count(
        "Scope: Durable product semantics for `trung-via/python_complete_agent`"
    ) == 1
    assert re.findall(r"^## (PC\d+ — .+)$", text, flags=re.MULTILINE) == (
        ARTICLE_HEADINGS
    )
    assert text.count("## Canonical Product Principle") == 1


def test_product_contract_preserves_governance_foundation() -> None:
    text = _load_product_contract()

    for label in GOVERNANCE_FOUNDATION_LABELS:
        assert text.count(label) == 1


def test_product_contract_names_each_durable_boundary_once() -> None:
    text = _load_product_contract()

    for label in DURABLE_BOUNDARY_LABELS:
        assert text.count(label) == 1
