from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

import bridge
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionOperation
from src.aios_bridge.roadmap_governance import (
    H_SERIES_ROADMAP_BLOB_SHA,
    H_SERIES_ROADMAP_ID,
    H_SERIES_ROADMAP_PATH,
    H_SERIES_ROADMAP_VERSION,
    ROADMAP_FINGERPRINT_ALGORITHM_VERSION,
    MilestoneCompletionRecord,
    RoadmapChangeClass,
    RoadmapEvolutionRequest,
    RoadmapGovernanceError,
    RoadmapPreflightReason,
    RoadmapRegistryEntry,
    RoadmapStatus,
    RoadmapTaskBinding,
    evaluate_roadmap_preflight,
    git_blob_sha,
    impact_cone,
    may_open_milestone,
    milestone_completion_artifact_path,
    parse_canonical_roadmap,
    parse_milestone_completion_records,
    parse_roadmap_task_binding,
    roadmap_fingerprint,
    task_requires_roadmap_governance,
    validate_controlled_evolution,
    validate_milestone_completion,
    validate_task_binding,
)
from src.aios_bridge.review_merge import (
    MergeGateReason,
    ReviewedMergeInput,
    RoadmapReviewAudit,
    evaluate_merge_gate,
)
from src.aios_bridge.task_authoring import (
    ExecutableArtifactPreflightError,
    preflight_executable_artifact,
)


ROADMAP_BYTES = subprocess.run(
    ["git", "cat-file", "blob", H_SERIES_ROADMAP_BLOB_SHA],
    check=True,
    stdout=subprocess.PIPE,
).stdout
ROADMAP_SHA256 = "449dd8bfa4867e74723a1e4a3f619779aebc0c77845a702491bef178a8bc4ce6"


def _parse_bytes(payload: bytes = ROADMAP_BYTES, *, path: str = H_SERIES_ROADMAP_PATH):
    return parse_canonical_roadmap(
        payload,
        artifact_path=path,
        expected_blob_sha=git_blob_sha(payload),
    )


def _binding(
    *,
    roadmap=None,
    milestone: str = "H0",
    capability_id: str | None = None,
    requirements: tuple[str, ...] | None = None,
) -> RoadmapTaskBinding:
    roadmap = roadmap or _parse_bytes()
    canonical = roadmap.milestone(milestone) if milestone in roadmap.milestone_ids else None
    return RoadmapTaskBinding(
        roadmap_id=roadmap.roadmap_id,
        roadmap_version=roadmap.roadmap_version,
        roadmap_blob_sha=roadmap.roadmap_blob_sha,
        roadmap_fingerprint=roadmap.roadmap_fingerprint,
        roadmap_fingerprint_algorithm_version=roadmap.algorithm_version,
        milestone=milestone,
        capability_id=capability_id or (canonical.capability_id if canonical else "H9_UNKNOWN"),
        requirement_bindings=requirements or (
            (canonical.requirements[0],) if canonical else ("H9.R1",)
        ),
        scope_in=("bounded implementation",),
        scope_out=("Bridge authority",),
    )


def _task(binding: RoadmapTaskBinding | None, *, milestone: str = "H0", class_value: str = "AIOS ENGINEERING H-SERIES") -> str:
    marker = ""
    if binding is not None:
        marker = "ROADMAP_BINDING_JSON: " + json.dumps(
            binding.to_dict(), sort_keys=True, separators=(",", ":")
        )
    return f"""# TASK-100 — {milestone} bounded implementation
STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: {class_value}
MILESTONE: {milestone}
{marker}
EXECUTOR_CONTEXT_REFS_JSON: [{{"path":"{H_SERIES_ROADMAP_PATH}","blob_sha":"{H_SERIES_ROADMAP_BLOB_SHA}"}}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {{"allow_paid_api":false,"candidates":[{{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["SHELL"],"supported_operations":["RUN"]}}],"operation":"RUN","required_capabilities":["SHELL"]}}
"""


def _resolver(path: str, blob_sha: str) -> bytes:
    assert path == H_SERIES_ROADMAP_PATH
    assert blob_sha == H_SERIES_ROADMAP_BLOB_SHA
    return ROADMAP_BYTES


def _complete(roadmap, milestone: str) -> MilestoneCompletionRecord:
    canonical = roadmap.milestone(milestone)
    return MilestoneCompletionRecord.create(
        roadmap=roadmap,
        milestone=milestone,
        requirement_evidence={requirement: f"REVIEWED:{requirement}" for requirement in canonical.requirements},
    )


def _completion_artifact(roadmap, records) -> bytes:
    return json.dumps(
        {
            "schema_version": "1",
            "roadmap_id": roadmap.roadmap_id,
            "roadmap_version": roadmap.roadmap_version,
            "roadmap_blob_sha": roadmap.roadmap_blob_sha,
            "roadmap_fingerprint": roadmap.roadmap_fingerprint,
            "roadmap_fingerprint_algorithm_version": roadmap.algorithm_version,
            "records": [record.to_dict() for record in records],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _review_input(binding: RoadmapTaskBinding, roadmap, audit: RoadmapReviewAudit | None):
    return ReviewedMergeInput(
        task_id="TASK-100",
        review_status="PASS",
        review_approved=True,
        auto_merge_eligible=True,
        reviewed_task_head_sha="a" * 40,
        reviewed_base_main_sha="b" * 40,
        current_task_head_sha="a" * 40,
        current_main_sha="b" * 40,
        merge_base_sha="b" * 40,
        ahead_by=1,
        behind_by=0,
        roadmap_governed=True,
        roadmap_audit=audit,
        task_roadmap_binding=binding,
        current_roadmap=roadmap,
    )


def _fix_review(
    roadmap,
    binding: RoadmapTaskBinding,
    task_blob_sha: str,
    *,
    task_ref_blob_sha: str | None = None,
    roadmap_id: str | None = None,
) -> str:
    refs = [
        {
            "path": ".ai/tasks/TASK-100.md",
            "blob_sha": task_ref_blob_sha or task_blob_sha,
        },
        {"path": H_SERIES_ROADMAP_PATH, "blob_sha": H_SERIES_ROADMAP_BLOB_SHA},
    ]
    policy = {
        "allow_paid_api": False,
        "candidates": [{
            "capacity_class": "SUBSCRIPTION",
            "executor_id": "codex",
            "preference_rank": 0,
            "supported_capabilities": ["SHELL"],
            "supported_operations": ["FIX"],
        }],
        "operation": "FIX",
        "required_capabilities": ["SHELL"],
    }
    return f"""# REVIEW-100 — governed repair
STATUS: CHANGES_REQUIRED
PUBLISHER_PROFILE: CANONICAL_E4
REVIEWED_TASK_HEAD_SHA: {'a' * 40}
TASK_ARTIFACT_BLOB_SHA: {task_blob_sha}
ROADMAP_ID: {roadmap_id or binding.roadmap_id}
ROADMAP_VERSION: {binding.roadmap_version}
ROADMAP_BLOB_SHA: {binding.roadmap_blob_sha}
ROADMAP_FINGERPRINT: {binding.roadmap_fingerprint}
MILESTONE: {binding.milestone}
CAPABILITY_ID: {binding.capability_id}
EXECUTOR_CONTEXT_REFS_JSON: {json.dumps(refs, separators=(',', ':'))}
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {json.dumps(policy, separators=(',', ':'))}
"""


def _audit(binding: RoadmapTaskBinding, **changes: str) -> RoadmapReviewAudit:
    values = {
        "roadmap_audit": "PASS",
        "roadmap_id": binding.roadmap_id,
        "roadmap_version": binding.roadmap_version,
        "roadmap_blob_sha": binding.roadmap_blob_sha,
        "roadmap_fingerprint": binding.roadmap_fingerprint,
        "milestone": binding.milestone,
        "capability_id": binding.capability_id,
        "requirement_bindings_fingerprint": binding.requirement_bindings_fingerprint(),
    }
    values.update(changes)
    return RoadmapReviewAudit(**values)


def test_canonical_roadmap_exact_blob_and_exact_byte_fingerprint() -> None:
    assert git_blob_sha(ROADMAP_BYTES) == H_SERIES_ROADMAP_BLOB_SHA
    assert roadmap_fingerprint(ROADMAP_BYTES) == ROADMAP_SHA256
    roadmap = _parse_bytes()
    assert roadmap.roadmap_id == H_SERIES_ROADMAP_ID
    assert roadmap.roadmap_version == H_SERIES_ROADMAP_VERSION
    assert roadmap.status is RoadmapStatus.LOCKED
    assert roadmap.algorithm_version == ROADMAP_FINGERPRINT_ALGORITHM_VERSION
    assert roadmap.milestone_ids == tuple(f"H{i}" for i in range(9))


def test_blob_fingerprint_and_algorithm_mismatch_rejected() -> None:
    with pytest.raises(RoadmapGovernanceError, match="blob SHA mismatch"):
        parse_canonical_roadmap(
            ROADMAP_BYTES + b"\n",
            artifact_path=H_SERIES_ROADMAP_PATH,
            expected_blob_sha=H_SERIES_ROADMAP_BLOB_SHA,
        )
    with pytest.raises(RoadmapGovernanceError, match="Unsupported roadmap fingerprint"):
        parse_canonical_roadmap(
            ROADMAP_BYTES,
            artifact_path=H_SERIES_ROADMAP_PATH,
            expected_blob_sha=H_SERIES_ROADMAP_BLOB_SHA,
            algorithm_version="roadmap-sha256-v2",
        )
    with pytest.raises(RoadmapGovernanceError, match="Malformed roadmap_fingerprint"):
        replace(_binding(), roadmap_fingerprint="0" * 63)


@pytest.mark.parametrize("status", ["DRAFT", "SUPERSEDED"])
def test_only_locked_roadmap_is_executable_without_migration(status: str) -> None:
    payload = ROADMAP_BYTES.replace(b"STATUS: LOCKED", f"STATUS: {status}".encode())
    roadmap = _parse_bytes(payload)
    binding = _binding(roadmap=roadmap)
    with pytest.raises(RoadmapGovernanceError, match="not executable"):
        validate_task_binding(
            _task(binding),
            binding,
            roadmap,
            context_refs=({"path": H_SERIES_ROADMAP_PATH, "blob_sha": roadmap.roadmap_blob_sha},),
        )


def test_draft_roadmap_is_not_executable_even_with_migration_evidence() -> None:
    payload = ROADMAP_BYTES.replace(b"STATUS: LOCKED", b"STATUS: DRAFT")
    roadmap = _parse_bytes(payload)
    binding = _binding(roadmap=roadmap)
    with pytest.raises(RoadmapGovernanceError, match="DRAFT is not executable"):
        validate_task_binding(
            _task(binding),
            binding,
            roadmap,
            context_refs=({"path": H_SERIES_ROADMAP_PATH, "blob_sha": roadmap.roadmap_blob_sha},),
            migration_approved=True,
        )


@pytest.mark.parametrize(
    "mutation,error",
    [
        (lambda b: b + b"\n### H0 - Duplicate\n\nCAPABILITY_ID: H0_DUP\n\nREQUIREMENTS:\n- H0.R9 - duplicate\n", "Duplicate milestone"),
        (lambda b: b.replace(b"CAPABILITY_ID: H1_REPOSITORY_EXPERIENCE_MANIFEST", b"CAPABILITY_ID: H0_BOUNDARY_CONTRACT"), "Duplicate capability"),
        (lambda b: b.replace(b"H1.R1 \xe2\x80\x94", b"H0.R9 \xe2\x80\x94"), "wrong milestone"),
        (lambda b: b.replace(b"H1.R1 \xe2\x80\x94", b"H1.R2 \xe2\x80\x94"), "Duplicate requirement"),
    ],
)
def test_malformed_or_duplicate_canonical_identities_rejected(mutation, error: str) -> None:
    payload = mutation(ROADMAP_BYTES)
    with pytest.raises(RoadmapGovernanceError, match=error):
        _parse_bytes(payload)


def test_h_series_missing_binding_and_undeclared_h9_fail_closed() -> None:
    decision = evaluate_roadmap_preflight(
        _task(None),
        context_refs=({"path": H_SERIES_ROADMAP_PATH, "blob_sha": H_SERIES_ROADMAP_BLOB_SHA},),
        roadmap_resolver=_resolver,
    )
    assert decision.allowed is False
    assert decision.reason is RoadmapPreflightReason.ROADMAP_BINDING_FAILED

    roadmap = _parse_bytes()
    h9 = _binding(roadmap=roadmap, milestone="H9")
    decision = evaluate_roadmap_preflight(
        _task(h9, milestone="H9"),
        context_refs=({"path": H_SERIES_ROADMAP_PATH, "blob_sha": H_SERIES_ROADMAP_BLOB_SHA},),
        roadmap_resolver=_resolver,
    )
    assert decision.allowed is False
    assert "undeclared H milestone" in decision.message.lower() or "Undeclared roadmap milestone" in decision.message


def test_exact_task_binding_and_authoring_integration_pass() -> None:
    binding = _binding()
    task = _task(binding)
    parsed = parse_roadmap_task_binding(task)
    assert parsed == binding
    decision = evaluate_roadmap_preflight(
        task,
        context_refs=({"path": H_SERIES_ROADMAP_PATH, "blob_sha": H_SERIES_ROADMAP_BLOB_SHA},),
        roadmap_resolver=_resolver,
    )
    assert decision.allowed is True
    assert decision.reason is RoadmapPreflightReason.ROADMAP_BINDING_VALID

    result = preflight_executable_artifact(
        task,
        work_path=".ai/tasks/TASK-100.md",
        operation=ExecutionOperation.RUN,
        selected_executor="codex",
        roadmap_resolver=_resolver,
    )
    assert result.roadmap_decision is not None
    assert result.roadmap_decision.allowed is True


def test_governed_authoring_requires_exact_roadmap_resolver() -> None:
    with pytest.raises(ExecutableArtifactPreflightError, match="ROADMAP_BINDING_FAILED"):
        preflight_executable_artifact(
            _task(_binding()),
            work_path=".ai/tasks/TASK-100.md",
            operation=ExecutionOperation.RUN,
            selected_executor="codex",
        )


@pytest.mark.parametrize(
    "binding_change,message",
    [
        ({"roadmap_blob_sha": "0" * 40}, "registered roadmap blob"),
        ({"roadmap_fingerprint": "0" * 64}, "roadmap_fingerprint mismatch"),
        ({"capability_id": "H1_REPOSITORY_EXPERIENCE_MANIFEST"}, "capability mismatch"),
        ({"requirement_bindings": ("H1.R1",)}, "wrong milestone"),
    ],
)
def test_task_binding_drift_rejected(binding_change: dict, message: str) -> None:
    binding = replace(_binding(), **binding_change)
    decision = evaluate_roadmap_preflight(
        _task(binding),
        context_refs=({"path": H_SERIES_ROADMAP_PATH, "blob_sha": H_SERIES_ROADMAP_BLOB_SHA},),
        roadmap_resolver=_resolver,
    )
    assert decision.allowed is False
    assert message.lower() in decision.message.lower()


def test_binding_json_duplicate_semantic_field_rejected() -> None:
    binding = _binding()
    payload = json.dumps(binding.to_dict(), separators=(",", ":"))
    payload = payload[:-1] + ',"milestone":"H0"}'
    task = _task(None).replace("\nEXECUTOR_CONTEXT", f"\nROADMAP_BINDING_JSON: {payload}\nEXECUTOR_CONTEXT")
    with pytest.raises(RoadmapGovernanceError, match="Duplicate ROADMAP_BINDING_JSON field"):
        parse_roadmap_task_binding(task)


def test_roadmap_context_ref_is_exact_and_required() -> None:
    roadmap = _parse_bytes()
    binding = _binding(roadmap=roadmap)
    task = _task(binding)
    with pytest.raises(RoadmapGovernanceError, match="context ref missing"):
        validate_task_binding(task, binding, roadmap, context_refs=())
    with pytest.raises(RoadmapGovernanceError, match="context ref blob mismatch"):
        validate_task_binding(
            task,
            binding,
            roadmap,
            context_refs=({"path": H_SERIES_ROADMAP_PATH, "blob_sha": "0" * 40},),
        )
    with pytest.raises(RoadmapGovernanceError, match="context path mismatch"):
        validate_task_binding(
            task,
            binding,
            roadmap,
            context_refs=({"path": ".ai/roadmaps/wrong.md", "blob_sha": H_SERIES_ROADMAP_BLOB_SHA},),
        )


def test_task_pass_does_not_imply_completion_and_exact_completion_passes() -> None:
    roadmap = _parse_bytes()
    assert may_open_milestone(roadmap, "H1", ()).allowed is False
    record = _complete(roadmap, "H0")
    assert validate_milestone_completion(record, roadmap).allowed is True
    assert may_open_milestone(roadmap, "H1", (record,)).allowed is True


def test_completion_rejects_missing_requirement_blocker_and_bad_fingerprint() -> None:
    roadmap = _parse_bytes()
    complete = _complete(roadmap, "H0")
    missing = MilestoneCompletionRecord.create(
        roadmap=roadmap,
        milestone="H0",
        requirement_evidence={"H0.R1": "reviewed evidence"},
    )
    assert validate_milestone_completion(missing, roadmap).allowed is False
    blocked = MilestoneCompletionRecord.create(
        roadmap=roadmap,
        milestone="H0",
        requirement_evidence=dict(complete.requirement_evidence),
        unresolved_blockers=("review blocker",),
    )
    assert validate_milestone_completion(blocked, roadmap).allowed is False
    tampered = replace(complete, record_fingerprint="0" * 64)
    assert validate_milestone_completion(tampered, roadmap).allowed is False


def test_later_milestone_requires_all_linear_predecessor_completions() -> None:
    roadmap = _parse_bytes()
    h0 = _complete(roadmap, "H0")
    assert may_open_milestone(roadmap, "H2", (h0,)).allowed is False
    h1 = _complete(roadmap, "H1")
    assert may_open_milestone(roadmap, "H2", (h0, h1)).allowed is True


def test_authoring_requires_authoritative_completion_artifact_for_later_milestone() -> None:
    roadmap = _parse_bytes()
    task = _task(_binding(roadmap=roadmap, milestone="H1"), milestone="H1")
    with pytest.raises(ExecutableArtifactPreflightError, match="authoritative control-plane"):
        preflight_executable_artifact(
            task,
            work_path=".ai/tasks/TASK-100.md",
            operation=ExecutionOperation.RUN,
            selected_executor="codex",
            roadmap_resolver=_resolver,
        )

    completion_path = milestone_completion_artifact_path(roadmap)
    result = preflight_executable_artifact(
        task,
        work_path=".ai/tasks/TASK-100.md",
        operation=ExecutionOperation.RUN,
        selected_executor="codex",
        roadmap_resolver=_resolver,
        milestone_completion_resolver=lambda path: (
            _completion_artifact(roadmap, (_complete(roadmap, "H0"),))
            if path == completion_path
            else b""
        ),
    )
    assert result.roadmap_decision is not None
    assert result.roadmap_decision.allowed is True


def test_completion_artifact_rejects_stale_duplicate_malformed_and_incomplete_records() -> None:
    roadmap = _parse_bytes()
    complete = _complete(roadmap, "H0")
    assert parse_milestone_completion_records(
        _completion_artifact(roadmap, (complete,)), roadmap=roadmap
    ) == (complete,)

    with pytest.raises(RoadmapGovernanceError, match="Duplicate completion record"):
        parse_milestone_completion_records(
            _completion_artifact(roadmap, (complete, complete)), roadmap=roadmap
        )

    stale = json.loads(_completion_artifact(roadmap, (complete,)))
    stale["roadmap_fingerprint"] = "0" * 64
    with pytest.raises(RoadmapGovernanceError, match="roadmap_fingerprint mismatch"):
        parse_milestone_completion_records(
            json.dumps(stale).encode("utf-8"), roadmap=roadmap
        )

    incomplete = MilestoneCompletionRecord.create(
        roadmap=roadmap,
        milestone="H0",
        requirement_evidence={"H0.R1": "reviewed"},
    )
    with pytest.raises(RoadmapGovernanceError, match="Invalid completion record"):
        parse_milestone_completion_records(
            _completion_artifact(roadmap, (incomplete,)), roadmap=roadmap
        )

    with pytest.raises(RoadmapGovernanceError, match="Malformed milestone completion"):
        parse_milestone_completion_records(b"{not-json", roadmap=roadmap)


def test_bridge_run_and_e4_paths_reject_missing_authoritative_progression(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    roadmap = _parse_bytes()
    task = _task(_binding(roadmap=roadmap, milestone="H1"), milestone="H1")
    task_blob = git_blob_sha(task.encode("utf-8"))
    mutations: list[str] = []
    runtime = tmp_path / "runtime"
    runtime.mkdir()

    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: {
        "remote": "origin",
        "control_branch": "ai-control",
        "base_branch": "main",
        "task_branch_prefix": "ai/task-",
    })
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "get_runtime_paths", lambda repo_root=None: {
        "root": runtime,
        "seen": runtime / "seen.json",
        "inbox": runtime / "inbox",
    })
    monkeypatch.setattr(bridge, "get_remote_blob_sha", lambda cfg, path: task_blob)
    monkeypatch.setattr(bridge, "read_remote_file", lambda cfg, path: task)
    monkeypatch.setattr(bridge, "resolve_control_commit_sha", lambda cfg: "c" * 40)
    monkeypatch.setattr(
        bridge,
        "resolve_git_blob_sha",
        lambda ref, path: task_blob if path.endswith("TASK-100.md") else H_SERIES_ROADMAP_BLOB_SHA,
    )
    monkeypatch.setattr(
        bridge,
        "read_git_blob_bytes",
        lambda ref, path: task.encode("utf-8") if path.endswith("TASK-100.md") else ROADMAP_BYTES,
    )
    monkeypatch.setattr(bridge, "resolve_exact_roadmap_bytes", lambda ref, path, blob: ROADMAP_BYTES)
    monkeypatch.setattr(
        bridge,
        "resolve_exact_control_artifact_bytes",
        lambda ref, path: (_ for _ in ()).throw(
            ContinuityStateValidationError("completion artifact missing")
        ),
    )
    monkeypatch.setattr(
        bridge,
        "prepare_task_branch",
        lambda *args: mutations.append("prepare") or "ai/task-100",
    )

    with pytest.raises(SystemExit):
        bridge.cmd_handoff(SimpleNamespace(
            task_id=100,
            action="run",
            executor="codex",
        ))
    assert mutations == []

    monkeypatch.setattr(bridge, "remote_ref", lambda cfg: "ai-control")
    monkeypatch.setattr(
        bridge,
        "_run_git_binary",
        lambda *args: SimpleNamespace(returncode=0, stdout=("c" * 40 + "\n").encode(), stderr=b""),
    )
    auth = {
        "artifact_path": ".ai/tasks/TASK-100.md",
        "artifact_blob_sha": task_blob,
        "action": "RUN",
        "executor_id": "codex",
    }
    with pytest.raises(ContinuityStateValidationError, match="MILESTONE_OPEN_BLOCKED"):
        bridge.resolve_e4_control_snapshot({}, auth)


@pytest.mark.parametrize(
    "case",
    ("exact", "missing_task", "task_blob_drift", "roadmap_mismatch"),
)
def test_bridge_governed_fix_uses_exact_original_task_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    roadmap = _parse_bytes()
    binding = _binding(roadmap=roadmap, milestone="H0")
    task = _task(binding, milestone="H0")
    task_blob = git_blob_sha(task.encode("utf-8"))
    review = _fix_review(
        roadmap,
        binding,
        task_blob,
        task_ref_blob_sha="0" * 40 if case == "task_blob_drift" else None,
        roadmap_id="WRONG-ROADMAP" if case == "roadmap_mismatch" else None,
    )
    review_blob = git_blob_sha(review.encode("utf-8"))
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    reached_prepare: list[bool] = []

    monkeypatch.setattr(bridge, "ensure_git", lambda: None)
    monkeypatch.setattr(bridge, "ensure_dirs", lambda: None)
    monkeypatch.setattr(bridge, "load_config", lambda: {
        "remote": "origin",
        "control_branch": "ai-control",
        "base_branch": "main",
        "task_branch_prefix": "ai/task-",
    })
    monkeypatch.setattr(bridge, "fetch_control", lambda cfg: None)
    monkeypatch.setattr(bridge, "get_runtime_paths", lambda repo_root=None: {
        "root": runtime,
        "seen": runtime / "seen.json",
        "inbox": runtime / "inbox",
    })

    def remote_blob(_cfg, path: str):
        if path.endswith("REVIEW-100.md"):
            return review_blob
        if path.endswith("TASK-100.md"):
            return None if case == "missing_task" else task_blob
        return None

    monkeypatch.setattr(bridge, "get_remote_blob_sha", remote_blob)
    monkeypatch.setattr(
        bridge,
        "read_remote_file",
        lambda cfg, path: review if path.endswith("REVIEW-100.md") else task,
    )
    monkeypatch.setattr(bridge, "resolve_control_commit_sha", lambda cfg: "c" * 40)
    monkeypatch.setattr(
        bridge,
        "resolve_git_blob_sha",
        lambda ref, path: review_blob if path.endswith("REVIEW-100.md") else task_blob,
    )
    monkeypatch.setattr(
        bridge,
        "read_git_blob_bytes",
        lambda ref, path: review.encode("utf-8") if path.endswith("REVIEW-100.md") else task.encode("utf-8"),
    )
    monkeypatch.setattr(bridge, "resolve_exact_roadmap_bytes", lambda ref, path, blob: ROADMAP_BYTES)
    monkeypatch.setattr(
        bridge,
        "get_artifact_path",
        lambda path: tmp_path / "cache" / path,
    )

    class ReachedPrepare(Exception):
        pass

    def prepare(*args):
        reached_prepare.append(True)
        raise ReachedPrepare

    monkeypatch.setattr(bridge, "prepare_task_branch", prepare)
    args = SimpleNamespace(task_id=100, action="fix", executor="codex")
    if case == "exact":
        with pytest.raises(ReachedPrepare):
            bridge.cmd_handoff(args)
        assert reached_prepare == [True]
    else:
        with pytest.raises(SystemExit):
            bridge.cmd_handoff(args)
        assert reached_prepare == []


def test_controlled_evolution_semantics_and_impact_cone() -> None:
    roadmap = _parse_bytes()
    refinement = validate_controlled_evolution(RoadmapEvolutionRequest(
        change_class=RoadmapChangeClass.IMPLEMENTATION_REFINEMENT,
        current_roadmap=roadmap,
    ))
    assert refinement.allowed is True

    extension = validate_controlled_evolution(RoadmapEvolutionRequest(
        change_class=RoadmapChangeClass.CAPABILITY_EXTENSION,
        current_roadmap=roadmap,
        canonical_requirement_identity_changed=True,
    ))
    assert extension.allowed is False

    same_version_upgrade = validate_controlled_evolution(RoadmapEvolutionRequest(
        change_class=RoadmapChangeClass.ARCHITECTURAL_UPGRADE,
        current_roadmap=roadmap,
        proposed_roadmap=roadmap,
        canonical_requirement_identity_changed=True,
        human_approved=True,
        approved_change_id="ADR-999",
    ))
    assert same_version_upgrade.allowed is False
    assert impact_cone(roadmap, "H4") == ("H4", "H5", "H6", "H7", "H8")


def test_review_merge_gate_requires_exact_roadmap_audit() -> None:
    roadmap = _parse_bytes()
    binding = _binding(roadmap=roadmap)
    missing = evaluate_merge_gate(_review_input(binding, roadmap, None))
    assert missing.reason is MergeGateReason.ROADMAP_AUDIT_MISSING

    wrong_roadmap = evaluate_merge_gate(_review_input(
        binding, roadmap, _audit(binding, roadmap_fingerprint="0" * 64)
    ))
    assert wrong_roadmap.reason is MergeGateReason.ROADMAP_IDENTITY_MISMATCH

    wrong_capability = evaluate_merge_gate(_review_input(
        binding, roadmap, _audit(binding, capability_id="H1_REPOSITORY_EXPERIENCE_MANIFEST")
    ))
    assert wrong_capability.reason is MergeGateReason.ROADMAP_CAPABILITY_MISMATCH

    exact = evaluate_merge_gate(_review_input(binding, roadmap, _audit(binding)))
    assert exact.eligible is True
    assert exact.reason is MergeGateReason.PASS_ELIGIBLE


def test_legacy_non_governed_task_compatibility() -> None:
    legacy = _task(None, milestone="LEGACY", class_value="LEGACY BRIDGE TASK")
    assert task_requires_roadmap_governance(legacy) is False
    decision = evaluate_roadmap_preflight(
        legacy,
        context_refs=({"path": ".ai/decisions/legacy.md", "blob_sha": "1" * 40},),
        roadmap_resolver=None,
    )
    assert decision.allowed is True
    assert decision.reason is RoadmapPreflightReason.NOT_GOVERNED


def test_governance_module_has_no_network_llm_provider_or_authority_io() -> None:
    import src.aios_bridge.roadmap_governance as module

    source = inspect.getsource(module).lower()
    for forbidden_import in ("import requests", "import httpx", "import openai", "import subprocess", "import pathlib"):
        assert forbidden_import not in source
    assert "executor_id" not in source
    assert "paid_api" not in source
