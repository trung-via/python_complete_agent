"""Unit tests for TASK-027 M3B Cross-Brain Proof Runner."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.aios_m3b_cross_brain_proof import (
    build_m3b_controlled_source_result,
    build_m3b_proof_state,
    build_m3b_replacement_capability,
    build_m3b_source_request,
    compute_git_blob_sha,
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


def _valid_diagnosis_sample() -> str:
    return (
        "# DIAGNOSIS\n\n"
        "## CAUSE\nCross-brain failover required.\n\n"
        "## EVIDENCE\nADR-010 and ADR-016 invariants.\n\n"
        "## FIX\nApply deterministic failover rules.\n\n"
        "## TESTS\nRun pytest suites.\n\n"
        "## RISKS\nNone.\n"
    )


def test_m3b_proof_runner_success_end_to_end(tmp_path: Path):
    """M3B proof runner executes cleanly and persists deterministic evidence artifacts."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()
    src_res = build_m3b_controlled_source_result(src_req)
    diag_text = _valid_diagnosis_sample()

    summary = verify_and_bind_m3b_proof(
        state=state,
        source_request=src_req,
        replacement_request=rep_req,
        replacement_capability=rep_cap,
        source_result=src_res,
        diagnosis_content_text=diag_text,
        output_dir=tmp_path,
    )

    assert len(summary["failover_proof_fingerprint"]) == 64
    assert len(summary["diagnosis_blob_sha"]) == 40
    assert summary["diagnosis_blob_sha"] == compute_git_blob_sha(diag_text.encode("utf-8"))

    # Verify persisted artifacts
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
        art_file = tmp_path / art_name
        assert art_file.exists(), f"Missing artifact: {art_name}"
        assert art_file.stat().st_size <= 16384


def test_m3b_proof_runner_source_success_rejected():
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
            diagnosis_content_text=_valid_diagnosis_sample(),
        )


def test_m3b_proof_runner_capability_missing_operation_rejected():
    """Replacement Brain missing DIAGNOSIS capability fails closed."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap_incomplete = BrainCapability(brain_id="claude-chat", supported_operations=(BrainOperation.PLAN,))
    src_res = build_m3b_controlled_source_result(src_req)

    with pytest.raises(ContinuityStateValidationError, match="does not support operation 'DIAGNOSIS'"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req,
            replacement_capability=rep_cap_incomplete,
            source_result=src_res,
            diagnosis_content_text=_valid_diagnosis_sample(),
        )


def test_m3b_proof_runner_oversize_diagnosis_rejected():
    """Diagnosis artifact exceeding 16 KiB fails closed."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()
    src_res = build_m3b_controlled_source_result(src_req)
    huge_diag = "x" * 20000

    with pytest.raises(ContinuityStateValidationError, match="exceeds 16 KiB bound"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req,
            replacement_capability=rep_cap,
            source_result=src_res,
            diagnosis_content_text=huge_diag,
        )


def test_m3b_proof_runner_same_brain_pseudo_failover_rejected():
    """Same brain_id pseudo-failover is rejected in replacement request derivation."""
    src_req = build_m3b_source_request()
    with pytest.raises(ContinuityStateValidationError, match="Same-Brain pseudo-failover rejected"):
        build_replacement_brain_request(src_req, "chatgpt-chat", "req-task-027-rep-01")


def test_m3b_proof_runner_semantic_drift_rejected():
    """Any objective, operation, or context drift between source and replacement fails validation."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()
    src_res = build_m3b_controlled_source_result(src_req)

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
            diagnosis_content_text=_valid_diagnosis_sample(),
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
            diagnosis_content_text=_valid_diagnosis_sample(),
        )

