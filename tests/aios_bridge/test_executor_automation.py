from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
    ExecutorCapabilities,
)
from src.aios_bridge.continuity.lease import ExecutorLease
from src.aios_bridge.continuity.state import ArtifactRef, ContinuityPhase, FreshnessStatus, check_freshness, StateObservation
from src.aios_bridge.executor_automation import (
    EXECUTOR_ALLOWED_PATHS_MARKER,
    EXECUTOR_CONTEXT_REFS_MARKER,
    build_executor_automation_launch_plan,
    build_published_execution_result,
    derive_executor_automation_ids,
    parse_executor_automation_markers,
    validate_executor_worktree_delta,
)
from src.aios_bridge.executor_context import ExecutorAuthorizationBinding


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def marker_text(context: str | None = None, allowed: str | None = None) -> str:
    context = context or '[{"path":".ai/decisions/ADR-032.md","blob_sha":"' + "a" * 40 + '"}]'
    allowed = allowed or '["bridge.py","src/aios_bridge/executor_automation.py"]'
    return f"{EXECUTOR_CONTEXT_REFS_MARKER} {context}\n{EXECUTOR_ALLOWED_PATHS_MARKER} {allowed}\n"


def launch_fixture(operation: ExecutionOperation = ExecutionOperation.RUN):
    task_id = "TASK-043"
    workspace_id = "c" * 64
    execution_fingerprint = "d" * 64
    lease = ExecutorLease(
        schema_version="1",
        lease_id="lease-task-043-abc123",
        task_id=task_id,
        workspace_id=workspace_id,
        executor_id="codex",
        operation=operation,
        execution_fingerprint=execution_fingerprint,
    )
    if operation is ExecutionOperation.RUN:
        work_path = ".ai/tasks/TASK-043.md"
        work_bytes = b"TASK\r\n"
        context_specs = [(".ai/decisions/ADR-032.md", b"ADR\n")]
        prior_result = None
    else:
        work_path = ".ai/reviews/REVIEW-043.md"
        work_bytes = b"REVIEW\n"
        context_specs = [
            (".ai/tasks/TASK-043.md", b"TASK\n"),
            (".ai/decisions/ADR-032.md", b"ADR\n"),
        ]
        prior_result = ArtifactRef(
            path=".ai/results/RESULT-043.md",
            ref="b" * 40,
            blob_sha="e" * 40,
        )
    work_ref = ArtifactRef(path=work_path, ref="9" * 40, blob_sha=git_blob(work_bytes))
    context_refs = tuple(
        ArtifactRef(path=path, ref="9" * 40, blob_sha=git_blob(payload))
        for path, payload in context_specs
    )
    payloads = {work_path: work_bytes, **dict(context_specs)}
    binding = ExecutorAuthorizationBinding(
        schema_version="1",
        task_id=task_id,
        operation=operation,
        executor_id="codex",
        target_branch="ai/task-043",
        artifact_path=work_ref.path,
        artifact_blob_sha=work_ref.blob_sha,
        lease_id=lease.lease_id,
        lease_fingerprint=lease.fingerprint(),
        workspace_id=workspace_id,
        execution_fingerprint=execution_fingerprint,
    )
    capabilities = ExecutorCapabilities(
        executor_id="codex",
        supported_operations=(ExecutionOperation.RUN, ExecutionOperation.FIX),
        supported_capabilities=(ExecutionCapability.FILESYSTEM_WRITE,),
    )
    kwargs = dict(
        task_id=task_id,
        operation=operation,
        executor_id="codex",
        main_branch="main",
        main_sha="a" * 40,
        target_branch="ai/task-043",
        task_head_sha="b" * 40,
        work_ref=work_ref,
        context_refs=context_refs,
        prior_result_ref=prior_result,
        required_capabilities=(ExecutionCapability.FILESYSTEM_WRITE,),
        executor_capabilities=capabilities,
        executor_lease=lease,
        authorization_binding=binding,
        artifact_payloads=payloads,
        transport_id="codex-local-v1",
    )
    return kwargs


def test_valid_markers_preserve_order():
    parsed = parse_executor_automation_markers(marker_text(), work_path=".ai/tasks/TASK-043.md")
    assert parsed.context_refs[0].path == ".ai/decisions/ADR-032.md"
    assert parsed.allowed_paths == ("bridge.py", "src/aios_bridge/executor_automation.py")


@pytest.mark.parametrize(
    "content",
    [
        EXECUTOR_ALLOWED_PATHS_MARKER + ' ["bridge.py"]',
        marker_text() + EXECUTOR_CONTEXT_REFS_MARKER + " []\n",
        marker_text(context="{}"),
        marker_text(context="[]"),
        marker_text(context='[{"path":".ai/x.md","blob_sha":"ABC"}]'),
        marker_text(context='[{"path":".ai/tasks/TASK-043.md","blob_sha":"' + "a" * 40 + '"}]'),
        marker_text(allowed='[".git/config"]'),
        marker_text(allowed='[".ai/results/RESULT-043.md"]'),
        marker_text(allowed='["a\\\\b.py"]'),
        marker_text(allowed='["a/../b.py"]'),
    ],
)
def test_marker_fail_closed_cases(content):
    with pytest.raises(ContinuityStateValidationError):
        parse_executor_automation_markers(content, work_path=".ai/tasks/TASK-043.md")


def test_deterministic_ids_use_lease_prefix():
    ids = derive_executor_automation_ids("TASK-043", "a" * 64)
    assert ids.request_id == "req-task-043-aaaaaaaaaaaaaaaa"
    assert ids.execution_id == "exec-task-043-aaaaaaaaaaaaaaaa"
    assert ids.invocation_id == "invoke-task-043-aaaaaaaaaaaaaaaa"
    assert ids == derive_executor_automation_ids("TASK-043", "a" * 64)


@pytest.mark.parametrize("operation", [ExecutionOperation.RUN, ExecutionOperation.FIX])
def test_launch_plan_reuses_m1_m4_e3_and_is_deterministic(operation):
    kwargs = launch_fixture(operation)
    first = build_executor_automation_launch_plan(**kwargs)
    second = build_executor_automation_launch_plan(**kwargs)
    assert first == second
    assert first.continuity_state.phase is (
        ContinuityPhase.RUNNING if operation is ExecutionOperation.RUN else ContinuityPhase.FIXING
    )
    observation = StateObservation(
        main_sha=kwargs["main_sha"],
        task_branch_sha=kwargs["task_head_sha"],
        artifact_blobs={
            ref.path: ref.blob_sha
            for ref in (
                first.continuity_state.artifacts.task,
                *first.continuity_state.artifacts.contracts,
                *(() if first.continuity_state.artifacts.result is None else (first.continuity_state.artifacts.result,)),
                *(() if first.continuity_state.artifacts.review is None else (first.continuity_state.artifacts.review,)),
            )
        },
    )
    assert check_freshness(first.continuity_state, observation).status is FreshnessStatus.FRESH
    assert first.context_pack.invocation.request_fingerprint == first.execution_request.fingerprint()
    assert first.context_pack.invocation.prepared_execution_fingerprint == first.prepared_execution.fingerprint()


def test_fix_requires_task_context():
    kwargs = launch_fixture(ExecutionOperation.FIX)
    kwargs["context_refs"] = kwargs["context_refs"][1:]
    kwargs["artifact_payloads"] = {
        key: value for key, value in kwargs["artifact_payloads"].items() if key != ".ai/tasks/TASK-043.md"
    }
    with pytest.raises(ContinuityStateValidationError, match="TASK ref"):
        build_executor_automation_launch_plan(**kwargs)


def test_launch_rejects_ineligible_executor():
    kwargs = launch_fixture()
    kwargs["executor_capabilities"] = ExecutorCapabilities(
        executor_id="codex",
        supported_operations=(ExecutionOperation.RUN,),
        supported_capabilities=(),
    )
    with pytest.raises(ContinuityStateValidationError, match="missing required capabilities"):
        build_executor_automation_launch_plan(**kwargs)


def test_worktree_delta_accepts_exact_scope_and_sorts():
    assert validate_executor_worktree_delta(
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("z.py", "a.py"),
        allowed_paths=("a.py", "z.py"),
    ) == ("a.py", "z.py")


@pytest.mark.parametrize(
    "updates",
    [
        {"post_branch": "main"},
        {"post_head_sha": "b" * 40},
        {"dirty_paths": ()},
        {"dirty_paths": ("forbidden.py",)},
        {"dirty_paths": ("old.py", "new.py"), "allowed_paths": ("new.py",)},
    ],
)
def test_worktree_delta_blocks_integrity_and_scope_violations(updates):
    values = dict(
        pre_branch="ai/task-043",
        post_branch="ai/task-043",
        pre_head_sha="a" * 40,
        post_head_sha="a" * 40,
        dirty_paths=("a.py",),
        allowed_paths=("a.py",),
    )
    values.update(updates)
    with pytest.raises(ContinuityStateValidationError):
        validate_executor_worktree_delta(**values)


def test_published_result_is_canonical_and_bound_to_request():
    launch = build_executor_automation_launch_plan(**launch_fixture())
    result = build_published_execution_result(
        launch.execution_request,
        published_sha="e" * 40,
        result_ref=ArtifactRef(
            path=".ai/results/RESULT-043.md",
            ref="ai/task-043",
            blob_sha="f" * 40,
        ),
    )
    assert result.implementation_sha == "e" * 40
    assert result.request_id == launch.execution_request.request_id


def test_published_result_rejects_wrong_branch():
    launch = build_executor_automation_launch_plan(**launch_fixture())
    with pytest.raises(ContinuityStateValidationError):
        build_published_execution_result(
            launch.execution_request,
            published_sha="e" * 40,
            result_ref=ArtifactRef(
                path=".ai/results/RESULT-043.md",
                ref="main",
                blob_sha="f" * 40,
            ),
        )


def test_module_imports_remain_pure():
    source_path = Path(__file__).parents[2] / "src" / "aios_bridge" / "executor_automation.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not ({"os", "subprocess", "bridge", "requests", "httpx"} & (imports | imported_from))
