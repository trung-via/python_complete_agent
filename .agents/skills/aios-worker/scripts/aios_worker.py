#!/usr/bin/env python3
"""Repository-owned launcher for the frozen AIOS-renew worker kernel.

This file owns environment bootstrap and operator protocol translation only.
TASK, RUN, RESULT, EVIDENCE, review, remediation, and executor semantics remain
inside the pinned AIOS-renew distribution.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import BinaryIO, Callable, Sequence


AUTHORITATIVE_COMMIT = "67db82bf19d63f25721d06aabb82d850db8b78d4"
AUTHORITATIVE_REPOSITORY = "https://github.com/trung-via/AIOS-renew.git"
PIN_LINE = (
    "aios-renew @ git+"
    f"{AUTHORITATIVE_REPOSITORY}@{AUTHORITATIVE_COMMIT}"
)
TASK_PATTERN = re.compile(r"^TASK-([0-9]+)\Z")
RUN_ID_PATTERN = re.compile(r"^RUN-([0-9]+)-([0-9]+)\Z")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}\Z")
ALLOWED_ACTIONS = ("FIX", "REPAIR", "RUN", "STATUS")
ALLOWED_EXECUTORS = ("antigravity", "codex")
PROVENANCE_PROGRAM = """\
import importlib.metadata
import sys

try:
    distribution = importlib.metadata.distribution("aios-renew")
    value = distribution.read_text("direct_url.json")
except (importlib.metadata.PackageNotFoundError, OSError):
    raise SystemExit(1)
if not value:
    raise SystemExit(1)
sys.stdout.write(value)
"""
BOOTSTRAP_HOST_PROBE = (
    "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
)


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class WorkerSurfaceError(RuntimeError):
    """Base class for a fail-closed worker surface error."""


class BootstrapError(WorkerSurfaceError):
    """The dedicated worker runtime could not be proven or created."""


@dataclass(frozen=True)
class RuntimeLayout:
    state_root: Path
    runtime: Path
    bootstrap_lock: Path
    requirements: Path


@dataclass(frozen=True)
class CanonicalPassSummary:
    baseline_field: str
    baseline_sha: str
    head_sha: str
    task_id: str | None = None
    failed_run: str | None = None


class BootstrapLock:
    """Blocking cross-process lock used only while validating/bootstraping."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file: BinaryIO | None = None

    def __enter__(self) -> "BootstrapLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.path.open("a+b")
        try:
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except OSError:
            lock_file.close()
            raise
        self._file = lock_file
        return self

    def __exit__(self, *args: object) -> None:
        if self._file is None:
            return
        lock_file = self._file
        self._file = None
        try:
            lock_file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()


def get_repo_root() -> Path:
    """Resolve the product repository from this checked-in script's layout."""

    script_path = Path(__file__).resolve()
    root = script_path.parent.parent.parent.parent.parent
    if not (root / ".ai" / "tasks").is_dir():
        raise WorkerSurfaceError(f"repository task store not found at {root}")
    return root


def parse_task_id(raw_task: str) -> tuple[str, str]:
    match = TASK_PATTERN.fullmatch(raw_task)
    if match is None or int(match.group(1)) <= 0:
        raise WorkerSurfaceError(
            f"invalid task ID {raw_task!r}; expected canonical TASK-<positive digits>"
        )
    return raw_task, match.group(1)


def parse_run_id(raw_run_id: str) -> str:
    match = RUN_ID_PATTERN.fullmatch(raw_run_id)
    if (
        match is None
        or int(match.group(1)) <= 0
        or int(match.group(2)) <= 0
    ):
        raise WorkerSurfaceError(
            f"invalid run ID {raw_run_id!r}; expected canonical RUN-<positive task id>-<positive run digits>"
        )
    return raw_run_id


def bootstrap_host_candidates(
    repo: Path,
    *,
    platform: str | None = None,
) -> tuple[tuple[str, ...], ...]:
    """Return the documented bootstrap-host argv candidates in fixed order."""

    selected_platform = os.name if platform is None else platform
    if selected_platform == "nt":
        repository_python = repo / "venv" / "Scripts" / "python.exe"
        candidates: list[tuple[str, ...]] = []
        if repository_python.is_file():
            candidates.append((str(repository_python),))
        candidates.extend((("py", "-3.11"), ("python3",), ("python",)))
        return tuple(candidates)

    repository_python = repo / "venv" / "bin" / "python"
    candidates = []
    if repository_python.is_file():
        candidates.append((str(repository_python),))
    candidates.extend((("python3",), ("python",)))
    return tuple(candidates)


def resolve_bootstrap_host(
    repo: Path,
    *,
    platform: str | None = None,
    runner: CommandRunner = subprocess.run,
) -> tuple[str, ...]:
    """Select the first fixed candidate proven to be Python 3.11 or newer."""

    for candidate in bootstrap_host_candidates(repo, platform=platform):
        try:
            completed = runner(
                (*candidate, "-c", BOOTSTRAP_HOST_PROBE),
                cwd=str(repo),
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            continue
        if completed.returncode == 0:
            return candidate
    raise BootstrapError("BOOTSTRAP_INTERPRETER_UNAVAILABLE")


def _run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    runner: CommandRunner = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            tuple(str(item) for item in command),
            cwd=None if cwd is None else str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise WorkerSurfaceError(f"command launch failed: {exc}") from exc


def _git(
    repo: Path,
    *args: str,
    runner: CommandRunner = subprocess.run,
) -> str:
    completed = _run(("git", "-C", str(repo), *args), runner=runner)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise WorkerSurfaceError(f"Git command failed: {detail}")
    return completed.stdout.strip()


def runtime_layout(
    repo: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> RuntimeLayout:
    git_dir_value = _git(repo, "rev-parse", "--git-dir", runner=runner)
    git_dir = Path(git_dir_value)
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    state_root = git_dir.resolve() / "aios"
    skill_dir = repo / ".agents" / "skills" / "aios-worker"
    return RuntimeLayout(
        state_root=state_root,
        runtime=state_root / "worker-runtime",
        bootstrap_lock=state_root / "worker-bootstrap.lock",
        requirements=skill_dir / "requirements-aios-renew.txt",
    )


def runtime_python(runtime: Path) -> Path:
    if os.name == "nt":
        return runtime / "Scripts" / "python.exe"
    return runtime / "bin" / "python"


def _normalise_repository_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized


def provenance_is_authoritative(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    vcs = payload.get("vcs_info")
    if not isinstance(vcs, dict):
        return False
    return (
        _normalise_repository_url(payload.get("url"))
        == _normalise_repository_url(AUTHORITATIVE_REPOSITORY)
        and vcs.get("vcs") == "git"
        and vcs.get("commit_id") == AUTHORITATIVE_COMMIT
    )


def runtime_is_authoritative(
    python: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> bool:
    if not python.is_file():
        return False
    completed = _run((str(python), "-c", PROVENANCE_PROGRAM), runner=runner)
    if completed.returncode != 0:
        return False
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False
    return provenance_is_authoritative(payload)


def _remove_generated_runtime(path: Path, *, state_root: Path) -> None:
    resolved = path.resolve()
    root = state_root.resolve()
    if resolved.parent != root or not resolved.name.startswith("worker-runtime"):
        raise BootstrapError(f"refusing to remove unexpected runtime path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def ensure_runtime(
    layout: RuntimeLayout,
    *,
    runner: CommandRunner = subprocess.run,
) -> Path:
    """Return a runtime proven by PEP 610 metadata, bootstrapping once if needed."""

    if not layout.requirements.is_file():
        raise BootstrapError(f"worker dependency pin missing: {layout.requirements}")
    pin_lines = [
        line.strip()
        for line in layout.requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if pin_lines != [PIN_LINE]:
        raise BootstrapError("worker dependency file does not contain the exact immutable pin")

    layout.state_root.mkdir(parents=True, exist_ok=True)
    try:
        with BootstrapLock(layout.bootstrap_lock):
            current_python = runtime_python(layout.runtime)
            if runtime_is_authoritative(current_python, runner=runner):
                return current_python

            staging = layout.state_root / f"worker-runtime.bootstrap-{os.getpid()}"
            _remove_generated_runtime(staging, state_root=layout.state_root)
            try:
                created = _run(
                    (sys.executable, "-m", "venv", str(staging)),
                    runner=runner,
                )
                if created.returncode != 0:
                    detail = created.stderr.strip() or created.stdout.strip()
                    raise BootstrapError(f"worker runtime creation failed: {detail}")

                staging_python = runtime_python(staging)
                installed = _run(
                    (
                        str(staging_python),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "--no-input",
                        "--requirement",
                        str(layout.requirements),
                    ),
                    runner=runner,
                )
                if installed.returncode != 0:
                    detail = installed.stderr.strip() or installed.stdout.strip()
                    raise BootstrapError(f"pinned AIOS-renew installation failed: {detail}")
                if not runtime_is_authoritative(staging_python, runner=runner):
                    raise BootstrapError(
                        "installed worker runtime provenance does not match the authoritative source+commit"
                    )

                _remove_generated_runtime(layout.runtime, state_root=layout.state_root)
                os.replace(staging, layout.runtime)
            except Exception:
                _remove_generated_runtime(staging, state_root=layout.state_root)
                raise

            final_python = runtime_python(layout.runtime)
            if not runtime_is_authoritative(final_python, runner=runner):
                raise BootstrapError("final worker runtime failed provenance validation")
            return final_python
    except OSError as exc:
        raise BootstrapError(f"worker runtime bootstrap lock failed: {exc}") from exc


def kernel_command(
    python: Path,
    *,
    action: str,
    target: str,
    executor: str,
    repo: Path,
    finding_id: str | None = None,
) -> tuple[str, ...]:
    base = (str(python), "-m", "aios_renew.operator")
    if action == "STATUS":
        return (*base, "task", target, "--repo", str(repo))
    if action == "RUN":
        return (
            *base,
            "run",
            target,
            "--executor",
            executor,
            "--repo",
            str(repo),
        )
    if action == "REPAIR":
        return (
            *base,
            "repair",
            target,
            "--executor",
            executor,
            "--repo",
            str(repo),
        )
    if finding_id is None:
        raise WorkerSurfaceError("FIX requires an explicit finding identifier")
    return (
        *base,
        "remediate",
        target,
        "--finding",
        finding_id,
        "--executor",
        executor,
        "--repo",
        str(repo),
    )


def invoke_kernel(
    command: Sequence[str],
    *,
    repo: Path,
    runner: CommandRunner = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    """Invoke the pinned kernel exactly once for one operator request."""

    return _run(command, cwd=repo, runner=runner)


def _unique_summary_field(lines: list[str], field: str) -> str:
    field_lines = [line for line in lines if line.startswith(f"{field}:")]
    if len(field_lines) != 1 or not field_lines[0].startswith(f"{field}: "):
        raise WorkerSurfaceError(
            f"AIOS PASS summary requires exactly one valid {field}"
        )
    return field_lines[0].removeprefix(f"{field}: ").strip()


def _unique_summary_sha(lines: list[str], field: str) -> str:
    value = _unique_summary_field(lines, field)
    if SHA_PATTERN.fullmatch(value) is None:
        raise WorkerSurfaceError(
            f"AIOS PASS summary requires exactly one valid {field}"
        )
    return value


def canonical_pass_summary(
    action: str,
    stdout: str,
) -> CanonicalPassSummary:
    if action not in ("RUN", "FIX", "REPAIR"):
        raise WorkerSurfaceError(f"unsupported PASS summary action: {action}")

    all_banners = {
        "RUN": "AIOS RUN PASS",
        "FIX": "AIOS REMEDIATION PASS",
        "REPAIR": "AIOS REPAIR PASS",
    }
    banner = all_banners[action]
    other_banners = [b for a, b in all_banners.items() if a != action]

    lines = stdout.splitlines()
    if lines.count(banner) != 1 or any(ob in lines for ob in other_banners):
        raise WorkerSurfaceError("AIOS returned no unique canonical PASS summary")

    if action == "REPAIR":
        if any(line.startswith("base_sha:") or line.startswith("reviewed_sha:") for line in lines):
            raise WorkerSurfaceError("AIOS PASS summary contains unexpected SHA field for REPAIR")
        failed_run = _unique_summary_field(lines, "failed_run")
        parse_run_id(failed_run)
        task_id = _unique_summary_field(lines, "task")
        parse_task_id(task_id)
        failed_head_sha = _unique_summary_sha(lines, "failed_head_sha")
        head_sha = _unique_summary_sha(lines, "head_sha")
        return CanonicalPassSummary(
            baseline_field="failed_head_sha",
            baseline_sha=failed_head_sha,
            head_sha=head_sha,
            task_id=task_id,
            failed_run=failed_run,
        )

    baseline_field = "base_sha" if action == "RUN" else "reviewed_sha"
    unexpected_fields = [
        "failed_head_sha",
        "failed_run",
        "reviewed_sha" if action == "RUN" else "base_sha",
    ]
    if any(any(line.startswith(f"{f}:") for line in lines) for f in unexpected_fields):
        raise WorkerSurfaceError(
            "AIOS PASS summary contains inconsistent fields"
        )
    baseline_sha = _unique_summary_sha(lines, baseline_field)
    head_sha = _unique_summary_sha(lines, "head_sha")
    return CanonicalPassSummary(
        baseline_field=baseline_field,
        baseline_sha=baseline_sha,
        head_sha=head_sha,
    )


def _emit_completed(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(
            completed.stderr,
            end="" if completed.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aios_worker.py")
    parser.add_argument("action", choices=ALLOWED_ACTIONS)
    parser.add_argument("target")
    parser.add_argument("finding_id", nargs="?")
    parser.add_argument("--executor", required=True, choices=ALLOWED_EXECUTORS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        if sys.version_info < (3, 11):
            raise BootstrapError("BOOTSTRAP_INTERPRETER_UNAVAILABLE")
        args = _parser().parse_args(argv)
        if args.action == "REPAIR":
            target = parse_run_id(args.target)
            if args.finding_id is not None:
                raise WorkerSurfaceError(
                    "REPAIR does not accept a finding identifier"
                )
        else:
            target, _ = parse_task_id(args.target)
            if args.action == "FIX":
                if args.finding_id is None:
                    raise WorkerSurfaceError("FIX requires an explicit finding identifier")
            elif args.finding_id is not None:
                raise WorkerSurfaceError(
                    f"{args.action} does not accept a finding identifier"
                )
        repo = get_repo_root()
        layout = runtime_layout(repo)
        python = ensure_runtime(layout)

        command = kernel_command(
            python,
            action=args.action,
            target=target,
            executor=args.executor,
            repo=repo,
            finding_id=args.finding_id,
        )

        if args.action == "STATUS":
            completed = invoke_kernel(command, repo=repo)
            _emit_completed(completed)
            return completed.returncode

        completed = invoke_kernel(command, repo=repo)
        _emit_completed(completed)
        if completed.returncode != 0:
            return completed.returncode

        summary = canonical_pass_summary(
            args.action,
            completed.stdout,
        )

        if args.action == "REPAIR" and summary.failed_run != target:
            raise WorkerSurfaceError(
                f"AIOS REPAIR PASS summary failed_run {summary.failed_run!r} does not match requested target {target!r}"
            )

        review_task = summary.task_id if args.action == "REPAIR" and summary.task_id else target

        print(f"REVIEW_CANDIDATE_HEAD: {summary.head_sha}")
        print(f"NEXT: Review {review_task} in ChatGPT")
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    except WorkerSurfaceError as exc:
        print(f"AIOS WORKER ERROR: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"AIOS WORKER ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
