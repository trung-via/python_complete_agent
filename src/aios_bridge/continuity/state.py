"""Canonical Project State contract, parser, serializer, and freshness evaluator (ADR-011)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .errors import ContinuityFreshnessError, ContinuityStateValidationError


SCHEMA_VERSION: str = "1"
MAX_SERIALIZED_BYTES: int = 16384  # 16 KiB

_TASK_ID_PATTERN = re.compile(r"^TASK-\d+$")
_HEX_40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ACTOR_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_GIT_REF_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+(?:\.[a-zA-Z0-9_\-]+)*$")
_GIT_REF_FORBIDDEN_CHARS = set(" ~^:?*[\\]@\0\t\r\n")

_SENSITIVE_PATH_EXTENSIONS = {
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    ".pkcs12",
    ".crt",
    ".cer",
    ".der",
}
_SENSITIVE_SUBSTRINGS = {
    "id_rsa",
    "id_ecdsa",
    "id_ed25519",
    "id_dsa",
    "secret",
    "token",
    "credential",
    "password",
    "cookie",
    "profile",
    "private_key",
    "private-key",
}


class ContinuityPhase(str, Enum):
    """Lifecycle phase of the active project task."""
    TASK_DEFINED = "TASK_DEFINED"
    READY_FOR_RUN = "READY_FOR_RUN"
    RUNNING = "RUNNING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    FIXING = "FIXING"
    APPROVED = "APPROVED"
    MERGED = "MERGED"


class NextOperation(str, Enum):
    """Expected next control-plane operation."""
    PLAN = "PLAN"
    RUN_APPROVAL = "RUN_APPROVAL"
    WAIT_FOR_RESULT = "WAIT_FOR_RESULT"
    REVIEW = "REVIEW"
    FIX_APPROVAL = "FIX_APPROVAL"
    MERGE_APPROVAL = "MERGE_APPROVAL"
    NONE = "NONE"


class BrainOperation(str, Enum):
    """Bounded set of analytical and generation operations for brain actors."""
    TASK = "TASK"
    TASK_AND_PLAN = "TASK_AND_PLAN"
    PLAN = "PLAN"
    DIAGNOSIS = "DIAGNOSIS"
    PATCH_PROPOSAL = "PATCH_PROPOSAL"
    REVIEW = "REVIEW"


class FreshnessStatus(str, Enum):
    """Evaluation outcome for explicit repository state observation."""
    FRESH = "FRESH"
    STALE = "STALE"
    INCOMPLETE = "INCOMPLETE"


class FreshnessIssueCode(str, Enum):
    """Machine-readable reason code for freshness evaluation findings."""
    MAIN_SHA_MISMATCH = "MAIN_SHA_MISMATCH"
    TASK_SHA_MISMATCH = "TASK_SHA_MISMATCH"
    ARTIFACT_BLOB_MISMATCH = "ARTIFACT_BLOB_MISMATCH"
    MISSING_MAIN_OBSERVATION = "MISSING_MAIN_OBSERVATION"
    MISSING_TASK_OBSERVATION = "MISSING_TASK_OBSERVATION"
    MISSING_ARTIFACT_OBSERVATION = "MISSING_ARTIFACT_OBSERVATION"


PHASE_NEXT_OPERATION_MAP: dict[ContinuityPhase, NextOperation] = {
    ContinuityPhase.TASK_DEFINED: NextOperation.PLAN,
    ContinuityPhase.READY_FOR_RUN: NextOperation.RUN_APPROVAL,
    ContinuityPhase.RUNNING: NextOperation.WAIT_FOR_RESULT,
    ContinuityPhase.READY_FOR_REVIEW: NextOperation.REVIEW,
    ContinuityPhase.CHANGES_REQUIRED: NextOperation.FIX_APPROVAL,
    ContinuityPhase.FIXING: NextOperation.WAIT_FOR_RESULT,
    ContinuityPhase.APPROVED: NextOperation.MERGE_APPROVAL,
    ContinuityPhase.MERGED: NextOperation.NONE,
}

PHASES_REQUIRING_TASK_BRANCH_SHA: set[ContinuityPhase] = {
    ContinuityPhase.RUNNING,
    ContinuityPhase.READY_FOR_REVIEW,
    ContinuityPhase.CHANGES_REQUIRED,
    ContinuityPhase.FIXING,
    ContinuityPhase.APPROVED,
    ContinuityPhase.MERGED,
}


def _validate_exact_hex_sha(sha: Any, field_name: str) -> str:
    if isinstance(sha, bool) or not isinstance(sha, str) or not _HEX_40_PATTERN.match(sha):
        raise ContinuityStateValidationError(
            f"{field_name} must be an exact lowercase 40-character hexadecimal SHA, got: {sha!r}"
        )
    return sha


def _validate_safe_git_ref(ref: Any, field_name: str) -> str:
    if isinstance(ref, bool) or not isinstance(ref, str) or not ref:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if ref != ref.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {ref!r}"
        )
    ref_str = ref

    if any(c in _GIT_REF_FORBIDDEN_CHARS for c in ref_str) or any(ord(c) < 32 or ord(c) == 127 for c in ref_str):
        raise ContinuityStateValidationError(f"{field_name} contains forbidden character in Git ref: {ref!r}")
    if ref_str.startswith("/") or ref_str.endswith("/") or ref_str.startswith(".") or ref_str.endswith("."):
        raise ContinuityStateValidationError(f"{field_name} cannot start or end with '/' or '.': {ref!r}")
    if "//" in ref_str or ".." in ref_str or "@{" in ref_str:
        raise ContinuityStateValidationError(f"{field_name} contains forbidden sequence in Git ref: {ref!r}")

    components = ref_str.split("/")
    for comp in components:
        if not comp:
            raise ContinuityStateValidationError(f"{field_name} contains empty component: {ref!r}")
        if comp.startswith(".") or comp.endswith(".lock"):
            raise ContinuityStateValidationError(
                f"{field_name} component cannot start with '.' or end with '.lock': {ref!r}"
            )
        if not _GIT_REF_COMPONENT_PATTERN.match(comp):
            raise ContinuityStateValidationError(
                f"{field_name} component has invalid characters: {comp!r} in {ref!r}"
            )

    return ref_str


def _validate_actor_id(actor_id: Any, field_name: str) -> str:
    if isinstance(actor_id, bool) or not isinstance(actor_id, str) or not actor_id:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if actor_id != actor_id.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {actor_id!r}"
        )
    actor_str = actor_id
    if not _ACTOR_ID_PATTERN.match(actor_str):
        raise ContinuityStateValidationError(
            f"{field_name} must be a conservative lowercase identifier (e.g. 'chatgpt-chat', 'antigravity'), got: {actor_id!r}"
        )
    return actor_str


def _validate_artifact_path(path: Any, field_name: str) -> str:
    if isinstance(path, bool) or not isinstance(path, str) or not path:
        raise ContinuityStateValidationError(f"{field_name} must be a non-empty string")
    if path != path.strip():
        raise ContinuityStateValidationError(
            f"{field_name} must not contain leading or trailing whitespace: {path!r}"
        )
    path_str = path

    # Reject backslashes, double slashes, traversal, absolute paths
    if "\\" in path_str:
        raise ContinuityStateValidationError(
            f"{field_name} must use POSIX forward slashes, backslashes are forbidden: {path!r}"
        )
    if path_str.startswith("/") or re.match(r"^[a-zA-Z]:", path_str):
        raise ContinuityStateValidationError(f"{field_name} must be a relative path: {path!r}")
    
    parts = path_str.split("/")
    if any(p == ".." for p in parts) or any(p == "" for p in parts):
        raise ContinuityStateValidationError(f"{field_name} must not contain empty or '..' segments: {path!r}")
    if not path_str.startswith(".ai/"):
        raise ContinuityStateValidationError(f"{field_name} must live under '.ai/', got: {path!r}")

    # Sensitive path rejection across ALL path components regardless of file extension
    p = PurePosixPath(path_str)
    if p.suffix.lower() in _SENSITIVE_PATH_EXTENSIONS:
        raise ContinuityStateValidationError(f"Sensitive file extension rejected in {field_name}: {path!r}")

    for component in parts:
        comp_lower = component.lower()
        if comp_lower == ".env" or comp_lower.startswith(".env."):
            raise ContinuityStateValidationError(f"Sensitive environment path rejected in {field_name}: {path!r}")
        for sub in _SENSITIVE_SUBSTRINGS:
            if sub in comp_lower:
                raise ContinuityStateValidationError(
                    f"Sensitive keyword/pattern '{sub}' rejected in {field_name}: {path!r}"
                )

    return path_str


@dataclass(frozen=True)
class BranchState:
    """Immutable Git branch and optional commit SHA pointer."""
    branch: str
    sha: str | None = None

    def __post_init__(self) -> None:
        _validate_safe_git_ref(self.branch, "BranchState.branch")
        if self.sha is not None:
            _validate_exact_hex_sha(self.sha, "BranchState.sha")

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch": self.branch,
            "sha": self.sha,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "BranchState") -> BranchState:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"branch", "sha"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        if "branch" not in data:
            raise ContinuityStateValidationError(f"Missing required field 'branch' in {context_name}")
        return cls(
            branch=data["branch"],
            sha=data.get("sha"),
        )


@dataclass(frozen=True)
class ArtifactRef:
    """Immutable pointer to a synchronized Git blob artifact."""
    path: str
    ref: str
    blob_sha: str

    def __post_init__(self) -> None:
        _validate_artifact_path(self.path, "ArtifactRef.path")
        _validate_safe_git_ref(self.ref, "ArtifactRef.ref")
        _validate_exact_hex_sha(self.blob_sha, "ArtifactRef.blob_sha")

    def to_dict(self) -> dict[str, Any]:
        return {
            "blob_sha": self.blob_sha,
            "path": self.path,
            "ref": self.ref,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "ArtifactRef") -> ArtifactRef:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"blob_sha", "path", "ref"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        for req in ("path", "ref", "blob_sha"):
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in {context_name}")
        return cls(
            path=data["path"],
            ref=data["ref"],
            blob_sha=data["blob_sha"],
        )


@dataclass(frozen=True)
class ContinuityArtifacts:
    """Immutable set of authoritative artifact pointers for the active task."""
    task: ArtifactRef
    contracts: tuple[ArtifactRef, ...] = ()
    plan: ArtifactRef | None = None
    result: ArtifactRef | None = None
    review: ArtifactRef | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task, ArtifactRef):
            raise ContinuityStateValidationError(f"task must be an ArtifactRef, got: {type(self.task).__name__}")

        if not isinstance(self.contracts, tuple):
            try:
                object.__setattr__(self, "contracts", tuple(self.contracts))
            except Exception as e:
                raise ContinuityStateValidationError("contracts must be an iterable of ArtifactRef") from e

        for idx, c in enumerate(self.contracts):
            if not isinstance(c, ArtifactRef):
                raise ContinuityStateValidationError(
                    f"contracts[{idx}] must be an ArtifactRef, got: {type(c).__name__}"
                )

        if self.plan is not None and not isinstance(self.plan, ArtifactRef):
            raise ContinuityStateValidationError(f"plan must be an ArtifactRef or None, got: {type(self.plan).__name__}")
        if self.result is not None and not isinstance(self.result, ArtifactRef):
            raise ContinuityStateValidationError(f"result must be an ArtifactRef or None, got: {type(self.result).__name__}")
        if self.review is not None and not isinstance(self.review, ArtifactRef):
            raise ContinuityStateValidationError(f"review must be an ArtifactRef or None, got: {type(self.review).__name__}")

        # Enforce global authoritative artifact path uniqueness across all present roles (C2 / AIP-3)
        all_refs: list[ArtifactRef] = [self.task]
        all_refs.extend(self.contracts)
        if self.plan is not None:
            all_refs.append(self.plan)
        if self.result is not None:
            all_refs.append(self.result)
        if self.review is not None:
            all_refs.append(self.review)

        seen_paths: set[str] = set()
        for ref_item in all_refs:
            if ref_item.path in seen_paths:
                raise ContinuityStateValidationError(
                    f"Duplicate authoritative artifact path detected across role set: {ref_item.path!r}"
                )
            seen_paths.add(ref_item.path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contracts": [c.to_dict() for c in self.contracts],
            "plan": self.plan.to_dict() if self.plan is not None else None,
            "result": self.result.to_dict() if self.result is not None else None,
            "review": self.review.to_dict() if self.review is not None else None,
            "task": self.task.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "ContinuityArtifacts") -> ContinuityArtifacts:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"contracts", "plan", "result", "review", "task"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        if "task" not in data:
            raise ContinuityStateValidationError(f"Missing required field 'task' in {context_name}")
        task_ref = ArtifactRef.from_dict(data["task"], f"{context_name}.task")

        contracts_raw = data.get("contracts", [])
        if not isinstance(contracts_raw, list):
            raise ContinuityStateValidationError(f"{context_name}.contracts must be a list")
        contracts_list: list[ArtifactRef] = []
        for idx, c in enumerate(contracts_raw):
            contracts_list.append(ArtifactRef.from_dict(c, f"{context_name}.contracts[{idx}]"))

        plan_ref = ArtifactRef.from_dict(data["plan"], f"{context_name}.plan") if data.get("plan") is not None else None
        result_ref = ArtifactRef.from_dict(data["result"], f"{context_name}.result") if data.get("result") is not None else None
        review_ref = ArtifactRef.from_dict(data["review"], f"{context_name}.review") if data.get("review") is not None else None

        return cls(
            task=task_ref,
            contracts=tuple(contracts_list),
            plan=plan_ref,
            result=result_ref,
            review=review_ref,
        )


@dataclass(frozen=True)
class BrainState:
    """Immutable descriptive metadata for brain actors."""
    last_id: str | None = None
    last_operation: BrainOperation | None = None

    def __post_init__(self) -> None:
        if self.last_id is not None:
            _validate_actor_id(self.last_id, "BrainState.last_id")
        if self.last_operation is not None:
            if not isinstance(self.last_operation, BrainOperation):
                try:
                    object.__setattr__(self, "last_operation", BrainOperation(self.last_operation))
                except Exception as e:
                    valid_ops = ", ".join(o.value for o in BrainOperation)
                    raise ContinuityStateValidationError(
                        f"Invalid BrainOperation: {self.last_operation!r}. Valid values: {valid_ops}"
                    ) from e

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_id": self.last_id,
            "last_operation": self.last_operation.value if self.last_operation is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "BrainState") -> BrainState:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"last_id", "last_operation"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")

        last_op_raw = data.get("last_operation")
        last_op: BrainOperation | None = None
        if last_op_raw is not None:
            try:
                last_op = BrainOperation(last_op_raw)
            except ValueError as e:
                valid_ops = ", ".join(o.value for o in BrainOperation)
                raise ContinuityStateValidationError(
                    f"Invalid BrainOperation in {context_name}.last_operation: {last_op_raw!r}. Valid values: {valid_ops}"
                ) from e

        return cls(
            last_id=data.get("last_id"),
            last_operation=last_op,
        )


@dataclass(frozen=True)
class ExecutorState:
    """Immutable descriptive metadata for executor actors."""
    last_id: str | None = None

    def __post_init__(self) -> None:
        if self.last_id is not None:
            _validate_actor_id(self.last_id, "ExecutorState.last_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_id": self.last_id,
        }

    @classmethod
    def from_dict(cls, data: Any, context_name: str = "ExecutorState") -> ExecutorState:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"{context_name} must be a dict, got: {type(data).__name__}")
        allowed_keys = {"last_id"}
        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown fields in {context_name}: {sorted(extra_keys)}")
        return cls(
            last_id=data.get("last_id"),
        )


@dataclass(frozen=True)
class ContinuityState:
    """
    Immutable, deterministic snapshot of cross-agent project continuity state.
    Conforms to ADR-010 and ADR-011 Schema Version 1.
    """
    task_id: str
    phase: ContinuityPhase
    next_operation: NextOperation
    main: BranchState
    task_branch: BranchState
    artifacts: ContinuityArtifacts
    brain: BrainState = BrainState()
    executor: ExecutorState = ExecutorState()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        # 1. Schema version
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )

        # 2. Task ID (strict case-sensitive)
        if isinstance(self.task_id, bool) or not isinstance(self.task_id, str):
            raise ContinuityStateValidationError("task_id must be a non-empty string")
        if not _TASK_ID_PATTERN.match(self.task_id):
            raise ContinuityStateValidationError(
                f"task_id must match exact case-sensitive '^TASK-\\d+$', got: {self.task_id!r}"
            )

        # 3. Phase and NextOperation validation
        if not isinstance(self.phase, ContinuityPhase):
            try:
                object.__setattr__(self, "phase", ContinuityPhase(self.phase))
            except Exception as e:
                valid_phases = ", ".join(p.value for p in ContinuityPhase)
                raise ContinuityStateValidationError(
                    f"Invalid ContinuityPhase: {self.phase!r}. Valid values: {valid_phases}"
                ) from e

        if not isinstance(self.next_operation, NextOperation):
            try:
                object.__setattr__(self, "next_operation", NextOperation(self.next_operation))
            except Exception as e:
                valid_ops = ", ".join(o.value for o in NextOperation)
                raise ContinuityStateValidationError(
                    f"Invalid NextOperation: {self.next_operation!r}. Valid values: {valid_ops}"
                ) from e

        expected_next_op = PHASE_NEXT_OPERATION_MAP[self.phase]
        if self.next_operation != expected_next_op:
            raise ContinuityStateValidationError(
                f"Incompatible phase/next_operation pair: phase={self.phase.value} requires "
                f"next_operation={expected_next_op.value}, got: {self.next_operation.value}"
            )

        # 4. Main branch requirements
        if not isinstance(self.main, BranchState):
            raise ContinuityStateValidationError(f"main must be a BranchState, got: {type(self.main).__name__}")
        if self.main.sha is None:
            raise ContinuityStateValidationError("main.sha is required and cannot be null")

        # 5. Task branch requirements
        if not isinstance(self.task_branch, BranchState):
            raise ContinuityStateValidationError(f"task_branch must be a BranchState, got: {type(self.task_branch).__name__}")
        if self.phase in PHASES_REQUIRING_TASK_BRANCH_SHA and self.task_branch.sha is None:
            raise ContinuityStateValidationError(
                f"task_branch.sha is required for phase {self.phase.value}, but was null"
            )

        # 6. Artifact exact namespace + task identity consistency
        if not isinstance(self.artifacts, ContinuityArtifacts):
            raise ContinuityStateValidationError(f"artifacts must be a ContinuityArtifacts, got: {type(self.artifacts).__name__}")

        # Task artifact exact canonical path: .ai/tasks/{task_id}.md
        expected_task_path = f".ai/tasks/{self.task_id}.md"
        if self.artifacts.task.path != expected_task_path:
            raise ContinuityStateValidationError(
                f"artifacts.task path must be exactly {expected_task_path!r}, got: {self.artifacts.task.path!r}"
            )

        # Result artifact exact canonical path: .ai/results/RESULT-{task_num}.md
        if self.artifacts.result is not None:
            expected_result_path = f".ai/results/RESULT-{self.task_id[5:]}.md"
            if self.artifacts.result.path != expected_result_path:
                raise ContinuityStateValidationError(
                    f"artifacts.result path must be exactly {expected_result_path!r}, got: {self.artifacts.result.path!r}"
                )

        # Review artifact exact canonical path: .ai/reviews/REVIEW-{task_num}.md
        if self.artifacts.review is not None:
            expected_review_path = f".ai/reviews/REVIEW-{self.task_id[5:]}.md"
            if self.artifacts.review.path != expected_review_path:
                raise ContinuityStateValidationError(
                    f"artifacts.review path must be exactly {expected_review_path!r}, got: {self.artifacts.review.path!r}"
                )

        # Plan artifact task identity check if declared
        if self.artifacts.plan is not None:
            plan_path_upper = self.artifacts.plan.path.upper()
            found_task_tokens = re.findall(r"TASK[-_](\d+)", plan_path_upper)
            if found_task_tokens:
                for tok in found_task_tokens:
                    if f"TASK-{tok}" != self.task_id:
                        raise ContinuityStateValidationError(
                            f"artifacts.plan path {self.artifacts.plan.path!r} declares task identifier 'TASK-{tok}' "
                            f"which does not match active task_id {self.task_id!r}"
                        )

        # 7. Phase-required artifact presence
        if self.phase == ContinuityPhase.READY_FOR_REVIEW:
            if self.artifacts.result is None:
                raise ContinuityStateValidationError(
                    f"Phase {self.phase.value} requires artifacts.result to be present"
                )
        elif self.phase in (
            ContinuityPhase.CHANGES_REQUIRED,
            ContinuityPhase.FIXING,
            ContinuityPhase.APPROVED,
            ContinuityPhase.MERGED,
        ):
            if self.artifacts.result is None:
                raise ContinuityStateValidationError(
                    f"Phase {self.phase.value} requires artifacts.result to be present"
                )
            if self.artifacts.review is None:
                raise ContinuityStateValidationError(
                    f"Phase {self.phase.value} requires artifacts.review to be present"
                )

        # 8. Brain and Executor records
        if not isinstance(self.brain, BrainState):
            raise ContinuityStateValidationError(f"brain must be a BrainState, got: {type(self.brain).__name__}")
        if not isinstance(self.executor, ExecutorState):
            raise ContinuityStateValidationError(f"executor must be an ExecutorState, got: {type(self.executor).__name__}")

        # 9. Strict constructor/parser 16 KiB size cap enforcement fail-closed
        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized ContinuityState size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable dictionary representation."""
        return {
            "artifacts": self.artifacts.to_dict(),
            "brain": self.brain.to_dict(),
            "executor": self.executor.to_dict(),
            "main": self.main.to_dict(),
            "next_operation": self.next_operation.value,
            "phase": self.phase.value,
            "schema_version": self.schema_version,
            "task_branch": self.task_branch.to_dict(),
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        """
        Produces deterministic canonical JSON string.
        Enforces maximum 16 KiB size cap fail-closed with no truncation.
        """
        data = self.to_dict()
        canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = canonical_str.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized ContinuityState size ({len(utf8_bytes)} bytes) exceeds MAX_SERIALIZED_BYTES limit ({MAX_SERIALIZED_BYTES})"
            )
        return canonical_str

    def fingerprint(self) -> str:
        """Computes deterministic SHA-256 fingerprint from canonical serialized bytes."""
        canonical_str = self.to_canonical_json()
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> ContinuityState:
        """Constructs and strictly validates ContinuityState from dictionary."""
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"ContinuityState root must be a dict, got: {type(data).__name__}")

        allowed_root_keys = {
            "artifacts",
            "brain",
            "executor",
            "main",
            "next_operation",
            "phase",
            "schema_version",
            "task_branch",
            "task_id",
        }
        extra_keys = set(data.keys()) - allowed_root_keys
        if extra_keys:
            raise ContinuityStateValidationError(f"Unknown root fields in ContinuityState: {sorted(extra_keys)}")

        for req in allowed_root_keys:
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in ContinuityState")

        if data["schema_version"] != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version: {data['schema_version']!r} (expected {SCHEMA_VERSION!r})"
            )

        task_id = data["task_id"]
        phase_raw = data["phase"]
        try:
            phase = ContinuityPhase(phase_raw)
        except ValueError as e:
            valid_phases = ", ".join(p.value for p in ContinuityPhase)
            raise ContinuityStateValidationError(
                f"Invalid phase: {phase_raw!r}. Valid values: {valid_phases}"
            ) from e

        next_op_raw = data["next_operation"]
        try:
            next_op = NextOperation(next_op_raw)
        except ValueError as e:
            valid_ops = ", ".join(o.value for o in NextOperation)
            raise ContinuityStateValidationError(
                f"Invalid next_operation: {next_op_raw!r}. Valid values: {valid_ops}"
            ) from e

        main_state = BranchState.from_dict(data["main"], "main")
        task_branch_state = BranchState.from_dict(data["task_branch"], "task_branch")
        artifacts = ContinuityArtifacts.from_dict(data["artifacts"], "artifacts")
        brain = BrainState.from_dict(data["brain"], "brain")
        executor = ExecutorState.from_dict(data["executor"], "executor")

        return cls(
            task_id=task_id,
            phase=phase,
            next_operation=next_op,
            main=main_state,
            task_branch=task_branch_state,
            artifacts=artifacts,
            brain=brain,
            executor=executor,
            schema_version=data["schema_version"],
        )

    @classmethod
    def from_json(cls, text: str | bytes) -> ContinuityState:
        """Parses and strictly validates ContinuityState from JSON string or bytes."""
        if isinstance(text, (bytes, bytearray)):
            raw_bytes = bytes(text)
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON size ({len(raw_bytes)} bytes) exceeds maximum allowable size of {MAX_SERIALIZED_BYTES} bytes"
                )
            try:
                decoded_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ContinuityStateValidationError(f"Invalid UTF-8 encoding in JSON: {e}") from e
        elif isinstance(text, str):
            raw_bytes = text.encode("utf-8")
            if len(raw_bytes) > MAX_SERIALIZED_BYTES:
                raise ContinuityStateValidationError(
                    f"Input JSON size ({len(raw_bytes)} bytes) exceeds maximum allowable size of {MAX_SERIALIZED_BYTES} bytes"
                )
            decoded_text = text
        else:
            raise ContinuityStateValidationError(f"from_json expects str or bytes, got: {type(text).__name__}")

        try:
            data = json.loads(decoded_text)
        except Exception as e:
            raise ContinuityStateValidationError(f"Malformed JSON input: {e}") from e

        return cls.from_dict(data)


@dataclass(frozen=True)
class StateObservation:
    """Immutable caller-provided observation of current repository facts."""
    main_sha: str | None = None
    task_branch_sha: str | None = None
    artifact_blobs: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.main_sha is not None:
            _validate_exact_hex_sha(self.main_sha, "StateObservation.main_sha")
        if self.task_branch_sha is not None:
            _validate_exact_hex_sha(self.task_branch_sha, "StateObservation.task_branch_sha")

        blobs_input = self.artifact_blobs if self.artifact_blobs is not None else {}
        if not isinstance(blobs_input, Mapping):
            raise ContinuityFreshnessError(
                f"artifact_blobs must be a Mapping[str, str], got: {type(blobs_input).__name__}"
            )

        validated_blobs: dict[str, str] = {}
        for path_key, blob_val in blobs_input.items():
            if not isinstance(path_key, str) or not isinstance(blob_val, str):
                raise ContinuityFreshnessError("artifact_blobs keys and values must be strings")
            _validate_exact_hex_sha(blob_val, f"artifact_blobs[{path_key!r}]")
            validated_blobs[path_key] = blob_val

        object.__setattr__(self, "artifact_blobs", MappingProxyType(validated_blobs))


@dataclass(frozen=True)
class FreshnessIssue:
    """Details of a discrepancy or missing fact discovered during freshness evaluation."""
    code: FreshnessIssueCode
    message: str
    target: str | None = None
    expected: str | None = None
    observed: str | None = None


@dataclass(frozen=True)
class FreshnessReport:
    """Evaluation result comparing state against explicit repository observations."""
    status: FreshnessStatus
    issues: tuple[FreshnessIssue, ...]
    state_fingerprint: str

    @property
    def is_fresh(self) -> bool:
        return self.status == FreshnessStatus.FRESH


def check_freshness(
    state: ContinuityState,
    observation: StateObservation,
) -> FreshnessReport:
    """
    Purity-preserving freshness evaluator comparing ContinuityState against explicit StateObservation.
    Performs NO filesystem, network, Git, or Brain/Executor calls.
    """
    if not isinstance(state, ContinuityState):
        raise ContinuityFreshnessError(f"state must be a ContinuityState, got: {type(state).__name__}")
    if not isinstance(observation, StateObservation):
        raise ContinuityFreshnessError(f"observation must be a StateObservation, got: {type(observation).__name__}")

    fingerprint = state.fingerprint()
    mismatches: list[FreshnessIssue] = []
    missing: list[FreshnessIssue] = []

    # 1. Evaluate main branch SHA
    if observation.main_sha is None:
        missing.append(
            FreshnessIssue(
                code=FreshnessIssueCode.MISSING_MAIN_OBSERVATION,
                message="Observed main commit SHA was not provided",
                target=state.main.branch,
                expected=state.main.sha,
            )
        )
    elif observation.main_sha.lower() != state.main.sha.lower():
        mismatches.append(
            FreshnessIssue(
                code=FreshnessIssueCode.MAIN_SHA_MISMATCH,
                message=f"Main commit SHA mismatch: expected {state.main.sha!r}, observed {observation.main_sha!r}",
                target=state.main.branch,
                expected=state.main.sha,
                observed=observation.main_sha,
            )
        )

    # 2. Evaluate task branch SHA (if state records one)
    if state.task_branch.sha is not None:
        if observation.task_branch_sha is None:
            missing.append(
                FreshnessIssue(
                    code=FreshnessIssueCode.MISSING_TASK_OBSERVATION,
                    message=f"Observed task branch commit SHA for {state.task_branch.branch!r} was not provided",
                    target=state.task_branch.branch,
                    expected=state.task_branch.sha,
                )
            )
        elif observation.task_branch_sha.lower() != state.task_branch.sha.lower():
            mismatches.append(
                FreshnessIssue(
                    code=FreshnessIssueCode.TASK_SHA_MISMATCH,
                    message=(
                        f"Task branch commit SHA mismatch for {state.task_branch.branch!r}: "
                        f"expected {state.task_branch.sha!r}, observed {observation.task_branch_sha!r}"
                    ),
                    target=state.task_branch.branch,
                    expected=state.task_branch.sha,
                    observed=observation.task_branch_sha,
                )
            )

    # 3. Evaluate artifacts
    all_artifacts: list[ArtifactRef] = [state.artifacts.task]
    all_artifacts.extend(state.artifacts.contracts)
    if state.artifacts.plan is not None:
        all_artifacts.append(state.artifacts.plan)
    if state.artifacts.result is not None:
        all_artifacts.append(state.artifacts.result)
    if state.artifacts.review is not None:
        all_artifacts.append(state.artifacts.review)

    for art in all_artifacts:
        observed_blob = observation.artifact_blobs.get(art.path)
        if observed_blob is None:
            missing.append(
                FreshnessIssue(
                    code=FreshnessIssueCode.MISSING_ARTIFACT_OBSERVATION,
                    message=f"Observed blob SHA for artifact {art.path!r} was not provided",
                    target=art.path,
                    expected=art.blob_sha,
                )
            )
        elif observed_blob.lower() != art.blob_sha.lower():
            mismatches.append(
                FreshnessIssue(
                    code=FreshnessIssueCode.ARTIFACT_BLOB_MISMATCH,
                    message=(
                        f"Artifact blob SHA mismatch for {art.path!r}: "
                        f"expected {art.blob_sha!r}, observed {observed_blob!r}"
                    ),
                    target=art.path,
                    expected=art.blob_sha,
                    observed=observed_blob,
                )
            )

    # Status precedence: STALE > INCOMPLETE > FRESH
    if mismatches:
        return FreshnessReport(
            status=FreshnessStatus.STALE,
            issues=tuple(mismatches + missing),
            state_fingerprint=fingerprint,
        )
    elif missing:
        return FreshnessReport(
            status=FreshnessStatus.INCOMPLETE,
            issues=tuple(missing),
            state_fingerprint=fingerprint,
        )
    else:
        return FreshnessReport(
            status=FreshnessStatus.FRESH,
            issues=(),
            state_fingerprint=fingerprint,
        )
