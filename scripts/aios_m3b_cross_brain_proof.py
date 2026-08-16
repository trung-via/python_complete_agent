"""
Deterministic M3B Real Cross-Chat Brain Failover Proof Runner (TASK-027 / ADR-016 / ADR-017).
Provides staged commands (prepare-source, validate-source, verify-replacement, audit-bundle),
stale downstream artifact purging, immutable Stage-2 proof binding, controlled source invariant,
strict attestation schema and token grammar, deterministic newline normalization, and test isolation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from src.aios_bridge.continuity.brain import (
    BrainCapability,
    BrainOperation,
    BrainOutputType,
    BrainRequest,
    BrainResult,
    BrainResultStatus,
    ContextRef,
    OutputContract,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.failover import (
    BrainFailoverProof,
    build_replacement_brain_request,
    validate_brain_failover_eligibility,
)
from src.aios_bridge.continuity.state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    ArtifactRef,
    BranchState,
    BrainState,
    ContinuityArtifacts,
    ContinuityPhase,
    ContinuityState,
    ExecutorState,
    NextOperation,
)

FORBIDDEN_ATTESTATION_KEYS = {
    "transcript",
    "transcripts",
    "raw_prompt",
    "raw_prompts",
    "raw_response",
    "raw_responses",
    "cookie",
    "cookies",
    "token",
    "tokens",
    "session",
    "sessions",
    "auth",
    "cot",
    "reasoning",
    "history",
}

_TOKEN_USAGE_PATTERN = re.compile(r"^(UNKNOWN|REPORTED\([a-zA-Z0-9_\-:, .]+\))$")

DOWNSTREAM_PROOF_ARTIFACTS = [
    "TASK-027-M3B-SOURCE-RESULT.json",
    "TASK-027-M3B-REPLACEMENT-REQUEST.json",
    "TASK-027-M3B-REPLACEMENT-CAPABILITY.json",
    "TASK-027-M3B-FAILOVER-PROOF.json",
    "TASK-027-M3B-REPLACEMENT-RESULT.json",
    "TASK-027-M3B-LIVE-ATTESTATION.json",
]


def normalize_line_endings(text: str | bytes) -> bytes:
    """
    Deterministic newline-only normalization (ADR-016 / TASK-027 C7 / R2-1):
    Converts CRLF and CR line endings to LF.
    Ensures a single trailing LF at the end of the artifact.
    Does NOT strip or alter leading/trailing spaces, tabs, or empty lines.
    """
    if isinstance(text, (bytes, bytearray)):
        decoded = bytes(text).decode("utf-8")
    else:
        decoded = str(text)

    # Normalize CRLF and CR to LF
    normalized = decoded.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized.encode("utf-8")


def validate_m3b_controlled_source_result(source_result: BrainResult) -> None:
    """
    Enforces the TASK-027 specific controlled source mode (TASK-027 C6 / R3-1):
    status == INCOMPLETE
    error_code == 'M3B-CONTROLLED-HANDOFF'
    artifact_ref is None
    evidence_ref is None
    """
    if source_result.status != BrainResultStatus.INCOMPLETE:
        raise ContinuityStateValidationError(
            f"TASK-027 requires source result status INCOMPLETE, got: {source_result.status.value}"
        )
    if source_result.error_code != "M3B-CONTROLLED-HANDOFF":
        raise ContinuityStateValidationError(
            f"TASK-027 requires error_code 'M3B-CONTROLLED-HANDOFF', got: {source_result.error_code!r}"
        )
    if source_result.artifact_ref is not None:
        raise ContinuityStateValidationError("TASK-027 controlled source result must not contain artifact_ref")
    if source_result.evidence_ref is not None:
        raise ContinuityStateValidationError("TASK-027 controlled source result must not contain evidence_ref")


@dataclass(frozen=True)
class M3BLiveAttestation:
    """Strict, bounded human attestation for non-mechanically observable live proof facts."""
    schema_version: str
    distinct_real_brain_surfaces: bool
    fresh_source_session: bool
    fresh_replacement_session: bool
    transcript_transferred: bool
    chat_ui_automation: bool
    interaction_transport: str
    human_bounded_transfer_bytes: int
    source_brain_id: str
    replacement_brain_id: str
    source_brain_token_usage: str
    replacement_brain_token_usage: str
    paid_external_api_calls: int

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContinuityStateValidationError(
                f"Unsupported schema_version in M3BLiveAttestation: {self.schema_version!r} (expected {SCHEMA_VERSION!r})"
            )
        if not isinstance(self.distinct_real_brain_surfaces, bool) or self.distinct_real_brain_surfaces is not True:
            raise ContinuityStateValidationError("distinct_real_brain_surfaces must be True for acceptance")
        if not isinstance(self.fresh_source_session, bool) or self.fresh_source_session is not True:
            raise ContinuityStateValidationError("fresh_source_session must be True for acceptance")
        if not isinstance(self.fresh_replacement_session, bool) or self.fresh_replacement_session is not True:
            raise ContinuityStateValidationError("fresh_replacement_session must be True for acceptance")
        if not isinstance(self.transcript_transferred, bool) or self.transcript_transferred is not False:
            raise ContinuityStateValidationError("transcript_transferred must be False for acceptance")
        if not isinstance(self.chat_ui_automation, bool) or self.chat_ui_automation is not False:
            raise ContinuityStateValidationError("chat_ui_automation must be False for acceptance")
        if self.interaction_transport != "HUMAN_BOUNDED_ARTIFACT_TRANSFER":
            raise ContinuityStateValidationError(
                f"interaction_transport must be 'HUMAN_BOUNDED_ARTIFACT_TRANSFER', got: {self.interaction_transport!r}"
            )
        if (
            isinstance(self.human_bounded_transfer_bytes, bool)
            or not isinstance(self.human_bounded_transfer_bytes, int)
            or self.human_bounded_transfer_bytes <= 0
            or self.human_bounded_transfer_bytes > MAX_SERIALIZED_BYTES
        ):
            raise ContinuityStateValidationError(
                f"human_bounded_transfer_bytes must be an integer between 1 and {MAX_SERIALIZED_BYTES}, got: {self.human_bounded_transfer_bytes!r}"
            )
        if not self.source_brain_id or not isinstance(self.source_brain_id, str):
            raise ContinuityStateValidationError("source_brain_id must be a non-empty string")
        if not self.replacement_brain_id or not isinstance(self.replacement_brain_id, str):
            raise ContinuityStateValidationError("replacement_brain_id must be a non-empty string")
        if self.source_brain_id == self.replacement_brain_id:
            raise ContinuityStateValidationError("source_brain_id and replacement_brain_id must differ")
        if (
            not self.source_brain_token_usage
            or not isinstance(self.source_brain_token_usage, str)
            or len(self.source_brain_token_usage) > 128
            or not _TOKEN_USAGE_PATTERN.match(self.source_brain_token_usage)
        ):
            raise ContinuityStateValidationError(
                f"source_brain_token_usage must match safe grammar 'UNKNOWN' or 'REPORTED(...)', got: {self.source_brain_token_usage!r}"
            )
        if (
            not self.replacement_brain_token_usage
            or not isinstance(self.replacement_brain_token_usage, str)
            or len(self.replacement_brain_token_usage) > 128
            or not _TOKEN_USAGE_PATTERN.match(self.replacement_brain_token_usage)
        ):
            raise ContinuityStateValidationError(
                f"replacement_brain_token_usage must match safe grammar 'UNKNOWN' or 'REPORTED(...)', got: {self.replacement_brain_token_usage!r}"
            )
        if (
            isinstance(self.paid_external_api_calls, bool)
            or not isinstance(self.paid_external_api_calls, int)
            or self.paid_external_api_calls != 0
        ):
            raise ContinuityStateValidationError("paid_external_api_calls must be exactly 0 for acceptance")

        raw_canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        utf8_bytes = raw_canonical.encode("utf-8")
        if len(utf8_bytes) > MAX_SERIALIZED_BYTES:
            raise ContinuityStateValidationError(
                f"Serialized M3BLiveAttestation exceeds size limit ({len(utf8_bytes)} > {MAX_SERIALIZED_BYTES})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chat_ui_automation": self.chat_ui_automation,
            "distinct_real_brain_surfaces": self.distinct_real_brain_surfaces,
            "fresh_replacement_session": self.fresh_replacement_session,
            "fresh_source_session": self.fresh_source_session,
            "human_bounded_transfer_bytes": self.human_bounded_transfer_bytes,
            "interaction_transport": self.interaction_transport,
            "paid_external_api_calls": self.paid_external_api_calls,
            "replacement_brain_id": self.replacement_brain_id,
            "replacement_brain_token_usage": self.replacement_brain_token_usage,
            "schema_version": self.schema_version,
            "source_brain_id": self.source_brain_id,
            "source_brain_token_usage": self.source_brain_token_usage,
            "transcript_transferred": self.transcript_transferred,
        }

    def to_canonical_json(self) -> str:
        data = self.to_dict()
        return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Any) -> M3BLiveAttestation:
        if not isinstance(data, dict):
            raise ContinuityStateValidationError(f"M3BLiveAttestation root must be a dict, got: {type(data).__name__}")

        allowed_keys = {
            "chat_ui_automation",
            "distinct_real_brain_surfaces",
            "fresh_replacement_session",
            "fresh_source_session",
            "human_bounded_transfer_bytes",
            "interaction_transport",
            "paid_external_api_calls",
            "replacement_brain_id",
            "replacement_brain_token_usage",
            "schema_version",
            "source_brain_id",
            "source_brain_token_usage",
            "transcript_transferred",
        }

        forbidden_present = set(data.keys()) & FORBIDDEN_ATTESTATION_KEYS
        if forbidden_present:
            raise ContinuityStateValidationError(
                f"Forbidden transcript/secret fields in M3BLiveAttestation: {sorted(forbidden_present)}"
            )

        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            raise ContinuityStateValidationError(
                f"Unknown fields in M3BLiveAttestation: {sorted(extra_keys)}"
            )

        for req in allowed_keys:
            if req not in data:
                raise ContinuityStateValidationError(f"Missing required field '{req}' in M3BLiveAttestation")

        return cls(
            schema_version=data["schema_version"],
            distinct_real_brain_surfaces=data["distinct_real_brain_surfaces"],
            fresh_source_session=data["fresh_source_session"],
            fresh_replacement_session=data["fresh_replacement_session"],
            transcript_transferred=data["transcript_transferred"],
            chat_ui_automation=data["chat_ui_automation"],
            interaction_transport=data["interaction_transport"],
            human_bounded_transfer_bytes=data["human_bounded_transfer_bytes"],
            source_brain_id=data["source_brain_id"],
            replacement_brain_id=data["replacement_brain_id"],
            source_brain_token_usage=data["source_brain_token_usage"],
            replacement_brain_token_usage=data["replacement_brain_token_usage"],
            paid_external_api_calls=data["paid_external_api_calls"],
        )


def compute_git_blob_sha(content_bytes: bytes) -> str:
    """Computes exact Git content-addressed blob SHA-1."""
    header = f"blob {len(content_bytes)}\0".encode("utf-8")
    return hashlib.sha1(header + content_bytes).hexdigest()


def validate_diagnosis_semantic_anchors(text: str) -> None:
    """
    Validates that Brain B's diagnosis artifact demonstrates the 6 mandatory semantic anchors (TASK-027 C7 / Phase 3 / R1-3):
    1. same canonical state fingerprint required;
    2. request semantics identical except Brain/request IDs;
    3. source SUCCESS blocks duplicate failover;
    4. zero transcript / hidden reasoning requirement;
    5. capability gate must pass;
    6. Brain remains advisory and Human RUN/FIX/MERGE authority is unchanged.
    """
    norm_text = text.lower()

    # Anchor 1: State fingerprint
    if "state fingerprint" not in norm_text and "state_fingerprint" not in norm_text:
        raise ContinuityStateValidationError("Diagnosis missing mandatory semantic anchor 1: canonical state fingerprint requirement")

    # Anchor 2: Semantic request equality
    if "request" not in norm_text or not any(k in norm_text for k in ["semantic", "identical", "equality", "objective"]):
        raise ContinuityStateValidationError("Diagnosis missing mandatory semantic anchor 2: request semantic equivalence")

    # Anchor 3: Source SUCCESS duplicate output blocking
    has_success_block = ("success" in norm_text and any(k in norm_text for k in ["duplicate", "competing", "block", "forbidden"]))
    if not has_success_block:
        raise ContinuityStateValidationError("Diagnosis missing mandatory semantic anchor 3: source SUCCESS duplicate output blocking")

    # Anchor 4: Zero transcript / hidden reasoning
    if not any(k in norm_text for k in ["transcript", "hidden reasoning", "chain-of-thought", "cot"]):
        raise ContinuityStateValidationError("Diagnosis missing mandatory semantic anchor 4: zero transcript/reasoning isolation")

    # Anchor 5: Capability gate
    if "capability" not in norm_text or not any(k in norm_text for k in ["gate", "support", "operation", "declaration"]):
        raise ContinuityStateValidationError("Diagnosis missing mandatory semantic anchor 5: capability gate validation")

    # Anchor 6: Advisory role & unchanged human authority
    if "advisory" not in norm_text or not any(k in norm_text for k in ["authority", "human", "run/fix/merge", "merge"]):
        raise ContinuityStateValidationError("Diagnosis missing mandatory semantic anchor 6: advisory role and unchanged human authority")


def build_m3b_proof_state() -> ContinuityState:
    """Constructs the canonical frozen schema-v1 ContinuityState for TASK-027 M3B proof."""
    main_sha = "44436c59eb42dbdbffaee28a738d11694958a4ea"
    task_blob = "96b0b10d32fe085f0ebc612d2540e7be2e968aed"
    adr010_blob = "504630c25f37c83819ae951076704765609105c7"
    adr011_blob = "0ce561b1de5c964bb93ea0a5a127b48d86a65839"
    adr016_blob = "36373689f0d094276e22cb2091e82770190c99fa"
    adr017_blob = "814d14ccdd2e6019f8138ea5b6e3d75ca1f5b52c"

    return ContinuityState(
        schema_version="1",
        task_id="TASK-027",
        phase=ContinuityPhase.READY_FOR_RUN,
        next_operation=NextOperation.RUN_APPROVAL,
        main=BranchState(branch="main", sha=main_sha),
        task_branch=BranchState(branch="ai/task-027", sha=None),
        artifacts=ContinuityArtifacts(
            task=ArtifactRef(path=".ai/tasks/TASK-027.md", ref="ai-control", blob_sha=task_blob),
            contracts=(
                ArtifactRef(path=".ai/decisions/ADR-010-OPEN-MULTI-AGENT-CONTINUITY-OS-ARCHITECTURE-LOCK.md", ref="ai-control", blob_sha=adr010_blob),
                ArtifactRef(path=".ai/decisions/ADR-011-AIOS-CONTINUITY-M1-CANONICAL-PROJECT-STATE-CONTRACT-LOCK.md", ref="ai-control", blob_sha=adr011_blob),
                ArtifactRef(path=".ai/decisions/ADR-016-AIOS-CONTINUITY-M3-BRAIN-FAILOVER-PROOF-CONTRACT-LOCK.md", ref="ai-control", blob_sha=adr016_blob),
                ArtifactRef(path=".ai/decisions/ADR-017-AIOS-UNIFORM-ASSURANCE-PIPELINE-AND-FINAL-INDEPENDENT-AUDIT-POLICY-LOCK.md", ref="ai-control", blob_sha=adr017_blob),
            ),
            plan=None,
            result=None,
            review=None,
        ),
        brain=BrainState(last_id="chatgpt-chat", last_operation=BrainOperation.PLAN),
        executor=ExecutorState(last_id="antigravity"),
    )


def build_m3b_source_request() -> BrainRequest:
    """Constructs the canonical source BrainRequest for Brain A (chatgpt-chat)."""
    return BrainRequest(
        schema_version="1",
        task_id="TASK-027",
        request_id="req-task-027-source-01",
        brain_id="chatgpt-chat",
        operation=BrainOperation.DIAGNOSIS,
        objective="Diagnose the invariants required for a valid M3B stable-boundary Brain failover and identify conditions that would make the handoff invalid.",
        output_contract=OutputContract(
            expected_output_type=BrainOutputType.DIAGNOSIS_ARTIFACT,
            target_artifact_path=".ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md",
        ),
        context_refs=(
            ContextRef(path=".ai/tasks/TASK-027.md", blob_sha="96b0b10d32fe085f0ebc612d2540e7be2e968aed"),
            ContextRef(path=".ai/decisions/ADR-016-AIOS-CONTINUITY-M3-BRAIN-FAILOVER-PROOF-CONTRACT-LOCK.md", blob_sha="36373689f0d094276e22cb2091e82770190c99fa"),
            ContextRef(path=".ai/decisions/ADR-010-OPEN-MULTI-AGENT-CONTINUITY-OS-ARCHITECTURE-LOCK.md", blob_sha="504630c25f37c83819ae951076704765609105c7"),
            ContextRef(path=".ai/decisions/ADR-017-AIOS-UNIFORM-ASSURANCE-PIPELINE-AND-FINAL-INDEPENDENT-AUDIT-POLICY-LOCK.md", blob_sha="814d14ccdd2e6019f8138ea5b6e3d75ca1f5b52c"),
        ),
    )


def build_m3b_replacement_capability() -> BrainCapability:
    """Constructs the replacement BrainCapability declaration for Brain B (claude-chat)."""
    return BrainCapability(
        brain_id="claude-chat",
        supported_operations=(
            BrainOperation.DIAGNOSIS,
            BrainOperation.PLAN,
            BrainOperation.REVIEW,
        ),
    )


def verify_and_bind_m3b_proof(
    state: ContinuityState,
    source_request: BrainRequest,
    replacement_request: BrainRequest,
    replacement_capability: BrainCapability,
    source_result: BrainResult,
    diagnosis_content_text: str | bytes,
    attestation: M3BLiveAttestation,
    output_dir: Path | None = None,
    worktree_root: Path = REPO_DIR,
    persisted_failover_proof: BrainFailoverProof | None = None,
) -> dict[str, Any]:
    """
    Executes pure deterministic failover validation and mechanically binds the replacement artifact.
    Writes proof artifacts to output_dir and worktree_root (isolated under test root when testing).
    Binds immutably to persisted_failover_proof when supplied from Stage 2.
    """
    state_fp = state.fingerprint()

    # 1. Enforce TASK-027 controlled source result invariant (R3-1)
    validate_m3b_controlled_source_result(source_result)

    # 2. Validate failover eligibility using pure M3A module
    recomputed_proof = validate_brain_failover_eligibility(
        source_request=source_request,
        replacement_request=replacement_request,
        state=state,
        expected_state_fingerprint=state_fp,
        replacement_capability=replacement_capability,
        source_result=source_result,
    )

    # If persisted Stage-2 proof was provided, verify exact immutable binding (R1-1 B)
    if persisted_failover_proof is not None:
        if persisted_failover_proof.fingerprint() != recomputed_proof.fingerprint():
            raise ContinuityStateValidationError(
                f"Persisted failover proof fingerprint '{persisted_failover_proof.fingerprint()}' "
                f"!= recomputed '{recomputed_proof.fingerprint()}'"
            )
        if persisted_failover_proof.replacement_request_fingerprint != replacement_request.fingerprint():
            raise ContinuityStateValidationError("Stage-2 proof replacement_request_fingerprint mismatch")

    failover_proof = persisted_failover_proof or recomputed_proof

    # 3. Cross-bind attestation identities with request identities (R1-4)
    if attestation.source_brain_id != source_request.brain_id:
        raise ContinuityStateValidationError(
            f"Attestation source_brain_id '{attestation.source_brain_id}' != source_request.brain_id '{source_request.brain_id}'"
        )
    if attestation.replacement_brain_id != replacement_request.brain_id:
        raise ContinuityStateValidationError(
            f"Attestation replacement_brain_id '{attestation.replacement_brain_id}' != replacement_request.brain_id '{replacement_request.brain_id}'"
        )

    # 4. Validate diagnosis semantic anchors
    diag_str = diagnosis_content_text if isinstance(diagnosis_content_text, str) else bytes(diagnosis_content_text).decode("utf-8")
    validate_diagnosis_semantic_anchors(diag_str)

    # 5. Deterministic newline-only normalization (R2-1)
    diagnosis_bytes = normalize_line_endings(diagnosis_content_text)
    if len(diagnosis_bytes) > MAX_SERIALIZED_BYTES:
        raise ContinuityStateValidationError(
            f"Diagnosis artifact exceeds 16 KiB bound: {len(diagnosis_bytes)} bytes"
        )

    diag_blob_sha = compute_git_blob_sha(diagnosis_bytes)
    target_path = replacement_request.output_contract.target_artifact_path
    if not target_path:
        raise ContinuityStateValidationError("Replacement request missing target_artifact_path")

    # 6. Construct replacement BrainResult
    replacement_result = BrainResult(
        schema_version="1",
        task_id=replacement_request.task_id,
        request_id=replacement_request.request_id,
        brain_id=replacement_request.brain_id,
        operation=replacement_request.operation,
        status=BrainResultStatus.SUCCESS,
        output_type=BrainOutputType.DIAGNOSIS_ARTIFACT,
        artifact_ref=ArtifactRef(
            path=target_path,
            ref="ai/task-027",
            blob_sha=diag_blob_sha,
        ),
        error_code=None,
        evidence_ref=None,
    )

    # 7. Persist isolated files under worktree_root & output_dir
    diag_file = worktree_root / target_path
    diag_file.parent.mkdir(parents=True, exist_ok=True)
    diag_file.write_bytes(diagnosis_bytes)

    # Verify on-disk written bytes match calculated blob SHA
    disk_bytes = diag_file.read_bytes()
    if disk_bytes != diagnosis_bytes:
        raise ContinuityStateValidationError("Disk written diagnosis bytes mismatch in-memory bytes")
    disk_blob_sha = compute_git_blob_sha(disk_bytes)
    if disk_blob_sha != diag_blob_sha:
        raise ContinuityStateValidationError(
            f"On-disk diagnosis blob SHA '{disk_blob_sha}' != computed '{diag_blob_sha}'"
        )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "TASK-027-M3B-STATE.json").write_text(state.to_canonical_json(), encoding="utf-8")
        (output_dir / "TASK-027-M3B-SOURCE-REQUEST.json").write_text(source_request.to_canonical_json(), encoding="utf-8")
        (output_dir / "TASK-027-M3B-SOURCE-RESULT.json").write_text(source_result.to_canonical_json(), encoding="utf-8")
        (output_dir / "TASK-027-M3B-REPLACEMENT-REQUEST.json").write_text(replacement_request.to_canonical_json(), encoding="utf-8")
        (output_dir / "TASK-027-M3B-REPLACEMENT-CAPABILITY.json").write_text(
            json.dumps(replacement_capability.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "TASK-027-M3B-FAILOVER-PROOF.json").write_text(failover_proof.to_canonical_json(), encoding="utf-8")
        (output_dir / "TASK-027-M3B-REPLACEMENT-RESULT.json").write_text(replacement_result.to_canonical_json(), encoding="utf-8")
        (output_dir / "TASK-027-M3B-LIVE-ATTESTATION.json").write_text(
            json.dumps(attestation.to_dict(), sort_keys=True, indent=2), encoding="utf-8"
        )

    return {
        "state_fingerprint": state_fp,
        "source_request_fingerprint": source_request.fingerprint(),
        "source_result_fingerprint": source_result.fingerprint(),
        "replacement_request_fingerprint": replacement_request.fingerprint(),
        "replacement_result_fingerprint": replacement_result.fingerprint(),
        "failover_proof_fingerprint": failover_proof.fingerprint(),
        "diagnosis_blob_sha": diag_blob_sha,
        "diagnosis_bytes_len": len(diagnosis_bytes),
        "attestation": attestation.to_dict(),
    }


def audit_persisted_bundle(proofs_dir: Path, worktree_root: Path = REPO_DIR) -> dict[str, Any]:
    """
    Non-mutating final bundle verifier (REVIEW-027 R1-2, R3-1, R3-2):
    Reloads all 8 persisted JSON proof artifacts and the on-disk diagnosis artifact.
    Re-runs full M3A failover validation, recomputes all fingerprints and Git blob SHA.
    Enforces TASK-027 controlled source result invariants (R3-1).
    Enforces full replacement BrainResult cross-binding against BrainRequest (R3-2).
    Fails closed on any inconsistency without writing or mutating any files.
    """
    for req_art in [
        "TASK-027-M3B-STATE.json",
        "TASK-027-M3B-SOURCE-REQUEST.json",
        "TASK-027-M3B-SOURCE-RESULT.json",
        "TASK-027-M3B-REPLACEMENT-REQUEST.json",
        "TASK-027-M3B-REPLACEMENT-CAPABILITY.json",
        "TASK-027-M3B-FAILOVER-PROOF.json",
        "TASK-027-M3B-REPLACEMENT-RESULT.json",
        "TASK-027-M3B-LIVE-ATTESTATION.json",
    ]:
        fpath = proofs_dir / req_art
        if not fpath.exists():
            raise ContinuityStateValidationError(f"Missing persisted proof artifact for audit: {req_art}")

    state = ContinuityState.from_json((proofs_dir / "TASK-027-M3B-STATE.json").read_text(encoding="utf-8"))
    src_req = BrainRequest.from_json((proofs_dir / "TASK-027-M3B-SOURCE-REQUEST.json").read_text(encoding="utf-8"))
    src_res = BrainResult.from_json((proofs_dir / "TASK-027-M3B-SOURCE-RESULT.json").read_text(encoding="utf-8"))
    rep_req = BrainRequest.from_json((proofs_dir / "TASK-027-M3B-REPLACEMENT-REQUEST.json").read_text(encoding="utf-8"))
    rep_cap_data = json.loads((proofs_dir / "TASK-027-M3B-REPLACEMENT-CAPABILITY.json").read_text(encoding="utf-8"))
    rep_cap = BrainCapability.from_dict(rep_cap_data)
    persisted_proof = BrainFailoverProof.from_json((proofs_dir / "TASK-027-M3B-FAILOVER-PROOF.json").read_text(encoding="utf-8"))
    rep_res = BrainResult.from_json((proofs_dir / "TASK-027-M3B-REPLACEMENT-RESULT.json").read_text(encoding="utf-8"))
    att_data = json.loads((proofs_dir / "TASK-027-M3B-LIVE-ATTESTATION.json").read_text(encoding="utf-8"))
    attestation = M3BLiveAttestation.from_dict(att_data)

    # 1. Enforce controlled source result invariant (R3-1)
    validate_m3b_controlled_source_result(src_res)

    # 2. Check diagnosis file on disk
    target_path = rep_req.output_contract.target_artifact_path
    if not target_path:
        raise ContinuityStateValidationError("Replacement request missing target_artifact_path")

    diag_file = worktree_root / target_path
    if not diag_file.exists():
        raise ContinuityStateValidationError(f"Persisted diagnosis file missing at target: {diag_file}")

    diag_bytes = diag_file.read_bytes()
    if len(diag_bytes) > MAX_SERIALIZED_BYTES:
        raise ContinuityStateValidationError(f"Persisted diagnosis size ({len(diag_bytes)}) exceeds limit")

    diag_text = diag_bytes.decode("utf-8")
    validate_diagnosis_semantic_anchors(diag_text)
    disk_blob_sha = compute_git_blob_sha(diag_bytes)

    # 3. Full structural cross-binding of replacement BrainResult against BrainRequest (R3-2)
    expected_rep_res = BrainResult(
        schema_version="1",
        task_id=rep_req.task_id,
        request_id=rep_req.request_id,
        brain_id=rep_req.brain_id,
        operation=rep_req.operation,
        status=BrainResultStatus.SUCCESS,
        output_type=rep_req.output_contract.expected_output_type,
        artifact_ref=ArtifactRef(
            path=target_path,
            ref="ai/task-027",
            blob_sha=disk_blob_sha,
        ),
        error_code=None,
        evidence_ref=None,
    )
    if rep_res.to_canonical_json() != expected_rep_res.to_canonical_json():
        raise ContinuityStateValidationError(
            f"Persisted replacement result does not match expected result derived from replacement request and diagnosis blob.\n"
            f"Persisted: {rep_res.to_dict()}\n"
            f"Expected:  {expected_rep_res.to_dict()}"
        )

    # 4. Re-validate M3A eligibility
    recomputed_proof = validate_brain_failover_eligibility(
        source_request=src_req,
        replacement_request=rep_req,
        state=state,
        expected_state_fingerprint=state.fingerprint(),
        replacement_capability=rep_cap,
        source_result=src_res,
    )

    if recomputed_proof.fingerprint() != persisted_proof.fingerprint():
        raise ContinuityStateValidationError(
            f"Recomputed failover proof fingerprint '{recomputed_proof.fingerprint()}' "
            f"!= persisted '{persisted_proof.fingerprint()}'"
        )

    # 5. Attestation cross-binding
    if attestation.source_brain_id != src_req.brain_id:
        raise ContinuityStateValidationError("Attestation source_brain_id != source_request.brain_id")
    if attestation.replacement_brain_id != rep_req.brain_id:
        raise ContinuityStateValidationError("Attestation replacement_brain_id != replacement_request.brain_id")

    return {
        "status": "PASS",
        "state_fingerprint": state.fingerprint(),
        "source_request_fingerprint": src_req.fingerprint(),
        "source_result_fingerprint": src_res.fingerprint(),
        "replacement_request_fingerprint": rep_req.fingerprint(),
        "replacement_result_fingerprint": rep_res.fingerprint(),
        "failover_proof_fingerprint": persisted_proof.fingerprint(),
        "diagnosis_blob_sha": disk_blob_sha,
        "diagnosis_bytes": len(diag_bytes),
    }


def command_prepare_source(output_dir: Path) -> int:
    """Stage 1: Deterministically constructs and writes state and source request only, purging stale downstream artifacts (R1-1 A)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Purge any pre-existing downstream artifacts (R1-1 A)
    for downstream in DOWNSTREAM_PROOF_ARTIFACTS:
        fpath = output_dir / downstream
        if fpath.exists():
            fpath.unlink()

    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()

    (output_dir / "TASK-027-M3B-STATE.json").write_text(state.to_canonical_json(), encoding="utf-8")
    (output_dir / "TASK-027-M3B-SOURCE-REQUEST.json").write_text(src_req.to_canonical_json(), encoding="utf-8")

    print("=== TASK-027 Stage 1: Source Preparation Complete ===")
    print(f"TASK_ID:                         {state.task_id}")
    print(f"STATE_FINGERPRINT:               {state.fingerprint()}")
    print(f"SOURCE_BRAIN_ID:                 {src_req.brain_id}")
    print(f"SOURCE_REQUEST_ID:               {src_req.request_id}")
    print(f"SOURCE_REQUEST_FINGERPRINT:      {src_req.fingerprint()}")
    print(f"OUTPUT_TARGET:                   {src_req.output_contract.target_artifact_path}")
    print(f"OUTPUT_DIR:                      {output_dir}")
    print("\n--- HUMAN CHECKPOINT 1 (Brain A: chatgpt-chat) ---")
    print("Provide source request pack to ChatGPT in a fresh session.")
    print("Return the controlled INCOMPLETE result JSON to proceed to validate-source / prepare-replacement.")
    return 0


def command_validate_source(source_result_path: Path, output_dir: Path) -> int:
    """
    Stage 2: Consumes external Brain A source result, validates failover eligibility & controlled mode (R3-1),
    and only on PASS emits replacement request, capability, and failover proof (R1-1).
    """
    if not source_result_path.exists():
        print(f"[ERROR] Source result file not found: {source_result_path}", file=sys.stderr)
        return 1

    state_path = output_dir / "TASK-027-M3B-STATE.json"
    src_req_path = output_dir / "TASK-027-M3B-SOURCE-REQUEST.json"
    if not state_path.exists() or not src_req_path.exists():
        print("[ERROR] Stage 1 artifacts missing in output_dir. Run prepare-source first.", file=sys.stderr)
        return 1

    state = ContinuityState.from_json(state_path.read_text(encoding="utf-8"))
    src_req = BrainRequest.from_json(src_req_path.read_text(encoding="utf-8"))
    src_res = BrainResult.from_json(source_result_path.read_text(encoding="utf-8"))

    # Purge downstream Stage 2/3 artifacts in case validation fails
    for downstream in DOWNSTREAM_PROOF_ARTIFACTS:
        fpath = output_dir / downstream
        if fpath.exists():
            fpath.unlink()

    # Enforce TASK-027 specific controlled source mode (R3-1)
    validate_m3b_controlled_source_result(src_res)

    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()

    # Failover eligibility validation gate (M3A pure validator)
    failover_proof = validate_brain_failover_eligibility(
        source_request=src_req,
        replacement_request=rep_req,
        state=state,
        expected_state_fingerprint=state.fingerprint(),
        replacement_capability=rep_cap,
        source_result=src_res,
    )

    # Persist Stage 2 artifacts
    (output_dir / "TASK-027-M3B-SOURCE-RESULT.json").write_text(src_res.to_canonical_json(), encoding="utf-8")
    (output_dir / "TASK-027-M3B-REPLACEMENT-REQUEST.json").write_text(rep_req.to_canonical_json(), encoding="utf-8")
    (output_dir / "TASK-027-M3B-REPLACEMENT-CAPABILITY.json").write_text(
        json.dumps(rep_cap.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "TASK-027-M3B-FAILOVER-PROOF.json").write_text(failover_proof.to_canonical_json(), encoding="utf-8")

    print("=== TASK-027 Stage 2: Source Validated & Failover Eligible ===")
    print(f"SOURCE_RESULT_STATUS:            {src_res.status.value}")
    print(f"FAILOVER_PROOF_FINGERPRINT:      {failover_proof.fingerprint()}")
    print(f"REPLACEMENT_BRAIN_ID:            {rep_req.brain_id}")
    print(f"REPLACEMENT_REQUEST_ID:          {rep_req.request_id}")
    print(f"REPLACEMENT_REQUEST_FINGERPRINT: {rep_req.fingerprint()}")
    print("\n--- HUMAN CHECKPOINT 2 (Brain B: claude-chat) ---")
    print("Provide replacement request pack to Claude in a fresh session (NO Brain A transcript).")
    print("Return diagnosis artifact and explicit live attestation to proceed to verify-replacement.")
    return 0


def command_verify_replacement(
    diagnosis_path: Path,
    attestation_path: Path,
    output_dir: Path,
    worktree_root: Path = REPO_DIR,
) -> int:
    """
    Stage 3: Consumes Brain B diagnosis and attestation, binds immutably to Stage-2 proof receipt (R1-1 B),
    binds replacement result, and audits bundle.
    """
    if not diagnosis_path.exists():
        print(f"[ERROR] Diagnosis artifact file not found: {diagnosis_path}", file=sys.stderr)
        return 1
    if not attestation_path.exists():
        print(f"[ERROR] Attestation file not found: {attestation_path}", file=sys.stderr)
        return 1

    proof_path = output_dir / "TASK-027-M3B-FAILOVER-PROOF.json"
    if not proof_path.exists():
        print("[ERROR] Stage 2 failover proof receipt missing in output_dir. Run validate-source first.", file=sys.stderr)
        return 1

    state = ContinuityState.from_json((output_dir / "TASK-027-M3B-STATE.json").read_text(encoding="utf-8"))
    src_req = BrainRequest.from_json((output_dir / "TASK-027-M3B-SOURCE-REQUEST.json").read_text(encoding="utf-8"))
    src_res = BrainResult.from_json((output_dir / "TASK-027-M3B-SOURCE-RESULT.json").read_text(encoding="utf-8"))
    rep_req = BrainRequest.from_json((output_dir / "TASK-027-M3B-REPLACEMENT-REQUEST.json").read_text(encoding="utf-8"))
    rep_cap_data = json.loads((output_dir / "TASK-027-M3B-REPLACEMENT-CAPABILITY.json").read_text(encoding="utf-8"))
    rep_cap = BrainCapability.from_dict(rep_cap_data)
    stage2_proof = BrainFailoverProof.from_json(proof_path.read_text(encoding="utf-8"))

    diag_text = diagnosis_path.read_text(encoding="utf-8")
    att_data = json.loads(attestation_path.read_text(encoding="utf-8"))
    attestation = M3BLiveAttestation.from_dict(att_data)

    summary = verify_and_bind_m3b_proof(
        state=state,
        source_request=src_req,
        replacement_request=rep_req,
        replacement_capability=rep_cap,
        source_result=src_res,
        diagnosis_content_text=diag_text,
        attestation=attestation,
        output_dir=output_dir,
        worktree_root=worktree_root,
        persisted_failover_proof=stage2_proof,
    )

    # Run non-mutating bundle audit to double-check consistency
    audit_summary = audit_persisted_bundle(proofs_dir=output_dir, worktree_root=worktree_root)

    print("\n=== M3B Proof Verification & Audit Passed ===")
    print(f"FAILOVER_PROOF_FINGERPRINT:      {summary['failover_proof_fingerprint']}")
    print(f"DIAGNOSIS_BLOB_SHA:              {summary['diagnosis_blob_sha']}")
    print(f"REPLACEMENT_RESULT_FINGERPRINT:  {summary['replacement_result_fingerprint']}")
    print(f"AUDIT_STATUS:                    {audit_summary['status']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TASK-027 M3B Cross-Brain Proof Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # prepare-source
    p_prep = subparsers.add_parser("prepare-source", help="Stage 1: Prepare state and source request, purge downstream")
    p_prep.add_argument("--output-dir", type=Path, default=REPO_DIR / ".ai" / "context" / "proofs", help="Output directory")

    # validate-source
    p_val = subparsers.add_parser("validate-source", help="Stage 2: Validate source result and prepare replacement")
    p_val.add_argument("--source-result", type=Path, required=True, help="Path to source BrainResult JSON")
    p_val.add_argument("--output-dir", type=Path, default=REPO_DIR / ".ai" / "context" / "proofs", help="Output directory")

    # verify-replacement
    p_ver = subparsers.add_parser("verify-replacement", help="Stage 3: Verify replacement diagnosis and bind evidence")
    p_ver.add_argument("--diagnosis-file", type=Path, required=True, help="Path to replacement diagnosis artifact markdown")
    p_ver.add_argument("--attestation", type=Path, required=True, help="Path to human live attestation JSON")
    p_ver.add_argument("--output-dir", type=Path, default=REPO_DIR / ".ai" / "context" / "proofs", help="Output directory")
    p_ver.add_argument("--worktree-root", type=Path, default=REPO_DIR, help="Worktree root for diagnosis destination")

    # audit-bundle
    p_aud = subparsers.add_parser("audit-bundle", help="Non-mutating audit of persisted proof bundle")
    p_aud.add_argument("--output-dir", type=Path, default=REPO_DIR / ".ai" / "context" / "proofs", help="Directory containing proof JSONs")
    p_aud.add_argument("--worktree-root", type=Path, default=REPO_DIR, help="Worktree root containing diagnosis")

    args = parser.parse_args()

    if args.command == "prepare-source":
        return command_prepare_source(args.output_dir)
    elif args.command == "validate-source":
        return command_validate_source(source_result_path=args.source_result, output_dir=args.output_dir)
    elif args.command == "verify-replacement":
        return command_verify_replacement(
            diagnosis_path=args.diagnosis_file,
            attestation_path=args.attestation,
            output_dir=args.output_dir,
            worktree_root=args.worktree_root,
        )
    elif args.command == "audit-bundle":
        res = audit_persisted_bundle(proofs_dir=args.output_dir, worktree_root=args.worktree_root)
        print("=== Non-Mutating Bundle Audit Passed ===")
        print(f"STATUS:                     {res['status']}")
        print(f"STATE_FINGERPRINT:          {res['state_fingerprint']}")
        print(f"FAILOVER_PROOF_FINGERPRINT: {res['failover_proof_fingerprint']}")
        print(f"DIAGNOSIS_BLOB_SHA:         {res['diagnosis_blob_sha']}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
