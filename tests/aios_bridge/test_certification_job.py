from dataclasses import FrozenInstanceError

import pytest

from src.aios_bridge.certification_job import (
    CERTIFICATION_WAIT_CONTRACT,
    CertificationContractError,
    CertificationJob,
    CertificationJobStatus,
    CertificationWaitContract,
    LongRunningWaitOwner,
    certification_candidate_matches,
    require_exact_certification_candidate,
    transition_certification_job,
)
from src.aios_bridge.validation import ValidationProfile


SHA_A = "a" * 40
SHA_B = "b" * 40
FP_A = "a" * 64
FP_B = "b" * 64
RESULT_DIGEST = "c" * 64


def job(**overrides):
    values = {
        "job_id": "cert-task-089-1",
        "task_id": "TASK-089",
        "candidate_head_sha": SHA_A,
        "candidate_fingerprint": FP_A,
        "validation_profile": ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        "certification_command_identity": "pytest-full-canonical-v1",
        "status": CertificationJobStatus.CERTIFICATION_PENDING,
        "started_at": None,
        "terminal_result_digest": None,
    }
    values.update(overrides)
    return CertificationJob(**values)


def test_certification_job_state_machine_is_closed_and_immutable():
    assert tuple(item.value for item in CertificationJobStatus) == (
        "CERTIFICATION_PENDING",
        "CERTIFICATION_RUNNING",
        "CERTIFICATION_PASS",
        "CERTIFICATION_FAILED",
        "SUPERSEDED",
    )
    pending = job()
    assert CertificationJob.from_dict(pending.to_dict()) == pending
    with pytest.raises(FrozenInstanceError):
        pending.status = CertificationJobStatus.CERTIFICATION_RUNNING
    with pytest.raises(ValueError):
        CertificationJobStatus("COMPLETE")


def test_certification_job_binds_exact_candidate_head_and_fingerprint():
    pending = job()
    assert certification_candidate_matches(pending, SHA_A, FP_A) is True
    assert certification_candidate_matches(pending, SHA_B, FP_A) is False
    assert certification_candidate_matches(pending, SHA_A, FP_B) is False
    assert require_exact_certification_candidate(pending, SHA_A, FP_A) is pending
    with pytest.raises(CertificationContractError, match="identity mismatch"):
        require_exact_certification_candidate(pending, SHA_B, FP_A)


def test_malformed_candidate_identity_fails_closed():
    with pytest.raises(CertificationContractError, match="40-hex"):
        certification_candidate_matches(job(), "HEAD", FP_A)
    with pytest.raises(CertificationContractError, match="64-hex"):
        certification_candidate_matches(job(), SHA_A, "UNKNOWN")


def test_certification_lifecycle_reaches_pass_only_from_running():
    pending = job()
    with pytest.raises(CertificationContractError, match="invalid certification transition"):
        transition_certification_job(
            pending, CertificationJobStatus.CERTIFICATION_PASS
        )
    running = transition_certification_job(
        pending,
        CertificationJobStatus.CERTIFICATION_RUNNING,
        started_at="2026-08-25T00:00:00Z",
    )
    with pytest.raises(CertificationContractError, match="requires terminal_result_digest"):
        transition_certification_job(
            running, CertificationJobStatus.CERTIFICATION_PASS
        )
    passed = transition_certification_job(
        running,
        CertificationJobStatus.CERTIFICATION_PASS,
        terminal_result_digest=RESULT_DIGEST,
    )
    assert passed.creates_certification_authority is True
    assert pending.creates_certification_authority is False


@pytest.mark.parametrize(
    "terminal_status",
    (
        CertificationJobStatus.CERTIFICATION_PASS,
        CertificationJobStatus.CERTIFICATION_FAILED,
        CertificationJobStatus.SUPERSEDED,
    ),
)
def test_terminal_state_reentry_fails_closed(terminal_status):
    terminal = job(
        status=terminal_status,
        started_at="2026-08-25T00:00:00Z",
        terminal_result_digest=(
            None
            if terminal_status is CertificationJobStatus.SUPERSEDED
            else RESULT_DIGEST
        ),
    )
    with pytest.raises(CertificationContractError, match="invalid certification transition"):
        transition_certification_job(
            terminal, CertificationJobStatus.CERTIFICATION_RUNNING
        )


def test_superseded_certification_is_terminal_and_non_authoritative():
    superseded = transition_certification_job(
        job(), CertificationJobStatus.SUPERSEDED
    )
    assert superseded.creates_certification_authority is False
    with pytest.raises(CertificationContractError, match="invalid certification transition"):
        transition_certification_job(
            superseded, CertificationJobStatus.CERTIFICATION_PASS
        )


def test_failed_certification_requires_terminal_result_digest():
    running = transition_certification_job(
        job(),
        CertificationJobStatus.CERTIFICATION_RUNNING,
        started_at="2026-08-25T00:00:00Z",
    )
    with pytest.raises(CertificationContractError, match="requires terminal_result_digest"):
        transition_certification_job(
            running, CertificationJobStatus.CERTIFICATION_FAILED
        )
    failed = transition_certification_job(
        running,
        CertificationJobStatus.CERTIFICATION_FAILED,
        terminal_result_digest=RESULT_DIGEST,
    )
    assert failed.terminal_result_digest == RESULT_DIGEST
    assert failed.creates_certification_authority is False


@pytest.mark.parametrize(
    "status",
    (
        CertificationJobStatus.CERTIFICATION_PASS,
        CertificationJobStatus.CERTIFICATION_FAILED,
    ),
)
def test_direct_and_machine_readable_result_statuses_require_digest(status):
    with pytest.raises(CertificationContractError, match="requires terminal_result_digest"):
        job(status=status, started_at="2026-08-25T00:00:00Z")

    data = job().to_dict()
    data.update(
        status=status.value,
        started_at="2026-08-25T00:00:00Z",
    )
    with pytest.raises(CertificationContractError, match="requires terminal_result_digest"):
        CertificationJob.from_dict(data)


def test_superseded_certification_rejects_terminal_result_digest():
    with pytest.raises(CertificationContractError, match="only for pass or failed"):
        job(
            status=CertificationJobStatus.SUPERSEDED,
            started_at="2026-08-25T00:00:00Z",
            terminal_result_digest=RESULT_DIGEST,
        )

    running = transition_certification_job(
        job(),
        CertificationJobStatus.CERTIFICATION_RUNNING,
        started_at="2026-08-25T00:00:00Z",
    )
    with pytest.raises(CertificationContractError, match="only for pass or failed"):
        transition_certification_job(
            running,
            CertificationJobStatus.SUPERSEDED,
            terminal_result_digest=RESULT_DIGEST,
        )


def test_no_model_polling_contract_is_provider_neutral_and_machine_readable():
    contract = CERTIFICATION_WAIT_CONTRACT
    assert contract.long_running_deterministic_wait_owner is (
        LongRunningWaitOwner.CERTIFICATION_BOUNDARY
    )
    assert contract.model_completion_polling_required is False
    assert contract.executor_completion_polling_required is False
    assert contract.provider_specific_semantics is False
    assert contract.future_executor_compatible is True
    assert contract.to_dict() == {
        "executor_completion_polling_required": False,
        "future_executor_compatible": True,
        "long_running_deterministic_wait_owner": "CERTIFICATION_BOUNDARY",
        "model_completion_polling_required": False,
        "provider_specific_semantics": False,
    }


def test_wait_contract_rejects_provider_or_polling_semantics():
    with pytest.raises(CertificationContractError, match="model completion polling"):
        CertificationWaitContract(
            long_running_deterministic_wait_owner=LongRunningWaitOwner.CERTIFICATION_BOUNDARY,
            model_completion_polling_required=True,
            executor_completion_polling_required=False,
            provider_specific_semantics=False,
            future_executor_compatible=True,
        )
