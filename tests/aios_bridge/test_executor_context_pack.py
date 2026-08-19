from __future__ import annotations

import ast
from dataclasses import dataclass, replace
import hashlib
import inspect
import json
from pathlib import Path
from typing import Mapping

import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import (
    ExecutionCapability,
    ExecutionOperation,
    ExecutionRequest,
    PreparedExecution,
)
from src.aios_bridge.continuity.executor_transport import (
    validate_executor_invocation,
    validate_invocation_payload,
)
from src.aios_bridge.continuity.lease import ExecutorLease
from src.aios_bridge.continuity.state import ArtifactRef, SCHEMA_VERSION
from src.aios_bridge import executor_context
from src.aios_bridge.executor_context import (
    ACTIVE_AUTHORIZATION_STATUS,
    CONTEXT_FORMAT_VERSION,
    CONTEXT_INSTRUCTION_PROFILE,
    MAX_CONTEXT_ARTIFACTS,
    MAX_CONTEXT_ARTIFACT_BYTES,
    MAX_CONTEXT_PACK_BYTES,
    MAX_CONTEXT_RAW_ARTIFACT_BYTES,
    ContextArtifactRole,
    ExecutorAuthorizationBinding,
    ExecutorContextPack,
    build_executor_context_pack,
)


CONTROL_REF = "refs/remotes/origin/ai-control"


def _git_blob_sha1(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def _artifact_ref(path: str, content: bytes) -> ArtifactRef:
    return ArtifactRef(path=path, ref=CONTROL_REF, blob_sha=_git_blob_sha1(content))


@dataclass(frozen=True)
class _Fixture:
    request: ExecutionRequest
    prepared: PreparedExecution
    lease: ExecutorLease
    binding: ExecutorAuthorizationBinding
    payloads: dict[str, bytes]

    def build(
        self,
        *,
        payloads: Mapping[str, bytes] | None = None,
        invocation_id: str = "invocation-042",
        transport_id: str = "codex-local-v1",
    ) -> ExecutorContextPack:
        return build_executor_context_pack(
            self.request,
            self.prepared,
            self.lease,
            self.binding,
            self.payloads if payloads is None else payloads,
            invocation_id=invocation_id,
            transport_id=transport_id,
        )


def _fixture(
    operation: ExecutionOperation = ExecutionOperation.RUN,
    *,
    contents: list[bytes] | None = None,
    context_count: int = 2,
) -> _Fixture:
    if contents is None:
        contents = [
            b"# Work artifact\nImplement the bounded task.\n",
            *[f"# Context {index}\nExact context.\n".encode("utf-8") for index in range(context_count)],
        ]
    context_count = len(contents) - 1
    work_path = (
        ".ai/tasks/TASK-042.md"
        if operation is ExecutionOperation.RUN
        else ".ai/reviews/REVIEW-042.md"
    )
    context_paths = [
        ".ai/decisions/ADR-031.md" if index == 0 else f".ai/context/E3-{index}.md"
        for index in range(context_count)
    ]
    work_ref = _artifact_ref(work_path, contents[0])
    context_refs = tuple(
        _artifact_ref(path, content)
        for path, content in zip(context_paths, contents[1:], strict=True)
    )
    request = ExecutionRequest(
        schema_version=SCHEMA_VERSION,
        task_id="TASK-042",
        request_id="request-042",
        executor_id="codex",
        operation=operation,
        state_fingerprint="1" * 64,
        target_branch="ai/task-042",
        expected_task_head_sha="a" * 40,
        work_ref=work_ref,
        context_refs=context_refs,
        required_capabilities=(
            ExecutionCapability.REPOSITORY_READ,
            ExecutionCapability.FILESYSTEM_WRITE,
            ExecutionCapability.SHELL,
            ExecutionCapability.TEST_EXECUTION,
            ExecutionCapability.LOCAL_GIT,
        ),
        expected_result_path=".ai/results/RESULT-042.md",
    )
    prepared = PreparedExecution(
        schema_version=SCHEMA_VERSION,
        task_id=request.task_id,
        request_id=request.request_id,
        executor_id=request.executor_id,
        execution_id="execution-042",
        request_fingerprint=request.fingerprint(),
    )
    lease = ExecutorLease(
        schema_version=SCHEMA_VERSION,
        lease_id="lease-042",
        task_id=request.task_id,
        workspace_id="2" * 64,
        executor_id=request.executor_id,
        operation=request.operation,
        execution_fingerprint="3" * 64,
    )
    binding = ExecutorAuthorizationBinding(
        schema_version=SCHEMA_VERSION,
        task_id=request.task_id,
        operation=request.operation,
        executor_id=request.executor_id,
        target_branch=request.target_branch,
        artifact_path=request.work_ref.path,
        artifact_blob_sha=request.work_ref.blob_sha,
        lease_id=lease.lease_id,
        lease_fingerprint=lease.fingerprint(),
        workspace_id=lease.workspace_id,
        execution_fingerprint=lease.execution_fingerprint,
    )
    ordered_refs = (request.work_ref, *request.context_refs)
    payloads = {ref.path: content for ref, content in zip(ordered_refs, contents, strict=True)}
    return _Fixture(request, prepared, lease, binding, payloads)


@pytest.mark.parametrize("operation", [ExecutionOperation.RUN, ExecutionOperation.FIX])
def test_run_and_fix_packs_are_valid(operation: ExecutionOperation) -> None:
    fixture = _fixture(operation)
    pack = fixture.build()

    assert pack.manifest.operation is operation
    assert pack.manifest.format_version == CONTEXT_FORMAT_VERSION
    assert pack.manifest.instruction_profile == CONTEXT_INSTRUCTION_PROFILE
    assert pack.manifest.task_id == fixture.request.task_id
    assert pack.manifest.request_id == fixture.request.request_id
    assert pack.manifest.executor_id == fixture.request.executor_id
    assert pack.manifest.target_branch == fixture.request.target_branch
    assert pack.manifest.workspace_id == fixture.lease.workspace_id
    assert pack.manifest.execution_id == fixture.prepared.execution_id
    assert pack.manifest.lease_id == fixture.lease.lease_id
    assert pack.manifest.required_capabilities == fixture.request.required_capabilities
    assert pack.manifest.authorization_binding_fingerprint == fixture.binding.fingerprint()
    validate_executor_invocation(
        pack.invocation, fixture.request, fixture.prepared, fixture.lease
    )
    validate_invocation_payload(pack.invocation, pack.payload)


def test_exact_artifact_order_and_roles_follow_request_not_mapping() -> None:
    fixture = _fixture()
    reversed_payloads = dict(reversed(tuple(fixture.payloads.items())))
    pack = fixture.build(payloads=reversed_payloads)
    refs = (fixture.request.work_ref, *fixture.request.context_refs)

    assert [entry.path for entry in pack.manifest.artifacts] == [ref.path for ref in refs]
    assert [entry.ordinal for entry in pack.manifest.artifacts] == [0, 1, 2]
    assert [entry.role for entry in pack.manifest.artifacts] == [
        ContextArtifactRole.WORK,
        ContextArtifactRole.CONTEXT,
        ContextArtifactRole.CONTEXT,
    ]
    positions = [pack.payload.index(f"PATH: {ref.path}".encode("utf-8")) for ref in refs]
    assert positions == sorted(positions)


def test_mapping_order_independence_and_repeat_build_determinism() -> None:
    fixture = _fixture()
    first = fixture.build()
    second = fixture.build(payloads=dict(reversed(tuple(fixture.payloads.items()))))
    third = fixture.build()

    assert first.payload == second.payload == third.payload
    assert first.manifest.to_canonical_json() == second.manifest.to_canonical_json()
    assert first.manifest.fingerprint() == second.manifest.fingerprint()
    assert first.invocation.fingerprint() == second.invocation.fingerprint()


def test_payload_and_invocation_are_exactly_content_addressed() -> None:
    fixture = _fixture()
    pack = fixture.build()

    assert pack.invocation.payload_sha256 == hashlib.sha256(pack.payload).hexdigest()
    assert pack.invocation.payload_size_bytes == len(pack.payload)
    assert pack.manifest.request_fingerprint == fixture.request.fingerprint()
    assert pack.manifest.prepared_execution_fingerprint == fixture.prepared.fingerprint()
    assert pack.manifest.lease_fingerprint == fixture.lease.fingerprint()
    assert json.loads(pack.manifest.to_canonical_json()) == pack.manifest.to_dict()
    assert pack.manifest.fingerprint() == hashlib.sha256(
        pack.manifest.to_canonical_json().encode("utf-8")
    ).hexdigest()


def test_crlf_bom_and_trailing_spaces_are_preserved_as_exact_bytes() -> None:
    exact = b"\xef\xbb\xbf# Work\r\nline with spaces   \r\nlast-space "
    fixture = _fixture(contents=[exact, b"context\r\n"])
    pack = fixture.build()
    entry = pack.manifest.artifacts[0]

    assert b"CONTENT_BEGIN\n" + exact + b"\nCONTENT_END" in pack.payload
    assert entry.size_bytes == len(exact)
    assert entry.content_sha256 == hashlib.sha256(exact).hexdigest()
    assert entry.blob_sha == _git_blob_sha1(exact)


def test_fixed_authority_and_thin_executor_instructions_appear_once() -> None:
    payload = _fixture().build().payload
    assert payload.count(b"AUTHORITY NOTICE") == 1
    assert payload.count(b"THIN EXECUTOR RULES") == 1
    assert payload.count(b"pack itself does not grant or extend RUN, FIX, or MERGE authority") == 1
    assert payload.startswith(b"AIOS_EXECUTOR_CONTEXT_PACK_V1\n")
    assert payload.endswith(b"AIOS_EXECUTOR_CONTEXT_PACK_END\n")


def test_git_blob_sha1_is_exact_and_wrong_bytes_fail() -> None:
    assert executor_context._git_blob_sha1(b"test content\n") == "d670460b4b4aece5915caf5c68d12f560a9fe3e4"
    fixture = _fixture()
    wrong = dict(fixture.payloads)
    wrong[fixture.request.work_ref.path] += b"mutation"
    with pytest.raises(ContinuityStateValidationError):
        fixture.build(payloads=wrong)


@pytest.mark.parametrize("missing_index", [0, 1])
def test_missing_artifact_fails_closed(missing_index: int) -> None:
    fixture = _fixture()
    payloads = dict(fixture.payloads)
    payloads.pop(tuple(payloads)[missing_index])
    with pytest.raises(ContinuityStateValidationError):
        fixture.build(payloads=payloads)


def test_extra_artifact_fails_closed() -> None:
    fixture = _fixture()
    payloads = dict(fixture.payloads)
    payloads[".ai/context/EXTRA.md"] = b"extra\n"
    with pytest.raises(ContinuityStateValidationError):
        fixture.build(payloads=payloads)


def test_non_string_mapping_key_fails_closed() -> None:
    fixture = _fixture()
    payloads: dict[object, bytes] = dict(fixture.payloads)
    payloads[7] = b"extra\n"
    with pytest.raises(ContinuityStateValidationError):
        fixture.build(payloads=payloads)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"\xffinvalid-utf8",
        b"contains\x00nul",
    ],
)
def test_unsafe_artifact_content_fails_closed(content: bytes) -> None:
    fixture = _fixture(contents=[content])
    with pytest.raises(ContinuityStateValidationError):
        fixture.build()


def test_bytearray_artifact_fails_closed() -> None:
    fixture = _fixture(contents=[b"exact bytes\n"])
    payloads: dict[str, object] = {
        fixture.request.work_ref.path: bytearray(b"exact bytes\n")
    }
    with pytest.raises(ContinuityStateValidationError):
        fixture.build(payloads=payloads)  # type: ignore[arg-type]


def test_artifact_count_above_eight_fails_without_omission() -> None:
    fixture = _fixture(context_count=MAX_CONTEXT_ARTIFACTS)
    assert len(fixture.payloads) == MAX_CONTEXT_ARTIFACTS + 1
    with pytest.raises(ContinuityStateValidationError):
        fixture.build()


def test_single_artifact_bound_fails_without_truncation() -> None:
    oversized = b"a" * (MAX_CONTEXT_ARTIFACT_BYTES + 1)
    fixture = _fixture(contents=[oversized])
    with pytest.raises(ContinuityStateValidationError):
        fixture.build()


def test_aggregate_raw_bound_fails_without_truncation() -> None:
    contents = [b"a" * 100_000, b"b" * 100_000]
    assert sum(map(len, contents)) > MAX_CONTEXT_RAW_ARTIFACT_BYTES
    fixture = _fixture(contents=contents)
    with pytest.raises(ContinuityStateValidationError):
        fixture.build()


def test_final_pack_bound_fails_without_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()
    complete = fixture.build()
    monkeypatch.setattr(executor_context, "MAX_CONTEXT_PACK_BYTES", len(complete.payload) - 1)
    with pytest.raises(ContinuityStateValidationError):
        fixture.build()
    assert len(complete.payload) <= MAX_CONTEXT_PACK_BYTES


@pytest.mark.parametrize(
    ("field_name", "drift"),
    [
        ("task_id", "TASK-999"),
        ("operation", ExecutionOperation.FIX),
        ("executor_id", "antigravity"),
        ("target_branch", "ai/other-branch"),
        ("artifact_path", ".ai/tasks/TASK-999.md"),
        ("artifact_blob_sha", "b" * 40),
        ("lease_id", "lease-other"),
        ("lease_fingerprint", "4" * 64),
        ("workspace_id", "5" * 64),
        ("execution_fingerprint", "6" * 64),
    ],
)
def test_authorization_binding_drift_fails_closed(
    field_name: str, drift: object
) -> None:
    fixture = _fixture()
    binding = replace(fixture.binding, **{field_name: drift})
    with pytest.raises(ContinuityStateValidationError):
        build_executor_context_pack(
            fixture.request,
            fixture.prepared,
            fixture.lease,
            binding,
            fixture.payloads,
            invocation_id="invocation-042",
            transport_id="codex-local-v1",
        )


@pytest.mark.parametrize("status", ["INACTIVE", "active", " ACTIVE", True, None])
def test_non_active_authorization_binding_is_rejected(status: object) -> None:
    fixture = _fixture()
    with pytest.raises(ContinuityStateValidationError):
        replace(fixture.binding, status=status)  # type: ignore[arg-type]


def test_prepared_request_mismatch_fails_closed() -> None:
    fixture = _fixture()
    prepared = replace(fixture.prepared, request_fingerprint="f" * 64)
    with pytest.raises(ContinuityStateValidationError):
        build_executor_context_pack(
            fixture.request,
            prepared,
            fixture.lease,
            fixture.binding,
            fixture.payloads,
            invocation_id="invocation-042",
            transport_id="codex-local-v1",
        )


@pytest.mark.parametrize(
    ("field_name", "drift"),
    [
        ("executor_id", "antigravity"),
        ("operation", ExecutionOperation.FIX),
        ("workspace_id", "7" * 64),
        ("execution_fingerprint", "8" * 64),
        ("lease_id", "lease-drift"),
    ],
)
def test_lease_request_or_binding_drift_fails_closed(
    field_name: str, drift: object
) -> None:
    fixture = _fixture()
    lease = replace(fixture.lease, **{field_name: drift})
    with pytest.raises(ContinuityStateValidationError):
        build_executor_context_pack(
            fixture.request,
            fixture.prepared,
            lease,
            fixture.binding,
            fixture.payloads,
            invocation_id="invocation-042",
            transport_id="codex-local-v1",
        )


@pytest.mark.parametrize(
    ("invocation_id", "transport_id"),
    [
        ("Bad Invocation", "codex-local-v1"),
        ("invocation-042", "Bad Transport"),
        ("", "codex-local-v1"),
        ("invocation-042", ""),
    ],
)
def test_malformed_invocation_or_transport_ids_are_rejected(
    invocation_id: str, transport_id: str
) -> None:
    fixture = _fixture()
    with pytest.raises(ContinuityStateValidationError):
        fixture.build(invocation_id=invocation_id, transport_id=transport_id)


def test_authorization_binding_contains_only_locked_evidence_fields() -> None:
    binding = _fixture().binding
    assert binding.status == ACTIVE_AUTHORIZATION_STATUS
    assert set(binding.to_dict()) == {
        "schema_version",
        "task_id",
        "operation",
        "executor_id",
        "target_branch",
        "artifact_path",
        "artifact_blob_sha",
        "lease_id",
        "lease_fingerprint",
        "workspace_id",
        "execution_fingerprint",
        "status",
    }
    assert json.loads(binding.to_canonical_json()) == binding.to_dict()


def test_public_builder_has_no_free_form_or_runtime_parameters() -> None:
    parameters = set(inspect.signature(build_executor_context_pack).parameters)
    assert parameters == {
        "execution_request",
        "prepared_execution",
        "executor_lease",
        "authorization_binding",
        "artifact_payloads",
        "invocation_id",
        "transport_id",
    }
    assert parameters.isdisjoint(
        {
            "prompt",
            "extra_prompt",
            "system_prompt",
            "instructions",
            "callback",
            "transport",
            "model",
        }
    )


def test_production_module_is_pure_and_has_no_transport_call() -> None:
    source = Path(executor_context.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)

    assert imported_roots.isdisjoint(
        {
            "os",
            "pathlib",
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "bridge",
            "runtime_dispatch",
            "runtime_lease",
            "executor_transports",
            "providers",
            "external_brain",
            "openai",
            "anthropic",
            "google",
            "browser",
        }
    )
    assert called_names.isdisjoint(
        {
            "approve",
            "publish",
            "commit",
            "push",
            "merge",
            "invoke",
            "Popen",
            "system",
            "checkout",
            "reset",
            "stash",
            "clean",
            "open",
        }
    )
