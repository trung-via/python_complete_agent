from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import inspect
import json

import pytest

from src.aios_bridge.continuity import (
    MAX_INVOCATION_PAYLOAD_BYTES,
    SCHEMA_VERSION,
    ArtifactRef,
    ExecutionCapability,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionTransport,
    ExecutorInvocation,
    ExecutorLease,
    InvocationReceipt,
    InvocationStatus,
    PreparedExecution,
    validate_executor_invocation,
    validate_invocation_payload,
    validate_invocation_receipt,
    validate_transport_binding,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
import src.aios_bridge.continuity.executor_transport as transport_module


PAYLOAD = b"bounded executor invocation payload\n"
WORKSPACE_FP = "1" * 64
EXECUTION_FP = "2" * 64


def make_request(
    *,
    task_id="TASK-040",
    request_id="request-task-040-01",
    executor_id="executor-a",
    operation=ExecutionOperation.RUN,
    target_branch="ai/task-040",
):
    task_number = task_id.split("-", 1)[1]
    if operation == ExecutionOperation.FIX:
        work_path = f".ai/reviews/REVIEW-{task_number}.md"
    else:
        work_path = f".ai/tasks/{task_id}.md"
    return ExecutionRequest(
        schema_version=SCHEMA_VERSION,
        task_id=task_id,
        request_id=request_id,
        executor_id=executor_id,
        operation=operation,
        state_fingerprint="3" * 64,
        target_branch=target_branch,
        expected_task_head_sha="a" * 40,
        work_ref=ArtifactRef(
            path=work_path,
            ref="refs/remotes/origin/ai-control",
            blob_sha="b" * 40,
        ),
        context_refs=(),
        required_capabilities=(ExecutionCapability.REPOSITORY_READ,),
        expected_result_path=f".ai/results/RESULT-{task_number}.md",
    )


def make_prepared(request=None, *, execution_id="execution-task-040-01"):
    request = request or make_request()
    return PreparedExecution(
        schema_version=request.schema_version,
        task_id=request.task_id,
        request_id=request.request_id,
        executor_id=request.executor_id,
        execution_id=execution_id,
        request_fingerprint=request.fingerprint(),
    )


def make_lease(
    request=None,
    *,
    task_id=None,
    workspace_id=WORKSPACE_FP,
    executor_id=None,
    operation=None,
    execution_fingerprint=EXECUTION_FP,
):
    request = request or make_request()
    return ExecutorLease(
        schema_version=SCHEMA_VERSION,
        lease_id="lease-task-040-abcdef123456",
        task_id=task_id or request.task_id,
        workspace_id=workspace_id,
        executor_id=executor_id or request.executor_id,
        operation=operation or request.operation,
        execution_fingerprint=execution_fingerprint,
    )


def make_invocation(
    request=None,
    prepared=None,
    lease=None,
    *,
    invocation_id="invocation-task-040-01",
    transport_id="transport-a",
    payload=PAYLOAD,
):
    request = request or make_request()
    prepared = prepared or make_prepared(request)
    lease = lease or make_lease(request)
    return ExecutorInvocation(
        schema_version=SCHEMA_VERSION,
        invocation_id=invocation_id,
        task_id=request.task_id,
        request_id=request.request_id,
        executor_id=request.executor_id,
        transport_id=transport_id,
        operation=request.operation,
        workspace_id=lease.workspace_id,
        target_branch=request.target_branch,
        execution_id=prepared.execution_id,
        request_fingerprint=request.fingerprint(),
        prepared_execution_fingerprint=prepared.fingerprint(),
        lease_fingerprint=lease.fingerprint(),
        execution_fingerprint=lease.execution_fingerprint,
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        payload_size_bytes=len(payload),
    )


def make_receipt(
    invocation=None,
    *,
    status=InvocationStatus.EXITED_ZERO,
    exit_code=0,
    error_code=None,
):
    invocation = invocation or make_invocation()
    return InvocationReceipt(
        schema_version=invocation.schema_version,
        invocation_id=invocation.invocation_id,
        task_id=invocation.task_id,
        request_id=invocation.request_id,
        executor_id=invocation.executor_id,
        transport_id=invocation.transport_id,
        operation=invocation.operation,
        execution_id=invocation.execution_id,
        invocation_fingerprint=invocation.fingerprint(),
        status=status,
        exit_code=exit_code,
        error_code=error_code,
    )


class NeutralTransport:
    def __init__(self, transport_id="transport-a", executor_id="executor-a"):
        self._transport_id = transport_id
        self._executor_id = executor_id
        self.invoke_count = 0

    @property
    def transport_id(self):
        return self._transport_id

    @property
    def executor_id(self):
        return self._executor_id

    def invoke(self, invocation, payload):
        self.invoke_count += 1
        return make_receipt(invocation)


@pytest.mark.parametrize("operation", [ExecutionOperation.RUN, ExecutionOperation.FIX])
def test_canonical_invocation_round_trip_for_run_and_fix(operation):
    request = make_request(operation=operation)
    prepared = make_prepared(request)
    lease = make_lease(request)
    invocation = make_invocation(request, prepared, lease)
    from_dict = ExecutorInvocation.from_dict(invocation.to_dict())
    from_json = ExecutorInvocation.from_json(invocation.to_canonical_json().encode("utf-8"))
    assert from_dict == invocation == from_json
    assert from_json.fingerprint() == invocation.fingerprint()
    assert invocation.to_canonical_json() == json.dumps(
        invocation.to_dict(), sort_keys=True, separators=(",", ":")
    )


def test_invocation_binds_exact_request_prepared_and_lease():
    request = make_request()
    prepared = make_prepared(request)
    lease = make_lease(request)
    validate_executor_invocation(make_invocation(request, prepared, lease), request, prepared, lease)


def test_exact_payload_bytes_validate():
    validate_invocation_payload(make_invocation(), PAYLOAD)


@pytest.mark.parametrize(
    ("status", "exit_code", "error_code"),
    [
        (InvocationStatus.EXITED_ZERO, 0, None),
        (InvocationStatus.EXITED_NONZERO, 1, "PROCESS_EXITED_NONZERO"),
        (InvocationStatus.FAILED_TO_START, None, "SPAWN_FAILED"),
        (InvocationStatus.TIMED_OUT, None, "TRANSPORT_TIMEOUT"),
        (InvocationStatus.INTERRUPTED, None, "INTERRUPTED_BY_CALLER"),
    ],
)
def test_every_valid_receipt_status_round_trips_and_binds(status, exit_code, error_code):
    invocation = make_invocation()
    receipt = make_receipt(
        invocation, status=status, exit_code=exit_code, error_code=error_code
    )
    assert InvocationReceipt.from_dict(receipt.to_dict()) == receipt
    assert InvocationReceipt.from_json(receipt.to_canonical_json()) == receipt
    assert len(receipt.fingerprint()) == 64
    validate_invocation_receipt(receipt, invocation)


def test_neutral_protocol_and_second_third_implementations_need_no_core_change():
    first = NeutralTransport("transport-a", "executor-a")
    second = NeutralTransport("transport-b", "executor-b")
    third = NeutralTransport("transport-c", "executor-c")
    assert isinstance(first, ExecutionTransport)
    assert isinstance(second, ExecutionTransport)
    assert isinstance(third, ExecutionTransport)
    validate_transport_binding(first, make_invocation())
    for transport, actor in ((second, "executor-b"), (third, "executor-c")):
        request = make_request(executor_id=actor)
        validate_transport_binding(
            transport,
            make_invocation(
                request,
                make_prepared(request),
                make_lease(request),
                transport_id=transport.transport_id,
            ),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("invocation_id", " invocation-task-040-01"),
        ("invocation_id", "Invocation-1"),
        ("invocation_id", "i" * 65),
        ("task_id", " task-040"),
        ("task_id", "task-040"),
        ("task_id", "TASK-ABC"),
        ("request_id", "request id"),
        ("request_id", "request-a "),
        ("execution_id", "execution/a"),
        ("execution_id", ""),
        ("executor_id", " executor-a"),
        ("executor_id", "executor_a"),
        ("transport_id", "Transport-a"),
        ("transport_id", "transport a"),
        ("transport_id", "t" * 65),
    ],
)
def test_invocation_rejects_noncanonical_or_padded_identity(field, value):
    data = make_invocation().to_dict()
    data[field] = value
    with pytest.raises(ContinuityStateValidationError):
        ExecutorInvocation.from_dict(data)


@pytest.mark.parametrize("operation", ["MERGE", "UNKNOWN", "run", None])
def test_invocation_rejects_merge_or_unknown_operation(operation):
    data = make_invocation().to_dict()
    data["operation"] = operation
    with pytest.raises(ContinuityStateValidationError):
        ExecutorInvocation.from_dict(data)


@pytest.mark.parametrize(
    "field",
    [
        "workspace_id",
        "request_fingerprint",
        "prepared_execution_fingerprint",
        "lease_fingerprint",
        "execution_fingerprint",
        "payload_sha256",
    ],
)
@pytest.mark.parametrize("bad", ["a" * 63, "a" * 65, "A" * 64])
def test_invocation_rejects_malformed_fingerprints(field, bad):
    data = make_invocation().to_dict()
    data[field] = bad
    with pytest.raises(ContinuityStateValidationError):
        ExecutorInvocation.from_dict(data)


@pytest.mark.parametrize("branch", [" ai/task-040", "ai/task-040 ", "../task", "ai//task", "ai/task.lock"])
def test_invocation_rejects_invalid_or_padded_branch(branch):
    data = make_invocation().to_dict()
    data["target_branch"] = branch
    with pytest.raises(ContinuityStateValidationError):
        ExecutorInvocation.from_dict(data)


@pytest.mark.parametrize("size", [0, -1, True, MAX_INVOCATION_PAYLOAD_BYTES + 1])
def test_invocation_rejects_invalid_payload_size(size):
    data = make_invocation().to_dict()
    data["payload_size_bytes"] = size
    with pytest.raises(ContinuityStateValidationError):
        ExecutorInvocation.from_dict(data)


@pytest.mark.parametrize(
    "alternate_request",
    [
        make_request(task_id="TASK-041", target_branch="ai/task-041"),
        make_request(request_id="request-task-040-02"),
        make_request(executor_id="executor-b"),
        make_request(operation=ExecutionOperation.FIX),
        make_request(target_branch="ai/task-040-other"),
    ],
)
def test_invocation_binding_rejects_request_identity_drift(alternate_request):
    invocation = make_invocation()
    with pytest.raises(ContinuityStateValidationError):
        validate_executor_invocation(
            invocation,
            alternate_request,
            make_prepared(alternate_request),
            make_lease(alternate_request),
        )


@pytest.mark.parametrize(
    "prepared",
    [
        replace(make_prepared(), task_id="TASK-041"),
        replace(make_prepared(), request_id="request-task-040-02"),
        replace(make_prepared(), executor_id="executor-b"),
        replace(make_prepared(), request_fingerprint="4" * 64),
        make_prepared(execution_id="execution-task-040-02"),
    ],
)
def test_invocation_binding_rejects_prepared_drift(prepared):
    request = make_request()
    with pytest.raises(ContinuityStateValidationError):
        validate_executor_invocation(make_invocation(), request, prepared, make_lease(request))


def test_invocation_binding_rejects_prepared_fingerprint_mismatch():
    request = make_request()
    prepared = make_prepared(request)
    invocation = replace(make_invocation(request, prepared), prepared_execution_fingerprint="4" * 64)
    with pytest.raises(ContinuityStateValidationError):
        validate_executor_invocation(invocation, request, prepared, make_lease(request))


@pytest.mark.parametrize(
    "lease",
    [
        make_lease(task_id="TASK-041"),
        make_lease(workspace_id="4" * 64),
        make_lease(executor_id="executor-b"),
        make_lease(operation=ExecutionOperation.FIX),
        make_lease(execution_fingerprint="4" * 64),
    ],
)
def test_invocation_binding_rejects_lease_identity_drift(lease):
    request = make_request()
    prepared = make_prepared(request)
    with pytest.raises(ContinuityStateValidationError):
        validate_executor_invocation(make_invocation(request, prepared), request, prepared, lease)


def test_invocation_binding_rejects_lease_fingerprint_mismatch():
    request = make_request()
    prepared = make_prepared(request)
    lease = make_lease(request)
    invocation = replace(make_invocation(request, prepared, lease), lease_fingerprint="4" * 64)
    with pytest.raises(ContinuityStateValidationError):
        validate_executor_invocation(invocation, request, prepared, lease)


@pytest.mark.parametrize("payload", ["text", bytearray(PAYLOAD), memoryview(PAYLOAD), iter(PAYLOAD)])
def test_payload_rejects_non_bytes(payload):
    with pytest.raises(ContinuityStateValidationError):
        validate_invocation_payload(make_invocation(), payload)


def test_payload_rejects_empty_length_hash_and_one_byte_tamper():
    invocation = make_invocation()
    for payload in (b"", PAYLOAD[:-1], PAYLOAD + b"x", PAYLOAD[:-1] + b"X"):
        with pytest.raises(ContinuityStateValidationError):
            validate_invocation_payload(invocation, payload)
    wrong_hash = replace(invocation, payload_sha256="4" * 64)
    with pytest.raises(ContinuityStateValidationError):
        validate_invocation_payload(wrong_hash, PAYLOAD)


def test_payload_rejects_runtime_bytes_over_safety_ceiling():
    oversized = b"x" * (MAX_INVOCATION_PAYLOAD_BYTES + 1)
    with pytest.raises(ContinuityStateValidationError):
        validate_invocation_payload(make_invocation(), oversized)


@pytest.mark.parametrize(
    ("transport_id", "executor_id"),
    [("transport-b", "executor-a"), ("transport-a", "executor-b")],
)
def test_transport_binding_rejects_transport_or_executor_mismatch(transport_id, executor_id):
    with pytest.raises(ContinuityStateValidationError):
        validate_transport_binding(NeutralTransport(transport_id, executor_id), make_invocation())


@pytest.mark.parametrize(
    ("transport_id", "executor_id"),
    [(" transport-a", "executor-a"), ("", "executor-a"), ("transport-a", " executor-a")],
)
def test_transport_binding_rejects_noncanonical_claims(transport_id, executor_id):
    with pytest.raises(ContinuityStateValidationError):
        validate_transport_binding(NeutralTransport(transport_id, executor_id), make_invocation())


def test_transport_binding_never_invokes_transport():
    transport = NeutralTransport()
    validate_transport_binding(transport, make_invocation())
    assert transport.invoke_count == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2"),
        ("invocation_id", "invocation-other"),
        ("task_id", "TASK-041"),
        ("request_id", "request-other"),
        ("executor_id", "executor-b"),
        ("transport_id", "transport-b"),
        ("operation", ExecutionOperation.FIX),
        ("execution_id", "execution-other"),
        ("invocation_fingerprint", "4" * 64),
    ],
)
def test_receipt_binding_rejects_every_identity_drift(field, value):
    invocation = make_invocation()
    data = make_receipt(invocation).to_dict()
    data[field] = value.value if isinstance(value, ExecutionOperation) else value
    if field == "schema_version":
        with pytest.raises(ContinuityStateValidationError):
            InvocationReceipt.from_dict(data)
        return
    receipt = InvocationReceipt.from_dict(data)
    with pytest.raises(ContinuityStateValidationError):
        validate_invocation_receipt(receipt, invocation)


@pytest.mark.parametrize(
    ("exit_code", "error_code"),
    [(None, None), (1, None), (0, "UNEXPECTED_ERROR")],
)
def test_exited_zero_rejects_invalid_payload_matrix(exit_code, error_code):
    with pytest.raises(ContinuityStateValidationError):
        make_receipt(exit_code=exit_code, error_code=error_code)


@pytest.mark.parametrize(
    ("exit_code", "error_code"),
    [
        (None, "PROCESS_ERROR"),
        (0, "PROCESS_ERROR"),
        (True, "PROCESS_ERROR"),
        (-2_147_483_649, "PROCESS_ERROR"),
        (2_147_483_648, "PROCESS_ERROR"),
        (1, None),
        (1, " bad"),
        (1, "bad code"),
        (1, "x" * 65),
    ],
)
def test_exited_nonzero_rejects_invalid_payload_matrix(exit_code, error_code):
    with pytest.raises(ContinuityStateValidationError):
        make_receipt(
            status=InvocationStatus.EXITED_NONZERO,
            exit_code=exit_code,
            error_code=error_code,
        )


@pytest.mark.parametrize(
    "status",
    [
        InvocationStatus.FAILED_TO_START,
        InvocationStatus.TIMED_OUT,
        InvocationStatus.INTERRUPTED,
    ],
)
@pytest.mark.parametrize(
    ("exit_code", "error_code"),
    [(1, "TRANSPORT_ERROR"), (None, None), (None, " bad"), (None, "bad code")],
)
def test_failure_statuses_reject_exit_code_or_missing_malformed_error(
    status, exit_code, error_code
):
    with pytest.raises(ContinuityStateValidationError):
        make_receipt(status=status, exit_code=exit_code, error_code=error_code)


@pytest.mark.parametrize("record_type", [ExecutorInvocation, InvocationReceipt])
def test_unknown_fields_are_rejected(record_type):
    source = make_invocation() if record_type is ExecutorInvocation else make_receipt()
    data = source.to_dict()
    data["unknown"] = "value"
    with pytest.raises(ContinuityStateValidationError):
        record_type.from_dict(data)


@pytest.mark.parametrize("record_type", [ExecutorInvocation, InvocationReceipt])
@pytest.mark.parametrize("field", sorted(transport_module.FORBIDDEN_INVOCATION_KEYS))
def test_authority_secret_and_raw_payload_fields_are_explicitly_rejected(record_type, field):
    source = make_invocation() if record_type is ExecutorInvocation else make_receipt()
    data = source.to_dict()
    data[field] = "forbidden"
    with pytest.raises(ContinuityStateValidationError, match="Forbidden"):
        record_type.from_dict(data)


@pytest.mark.parametrize("record_type", [ExecutorInvocation, InvocationReceipt])
def test_from_json_rejects_over_16_kib_input(record_type):
    raw = json.dumps({"padding": "x" * 17_000})
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum"):
        record_type.from_json(raw)


def test_module_is_pure_zero_io_and_has_no_authority_or_runtime_mutation_surface():
    tree = ast.parse(inspect.getsource(transport_module))
    forbidden_import_roots = {
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "httpx",
        "time",
        "datetime",
        "bridge",
        "runtime_dispatch",
        "runtime_lease",
        "providers",
    }
    imported = set()
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    assert imported.isdisjoint(forbidden_import_roots)
    assert called.isdisjoint(
        {
            "approve",
            "handoff",
            "publish",
            "commit",
            "push",
            "acquire",
            "release",
            "dispatch_executor",
            "invoke",
            "open",
            "write",
            "read",
        }
    )
    assert "CodexLocalTransport" not in inspect.getsource(transport_module)
