import inspect
import json
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.certification_job import (
    CERTIFICATION_WAIT_CONTRACT,
    CertificationContractError,
    CertificationJob,
    CertificationJobStatus,
    CertificationPreflightEvidence,
    build_candidate_fingerprint,
    build_certification_command_identity,
    require_certification_preflight,
)
from src.aios_bridge.review_pipeline import (
    ReviewContractError,
    ReviewState,
    derive_review_first_final_state,
)
from src.aios_bridge.validation import (
    CONTROL_PLANE_STRICT_COMPAT_PLAN,
    ValidationProfile,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
FP_A = "a" * 64
FP_B = "b" * 64
COMMAND = "python -m pytest tests/ -q"
COMMAND_ID = build_certification_command_identity(COMMAND)


def candidate_fingerprint(head=SHA_A):
    return build_candidate_fingerprint(
        task_id="TASK-091",
        candidate_head_sha=head,
        base_main_sha=SHA_B,
        task_artifact_blob_sha="c" * 40,
        roadmap_fingerprint="d" * 64,
        validation_profile=ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        certification_command_identity=COMMAND_ID,
    )


def certification_context(head=SHA_A):
    return {
        "task_id": "TASK-091",
        "candidate_head_sha": head,
        "candidate_fingerprint": candidate_fingerprint(head),
        "validation_plan": CONTROL_PLANE_STRICT_COMPAT_PLAN,
        "command": COMMAND,
        "command_identity": COMMAND_ID,
    }


def preflight(**overrides):
    values = {
        "task_exists": True,
        "review_first_mode": True,
        "review_status": "SEMANTICALLY_ACCEPTED_PENDING_T2",
        "review_approved": True,
        "auto_merge_eligible": True,
        "reviewed_task_head_sha": SHA_A,
        "reviewed_base_main_sha": SHA_B,
        "remote_task_head_sha": SHA_A,
        "remote_main_sha": SHA_B,
        "local_branch": "ai/task-091",
        "expected_task_branch": "ai/task-091",
        "local_head_sha": SHA_A,
        "worktree_clean": True,
        "merge_base_sha": SHA_B,
        "behind_by": 0,
        "roadmap_valid": True,
        "certification_owned_t2_count": 1,
    }
    values.update(overrides)
    return CertificationPreflightEvidence(**values)


def passed_job(**overrides):
    values = {
        "job_id": "cert-task-091-a",
        "task_id": "TASK-091",
        "candidate_head_sha": SHA_A,
        "candidate_fingerprint": candidate_fingerprint(),
        "validation_profile": ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        "certification_command_identity": COMMAND_ID,
        "status": CertificationJobStatus.CERTIFICATION_PASS,
        "started_at": "2026-08-25T00:00:00Z",
        "completed_at": "2026-08-25T00:00:01Z",
        "terminal_result_digest": "e" * 64,
        "aios_managed_t2_execution_count": 1,
        "t2_exit_status": 0,
        "t2_succeeded": True,
        "duration_seconds": 1.0,
    }
    values.update(overrides)
    return CertificationJob(**values)


def test_certify_reviewed_cli_is_provider_neutral_and_has_no_routing_options():
    args = bridge.build_parser().parse_args(["certify-reviewed", "91"])
    assert args.func is bridge.cmd_certify_reviewed
    assert args.task_id == 91
    with pytest.raises(SystemExit):
        bridge.build_parser().parse_args(
            ["certify-reviewed", "91", "--executor", "codex"]
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"review_status": "CHANGES_REQUIRED"}, "not semantically accepted"),
        ({"remote_task_head_sha": "c" * 40}, "task head drifted"),
        ({"remote_main_sha": "c" * 40}, "base main drifted"),
        ({"worktree_clean": False}, "clean worktree"),
        ({"behind_by": 1}, "behind"),
        ({"roadmap_valid": False}, "roadmap"),
        ({"certification_owned_t2_count": 0}, "exactly one"),
    ),
)
def test_certification_preflight_drift_fails_before_t2(overrides, message):
    with pytest.raises(CertificationContractError, match=message):
        require_certification_preflight(preflight(**overrides))


def test_certification_job_runs_t2_exactly_once_is_idempotent_and_persists_no_stdout(
    tmp_path, monkeypatch
):
    calls = []
    job_path = tmp_path / "runtime" / "TASK-091" / "job.json"
    monkeypatch.setattr(bridge, "_preflight_certify_reviewed", lambda _: certification_context())
    monkeypatch.setattr(bridge, "_certification_job_path", lambda _: job_path)
    monkeypatch.setattr(bridge, "update_state", lambda *args: None)
    monkeypatch.setattr(bridge, "now", lambda: "2026-08-25T00:00:00Z")

    def run_once(*args, **kwargs):
        calls.append(args[0])
        return SimpleNamespace(returncode=0, stdout="RAW_SECRET_T2_STDOUT", stderr="")

    monkeypatch.setattr(bridge, "run", run_once)
    first = bridge.cmd_certify_reviewed(SimpleNamespace(task_id=91))
    second = bridge.cmd_certify_reviewed(SimpleNamespace(task_id=91))

    assert first.status is CertificationJobStatus.CERTIFICATION_PASS
    assert second == first
    assert calls == [COMMAND]
    payload_text = job_path.read_text(encoding="utf-8")
    payload = json.loads(payload_text)
    assert "RAW_SECRET_T2_STDOUT" not in payload_text
    assert payload["aios_managed_t2_execution_count"] == 1
    assert payload["t2_exit_status"] == 0
    assert payload["t2_succeeded"] is True
    assert payload["model_poll_count"] == 0
    assert payload["executor_poll_count"] == 0
    assert CERTIFICATION_WAIT_CONTRACT.model_completion_polling_required is False
    assert CERTIFICATION_WAIT_CONTRACT.executor_completion_polling_required is False


def test_failed_certification_has_no_automatic_retry_or_merge_authority(
    tmp_path, monkeypatch
):
    calls = []
    job_path = tmp_path / "runtime" / "TASK-091" / "job.json"
    monkeypatch.setattr(bridge, "_preflight_certify_reviewed", lambda _: certification_context())
    monkeypatch.setattr(bridge, "_certification_job_path", lambda _: job_path)
    monkeypatch.setattr(bridge, "update_state", lambda *args: None)
    monkeypatch.setattr(bridge, "now", lambda: "2026-08-25T00:00:00Z")

    def fail_t2(*args, **kwargs):
        calls.append(args[0])
        return SimpleNamespace(returncode=2, stdout="failed", stderr="")

    monkeypatch.setattr(bridge, "run", fail_t2)
    with pytest.raises(SystemExit):
        bridge.cmd_certify_reviewed(SimpleNamespace(task_id=91))
    with pytest.raises(SystemExit):
        bridge.cmd_certify_reviewed(SimpleNamespace(task_id=91))

    failed = CertificationJob.from_dict(json.loads(job_path.read_text(encoding="utf-8")))
    assert calls == [COMMAND]
    assert failed.status is CertificationJobStatus.CERTIFICATION_FAILED
    assert failed.creates_certification_authority is False


def test_existing_job_for_different_candidate_fails_without_t2(tmp_path, monkeypatch):
    job_path = tmp_path / "runtime" / "TASK-091" / "job.json"
    job_path.parent.mkdir(parents=True)
    job_path.write_text(json.dumps(passed_job().to_dict()), encoding="utf-8")
    monkeypatch.setattr(
        bridge,
        "_preflight_certify_reviewed",
        lambda _: certification_context(head="c" * 40),
    )
    monkeypatch.setattr(bridge, "_certification_job_path", lambda _: job_path)
    monkeypatch.setattr(
        bridge,
        "run",
        lambda *args, **kwargs: pytest.fail("T2 must not run for a different candidate"),
    )
    with pytest.raises(SystemExit):
        bridge.cmd_certify_reviewed(SimpleNamespace(task_id=91))


def test_semantic_acceptance_or_failed_certification_cannot_derive_final_pass():
    kwargs = {
        "task_id": "TASK-091",
        "review_state": ReviewState.SEMANTICALLY_ACCEPTED_PENDING_T2,
        "approved": True,
        "auto_merge_eligible": True,
        "candidate_head_sha": SHA_A,
        "candidate_fingerprint": candidate_fingerprint(),
        "validation_profile": ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        "certification_command_identity": COMMAND_ID,
    }
    failed = CertificationJob.from_dict(
        {
            **passed_job().to_dict(),
            "status": CertificationJobStatus.CERTIFICATION_FAILED.value,
            "t2_exit_status": 1,
            "t2_succeeded": False,
        }
    )
    with pytest.raises(ReviewContractError, match="CERTIFICATION_PASS"):
        derive_review_first_final_state(certification_job=failed, **kwargs)


def test_exact_pass_finalization_feeds_existing_merge_gate_without_duplicate_merge_logic():
    state = derive_review_first_final_state(
        task_id="TASK-091",
        review_state=ReviewState.SEMANTICALLY_ACCEPTED_PENDING_T2,
        approved=True,
        auto_merge_eligible=True,
        certification_job=passed_job(),
        candidate_head_sha=SHA_A,
        candidate_fingerprint=candidate_fingerprint(),
        validation_profile=ValidationProfile.CONTROL_PLANE_STRICT_COMPAT,
        certification_command_identity=COMMAND_ID,
    )
    source = inspect.getsource(bridge.cmd_merge_reviewed)
    assert state is ReviewState.FINAL_PASS
    assert source.index("derive_review_first_final_state") < source.index(
        "evaluate_merge_gate"
    )
    assert "git(\"push\"" in source


def test_publication_integration_preserves_legacy_and_defers_review_first_t2():
    source = inspect.getsource(bridge.cmd_publish)
    assert "require_certification_for_publication" in source
    assert "require_review_first_candidate_publication" in source
    assert "READY_FOR_SEMANTIC_REVIEW" in source
    assert "DEFERRED_TO_CERTIFY_REVIEWED" in source
    assert "Review-first EVIDENCE_REFRESH" in source


def test_slice_scope_does_not_implement_reserved_task_087():
    combined = "\n".join(
        inspect.getsource(item)
        for item in (
            bridge.cmd_publish,
            bridge.cmd_certify_reviewed,
            bridge.cmd_merge_reviewed,
        )
    )
    assert "TASK-087" not in combined
