"""Bounded M11.3C orchestration for one real paid-API Brain escape.

The module composes explicit caller-supplied Git/runtime evidence only.  It
does not discover a repository, load credentials, construct grants, download
assets, install packages, or provide Executor authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Any, Callable

from .continuity.brain import BrainCapability
from .continuity.dispatch import (
    BrainDispatchCandidate,
    BrainDispatchRequest,
    CandidateReason,
    CapacityClass,
    CapacityState,
    DispatchActorKind,
    DispatchStatus,
    dispatch_brain,
)
from .continuity.state import ArtifactRef, BrainOperation
from .external_brain.budget import ContextBudget
from .external_brain.context import ContextBuilder
from .external_brain.contracts import (
    BrainOperation as ExternalBrainOperation,
    BrainOutputType,
    BrainRole,
    ContextItem,
    ContextKind,
    ModelRequest,
    ModelResponse,
)
from .external_brain.gateway import ModelGateway
from .external_brain.usage import UsageLedger
from .minimax_m3_input_counter import MiniMaxM3LocalProviderInputCounter
from .minimax_m3_proof_lock import (
    MiniMaxM3ProofLock,
    validate_canonical_ai_proof_lock_path,
)
from .paid_api_brain_escape import (
    PaidApiBrainEscapeResult,
    execute_paid_api_brain_escape,
)
from .paid_api_grant import PaidApiGrant
from .paid_api_operational_proof import (
    PaidApiOperationalProofReceipt,
    build_paid_api_operational_proof,
)
from .paid_api_proof_preflight import PaidApiProofPreflightReceipt
from .runtime_dispatch import (
    RuntimeCapacityRecord,
    classify_capacity_freshness,
)
from .runtime_paid_api_grant import AtomicPaidApiGrantStore


REAL_ESCAPE_SCHEMA_VERSION = "1"
MAX_PROPOSAL_BYTES = 512 * 1024
MAX_PROOF_BYTES = 64 * 1024

_TASK_ID_RE = re.compile(r"^TASK-[0-9]{3,}$")
_HEX_40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"(?i)(?:^|[\s('`\"])[a-z]:[\\/][^\s]+")
_UNC_PATH_RE = re.compile(r"(?:^|[\s('`\"])(?:\\\\|//)[A-Za-z0-9._-]+[\\/]")
_POSIX_ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s('`\"<>,[\]():;])/(?!/)[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]*)*"
)
_FORBIDDEN_PROPOSAL_RE = re.compile(
    r"(?i)(?:<\s*/?\s*think\b|reasoning_content|"
    r"authorization\s*[:=]|bearer\s+[A-Za-z0-9]|"
    r"cookie\s*[:=]|api[_ -]?key\s*[:=])"
)

REAL_PROOF_INSTRUCTION = (
    "Produce a concise advisory PLAN for the authorized TASK context. "
    "Describe bounded implementation steps, files, tests, and risks. "
    "Do not output patches or executable commands, request or expose credentials "
    "or hidden reasoning, invoke tools, or claim execution authority."
)


class PaidApiRealEscapeError(ValueError):
    """Raised with a bounded diagnostic when the real escape fails closed."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _require_task_id(value: object) -> str:
    if type(value) is not str or _TASK_ID_RE.fullmatch(value) is None:
        raise PaidApiRealEscapeError("task_id must be canonical TASK-<digits>")
    return value


def _require_hex(value: object, field_name: str, pattern: re.Pattern[str]) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise PaidApiRealEscapeError(f"{field_name} has an invalid digest")
    return value


def _require_exact_type(value: object, expected: type, field_name: str):
    if type(value) is not expected:
        raise PaidApiRealEscapeError(
            f"{field_name} must be an exact {expected.__name__}"
        )
    return value


def _git_blob_sha(content: str) -> str:
    raw = content.encode("utf-8")
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _grant_key(grant_id: str) -> str:
    return hashlib.sha256(grant_id.encode("utf-8")).hexdigest()


def _logical_paths(task_id: str, grant_id: str) -> tuple[str, str]:
    namespace = f"paid_api_proofs/{task_id}/{_grant_key(grant_id)}"
    return f"{namespace}/proposal.md", f"{namespace}/proof.json"


def _require_logical_proof_path(
    value: object,
    *,
    task_id: str,
    grant_id_sha256: str,
    filename: str,
) -> str:
    expected = f"paid_api_proofs/{task_id}/{grant_id_sha256}/{filename}"
    if type(value) is not str or value != expected:
        raise PaidApiRealEscapeError(f"{filename} logical path is not canonical")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise PaidApiRealEscapeError(f"{filename} logical path is not relative")
    return value


def _validate_proposal_content(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise PaidApiRealEscapeError("proposal content must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_PROPOSAL_BYTES:
        raise PaidApiRealEscapeError("proposal content exceeds its bounded size")
    if _FORBIDDEN_PROPOSAL_RE.search(value) is not None:
        raise PaidApiRealEscapeError("proposal content contains forbidden sensitive data")
    if (
        _WINDOWS_ABSOLUTE_PATH_RE.search(value) is not None
        or _UNC_PATH_RE.search(value) is not None
        or _POSIX_ABSOLUTE_PATH_RE.search(value) is not None
    ):
        raise PaidApiRealEscapeError("proposal content contains an absolute path")
    return value


@dataclass(frozen=True, slots=True)
class PaidApiRealEscapeProofReceipt:
    """Bounded proof.json semantics for a completed one-call escape."""

    schema_version: str
    task_id: str
    grant_id_sha256: str
    grant_fingerprint: str
    brain_id: str
    provider_id: str
    model_id: str
    runtime_main_sha: str
    control_commit_sha: str
    proof_lock_path: str
    proof_lock_blob_sha: str
    proof_lock_fingerprint: str
    subscription_brain_id: str
    subscription_capacity_fingerprint: str
    paid_capacity_fingerprint: str
    preflight_fingerprint: str
    operational_proof_fingerprint: str
    proposal_logical_path: str
    proposal_sha256: str
    proof_logical_path: str
    grant_consumed: bool
    provider_call_count: int
    retry_count: int
    executor_authority_created: bool

    def __post_init__(self) -> None:
        if self.schema_version != REAL_ESCAPE_SCHEMA_VERSION:
            raise PaidApiRealEscapeError("unsupported real escape proof schema")
        task_id = _require_task_id(self.task_id)
        grant_key = _require_hex(
            self.grant_id_sha256, "grant_id_sha256", _HEX_64_RE
        )
        for field_name in (
            "grant_fingerprint",
            "proof_lock_fingerprint",
            "subscription_capacity_fingerprint",
            "paid_capacity_fingerprint",
            "preflight_fingerprint",
            "operational_proof_fingerprint",
            "proposal_sha256",
        ):
            _require_hex(getattr(self, field_name), field_name, _HEX_64_RE)
        for field_name in (
            "runtime_main_sha",
            "control_commit_sha",
            "proof_lock_blob_sha",
        ):
            _require_hex(getattr(self, field_name), field_name, _HEX_40_RE)
        try:
            validate_canonical_ai_proof_lock_path(self.proof_lock_path)
        except Exception as exc:
            raise PaidApiRealEscapeError("proof_lock_path is not canonical") from exc
        for field_name in (
            "brain_id",
            "provider_id",
            "model_id",
            "subscription_brain_id",
        ):
            value = getattr(self, field_name)
            if type(value) is not str or not value or value != value.strip():
                raise PaidApiRealEscapeError(f"{field_name} is not canonical")
        _require_logical_proof_path(
            self.proposal_logical_path,
            task_id=task_id,
            grant_id_sha256=grant_key,
            filename="proposal.md",
        )
        _require_logical_proof_path(
            self.proof_logical_path,
            task_id=task_id,
            grant_id_sha256=grant_key,
            filename="proof.json",
        )
        if self.grant_consumed is not True:
            raise PaidApiRealEscapeError("grant_consumed must be exactly true")
        if type(self.provider_call_count) is not int or self.provider_call_count != 1:
            raise PaidApiRealEscapeError("provider_call_count must be exactly one")
        if type(self.retry_count) is not int or self.retry_count != 0:
            raise PaidApiRealEscapeError("retry_count must be exactly zero")
        if self.executor_authority_created is not False:
            raise PaidApiRealEscapeError(
                "executor_authority_created must be exactly false"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "brain_id": self.brain_id,
            "control_commit_sha": self.control_commit_sha,
            "executor_authority_created": self.executor_authority_created,
            "grant_consumed": self.grant_consumed,
            "grant_fingerprint": self.grant_fingerprint,
            "grant_id_sha256": self.grant_id_sha256,
            "model_id": self.model_id,
            "operational_proof_fingerprint": self.operational_proof_fingerprint,
            "paid_capacity_fingerprint": self.paid_capacity_fingerprint,
            "preflight_fingerprint": self.preflight_fingerprint,
            "proof_lock_blob_sha": self.proof_lock_blob_sha,
            "proof_lock_fingerprint": self.proof_lock_fingerprint,
            "proof_lock_path": self.proof_lock_path,
            "proof_logical_path": self.proof_logical_path,
            "proposal_logical_path": self.proposal_logical_path,
            "proposal_sha256": self.proposal_sha256,
            "provider_call_count": self.provider_call_count,
            "provider_id": self.provider_id,
            "retry_count": self.retry_count,
            "runtime_main_sha": self.runtime_main_sha,
            "schema_version": self.schema_version,
            "subscription_brain_id": self.subscription_brain_id,
            "subscription_capacity_fingerprint": self.subscription_capacity_fingerprint,
            "task_id": self.task_id,
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    def fingerprint(self) -> str:
        return hashlib.sha256(
            self.to_canonical_json().encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class PaidApiRealEscapeResult:
    """In-memory result returned after proof artifacts are durably persisted."""

    escape_result: PaidApiBrainEscapeResult
    operational_proof: PaidApiOperationalProofReceipt
    proof_receipt: PaidApiRealEscapeProofReceipt

    def __post_init__(self) -> None:
        _require_exact_type(
            self.escape_result, PaidApiBrainEscapeResult, "escape_result"
        )
        _require_exact_type(
            self.operational_proof,
            PaidApiOperationalProofReceipt,
            "operational_proof",
        )
        _require_exact_type(
            self.proof_receipt,
            PaidApiRealEscapeProofReceipt,
            "proof_receipt",
        )


class _DeferredSingleCallProvider:
    """Expose identity early but construct the real provider only at invocation."""

    def __init__(
        self,
        *,
        provider_id: str,
        model_name: str,
        provider_factory: Callable[[], object],
    ) -> None:
        if type(provider_id) is not str or not provider_id:
            raise PaidApiRealEscapeError("deferred provider_id is invalid")
        if type(model_name) is not str or not model_name:
            raise PaidApiRealEscapeError("deferred model_name is invalid")
        if not callable(provider_factory):
            raise PaidApiRealEscapeError("provider_factory must be callable")
        self.provider_id = provider_id
        self.model_name = model_name
        self._provider_factory = provider_factory
        self.factory_call_count = 0
        self.invoke_call_count = 0

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        if self.invoke_call_count != 0 or self.factory_call_count != 0:
            raise PaidApiRealEscapeError("deferred provider cannot be retried")
        self.invoke_call_count += 1
        self.factory_call_count += 1
        provider = self._provider_factory()
        if getattr(provider, "provider_id", None) != self.provider_id:
            raise PaidApiRealEscapeError("constructed provider_id changed after gates")
        if getattr(provider, "model_name", None) != self.model_name:
            raise PaidApiRealEscapeError("constructed model_name changed after gates")
        invoke = getattr(provider, "invoke", None)
        if not callable(invoke):
            raise PaidApiRealEscapeError("constructed provider has no invoke surface")
        return await invoke(request)


def _validate_preflight(
    *,
    task_id: str,
    runtime_main_sha: str,
    control_commit_sha: str,
    proof_lock_path: str,
    proof_lock_blob_sha: str,
    proof_lock: MiniMaxM3ProofLock,
    preflight_receipt: PaidApiProofPreflightReceipt,
    grant: PaidApiGrant,
    counter: MiniMaxM3LocalProviderInputCounter,
) -> None:
    expected_ledger = f"paid_api_usage/{task_id}/{_grant_key(grant.grant_id)}.jsonl"
    bindings = (
        (preflight_receipt.task_id, task_id, "preflight task"),
        (preflight_receipt.grant_id, grant.grant_id, "preflight grant"),
        (
            preflight_receipt.grant_fingerprint,
            grant.fingerprint(),
            "preflight grant fingerprint",
        ),
        (preflight_receipt.workspace_id, grant.workspace_id, "preflight workspace"),
        (preflight_receipt.brain_id, grant.brain_id, "preflight Brain"),
        (preflight_receipt.provider_id, proof_lock.provider_id, "preflight provider"),
        (preflight_receipt.model_id, proof_lock.model_id, "preflight model"),
        (preflight_receipt.runtime_main_sha, runtime_main_sha, "preflight main"),
        (
            preflight_receipt.control_commit_sha,
            control_commit_sha,
            "preflight control commit",
        ),
        (
            preflight_receipt.authorized_artifact_path,
            grant.authorized_artifact_path,
            "preflight artifact path",
        ),
        (
            preflight_receipt.authorized_artifact_blob_sha,
            grant.authorized_artifact_blob_sha,
            "preflight artifact blob",
        ),
        (preflight_receipt.proof_lock_path, proof_lock_path, "preflight proof path"),
        (
            preflight_receipt.proof_lock_blob_sha,
            proof_lock_blob_sha,
            "preflight proof blob",
        ),
        (
            preflight_receipt.proof_lock_fingerprint,
            proof_lock.fingerprint(),
            "preflight proof fingerprint",
        ),
        (preflight_receipt.counter_id, counter.counter_id, "preflight counter"),
        (preflight_receipt.ledger_logical_path, expected_ledger, "preflight ledger"),
    )
    for actual, expected, label in bindings:
        if actual != expected:
            raise PaidApiRealEscapeError(f"{label} binding mismatch")


def _validate_capacity_record(
    *,
    record: RuntimeCapacityRecord,
    actor_id: str,
    expected_fingerprint: str,
    now_epoch_seconds: int,
    allowed_states: frozenset[CapacityState],
    label: str,
) -> RuntimeCapacityRecord:
    _require_exact_type(record, RuntimeCapacityRecord, f"{label}_capacity_record")
    fingerprint = _require_hex(
        expected_fingerprint, f"{label}_capacity_fingerprint", _HEX_64_RE
    )
    if record.actor_kind is not DispatchActorKind.BRAIN:
        raise PaidApiRealEscapeError(f"{label} capacity actor_kind must be BRAIN")
    if record.actor_id != actor_id:
        raise PaidApiRealEscapeError(f"{label} capacity actor_id mismatch")
    if (
        record.record_fingerprint != fingerprint
        or record.fingerprint() != fingerprint
    ):
        raise PaidApiRealEscapeError(f"{label} capacity fingerprint mismatch")
    try:
        freshness = classify_capacity_freshness(record, now_epoch_seconds)
    except Exception as exc:
        raise PaidApiRealEscapeError(
            f"{label} capacity timestamp is invalid"
        ) from exc
    if freshness != "FRESH":
        raise PaidApiRealEscapeError(f"{label} capacity evidence is not FRESH")
    if record.capacity_state not in allowed_states:
        raise PaidApiRealEscapeError(f"{label} capacity state is forbidden")
    return record


def _build_base_dispatch(
    *,
    grant: PaidApiGrant,
    subscription_capacity: RuntimeCapacityRecord,
    paid_capacity: RuntimeCapacityRecord,
    required_context_bytes: int,
) -> BrainDispatchRequest:
    operation = BrainOperation.PLAN
    subscription = BrainDispatchCandidate(
        brain_id=subscription_capacity.actor_id,
        capability=BrainCapability(
            brain_id=subscription_capacity.actor_id,
            supported_operations=(operation,),
        ),
        capacity_state=subscription_capacity.capacity_state,
        capacity_class=CapacityClass.SUBSCRIPTION,
        preference_rank=0,
    )
    paid = BrainDispatchCandidate(
        brain_id=paid_capacity.actor_id,
        capability=BrainCapability(
            brain_id=paid_capacity.actor_id,
            supported_operations=(operation,),
        ),
        capacity_state=paid_capacity.capacity_state,
        capacity_class=CapacityClass.PAID_API,
        preference_rank=1,
    )
    request = BrainDispatchRequest(
        operation=operation,
        candidates=(subscription, paid),
        required_context_bytes=required_context_bytes,
        allow_paid_api=False,
    )
    result = dispatch_brain(request)
    if result.status is not DispatchStatus.WAIT or result.selected_actor_id is not None:
        raise PaidApiRealEscapeError(
            "base dispatch must not select any Brain before grant enablement"
        )
    evaluations = {item.actor_id: item for item in result.evaluations}
    subscription_evaluation = evaluations.get(subscription.brain_id)
    paid_evaluation = evaluations.get(paid.brain_id)
    if (
        subscription_evaluation is None
        or subscription_evaluation.runnable is not False
        or subscription_evaluation.compatible is not True
    ):
        raise PaidApiRealEscapeError(
            "subscription Brain must be compatible but not runnable"
        )
    if (
        paid_evaluation is None
        or paid_evaluation.runnable is not False
        or paid_evaluation.compatible is not False
        or CandidateReason.PAID_API_NOT_ALLOWED not in paid_evaluation.reasons
    ):
        raise PaidApiRealEscapeError(
            "base dispatch did not preserve paid-api default deny"
        )
    if paid.brain_id != grant.brain_id:
        raise PaidApiRealEscapeError("paid dispatch candidate does not match grant")
    return request


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(str(directory), flags)
    except OSError:
        return
    try:
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        os.close(descriptor)


def _write_durable_new_file(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _is_link_or_junction(path: Path) -> bool:
    try:
        if path.is_symlink() or os.path.islink(str(path)):
            return True
        st = path.stat(follow_symlinks=False)
        if stat.S_ISLNK(st.st_mode):
            return True
        reparse_attr = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        file_attrs = getattr(st, "st_file_attributes", 0)
        if file_attrs & reparse_attr:
            return True
    except OSError:
        pass
    return False


def persist_paid_api_real_escape_artifacts(
    *,
    runtime_root: str | os.PathLike[str],
    proposal_content: str,
    proof_receipt: PaidApiRealEscapeProofReceipt,
) -> None:
    """Atomically publish proposal.md and proof.json under external runtime."""

    _require_exact_type(
        proof_receipt, PaidApiRealEscapeProofReceipt, "proof_receipt"
    )
    proposal = _validate_proposal_content(proposal_content)
    if hashlib.sha256(proposal.encode("utf-8")).hexdigest() != proof_receipt.proposal_sha256:
        raise PaidApiRealEscapeError("proposal digest does not match proof receipt")
    try:
        supplied_root = Path(runtime_root)
        if _is_link_or_junction(supplied_root):
            raise PaidApiRealEscapeError("external runtime root cannot be a symlink or junction")
        supplied_root.mkdir(parents=True, exist_ok=True)
        root = supplied_root.resolve(strict=True)
    except PaidApiRealEscapeError:
        raise
    except (OSError, TypeError) as exc:
        raise PaidApiRealEscapeError("external runtime root is unavailable") from exc

    proofs_root = root / "paid_api_proofs"
    if _is_link_or_junction(proofs_root):
        raise PaidApiRealEscapeError("proofs root cannot be a symlink or junction")
    try:
        proofs_root.mkdir(exist_ok=True)
        resolved_proofs = proofs_root.resolve(strict=True)
        if resolved_proofs.parent != root:
            raise PaidApiRealEscapeError("proofs root escapes the external runtime directory")
    except PaidApiRealEscapeError:
        raise
    except OSError as exc:
        raise PaidApiRealEscapeError("proofs root is unavailable") from exc

    task_root = proofs_root / proof_receipt.task_id
    if _is_link_or_junction(task_root):
        raise PaidApiRealEscapeError("task directory cannot be a symlink or junction")
    try:
        task_root.mkdir(exist_ok=True)
        resolved_task = task_root.resolve(strict=True)
        if resolved_task.parent != resolved_proofs:
            raise PaidApiRealEscapeError("task directory escapes the external runtime directory")
    except PaidApiRealEscapeError:
        raise
    except OSError as exc:
        raise PaidApiRealEscapeError("task directory is unavailable") from exc

    final_root = task_root / proof_receipt.grant_id_sha256
    if _is_link_or_junction(final_root):
        raise PaidApiRealEscapeError("proof namespace cannot be a symlink or junction")
    if final_root.exists():
        raise PaidApiRealEscapeError("proof namespace already exists")

    staging_root = task_root / (
        f".{proof_receipt.grant_id_sha256}.tmp-{secrets.token_hex(8)}"
    )
    proof_payload = (proof_receipt.to_canonical_json() + "\n").encode("utf-8")
    proposal_payload = proposal.encode("utf-8")
    if len(proof_payload) > MAX_PROOF_BYTES:
        raise PaidApiRealEscapeError("proof receipt exceeds its bounded size")

    try:
        staging_root.mkdir()
        resolved_staging = staging_root.resolve(strict=True)
        if resolved_staging.parent != resolved_task:
            raise PaidApiRealEscapeError("staging directory escapes the external runtime directory")

        _write_durable_new_file(staging_root / "proposal.md", proposal_payload)
        _write_durable_new_file(staging_root / "proof.json", proof_payload)
        _fsync_directory(staging_root)

        os.replace(staging_root, final_root)
        _fsync_directory(task_root)

        resolved_final = final_root.resolve(strict=True)
        if resolved_final.parent != resolved_task:
            raise PaidApiRealEscapeError("final proof directory escapes the external runtime directory")

        if (final_root / "proposal.md").read_bytes() != proposal_payload:
            raise PaidApiRealEscapeError("proposal durable read-back mismatch")
        if (final_root / "proof.json").read_bytes() != proof_payload:
            raise PaidApiRealEscapeError("proof durable read-back mismatch")
    except PaidApiRealEscapeError:
        raise
    except Exception as exc:
        raise PaidApiRealEscapeError("atomic external proof persistence failed") from exc
    finally:
        if staging_root.exists():
            for filename in ("proposal.md", "proof.json"):
                try:
                    (staging_root / filename).unlink(missing_ok=True)
                except OSError:
                    pass
            try:
                staging_root.rmdir()
            except OSError:
                pass


async def execute_paid_api_real_escape(
    *,
    task_id: str,
    runtime_main_sha: str,
    control_commit_sha: str,
    proof_lock_path: str,
    proof_lock_blob_sha: str,
    proof_lock: MiniMaxM3ProofLock,
    preflight_receipt: PaidApiProofPreflightReceipt,
    grant: PaidApiGrant,
    grant_store: AtomicPaidApiGrantStore,
    authorized_artifact: ArtifactRef,
    authorized_artifact_content: str,
    provider_input_counter: MiniMaxM3LocalProviderInputCounter,
    subscription_brain_id: str,
    subscription_capacity_record: RuntimeCapacityRecord,
    paid_capacity_record: RuntimeCapacityRecord,
    subscription_capacity_fingerprint: str,
    paid_capacity_fingerprint: str,
    now_epoch_seconds: int,
    runtime_root: str | os.PathLike[str],
    provider_factory: Callable[[], object],
    ledger: UsageLedger,
    gateway_factory: Callable[[object, UsageLedger], ModelGateway] | None = None,
) -> PaidApiRealEscapeResult:
    """Validate R0-R7 evidence, consume/call once, then persist R9 proof.

    R0/R1 Git operations remain in Bridge; this function verifies their exact
    caller-supplied immutable evidence and performs no repository discovery.
    """

    task_id = _require_task_id(task_id)
    runtime_main_sha = _require_hex(runtime_main_sha, "runtime_main_sha", _HEX_40_RE)
    control_commit_sha = _require_hex(
        control_commit_sha, "control_commit_sha", _HEX_40_RE
    )
    proof_lock_blob_sha = _require_hex(
        proof_lock_blob_sha, "proof_lock_blob_sha", _HEX_40_RE
    )
    if type(now_epoch_seconds) is not int or now_epoch_seconds < 0:
        raise PaidApiRealEscapeError("now_epoch_seconds must be non-negative")
    if (
        type(subscription_brain_id) is not str
        or not subscription_brain_id
        or subscription_brain_id != subscription_brain_id.strip()
    ):
        raise PaidApiRealEscapeError("subscription_brain_id is not canonical")
    _require_exact_type(proof_lock, MiniMaxM3ProofLock, "proof_lock")
    _require_exact_type(
        preflight_receipt, PaidApiProofPreflightReceipt, "preflight_receipt"
    )
    _require_exact_type(grant, PaidApiGrant, "grant")
    _require_exact_type(grant_store, AtomicPaidApiGrantStore, "grant_store")
    _require_exact_type(authorized_artifact, ArtifactRef, "authorized_artifact")
    _require_exact_type(
        provider_input_counter,
        MiniMaxM3LocalProviderInputCounter,
        "provider_input_counter",
    )
    try:
        proof_lock_path = validate_canonical_ai_proof_lock_path(proof_lock_path)
    except Exception as exc:
        raise PaidApiRealEscapeError("proof_lock_path is not canonical") from exc

    # R2: exact ACTIVE, PLAN-only Human grant before any paid provider object.
    if grant.task_id != task_id:
        raise PaidApiRealEscapeError("grant task binding mismatch")
    if grant.actor_kind is not DispatchActorKind.BRAIN:
        raise PaidApiRealEscapeError("grant actor_kind must be BRAIN")
    if grant.brain_operation is not BrainOperation.PLAN:
        raise PaidApiRealEscapeError("real proof grant must be PLAN-only")
    if grant.max_calls != 1:
        raise PaidApiRealEscapeError("real proof grant max_calls must be one")
    if grant.workspace_id != grant_store.workspace_id:
        raise PaidApiRealEscapeError("grant workspace binding mismatch")
    if grant.provider_id != proof_lock.provider_id or grant.model_id != proof_lock.model_id:
        raise PaidApiRealEscapeError("grant provider/model proof-lock mismatch")
    try:
        grant_store.require_active(grant, now_epoch_seconds=now_epoch_seconds)
    except Exception as exc:
        raise PaidApiRealEscapeError("GRANT_NOT_ACTIVE / NO_PROVIDER_CALL") from exc

    # R3: exact authorized TASK bytes from the caller-supplied control snapshot.
    if authorized_artifact.ref != control_commit_sha:
        raise PaidApiRealEscapeError("authorized artifact control commit mismatch")
    if (
        authorized_artifact.path != grant.authorized_artifact_path
        or authorized_artifact.blob_sha != grant.authorized_artifact_blob_sha
    ):
        raise PaidApiRealEscapeError("authorized artifact grant binding mismatch")
    if authorized_artifact.path != f".ai/tasks/{task_id}.md":
        raise PaidApiRealEscapeError("authorized artifact must be the exact TASK artifact")
    if type(authorized_artifact_content) is not str:
        raise PaidApiRealEscapeError("authorized artifact content must be strict UTF-8 text")
    if _git_blob_sha(authorized_artifact_content) != authorized_artifact.blob_sha:
        raise PaidApiRealEscapeError("authorized artifact content changed")

    # R4: one proof-locked object is both ContextBuilder and full-input counter.
    if provider_input_counter.proof_lock != proof_lock:
        raise PaidApiRealEscapeError("counter proof-lock binding mismatch")
    if (
        provider_input_counter.provider_id != proof_lock.provider_id
        or provider_input_counter.model_id != proof_lock.model_id
        or provider_input_counter.is_exact is not True
    ):
        raise PaidApiRealEscapeError("counter provider/model/exactness mismatch")
    _validate_preflight(
        task_id=task_id,
        runtime_main_sha=runtime_main_sha,
        control_commit_sha=control_commit_sha,
        proof_lock_path=proof_lock_path,
        proof_lock_blob_sha=proof_lock_blob_sha,
        proof_lock=proof_lock,
        preflight_receipt=preflight_receipt,
        grant=grant,
        counter=provider_input_counter,
    )
    task_context = ContextItem(
        kind=ContextKind.TASK,
        content=authorized_artifact_content,
        path=authorized_artifact.path,
        priority=100,
        content_sha256=hashlib.sha256(
            authorized_artifact_content.encode("utf-8")
        ).hexdigest(),
    )
    context_build = ContextBuilder(provider_input_counter).build(
        (task_context,),
        ContextBudget(max_context_tokens=grant.max_input_tokens),
    )
    if (
        context_build.token_count_is_exact is not True
        or context_build.counter_id != provider_input_counter.counter_id
        or context_build.selected != (task_context,)
    ):
        raise PaidApiRealEscapeError("exact context construction failed")
    request_id = f"paid-proof-{task_id.lower()}-{_grant_key(grant.grant_id)[:16]}"
    model_request = ModelRequest(
        schema_version="1",
        request_id=request_id,
        task_id=task_id,
        role=BrainRole.ARCHITECT,
        operation=ExternalBrainOperation.PLAN,
        instruction=REAL_PROOF_INSTRUCTION,
        context=context_build.selected,
        output_format=BrainOutputType.PLAN,
        provider=grant.provider_id,
        model=grant.model_id,
        max_input_tokens=grant.max_input_tokens,
        max_output_tokens=grant.max_output_tokens,
    )

    # R5: exactly two fresh BRAIN capacity records with caller-bound digests.
    if subscription_brain_id == grant.brain_id:
        raise PaidApiRealEscapeError("subscription and paid Brain IDs must differ")
    subscription = _validate_capacity_record(
        record=subscription_capacity_record,
        actor_id=subscription_brain_id,
        expected_fingerprint=subscription_capacity_fingerprint,
        now_epoch_seconds=now_epoch_seconds,
        allowed_states=frozenset(
            {CapacityState.QUOTA_EXHAUSTED, CapacityState.UNAVAILABLE}
        ),
        label="subscription",
    )
    paid = _validate_capacity_record(
        record=paid_capacity_record,
        actor_id=grant.brain_id,
        expected_fingerprint=paid_capacity_fingerprint,
        now_epoch_seconds=now_epoch_seconds,
        allowed_states=frozenset({CapacityState.AVAILABLE}),
        label="paid",
    )

    # R6: M10 default deny first; grant-aware enablement remains in M11.2C.
    base_dispatch_request = _build_base_dispatch(
        grant=grant,
        subscription_capacity=subscription,
        paid_capacity=paid,
        required_context_bytes=len(authorized_artifact_content.encode("utf-8")),
    )

    # The wrapper is identity-only.  The injected real/fake provider factory is
    # called from gateway.invoke, after M11.2C's exact full-input R7 gate and
    # durable consume transition.
    deferred_provider = _DeferredSingleCallProvider(
        provider_id=grant.provider_id,
        model_name=grant.model_id,
        provider_factory=provider_factory,
    )
    if gateway_factory is None:
        gateway = ModelGateway(provider=deferred_provider, ledger=ledger)
    else:
        if not callable(gateway_factory):
            raise PaidApiRealEscapeError("gateway_factory must be callable")
        gateway = gateway_factory(deferred_provider, ledger)
    if type(gateway) is not ModelGateway or gateway.provider is not deferred_provider:
        raise PaidApiRealEscapeError(
            "gateway_factory must preserve the exact deferred provider"
        )
    if (
        deferred_provider.factory_call_count != 0
        or deferred_provider.invoke_call_count != 0
    ):
        raise PaidApiRealEscapeError(
            "gateway_factory started provider work before full-input validation"
        )
    try:
        escape_result = await execute_paid_api_brain_escape(
            base_dispatch_request=base_dispatch_request,
            grant=grant,
            grant_store=grant_store,
            authorized_artifact=authorized_artifact,
            model_request=model_request,
            context_build=context_build,
            provider_input_counter=provider_input_counter,
            gateway=gateway,
            now_epoch_seconds=now_epoch_seconds,
        )
    except Exception as exc:
        try:
            consumed = grant_store.load_consumed(task_id, grant.grant_id)
        except Exception:
            consumed = None
        message = (
            "PROVIDER_EXECUTION_FAILED_AFTER_CONSUME"
            if consumed is not None
            else "PRE_CALL_VALIDATION_FAILED / NO_PROVIDER_CALL"
        )
        raise PaidApiRealEscapeError(message) from exc

    if (
        escape_result.paid_candidate_selected is not True
        or escape_result.grant_consumed is not True
        or deferred_provider.factory_call_count != 1
        or deferred_provider.invoke_call_count != 1
    ):
        raise PaidApiRealEscapeError("one-call paid dispatch proof did not complete")

    # R9: build only from the original pre-call evidence held by escape_result.
    try:
        operational_proof = build_paid_api_operational_proof(
            escape_result=escape_result,
            grant=grant,
            grant_store=grant_store,
            model_request=model_request,
        )
    except Exception as exc:
        raise PaidApiRealEscapeError(
            "OPERATIONAL_PROOF_FAILED_AFTER_CONSUME"
        ) from exc
    gateway_result = escape_result.gateway_result
    if gateway_result is None:
        raise PaidApiRealEscapeError("successful gateway evidence is missing")
    proposal_content = _validate_proposal_content(gateway_result.response.content)
    proposal_sha = hashlib.sha256(proposal_content.encode("utf-8")).hexdigest()
    if proposal_sha != operational_proof.response_content_sha256:
        raise PaidApiRealEscapeError("proposal content correlation failed")
    proposal_logical_path, proof_logical_path = _logical_paths(
        task_id, grant.grant_id
    )
    proof_receipt = PaidApiRealEscapeProofReceipt(
        schema_version=REAL_ESCAPE_SCHEMA_VERSION,
        task_id=task_id,
        grant_id_sha256=_grant_key(grant.grant_id),
        grant_fingerprint=grant.fingerprint(),
        brain_id=grant.brain_id,
        provider_id=grant.provider_id,
        model_id=grant.model_id,
        runtime_main_sha=runtime_main_sha,
        control_commit_sha=control_commit_sha,
        proof_lock_path=proof_lock_path,
        proof_lock_blob_sha=proof_lock_blob_sha,
        proof_lock_fingerprint=proof_lock.fingerprint(),
        subscription_brain_id=subscription.actor_id,
        subscription_capacity_fingerprint=subscription_capacity_fingerprint,
        paid_capacity_fingerprint=paid_capacity_fingerprint,
        preflight_fingerprint=preflight_receipt.fingerprint(),
        operational_proof_fingerprint=operational_proof.fingerprint(),
        proposal_logical_path=proposal_logical_path,
        proposal_sha256=proposal_sha,
        proof_logical_path=proof_logical_path,
        grant_consumed=True,
        provider_call_count=1,
        retry_count=0,
        executor_authority_created=False,
    )
    try:
        persist_paid_api_real_escape_artifacts(
            runtime_root=runtime_root,
            proposal_content=proposal_content,
            proof_receipt=proof_receipt,
        )
    except Exception as exc:
        raise PaidApiRealEscapeError("PROOF_WRITE_FAILED_AFTER_CONSUME") from exc
    return PaidApiRealEscapeResult(
        escape_result=escape_result,
        operational_proof=operational_proof,
        proof_receipt=proof_receipt,
    )


__all__ = [
    "MAX_PROOF_BYTES",
    "MAX_PROPOSAL_BYTES",
    "PaidApiRealEscapeError",
    "PaidApiRealEscapeProofReceipt",
    "PaidApiRealEscapeResult",
    "REAL_ESCAPE_SCHEMA_VERSION",
    "REAL_PROOF_INSTRUCTION",
    "execute_paid_api_real_escape",
    "persist_paid_api_real_escape_artifacts",
]
