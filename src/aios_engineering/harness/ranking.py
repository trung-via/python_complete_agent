"""Pure deterministic H2 task-relevance ranking over H1 evidence metadata."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from src.aios_engineering.harness.contracts import (
    EvidenceKind,
    HarnessEvidenceExclusion,
    HarnessIntelligencePlan,
    HarnessReceipt,
    RepositoryEvidenceRef,
    _validate_hex_64,
    _validate_posix_path,
    _validate_task_id,
)
from src.aios_engineering.harness.discovery import RepositoryDiscoveryResult
from src.aios_engineering.harness.errors import (
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.fingerprint import canonical_json_bytes, compute_sha256


H2_RANKING_POLICY_VERSION: str = "h2-v1"
RANKING_SCHEMA_VERSION: str = "1"

MAX_EXACT_PATH_HINTS: int = 32
MAX_PATH_PREFIX_HINTS: int = 32
MAX_QUERY_TERMS: int = 64
MAX_QUERY_TERM_LENGTH: int = 64
MAX_SELECTED_EVIDENCE: int = 32

H2_TASK_RELEVANCE: str = "H2_TASK_RELEVANCE"
H2_ZERO_RELEVANCE: str = "H2_ZERO_RELEVANCE"
H2_SELECTION_BOUND: str = "H2_SELECTION_BOUND"

EXACT_PATH_WEIGHT: int = 600
PATH_PREFIX_WEIGHT: int = 300
QUERY_TERM_WEIGHT: int = 30
MAX_QUERY_TERM_SCORE: int = 180
PREFERRED_KIND_WEIGHT: int = 100
MAX_RELEVANCE_SCORE: int = 1000

_QUERY_TERM_RE = re.compile(r"\A[a-z0-9]+\Z", re.ASCII)
_PATH_TOKEN_RE = re.compile(r"[a-z0-9]+", re.ASCII)
_ASCII_LOWER_TRANSLATION = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
)


@dataclass(frozen=True)
class TaskRelevanceSpec:
    """Immutable, bounded metadata signals used by the H2 ranking policy."""

    task_id: str
    exact_paths: tuple[str, ...] = ()
    path_prefixes: tuple[str, ...] = ()
    query_terms: tuple[str, ...] = ()
    preferred_kinds: tuple[EvidenceKind, ...] = ()
    max_selected: int = MAX_SELECTED_EVIDENCE
    schema_version: str = RANKING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RANKING_SCHEMA_VERSION:
            raise HarnessValidationError(
                f"schema_version must be {RANKING_SCHEMA_VERSION!r}: got {self.schema_version!r}"
            )
        _validate_task_id(self.task_id)

        for field_name, value in (
            ("exact_paths", self.exact_paths),
            ("path_prefixes", self.path_prefixes),
            ("query_terms", self.query_terms),
            ("preferred_kinds", self.preferred_kinds),
        ):
            if type(value) is not tuple:
                raise HarnessValidationError(f"{field_name} must be an exact tuple")

        _validate_bounded_unique_tuple(
            "exact_paths",
            self.exact_paths,
            MAX_EXACT_PATH_HINTS,
        )
        _validate_bounded_unique_tuple(
            "path_prefixes",
            self.path_prefixes,
            MAX_PATH_PREFIX_HINTS,
        )
        _validate_bounded_unique_tuple(
            "query_terms",
            self.query_terms,
            MAX_QUERY_TERMS,
        )
        _validate_bounded_unique_tuple(
            "preferred_kinds",
            self.preferred_kinds,
            len(EvidenceKind),
        )

        for path in self.exact_paths:
            _validate_posix_path(path)
        for prefix in self.path_prefixes:
            _validate_posix_path(prefix)
        for term in self.query_terms:
            if type(term) is not str or not _QUERY_TERM_RE.fullmatch(term):
                raise HarnessValidationError(
                    "query terms must be non-empty lowercase ASCII alphanumeric tokens"
                )
            if len(term) > MAX_QUERY_TERM_LENGTH:
                raise HarnessValidationError(
                    f"query term length ({len(term)}) exceeds hard limit "
                    f"({MAX_QUERY_TERM_LENGTH})"
                )
        for kind in self.preferred_kinds:
            if type(kind) is not EvidenceKind:
                raise HarnessValidationError(
                    f"preferred_kinds entries must be exact EvidenceKind values: got {kind!r}"
                )

        if not any(
            (
                self.exact_paths,
                self.path_prefixes,
                self.query_terms,
                self.preferred_kinds,
            )
        ):
            raise HarnessValidationError("at least one task relevance signal is required")
        if type(self.max_selected) is not int:
            raise HarnessValidationError(
                f"max_selected must be an exact integer (bool forbidden): got {self.max_selected!r}"
            )
        if not (1 <= self.max_selected <= MAX_SELECTED_EVIDENCE):
            raise HarnessValidationError(
                f"max_selected must be between 1 and {MAX_SELECTED_EVIDENCE}: "
                f"got {self.max_selected}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "exact_paths": list(self.exact_paths),
            "max_selected": self.max_selected,
            "path_prefixes": list(self.path_prefixes),
            "preferred_kinds": [kind.value for kind in self.preferred_kinds],
            "query_terms": list(self.query_terms),
            "schema_version": self.schema_version,
            "task_id": self.task_id,
        }


@dataclass(frozen=True)
class RepositoryRankingResult:
    """Immutable, fingerprint-verified H2 ranking bound to H1 and an H2 spec."""

    task_id: str
    discovery_fingerprint: str
    input_candidate_set_fingerprint: str
    relevance_spec_fingerprint: str
    plan: HarnessIntelligencePlan
    ranking_fingerprint: str
    schema_version: str = RANKING_SCHEMA_VERSION
    policy_version: str = H2_RANKING_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RANKING_SCHEMA_VERSION:
            raise HarnessValidationError(
                f"schema_version must be {RANKING_SCHEMA_VERSION!r}: got {self.schema_version!r}"
            )
        if self.policy_version != H2_RANKING_POLICY_VERSION:
            raise HarnessValidationError(
                f"policy_version must be {H2_RANKING_POLICY_VERSION!r}: "
                f"got {self.policy_version!r}"
            )
        _validate_task_id(self.task_id)
        _validate_hex_64(self.discovery_fingerprint, "discovery_fingerprint")
        _validate_hex_64(
            self.input_candidate_set_fingerprint,
            "input_candidate_set_fingerprint",
        )
        _validate_hex_64(
            self.relevance_spec_fingerprint,
            "relevance_spec_fingerprint",
        )
        _validate_hex_64(self.ranking_fingerprint, "ranking_fingerprint")
        if not isinstance(self.plan, HarnessIntelligencePlan):
            raise HarnessValidationError(
                f"plan must be HarnessIntelligencePlan: got {self.plan!r}"
            )
        _revalidate_plan(self.plan)
        if self.task_id != self.plan.task_id:
            raise HarnessValidationError(
                "ranking result task_id must equal HarnessIntelligencePlan task_id"
            )
        _validate_plan_ranking_shape(self.plan)

        expected_fingerprint = _compute_ranking_fingerprint(
            schema_version=self.schema_version,
            policy_version=self.policy_version,
            task_id=self.task_id,
            discovery_fingerprint=self.discovery_fingerprint,
            input_candidate_set_fingerprint=self.input_candidate_set_fingerprint,
            relevance_spec_fingerprint=self.relevance_spec_fingerprint,
            plan=self.plan,
        )
        if self.ranking_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(
                "Ranking fingerprint mismatch: "
                f"expected {expected_fingerprint}, got {self.ranking_fingerprint}"
            )

    @classmethod
    def create(
        cls,
        discovery: RepositoryDiscoveryResult,
        spec: TaskRelevanceSpec,
        plan: HarnessIntelligencePlan,
    ) -> "RepositoryRankingResult":
        """Create a result after revalidating every H1/spec/plan cross-binding."""

        _revalidate_discovery(discovery)
        _revalidate_spec(spec)
        if not isinstance(plan, HarnessIntelligencePlan):
            raise HarnessValidationError(
                f"plan must be HarnessIntelligencePlan: got {plan!r}"
            )
        _revalidate_plan(plan)
        if plan.task_id != spec.task_id:
            raise HarnessValidationError("plan task_id must equal relevance spec task_id")
        if plan.snapshot != discovery.snapshot:
            raise HarnessValidationError("plan snapshot must equal H1 discovery snapshot")
        if len(plan.selected_evidence) + len(plan.excluded_evidence) != len(discovery.evidence):
            raise HarnessValidationError(
                "plan selected and excluded evidence must account for every H1 candidate"
            )

        expected_selected, expected_excluded = _ranked_partition(discovery, spec)
        if plan.selected_evidence != expected_selected:
            raise HarnessValidationError(
                "plan selected evidence does not match deterministic H2 ranking"
            )
        if plan.excluded_evidence != expected_excluded:
            raise HarnessValidationError(
                "plan excluded evidence does not match deterministic H2 accounting"
            )

        relevance_spec_fingerprint = compute_relevance_spec_fingerprint(spec)
        ranking_fingerprint = _compute_ranking_fingerprint(
            schema_version=RANKING_SCHEMA_VERSION,
            policy_version=H2_RANKING_POLICY_VERSION,
            task_id=spec.task_id,
            discovery_fingerprint=discovery.discovery_fingerprint,
            input_candidate_set_fingerprint=discovery.candidate_set_fingerprint,
            relevance_spec_fingerprint=relevance_spec_fingerprint,
            plan=plan,
        )
        return cls(
            task_id=spec.task_id,
            discovery_fingerprint=discovery.discovery_fingerprint,
            input_candidate_set_fingerprint=discovery.candidate_set_fingerprint,
            relevance_spec_fingerprint=relevance_spec_fingerprint,
            plan=plan,
            ranking_fingerprint=ranking_fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovery_fingerprint": self.discovery_fingerprint,
            "input_candidate_set_fingerprint": self.input_candidate_set_fingerprint,
            "plan": self.plan.to_dict(),
            "policy_version": self.policy_version,
            "ranking_fingerprint": self.ranking_fingerprint,
            "relevance_spec_fingerprint": self.relevance_spec_fingerprint,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
        }


def _validate_bounded_unique_tuple(
    field_name: str,
    values: tuple[Any, ...],
    hard_limit: int,
) -> None:
    if len(values) > hard_limit:
        raise HarnessValidationError(
            f"{field_name} count ({len(values)}) exceeds hard limit ({hard_limit})"
        )
    try:
        unique_count = len(set(values))
    except TypeError as exc:
        raise HarnessValidationError(f"{field_name} entries must be immutable values") from exc
    if unique_count != len(values):
        raise HarnessValidationError(f"duplicate {field_name} entries are forbidden")


def _revalidate_spec(spec: TaskRelevanceSpec) -> None:
    if not isinstance(spec, TaskRelevanceSpec):
        raise HarnessValidationError(
            f"spec must be TaskRelevanceSpec: got {spec!r}"
        )
    TaskRelevanceSpec(
        task_id=spec.task_id,
        exact_paths=spec.exact_paths,
        path_prefixes=spec.path_prefixes,
        query_terms=spec.query_terms,
        preferred_kinds=spec.preferred_kinds,
        max_selected=spec.max_selected,
        schema_version=spec.schema_version,
    )


def _revalidate_discovery(discovery: RepositoryDiscoveryResult) -> None:
    if not isinstance(discovery, RepositoryDiscoveryResult):
        raise HarnessValidationError(
            f"discovery must be RepositoryDiscoveryResult: got {discovery!r}"
        )
    RepositoryDiscoveryResult(
        snapshot=discovery.snapshot,
        evidence=discovery.evidence,
        exclusions=discovery.exclusions,
        candidate_set_fingerprint=discovery.candidate_set_fingerprint,
        discovery_fingerprint=discovery.discovery_fingerprint,
        schema_version=discovery.schema_version,
        policy_version=discovery.policy_version,
    )


def _revalidate_plan(plan: HarnessIntelligencePlan) -> None:
    HarnessIntelligencePlan(
        task_id=plan.task_id,
        snapshot=plan.snapshot,
        selected_evidence=plan.selected_evidence,
        excluded_evidence=plan.excluded_evidence,
        candidate_set_fingerprint=plan.candidate_set_fingerprint,
        plan_fingerprint=plan.plan_fingerprint,
        schema_version=plan.schema_version,
    )


def _path_tokens(path: str) -> frozenset[str]:
    """Tokenize a canonical path using ASCII alphanumerics and all else as delimiters."""

    ascii_lower_path = path.translate(_ASCII_LOWER_TRANSLATION)
    return frozenset(_PATH_TOKEN_RE.findall(ascii_lower_path))


def _score_evidence(evidence: RepositoryEvidenceRef, spec: TaskRelevanceSpec) -> int:
    score = 0
    if evidence.path in spec.exact_paths:
        score += EXACT_PATH_WEIGHT
    if any(
        evidence.path == prefix or evidence.path.startswith(prefix + "/")
        for prefix in spec.path_prefixes
    ):
        score += PATH_PREFIX_WEIGHT
    matched_terms = _path_tokens(evidence.path).intersection(spec.query_terms)
    score += min(len(matched_terms) * QUERY_TERM_WEIGHT, MAX_QUERY_TERM_SCORE)
    if evidence.evidence_kind in spec.preferred_kinds:
        score += PREFERRED_KIND_WEIGHT
    return min(score, MAX_RELEVANCE_SCORE)


def _rank_order_key(evidence: RepositoryEvidenceRef) -> tuple[int, str, str]:
    return (-evidence.priority, evidence.path, evidence.blob_sha)


def _ranked_partition(
    discovery: RepositoryDiscoveryResult,
    spec: TaskRelevanceSpec,
) -> tuple[tuple[RepositoryEvidenceRef, ...], tuple[HarnessEvidenceExclusion, ...]]:
    ranked = []
    for candidate in discovery.evidence:
        ranked.append(
            RepositoryEvidenceRef(
                path=candidate.path,
                blob_sha=candidate.blob_sha,
                evidence_kind=candidate.evidence_kind,
                reason_code=H2_TASK_RELEVANCE,
                priority=_score_evidence(candidate, spec),
                symbol_locator=candidate.symbol_locator,
            )
        )
    ranked.sort(key=_rank_order_key)

    selected: list[RepositoryEvidenceRef] = []
    excluded: list[HarnessEvidenceExclusion] = []
    for evidence in ranked:
        if evidence.priority == 0:
            excluded.append(
                HarnessEvidenceExclusion(
                    evidence=evidence,
                    reason_code=H2_ZERO_RELEVANCE,
                )
            )
        elif len(selected) < spec.max_selected:
            selected.append(evidence)
        else:
            excluded.append(
                HarnessEvidenceExclusion(
                    evidence=evidence,
                    reason_code=H2_SELECTION_BOUND,
                )
            )
    return tuple(selected), tuple(excluded)


def _validate_plan_ranking_shape(plan: HarnessIntelligencePlan) -> None:
    if len(plan.selected_evidence) > MAX_SELECTED_EVIDENCE:
        raise HarnessValidationError(
            f"selected evidence exceeds hard limit ({MAX_SELECTED_EVIDENCE})"
        )
    if plan.selected_evidence != tuple(sorted(plan.selected_evidence, key=_rank_order_key)):
        raise HarnessValidationError("selected evidence must be in deterministic ranking order")

    excluded_evidence = tuple(item.evidence for item in plan.excluded_evidence)
    if excluded_evidence != tuple(sorted(excluded_evidence, key=_rank_order_key)):
        raise HarnessValidationError("excluded evidence must be in deterministic ranking order")

    for evidence in plan.selected_evidence:
        if evidence.reason_code != H2_TASK_RELEVANCE or evidence.priority <= 0:
            raise HarnessValidationError(
                "selected evidence must be positive-score H2 task relevance evidence"
            )
    for exclusion in plan.excluded_evidence:
        if exclusion.evidence.reason_code != H2_TASK_RELEVANCE:
            raise HarnessValidationError(
                "excluded evidence must preserve the H2 task relevance identity"
            )
        expected_reason = (
            H2_ZERO_RELEVANCE
            if exclusion.evidence.priority == 0
            else H2_SELECTION_BOUND
        )
        if exclusion.reason_code != expected_reason:
            raise HarnessValidationError(
                "exclusion reason must match zero relevance or selection-bound semantics"
            )


def compute_relevance_spec_fingerprint(spec: TaskRelevanceSpec) -> str:
    """Return the canonical deterministic fingerprint for one validated H2 spec."""

    _revalidate_spec(spec)
    return compute_sha256(canonical_json_bytes(spec.to_dict()))


def _compute_ranking_fingerprint(
    *,
    schema_version: str,
    policy_version: str,
    task_id: str,
    discovery_fingerprint: str,
    input_candidate_set_fingerprint: str,
    relevance_spec_fingerprint: str,
    plan: HarnessIntelligencePlan,
) -> str:
    return compute_sha256(
        canonical_json_bytes(
            {
                "discovery_fingerprint": discovery_fingerprint,
                "input_candidate_set_fingerprint": input_candidate_set_fingerprint,
                "plan": plan.to_dict(),
                "policy_version": policy_version,
                "relevance_spec_fingerprint": relevance_spec_fingerprint,
                "schema_version": schema_version,
                "task_id": task_id,
            }
        )
    )


def rank_repository_evidence(
    discovery: RepositoryDiscoveryResult,
    spec: TaskRelevanceSpec,
) -> tuple[RepositoryRankingResult, HarnessReceipt]:
    """Rank and account for every H1 candidate without I/O or authority creation."""

    _revalidate_discovery(discovery)
    _revalidate_spec(spec)
    selected, excluded = _ranked_partition(discovery, spec)
    plan = HarnessIntelligencePlan.create(
        task_id=spec.task_id,
        snapshot=discovery.snapshot,
        selected_evidence=selected,
        excluded_evidence=excluded,
    )
    result = RepositoryRankingResult.create(discovery, spec, plan)
    input_fingerprint = compute_sha256(
        canonical_json_bytes(
            {
                "discovery_fingerprint": discovery.discovery_fingerprint,
                "input_candidate_set_fingerprint": discovery.candidate_set_fingerprint,
                "operation": "repository_evidence_ranking",
                "policy_version": H2_RANKING_POLICY_VERSION,
                "relevance_spec_fingerprint": result.relevance_spec_fingerprint,
                "schema_version": RANKING_SCHEMA_VERSION,
                "snapshot": discovery.snapshot.to_dict(),
            }
        )
    )
    receipt = HarnessReceipt(
        task_id=spec.task_id,
        repository_commit_sha=discovery.snapshot.repository_commit_sha,
        input_fingerprint=input_fingerprint,
        output_fingerprint=result.ranking_fingerprint,
        generator_version=H2_RANKING_POLICY_VERSION,
        candidate_count=len(discovery.evidence),
        selected_count=len(plan.selected_evidence),
        excluded_count=len(plan.excluded_evidence),
    )
    return result, receipt


__all__ = [
    "EXACT_PATH_WEIGHT",
    "H2_RANKING_POLICY_VERSION",
    "H2_SELECTION_BOUND",
    "H2_TASK_RELEVANCE",
    "H2_ZERO_RELEVANCE",
    "MAX_EXACT_PATH_HINTS",
    "MAX_PATH_PREFIX_HINTS",
    "MAX_QUERY_TERMS",
    "MAX_QUERY_TERM_LENGTH",
    "MAX_RELEVANCE_SCORE",
    "MAX_SELECTED_EVIDENCE",
    "PATH_PREFIX_WEIGHT",
    "PREFERRED_KIND_WEIGHT",
    "QUERY_TERM_WEIGHT",
    "RANKING_SCHEMA_VERSION",
    "RepositoryRankingResult",
    "TaskRelevanceSpec",
    "compute_relevance_spec_fingerprint",
    "rank_repository_evidence",
]
