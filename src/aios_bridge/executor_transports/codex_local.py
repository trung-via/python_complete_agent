"""Fail-closed local Codex process transport (ADR-030 / E2)."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from typing import Mapping

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor_transport import (
    ExecutionTransport,
    ExecutorInvocation,
    InvocationReceipt,
    InvocationStatus,
    validate_invocation_payload,
    validate_invocation_receipt,
    validate_transport_binding,
)


CODEX_EXECUTOR_ID = "codex"
CODEX_TRANSPORT_ID = "codex-local-v1"
DEFAULT_CODEX_TIMEOUT_SECONDS = 1800
MAX_CODEX_TIMEOUT_SECONDS = 7200

ERROR_CODEX_NOT_FOUND = "CODEX_NOT_FOUND"
ERROR_CODEX_START_FAILED = "CODEX_START_FAILED"
ERROR_WORKSPACE_PRECONDITION_FAILED = "WORKSPACE_PRECONDITION_FAILED"
ERROR_CODEX_EXIT_NONZERO = "CODEX_EXIT_NONZERO"
ERROR_CODEX_TIMEOUT = "CODEX_TIMEOUT"
ERROR_CALLER_INTERRUPTED = "CALLER_INTERRUPTED"
ERROR_CODEX_EXIT_CODE_INVALID = "CODEX_EXIT_CODE_INVALID"

_GIT_PREFLIGHT_TIMEOUT_SECONDS = 10
_CLEANUP_WAIT_SECONDS = 2
_IS_WINDOWS = sys.platform == "win32"

_WINDOWS_ENVIRONMENT_ALLOWLIST = frozenset(
    {
        "PATH",
        "PATHEXT",
        "SystemRoot",
        "WINDIR",
        "COMSPEC",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
        "TEMP",
        "TMP",
        "CODEX_HOME",
        "LANG",
        "LC_ALL",
        "TERM",
    }
)
_POSIX_ENVIRONMENT_ALLOWLIST = frozenset(
    {
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "TERM",
        "CODEX_HOME",
    }
)
_SECRET_ENVIRONMENT_DENYLIST = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "DEEPSEEK_API_KEY",
        "MINIMAX_API_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AZURE_OPENAI_API_KEY",
    }
)


def _build_child_environment(source: Mapping[str, str]) -> dict[str, str]:
    """Build the closed, subscription-first child environment."""
    allowlist = (
        _WINDOWS_ENVIRONMENT_ALLOWLIST
        if os.name == "nt"
        else _POSIX_ENVIRONMENT_ALLOWLIST
    )
    child = {key: source[key] for key in allowlist if key in source}
    for key in _SECRET_ENVIRONMENT_DENYLIST:
        child.pop(key, None)
    return child


def _validate_timeout_seconds(value: object) -> int:
    if type(value) is not int or not 1 <= value <= MAX_CODEX_TIMEOUT_SECONDS:
        raise ContinuityStateValidationError(
            "timeout_seconds must be an exact int between 1 and "
            f"{MAX_CODEX_TIMEOUT_SECONDS}"
        )
    return value


def _resolve_codex_executable(spec: str) -> str | None:
    if type(spec) is not str or not spec or spec != spec.strip():
        return None

    has_path_separator = os.sep in spec or (os.altsep is not None and os.altsep in spec)
    candidate = Path(spec)
    if candidate.is_absolute() or has_path_separator:
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            return None
        return str(resolved) if resolved.is_file() else None

    return shutil.which(spec)


def _build_codex_argv(executable: str, workspace: Path) -> list[str]:
    return [
        executable,
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


def _make_receipt(
    invocation: ExecutorInvocation,
    *,
    status: InvocationStatus,
    exit_code: int | None,
    error_code: str | None,
) -> InvocationReceipt:
    receipt = InvocationReceipt(
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
    validate_invocation_receipt(receipt, invocation)
    return receipt


def _resolve_workspace(workspace: Path) -> Path | None:
    try:
        resolved = workspace.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    return resolved if resolved.is_dir() else None


def _run_git_command(workspace: Path, *arguments: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(workspace), *arguments],
            cwd=str(workspace),
            shell=False,
            env=_build_child_environment(os.environ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            timeout=_GIT_PREFLIGHT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None


def _git_preflight(workspace: Path, target_branch: str) -> bool:
    toplevel = _run_git_command(workspace, "rev-parse", "--show-toplevel")
    if toplevel is None or toplevel.returncode != 0:
        return False
    try:
        reported_toplevel = Path(toplevel.stdout.rstrip("\r\n")).resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    if reported_toplevel != workspace:
        return False

    branch = _run_git_command(workspace, "branch", "--show-current")
    if branch is None or branch.returncode != 0:
        return False
    if branch.stdout.rstrip("\r\n") != target_branch:
        return False

    status = _run_git_command(
        workspace, "status", "--porcelain", "--untracked-files=all"
    )
    return status is not None and status.returncode == 0 and status.stdout == ""


def _cleanup_process(process: subprocess.Popen[bytes]) -> None:
    """Best-effort bounded process-group/tree cleanup."""
    try:
        candidate_pid = process.pid
    except Exception:
        candidate_pid = None
    pid = candidate_pid if type(candidate_pid) is int and candidate_pid > 0 else None

    if _IS_WINDOWS:
        try:
            process.terminate()
        except Exception:
            pass
        if pid is not None:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    shell=False,
                    env=_build_child_environment(os.environ),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=_CLEANUP_WAIT_SECONDS,
                    check=False,
                )
            except Exception:
                pass

        try:
            process.wait(timeout=_CLEANUP_WAIT_SECONDS)
            parent_exited = True
        except Exception:
            parent_exited = False
        if not parent_exited:
            try:
                process.kill()
            except Exception:
                pass
            try:
                process.wait(timeout=_CLEANUP_WAIT_SECONDS)
            except Exception:
                pass
        return

    if pid is None:
        try:
            process.terminate()
        except Exception:
            pass
        try:
            process.wait(timeout=_CLEANUP_WAIT_SECONDS)
            parent_exited = True
        except Exception:
            parent_exited = False
        if not parent_exited:
            try:
                process.kill()
            except Exception:
                pass
            try:
                process.wait(timeout=_CLEANUP_WAIT_SECONDS)
            except Exception:
                pass
        return

    try:
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    except Exception:
        pass
    try:
        process.wait(timeout=_CLEANUP_WAIT_SECONDS)
    except Exception:
        pass
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass
    except Exception:
        pass
    try:
        process.wait(timeout=_CLEANUP_WAIT_SECONDS)
    except Exception:
        pass


class CodexLocalTransport:
    """Synchronous local Codex transport with no authority or result semantics."""

    def __init__(
        self,
        workspace: str | Path,
        *,
        codex_executable: str = "codex",
        timeout_seconds: int = DEFAULT_CODEX_TIMEOUT_SECONDS,
    ) -> None:
        self._workspace = Path(workspace)
        self._codex_executable = codex_executable
        self._timeout_seconds = _validate_timeout_seconds(timeout_seconds)

    @property
    def transport_id(self) -> str:
        return CODEX_TRANSPORT_ID

    @property
    def executor_id(self) -> str:
        return CODEX_EXECUTOR_ID

    def invoke(
        self,
        invocation: ExecutorInvocation,
        payload: bytes,
    ) -> InvocationReceipt:
        validate_transport_binding(self, invocation)
        validate_invocation_payload(invocation, payload)

        workspace = _resolve_workspace(self._workspace)
        if workspace is None or not _git_preflight(workspace, invocation.target_branch):
            return _make_receipt(
                invocation,
                status=InvocationStatus.FAILED_TO_START,
                exit_code=None,
                error_code=ERROR_WORKSPACE_PRECONDITION_FAILED,
            )

        executable = _resolve_codex_executable(self._codex_executable)
        if executable is None:
            return _make_receipt(
                invocation,
                status=InvocationStatus.FAILED_TO_START,
                exit_code=None,
                error_code=ERROR_CODEX_NOT_FOUND,
            )

        environment = _build_child_environment(os.environ)
        argv = _build_codex_argv(executable, workspace)
        process: subprocess.Popen[bytes] | None = None
        popen_options: dict[str, object] = {}
        if os.name == "nt":
            popen_options["creationflags"] = getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
        else:
            popen_options["start_new_session"] = True

        try:
            process = subprocess.Popen(
                argv,
                cwd=str(workspace),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                env=environment,
                **popen_options,
            )
            process.communicate(input=payload, timeout=self._timeout_seconds)
        except subprocess.TimeoutExpired:
            if process is not None:
                _cleanup_process(process)
            return _make_receipt(
                invocation,
                status=InvocationStatus.TIMED_OUT,
                exit_code=None,
                error_code=ERROR_CODEX_TIMEOUT,
            )
        except KeyboardInterrupt:
            if process is not None:
                _cleanup_process(process)
            return _make_receipt(
                invocation,
                status=InvocationStatus.INTERRUPTED,
                exit_code=None,
                error_code=ERROR_CALLER_INTERRUPTED,
            )
        except OSError:
            if process is not None:
                _cleanup_process(process)
            return _make_receipt(
                invocation,
                status=InvocationStatus.FAILED_TO_START,
                exit_code=None,
                error_code=ERROR_CODEX_START_FAILED,
            )

        return_code = process.returncode
        if type(return_code) is not int or not -2_147_483_648 <= return_code <= 2_147_483_647:
            return _make_receipt(
                invocation,
                status=InvocationStatus.FAILED_TO_START,
                exit_code=None,
                error_code=ERROR_CODEX_EXIT_CODE_INVALID,
            )
        if return_code == 0:
            return _make_receipt(
                invocation,
                status=InvocationStatus.EXITED_ZERO,
                exit_code=0,
                error_code=None,
            )
        return _make_receipt(
            invocation,
            status=InvocationStatus.EXITED_NONZERO,
            exit_code=return_code,
            error_code=ERROR_CODEX_EXIT_NONZERO,
        )


__all__ = [
    "CODEX_EXECUTOR_ID",
    "CODEX_TRANSPORT_ID",
    "DEFAULT_CODEX_TIMEOUT_SECONDS",
    "CodexLocalTransport",
]
