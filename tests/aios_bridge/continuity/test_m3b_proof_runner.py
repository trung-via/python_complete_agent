"""Unit tests for TASK-027 M3B Cross-Brain Proof Runner (ADR-016 / ADR-017 / REVIEW-027 R1-1..R3-2)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.aios_m3b_cross_brain_proof import (
    DOWNSTREAM_PROOF_ARTIFACTS,
    REPO_DIR,
    M3BLiveAttestation,
    audit_persisted_bundle,
    build_m3b_proof_state,
    build_m3b_replacement_capability,
    build_m3b_source_request,
    command_prepare_source,
    command_validate_source,
    command_verify_replacement,
    compute_git_blob_sha,
    normalize_line_endings,
    validate_diagnosis_semantic_anchors,
    validate_m3b_controlled_source_result,
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
        "3. A source result with SUCCESS blocks duplicate competing outputs fail-closed.\n"
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
    # Snapshot real repository target before test to ensure it remains untouched
    real_target = REPO_DIR / ".ai" / "diagnosis" / "TASK-027-M3B-DIAGNOSIS.md"
    real_target_exists = real_target.exists()
    real_target_bytes = real_target.read_bytes() if real_target_exists else None

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
    norm_diag_bytes = normalize_line_endings(diag_text)
    assert summary["diagnosis_blob_sha"] == compute_git_blob_sha(norm_diag_bytes)

    # Verify isolated file written under tmp_path
    isolated_diag = tmp_path / ".ai" / "diagnosis" / "TASK-027-M3B-DIAGNOSIS.md"
    assert isolated_diag.exists()
    assert isolated_diag.read_bytes() == norm_diag_bytes

    # Regression assertion: real repository file was NOT touched (R1-2)
    if real_target_exists:
        assert real_target.exists()
        assert real_target.read_bytes() == real_target_bytes

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

    # Non-mutating audit passes on this bundle
    audit_res = audit_persisted_bundle(proofs_dir=output_proofs_dir, worktree_root=tmp_path)
    assert audit_res["status"] == "PASS"


def test_m3b_controlled_source_result_validation(tmp_path: Path):
    """TASK-027 controlled source result mode is strictly enforced (R3-1)."""
    src_req = build_m3b_source_request()

    # Valid controlled source result
    valid = _valid_source_result(src_req)
    validate_m3b_controlled_source_result(valid)

    # 1. Invalid statuses
    for bad_status in [BrainResultStatus.FAILED, BrainResultStatus.REJECTED, BrainResultStatus.SUCCESS]:
        bad_res = BrainResult(
            schema_version="1",
            task_id=src_req.task_id,
            request_id=src_req.request_id,
            brain_id=src_req.brain_id,
            operation=src_req.operation,
            status=bad_status,
            output_type=src_req.output_contract.expected_output_type,
            error_code="M3B-CONTROLLED-HANDOFF" if bad_status != BrainResultStatus.SUCCESS else None,
            artifact_ref=ArtifactRef(path=".ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md", ref="ai/task-027", blob_sha="1" * 40) if bad_status == BrainResultStatus.SUCCESS else None,
        )
        with pytest.raises(ContinuityStateValidationError, match="TASK-027 requires source result status INCOMPLETE"):
            validate_m3b_controlled_source_result(bad_res)

    # 2. Wrong error code
    bad_code = BrainResult(
        schema_version="1",
        task_id=src_req.task_id,
        request_id=src_req.request_id,
        brain_id=src_req.brain_id,
        operation=src_req.operation,
        status=BrainResultStatus.INCOMPLETE,
        output_type=src_req.output_contract.expected_output_type,
        error_code="OTHER-ERROR",
    )
    with pytest.raises(ContinuityStateValidationError, match="requires error_code 'M3B-CONTROLLED-HANDOFF'"):
        validate_m3b_controlled_source_result(bad_code)

    # 3. Present artifact_ref or evidence_ref
    bad_artifact = BrainResult(
        schema_version="1",
        task_id=src_req.task_id,
        request_id=src_req.request_id,
        brain_id=src_req.brain_id,
        operation=src_req.operation,
        status=BrainResultStatus.INCOMPLETE,
        output_type=src_req.output_contract.expected_output_type,
        error_code="M3B-CONTROLLED-HANDOFF",
        artifact_ref=ArtifactRef(path=".ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md", ref="ai/task-027", blob_sha="1" * 40),
    )
    with pytest.raises(ContinuityStateValidationError, match="must not contain artifact_ref"):
        validate_m3b_controlled_source_result(bad_artifact)


def test_prepare_source_purges_stale_downstream_artifacts(tmp_path: Path):
    """prepare-source removes any pre-existing downstream Stage 2/3 artifacts (R1-1 A)."""
    proofs_dir = tmp_path / "proofs"
    proofs_dir.mkdir(parents=True, exist_ok=True)

    # Populate stale downstream artifacts
    for art in DOWNSTREAM_PROOF_ARTIFACTS:
        (proofs_dir / art).write_text("stale content", encoding="utf-8")

    assert command_prepare_source(proofs_dir) == 0

    # Ensure Stage 1 artifacts exist
    assert (proofs_dir / "TASK-027-M3B-STATE.json").exists()
    assert (proofs_dir / "TASK-027-M3B-SOURCE-REQUEST.json").exists()

    # Ensure ALL downstream artifacts were wiped clean
    for art in DOWNSTREAM_PROOF_ARTIFACTS:
        assert not (proofs_dir / art).exists(), f"Stale artifact not purged: {art}"


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
    """M3BLiveAttestation enforces strict schema, booleans, token grammar, and size limits (R1-4)."""
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

    # 4. Token usage safe grammar (R1-4)
    # Valid forms:
    M3BLiveAttestation.from_dict({**valid.to_dict(), "source_brain_token_usage": "UNKNOWN"})
    M3BLiveAttestation.from_dict({**valid.to_dict(), "replacement_brain_token_usage": "REPORTED(prompt_tokens: 100, completion_tokens: 50)"})

    # Invalid forms:
    with pytest.raises(ContinuityStateValidationError, match="source_brain_token_usage must match safe grammar"):
        M3BLiveAttestation.from_dict({**valid.to_dict(), "source_brain_token_usage": "leak secret key or arbitrary text"})

    with pytest.raises(ContinuityStateValidationError, match="replacement_brain_token_usage must match safe grammar"):
        M3BLiveAttestation.from_dict({**valid.to_dict(), "replacement_brain_token_usage": "REPORTED(" + "x" * 200 + ")"})

    # 5. Oversized attestation payload (> 16 KiB) (R1-4)
    with pytest.raises(ContinuityStateValidationError, match="must be an integer between 1 and"):
        M3BLiveAttestation.from_dict({**valid.to_dict(), "human_bounded_transfer_bytes": 20000})


def test_m3b_attestation_brain_id_cross_binding(tmp_path: Path):
    """Attestation source and replacement Brain IDs must cross-bind to request Brain IDs (R1-4)."""
    state = build_m3b_proof_state()
    src_req = build_m3b_source_request()
    rep_req = build_replacement_brain_request(src_req, "claude-chat", "req-task-027-rep-01")
    rep_cap = build_m3b_replacement_capability()
    src_res = _valid_source_result(src_req)

    # 1. Attestation has wrong source brain ID
    att_wrong_src = _valid_attestation(source_brain="gpt-4o", rep_brain="claude-chat")
    with pytest.raises(ContinuityStateValidationError, match="Attestation source_brain_id 'gpt-4o' != source_request.brain_id 'chatgpt-chat'"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req,
            replacement_capability=rep_cap,
            source_result=src_res,
            diagnosis_content_text=_valid_anchored_diagnosis_sample(),
            attestation=att_wrong_src,
            worktree_root=tmp_path,
        )

    # 2. Attestation has wrong replacement brain ID
    att_wrong_rep = _valid_attestation(source_brain="chatgpt-chat", rep_brain="gemini-pro")
    with pytest.raises(ContinuityStateValidationError, match="Attestation replacement_brain_id 'gemini-pro' != replacement_request.brain_id 'claude-chat'"):
        verify_and_bind_m3b_proof(
            state=state,
            source_request=src_req,
            replacement_request=rep_req,
            replacement_capability=rep_cap,
            source_result=src_res,
            diagnosis_content_text=_valid_anchored_diagnosis_sample(),
            attestation=att_wrong_rep,
            worktree_root=tmp_path,
        )


def test_diagnosis_semantic_anchors_validation():
    """validate_diagnosis_semantic_anchors enforces all 6 required semantic anchors (R1-3)."""
    full_sample = _valid_anchored_diagnosis_sample()
    validate_diagnosis_semantic_anchors(full_sample)

    # Missing anchor 1: state fingerprint
    missing_1 = full_sample.replace("Canonical state fingerprint", "Repository snapshot")
    with pytest.raises(ContinuityStateValidationError, match="anchor 1: canonical state fingerprint"):
        validate_diagnosis_semantic_anchors(missing_1)

    # Missing anchor 3: source success duplicate output blocking
    missing_3 = full_sample.replace("A source result with SUCCESS blocks duplicate competing outputs fail-closed.", "")
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


def test_deterministic_newline_only_normalization():
    """normalize_line_endings converts CRLF/CR to LF without stripping leading/trailing whitespace (R2-1)."""
    raw_with_spaces = "  leading spaces\r\n\ttab indented\rline with trailing spaces  \r\n"
    norm_bytes = normalize_line_endings(raw_with_spaces)
    norm_text = norm_bytes.decode("utf-8")

    assert "\r" not in norm_text
    assert norm_text.endswith("\n")
    # Verify spaces and tabs were preserved byte-for-byte on the lines
    assert norm_text.startswith("  leading spaces\n")
    assert "\ttab indented\n" in norm_text
    assert "line with trailing spaces  \n" in norm_text


def test_staged_lifecycle_commands_and_immutable_binding(tmp_path: Path):
    """Test staged lifecycle and immutable Stage-2 proof receipt binding (R1-1, R1-2, R3-1)."""
    proofs_dir = tmp_path / "proofs"

    # 1. Stage 1: prepare-source
    assert command_prepare_source(proofs_dir) == 0
    assert (proofs_dir / "TASK-027-M3B-STATE.json").exists()
    assert (proofs_dir / "TASK-027-M3B-SOURCE-REQUEST.json").exists()
    # Ensure replacement artifacts are NOT yet created
    assert not (proofs_dir / "TASK-027-M3B-REPLACEMENT-REQUEST.json").exists()

    # 2. Negative test: Source SUCCESS fails validate-source and blocks replacement emission
    src_req = build_m3b_source_request()
    src_res_success = BrainResult(
        schema_version="1",
        task_id=src_req.task_id,
        request_id=src_req.request_id,
        brain_id=src_req.brain_id,
        operation=src_req.operation,
        status=BrainResultStatus.SUCCESS,
        output_type=BrainOutputType.DIAGNOSIS_ARTIFACT,
        artifact_ref=ArtifactRef(path=".ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md", ref="ai/task-027", blob_sha="2" * 40),
    )
    src_res_succ_file = tmp_path / "src_res_success.json"
    src_res_succ_file.write_text(src_res_success.to_canonical_json(), encoding="utf-8")

    with pytest.raises(ContinuityStateValidationError, match="TASK-027 requires source result status INCOMPLETE"):
        command_validate_source(src_res_succ_file, proofs_dir)

    # 3. Stage 2: validate-source with valid controlled INCOMPLETE result
    src_res_valid = _valid_source_result(src_req)
    src_res_file = tmp_path / "src_res_valid.json"
    src_res_file.write_text(src_res_valid.to_canonical_json(), encoding="utf-8")

    assert command_validate_source(src_res_file, proofs_dir) == 0
    assert (proofs_dir / "TASK-027-M3B-REPLACEMENT-REQUEST.json").exists()
    assert (proofs_dir / "TASK-027-M3B-REPLACEMENT-CAPABILITY.json").exists()
    assert (proofs_dir / "TASK-027-M3B-FAILOVER-PROOF.json").exists()

    # 4. Stage 3: verify-replacement
    diag_file = tmp_path / "incoming_diag.md"
    diag_file.write_text(_valid_anchored_diagnosis_sample(), encoding="utf-8")
    att_file = tmp_path / "attestation.json"
    att_file.write_text(json.dumps(_valid_attestation().to_dict()), encoding="utf-8")

    assert command_verify_replacement(
        diagnosis_path=diag_file,
        attestation_path=att_file,
        output_dir=proofs_dir,
        worktree_root=tmp_path,
    ) == 0

    # 5. Non-mutating audit passes
    audit_res = audit_persisted_bundle(proofs_dir=proofs_dir, worktree_root=tmp_path)
    assert audit_res["status"] == "PASS"


def test_audit_persisted_bundle_full_cross_binding_negative(tmp_path: Path):
    """audit_persisted_bundle fails closed on any structural drift in replacement BrainResult (R3-2)."""
    proofs_dir = tmp_path / "proofs"
    assert command_prepare_source(proofs_dir) == 0
    src_req = build_m3b_source_request()
    src_res_file = tmp_path / "src_res.json"
    src_res_file.write_text(_valid_source_result(src_req).to_canonical_json(), encoding="utf-8")
    assert command_validate_source(src_res_file, proofs_dir) == 0

    diag_file = tmp_path / "diag.md"
    diag_file.write_text(_valid_anchored_diagnosis_sample(), encoding="utf-8")
    att_file = tmp_path / "att.json"
    att_file.write_text(json.dumps(_valid_attestation().to_dict()), encoding="utf-8")

    assert command_verify_replacement(
        diagnosis_path=diag_file,
        attestation_path=att_file,
        output_dir=proofs_dir,
        worktree_root=tmp_path,
    ) == 0

    # 1. Corrupt persisted diagnosis on disk with valid semantic anchors but mismatched bytes -> audit fails
    target_diag = tmp_path / ".ai" / "diagnosis" / "TASK-027-M3B-DIAGNOSIS.md"
    orig_diag_bytes = target_diag.read_bytes()
    target_diag.write_bytes(orig_diag_bytes + b"\n# extra line\n")
    with pytest.raises(ContinuityStateValidationError, match="Persisted replacement result does not match expected"):
        audit_persisted_bundle(proofs_dir=proofs_dir, worktree_root=tmp_path)

    # Restore diagnosis
    target_diag.write_bytes(orig_diag_bytes)
    assert audit_persisted_bundle(proofs_dir=proofs_dir, worktree_root=tmp_path)["status"] == "PASS"

    rep_res_file = proofs_dir / "TASK-027-M3B-REPLACEMENT-RESULT.json"
    orig_rep_res_data = json.loads(rep_res_file.read_text(encoding="utf-8"))

    # 2. Corrupt replacement result request_id -> audit fails (R3-2)
    rep_res_corrupt_req = dict(orig_rep_res_data)
    rep_res_corrupt_req["request_id"] = "req-task-027-drifted"
    rep_res_file.write_text(json.dumps(rep_res_corrupt_req), encoding="utf-8")
    with pytest.raises(ContinuityStateValidationError, match="Persisted replacement result does not match expected"):
        audit_persisted_bundle(proofs_dir=proofs_dir, worktree_root=tmp_path)

    # 3. Corrupt replacement result brain_id -> audit fails (R3-2)
    rep_res_corrupt_brain = dict(orig_rep_res_data)
    rep_res_corrupt_brain["brain_id"] = "gemini-chat"
    rep_res_file.write_text(json.dumps(rep_res_corrupt_brain), encoding="utf-8")
    with pytest.raises(ContinuityStateValidationError, match="Persisted replacement result does not match expected"):
        audit_persisted_bundle(proofs_dir=proofs_dir, worktree_root=tmp_path)

    # 4. Corrupt replacement result artifact_ref.ref -> audit fails (R3-2)
    rep_res_corrupt_ref = dict(orig_rep_res_data)
    rep_res_corrupt_ref["artifact_ref"] = dict(orig_rep_res_data["artifact_ref"])
    rep_res_corrupt_ref["artifact_ref"]["ref"] = "main"
    rep_res_file.write_text(json.dumps(rep_res_corrupt_ref), encoding="utf-8")
    with pytest.raises(ContinuityStateValidationError, match="Persisted replacement result does not match expected"):
        audit_persisted_bundle(proofs_dir=proofs_dir, worktree_root=tmp_path)
