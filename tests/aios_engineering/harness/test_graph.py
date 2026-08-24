from __future__ import annotations

import dataclasses
from pathlib import Path
import subprocess

import pytest

from src.aios_engineering import harness as harness_module
from src.aios_engineering.harness import (
    ContentAnalysisStatus,
    EvidenceKind,
    H2_IMPORT_GRAPH_POLICY_VERSION,
    HarnessFingerprintError,
    HarnessValidationError,
    ImportDependencyKind,
    ImportResolutionStatus,
    MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE,
    MAX_H2_IMPORT_GRAPH_TOTAL_IMPORT_EDGES,
    RepositoryDependencyGraphBoundError,
    RepositoryDependencyGraphConsistencyError,
    RepositoryDiscoveryResult,
    RepositoryEvidenceRef,
    RepositoryImportDependency,
    RepositoryRoleSummaryGitError,
    RepositoryRoleSummaryResult,
    RepositorySnapshotRef,
    TaskRelevanceSpec,
    build_repository_dependency_graph,
    discover_repository_snapshot,
    rank_repository_evidence,
    summarize_repository_roles,
)
from src.aios_engineering.harness import graph as graph_module
from src.aios_engineering.harness import roles as roles_module


HISTORICAL_SOURCE_SHA = "fea85a8bc7f696c50fd5457b0cea3b5d8032b24f"


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
    _git(repository, "config", "user.name", "H2 Import Graph Tests")
    _git(repository, "config", "user.email", "h2-import-graph-tests@example.invalid")
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


def _ranking(
    repository: Path,
    *,
    exact_paths: tuple[str, ...] = (),
    max_selected: int | None = None,
):
    snapshot = _snapshot(repository)
    discovery, _ = discover_repository_snapshot(
        repository,
        snapshot.repository_commit_sha,
        task_id="TASK-079",
    )
    selected_limit = len(discovery.evidence) if max_selected is None else max_selected
    spec = TaskRelevanceSpec(
        task_id="TASK-079",
        exact_paths=exact_paths,
        preferred_kinds=tuple(EvidenceKind),
        max_selected=selected_limit,
    )
    ranking, _ = rank_repository_evidence(discovery, spec)
    return ranking


def _inputs(
    repository: Path,
    *,
    exact_paths: tuple[str, ...] = (),
    max_selected: int | None = None,
):
    ranking = _ranking(
        repository,
        exact_paths=exact_paths,
        max_selected=max_selected,
    )
    roles, _ = summarize_repository_roles(repository, ranking)
    return ranking, roles


def _single_source(tmp_path: Path, body: bytes = b"import external\n"):
    repository = _make_repository(tmp_path, {"src/main.py": body})
    ranking, roles = _inputs(repository)
    return repository, ranking, roles


def test_salvage_provenance_and_h2_public_identity_are_locked():
    repository_root = Path(__file__).resolve().parents[3]

    assert HISTORICAL_SOURCE_SHA == "fea85a8bc7f696c50fd5457b0cea3b5d8032b24f"

    assert H2_IMPORT_GRAPH_POLICY_VERSION == "h2-import-graph-v1"
    assert harness_module.H2_IMPORT_GRAPH_POLICY_VERSION == H2_IMPORT_GRAPH_POLICY_VERSION
    prior_milestone = "H" + str(4)
    assert not hasattr(harness_module, f"{prior_milestone}_GRAPH_POLICY_VERSION")

    forbidden_identity_tokens = (
        f"{prior_milestone}_GRAPH_POLICY_VERSION",
        f"MAX_{prior_milestone}_",
        f"{prior_milestone.lower()}-v1",
        f"{prior_milestone} static Python import dependency graph",
        f"{prior_milestone} dependency graph",
    )
    changed_paths = (
        repository_root / "src/aios_engineering/harness/graph.py",
        repository_root / "src/aios_engineering/harness/__init__.py",
        Path(__file__),
    )
    for changed_path in changed_paths:
        changed_text = changed_path.read_text(encoding="utf-8")
        assert not any(token in changed_text for token in forbidden_identity_tokens)

    graph_text = changed_paths[0].read_text(encoding="utf-8")
    out_of_scope_claims = (
        "H2_COMPLETE",
        "RepositoryExperienceGraph",
        "ComponentGraph",
        "ExecutorTendency",
        "KnowledgeRegistry",
        "HybridRetrieval",
    )
    assert not any(claim in graph_text for claim in out_of_scope_claims)


def test_static_import_extraction_resolution_and_order_are_deterministic(tmp_path: Path):
    main_source = (
        "import pkg.selected\n"
        "import pkg.unselected\n"
        "import pkg.ambiguous\n"
        "import app.helper\n"
        "import outside\n"
        "from pkg.selected import A, B\n"
        "from .helper import local\n"
        "from . import maybe_symbol\n"
        "def nested():\n"
        "    import pkg.selected\n"
        "__import__('pkg.unselected')\n"
        "importlib.import_module('pkg.unselected')\n"
    ).encode("utf-8")
    repository = _make_repository(
        tmp_path,
        {
            "pkg/selected.py": b"VALUE = 1\n",
            "pkg/unselected.py": b"VALUE = 2\n",
            "pkg/ambiguous.py": b"VALUE = 3\n",
            "src/pkg/ambiguous.py": b"VALUE = 4\n",
            "src/app/__init__.py": b"VALUE = 5\n",
            "src/app/helper.py": b"VALUE = 6\n",
            "src/app/main.py": main_source,
        },
    )
    selected_paths = (
        "pkg/selected.py",
        "src/app/__init__.py",
        "src/app/helper.py",
        "src/app/main.py",
    )
    ranking, roles = _inputs(
        repository,
        exact_paths=selected_paths,
        max_selected=len(selected_paths),
    )

    first, first_receipt = build_repository_dependency_graph(repository, ranking, roles)
    second, second_receipt = build_repository_dependency_graph(repository, ranking, roles)

    assert first == second
    assert first_receipt == second_receipt
    assert [edge.line_number for edge in first.edges] == [1, 2, 3, 4, 5, 6, 6, 7, 8, 10]
    assert [edge.imported_name for edge in first.edges[5:7]] == ["A", "B"]
    assert all(edge.source_path == "src/app/main.py" for edge in first.edges)
    assert first.edges[0].kind is ImportDependencyKind.IMPORT_MODULE
    assert first.edges[5].kind is ImportDependencyKind.IMPORT_FROM

    by_line = {edge.line_number: edge for edge in first.edges if edge.line_number != 6}
    assert by_line[1].resolution_status is ImportResolutionStatus.INTERNAL_SELECTED
    assert by_line[1].target_path == "pkg/selected.py"
    assert by_line[2].resolution_status is ImportResolutionStatus.INTERNAL_UNSELECTED
    assert by_line[2].target_path == "pkg/unselected.py"
    assert by_line[3].resolution_status is ImportResolutionStatus.AMBIGUOUS_INTERNAL
    assert by_line[3].target_path is None
    assert by_line[4].resolution_status is ImportResolutionStatus.INTERNAL_SELECTED
    assert by_line[4].target_path == "src/app/helper.py"
    assert by_line[5].resolution_status is ImportResolutionStatus.EXTERNAL_OR_UNRESOLVED
    assert by_line[7].resolution_status is ImportResolutionStatus.INTERNAL_SELECTED
    assert by_line[7].target_path == "src/app/helper.py"
    assert by_line[8].resolution_status is ImportResolutionStatus.INTERNAL_SELECTED
    assert by_line[8].target_path == "src/app/__init__.py"
    assert not any(edge.line_number in {11, 12} for edge in first.edges)


def test_cross_binding_mismatch_fails_before_any_git_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repository, ranking, roles = _single_source(tmp_path)
    object.__setattr__(roles, "ranking_fingerprint", "0" * 64)

    def forbidden_git(*args: object, **kwargs: object) -> object:
        raise AssertionError("Git must not run before the complete H2/H3 binding gate")

    monkeypatch.setattr(roles_module, "_open_git_process", forbidden_git)
    with pytest.raises(HarnessFingerprintError, match="Role result fingerprint mismatch"):
        build_repository_dependency_graph(repository, ranking, roles)


def test_only_selected_parsed_python_bodies_are_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repository = _make_repository(
        tmp_path,
        {
            "docs/selected.md": b"not Python\n",
            "src/parsed.py": b"import external\n",
            "src/rejected.py": b"def broken(:\n",
            "src/unselected.py": b"import must_not_be_read\n",
        },
    )
    selected = ("docs/selected.md", "src/parsed.py", "src/rejected.py")
    ranking, roles = _inputs(repository, exact_paths=selected, max_selected=3)
    body_reads: list[str] = []
    original_read = roles_module._read_blob_body

    def recording_read(root: Path, blob_sha: str, size: int) -> bytes:
        body_reads.append(blob_sha)
        return original_read(root, blob_sha, size)

    monkeypatch.setattr(roles_module, "_read_blob_body", recording_read)
    result, _ = build_repository_dependency_graph(repository, ranking, roles)
    parsed = next(summary for summary in roles.summaries if summary.path == "src/parsed.py")

    assert body_reads == [parsed.blob_sha]
    assert all(edge.source_path == "src/parsed.py" for edge in result.edges)
    assert {
        summary.path: summary.analysis_status for summary in roles.summaries
    } == {
        "docs/selected.md": ContentAnalysisStatus.NOT_PYTHON,
        "src/parsed.py": ContentAnalysisStatus.PARSED,
        "src/rejected.py": ContentAnalysisStatus.SYNTAX_REJECTED,
    }


def test_dirty_worktree_and_path_body_reads_do_not_affect_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repository, ranking, roles = _single_source(tmp_path, b"import committed\n")
    first, first_receipt = build_repository_dependency_graph(repository, ranking, roles)
    (repository / "src/main.py").write_bytes(b"this dirty source is invalid\n")
    (repository / "src/untracked.py").write_bytes(b"import ignored\n")

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("mutable worktree body read attempted")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    second, second_receipt = build_repository_dependency_graph(repository, ranking, roles)

    assert second == first
    assert second_receipt == first_receipt


def test_exact_commit_tree_binding_is_reverified_before_body_read(tmp_path: Path):
    repository, original_ranking, original_roles = _single_source(tmp_path)
    original_snapshot = original_ranking.plan.snapshot
    (repository / "src/second.py").write_bytes(b"pass\n")
    _git(repository, "add", "--all")
    _git(repository, "commit", "-q", "-m", "second snapshot")
    mismatched_snapshot = RepositorySnapshotRef(
        original_snapshot.repository_commit_sha,
        _snapshot(repository).repository_tree_sha,
    )
    original_evidence = original_ranking.plan.selected_evidence[0]
    discovery = RepositoryDiscoveryResult.create(
        mismatched_snapshot,
        (
            RepositoryEvidenceRef(
                path=original_evidence.path,
                blob_sha=original_evidence.blob_sha,
                evidence_kind=original_evidence.evidence_kind,
                reason_code="DISCOVERED_GIT_BLOB",
                priority=0,
            ),
        ),
    )
    ranking, _ = rank_repository_evidence(
        discovery,
        TaskRelevanceSpec(task_id="TASK-079", preferred_kinds=(EvidenceKind.SOURCE,)),
    )
    roles = RepositoryRoleSummaryResult.create(ranking, original_roles.summaries)

    with pytest.raises(RepositoryRoleSummaryGitError, match="tree"):
        build_repository_dependency_graph(repository, ranking, roles)


def test_h3_exact_blob_sha_reproof_is_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repository, ranking, roles = _single_source(tmp_path, b"import exact_blob\n")
    original_run = roles_module._run_git_output

    def tampered_run(
        root: Path,
        command: list[str],
        *,
        output_limit: int,
    ) -> bytes:
        output = original_run(root, command, output_limit=output_limit)
        if len(command) >= 3 and command[:2] == ["cat-file", "blob"]:
            return b"x" * len(output)
        return output

    monkeypatch.setattr(roles_module, "_run_git_output", tampered_run)
    with pytest.raises(RepositoryRoleSummaryGitError, match="actual analyzed body Git blob SHA"):
        build_repository_dependency_graph(repository, ranking, roles)


def test_duplicate_exact_import_edge_fails_closed(tmp_path: Path):
    repository, ranking, roles = _single_source(tmp_path, b"import duplicate, duplicate\n")

    with pytest.raises(HarnessValidationError, match="duplicate exact dependency edge"):
        build_repository_dependency_graph(repository, ranking, roles)


def test_per_file_edge_bound_fails_without_silent_truncation(tmp_path: Path):
    source = "".join(
        f"import external_{index}\n"
        for index in range(MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE + 1)
    ).encode("utf-8")
    repository, ranking, roles = _single_source(tmp_path, source)

    with pytest.raises(RepositoryDependencyGraphBoundError, match="per-file"):
        build_repository_dependency_graph(repository, ranking, roles)


def test_total_edge_bound_fails_without_silent_truncation(tmp_path: Path):
    file_count = MAX_H2_IMPORT_GRAPH_TOTAL_IMPORT_EDGES // MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE + 1
    files = {
        f"src/source_{file_index}.py": "".join(
            f"import external_{file_index}_{edge_index}\n"
            for edge_index in range(MAX_H2_IMPORT_GRAPH_IMPORT_EDGES_PER_FILE)
        ).encode("utf-8")
        for file_index in range(file_count)
    }
    repository = _make_repository(tmp_path, files)
    ranking, roles = _inputs(repository)

    with pytest.raises(RepositoryDependencyGraphBoundError, match="total import edge"):
        build_repository_dependency_graph(repository, ranking, roles)


def test_total_body_bound_is_recomputed_in_selected_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repository, ranking, roles = _single_source(tmp_path, b"import bounded\n")
    parsed_size = roles.summaries[0].blob_size_bytes
    monkeypatch.setattr(graph_module, "MAX_H2_IMPORT_GRAPH_TOTAL_BODY_BYTES", parsed_size - 1)

    with pytest.raises(RepositoryDependencyGraphBoundError, match="aggregate body"):
        build_repository_dependency_graph(repository, ranking, roles)


def test_upstream_parsed_contradiction_and_operational_ast_failure_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repository, ranking, roles = _single_source(tmp_path, b"import stable\n")
    original_body_read = roles_module._read_blob_body

    def undecodable_body(root: Path, blob_sha: str, size: int) -> bytes:
        original_body_read(root, blob_sha, size)
        return b"\xff" * size

    monkeypatch.setattr(roles_module, "_read_blob_body", undecodable_body)
    with pytest.raises(RepositoryDependencyGraphConsistencyError, match="UTF-8"):
        build_repository_dependency_graph(repository, ranking, roles)

    monkeypatch.setattr(roles_module, "_read_blob_body", original_body_read)

    def operational_failure(*args: object, **kwargs: object) -> object:
        raise RuntimeError("operational AST failure")

    monkeypatch.setattr(graph_module.ast, "parse", operational_failure)
    with pytest.raises(RuntimeError, match="operational AST failure"):
        build_repository_dependency_graph(repository, ranking, roles)


def test_fingerprints_bind_h2_h3_snapshot_edges_and_receipt_is_zero_authority(
    tmp_path: Path,
):
    repository, ranking, roles = _single_source(tmp_path, b"import fingerprinted\n")
    result, receipt = build_repository_dependency_graph(repository, ranking, roles)

    assert result.policy_version == H2_IMPORT_GRAPH_POLICY_VERSION
    assert result.ranking_fingerprint == ranking.ranking_fingerprint
    assert result.h2_plan_fingerprint == ranking.plan.plan_fingerprint
    assert result.h3_role_summary_fingerprint == roles.role_summary_fingerprint
    assert result.source_summary_fingerprints == tuple(
        summary.summary_fingerprint for summary in roles.summaries
    )
    assert receipt.generator_version == H2_IMPORT_GRAPH_POLICY_VERSION
    assert receipt.output_fingerprint == result.graph_fingerprint
    assert receipt.candidate_count == len(roles.summaries)
    assert receipt.selected_count == len(roles.summaries)
    assert receipt.excluded_count == 0
    assert receipt.authority_created is False
    assert receipt.network_used is False
    assert receipt.llm_used is False
    assert receipt.paid_api_used is False
    with pytest.raises(HarnessFingerprintError, match="Dependency graph fingerprint mismatch"):
        dataclasses.replace(result, ranking_fingerprint="0" * 64)
    with pytest.raises(HarnessFingerprintError, match="Dependency graph fingerprint mismatch"):
        dataclasses.replace(result, h2_plan_fingerprint="0" * 64)
    with pytest.raises(HarnessFingerprintError, match="Dependency graph fingerprint mismatch"):
        dataclasses.replace(result, h3_role_summary_fingerprint="0" * 64)
    changed_snapshot = RepositorySnapshotRef(
        "0" * 40,
        result.snapshot.repository_tree_sha,
    )
    with pytest.raises(HarnessFingerprintError, match="Dependency graph fingerprint mismatch"):
        dataclasses.replace(result, snapshot=changed_snapshot)
    with pytest.raises(HarnessFingerprintError, match="edge fingerprint mismatch"):
        dataclasses.replace(result.edges[0], line_number=2)


def test_edge_contracts_are_frozen_and_integer_bools_are_rejected(tmp_path: Path):
    repository, ranking, roles = _single_source(tmp_path)
    result, _ = build_repository_dependency_graph(repository, ranking, roles)
    edge = result.edges[0]

    with pytest.raises(dataclasses.FrozenInstanceError):
        edge.line_number = 2  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.task_id = "TASK-999"  # type: ignore[misc]
    with pytest.raises(HarnessValidationError, match="relative_level"):
        RepositoryImportDependency.create(
            source_path=edge.source_path,
            source_blob_sha=edge.source_blob_sha,
            kind=ImportDependencyKind.IMPORT_FROM,
            module_expression="pkg",
            imported_name="name",
            relative_level=True,  # type: ignore[arg-type]
            line_number=1,
            column_offset=0,
            resolution_status=ImportResolutionStatus.EXTERNAL_OR_UNRESOLVED,
        )
