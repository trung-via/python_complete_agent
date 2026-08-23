"""Tests for bounded H1 repository snapshot discovery and provenance."""
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
    DISCOVERED_GIT_BLOB,
    H1_DISCOVERY_POLICY_VERSION,
    NON_REGULAR_GIT_MODE,
    UNSUPPORTED_GIT_OBJECT_TYPE,
    RepositoryDiscoveryExclusion,
    RepositoryDiscoveryResult,
    _GitTreeEntry,
    _convert_tree_entries,
    _open_git_process,
    _parse_git_tree_record,
    _read_git_tree_stream,
    _run_git_tree,
    classify_evidence_kind,
    discover_repository_snapshot,
)
from src.aios_engineering.harness.errors import (
    HarnessFingerprintError,
    HarnessValidationError,
    RepositoryDiscoveryBoundError,
    RepositoryDiscoveryGitError,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
TREE_A = "c" * 40


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
def local_git_repository(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repository"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "h1-tests@example.invalid")
    _git(repo, "config", "user.name", "H1 Tests")

    tracked_files = {
        ".ai/decisions/ADR-X.md": b"contract\n",
        "README.md": b"readme\n",
        "assets/sample.bin": b"\x00\x01\x02",
        "docs/guide.md": b"guide\n",
        "pyproject.toml": b"[build-system]\n",
        "requirements.txt": b"pytest\n",
        "scripts/tool.ps1": b"Write-Output 'tool'\n",
        "src/pkg/module.py": b"VALUE = 'snapshot'\n",
        "tests/test_x.py": b"def test_x(): pass\n",
    }
    for relative_path, content in tracked_files.items():
        _write(repo, relative_path, content)
    _git(repo, "add", "-A")
    _git(repo, "update-index", "--chmod=+x", "scripts/tool.ps1")
    _git(repo, "commit", "-q", "-m", "regular blobs")
    base_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()

    link_blob = _git(repo, "hash-object", "-w", "--stdin", input_bytes=b"src/pkg/module.py").decode(
        "ascii"
    ).strip()
    _git(repo, "update-index", "--add", "--cacheinfo", f"120000,{link_blob},module-link")
    _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{base_commit},vendor/submodule")
    _git(repo, "commit", "-q", "-m", "non-regular entries")
    snapshot_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()

    # These mutable worktree bytes must never become snapshot provenance.
    _write(repo, "src/pkg/module.py", b"VALUE = 'dirty worktree'\n")
    _write(repo, "untracked.py", b"UNTRACKED = True\n")
    return repo, snapshot_commit


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".ai/decisions/ADR-X.md", EvidenceKind.CONTRACT),
        ("tests/test_x.py", EvidenceKind.TEST),
        ("docs/guide.md", EvidenceKind.DOCUMENTATION),
        ("README.md", EvidenceKind.DOCUMENTATION),
        ("pyproject.toml", EvidenceKind.CONFIGURATION),
        ("requirements.txt", EvidenceKind.CONFIGURATION),
        ("src/pkg/module.py", EvidenceKind.SOURCE),
        ("scripts/tool.ps1", EvidenceKind.SOURCE),
        ("assets/sample.bin", EvidenceKind.OTHER),
    ],
)
def test_classifier_required_cases(path: str, expected: EvidenceKind):
    assert classify_evidence_kind(path) is expected


def test_classifier_precedence_is_contract_then_test_then_docs_then_config_then_source():
    assert classify_evidence_kind(".ai/tasks/test_contract.md") is EvidenceKind.CONTRACT
    assert classify_evidence_kind("tests/docs/pyproject.toml") is EvidenceKind.TEST
    assert classify_evidence_kind("docs/config/example.py") is EvidenceKind.DOCUMENTATION
    assert classify_evidence_kind("config/runtime.py") is EvidenceKind.CONFIGURATION
    assert classify_evidence_kind("src/assets/sample.bin") is EvidenceKind.SOURCE


@pytest.mark.parametrize(
    "record",
    [
        b"",
        b"100644 blob " + SHA_A.encode("ascii"),
        b"10064 blob " + SHA_A.encode("ascii") + b"\tfile.py",
        b"100644  blob " + SHA_A.encode("ascii") + b"\tfile.py",
        b"100644 BLOB " + SHA_A.encode("ascii") + b"\tfile.py",
        b"100644 blob short\tfile.py",
        b"100644 blob " + SHA_A.encode("ascii") + b"\t\xff.py",
    ],
)
def test_malformed_git_record_fails_closed(record: bytes):
    with pytest.raises(HarnessValidationError):
        _parse_git_tree_record(record)


@pytest.mark.parametrize(
    "path",
    [
        b"/absolute.py",
        b"../escape.py",
        b"src/../escape.py",
        b"src\\windows.py",
        b".git/config",
        b"src/control\n.py",
    ],
)
def test_invalid_git_path_fails_closed_without_normalization(path: bytes):
    record = b"100644 blob " + SHA_A.encode("ascii") + b"\t" + path
    with pytest.raises(HarnessValidationError):
        _parse_git_tree_record(record)


def _record(path: str = "src/a.py", *, mode: str = "100644", object_type: str = "blob") -> bytes:
    return f"{mode} {object_type} {SHA_A}\t{path}".encode("ascii")


def test_stream_entry_bound_fails_closed():
    stream = io.BytesIO(_record("a.py") + b"\0" + _record("b.py") + b"\0")
    with pytest.raises(RepositoryDiscoveryBoundError, match="entry count"):
        _read_git_tree_stream(stream, max_entries=1)


def test_stream_byte_bound_fails_closed_while_reading():
    framed_record = _record() + b"\0"
    with pytest.raises(RepositoryDiscoveryBoundError, match="stream bytes"):
        _read_git_tree_stream(io.BytesIO(framed_record), max_stream_bytes=len(framed_record) - 1)


def test_record_byte_bound_fails_closed_while_parsing():
    record = _record()
    with pytest.raises(RepositoryDiscoveryBoundError, match="record bytes"):
        _read_git_tree_stream(io.BytesIO(record + b"\0"), max_record_bytes=len(record) - 1)


def test_stream_requires_nul_termination_and_uses_bounded_reads():
    class RecordingStream(io.BytesIO):
        def __init__(self, initial_bytes: bytes) -> None:
            super().__init__(initial_bytes)
            self.read_sizes: list[int] = []

        def read(self, size: int = -1) -> bytes:
            self.read_sizes.append(size)
            return super().read(size)

    stream = RecordingStream(_record() + b"\0")
    assert len(_read_git_tree_stream(stream)) == 1
    assert stream.read_sizes
    assert all(0 < size <= 64 * 1024 * 1024 + 1 for size in stream.read_sizes)
    with pytest.raises(HarnessValidationError, match="unterminated"):
        _read_git_tree_stream(io.BytesIO(_record()))


def test_non_regular_and_unexpected_object_types_are_exclusions_only():
    entries = (
        _GitTreeEntry("link", SHA_A, "120000", "blob"),
        _GitTreeEntry("vendor/sub", SHA_B, "160000", "commit"),
        _GitTreeEntry("odd", SHA_A, "100644", "tree"),
    )
    evidence, exclusions = _convert_tree_entries(entries)
    assert evidence == ()
    assert [item.reason_code for item in exclusions] == [
        NON_REGULAR_GIT_MODE,
        NON_REGULAR_GIT_MODE,
        UNSUPPORTED_GIT_OBJECT_TYPE,
    ]


def _sample_evidence(path: str = "src/a.py", blob_sha: str = SHA_A) -> RepositoryEvidenceRef:
    return RepositoryEvidenceRef(
        path=path,
        blob_sha=blob_sha,
        evidence_kind=EvidenceKind.SOURCE,
        reason_code=DISCOVERED_GIT_BLOB,
        priority=0,
        symbol_locator=None,
    )


def _sample_exclusion(
    path: str = "link", object_sha: str = SHA_A
) -> RepositoryDiscoveryExclusion:
    return RepositoryDiscoveryExclusion(
        path=path,
        object_sha=object_sha,
        git_mode="120000",
        object_type="blob",
        reason_code=NON_REGULAR_GIT_MODE,
    )


def test_result_contract_uses_exact_tuples_canonical_order_and_rejects_duplicates():
    snapshot = RepositorySnapshotRef(SHA_A, TREE_A)
    result = RepositoryDiscoveryResult.create(
        snapshot,
        (_sample_evidence("src/b.py", SHA_B), _sample_evidence("src/a.py", SHA_A)),
        (_sample_exclusion("z-link", SHA_B), _sample_exclusion("a-link", SHA_A)),
    )
    assert type(result.evidence) is tuple
    assert type(result.exclusions) is tuple
    assert [item.path for item in result.evidence] == ["src/a.py", "src/b.py"]
    assert [item.path for item in result.exclusions] == ["a-link", "z-link"]
    with pytest.raises(HarnessValidationError, match="duplicate or ambiguous"):
        RepositoryDiscoveryResult.create(snapshot, (_sample_evidence(), _sample_evidence()))
    with pytest.raises(HarnessValidationError, match="exact tuple"):
        dataclasses.replace(result, evidence=list(result.evidence))  # type: ignore[arg-type]


@pytest.mark.parametrize("iterable_kind", ["list", "generator", "reversed", "string"])
def test_result_factory_rejects_non_tuple_evidence(iterable_kind: str):
    snapshot = RepositorySnapshotRef(SHA_A, TREE_A)
    evidence = (_sample_evidence(),)
    invalid_evidence = {
        "list": list(evidence),
        "generator": (item for item in evidence),
        "reversed": reversed(evidence),
        "string": "src/a.py",
    }[iterable_kind]
    with pytest.raises(HarnessValidationError, match="evidence must be an exact tuple"):
        RepositoryDiscoveryResult.create(snapshot, invalid_evidence)  # type: ignore[arg-type]


@pytest.mark.parametrize("iterable_kind", ["list", "generator", "reversed", "string"])
def test_result_factory_rejects_non_tuple_exclusions(iterable_kind: str):
    snapshot = RepositorySnapshotRef(SHA_A, TREE_A)
    exclusions = (_sample_exclusion(),)
    invalid_exclusions = {
        "list": list(exclusions),
        "generator": (item for item in exclusions),
        "reversed": reversed(exclusions),
        "string": "link",
    }[iterable_kind]
    with pytest.raises(HarnessValidationError, match="exclusions must be an exact tuple"):
        RepositoryDiscoveryResult.create(snapshot, (), invalid_exclusions)  # type: ignore[arg-type]


def test_result_fingerprints_are_deterministic_and_tamper_evident():
    snapshot = RepositorySnapshotRef(SHA_A, TREE_A)
    evidence = (_sample_evidence("src/b.py", SHA_B), _sample_evidence("src/a.py", SHA_A))
    first = RepositoryDiscoveryResult.create(snapshot, evidence)
    second = RepositoryDiscoveryResult.create(snapshot, tuple(reversed(evidence)))
    assert first.candidate_set_fingerprint == second.candidate_set_fingerprint
    assert first.discovery_fingerprint == second.discovery_fingerprint
    with pytest.raises(HarnessFingerprintError, match="Candidate set fingerprint mismatch"):
        dataclasses.replace(first, candidate_set_fingerprint="0" * 64)
    with pytest.raises(HarnessFingerprintError, match="Discovery fingerprint mismatch"):
        dataclasses.replace(first, discovery_fingerprint="0" * 64)


def test_discovery_binds_exact_snapshot_objects_and_ignores_worktree(local_git_repository):
    repo, commit_sha = local_git_repository
    result, receipt = discover_repository_snapshot(repo, commit_sha, task_id="TASK-070")
    expected_tree = _git(repo, "rev-parse", f"{commit_sha}^{{tree}}").decode("ascii").strip()
    expected_blob = _git(repo, "rev-parse", f"{commit_sha}:src/pkg/module.py").decode("ascii").strip()
    evidence_by_path = {item.path: item for item in result.evidence}

    assert result.snapshot.repository_commit_sha == commit_sha
    assert result.snapshot.repository_tree_sha == expected_tree
    assert evidence_by_path["src/pkg/module.py"].blob_sha == expected_blob
    assert "untracked.py" not in evidence_by_path
    assert [item.path for item in result.evidence] == sorted(evidence_by_path)
    assert type(result.evidence) is tuple
    assert type(result.exclusions) is tuple
    assert all(item.priority == 0 for item in result.evidence)
    assert all(item.symbol_locator is None for item in result.evidence)
    assert all(item.reason_code == DISCOVERED_GIT_BLOB for item in result.evidence)

    executable_mode = _git(repo, "ls-tree", commit_sha, "--", "scripts/tool.ps1").split()[0]
    assert executable_mode == b"100755"
    assert evidence_by_path["scripts/tool.ps1"].blob_sha
    assert {item.path: item.reason_code for item in result.exclusions} == {
        "module-link": NON_REGULAR_GIT_MODE,
        "vendor/submodule": NON_REGULAR_GIT_MODE,
    }

    assert receipt.repository_commit_sha == commit_sha
    assert receipt.generator_version == H1_DISCOVERY_POLICY_VERSION
    assert receipt.candidate_count == len(result.evidence) + len(result.exclusions)
    assert receipt.selected_count == len(result.evidence)
    assert receipt.excluded_count == len(result.exclusions)
    assert receipt.authority_created is False
    assert receipt.network_used is False
    assert receipt.llm_used is False
    assert receipt.paid_api_used is False


def test_discovery_classification_matches_locked_precedence(local_git_repository):
    repo, commit_sha = local_git_repository
    result, _ = discover_repository_snapshot(repo, commit_sha, task_id="TASK-070")
    kinds = {item.path: item.evidence_kind for item in result.evidence}
    assert kinds[".ai/decisions/ADR-X.md"] is EvidenceKind.CONTRACT
    assert kinds["tests/test_x.py"] is EvidenceKind.TEST
    assert kinds["docs/guide.md"] is EvidenceKind.DOCUMENTATION
    assert kinds["README.md"] is EvidenceKind.DOCUMENTATION
    assert kinds["pyproject.toml"] is EvidenceKind.CONFIGURATION
    assert kinds["requirements.txt"] is EvidenceKind.CONFIGURATION
    assert kinds["src/pkg/module.py"] is EvidenceKind.SOURCE
    assert kinds["scripts/tool.ps1"] is EvidenceKind.SOURCE
    assert kinds["assets/sample.bin"] is EvidenceKind.OTHER


@pytest.mark.parametrize(
    "invalid_identity",
    [
        "HEAD",
        "main",
        "a" * 12,
        "A" * 40,
        "a" * 39,
        "a" * 41,
        "g" * 40,
        "a" * 40 + "^",
    ],
)
def test_exact_lowercase_commit_sha_is_required(local_git_repository, invalid_identity: str):
    repo, _ = local_git_repository
    with pytest.raises(HarnessValidationError, match="exact lowercase 40-hex"):
        discover_repository_snapshot(repo, invalid_identity, task_id="TASK-070")


def test_exact_non_commit_object_is_rejected(local_git_repository):
    repo, _ = local_git_repository
    blob_sha = _git(repo, "hash-object", "README.md").decode("ascii").strip()
    with pytest.raises(RepositoryDiscoveryGitError, match="not a commit"):
        discover_repository_snapshot(repo, blob_sha, task_id="TASK-070")


def test_discovery_and_receipt_fingerprints_are_deterministic_and_snapshot_sensitive(
    local_git_repository,
):
    repo, first_commit = local_git_repository
    first, first_receipt = discover_repository_snapshot(repo, first_commit, task_id="TASK-070")
    repeated, repeated_receipt = discover_repository_snapshot(repo, first_commit, task_id="TASK-070")
    assert first == repeated
    assert first_receipt == repeated_receipt

    _write(repo, "src/new.py", b"NEW = True\n")
    _git(repo, "add", "src/new.py")
    _git(repo, "commit", "-q", "-m", "new snapshot")
    second_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    second, _ = discover_repository_snapshot(repo, second_commit, task_id="TASK-070")
    assert first.snapshot != second.snapshot
    assert first.candidate_set_fingerprint != second.candidate_set_fingerprint
    assert first.discovery_fingerprint != second.discovery_fingerprint


def test_discovery_uses_explicit_local_git_argv_and_no_unbounded_capture(local_git_repository):
    repo, commit_sha = local_git_repository
    discover_repository_snapshot(repo, commit_sha, task_id="TASK-070")
    assert _git(repo, "remote").strip() == b""

    open_source = inspect.getsource(_open_git_process)
    tree_source = inspect.getsource(_run_git_tree)
    assert "shell=False" in open_source
    assert "stdout=subprocess.PIPE" in open_source
    assert "capture_output" not in tree_source
    assert "communicate(" not in tree_source
    implementation = Path("src/aios_engineering/harness/discovery.py").read_text(encoding="utf-8")
    assert "subprocess.run" not in implementation
    assert "git fetch" not in implementation
    assert "git pull" not in implementation
    assert "git clone" not in implementation


def test_every_git_process_forces_no_lazy_fetch_even_if_caller_enables_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("GIT_NO_LAZY_FETCH", "0")
    calls: list[tuple[list[str], dict[str, object]]] = []
    process_sentinel = object()

    def fake_popen(argv: list[str], **kwargs: object) -> object:
        calls.append((argv, kwargs))
        return process_sentinel

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    commands = (
        ("cat-file", "-t", SHA_A),
        ("rev-parse", f"{SHA_A}^{{tree}}"),
        ("ls-tree", "-r", "-z", "--full-tree", SHA_A, "--"),
    )

    for command in commands:
        assert _open_git_process(tmp_path, command) is process_sentinel

    assert len(calls) == len(commands)
    for argv, kwargs in calls:
        assert argv[:2] == ["git", "--no-replace-objects"]
        assert kwargs["shell"] is False
        child_environment = kwargs["env"]
        assert isinstance(child_environment, dict)
        assert child_environment["GIT_NO_LAZY_FETCH"] == "1"


def test_discovery_records_are_frozen():
    exclusion = RepositoryDiscoveryExclusion(
        path="link",
        object_sha=SHA_A,
        git_mode="120000",
        object_type="blob",
        reason_code=NON_REGULAR_GIT_MODE,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        exclusion.path = "changed"  # type: ignore[misc]
