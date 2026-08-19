from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess

import pytest

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity import executor_transport as contract
from src.aios_bridge.continuity.executor_transport import (
    ExecutionTransport,
    ExecutorInvocation,
    InvocationStatus,
    validate_invocation_receipt,
)
from src.aios_bridge.executor_transports import (
    CODEX_EXECUTOR_ID,
    CODEX_TRANSPORT_ID,
    DEFAULT_CODEX_TIMEOUT_SECONDS,
    CodexLocalTransport,
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
    ) -> None:
        self.returncode = returncode
        self.communicate_error = communicate_error
        self.inputs: list[tuple[bytes, int]] = []
        self.pid = 41041

    def communicate(self, *, input: bytes, timeout: int) -> tuple[None, None]:
        self.inputs.append((input, timeout))
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
        return process

    monkeypatch.setattr(codex_local.subprocess, "Popen", fake_popen)
    return calls


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
        "exec",
        "--ephemeral",
        "--json",
        "--color",
        "never",
        "--sandbox",
        "workspace-write",
        "--ask-for-approval",
        "never",
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        'web_search="disabled"',
        "-C",
        str(workspace),
        "-",
    ]
    assert options["cwd"] == str(workspace)
    assert options["stdin"] is subprocess.PIPE
    assert options["stdout"] is subprocess.DEVNULL
    assert options["stderr"] is subprocess.DEVNULL
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
