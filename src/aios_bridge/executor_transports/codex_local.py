"""Fail-closed local Codex process transport with bounded diagnostic observability (ADR-030 / ADR-040 / E2 / TASK-067)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

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

MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM: int = 65536
MAX_CODEX_DIAGNOSTIC_EVENT_TYPES: int = 32
MAX_SINGLE_EVENT_TYPE_LENGTH: int = 64
MAX_DIAGNOSTIC_CODE_LENGTH: int = 64
MAX_SCHEMA_VERSION_LENGTH: int = 64

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

_EVENT_TYPE_RE = re.compile(r"\A[A-Za-z0-9_.:-]{1,64}\Z")
_FAILURE_EVENT_TYPES = frozenset({"error", "turn.failed"})


class CodexDiagnosticCode(str, Enum):
    """Closed vocabulary of safe diagnostic output codes for Codex execution streams."""
    EMPTY_OUTPUT = "EMPTY_OUTPUT"
    STDERR_ONLY = "STDERR_ONLY"
    JSON_EVENT_STREAM = "JSON_EVENT_STREAM"
    JSON_ERROR_EVENT = "JSON_ERROR_EVENT"
    NON_JSON_OUTPUT = "NON_JSON_OUTPUT"
    MIXED_OUTPUT = "MIXED_OUTPUT"
    UNKNOWN_OUTPUT_SHAPE = "UNKNOWN_OUTPUT_SHAPE"
    CAPTURE_FAILED = "CAPTURE_FAILED"


_ALLOWED_DIAGNOSTIC_CODES = frozenset(c.value for c in CodexDiagnosticCode)

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


@dataclass(frozen=True)
class CodexTransportDiagnostic:
    """Immutable safe diagnostic metadata derived from temporary Codex execution streams."""
    code: str
    stdout_total_bytes: int
    stderr_total_bytes: int
    stdout_scan_truncated: bool
    stderr_scan_truncated: bool
    stdout_json_line_count: int
    stdout_non_json_line_count: int
    stdout_event_types: tuple[str, ...]
    last_stdout_event_type: str | None
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ContinuityStateValidationError("schema_version must be non-empty string")
        if len(self.schema_version) > MAX_SCHEMA_VERSION_LENGTH:
            raise ContinuityStateValidationError(
                f"schema_version length ({len(self.schema_version)}) exceeds maximum ({MAX_SCHEMA_VERSION_LENGTH})"
            )

        if not isinstance(self.code, str) or self.code not in _ALLOWED_DIAGNOSTIC_CODES:
            raise ContinuityStateValidationError(
                f"diagnostic code must be one of {sorted(_ALLOWED_DIAGNOSTIC_CODES)}: got {self.code!r}"
            )

        for name, count_val in [
            ("stdout_total_bytes", self.stdout_total_bytes),
            ("stderr_total_bytes", self.stderr_total_bytes),
            ("stdout_json_line_count", self.stdout_json_line_count),
            ("stdout_non_json_line_count", self.stdout_non_json_line_count),
        ]:
            if type(count_val) is not int:
                raise ContinuityStateValidationError(f"{name} must be exact int (bool forbidden): got {count_val!r}")
            if count_val < 0:
                raise ContinuityStateValidationError(f"{name} must be non-negative: got {count_val}")

        for name, trunc_val in [
            ("stdout_scan_truncated", self.stdout_scan_truncated),
            ("stderr_scan_truncated", self.stderr_scan_truncated),
        ]:
            if type(trunc_val) is not bool:
                raise ContinuityStateValidationError(f"{name} must be exact bool: got {trunc_val!r}")

        if not isinstance(self.stdout_event_types, tuple):
            raise ContinuityStateValidationError(
                f"stdout_event_types must be exact tuple of strings: got {type(self.stdout_event_types).__name__}"
            )

        if len(self.stdout_event_types) > MAX_CODEX_DIAGNOSTIC_EVENT_TYPES:
            raise ContinuityStateValidationError(
                f"stdout_event_types count ({len(self.stdout_event_types)}) exceeds maximum ({MAX_CODEX_DIAGNOSTIC_EVENT_TYPES})"
            )

        for ev in self.stdout_event_types:
            if not isinstance(ev, str) or not _EVENT_TYPE_RE.fullmatch(ev):
                raise ContinuityStateValidationError(f"Invalid stdout_event_type: {ev!r}")
            if any(ord(c) < 32 or ord(c) == 127 for c in ev):
                raise ContinuityStateValidationError(f"event_type must not contain control characters: {ev!r}")

        if self.last_stdout_event_type is not None:
            if not isinstance(self.last_stdout_event_type, str) or not _EVENT_TYPE_RE.fullmatch(self.last_stdout_event_type):
                raise ContinuityStateValidationError(
                    f"Invalid last_stdout_event_type: {self.last_stdout_event_type!r}"
                )
            if any(ord(c) < 32 or ord(c) == 127 for c in self.last_stdout_event_type):
                raise ContinuityStateValidationError(
                    f"last_stdout_event_type must not contain control characters: {self.last_stdout_event_type!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "last_stdout_event_type": self.last_stdout_event_type,
            "schema_version": self.schema_version,
            "stderr_scan_truncated": self.stderr_scan_truncated,
            "stderr_total_bytes": self.stderr_total_bytes,
            "stdout_event_types": list(self.stdout_event_types),
            "stdout_json_line_count": self.stdout_json_line_count,
            "stdout_non_json_line_count": self.stdout_non_json_line_count,
            "stdout_scan_truncated": self.stdout_scan_truncated,
            "stdout_total_bytes": self.stdout_total_bytes,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def fingerprint(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest().lower()


@dataclass(frozen=True)
class CodexInvocationOutcome:
    """Immutable binding of canonical InvocationReceipt and bounded CodexTransportDiagnostic."""
    receipt: InvocationReceipt
    diagnostic: CodexTransportDiagnostic

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, InvocationReceipt):
            raise ContinuityStateValidationError(f"receipt must be InvocationReceipt: got {self.receipt!r}")
        if not isinstance(self.diagnostic, CodexTransportDiagnostic):
            raise ContinuityStateValidationError(
                f"diagnostic must be CodexTransportDiagnostic: got {self.diagnostic!r}"
            )


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


def _is_subpath_or_same(target: Path, base: Path) -> bool:
    """Check if target path is inside or identical to base path."""
    try:
        t_res = target.resolve()
        b_res = base.resolve()
        return t_res == b_res or b_res in t_res.parents
    except (ValueError, OSError, RuntimeError):
        return False


def _get_persistent_runtime_dirs() -> list[Path]:
    """Collect known persistent AIOS runtime directory paths matching Bridge runtime contract."""
    dirs: list[Path] = []

    # 1. Exact runtime override (Bridge: AIOS_RUNTIME_DIR)
    runtime_override = os.environ.get("AIOS_RUNTIME_DIR")
    if runtime_override:
        dirs.append(Path(runtime_override))

    # 2. Base directory override (Bridge: AIOS_HOME)
    home_override = os.environ.get("AIOS_HOME")
    if home_override:
        dirs.append(Path(home_override))

    # 3. Windows standard base (Bridge: LOCALAPPDATA / aios-bridge)
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        dirs.append(Path(local_app) / "aios-bridge")

    # 4. POSIX XDG base (Bridge: XDG_DATA_HOME / aios-bridge)
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        dirs.append(Path(xdg_data) / "aios-bridge")

    # 5. Standard home fallbacks (Bridge: ~/.aios-bridge, and legacy ~/.aios_bridge)
    dirs.append(Path.home() / ".aios-bridge")
    dirs.append(Path.home() / ".aios_bridge")

    # 6. Legacy environment override if set
    legacy_env = os.environ.get("AIOS_BRIDGE_RUNTIME_DIR")
    if legacy_env:
        dirs.append(Path(legacy_env))

    return dirs


def _resolve_safe_temporary_dir(workspace: Path) -> Path | None:
    """Resolve a temporary directory that is provably outside workspace and persistent runtime."""
    try:
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    except (OSError, RuntimeError):
        return None

    if not temp_root.is_dir():
        return None

    # Fail closed if temp_root is inside or identical to workspace
    if _is_subpath_or_same(temp_root, workspace):
        return None

    # Fail closed if temp_root is inside any persistent AIOS runtime directory
    for r_dir in _get_persistent_runtime_dirs():
        if _is_subpath_or_same(temp_root, r_dir):
            return None

    return temp_root


def _analyze_diagnostic_stream(
    stdout_file: Any,
    stderr_file: Any,
) -> CodexTransportDiagnostic:
    """Safely analyze temporary stdout/stderr streams within strict bounds."""
    try:
        total_out = 0
        scan_out = b""
        if stdout_file is not None:
            try:
                stdout_file.seek(0, os.SEEK_END)
                total_out = stdout_file.tell()
                stdout_file.seek(0)
                scan_out = stdout_file.read(MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM)
            except Exception:
                pass

        total_err = 0
        scan_err = b""
        if stderr_file is not None:
            try:
                stderr_file.seek(0, os.SEEK_END)
                total_err = stderr_file.tell()
                stderr_file.seek(0)
                scan_err = stderr_file.read(MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM)
            except Exception:
                pass

        out_truncated = total_out > len(scan_out)
        err_truncated = total_err > len(scan_err)

        json_line_count = 0
        non_json_line_count = 0
        event_types: list[str] = []
        seen_event_types: set[str] = set()
        last_event_type: str | None = None
        has_failure_event = False

        if scan_out:
            raw_lines = scan_out.splitlines()
            for raw_line in raw_lines:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    decoded = line.decode("utf-8")
                    parsed = json.loads(decoded)
                    if isinstance(parsed, dict) and "type" in parsed:
                        ev_type = parsed["type"]
                        if (
                            isinstance(ev_type, str)
                            and ev_type
                            and len(ev_type) <= MAX_SINGLE_EVENT_TYPE_LENGTH
                            and _EVENT_TYPE_RE.fullmatch(ev_type)
                            and not any(ord(c) < 32 or ord(c) == 127 for c in ev_type)
                        ):
                            if (
                                ev_type not in seen_event_types
                                and len(event_types) < MAX_CODEX_DIAGNOSTIC_EVENT_TYPES
                            ):
                                event_types.append(ev_type)
                                seen_event_types.add(ev_type)
                            last_event_type = ev_type
                            if ev_type.lower() in _FAILURE_EVENT_TYPES:
                                has_failure_event = True
                        json_line_count += 1
                    else:
                        json_line_count += 1
                except Exception:
                    non_json_line_count += 1

        if total_out == 0 and total_err == 0:
            code = CodexDiagnosticCode.EMPTY_OUTPUT.value
        elif total_out == 0 and total_err > 0:
            code = CodexDiagnosticCode.STDERR_ONLY.value
        elif has_failure_event:
            code = CodexDiagnosticCode.JSON_ERROR_EVENT.value
        elif json_line_count > 0 and non_json_line_count == 0:
            code = CodexDiagnosticCode.JSON_EVENT_STREAM.value
        elif json_line_count > 0 and non_json_line_count > 0:
            code = CodexDiagnosticCode.MIXED_OUTPUT.value
        elif json_line_count == 0 and total_out > 0:
            code = CodexDiagnosticCode.NON_JSON_OUTPUT.value
        else:
            code = CodexDiagnosticCode.UNKNOWN_OUTPUT_SHAPE.value

        return CodexTransportDiagnostic(
            code=code,
            stdout_total_bytes=total_out,
            stderr_total_bytes=total_err,
            stdout_scan_truncated=out_truncated,
            stderr_scan_truncated=err_truncated,
            stdout_json_line_count=json_line_count,
            stdout_non_json_line_count=non_json_line_count,
            stdout_event_types=tuple(event_types),
            last_stdout_event_type=last_event_type,
        )
    except Exception:
        return CodexTransportDiagnostic(
            code=CodexDiagnosticCode.CAPTURE_FAILED.value,
            stdout_total_bytes=0,
            stderr_total_bytes=0,
            stdout_scan_truncated=False,
            stderr_scan_truncated=False,
            stdout_json_line_count=0,
            stdout_non_json_line_count=0,
            stdout_event_types=(),
            last_stdout_event_type=None,
        )


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
    """Synchronous local Codex transport with bounded diagnostic observability."""

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
        """Invoke Codex local transport conforming to ExecutionTransport Protocol."""
        return self.invoke_with_diagnostic(invocation, payload).receipt

    def invoke_with_diagnostic(
        self,
        invocation: ExecutorInvocation,
        payload: bytes,
    ) -> CodexInvocationOutcome:
        """Invoke Codex exactly once with temporary bounded diagnostic capture."""
        validate_transport_binding(self, invocation)
        validate_invocation_payload(invocation, payload)

        workspace = _resolve_workspace(self._workspace)
        if workspace is None or not _git_preflight(workspace, invocation.target_branch):
            receipt = _make_receipt(
                invocation,
                status=InvocationStatus.FAILED_TO_START,
                exit_code=None,
                error_code=ERROR_WORKSPACE_PRECONDITION_FAILED,
            )
            diagnostic = CodexTransportDiagnostic(
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
            return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

        # Ensure temporary capture location is strictly safe and outside workspace & persistent runtime
        safe_temp_dir = _resolve_safe_temporary_dir(workspace)
        if safe_temp_dir is None:
            receipt = _make_receipt(
                invocation,
                status=InvocationStatus.FAILED_TO_START,
                exit_code=None,
                error_code=ERROR_WORKSPACE_PRECONDITION_FAILED,
            )
            diagnostic = CodexTransportDiagnostic(
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
            return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

        executable = _resolve_codex_executable(self._codex_executable)
        if executable is None:
            receipt = _make_receipt(
                invocation,
                status=InvocationStatus.FAILED_TO_START,
                exit_code=None,
                error_code=ERROR_CODEX_NOT_FOUND,
            )
            diagnostic = CodexTransportDiagnostic(
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
            return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

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

        with tempfile.TemporaryFile(dir=safe_temp_dir) as out_f, tempfile.TemporaryFile(dir=safe_temp_dir) as err_f:
            timed_out = False
            interrupted = False
            start_failed = False
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=str(workspace),
                    stdin=subprocess.PIPE,
                    stdout=out_f,
                    stderr=err_f,
                    shell=False,
                    env=environment,
                    **popen_options,
                )
                process.communicate(input=payload, timeout=self._timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                if process is not None:
                    _cleanup_process(process)
            except KeyboardInterrupt:
                interrupted = True
                if process is not None:
                    _cleanup_process(process)
            except OSError:
                start_failed = True
                if process is not None:
                    _cleanup_process(process)

            # Analyze diagnostic metadata from temporary sinks
            diagnostic = _analyze_diagnostic_stream(out_f, err_f)

            if timed_out:
                receipt = _make_receipt(
                    invocation,
                    status=InvocationStatus.TIMED_OUT,
                    exit_code=None,
                    error_code=ERROR_CODEX_TIMEOUT,
                )
                return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

            if interrupted:
                receipt = _make_receipt(
                    invocation,
                    status=InvocationStatus.INTERRUPTED,
                    exit_code=None,
                    error_code=ERROR_CALLER_INTERRUPTED,
                )
                return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

            if start_failed:
                receipt = _make_receipt(
                    invocation,
                    status=InvocationStatus.FAILED_TO_START,
                    exit_code=None,
                    error_code=ERROR_CODEX_START_FAILED,
                )
                return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

            return_code = process.returncode if process is not None else None
            if type(return_code) is not int or not -2_147_483_648 <= return_code <= 2_147_483_647:
                receipt = _make_receipt(
                    invocation,
                    status=InvocationStatus.FAILED_TO_START,
                    exit_code=None,
                    error_code=ERROR_CODEX_EXIT_CODE_INVALID,
                )
                return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

            if return_code == 0:
                receipt = _make_receipt(
                    invocation,
                    status=InvocationStatus.EXITED_ZERO,
                    exit_code=0,
                    error_code=None,
                )
                return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)

            receipt = _make_receipt(
                invocation,
                status=InvocationStatus.EXITED_NONZERO,
                exit_code=return_code,
                error_code=ERROR_CODEX_EXIT_NONZERO,
            )
            return CodexInvocationOutcome(receipt=receipt, diagnostic=diagnostic)


__all__ = [
    "CODEX_EXECUTOR_ID",
    "CODEX_TRANSPORT_ID",
    "DEFAULT_CODEX_TIMEOUT_SECONDS",
    "MAX_CODEX_TIMEOUT_SECONDS",
    "MAX_CODEX_DIAGNOSTIC_SCAN_BYTES_PER_STREAM",
    "MAX_CODEX_DIAGNOSTIC_EVENT_TYPES",
    "MAX_SINGLE_EVENT_TYPE_LENGTH",
    "CodexDiagnosticCode",
    "CodexLocalTransport",
    "CodexTransportDiagnostic",
    "CodexInvocationOutcome",
]
