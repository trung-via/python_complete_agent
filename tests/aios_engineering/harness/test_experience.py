"""Tests for bounded H1 repository/control-plane experience provenance."""
from __future__ import annotations

import dataclasses
import inspect
import io
from pathlib import Path
import subprocess

import pytest

from src.aios_engineering.harness.contracts import (
    EvidenceKind,
    RepositoryEvidenceRef,
    RepositorySnapshotRef,
)
from src.aios_engineering.harness.discovery import (
    NON_REGULAR_GIT_MODE,
    RepositoryDiscoveryExclusion,
    RepositoryDiscoveryResult,
    discover_repository_snapshot,
)
from src.aios_engineering.harness.errors import HarnessFingerprintError, HarnessValidationError
from src.aios_engineering.harness.experience import (
    EXPERIENCE_SCHEMA_VERSION,
    H1_EXPERIENCE_POLICY_VERSION,
    LEARNING_PATH_PREFIXES,
    MAX_EXPERIENCE_EVIDENCE_COUNT,
    ControlPlaneExperienceManifest,
    ControlPlaneSnapshotRef,
    ExperienceArtifactKind,
    ExperienceArtifactRef,
    ExperienceManifestBoundError,
    ExperienceManifestGitError,
    ExperienceSurface,
    RepositoryExperienceManifest,
    _ControlGitTreeEntry,
    _convert_control_tree_entries,
    _open_control_git_process,
    _parse_control_tree_record,
    _read_control_tree_stream,
    _run_control_git_tree,
    build_repository_experience_manifest,
    classify_experience_artifact,
    discover_control_plane_experience,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
TREE_A = "e" * 40
TREE_B = "f" * 40


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    return completed.stdout


def _write(repo: Path, relative_path: str, content: bytes) -> None:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


@pytest.fixture
def dual_git_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repository"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "h1-experience@example.invalid")
    _git(repo, "config", "user.name", "H1 Experience Tests")

    repository_files = {
        ".ai/learning/repository-lesson.md": b"repository learning\n",
        ".ai/results/shared.md": b"repository result\n",
        ".ai/tasks/repository-task.md": b"not selected from repository surface\n",
        "src/pkg/module.py": b"VALUE = 'snapshot'\n",
    }
    for relative_path, content in repository_files.items():
        _write(repo, relative_path, content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "repository snapshot")
    repository_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()

    control_files = {
        ".ai/decisions/ADR-X.md": b"decision\n",
        ".ai/findings/control-finding.md": b"explicit learning path only\n",
        ".ai/results/control-result.md": b"control result\n",
        ".ai/reviews/REVIEW-X.md": b"review\n",
        ".ai/tasks/TASK-X.md": b"task\n",
        ".ai/unknown/not-experience.md": b"unknown\n",
    }
    for relative_path, content in control_files.items():
        _write(repo, relative_path, content)
    link_blob = _git(
        repo,
        "hash-object",
        "-w",
        "--stdin",
        input_bytes=b".ai/tasks/TASK-X.md",
    ).decode("ascii").strip()
    _git(repo, "add", "-A")
    _git(
        repo,
        "update-index",
        "--add",
        "--cacheinfo",
        f"120000,{link_blob},.ai/tasks/task-link.md",
    )
    _git(repo, "commit", "-q", "-m", "control snapshot")
    control_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()

    # Mutable and untracked bytes must not replace either frozen snapshot.
    _write(repo, ".ai/tasks/TASK-X.md", b"dirty task worktree bytes\n")
    _write(repo, ".ai/reviews/untracked.md", b"untracked review\n")
    return repo, repository_commit, control_commit


def _record(
    path: bytes = b".ai/tasks/TASK-X.md",
    *,
    sha: bytes = b"a" * 40,
    mode: bytes = b"100644",
    object_type: bytes = b"blob",
) -> bytes:
    return mode + b" " + object_type + b" " + sha + b"\t" + path


def _repository_evidence(path: str, sha: str) -> RepositoryEvidenceRef:
    return RepositoryEvidenceRef(
        path=path,
        blob_sha=sha,
        evidence_kind=EvidenceKind.CONTRACT,
        reason_code="DISCOVERED_GIT_BLOB",
        priority=0,
    )


def _repository_discovery(
    *,
    commit: str = SHA_A,
    tree: str = TREE_A,
    evidence: tuple[RepositoryEvidenceRef, ...] | None = None,
    exclusions: tuple[RepositoryDiscoveryExclusion, ...] = (),
) -> RepositoryDiscoveryResult:
    selected = evidence or (
        _repository_evidence(".ai/results/shared.md", SHA_A),
        _repository_evidence(".ai/learning/lesson.md", SHA_B),
    )
    return RepositoryDiscoveryResult.create(
        RepositorySnapshotRef(commit, tree),
        selected,
        exclusions,
    )


def _control_manifest(
    *,
    commit: str = SHA_C,
    tree: str = TREE_B,
    evidence: tuple[ExperienceArtifactRef, ...] | None = None,
) -> ControlPlaneExperienceManifest:
    selected = evidence or (
        ExperienceArtifactRef(
            ExperienceSurface.CONTROL_PLANE,
            ".ai/tasks/TASK-X.md",
            SHA_C,
            ExperienceArtifactKind.TASK,
        ),
    )
    return ControlPlaneExperienceManifest.create(
        ControlPlaneSnapshotRef(commit, tree),
        selected,
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".ai/tasks/TASK-X.md", ExperienceArtifactKind.TASK),
        (".ai/results/RESULT-X.md", ExperienceArtifactKind.RESULT),
        (".ai/reviews/REVIEW-X.md", ExperienceArtifactKind.REVIEW),
        (".ai/decisions/ADR-X.md", ExperienceArtifactKind.DECISION),
        (".ai/learning/a.md", ExperienceArtifactKind.LEARNING),
        (".ai/lessons/a.md", ExperienceArtifactKind.LEARNING),
        (".ai/findings/a.md", ExperienceArtifactKind.LEARNING),
        (".ai/skills/a.md", ExperienceArtifactKind.LEARNING),
        (".ai/knowledge/a.md", ExperienceArtifactKind.LEARNING),
        (".ai/context/not-experience.md", None),
        ("src/pkg/module.py", None),
    ],
)
def test_explicit_path_classification(path: str, expected: ExperienceArtifactKind | None):
    assert classify_experience_artifact(path) is expected


def test_learning_prefixes_are_explicit_and_conservative():
    assert LEARNING_PATH_PREFIXES == tuple(sorted(LEARNING_PATH_PREFIXES))
    assert classify_experience_artifact(".ai/learningish/not-learning.md") is None


@pytest.mark.parametrize(
    "record",
    [
        b"",
        b"100644 blob " + b"a" * 40,
        b"10064 blob " + b"a" * 40 + b"\t.ai/tasks/TASK-X.md",
        b"100644 bad$type " + b"a" * 40 + b"\t.ai/tasks/TASK-X.md",
        b"100644 blob short\t.ai/tasks/TASK-X.md",
        b"100644 blob " + b"a" * 40 + b"\t",
    ],
)
def test_malformed_control_git_records_fail_closed(record: bytes):
    with pytest.raises(HarnessValidationError):
        _parse_control_tree_record(record)


@pytest.mark.parametrize(
    "path",
    [
        b"/.ai/tasks/TASK-X.md",
        b"../.ai/tasks/TASK-X.md",
        b".ai//tasks/TASK-X.md",
        b".ai/tasks/../../secret",
        b".git/config",
        b".ai\\tasks\\TASK-X.md",
        b".ai/tasks/bad\npath.md",
    ],
)
def test_unsafe_control_paths_fail_closed_without_normalization(path: bytes):
    with pytest.raises(HarnessValidationError):
        _parse_control_tree_record(_record(path))


def test_control_stream_and_record_and_entry_bounds_are_enforced():
    framed = _record() + b"\0"
    with pytest.raises(ExperienceManifestBoundError, match="stream bytes"):
        _read_control_tree_stream(
            io.BytesIO(framed),
            max_stream_bytes=len(framed) - 1,
        )
    with pytest.raises(ExperienceManifestBoundError, match="record bytes"):
        _read_control_tree_stream(
            io.BytesIO(framed),
            max_record_bytes=len(framed) - 2,
        )
    with pytest.raises(ExperienceManifestBoundError, match="entry count"):
        _read_control_tree_stream(
            io.BytesIO(framed + framed),
            max_entries=1,
        )


def test_control_stream_requires_nul_termination_and_uses_bounded_reads():
    class RecordingStream(io.BytesIO):
        def __init__(self, initial_bytes: bytes):
            super().__init__(initial_bytes)
            self.read_sizes: list[int] = []

        def read(self, size: int = -1) -> bytes:
            self.read_sizes.append(size)
            assert size > 0
            return super().read(size)

    stream = RecordingStream(_record() + b"\0")
    assert len(_read_control_tree_stream(stream)) == 1
    assert stream.read_sizes
    with pytest.raises(HarnessValidationError, match="unterminated"):
        _read_control_tree_stream(io.BytesIO(_record()))


def test_non_regular_unknown_and_non_blob_entries_are_never_promoted():
    entries = (
        _ControlGitTreeEntry(".ai/tasks/regular.md", SHA_A, "100644", "blob"),
        _ControlGitTreeEntry(".ai/reviews/link.md", SHA_B, "120000", "blob"),
        _ControlGitTreeEntry(".ai/decisions/tree.md", SHA_C, "100644", "tree"),
        _ControlGitTreeEntry("src/unknown.py", SHA_D, "100644", "blob"),
    )
    evidence = _convert_control_tree_entries(entries)
    assert [(item.path, item.artifact_kind) for item in evidence] == [
        (".ai/tasks/regular.md", ExperienceArtifactKind.TASK)
    ]


def test_duplicate_conflicting_control_paths_are_rejected():
    entries = (
        _ControlGitTreeEntry(".ai/tasks/TASK-X.md", SHA_A, "100644", "blob"),
        _ControlGitTreeEntry(".ai/tasks/TASK-X.md", SHA_B, "100644", "blob"),
    )
    with pytest.raises(HarnessValidationError, match="duplicate or conflicting"):
        _convert_control_tree_entries(entries)


def test_experience_count_bound_is_enforced(monkeypatch: pytest.MonkeyPatch):
    import src.aios_engineering.harness.experience as experience

    monkeypatch.setattr(experience, "MAX_EXPERIENCE_EVIDENCE_COUNT", 1)
    entries = (
        _ControlGitTreeEntry(".ai/tasks/A.md", SHA_A, "100644", "blob"),
        _ControlGitTreeEntry(".ai/tasks/B.md", SHA_B, "100644", "blob"),
    )
    with pytest.raises(ExperienceManifestBoundError, match="evidence count"):
        _convert_control_tree_entries(entries)


def test_fingerprint_payload_bound_is_enforced(monkeypatch: pytest.MonkeyPatch):
    import src.aios_engineering.harness.experience as experience

    monkeypatch.setattr(experience, "MAX_EXPERIENCE_FINGERPRINT_PAYLOAD_BYTES", 1)
    with pytest.raises(ExperienceManifestBoundError, match="fingerprint payload"):
        _control_manifest()


@pytest.mark.parametrize(
    "invalid_identity",
    [
        "HEAD",
        "ai-control",
        "a" * 12,
        "A" * 40,
        "a" * 39,
        "a" * 41,
        "g" * 40,
        "a" * 40 + "^",
    ],
)
def test_exact_lowercase_control_commit_is_required(
    dual_git_repository: tuple[Path, str, str],
    invalid_identity: str,
):
    repo, _, _ = dual_git_repository
    with pytest.raises(HarnessValidationError, match="exact lowercase 40-hex"):
        discover_control_plane_experience(repo, invalid_identity)


def test_exact_non_commit_control_object_is_rejected(
    dual_git_repository: tuple[Path, str, str],
):
    repo, _, control_commit = dual_git_repository
    blob_sha = _git(
        repo,
        "rev-parse",
        f"{control_commit}:.ai/tasks/TASK-X.md",
    ).decode("ascii").strip()
    with pytest.raises(ExperienceManifestGitError, match="not a commit"):
        discover_control_plane_experience(repo, blob_sha)


def test_control_discovery_binds_exact_tree_and_blobs_without_worktree_bytes(
    dual_git_repository: tuple[Path, str, str],
):
    repo, _, control_commit = dual_git_repository
    manifest = discover_control_plane_experience(repo, control_commit)
    expected_tree = _git(repo, "rev-parse", f"{control_commit}^{{tree}}").decode("ascii").strip()
    expected_blob = _git(
        repo,
        "rev-parse",
        f"{control_commit}:.ai/tasks/TASK-X.md",
    ).decode("ascii").strip()
    evidence_by_path = {item.path: item for item in manifest.evidence}

    assert manifest.snapshot.control_commit_sha == control_commit
    assert manifest.snapshot.control_tree_sha == expected_tree
    assert evidence_by_path[".ai/tasks/TASK-X.md"].blob_sha == expected_blob
    assert ".ai/reviews/untracked.md" not in evidence_by_path
    assert ".ai/unknown/not-experience.md" not in evidence_by_path
    assert ".ai/tasks/task-link.md" not in evidence_by_path
    assert manifest.schema_version == EXPERIENCE_SCHEMA_VERSION
    assert manifest.policy_version == H1_EXPERIENCE_POLICY_VERSION
    assert type(manifest.evidence) is tuple

    kinds = {item.path: item.artifact_kind for item in manifest.evidence}
    assert kinds[".ai/tasks/TASK-X.md"] is ExperienceArtifactKind.TASK
    assert kinds[".ai/reviews/REVIEW-X.md"] is ExperienceArtifactKind.REVIEW
    assert kinds[".ai/decisions/ADR-X.md"] is ExperienceArtifactKind.DECISION
    assert kinds[".ai/results/control-result.md"] is ExperienceArtifactKind.RESULT
    assert kinds[".ai/findings/control-finding.md"] is ExperienceArtifactKind.LEARNING


def test_control_discovery_is_deterministic_and_snapshot_sensitive(
    dual_git_repository: tuple[Path, str, str],
):
    repo, repository_commit, control_commit = dual_git_repository
    first = discover_control_plane_experience(repo, repository_commit)
    repeated = discover_control_plane_experience(repo, repository_commit)
    second = discover_control_plane_experience(repo, control_commit)
    assert first == repeated
    assert first.snapshot != second.snapshot
    assert first.manifest_fingerprint != second.manifest_fingerprint


def test_control_git_boundary_is_local_bounded_and_has_no_network_fallback(
    dual_git_repository: tuple[Path, str, str],
):
    repo, _, control_commit = dual_git_repository
    discover_control_plane_experience(repo, control_commit)
    assert _git(repo, "remote").strip() == b""

    open_source = inspect.getsource(_open_control_git_process)
    tree_source = inspect.getsource(_run_control_git_tree)
    assert "shell=False" in open_source
    assert "stdout=subprocess.PIPE" in open_source
    assert "capture_output" not in tree_source
    assert "communicate(" not in tree_source
    implementation = Path("src/aios_engineering/harness/experience.py").read_text(encoding="utf-8")
    for forbidden in (
        "subprocess.run",
        "git fetch",
        "git pull",
        "git clone",
        "requests.",
        "httpx.",
        "openai",
        "anthropic",
        "aios_bridge",
        "TASK-076",
    ):
        assert forbidden not in implementation


def test_every_control_git_process_uses_closed_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setenv("GIT_NO_LAZY_FETCH", "0")
    monkeypatch.setenv("AIOS_UNRELATED_CALLER_VALUE", "must-not-be-copied")
    provider_secrets = {
        "OPENAI_API_KEY": "openai-provider-secret",
        "ANTHROPIC_API_KEY": "anthropic-provider-secret",
        "GEMINI_API_KEY": "gemini-provider-secret",
        "AWS_SECRET_ACCESS_KEY": "aws-provider-secret",
    }
    caller_git_overrides = {
        "GIT_DIR": "caller-git-dir",
        "GIT_WORK_TREE": "caller-work-tree",
        "GIT_OBJECT_DIRECTORY": "caller-object-directory",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "caller-alternate-objects",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.repositoryformatversion",
        "GIT_CONFIG_VALUE_0": "999",
        "GIT_CONFIG_GLOBAL": "caller-global-config",
        "GIT_CONFIG_SYSTEM": "caller-system-config",
    }
    for name, value in {**provider_secrets, **caller_git_overrides}.items():
        monkeypatch.setenv(name, value)
    calls: list[tuple[list[str], dict[str, object]]] = []
    process_sentinel = object()

    def fake_popen(argv: list[str], **kwargs: object) -> object:
        calls.append((argv, kwargs))
        return process_sentinel

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    commands = (
        ("cat-file", "-t", SHA_A),
        ("rev-parse", "--verify", f"{SHA_A}^{{tree}}"),
        ("ls-tree", "-r", "-z", "--full-tree", SHA_A, "--"),
    )
    for command in commands:
        assert _open_control_git_process(tmp_path, command) is process_sentinel

    assert len(calls) == len(commands)
    for argv, kwargs in calls:
        assert argv[:2] == ["git", "--no-replace-objects"]
        assert kwargs["shell"] is False
        child_environment = kwargs["env"]
        assert isinstance(child_environment, dict)
        assert child_environment["GIT_NO_LAZY_FETCH"] == "1"
        assert "AIOS_UNRELATED_CALLER_VALUE" not in child_environment
        assert set(child_environment).isdisjoint(provider_secrets)
        assert set(child_environment.values()).isdisjoint(provider_secrets.values())
        assert set(child_environment).isdisjoint(caller_git_overrides)
        assert {name for name in child_environment if name.startswith("GIT_")} == {
            "GIT_NO_LAZY_FETCH"
        }


def test_dual_manifest_includes_repository_and_control_experience(
    dual_git_repository: tuple[Path, str, str],
):
    repo, repository_commit, control_commit = dual_git_repository
    repository_discovery, _ = discover_repository_snapshot(
        repo,
        repository_commit,
        task_id="TASK-078",
    )
    control_manifest = discover_control_plane_experience(repo, control_commit)
    manifest = build_repository_experience_manifest(repository_discovery, control_manifest)
    identities = {(item.surface, item.path, item.artifact_kind) for item in manifest.evidence}

    assert (
        ExperienceSurface.REPOSITORY,
        ".ai/results/shared.md",
        ExperienceArtifactKind.RESULT,
    ) in identities
    assert (
        ExperienceSurface.REPOSITORY,
        ".ai/learning/repository-lesson.md",
        ExperienceArtifactKind.LEARNING,
    ) in identities
    assert all(
        not (
            item.surface is ExperienceSurface.REPOSITORY
            and item.path == ".ai/tasks/repository-task.md"
        )
        for item in manifest.evidence
    )
    assert any(item.surface is ExperienceSurface.CONTROL_PLANE for item in manifest.evidence)
    shared = [item for item in manifest.evidence if item.path == ".ai/results/shared.md"]
    assert {item.surface for item in shared} == {
        ExperienceSurface.REPOSITORY,
        ExperienceSurface.CONTROL_PLANE,
    }
    assert manifest.repository_snapshot == repository_discovery.snapshot
    assert manifest.repository_discovery_fingerprint == repository_discovery.discovery_fingerprint
    assert (
        manifest.repository_candidate_set_fingerprint
        == repository_discovery.candidate_set_fingerprint
    )
    assert manifest.control_plane_snapshot == control_manifest.snapshot
    assert manifest.control_plane_manifest_fingerprint == control_manifest.manifest_fingerprint
    assert manifest.authority_created is False


def test_factories_are_canonical_order_permutation_invariant():
    evidence = (
        ExperienceArtifactRef(
            ExperienceSurface.CONTROL_PLANE,
            ".ai/reviews/R.md",
            SHA_A,
            ExperienceArtifactKind.REVIEW,
        ),
        ExperienceArtifactRef(
            ExperienceSurface.CONTROL_PLANE,
            ".ai/tasks/T.md",
            SHA_B,
            ExperienceArtifactKind.TASK,
        ),
    )
    first = ControlPlaneExperienceManifest.create(ControlPlaneSnapshotRef(SHA_C, TREE_A), evidence)
    second = ControlPlaneExperienceManifest.create(
        ControlPlaneSnapshotRef(SHA_C, TREE_A),
        tuple(reversed(evidence)),
    )
    assert first == second
    assert first.evidence == tuple(sorted(evidence, key=lambda item: (item.surface.value, item.path, item.blob_sha, item.artifact_kind.value)))


def test_manifest_contracts_reject_duplicates_and_non_tuples():
    item = ExperienceArtifactRef(
        ExperienceSurface.CONTROL_PLANE,
        ".ai/tasks/T.md",
        SHA_A,
        ExperienceArtifactKind.TASK,
    )
    with pytest.raises(HarnessValidationError, match="exact tuple"):
        ControlPlaneExperienceManifest.create(
            ControlPlaneSnapshotRef(SHA_C, TREE_A),
            [item],  # type: ignore[arg-type]
        )
    with pytest.raises(HarnessValidationError, match="duplicate or conflicting"):
        ControlPlaneExperienceManifest.create(
            ControlPlaneSnapshotRef(SHA_C, TREE_A),
            (item, item),
        )


def test_artifact_kind_tampering_is_rejected_by_explicit_path_identity():
    item = ExperienceArtifactRef(
        ExperienceSurface.CONTROL_PLANE,
        ".ai/tasks/T.md",
        SHA_A,
        ExperienceArtifactKind.TASK,
    )
    with pytest.raises(HarnessValidationError, match="explicit path identity"):
        dataclasses.replace(item, artifact_kind=ExperienceArtifactKind.REVIEW)


def test_control_and_dual_fingerprints_are_tamper_evident():
    control = _control_manifest()
    manifest = build_repository_experience_manifest(_repository_discovery(), control)
    with pytest.raises(HarnessFingerprintError, match="Control-plane manifest"):
        dataclasses.replace(control, manifest_fingerprint="0" * 64)
    with pytest.raises(HarnessFingerprintError, match="Combined experience"):
        dataclasses.replace(manifest, combined_experience_fingerprint="0" * 64)
    with pytest.raises(HarnessFingerprintError, match="Repository experience manifest"):
        dataclasses.replace(manifest, manifest_fingerprint="0" * 64)


def test_dual_manifest_fingerprint_is_repository_commit_and_tree_sensitive():
    control = _control_manifest()
    baseline = build_repository_experience_manifest(_repository_discovery(), control)
    commit_changed = build_repository_experience_manifest(
        _repository_discovery(commit=SHA_B),
        control,
    )
    tree_changed = build_repository_experience_manifest(
        _repository_discovery(tree=TREE_B),
        control,
    )
    assert len(
        {
            baseline.combined_experience_fingerprint,
            commit_changed.combined_experience_fingerprint,
            tree_changed.combined_experience_fingerprint,
        }
    ) == 3


def test_dual_manifest_fingerprint_is_repository_discovery_sensitive():
    control = _control_manifest()
    baseline_discovery = _repository_discovery()
    exclusion = RepositoryDiscoveryExclusion(
        path="link",
        object_sha=SHA_D,
        git_mode="120000",
        object_type="blob",
        reason_code=NON_REGULAR_GIT_MODE,
    )
    changed_discovery = _repository_discovery(exclusions=(exclusion,))
    assert (
        baseline_discovery.candidate_set_fingerprint
        == changed_discovery.candidate_set_fingerprint
    )
    baseline = build_repository_experience_manifest(baseline_discovery, control)
    changed = build_repository_experience_manifest(changed_discovery, control)
    assert baseline.repository_discovery_fingerprint != changed.repository_discovery_fingerprint
    assert baseline.combined_experience_fingerprint != changed.combined_experience_fingerprint


def test_dual_manifest_fingerprint_is_control_commit_tree_and_blob_sensitive():
    repository = _repository_discovery()
    baseline = build_repository_experience_manifest(repository, _control_manifest())
    commit_changed = build_repository_experience_manifest(
        repository,
        _control_manifest(commit=SHA_D),
    )
    tree_changed = build_repository_experience_manifest(
        repository,
        _control_manifest(tree=TREE_A),
    )
    blob_changed = build_repository_experience_manifest(
        repository,
        _control_manifest(
            evidence=(
                ExperienceArtifactRef(
                    ExperienceSurface.CONTROL_PLANE,
                    ".ai/tasks/TASK-X.md",
                    SHA_D,
                    ExperienceArtifactKind.TASK,
                ),
            )
        ),
    )
    assert len(
        {
            baseline.combined_experience_fingerprint,
            commit_changed.combined_experience_fingerprint,
            tree_changed.combined_experience_fingerprint,
            blob_changed.combined_experience_fingerprint,
        }
    ) == 4


def test_same_result_path_on_different_surfaces_has_distinct_identity():
    repository = _repository_discovery(
        evidence=(_repository_evidence(".ai/results/shared.md", SHA_A),)
    )
    control = _control_manifest(
        evidence=(
            ExperienceArtifactRef(
                ExperienceSurface.CONTROL_PLANE,
                ".ai/results/shared.md",
                SHA_A,
                ExperienceArtifactKind.RESULT,
            ),
        )
    )
    manifest = build_repository_experience_manifest(repository, control)
    assert len(manifest.evidence) == 2
    assert manifest.evidence[0].surface is ExperienceSurface.CONTROL_PLANE
    assert manifest.evidence[1].surface is ExperienceSurface.REPOSITORY
    assert manifest.evidence[0].to_dict() != manifest.evidence[1].to_dict()


def test_public_manifest_records_are_frozen():
    snapshot = ControlPlaneSnapshotRef(SHA_C, TREE_A)
    artifact = ExperienceArtifactRef(
        ExperienceSurface.CONTROL_PLANE,
        ".ai/tasks/T.md",
        SHA_A,
        ExperienceArtifactKind.TASK,
    )
    control = ControlPlaneExperienceManifest.create(snapshot, (artifact,))
    manifest = build_repository_experience_manifest(_repository_discovery(), control)
    for record, field, value in (
        (snapshot, "control_commit_sha", SHA_D),
        (artifact, "blob_sha", SHA_D),
        (control, "manifest_fingerprint", "0" * 64),
        (manifest, "authority_created", True),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(record, field, value)


def test_experience_public_api_exports_stable_contracts_only():
    import src.aios_engineering.harness as harness

    for name in (
        "ControlPlaneExperienceManifest",
        "ControlPlaneSnapshotRef",
        "ExperienceArtifactKind",
        "ExperienceArtifactRef",
        "ExperienceSurface",
        "RepositoryExperienceManifest",
        "build_repository_experience_manifest",
        "classify_experience_artifact",
        "discover_control_plane_experience",
    ):
        assert name in harness.__all__
        assert getattr(harness, name) is not None
    assert "_open_control_git_process" not in harness.__all__
    assert "_run_control_git_tree" not in harness.__all__
    assert MAX_EXPERIENCE_EVIDENCE_COUNT > 0


def test_existing_h1_discovery_remains_unchanged_and_usable(
    dual_git_repository: tuple[Path, str, str],
):
    repo, repository_commit, _ = dual_git_repository
    result, receipt = discover_repository_snapshot(
        repo,
        repository_commit,
        task_id="TASK-078",
    )
    assert result.snapshot.repository_commit_sha == repository_commit
    assert receipt.authority_created is False
    assert receipt.network_used is False
    assert receipt.llm_used is False
    assert receipt.paid_api_used is False
