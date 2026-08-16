"""Structural validation helpers for External Brain output artifacts."""
from __future__ import annotations

import re
from typing import Mapping

from .contracts import BrainOutputType
from .errors import OutputContractError

REQUIRED_SECTIONS: Mapping[BrainOutputType, tuple[str, ...]] = {
    BrainOutputType.PLAN: ("SUMMARY", "STEPS", "FILES", "TESTS", "RISKS"),
    BrainOutputType.PATCH_PROPOSAL: ("SUMMARY", "FILES", "PATCH", "TESTS", "RISKS"),
    BrainOutputType.DIAGNOSIS: ("CAUSE", "EVIDENCE", "FIX", "TESTS", "RISKS"),
    BrainOutputType.REVIEW: ("STATUS", "FINDINGS", "TESTS", "RISKS"),
}

ALLOWED_REVIEW_STATUSES: frozenset[str] = frozenset({"PASS", "CHANGES_REQUIRED"})

# Regex to match markdown headings like `# SECTION`, `## SECTION`, `### SECTION`, `**SECTION:**`, or `SECTION:` at start of line
_SECTION_HEADER_RE = re.compile(
    r"^(?:#{1,6}\s+([A-Za-z0-9_ ]+?)\s*|\*{2}([A-Za-z0-9_ ]+?)\*{2}\s*:?|([A-Za-z0-9_]+)\s*:)\s*$",
    re.MULTILINE,
)


def parse_artifact_sections(content: str) -> dict[str, str]:
    """
    Parses a Markdown artifact into a dictionary of normalized upper-case section names to section contents.
    """
    if not isinstance(content, str) or not content.strip():
        raise OutputContractError("Artifact content must be a non-empty string")

    # Find all potential section headers
    matches = list(_SECTION_HEADER_RE.finditer(content))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        raw_header = match.group(1) or match.group(2) or match.group(3) or ""
        header = raw_header.strip().upper().rstrip(" :").strip()
        start_idx = match.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start_idx:end_idx].strip()
        sections[header] = body

    return sections


def validate_artifact_structure(output_type: BrainOutputType, content: str) -> dict[str, str]:
    """
    Validates that artifact content complies with the required structural sections for output_type.
    Returns the parsed section dictionary if valid, or raises OutputContractError.
    """
    if not isinstance(output_type, BrainOutputType):
        try:
            output_type = BrainOutputType(output_type)
        except Exception as e:
            raise OutputContractError(f"Invalid BrainOutputType: {output_type}") from e

    expected_sections = REQUIRED_SECTIONS.get(output_type)
    if expected_sections is None:
        raise OutputContractError(f"No section requirements defined for output_type: {output_type}")

    sections = parse_artifact_sections(content)

    missing = [sec for sec in expected_sections if sec not in sections or not sections[sec].strip()]
    if missing:
        raise OutputContractError(
            f"Artifact of type {output_type.value} is missing required non-empty sections: {', '.join(missing)}"
        )

    # Additional validations for specific output types
    if output_type == BrainOutputType.REVIEW:
        status_text = sections["STATUS"].strip()
        # Find exact PASS or CHANGES_REQUIRED in the status text
        first_line = status_text.splitlines()[0].strip().upper().rstrip(".")
        # Handle cases like `STATUS: PASS` or `**PASS**` or `PASS`
        cleaned_status = re.sub(r"[^A-Z_]", "", first_line)
        if cleaned_status not in ALLOWED_REVIEW_STATUSES:
            raise OutputContractError(
                f"Invalid REVIEW status: {status_text!r}. Allowed statuses are: {', '.join(sorted(ALLOWED_REVIEW_STATUSES))}"
            )

    return sections
