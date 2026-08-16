"""Comprehensive test suite for AIOS Brain-Neutral Contract (ADR-010 M2)."""
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
    """Actor ID must be lowercase alphanumeric/hyphen, request ID must match conservative pattern."""
    d_bad_actor = _make_valid_brain_request_dict()
    d_bad_actor["brain_id"] = "Claude_3.5_Sonnet"
    with pytest.raises(ContinuityStateValidationError, match="conservative lowercase identifier"):
        BrainRequest.from_dict(d_bad_actor)

    d_bad_req = _make_valid_brain_request_dict()
    d_bad_req["request_id"] = "bad request ID with spaces"
    with pytest.raises(ContinuityStateValidationError, match="conservative lowercase identifier"):
        BrainRequest.from_dict(d_bad_req)

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
    res_bad_role["artifact_ref"]["path"] = ".ai/tasks/TASK-021.md"
    with pytest.raises(ContinuityStateValidationError, match="incompatible with REVIEW_ARTIFACT"):
        BrainResult.from_dict(res_bad_role)

    # Task identity mismatch (pointing to TASK-099 for active TASK-021)
    res_task_mismatch = _make_valid_brain_result_dict()
    res_task_mismatch["artifact_ref"]["path"] = ".ai/tasks/TASK-099.md"
    with pytest.raises(ContinuityStateValidationError, match="incompatible with TASK_ARTIFACT for TASK-021"):
        BrainResult.from_dict(res_task_mismatch)


def test_result_payload_exclusivity():
    """SUCCESS status requires exactly one result pointer (artifact_ref or evidence_ref)."""
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


def test_bounded_context_refs_and_duplicate_rejection():
    """Context references are bounded, validate paths, and reject duplicates."""
    d = _make_valid_brain_request_dict()
    d["context_refs"] = [
        {"path": ".ai/tasks/TASK-021.md"},
        {"path": ".ai/tasks/TASK-021.md"},  # Duplicate
    ]
    with pytest.raises(ContinuityStateValidationError, match="Duplicate context_ref path rejected"):
        BrainRequest.from_dict(d)

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


def test_brain_capability_declarative_only():
    """BrainCapability is purely descriptive and declarative."""
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
