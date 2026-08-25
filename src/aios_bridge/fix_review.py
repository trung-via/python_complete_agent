"""Deterministic Slice-C FIX proof reuse and delta/impact contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Callable, Mapping, Sequence

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.review_pipeline import (
    ImpactConfidence,
    ProofCarryForwardDecision,
    ProofRecord,
    evaluate_proof_carry_forward,
)


FIX_REVIEW_MODE_MARKER = "FIX_REVIEW_MODE:"
FIX_CONTEXT_PACK_MARKER = "FIX_CONTEXT_PACK_JSON:"
FIX_CONTEXT_SCHEMA_VERSION = "1"
MAX_FIX_CONTEXT_BYTES = 65_536
MAX_FIX_PATHS = 128
MAX_FIX_PROOFS = 64

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_FORBIDDEN_NAMESPACES = (
    ".git",
    ".ai/auth",
    ".ai/bridge",
    ".ai/inbox",
    ".ai/results",
    ".ai/runtime",
    ".ai/state",
)


class FixReviewContractError(ContinuityStateValidationError):
    """Malformed or unverifiable Slice-C review evidence."""


class FixReviewMode(str, Enum):
    COMPATIBILITY = "COMPATIBILITY"
    PROOF_REUSE_DELTA_IMPACT = "PROOF_REUSE_DELTA_IMPACT"


BlobResolver = Callable[[str, str], str | None]


def _error(message: str) -> FixReviewContractError:
    return FixReviewContractError(message)


def _top_level_values(content: str, marker: str) -> list[str]:
    if type(content) is not str:
        raise _error("review content must be exact text")
    values: list[str] = []
    fence: str | None = None
    for line in content.splitlines():
        stripped = line.lstrip()
        match = re.match(r"(`{3,}|~{3,})", stripped)
        if match:
            token = match.group(1)[0]
            if fence is None:
                fence = token
            elif fence == token:
                fence = None
            continue
        if fence is None and line.startswith(marker):
            values.append(line[len(marker) :].strip())
    return values


def parse_fix_review_mode(review_content: str) -> FixReviewMode:
    """Activate Slice C only through one exact, unfenced top-level marker."""
    values = _top_level_values(review_content, FIX_REVIEW_MODE_MARKER)
    if not values:
        return FixReviewMode.COMPATIBILITY
    if len(values) != 1:
        raise _error("review must contain at most one top-level FIX_REVIEW_MODE marker")
    if values[0] != FixReviewMode.PROOF_REUSE_DELTA_IMPACT.value:
        raise _error(f"unknown FIX_REVIEW_MODE: {values[0]!r}")
    return FixReviewMode.PROOF_REUSE_DELTA_IMPACT


def _canonical_path(value: object, name: str, *, test_path: bool = False) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise _error(f"{name} must be an exact non-empty path")
    if "\\" in value or _CONTROL_RE.search(value):
        raise _error(f"{name} must be a control-free POSIX path")
    pure = PurePosixPath(value)
    parts = value.split("/")
    if pure.is_absolute() or value.startswith("/") or any(
        part in {"", ".", ".."} for part in parts
    ) or str(pure) != value:
        raise _error(f"{name} must be a canonical repository-relative path")
    for namespace in _FORBIDDEN_NAMESPACES:
        if value == namespace or value.startswith(namespace + "/"):
            raise _error(f"{name} cannot grant Git/admin/runtime scope")
    if test_path and not value.startswith("tests/"):
        raise _error(f"{name} must live under tests/")
    return value


def _path_tuple(value: object, name: str, *, test_paths: bool = False) -> tuple[str, ...]:
    if type(value) is not list:
        raise _error(f"{name} must be an exact JSON list")
    if len(value) > MAX_FIX_PATHS:
        raise _error(f"{name} exceeds the bounded maximum")
    paths = tuple(
        _canonical_path(item, f"{name}[{index}]", test_path=test_paths)
        for index, item in enumerate(value)
    )
    if len(set(paths)) != len(paths):
        raise _error(f"{name} must be duplicate-free")
    return paths


def _identifier_tuple(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not list or len(value) > MAX_FIX_PATHS:
        raise _error(f"{name} must be a bounded exact JSON list")
    items: list[str] = []
    for item in value:
        if type(item) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", item) is None:
            raise _error(f"{name} contains a non-canonical identifier")
        items.append(item)
    if len(set(items)) != len(items):
        raise _error(f"{name} must be duplicate-free")
    return tuple(items)


@dataclass(frozen=True, slots=True)
class FixProofBinding:
    proof: ProofRecord
    subject_paths: tuple[str, ...]
    dependency_paths: tuple[str, ...]
    test_paths: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: object) -> "FixProofBinding":
        fields = {
            "proof_id", "subject", "subject_paths", "dependency_paths",
            "subject_fingerprint", "dependency_fingerprint", "evidence_fingerprint",
            "source_review_round", "status", "test_paths",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("proof binding must contain the exact bounded field set")
        try:
            proof = ProofRecord.from_dict(
                {
                    "proof_id": data["proof_id"],
                    "subject": data["subject"],
                    "subject_fingerprint": data["subject_fingerprint"],
                    "dependency_fingerprint": data["dependency_fingerprint"],
                    "evidence_fingerprint": data["evidence_fingerprint"],
                    "source_review_round": data["source_review_round"],
                    "status": data["status"],
                }
            )
        except (TypeError, ValueError, ContinuityStateValidationError) as exc:
            raise _error(f"malformed proof binding: {exc}") from exc
        subject_paths = _path_tuple(data["subject_paths"], "subject_paths")
        if not subject_paths:
            raise _error("subject_paths must not be empty")
        return cls(
            proof=proof,
            subject_paths=subject_paths,
            dependency_paths=_path_tuple(data["dependency_paths"], "dependency_paths"),
            test_paths=_path_tuple(data["test_paths"], "test_paths", test_paths=True),
        )

    def to_dict(self) -> dict[str, Any]:
        data = self.proof.to_dict()
        data.update(
            subject_paths=list(self.subject_paths),
            dependency_paths=list(self.dependency_paths),
            test_paths=list(self.test_paths),
        )
        return data


@dataclass(frozen=True, slots=True)
class FixContextPack:
    schema_version: str
    previous_reviewed_head_sha: str
    impact_confidence: ImpactConfidence
    open_finding_ids: tuple[str, ...]
    affected_paths: tuple[str, ...]
    protected_accepted_paths: tuple[str, ...]
    required_test_paths: tuple[str, ...]
    unknown_impact_fallback_test_paths: tuple[str, ...]
    proof_bindings: tuple[FixProofBinding, ...]

    @classmethod
    def from_dict(cls, data: object) -> "FixContextPack":
        fields = {
            "schema_version", "previous_reviewed_head_sha", "impact_confidence",
            "open_finding_ids", "affected_paths", "protected_accepted_paths",
            "required_test_paths", "unknown_impact_fallback_test_paths", "proof_bindings",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("FIX Context Pack must contain the exact bounded field set")
        if data["schema_version"] != FIX_CONTEXT_SCHEMA_VERSION:
            raise _error("unsupported FIX Context Pack schema_version")
        head = data["previous_reviewed_head_sha"]
        if type(head) is not str or _SHA_RE.fullmatch(head) is None:
            raise _error("previous_reviewed_head_sha must be exact lowercase 40-hex")
        if type(data["proof_bindings"]) is not list or len(data["proof_bindings"]) > MAX_FIX_PROOFS:
            raise _error("proof_bindings must be a bounded exact JSON list")
        try:
            confidence = ImpactConfidence(data["impact_confidence"])
        except (TypeError, ValueError) as exc:
            raise _error("impact_confidence must be an existing closed ImpactConfidence") from exc
        bindings = tuple(FixProofBinding.from_dict(item) for item in data["proof_bindings"])
        proof_ids = tuple(binding.proof.proof_id for binding in bindings)
        if len(set(proof_ids)) != len(proof_ids):
            raise _error("proof_bindings proof IDs must be duplicate-free")
        fallback = _path_tuple(
            data["unknown_impact_fallback_test_paths"],
            "unknown_impact_fallback_test_paths", test_paths=True,
        )
        if not fallback:
            raise _error("Slice-C optimization requires bounded fallback test paths")
        return cls(
            schema_version=data["schema_version"],
            previous_reviewed_head_sha=head,
            impact_confidence=confidence,
            open_finding_ids=_identifier_tuple(data["open_finding_ids"], "open_finding_ids"),
            affected_paths=_path_tuple(data["affected_paths"], "affected_paths"),
            protected_accepted_paths=_path_tuple(
                data["protected_accepted_paths"], "protected_accepted_paths"
            ),
            required_test_paths=_path_tuple(
                data["required_test_paths"], "required_test_paths", test_paths=True
            ),
            unknown_impact_fallback_test_paths=fallback,
            proof_bindings=bindings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "affected_paths": list(self.affected_paths),
            "impact_confidence": self.impact_confidence.value,
            "open_finding_ids": list(self.open_finding_ids),
            "previous_reviewed_head_sha": self.previous_reviewed_head_sha,
            "proof_bindings": [binding.to_dict() for binding in self.proof_bindings],
            "protected_accepted_paths": list(self.protected_accepted_paths),
            "required_test_paths": list(self.required_test_paths),
            "schema_version": self.schema_version,
            "unknown_impact_fallback_test_paths": list(
                self.unknown_impact_fallback_test_paths
            ),
        }


def parse_fix_context_pack(
    review_content: str,
    *,
    reviewed_task_head_sha: str,
) -> FixContextPack | None:
    """Parse and bind the opt-in pack to the exact review header candidate."""
    mode = parse_fix_review_mode(review_content)
    values = _top_level_values(review_content, FIX_CONTEXT_PACK_MARKER)
    if mode is FixReviewMode.COMPATIBILITY:
        if values:
            raise _error("FIX_CONTEXT_PACK_JSON requires exact Slice-C mode opt-in")
        return None
    if len(values) != 1:
        raise _error("Slice-C review requires exactly one top-level FIX_CONTEXT_PACK_JSON marker")
    if len(values[0].encode("utf-8")) > MAX_FIX_CONTEXT_BYTES:
        raise _error("FIX_CONTEXT_PACK_JSON exceeds its byte bound")
    try:
        raw = json.loads(values[0])
    except (TypeError, ValueError) as exc:
        raise _error(f"malformed FIX_CONTEXT_PACK_JSON: {exc}") from exc
    pack = FixContextPack.from_dict(raw)
    if type(reviewed_task_head_sha) is not str or not _SHA_RE.fullmatch(reviewed_task_head_sha):
        raise _error("REVIEWED_TASK_HEAD_SHA must be exact lowercase 40-hex")
    if pack.previous_reviewed_head_sha != reviewed_task_head_sha:
        raise _error("FIX Context Pack previous head does not match REVIEWED_TASK_HEAD_SHA")
    return pack


def canonical_proof_fingerprint(path_blobs: Mapping[str, str]) -> str:
    """Hash sorted exact path/Git-blob evidence; wording never participates."""
    if not isinstance(path_blobs, Mapping):
        raise _error("path_blobs must be a mapping")
    if len(path_blobs) > MAX_FIX_PATHS:
        raise _error("path_blobs exceeds the bounded maximum")
    canonical: list[list[str]] = []
    for path, blob_sha in path_blobs.items():
        clean = _canonical_path(path, "proof path")
        if type(blob_sha) is not str or _SHA_RE.fullmatch(blob_sha) is None:
            raise _error("proof blob identity must be exact lowercase 40-hex")
        canonical.append([clean, blob_sha])
    canonical.sort(key=lambda item: item[0])
    payload = json.dumps(canonical, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_fingerprint(
    head_sha: str,
    paths: tuple[str, ...],
    resolver: BlobResolver,
) -> str | None:
    evidence: dict[str, str] = {}
    for path in paths:
        try:
            blob = resolver(head_sha, path)
        except Exception:
            return None
        if type(blob) is not str or _SHA_RE.fullmatch(blob) is None:
            return None
        evidence[path] = blob
    return canonical_proof_fingerprint(evidence)


@dataclass(frozen=True, slots=True)
class FixImpactAnalysis:
    previous_reviewed_head_sha: str
    impact_confidence_observed: ImpactConfidence
    impact_scope_expanded: bool
    actual_changed_paths: tuple[str, ...]
    carried_forward_proof_ids: tuple[str, ...]
    invalidated_proof_ids: tuple[str, ...]
    forbidden_or_unknown_proof_ids: tuple[str, ...]
    selected_test_paths: tuple[str, ...]
    protected_accepted_paths_unchanged: bool
    proof_decisions: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actual_changed_paths": list(self.actual_changed_paths),
            "carried_forward_proof_ids": list(self.carried_forward_proof_ids),
            "forbidden_or_unknown_proof_ids": list(self.forbidden_or_unknown_proof_ids),
            "impact_confidence_observed": self.impact_confidence_observed.value,
            "impact_scope_expanded": self.impact_scope_expanded,
            "invalidated_proof_ids": list(self.invalidated_proof_ids),
            "previous_reviewed_head_sha": self.previous_reviewed_head_sha,
            "proof_decisions": [list(item) for item in self.proof_decisions],
            "protected_accepted_paths_unchanged": self.protected_accepted_paths_unchanged,
            "selected_test_paths": list(self.selected_test_paths),
        }

    @classmethod
    def from_dict(cls, data: object) -> "FixImpactAnalysis":
        fields = {
            "actual_changed_paths", "carried_forward_proof_ids",
            "forbidden_or_unknown_proof_ids", "impact_confidence_observed",
            "impact_scope_expanded", "invalidated_proof_ids", "previous_reviewed_head_sha",
            "proof_decisions", "protected_accepted_paths_unchanged", "selected_test_paths",
        }
        if type(data) is not dict or set(data) != fields:
            raise _error("FixImpactAnalysis must contain the exact field set")
        decisions_raw = data["proof_decisions"]
        if type(decisions_raw) is not list or any(
            type(item) is not list or len(item) != 2 or any(type(v) is not str for v in item)
            for item in decisions_raw
        ):
            raise _error("proof_decisions must be exact pairs")
        try:
            confidence = ImpactConfidence(data["impact_confidence_observed"])
        except (TypeError, ValueError) as exc:
            raise _error("analysis impact confidence is invalid") from exc
        head = data["previous_reviewed_head_sha"]
        if type(head) is not str or _SHA_RE.fullmatch(head) is None:
            raise _error("analysis previous head is invalid")
        for name in ("impact_scope_expanded", "protected_accepted_paths_unchanged"):
            if type(data[name]) is not bool:
                raise _error(f"{name} must be exact bool")
        return cls(
            previous_reviewed_head_sha=head,
            impact_confidence_observed=confidence,
            impact_scope_expanded=data["impact_scope_expanded"],
            actual_changed_paths=_path_tuple(data["actual_changed_paths"], "actual_changed_paths"),
            carried_forward_proof_ids=_identifier_tuple(data["carried_forward_proof_ids"], "carried_forward_proof_ids"),
            invalidated_proof_ids=_identifier_tuple(data["invalidated_proof_ids"], "invalidated_proof_ids"),
            forbidden_or_unknown_proof_ids=_identifier_tuple(data["forbidden_or_unknown_proof_ids"], "forbidden_or_unknown_proof_ids"),
            selected_test_paths=_path_tuple(data["selected_test_paths"], "selected_test_paths", test_paths=True),
            protected_accepted_paths_unchanged=data["protected_accepted_paths_unchanged"],
            proof_decisions=tuple((item[0], item[1]) for item in decisions_raw),
        )


def analyze_fix_impact(
    pack: FixContextPack,
    *,
    current_head_sha: str,
    previous_blob_resolver: BlobResolver,
    current_blob_resolver: BlobResolver,
    actual_changed_paths: Sequence[str] = (),
) -> FixImpactAnalysis:
    """Verify previous evidence, decide carry-forward, and select bounded impacted T1."""
    if type(pack) is not FixContextPack:
        raise _error("pack must be an exact FixContextPack")
    if type(current_head_sha) is not str or _SHA_RE.fullmatch(current_head_sha) is None:
        raise _error("current_head_sha must be exact lowercase 40-hex")
    if current_head_sha != pack.previous_reviewed_head_sha:
        raise _error("FIX analysis must start from the exact previous reviewed head")
    if isinstance(actual_changed_paths, (str, bytes)) or not isinstance(actual_changed_paths, Sequence):
        raise _error("actual_changed_paths must be a sequence")
    if len(actual_changed_paths) > MAX_FIX_PATHS:
        raise _error("actual_changed_paths exceeds the bounded maximum")
    actual = tuple(
        _canonical_path(path, f"actual_changed_paths[{index}]")
        for index, path in enumerate(actual_changed_paths)
    )
    if len(set(actual)) != len(actual):
        raise _error("actual_changed_paths must be duplicate-free")
    actual = tuple(sorted(actual))

    carried: list[str] = []
    invalidated: list[str] = []
    forbidden_unknown: list[str] = []
    decisions: list[tuple[str, str]] = []
    invalidated_tests: list[str] = []
    unknown = pack.impact_confidence is ImpactConfidence.UNKNOWN

    for binding in pack.proof_bindings:
        proof = binding.proof
        previous_subject = _resolve_fingerprint(
            pack.previous_reviewed_head_sha, binding.subject_paths, previous_blob_resolver
        )
        previous_dependency = _resolve_fingerprint(
            pack.previous_reviewed_head_sha, binding.dependency_paths, previous_blob_resolver
        )
        if previous_subject is not None and previous_subject != proof.subject_fingerprint:
            raise _error(f"reviewer subject fingerprint mismatch for proof {proof.proof_id}")
        if previous_dependency is not None and previous_dependency != proof.dependency_fingerprint:
            raise _error(f"reviewer dependency fingerprint mismatch for proof {proof.proof_id}")
        current_subject = _resolve_fingerprint(
            current_head_sha, binding.subject_paths, current_blob_resolver
        )
        current_dependency = _resolve_fingerprint(
            current_head_sha, binding.dependency_paths, current_blob_resolver
        )
        if None in (previous_subject, previous_dependency, current_subject, current_dependency):
            unknown = True
            forbidden_unknown.append(proof.proof_id)
            decisions.append((proof.proof_id, "UNKNOWN_IMPACT"))
            continue
        decision = evaluate_proof_carry_forward(proof, current_subject, current_dependency)
        if (
            decision is ProofCarryForwardDecision.CARRY_FORWARD_ALLOWED
            and set(actual) & set((*binding.subject_paths, *binding.dependency_paths))
        ):
            decision = ProofCarryForwardDecision.INVALIDATE
        decisions.append((proof.proof_id, decision.value))
        if decision is ProofCarryForwardDecision.CARRY_FORWARD_ALLOWED:
            carried.append(proof.proof_id)
        elif decision is ProofCarryForwardDecision.INVALIDATE:
            invalidated.append(proof.proof_id)
            invalidated_tests.extend(binding.test_paths)
        else:
            forbidden_unknown.append(proof.proof_id)
            invalidated_tests.extend(binding.test_paths)

    affected = set(pack.affected_paths)
    proof_surface = {
        path for binding in pack.proof_bindings
        for path in (*binding.subject_paths, *binding.dependency_paths)
    }
    escaped = any(path not in affected for path in actual)
    uncovered_protected = any(
        path in pack.protected_accepted_paths and path not in proof_surface
        for path in actual
    )
    if escaped or uncovered_protected:
        unknown = True
    protected_unchanged = not bool(set(actual) & set(pack.protected_accepted_paths))
    if unknown:
        selected = tuple(sorted(pack.unknown_impact_fallback_test_paths))
        confidence = ImpactConfidence.UNKNOWN
    else:
        selected = tuple(sorted(set(pack.required_test_paths) | set(invalidated_tests)))
        confidence = ImpactConfidence.KNOWN
    return FixImpactAnalysis(
        previous_reviewed_head_sha=pack.previous_reviewed_head_sha,
        impact_confidence_observed=confidence,
        impact_scope_expanded=unknown,
        actual_changed_paths=actual,
        carried_forward_proof_ids=tuple(carried),
        invalidated_proof_ids=tuple(invalidated),
        forbidden_or_unknown_proof_ids=tuple(forbidden_unknown),
        selected_test_paths=selected,
        protected_accepted_paths_unchanged=protected_unchanged,
        proof_decisions=tuple(decisions),
    )


def render_fix_executor_context(pack: FixContextPack, analysis: FixImpactAnalysis) -> bytes:
    """Render provider-neutral bounded guidance without creating authority."""
    if type(pack) is not FixContextPack or type(analysis) is not FixImpactAnalysis:
        raise _error("FIX executor context requires exact contract values")
    if pack.previous_reviewed_head_sha != analysis.previous_reviewed_head_sha:
        raise _error("FIX pack/analysis previous head mismatch")
    payload = {
        "affected_paths": list(pack.affected_paths),
        "fallback_test_paths": list(pack.unknown_impact_fallback_test_paths),
        "impact_confidence": analysis.impact_confidence_observed.value,
        "open_finding_ids": list(pack.open_finding_ids),
        "previous_reviewed_head_sha": pack.previous_reviewed_head_sha,
        "proof_states": [list(item) for item in analysis.proof_decisions],
        "protected_accepted_paths": list(pack.protected_accepted_paths),
        "required_impacted_test_paths": list(analysis.selected_test_paths),
    }
    text = (
        "FIX CONTEXT PACK BEGIN\n"
        "GUIDANCE_ONLY: roadmap/task authority remains external and unchanged\n"
        "FIX_CONTEXT_JSON: "
        + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\nFIX CONTEXT PACK END\n"
    )
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_FIX_CONTEXT_BYTES:
        raise _error("rendered FIX executor context exceeds byte bound")
    return encoded


def delta_impact_evidence(
    analysis: FixImpactAnalysis,
    *,
    selected_test_status: str,
) -> dict[str, Any]:
    if type(analysis) is not FixImpactAnalysis:
        raise _error("analysis must be exact FixImpactAnalysis")
    if selected_test_status not in {"PASS", "NOT_REQUIRED"}:
        raise _error("selected_test_status must be exact PASS or NOT_REQUIRED")
    evidence = analysis.to_dict()
    evidence.pop("proof_decisions")
    evidence["selected_test_status"] = selected_test_status
    return evidence


__all__ = [
    "FIX_CONTEXT_PACK_MARKER", "FIX_CONTEXT_SCHEMA_VERSION", "FIX_REVIEW_MODE_MARKER",
    "FixContextPack", "FixImpactAnalysis", "FixProofBinding", "FixReviewContractError",
    "FixReviewMode", "analyze_fix_impact", "canonical_proof_fingerprint",
    "delta_impact_evidence", "parse_fix_context_pack", "parse_fix_review_mode",
    "render_fix_executor_context",
]
