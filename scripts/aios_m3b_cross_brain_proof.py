"""
Deterministic M3B Real Cross-Chat Brain Failover Proof Runner (TASK-027 / ADR-016 / ADR-017).
Provides separate prepare and verify commands with strict live-attestation schema and test isolation.
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
        if not self.source_brain_token_usage or not isinstance(self.source_brain_token_usage, str):
            raise ContinuityStateValidationError("source_brain_token_usage must be a non-empty string")
        if not self.replacement_brain_token_usage or not isinstance(self.replacement_brain_token_usage, str):
            raise ContinuityStateValidationError("replacement_brain_token_usage must be a non-empty string")
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
    if "success" not in norm_text or not any(k in norm_text for k in ["duplicate", "competing", "block", "forbidden", "fail over"]):
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
    diagnosis_content_text: str,
    attestation: M3BLiveAttestation,
    output_dir: Path | None = None,
    worktree_root: Path = REPO_DIR,
) -> dict[str, Any]:
    """
    Executes pure deterministic failover validation and mechanically binds the replacement artifact.
    Writes proof artifacts to output_dir and worktree_root (isolated under test root when testing).
    """
    state_fp = state.fingerprint()

    # 1. Validate failover eligibility using pure M3A module
    failover_proof = validate_brain_failover_eligibility(
        source_request=source_request,
        replacement_request=replacement_request,
        state=state,
        expected_state_fingerprint=state_fp,
        replacement_capability=replacement_capability,
        source_result=source_result,
    )

    # 2. Validate diagnosis semantic anchors
    validate_diagnosis_semantic_anchors(diagnosis_content_text)

    # 3. Mechanically verify and bind diagnosis artifact
    norm_diagnosis_text = diagnosis_content_text.replace("\r\n", "\n").strip() + "\n"
    diagnosis_bytes = norm_diagnosis_text.encode("utf-8")
    if len(diagnosis_bytes) > MAX_SERIALIZED_BYTES:
        raise ContinuityStateValidationError(
            f"Diagnosis artifact exceeds 16 KiB bound: {len(diagnosis_bytes)} bytes"
        )

    diag_blob_sha = compute_git_blob_sha(diagnosis_bytes)
    target_path = replacement_request.output_contract.target_artifact_path
    if not target_path:
        raise ContinuityStateValidationError("Replacement request missing target_artifact_path")

    # 4. Construct replacement BrainResult
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

    # 5. Persist isolated files under worktree_root & output_dir
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


def command_prepare(output_dir: Path) -> int:
    """Deterministic prepare command: emits state, requests, capability, and prompts."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "TASK-027-M3B-STATE.json").write_text(state.to_canonical_json(), encoding="utf-8")
    (output_dir / "TASK-027-M3B-SOURCE-REQUEST.json").write_text(src_req.to_canonical_json(), encoding="utf-8")
    (output_dir / "TASK-027-M3B-REPLACEMENT-REQUEST.json").write_text(rep_req.to_canonical_json(), encoding="utf-8")
    (output_dir / "TASK-027-M3B-REPLACEMENT-CAPABILITY.json").write_text(
        json.dumps(rep_cap.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    print("=== TASK-027 M3B Preparation Complete ===")
    print(f"TASK_ID:                         {state.task_id}")
    print(f"STATE_FINGERPRINT:               {state.fingerprint()}")
    print(f"SOURCE_BRAIN_ID:                 {src_req.brain_id}")
    print(f"SOURCE_REQUEST_ID:               {src_req.request_id}")
    print(f"SOURCE_REQUEST_FINGERPRINT:      {src_req.fingerprint()}")
    print(f"REPLACEMENT_BRAIN_ID:            {rep_req.brain_id}")
    print(f"REPLACEMENT_REQUEST_ID:          {rep_req.request_id}")
    print(f"REPLACEMENT_REQUEST_FINGERPRINT: {rep_req.fingerprint()}")
    print(f"OUTPUT_TARGET:                   {src_req.output_contract.target_artifact_path}")
    print(f"OUTPUT_DIR:                      {output_dir}")
    print("\n--- HUMAN CHECKPOINT 1 (Brain A: chatgpt-chat) ---")
    print("Provide source request pack to ChatGPT in a fresh session. Return controlled INCOMPLETE result.")
    print("\n--- HUMAN CHECKPOINT 2 (Brain B: claude-chat) ---")
    print("Provide replacement request pack to Claude in a fresh session (NO Brain A transcript). Return diagnosis artifact.")
    return 0


def command_verify(
    source_result_path: Path,
    diagnosis_path: Path,
    attestation_path: Path,
    output_dir: Path,
    worktree_root: Path = REPO_DIR,
) -> int:
    """Verifies failover eligibility from explicit external live inputs and binds replacement artifact."""
    if not source_result_path.exists():
        print(f"[ERROR] Source result file not found: {source_result_path}", file=sys.stderr)
        return 1
    if not diagnosis_path.exists():
        print(f"[ERROR] Diagnosis artifact file not found: {diagnosis_path}", file=sys.stderr)
        return 1
    if not attestation_path.exists():
        print(f"[ERROR] Attestation file not found: {attestation_path}", file=sys.stderr)
        return 1

    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()

    src_res = BrainResult.from_json(source_result_path.read_text(encoding="utf-8"))
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
    )

    print("\n=== M3B Proof Verification Passed ===")
    print(f"FAILOVER_PROOF_FINGERPRINT:      {summary['failover_proof_fingerprint']}")
    print(f"DIAGNOSIS_BLOB_SHA:              {summary['diagnosis_blob_sha']}")
    print(f"REPLACEMENT_RESULT_FINGERPRINT:  {summary['replacement_result_fingerprint']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TASK-027 M3B Cross-Brain Proof Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # prepare
    prep_p = subparsers.add_parser("prepare", help="Prepare deterministic proof state and requests")
    prep_p.add_argument("--output-dir", type=Path, default=REPO_DIR / ".ai" / "context" / "proofs", help="Output directory for prepared artifacts")

    # verify
    ver_p = subparsers.add_parser("verify", help="Verify live failover proof from explicit external inputs")
    ver_p.add_argument("--source-result", type=Path, required=True, help="Path to normalized source BrainResult JSON")
    ver_p.add_argument("--diagnosis-file", type=Path, required=True, help="Path to replacement diagnosis artifact markdown")
    ver_p.add_argument("--attestation", type=Path, required=True, help="Path to human live attestation JSON")
    ver_p.add_argument("--output-dir", type=Path, default=REPO_DIR / ".ai" / "context" / "proofs", help="Output directory for proof evidence")
    ver_p.add_argument("--worktree-root", type=Path, default=REPO_DIR, help="Worktree root for diagnosis destination")

    args = parser.parse_args()

    if args.command == "prepare":
        return command_prepare(args.output_dir)
    elif args.command == "verify":
        return command_verify(
            source_result_path=args.source_result,
            diagnosis_path=args.diagnosis_file,
            attestation_path=args.attestation,
            output_dir=args.output_dir,
            worktree_root=args.worktree_root,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
