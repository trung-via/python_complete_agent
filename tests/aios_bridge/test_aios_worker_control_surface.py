"""TASK-097 revision 3 certification for the AIOS-renew worker surface."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import MagicMock

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "aios-worker"
SCRIPT = SKILL_DIR / "scripts" / "aios_worker.py"
PIN_FILE = SKILL_DIR / "requirements-aios-renew.txt"
SKILL_FILE = SKILL_DIR / "SKILL.md"
WORKFLOW_FILE = REPO_ROOT / ".agents" / "workflows" / "aios-worker.md"
DOCS_FILE = REPO_ROOT / "docs" / "AIOS_UNIFIED_WORKER_WORKFLOW.md"
BASE_SHA = "1" * 40
HEAD_SHA = "2" * 40

if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))

import aios_worker as aw  # noqa: E402


def done(
    command=(),
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def direct_url(*, url: str | None = None, commit: str | None = None) -> str:
    return json.dumps(
        {
            "url": url or aw.AUTHORITATIVE_REPOSITORY,
            "vcs_info": {
                "vcs": "git",
                "commit_id": commit or aw.AUTHORITATIVE_COMMIT,
                "requested_revision": commit or aw.AUTHORITATIVE_COMMIT,
            },
        }
    )


def make_layout(tmp_path: Path) -> aw.RuntimeLayout:
    state = tmp_path / ".git" / "aios"
    requirements = tmp_path / "requirements-aios-renew.txt"
    requirements.write_text(aw.PIN_LINE + "\n", encoding="utf-8")
    return aw.RuntimeLayout(
        state_root=state,
        runtime=state / "worker-runtime",
        bootstrap_lock=state / "worker-bootstrap.lock",
        requirements=requirements,
    )


def write_review(
    layout: aw.RuntimeLayout,
    *,
    review_id: str = "REVIEW-097-001",
    sha: str = HEAD_SHA,
    mode: str = "PRIMARY",
    finding: str = "R1",
    prior_finding: str | None = None,
) -> Path:
    path = layout.state_root / "reviews" / f"{review_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = "" if prior_finding is None else f"prior_finding_id: {prior_finding}\n"
    path.write_text(
        f"""review_id: {review_id}
reviewed_sha: {sha}
mode: {mode}
verdict: CHANGES_REQUIRED
acceptance:
  AC1: FAIL
findings:
  - id: {finding}
    basis: AC1
    action: CODE_FIX
    location: example.py
    issue: issue
    expected: expected
{prior}""",
        encoding="utf-8",
    )
    return path


def write_remediation(
    layout: aw.RuntimeLayout,
    *,
    finding: str = "R1",
    sha: str = HEAD_SHA,
    suffix: str | None = None,
) -> Path:
    name = suffix or finding
    path = layout.state_root / "remediations" / f"REMEDIATION-097-{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""finding_id: {finding}
action: CODE_FIX
reviewed_sha: {sha}
modification_scope: [example.py]
affected_verification: [git diff --check]
""",
        encoding="utf-8",
    )
    return path


class TestImmutableRuntimePin:
    def test_dependency_file_is_exactly_one_active_immutable_pin(self):
        active = [
            line.strip()
            for line in PIN_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        assert active == [aw.PIN_LINE]
        assert active == [
            "aios-renew @ git+https://github.com/trung-via/AIOS-renew.git@"
            "2ee57fd87316fdf8eb52a77777c51dff6d023214"
        ]

    def test_authoritative_pep610_metadata_is_accepted(self):
        assert aw.provenance_is_authoritative(json.loads(direct_url()))

    @pytest.mark.parametrize(
        ("url", "commit"),
        [
            ("https://github.com/other/AIOS-renew.git", aw.AUTHORITATIVE_COMMIT),
            (aw.AUTHORITATIVE_REPOSITORY, "3" * 40),
            ("file:///C:/AIOS-renew", aw.AUTHORITATIVE_COMMIT),
        ],
    )
    def test_alternate_or_stale_provenance_is_rejected(self, url, commit):
        assert not aw.provenance_is_authoritative(
            json.loads(direct_url(url=url, commit=commit))
        )

    def test_runtime_validation_reads_distribution_direct_url(self, tmp_path):
        python = tmp_path / "python"
        python.touch()
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return done(command, stdout=direct_url())

        assert aw.runtime_is_authoritative(python, runner=runner)
        assert calls == [
            (
                (str(python), "-c", aw.PROVENANCE_PROGRAM),
                {
                    "cwd": None,
                    "capture_output": True,
                    "text": True,
                    "check": False,
                },
            )
        ]

    def test_unverifiable_runtime_is_rejected(self, tmp_path):
        python = tmp_path / "python"
        python.touch()
        assert not aw.runtime_is_authoritative(
            python,
            runner=lambda command, **kwargs: done(command, stdout="not-json"),
        )


class TestRuntimeBootstrap:
    def test_valid_runtime_is_reused_without_install(self, tmp_path, monkeypatch):
        layout = make_layout(tmp_path)
        python = aw.runtime_python(layout.runtime)
        python.parent.mkdir(parents=True)
        python.touch()
        monkeypatch.setattr(aw, "runtime_is_authoritative", lambda *a, **k: True)
        runner = MagicMock(side_effect=AssertionError("bootstrap command not expected"))

        assert aw.ensure_runtime(layout, runner=runner) == python
        runner.assert_not_called()

    def test_fresh_runtime_bootstrap_installs_only_requirements_pin(
        self, tmp_path, monkeypatch
    ):
        layout = make_layout(tmp_path)
        checks = iter([False, True, True])
        monkeypatch.setattr(
            aw,
            "runtime_is_authoritative",
            lambda *args, **kwargs: next(checks),
        )
        calls = []

        def runner(command, **kwargs):
            command = tuple(command)
            calls.append(command)
            if command[1:3] == ("-m", "venv"):
                python = aw.runtime_python(Path(command[-1]))
                python.parent.mkdir(parents=True)
                python.touch()
            return done(command)

        python = aw.ensure_runtime(layout, runner=runner)
        pip_calls = [call for call in calls if "pip" in call]
        assert python == aw.runtime_python(layout.runtime)
        assert python.is_file()
        assert pip_calls == [
            (
                str(aw.runtime_python(layout.state_root / f"worker-runtime.bootstrap-{aw.os.getpid()}")),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--requirement",
                str(layout.requirements),
            )
        ]

    def test_incomplete_runtime_is_rebuilt_atomically(self, tmp_path, monkeypatch):
        layout = make_layout(tmp_path)
        layout.runtime.mkdir(parents=True)
        (layout.runtime / "incomplete.txt").write_text("partial", encoding="utf-8")
        checks = iter([False, True, True])
        monkeypatch.setattr(
            aw,
            "runtime_is_authoritative",
            lambda *args, **kwargs: next(checks),
        )

        def runner(command, **kwargs):
            command = tuple(command)
            if command[1:3] == ("-m", "venv"):
                python = aw.runtime_python(Path(command[-1]))
                python.parent.mkdir(parents=True)
                python.touch()
            return done(command)

        aw.ensure_runtime(layout, runner=runner)
        assert aw.runtime_python(layout.runtime).is_file()
        assert not (layout.runtime / "incomplete.txt").exists()

    def test_concurrent_first_use_is_serialized_and_installs_once(self, tmp_path):
        layout = make_layout(tmp_path)
        installed = False
        calls = []
        calls_lock = threading.Lock()

        def runner(command, **kwargs):
            nonlocal installed
            command = tuple(command)
            with calls_lock:
                calls.append(command)
            if command[1:3] == ("-m", "venv"):
                python = aw.runtime_python(Path(command[-1]))
                python.parent.mkdir(parents=True)
                python.touch()
                return done(command)
            if "pip" in command:
                installed = True
                return done(command)
            if len(command) > 1 and command[1] == "-c":
                return done(command, returncode=0 if installed else 1, stdout=direct_url())
            return done(command)

        results = []

        def bootstrap():
            results.append(aw.ensure_runtime(layout, runner=runner))

        threads = [threading.Thread(target=bootstrap) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert len(results) == 2
        assert results[0] == results[1] == aw.runtime_python(layout.runtime)
        assert len([call for call in calls if "pip" in call]) == 1
        assert layout.bootstrap_lock.name == "worker-bootstrap.lock"
        assert layout.bootstrap_lock != layout.state_root / "operator.lock"

    def test_bootstrap_failure_occurs_before_any_kernel_invocation(
        self, tmp_path, monkeypatch
    ):
        repo = tmp_path
        layout = make_layout(tmp_path)
        monkeypatch.setattr(aw, "get_repo_root", lambda: repo)
        monkeypatch.setattr(aw, "runtime_layout", lambda value: layout)
        monkeypatch.setattr(
            aw,
            "ensure_runtime",
            MagicMock(side_effect=aw.BootstrapError("install failed")),
        )
        kernel = MagicMock()
        monkeypatch.setattr(aw, "invoke_kernel", kernel)

        assert aw.main(["RUN", "TASK-097", "--executor", "codex"]) == 1
        kernel.assert_not_called()


class TestBootstrapHostResolution:
    def test_windows_candidates_are_in_exact_documented_order(self, tmp_path):
        repository_python = tmp_path / "venv" / "Scripts" / "python.exe"
        repository_python.parent.mkdir(parents=True)
        repository_python.touch()
        assert aw.bootstrap_host_candidates(tmp_path, platform="nt") == (
            (str(repository_python),),
            ("py", "-3.11"),
            ("python3",),
            ("python",),
        )

    def test_posix_candidates_are_in_exact_documented_order(self, tmp_path):
        repository_python = tmp_path / "venv" / "bin" / "python"
        repository_python.parent.mkdir(parents=True)
        repository_python.touch()
        assert aw.bootstrap_host_candidates(tmp_path, platform="posix") == (
            (str(repository_python),),
            ("python3",),
            ("python",),
        )

    def test_bare_python_unavailable_still_selects_python3_once(self, tmp_path):
        calls = []

        def runner(command, **kwargs):
            calls.append((tuple(command), kwargs))
            if tuple(command[:2]) == ("py", "-3.11"):
                raise FileNotFoundError("py unavailable")
            if command[0] == "python3":
                return done(command)
            raise AssertionError("bare python must not be required after python3 succeeds")

        selected = aw.resolve_bootstrap_host(
            tmp_path,
            platform="nt",
            runner=runner,
        )
        assert selected == ("python3",)
        assert [call[0][0] for call in calls] == ["py", "python3"]
        assert all(call[0][-2:] == ("-c", aw.BOOTSTRAP_HOST_PROBE) for call in calls)

    def test_old_repository_python_is_rejected_before_py311(self, tmp_path):
        repository_python = tmp_path / "venv" / "Scripts" / "python.exe"
        repository_python.parent.mkdir(parents=True)
        repository_python.touch()
        calls = []

        def runner(command, **kwargs):
            calls.append(tuple(command))
            return done(command, returncode=1 if command[0] == str(repository_python) else 0)

        selected = aw.resolve_bootstrap_host(tmp_path, platform="nt", runner=runner)
        assert selected == ("py", "-3.11")
        assert [call[:-2] for call in calls] == [
            (str(repository_python),),
            ("py", "-3.11"),
        ]

    def test_no_python311_candidate_fails_closed_with_exact_reason(self, tmp_path):
        with pytest.raises(
            aw.BootstrapError,
            match="^BOOTSTRAP_INTERPRETER_UNAVAILABLE$",
        ):
            aw.resolve_bootstrap_host(
                tmp_path,
                platform="posix",
                runner=lambda command, **kwargs: done(command, returncode=1),
            )


class TestKernelRouting:
    @pytest.mark.parametrize("task_id", ["TASK-1", "TASK-097", "TASK-1000"])
    def test_positive_canonical_task_ids_allow_padding(self, task_id):
        assert aw.parse_task_id(task_id)[0] == task_id

    @pytest.mark.parametrize("task_id", ["TASK-0", "task-097", "TASK-", "TASK--1"])
    def test_noncanonical_or_zero_task_ids_fail_closed(self, task_id):
        with pytest.raises(aw.WorkerSurfaceError):
            aw.parse_task_id(task_id)

    def test_codex_run_exact_command(self, tmp_path):
        python = tmp_path / "python"
        command = aw.kernel_command(
            python,
            action="RUN",
            task_id="TASK-097",
            executor="codex",
            repo=tmp_path,
        )
        assert command == (
            str(python),
            "-m",
            "aios_renew.operator",
            "run",
            "TASK-097",
            "--executor",
            "codex",
            "--repo",
            str(tmp_path),
            "--codex-sandbox",
            "danger-full-access",
        )

    def test_antigravity_run_differs_only_by_executor_and_sandbox(self, tmp_path):
        python = tmp_path / "python"
        codex = aw.kernel_command(
            python,
            action="RUN",
            task_id="TASK-097",
            executor="codex",
            repo=tmp_path,
        )
        antigravity = aw.kernel_command(
            python,
            action="RUN",
            task_id="TASK-097",
            executor="antigravity",
            repo=tmp_path,
        )
        assert antigravity == codex[:-2][:6] + ("antigravity",) + codex[7:-2]
        assert "danger-full-access" not in antigravity

    def test_status_delegates_to_task_description_without_executor(self, tmp_path):
        command = aw.kernel_command(
            tmp_path / "python",
            action="STATUS",
            task_id="TASK-097",
            executor="codex",
            repo=tmp_path,
        )
        assert command[3:] == ("task", "TASK-097", "--repo", str(tmp_path))
        assert "--executor" not in command
        assert "push" not in command

    def test_one_run_request_invokes_kernel_exactly_once(self, tmp_path, monkeypatch):
        layout = make_layout(tmp_path)
        python = tmp_path / "worker-python"
        kernel = MagicMock(
            return_value=done(
                stdout=f"AIOS RUN PASS\nbase_sha: {BASE_SHA}\nhead_sha: {HEAD_SHA}\n"
            )
        )
        publication = MagicMock(
            return_value=aw.PublicationResult(status="PUSHED", head_sha=HEAD_SHA)
        )
        monkeypatch.setattr(aw, "get_repo_root", lambda: tmp_path)
        monkeypatch.setattr(aw, "runtime_layout", lambda repo: layout)
        monkeypatch.setattr(aw, "ensure_runtime", lambda value: python)
        monkeypatch.setattr(aw, "invoke_kernel", kernel)
        monkeypatch.setattr(aw, "publish_after_pass", publication)

        assert aw.main(["RUN", "TASK-097", "--executor", "codex"]) == 0
        kernel.assert_called_once_with(
            (
                str(python),
                "-m",
                "aios_renew.operator",
                "run",
                "TASK-097",
                "--executor",
                "codex",
                "--repo",
                str(tmp_path),
                "--codex-sandbox",
                "danger-full-access",
            ),
            repo=tmp_path,
        )
        publication.assert_called_once_with(
            tmp_path,
            canonical_baseline_sha=BASE_SHA,
            result_head_sha=HEAD_SHA,
        )

    def test_primary_sync_only_uses_canonical_base_and_never_samples_prehead(
        self, tmp_path, monkeypatch
    ):
        layout = make_layout(tmp_path)
        synchronized_sha = "4" * 40
        kernel = MagicMock(
            return_value=done(
                stdout=(
                    "AIOS RUN PASS\n"
                    f"base_sha: {synchronized_sha}\n"
                    f"head_sha: {synchronized_sha}\n"
                )
            )
        )
        publication = MagicMock(
            return_value=aw.PublicationResult("NOT_REQUIRED", synchronized_sha)
        )
        monkeypatch.setattr(aw, "get_repo_root", lambda: tmp_path)
        monkeypatch.setattr(aw, "runtime_layout", lambda repo: layout)
        monkeypatch.setattr(aw, "ensure_runtime", lambda value: tmp_path / "worker-python")
        monkeypatch.setattr(aw, "invoke_kernel", kernel)
        monkeypatch.setattr(
            aw,
            "_git",
            MagicMock(side_effect=AssertionError("pre-run local HEAD A must not be sampled")),
        )
        monkeypatch.setattr(aw, "publish_after_pass", publication)

        assert aw.main(["RUN", "TASK-097", "--executor", "codex"]) == 0
        kernel.assert_called_once()
        publication.assert_called_once_with(
            tmp_path,
            canonical_baseline_sha=synchronized_sha,
            result_head_sha=synchronized_sha,
        )

    def test_aios_failure_is_not_retried_or_published(self, tmp_path, monkeypatch):
        layout = make_layout(tmp_path)
        kernel = MagicMock(return_value=done(returncode=7, stderr="AIOS ERROR\n"))
        publication = MagicMock()
        monkeypatch.setattr(aw, "get_repo_root", lambda: tmp_path)
        monkeypatch.setattr(aw, "runtime_layout", lambda repo: layout)
        monkeypatch.setattr(aw, "ensure_runtime", lambda value: tmp_path / "python")
        monkeypatch.setattr(aw, "invoke_kernel", kernel)
        monkeypatch.setattr(aw, "publish_after_pass", publication)

        assert aw.main(["RUN", "TASK-097", "--executor", "codex"]) == 7
        assert kernel.call_count == 1
        publication.assert_not_called()

    def test_remediation_publication_uses_reviewed_sha_from_summary_and_lineage(
        self, tmp_path, monkeypatch
    ):
        layout = make_layout(tmp_path)
        review = tmp_path / "REVIEW-097-001.yaml"
        remediation = tmp_path / "REMEDIATION-097-R1.yaml"
        lineage = aw.FixLineage(review, remediation, BASE_SHA)
        kernel = MagicMock(
            return_value=done(
                stdout=(
                    "AIOS REMEDIATION PASS\n"
                    f"reviewed_sha: {BASE_SHA}\n"
                    f"head_sha: {HEAD_SHA}\n"
                )
            )
        )
        publication = MagicMock(
            return_value=aw.PublicationResult("PUSHED", HEAD_SHA)
        )
        monkeypatch.setattr(aw, "get_repo_root", lambda: tmp_path)
        monkeypatch.setattr(aw, "runtime_layout", lambda repo: layout)
        monkeypatch.setattr(aw, "ensure_runtime", lambda value: tmp_path / "worker-python")
        monkeypatch.setattr(aw, "resolve_fix_lineage", lambda *args: lineage)
        monkeypatch.setattr(aw, "invoke_kernel", kernel)
        monkeypatch.setattr(aw, "publish_after_pass", publication)

        assert aw.main(["FIX", "TASK-097", "--executor", "codex"]) == 0
        publication.assert_called_once_with(
            tmp_path,
            canonical_baseline_sha=BASE_SHA,
            result_head_sha=HEAD_SHA,
        )

    def test_status_does_not_read_head_resolve_lineage_or_publish(
        self, tmp_path, monkeypatch
    ):
        layout = make_layout(tmp_path)
        kernel = MagicMock(return_value=done(stdout="TASK-097\n"))
        monkeypatch.setattr(aw, "get_repo_root", lambda: tmp_path)
        monkeypatch.setattr(aw, "runtime_layout", lambda repo: layout)
        monkeypatch.setattr(aw, "ensure_runtime", lambda value: tmp_path / "python")
        monkeypatch.setattr(aw, "invoke_kernel", kernel)
        git = MagicMock(side_effect=AssertionError("STATUS must not inspect Git state"))
        lineage = MagicMock(side_effect=AssertionError("STATUS must not resolve FIX"))
        publish = MagicMock(side_effect=AssertionError("STATUS must not publish"))
        monkeypatch.setattr(aw, "_git", git)
        monkeypatch.setattr(aw, "resolve_fix_lineage", lineage)
        monkeypatch.setattr(aw, "publish_after_pass", publish)

        assert aw.main(["STATUS", "TASK-097", "--executor", "codex"]) == 0
        kernel.assert_called_once()
        git.assert_not_called()
        lineage.assert_not_called()
        publish.assert_not_called()


class TestFixLineage:
    def test_unique_primary_lineage_resolves(self, tmp_path):
        layout = make_layout(tmp_path)
        review = write_review(layout)
        remediation = write_remediation(layout)
        lineage = aw.resolve_fix_lineage(
            tmp_path,
            layout,
            "TASK-097",
            "097",
            runner=lambda *args, **kwargs: done(stdout=HEAD_SHA + "\n"),
        )
        assert lineage == aw.FixLineage(review, remediation, HEAD_SHA)

    @pytest.mark.parametrize("missing", ["review", "remediation"])
    def test_missing_lineage_fails_closed(self, tmp_path, missing):
        layout = make_layout(tmp_path)
        if missing != "review":
            write_review(layout)
        if missing != "remediation":
            write_remediation(layout)
        with pytest.raises(aw.LineageError, match="exactly one canonical"):
            aw.resolve_fix_lineage(
                tmp_path,
                layout,
                "TASK-097",
                "097",
                runner=lambda *args, **kwargs: done(stdout=HEAD_SHA + "\n"),
            )

    def test_ambiguous_current_review_fails_closed(self, tmp_path):
        layout = make_layout(tmp_path)
        write_review(layout, review_id="REVIEW-097-001", finding="R1")
        write_review(layout, review_id="REVIEW-097-002", finding="R2")
        write_remediation(layout)
        with pytest.raises(aw.LineageError, match="exactly one canonical.*REVIEW"):
            aw.resolve_fix_lineage(
                tmp_path,
                layout,
                "TASK-097",
                "097",
                runner=lambda *args, **kwargs: done(stdout=HEAD_SHA + "\n"),
            )

    def test_noncanonical_remediation_filename_is_ignored(self, tmp_path):
        layout = make_layout(tmp_path)
        write_review(layout)
        write_remediation(layout, suffix="wrong-name")
        with pytest.raises(aw.LineageError, match="exactly one canonical REMEDIATION"):
            aw.resolve_fix_lineage(
                tmp_path,
                layout,
                "TASK-097",
                "097",
                runner=lambda *args, **kwargs: done(stdout=HEAD_SHA + "\n"),
            )

    def test_delta_review_resolves_one_prior_review(self, tmp_path):
        layout = make_layout(tmp_path)
        prior = write_review(
            layout,
            review_id="REVIEW-097-001",
            sha=BASE_SHA,
            finding="R1",
        )
        current = write_review(
            layout,
            review_id="REVIEW-097-002",
            mode="DELTA",
            finding="R2",
            prior_finding="R1",
        )
        remediation = write_remediation(layout, finding="R2")
        lineage = aw.resolve_fix_lineage(
            tmp_path,
            layout,
            "TASK-097",
            "097",
            runner=lambda *args, **kwargs: done(stdout=HEAD_SHA + "\n"),
        )
        assert lineage == aw.FixLineage(current, remediation, HEAD_SHA, prior)
        command = aw.kernel_command(
            tmp_path / "python",
            action="FIX",
            task_id="TASK-097",
            executor="codex",
            repo=tmp_path,
            lineage=lineage,
        )
        assert command.count("--prior-review") == 1
        assert command[command.index("--prior-review") + 1] == str(prior)

    def test_delta_missing_prior_review_fails_closed(self, tmp_path):
        layout = make_layout(tmp_path)
        write_review(
            layout,
            review_id="REVIEW-097-002",
            mode="DELTA",
            finding="R2",
            prior_finding="R1",
        )
        write_remediation(layout, finding="R2")
        with pytest.raises(aw.LineageError, match="prior lineage"):
            aw.resolve_fix_lineage(
                tmp_path,
                layout,
                "TASK-097",
                "097",
                runner=lambda *args, **kwargs: done(stdout=HEAD_SHA + "\n"),
            )


class TestCanonicalPassSummary:
    def test_primary_uses_exact_base_and_head(self):
        summary = aw.canonical_pass_summary(
            "RUN",
            f"AIOS RUN PASS\nbase_sha: {BASE_SHA}\nhead_sha: {HEAD_SHA}\n",
        )
        assert summary == aw.CanonicalPassSummary("base_sha", BASE_SHA, HEAD_SHA)

    def test_remediation_uses_exact_reviewed_and_head_bound_to_lineage(self):
        summary = aw.canonical_pass_summary(
            "FIX",
            (
                "AIOS REMEDIATION PASS\n"
                f"reviewed_sha: {BASE_SHA}\n"
                f"head_sha: {HEAD_SHA}\n"
            ),
            expected_baseline_sha=BASE_SHA,
        )
        assert summary == aw.CanonicalPassSummary(
            "reviewed_sha", BASE_SHA, HEAD_SHA
        )

    @pytest.mark.parametrize(
        "stdout",
        [
            f"AIOS RUN PASS\nhead_sha: {HEAD_SHA}\n",
            (
                f"AIOS RUN PASS\nbase_sha: {BASE_SHA}\n"
                f"base_sha: {BASE_SHA}\nhead_sha: {HEAD_SHA}\n"
            ),
            (
                f"AIOS RUN PASS\nbase_sha: {BASE_SHA}\n"
                f"base_sha:not-canonical\nhead_sha: {HEAD_SHA}\n"
            ),
            f"AIOS RUN PASS\nbase_sha: not-a-sha\nhead_sha: {HEAD_SHA}\n",
            (
                f"AIOS RUN PASS\nbase_sha: {BASE_SHA}\n"
                f"head_sha: {HEAD_SHA}\nhead_sha: {HEAD_SHA}\n"
            ),
            (
                f"AIOS RUN PASS\nAIOS RUN PASS\n"
                f"base_sha: {BASE_SHA}\nhead_sha: {HEAD_SHA}\n"
            ),
            (
                f"AIOS RUN PASS\nbase_sha: {BASE_SHA}\n"
                f"reviewed_sha: {BASE_SHA}\nhead_sha: {HEAD_SHA}\n"
            ),
        ],
    )
    def test_missing_duplicate_malformed_or_inconsistent_primary_fails_closed(
        self, stdout
    ):
        with pytest.raises(aw.PublicationError):
            aw.canonical_pass_summary("RUN", stdout)

    def test_remediation_summary_must_match_resolved_lineage(self):
        with pytest.raises(aw.PublicationError, match="canonical remediation lineage"):
            aw.canonical_pass_summary(
                "FIX",
                (
                    "AIOS REMEDIATION PASS\n"
                    f"reviewed_sha: {BASE_SHA}\n"
                    f"head_sha: {HEAD_SHA}\n"
                ),
                expected_baseline_sha="5" * 40,
            )


class TestGuardedPublication:
    def publication_runner(self, *, push_code=0, dirty=False, head=HEAD_SHA):
        calls = []

        def runner(command, **kwargs):
            command = tuple(command)
            calls.append(command)
            tail = command[3:]
            if tail == ("status", "--porcelain"):
                return done(command, stdout=" M dirty.py\n" if dirty else "")
            if tail == ("rev-parse", "HEAD"):
                return done(command, stdout=head + "\n")
            if tail == ("symbolic-ref", "--quiet", "--short", "HEAD"):
                return done(command, stdout="migration/aios-renew-surface\n")
            if tail == (
                "config",
                "--get",
                "branch.migration/aios-renew-surface.remote",
            ):
                return done(command, stdout="origin\n")
            if tail == (
                "config",
                "--get",
                "branch.migration/aios-renew-surface.merge",
            ):
                return done(command, stdout="refs/heads/migration/aios-renew-surface\n")
            if tail[:2] == ("push", "origin"):
                return done(command, returncode=push_code, stderr="push failed")
            raise AssertionError(command)

        return runner, calls

    def test_canonical_base_b_to_head_c_pushes_exactly_once(self, tmp_path):
        runner, calls = self.publication_runner()
        result = aw.publish_after_pass(
            tmp_path,
            canonical_baseline_sha=BASE_SHA,
            result_head_sha=HEAD_SHA,
            runner=runner,
        )
        pushes = [call for call in calls if "push" in call]
        assert result == aw.PublicationResult("PUSHED", HEAD_SHA)
        assert pushes == [
            (
                "git",
                "-C",
                str(tmp_path),
                "push",
                "origin",
                "HEAD:refs/heads/migration/aios-renew-surface",
            )
        ]
        assert all("--force" not in call and "-f" not in call for call in pushes)

    def test_canonical_base_b_equals_head_b_issues_zero_push(self, tmp_path):
        runner, calls = self.publication_runner(head=BASE_SHA)
        result = aw.publish_after_pass(
            tmp_path,
            canonical_baseline_sha=BASE_SHA,
            result_head_sha=BASE_SHA,
            runner=runner,
        )
        assert result.status == "NOT_REQUIRED"
        assert not [call for call in calls if "push" in call]

    def test_dirty_or_head_mismatch_prevents_push(self, tmp_path):
        dirty_runner, dirty_calls = self.publication_runner(dirty=True)
        with pytest.raises(aw.PublicationError, match="dirty"):
            aw.publish_after_pass(
                tmp_path,
                canonical_baseline_sha=BASE_SHA,
                result_head_sha=HEAD_SHA,
                runner=dirty_runner,
            )
        assert not [call for call in dirty_calls if "push" in call]

        mismatch_runner, mismatch_calls = self.publication_runner(head="3" * 40)
        with pytest.raises(aw.PublicationError, match="does not equal"):
            aw.publish_after_pass(
                tmp_path,
                canonical_baseline_sha=BASE_SHA,
                result_head_sha=HEAD_SHA,
                runner=mismatch_runner,
            )
        assert not [call for call in mismatch_calls if "push" in call]

    def test_push_failure_is_distinct_and_not_retried(self, tmp_path):
        runner, calls = self.publication_runner(push_code=1)
        with pytest.raises(aw.PublicationError, match="normal upstream push failed"):
            aw.publish_after_pass(
                tmp_path,
                canonical_baseline_sha=BASE_SHA,
                result_head_sha=HEAD_SHA,
                runner=runner,
            )
        assert len([call for call in calls if "push" in call]) == 1

    def test_main_reports_aios_pass_and_publication_failure_separately(
        self, tmp_path, monkeypatch, capsys
    ):
        layout = make_layout(tmp_path)
        kernel = MagicMock(
            return_value=done(
                stdout=f"AIOS RUN PASS\nbase_sha: {BASE_SHA}\nhead_sha: {HEAD_SHA}\n"
            )
        )
        monkeypatch.setattr(aw, "get_repo_root", lambda: tmp_path)
        monkeypatch.setattr(aw, "runtime_layout", lambda repo: layout)
        monkeypatch.setattr(aw, "ensure_runtime", lambda value: tmp_path / "python")
        monkeypatch.setattr(aw, "invoke_kernel", kernel)
        monkeypatch.setattr(
            aw,
            "publish_after_pass",
            MagicMock(side_effect=aw.PublicationError("network unavailable")),
        )

        assert aw.main(["RUN", "TASK-097", "--executor", "codex"]) == 2
        captured = capsys.readouterr()
        assert "AIOS RUN PASS" in captured.out
        assert "AIOS_STATUS: PASS" in captured.err
        assert "PUBLICATION_STATUS: FAILED" in captured.err
        assert kernel.call_count == 1


class TestSurfaceAndDocumentation:
    def test_active_launcher_has_no_legacy_execution_tokens(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "src.aios_bridge",
            "bridge.py",
            "WorkerFlowCoordinator",
            "--adapter",
        ):
            assert forbidden not in source
        assert "pytest" not in source
        assert "aios_renew.operator" in source

    def test_surface_files_bind_only_their_executor_and_same_launcher(self):
        skill = SKILL_FILE.read_text(encoding="utf-8")
        workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
        assert "--executor codex" in skill
        assert "--executor antigravity" not in skill
        assert "--executor antigravity" in workflow
        assert "--executor codex" not in workflow
        assert "scripts/aios_worker.py" in skill
        assert "scripts/aios_worker.py" in workflow
        assert "must not" in skill.lower() and "implementation" in skill.lower()
        assert "must not" in workflow.lower() and "implementation" in workflow.lower()

    @pytest.mark.parametrize("surface", [SKILL_FILE, WORKFLOW_FILE])
    def test_surfaces_resolve_bootstrap_host_without_requiring_bare_python(
        self, surface
    ):
        text = surface.read_text(encoding="utf-8")
        windows_order = [
            "venv/Scripts/python.exe",
            "py -3.11",
            "python3",
            "then `python`",
        ]
        positions = [text.index(token) for token in windows_order]
        assert positions == sorted(positions)
        assert "venv/bin/python" in text
        assert aw.BOOTSTRAP_HOST_PROBE in text
        assert "BOOTSTRAP_INTERPRETER_UNAVAILABLE" in text
        assert "invoke the launcher exactly once" in text.lower()
        assert "python .agents/skills/aios-worker/scripts/aios_worker.py" not in text
        assert ".git/aios/worker-runtime" in text

    def test_surface_files_are_lf_frontmatter_without_bom(self):
        for path in (SKILL_FILE, WORKFLOW_FILE):
            raw = path.read_bytes()
            assert raw.startswith(b"---\n")
            assert not raw.startswith(b"\xef\xbb\xbf")
            assert b"\r\n" not in raw

    def test_docs_name_sole_kernel_runtime_publication_and_migration_boundary(self):
        text = DOCS_FILE.read_text(encoding="utf-8")
        assert "delegate exclusively" in text
        assert aw.AUTHORITATIVE_COMMIT in text
        assert "worker-bootstrap.lock" in text
        assert "PEP 610" in text
        assert "normal non-force push" in text
        assert "bare `python`" in text
        assert "venv/Scripts/python.exe" in text
        assert "BOOTSTRAP_INTERPRETER_UNAVAILABLE" in text
        assert "`base_sha`" in text and "`reviewed_sha`" in text
        assert "never uses a\nlocal HEAD sampled before" in text
        assert "fresh or\nexplicitly reloaded" in text
        assert "TASK-096 remains pending" in text
        assert "archived" in text and "inactive" in text

    def test_product_requirements_and_task_096_are_not_modified_by_task_097(self):
        task = (REPO_ROOT / ".ai" / "tasks" / "TASK-097.yaml").read_text(
            encoding="utf-8"
        )
        assert "requirements.txt" not in task.split("modify:", 1)[1].split(
            "non_goals:", 1
        )[0]
        assert (REPO_ROOT / ".ai" / "tasks" / "TASK-096.yaml").is_file()
