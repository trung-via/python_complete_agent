"""Tests for External Brain output artifact structural validation."""
from __future__ import annotations

import pytest

from src.aios_bridge.external_brain import (
    BrainOutputType,
    OutputContractError,
    validate_artifact_structure,
)


def test_plan_structural_validation():
    """PLAN artifact with all required non-empty sections passes validation."""
    valid_plan = """# SUMMARY
Implement the contract foundation for External Brain.

## STEPS
1. Define enums
2. Create dataclasses
3. Add tests

## FILES
- src/aios_bridge/external_brain/contracts.py
- tests/aios_bridge/external_brain/test_contracts.py

## TESTS
Run pytest on the test suite.

## RISKS
Minimal risk as contracts are additive only.
"""
    sections = validate_artifact_structure(BrainOutputType.PLAN, valid_plan)
    assert "SUMMARY" in sections
    assert "STEPS" in sections
    assert "FILES" in sections
    assert "TESTS" in sections
    assert "RISKS" in sections

    # Missing section fails
    missing_steps_plan = """# SUMMARY
Just summary.
## FILES
None
## TESTS
None
## RISKS
None
"""
    with pytest.raises(OutputContractError, match="missing required non-empty sections: STEPS"):
        validate_artifact_structure(BrainOutputType.PLAN, missing_steps_plan)


def test_patch_proposal_structural_validation_and_data_treatment():
    """PATCH_PROPOSAL requires SUMMARY, FILES, PATCH, TESTS, RISKS and treats patch as data only."""
    valid_patch = """## SUMMARY
Fix typo in file.

## FILES
- src/main.py

## PATCH
```diff
- foo
+ bar
```

## TESTS
pytest

## RISKS
None
"""
    sections = validate_artifact_structure(BrainOutputType.PATCH_PROPOSAL, valid_patch)
    assert sections["PATCH"] == "```diff\n- foo\n+ bar\n```"

    # Missing PATCH section fails
    incomplete_patch = """## SUMMARY
Summary
## FILES
Files
## TESTS
Tests
## RISKS
Risks
"""
    with pytest.raises(OutputContractError, match="missing required non-empty sections: PATCH"):
        validate_artifact_structure(BrainOutputType.PATCH_PROPOSAL, incomplete_patch)


def test_diagnosis_structural_validation():
    """DIAGNOSIS requires CAUSE, EVIDENCE, FIX, TESTS, RISKS."""
    valid_diag = """## CAUSE
Null pointer dereference in parser.

## EVIDENCE
Traceback at line 45.

## FIX
Add null check before accessing property.

## TESTS
Add test_null_input.

## RISKS
Low.
"""
    sections = validate_artifact_structure(BrainOutputType.DIAGNOSIS, valid_diag)
    assert sections["CAUSE"] == "Null pointer dereference in parser."
    assert sections["FIX"] == "Add null check before accessing property."

    # Missing FIX section fails
    missing_fix = """## CAUSE
Cause
## EVIDENCE
Evidence
## TESTS
Tests
## RISKS
Risks
"""
    with pytest.raises(OutputContractError, match="missing required non-empty sections: FIX"):
        validate_artifact_structure(BrainOutputType.DIAGNOSIS, missing_fix)


def test_review_structural_validation_and_allowed_statuses():
    """REVIEW requires STATUS (PASS or CHANGES_REQUIRED), FINDINGS, TESTS, RISKS."""
    valid_pass = """## STATUS
PASS

## FINDINGS
Everything looks clean and conforms to ADR-005.

## TESTS
50/50 tests passed.

## RISKS
Zero regressions.
"""
    sections_pass = validate_artifact_structure(BrainOutputType.REVIEW, valid_pass)
    assert "PASS" in sections_pass["STATUS"]

    valid_changes = """## STATUS
CHANGES_REQUIRED

## FINDINGS
Missing edge-case test for invalid SHA-256.

## TESTS
Add regression test.

## RISKS
Potential bug in future validation.
"""
    sections_changes = validate_artifact_structure(BrainOutputType.REVIEW, valid_changes)
    assert "CHANGES_REQUIRED" in sections_changes["STATUS"]

    # Unsupported status fails
    invalid_status = """## STATUS
APPROVED

## FINDINGS
Looks good.

## TESTS
Passed.

## RISKS
None.
"""
    with pytest.raises(OutputContractError, match="Invalid REVIEW status: 'APPROVED'"):
        validate_artifact_structure(BrainOutputType.REVIEW, invalid_status)
