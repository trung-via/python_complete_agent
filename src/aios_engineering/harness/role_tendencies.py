"""Canonical H3 component technical role summaries and evidence-based executor tendencies."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

from src.aios_engineering.harness.contracts import (
    HarnessReceipt,
    RepositorySnapshotRef,
    _validate_hex_40,
    _validate_hex_64,
    _validate_posix_path,
    _validate_task_id,
)
from src.aios_engineering.harness.errors import (
    HarnessError,
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.fingerprint import canonical_json_bytes, compute_sha256
from src.aios_engineering.harness.roles import (
    ArtifactRole,
    RepositoryRoleSummaryResult,
)
from src.aios_engineering.harness.structural_experience_graph import (
    H2GraphRelation,
    RepositoryStructuralExperienceGraphResult,
    StructuralComponentKind,
)


H3_ROLE_TENDENCY_POLICY_VERSION: str = "h3-role-tendency-v1"
H3_ROLE_TENDENCY_SCHEMA_VERSION: str = "1"

# Bounded finite scales
MAX_H3_COMPONENT_SUMMARIES: int = 512
MAX_H3_MEMBER_FILES_PER_COMPONENT: int = 256
MAX_H3_ROLES_PER_COMPONENT: int = 16
MAX_H3_SYMBOLS_PER_COMPONENT: int = 65536
MAX_H3_COMPONENT_RELATIONSHIPS: int = 4096
MAX_H3_EXECUTOR_PROFILES: int = 256
MAX_H3_OBSERVED_TASKS_PER_EXECUTOR: int = 1024
MAX_H3_COMPONENT_OBSERVATIONS_PER_EXECUTOR: int = 512
MAX_H3_REVIEW_FINDINGS_PER_EXECUTOR: int = 1024
MAX_H3_UNOBSERVED_ROLE_FILES: int = 131072
MAX_H3_FINGERPRINT_PAYLOAD_BYTES: int = 64 * 1024 * 1024


class RepositoryRoleTendencyError(HarnessError):
    """Base error for canonical H3 role tendency operations."""


class RepositoryRoleTendencyBoundError(RepositoryRoleTendencyError):
    """Raised when an H3 role tendency hard bound is exceeded."""


class RepositoryRoleTendencyConsistencyError(RepositoryRoleTendencyError):
    """Raised when upstream evidence or identities are contradictory or inconsistent."""


class H3MustNotOwn(str, Enum):
    """Immutable H0 negative-authority boundaries every H3 component must never own."""

    BRIDGE_TASK_AUTHORITY = "BRIDGE_TASK_AUTHORITY"
    BRIDGE_REVIEW_AUTHORITY = "BRIDGE_REVIEW_AUTHORITY"
    LEASE_AUTHORITY = "LEASE_AUTHORITY"
    EXECUTOR_DISPATCH_AUTHORITY = "EXECUTOR_DISPATCH_AUTHORITY"
    RETRY_REROUTE_AUTHORITY = "RETRY_REROUTE_AUTHORITY"
    MERGE_AUTHORITY = "MERGE_AUTHORITY"
    PAID_PROVIDER_AUTHORITY = "PAID_PROVIDER_AUTHORITY"


H3_MUST_NOT_OWN_DEFAULT: tuple[str, ...] = (
    H3MustNotOwn.BRIDGE_TASK_AUTHORITY.value,
    H3MustNotOwn.BRIDGE_REVIEW_AUTHORITY.value,
    H3MustNotOwn.LEASE_AUTHORITY.value,
    H3MustNotOwn.EXECUTOR_DISPATCH_AUTHORITY.value,
    H3MustNotOwn.RETRY_REROUTE_AUTHORITY.value,
    H3MustNotOwn.MERGE_AUTHORITY.value,
    H3MustNotOwn.PAID_PROVIDER_AUTHORITY.value,
)


def _validate_bounded_int(
    value: Any,
    field_name: str,
    *,
    min_val: int = 0,
    max_val: int | None = None,
) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise HarnessValidationError(f"{field_name} must be an exact integer, not bool or other type")
    if value < min_val:
        raise HarnessValidationError(f"{field_name} must be >= {min_val}: got {value}")
    if max_val is not None and value > max_val:
        raise RepositoryRoleTendencyBoundError(
            f"{field_name} ({value}) exceeds hard limit ({max_val})"
        )
    return value


def _bounded_fingerprint(payload: Any) -> str:
    encoded = canonical_json_bytes(payload)
    if len(encoded) > MAX_H3_FINGERPRINT_PAYLOAD_BYTES:
        raise RepositoryRoleTendencyBoundError(
            f"payload bytes ({len(encoded)}) exceeds hard limit ({MAX_H3_FINGERPRINT_PAYLOAD_BYTES})"
        )
    return compute_sha256(encoded)


@dataclass(frozen=True)
class ComponentMemberFile:
    """Exact file identity and observed artifact role within an H2 component."""

    path: str
    blob_sha: str
    observed_role: ArtifactRole | None

    def __post_init__(self) -> None:
        _validate_posix_path(self.path)
        _validate_hex_40(self.blob_sha, "blob_sha")
        if self.observed_role is not None and type(self.observed_role) is not ArtifactRole:
            raise HarnessValidationError(
                f"observed_role must be an exact ArtifactRole or None: got {self.observed_role!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "blob_sha": self.blob_sha,
            "observed_role": self.observed_role.value if self.observed_role is not None else None,
            "path": self.path,
        }


def _component_role_summary_payload(
    *,
    component_id: str,
    path: str,
    kind: StructuralComponentKind,
    member_files: Sequence[ComponentMemberFile],
    observed_roles: Sequence[ArtifactRole],
    symbol_count: int,
    inbound_component_count: int,
    outbound_component_count: int,
    must_not_own: Sequence[str],
) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "inbound_component_count": inbound_component_count,
        "kind": kind.value,
        "member_files": [f.to_dict() for f in member_files],
        "must_not_own": list(must_not_own),
        "observed_roles": [r.value for r in observed_roles],
        "outbound_component_count": outbound_component_count,
        "path": path,
        "policy_version": H3_ROLE_TENDENCY_POLICY_VERSION,
        "symbol_count": symbol_count,
    }


@dataclass(frozen=True)
class ComponentRoleSummary:
    """Deterministic, bounded technical role summary for one H2 structural component."""

    component_id: str
    path: str
    kind: StructuralComponentKind
    member_files: tuple[ComponentMemberFile, ...]
    observed_roles: tuple[ArtifactRole, ...]
    symbol_count: int
    inbound_component_count: int
    outbound_component_count: int
    must_not_own: tuple[str, ...]
    summary_fingerprint: str

    def __post_init__(self) -> None:
        if type(self.kind) is not StructuralComponentKind:
            raise HarnessValidationError(
                f"kind must be an exact StructuralComponentKind: got {self.kind!r}"
            )
        _validate_posix_path(self.path)
        expected_id = f"component:{self.kind.value}:{self.path}"
        if self.component_id != expected_id:
            raise HarnessValidationError(
                f"component_id must equal {expected_id!r}: got {self.component_id!r}"
            )
        if type(self.member_files) is not tuple:
            raise HarnessValidationError("member_files must be an exact tuple")
        if len(self.member_files) > MAX_H3_MEMBER_FILES_PER_COMPONENT:
            raise RepositoryRoleTendencyBoundError(
                f"member file count ({len(self.member_files)}) exceeds hard limit "
                f"({MAX_H3_MEMBER_FILES_PER_COMPONENT})"
            )
        seen_paths: set[str] = set()
        for idx, mf in enumerate(self.member_files):
            if type(mf) is not ComponentMemberFile:
                raise HarnessValidationError(
                    f"member_files must contain ComponentMemberFile: got {mf!r}"
                )
            if mf.path in seen_paths:
                raise HarnessValidationError(f"duplicate member file path: {mf.path}")
            seen_paths.add(mf.path)
            if idx > 0 and mf.path < self.member_files[idx - 1].path:
                raise HarnessValidationError("member_files must be sorted in canonical path order")

        if type(self.observed_roles) is not tuple:
            raise HarnessValidationError("observed_roles must be an exact tuple")
        if len(self.observed_roles) > MAX_H3_ROLES_PER_COMPONENT:
            raise RepositoryRoleTendencyBoundError(
                f"observed roles count ({len(self.observed_roles)}) exceeds hard limit "
                f"({MAX_H3_ROLES_PER_COMPONENT})"
            )
        seen_roles: set[ArtifactRole] = set()
        for idx, role in enumerate(self.observed_roles):
            if type(role) is not ArtifactRole:
                raise HarnessValidationError(f"observed_roles must contain ArtifactRole: got {role!r}")
            if role in seen_roles:
                raise HarnessValidationError(f"duplicate observed role: {role.value}")
            seen_roles.add(role)
            if idx > 0 and role.value < self.observed_roles[idx - 1].value:
                raise HarnessValidationError("observed_roles must be sorted canonically")

        _validate_bounded_int(
            self.symbol_count,
            "symbol_count",
            min_val=0,
            max_val=MAX_H3_SYMBOLS_PER_COMPONENT,
        )
        _validate_bounded_int(
            self.inbound_component_count,
            "inbound_component_count",
            min_val=0,
            max_val=MAX_H3_COMPONENT_RELATIONSHIPS,
        )
        _validate_bounded_int(
            self.outbound_component_count,
            "outbound_component_count",
            min_val=0,
            max_val=MAX_H3_COMPONENT_RELATIONSHIPS,
        )

        if type(self.must_not_own) is not tuple or self.must_not_own != H3_MUST_NOT_OWN_DEFAULT:
            raise HarnessValidationError(
                "must_not_own must be the exact canonical H3_MUST_NOT_OWN_DEFAULT tuple"
            )

        _validate_hex_64(self.summary_fingerprint, "summary_fingerprint")
        expected_fingerprint = _bounded_fingerprint(
            _component_role_summary_payload(
                component_id=self.component_id,
                path=self.path,
                kind=self.kind,
                member_files=self.member_files,
                observed_roles=self.observed_roles,
                symbol_count=self.symbol_count,
                inbound_component_count=self.inbound_component_count,
                outbound_component_count=self.outbound_component_count,
                must_not_own=self.must_not_own,
            )
        )
        if self.summary_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(
                f"ComponentRoleSummary fingerprint mismatch for {self.component_id}"
            )

    @classmethod
    def create(
        cls,
        *,
        component_id: str,
        path: str,
        kind: StructuralComponentKind,
        member_files: Sequence[ComponentMemberFile],
        observed_roles: Sequence[ArtifactRole],
        symbol_count: int,
        inbound_component_count: int,
        outbound_component_count: int,
    ) -> "ComponentRoleSummary":
        seen_member_paths: set[str] = set()
        for mf in member_files:
            if not isinstance(mf, ComponentMemberFile):
                raise HarnessValidationError(
                    f"member_files must contain ComponentMemberFile: got {mf!r}"
                )
            if mf.path in seen_member_paths:
                raise HarnessValidationError(f"duplicate member file path: {mf.path}")
            seen_member_paths.add(mf.path)

        seen_roles: set[ArtifactRole] = set()
        for r in observed_roles:
            if type(r) is not ArtifactRole:
                raise HarnessValidationError(
                    f"observed_roles must contain ArtifactRole: got {r!r}"
                )
            if r in seen_roles:
                raise HarnessValidationError(f"duplicate observed role: {r.value}")
            seen_roles.add(r)

        sorted_files = tuple(sorted(member_files, key=lambda f: f.path))
        sorted_roles = tuple(sorted(observed_roles, key=lambda r: r.value))
        fingerprint = _bounded_fingerprint(
            _component_role_summary_payload(
                component_id=component_id,
                path=path,
                kind=kind,
                member_files=sorted_files,
                observed_roles=sorted_roles,
                symbol_count=symbol_count,
                inbound_component_count=inbound_component_count,
                outbound_component_count=outbound_component_count,
                must_not_own=H3_MUST_NOT_OWN_DEFAULT,
            )
        )
        return cls(
            component_id=component_id,
            path=path,
            kind=kind,
            member_files=sorted_files,
            observed_roles=sorted_roles,
            symbol_count=symbol_count,
            inbound_component_count=inbound_component_count,
            outbound_component_count=outbound_component_count,
            must_not_own=H3_MUST_NOT_OWN_DEFAULT,
            summary_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "inbound_component_count": self.inbound_component_count,
            "kind": self.kind.value,
            "member_files": [f.to_dict() for f in self.member_files],
            "must_not_own": list(self.must_not_own),
            "observed_roles": [r.value for r in self.observed_roles],
            "outbound_component_count": self.outbound_component_count,
            "path": self.path,
            "summary_fingerprint": self.summary_fingerprint,
            "symbol_count": self.symbol_count,
        }


@dataclass(frozen=True)
class ExecutorComponentObservation:
    """Descriptive co-observation count of an executor on a component."""

    component_id: str
    coobserved_task_count: int

    def __post_init__(self) -> None:
        if type(self.component_id) is not str or not self.component_id.startswith("component:"):
            raise HarnessValidationError("component_id must be a valid component ID string")
        _validate_bounded_int(
            self.coobserved_task_count,
            "coobserved_task_count",
            min_val=1,
            max_val=MAX_H3_OBSERVED_TASKS_PER_EXECUTOR,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "coobserved_task_count": self.coobserved_task_count,
        }


def _executor_profile_payload(
    *,
    executor_id: str,
    observed_tasks: Sequence[str],
    observed_task_count: int,
    component_observations: Sequence[ExecutorComponentObservation],
    coobserved_component_ids: Sequence[str],
    coobserved_review_finding_ids: Sequence[str],
    coobserved_review_finding_count: int,
) -> dict[str, Any]:
    return {
        "component_observations": [c.to_dict() for c in component_observations],
        "coobserved_component_ids": list(coobserved_component_ids),
        "coobserved_review_finding_count": coobserved_review_finding_count,
        "coobserved_review_finding_ids": list(coobserved_review_finding_ids),
        "executor_id": executor_id,
        "observed_task_count": observed_task_count,
        "observed_tasks": list(observed_tasks),
        "policy_version": H3_ROLE_TENDENCY_POLICY_VERSION,
    }


@dataclass(frozen=True)
class ExecutorTendencyProfile:
    """Bounded, purely descriptive historical experience profile for one evidenced executor."""

    executor_id: str
    observed_tasks: tuple[str, ...]
    observed_task_count: int
    component_observations: tuple[ExecutorComponentObservation, ...]
    coobserved_component_ids: tuple[str, ...]
    coobserved_review_finding_ids: tuple[str, ...]
    coobserved_review_finding_count: int
    profile_fingerprint: str

    def __post_init__(self) -> None:
        if type(self.executor_id) is not str or not self.executor_id:
            raise HarnessValidationError("executor_id must be an exact non-empty string")
        if len(self.executor_id) > 64:
            raise RepositoryRoleTendencyBoundError("executor_id exceeds 64 chars")

        _validate_bounded_int(
            self.observed_task_count,
            "observed_task_count",
            min_val=1,
            max_val=MAX_H3_OBSERVED_TASKS_PER_EXECUTOR,
        )
        if type(self.observed_tasks) is not tuple or len(self.observed_tasks) != self.observed_task_count:
            raise HarnessValidationError("observed_tasks must match observed_task_count")
        seen_tasks: set[str] = set()
        for idx, task in enumerate(self.observed_tasks):
            _validate_task_id(task)
            if task in seen_tasks:
                raise HarnessValidationError(f"duplicate observed task: {task}")
            seen_tasks.add(task)
            if idx > 0 and task < self.observed_tasks[idx - 1]:
                raise HarnessValidationError("observed_tasks must be sorted in canonical order")

        if type(self.component_observations) is not tuple:
            raise HarnessValidationError("component_observations must be a tuple")
        if len(self.component_observations) > MAX_H3_COMPONENT_OBSERVATIONS_PER_EXECUTOR:
            raise RepositoryRoleTendencyBoundError(
                "component_observations count exceeds hard limit"
            )
        seen_comp_ids: set[str] = set()
        for idx, obs in enumerate(self.component_observations):
            if type(obs) is not ExecutorComponentObservation:
                raise HarnessValidationError("invalid ExecutorComponentObservation item")
            if obs.component_id in seen_comp_ids:
                raise HarnessValidationError(f"duplicate component observation: {obs.component_id}")
            seen_comp_ids.add(obs.component_id)
            if obs.coobserved_task_count > self.observed_task_count:
                raise HarnessValidationError(
                    f"coobserved_task_count ({obs.coobserved_task_count}) cannot exceed "
                    f"observed_task_count ({self.observed_task_count})"
                )
            if idx > 0 and obs.component_id < self.component_observations[idx - 1].component_id:
                raise HarnessValidationError("component_observations must be sorted canonically")

        expected_comp_ids = tuple(obs.component_id for obs in self.component_observations)
        if self.coobserved_component_ids != expected_comp_ids:
            raise HarnessValidationError(
                "coobserved_component_ids must match component_observations IDs exactly"
            )

        _validate_bounded_int(
            self.coobserved_review_finding_count,
            "coobserved_review_finding_count",
            min_val=0,
            max_val=MAX_H3_REVIEW_FINDINGS_PER_EXECUTOR,
        )
        if (
            type(self.coobserved_review_finding_ids) is not tuple
            or len(self.coobserved_review_finding_ids) != self.coobserved_review_finding_count
        ):
            raise HarnessValidationError("coobserved_review_finding_ids must match count")
        seen_findings: set[str] = set()
        for idx, finding in enumerate(self.coobserved_review_finding_ids):
            if type(finding) is not str or not finding:
                raise HarnessValidationError("finding ID must be non-empty str")
            if finding in seen_findings:
                raise HarnessValidationError(f"duplicate finding ID: {finding}")
            seen_findings.add(finding)
            if idx > 0 and finding < self.coobserved_review_finding_ids[idx - 1]:
                raise HarnessValidationError("coobserved_review_finding_ids must be sorted")

        _validate_hex_64(self.profile_fingerprint, "profile_fingerprint")
        expected_fingerprint = _bounded_fingerprint(
            _executor_profile_payload(
                executor_id=self.executor_id,
                observed_tasks=self.observed_tasks,
                observed_task_count=self.observed_task_count,
                component_observations=self.component_observations,
                coobserved_component_ids=self.coobserved_component_ids,
                coobserved_review_finding_ids=self.coobserved_review_finding_ids,
                coobserved_review_finding_count=self.coobserved_review_finding_count,
            )
        )
        if self.profile_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(
                f"ExecutorTendencyProfile fingerprint mismatch for {self.executor_id}"
            )

    @classmethod
    def create(
        cls,
        *,
        executor_id: str,
        observed_tasks: Sequence[str],
        component_observations: Sequence[ExecutorComponentObservation],
        coobserved_review_finding_ids: Sequence[str],
    ) -> "ExecutorTendencyProfile":
        seen_tasks: set[str] = set()
        for t in observed_tasks:
            _validate_task_id(t)
            if t in seen_tasks:
                raise HarnessValidationError(f"duplicate observed task: {t}")
            seen_tasks.add(t)

        seen_comp_obs: set[str] = set()
        for obs in component_observations:
            if not isinstance(obs, ExecutorComponentObservation):
                raise HarnessValidationError(
                    f"component_observations must contain ExecutorComponentObservation: got {obs!r}"
                )
            if obs.component_id in seen_comp_obs:
                raise HarnessValidationError(f"duplicate component observation: {obs.component_id}")
            seen_comp_obs.add(obs.component_id)

        seen_findings: set[str] = set()
        for f in coobserved_review_finding_ids:
            if type(f) is not str or not f:
                raise HarnessValidationError("finding ID must be non-empty str")
            if f in seen_findings:
                raise HarnessValidationError(f"duplicate finding ID: {f}")
            seen_findings.add(f)

        sorted_tasks = tuple(sorted(observed_tasks))
        sorted_comp_obs = tuple(sorted(component_observations, key=lambda c: c.component_id))
        coobserved_comp_ids = tuple(c.component_id for c in sorted_comp_obs)
        sorted_finding_ids = tuple(sorted(coobserved_review_finding_ids))
        fingerprint = _bounded_fingerprint(
            _executor_profile_payload(
                executor_id=executor_id,
                observed_tasks=sorted_tasks,
                observed_task_count=len(sorted_tasks),
                component_observations=sorted_comp_obs,
                coobserved_component_ids=coobserved_comp_ids,
                coobserved_review_finding_ids=sorted_finding_ids,
                coobserved_review_finding_count=len(sorted_finding_ids),
            )
        )
        return cls(
            executor_id=executor_id,
            observed_tasks=sorted_tasks,
            observed_task_count=len(sorted_tasks),
            component_observations=sorted_comp_obs,
            coobserved_component_ids=coobserved_comp_ids,
            coobserved_review_finding_ids=sorted_finding_ids,
            coobserved_review_finding_count=len(sorted_finding_ids),
            profile_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_observations": [c.to_dict() for c in self.component_observations],
            "coobserved_component_ids": list(self.coobserved_component_ids),
            "coobserved_review_finding_count": self.coobserved_review_finding_count,
            "coobserved_review_finding_ids": list(self.coobserved_review_finding_ids),
            "executor_id": self.executor_id,
            "observed_task_count": self.observed_task_count,
            "observed_tasks": list(self.observed_tasks),
            "profile_fingerprint": self.profile_fingerprint,
        }


def _result_payload(
    *,
    schema_version: str,
    policy_version: str,
    snapshot: RepositorySnapshotRef,
    h2_graph_fingerprint: str,
    role_summary_fingerprint: str,
    component_summaries: Sequence[ComponentRoleSummary],
    executor_profiles: Sequence[ExecutorTendencyProfile],
    unobserved_role_file_count: int,
) -> dict[str, Any]:
    return {
        "component_summaries": [c.to_dict() for c in component_summaries],
        "executor_profiles": [e.to_dict() for e in executor_profiles],
        "h2_graph_fingerprint": h2_graph_fingerprint,
        "policy_version": policy_version,
        "role_summary_fingerprint": role_summary_fingerprint,
        "schema_version": schema_version,
        "snapshot": snapshot.to_dict(),
        "unobserved_role_file_count": unobserved_role_file_count,
    }


@dataclass(frozen=True)
class RepositoryRoleTendencyResult:
    """Canonical H3 result composing technical role summaries and executor tendencies."""

    schema_version: str
    policy_version: str
    snapshot: RepositorySnapshotRef
    h2_graph_fingerprint: str
    role_summary_fingerprint: str
    component_summaries: tuple[ComponentRoleSummary, ...]
    executor_profiles: tuple[ExecutorTendencyProfile, ...]
    unobserved_role_file_count: int
    result_fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != H3_ROLE_TENDENCY_SCHEMA_VERSION:
            raise HarnessValidationError("invalid H3 role-tendency schema version")
        if self.policy_version != H3_ROLE_TENDENCY_POLICY_VERSION:
            raise HarnessValidationError("invalid H3 role-tendency policy version")
        if type(self.snapshot) is not RepositorySnapshotRef:
            raise HarnessValidationError("snapshot must be exact RepositorySnapshotRef")
        _validate_hex_64(self.h2_graph_fingerprint, "h2_graph_fingerprint")
        _validate_hex_64(self.role_summary_fingerprint, "role_summary_fingerprint")

        if type(self.component_summaries) is not tuple:
            raise HarnessValidationError("component_summaries must be an exact tuple")
        if len(self.component_summaries) > MAX_H3_COMPONENT_SUMMARIES:
            raise RepositoryRoleTendencyBoundError("component_summaries exceeds hard limit")
        seen_comp_ids: set[str] = set()
        for idx, comp in enumerate(self.component_summaries):
            if type(comp) is not ComponentRoleSummary:
                raise HarnessValidationError("invalid ComponentRoleSummary in result")
            if comp.component_id in seen_comp_ids:
                raise HarnessValidationError(f"duplicate component summary: {comp.component_id}")
            seen_comp_ids.add(comp.component_id)
            if idx > 0 and comp.component_id < self.component_summaries[idx - 1].component_id:
                raise HarnessValidationError("component_summaries must be sorted canonically")

        if type(self.executor_profiles) is not tuple:
            raise HarnessValidationError("executor_profiles must be an exact tuple")
        if len(self.executor_profiles) > MAX_H3_EXECUTOR_PROFILES:
            raise RepositoryRoleTendencyBoundError("executor_profiles exceeds hard limit")
        seen_exec_ids: set[str] = set()
        for idx, prof in enumerate(self.executor_profiles):
            if type(prof) is not ExecutorTendencyProfile:
                raise HarnessValidationError("invalid ExecutorTendencyProfile in result")
            if prof.executor_id in seen_exec_ids:
                raise HarnessValidationError(f"duplicate executor profile: {prof.executor_id}")
            seen_exec_ids.add(prof.executor_id)
            if idx > 0 and prof.executor_id < self.executor_profiles[idx - 1].executor_id:
                raise HarnessValidationError("executor_profiles must be sorted canonically")

        _validate_bounded_int(
            self.unobserved_role_file_count,
            "unobserved_role_file_count",
            min_val=0,
            max_val=MAX_H3_UNOBSERVED_ROLE_FILES,
        )

        _validate_hex_64(self.result_fingerprint, "result_fingerprint")
        expected_fingerprint = _bounded_fingerprint(
            _result_payload(
                schema_version=self.schema_version,
                policy_version=self.policy_version,
                snapshot=self.snapshot,
                h2_graph_fingerprint=self.h2_graph_fingerprint,
                role_summary_fingerprint=self.role_summary_fingerprint,
                component_summaries=self.component_summaries,
                executor_profiles=self.executor_profiles,
                unobserved_role_file_count=self.unobserved_role_file_count,
            )
        )
        if self.result_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError("RepositoryRoleTendencyResult fingerprint mismatch")

    @classmethod
    def create(
        cls,
        *,
        snapshot: RepositorySnapshotRef,
        h2_graph_fingerprint: str,
        role_summary_fingerprint: str,
        component_summaries: Sequence[ComponentRoleSummary],
        executor_profiles: Sequence[ExecutorTendencyProfile],
        unobserved_role_file_count: int,
    ) -> "RepositoryRoleTendencyResult":
        seen_comps: set[str] = set()
        for c in component_summaries:
            if not isinstance(c, ComponentRoleSummary):
                raise HarnessValidationError(
                    f"component_summaries must contain ComponentRoleSummary: got {c!r}"
                )
            if c.component_id in seen_comps:
                raise HarnessValidationError(f"duplicate component summary: {c.component_id}")
            seen_comps.add(c.component_id)

        seen_profs: set[str] = set()
        for p in executor_profiles:
            if not isinstance(p, ExecutorTendencyProfile):
                raise HarnessValidationError(
                    f"executor_profiles must contain ExecutorTendencyProfile: got {p!r}"
                )
            if p.executor_id in seen_profs:
                raise HarnessValidationError(f"duplicate executor profile: {p.executor_id}")
            seen_profs.add(p.executor_id)

        sorted_comps = tuple(sorted(component_summaries, key=lambda c: c.component_id))
        sorted_profs = tuple(sorted(executor_profiles, key=lambda p: p.executor_id))
        fingerprint = _bounded_fingerprint(
            _result_payload(
                schema_version=H3_ROLE_TENDENCY_SCHEMA_VERSION,
                policy_version=H3_ROLE_TENDENCY_POLICY_VERSION,
                snapshot=snapshot,
                h2_graph_fingerprint=h2_graph_fingerprint,
                role_summary_fingerprint=role_summary_fingerprint,
                component_summaries=sorted_comps,
                executor_profiles=sorted_profs,
                unobserved_role_file_count=unobserved_role_file_count,
            )
        )
        return cls(
            schema_version=H3_ROLE_TENDENCY_SCHEMA_VERSION,
            policy_version=H3_ROLE_TENDENCY_POLICY_VERSION,
            snapshot=snapshot,
            h2_graph_fingerprint=h2_graph_fingerprint,
            role_summary_fingerprint=role_summary_fingerprint,
            component_summaries=sorted_comps,
            executor_profiles=sorted_profs,
            unobserved_role_file_count=unobserved_role_file_count,
            result_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_summaries": [c.to_dict() for c in self.component_summaries],
            "executor_profiles": [e.to_dict() for e in self.executor_profiles],
            "h2_graph_fingerprint": self.h2_graph_fingerprint,
            "policy_version": self.policy_version,
            "result_fingerprint": self.result_fingerprint,
            "role_summary_fingerprint": self.role_summary_fingerprint,
            "schema_version": self.schema_version,
            "snapshot": self.snapshot.to_dict(),
            "unobserved_role_file_count": self.unobserved_role_file_count,
        }


def _revalidate_upstream(
    h2_graph: RepositoryStructuralExperienceGraphResult,
    role_summaries: RepositoryRoleSummaryResult,
) -> None:
    if type(h2_graph) is not RepositoryStructuralExperienceGraphResult:
        raise HarnessValidationError(
            f"h2_graph must be exact RepositoryStructuralExperienceGraphResult: got {h2_graph!r}"
        )
    if type(role_summaries) is not RepositoryRoleSummaryResult:
        raise HarnessValidationError(
            f"role_summaries must be exact RepositoryRoleSummaryResult: got {role_summaries!r}"
        )

    # Cross-binding verification
    if (
        h2_graph.repository_snapshot.repository_commit_sha
        != role_summaries.snapshot.repository_commit_sha
    ):
        raise RepositoryRoleTendencyConsistencyError(
            "repository commit SHA mismatch between H2 graph and role summary results"
        )
    if (
        h2_graph.repository_snapshot.repository_tree_sha
        != role_summaries.snapshot.repository_tree_sha
    ):
        raise RepositoryRoleTendencyConsistencyError(
            "repository tree SHA mismatch between H2 graph and role summary results"
        )
    if h2_graph.role_summary_fingerprint != role_summaries.role_summary_fingerprint:
        raise RepositoryRoleTendencyConsistencyError(
            "role_summary_fingerprint mismatch between H2 graph and role summary results"
        )

    # Revalidate internal contracts of both upstream inputs
    RepositoryStructuralExperienceGraphResult(
        task_id=h2_graph.task_id,
        repository_snapshot=h2_graph.repository_snapshot,
        control_plane_snapshot=h2_graph.control_plane_snapshot,
        discovery_fingerprint=h2_graph.discovery_fingerprint,
        candidate_set_fingerprint=h2_graph.candidate_set_fingerprint,
        experience_manifest_fingerprint=h2_graph.experience_manifest_fingerprint,
        ranking_fingerprint=h2_graph.ranking_fingerprint,
        relevance_spec_fingerprint=h2_graph.relevance_spec_fingerprint,
        role_summary_fingerprint=h2_graph.role_summary_fingerprint,
        import_graph_fingerprint=h2_graph.import_graph_fingerprint,
        components=h2_graph.components,
        symbols=h2_graph.symbols,
        nodes=h2_graph.nodes,
        edges=h2_graph.edges,
        unresolved_records=h2_graph.unresolved_records,
        graph_fingerprint=h2_graph.graph_fingerprint,
        schema_version=h2_graph.schema_version,
        policy_version=h2_graph.policy_version,
        authority_created=h2_graph.authority_created,
    )

    RepositoryRoleSummaryResult(
        task_id=role_summaries.task_id,
        snapshot=role_summaries.snapshot,
        ranking_fingerprint=role_summaries.ranking_fingerprint,
        h2_plan_fingerprint=role_summaries.h2_plan_fingerprint,
        summaries=role_summaries.summaries,
        role_summary_fingerprint=role_summaries.role_summary_fingerprint,
        schema_version=role_summaries.schema_version,
        policy_version=role_summaries.policy_version,
    )


def summarize_repository_roles_and_executor_tendencies(
    h2_graph: RepositoryStructuralExperienceGraphResult,
    role_summaries: RepositoryRoleSummaryResult,
) -> tuple[RepositoryRoleTendencyResult, HarnessReceipt]:
    """Pure composition of H2 structural/experience graph and historical role summaries."""
    _revalidate_upstream(h2_graph, role_summaries)

    # Map role summaries by exact (path, blob_sha)
    role_by_path_blob: dict[tuple[str, str], ArtifactRole] = {
        (s.path, s.blob_sha): s.artifact_role for s in role_summaries.summaries
    }

    # Extract member file relationships from H2 graph edges
    # FILE_BELONGS_TO_COMPONENT: source_node_id=file:<path>:<blob_sha>, target_node_id=component:...
    component_member_files: dict[str, list[ComponentMemberFile]] = defaultdict(list)
    unobserved_role_file_count = 0

    for edge in h2_graph.edges:
        if edge.relation is H2GraphRelation.FILE_BELONGS_TO_COMPONENT:
            comp_id = edge.target_node_id
            path = edge.evidence_path
            blob_sha = edge.evidence_blob_sha
            if (path, blob_sha) in role_by_path_blob:
                observed_role = role_by_path_blob[(path, blob_sha)]
            else:
                observed_role = None
                unobserved_role_file_count += 1
            component_member_files[comp_id].append(
                ComponentMemberFile(path=path, blob_sha=blob_sha, observed_role=observed_role)
            )

    # Count symbols per component from BELONGS_TO_COMPONENT edges
    component_symbol_counts: dict[str, int] = defaultdict(int)
    for edge in h2_graph.edges:
        if edge.relation is H2GraphRelation.BELONGS_TO_COMPONENT:
            component_symbol_counts[edge.target_node_id] += 1

    # Count inbound and outbound component import edges
    inbound_import_counts: dict[str, int] = defaultdict(int)
    outbound_import_counts: dict[str, int] = defaultdict(int)
    for edge in h2_graph.edges:
        if edge.relation is H2GraphRelation.COMPONENT_IMPORTS_COMPONENT:
            outbound_import_counts[edge.source_node_id] += 1
            inbound_import_counts[edge.target_node_id] += 1

    # Build ComponentRoleSummary for each component in H2 graph
    component_summaries: list[ComponentRoleSummary] = []
    for component in h2_graph.components:
        files = component_member_files.get(component.component_id, [])
        observed_roles_set: list[ArtifactRole] = []
        seen_roles: set[ArtifactRole] = set()
        for f in files:
            if f.observed_role is not None and f.observed_role not in seen_roles:
                seen_roles.add(f.observed_role)
                observed_roles_set.append(f.observed_role)
        summary = ComponentRoleSummary.create(
            component_id=component.component_id,
            path=component.path,
            kind=component.kind,
            member_files=files,
            observed_roles=observed_roles_set,
            symbol_count=component_symbol_counts.get(component.component_id, 0),
            inbound_component_count=inbound_import_counts.get(component.component_id, 0),
            outbound_component_count=outbound_import_counts.get(component.component_id, 0),
        )
        component_summaries.append(summary)

    # Extract executor experience relationships from H2 graph edges
    # 1. TASK_EXECUTED_BY_EXECUTOR: source_node_id=task:<task_id>, target_node_id=executor:<executor_id>
    executor_tasks: dict[str, set[str]] = defaultdict(set)
    for edge in h2_graph.edges:
        if edge.relation is H2GraphRelation.TASK_EXECUTED_BY_EXECUTOR:
            task_id = edge.source_node_id.removeprefix("task:")
            executor_id = edge.target_node_id.removeprefix("executor:")
            executor_tasks[executor_id].add(task_id)

    # 2. TASK_TOUCHES_COMPONENT: source_node_id=task:<task_id>, target_node_id=component:...
    task_components: dict[str, set[str]] = defaultdict(set)
    for edge in h2_graph.edges:
        if edge.relation is H2GraphRelation.TASK_TOUCHES_COMPONENT:
            task_id = edge.source_node_id.removeprefix("task:")
            task_components[task_id].add(edge.target_node_id)

    # 3. TASK_HAS_REVIEW_FINDING: source_node_id=task:<task_id>, target_node_id=review-finding:...
    task_findings: dict[str, set[str]] = defaultdict(set)
    for edge in h2_graph.edges:
        if edge.relation is H2GraphRelation.TASK_HAS_REVIEW_FINDING:
            task_id = edge.source_node_id.removeprefix("task:")
            task_findings[task_id].add(edge.target_node_id)

    # Build ExecutorTendencyProfile for each evidenced executor
    executor_profiles: list[ExecutorTendencyProfile] = []
    for executor_id in sorted(executor_tasks.keys()):
        tasks = executor_tasks[executor_id]
        comp_counts: dict[str, int] = defaultdict(int)
        findings_set: set[str] = set()

        for t in tasks:
            for comp_id in task_components.get(t, ()):
                comp_counts[comp_id] += 1
            for finding_id in task_findings.get(t, ()):
                findings_set.add(finding_id)

        comp_obs = [
            ExecutorComponentObservation(
                component_id=comp_id, coobserved_task_count=count
            )
            for comp_id, count in sorted(comp_counts.items())
        ]
        profile = ExecutorTendencyProfile.create(
            executor_id=executor_id,
            observed_tasks=sorted(tasks),
            component_observations=comp_obs,
            coobserved_review_finding_ids=sorted(findings_set),
        )
        executor_profiles.append(profile)

    result = RepositoryRoleTendencyResult.create(
        snapshot=h2_graph.repository_snapshot,
        h2_graph_fingerprint=h2_graph.graph_fingerprint,
        role_summary_fingerprint=role_summaries.role_summary_fingerprint,
        component_summaries=component_summaries,
        executor_profiles=executor_profiles,
        unobserved_role_file_count=unobserved_role_file_count,
    )

    input_fingerprint = _bounded_fingerprint(
        {
            "h2_graph_fingerprint": h2_graph.graph_fingerprint,
            "operation": "repository_role_tendency_summary",
            "policy_version": H3_ROLE_TENDENCY_POLICY_VERSION,
            "role_summary_fingerprint": role_summaries.role_summary_fingerprint,
            "schema_version": H3_ROLE_TENDENCY_SCHEMA_VERSION,
            "snapshot": h2_graph.repository_snapshot.to_dict(),
            "task_id": h2_graph.task_id,
        }
    )
    receipt = HarnessReceipt(
        task_id=h2_graph.task_id,
        repository_commit_sha=h2_graph.repository_snapshot.repository_commit_sha,
        input_fingerprint=input_fingerprint,
        output_fingerprint=result.result_fingerprint,
        generator_version=H3_ROLE_TENDENCY_POLICY_VERSION,
        candidate_count=len(h2_graph.components),
        selected_count=len(result.component_summaries),
        excluded_count=0,
        authority_created=False,
        network_used=False,
        llm_used=False,
        paid_api_used=False,
    )

    return result, receipt


__all__ = [
    "ComponentMemberFile",
    "ComponentRoleSummary",
    "ExecutorComponentObservation",
    "ExecutorTendencyProfile",
    "H3MustNotOwn",
    "H3_MUST_NOT_OWN_DEFAULT",
    "H3_ROLE_TENDENCY_POLICY_VERSION",
    "H3_ROLE_TENDENCY_SCHEMA_VERSION",
    "MAX_H3_COMPONENT_OBSERVATIONS_PER_EXECUTOR",
    "MAX_H3_COMPONENT_RELATIONSHIPS",
    "MAX_H3_COMPONENT_SUMMARIES",
    "MAX_H3_EXECUTOR_PROFILES",
    "MAX_H3_FINGERPRINT_PAYLOAD_BYTES",
    "MAX_H3_MEMBER_FILES_PER_COMPONENT",
    "MAX_H3_OBSERVED_TASKS_PER_EXECUTOR",
    "MAX_H3_REVIEW_FINDINGS_PER_EXECUTOR",
    "MAX_H3_ROLES_PER_COMPONENT",
    "MAX_H3_SYMBOLS_PER_COMPONENT",
    "MAX_H3_UNOBSERVED_ROLE_FILES",
    "RepositoryRoleTendencyBoundError",
    "RepositoryRoleTendencyConsistencyError",
    "RepositoryRoleTendencyError",
    "RepositoryRoleTendencyResult",
    "summarize_repository_roles_and_executor_tendencies",
]
