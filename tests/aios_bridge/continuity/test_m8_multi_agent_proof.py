"""
Unit tests for M8 Real Multi-Agent Continuity Proof (TASK-032 / ADR-022).
Tests Brain boundary, Executor boundary, composite causal chain, scope isolation,
attestation sanitization, and deterministic verification.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import pytest

from scripts.aios_m8_multi_agent_continuity_proof import (
    compute_git_blob_sha,
    compute_sha256,
    normalize_line_endings,
    prepare_brain_pack,
    validate_m8_attestation,
    validate_m8_controlled_source_result,
    validate_m8_diagnosis_artifact,
    verify_brain_proof,
    verify_composite_chain,
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
    SCHEMA_VERSION,
)


@pytest.fixture
def sample_m8_valid_bundle(tmp_path: Path):
    """
    Creates a complete, valid M8 Brain proof bundle fixture in tmp_path.
    """
    s0_sha = "08508e48f6ffda70d1891dad461f6fd1b893b24b"
    task_ref = ArtifactRef(path=".ai/tasks/TASK-032.md", ref=s0_sha, blob_sha="a" * 40)
    adr_ref = ArtifactRef(path=".ai/decisions/ADR-022.md", ref=s0_sha, blob_sha="b" * 40)
    result_ref = ArtifactRef(path=".ai/results/RESULT-032.md", ref=s0_sha, blob_sha="c" * 40)

    state = ContinuityState(
        schema_version=SCHEMA_VERSION,
        task_id="TASK-032",
        phase=ContinuityPhase.READY_FOR_REVIEW,
        next_operation=NextOperation.REVIEW,
        main=BranchState(branch="main", sha=s0_sha),
        task_branch=BranchState(branch="ai/task-032", sha=s0_sha),
        artifacts=ContinuityArtifacts(
            task=task_ref,
            contracts=(adr_ref,),
            result=result_ref,
        ),
        brain=BrainState(last_id="chatgpt-chat", last_operation=BrainOperation.DIAGNOSIS),
        executor=ExecutorState(last_id="antigravity"),
    )
    state_fingerprint = state.fingerprint()

    context_refs = (
        ContextRef(path=".ai/tasks/TASK-032.md", blob_sha="a" * 40, description="Task contract"),
        ContextRef(path=".ai/decisions/ADR-022.md", blob_sha="b" * 40, description="ADR contract"),
    )

    output_contract = OutputContract(
        expected_output_type=BrainOutputType.DIAGNOSIS_ARTIFACT,
        target_artifact_path=".ai/context/proofs/TASK-032-M8/brain/BRAIN-DIAGNOSIS.md",
    )

    source_req = BrainRequest(
        schema_version="1",
        task_id="TASK-032",
        request_id="req-task-032-diag-001",
        brain_id="chatgpt-chat",
        operation=BrainOperation.DIAGNOSIS,
        objective="Independently diagnose whether S0 is safe",
        output_contract=output_contract,
        context_refs=context_refs,
    )

    repl_req = build_replacement_brain_request(
        source_req,
        replacement_brain_id="claude-chat",
        replacement_request_id="req-task-032-diag-002",
    )

    repl_cap = BrainCapability(
        brain_id="claude-chat",
        supported_operations=(BrainOperation.DIAGNOSIS, BrainOperation.PLAN),
    )

    source_res = BrainResult(
        schema_version="1",
        task_id="TASK-032",
        request_id="req-task-032-diag-001",
        brain_id="chatgpt-chat",
        operation=BrainOperation.DIAGNOSIS,
        status=BrainResultStatus.INCOMPLETE,
        output_type=BrainOutputType.DIAGNOSIS_ARTIFACT,
        error_code="M8-CONTROLLED-BRAIN-HANDOFF",
        artifact_ref=None,
        evidence_ref=None,
    )

    diag_text = """# Brain Diagnosis

## CAUSE
No blocking root cause found in S0 baseline.

## EVIDENCE
All contracts and test suites green.

## FIX
No source fix required.

## TESTS
755/755 repo tests passing.

## RISKS
Scope drift without strict verifier.
"""
    diag_norm = normalize_line_endings(diag_text)
    diag_blob = compute_git_blob_sha(diag_norm)

    repl_res = BrainResult(
        schema_version="1",
        task_id="TASK-032",
        request_id="req-task-032-diag-002",
        brain_id="claude-chat",
        operation=BrainOperation.DIAGNOSIS,
        status=BrainResultStatus.SUCCESS,
        output_type=BrainOutputType.DIAGNOSIS_ARTIFACT,
        error_code=None,
        artifact_ref=ArtifactRef(
            path=".ai/context/proofs/TASK-032-M8/brain/BRAIN-DIAGNOSIS.md",
            ref="ai-control",
            blob_sha=diag_blob,
        ),
        evidence_ref=None,
    )

    proof = BrainFailoverProof(
        schema_version="1",
        task_id="TASK-032",
        operation=BrainOperation.DIAGNOSIS,
        state_fingerprint=state_fingerprint,
        source_brain_id=source_req.brain_id,
        source_request_id=source_req.request_id,
        source_request_fingerprint=source_req.fingerprint(),
        source_result_status=BrainResultStatus.INCOMPLETE,
        replacement_brain_id=repl_req.brain_id,
        replacement_request_id=repl_req.request_id,
        replacement_request_fingerprint=repl_req.fingerprint(),
    )

    attestation = {
        "human_bounded_artifact_transfer": "YES",
        "human_bounded_artifact_transfer_bytes": len(diag_norm),
        "token_usage": "UNKNOWN",
    }

    (tmp_path / "canonical-state.json").write_text(state.to_canonical_json(), encoding="utf-8")
    (tmp_path / "source-request.json").write_text(source_req.to_canonical_json(), encoding="utf-8")
    (tmp_path / "replacement-request.json").write_text(repl_req.to_canonical_json(), encoding="utf-8")
    (tmp_path / "replacement-capability.json").write_text(json.dumps(repl_cap.to_dict(), indent=2), encoding="utf-8")
    (tmp_path / "source-result.json").write_text(source_res.to_canonical_json(), encoding="utf-8")
    (tmp_path / "replacement-result.json").write_text(repl_res.to_canonical_json(), encoding="utf-8")
    (tmp_path / "brain-failover-proof.json").write_text(proof.to_canonical_json(), encoding="utf-8")
    (tmp_path / "BRAIN-DIAGNOSIS.md").write_bytes(diag_norm)
    (tmp_path / "brain-proof-attestation.json").write_text(json.dumps(attestation), encoding="utf-8")

    return {
        "dir": tmp_path,
        "s0_sha": s0_sha,
        "state_fingerprint": state_fingerprint,
        "proof_fingerprint": proof.fingerprint(),
        "diag_blob": diag_blob,
    }


def test_m8_verify_brain_proof_success(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    res = verify_brain_proof(bundle["dir"])
    assert res["status"] == "PASS"
    assert res["state_fingerprint"] == bundle["state_fingerprint"]
    assert res["failover_proof_fingerprint"] == bundle["proof_fingerprint"]
    assert res["diagnosis_artifact_blob_sha"] == bundle["diag_blob"]


def test_m8_brain_proof_fails_on_same_source_and_replacement_actor(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    repl_req_path = bundle["dir"] / "replacement-request.json"
    req_data = json.loads(repl_req_path.read_text(encoding="utf-8"))
    req_data["brain_id"] = "chatgpt-chat"
    repl_req_path.write_text(json.dumps(req_data), encoding="utf-8")

    repl_res_path = bundle["dir"] / "replacement-result.json"
    res_data = json.loads(repl_res_path.read_text(encoding="utf-8"))
    res_data["brain_id"] = "chatgpt-chat"
    repl_res_path.write_text(json.dumps(res_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="Replacement brain_id must differ|Same-Brain pseudo-failover rejected"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_source_success_instead_of_controlled_non_success(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    src_res_path = bundle["dir"] / "source-result.json"
    res_data = json.loads(src_res_path.read_text(encoding="utf-8"))
    res_data["status"] = "SUCCESS"
    res_data["error_code"] = None
    res_data["artifact_ref"] = {
        "path": ".ai/context/proofs/TASK-032-M8/brain/BRAIN-DIAGNOSIS.md",
        "ref": "ai-control",
        "blob_sha": bundle["diag_blob"],
    }
    src_res_path.write_text(json.dumps(res_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="requires source result status INCOMPLETE"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_missing_diagnosis_section(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    diag_path = bundle["dir"] / "BRAIN-DIAGNOSIS.md"
    diag_path.write_text("## CAUSE\nNo cause\n## FIX\nNo fix\n", encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="missing required section: 'EVIDENCE'"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_diagnosis_blob_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    repl_res_path = bundle["dir"] / "replacement-result.json"
    res_data = json.loads(repl_res_path.read_text(encoding="utf-8"))
    res_data["artifact_ref"]["blob_sha"] = "0" * 40
    repl_res_path.write_text(json.dumps(res_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="artifact blob mismatch"):
        verify_brain_proof(bundle["dir"])


def test_m8_attestation_rejects_forbidden_keys(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    att_path = bundle["dir"] / "brain-proof-attestation.json"
    att_data = json.loads(att_path.read_text(encoding="utf-8"))
    att_data["transcript"] = "some user chat history"
    att_path.write_text(json.dumps(att_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="forbidden key: 'transcript'"):
        verify_brain_proof(bundle["dir"])


def test_m8_attestation_rejects_invalid_token_usage_format():
    with pytest.raises(ContinuityStateValidationError, match="token_usage format invalid"):
        validate_m8_attestation({"token_usage": "1500 tokens used"})


def test_m8_composite_chain_verification_success(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    s0 = bundle["s0_sha"]
    s1 = "1" * 40

    review_text = f"""# REVIEW-032
STATUS: CHANGES_REQUIRED
M8_SOURCE_EXECUTOR_PUBLISHED_SHA: {s0}
M8_BRAIN_SOURCE_ID: chatgpt-chat
M8_BRAIN_REPLACEMENT_ID: claude-chat
M8_BRAIN_FAILOVER_PROOF_FINGERPRINT: {bundle['proof_fingerprint']}
M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA: {bundle['diag_blob']}
M8_CANONICAL_STATE_FINGERPRINT: {bundle['state_fingerprint']}
"""
    rev_blob = compute_git_blob_sha(normalize_line_endings(review_text))

    s1_result_text = f"""# RESULT-032
EXECUTOR_FAILOVER: YES
FAILOVER_SOURCE_PUBLISHED_SHA: {s0}
FAILOVER_REVIEW_BLOB_SHA: {rev_blob}
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF: PASS
M8_COMPOSITE_CHAIN: PASS
"""

    res = verify_composite_chain(
        s0_sha=s0,
        review_content=review_text,
        proof_dir=bundle["dir"],
        s1_sha=s1,
        s1_result_content=s1_result_text,
    )
    assert res["status"] == "PASS"
    assert res["s0_sha"] == s0
    assert res["s1_sha"] == s1
    assert res["review_blob_sha"] == rev_blob


def test_m8_composite_chain_fails_on_review_fingerprint_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    s0 = bundle["s0_sha"]

    review_text = f"""# REVIEW-032
STATUS: CHANGES_REQUIRED
M8_SOURCE_EXECUTOR_PUBLISHED_SHA: {s0}
M8_BRAIN_SOURCE_ID: chatgpt-chat
M8_BRAIN_REPLACEMENT_ID: claude-chat
M8_BRAIN_FAILOVER_PROOF_FINGERPRINT: {'f' * 64}
M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA: {bundle['diag_blob']}
M8_CANONICAL_STATE_FINGERPRINT: {bundle['state_fingerprint']}
"""
    with pytest.raises(ContinuityStateValidationError, match="provenance mismatch for 'M8_BRAIN_FAILOVER_PROOF_FINGERPRINT'"):
        verify_composite_chain(
            s0_sha=s0,
            review_content=review_text,
            proof_dir=bundle["dir"],
        )


def test_m8_brain_proof_fails_on_proof_state_fingerprint_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    proof_path = bundle["dir"] / "brain-failover-proof.json"
    p_data = json.loads(proof_path.read_text(encoding="utf-8"))
    p_data["state_fingerprint"] = "0" * 64
    proof_path.write_text(json.dumps(p_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="BrainFailoverProof state_fingerprint mismatch"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_proof_source_request_fingerprint_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    proof_path = bundle["dir"] / "brain-failover-proof.json"
    p_data = json.loads(proof_path.read_text(encoding="utf-8"))
    p_data["source_request_fingerprint"] = "0" * 64
    proof_path.write_text(json.dumps(p_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="BrainFailoverProof source_request_fingerprint mismatch"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_proof_replacement_request_fingerprint_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    proof_path = bundle["dir"] / "brain-failover-proof.json"
    p_data = json.loads(proof_path.read_text(encoding="utf-8"))
    p_data["replacement_request_fingerprint"] = "0" * 64
    proof_path.write_text(json.dumps(p_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="BrainFailoverProof replacement_request_fingerprint mismatch"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_replacement_result_task_id_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    repl_res_path = bundle["dir"] / "replacement-result.json"
    res_data = json.loads(repl_res_path.read_text(encoding="utf-8"))
    res_data["task_id"] = "TASK-999"
    res_data["artifact_ref"]["path"] = ".ai/context/proofs/TASK-999-M8/brain/BRAIN-DIAGNOSIS.md"
    repl_res_path.write_text(json.dumps(res_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="Replacement result task_id mismatch"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_replacement_result_operation_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    repl_res_path = bundle["dir"] / "replacement-result.json"
    res_data = json.loads(repl_res_path.read_text(encoding="utf-8"))
    res_data["operation"] = "PLAN"
    res_data["output_type"] = "PLAN_ARTIFACT"
    res_data["artifact_ref"]["path"] = ".ai/plans/TASK-032-PLAN.md"
    repl_res_path.write_text(json.dumps(res_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="Replacement result operation mismatch"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_replacement_result_output_type_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    repl_res_path = bundle["dir"] / "replacement-result.json"
    res_data = json.loads(repl_res_path.read_text(encoding="utf-8"))
    res_data["output_type"] = "BOUNDED_TEXT"
    res_data["artifact_ref"] = None
    res_data["evidence_ref"] = {"path": ".ai/context/proofs/TASK-032-M8/brain/BRAIN-DIAGNOSIS.md"}
    repl_res_path.write_text(json.dumps(res_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="Replacement result output_type mismatch"):
        verify_brain_proof(bundle["dir"])


def test_m8_brain_proof_fails_on_replacement_result_artifact_path_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    repl_res_path = bundle["dir"] / "replacement-result.json"
    res_data = json.loads(repl_res_path.read_text(encoding="utf-8"))
    res_data["artifact_ref"]["path"] = ".ai/context/proofs/TASK-032-M8/brain/OTHER-DIAGNOSIS-TASK-032.md"
    repl_res_path.write_text(json.dumps(res_data), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="Replacement result artifact path mismatch"):
        verify_brain_proof(bundle["dir"])


def test_prepare_brain_pack_fails_on_invalid_or_missing_s0_commit(tmp_path: Path):
    with pytest.raises(ContinuityStateValidationError, match="must be a 40-hex lowercase string"):
        prepare_brain_pack(
            repo_dir=Path("."),
            output_dir=tmp_path / "pack",
            source_published_sha="invalid-sha",
        )

    with pytest.raises(ContinuityStateValidationError, match="does not exist as a commit"):
        prepare_brain_pack(
            repo_dir=Path("."),
            output_dir=tmp_path / "pack",
            source_published_sha="f" * 40,
        )


def test_prepare_brain_pack_success_on_real_head(tmp_path: Path):
    p_head = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
    head_sha = p_head.stdout.strip()

    res = prepare_brain_pack(
        repo_dir=Path("."),
        output_dir=tmp_path / "pack",
        source_published_sha=head_sha,
    )
    assert res["task_id"] == "TASK-032"
    assert res["source_published_sha"] == head_sha
    assert (tmp_path / "pack" / "canonical-state.json").exists()
    assert (tmp_path / "pack" / "source-request.json").exists()
    assert (tmp_path / "pack" / "replacement-request.json").exists()
    assert (tmp_path / "pack" / "replacement-capability.json").exists()
    assert (tmp_path / "pack" / "BRAIN_PROMPT.md").exists()


def test_m8_composite_chain_fails_on_s1_review_blob_mismatch(sample_m8_valid_bundle):
    bundle = sample_m8_valid_bundle
    s0 = bundle["s0_sha"]

    review_text = f"""# REVIEW-032
STATUS: CHANGES_REQUIRED
M8_SOURCE_EXECUTOR_PUBLISHED_SHA: {s0}
M8_BRAIN_SOURCE_ID: chatgpt-chat
M8_BRAIN_REPLACEMENT_ID: claude-chat
M8_BRAIN_FAILOVER_PROOF_FINGERPRINT: {bundle['proof_fingerprint']}
M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA: {bundle['diag_blob']}
M8_CANONICAL_STATE_FINGERPRINT: {bundle['state_fingerprint']}
"""
    s1_result_text = f"""# RESULT-032
EXECUTOR_FAILOVER: YES
FAILOVER_SOURCE_PUBLISHED_SHA: {s0}
FAILOVER_REVIEW_BLOB_SHA: {'0' * 40}
M8_BRAIN_PROOF: PASS
M8_EXECUTOR_PROOF: PASS
M8_COMPOSITE_CHAIN: PASS
"""
    with pytest.raises(ContinuityStateValidationError, match="S1 RESULT-032 mismatch for 'FAILOVER_REVIEW_BLOB_SHA'"):
        verify_composite_chain(
            s0_sha=s0,
            review_content=review_text,
            proof_dir=bundle["dir"],
            s1_sha="1" * 40,
            s1_result_content=s1_result_text,
        )
