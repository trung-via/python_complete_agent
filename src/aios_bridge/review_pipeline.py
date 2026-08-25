"""Pure deterministic contracts for the Lean Review lifecycle foundation."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import re
from typing import Any

from src.aios_bridge.certification_job import (
    CertificationContractError,
    CertificationJob,
    CertificationJobStatus,
    require_exact_certification_candidate,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.validation import ValidationProfile


_IDENTIFIER_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_FINGERPRINT_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_TOKEN_RE = re.compile(r"\A[A-Z][A-Z0-9_]{0,63}\Z")
_MAX_PATH_CLASSES = 16
_MAX_SURFACES = 64
_MAX_PROOF_IDS = 64
_PIPELINE_MODE_MARKER = "REVIEW_PIPELINE_MODE:"


class ReviewContractError(ContinuityStateValidationError):
    """A malformed contract value or invalid lifecycle transition."""


def _error(message: str) -> ReviewContractError:
    return ReviewContractError(message)


def _require_identifier(value: object, name: str) -> str:
    if type(value) is not str or _IDENTIFIER_RE.fullmatch(value) is None:
        raise _error(f"{name} must be a canonical bounded identifier")
    return value


def _require_fingerprint(value: object, name: str) -> str:
    if type(value) is not str or _FINGERPRINT_RE.fullmatch(value) is None:
        raise _error(f"{name} must be an exact lowercase 64-hex fingerprint")
    return value


def _require_round(value: object, name: str) -> int:
    if type(value) is not int or value < 1:
        raise _error(f"{name} must be an exact positive integer")
    return value


class TaskPipelineMode(str, Enum):
    LEGACY_CERTIFY_ON_PUBLISH = "LEGACY_CERTIFY_ON_PUBLISH"
    REVIEW_FIRST_CERTIFICATION = "REVIEW_FIRST_CERTIFICATION"


def parse_task_pipeline_mode(
    task_content: str,
    *,
    task_id: str | None = None,
) -> TaskPipelineMode:
    """Parse one exact top-level opt-in marker while ignoring fenced examples."""
    if type(task_content) is not str:
        raise _error("task_content must be exact text")
    if task_id is not None and (
        type(task_id) is not str or re.fullmatch(r"TASK-\d+", task_id) is None
    ):
        raise _error("task_id must match exact TASK-<digits> or be None")

    values: list[str] = []
    fence: str | None = None
    for line in task_content.splitlines():
        stripped = line.lstrip()
        fence_match = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_match:
            token = fence_match.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
            continue
        if fence is None and line.startswith(_PIPELINE_MODE_MARKER):
            values.append(line[len(_PIPELINE_MODE_MARKER) :].strip())

    if not values:
        return TaskPipelineMode.LEGACY_CERTIFY_ON_PUBLISH
    if len(values) != 1:
        raise _error("task must contain at most one top-level REVIEW_PIPELINE_MODE marker")
    try:
        parsed = TaskPipelineMode(values[0])
    except ValueError as exc:
        raise _error(f"unknown REVIEW_PIPELINE_MODE: {values[0]!r}") from exc
    if parsed is TaskPipelineMode.LEGACY_CERTIFY_ON_PUBLISH:
        raise _error("legacy compatibility is selected only by a missing mode marker")
    if task_id == "TASK-090":
        return TaskPipelineMode.LEGACY_CERTIFY_ON_PUBLISH
    return parsed


class ReviewState(str, Enum):
    READY_FOR_SEMANTIC_REVIEW = "READY_FOR_SEMANTIC_REVIEW"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    SEMANTICALLY_ACCEPTED_PENDING_T2 = "SEMANTICALLY_ACCEPTED_PENDING_T2"
    CERTIFICATION_RUNNING = "CERTIFICATION_RUNNING"
    CERTIFIED = "CERTIFIED"
    FINAL_PASS = "FINAL_PASS"
    SUPERSEDED = "SUPERSEDED"


_REVIEW_TRANSITIONS: dict[ReviewState, frozenset[ReviewState]] = {
    ReviewState.READY_FOR_SEMANTIC_REVIEW: frozenset(
        {
            ReviewState.CHANGES_REQUIRED,
            ReviewState.SEMANTICALLY_ACCEPTED_PENDING_T2,
            ReviewState.SUPERSEDED,
        }
    ),
    ReviewState.CHANGES_REQUIRED: frozenset(
        {ReviewState.READY_FOR_SEMANTIC_REVIEW, ReviewState.SUPERSEDED}
    ),
    ReviewState.SEMANTICALLY_ACCEPTED_PENDING_T2: frozenset(
        {ReviewState.CERTIFICATION_RUNNING, ReviewState.SUPERSEDED}
    ),
    ReviewState.CERTIFICATION_RUNNING: frozenset(
        {ReviewState.CERTIFIED, ReviewState.CHANGES_REQUIRED, ReviewState.SUPERSEDED}
    ),
    ReviewState.CERTIFIED: frozenset(
        {ReviewState.FINAL_PASS, ReviewState.SUPERSEDED}
    ),
    ReviewState.FINAL_PASS: frozenset(),
    ReviewState.SUPERSEDED: frozenset(),
}


def transition_review_state(current: ReviewState, target: ReviewState) -> ReviewState:
    """Return the target for a valid review transition, otherwise fail closed."""
    if type(current) is not ReviewState or type(target) is not ReviewState:
        raise _error("review transitions require exact ReviewState values")
    if target not in _REVIEW_TRANSITIONS[current]:
        raise _error(f"invalid review transition: {current.value} -> {target.value}")
    return target


def review_state_creates_merge_authority(state: ReviewState) -> bool:
    """Only FINAL_PASS is authoritative; semantic acceptance is never authority."""
    if type(state) is not ReviewState:
        raise _error("state must be an exact ReviewState")
    return state is ReviewState.FINAL_PASS


def derive_review_first_final_state(
    *,
    task_id: str,
    review_state: ReviewState,
    approved: bool,
    auto_merge_eligible: bool,
    certification_job: CertificationJob,
    candidate_head_sha: str,
    candidate_fingerprint: str,
    validation_profile: ValidationProfile,
    certification_command_identity: str,
) -> ReviewState:
    """Derive FINAL_PASS only from exact semantic acceptance plus exact PASS evidence."""
    if review_state is not ReviewState.SEMANTICALLY_ACCEPTED_PENDING_T2:
        raise _error("review-first finalization requires semantic acceptance pending T2")
    if type(approved) is not bool or not approved:
        raise _error("review-first finalization requires APPROVED YES")
    if type(auto_merge_eligible) is not bool or not auto_merge_eligible:
        raise _error("review-first finalization requires AUTO_MERGE_ELIGIBLE YES")
    if type(task_id) is not str or re.fullmatch(r"TASK-\d+", task_id) is None:
        raise _error("task_id must match exact TASK-<digits>")
    if certification_job.task_id != task_id:
        raise _error("certification job task identity mismatch")
    if type(validation_profile) is not ValidationProfile:
        raise _error("validation_profile must be an exact ValidationProfile")
    if (
        type(certification_command_identity) is not str
        or not certification_command_identity
        or certification_command_identity != certification_command_identity.strip()
    ):
        raise _error("certification_command_identity must be exact non-empty text")
    try:
        require_exact_certification_candidate(
            certification_job,
            candidate_head_sha,
            candidate_fingerprint,
        )
    except CertificationContractError as exc:
        raise _error(str(exc)) from exc
    if certification_job.status is not CertificationJobStatus.CERTIFICATION_PASS:
        raise _error("FINAL_PASS requires exact CERTIFICATION_PASS evidence")
    if certification_job.validation_profile is not validation_profile:
        raise _error("certification validation profile mismatch")
    if certification_job.certification_command_identity != certification_command_identity:
        raise _error("certification command identity mismatch")
    return ReviewState.FINAL_PASS


class FindingStatus(str, Enum):
    NEW = "NEW"
    OPEN = "OPEN"
    FIX_SUBMITTED = "FIX_SUBMITTED"
    VERIFYING = "VERIFYING"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


_FINDING_TRANSITIONS: dict[FindingStatus, frozenset[FindingStatus]] = {
    FindingStatus.NEW: frozenset({FindingStatus.OPEN}),
    FindingStatus.OPEN: frozenset({FindingStatus.FIX_SUBMITTED}),
    FindingStatus.FIX_SUBMITTED: frozenset({FindingStatus.VERIFYING}),
    FindingStatus.VERIFYING: frozenset({FindingStatus.CLOSED, FindingStatus.OPEN}),
    FindingStatus.CLOSED: frozenset({FindingStatus.REOPENED}),
    FindingStatus.REOPENED: frozenset(
        {FindingStatus.OPEN, FindingStatus.FIX_SUBMITTED}
    ),
}


@dataclass(frozen=True, slots=True)
class FindingRecord:
    finding_id: str
    introduced_review_round: int
    severity: str
    affected_surfaces: tuple[str, ...]
    status: FindingStatus
    required_proof_ids: tuple[str, ...]
    fixed_by_sha: str | None = None
    closure_review_round: int | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.finding_id, "finding_id")
        _require_round(self.introduced_review_round, "introduced_review_round")
        if type(self.severity) is not str or _TOKEN_RE.fullmatch(self.severity) is None:
            raise _error("severity must be a canonical uppercase token")
        if type(self.status) is not FindingStatus:
            raise _error("status must be an exact FindingStatus")
        if type(self.affected_surfaces) is not tuple or not self.affected_surfaces:
            raise _error("affected_surfaces must be a non-empty exact tuple")
        if len(self.affected_surfaces) > _MAX_SURFACES:
            raise _error("affected_surfaces exceeds the bounded maximum")
        for surface in self.affected_surfaces:
            if type(surface) is not str or not surface or surface != surface.strip() or len(surface) > 512:
                raise _error("each affected surface must be bounded exact non-empty text")
        if len(set(self.affected_surfaces)) != len(self.affected_surfaces):
            raise _error("duplicate affected surface")
        if type(self.required_proof_ids) is not tuple:
            raise _error("required_proof_ids must be an exact tuple")
        if len(self.required_proof_ids) > _MAX_PROOF_IDS:
            raise _error("required_proof_ids exceeds the bounded maximum")
        for proof_id in self.required_proof_ids:
            _require_identifier(proof_id, "required proof ID")
        if len(set(self.required_proof_ids)) != len(self.required_proof_ids):
            raise _error("duplicate required proof ID")
        if self.fixed_by_sha is not None and (
            type(self.fixed_by_sha) is not str or _SHA_RE.fullmatch(self.fixed_by_sha) is None
        ):
            raise _error("fixed_by_sha must be an exact lowercase 40-hex SHA or None")
        if self.closure_review_round is not None:
            _require_round(self.closure_review_round, "closure_review_round")
            if self.closure_review_round < self.introduced_review_round:
                raise _error("closure_review_round cannot precede introduction")
        if self.status is FindingStatus.CLOSED:
            if self.fixed_by_sha is None:
                raise _error("closed finding requires fixed_by_sha")
            if self.closure_review_round is None:
                raise _error("closed finding requires closure_review_round")

    def to_dict(self) -> dict[str, Any]:
        return {
            "affected_surfaces": list(self.affected_surfaces),
            "closure_review_round": self.closure_review_round,
            "finding_id": self.finding_id,
            "fixed_by_sha": self.fixed_by_sha,
            "introduced_review_round": self.introduced_review_round,
            "required_proof_ids": list(self.required_proof_ids),
            "severity": self.severity,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: object) -> "FindingRecord":
        fields = {
            "affected_surfaces",
            "closure_review_round",
            "finding_id",
            "fixed_by_sha",
            "introduced_review_round",
            "required_proof_ids",
            "severity",
            "status",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("FindingRecord must contain the exact bounded field set")
        if type(data["affected_surfaces"]) is not list:
            raise _error("affected_surfaces must be an exact list")
        if type(data["required_proof_ids"]) is not list:
            raise _error("required_proof_ids must be an exact list")
        try:
            return cls(
                finding_id=data["finding_id"],
                introduced_review_round=data["introduced_review_round"],
                severity=data["severity"],
                affected_surfaces=tuple(data["affected_surfaces"]),
                status=FindingStatus(data["status"]),
                fixed_by_sha=data["fixed_by_sha"],
                required_proof_ids=tuple(data["required_proof_ids"]),
                closure_review_round=data["closure_review_round"],
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed FindingRecord: {exc}") from exc


def transition_finding_status(
    finding: FindingRecord,
    target: FindingStatus,
    *,
    reopen_evidence: bool = False,
    fixed_by_sha: str | None = None,
    closure_review_round: int | None = None,
) -> FindingRecord:
    """Pure finding transition with evidence-gated CLOSED reopening."""
    if type(finding) is not FindingRecord or type(target) is not FindingStatus:
        raise _error("finding transitions require exact contract types")
    if type(reopen_evidence) is not bool:
        raise _error("reopen_evidence must be an exact bool")
    if target not in _FINDING_TRANSITIONS[finding.status]:
        raise _error(
            f"invalid finding transition: {finding.status.value} -> {target.value}"
        )
    closed_reopen = finding.status is FindingStatus.CLOSED and target is FindingStatus.REOPENED
    if closed_reopen and not reopen_evidence:
        raise _error("closed finding reopen requires explicit evidence signal")
    if reopen_evidence and not closed_reopen:
        raise _error("reopen evidence is valid only for CLOSED -> REOPENED")
    return replace(
        finding,
        status=target,
        fixed_by_sha=finding.fixed_by_sha if fixed_by_sha is None else fixed_by_sha,
        closure_review_round=(
            finding.closure_review_round
            if closure_review_round is None
            else closure_review_round
        ),
    )


class ProofStatus(str, Enum):
    VALID = "VALID"
    INVALIDATED = "INVALIDATED"
    NEW = "NEW"


class ProofCarryForwardDecision(str, Enum):
    CARRY_FORWARD_ALLOWED = "CARRY_FORWARD_ALLOWED"
    INVALIDATE = "INVALIDATE"
    CARRY_FORWARD_FORBIDDEN = "CARRY_FORWARD_FORBIDDEN"


@dataclass(frozen=True, slots=True)
class ProofRecord:
    proof_id: str
    subject: str
    subject_fingerprint: str
    dependency_fingerprint: str
    evidence_fingerprint: str
    source_review_round: int
    status: ProofStatus

    def __post_init__(self) -> None:
        _require_identifier(self.proof_id, "proof_id")
        if type(self.subject) is not str or not self.subject or self.subject != self.subject.strip():
            raise _error("subject must be exact non-empty text")
        if len(self.subject) > 512:
            raise _error("subject exceeds the bounded maximum")
        _require_fingerprint(self.subject_fingerprint, "subject_fingerprint")
        _require_fingerprint(self.dependency_fingerprint, "dependency_fingerprint")
        _require_fingerprint(self.evidence_fingerprint, "evidence_fingerprint")
        _require_round(self.source_review_round, "source_review_round")
        if type(self.status) is not ProofStatus:
            raise _error("status must be an exact ProofStatus")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_fingerprint": self.dependency_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "proof_id": self.proof_id,
            "source_review_round": self.source_review_round,
            "status": self.status.value,
            "subject": self.subject,
            "subject_fingerprint": self.subject_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: object) -> "ProofRecord":
        fields = {
            "dependency_fingerprint",
            "evidence_fingerprint",
            "proof_id",
            "source_review_round",
            "status",
            "subject",
            "subject_fingerprint",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("ProofRecord must contain the exact bounded field set")
        try:
            return cls(
                proof_id=data["proof_id"],
                subject=data["subject"],
                subject_fingerprint=data["subject_fingerprint"],
                dependency_fingerprint=data["dependency_fingerprint"],
                evidence_fingerprint=data["evidence_fingerprint"],
                source_review_round=data["source_review_round"],
                status=ProofStatus(data["status"]),
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed ProofRecord: {exc}") from exc


def evaluate_proof_carry_forward(
    proof: ProofRecord,
    current_subject_fingerprint: str,
    current_dependency_fingerprint: str,
) -> ProofCarryForwardDecision:
    """Decide proof reuse solely from status and exact current fingerprints."""
    if type(proof) is not ProofRecord:
        raise _error("proof must be an exact ProofRecord")
    _require_fingerprint(current_subject_fingerprint, "current_subject_fingerprint")
    _require_fingerprint(current_dependency_fingerprint, "current_dependency_fingerprint")
    if proof.status in {ProofStatus.NEW, ProofStatus.INVALIDATED}:
        return ProofCarryForwardDecision.CARRY_FORWARD_FORBIDDEN
    if proof.subject_fingerprint != current_subject_fingerprint:
        return ProofCarryForwardDecision.INVALIDATE
    if proof.dependency_fingerprint != current_dependency_fingerprint:
        return ProofCarryForwardDecision.INVALIDATE
    return ProofCarryForwardDecision.CARRY_FORWARD_ALLOWED


class ReviewEffort(str, Enum):
    FAST = "FAST"
    STANDARD = "STANDARD"
    DEEP = "DEEP"
    CRITICAL_SECOND_REVIEW = "CRITICAL_SECOND_REVIEW"


class RiskTaskClass(str, Enum):
    LOW_BOUNDED_NON_CRITICAL = "LOW_BOUNDED_NON_CRITICAL"
    STANDARD = "STANDARD"
    HIGH_IMPACT = "HIGH_IMPACT"
    CONTROL_PLANE_CRITICAL = "CONTROL_PLANE_CRITICAL"


class ChangedPathClass(str, Enum):
    DOCUMENTATION = "DOCUMENTATION"
    TESTS = "TESTS"
    PRODUCT_CODE = "PRODUCT_CODE"
    PUBLIC_API_OR_CONTRACT = "PUBLIC_API_OR_CONTRACT"
    AUTHORITY_OR_SECURITY = "AUTHORITY_OR_SECURITY"
    SCHEMA_OR_STORAGE = "SCHEMA_OR_STORAGE"
    TEST_INFRASTRUCTURE = "TEST_INFRASTRUCTURE"
    ROADMAP_OR_CONTROL_PLANE = "ROADMAP_OR_CONTROL_PLANE"


class DependencyBlastRadius(str, Enum):
    NONE = "NONE"
    LOCAL = "LOCAL"
    BOUNDED = "BOUNDED"
    WIDE = "WIDE"
    UNKNOWN = "UNKNOWN"


class ImpactConfidence(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RiskEvidence:
    task_class: RiskTaskClass
    changed_path_classes: tuple[ChangedPathClass, ...]
    dependency_blast_radius: DependencyBlastRadius
    public_api_or_contract_impact: bool
    authority_or_security_impact: bool
    schema_or_storage_impact: bool
    test_infrastructure_impact: bool
    roadmap_or_control_plane_criticality: bool
    impact_confidence: ImpactConfidence

    def __post_init__(self) -> None:
        if type(self.task_class) is not RiskTaskClass:
            raise _error("task_class must be an exact RiskTaskClass")
        if type(self.changed_path_classes) is not tuple or any(
            type(item) is not ChangedPathClass for item in self.changed_path_classes
        ):
            raise _error("changed_path_classes must be an exact tuple of closed values")
        if len(self.changed_path_classes) > _MAX_PATH_CLASSES:
            raise _error("changed_path_classes exceeds the bounded maximum")
        if len(set(self.changed_path_classes)) != len(self.changed_path_classes):
            raise _error("duplicate changed path class")
        if type(self.dependency_blast_radius) is not DependencyBlastRadius:
            raise _error("dependency_blast_radius must be an exact closed value")
        for name in (
            "public_api_or_contract_impact",
            "authority_or_security_impact",
            "schema_or_storage_impact",
            "test_infrastructure_impact",
            "roadmap_or_control_plane_criticality",
        ):
            if type(getattr(self, name)) is not bool:
                raise _error(f"{name} must be an exact bool")
        if type(self.impact_confidence) is not ImpactConfidence:
            raise _error("impact_confidence must be an exact ImpactConfidence")

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_or_security_impact": self.authority_or_security_impact,
            "changed_path_classes": [item.value for item in self.changed_path_classes],
            "dependency_blast_radius": self.dependency_blast_radius.value,
            "impact_confidence": self.impact_confidence.value,
            "public_api_or_contract_impact": self.public_api_or_contract_impact,
            "roadmap_or_control_plane_criticality": self.roadmap_or_control_plane_criticality,
            "schema_or_storage_impact": self.schema_or_storage_impact,
            "task_class": self.task_class.value,
            "test_infrastructure_impact": self.test_infrastructure_impact,
        }

    @classmethod
    def from_dict(cls, data: object) -> "RiskEvidence":
        fields = {
            "authority_or_security_impact",
            "changed_path_classes",
            "dependency_blast_radius",
            "impact_confidence",
            "public_api_or_contract_impact",
            "roadmap_or_control_plane_criticality",
            "schema_or_storage_impact",
            "task_class",
            "test_infrastructure_impact",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("RiskEvidence must contain the exact bounded field set")
        try:
            return cls(
                task_class=RiskTaskClass(data["task_class"]),
                changed_path_classes=tuple(
                    ChangedPathClass(item) for item in data["changed_path_classes"]
                ),
                dependency_blast_radius=DependencyBlastRadius(
                    data["dependency_blast_radius"]
                ),
                public_api_or_contract_impact=data["public_api_or_contract_impact"],
                authority_or_security_impact=data["authority_or_security_impact"],
                schema_or_storage_impact=data["schema_or_storage_impact"],
                test_infrastructure_impact=data["test_infrastructure_impact"],
                roadmap_or_control_plane_criticality=data[
                    "roadmap_or_control_plane_criticality"
                ],
                impact_confidence=ImpactConfidence(data["impact_confidence"]),
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed RiskEvidence: {exc}") from exc


def route_review_effort(evidence: RiskEvidence) -> ReviewEffort:
    """Select review effort deterministically from bounded evidence."""
    if type(evidence) is not RiskEvidence:
        raise _error("evidence must be an exact RiskEvidence")
    paths = set(evidence.changed_path_classes)
    if (
        evidence.authority_or_security_impact
        or ChangedPathClass.AUTHORITY_OR_SECURITY in paths
        or evidence.task_class is RiskTaskClass.CONTROL_PLANE_CRITICAL
        or evidence.roadmap_or_control_plane_criticality
    ):
        return ReviewEffort.CRITICAL_SECOND_REVIEW
    if evidence.impact_confidence is ImpactConfidence.UNKNOWN:
        return ReviewEffort.DEEP
    if (
        evidence.task_class is RiskTaskClass.HIGH_IMPACT
        or evidence.dependency_blast_radius
        in {DependencyBlastRadius.WIDE, DependencyBlastRadius.UNKNOWN}
        or evidence.public_api_or_contract_impact
        or evidence.schema_or_storage_impact
        or evidence.test_infrastructure_impact
        or bool(
            paths
            & {
                ChangedPathClass.PUBLIC_API_OR_CONTRACT,
                ChangedPathClass.SCHEMA_OR_STORAGE,
                ChangedPathClass.TEST_INFRASTRUCTURE,
                ChangedPathClass.ROADMAP_OR_CONTROL_PLANE,
            }
        )
    ):
        return ReviewEffort.DEEP
    if evidence.task_class is RiskTaskClass.LOW_BOUNDED_NON_CRITICAL:
        return ReviewEffort.FAST
    return ReviewEffort.STANDARD


@dataclass(frozen=True, slots=True)
class FindingRegistry:
    """One exact-head, exact-round semantic-review finding registry."""

    finding_records: tuple[FindingRecord, ...]
    review_round: int
    candidate_head_sha: str
    review_effort: ReviewEffort
    risk_evidence: RiskEvidence

    def __post_init__(self) -> None:
        if type(self.finding_records) is not tuple or len(self.finding_records) > 128:
            raise _error("finding_records must be an exact bounded tuple")
        if any(type(item) is not FindingRecord for item in self.finding_records):
            raise _error("finding_records must contain exact FindingRecord values")
        ids = [item.finding_id for item in self.finding_records]
        if len(set(ids)) != len(ids):
            raise _error("finding registry entries must be duplicate-free by finding_id")
        if tuple(sorted(ids)) != tuple(ids):
            raise _error("finding registry records must be canonically sorted by finding_id")
        _require_round(self.review_round, "review_round")
        if type(self.candidate_head_sha) is not str or _SHA_RE.fullmatch(self.candidate_head_sha) is None:
            raise _error("candidate_head_sha must be an exact lowercase 40-hex SHA")
        if type(self.review_effort) is not ReviewEffort:
            raise _error("review_effort must be an exact ReviewEffort")
        if type(self.risk_evidence) is not RiskEvidence:
            raise _error("risk_evidence must be exact RiskEvidence")
        if self.review_effort is not route_review_effort(self.risk_evidence):
            raise _error("review_effort must equal deterministic risk router output")
        for finding in self.finding_records:
            if finding.introduced_review_round > self.review_round:
                raise _error("finding introduction cannot be later than registry review_round")
            if (
                finding.closure_review_round is not None
                and finding.closure_review_round > self.review_round
            ):
                raise _error("finding closure cannot be later than registry review_round")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_head_sha": self.candidate_head_sha,
            "finding_records": [item.to_dict() for item in self.finding_records],
            "review_effort": self.review_effort.value,
            "review_round": self.review_round,
            "risk_evidence": self.risk_evidence.to_dict(),
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: object) -> "FindingRegistry":
        fields = {
            "candidate_head_sha",
            "finding_records",
            "review_effort",
            "review_round",
            "risk_evidence",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("FindingRegistry must contain the exact bounded field set")
        if type(data["finding_records"]) is not list:
            raise _error("finding_records must be an exact JSON list")
        try:
            return cls(
                finding_records=tuple(
                    FindingRecord.from_dict(item) for item in data["finding_records"]
                ),
                review_round=data["review_round"],
                candidate_head_sha=data["candidate_head_sha"],
                review_effort=ReviewEffort(data["review_effort"]),
                risk_evidence=RiskEvidence.from_dict(data["risk_evidence"]),
            )
        except (TypeError, ValueError) as exc:
            raise _error(f"malformed FindingRegistry: {exc}") from exc


def transition_registry_finding(
    registry: FindingRegistry,
    finding_id: str,
    target: FindingStatus,
    *,
    candidate_head_sha: str,
    review_round: int,
    reopen_evidence: bool = False,
    fixed_by_sha: str | None = None,
    closure_review_round: int | None = None,
) -> FindingRegistry:
    """Transition one finding while rebinding the registry to the exact new review subject."""
    if type(registry) is not FindingRegistry:
        raise _error("registry must be an exact FindingRegistry")
    _require_identifier(finding_id, "finding_id")
    _require_round(review_round, "review_round")
    if review_round < registry.review_round:
        raise _error("review_round cannot move backwards")
    if type(candidate_head_sha) is not str or _SHA_RE.fullmatch(candidate_head_sha) is None:
        raise _error("candidate_head_sha must be an exact lowercase 40-hex SHA")
    matches = [item for item in registry.finding_records if item.finding_id == finding_id]
    if len(matches) != 1:
        raise _error("finding_id must resolve exactly once in the registry")
    updated = transition_finding_status(
        matches[0],
        target,
        reopen_evidence=reopen_evidence,
        fixed_by_sha=fixed_by_sha,
        closure_review_round=closure_review_round,
    )
    records = tuple(
        updated if item.finding_id == finding_id else item
        for item in registry.finding_records
    )
    return replace(
        registry,
        finding_records=records,
        review_round=review_round,
        candidate_head_sha=candidate_head_sha,
    )
