from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess

import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity import executor_transport as contract
from src.aios_bridge.continuity.executor_transport import (
    ExecutionTransport,
    ExecutorInvocation,
    InvocationReceipt,
    InvocationStatus,
    validate_invocation_receipt,
)
from src.aios_bridge.executor_transports import (
    CODEX_EXECUTOR_ID,
    CODEX_TRANSPORT_ID,
    DEFAULT_CODEX_TIMEOUT_SECONDS,
    MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM,
    MAX_CODEX_DIAGNOSTIC_EVENT_TYPES,
    MAX_SINGLE_EVENT_TYPE_LENGTH,
    CodexDiagnosticCode,
    CodexLocalTransport,
    CodexTransportDiagnostic,
    CodexInvocationOutcome,
)

from src.aios_bridge.executor_transports import codex_local


PAYLOAD = b"E2 bounded transport payload\n"


def _invocation(payload: bytes = PAYLOAD, **changes: object) -> ExecutorInvocation:
    values: dict[str, object] = {
        "schema_version": contract.SCHEMA_VERSION,
        "invocation_id": "invocation-041",
        "task_id": "TASK-041",
        "request_id": "request-041",
        "executor_id": CODEX_EXECUTOR_ID,
        "transport_id": CODEX_TRANSPORT_ID,
        "operation": "RUN",
        "workspace_id": "1" * 64,
        "target_branch": "ai/task-041",
        "execution_id": "execution-041",
        "request_fingerprint": "2" * 64,
        "prepared_execution_fingerprint": "3" * 64,
        "lease_fingerprint": "4" * 64,
        "execution_fingerprint": "5" * 64,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "payload_size_bytes": len(payload),
    }
    values.update(changes)
    return ExecutorInvocation(**values)


class _FakeProcess:
    def __init__(
        self,
        returncode: object = 0,
        communicate_error: BaseException | None = None,
        stdout_bytes: bytes = b"",
        stderr_bytes: bytes = b"",
    ) -> None:
        self.returncode = returncode
        self.communicate_error = communicate_error
        self.stdout_bytes = stdout_bytes
        self.stderr_bytes = stderr_bytes
        self.stdout_file = None
        self.stderr_file = None
        self.inputs: list[tuple[bytes, int]] = []
        self.pid = 41041

    def communicate(self, *, input: bytes, timeout: int) -> tuple[None, None]:
        self.inputs.append((input, timeout))
        if self.stdout_file is not None and self.stdout_bytes:
            self.stdout_file.write(self.stdout_bytes)
        if self.stderr_file is not None and self.stderr_bytes:
            self.stderr_file.write(self.stderr_bytes)
        if self.communicate_error is not None:
            raise self.communicate_error
        return None, None

    def poll(self) -> object:
        return self.returncode

    def terminate(self) -> None:
        return None

    def kill(self) -> None:
        return None

    def wait(self, *, timeout: int) -> object:
        return self.returncode


class _CleanupProcess(_FakeProcess):
    def __init__(
        self,
        *,
        pid: object = 41041,
        returncode: object = None,
        exit_on_terminate: bool = False,
        fail_direct_cleanup: bool = False,
        communicate_error: BaseException | None = None,
    ) -> None:
        super().__init__(returncode, communicate_error)
        self.pid = pid
        self.exit_on_terminate = exit_on_terminate
        self.fail_direct_cleanup = fail_direct_cleanup
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_timeouts: list[int] = []

    def terminate(self) -> None:
        self.terminate_calls += 1
        if self.exit_on_terminate:
            self.returncode = 0
        if self.fail_direct_cleanup:
            raise OSError("synthetic terminate failure")

    def kill(self) -> None:
        self.kill_calls += 1
        if self.fail_direct_cleanup:
            raise OSError("synthetic kill failure")
        self.returncode = -9

    def wait(self, *, timeout: int) -> object:
        self.wait_timeouts.append(timeout)
        if self.fail_direct_cleanup or self.returncode is None:
            raise subprocess.TimeoutExpired("codex", timeout)
        return self.returncode


def _install_valid_git(
    monkeypatch: pytest.MonkeyPatch,
    workspace: Path,
) -> list[tuple[list[str], dict[str, object]]]:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((argv, kwargs))
        operation = tuple(argv[3:])
        outputs = {
            ("rev-parse", "--show-toplevel"): f"{workspace}\n",
            ("branch", "--show-current"): "ai/task-041\r\n",
            ("status", "--porcelain", "--untracked-files=all"): "",
        }
        return subprocess.CompletedProcess(argv, 0, stdout=outputs[operation])

    monkeypatch.setattr(codex_local.subprocess, "run", fake_run)
    return calls


def _install_process(
    monkeypatch: pytest.MonkeyPatch,
    process: _FakeProcess,
) -> list[tuple[list[str], dict[str, object]]]:
    calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(codex_local.shutil, "which", lambda spec: "resolved-codex")

    def fake_popen(argv: list[str], **kwargs: object) -> _FakeProcess:
        calls.append((argv, kwargs))
        process.stdout_file = kwargs.get("stdout")
        process.stderr_file = kwargs.get("stderr")
        return process

    monkeypatch.setattr(codex_local.subprocess, "Popen", fake_popen)
    return calls


def _invoke_with_diagnostic_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    process: _FakeProcess,
    *,
    payload: bytes = PAYLOAD,
) -> tuple[CodexInvocationOutcome, list[tuple[list[str], dict[str, object]]], list[tuple[list[str], dict[str, object]]]]:
    workspace = tmp_path.resolve()
    git_calls = _install_valid_git(monkeypatch, workspace)
    popen_calls = _install_process(monkeypatch, process)
    outcome = CodexLocalTransport(workspace).invoke_with_diagnostic(_invocation(payload), payload)
    return outcome, git_calls, popen_calls


def _invoke_with_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    process: _FakeProcess,
    *,
    payload: bytes = PAYLOAD,
) -> tuple[object, list[tuple[list[str], dict[str, object]]], list[tuple[list[str], dict[str, object]]]]:
    workspace = tmp_path.resolve()
    git_calls = _install_valid_git(monkeypatch, workspace)
    popen_calls = _install_process(monkeypatch, process)
    receipt = CodexLocalTransport(workspace).invoke(_invocation(payload), payload)
    return receipt, git_calls, popen_calls


def test_public_surface_and_protocol_conformance(tmp_path: Path) -> None:
    transport = CodexLocalTransport(tmp_path)
    assert isinstance(transport, ExecutionTransport)
    assert transport.executor_id == CODEX_EXECUTOR_ID == "codex"
    assert transport.transport_id == CODEX_TRANSPORT_ID == "codex-local-v1"
    assert DEFAULT_CODEX_TIMEOUT_SECONDS == 1800


@pytest.mark.parametrize("value", [True, False, 0, -1, 7201, 1.0, "1", None])
def test_timeout_validation_rejects_non_exact_bounded_integer(
    tmp_path: Path, value: object
) -> None:
    with pytest.raises(ContinuityStateValidationError):
        CodexLocalTransport(tmp_path, timeout_seconds=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [1, 7200])
def test_timeout_validation_accepts_boundaries(tmp_path: Path, value: int) -> None:
    CodexLocalTransport(tmp_path, timeout_seconds=value)


def test_exact_argv_process_contract_and_payload_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = _FakeProcess(0)
    receipt, git_calls, popen_calls = _invoke_with_process(monkeypatch, tmp_path, process)
    workspace = tmp_path.resolve()

    assert len(popen_calls) == 1
    argv, options = popen_calls[0]
    assert argv == [
        "resolved-codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--ephemeral",
        "--json",
        "--color",
        "never",
        "--sandbox",
        "workspace-write",
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        'web_search="disabled"',
        "-C",
        str(workspace),
        "-",
    ]
    assert argv.count("--ask-for-approval") == 1
    assert argv.index("--ask-for-approval") == 1
    assert argv[1:3] == ["--ask-for-approval", "never"]
    assert argv.index("exec") == 3
    assert argv.index("--ask-for-approval") < argv.index("exec")
    assert options["cwd"] == str(workspace)
    assert options["stdin"] is subprocess.PIPE
    assert options["stdout"] is not None and options["stdout"] is not subprocess.DEVNULL
    assert options["stderr"] is not None and options["stderr"] is not subprocess.DEVNULL
    assert options["shell"] is False
    assert options["env"] == codex_local._build_child_environment(codex_local.os.environ)
    if codex_local.os.name == "nt":
        assert options["creationflags"] == getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
        assert "start_new_session" not in options
    else:
        assert options["start_new_session"] is True
        assert "creationflags" not in options
    assert process.inputs == [(PAYLOAD, DEFAULT_CODEX_TIMEOUT_SECONDS)]
    assert PAYLOAD not in argv
    assert receipt.status is InvocationStatus.EXITED_ZERO
    assert receipt.exit_code == 0
    assert receipt.error_code is None
    validate_invocation_receipt(receipt, _invocation())

    assert [call[0] for call in git_calls] == [
        ["git", "-C", str(workspace), "rev-parse", "--show-toplevel"],
        ["git", "-C", str(workspace), "branch", "--show-current"],
        [
            "git",
            "-C",
            str(workspace),
            "status",
            "--porcelain",
            "--untracked-files=all",
        ],
    ]
    assert all(options["shell"] is False for _, options in git_calls)


def test_payload_is_not_normalized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = b"\x00 leading\r\ntrailing \n"
    process = _FakeProcess(0)
    _invoke_with_process(monkeypatch, tmp_path, process, payload=payload)
    assert process.inputs[0][0] == payload


def test_child_environment_is_closed_and_does_not_mutate_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = {
        "PATH": "path-value",
        "HOME": "home-value",
        "SystemRoot": "windows-value",
        "CODEX_HOME": "codex-value",
        "UNRELATED": "must-not-pass",
        **{key: f"secret-{key}" for key in codex_local._SECRET_ENVIRONMENT_DENYLIST},
    }
    original = dict(source)
    child = codex_local._build_child_environment(source)

    expected_allowlist = (
        codex_local._WINDOWS_ENVIRONMENT_ALLOWLIST
        if codex_local.os.name == "nt"
        else codex_local._POSIX_ENVIRONMENT_ALLOWLIST
    )
    assert set(child) <= expected_allowlist
    assert child["PATH"] == "path-value"
    assert child["CODEX_HOME"] == "codex-value"
    assert "UNRELATED" not in child
    assert not set(child).intersection(codex_local._SECRET_ENVIRONMENT_DENYLIST)
    assert source == original


@pytest.mark.parametrize(
    ("path_kind", "create_file"),
    [("missing", False), ("not-directory", True)],
)
def test_invalid_workspace_fails_before_git_or_codex_spawn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    path_kind: str,
    create_file: bool,
) -> None:
    workspace = tmp_path / path_kind
    if create_file:
        workspace.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(
        codex_local.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("Git must not run"),
    )
    monkeypatch.setattr(
        codex_local.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("Codex must not spawn"),
    )

    receipt = CodexLocalTransport(workspace).invoke(_invocation(), PAYLOAD)
    assert receipt.status is InvocationStatus.FAILED_TO_START
    assert receipt.error_code == codex_local.ERROR_WORKSPACE_PRECONDITION_FAILED


@pytest.mark.parametrize(
    ("returncodes", "outputs"),
    [
        ([1], [""]),
        ([0], ["C:/different/workspace\n"]),
        ([0, 0], ["{workspace}\n", "wrong-branch\n"]),
        ([0, 0], ["{workspace}\n", ""]),
        ([0, 0, 0], ["{workspace}\n", "ai/task-041\n", " M tracked.py\n"]),
        ([0, 0, 0], ["{workspace}\n", "ai/task-041\n", "?? untracked.py\n"]),
    ],
)
def test_git_preflight_failures_refuse_spawn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    returncodes: list[int],
    outputs: list[str],
) -> None:
    workspace = tmp_path.resolve()
    calls = 0

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        index = calls
        calls += 1
        stdout = outputs[index].format(workspace=workspace)
        return subprocess.CompletedProcess(argv, returncodes[index], stdout=stdout)

    monkeypatch.setattr(codex_local.subprocess, "run", fake_run)
    monkeypatch.setattr(
        codex_local.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("Codex must not spawn"),
    )
    receipt = CodexLocalTransport(workspace).invoke(_invocation(), PAYLOAD)
    assert receipt.status is InvocationStatus.FAILED_TO_START
    assert receipt.error_code == codex_local.ERROR_WORKSPACE_PRECONDITION_FAILED


def test_git_preflight_exception_refuses_spawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        codex_local.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired("git", 10)
        ),
    )
    monkeypatch.setattr(
        codex_local.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("Codex must not spawn"),
    )
    receipt = CodexLocalTransport(tmp_path).invoke(_invocation(), PAYLOAD)
    assert receipt.error_code == codex_local.ERROR_WORKSPACE_PRECONDITION_FAILED


@pytest.mark.parametrize(
    "invocation",
    [
        replace(_invocation(), executor_id="antigravity"),
        replace(_invocation(), transport_id="codex-local-v2"),
    ],
)
def test_binding_errors_propagate_before_preflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    invocation: ExecutorInvocation,
) -> None:
    monkeypatch.setattr(
        codex_local,
        "_git_preflight",
        lambda *args: pytest.fail("preflight must not run"),
    )
    with pytest.raises(ContinuityStateValidationError):
        CodexLocalTransport(tmp_path).invoke(invocation, PAYLOAD)


@pytest.mark.parametrize("payload", [b"E2 bounded transport payloae\n", bytearray(PAYLOAD)])
def test_payload_errors_propagate_before_preflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: object,
) -> None:
    monkeypatch.setattr(
        codex_local,
        "_git_preflight",
        lambda *args: pytest.fail("preflight must not run"),
    )
    with pytest.raises(ContinuityStateValidationError):
        CodexLocalTransport(tmp_path).invoke(_invocation(), payload)  # type: ignore[arg-type]


def test_missing_codex_maps_failed_to_start_without_spawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_valid_git(monkeypatch, tmp_path.resolve())
    monkeypatch.setattr(codex_local.shutil, "which", lambda spec: None)
    monkeypatch.setattr(
        codex_local.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("Codex must not spawn"),
    )
    receipt = CodexLocalTransport(tmp_path).invoke(_invocation(), PAYLOAD)
    assert receipt.status is InvocationStatus.FAILED_TO_START
    assert receipt.error_code == codex_local.ERROR_CODEX_NOT_FOUND


def test_explicit_executable_resolution_is_bounded(tmp_path: Path) -> None:
    executable = tmp_path / "codex-test.exe"
    executable.write_bytes(b"test double path only")
    assert codex_local._resolve_codex_executable(str(executable)) == str(
        executable.resolve()
    )
    assert codex_local._resolve_codex_executable(str(tmp_path / "missing.exe")) is None
    assert codex_local._resolve_codex_executable(" codex") is None


def test_spawn_oserror_maps_failed_to_start_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_valid_git(monkeypatch, tmp_path.resolve())
    monkeypatch.setattr(codex_local.shutil, "which", lambda spec: "resolved-codex")
    spawn_count = 0

    def fail_spawn(*args: object, **kwargs: object) -> None:
        nonlocal spawn_count
        spawn_count += 1
        raise OSError("synthetic launch failure")

    monkeypatch.setattr(codex_local.subprocess, "Popen", fail_spawn)
    receipt = CodexLocalTransport(tmp_path).invoke(_invocation(), PAYLOAD)
    assert spawn_count == 1
    assert receipt.status is InvocationStatus.FAILED_TO_START
    assert receipt.error_code == codex_local.ERROR_CODEX_START_FAILED


@pytest.mark.parametrize(
    ("returncode", "status", "exit_code", "error_code"),
    [
        (0, InvocationStatus.EXITED_ZERO, 0, None),
        (7, InvocationStatus.EXITED_NONZERO, 7, codex_local.ERROR_CODEX_EXIT_NONZERO),
        (-15, InvocationStatus.EXITED_NONZERO, -15, codex_local.ERROR_CODEX_EXIT_NONZERO),
        (
            2_147_483_648,
            InvocationStatus.FAILED_TO_START,
            None,
            codex_local.ERROR_CODEX_EXIT_CODE_INVALID,
        ),
        (
            None,
            InvocationStatus.FAILED_TO_START,
            None,
            codex_local.ERROR_CODEX_EXIT_CODE_INVALID,
        ),
        (
            True,
            InvocationStatus.FAILED_TO_START,
            None,
            codex_local.ERROR_CODEX_EXIT_CODE_INVALID,
        ),
    ],
)
def test_process_status_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    returncode: object,
    status: InvocationStatus,
    exit_code: int | None,
    error_code: str | None,
) -> None:
    receipt, _, popen_calls = _invoke_with_process(
        monkeypatch, tmp_path, _FakeProcess(returncode)
    )
    assert len(popen_calls) == 1
    assert receipt.status is status
    assert receipt.exit_code == exit_code
    assert receipt.error_code == error_code


@pytest.mark.parametrize(
    ("error", "status", "error_code"),
    [
        (
            subprocess.TimeoutExpired("codex", DEFAULT_CODEX_TIMEOUT_SECONDS),
            InvocationStatus.TIMED_OUT,
            codex_local.ERROR_CODEX_TIMEOUT,
        ),
        (
            KeyboardInterrupt(),
            InvocationStatus.INTERRUPTED,
            codex_local.ERROR_CALLER_INTERRUPTED,
        ),
    ],
)
def test_timeout_and_interruption_cleanup_without_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error: BaseException,
    status: InvocationStatus,
    error_code: str,
) -> None:
    process = _FakeProcess(None, error)
    cleaned: list[_FakeProcess] = []
    monkeypatch.setattr(codex_local, "_cleanup_process", cleaned.append)
    receipt, _, popen_calls = _invoke_with_process(monkeypatch, tmp_path, process)
    assert len(popen_calls) == 1
    assert cleaned == [process]
    assert receipt.status is status
    assert receipt.exit_code is None
    assert receipt.error_code == error_code


def test_windows_parent_exit_after_terminate_still_attempts_tree_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _CleanupProcess(exit_on_terminate=True)
    taskkill_calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(codex_local, "_IS_WINDOWS", True)

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        taskkill_calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(codex_local.subprocess, "run", fake_run)
    codex_local._cleanup_process(process)  # type: ignore[arg-type]

    assert process.terminate_calls == 1
    assert taskkill_calls[0][0] == [
        "taskkill",
        "/PID",
        "41041",
        "/T",
        "/F",
    ]
    assert taskkill_calls[0][1]["shell"] is False
    assert taskkill_calls[0][1]["timeout"] == codex_local._CLEANUP_WAIT_SECONDS
    assert taskkill_calls[0][1]["env"] == codex_local._build_child_environment(
        codex_local.os.environ
    )
    assert process.wait_timeouts == [codex_local._CLEANUP_WAIT_SECONDS]


def test_windows_taskkill_and_direct_cleanup_failures_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _CleanupProcess(fail_direct_cleanup=True)
    taskkill_calls = 0
    monkeypatch.setattr(codex_local, "_IS_WINDOWS", True)

    def fail_taskkill(*args: object, **kwargs: object) -> None:
        nonlocal taskkill_calls
        taskkill_calls += 1
        raise OSError("synthetic taskkill failure")

    monkeypatch.setattr(codex_local.subprocess, "run", fail_taskkill)
    codex_local._cleanup_process(process)  # type: ignore[arg-type]

    assert taskkill_calls == 1
    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert process.wait_timeouts == [
        codex_local._CLEANUP_WAIT_SECONDS,
        codex_local._CLEANUP_WAIT_SECONDS,
    ]


def test_windows_already_exited_parent_with_valid_pid_still_attempts_tree_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _CleanupProcess(returncode=0)
    taskkill_calls: list[list[str]] = []
    monkeypatch.setattr(codex_local, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        codex_local.subprocess,
        "run",
        lambda argv, **kwargs: taskkill_calls.append(argv)
        or subprocess.CompletedProcess(argv, 1),
    )

    codex_local._cleanup_process(process)  # type: ignore[arg-type]
    assert taskkill_calls == [["taskkill", "/PID", "41041", "/T", "/F"]]


@pytest.mark.parametrize("pid", [None, 0, -1, True, "41041"])
def test_windows_invalid_pid_is_bounded_and_skips_taskkill(
    monkeypatch: pytest.MonkeyPatch, pid: object
) -> None:
    process = _CleanupProcess(pid=pid, returncode=0)
    monkeypatch.setattr(codex_local, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        codex_local.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("taskkill requires a valid positive PID"),
    )

    codex_local._cleanup_process(process)  # type: ignore[arg-type]
    assert process.terminate_calls == 1
    assert process.wait_timeouts == [codex_local._CLEANUP_WAIT_SECONDS]


def test_posix_exited_group_leader_still_receives_group_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _CleanupProcess(returncode=0)
    posix_sigkill = 9
    signals: list[tuple[int, object]] = []
    monkeypatch.setattr(codex_local, "_IS_WINDOWS", False)
    monkeypatch.setattr(codex_local.signal, "SIGKILL", posix_sigkill, raising=False)

    def fake_killpg(pid: int, sent_signal: object) -> None:
        signals.append((pid, sent_signal))
        if sent_signal == posix_sigkill:
            raise ProcessLookupError("synthetic group already gone")

    monkeypatch.setattr(codex_local.os, "killpg", fake_killpg, raising=False)
    codex_local._cleanup_process(process)  # type: ignore[arg-type]

    assert signals == [
        (41041, signal.SIGTERM),
        (41041, posix_sigkill),
    ]
    assert process.wait_timeouts == [
        codex_local._CLEANUP_WAIT_SECONDS,
        codex_local._CLEANUP_WAIT_SECONDS,
    ]


@pytest.mark.parametrize(
    ("error", "status", "error_code"),
    [
        (
            subprocess.TimeoutExpired("codex", DEFAULT_CODEX_TIMEOUT_SECONDS),
            InvocationStatus.TIMED_OUT,
            codex_local.ERROR_CODEX_TIMEOUT,
        ),
        (
            KeyboardInterrupt(),
            InvocationStatus.INTERRUPTED,
            codex_local.ERROR_CALLER_INTERRUPTED,
        ),
    ],
)
def test_real_cleanup_failures_preserve_primary_receipt_and_single_spawn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error: BaseException,
    status: InvocationStatus,
    error_code: str,
) -> None:
    process = _CleanupProcess(
        fail_direct_cleanup=True,
        communicate_error=error,
    )
    spawn_calls = 0
    taskkill_calls = 0
    monkeypatch.setattr(codex_local, "_IS_WINDOWS", True)
    monkeypatch.setattr(codex_local, "_git_preflight", lambda *args: True)
    monkeypatch.setattr(
        codex_local, "_resolve_codex_executable", lambda spec: "resolved-codex"
    )

    def fake_popen(*args: object, **kwargs: object) -> _CleanupProcess:
        nonlocal spawn_calls
        spawn_calls += 1
        return process

    def fail_taskkill(*args: object, **kwargs: object) -> None:
        nonlocal taskkill_calls
        taskkill_calls += 1
        raise OSError("synthetic taskkill failure")

    monkeypatch.setattr(codex_local.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(codex_local.subprocess, "run", fail_taskkill)

    receipt = CodexLocalTransport(tmp_path).invoke(_invocation(), PAYLOAD)
    assert spawn_calls == 1
    assert taskkill_calls == 1
    assert receipt.status is status
    assert receipt.exit_code is None
    assert receipt.error_code == error_code


def test_production_module_has_no_forbidden_scope_or_unsafe_command_tokens() -> None:
    source = Path(codex_local.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Name):
            identifiers.add(node.id)
        elif isinstance(node, ast.Attribute):
            identifiers.add(node.attr)

    assert imported_roots.isdisjoint(
        {"bridge", "requests", "httpx", "urllib", "browser", "providers"}
    )
    assert identifiers.isdisjoint(
        {
            "runtime_dispatch",
            "runtime_lease",
            "dispatch_executor",
            "approve",
            "handoff",
            "publish",
            "commit",
            "push",
            "merge",
            "acquire",
            "release",
        }
    )
    for forbidden in (
        "--dangerously-bypass-approvals-and-sandbox",
        "danger-full-access",
        "--skip-git-repo-check",
        "--add-dir",
        "--full-auto",
        "shell=True",
        "resume",
    ):
        assert forbidden not in source


# -----------------------------------------------------------------------------
# TASK-067 / ADR-040 Bounded Diagnostic Observability Tests (Review Fixes B1-B4)
# -----------------------------------------------------------------------------


def test_diagnostic_dataclass_immutability_and_validation() -> None:
    diag = CodexTransportDiagnostic(
        code=CodexDiagnosticCode.JSON_EVENT_STREAM.value,
        stdout_total_bytes=100,
        stderr_total_bytes=0,
        stdout_scan_truncated=False,
        stderr_scan_truncated=False,
        stdout_json_line_count=3,
        stdout_non_json_line_count=0,
        stdout_event_types=("turn.started", "item.completed"),
        last_stdout_event_type="item.completed",
    )
    assert diag.code == "JSON_EVENT_STREAM"
    assert diag.stdout_total_bytes == 100
    assert diag.stdout_event_types == ("turn.started", "item.completed")
    assert diag.schema_version == "1"

    d = diag.to_dict()
    assert d == {
        "code": "JSON_EVENT_STREAM",
        "command_activity_count": "UNKNOWN",
        "executor_outcome": "UNKNOWN",
        "file_change_activity_count": "UNKNOWN",
        "final_agent_message_observed": "UNKNOWN",
        "last_stdout_event_type": "item.completed",
        "schema_version": "1",
        "stderr_scan_truncated": False,
        "stderr_total_bytes": 0,
        "stdout_event_types": ["turn.started", "item.completed"],
        "stdout_json_line_count": 3,
        "stdout_non_json_line_count": 0,
        "stdout_scan_truncated": False,
        "stdout_total_bytes": 100,
    }
    assert len(diag.fingerprint()) == 64
    assert diag.fingerprint() == diag.fingerprint()

    with pytest.raises(Exception):
        diag.code = "MUTATED"  # type: ignore


@pytest.mark.parametrize("invalid_field,kwargs", [
    ("bool_as_int", {"stdout_total_bytes": True}),
    ("negative_int", {"stdout_total_bytes": -1}),
    ("unknown_code", {"code": "RANDOM_UNSUPPORTED_CODE"}),
    ("lowercase_code", {"code": "json_event_stream"}),
    ("empty_code", {"code": ""}),
    ("control_code", {"code": "JSON_EVENT_STREAM\n"}),
    ("list_event_types", {"stdout_event_types": ["turn.started"]}),
    ("string_event_types", {"stdout_event_types": "turn.started"}),
    ("dict_event_types", {"stdout_event_types": {"type": "turn.started"}}),
    ("oversized_event_type", {"stdout_event_types": ("A" * 65,)}),
    ("control_event_type", {"stdout_event_types": ("turn\nstarted",)}),
    ("too_many_event_types", {"stdout_event_types": tuple(f"type_{i}" for i in range(33))}),
    ("control_last_event", {"last_stdout_event_type": "turn\r"}),
])
def test_diagnostic_rejects_invalid_types_and_bounds(invalid_field, kwargs) -> None:
    valid_args = {
        "code": CodexDiagnosticCode.JSON_EVENT_STREAM.value,
        "stdout_total_bytes": 100,
        "stderr_total_bytes": 0,
        "stdout_scan_truncated": False,
        "stderr_scan_truncated": False,
        "stdout_json_line_count": 1,
        "stdout_non_json_line_count": 0,
        "stdout_event_types": ("turn.started",),
        "last_stdout_event_type": "turn.started",
    }
    valid_args.update(kwargs)
    with pytest.raises(ContinuityStateValidationError):
        CodexTransportDiagnostic(**valid_args)


def test_outcome_dataclass_immutability_and_validation() -> None:
    inv = _invocation()
    receipt = InvocationReceipt(
        schema_version="1",
        invocation_id=inv.invocation_id,
        task_id=inv.task_id,
        request_id=inv.request_id,
        executor_id=inv.executor_id,
        transport_id=inv.transport_id,
        operation=inv.operation,
        execution_id=inv.execution_id,
        invocation_fingerprint=inv.fingerprint(),
        status=InvocationStatus.EXITED_ZERO,
        exit_code=0,
        error_code=None,
    )
    diag = CodexTransportDiagnostic(
        code=CodexDiagnosticCode.EMPTY_OUTPUT.value,
        stdout_total_bytes=0,
        stderr_total_bytes=0,
        stdout_scan_truncated=False,
        stderr_scan_truncated=False,
        stdout_json_line_count=0,
        stdout_non_json_line_count=0,
        stdout_event_types=(),
        last_stdout_event_type=None,
    )
    outcome = CodexInvocationOutcome(receipt=receipt, diagnostic=diag)
    assert outcome.receipt is receipt
    assert outcome.diagnostic is diag

    with pytest.raises(Exception):
        outcome.receipt = None  # type: ignore


def test_invoke_with_diagnostic_returns_outcome_with_empty_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = _FakeProcess(returncode=0)
    outcome, git_calls, popen_calls = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert isinstance(outcome, CodexInvocationOutcome)
    assert outcome.receipt.status is InvocationStatus.EXITED_ZERO
    assert outcome.receipt.exit_code == 0
    assert outcome.diagnostic.code == "EMPTY_OUTPUT"
    assert outcome.diagnostic.stdout_total_bytes == 0
    assert outcome.diagnostic.stderr_total_bytes == 0
    assert outcome.diagnostic.stdout_json_line_count == 0
    assert outcome.diagnostic.stdout_non_json_line_count == 0
    assert outcome.diagnostic.stdout_event_types == ()
    assert outcome.diagnostic.last_stdout_event_type is None
    assert len(popen_calls) == 1


def test_invoke_with_diagnostic_parses_real_codex_dotted_event_stream(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ndjson = (
        b'{"type": "thread.started", "thread_id": "t-1", "secret": "forbidden"}\n'
        b'{"type": "turn.started", "turn_id": "turn-1"}\n'
        b'{"type": "item.started", "item_id": "item-1"}\n'
        b'{"type": "item.updated", "item_id": "item-1"}\n'
        b'{"type": "item.completed", "item_id": "item-1", "result": "ok"}\n'
        b'{"type": "turn.completed", "turn_id": "turn-1"}\n'
    )
    process = _FakeProcess(returncode=0, stdout_bytes=ndjson)
    outcome, _, popen_calls = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert len(popen_calls) == 1
    assert outcome.receipt.status is InvocationStatus.EXITED_ZERO
    assert outcome.diagnostic.code == "JSON_EVENT_STREAM"
    assert outcome.diagnostic.stdout_total_bytes == len(ndjson)
    assert outcome.diagnostic.stdout_json_line_count == 6
    assert outcome.diagnostic.stdout_non_json_line_count == 0
    assert outcome.diagnostic.stdout_event_types == (
        "thread.started",
        "turn.started",
        "item.started",
        "item.updated",
        "item.completed",
        "turn.completed",
    )
    assert outcome.diagnostic.last_stdout_event_type == "turn.completed"
    # Ensure no raw secret/payloads in diagnostic dict
    d_str = str(outcome.diagnostic.to_dict())
    assert "forbidden" not in d_str
    assert "secret" not in d_str
    assert "item_id" not in d_str


@pytest.mark.parametrize("failure_event", ["error", "turn.failed"])
def test_invoke_with_diagnostic_detects_mechanical_failure_events(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure_event: str
) -> None:
    ndjson = (
        f'{{"type": "turn.started"}}\n'
        f'{{"type": "{failure_event}", "message": "auth error"}}\n'
    ).encode("utf-8")
    process = _FakeProcess(returncode=1, stdout_bytes=ndjson)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.receipt.status is InvocationStatus.EXITED_NONZERO
    assert outcome.receipt.exit_code == 1
    assert outcome.receipt.error_code == codex_local.ERROR_CODEX_EXIT_NONZERO
    assert outcome.diagnostic.code == "JSON_ERROR_EVENT"
    assert outcome.diagnostic.stdout_json_line_count == 2
    assert failure_event in outcome.diagnostic.stdout_event_types
    assert outcome.diagnostic.last_stdout_event_type == failure_event
    assert "auth error" not in str(outcome.diagnostic.to_dict())


def test_diagnostic_does_not_infer_error_from_arbitrary_substrings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ndjson = (
        b'{"type": "error_reporting_config"}\n'
        b'{"type": "system.terrordome"}\n'
    )
    process = _FakeProcess(returncode=0, stdout_bytes=ndjson)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    # Must NOT classify as JSON_ERROR_EVENT because neither is in _FAILURE_EVENT_TYPES
    assert outcome.diagnostic.code == "JSON_EVENT_STREAM"
    assert outcome.diagnostic.stdout_event_types == ("error_reporting_config", "system.terrordome")


def test_invoke_with_diagnostic_handles_non_json_stdout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_text = b"Error: unrecognized argument --unknown\nFatal exit\n"
    process = _FakeProcess(returncode=2, stdout_bytes=raw_text)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.receipt.status is InvocationStatus.EXITED_NONZERO
    assert outcome.diagnostic.code == "NON_JSON_OUTPUT"
    assert outcome.diagnostic.stdout_json_line_count == 0
    assert outcome.diagnostic.stdout_non_json_line_count == 2
    assert outcome.diagnostic.stdout_event_types == ()
    assert outcome.diagnostic.last_stdout_event_type is None
    assert "unrecognized" not in str(outcome.diagnostic.to_dict())


def test_invoke_with_diagnostic_handles_mixed_json_and_non_json_stdout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mixed = (
        b"some initial banner text\n"
        b'{"type": "turn.started"}\n'
    )
    process = _FakeProcess(returncode=0, stdout_bytes=mixed)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.receipt.status is InvocationStatus.EXITED_ZERO
    assert outcome.diagnostic.code == "MIXED_OUTPUT"
    assert outcome.diagnostic.stdout_json_line_count == 1
    assert outcome.diagnostic.stdout_non_json_line_count == 1
    assert outcome.diagnostic.stdout_event_types == ("turn.started",)


def test_invoke_with_diagnostic_handles_stderr_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    stderr_data = b"fatal: unexpected error occurred in codex wrapper\n"
    process = _FakeProcess(returncode=1, stderr_bytes=stderr_data)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.receipt.status is InvocationStatus.EXITED_NONZERO
    assert outcome.diagnostic.code == "STDERR_ONLY"
    assert outcome.diagnostic.stdout_total_bytes == 0
    assert outcome.diagnostic.stderr_total_bytes == len(stderr_data)
    assert outcome.diagnostic.stdout_json_line_count == 0
    assert outcome.diagnostic.stdout_non_json_line_count == 0
    assert "unexpected error" not in str(outcome.diagnostic.to_dict())


def test_diagnostic_scan_bytes_bounded_and_truncation_flag_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    line = b'{"type": "item.progress"}\n'
    num_lines = (MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM // len(line)) + 100
    large_stdout = line * num_lines
    assert len(large_stdout) > MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM

    process = _FakeProcess(returncode=0, stdout_bytes=large_stdout)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.diagnostic.stdout_total_bytes == len(large_stdout)
    assert outcome.diagnostic.stdout_scan_truncated is True
    assert outcome.diagnostic.stderr_scan_truncated is False


def test_diagnostic_event_types_bounded_at_maximum_32(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lines = [f'{{"type": "event.type.{i}"}}\n'.encode("utf-8") for i in range(50)]
    process = _FakeProcess(returncode=0, stdout_bytes=b"".join(lines))
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert len(outcome.diagnostic.stdout_event_types) == MAX_CODEX_DIAGNOSTIC_EVENT_TYPES == 32
    assert outcome.diagnostic.last_stdout_event_type == "event.type.49"


def test_diagnostic_event_types_filters_invalid_tokens_and_control_chars(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ndjson = (
        b'{"type": "valid.token"}\n'
        b'{"type": "invalid with space"}\n'
        b'{"type": "invalid_with_control\\n"}\n'
        b'{"type": "' + b"A" * 65 + b'"}\n'
        b'{"type": "another.valid.token"}\n'
    )
    process = _FakeProcess(returncode=0, stdout_bytes=ndjson)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.diagnostic.stdout_event_types == ("valid.token", "another.valid.token")
    assert outcome.diagnostic.last_stdout_event_type == "another.valid.token"


def test_diagnostic_handles_malformed_and_invalid_utf8_safely(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    malformed = b"\xff\xfe\x00invalid binary\n{broken json\n"
    process = _FakeProcess(returncode=1, stdout_bytes=malformed)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.receipt.status is InvocationStatus.EXITED_NONZERO
    assert outcome.diagnostic.code == "NON_JSON_OUTPUT"
    assert outcome.diagnostic.stdout_non_json_line_count == 2


def test_unsafe_temporary_capture_location_inside_workspace_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path.resolve()
    inside_temp = workspace / "sub_temp"
    inside_temp.mkdir(parents=True, exist_ok=True)
    _install_valid_git(monkeypatch, workspace)
    monkeypatch.setattr(codex_local.shutil, "which", lambda spec: "resolved-codex")
    monkeypatch.setattr(codex_local.tempfile, "gettempdir", lambda: str(inside_temp))

    spawned = False

    def fake_popen(*args: object, **kwargs: object) -> _FakeProcess:
        nonlocal spawned
        spawned = True
        return _FakeProcess(0)

    monkeypatch.setattr(codex_local.subprocess, "Popen", fake_popen)

    outcome = CodexLocalTransport(workspace).invoke_with_diagnostic(_invocation(), PAYLOAD)
    assert not spawned
    assert outcome.receipt.status is InvocationStatus.FAILED_TO_START
    assert outcome.receipt.error_code == codex_local.ERROR_WORKSPACE_PRECONDITION_FAILED


@pytest.mark.parametrize("runtime_env,base_name", [
    ("AIOS_RUNTIME_DIR", ""),
    ("AIOS_HOME", ""),
    ("LOCALAPPDATA", "aios-bridge"),
    ("XDG_DATA_HOME", "aios-bridge"),
    ("AIOS_BRIDGE_RUNTIME_DIR", ""),
])
def test_unsafe_temporary_capture_location_inside_persistent_runtime_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runtime_env: str, base_name: str
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    runtime_root = tmp_path / "persistent_runtime_root"
    runtime_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv(runtime_env, str(runtime_root))
    if base_name:
        temp_inside = runtime_root / base_name / "temp"
    else:
        temp_inside = runtime_root / "temp"
    temp_inside.mkdir(parents=True, exist_ok=True)

    _install_valid_git(monkeypatch, workspace)
    monkeypatch.setattr(codex_local.shutil, "which", lambda spec: "resolved-codex")
    monkeypatch.setattr(codex_local.tempfile, "gettempdir", lambda: str(temp_inside))

    spawned = False

    def fake_popen(*args: object, **kwargs: object) -> _FakeProcess:
        nonlocal spawned
        spawned = True
        return _FakeProcess(0)

    monkeypatch.setattr(codex_local.subprocess, "Popen", fake_popen)

    outcome = CodexLocalTransport(workspace).invoke_with_diagnostic(_invocation(), PAYLOAD)
    assert not spawned
    assert outcome.receipt.status is InvocationStatus.FAILED_TO_START
    assert outcome.receipt.error_code == codex_local.ERROR_WORKSPACE_PRECONDITION_FAILED


def test_unsafe_temporary_capture_location_inside_home_fallback_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    fallback_dir = fake_home / ".aios-bridge" / "temp"
    fallback_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(codex_local.Path, "home", lambda: fake_home)
    _install_valid_git(monkeypatch, workspace)
    monkeypatch.setattr(codex_local.shutil, "which", lambda spec: "resolved-codex")
    monkeypatch.setattr(codex_local.tempfile, "gettempdir", lambda: str(fallback_dir))

    spawned = False

    def fake_popen(*args: object, **kwargs: object) -> _FakeProcess:
        nonlocal spawned
        spawned = True
        return _FakeProcess(0)

    monkeypatch.setattr(codex_local.subprocess, "Popen", fake_popen)

    outcome = CodexLocalTransport(workspace).invoke_with_diagnostic(_invocation(), PAYLOAD)
    assert not spawned
    assert outcome.receipt.status is InvocationStatus.FAILED_TO_START
    assert outcome.receipt.error_code == codex_local.ERROR_WORKSPACE_PRECONDITION_FAILED


def test_long_json_stream_tail_turn_failed_produces_json_error_event(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lines = [json.dumps({"type": "turn_started"}).encode("utf-8") + b"\n"]
    filler_line = json.dumps({"type": "item_in_progress", "data": "x" * 200}).encode("utf-8") + b"\n"
    while sum(len(l) for l in lines) < 120000:
        lines.append(filler_line)
    lines.append(json.dumps({"type": "turn.failed"}).encode("utf-8") + b"\n")
    stdout_data = b"".join(lines)

    process = _FakeProcess(returncode=2, stdout_bytes=stdout_data)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.diagnostic.stdout_total_bytes > 65536
    assert outcome.diagnostic.stdout_scan_truncated is True
    assert outcome.diagnostic.code == CodexDiagnosticCode.JSON_ERROR_EVENT.value
    assert outcome.diagnostic.last_stdout_event_type == "turn.failed"
    assert "turn.failed" in outcome.diagnostic.stdout_event_types


def test_long_json_stream_tail_error_event_produces_json_error_event(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lines = [json.dumps({"type": "turn_started"}).encode("utf-8") + b"\n"]
    filler_line = json.dumps({"type": "item_in_progress", "data": "y" * 200}).encode("utf-8") + b"\n"
    while sum(len(l) for l in lines) < 100000:
        lines.append(filler_line)
    lines.append(json.dumps({"type": "error"}).encode("utf-8") + b"\n")
    stdout_data = b"".join(lines)

    process = _FakeProcess(returncode=2, stdout_bytes=stdout_data)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.diagnostic.stdout_total_bytes > 65536
    assert outcome.diagnostic.stdout_scan_truncated is True
    assert outcome.diagnostic.code == CodexDiagnosticCode.JSON_ERROR_EVENT.value
    assert outcome.diagnostic.last_stdout_event_type == "error"


def test_long_json_stream_tail_turn_completed_observed_as_last_event(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lines = [json.dumps({"type": "turn_started"}).encode("utf-8") + b"\n"]
    filler_line = json.dumps({"type": "item_completed", "data": "z" * 200}).encode("utf-8") + b"\n"
    while sum(len(l) for l in lines) < 100000:
        lines.append(filler_line)
    lines.append(json.dumps({"type": "turn.completed"}).encode("utf-8") + b"\n")
    stdout_data = b"".join(lines)

    process = _FakeProcess(returncode=0, stdout_bytes=stdout_data)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.diagnostic.stdout_total_bytes > 65536
    assert outcome.diagnostic.stdout_scan_truncated is True
    assert outcome.diagnostic.code == CodexDiagnosticCode.JSON_EVENT_STREAM.value
    assert outcome.diagnostic.last_stdout_event_type == "turn.completed"


def test_head_and_tail_boundary_fragments_do_not_produce_false_non_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    line1 = (json.dumps({"type": "head_event", "padding": "a" * 32000}) + "\n").encode("utf-8")
    line2 = (json.dumps({"type": "middle_event_cut", "padding": "b" * 40000}) + "\n").encode("utf-8")
    line3 = (json.dumps({"type": "tail_event", "padding": "c" * 32000}) + "\n").encode("utf-8")
    stdout_data = line1 + line2 + line3

    process = _FakeProcess(returncode=0, stdout_bytes=stdout_data)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)
    assert outcome.diagnostic.stdout_scan_truncated is True
    assert outcome.diagnostic.stdout_non_json_line_count == 0
    assert outcome.diagnostic.code == CodexDiagnosticCode.JSON_EVENT_STREAM.value


def test_cut_tail_boundary_fragment_with_syntactically_valid_json_suffix_is_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Construct a stream where byte offset total_bytes - 32768 lands in the middle of a huge record,
    # and the trailing slice starts with a valid JSON suffix like '{"type":"error"}\n'
    head_line = (json.dumps({"type": "head_event"}) + "\n").encode("utf-8")
    fake_cut_suffix = (json.dumps({"type": "error"}) + "\n").encode("utf-8")
    tail_real_event = (json.dumps({"type": "turn.completed"}) + "\n").encode("utf-8")

    # We want total_bytes > 65536 and tail_start = total_bytes - 32768 to fall mid-record.
    # Total tail size = 32768.
    # Tail slice will be: fake_cut_suffix + tail_real_event + padding
    tail_prefix = fake_cut_suffix
    tail_suffix = tail_real_event
    needed_len = 32768 - len(tail_prefix) - len(tail_suffix)
    base_json = json.dumps({"type": "filler", "d": ""}) + "\n"
    pad_chars = needed_len - len(base_json.encode("utf-8"))
    tail_padding = (json.dumps({"type": "filler", "d": "a" * pad_chars}) + "\n").encode("utf-8")
    tail_slice = tail_prefix + tail_padding + tail_suffix
    assert len(tail_slice) == 32768

    # Middle record prefix: needs to not end with \n before tail_slice begins
    middle_prefix = b'{"huge_field":"' + b"A" * 40000  # no newline!
    stdout_data = head_line + middle_prefix + tail_slice
    assert len(stdout_data) > 65536

    process = _FakeProcess(returncode=0, stdout_bytes=stdout_data)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    assert outcome.diagnostic.stdout_scan_truncated is True
    # The fake_cut_suffix was a proven cut fragment -> ignored and NOT parsed as error event!
    assert "error" not in outcome.diagnostic.stdout_event_types
    assert outcome.diagnostic.code == CodexDiagnosticCode.JSON_EVENT_STREAM.value
    assert outcome.diagnostic.last_stdout_event_type == "turn.completed"


def test_exact_record_boundary_tail_start_parses_malformed_and_valid_records_correctly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Construct a stream where byte offset total_bytes - 32768 lands EXACTLY after \n
    # Tail size = 32768.
    malformed_line = b"MALFORMED_LINE_AT_BOUNDARY\n"
    valid_line = (json.dumps({"type": "turn.completed"}) + "\n").encode("utf-8")
    tail_rest = b"y" * (32768 - len(malformed_line) - len(valid_line) - 1) + b"\n"
    tail_slice = malformed_line + valid_line + tail_rest
    assert len(tail_slice) == 32768

    # Prefix total length must end with \n immediately before tail_slice
    prefix = (json.dumps({"type": "head_event"}) + "\n").encode("utf-8")
    prefix += b"A" * (40000 - len(prefix) - 1) + b"\n"
    stdout_data = prefix + tail_slice
    assert len(stdout_data) > 65536
    # Check that byte immediately before tail_slice is \n
    tail_start = len(stdout_data) - 32768
    assert stdout_data[tail_start - 1 : tail_start] == b"\n"

    process = _FakeProcess(returncode=0, stdout_bytes=stdout_data)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    assert outcome.diagnostic.stdout_scan_truncated is True
    # Because it starts on record boundary, malformed_line is counted as non_json
    assert outcome.diagnostic.stdout_non_json_line_count >= 1
    assert outcome.diagnostic.last_stdout_event_type == "turn.completed"


def test_diagnostic_stream_read_strictly_bounded_to_budget_bytes() -> None:
    class BoundedStreamCounter:
        def __init__(self, data: bytes) -> None:
            self._data = data
            self._pos = 0
            self.total_bytes_read = 0

        def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
            if whence == os.SEEK_SET:
                self._pos = offset
            elif whence == os.SEEK_END:
                self._pos = len(self._data) + offset
            elif whence == os.SEEK_CUR:
                self._pos += offset
            return self._pos

        def tell(self) -> int:
            return self._pos

        def read(self, n: int = -1) -> bytes:
            if n < 0:
                chunk = self._data[self._pos:]
            else:
                chunk = self._data[self._pos : self._pos + n]
            self._pos += len(chunk)
            self.total_bytes_read += len(chunk)
            return chunk

    test_sizes = [0, 1, 100, 10000, 65535, 65536, 65537, 70000, 131072, 500000]
    for size in test_sizes:
        raw_data = b"x" * size
        stream = BoundedStreamCounter(raw_data)
        total, head, tail, truncated, head_boundary, tail_boundary = codex_local._read_bounded_stream(stream)
        assert total == size
        assert stream.total_bytes_read <= codex_local.MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM
        assert len(head) + len(tail) <= codex_local.MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM
        if size <= 65536:
            assert truncated is False
            assert len(tail) == 0
        else:
            assert truncated is True
            assert len(head) == 32768
            assert len(tail) == 32767
            # Total bytes read across head and tail chunk is exactly 65536
            assert stream.total_bytes_read == 65536


# --- TASK-088 SYNTHETIC REGRESSION TESTS ---


def test_codex_outcome_observability_implemented(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        json.dumps({"type": "turn.started"}),
        json.dumps({"type": "command_execution", "name": "git_status"}),
        json.dumps({"type": "file_change", "path": "src/module.py"}),
        json.dumps({"type": "message", "role": "assistant", "content": "Done work.\nAIOS_EXECUTOR_OUTCOME: IMPLEMENTED"}),
    ]
    stdout_bytes = ("\n".join(events) + "\n").encode("utf-8")
    process = _FakeProcess(returncode=0, stdout_bytes=stdout_bytes)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    diag = outcome.diagnostic
    assert diag.executor_outcome == "IMPLEMENTED"
    assert diag.final_agent_message_observed == "YES"
    assert diag.command_activity_count == 1
    assert diag.file_change_activity_count == 1


def test_codex_outcome_observability_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        json.dumps({"type": "message", "role": "assistant", "content": "Cannot complete work.\nAIOS_EXECUTOR_OUTCOME: BLOCKED"}),
    ]
    stdout_bytes = ("\n".join(events) + "\n").encode("utf-8")
    process = _FakeProcess(returncode=0, stdout_bytes=stdout_bytes)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    diag = outcome.diagnostic
    assert diag.executor_outcome == "BLOCKED"
    assert diag.final_agent_message_observed == "YES"


def test_codex_outcome_observability_no_work_required(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        json.dumps({"type": "message", "role": "assistant", "content": "Work already done.\nAIOS_EXECUTOR_OUTCOME: NO_WORK_REQUIRED"}),
    ]
    stdout_bytes = ("\n".join(events) + "\n").encode("utf-8")
    process = _FakeProcess(returncode=0, stdout_bytes=stdout_bytes)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    diag = outcome.diagnostic
    assert diag.executor_outcome == "NO_WORK_REQUIRED"
    assert diag.final_agent_message_observed == "YES"


def test_codex_outcome_observability_instruction_conflict(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        json.dumps({"type": "message", "role": "assistant", "content": "Conflicting instructions.\nAIOS_EXECUTOR_OUTCOME: INSTRUCTION_CONFLICT"}),
    ]
    stdout_bytes = ("\n".join(events) + "\n").encode("utf-8")
    process = _FakeProcess(returncode=0, stdout_bytes=stdout_bytes)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    diag = outcome.diagnostic
    assert diag.executor_outcome == "INSTRUCTION_CONFLICT"
    assert diag.final_agent_message_observed == "YES"


def test_codex_outcome_observability_no_terminal_marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        json.dumps({"type": "message", "role": "assistant", "content": "Finished response without explicit marker."}),
    ]
    stdout_bytes = ("\n".join(events) + "\n").encode("utf-8")
    process = _FakeProcess(returncode=0, stdout_bytes=stdout_bytes)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    diag = outcome.diagnostic
    assert diag.executor_outcome == "UNKNOWN"
    assert diag.final_agent_message_observed == "YES"


def test_codex_outcome_observability_reasoning_like_content_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        json.dumps({"type": "reasoning", "content": "Thinking about AIOS_EXECUTOR_OUTCOME: IMPLEMENTED"}),
        json.dumps({"type": "message", "role": "assistant", "content": "Actual final response without marker."}),
    ]
    stdout_bytes = ("\n".join(events) + "\n").encode("utf-8")
    process = _FakeProcess(returncode=0, stdout_bytes=stdout_bytes)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    diag = outcome.diagnostic
    assert diag.executor_outcome == "UNKNOWN"
    assert diag.final_agent_message_observed == "YES"


def test_codex_outcome_observability_non_final_message_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    events = [
        json.dumps({"type": "message", "role": "assistant", "content": "Drafting...\nAIOS_EXECUTOR_OUTCOME: IMPLEMENTED"}),
        json.dumps({"type": "message", "role": "assistant", "content": "Final turn: I am actually blocked.\nAIOS_EXECUTOR_OUTCOME: BLOCKED"}),
    ]
    stdout_bytes = ("\n".join(events) + "\n").encode("utf-8")
    process = _FakeProcess(returncode=0, stdout_bytes=stdout_bytes)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    diag = outcome.diagnostic
    assert diag.executor_outcome == "BLOCKED"
    assert diag.final_agent_message_observed == "YES"


def test_codex_outcome_observability_unobservable_activity_stays_unknown(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stdout_bytes = b"non json text stream output\n"
    process = _FakeProcess(returncode=0, stdout_bytes=stdout_bytes)
    outcome, _, _ = _invoke_with_diagnostic_process(monkeypatch, tmp_path, process)

    diag = outcome.diagnostic
    assert diag.executor_outcome == "UNKNOWN"
    assert diag.final_agent_message_observed == "UNKNOWN"
    assert diag.command_activity_count == "UNKNOWN"
    assert diag.file_change_activity_count == "UNKNOWN"
