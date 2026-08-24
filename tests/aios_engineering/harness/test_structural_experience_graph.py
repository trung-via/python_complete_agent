from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import subprocess

import pytest

import src.aios_engineering.harness.structural_experience_graph as graph_module
from src.aios_engineering.harness import (
    ControlPlaneExperienceManifest,
    ExperienceArtifactKind,
    ExperienceArtifactRef,
    ExperienceSurface,
    H2ExperienceParseStatus,
    H2GraphNodeKind,
    H2GraphRelation,
    H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION,
    ImportResolutionStatus,
    RepositoryExperienceManifest,
    RepositoryStructuralExperienceGraphBoundError,
    RepositoryStructuralExperienceGraphConsistencyError,
    RepositoryStructuralExperienceGraphGitError,
    STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION,
    StructuralComponentKind,
    TaskRelevanceSpec,
    build_repository_dependency_graph,
    build_repository_experience_manifest,
    build_repository_structural_experience_graph,
    discover_control_plane_experience,
    discover_repository_snapshot,
    rank_repository_evidence,
    summarize_repository_roles,
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
        "src/pkg/sub/__init__.py": "",
        "src/pkg/sub/a.py": (
            "from . import b\n"
            "import amb\n"
            "import missing_external\n\n"
            "class Service:\n"
            "    pass\n\n"
            "def run():\n"
            "    return b.VALUE\n"
        ),
        "src/pkg/sub/b.py": "VALUE = 1\n",
        "loose.py": "def loose():\n    return 1\n",
        "amb.py": "VALUE = 'module'\n",
        "amb/__init__.py": "VALUE = 'package'\n",
        ".ai/tasks/TASK-080.md": (
            "# TASK-080\n\n"
            "EXECUTOR_ALLOWED_PATHS_JSON: "
            "[\"src/pkg/sub/a.py\",\"missing.py\"]\n"
            "H2_INVARIANT_REFS_JSON: "
            "[{\"invariant_id\":\"INV-EXACT\",\"component_path\":\"src/pkg/sub\"}]\n"
        ),
        ".ai/results/RESULT-080.md": (
            "# RESULT-080\n\n"
            "## Review Manifest\n\n"
            "```text\n"
            "TASK_ID: TASK-080\n"
            "EXECUTOR_ID: codex\n"
            "STATUS: PASS\n"
            "```\n"
        ),
        ".ai/reviews/REVIEW-080.md": (
            "# REVIEW-080\n\n"
            "### B1 — Exact structural path\n\n"
            "H2_COMPONENT_PATH: loose.py\n\n"
            "### B2 — src/pkg/sub/a.py title-only invariant prose\n\n"
            "The title and legacy invariant wording are not component evidence.\n"
        ),
        ".ai/decisions/ADR-080.md": "# Decision\n\nLegacy invariant prose only.\n",
    }


def _build_fixture(tmp_path: Path, overrides: dict[str, str] | None = None):
    repository = tmp_path / "repository"
    repository.mkdir(parents=True)
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "h2@example.invalid")
    _git(repository, "config", "user.name", "H2 Fixture")
    files = _base_files()
    if overrides:
        files.update(overrides)
    for path, body in files.items():
        _write(repository, path, body)
    _git(repository, "add", ".")
    _git(repository, "commit", "-q", "-m", "exact h2 fixture")
    commit_sha = _git(repository, "rev-parse", "HEAD").decode().strip()

    discovery, _ = discover_repository_snapshot(repository, commit_sha, task_id="TASK-080")
    spec = TaskRelevanceSpec(
        task_id="TASK-080",
        exact_paths=("loose.py", "amb.py", "amb/__init__.py"),
        path_prefixes=("src",),
        max_selected=32,
    )
    ranking, _ = rank_repository_evidence(discovery, spec)
    roles, _ = summarize_repository_roles(repository, ranking)
    import_graph, _ = build_repository_dependency_graph(repository, ranking, roles)
    control = discover_control_plane_experience(repository, commit_sha)
    manifest = build_repository_experience_manifest(discovery, control)
    result, receipt = build_repository_structural_experience_graph(
        repository,
        discovery,
        ranking,
        roles,
        import_graph,
        manifest,
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
        "result": result,
        "receipt": receipt,
    }


def _relations(result, relation: H2GraphRelation):
    return tuple(edge for edge in result.edges if edge.relation is relation)


def test_h2_canonical_policy_and_file_symbol_component_graph(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]
    assert H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION == "h2-structural-experience-v1"
    assert STRUCTURAL_EXPERIENCE_GRAPH_SCHEMA_VERSION == "1"
    assert result.policy_version == H2_STRUCTURAL_EXPERIENCE_GRAPH_POLICY_VERSION
    assert any(
        component.kind is StructuralComponentKind.PYTHON_PACKAGE
        and component.path == "src/pkg/sub"
        for component in result.components
    )
    assert any(
        component.kind is StructuralComponentKind.STANDALONE_PYTHON_MODULE
        and component.path == "loose.py"
        for component in result.components
    )
    assert _relations(result, H2GraphRelation.CONTAINS_SYMBOL)
    assert _relations(result, H2GraphRelation.BELONGS_TO_COMPONENT)
    assert _relations(result, H2GraphRelation.FILE_BELONGS_TO_COMPONENT)
    assert {symbol.name for symbol in result.symbols} >= {"Service", "run", "loose"}


def test_experience_relationships_are_closed_evidence_only(tmp_path: Path):
    result = _build_fixture(tmp_path)["result"]
    assert _relations(result, H2GraphRelation.TASK_TOUCHES_COMPONENT)
    assert _relations(result, H2GraphRelation.TASK_EXECUTED_BY_EXECUTOR)
    assert len(_relations(result, H2GraphRelation.TASK_HAS_REVIEW_FINDING)) == 2
    assert len(_relations(result, H2GraphRelation.REVIEW_FINDING_RELATES_TO_COMPONENT)) == 1
    assert _relations(result, H2GraphRelation.TASK_REFERENCES_INVARIANT)
    assert _relations(result, H2GraphRelation.INVARIANT_RELATES_TO_COMPONENT)
    assert sum(node.kind is H2GraphNodeKind.INVARIANT for node in result.nodes) == 1
    assert any(
        record.status is H2ExperienceParseStatus.PATH_NOT_IN_STRUCTURAL_GRAPH
        and record.subject == "missing.py"
        for record in result.unresolved_records
    )


def test_import_graph_is_bound_and_resolution_is_conservative(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]
    assert result.import_graph_fingerprint == fixture["import_graph"].graph_fingerprint
    assert _relations(result, H2GraphRelation.COMPONENT_IMPORTS_COMPONENT)
    ambiguous = tuple(
        edge
        for edge in fixture["import_graph"].edges
        if edge.resolution_status is ImportResolutionStatus.AMBIGUOUS_INTERNAL
    )
    unresolved = tuple(
        edge
        for edge in fixture["import_graph"].edges
        if edge.resolution_status is ImportResolutionStatus.EXTERNAL_OR_UNRESOLVED
    )
    assert ambiguous and unresolved
    assert any(
        record.status is H2ExperienceParseStatus.AMBIGUOUS_COMPONENT
        for record in result.unresolved_records
    )
    # Neither ambiguous nor unresolved import evidence creates a target component edge.
    linked_evidence = {
        edge.evidence_fingerprint
        for edge in _relations(result, H2GraphRelation.COMPONENT_IMPORTS_COMPONENT)
    }
    assert all(edge.edge_fingerprint not in linked_evidence for edge in (*ambiguous, *unresolved))


def test_combined_identity_order_and_zero_authority_receipt(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]
    receipt = fixture["receipt"]
    assert result.nodes == tuple(sorted(result.nodes, key=graph_module._node_order_key))
    assert result.edges == tuple(sorted(result.edges, key=graph_module._graph_edge_order_key))
    assert receipt.generator_version == "h2-structural-experience-v1"
    assert receipt.output_fingerprint == result.graph_fingerprint
    assert receipt.authority_created is receipt.network_used is receipt.llm_used is False
    assert receipt.paid_api_used is False
    assert result.authority_created is False


def test_exact_git_blobs_ignore_worktree_experience_bytes(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    original = fixture["result"]
    _write(
        fixture["repository"],
        ".ai/tasks/TASK-080.md",
        "EXECUTOR_ALLOWED_PATHS_JSON: [\"loose.py\"]\n",
    )
    rebuilt, _ = build_repository_structural_experience_graph(
        fixture["repository"],
        fixture["discovery"],
        fixture["ranking"],
        fixture["roles"],
        fixture["import_graph"],
        fixture["manifest"],
    )
    assert rebuilt == original


def test_upstream_task_role_import_and_manifest_mismatches_fail_before_body_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fixture = _build_fixture(tmp_path)
    body_read = False

    def forbidden_body(*args, **kwargs):
        nonlocal body_read
        body_read = True
        raise AssertionError("body read occurred before binding gate")

    monkeypatch.setattr(graph_module, "_read_experience_blob", forbidden_body)
    with pytest.raises(RepositoryStructuralExperienceGraphConsistencyError):
        build_repository_structural_experience_graph(
            fixture["repository"],
            fixture["discovery"],
            fixture["ranking"],
            fixture["roles"],
            fixture["import_graph"],
            fixture["manifest"],
            task_id="TASK-081",
        )
    assert body_read is False

    bad_roles = copy.copy(fixture["roles"])
    object.__setattr__(bad_roles, "ranking_fingerprint", "0" * 64)
    with pytest.raises(Exception):
        build_repository_structural_experience_graph(
            fixture["repository"], fixture["discovery"], fixture["ranking"], bad_roles,
            fixture["import_graph"], fixture["manifest"]
        )
    bad_import = copy.copy(fixture["import_graph"])
    object.__setattr__(bad_import, "ranking_fingerprint", "0" * 64)
    with pytest.raises(Exception):
        build_repository_structural_experience_graph(
            fixture["repository"], fixture["discovery"], fixture["ranking"], fixture["roles"],
            bad_import, fixture["manifest"]
        )
    bad_manifest = copy.copy(fixture["manifest"])
    object.__setattr__(bad_manifest, "repository_discovery_fingerprint", "0" * 64)
    with pytest.raises(Exception):
        build_repository_structural_experience_graph(
            fixture["repository"], fixture["discovery"], fixture["ranking"], fixture["roles"],
            fixture["import_graph"], bad_manifest
        )
    assert body_read is False


def test_result_task_id_mismatch_is_rejected_during_build(tmp_path: Path):
    with pytest.raises(RepositoryStructuralExperienceGraphConsistencyError):
        _build_fixture(
            tmp_path,
            {
                ".ai/results/RESULT-080.md": (
                    "## Review Manifest\n\n```text\n"
                    "TASK_ID: TASK-081\nEXECUTOR_ID: codex\n```\n"
                )
            },
        )


def test_malformed_explicit_machine_evidence_fails_closed(tmp_path: Path):
    with pytest.raises(RepositoryStructuralExperienceGraphConsistencyError):
        _build_fixture(
            tmp_path,
            {".ai/tasks/TASK-080.md": "EXECUTOR_ALLOWED_PATHS_JSON: {bad json}\n"},
        )


def test_no_explicit_invariant_evidence_allows_zero_invariant_nodes(tmp_path: Path):
    fixture = _build_fixture(
        tmp_path,
        {
            ".ai/tasks/TASK-080.md": (
                "EXECUTOR_ALLOWED_PATHS_JSON: [\"src/pkg/sub/a.py\"]\n"
                "Legacy invariant prose must not create a node.\n"
            )
        },
    )
    assert not any(
        node.kind is H2GraphNodeKind.INVARIANT for node in fixture["result"].nodes
    )


def test_missing_local_experience_object_fails_without_fallback(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    missing = ExperienceArtifactRef(
        surface=ExperienceSurface.CONTROL_PLANE,
        path=".ai/tasks/TASK-999.md",
        blob_sha="f" * 40,
        artifact_kind=ExperienceArtifactKind.TASK,
    )
    control = ControlPlaneExperienceManifest.create(
        fixture["control"].snapshot,
        (*fixture["control"].evidence, missing),
    )
    manifest = build_repository_experience_manifest(fixture["discovery"], control)
    with pytest.raises(RepositoryStructuralExperienceGraphGitError):
        build_repository_structural_experience_graph(
            fixture["repository"], fixture["discovery"], fixture["ranking"], fixture["roles"],
            fixture["import_graph"], manifest
        )


def test_per_blob_and_total_body_bounds_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fixture = _build_fixture(tmp_path)
    monkeypatch.setattr(graph_module, "MAX_H2_GRAPH_EXPERIENCE_BLOB_BYTES", 1)
    with pytest.raises(RepositoryStructuralExperienceGraphBoundError):
        build_repository_structural_experience_graph(
            fixture["repository"], fixture["discovery"], fixture["ranking"], fixture["roles"],
            fixture["import_graph"], fixture["manifest"]
        )
    monkeypatch.setattr(graph_module, "MAX_H2_GRAPH_EXPERIENCE_BLOB_BYTES", 512 * 1024)
    monkeypatch.setattr(graph_module, "MAX_H2_GRAPH_TOTAL_EXPERIENCE_BYTES", 1)
    with pytest.raises(RepositoryStructuralExperienceGraphBoundError):
        build_repository_structural_experience_graph(
            fixture["repository"], fixture["discovery"], fixture["ranking"], fixture["roles"],
            fixture["import_graph"], fixture["manifest"]
        )


def test_node_edge_unresolved_and_component_bounds_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fixture = _build_fixture(tmp_path)
    monkeypatch.setattr(graph_module, "MAX_H2_GRAPH_COMPONENTS", 1)
    with pytest.raises(RepositoryStructuralExperienceGraphBoundError):
        build_repository_structural_experience_graph(
            fixture["repository"], fixture["discovery"], fixture["ranking"], fixture["roles"],
            fixture["import_graph"], fixture["manifest"]
        )
    monkeypatch.setattr(graph_module, "MAX_H2_GRAPH_COMPONENTS", 512)
    monkeypatch.setattr(graph_module, "MAX_H2_GRAPH_UNRESOLVED_RECORDS", 1)
    with pytest.raises(RepositoryStructuralExperienceGraphBoundError):
        build_repository_structural_experience_graph(
            fixture["repository"], fixture["discovery"], fixture["ranking"], fixture["roles"],
            fixture["import_graph"], fixture["manifest"]
        )


def test_node_edge_and_combined_fingerprints_are_tamper_evident(tmp_path: Path):
    result = _build_fixture(tmp_path)["result"]
    bad_node = copy.copy(result.nodes[0])
    object.__setattr__(bad_node, "node_fingerprint", "0" * 64)
    with pytest.raises(Exception):
        replace(result, nodes=(bad_node, *result.nodes[1:]))
    bad_edge = copy.copy(result.edges[0])
    object.__setattr__(bad_edge, "edge_fingerprint", "0" * 64)
    with pytest.raises(Exception):
        replace(result, edges=(bad_edge, *result.edges[1:]))
    with pytest.raises(Exception):
        replace(result, graph_fingerprint="0" * 64)


def test_unresolved_and_upstream_changes_are_combined_fingerprint_sensitive(tmp_path: Path):
    first = _build_fixture(tmp_path / "one")["result"]
    second = _build_fixture(
        tmp_path / "two",
        {
            ".ai/tasks/TASK-080.md": (
                "EXECUTOR_ALLOWED_PATHS_JSON: [\"src/pkg/sub/a.py\"]\n"
                "H2_INVARIANT_REFS_JSON: "
                "[{\"invariant_id\":\"INV-EXACT\",\"component_path\":\"src/pkg/sub\"}]\n"
            )
        },
    )["result"]
    assert first.graph_fingerprint != second.graph_fingerprint
    assert first.experience_manifest_fingerprint != second.experience_manifest_fingerprint


def test_h2_boundary_preserves_h1_and_does_not_claim_h3_h4_or_ownership():
    source = Path(graph_module.__file__).read_text(encoding="utf-8")
    assert "import ast" not in source
    assert "must-own" not in source and "must_not_own" not in source
    assert "knowledge lifecycle" not in source
    assert "H2_COMPLETE" not in source
    assert "network" not in graph_module.build_repository_structural_experience_graph.__doc__.lower()


def test_top_level_markdown_boundary_enforcement(tmp_path: Path):
    # 1. TASK marker inside fence only -> IGNORED (no TASK_TOUCHES_COMPONENT edge)
    fixture_fenced_task = _build_fixture(
        tmp_path / "fenced_task",
        {
            ".ai/tasks/TASK-080.md": (
                "# TASK-080\n\n"
                "Example in docs:\n"
                "```text\n"
                "EXECUTOR_ALLOWED_PATHS_JSON: [\"src/pkg/sub/a.py\"]\n"
                "```\n"
            )
        },
    )
    touches = _relations(fixture_fenced_task["result"], H2GraphRelation.TASK_TOUCHES_COMPONENT)
    assert len(touches) == 0

    # 2. Top-level plus fenced example -> EXACTLY ONE REAL MARKER parsed
    fixture_mixed_task = _build_fixture(
        tmp_path / "mixed_task",
        {
            ".ai/tasks/TASK-080.md": (
                "# TASK-080\n\n"
                "EXECUTOR_ALLOWED_PATHS_JSON: [\"src/pkg/sub/a.py\"]\n\n"
                "Example below:\n"
                "```text\n"
                "EXECUTOR_ALLOWED_PATHS_JSON: [\"loose.py\"]\n"
                "```\n"
            )
        },
    )
    mixed_touches = _relations(fixture_mixed_task["result"], H2GraphRelation.TASK_TOUCHES_COMPONENT)
    assert len(mixed_touches) == 1
    assert mixed_touches[0].target_node_id == "component:PYTHON_PACKAGE:src/pkg/sub"

    # 3. Two top-level task markers -> FAIL CLOSED
    with pytest.raises(RepositoryStructuralExperienceGraphConsistencyError, match="multiple EXECUTOR_ALLOWED_PATHS_JSON markers"):
        _build_fixture(
            tmp_path / "two_top_level",
            {
                ".ai/tasks/TASK-080.md": (
                    "# TASK-080\n\n"
                    "EXECUTOR_ALLOWED_PATHS_JSON: [\"src/pkg/sub/a.py\"]\n"
                    "EXECUTOR_ALLOWED_PATHS_JSON: [\"loose.py\"]\n"
                )
            },
        )

    # 4. Invariant marker inside fence -> IGNORED
    fixture_fenced_invariant = _build_fixture(
        tmp_path / "fenced_invariant",
        {
            ".ai/tasks/TASK-080.md": (
                "# TASK-080\n\n"
                "```markdown\n"
                "H2_INVARIANT_REFS_JSON: [{\"invariant_id\":\"INV-FAKE\",\"component_path\":\"src/pkg/sub\"}]\n"
                "```\n"
            )
        },
    )
    inv_refs = _relations(fixture_fenced_invariant["result"], H2GraphRelation.TASK_REFERENCES_INVARIANT)
    assert len(inv_refs) == 0

    # 5. REVIEW finding heading inside fence -> IGNORED
    fixture_fenced_review = _build_fixture(
        tmp_path / "fenced_review",
        {
            ".ai/reviews/REVIEW-080.md": (
                "# REVIEW-080\n\n"
                "### B1 — Real finding\n\n"
                "H2_COMPONENT_PATH: loose.py\n\n"
                "Example of finding inside fence:\n"
                "```markdown\n"
                "### B2 — Faked finding heading inside fence\n\n"
                "H2_COMPONENT_PATH: src/pkg/sub/a.py\n"
                "```\n"
            )
        },
    )
    review_findings = _relations(fixture_fenced_review["result"], H2GraphRelation.TASK_HAS_REVIEW_FINDING)
    assert len(review_findings) == 1
    assert review_findings[0].target_node_id.startswith("review-finding:TASK-080:B1:")

    # 6. REVIEW component path inside fence -> IGNORED
    fixture_fenced_path = _build_fixture(
        tmp_path / "fenced_path",
        {
            ".ai/reviews/REVIEW-080.md": (
                "# REVIEW-080\n\n"
                "### B1 — Real finding\n\n"
                "Here is an example:\n"
                "```text\n"
                "H2_COMPONENT_PATH: src/pkg/sub/a.py\n"
                "```\n\n"
                "Actual path:\n"
                "H2_COMPONENT_PATH: loose.py\n"
            )
        },
    )
    finding_rel = _relations(fixture_fenced_path["result"], H2GraphRelation.REVIEW_FINDING_RELATES_TO_COMPONENT)
    assert len(finding_rel) == 1
    assert finding_rel[0].target_node_id == "component:STANDALONE_PYTHON_MODULE:loose.py"


def test_result_review_manifest_crlf_and_lf_handling(tmp_path: Path):
    # LF Result
    lf_body = (
        "# RESULT-080\n\n"
        "## Review Manifest\n\n"
        "```text\n"
        "TASK_ID: TASK-080\n"
        "EXECUTOR_ID: codex\n"
        "STATUS: PASS\n"
        "```\n"
    )
    crlf_body = lf_body.replace("\n", "\r\n")

    # Explicitly write CRLF bytes directly into repository to ensure real CRLF blob
    lf_fixture = _build_fixture(tmp_path / "lf", {".ai/results/RESULT-080.md": lf_body})
    crlf_fixture = _build_fixture(tmp_path / "crlf", {".ai/results/RESULT-080.md": crlf_body})

    lf_exec_edges = _relations(lf_fixture["result"], H2GraphRelation.TASK_EXECUTED_BY_EXECUTOR)
    crlf_exec_edges = _relations(crlf_fixture["result"], H2GraphRelation.TASK_EXECUTED_BY_EXECUTOR)

    assert len(lf_exec_edges) >= 1
    assert len(lf_exec_edges) == len(crlf_exec_edges)
    assert all(
        e.source_node_id == "task:TASK-080" and e.target_node_id == "executor:codex"
        for e in crlf_exec_edges
    )

    # Mismatched TASK_ID in CRLF Result -> FAIL CLOSED
    bad_task_id_crlf = crlf_body.replace("TASK_ID: TASK-080", "TASK_ID: TASK-081")
    with pytest.raises(RepositoryStructuralExperienceGraphConsistencyError, match="TASK_ID does not match RESULT path"):
        _build_fixture(tmp_path / "bad_task_crlf", {".ai/results/RESULT-080.md": bad_task_id_crlf})

    # Duplicate Review Manifest in CRLF Result -> FAIL CLOSED
    dup_manifest_crlf = crlf_body + "\r\n" + crlf_body
    with pytest.raises(RepositoryStructuralExperienceGraphConsistencyError, match="one closed fenced block"):
        _build_fixture(tmp_path / "dup_manifest_crlf", {".ai/results/RESULT-080.md": dup_manifest_crlf})
