"""Comprehensive test suite for AIOS Brain-Neutral Contract (ADR-010 M2 / TASK-023 Hardening)."""
from __future__ import annotations

import json
import pytest

from src.aios_bridge.continuity import (
    ArtifactRef,
    BrainCapability,
    BrainOperation,
    BrainOutputType,
    BrainRequest,
    BrainResult,
    BrainResultStatus,
    ContextRef,
    ContinuityStateValidationError,
    OPERATION_OUTPUT_TYPE_COMPATIBILITY,
    OutputContract,
)
from src.aios_bridge.continuity.brain import MAX_BRAIN_CAPACITY_CONTEXT_BYTES


def _make_valid_brain_request_dict() -> dict:
    """Returns a valid dictionary representation of a BrainRequest."""
    return {
        "schema_version": "1",
        "task_id": "TASK-021",
        "request_id": "req-task-021-task-and-plan-r1",
        "brain_id": "chatgpt-chat",
        "operation": "TASK_AND_PLAN",
        "objective": "Design and author TASK-021 contract and implementation plan",
        "context_refs": [
            {
                "path": ".ai/decisions/ADR-010-OPEN-MULTI-AGENT-CONTINUITY-OS-ARCHITECTURE-LOCK.md",
                "blob_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
                "description": "Continuity OS architecture lock",
            },
            {
                "path": ".ai/tasks/TASK-021.md",
                "blob_sha": None,
                "description": "Task definition",
            },
        ],
        "output_contract": {
            "expected_output_type": "TASK_ARTIFACT",
            "target_artifact_path": ".ai/tasks/TASK-021.md",
            "max_output_bytes": 16384,
        },
    }


def _make_valid_brain_result_dict() -> dict:
    """Returns a valid dictionary representation of a BrainResult."""
    return {
        "schema_version": "1",
        "task_id": "TASK-021",
        "request_id": "req-task-021-task-and-plan-r1",
        "brain_id": "chatgpt-chat",
        "operation": "TASK_AND_PLAN",
        "status": "SUCCESS",
        "output_type": "TASK_ARTIFACT",
        "artifact_ref": {
            "path": ".ai/tasks/TASK-021.md",
            "blob_sha": "3ca21b58663c2de99ee2f16d16e2203ec77d0558",
            "ref": "task",
        },
        "evidence_ref": None,
        "error_code": None,
    }


def test_valid_neutral_brain_request_and_result_round_trip():
    """Valid BrainRequest and BrainResult parse and preserve all attributes accurately."""
    req_dict = _make_valid_brain_request_dict()
    req = BrainRequest.from_dict(req_dict)

    assert req.schema_version == "1"
    assert req.task_id == "TASK-021"
    assert req.request_id == "req-task-021-task-and-plan-r1"
    assert req.brain_id == "chatgpt-chat"
    assert req.operation == BrainOperation.TASK_AND_PLAN
    assert len(req.context_refs) == 2
    assert req.context_refs[0].path == ".ai/decisions/ADR-010-OPEN-MULTI-AGENT-CONTINUITY-OS-ARCHITECTURE-LOCK.md"
    assert req.output_contract.expected_output_type == BrainOutputType.TASK_ARTIFACT

    res_dict = _make_valid_brain_result_dict()
    res = BrainResult.from_dict(res_dict)

    assert res.schema_version == "1"
    assert res.task_id == "TASK-021"
    assert res.brain_id == "chatgpt-chat"
    assert res.status == BrainResultStatus.SUCCESS
    assert res.artifact_ref is not None
    assert res.artifact_ref.path == ".ai/tasks/TASK-021.md"


def test_deterministic_canonical_json_and_fingerprint():
    """Canonical JSON serialization and fingerprints are stable and identical across round-trips."""
    req_dict = _make_valid_brain_request_dict()
    r1 = BrainRequest.from_dict(req_dict)
    json1 = r1.to_canonical_json()
    fp1 = r1.fingerprint()

    r2 = BrainRequest.from_json(json1)
    json2 = r2.to_canonical_json()
    fp2 = r2.fingerprint()

    assert json1 == json2
    assert fp1 == fp2
    assert len(fp1) == 64

    res_dict = _make_valid_brain_result_dict()
    res1 = BrainResult.from_dict(res_dict)
    res_json1 = res1.to_canonical_json()
    res_fp1 = res1.fingerprint()

    res2 = BrainResult.from_json(res_json1)
    res_json2 = res2.to_canonical_json()
    res_fp2 = res2.fingerprint()

    assert res_json1 == res_json2
    assert res_fp1 == res_fp2
    assert len(res_fp1) == 64


def test_strict_task_identity_validation():
    """Task ID must be exact case-sensitive ^TASK-\\d+$."""
    d = _make_valid_brain_request_dict()
    d["task_id"] = "task-021"
    with pytest.raises(ContinuityStateValidationError, match="case-sensitive"):
        BrainRequest.from_dict(d)

    d_num = _make_valid_brain_request_dict()
    d_num["task_id"] = 21
    with pytest.raises(ContinuityStateValidationError, match="must be a non-empty string"):
        BrainRequest.from_dict(d_num)


def test_actor_and_request_id_validation():
    """Actor ID and request ID must be exact canonical without whitespace padding (C1 / Checklist 1-3)."""
    d_bad_actor = _make_valid_brain_request_dict()
    d_bad_actor["brain_id"] = "Claude_3.5_Sonnet"
    with pytest.raises(ContinuityStateValidationError, match="conservative lowercase identifier"):
        BrainRequest.from_dict(d_bad_actor)

    # Leading / trailing whitespace in brain_id fails closed
    for padded in [" chatgpt-chat", "chatgpt-chat ", "  chatgpt-chat  "]:
        d_pad_actor = _make_valid_brain_request_dict()
        d_pad_actor["brain_id"] = padded
        with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
            BrainRequest.from_dict(d_pad_actor)

        res_pad_actor = _make_valid_brain_result_dict()
        res_pad_actor["brain_id"] = padded
        with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
            BrainResult.from_dict(res_pad_actor)

    d_bad_req = _make_valid_brain_request_dict()
    d_bad_req["request_id"] = "bad request ID with spaces"
    with pytest.raises(ContinuityStateValidationError, match="conservative lowercase identifier"):
        BrainRequest.from_dict(d_bad_req)

    # Leading / trailing whitespace in request_id fails closed
    for padded in [" req-task-021-r1", "req-task-021-r1 ", " req-task-021-r1 "]:
        d_pad_req = _make_valid_brain_request_dict()
        d_pad_req["request_id"] = padded
        with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
            BrainRequest.from_dict(d_pad_req)

        res_pad_req = _make_valid_brain_result_dict()
        res_pad_req["request_id"] = padded
        with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
            BrainResult.from_dict(res_pad_req)

    d_oversized_req = _make_valid_brain_request_dict()
    d_oversized_req["request_id"] = "a" * 65
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed"):
        BrainRequest.from_dict(d_oversized_req)


def test_closed_operation_status_and_output_type_validation():
    """Operations, statuses, and output types are strictly validated against closed enums."""
    d_bad_op = _make_valid_brain_request_dict()
    d_bad_op["operation"] = "ARBITRARY_REASONING"
    with pytest.raises(ContinuityStateValidationError, match="Invalid BrainOperation"):
        BrainRequest.from_dict(d_bad_op)

    res_bad_status = _make_valid_brain_result_dict()
    res_bad_status["status"] = "MAYBE"
    with pytest.raises(ContinuityStateValidationError, match="Invalid BrainResultStatus"):
        BrainResult.from_dict(res_bad_status)

    res_bad_out = _make_valid_brain_result_dict()
    res_bad_out["output_type"] = "CHAT_STREAM"
    with pytest.raises(ContinuityStateValidationError, match="Invalid BrainOutputType"):
        BrainResult.from_dict(res_bad_out)


def test_unknown_fields_and_raw_body_rejection():
    """Unknown fields and raw transcript/reasoning/content fields fail closed."""
    # Root level arbitrary field
    d_root = _make_valid_brain_request_dict()
    d_root["prompt_override"] = "system prompt"
    with pytest.raises(ContinuityStateValidationError, match="Unknown root fields in BrainRequest"):
        BrainRequest.from_dict(d_root)

    # Raw content / reasoning rejection in BrainResult
    for forbidden_field in ["bounded_content", "transcript", "reasoning", "raw_output"]:
        res_raw = _make_valid_brain_result_dict()
        res_raw[forbidden_field] = "Some model output body"
        with pytest.raises(ContinuityStateValidationError, match="Unknown root fields in BrainResult"):
            BrainResult.from_dict(res_raw)

    d_context = _make_valid_brain_request_dict()
    d_context["context_refs"][0]["raw_content"] = "file body"
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in context_refs"):
        BrainRequest.from_dict(d_context)

    d_out = _make_valid_brain_request_dict()
    d_out["output_contract"]["auto_merge"] = True
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in output_contract"):
        BrainRequest.from_dict(d_out)


def test_operation_and_output_type_compatibility():
    """Operation and output_type must adhere to closed compatibility matrix."""
    # REVIEW operation with TASK_ARTIFACT output contract is rejected
    d_mismatch = _make_valid_brain_request_dict()
    d_mismatch["operation"] = "REVIEW"
    d_mismatch["output_contract"]["expected_output_type"] = "TASK_ARTIFACT"
    with pytest.raises(ContinuityStateValidationError, match="Incompatible expected_output_type"):
        BrainRequest.from_dict(d_mismatch)

    # Result with operation=REVIEW and output_type=TASK_ARTIFACT is rejected
    res_mismatch = _make_valid_brain_result_dict()
    res_mismatch["operation"] = "REVIEW"
    res_mismatch["output_type"] = "TASK_ARTIFACT"
    with pytest.raises(ContinuityStateValidationError, match="Incompatible output_type"):
        BrainResult.from_dict(res_mismatch)


def test_output_type_and_artifact_role_validation():
    """Output type and artifact role/path must match active task identity and role."""
    # REVIEW_ARTIFACT pointing to .ai/tasks/... fails
    res_bad_role = _make_valid_brain_result_dict()
    res_bad_role["operation"] = "REVIEW"
    res_bad_role["output_type"] = "REVIEW_ARTIFACT"
    res_bad_role["artifact_ref"] = {
        "path": ".ai/tasks/TASK-021.md",
        "blob_sha": "3ca21b58663c2de99ee2f16d16e2203ec77d0558",
        "ref": "review",
    }
    with pytest.raises(ContinuityStateValidationError, match="incompatible with REVIEW_ARTIFACT"):
        BrainResult.from_dict(res_bad_role)

    # Task identity mismatch (pointing to TASK-099 for active TASK-021)
    res_task_mismatch = _make_valid_brain_result_dict()
    res_task_mismatch["artifact_ref"]["path"] = ".ai/tasks/TASK-099.md"
    with pytest.raises(ContinuityStateValidationError, match="incompatible with TASK_ARTIFACT for TASK-021"):
        BrainResult.from_dict(res_task_mismatch)


def test_artifact_producing_request_requires_target_path():
    """BrainRequest with an artifact output type requires non-null target_artifact_path."""
    # TASK_ARTIFACT without target path fails
    d_no_target = _make_valid_brain_request_dict()
    d_no_target["output_contract"]["target_artifact_path"] = None
    with pytest.raises(ContinuityStateValidationError, match="requires a non-null target_artifact_path"):
        BrainRequest.from_dict(d_no_target)

    # REVIEW_ARTIFACT without target path fails
    d_review_no_target = _make_valid_brain_request_dict()
    d_review_no_target["operation"] = "REVIEW"
    d_review_no_target["output_contract"] = {
        "expected_output_type": "REVIEW_ARTIFACT",
        "target_artifact_path": None,
    }
    with pytest.raises(ContinuityStateValidationError, match="requires a non-null target_artifact_path"):
        BrainRequest.from_dict(d_review_no_target)

    # BOUNDED_TEXT without target path succeeds
    d_bounded_text = _make_valid_brain_request_dict()
    d_bounded_text["operation"] = "DIAGNOSIS"
    d_bounded_text["output_contract"] = {
        "expected_output_type": "BOUNDED_TEXT",
        "target_artifact_path": None,
    }
    req = BrainRequest.from_dict(d_bounded_text)
    assert req.output_contract.target_artifact_path is None

    # BOUNDED_TEXT with non-null target path fails closed (C5 / Checklist 9)
    d_bounded_text_with_target = _make_valid_brain_request_dict()
    d_bounded_text_with_target["operation"] = "DIAGNOSIS"
    d_bounded_text_with_target["output_contract"] = {
        "expected_output_type": "BOUNDED_TEXT",
        "target_artifact_path": ".ai/context/TASK-021-DIAGNOSIS.md",
    }
    with pytest.raises(ContinuityStateValidationError, match="must have target_artifact_path=None"):
        BrainRequest.from_dict(d_bounded_text_with_target)


def test_plan_diagnosis_patch_artifact_namespace_validation():
    """PLAN, DIAGNOSIS, and PATCH_PROPOSAL must live in allowed namespaces and reject wrong-role directories."""
    # PLAN_ARTIFACT under .ai/tasks/ fails
    res_plan_in_tasks = _make_valid_brain_result_dict()
    res_plan_in_tasks["operation"] = "PLAN"
    res_plan_in_tasks["output_type"] = "PLAN_ARTIFACT"
    res_plan_in_tasks["artifact_ref"]["path"] = ".ai/tasks/TASK-021-PLAN.md"
    with pytest.raises(ContinuityStateValidationError, match="incompatible with PLAN_ARTIFACT"):
        BrainResult.from_dict(res_plan_in_tasks)

    # DIAGNOSIS_ARTIFACT under .ai/reviews/ fails
    res_diag_in_reviews = _make_valid_brain_result_dict()
    res_diag_in_reviews["operation"] = "DIAGNOSIS"
    res_diag_in_reviews["output_type"] = "DIAGNOSIS_ARTIFACT"
    res_diag_in_reviews["artifact_ref"]["path"] = ".ai/reviews/TASK-021-DIAGNOSIS.md"
    with pytest.raises(ContinuityStateValidationError, match="incompatible with DIAGNOSIS_ARTIFACT"):
        BrainResult.from_dict(res_diag_in_reviews)

    # PATCH_PROPOSAL_ARTIFACT under .ai/tasks/ fails
    res_patch_in_tasks = _make_valid_brain_result_dict()
    res_patch_in_tasks["operation"] = "PATCH_PROPOSAL"
    res_patch_in_tasks["output_type"] = "PATCH_PROPOSAL_ARTIFACT"
    res_patch_in_tasks["artifact_ref"]["path"] = ".ai/tasks/TASK-021-PATCH.md"
    with pytest.raises(ContinuityStateValidationError, match="incompatible with PATCH_PROPOSAL_ARTIFACT"):
        BrainResult.from_dict(res_patch_in_tasks)

    # Valid PLAN under .ai/context/ succeeds
    res_plan_valid = _make_valid_brain_result_dict()
    res_plan_valid["operation"] = "PLAN"
    res_plan_valid["output_type"] = "PLAN_ARTIFACT"
    res_plan_valid["artifact_ref"]["path"] = ".ai/context/TASK-021-CHATGPT-PLAN.md"
    obj = BrainResult.from_dict(res_plan_valid)
    assert obj.artifact_ref.path == ".ai/context/TASK-021-CHATGPT-PLAN.md"


def test_exact_task_token_matching_in_role_paths():
    """Exact delimiter-aware task token parsing rejects TASK-0210, TASK-21, TASK-0021, lowercase, and REVIEW aliases (C3 / R1-1)."""
    # 1. TASK-0210 fails for active TASK-021
    res_plan_210 = _make_valid_brain_result_dict()
    res_plan_210["operation"] = "PLAN"
    res_plan_210["output_type"] = "PLAN_ARTIFACT"
    res_plan_210["artifact_ref"]["path"] = ".ai/plans/TASK-0210-PLAN.md"
    with pytest.raises(ContinuityStateValidationError, match="which does not match active task identity TASK-021"):
        BrainResult.from_dict(res_plan_210)

    # 2. TASK-21 (unpadded alias) fails for active TASK-021 (R1-1)
    res_plan_short_21 = _make_valid_brain_result_dict()
    res_plan_short_21["operation"] = "PLAN"
    res_plan_short_21["output_type"] = "PLAN_ARTIFACT"
    res_plan_short_21["artifact_ref"]["path"] = ".ai/plans/TASK-21-ARCHITECTURE-PLAN.md"
    with pytest.raises(ContinuityStateValidationError, match="which does not match active task identity TASK-021"):
        BrainResult.from_dict(res_plan_short_21)

    # 3. TASK-0021 (overpadded alias) fails for active TASK-021 (R1-1)
    res_plan_overpadded = _make_valid_brain_result_dict()
    res_plan_overpadded["operation"] = "PLAN"
    res_plan_overpadded["output_type"] = "PLAN_ARTIFACT"
    res_plan_overpadded["artifact_ref"]["path"] = ".ai/plans/TASK-0021-PLAN.md"
    with pytest.raises(ContinuityStateValidationError, match="which does not match active task identity TASK-021"):
        BrainResult.from_dict(res_plan_overpadded)

    # 4. Lowercase task-021 fails for active TASK-021 (case-sensitive R1-1)
    res_plan_lowercase = _make_valid_brain_result_dict()
    res_plan_lowercase["operation"] = "PLAN"
    res_plan_lowercase["output_type"] = "PLAN_ARTIFACT"
    res_plan_lowercase["artifact_ref"]["path"] = ".ai/plans/task-021-plan.md"
    with pytest.raises(ContinuityStateValidationError, match="must match active task identity TASK-021"):
        BrainResult.from_dict(res_plan_lowercase)

    # 5. Conflicting multiple task tokens fail closed
    res_plan_conflict = _make_valid_brain_result_dict()
    res_plan_conflict["operation"] = "PLAN"
    res_plan_conflict["output_type"] = "PLAN_ARTIFACT"
    res_plan_conflict["artifact_ref"]["path"] = ".ai/context/TASK-021-OTHER-TASK-099.md"
    with pytest.raises(ContinuityStateValidationError, match="which does not match active task identity TASK-021"):
        BrainResult.from_dict(res_plan_conflict)

    # 6. Valid exact TASK-021 role paths succeed
    for valid_path in [
        ".ai/plans/TASK-021.md",
        ".ai/plans/TASK-021-PLAN.md",
        ".ai/context/TASK-021-SUBTASK-TASK-021.md",
    ]:
        res_valid = _make_valid_brain_result_dict()
        res_valid["operation"] = "PLAN"
        res_valid["output_type"] = "PLAN_ARTIFACT"
        res_valid["artifact_ref"]["path"] = valid_path
        obj = BrainResult.from_dict(res_valid)
        assert obj.artifact_ref.path == valid_path

    # 7. REVIEW_ARTIFACT canonical uniqueness (R1-1): exact matching without aliases
    res_review_valid = {
        "schema_version": "1",
        "task_id": "TASK-021",
        "request_id": "req-task-021-rev-r1",
        "brain_id": "chatgpt-chat",
        "operation": "REVIEW",
        "status": "SUCCESS",
        "output_type": "REVIEW_ARTIFACT",
        "artifact_ref": {
            "path": ".ai/reviews/REVIEW-021.md",
            "blob_sha": "3ca21b58663c2de99ee2f16d16e2203ec77d0558",
            "ref": "review",
        },
        "evidence_ref": None,
        "error_code": None,
    }
    assert BrainResult.from_dict(res_review_valid).artifact_ref.path == ".ai/reviews/REVIEW-021.md"

    # Aliased short REVIEW-21.md fails for active TASK-021
    res_review_alias = dict(res_review_valid)
    res_review_alias["artifact_ref"] = {
        "path": ".ai/reviews/REVIEW-21.md",
        "blob_sha": "3ca21b58663c2de99ee2f16d16e2203ec77d0558",
        "ref": "review",
    }
    with pytest.raises(ContinuityStateValidationError, match="incompatible with REVIEW_ARTIFACT for TASK-021"):
        BrainResult.from_dict(res_review_alias)


def test_bounded_text_evidence_ref_task_and_role_consistency():
    """evidence_ref must belong to active task_id and appropriate evidence namespace (C4 / R1-2)."""
    # 1. Valid DIAGNOSIS evidence under .ai/context/ and .ai/diagnosis/ succeeds
    for valid_evidence_path in [
        ".ai/context/TASK-021-DIAGNOSIS.md",
        ".ai/diagnosis/TASK-021-ANALYSIS.md",
    ]:
        res = BrainResult(
            schema_version="1",
            task_id="TASK-021",
            request_id="req-task-021-diag-r1",
            brain_id="chatgpt-chat",
            operation=BrainOperation.DIAGNOSIS,
            status=BrainResultStatus.SUCCESS,
            output_type=BrainOutputType.BOUNDED_TEXT,
            evidence_ref=ContextRef(path=valid_evidence_path),
        )
        assert res.evidence_ref.path == valid_evidence_path

    # 2. Valid PATCH_PROPOSAL evidence under .ai/patches/ succeeds
    res_patch = BrainResult(
        schema_version="1",
        task_id="TASK-021",
        request_id="req-task-021-patch-r1",
        brain_id="chatgpt-chat",
        operation=BrainOperation.PATCH_PROPOSAL,
        status=BrainResultStatus.SUCCESS,
        output_type=BrainOutputType.BOUNDED_TEXT,
        evidence_ref=ContextRef(path=".ai/patches/TASK-021-PROPOSAL.md"),
    )
    assert res_patch.evidence_ref.path == ".ai/patches/TASK-021-PROPOSAL.md"

    # 3. Wrong task in evidence_ref fails closed (R1-2)
    with pytest.raises(ContinuityStateValidationError, match="which does not match active task identity TASK-021"):
        BrainResult(
            schema_version="1",
            task_id="TASK-021",
            request_id="req-task-021-diag-r1",
            brain_id="chatgpt-chat",
            operation=BrainOperation.DIAGNOSIS,
            status=BrainResultStatus.SUCCESS,
            output_type=BrainOutputType.BOUNDED_TEXT,
            evidence_ref=ContextRef(path=".ai/context/TASK-099-DIAGNOSIS.md"),
        )

    # 4. Wrong role namespace in evidence_ref fails closed (e.g. .ai/tasks/ or .ai/reviews/)
    for bad_namespace in [
        ".ai/tasks/TASK-021.md",
        ".ai/reviews/REVIEW-021.md",
        ".ai/results/RESULT-021.md",
    ]:
        with pytest.raises(ContinuityStateValidationError, match="incompatible with DIAGNOSIS evidence"):
            BrainResult(
                schema_version="1",
                task_id="TASK-021",
                request_id="req-task-021-diag-r1",
                brain_id="chatgpt-chat",
                operation=BrainOperation.DIAGNOSIS,
                status=BrainResultStatus.SUCCESS,
                output_type=BrainOutputType.BOUNDED_TEXT,
                evidence_ref=ContextRef(path=bad_namespace),
            )

    # 5. Non-success status with wrong-task evidence_ref fails closed
    with pytest.raises(ContinuityStateValidationError, match="which does not match active task identity TASK-021"):
        BrainResult(
            schema_version="1",
            task_id="TASK-021",
            request_id="req-task-021-diag-r1",
            brain_id="chatgpt-chat",
            operation=BrainOperation.DIAGNOSIS,
            status=BrainResultStatus.FAILED,
            output_type=BrainOutputType.BOUNDED_TEXT,
            evidence_ref=ContextRef(path=".ai/context/TASK-099-DIAGNOSIS.md"),
            error_code="FAILED_ANALYSIS",
        )


def test_artifact_ref_canonical_git_ref_validation():
    """ArtifactRef.ref inside BrainResult must be exact canonical without whitespace padding (R1-4)."""
    # Padded ref fails closed
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainResult(
            schema_version="1",
            task_id="TASK-021",
            request_id="req-task-021-r1",
            brain_id="chatgpt-chat",
            operation=BrainOperation.TASK,
            status=BrainResultStatus.SUCCESS,
            output_type=BrainOutputType.TASK_ARTIFACT,
            artifact_ref=ArtifactRef(
                path=".ai/tasks/TASK-021.md",
                ref=" task ",
                blob_sha="3ca21b58663c2de99ee2f16d16e2203ec77d0558",
            ),
        )

    # Exact canonical ref succeeds
    res = BrainResult(
        schema_version="1",
        task_id="TASK-021",
        request_id="req-task-021-r1",
        brain_id="chatgpt-chat",
        operation=BrainOperation.TASK,
        status=BrainResultStatus.SUCCESS,
        output_type=BrainOutputType.TASK_ARTIFACT,
        artifact_ref=ArtifactRef(
            path=".ai/tasks/TASK-021.md",
            ref="task",
            blob_sha="3ca21b58663c2de99ee2f16d16e2203ec77d0558",
        ),
    )
    assert res.artifact_ref.ref == "task"


def test_result_payload_exclusivity_and_status_matrix():
    """SUCCESS requires exactly one valid pointer, error_code=None, and non-success rejects conflicting/cross-task pointers (C4 / Checklist 15-23)."""
    # Both provided -> ambiguous
    res_both = _make_valid_brain_result_dict()
    res_both["evidence_ref"] = {"path": ".ai/context/TASK-021-EVIDENCE.md"}
    with pytest.raises(ContinuityStateValidationError, match="Ambiguous result payload"):
        BrainResult.from_dict(res_both)

    # Neither provided -> missing
    res_none = _make_valid_brain_result_dict()
    res_none["artifact_ref"] = None
    res_none["evidence_ref"] = None
    with pytest.raises(ContinuityStateValidationError, match="SUCCESS status requires exactly one result payload pointer"):
        BrainResult.from_dict(res_none)

    # SUCCESS with non-null error_code fails closed (Checklist 19)
    res_success_err = _make_valid_brain_result_dict()
    res_success_err["error_code"] = "SOME_ERROR"
    with pytest.raises(ContinuityStateValidationError, match="SUCCESS status cannot have a non-null error_code"):
        BrainResult.from_dict(res_success_err)

    # SUCCESS artifact output + evidence_ref fails (Checklist 16)
    res_artifact_with_evidence = {
        "schema_version": "1",
        "task_id": "TASK-021",
        "request_id": "req-task-021-r1",
        "brain_id": "chatgpt-chat",
        "operation": "TASK",
        "status": "SUCCESS",
        "output_type": "TASK_ARTIFACT",
        "artifact_ref": None,
        "evidence_ref": {
            "path": ".ai/context/TASK-021-EVIDENCE.md",
        },
        "error_code": None,
    }
    with pytest.raises(ContinuityStateValidationError, match="cannot carry evidence_ref"):
        BrainResult.from_dict(res_artifact_with_evidence)

    # SUCCESS BOUNDED_TEXT + artifact_ref fails (Checklist 18)
    res_bounded_with_artifact = {
        "schema_version": "1",
        "task_id": "TASK-021",
        "request_id": "req-task-021-diag-r1",
        "brain_id": "chatgpt-chat",
        "operation": "DIAGNOSIS",
        "status": "SUCCESS",
        "output_type": "BOUNDED_TEXT",
        "artifact_ref": {
            "path": ".ai/tasks/TASK-021.md",
            "blob_sha": "3ca21b58663c2de99ee2f16d16e2203ec77d0558",
            "ref": "task",
        },
        "evidence_ref": None,
        "error_code": None,
    }
    with pytest.raises(ContinuityStateValidationError, match="cannot carry artifact_ref"):
        BrainResult.from_dict(res_bounded_with_artifact)

    # Evidence ref with BOUNDED_TEXT succeeds
    res_evidence = {
        "schema_version": "1",
        "task_id": "TASK-021",
        "request_id": "req-task-021-diag-r1",
        "brain_id": "chatgpt-chat",
        "operation": "DIAGNOSIS",
        "status": "SUCCESS",
        "output_type": "BOUNDED_TEXT",
        "artifact_ref": None,
        "evidence_ref": {
            "path": ".ai/context/TASK-021-DIAGNOSIS.md",
            "blob_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            "description": "Diagnosis evidence pointer",
        },
        "error_code": None,
    }
    res_obj = BrainResult.from_dict(res_evidence)
    assert res_obj.evidence_ref is not None
    assert res_obj.evidence_ref.path == ".ai/context/TASK-021-DIAGNOSIS.md"

    # FAILED status cannot smuggle cross-task artifact pointer (Checklist 21)
    res_failed_crosstask = {
        "schema_version": "1",
        "task_id": "TASK-021",
        "request_id": "req-task-021-r1",
        "brain_id": "chatgpt-chat",
        "operation": "TASK",
        "status": "FAILED",
        "output_type": "TASK_ARTIFACT",
        "artifact_ref": {
            "path": ".ai/tasks/TASK-099.md",
            "blob_sha": "3ca21b58663c2de99ee2f16d16e2203ec77d0558",
            "ref": "task",
        },
        "evidence_ref": None,
        "error_code": "FAILED_GENERATION",
    }
    with pytest.raises(ContinuityStateValidationError, match="incompatible with TASK_ARTIFACT for TASK-021"):
        BrainResult.from_dict(res_failed_crosstask)

    # Non-success with both artifact_ref and evidence_ref fails closed (Checklist 22)
    res_failed_both = {
        "schema_version": "1",
        "task_id": "TASK-021",
        "request_id": "req-task-021-r1",
        "brain_id": "chatgpt-chat",
        "operation": "DIAGNOSIS",
        "status": "FAILED",
        "output_type": "BOUNDED_TEXT",
        "artifact_ref": {
            "path": ".ai/context/TASK-021-DIAG.md",
            "blob_sha": "3ca21b58663c2de99ee2f16d16e2203ec77d0558",
            "ref": "diagnosis",
        },
        "evidence_ref": {
            "path": ".ai/context/TASK-021-EVIDENCE.md",
        },
        "error_code": "FAILED_GENERATION",
    }
    with pytest.raises(ContinuityStateValidationError, match="Ambiguous result payload"):
        BrainResult.from_dict(res_failed_both)


def test_bounded_context_refs_and_duplicate_rejection():
    """Context references are bounded, validate paths, reject duplicates, and reject whitespace padding (C2 / Checklist 5-8)."""
    d = _make_valid_brain_request_dict()
    d["context_refs"] = [
        {"path": ".ai/tasks/TASK-021.md"},
        {"path": ".ai/tasks/TASK-021.md"},  # Duplicate
    ]
    with pytest.raises(ContinuityStateValidationError, match="Duplicate context_ref path rejected"):
        BrainRequest.from_dict(d)

    # Padded ContextRef path fails closed
    d_padded = _make_valid_brain_request_dict()
    d_padded["context_refs"] = [
        {"path": " .ai/tasks/TASK-021.md "},
    ]
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainRequest.from_dict(d_padded)

    # Max count bound
    d_too_many = _make_valid_brain_request_dict()
    d_too_many["context_refs"] = [{"path": f".ai/tasks/TASK-{i:03d}.md"} for i in range(35)]
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed"):
        BrainRequest.from_dict(d_too_many)


def test_unsafe_and_sensitive_path_rejection():
    """Context paths and artifact paths reject traversal, absolute paths, and sensitive directories."""
    d_traversal = _make_valid_brain_request_dict()
    d_traversal["context_refs"] = [{"path": "../../../etc/passwd"}]
    with pytest.raises(ContinuityStateValidationError, match="must not contain empty or '\\.\\.' segments"):
        BrainRequest.from_dict(d_traversal)

    d_secret = _make_valid_brain_request_dict()
    d_secret["context_refs"] = [{"path": ".ai/secrets/token.json"}]
    with pytest.raises(ContinuityStateValidationError, match="Sensitive"):
        BrainRequest.from_dict(d_secret)

    d_cred = _make_valid_brain_request_dict()
    d_cred["output_contract"]["target_artifact_path"] = ".ai/credentials/user.yaml"
    with pytest.raises(ContinuityStateValidationError, match="Sensitive"):
        BrainRequest.from_dict(d_cred)


def test_16kib_fail_closed_limit():
    """Oversized BrainRequest or BrainResult fails closed in constructor and parser."""
    d_huge = _make_valid_brain_request_dict()
    d_huge["objective"] = "x" * 4000
    refs = []
    for i in range(30):
        refs.append({
            "path": f".ai/decisions/ADR-{i:03d}-VERY-LONG-NAME-PADDING-PADDING-PADDING-PADDING-PADDING-PADDING-PADDING-PADDING-PADDING.md",
            "blob_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            "description": "d" * 250,
        })
    d_huge["context_refs"] = refs

    with pytest.raises(ContinuityStateValidationError, match="exceeds MAX_SERIALIZED_BYTES"):
        BrainRequest.from_dict(d_huge)


def test_brain_capability_declarative_and_bounded():
    """BrainCapability is purely descriptive, rejects duplicates, and is bounded (C6 / R1-3 / Checklist 24-28)."""
    cap = BrainCapability(
        brain_id="chatgpt-chat",
        supported_operations=(
            BrainOperation.TASK,
            BrainOperation.TASK_AND_PLAN,
            BrainOperation.PLAN,
            BrainOperation.REVIEW,
        ),
        max_context_bytes=1048576,
        declarative_only=True,
    )
    assert cap.brain_id == "chatgpt-chat"
    assert BrainOperation.TASK_AND_PLAN in cap.supported_operations
    assert cap.declarative_only is True

    # Duplicate supported operations fail closed
    with pytest.raises(ContinuityStateValidationError, match="Duplicate BrainOperation in supported_operations"):
        BrainCapability(
            brain_id="chatgpt-chat",
            supported_operations=(
                BrainOperation.TASK,
                BrainOperation.PLAN,
                BrainOperation.TASK,
            ),
        )

    # Padded brain_id fails closed
    with pytest.raises(ContinuityStateValidationError, match="must not contain leading or trailing whitespace"):
        BrainCapability(
            brain_id=" chatgpt-chat ",
            supported_operations=(BrainOperation.TASK,),
        )

    # declarative_only must be True
    with pytest.raises(ContinuityStateValidationError, match="declarative_only must be True"):
        BrainCapability(
            brain_id="chatgpt-chat",
            supported_operations=(BrainOperation.TASK,),
            declarative_only=False,
        )

    # Empty operations list is rejected
    with pytest.raises(ContinuityStateValidationError, match="supported_operations cannot be empty"):
        BrainCapability(
            brain_id="chatgpt-chat",
            supported_operations=(),
        )

    # max_context_bytes upper bound validation (R1-3)
    cap_max = BrainCapability(
        brain_id="chatgpt-chat",
        supported_operations=(BrainOperation.TASK,),
        max_context_bytes=MAX_BRAIN_CAPACITY_CONTEXT_BYTES,
    )
    assert cap_max.max_context_bytes == MAX_BRAIN_CAPACITY_CONTEXT_BYTES

    # max_context_bytes > MAX_BRAIN_CAPACITY_CONTEXT_BYTES fails closed
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowed"):
        BrainCapability(
            brain_id="chatgpt-chat",
            supported_operations=(BrainOperation.TASK,),
            max_context_bytes=MAX_BRAIN_CAPACITY_CONTEXT_BYTES + 1,
        )

    # Negative integer fails closed
    with pytest.raises(ContinuityStateValidationError, match="must be >= 0"):
        BrainCapability(
            brain_id="chatgpt-chat",
            supported_operations=(BrainOperation.TASK,),
            max_context_bytes=-1,
        )

    # Bool fails closed
    with pytest.raises(ContinuityStateValidationError, match="must be an integer"):
        BrainCapability(
            brain_id="chatgpt-chat",
            supported_operations=(BrainOperation.TASK,),
            max_context_bytes=True,
        )

    # None is permitted (unspecified capacity)
    cap_none = BrainCapability(
        brain_id="chatgpt-chat",
        supported_operations=(BrainOperation.TASK,),
        max_context_bytes=None,
    )
    assert cap_none.max_context_bytes is None
