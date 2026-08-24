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
    H2GraphEdge,
    H2GraphNode,
    H2GraphNodeKind,
    H2GraphRelation,
    H3MustNotOwn,
    H3_MUST_NOT_OWN_DEFAULT,
    H3_ROLE_TENDENCY_POLICY_VERSION,
    H3_ROLE_TENDENCY_SCHEMA_VERSION,
    HarnessFingerprintError,
    HarnessValidationError,
    MAX_H3_COMPONENT_OBSERVATIONS_PER_EXECUTOR,
    MAX_H3_COMPONENT_RELATIONSHIPS,
    MAX_H3_COMPONENT_SUMMARIES,
    MAX_H3_EXECUTOR_PROFILES,
    MAX_H3_FINGERPRINT_PAYLOAD_BYTES,
    MAX_H3_MEMBER_FILES_PER_COMPONENT,
    MAX_H3_OBSERVED_TASKS_PER_EXECUTOR,
    MAX_H3_REVIEW_FINDINGS_PER_EXECUTOR,
    MAX_H3_ROLES_PER_COMPONENT,
    MAX_H3_SYMBOLS_PER_COMPONENT,
    MAX_H3_UNOBSERVED_ROLE_FILES,
    RepositoryRoleTendencyBoundError,
    RepositoryRoleTendencyConsistencyError,
    RepositoryRoleTendencyResult,
    RepositorySnapshotRef,
    RepositoryStructuralExperienceGraphResult,
    StructuralComponentKind,
    TaskRelevanceSpec,
    build_repository_dependency_graph,
    build_repository_experience_manifest,
    build_repository_structural_experience_graph,
    canonical_json_bytes,
    compute_sha256,
    discover_control_plane_experience,
    discover_repository_snapshot,
    rank_repository_evidence,
    summarize_repository_roles,
    summarize_repository_roles_and_executor_tendencies,
)
from src.aios_engineering.harness.structural_experience_graph import (
    _bounded_fingerprint,
    _graph_edge_order_key,
    _node_order_key,
    _result_payload as _h2_result_payload,
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


def test_no_business_domain_role_inference_with_misleading_paths(tmp_path: Path):
    # Create files with misleading business domain names
    domain_files = {
        "src/billing/payment_processor.py": "def process(): pass\n",
        "src/bridge/authority.py": "def run(): pass\n",
        "src/agent/executor_dispatch.py": "def dispatch(): pass\n",
        "src/product/order_manager.py": "def manage(): pass\n",
    }
    fixture = _build_fixture(tmp_path, domain_files)
    result = fixture["result"]

    # Verify all components only receive technical artifact roles and fixed H3 negative boundaries
    for comp in result.component_summaries:
        assert comp.must_not_own == H3_MUST_NOT_OWN_DEFAULT
        for role in comp.observed_roles:
            assert isinstance(role, ArtifactRole)
        # Ensure no manufactured domain properties
        assert not hasattr(comp, "domain_ownership")
        assert not hasattr(comp, "business_concept")
        assert not hasattr(comp, "business_function")


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
    # Construct exact synthetic H2 input containing TWO valid TASK_EXECUTED_BY_EXECUTOR
    # observations for the EXACT SAME TASK (TASK-081)
    fixture = _build_fixture(tmp_path)
    h2_graph = fixture["h2_graph"]
    roles = fixture["roles"]

    codex_node = H2GraphNode.create(
        node_id="executor:codex",
        kind=H2GraphNodeKind.EXECUTOR,
        identity="executor:codex",
        evidence_fingerprint=compute_sha256(canonical_json_bytes({"executor_id": "codex"})),
    )
    codex_edge = H2GraphEdge.create(
        source_node_id="task:TASK-081",
        target_node_id="executor:codex",
        relation=H2GraphRelation.TASK_EXECUTED_BY_EXECUTOR,
        evidence_path=".ai/results/RESULT-081-codex.md",
        evidence_blob_sha="0" * 40,
        evidence_fingerprint="0" * 64,
    )
    sorted_nodes = tuple(sorted((*h2_graph.nodes, codex_node), key=_node_order_key))
    sorted_edges = tuple(sorted((*h2_graph.edges, codex_edge), key=_graph_edge_order_key))

    payload = _h2_result_payload(
        task_id=h2_graph.task_id,
        repository_snapshot=h2_graph.repository_snapshot,
        control_plane_snapshot=h2_graph.control_plane_snapshot,
        discovery_fingerprint=h2_graph.discovery_fingerprint,
        candidate_set_fingerprint=h2_graph.candidate_set_fingerprint,
        experience_manifest_fingerprint=h2_graph.experience_manifest_fingerprint,
        ranking_fingerprint=h2_graph.ranking_fingerprint,
        relevance_spec_fingerprint=h2_graph.relevance_spec_fingerprint,
        role_summary_fingerprint=h2_graph.role_summary_fingerprint,
        import_graph_fingerprint=h2_graph.import_graph_fingerprint,
        components=h2_graph.components,
        symbols=h2_graph.symbols,
        nodes=sorted_nodes,
        edges=sorted_edges,
        unresolved_records=h2_graph.unresolved_records,
        authority_created=False,
    )
    multi_h2_graph = RepositoryStructuralExperienceGraphResult(
        task_id=h2_graph.task_id,
        repository_snapshot=h2_graph.repository_snapshot,
        control_plane_snapshot=h2_graph.control_plane_snapshot,
        discovery_fingerprint=h2_graph.discovery_fingerprint,
        candidate_set_fingerprint=h2_graph.candidate_set_fingerprint,
        experience_manifest_fingerprint=h2_graph.experience_manifest_fingerprint,
        ranking_fingerprint=h2_graph.ranking_fingerprint,
        relevance_spec_fingerprint=h2_graph.relevance_spec_fingerprint,
        role_summary_fingerprint=h2_graph.role_summary_fingerprint,
        import_graph_fingerprint=h2_graph.import_graph_fingerprint,
        components=h2_graph.components,
        symbols=h2_graph.symbols,
        nodes=sorted_nodes,
        edges=sorted_edges,
        unresolved_records=h2_graph.unresolved_records,
        graph_fingerprint=_bounded_fingerprint(payload),
    )

    res, receipt = summarize_repository_roles_and_executor_tendencies(multi_h2_graph, roles)

    # 1. Both executor profiles are preserved
    assert len(res.executor_profiles) == 2
    prof_map = {p.executor_id: p for p in res.executor_profiles}
    assert set(prof_map.keys()) == {"antigravity", "codex"}

    # 2. The exact same task appears in BOTH profiles
    assert prof_map["antigravity"].observed_tasks == ("TASK-081",)
    assert prof_map["codex"].observed_tasks == ("TASK-081",)
    assert prof_map["antigravity"].observed_task_count == 1
    assert prof_map["codex"].observed_task_count == 1

    # 3. Component & review finding co-observations appear in both profiles
    assert prof_map["antigravity"].coobserved_component_ids == prof_map["codex"].coobserved_component_ids
    assert prof_map["antigravity"].coobserved_review_finding_ids == prof_map["codex"].coobserved_review_finding_ids

    # 4. Absolutely no preferred executor or routing authority
    for p in res.executor_profiles:
        assert not hasattr(p, "preferred_executor")
        assert not hasattr(p, "routing_score")
        assert not hasattr(p, "winner")
        assert not hasattr(p, "quality_grade")


def test_no_executor_edge_produces_no_executor_profiles(tmp_path: Path):
    # Overwrite RESULT-081 with no review manifest
    fixture = _build_fixture(
        tmp_path,
        {".ai/results/RESULT-081.md": "# RESULT-081\n\nNo manifest here.\n"},
    )
    result = fixture["result"]
    assert len(result.executor_profiles) == 0


def test_order_independence(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]

    # 1. Component summaries order permutation in Result
    reversed_comps = tuple(reversed(result.component_summaries))
    res_permuted_comps = RepositoryRoleTendencyResult.create(
        snapshot=result.snapshot,
        h2_graph_fingerprint=result.h2_graph_fingerprint,
        role_summary_fingerprint=result.role_summary_fingerprint,
        component_summaries=reversed_comps,
        executor_profiles=result.executor_profiles,
        unobserved_role_file_count=result.unobserved_role_file_count,
    )
    assert res_permuted_comps.component_summaries == result.component_summaries
    assert res_permuted_comps.result_fingerprint == result.result_fingerprint

    # 2. Member files order permutation in ComponentRoleSummary
    first_comp = result.component_summaries[0]
    if len(first_comp.member_files) > 1:
        reversed_files = tuple(reversed(first_comp.member_files))
        comp_permuted_files = ComponentRoleSummary.create(
            component_id=first_comp.component_id,
            path=first_comp.path,
            kind=first_comp.kind,
            member_files=reversed_files,
            observed_roles=first_comp.observed_roles,
            symbol_count=first_comp.symbol_count,
            inbound_component_count=first_comp.inbound_component_count,
            outbound_component_count=first_comp.outbound_component_count,
        )
        assert comp_permuted_files.member_files == first_comp.member_files
        assert comp_permuted_files.summary_fingerprint == first_comp.summary_fingerprint

    # 3. Tasks / components / findings permutation in ExecutorTendencyProfile
    prof = result.executor_profiles[0]
    prof_permuted = ExecutorTendencyProfile.create(
        executor_id=prof.executor_id,
        observed_tasks=tuple(reversed(prof.observed_tasks)),
        component_observations=tuple(reversed(prof.component_observations)),
        coobserved_review_finding_ids=tuple(reversed(prof.coobserved_review_finding_ids)),
    )
    assert prof_permuted.observed_tasks == prof.observed_tasks
    assert prof_permuted.component_observations == prof.component_observations
    assert prof_permuted.coobserved_review_finding_ids == prof.coobserved_review_finding_ids
    assert prof_permuted.profile_fingerprint == prof.profile_fingerprint


def test_duplicate_identity_rejection(tmp_path: Path):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]
    comp = result.component_summaries[0]
    prof = result.executor_profiles[0]
    dup_file = comp.member_files[0]
    obs = prof.component_observations[0]

    # --- 1. Direct dataclass replace duplicates ---
    with pytest.raises(HarnessValidationError, match="duplicate member file path"):
        replace(comp, member_files=(dup_file, dup_file))

    with pytest.raises(HarnessValidationError, match="duplicate observed role"):
        replace(comp, observed_roles=(ArtifactRole.SOURCE_IMPLEMENTATION, ArtifactRole.SOURCE_IMPLEMENTATION))

    with pytest.raises(HarnessValidationError, match="duplicate observed task"):
        replace(prof, observed_tasks=("TASK-081", "TASK-081"), observed_task_count=2)

    with pytest.raises(HarnessValidationError, match="duplicate component observation"):
        replace(
            prof,
            component_observations=(obs, obs),
            coobserved_component_ids=(obs.component_id, obs.component_id),
        )

    with pytest.raises(HarnessValidationError, match="duplicate finding ID"):
        replace(
            prof,
            coobserved_review_finding_ids=("review-finding:1", "review-finding:1"),
            coobserved_review_finding_count=2,
        )

    with pytest.raises(HarnessValidationError, match="duplicate component summary"):
        replace(result, component_summaries=(comp, comp))

    with pytest.raises(HarnessValidationError, match="duplicate executor profile"):
        replace(result, executor_profiles=(prof, prof))

    # --- 2. Public factory create(...) duplicate fail-closed checks ---
    with pytest.raises(HarnessValidationError, match="duplicate member file path"):
        ComponentRoleSummary.create(
            component_id=comp.component_id,
            path=comp.path,
            kind=comp.kind,
            member_files=(dup_file, dup_file),
            observed_roles=(),
            symbol_count=0,
            inbound_component_count=0,
            outbound_component_count=0,
        )

    with pytest.raises(HarnessValidationError, match="duplicate observed role"):
        ComponentRoleSummary.create(
            component_id=comp.component_id,
            path=comp.path,
            kind=comp.kind,
            member_files=(dup_file,),
            observed_roles=(ArtifactRole.SOURCE_IMPLEMENTATION, ArtifactRole.SOURCE_IMPLEMENTATION),
            symbol_count=0,
            inbound_component_count=0,
            outbound_component_count=0,
        )

    with pytest.raises(HarnessValidationError, match="duplicate observed task"):
        ExecutorTendencyProfile.create(
            executor_id=prof.executor_id,
            observed_tasks=("TASK-081", "TASK-081"),
            component_observations=(),
            coobserved_review_finding_ids=(),
        )

    with pytest.raises(HarnessValidationError, match="duplicate component observation"):
        ExecutorTendencyProfile.create(
            executor_id=prof.executor_id,
            observed_tasks=("TASK-081",),
            component_observations=(obs, obs),
            coobserved_review_finding_ids=(),
        )

    with pytest.raises(HarnessValidationError, match="duplicate finding ID"):
        ExecutorTendencyProfile.create(
            executor_id=prof.executor_id,
            observed_tasks=("TASK-081",),
            component_observations=(),
            coobserved_review_finding_ids=("review-finding:1", "review-finding:1"),
        )

    with pytest.raises(HarnessValidationError, match="duplicate component summary"):
        RepositoryRoleTendencyResult.create(
            snapshot=result.snapshot,
            h2_graph_fingerprint=result.h2_graph_fingerprint,
            role_summary_fingerprint=result.role_summary_fingerprint,
            component_summaries=(comp, comp),
            executor_profiles=result.executor_profiles,
            unobserved_role_file_count=0,
        )

    with pytest.raises(HarnessValidationError, match="duplicate executor profile"):
        RepositoryRoleTendencyResult.create(
            snapshot=result.snapshot,
            h2_graph_fingerprint=result.h2_graph_fingerprint,
            role_summary_fingerprint=result.role_summary_fingerprint,
            component_summaries=result.component_summaries,
            executor_profiles=(prof, prof),
            unobserved_role_file_count=0,
        )


def test_all_hard_bounds_and_bool_as_int_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    fixture = _build_fixture(tmp_path)
    result = fixture["result"]
    comp = result.component_summaries[0]
    prof = result.executor_profiles[0]

    # 1. Bool as int rejection on all scalar fields
    with pytest.raises(HarnessValidationError, match="symbol_count must be an exact integer, not bool"):
        replace(comp, symbol_count=True)  # type: ignore[arg-type]

    with pytest.raises(HarnessValidationError, match="inbound_component_count must be an exact integer, not bool"):
        replace(comp, inbound_component_count=True)  # type: ignore[arg-type]

    with pytest.raises(HarnessValidationError, match="outbound_component_count must be an exact integer, not bool"):
        replace(comp, outbound_component_count=True)  # type: ignore[arg-type]

    with pytest.raises(HarnessValidationError, match="coobserved_task_count must be an exact integer, not bool"):
        ExecutorComponentObservation(component_id="component:PYTHON_PACKAGE:pkg", coobserved_task_count=True)  # type: ignore[arg-type]

    with pytest.raises(HarnessValidationError, match="unobserved_role_file_count must be an exact integer, not bool"):
        replace(result, unobserved_role_file_count=True)  # type: ignore[arg-type]

    # 2. Negative int rejection on all scalar fields
    with pytest.raises(HarnessValidationError, match="symbol_count must be >= 0"):
        replace(comp, symbol_count=-1)

    with pytest.raises(HarnessValidationError, match="inbound_component_count must be >= 0"):
        replace(comp, inbound_component_count=-1)

    with pytest.raises(HarnessValidationError, match="outbound_component_count must be >= 0"):
        replace(comp, outbound_component_count=-1)

    with pytest.raises(HarnessValidationError, match="coobserved_task_count must be >= 1"):
        ExecutorComponentObservation(component_id="component:PYTHON_PACKAGE:pkg", coobserved_task_count=0)

    with pytest.raises(HarnessValidationError, match="unobserved_role_file_count must be >= 0"):
        replace(result, unobserved_role_file_count=-1)

    # 3. Scalar overflow limits
    with pytest.raises(RepositoryRoleTendencyBoundError, match="symbol_count .* exceeds hard limit"):
        replace(comp, symbol_count=MAX_H3_SYMBOLS_PER_COMPONENT + 1)

    with pytest.raises(RepositoryRoleTendencyBoundError, match="inbound_component_count .* exceeds hard limit"):
        replace(comp, inbound_component_count=MAX_H3_COMPONENT_RELATIONSHIPS + 1)

    with pytest.raises(RepositoryRoleTendencyBoundError, match="outbound_component_count .* exceeds hard limit"):
        replace(comp, outbound_component_count=MAX_H3_COMPONENT_RELATIONSHIPS + 1)

    with pytest.raises(RepositoryRoleTendencyBoundError, match="coobserved_task_count .* exceeds hard limit"):
        ExecutorComponentObservation(
            component_id="component:PYTHON_PACKAGE:pkg",
            coobserved_task_count=MAX_H3_OBSERVED_TASKS_PER_EXECUTOR + 1,
        )

    with pytest.raises(RepositoryRoleTendencyBoundError, match="unobserved_role_file_count .* exceeds hard limit"):
        replace(result, unobserved_role_file_count=MAX_H3_UNOBSERVED_ROLE_FILES + 1)

    # 4. Invariant: coobserved_task_count <= observed_task_count inside ExecutorTendencyProfile
    big_obs = ExecutorComponentObservation(component_id="component:PYTHON_PACKAGE:pkg", coobserved_task_count=2)
    with pytest.raises(HarnessValidationError, match="cannot exceed"):
        replace(prof, component_observations=(big_obs,), coobserved_component_ids=(big_obs.component_id,))

    # 5. Boundary & overflow test for EVERY hard-bound family:
    # A. MAX_H3_COMPONENT_SUMMARIES
    with monkeypatch.context() as m:
        m.setattr(role_tendencies_module, "MAX_H3_COMPONENT_SUMMARIES", 1)
        with pytest.raises(RepositoryRoleTendencyBoundError, match="component_summaries exceeds hard limit"):
            replace(result, component_summaries=(result.component_summaries[0], result.component_summaries[1]))

    # B. MAX_H3_MEMBER_FILES_PER_COMPONENT
    with monkeypatch.context() as m:
        m.setattr(role_tendencies_module, "MAX_H3_MEMBER_FILES_PER_COMPONENT", 1)
        with pytest.raises(RepositoryRoleTendencyBoundError, match="member file count .* exceeds hard limit"):
            ComponentRoleSummary.create(
                component_id=comp.component_id,
                path=comp.path,
                kind=comp.kind,
                member_files=(
                    ComponentMemberFile(path="src/a.py", blob_sha="a" * 40, observed_role=None),
                    ComponentMemberFile(path="src/b.py", blob_sha="b" * 40, observed_role=None),
                ),
                observed_roles=(),
                symbol_count=0,
                inbound_component_count=0,
                outbound_component_count=0,
            )

    # C. MAX_H3_ROLES_PER_COMPONENT
    with monkeypatch.context() as m:
        m.setattr(role_tendencies_module, "MAX_H3_ROLES_PER_COMPONENT", 1)
        with pytest.raises(RepositoryRoleTendencyBoundError, match="observed roles count .* exceeds hard limit"):
            ComponentRoleSummary.create(
                component_id=comp.component_id,
                path=comp.path,
                kind=comp.kind,
                member_files=(comp.member_files[0],),
                observed_roles=(ArtifactRole.SOURCE_IMPLEMENTATION, ArtifactRole.EXECUTABLE_ENTRYPOINT),
                symbol_count=0,
                inbound_component_count=0,
                outbound_component_count=0,
            )

    # D. MAX_H3_EXECUTOR_PROFILES
    with monkeypatch.context() as m:
        m.setattr(role_tendencies_module, "MAX_H3_EXECUTOR_PROFILES", 1)
        prof2 = ExecutorTendencyProfile.create(
            executor_id="codex",
            observed_tasks=("TASK-081",),
            component_observations=(),
            coobserved_review_finding_ids=(),
        )
        with pytest.raises(RepositoryRoleTendencyBoundError, match="executor_profiles exceeds hard limit"):
            replace(result, executor_profiles=(prof, prof2))

    # E. MAX_H3_OBSERVED_TASKS_PER_EXECUTOR
    with monkeypatch.context() as m:
        m.setattr(role_tendencies_module, "MAX_H3_OBSERVED_TASKS_PER_EXECUTOR", 1)
        with pytest.raises(RepositoryRoleTendencyBoundError, match="observed_task_count .* exceeds hard limit"):
            replace(prof, observed_tasks=("TASK-081", "TASK-082"), observed_task_count=2)

    # F. MAX_H3_COMPONENT_OBSERVATIONS_PER_EXECUTOR
    with monkeypatch.context() as m:
        m.setattr(role_tendencies_module, "MAX_H3_COMPONENT_OBSERVATIONS_PER_EXECUTOR", 1)
        obs1 = ExecutorComponentObservation(component_id="component:PYTHON_PACKAGE:a", coobserved_task_count=1)
        obs2 = ExecutorComponentObservation(component_id="component:PYTHON_PACKAGE:b", coobserved_task_count=1)
        with pytest.raises(RepositoryRoleTendencyBoundError, match="component_observations count exceeds hard limit"):
            replace(prof, component_observations=(obs1, obs2), coobserved_component_ids=(obs1.component_id, obs2.component_id))

    # G. MAX_H3_REVIEW_FINDINGS_PER_EXECUTOR
    with monkeypatch.context() as m:
        m.setattr(role_tendencies_module, "MAX_H3_REVIEW_FINDINGS_PER_EXECUTOR", 1)
        with pytest.raises(RepositoryRoleTendencyBoundError, match="coobserved_review_finding_count .* exceeds hard limit"):
            replace(
                prof,
                coobserved_review_finding_ids=("review-finding:1", "review-finding:2"),
                coobserved_review_finding_count=2,
            )

    # H. MAX_H3_FINGERPRINT_PAYLOAD_BYTES
    with monkeypatch.context() as m:
        m.setattr(role_tendencies_module, "MAX_H3_FINGERPRINT_PAYLOAD_BYTES", 10)
        with pytest.raises(RepositoryRoleTendencyBoundError, match="payload bytes .* exceeds hard limit"):
            role_tendencies_module._bounded_fingerprint({"key": "a_long_value_that_exceeds_10_bytes"})


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
