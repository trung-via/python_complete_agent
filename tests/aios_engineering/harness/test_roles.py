from __future__ import annotations

import dataclasses
from pathlib import Path
import subprocess

import pytest

from src.aios_engineering.harness import (
    ArtifactRole,
    ContentAnalysisStatus,
    EvidenceKind,
    H3_ROLE_POLICY_VERSION,
    HarnessFingerprintError,
    HarnessValidationError,
    MAX_H3_BLOB_BYTES,
    MAX_H3_SYMBOLS_PER_FILE,
    MAX_H3_TOTAL_BODY_BYTES,
    PythonSymbolKind,
    RepositoryDiscoveryResult,
    RepositoryEvidenceRef,
    RepositoryRoleSummaryGitError,
    RepositoryRoleSummaryResult,
    RepositorySnapshotRef,
    TaskRelevanceSpec,
    discover_repository_snapshot,
    rank_repository_evidence,
    summarize_repository_roles,
)
from src.aios_engineering.harness import roles as roles_module


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _make_repository(tmp_path: Path, files: dict[str, bytes]) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "H3 Tests")
    _git(repository, "config", "user.email", "h3-tests@example.invalid")
    for relative_path, body in files.items():
        target = repository / Path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    _git(repository, "add", "--all")
    _git(repository, "commit", "-q", "-m", "snapshot")
    return repository


def _snapshot(repository: Path) -> RepositorySnapshotRef:
    commit_sha = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    tree_sha = _git(repository, "rev-parse", "HEAD^{tree}").decode("ascii").strip()
    return RepositorySnapshotRef(commit_sha, tree_sha)


def _ranking(repository: Path, *, max_selected: int | None = None):
    snapshot = _snapshot(repository)
    discovery, _ = discover_repository_snapshot(
        repository,
        snapshot.repository_commit_sha,
        task_id="TASK-075",
    )
    selected_limit = len(discovery.evidence) if max_selected is None else max_selected
    spec = TaskRelevanceSpec(
        task_id="TASK-075",
        preferred_kinds=tuple(EvidenceKind),
        max_selected=selected_limit,
    )
    ranking, _ = rank_repository_evidence(discovery, spec)
    return ranking


def _single_source_repository(tmp_path: Path, body: bytes = b"def selected():\n    pass\n"):
    repository = _make_repository(tmp_path, {"src/selected.py": body})
    return repository, _ranking(repository)


def test_roles_follow_locked_precedence_and_all_selected_items_are_accounted(tmp_path: Path):
    repository = _make_repository(
        tmp_path,
        {
            ".ai/tasks/TASK-X.md": b"contract\n",
            "tests/test_sample.py": b"def test_sample():\n    pass\n",
            "docs/guide.md": b"guide\n",
            "pyproject.toml": b"[build-system]\n",
            "src/pkg/__init__.py": b"def exported():\n    pass\n",
            "src/main.py": b"pass\n",
            "src/guarded.py": b'if __name__ == "__main__":\n    pass\n',
            "src/implementation.py": b"VALUE = 1\n",
            "assets/data.bin": b"data\n",
        },
    )
    ranking = _ranking(repository)
    before = ranking.to_dict()

    result, receipt = summarize_repository_roles(repository, ranking)

    assert [summary.path for summary in result.summaries] == [
        evidence.path for evidence in ranking.plan.selected_evidence
    ]
    assert [summary.h2_priority for summary in result.summaries] == [
        evidence.priority for evidence in ranking.plan.selected_evidence
    ]
    assert ranking.to_dict() == before
    roles_by_path = {summary.path: summary.artifact_role for summary in result.summaries}
    assert roles_by_path == {
        ".ai/tasks/TASK-X.md": ArtifactRole.CONTRACT_ARTIFACT,
        "assets/data.bin": ArtifactRole.OTHER_ARTIFACT,
        "docs/guide.md": ArtifactRole.DOCUMENTATION_ARTIFACT,
        "pyproject.toml": ArtifactRole.CONFIGURATION_ARTIFACT,
        "src/guarded.py": ArtifactRole.EXECUTABLE_ENTRYPOINT,
        "src/implementation.py": ArtifactRole.SOURCE_IMPLEMENTATION,
        "src/main.py": ArtifactRole.EXECUTABLE_ENTRYPOINT,
        "src/pkg/__init__.py": ArtifactRole.PACKAGE_EXPORT_SURFACE,
        "tests/test_sample.py": ArtifactRole.TEST_ARTIFACT,
    }
    assert receipt.candidate_count == len(ranking.plan.selected_evidence)
    assert receipt.selected_count == len(result.summaries)
    assert receipt.excluded_count == 0


def test_top_level_symbols_are_extracted_in_source_order_without_import_or_execution(
    tmp_path: Path,
):
    extra_functions = "".join(
        f"def extra_{index}():\n    pass\n" for index in range(130)
    )
    source = (
        "import module_that_must_not_be_imported\n"
        "raise RuntimeError('module body must not execute')\n"
        "class TopLevel:\n"
        "    def method(self):\n"
        "        pass\n"
        "def outer():\n"
        "    def nested():\n"
        "        pass\n"
        "async def coroutine():\n"
        "    pass\n"
        + extra_functions
    ).encode("utf-8")
    repository, ranking = _single_source_repository(tmp_path, source)

    result, _ = summarize_repository_roles(repository, ranking)

    summary = result.summaries[0]
    assert summary.analysis_status is ContentAnalysisStatus.PARSED
    assert len(summary.symbols) == MAX_H3_SYMBOLS_PER_FILE
    assert [(symbol.kind, symbol.name) for symbol in summary.symbols[:3]] == [
        (PythonSymbolKind.CLASS, "TopLevel"),
        (PythonSymbolKind.FUNCTION, "outer"),
        (PythonSymbolKind.ASYNC_FUNCTION, "coroutine"),
    ]
    assert "nested" not in {symbol.name for symbol in summary.symbols}
    assert "method" not in {symbol.name for symbol in summary.symbols}
    assert [symbol.line_number for symbol in summary.symbols] == sorted(
        symbol.line_number for symbol in summary.symbols
    )
    assert all(len(symbol.name) <= 128 for symbol in summary.symbols)


def test_non_python_and_rejected_python_statuses_are_exact(tmp_path: Path):
    repository = _make_repository(
        tmp_path,
        {
            "docs/readme.md": b"not Python\n",
            "src/bad_encoding.py": b"def valid_name():\n    return \xff\n",
            "src/bad_syntax.py": b"def broken(:\n    pass\n",
        },
    )
    result, _ = summarize_repository_roles(repository, _ranking(repository))
    summaries = {summary.path: summary for summary in result.summaries}

    assert summaries["docs/readme.md"].analysis_status is ContentAnalysisStatus.NOT_PYTHON
    assert summaries["src/bad_encoding.py"].analysis_status is ContentAnalysisStatus.DECODE_REJECTED
    assert summaries["src/bad_syntax.py"].analysis_status is ContentAnalysisStatus.SYNTAX_REJECTED
    assert all(not summary.symbols for summary in summaries.values())


def test_per_blob_bound_is_checked_before_body_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    oversized = b"def must_not_be_partially_parsed():\n    pass\n" + b"#" * MAX_H3_BLOB_BYTES
    repository, ranking = _single_source_repository(tmp_path, oversized)

    def forbidden_body_read(*args: object, **kwargs: object) -> bytes:
        raise AssertionError("oversized body must not be read")

    monkeypatch.setattr(roles_module, "_read_blob_body", forbidden_body_read)
    result, _ = summarize_repository_roles(repository, ranking)

    summary = result.summaries[0]
    assert summary.blob_size_bytes > MAX_H3_BLOB_BYTES
    assert summary.analysis_status is ContentAnalysisStatus.CONTENT_BOUND_EXCEEDED
    assert summary.symbols == ()


def test_aggregate_body_bound_is_exact_and_never_partially_parses(tmp_path: Path):
    bounded_body = b"#" + b"x" * (MAX_H3_BLOB_BYTES - 2) + b"\n"
    repository = _make_repository(
        tmp_path,
        {f"src/file_{index:02d}.py": bounded_body for index in range(17)},
    )

    result, _ = summarize_repository_roles(repository, _ranking(repository))

    assert MAX_H3_TOTAL_BODY_BYTES == MAX_H3_BLOB_BYTES * 16
    assert all(
        summary.analysis_status is ContentAnalysisStatus.PARSED
        for summary in result.summaries[:16]
    )
    assert result.summaries[16].analysis_status is ContentAnalysisStatus.CONTENT_BOUND_EXCEEDED
    assert result.summaries[16].symbols == ()


def test_only_selected_python_blob_bodies_are_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repository = _make_repository(
        tmp_path,
        {
            "src/a.py": b"def selected_by_tie_break():\n    pass\n",
            "src/b.py": b"def unselected():\n    pass\n",
            "zz/readme.md": b"non-Python body is unnecessary\n",
        },
    )
    ranking = _ranking(repository, max_selected=1)
    body_reads: list[str] = []
    original_read = roles_module._read_blob_body

    def recording_read(root: Path, blob_sha: str, size: int) -> bytes:
        body_reads.append(blob_sha)
        return original_read(root, blob_sha, size)

    monkeypatch.setattr(roles_module, "_read_blob_body", recording_read)
    result, _ = summarize_repository_roles(repository, ranking)

    assert len(result.summaries) == 1
    assert body_reads == [ranking.plan.selected_evidence[0].blob_sha]


def test_dirty_worktree_and_worktree_read_helpers_do_not_affect_snapshot_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repository, ranking = _single_source_repository(tmp_path)
    first, first_receipt = summarize_repository_roles(repository, ranking)
    (repository / "src/selected.py").write_bytes(b"this is dirty and invalid Python\n")
    (repository / "src/untracked.py").write_bytes(b"raise RuntimeError\n")

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("mutable worktree content read attempted")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    second, second_receipt = summarize_repository_roles(repository, ranking)

    assert second == first
    assert second_receipt == first_receipt


def test_exact_commit_tree_binding_fails_closed(tmp_path: Path):
    repository, original_ranking = _single_source_repository(tmp_path)
    original_snapshot = original_ranking.plan.snapshot
    (repository / "src/second.py").write_bytes(b"pass\n")
    _git(repository, "add", "--all")
    _git(repository, "commit", "-q", "-m", "second snapshot")
    second_tree = _snapshot(repository).repository_tree_sha
    mismatched_snapshot = RepositorySnapshotRef(
        original_snapshot.repository_commit_sha,
        second_tree,
    )
    discovery = RepositoryDiscoveryResult.create(
        mismatched_snapshot,
        (
            RepositoryEvidenceRef(
                path=original_ranking.plan.selected_evidence[0].path,
                blob_sha=original_ranking.plan.selected_evidence[0].blob_sha,
                evidence_kind=EvidenceKind.SOURCE,
                reason_code="DISCOVERED_GIT_BLOB",
                priority=0,
            ),
        ),
    )
    ranking, _ = rank_repository_evidence(
        discovery,
        TaskRelevanceSpec(task_id="TASK-075", preferred_kinds=(EvidenceKind.SOURCE,)),
    )

    with pytest.raises(RepositoryRoleSummaryGitError, match="tree"):
        summarize_repository_roles(repository, ranking)


def test_exact_selected_object_must_be_a_blob(tmp_path: Path):
    repository, _ = _single_source_repository(tmp_path)
    snapshot = _snapshot(repository)
    discovery = RepositoryDiscoveryResult.create(
        snapshot,
        (
            RepositoryEvidenceRef(
                path="src/not_a_blob.py",
                blob_sha=snapshot.repository_commit_sha,
                evidence_kind=EvidenceKind.SOURCE,
                reason_code="DISCOVERED_GIT_BLOB",
                priority=0,
            ),
        ),
    )
    ranking, _ = rank_repository_evidence(
        discovery,
        TaskRelevanceSpec(task_id="TASK-075", preferred_kinds=(EvidenceKind.SOURCE,)),
    )

    with pytest.raises(RepositoryRoleSummaryGitError, match="not a blob"):
        summarize_repository_roles(repository, ranking)


def test_fingerprints_are_deterministic_bind_h2_and_snapshot(tmp_path: Path):
    repository, ranking = _single_source_repository(tmp_path)
    first, first_receipt = summarize_repository_roles(repository, ranking)
    second, second_receipt = summarize_repository_roles(repository, ranking)

    assert first == second
    assert first_receipt == second_receipt
    assert first.policy_version == H3_ROLE_POLICY_VERSION
    assert first.ranking_fingerprint == ranking.ranking_fingerprint
    assert first.h2_plan_fingerprint == ranking.plan.plan_fingerprint
    assert first_receipt.output_fingerprint == first.role_summary_fingerprint
    with pytest.raises(HarnessFingerprintError, match="Role result fingerprint mismatch"):
        dataclasses.replace(first, ranking_fingerprint="0" * 64)
    changed_snapshot = RepositorySnapshotRef(
        "0" * 40,
        first.snapshot.repository_tree_sha,
    )
    with pytest.raises(HarnessFingerprintError, match="Role result fingerprint mismatch"):
        dataclasses.replace(first, snapshot=changed_snapshot)
    with pytest.raises(HarnessFingerprintError, match="Role summary fingerprint mismatch"):
        dataclasses.replace(first.summaries[0], h2_priority=999)


def test_result_factory_rejects_summary_order_or_identity_mismatch(tmp_path: Path):
    repository = _make_repository(
        tmp_path,
        {
            "src/a.py": b"pass\n",
            "src/b.py": b"pass\n",
        },
    )
    ranking = _ranking(repository)
    result, _ = summarize_repository_roles(repository, ranking)

    with pytest.raises(HarnessValidationError, match="preserve exact H2"):
        RepositoryRoleSummaryResult.create(ranking, tuple(reversed(result.summaries)))
    with pytest.raises(HarnessValidationError, match="count"):
        RepositoryRoleSummaryResult.create(ranking, result.summaries[:1])


def test_tampered_h2_ranking_is_revalidated_before_git_body_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repository, ranking = _single_source_repository(tmp_path)
    object.__setattr__(ranking, "ranking_fingerprint", "0" * 64)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("Git must not run before H2 revalidation")

    monkeypatch.setattr(roles_module, "_open_git_process", forbidden)
    with pytest.raises(HarnessFingerprintError, match="Ranking fingerprint mismatch"):
        summarize_repository_roles(repository, ranking)


def test_receipt_is_exact_zero_authority_and_no_executor_tendency_is_inferred(tmp_path: Path):
    repository, ranking = _single_source_repository(tmp_path)
    result, receipt = summarize_repository_roles(repository, ranking)

    assert receipt.generator_version == H3_ROLE_POLICY_VERSION
    assert receipt.candidate_count == 1
    assert receipt.selected_count == 1
    assert receipt.excluded_count == 0
    assert receipt.authority_created is False
    assert receipt.network_used is False
    assert receipt.llm_used is False
    assert receipt.paid_api_used is False
    assert not hasattr(result, "executor_tendency")
    assert not hasattr(result.summaries[0], "executor_tendency")


def test_main_guard_equivalence_accepts_reversed_operands(tmp_path: Path):
    repository, ranking = _single_source_repository(
        tmp_path,
        b'if "__main__" == __name__:\n    pass\n',
    )
    result, _ = summarize_repository_roles(repository, ranking)
    assert result.summaries[0].artifact_role is ArtifactRole.EXECUTABLE_ENTRYPOINT


def test_summary_types_are_frozen_and_symbol_locators_are_bounded(tmp_path: Path):
    repository, ranking = _single_source_repository(tmp_path)
    result, _ = summarize_repository_roles(repository, ranking)
    summary = result.summaries[0]
    symbol = summary.symbols[0]

    assert symbol.symbol_locator == "function:selected@L1"
    with pytest.raises(dataclasses.FrozenInstanceError):
        symbol.name = "changed"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.h2_priority = 1  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.task_id = "TASK-999"  # type: ignore[misc]
