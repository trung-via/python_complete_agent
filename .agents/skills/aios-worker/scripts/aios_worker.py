#!/usr/bin/env python3
"""Repository-owned launcher for the frozen AIOS-renew worker kernel.

This file owns environment bootstrap and guarded post-PASS publication only.
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


AUTHORITATIVE_COMMIT = "2ee57fd87316fdf8eb52a77777c51dff6d023214"
AUTHORITATIVE_REPOSITORY = "https://github.com/trung-via/AIOS-renew.git"
PIN_LINE = (
    "aios-renew @ git+"
    f"{AUTHORITATIVE_REPOSITORY}@{AUTHORITATIVE_COMMIT}"
)
TASK_PATTERN = re.compile(r"^TASK-([0-9]+)\Z")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}\Z")
ALLOWED_ACTIONS = ("FIX", "RUN", "STATUS")
ALLOWED_EXECUTORS = ("antigravity", "codex")
PUBLICATION_FAILURE = 2
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


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class WorkerSurfaceError(RuntimeError):
    """Base class for a fail-closed worker surface error."""


class BootstrapError(WorkerSurfaceError):
    """The dedicated worker runtime could not be proven or created."""


class LineageError(WorkerSurfaceError):
    """A unique canonical remediation lineage could not be resolved."""


class PublicationError(WorkerSurfaceError):
    """Canonical AIOS execution passed but guarded publication failed."""


@dataclass(frozen=True)
class RuntimeLayout:
    state_root: Path
    runtime: Path
    bootstrap_lock: Path
    requirements: Path


@dataclass(frozen=True)
class FixLineage:
    review: Path
    remediation: Path
    prior_review: Path | None = None


@dataclass(frozen=True)
class PublicationResult:
    status: str
    head_sha: str


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


def _top_level_scalar(source: str, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
    match = pattern.search(source)
    if match is None:
        return None
    value = match.group(1).strip()
    if not value or value in ("|", ">", "null", "~"):
        return None
    if value.startswith('"') and value.endswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, str) else None
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value.split(" #", 1)[0].strip()


def _review_finding_ids(source: str) -> tuple[str, ...]:
    values = re.findall(
        r"^[ \t]+-[ \t]+id:[ \t]*([^#\r\n]+?)\s*$",
        source,
        re.MULTILINE,
    )
    return tuple(value.strip().strip("'\"") for value in values)


def resolve_fix_lineage(
    repo: Path,
    layout: RuntimeLayout,
    task_id: str,
    task_number: str,
    *,
    runner: CommandRunner = subprocess.run,
) -> FixLineage:
    """Locate one exact local REVIEW/REMEDIATION lineage for current HEAD."""

    current_sha = _git(repo, "rev-parse", "HEAD", runner=runner)
    review_dir = layout.state_root / "reviews"
    remediation_dir = layout.state_root / "remediations"
    review_records: list[
        tuple[Path, str, str, str, tuple[str, ...], str | None]
    ] = []

    for path in sorted(review_dir.glob(f"REVIEW-{task_number}-*.yaml")):
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        review_id = _top_level_scalar(source, "review_id")
        reviewed_sha = _top_level_scalar(source, "reviewed_sha")
        mode = _top_level_scalar(source, "mode")
        verdict = _top_level_scalar(source, "verdict")
        if (
            review_id != path.stem
            or not review_id.startswith(f"REVIEW-{task_number}-")
            or reviewed_sha is None
            or mode not in ("PRIMARY", "DELTA")
            or verdict is None
        ):
            continue
        review_records.append(
            (
                path,
                reviewed_sha,
                mode,
                verdict,
                _review_finding_ids(source),
                _top_level_scalar(source, "prior_finding_id"),
            )
        )

    current_reviews = [
        record
        for record in review_records
        if record[1] == current_sha and record[3] == "CHANGES_REQUIRED"
    ]
    if len(current_reviews) != 1:
        raise LineageError(
            f"FIX requires exactly one canonical CHANGES_REQUIRED REVIEW for {task_id} at current HEAD"
        )

    review_path, reviewed_sha, mode, _, finding_ids, prior_finding_id = (
        current_reviews[0]
    )
    remediation_matches: list[Path] = []
    for path in sorted(remediation_dir.glob(f"REMEDIATION-{task_number}-*.yaml")):
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        finding_id = _top_level_scalar(source, "finding_id")
        if (
            finding_id in finding_ids
            and _top_level_scalar(source, "reviewed_sha") == reviewed_sha
            and path.stem == f"REMEDIATION-{task_number}-{finding_id}"
        ):
            remediation_matches.append(path)
    if len(remediation_matches) != 1:
        raise LineageError(
            f"FIX requires exactly one canonical REMEDIATION for {task_id} at current HEAD"
        )

    prior_review: Path | None = None
    if mode == "DELTA":
        if prior_finding_id is None:
            raise LineageError("DELTA REVIEW is missing prior_finding_id")
        prior_matches = [
            record[0]
            for record in review_records
            if record[0] != review_path and prior_finding_id in record[4]
        ]
        if len(prior_matches) != 1:
            raise LineageError("DELTA REVIEW prior lineage is missing or ambiguous")
        prior_review = prior_matches[0]

    return FixLineage(
        review=review_path,
        remediation=remediation_matches[0],
        prior_review=prior_review,
    )


def kernel_command(
    python: Path,
    *,
    action: str,
    task_id: str,
    executor: str,
    repo: Path,
    lineage: FixLineage | None = None,
) -> tuple[str, ...]:
    base = (str(python), "-m", "aios_renew.operator")
    if action == "STATUS":
        return (*base, "task", task_id, "--repo", str(repo))
    if action == "RUN":
        command = (
            *base,
            "run",
            task_id,
            "--executor",
            executor,
            "--repo",
            str(repo),
        )
    else:
        if lineage is None:
            raise LineageError("FIX requires canonical review/remediation lineage")
        command = (
            *base,
            "remediate",
            task_id,
            "--review",
            str(lineage.review),
            "--remediation",
            str(lineage.remediation),
            "--executor",
            executor,
            "--repo",
            str(repo),
        )
        if lineage.prior_review is not None:
            command = (*command, "--prior-review", str(lineage.prior_review))
    if executor == "codex":
        command = (*command, "--codex-sandbox", "danger-full-access")
    return command


def invoke_kernel(
    command: Sequence[str],
    *,
    repo: Path,
    runner: CommandRunner = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    """Invoke the pinned kernel exactly once for one operator request."""

    return _run(command, cwd=repo, runner=runner)


def canonical_pass_head(action: str, stdout: str) -> str:
    banner = "AIOS RUN PASS" if action == "RUN" else "AIOS REMEDIATION PASS"
    lines = stdout.splitlines()
    if banner not in lines:
        raise PublicationError("AIOS returned success without a canonical PASS summary")
    heads = [
        line.removeprefix("head_sha: ")
        for line in lines
        if line.startswith("head_sha: ")
    ]
    if len(heads) != 1 or SHA_PATTERN.fullmatch(heads[0]) is None:
        raise PublicationError("AIOS PASS summary has no unique canonical head_sha")
    return heads[0]


def publish_after_pass(
    repo: Path,
    *,
    base_sha: str,
    result_head_sha: str,
    runner: CommandRunner = subprocess.run,
) -> PublicationResult:
    """Perform the sole permitted normal push after validating PASS state."""

    try:
        if _git(repo, "status", "--porcelain", runner=runner):
            raise PublicationError("worktree is dirty after AIOS PASS")
        local_head = _git(repo, "rev-parse", "HEAD", runner=runner)
        if local_head != result_head_sha:
            raise PublicationError("local HEAD does not equal canonical AIOS head_sha")
        if local_head == base_sha:
            return PublicationResult(status="NOT_REQUIRED", head_sha=local_head)

        branch = _git(
            repo,
            "symbolic-ref",
            "--quiet",
            "--short",
            "HEAD",
            runner=runner,
        )
        remote = _git(
            repo,
            "config",
            "--get",
            f"branch.{branch}.remote",
            runner=runner,
        )
        merge_ref = _git(
            repo,
            "config",
            "--get",
            f"branch.{branch}.merge",
            runner=runner,
        )
        if not remote or not merge_ref.startswith("refs/heads/"):
            raise PublicationError("attached branch has no valid remote+merge upstream")

        pushed = _run(
            ("git", "-C", str(repo), "push", remote, f"HEAD:{merge_ref}"),
            runner=runner,
        )
        if pushed.returncode != 0:
            detail = pushed.stderr.strip() or pushed.stdout.strip()
            raise PublicationError(f"normal upstream push failed: {detail}")
        return PublicationResult(status="PUSHED", head_sha=local_head)
    except PublicationError:
        raise
    except WorkerSurfaceError as exc:
        raise PublicationError(str(exc)) from exc


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
    parser.add_argument("task_id")
    parser.add_argument("--executor", required=True, choices=ALLOWED_EXECUTORS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        task_id, task_number = parse_task_id(args.task_id)
        repo = get_repo_root()
        layout = runtime_layout(repo)
        python = ensure_runtime(layout)

        lineage = None
        if args.action == "FIX":
            lineage = resolve_fix_lineage(
                repo,
                layout,
                task_id,
                task_number,
            )
        command = kernel_command(
            python,
            action=args.action,
            task_id=task_id,
            executor=args.executor,
            repo=repo,
            lineage=lineage,
        )

        if args.action == "STATUS":
            completed = invoke_kernel(command, repo=repo)
            _emit_completed(completed)
            return completed.returncode

        base_sha = _git(repo, "rev-parse", "HEAD")
        completed = invoke_kernel(command, repo=repo)
        _emit_completed(completed)
        if completed.returncode != 0:
            return completed.returncode

        result_head = canonical_pass_head(args.action, completed.stdout)
        try:
            publication = publish_after_pass(
                repo,
                base_sha=base_sha,
                result_head_sha=result_head,
            )
        except PublicationError as exc:
            print("AIOS_STATUS: PASS", file=sys.stderr)
            print("PUBLICATION_STATUS: FAILED", file=sys.stderr)
            print(f"PUBLICATION_ERROR: {exc}", file=sys.stderr)
            return PUBLICATION_FAILURE

        print(f"PUBLICATION_STATUS: {publication.status}")
        print(f"PUBLISHED_HEAD: {publication.head_sha}")
        print(f"NEXT: Review {task_id} in ChatGPT")
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
