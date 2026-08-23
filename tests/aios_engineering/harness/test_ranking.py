"""Tests for pure H2 deterministic relevance ranking and bounded selection."""
from __future__ import annotations

import builtins
import dataclasses
import socket
import subprocess

import pytest

from src.aios_engineering.harness.contracts import (
    EvidenceKind,
    HarnessIntelligencePlan,
    RepositoryEvidenceRef,
    RepositorySnapshotRef,
)
from src.aios_engineering.harness.discovery import (
    DISCOVERED_GIT_BLOB,
    RepositoryDiscoveryResult,
)
from src.aios_engineering.harness.errors import (
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.ranking import (
    H2_RANKING_POLICY_VERSION,
    H2_SELECTION_BOUND,
    H2_TASK_RELEVANCE,
    H2_ZERO_RELEVANCE,
    MAX_EXACT_PATH_HINTS,
    MAX_PATH_PREFIX_HINTS,
    MAX_QUERY_TERMS,
    MAX_QUERY_TERM_LENGTH,
    MAX_SELECTED_EVIDENCE,
    RepositoryRankingResult,
    TaskRelevanceSpec,
    _rank_order_key,
    compute_relevance_spec_fingerprint,
    rank_repository_evidence,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
TREE_A = "e" * 40
TREE_B = "f" * 40


def _evidence(
    path: str,
    blob_sha: str = SHA_A,
    kind: EvidenceKind = EvidenceKind.SOURCE,
    symbol_locator: str | None = None,
) -> RepositoryEvidenceRef:
    return RepositoryEvidenceRef(
        path=path,
        blob_sha=blob_sha,
        evidence_kind=kind,
        reason_code=DISCOVERED_GIT_BLOB,
        priority=0,
        symbol_locator=symbol_locator,
    )


def _discovery(
    *evidence: RepositoryEvidenceRef,
    commit_sha: str = SHA_A,
    tree_sha: str = TREE_A,
) -> RepositoryDiscoveryResult:
    return RepositoryDiscoveryResult.create(
        RepositorySnapshotRef(commit_sha, tree_sha),
        tuple(evidence),
    )


def _spec(**changes: object) -> TaskRelevanceSpec:
    values: dict[str, object] = {
        "task_id": "TASK-072",
        "exact_paths": (),
        "path_prefixes": (),
        "query_terms": ("ranking",),
        "preferred_kinds": (),
        "max_selected": MAX_SELECTED_EVIDENCE,
    }
    values.update(changes)
    return TaskRelevanceSpec(**values)  # type: ignore[arg-type]


def test_valid_spec_is_frozen_and_uses_exact_tuples():
    spec = _spec(
        exact_paths=("src/pkg/ranking.py",),
        path_prefixes=("tests",),
        query_terms=("ranking", "task"),
        preferred_kinds=(EvidenceKind.SOURCE,),
        max_selected=7,
    )
    assert type(spec.exact_paths) is tuple
    assert type(spec.path_prefixes) is tuple
    assert type(spec.query_terms) is tuple
    assert type(spec.preferred_kinds) is tuple
    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.max_selected = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("exact_paths", ["src/a.py"]),
        ("path_prefixes", ["src"]),
        ("query_terms", ["ranking"]),
        ("preferred_kinds", [EvidenceKind.SOURCE]),
        ("query_terms", (term for term in ("ranking",))),
    ],
)
def test_non_tuple_spec_collections_are_rejected(field_name: str, invalid_value: object):
    with pytest.raises(HarnessValidationError, match="exact tuple"):
        _spec(**{field_name: invalid_value})


def test_empty_relevance_spec_is_rejected():
    with pytest.raises(HarnessValidationError, match="at least one"):
        _spec(query_terms=())


@pytest.mark.parametrize(
    ("field_name", "duplicate_value"),
    [
        ("exact_paths", ("src/a.py", "src/a.py")),
        ("path_prefixes", ("src", "src")),
        ("query_terms", ("ranking", "ranking")),
        ("preferred_kinds", (EvidenceKind.SOURCE, EvidenceKind.SOURCE)),
    ],
)
def test_duplicate_relevance_signals_are_rejected(
    field_name: str,
    duplicate_value: tuple[object, ...],
):
    with pytest.raises(HarnessValidationError, match="duplicate"):
        _spec(**{field_name: duplicate_value})


@pytest.mark.parametrize("invalid_term", ["", "UPPER", "two words", "café", "term-name", "a" * 65])
def test_query_term_grammar_and_length_bounds_are_enforced(invalid_term: str):
    with pytest.raises(HarnessValidationError, match="query term"):
        _spec(query_terms=(invalid_term,))


def test_query_term_and_hint_count_bounds_are_enforced():
    with pytest.raises(HarnessValidationError, match="hard limit"):
        _spec(query_terms=tuple(f"term{index}" for index in range(MAX_QUERY_TERMS + 1)))
    with pytest.raises(HarnessValidationError, match="hard limit"):
        _spec(
            exact_paths=tuple(f"src/file{index}.py" for index in range(MAX_EXACT_PATH_HINTS + 1))
        )
    with pytest.raises(HarnessValidationError, match="hard limit"):
        _spec(
            path_prefixes=tuple(f"src/root{index}" for index in range(MAX_PATH_PREFIX_HINTS + 1))
        )
    assert MAX_QUERY_TERM_LENGTH == 64


@pytest.mark.parametrize("invalid_max", [0, 33, True, False, 1.0, "1"])
def test_max_selected_zero_33_bool_and_non_int_are_rejected(invalid_max: object):
    with pytest.raises(HarnessValidationError, match="max_selected"):
        _spec(max_selected=invalid_max)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("exact_paths", ("../escape.py",)),
        ("path_prefixes", ("src/../escape",)),
        ("preferred_kinds", ("SOURCE",)),
    ],
)
def test_paths_prefixes_and_preferred_kinds_fail_closed(
    field_name: str,
    invalid_value: tuple[object, ...],
):
    with pytest.raises(HarnessValidationError):
        _spec(**{field_name: invalid_value})


def test_exact_path_score_contributes_600():
    discovery = _discovery(_evidence("src/pkg/ranking.py"))
    result, _ = rank_repository_evidence(
        discovery,
        _spec(exact_paths=("src/pkg/ranking.py",), query_terms=()),
    )
    assert result.plan.selected_evidence[0].priority == 600


def test_prefix_score_contributes_300_and_obeys_segment_boundaries():
    discovery = _discovery(
        _evidence("src/pkg/a.py", SHA_A),
        _evidence("src-other/b.py", SHA_B),
    )
    result, _ = rank_repository_evidence(
        discovery,
        _spec(path_prefixes=("src",), query_terms=()),
    )
    assert [(item.path, item.priority) for item in result.plan.selected_evidence] == [
        ("src/pkg/a.py", 300)
    ]
    assert result.plan.excluded_evidence[0].evidence.path == "src-other/b.py"


def test_query_term_score_is_30_each_and_capped_at_180():
    discovery = _discovery(
        _evidence("src/alpha-beta.py", SHA_A),
        _evidence("src/alpha-beta-gamma-delta-epsilon-zeta-eta.py", SHA_B),
    )
    result, _ = rank_repository_evidence(
        discovery,
        _spec(
            query_terms=("alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta")
        ),
    )
    priorities = {item.path: item.priority for item in result.plan.selected_evidence}
    assert priorities["src/alpha-beta.py"] == 60
    assert priorities["src/alpha-beta-gamma-delta-epsilon-zeta-eta.py"] == 180


def test_path_tokenization_is_explicit_ascii_and_case_insensitive_for_ascii_paths():
    discovery = _discovery(
        _evidence("SRC/My_Ranking-Test.PY", SHA_A),
        _evidence("src/café.py", SHA_B),
    )
    result, _ = rank_repository_evidence(
        discovery,
        _spec(query_terms=("src", "my", "ranking", "test", "caf")),
    )
    priorities = {item.path: item.priority for item in result.plan.selected_evidence}
    assert priorities["SRC/My_Ranking-Test.PY"] == 120
    assert priorities["src/café.py"] == 60


def test_preferred_kind_score_contributes_100():
    discovery = _discovery(_evidence("assets/data.bin", kind=EvidenceKind.OTHER))
    result, _ = rank_repository_evidence(
        discovery,
        _spec(query_terms=(), preferred_kinds=(EvidenceKind.OTHER,)),
    )
    assert result.plan.selected_evidence[0].priority == 100


def test_combined_score_is_clamped_to_1000():
    path = "src/alpha-beta-gamma-delta-epsilon-zeta.py"
    discovery = _discovery(_evidence(path, kind=EvidenceKind.SOURCE))
    result, _ = rank_repository_evidence(
        discovery,
        _spec(
            exact_paths=(path,),
            path_prefixes=("src",),
            query_terms=("alpha", "beta", "gamma", "delta", "epsilon", "zeta"),
            preferred_kinds=(EvidenceKind.SOURCE,),
        ),
    )
    assert result.plan.selected_evidence[0].priority == 1000


def test_zero_relevance_is_never_selected():
    discovery = _discovery(_evidence("src/unmatched.py"))
    result, _ = rank_repository_evidence(discovery, _spec(query_terms=("ranking",)))
    assert result.plan.selected_evidence == ()
    assert len(result.plan.excluded_evidence) == 1
    assert result.plan.excluded_evidence[0].reason_code == H2_ZERO_RELEVANCE
    assert result.plan.excluded_evidence[0].evidence.priority == 0


def test_max_selected_is_enforced_with_positive_overflow_accounted():
    discovery = _discovery(
        _evidence("src/a.py", SHA_A),
        _evidence("src/b.py", SHA_B),
        _evidence("src/c.py", SHA_C),
    )
    result, _ = rank_repository_evidence(
        discovery,
        _spec(query_terms=(), preferred_kinds=(EvidenceKind.SOURCE,), max_selected=2),
    )
    assert [item.path for item in result.plan.selected_evidence] == ["src/a.py", "src/b.py"]
    assert result.plan.excluded_evidence[0].evidence.path == "src/c.py"
    assert result.plan.excluded_evidence[0].reason_code == H2_SELECTION_BOUND


def test_tie_break_is_path_then_blob_and_is_deterministic():
    evidence = [
        RepositoryEvidenceRef("same", SHA_B, EvidenceKind.OTHER, H2_TASK_RELEVANCE, 100),
        RepositoryEvidenceRef("z.py", SHA_A, EvidenceKind.SOURCE, H2_TASK_RELEVANCE, 100),
        RepositoryEvidenceRef("a.py", SHA_C, EvidenceKind.SOURCE, H2_TASK_RELEVANCE, 100),
        RepositoryEvidenceRef("same", SHA_A, EvidenceKind.OTHER, H2_TASK_RELEVANCE, 100),
    ]
    assert [(item.path, item.blob_sha) for item in sorted(evidence, key=_rank_order_key)] == [
        ("a.py", SHA_C),
        ("same", SHA_A),
        ("same", SHA_B),
        ("z.py", SHA_A),
    ]


def test_every_h1_candidate_is_accounted_exactly_once_and_h1_is_not_mutated():
    original_items = (
        _evidence("src/ranking.py", SHA_A, EvidenceKind.SOURCE, "class:Ranker"),
        _evidence("tests/test_other.py", SHA_B, EvidenceKind.TEST),
        _evidence("docs/guide.md", SHA_C, EvidenceKind.DOCUMENTATION),
    )
    discovery = _discovery(*original_items)
    before = discovery.to_dict()
    result, _ = rank_repository_evidence(discovery, _spec(query_terms=("ranking",), max_selected=1))
    accounted = [*result.plan.selected_evidence]
    accounted.extend(item.evidence for item in result.plan.excluded_evidence)
    assert len(accounted) == len(original_items)
    assert {item.path for item in accounted} == {item.path for item in original_items}
    assert len({(item.path, item.blob_sha) for item in accounted}) == len(original_items)
    assert all(item.reason_code == H2_TASK_RELEVANCE for item in accounted)
    assert accounted[0].symbol_locator == "class:Ranker"
    assert discovery.to_dict() == before
    assert all(ranked is not original for ranked in accounted for original in original_items)


def test_h0_plan_is_reused_and_selected_order_is_score_descending():
    discovery = _discovery(
        _evidence("src/ranking.py", SHA_A),
        _evidence("src/other.py", SHA_B),
        _evidence("tests/ranking.py", SHA_C, EvidenceKind.TEST),
    )
    result, _ = rank_repository_evidence(
        discovery,
        _spec(
            exact_paths=("src/ranking.py",),
            query_terms=("ranking",),
            preferred_kinds=(EvidenceKind.TEST,),
        ),
    )
    assert type(result.plan) is HarnessIntelligencePlan
    assert [item.priority for item in result.plan.selected_evidence] == [630, 130]


def test_h0_plan_fingerprint_is_selected_rank_sensitive():
    discovery = _discovery(
        _evidence("src/a.py", SHA_A),
        _evidence("src/b.py", SHA_B),
    )
    result, _ = rank_repository_evidence(
        discovery,
        _spec(query_terms=(), preferred_kinds=(EvidenceKind.SOURCE,)),
    )
    reversed_plan = HarnessIntelligencePlan.create(
        task_id=result.task_id,
        snapshot=result.plan.snapshot,
        selected_evidence=tuple(reversed(result.plan.selected_evidence)),
        excluded_evidence=result.plan.excluded_evidence,
    )
    assert reversed_plan.plan_fingerprint != result.plan.plan_fingerprint


def test_spec_and_ranking_fingerprints_are_deterministic():
    discovery = _discovery(_evidence("src/ranking.py"))
    spec = _spec(query_terms=("ranking",))
    first, first_receipt = rank_repository_evidence(discovery, spec)
    second, second_receipt = rank_repository_evidence(discovery, spec)
    assert compute_relevance_spec_fingerprint(spec) == first.relevance_spec_fingerprint
    assert first == second
    assert first_receipt == second_receipt


def test_discovery_fingerprint_change_changes_ranking_binding():
    evidence = _evidence("src/ranking.py")
    first, _ = rank_repository_evidence(
        _discovery(evidence, commit_sha=SHA_A, tree_sha=TREE_A),
        _spec(),
    )
    second, _ = rank_repository_evidence(
        _discovery(evidence, commit_sha=SHA_D, tree_sha=TREE_B),
        _spec(),
    )
    assert first.plan.selected_evidence == second.plan.selected_evidence
    assert first.discovery_fingerprint != second.discovery_fingerprint
    assert first.ranking_fingerprint != second.ranking_fingerprint


def test_spec_change_changes_ranking_binding():
    discovery = _discovery(_evidence("src/ranking.py"))
    first, _ = rank_repository_evidence(discovery, _spec(query_terms=("ranking",)))
    second, _ = rank_repository_evidence(discovery, _spec(query_terms=("src",)))
    assert first.relevance_spec_fingerprint != second.relevance_spec_fingerprint
    assert first.ranking_fingerprint != second.ranking_fingerprint


def test_result_is_frozen_and_fingerprint_tampering_fails_closed():
    result, _ = rank_repository_evidence(
        _discovery(_evidence("src/ranking.py")),
        _spec(),
    )
    assert isinstance(result, RepositoryRankingResult)
    assert result.policy_version == H2_RANKING_POLICY_VERSION
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.task_id = "TASK-999"  # type: ignore[misc]
    with pytest.raises(HarnessFingerprintError, match="Ranking fingerprint mismatch"):
        dataclasses.replace(result, ranking_fingerprint="0" * 64)


def test_non_h1_discovery_input_is_rejected():
    with pytest.raises(HarnessValidationError, match="RepositoryDiscoveryResult"):
        rank_repository_evidence(object(), _spec())  # type: ignore[arg-type]


def test_receipt_counts_and_zero_authority_flags_are_exact():
    discovery = _discovery(
        _evidence("src/ranking.py", SHA_A),
        _evidence("src/other.py", SHA_B),
        _evidence("tests/other.py", SHA_C, EvidenceKind.TEST),
    )
    result, receipt = rank_repository_evidence(
        discovery,
        _spec(query_terms=("ranking",)),
    )
    assert receipt.generator_version == H2_RANKING_POLICY_VERSION
    assert receipt.candidate_count == 3
    assert receipt.selected_count == 1
    assert receipt.excluded_count == 2
    assert receipt.candidate_count == receipt.selected_count + receipt.excluded_count
    assert receipt.output_fingerprint == result.ranking_fingerprint
    assert receipt.authority_created is False
    assert receipt.network_used is False
    assert receipt.llm_used is False
    assert receipt.paid_api_used is False


def test_ranking_uses_no_git_subprocess_network_or_worktree_bytes(
    monkeypatch: pytest.MonkeyPatch,
):
    discovery = _discovery(_evidence("src/ranking.py"))

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("forbidden side effect attempted")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    result, receipt = rank_repository_evidence(discovery, _spec())
    assert result.plan.selected_evidence[0].path == "src/ranking.py"
    assert receipt.network_used is False

