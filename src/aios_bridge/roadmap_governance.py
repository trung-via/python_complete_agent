"""Deterministic local-only canonical roadmap governance (ADR-050 / TASK-077).

This module validates authority evidence.  It performs no filesystem, Git,
network, model, executor, lease, dispatch, review-state, or merge operations.
Exact roadmap bytes and provenance are always supplied by the caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

from src.aios_bridge.continuity.errors import ContinuityStateValidationError


ROADMAP_FINGERPRINT_ALGORITHM_VERSION = "roadmap-sha256-v1"
ROADMAP_BINDING_MARKER = "ROADMAP_BINDING_JSON:"

H_SERIES_ROADMAP_ID = "AIOS-ENGINEERING-H-SERIES"
H_SERIES_ROADMAP_VERSION = "1.0"
H_SERIES_ROADMAP_PATH = ".ai/roadmaps/H-SERIES-v1.0.md"
H_SERIES_ROADMAP_BLOB_SHA = "41775383879c86dc68a7d87c0d705cfc8512f62d"

MAX_BINDING_JSON_BYTES = 32768
MAX_BINDING_LIST_ITEMS = 64
MAX_BINDING_STRING_CHARS = 512
MAX_EVIDENCE_CHARS = 2048

_BLOB_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_FINGERPRINT_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_IDENTITY_RE = re.compile(r"\A[A-Z0-9][A-Z0-9_.-]{0,127}\Z")
_VERSION_RE = re.compile(r"\A[0-9][A-Za-z0-9_.-]{0,63}\Z")
_MILESTONE_RE = re.compile(r"\A[A-Z][A-Z0-9_.-]{0,63}\Z")
_H_MILESTONE_RE = re.compile(r"\AH(?:0|[1-9][0-9]*)\Z")
_CAPABILITY_RE = re.compile(r"\A[A-Z][A-Z0-9_]{1,127}\Z")
_REQUIREMENT_RE = re.compile(r"\A([A-Z][A-Z0-9_.-]{0,63})\.R([1-9][0-9]*)\Z")
_ROADMAP_FIELD_RE = re.compile(
    r"\A(ROADMAP_ID|ROADMAP_VERSION|STATUS|AUTHORITY):\s*(\S(?:.*\S)?)\s*\Z"
)
_MILESTONE_HEADING_RE = re.compile(r"\A###\s+([A-Z][A-Z0-9_.-]{0,63})\s+(?:—|-)\s+(.+?)\s*\Z")
_CAPABILITY_LINE_RE = re.compile(r"\ACAPABILITY_ID:\s*(\S+)\s*\Z")
_REQUIREMENT_LINE_RE = re.compile(r"\A-\s+([A-Z][A-Z0-9_.-]{0,63}\.R[1-9][0-9]*)\s+(?:—|-)\s+(.+?)\s*\Z")
_HEADER_FIELD_RE = re.compile(r"\A([A-Z][A-Z0-9_]*)\s*:\s*(.*?)\s*\Z")
_H_CLAIM_RE = re.compile(r"(?<![A-Z0-9])H(?:0|[1-9][0-9]*)(?![A-Z0-9])")


class RoadmapGovernanceError(ContinuityStateValidationError):
    """Fail-closed deterministic roadmap-governance validation error."""


class RoadmapStatus(str, Enum):
    DRAFT = "DRAFT"
    LOCKED = "LOCKED"
    SUPERSEDED = "SUPERSEDED"


class RoadmapChangeClass(str, Enum):
    IMPLEMENTATION_REFINEMENT = "IMPLEMENTATION_REFINEMENT"
    CAPABILITY_EXTENSION = "CAPABILITY_EXTENSION"
    ARCHITECTURAL_UPGRADE = "ARCHITECTURAL_UPGRADE"


class RoadmapPreflightReason(str, Enum):
    NOT_GOVERNED = "NOT_GOVERNED"
    ROADMAP_BINDING_VALID = "ROADMAP_BINDING_VALID"
    ROADMAP_BINDING_FAILED = "ROADMAP_BINDING_FAILED"
    MILESTONE_COMPLETE = "MILESTONE_COMPLETE"
    MILESTONE_COMPLETION_FAILED = "MILESTONE_COMPLETION_FAILED"
    MILESTONE_OPEN_ALLOWED = "MILESTONE_OPEN_ALLOWED"
    MILESTONE_OPEN_BLOCKED = "MILESTONE_OPEN_BLOCKED"
    CONTROLLED_EVOLUTION_VALID = "CONTROLLED_EVOLUTION_VALID"
    CONTROLLED_EVOLUTION_FAILED = "CONTROLLED_EVOLUTION_FAILED"


@dataclass(frozen=True)
class CanonicalMilestone:
    milestone: str
    title: str
    capability_id: str
    requirements: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_match(self.milestone, _MILESTONE_RE, "milestone")
        _require_bounded_string(self.title, "title")
        _require_match(self.capability_id, _CAPABILITY_RE, "capability_id")
        _require_unique_strings(self.requirements, "requirements", non_empty=True)
        for requirement in self.requirements:
            match = _REQUIREMENT_RE.fullmatch(requirement)
            if match is None or match.group(1) != self.milestone:
                raise RoadmapGovernanceError(
                    f"Requirement {requirement!r} is attached to wrong milestone {self.milestone!r}"
                )


@dataclass(frozen=True)
class CanonicalRoadmap:
    roadmap_id: str
    roadmap_version: str
    status: RoadmapStatus
    authority: str
    artifact_path: str
    roadmap_blob_sha: str
    roadmap_fingerprint: str
    algorithm_version: str
    milestones: tuple[CanonicalMilestone, ...]

    def __post_init__(self) -> None:
        _require_match(self.roadmap_id, _IDENTITY_RE, "roadmap_id")
        _require_match(self.roadmap_version, _VERSION_RE, "roadmap_version")
        if not isinstance(self.status, RoadmapStatus):
            raise RoadmapGovernanceError("status must be RoadmapStatus")
        if self.authority != "CANONICAL":
            raise RoadmapGovernanceError("AUTHORITY must be exact CANONICAL")
        _require_bounded_string(self.artifact_path, "artifact_path")
        _require_match(self.roadmap_blob_sha, _BLOB_SHA_RE, "roadmap_blob_sha")
        _require_match(self.roadmap_fingerprint, _FINGERPRINT_RE, "roadmap_fingerprint")
        if self.algorithm_version != ROADMAP_FINGERPRINT_ALGORITHM_VERSION:
            raise RoadmapGovernanceError(
                f"Unsupported roadmap fingerprint algorithm version {self.algorithm_version!r}"
            )
        if type(self.milestones) is not tuple or not self.milestones:
            raise RoadmapGovernanceError("Canonical roadmap must contain milestones")
        milestone_ids = tuple(item.milestone for item in self.milestones)
        capability_ids = tuple(item.capability_id for item in self.milestones)
        _require_unique_strings(milestone_ids, "milestone identities", non_empty=True)
        _require_unique_strings(capability_ids, "capability identities", non_empty=True)

    @property
    def milestone_ids(self) -> tuple[str, ...]:
        return tuple(item.milestone for item in self.milestones)

    def milestone(self, milestone_id: str) -> CanonicalMilestone:
        matches = tuple(item for item in self.milestones if item.milestone == milestone_id)
        if len(matches) != 1:
            raise RoadmapGovernanceError(f"Undeclared roadmap milestone {milestone_id!r}")
        return matches[0]


@dataclass(frozen=True)
class RoadmapRegistryEntry:
    roadmap_id: str
    roadmap_version: str
    artifact_path: str
    roadmap_blob_sha: str

    def __post_init__(self) -> None:
        if type(self.roadmap_id) is not str or _IDENTITY_RE.fullmatch(self.roadmap_id) is None:
            raise RoadmapGovernanceError("Malformed roadmap_id")
        if type(self.roadmap_version) is not str or _VERSION_RE.fullmatch(self.roadmap_version) is None:
            raise RoadmapGovernanceError("Malformed roadmap_version")
        if type(self.artifact_path) is not str or not self.artifact_path or self.artifact_path != self.artifact_path.strip():
            raise RoadmapGovernanceError("Malformed artifact_path")
        if type(self.roadmap_blob_sha) is not str or _BLOB_SHA_RE.fullmatch(self.roadmap_blob_sha) is None:
            raise RoadmapGovernanceError("Malformed roadmap_blob_sha")


DEFAULT_ROADMAP_REGISTRY: Mapping[tuple[str, str], RoadmapRegistryEntry] = {
    (H_SERIES_ROADMAP_ID, H_SERIES_ROADMAP_VERSION): RoadmapRegistryEntry(
        roadmap_id=H_SERIES_ROADMAP_ID,
        roadmap_version=H_SERIES_ROADMAP_VERSION,
        artifact_path=H_SERIES_ROADMAP_PATH,
        roadmap_blob_sha=H_SERIES_ROADMAP_BLOB_SHA,
    )
}


@dataclass(frozen=True)
class RoadmapTaskBinding:
    roadmap_id: str
    roadmap_version: str
    roadmap_blob_sha: str
    roadmap_fingerprint: str
    roadmap_fingerprint_algorithm_version: str
    milestone: str
    capability_id: str
    requirement_bindings: tuple[str, ...]
    scope_in: tuple[str, ...]
    scope_out: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_match(self.roadmap_id, _IDENTITY_RE, "roadmap_id")
        _require_match(self.roadmap_version, _VERSION_RE, "roadmap_version")
        _require_match(self.roadmap_blob_sha, _BLOB_SHA_RE, "roadmap_blob_sha")
        _require_match(self.roadmap_fingerprint, _FINGERPRINT_RE, "roadmap_fingerprint")
        if self.roadmap_fingerprint_algorithm_version != ROADMAP_FINGERPRINT_ALGORITHM_VERSION:
            raise RoadmapGovernanceError(
                "Unsupported roadmap fingerprint algorithm version "
                f"{self.roadmap_fingerprint_algorithm_version!r}"
            )
        _require_match(self.milestone, _MILESTONE_RE, "milestone")
        _require_match(self.capability_id, _CAPABILITY_RE, "capability_id")
        _require_unique_strings(self.requirement_bindings, "requirement_bindings", non_empty=True)
        _require_unique_strings(self.scope_in, "scope_in", non_empty=False)
        _require_unique_strings(self.scope_out, "scope_out", non_empty=False)
        for field_name, values in (
            ("requirement_bindings", self.requirement_bindings),
            ("scope_in", self.scope_in),
            ("scope_out", self.scope_out),
        ):
            if len(values) > MAX_BINDING_LIST_ITEMS:
                raise RoadmapGovernanceError(f"{field_name} exceeds bounded list count")
            for item in values:
                _require_bounded_string(item, field_name)

    def requirement_bindings_fingerprint(self) -> str:
        return requirement_bindings_fingerprint(self.requirement_bindings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "roadmap_id": self.roadmap_id,
            "roadmap_version": self.roadmap_version,
            "roadmap_blob_sha": self.roadmap_blob_sha,
            "roadmap_fingerprint": self.roadmap_fingerprint,
            "roadmap_fingerprint_algorithm_version": self.roadmap_fingerprint_algorithm_version,
            "milestone": self.milestone,
            "capability_id": self.capability_id,
            "requirement_bindings": list(self.requirement_bindings),
            "scope_in": list(self.scope_in),
            "scope_out": list(self.scope_out),
        }


@dataclass(frozen=True)
class MilestoneCompletionRecord:
    roadmap_id: str
    roadmap_version: str
    roadmap_blob_sha: str
    roadmap_fingerprint: str
    roadmap_fingerprint_algorithm_version: str
    milestone: str
    capability_id: str
    requirement_evidence: tuple[tuple[str, str], ...] | Mapping[str, str]
    unresolved_requirements: tuple[str, ...]
    unresolved_blockers: tuple[str, ...]
    status: str
    record_fingerprint: str

    def __post_init__(self) -> None:
        evidence = _normalise_evidence(self.requirement_evidence)
        object.__setattr__(self, "requirement_evidence", evidence)
        _require_match(self.roadmap_id, _IDENTITY_RE, "roadmap_id")
        _require_match(self.roadmap_version, _VERSION_RE, "roadmap_version")
        _require_match(self.roadmap_blob_sha, _BLOB_SHA_RE, "roadmap_blob_sha")
        _require_match(self.roadmap_fingerprint, _FINGERPRINT_RE, "roadmap_fingerprint")
        if self.roadmap_fingerprint_algorithm_version != ROADMAP_FINGERPRINT_ALGORITHM_VERSION:
            raise RoadmapGovernanceError("Unsupported completion record fingerprint algorithm")
        _require_match(self.milestone, _MILESTONE_RE, "milestone")
        _require_match(self.capability_id, _CAPABILITY_RE, "capability_id")
        _require_unique_strings(self.unresolved_requirements, "unresolved_requirements", non_empty=False)
        _require_unique_strings(self.unresolved_blockers, "unresolved_blockers", non_empty=False)
        _require_bounded_string(self.status, "status")
        _require_match(self.record_fingerprint, _FINGERPRINT_RE, "record_fingerprint")

    @classmethod
    def create(
        cls,
        *,
        roadmap: CanonicalRoadmap,
        milestone: str,
        requirement_evidence: Mapping[str, str] | Sequence[tuple[str, str]],
        unresolved_requirements: Sequence[str] = (),
        unresolved_blockers: Sequence[str] = (),
        status: str = "COMPLETE",
    ) -> "MilestoneCompletionRecord":
        canonical = roadmap.milestone(milestone)
        values = {
            "roadmap_id": roadmap.roadmap_id,
            "roadmap_version": roadmap.roadmap_version,
            "roadmap_blob_sha": roadmap.roadmap_blob_sha,
            "roadmap_fingerprint": roadmap.roadmap_fingerprint,
            "roadmap_fingerprint_algorithm_version": roadmap.algorithm_version,
            "milestone": milestone,
            "capability_id": canonical.capability_id,
            "requirement_evidence": _normalise_evidence(requirement_evidence),
            "unresolved_requirements": tuple(unresolved_requirements),
            "unresolved_blockers": tuple(unresolved_blockers),
            "status": status,
        }
        fingerprint = _completion_record_fingerprint(values)
        return cls(**values, record_fingerprint=fingerprint)


@dataclass(frozen=True)
class RoadmapPreflightDecision:
    allowed: bool
    reason: RoadmapPreflightReason
    message: str
    binding: RoadmapTaskBinding | None = None
    roadmap: CanonicalRoadmap | None = None

    def __post_init__(self) -> None:
        if type(self.allowed) is not bool:
            raise RoadmapGovernanceError("allowed must be exact bool")
        if not isinstance(self.reason, RoadmapPreflightReason):
            raise RoadmapGovernanceError("reason must be RoadmapPreflightReason")
        _require_bounded_string(self.message, "message", maximum=2048)


@dataclass(frozen=True)
class RoadmapEvolutionRequest:
    change_class: RoadmapChangeClass
    current_roadmap: CanonicalRoadmap
    proposed_roadmap: CanonicalRoadmap | None = None
    canonical_requirement_identity_changed: bool = False
    human_approved: bool = False
    approved_change_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.change_class, RoadmapChangeClass):
            raise RoadmapGovernanceError("change_class must be RoadmapChangeClass")
        if not isinstance(self.current_roadmap, CanonicalRoadmap):
            raise RoadmapGovernanceError("current_roadmap must be CanonicalRoadmap")
        if type(self.canonical_requirement_identity_changed) is not bool:
            raise RoadmapGovernanceError("canonical_requirement_identity_changed must be exact bool")
        if type(self.human_approved) is not bool:
            raise RoadmapGovernanceError("human_approved must be exact bool")
        if self.approved_change_id is not None:
            _require_match(self.approved_change_id, _IDENTITY_RE, "approved_change_id")


@dataclass(frozen=True)
class RoadmapDriftFinding:
    code: str
    message: str

    def __post_init__(self) -> None:
        _require_match(self.code, _IDENTITY_RE, "code")
        _require_bounded_string(self.message, "message", maximum=2048)


def _require_bounded_string(value: object, field_name: str, *, maximum: int = MAX_BINDING_STRING_CHARS) -> str:
    if type(value) is not str or not value or value != value.strip() or len(value) > maximum:
        raise RoadmapGovernanceError(f"{field_name} must be an exact bounded non-empty string")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise RoadmapGovernanceError(f"{field_name} must not contain control characters")
    return value


def _require_match(value: object, pattern: re.Pattern[str], field_name: str) -> str:
    value = _require_bounded_string(value, field_name)
    if pattern.fullmatch(value) is None:
        raise RoadmapGovernanceError(f"Malformed {field_name}: {value!r}")
    return value


def _require_unique_strings(values: object, field_name: str, *, non_empty: bool) -> tuple[str, ...]:
    if type(values) is not tuple or (non_empty and not values):
        qualifier = "non-empty " if non_empty else ""
        raise RoadmapGovernanceError(f"{field_name} must be an exact {qualifier}tuple")
    if any(type(value) is not str for value in values):
        raise RoadmapGovernanceError(f"{field_name} must contain exact strings")
    if len(set(values)) != len(values):
        raise RoadmapGovernanceError(f"Duplicate {field_name} rejected")
    return values


def git_blob_sha(exact_bytes: bytes) -> str:
    if type(exact_bytes) is not bytes or not exact_bytes:
        raise RoadmapGovernanceError("Roadmap payload must be exact non-empty bytes")
    header = b"blob " + str(len(exact_bytes)).encode("ascii") + b"\0"
    return hashlib.sha1(header + exact_bytes).hexdigest()


def roadmap_fingerprint(exact_bytes: bytes, *, algorithm_version: str = ROADMAP_FINGERPRINT_ALGORITHM_VERSION) -> str:
    if algorithm_version != ROADMAP_FINGERPRINT_ALGORITHM_VERSION:
        raise RoadmapGovernanceError(f"Unsupported roadmap fingerprint algorithm version {algorithm_version!r}")
    if type(exact_bytes) is not bytes or not exact_bytes:
        raise RoadmapGovernanceError("Roadmap payload must be exact non-empty bytes")
    return hashlib.sha256(exact_bytes).hexdigest()


def parse_canonical_roadmap(
    exact_bytes: bytes,
    *,
    artifact_path: str,
    expected_blob_sha: str,
    algorithm_version: str = ROADMAP_FINGERPRINT_ALGORITHM_VERSION,
) -> CanonicalRoadmap:
    """Parse one exact-byte canonical roadmap and verify its Git provenance."""
    _require_bounded_string(artifact_path, "artifact_path")
    _require_match(expected_blob_sha, _BLOB_SHA_RE, "expected_blob_sha")
    if type(exact_bytes) is not bytes or not exact_bytes:
        raise RoadmapGovernanceError("Roadmap payload must be exact non-empty bytes")
    observed_blob = git_blob_sha(exact_bytes)
    if observed_blob != expected_blob_sha:
        raise RoadmapGovernanceError(
            f"Roadmap blob SHA mismatch: expected {expected_blob_sha}, got {observed_blob}"
        )
    try:
        text = exact_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RoadmapGovernanceError("Roadmap bytes must be strict UTF-8") from exc
    if "\x00" in text:
        raise RoadmapGovernanceError("Roadmap bytes must not contain NUL")

    fields: dict[str, str] = {}
    field_counts: dict[str, int] = {}
    milestones: list[CanonicalMilestone] = []
    current_id: str | None = None
    current_title: str | None = None
    current_capability: str | None = None
    current_requirements: list[str] = []
    capability_seen: set[str] = set()
    requirement_seen: set[str] = set()

    def finish_milestone() -> None:
        nonlocal current_id, current_title, current_capability, current_requirements
        if current_id is None:
            return
        if current_capability is None:
            raise RoadmapGovernanceError(f"Milestone {current_id} is missing CAPABILITY_ID")
        milestones.append(CanonicalMilestone(
            milestone=current_id,
            title=current_title or current_id,
            capability_id=current_capability,
            requirements=tuple(current_requirements),
        ))
        current_id = None
        current_title = None
        current_capability = None
        current_requirements = []

    in_fence = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            finish_milestone()
            continue
        field_match = _ROADMAP_FIELD_RE.fullmatch(line)
        if field_match:
            key, value = field_match.groups()
            field_counts[key] = field_counts.get(key, 0) + 1
            fields[key] = value
            continue
        milestone_match = _MILESTONE_HEADING_RE.fullmatch(line)
        if milestone_match:
            finish_milestone()
            current_id, current_title = milestone_match.groups()
            if any(item.milestone == current_id for item in milestones):
                raise RoadmapGovernanceError(f"Duplicate milestone identity {current_id}")
            continue
        capability_match = _CAPABILITY_LINE_RE.fullmatch(line)
        if capability_match and current_id is not None:
            if current_capability is not None:
                raise RoadmapGovernanceError(f"Duplicate CAPABILITY_ID in milestone {current_id}")
            current_capability = capability_match.group(1)
            _require_match(current_capability, _CAPABILITY_RE, "CAPABILITY_ID")
            if current_capability in capability_seen:
                raise RoadmapGovernanceError(f"Duplicate capability identity {current_capability}")
            capability_seen.add(current_capability)
            continue
        requirement_match = _REQUIREMENT_LINE_RE.fullmatch(line)
        if requirement_match and current_id is not None:
            requirement = requirement_match.group(1)
            requirement_identity = _REQUIREMENT_RE.fullmatch(requirement)
            if requirement_identity is None:
                raise RoadmapGovernanceError(f"Malformed requirement identity {requirement}")
            if requirement_identity.group(1) != current_id:
                raise RoadmapGovernanceError(
                    f"Requirement {requirement} is attached to wrong milestone {current_id}"
                )
            if requirement in requirement_seen:
                raise RoadmapGovernanceError(f"Duplicate requirement identity {requirement}")
            requirement_seen.add(requirement)
            current_requirements.append(requirement)
            continue
        if current_id is not None and line.startswith("- "):
            raise RoadmapGovernanceError(
                f"Malformed requirement declaration in milestone {current_id}: {line!r}"
            )
    finish_milestone()

    for required in ("ROADMAP_ID", "ROADMAP_VERSION", "STATUS", "AUTHORITY"):
        count = field_counts.get(required, 0)
        if count != 1:
            raise RoadmapGovernanceError(f"Roadmap must contain exactly one {required}; found {count}")
    try:
        status = RoadmapStatus(fields["STATUS"])
    except ValueError as exc:
        raise RoadmapGovernanceError(f"Unsupported roadmap STATUS {fields['STATUS']!r}") from exc

    return CanonicalRoadmap(
        roadmap_id=fields["ROADMAP_ID"],
        roadmap_version=fields["ROADMAP_VERSION"],
        status=status,
        authority=fields["AUTHORITY"],
        artifact_path=artifact_path,
        roadmap_blob_sha=observed_blob,
        roadmap_fingerprint=roadmap_fingerprint(exact_bytes, algorithm_version=algorithm_version),
        algorithm_version=algorithm_version,
        milestones=tuple(milestones),
    )


def _strict_json_object(payload: str) -> dict[str, Any]:
    if len(payload.encode("utf-8")) > MAX_BINDING_JSON_BYTES:
        raise RoadmapGovernanceError("ROADMAP_BINDING_JSON exceeds bounded serialized size")

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise RoadmapGovernanceError(f"Duplicate ROADMAP_BINDING_JSON field {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise RoadmapGovernanceError(f"Non-finite JSON constant rejected: {value}")

    try:
        result = json.loads(payload, object_pairs_hook=pairs_hook, parse_constant=reject_constant)
    except RoadmapGovernanceError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RoadmapGovernanceError(f"Malformed ROADMAP_BINDING_JSON: {exc}") from exc
    if type(result) is not dict:
        raise RoadmapGovernanceError("ROADMAP_BINDING_JSON root must be a strict object")
    return result


def _top_level_marker_payloads(content: str, marker: str) -> list[str]:
    payloads: list[str] = []
    in_fence = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith(marker):
            payloads.append(line[len(marker):].strip())
    return payloads


def parse_roadmap_task_binding(task_text: str) -> RoadmapTaskBinding:
    if type(task_text) is not str or not task_text.strip():
        raise RoadmapGovernanceError("Task text must be exact non-empty string")
    payloads = _top_level_marker_payloads(task_text, ROADMAP_BINDING_MARKER)
    if len(payloads) != 1:
        raise RoadmapGovernanceError(
            f"Task must contain exactly one {ROADMAP_BINDING_MARKER} marker; found {len(payloads)}"
        )
    if not payloads[0]:
        raise RoadmapGovernanceError("ROADMAP_BINDING_JSON payload must not be empty")
    data = _strict_json_object(payloads[0])
    required = {
        "roadmap_id", "roadmap_version", "roadmap_blob_sha", "roadmap_fingerprint",
        "roadmap_fingerprint_algorithm_version", "milestone", "capability_id",
        "requirement_bindings", "scope_in", "scope_out",
    }
    if set(data) != required:
        missing = sorted(required - set(data))
        extra = sorted(set(data) - required)
        raise RoadmapGovernanceError(
            f"ROADMAP_BINDING_JSON keys must be exact; missing={missing}, extra={extra}"
        )
    for name in ("requirement_bindings", "scope_in", "scope_out"):
        value = data[name]
        if type(value) is not list or len(value) > MAX_BINDING_LIST_ITEMS:
            raise RoadmapGovernanceError(f"{name} must be a bounded JSON list")
        if any(type(item) is not str for item in value):
            raise RoadmapGovernanceError(f"{name} must contain exact JSON strings")
    scalar_names = required - {"requirement_bindings", "scope_in", "scope_out"}
    if any(type(data[name]) is not str for name in scalar_names):
        raise RoadmapGovernanceError("ROADMAP_BINDING_JSON scalar fields must be exact strings")
    return RoadmapTaskBinding(
        roadmap_id=data["roadmap_id"],
        roadmap_version=data["roadmap_version"],
        roadmap_blob_sha=data["roadmap_blob_sha"],
        roadmap_fingerprint=data["roadmap_fingerprint"],
        roadmap_fingerprint_algorithm_version=data["roadmap_fingerprint_algorithm_version"],
        milestone=data["milestone"],
        capability_id=data["capability_id"],
        requirement_bindings=tuple(data["requirement_bindings"]),
        scope_in=tuple(data["scope_in"]),
        scope_out=tuple(data["scope_out"]),
    )


def task_header_fields(task_text: str) -> tuple[str, Mapping[str, tuple[str, ...]]]:
    """Return title plus exact top-header fields, stopping at the first section/fence."""
    title = ""
    values: dict[str, list[str]] = {}
    for raw_line in task_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("##") or line.startswith("```"):
            break
        if line.startswith("# "):
            if not title:
                title = line[2:].strip()
            continue
        match = _HEADER_FIELD_RE.fullmatch(line)
        if match:
            key, value = match.groups()
            values.setdefault(key, []).append(value)
    return title, {key: tuple(items) for key, items in values.items()}


def claimed_h_milestones(task_text: str) -> tuple[str, ...]:
    title, fields = task_header_fields(task_text)
    claims = list(_H_CLAIM_RE.findall(title))
    for value in fields.get("MILESTONE", ()):
        claims.extend(_H_CLAIM_RE.findall(value))
    return tuple(dict.fromkeys(claims))


def task_requires_roadmap_governance(task_text: str) -> bool:
    title, fields = task_header_fields(task_text)
    del title
    if any("AIOS ENGINEERING H-SERIES" in value for value in fields.get("CLASS", ())):
        return True
    return bool(claimed_h_milestones(task_text))


def requirement_bindings_fingerprint(requirements: Sequence[str]) -> str:
    if isinstance(requirements, (str, bytes)):
        raise RoadmapGovernanceError("requirements must be a sequence of strings")
    values = tuple(requirements)
    _require_unique_strings(values, "requirement bindings", non_empty=True)
    payload = json.dumps(sorted(values), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_task_binding(
    task_text: str,
    binding: RoadmapTaskBinding,
    roadmap: CanonicalRoadmap,
    *,
    context_refs: Sequence[object],
    migration_approved: bool = False,
) -> None:
    if not isinstance(binding, RoadmapTaskBinding) or not isinstance(roadmap, CanonicalRoadmap):
        raise RoadmapGovernanceError("binding and roadmap must use canonical governance types")
    if roadmap.status is RoadmapStatus.DRAFT:
        raise RoadmapGovernanceError("Roadmap STATUS DRAFT is not executable under any migration")
    if roadmap.status is RoadmapStatus.SUPERSEDED and not migration_approved:
        raise RoadmapGovernanceError(
            f"Roadmap STATUS {roadmap.status.value} is not executable without approved migration/revalidation"
        )
    exact_pairs = (
        ("roadmap_id", binding.roadmap_id, roadmap.roadmap_id),
        ("roadmap_version", binding.roadmap_version, roadmap.roadmap_version),
        ("roadmap_blob_sha", binding.roadmap_blob_sha, roadmap.roadmap_blob_sha),
        ("roadmap_fingerprint", binding.roadmap_fingerprint, roadmap.roadmap_fingerprint),
        ("roadmap_fingerprint_algorithm_version", binding.roadmap_fingerprint_algorithm_version, roadmap.algorithm_version),
    )
    for name, task_value, canonical_value in exact_pairs:
        if task_value != canonical_value:
            raise RoadmapGovernanceError(
                f"Task {name} mismatch: bound {task_value!r}, canonical {canonical_value!r}"
            )
    milestone = roadmap.milestone(binding.milestone)
    if binding.capability_id != milestone.capability_id:
        raise RoadmapGovernanceError(
            f"Task capability mismatch for {binding.milestone}: {binding.capability_id!r} != {milestone.capability_id!r}"
        )
    canonical_requirements = set(milestone.requirements)
    for requirement in binding.requirement_bindings:
        if requirement not in canonical_requirements:
            owner = next(
                (item.milestone for item in roadmap.milestones if requirement in item.requirements),
                None,
            )
            if owner is not None:
                raise RoadmapGovernanceError(
                    f"Requirement {requirement} belongs to wrong milestone {owner}, not {binding.milestone}"
                )
            raise RoadmapGovernanceError(f"Undeclared canonical requirement {requirement}")

    title, fields = task_header_fields(task_text)
    del title
    header_milestones = fields.get("MILESTONE", ())
    if len(header_milestones) > 1:
        raise RoadmapGovernanceError("Duplicate task MILESTONE header rejected")
    if header_milestones and header_milestones[0] != binding.milestone:
        raise RoadmapGovernanceError(
            f"Task header milestone {header_milestones[0]!r} differs from roadmap binding {binding.milestone!r}"
        )
    for claim in claimed_h_milestones(task_text):
        if claim not in roadmap.milestone_ids:
            raise RoadmapGovernanceError(f"Task title/header claims undeclared H milestone {claim}")
        if claim != binding.milestone:
            raise RoadmapGovernanceError(
                f"Task title/header claims milestone {claim}, binding declares {binding.milestone}"
            )

    parsed_refs: list[tuple[str, str]] = []
    for index, ref in enumerate(context_refs):
        if isinstance(ref, Mapping):
            path, blob = ref.get("path"), ref.get("blob_sha")
        else:
            path, blob = getattr(ref, "path", None), getattr(ref, "blob_sha", None)
        if type(path) is not str or type(blob) is not str:
            raise RoadmapGovernanceError(f"Malformed roadmap context ref at index {index}")
        parsed_refs.append((path, blob))
    path_matches = tuple(pair for pair in parsed_refs if pair[0] == roadmap.artifact_path)
    if len(path_matches) != 1:
        if any(blob == binding.roadmap_blob_sha for path, blob in parsed_refs if path != roadmap.artifact_path):
            raise RoadmapGovernanceError("Canonical roadmap context path mismatch")
        raise RoadmapGovernanceError("Canonical roadmap context ref missing or duplicated")
    if path_matches[0][1] != binding.roadmap_blob_sha:
        raise RoadmapGovernanceError("Canonical roadmap context ref blob mismatch")
    conflicts = tuple(
        pair for pair in parsed_refs
        if pair[0] != roadmap.artifact_path and pair[1] == binding.roadmap_blob_sha
    )
    if conflicts:
        raise RoadmapGovernanceError("Duplicate conflicting canonical roadmap context refs")


def evaluate_roadmap_preflight(
    task_text: str,
    *,
    context_refs: Sequence[object],
    roadmap_resolver: Callable[[str, str], bytes] | None,
    registry: Mapping[tuple[str, str], RoadmapRegistryEntry] = DEFAULT_ROADMAP_REGISTRY,
    migration_approved: bool = False,
) -> RoadmapPreflightDecision:
    """Resolve and validate governed task binding without creating authority."""
    governed = task_requires_roadmap_governance(task_text) or bool(
        _top_level_marker_payloads(task_text, ROADMAP_BINDING_MARKER)
    )
    if not governed:
        return RoadmapPreflightDecision(
            allowed=True,
            reason=RoadmapPreflightReason.NOT_GOVERNED,
            message="Executable artifact is not registered or identified as roadmap governed",
        )
    try:
        binding = parse_roadmap_task_binding(task_text)
        registration = registry.get((binding.roadmap_id, binding.roadmap_version))
        if registration is None:
            raise RoadmapGovernanceError(
                f"Roadmap identity {(binding.roadmap_id, binding.roadmap_version)!r} is not registered"
            )
        if binding.roadmap_blob_sha != registration.roadmap_blob_sha:
            raise RoadmapGovernanceError("Task-bound roadmap blob does not match current registered roadmap blob")
        if roadmap_resolver is None:
            raise RoadmapGovernanceError("Exact canonical roadmap resolver is required for governed task")
        exact_bytes = roadmap_resolver(registration.artifact_path, registration.roadmap_blob_sha)
        roadmap = parse_canonical_roadmap(
            exact_bytes,
            artifact_path=registration.artifact_path,
            expected_blob_sha=registration.roadmap_blob_sha,
        )
        validate_task_binding(
            task_text,
            binding,
            roadmap,
            context_refs=context_refs,
            migration_approved=migration_approved,
        )
        return RoadmapPreflightDecision(
            allowed=True,
            reason=RoadmapPreflightReason.ROADMAP_BINDING_VALID,
            message="Task is exactly bound to the current locked canonical roadmap",
            binding=binding,
            roadmap=roadmap,
        )
    except (RoadmapGovernanceError, ContinuityStateValidationError) as exc:
        return RoadmapPreflightDecision(
            allowed=False,
            reason=RoadmapPreflightReason.ROADMAP_BINDING_FAILED,
            message=str(exc),
        )


def require_roadmap_preflight(*args: Any, **kwargs: Any) -> RoadmapPreflightDecision:
    decision = evaluate_roadmap_preflight(*args, **kwargs)
    if not decision.allowed:
        raise RoadmapGovernanceError(f"{decision.reason.value}: {decision.message}")
    return decision


def _normalise_evidence(
    evidence: Mapping[str, str] | Sequence[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    if isinstance(evidence, Mapping):
        raw = tuple(evidence.items())
    elif isinstance(evidence, (str, bytes)):
        raise RoadmapGovernanceError("requirement_evidence must be a mapping or pair sequence")
    else:
        raw = tuple(evidence)
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, pair in enumerate(raw):
        if type(pair) not in (tuple, list) or len(pair) != 2:
            raise RoadmapGovernanceError(f"requirement_evidence[{index}] must be a key/value pair")
        requirement, value = pair
        _require_bounded_string(requirement, "requirement_evidence requirement")
        _require_bounded_string(value, "requirement_evidence value", maximum=MAX_EVIDENCE_CHARS)
        if requirement in seen:
            raise RoadmapGovernanceError(f"Duplicate requirement evidence {requirement}")
        seen.add(requirement)
        result.append((requirement, value))
    return tuple(sorted(result))


def _completion_record_payload(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "roadmap_id": values["roadmap_id"],
        "roadmap_version": values["roadmap_version"],
        "roadmap_blob_sha": values["roadmap_blob_sha"],
        "roadmap_fingerprint": values["roadmap_fingerprint"],
        "roadmap_fingerprint_algorithm_version": values["roadmap_fingerprint_algorithm_version"],
        "milestone": values["milestone"],
        "capability_id": values["capability_id"],
        "requirement_evidence": {key: evidence for key, evidence in values["requirement_evidence"]},
        "unresolved_requirements": list(values["unresolved_requirements"]),
        "unresolved_blockers": list(values["unresolved_blockers"]),
        "status": values["status"],
    }


def _completion_record_fingerprint(values: Mapping[str, Any]) -> str:
    payload = json.dumps(
        _completion_record_payload(values), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_milestone_completion(
    record: MilestoneCompletionRecord,
    roadmap: CanonicalRoadmap,
) -> RoadmapPreflightDecision:
    try:
        if not isinstance(record, MilestoneCompletionRecord):
            raise RoadmapGovernanceError("record must be MilestoneCompletionRecord")
        exact_pairs = (
            (record.roadmap_id, roadmap.roadmap_id, "roadmap_id"),
            (record.roadmap_version, roadmap.roadmap_version, "roadmap_version"),
            (record.roadmap_blob_sha, roadmap.roadmap_blob_sha, "roadmap_blob_sha"),
            (record.roadmap_fingerprint, roadmap.roadmap_fingerprint, "roadmap_fingerprint"),
            (record.roadmap_fingerprint_algorithm_version, roadmap.algorithm_version, "algorithm_version"),
        )
        for actual, expected, name in exact_pairs:
            if actual != expected:
                raise RoadmapGovernanceError(f"Completion record {name} mismatch")
        milestone = roadmap.milestone(record.milestone)
        if record.capability_id != milestone.capability_id:
            raise RoadmapGovernanceError("Completion record capability mismatch")
        if record.status != "COMPLETE":
            raise RoadmapGovernanceError("Milestone completion status must be exact COMPLETE")
        evidence_ids = tuple(key for key, _ in record.requirement_evidence)
        if set(evidence_ids) != set(milestone.requirements):
            missing = sorted(set(milestone.requirements) - set(evidence_ids))
            extra = sorted(set(evidence_ids) - set(milestone.requirements))
            raise RoadmapGovernanceError(
                f"Completion evidence must exactly cover canonical requirements; missing={missing}, extra={extra}"
            )
        if record.unresolved_requirements:
            raise RoadmapGovernanceError("Completion record has unresolved requirements")
        if record.unresolved_blockers:
            raise RoadmapGovernanceError("Completion record has unresolved blockers")
        expected_fingerprint = _completion_record_fingerprint(record.__dict__)
        if record.record_fingerprint != expected_fingerprint:
            raise RoadmapGovernanceError("Completion record fingerprint mismatch")
        return RoadmapPreflightDecision(
            allowed=True,
            reason=RoadmapPreflightReason.MILESTONE_COMPLETE,
            message=f"Milestone {record.milestone} has exact complete canonical evidence",
            roadmap=roadmap,
        )
    except (RoadmapGovernanceError, ContinuityStateValidationError) as exc:
        return RoadmapPreflightDecision(
            allowed=False,
            reason=RoadmapPreflightReason.MILESTONE_COMPLETION_FAILED,
            message=str(exc),
            roadmap=roadmap,
        )


def may_open_milestone(
    roadmap: CanonicalRoadmap,
    target_milestone: str,
    completion_records: Sequence[MilestoneCompletionRecord],
    *,
    dependencies: Mapping[str, Sequence[str]] | None = None,
) -> RoadmapPreflightDecision:
    try:
        roadmap.milestone(target_milestone)
        if dependencies is None:
            ordered = roadmap.milestone_ids
            target_index = ordered.index(target_milestone)
            required = ordered[:target_index]
        else:
            required = tuple(sorted(_transitive_prerequisites(target_milestone, dependencies)))
        records_by_milestone: dict[str, MilestoneCompletionRecord] = {}
        for record in completion_records:
            if record.milestone in records_by_milestone:
                raise RoadmapGovernanceError(f"Duplicate completion record for {record.milestone}")
            records_by_milestone[record.milestone] = record
        for prerequisite in required:
            record = records_by_milestone.get(prerequisite)
            if record is None:
                raise RoadmapGovernanceError(
                    f"Milestone {target_milestone} cannot open without COMPLETE evidence for {prerequisite}"
                )
            decision = validate_milestone_completion(record, roadmap)
            if not decision.allowed:
                raise RoadmapGovernanceError(
                    f"Milestone {target_milestone} prerequisite {prerequisite} invalid: {decision.message}"
                )
        return RoadmapPreflightDecision(
            allowed=True,
            reason=RoadmapPreflightReason.MILESTONE_OPEN_ALLOWED,
            message=f"Milestone {target_milestone} may be opened from supplied completion evidence",
            roadmap=roadmap,
        )
    except (RoadmapGovernanceError, ContinuityStateValidationError, ValueError) as exc:
        return RoadmapPreflightDecision(
            allowed=False,
            reason=RoadmapPreflightReason.MILESTONE_OPEN_BLOCKED,
            message=str(exc),
            roadmap=roadmap,
        )


def validate_controlled_evolution(request: RoadmapEvolutionRequest) -> RoadmapPreflightDecision:
    try:
        current = request.current_roadmap
        proposed = request.proposed_roadmap
        if request.change_class is RoadmapChangeClass.IMPLEMENTATION_REFINEMENT:
            if current.status is not RoadmapStatus.LOCKED:
                raise RoadmapGovernanceError("Implementation refinement requires current LOCKED roadmap")
            if request.canonical_requirement_identity_changed:
                raise RoadmapGovernanceError("Implementation refinement cannot change canonical requirement identity")
            if proposed is not None and (
                proposed.roadmap_id != current.roadmap_id
                or proposed.roadmap_version != current.roadmap_version
                or proposed.roadmap_blob_sha != current.roadmap_blob_sha
                or proposed.roadmap_fingerprint != current.roadmap_fingerprint
            ):
                raise RoadmapGovernanceError("Implementation refinement cannot silently mutate a LOCKED roadmap")
        elif request.change_class is RoadmapChangeClass.CAPABILITY_EXTENSION:
            if not request.human_approved or request.approved_change_id is None:
                raise RoadmapGovernanceError("Capability extension requires explicit Human-approved amendment identity")
        elif request.change_class is RoadmapChangeClass.ARCHITECTURAL_UPGRADE:
            if not request.human_approved or request.approved_change_id is None:
                raise RoadmapGovernanceError("Architectural upgrade requires explicit Human approval and change identity")
            if proposed is None:
                raise RoadmapGovernanceError("Architectural upgrade requires a proposed superseding roadmap")
            if proposed.roadmap_version == current.roadmap_version:
                raise RoadmapGovernanceError("Architectural upgrade cannot reuse the same locked roadmap version")
            if proposed.status is not RoadmapStatus.LOCKED:
                raise RoadmapGovernanceError("Superseding roadmap must be LOCKED before executable binding")
        return RoadmapPreflightDecision(
            allowed=True,
            reason=RoadmapPreflightReason.CONTROLLED_EVOLUTION_VALID,
            message=f"{request.change_class.value} satisfies controlled-evolution requirements",
            roadmap=proposed or current,
        )
    except (RoadmapGovernanceError, ContinuityStateValidationError) as exc:
        return RoadmapPreflightDecision(
            allowed=False,
            reason=RoadmapPreflightReason.CONTROLLED_EVOLUTION_FAILED,
            message=str(exc),
            roadmap=request.current_roadmap,
        )


def _transitive_prerequisites(
    milestone: str,
    dependencies: Mapping[str, Sequence[str]],
) -> set[str]:
    result: set[str] = set()
    visiting: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise RoadmapGovernanceError("Milestone dependency cycle rejected")
        visiting.add(node)
        for prerequisite in dependencies.get(node, ()):
            if prerequisite not in result:
                result.add(prerequisite)
                visit(prerequisite)
        visiting.remove(node)

    visit(milestone)
    return result


def impact_cone(
    roadmap: CanonicalRoadmap,
    changed_milestone: str,
    *,
    dependencies: Mapping[str, Sequence[str]] | None = None,
) -> tuple[str, ...]:
    """Return changed milestone plus all dependent milestones in canonical order."""
    roadmap.milestone(changed_milestone)
    ordered = roadmap.milestone_ids
    if dependencies is None:
        return ordered[ordered.index(changed_milestone):]
    unknown = (set(dependencies) | {dep for deps in dependencies.values() for dep in deps}) - set(ordered)
    if unknown:
        raise RoadmapGovernanceError(f"Dependency graph contains undeclared milestones: {sorted(unknown)}")
    cone = {changed_milestone}
    changed = True
    while changed:
        changed = False
        for milestone, prerequisites in dependencies.items():
            if milestone not in cone and any(prerequisite in cone for prerequisite in prerequisites):
                cone.add(milestone)
                changed = True
    return tuple(item for item in ordered if item in cone)


def detect_task_roadmap_drift(
    task_text: str,
    binding: RoadmapTaskBinding,
    roadmap: CanonicalRoadmap,
    *,
    context_refs: Sequence[object],
) -> tuple[RoadmapDriftFinding, ...]:
    try:
        validate_task_binding(task_text, binding, roadmap, context_refs=context_refs)
    except RoadmapGovernanceError as exc:
        return (RoadmapDriftFinding(code="ROADMAP_BINDING_FAILED", message=str(exc)),)
    return ()


__all__ = [
    "ROADMAP_FINGERPRINT_ALGORITHM_VERSION", "ROADMAP_BINDING_MARKER",
    "H_SERIES_ROADMAP_ID", "H_SERIES_ROADMAP_VERSION", "H_SERIES_ROADMAP_PATH",
    "H_SERIES_ROADMAP_BLOB_SHA", "DEFAULT_ROADMAP_REGISTRY",
    "RoadmapGovernanceError", "RoadmapStatus", "RoadmapChangeClass",
    "RoadmapPreflightReason", "CanonicalMilestone", "CanonicalRoadmap",
    "RoadmapRegistryEntry", "RoadmapTaskBinding", "MilestoneCompletionRecord",
    "RoadmapPreflightDecision", "RoadmapEvolutionRequest", "RoadmapDriftFinding",
    "git_blob_sha", "roadmap_fingerprint", "parse_canonical_roadmap",
    "parse_roadmap_task_binding", "task_header_fields", "claimed_h_milestones",
    "task_requires_roadmap_governance", "requirement_bindings_fingerprint",
    "validate_task_binding", "evaluate_roadmap_preflight", "require_roadmap_preflight",
    "validate_milestone_completion", "may_open_milestone", "validate_controlled_evolution",
    "impact_cone", "detect_task_roadmap_drift",
]
