"""Unit tests for TASK-027 M3B Cross-Brain Proof Runner (ADR-016 / ADR-017 / REVIEW-027 R1-1..R1-4)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.aios_m3b_cross_brain_proof import (
    REPO_DIR,
    M3BLiveAttestation,
    build_m3b_proof_state,
    build_m3b_replacement_capability,
    build_m3b_source_request,
    compute_git_blob_sha,
    validate_diagnosis_semantic_anchors,
    verify_and_bind_m3b_proof,
)
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
    ArtifactRef,
    BranchState,
    BrainState,
    ContinuityArtifacts,
    ContinuityPhase,
    ContinuityState,
    ExecutorState,
    NextOperation,
)


def _valid_anchored_diagnosis_sample() -> str:
    return (
        "# DIAGNOSIS — M3B Stable-Boundary Brain Failover Invariants\n\n"
        "## CAUSE\n"
        "Cross-brain failover required at non-success boundary.\n\n"
        "## EVIDENCE\n"
        "1. Canonical state fingerprint locks the repository state and decisions before handoff.\n"
        "2. BrainRequest semantic equality guarantees identical objective, operation, context refs, and output contract.\n"
        "3. A source result with SUCCESS blocks duplicate competing outputs.\n"
        "4. Replacement Brain reconstructs without prior chat transcript, cookies, or hidden reasoning / chain-of-thought.\n"
        "5. Capability gate validation confirms the replacement surface declares support for the operation.\n"
        "6. Brain remains strictly advisory; human authority for RUN, FIX, and MERGE remains unchanged.\n\n"
        "## FIX\n"
        "Apply deterministic failover rules.\n\n"
        "## TESTS\n"
        "Run continuity test suites.\n\n"
        "## RISKS\n"
        "State drift if unstaged changes exist.\n"
    )


def _valid_attestation(source_brain: str = "chatgpt-chat", rep_brain: str = "claude-chat") -> M3BLiveAttestation:
    return M3BLiveAttestation(
        schema_version="1",
        distinct_real_brain_surfaces=True,
        fresh_source_session=True,
        fresh_replacement_session=True,
        transcript_transferred=False,
        chat_ui_automation=False,
        interaction_transport="HUMAN_BOUNDED_ARTIFACT_TRANSFER",
        human_bounded_transfer_bytes=1024,
        source_brain_id=source_brain,
        replacement_brain_id=rep_brain,
        source_brain_token_usage="UNKNOWN",
        replacement_brain_token_usage="UNKNOWN",
        paid_external_api_calls=0,
    )


def _valid_source_result(src_req: BrainRequest) -> BrainResult:
    return BrainResult(
        schema_version="1",
        task_id=src_req.task_id,
        request_id=src_req.request_id,
        brain_id=src_req.brain_id,
        operation=src_req.operation,
        status=BrainResultStatus.INCOMPLETE,
        output_type=src_req.output_contract.expected_output_type,
        error_code="M3B-CONTROLLED-HANDOFF",
        artifact_ref=None,
        evidence_ref=None,
    )


def test_m3b_proof_runner_success_end_to_end(tmp_path: Path):
    """M3B proof runner executes cleanly and isolates all writes under worktree_root (R1-2)."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()
    src_res = _valid_source_result(src_req)
    diag_text = _valid_anchored_diagnosis_sample()
    attestation = _valid_attestation()

    output_proofs_dir = tmp_path / "proofs"

    summary = verify_and_bind_m3b_proof(
        state=state,
        source_request=src_req,
        replacement_request=rep_req,
        replacement_capability=rep_cap,
        source_result=src_res,
        diagnosis_content_text=diag_text,
        attestation=attestation,
        output_dir=output_proofs_dir,
        worktree_root=tmp_path,
    )

    assert len(summary["failover_proof_fingerprint"]) == 64
    assert len(summary["diagnosis_blob_sha"]) == 40
    norm_diag_bytes = (diag_text.replace("\r\n", "\n").strip() + "\n").encode("utf-8")
    assert summary["diagnosis_blob_sha"] == compute_git_blob_sha(norm_diag_bytes)

    # Verify isolated file written under tmp_path
    isolated_diag = tmp_path / ".ai" / "diagnosis" / "TASK-027-M3B-DIAGNOSIS.md"
    assert isolated_diag.exists()
    assert isolated_diag.read_bytes() == norm_diag_bytes

    # Verify all proof evidence JSON files exist under output_proofs_dir
    for art_name in [
        "TASK-027-M3B-STATE.json",
        "TASK-027-M3B-SOURCE-REQUEST.json",
        "TASK-027-M3B-SOURCE-RESULT.json",
        "TASK-027-M3B-REPLACEMENT-REQUEST.json",
        "TASK-027-M3B-REPLACEMENT-CAPABILITY.json",
        "TASK-027-M3B-FAILOVER-PROOF.json",
        "TASK-027-M3B-REPLACEMENT-RESULT.json",
        "TASK-027-M3B-LIVE-ATTESTATION.json",
    ]:
        art_file = output_proofs_dir / art_name
        assert art_file.exists(), f"Missing artifact: {art_name}"
        assert art_file.stat().st_size <= 16384


def test_m3b_proof_runner_source_success_rejected(tmp_path: Path):
    """Source SUCCESS result fails failover validation (duplicate outputs forbidden)."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()

    # Source produced SUCCESS -> failover is forbidden
    src_res_success = BrainResult(
        schema_version="1",
        task_id=src_req.task_id,
        request_id=src_req.request_id,
        brain_id=src_req.brain_id,
        operation=src_req.operation,
        status=BrainResultStatus.SUCCESS,
        output_type=BrainOutputType.DIAGNOSIS_ARTIFACT,
        artifact_ref=ArtifactRef(path=".ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md", ref="ai/task-027", blob_sha="1" * 40),
    )

    with pytest.raises(ContinuityStateValidationError, match="source request already succeeded with status SUCCESS"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req,
            replacement_capability=rep_cap,
            source_result=src_res_success,
            diagnosis_content_text=_valid_anchored_diagnosis_sample(),
            attestation=_valid_attestation(),
            worktree_root=tmp_path,
        )


def test_m3b_proof_runner_capability_missing_operation_rejected(tmp_path: Path):
    """Replacement Brain missing DIAGNOSIS capability fails closed."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap_incomplete = BrainCapability(brain_id="claude-chat", supported_operations=(BrainOperation.PLAN,))
    src_res = _valid_source_result(src_req)

    with pytest.raises(ContinuityStateValidationError, match="does not support operation 'DIAGNOSIS'"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req,
            replacement_capability=rep_cap_incomplete,
            source_result=src_res,
            diagnosis_content_text=_valid_anchored_diagnosis_sample(),
            attestation=_valid_attestation(),
            worktree_root=tmp_path,
        )


def test_m3b_proof_runner_oversize_diagnosis_rejected(tmp_path: Path):
    """Diagnosis artifact exceeding 16 KiB fails closed."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()
    src_res = _valid_source_result(src_req)
    huge_diag = _valid_anchored_diagnosis_sample() + ("\n# extra padding\n" + "x" * 20000)

    with pytest.raises(ContinuityStateValidationError, match="exceeds 16 KiB bound"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req,
            replacement_capability=rep_cap,
            source_result=src_res,
            diagnosis_content_text=huge_diag,
            attestation=_valid_attestation(),
            worktree_root=tmp_path,
        )


def test_m3b_proof_runner_same_brain_pseudo_failover_rejected():
    """Same brain_id pseudo-failover is rejected in replacement request derivation."""
    src_req = build_m3b_source_request()
    with pytest.raises(ContinuityStateValidationError, match="Same-Brain pseudo-failover rejected"):
        build_replacement_brain_request(src_req, "chatgpt-chat", "req-task-027-rep-01")


def test_m3b_proof_runner_semantic_drift_rejected(tmp_path: Path):
    """Any objective, operation, or context drift between source and replacement fails validation."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()
    src_res = _valid_source_result(src_req)

    # 1. Objective drift
    rep_req_drift = BrainRequest(
        schema_version="1",
        task_id=rep_req.task_id,
        request_id=rep_req.request_id,
        brain_id=rep_req.brain_id,
        operation=rep_req.operation,
        objective="Drifted objective that does not match source",
        output_contract=rep_req.output_contract,
        context_refs=rep_req.context_refs,
    )
    with pytest.raises(ContinuityStateValidationError, match="Objective drift in failover"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req_drift,
            replacement_capability=rep_cap,
            source_result=src_res,
            diagnosis_content_text=_valid_anchored_diagnosis_sample(),
            attestation=_valid_attestation(),
            worktree_root=tmp_path,
        )

    # 2. Context ref blob drift
    drifted_refs = list(rep_req.context_refs)
    drifted_refs[0] = ContextRef(path=drifted_refs[0].path, blob_sha="0" * 40)
    rep_req_context_drift = BrainRequest(
        schema_version="1",
        task_id=rep_req.task_id,
        request_id=rep_req.request_id,
        brain_id=rep_req.brain_id,
        operation=rep_req.operation,
        objective=rep_req.objective,
        output_contract=rep_req.output_contract,
        context_refs=tuple(drifted_refs),
    )
    with pytest.raises(ContinuityStateValidationError, match="ContextRefs drift in failover"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req_context_drift,
            replacement_capability=rep_cap,
            source_result=src_res,
            diagnosis_content_text=_valid_anchored_diagnosis_sample(),
            attestation=_valid_attestation(),
            worktree_root=tmp_path,
        )


def test_m3b_attestation_validation():
    """M3BLiveAttestation enforces strict schema, booleans, and forbids leaked transcript/secret fields (R1-4)."""
    valid = _valid_attestation()
    assert valid.to_dict()["distinct_real_brain_surfaces"] is True

    # 1. Unsafe boolean values fail closed
    with pytest.raises(ContinuityStateValidationError, match="distinct_real_brain_surfaces must be True"):
        M3BLiveAttestation.from_dict({**valid.to_dict(), "distinct_real_brain_surfaces": False})

    with pytest.raises(ContinuityStateValidationError, match="transcript_transferred must be False"):
        M3BLiveAttestation.from_dict({**valid.to_dict(), "transcript_transferred": True})

    with pytest.raises(ContinuityStateValidationError, match="chat_ui_automation must be False"):
        M3BLiveAttestation.from_dict({**valid.to_dict(), "chat_ui_automation": True})

    with pytest.raises(ContinuityStateValidationError, match="paid_external_api_calls must be exactly 0"):
        M3BLiveAttestation.from_dict({**valid.to_dict(), "paid_external_api_calls": 5})

    # 2. Forbidden keys fail closed
    for forbidden in ["transcript", "raw_prompt", "raw_response", "cookie", "token", "session", "cot", "reasoning"]:
        with pytest.raises(ContinuityStateValidationError, match="Forbidden transcript/secret fields"):
            M3BLiveAttestation.from_dict({**valid.to_dict(), forbidden: "leak"})

    # 3. Unknown keys fail closed
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in M3BLiveAttestation"):
        M3BLiveAttestation.from_dict({**valid.to_dict(), "unrecognized_custom_field": 123})


def test_diagnosis_semantic_anchors_validation():
    """validate_diagnosis_semantic_anchors enforces all 6 required semantic anchors (R1-3)."""
    full_sample = _valid_anchored_diagnosis_sample()
    validate_diagnosis_semantic_anchors(full_sample)

    # Missing anchor 1: state fingerprint
    missing_1 = full_sample.replace("Canonical state fingerprint", "Repository snapshot")
    with pytest.raises(ContinuityStateValidationError, match="anchor 1: canonical state fingerprint"):
        validate_diagnosis_semantic_anchors(missing_1)

    # Missing anchor 3: source success duplicate output blocking
    missing_3 = full_sample.replace("A source result with SUCCESS blocks duplicate competing outputs.", "")
    with pytest.raises(ContinuityStateValidationError, match="anchor 3: source SUCCESS duplicate"):
        validate_diagnosis_semantic_anchors(missing_3)

    # Missing anchor 4: zero transcript/reasoning isolation
    missing_4 = full_sample.replace("prior chat transcript, cookies, or hidden reasoning / chain-of-thought", "any external state")
    with pytest.raises(ContinuityStateValidationError, match="anchor 4: zero transcript/reasoning"):
        validate_diagnosis_semantic_anchors(missing_4)

    # Missing anchor 6: advisory role & unchanged human authority
    missing_6 = full_sample.replace("Brain remains strictly advisory; human authority for RUN, FIX, and MERGE remains unchanged.", "")
    with pytest.raises(ContinuityStateValidationError, match="anchor 6: advisory role and unchanged human authority"):
        validate_diagnosis_semantic_anchors(missing_6)
