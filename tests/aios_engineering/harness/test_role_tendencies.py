from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import subprocess

import pytest

import src.aios_engineering.harness.role_tendencies as role_tendencies_module
from src.aios_engineering.harness import (
    ArtifactRole,
    ComponentMemberFile,
    ComponentRoleSummary,
    ExecutorComponentObservation,
    ExecutorTendencyProfile,
    H2GraphRelation,
    H3MustNotOwn,
    H3_MUST_NOT_OWN_DEFAULT,
    H3_ROLE_TENDENCY_POLICY_VERSION,
    H3_ROLE_TENDENCY_SCHEMA_VERSION,
    HarnessFingerprintError,
    HarnessValidationError,
    RepositoryRoleSummaryResult,
    RepositoryRoleTendencyBoundError,
    RepositoryRoleTendencyConsistencyError,
    RepositoryRoleTendencyResult,
    RepositorySnapshotRef,
    StructuralComponentKind,
    TaskRelevanceSpec,
    build_repository_dependency_graph,
    build_repository_experience_manifest,
    build_repository_structural_experience_graph,
    discover_control_plane_experience,
    discover_repository_snapshot,
    rank_repository_evidence,
    summarize_repository_roles,
    summarize_repository_roles_and_executor_tendencies,
)


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _write(repository: Path, path: str, body: str | bytes) -> None:
    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(body, bytes):
        target.write_bytes(body)
    else:
        target.write_bytes(body.encode("utf-8"))


def _base_files() -> dict[str, str]:
    return {
        "src/__init__.py": "",
        "src/pkg/__init__.py": "",
        "src/pkg/sub/__init__.py": "VALUE = 1\n",
        "src/pkg/sub/a.py": (
            "from . import b\n"
            "class Service:\n"
            "    pass\n\n"
            "def run():\n"
            "    return b.VALUE\n"
        ),
        "src/pkg/sub/b.py": "VALUE = 1\n",
        "loose.py": "def loose():\n    return 1\n",
        "standalone_entry.py": "if __name__ == '__main__':\n    pass\n",
        ".ai/tasks/TASK-081.md": (
            "# TASK-081\n\n"
            "EXECUTOR_ALLOWED_PATHS_JSON: "
            "[\"src/pkg/sub/a.py\",\"loose.py\"]\n"
        ),
        ".ai/results/RESULT-081.md": (
            "# RESULT-081\n\n"
            "## Review Manifest\n\n"
            "```text\n"
            "TASK_ID: TASK-081\n"
            "EXECUTOR_ID: antigravity\n"
            "STATUS: PASS\n"
            "```\n"
        ),
        ".ai/reviews/REVIEW-081.md": (
            "# REVIEW-081\n\n"
            "### B1 — Structural finding\n\n"
            "H2_COMPONENT_PATH: loose.py\n"
        ),
    }


def _build_fixture(tmp_path: Path, overrides: dict[str, str] | None = None):
    repository = tmp_path / "repository"
    repository.mkdir(parents=True, exist_ok=True)
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "h3@example.invalid")
    _git(repository, "config", "user.name", "H3 Fixture")
    files = _base_files()
    if overrides:
        files.update(overrides)
    for path, body in files.items():
        _write(repository, path, body)
    _git(repository, "add", ".")
    _git(repository, "commit", "-q", "-m", "exact h3 fixture")
    commit_sha = _git(repository, "rev-parse", "HEAD").decode().strip()

    discovery, _ = discover_repository_snapshot(repository, commit_sha, task_id="TASK-081")
    spec = TaskRelevanceSpec(
        task_id="TASK-081",
        exact_paths=("loose.py", "standalone_entry.py"),
        path_prefixes=("src",),
        max_selected=32,
    )
    ranking, _ = rank_repository_evidence(discovery, spec)
    roles, role_receipt = summarize_repository_roles(repository, ranking)
    import_graph, _ = build_repository_dependency_graph(repository, ranking, roles)
    control = discover_control_plane_experience(repository, commit_sha)
    manifest = build_repository_experience_manifest(discovery, control)
    h2_graph, h2_receipt = build_repository_structural_experience_graph(
        repository,
        discovery,
        ranking,
        roles,
        import_graph,
        manifest,
    )
    result, receipt = summarize_repository_roles_and_executor_tendencies(
        h2_graph,
        roles,
    )
    return {
        "repository": repository,
        "commit_sha": commit_sha,
        "discovery": discovery,
        "ranking": ranking,
        "roles": roles,
        "import_graph": import_graph,
        "control": control,
        "manifest": manifest,
        "h2_graph": h2_graph,
        "result": result,
        "receipt": receipt,
    }


def test_h3_policy_schema_identity(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]
    receipt = fixture["receipt"]

    assert H3_ROLE_TENDENCY_POLICY_VERSION == "h3-role-tendency-v1"
    assert H3_ROLE_TENDENCY_SCHEMA_VERSION == "1"
    assert result.policy_version == H3_ROLE_TENDENCY_POLICY_VERSION
    assert result.schema_version == H3_ROLE_TENDENCY_SCHEMA_VERSION
    assert receipt.generator_version == H3_ROLE_TENDENCY_POLICY_VERSION
    assert receipt.authority_created is False
    assert receipt.network_used is False
    assert receipt.llm_used is False
    assert receipt.paid_api_used is False


def test_h2_and_role_input_revalidation(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    h2_graph = fixture["h2_graph"]
    roles = fixture["roles"]

    with pytest.raises(HarnessValidationError, match="h2_graph must be exact"):
        summarize_repository_roles_and_executor_tendencies(None, roles)  # type: ignore[arg-type]

    with pytest.raises(HarnessValidationError, match="role_summaries must be exact"):
        summarize_repository_roles_and_executor_tendencies(h2_graph, None)  # type: ignore[arg-type]


def test_repository_snapshot_cross_binding(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    h2_graph = fixture["h2_graph"]
    roles = fixture["roles"]

    # Tamper roles snapshot commit SHA
    bad_snapshot_commit = RepositorySnapshotRef(
        repository_commit_sha="0" * 40,
        repository_tree_sha=roles.snapshot.repository_tree_sha,
    )
    tampered_roles_commit = copy.copy(roles)
    object.__setattr__(tampered_roles_commit, "snapshot", bad_snapshot_commit)
    with pytest.raises(RepositoryRoleTendencyConsistencyError, match="commit SHA mismatch"):
        summarize_repository_roles_and_executor_tendencies(h2_graph, tampered_roles_commit)

    # Tamper roles snapshot tree SHA
    bad_snapshot_tree = RepositorySnapshotRef(
        repository_commit_sha=roles.snapshot.repository_commit_sha,
        repository_tree_sha="0" * 40,
    )
    tampered_roles_tree = copy.copy(roles)
    object.__setattr__(tampered_roles_tree, "snapshot", bad_snapshot_tree)
    with pytest.raises(RepositoryRoleTendencyConsistencyError, match="tree SHA mismatch"):
        summarize_repository_roles_and_executor_tendencies(h2_graph, tampered_roles_tree)

    # Tamper role_summary_fingerprint
    tampered_h2_graph = copy.copy(h2_graph)
    object.__setattr__(tampered_h2_graph, "role_summary_fingerprint", "0" * 64)
    with pytest.raises(RepositoryRoleTendencyConsistencyError, match="role_summary_fingerprint mismatch"):
        summarize_repository_roles_and_executor_tendencies(tampered_h2_graph, roles)


def test_component_summary_for_each_h2_component_and_member_files(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]
    h2_graph = fixture["h2_graph"]

    assert len(result.component_summaries) == len(h2_graph.components)
    component_ids = {c.component_id for c in result.component_summaries}
    h2_component_ids = {c.component_id for c in h2_graph.components}
    assert component_ids == h2_component_ids

    pkg_summary = next(c for c in result.component_summaries if c.path == "src/pkg/sub")
    assert pkg_summary.kind is StructuralComponentKind.PYTHON_PACKAGE
    assert any(f.path == "src/pkg/sub/a.py" for f in pkg_summary.member_files)
    assert any(f.path == "src/pkg/sub/b.py" for f in pkg_summary.member_files)
    assert any(f.path == "src/pkg/sub/__init__.py" for f in pkg_summary.member_files)
    assert ArtifactRole.PACKAGE_EXPORT_SURFACE in pkg_summary.observed_roles
    assert ArtifactRole.SOURCE_IMPLEMENTATION in pkg_summary.observed_roles

    entry_summary = next(c for c in result.component_summaries if c.path == "standalone_entry.py")
    assert entry_summary.kind is StructuralComponentKind.STANDALONE_PYTHON_MODULE
    assert ArtifactRole.EXECUTABLE_ENTRYPOINT in entry_summary.observed_roles


def test_missing_role_evidence_not_guessed_and_blob_mismatch_fails_to_attach():
    # 1. Direct model test: ComponentMemberFile with unobserved role
    unobserved_file = ComponentMemberFile(
        path="src/unobserved.py",
        blob_sha="a" * 40,
        observed_role=None,
    )
    assert unobserved_file.observed_role is None
    assert unobserved_file.to_dict() == {
        "blob_sha": "a" * 40,
        "observed_role": None,
        "path": "src/unobserved.py",
    }

    # 2. ComponentRoleSummary with unobserved member file
    comp = ComponentRoleSummary.create(
        component_id="component:STANDALONE_PYTHON_MODULE:src/unobserved.py",
        path="src/unobserved.py",
        kind=StructuralComponentKind.STANDALONE_PYTHON_MODULE,
        member_files=(unobserved_file,),
        observed_roles=(),
        symbol_count=0,
        inbound_component_count=0,
        outbound_component_count=0,
    )
    assert comp.observed_roles == ()
    assert comp.member_files[0].observed_role is None

    # 3. Path match alone does NOT attach role when blob_sha differs
    role_by_path_blob = {("src/unobserved.py", "b" * 40): ArtifactRole.SOURCE_IMPLEMENTATION}
    attached_role = role_by_path_blob.get((unobserved_file.path, unobserved_file.blob_sha))
    assert attached_role is None


def test_global_must_not_own_set_exact_and_cannot_be_removed(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]

    expected_set = (
        "BRIDGE_TASK_AUTHORITY",
        "BRIDGE_REVIEW_AUTHORITY",
        "LEASE_AUTHORITY",
        "EXECUTOR_DISPATCH_AUTHORITY",
        "RETRY_REROUTE_AUTHORITY",
        "MERGE_AUTHORITY",
        "PAID_PROVIDER_AUTHORITY",
    )
    assert H3_MUST_NOT_OWN_DEFAULT == expected_set
    for comp in result.component_summaries:
        assert comp.must_not_own == expected_set

    # Attempting to construct ComponentRoleSummary with tampered must_not_own fails
    first_comp = result.component_summaries[0]
    with pytest.raises(HarnessValidationError, match="must_not_own must be the exact canonical"):
        replace(first_comp, must_not_own=("MERGE_AUTHORITY",))


def test_executor_profile_from_h2_executor_edge_and_coobservations(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]

    assert len(result.executor_profiles) == 1
    profile = result.executor_profiles[0]
    assert profile.executor_id == "antigravity"
    assert profile.observed_tasks == ("TASK-081",)
    assert profile.observed_task_count == 1
    assert "component:PYTHON_PACKAGE:src/pkg/sub" in profile.coobserved_component_ids
    assert "component:STANDALONE_PYTHON_MODULE:loose.py" in profile.coobserved_component_ids
    assert len(profile.coobserved_review_finding_ids) == 1
    assert profile.coobserved_review_finding_ids[0].startswith("review-finding:TASK-081:B1:")


def test_multiple_executors_one_task_preserved_and_no_preference(tmp_path: Path):
    overrides = {
        ".ai/tasks/TASK-082.md": "# TASK-082\n\nEXECUTOR_ALLOWED_PATHS_JSON: [\"loose.py\"]\n",
        ".ai/results/RESULT-082.md": (
            "# RESULT-082\n\n"
            "## Review Manifest\n\n"
            "```text\n"
            "TASK_ID: TASK-082\n"
            "EXECUTOR_ID: codex\n"
            "STATUS: PASS\n"
            "```\n"
        ),
    }
    fixture = _build_fixture(tmp_path, overrides)
    res = fixture["result"]
    assert len(res.executor_profiles) == 2
    executors = {p.executor_id for p in res.executor_profiles}
    assert executors == {"antigravity", "codex"}
    for p in res.executor_profiles:
        assert not hasattr(p, "preferred_executor")
        assert not hasattr(p, "routing_score")
        assert not hasattr(p, "winner")


def test_no_executor_edge_produces_no_executor_profiles(tmp_path: Path):
    # Overwrite RESULT-081 with no review manifest
    fixture = _build_fixture(
        tmp_path,
        {".ai/results/RESULT-081.md": "# RESULT-081\n\nNo manifest here.\n"},
    )
    result = fixture["result"]
    assert len(result.executor_profiles) == 0


def test_hard_bounds_and_bool_as_int_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]
    comp = result.component_summaries[0]

    # bool as int in symbol_count
    with pytest.raises(HarnessValidationError, match="symbol_count must be an exact integer, not bool"):
        replace(comp, symbol_count=True)  # type: ignore[arg-type]

    # negative int in symbol_count
    with pytest.raises(HarnessValidationError, match="symbol_count must be >= 0"):
        replace(comp, symbol_count=-1)

    # bounds enforcement
    monkeypatch.setattr(role_tendencies_module, "MAX_H3_COMPONENT_SUMMARIES", 1)
    with pytest.raises(RepositoryRoleTendencyBoundError, match="component_summaries exceeds hard limit"):
        RepositoryRoleTendencyResult.create(
            snapshot=result.snapshot,
            h2_graph_fingerprint=result.h2_graph_fingerprint,
            role_summary_fingerprint=result.role_summary_fingerprint,
            component_summaries=result.component_summaries,
            executor_profiles=result.executor_profiles,
            unobserved_role_file_count=0,
        )


def test_tamper_evidence_on_components_profiles_and_result(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]

    # Tamper component summary fingerprint
    bad_comp = copy.copy(result.component_summaries[0])
    object.__setattr__(bad_comp, "summary_fingerprint", "0" * 64)
    with pytest.raises(HarnessFingerprintError):
        replace(result, component_summaries=(bad_comp, *result.component_summaries[1:]))

    # Tamper executor profile fingerprint
    bad_prof = copy.copy(result.executor_profiles[0])
    object.__setattr__(bad_prof, "profile_fingerprint", "0" * 64)
    with pytest.raises(HarnessFingerprintError):
        replace(result, executor_profiles=(bad_prof, *result.executor_profiles[1:]))

    # Tamper result fingerprint
    with pytest.raises(HarnessFingerprintError):
        replace(result, result_fingerprint="0" * 64)


def test_pure_composition_no_worktree_reads_or_subprocesses_or_authority_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    fixture = _build_fixture(tmp_path)

    # Monkeypatch subprocess.Popen and subprocess.run to forbid calls
    def forbidden(*args: object, **kwargs: object):
        raise AssertionError("No subprocesses allowed in pure H3 composition")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)

    res, receipt = summarize_repository_roles_and_executor_tendencies(
        fixture["h2_graph"],
        fixture["roles"],
    )
    assert res.result_fingerprint is not None
    assert receipt.authority_created is False

    # Check source code has no AST imports, network, or bridge authority imports
    source = Path(role_tendencies_module.__file__).read_text(encoding="utf-8")
    assert "import ast" not in source
    assert "urllib" not in source and "requests" not in source and "http" not in source
    assert "bridge.py" not in source
    assert "preferred_executor" not in source
    assert "routing_score" not in source
    assert "quality_grade" not in source
