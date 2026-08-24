"""Provider-neutral bounded executor outcome model and parsing (ADR-063 / TASK-088)."""
from __future__ import annotations

from enum import Enum
import re

from src.aios_bridge.continuity.errors import ContinuityStateValidationError

AIOS_EXECUTOR_OUTCOME_PREFIX = "AIOS_EXECUTOR_OUTCOME:"
_OUTCOME_MARKER_RE = re.compile(r"^AIOS_EXECUTOR_OUTCOME:\s*([A-Z_]+)\s*$", re.MULTILINE)


class ExecutorOutcomeCode(str, Enum):
    """Closed, provider-neutral vocabulary of diagnostic execution outcomes (ADR-063)."""

    IMPLEMENTED = "IMPLEMENTED"
    BLOCKED = "BLOCKED"
    NO_WORK_REQUIRED = "NO_WORK_REQUIRED"
    INSTRUCTION_CONFLICT = "INSTRUCTION_CONFLICT"
    UNKNOWN = "UNKNOWN"


ALLOWED_OUTCOME_CODES = frozenset(c.value for c in ExecutorOutcomeCode)


class FinalAgentMessageObservation(str, Enum):
    """Observation status of the worker's final explicit agent response message."""

    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


ALLOWED_FINAL_MESSAGE_OBSERVATION_STATUSES = frozenset(
    s.value for s in FinalAgentMessageObservation
)


def parse_executor_outcome_code(value: object) -> ExecutorOutcomeCode:
    """Safely parse or normalize an outcome value into an exact ExecutorOutcomeCode."""
    if isinstance(value, ExecutorOutcomeCode):
        return value
    if type(value) is str:
        s = value.strip()
        if s in ALLOWED_OUTCOME_CODES:
            return ExecutorOutcomeCode(s)
    return ExecutorOutcomeCode.UNKNOWN


def parse_final_agent_message_observation(value: object) -> FinalAgentMessageObservation:
    """Safely parse or normalize final agent message observation status."""
    if isinstance(value, FinalAgentMessageObservation):
        return value
    if type(value) is str:
        s = value.strip()
        if s in ALLOWED_FINAL_MESSAGE_OBSERVATION_STATUSES:
            return FinalAgentMessageObservation(s)
    return FinalAgentMessageObservation.UNKNOWN


def validate_activity_count(value: object, field_name: str) -> int | str:
    """Validate activity count field: non-negative integer or exact string 'UNKNOWN'."""
    if type(value) is str and value == "UNKNOWN":
        return "UNKNOWN"
    if type(value) is int and not isinstance(value, bool) and value >= 0:
        return value
    raise ContinuityStateValidationError(
        f"{field_name} must be non-negative int (bool forbidden) or exact 'UNKNOWN': got {value!r}"
    )


def extract_terminal_outcome_from_text(text: str | None) -> ExecutorOutcomeCode:
    """Extract terminal AIOS_EXECUTOR_OUTCOME marker from message text.

    Returns exact ExecutorOutcomeCode if a single unambiguous marker is found,
    or UNKNOWN if absent, ambiguous, or invalid.
    """
    if not isinstance(text, str) or not text.strip():
        return ExecutorOutcomeCode.UNKNOWN

    matches = _OUTCOME_MARKER_RE.findall(text)
    if len(matches) == 1:
        raw = matches[0].strip()
        if raw in ALLOWED_OUTCOME_CODES:
            return ExecutorOutcomeCode(raw)

    return ExecutorOutcomeCode.UNKNOWN


__all__ = [
    "AIOS_EXECUTOR_OUTCOME_PREFIX",
    "ALLOWED_FINAL_MESSAGE_OBSERVATION_STATUSES",
    "ALLOWED_OUTCOME_CODES",
    "ExecutorOutcomeCode",
    "FinalAgentMessageObservation",
    "extract_terminal_outcome_from_text",
    "parse_executor_outcome_code",
    "parse_final_agent_message_observation",
    "validate_activity_count",
]
