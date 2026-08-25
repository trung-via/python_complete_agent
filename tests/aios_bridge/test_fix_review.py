import hashlib
import json

import pytest

import bridge
from src.aios_bridge.fix_review import (
    FIX_CONTEXT_PACK_MARKER,
    FixContextPack,
    FixReviewContractError,
    FixReviewMode,
    analyze_fix_impact,
    canonical_proof_fingerprint,
    delta_impact_evidence,
    parse_fix_context_pack,
    parse_fix_review_mode,
    render_fix_executor_context,
)


HEAD = "a" * 40
BLOB_A = "1" * 40
BLOB_B = "2" * 40
BLOB_C = "3" * 40
EVIDENCE = "e" * 64


def fingerprint(evidence):
    return canonical_proof_fingerprint(evidence)


def pack_data(**overrides):
    values = {
        "schema_version": "1",
        "previous_reviewed_head_sha": HEAD,
        "impact_confidence": "KNOWN",
        "open_finding_ids": ["finding-1"],
        "affected_paths": ["src/fix.py", "src/subject.py", "src/dependency.py"],
        "protected_accepted_paths": ["src/subject.py", "src/dependency.py"],
        "required_test_paths": ["tests/test_fix.py"],
        "unknown_impact_fallback_test_paths": ["tests/test_fallback.py"],
        "proof_bindings": [
            {
                "proof_id": "proof-1",
                "subject": "accepted subject",
                "subject_paths": ["src/subject.py"],
                "dependency_paths": ["src/dependency.py"],
                "subject_fingerprint": fingerprint({"src/subject.py": BLOB_A}),
                "dependency_fingerprint": fingerprint({"src/dependency.py": BLOB_B}),
                "evidence_fingerprint": EVIDENCE,
                "source_review_round": 2,
                "status": "VALID",
                "test_paths": ["tests/test_proof.py"],
            }
        ],
    }
    values.update(overrides)
    return values


def pack(**overrides):
    return FixContextPack.from_dict(pack_data(**overrides))


def resolver(values):
    return lambda _head, path: values.get(path)


def review(payload=None, *, mode="PROOF_REUSE_DELTA_IMPACT", head=HEAD):
    payload = pack_data() if payload is None else payload
    return (
        "# REVIEW-091\n"
        "STATUS: CHANGES_REQUIRED\n"
        f"REVIEWED_TASK_HEAD_SHA: {head}\n"
        f"FIX_REVIEW_MODE: {mode}\n"
        f"{FIX_CONTEXT_PACK_MARKER} "
        + json.dumps(payload, sort_keys=True, separators=(",", ":"))
        + "\n"
    )


def test_fix_mode_missing_is_compatible_and_exact_opt_in_activates():
    assert parse_fix_review_mode("STATUS: CHANGES_REQUIRED\n") is FixReviewMode.COMPATIBILITY
    assert parse_fix_review_mode(review()) is FixReviewMode.PROOF_REUSE_DELTA_IMPACT


@pytest.mark.parametrize(
    "content",
    (
        "FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT\nFIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT\n",
        "FIX_REVIEW_MODE: FUTURE_MODE\n",
    ),
)
def test_fix_mode_duplicate_or_unknown_fails_closed(content):
    with pytest.raises(FixReviewContractError):
        parse_fix_review_mode(content)


def test_fenced_fix_mode_example_does_not_activate():
    content = "```text\nFIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT\n```\n"
    assert parse_fix_review_mode(content) is FixReviewMode.COMPATIBILITY


def test_shorter_inner_fence_does_not_close_valid_outer_fence():
    content = (
        "````markdown\n"
        "```text\n"
        "FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT\n"
        f"{FIX_CONTEXT_PACK_MARKER} {{}}\n"
        "```\n"
        "````\n"
    )
    assert parse_fix_review_mode(content) is FixReviewMode.COMPATIBILITY
    assert parse_fix_context_pack(content, reviewed_task_head_sha=HEAD) is None


def test_fix_pack_is_strict_bounded_and_round_trips():
    parsed = parse_fix_context_pack(review(), reviewed_task_head_sha=HEAD)
    assert parsed == pack()
    assert FixContextPack.from_dict(parsed.to_dict()) == parsed
    malformed = pack_data(extra="not-closed")
    with pytest.raises(FixReviewContractError, match="exact bounded field set"):
        parse_fix_context_pack(review(malformed), reviewed_task_head_sha=HEAD)


def test_fix_pack_previous_head_must_match_review_header():
    with pytest.raises(FixReviewContractError, match="does not match"):
        parse_fix_context_pack(review(), reviewed_task_head_sha="b" * 40)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("affected_paths", ["src/../escape.py"]),
        ("protected_accepted_paths", [".git/config"]),
        ("required_test_paths", ["src/not_a_test.py"]),
        ("unknown_impact_fallback_test_paths", [".ai/runtime/job.json"]),
    ),
)
def test_fix_pack_paths_are_canonical_and_cannot_grant_admin_scope(field, value):
    with pytest.raises(FixReviewContractError):
        FixContextPack.from_dict(pack_data(**{field: value}))


def test_proof_fingerprint_is_deterministic_and_path_order_independent():
    first = canonical_proof_fingerprint({"src/b.py": BLOB_B, "src/a.py": BLOB_A})
    second = canonical_proof_fingerprint({"src/a.py": BLOB_A, "src/b.py": BLOB_B})
    assert first == second
    expected_payload = '[["src/a.py","' + BLOB_A + '"],["src/b.py","' + BLOB_B + '"]]'
    assert first == hashlib.sha256(expected_payload.encode()).hexdigest()


def test_proof_fingerprint_changes_on_blob_or_declared_path_change():
    original = fingerprint({"src/subject.py": BLOB_A})
    assert fingerprint({"src/subject.py": BLOB_C}) != original
    assert fingerprint({"src/subject.py": BLOB_A, "src/added.py": BLOB_C}) != original
    assert fingerprint({}) != original


def test_unchanged_valid_proof_carries_forward_without_rerunning_its_test():
    exact = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    analysis = analyze_fix_impact(
        pack(),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(exact),
        current_blob_resolver=resolver(exact),
        actual_changed_paths=("src/fix.py",),
    )
    assert analysis.carried_forward_proof_ids == ("proof-1",)
    assert analysis.invalidated_proof_ids == ()
    assert analysis.selected_test_paths == ("tests/test_fix.py",)
    assert analysis.proof_decisions == (("proof-1", "CARRY_FORWARD_ALLOWED"),)


@pytest.mark.parametrize("changed_path", ("src/subject.py", "src/dependency.py"))
def test_subject_or_dependency_change_invalidates_only_affected_proof(changed_path):
    previous = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    current = dict(previous)
    current[changed_path] = BLOB_C
    analysis = analyze_fix_impact(
        pack(),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(previous),
        current_blob_resolver=resolver(current),
        actual_changed_paths=(changed_path,),
    )
    assert analysis.invalidated_proof_ids == ("proof-1",)
    assert analysis.selected_test_paths == (
        "tests/test_fix.py",
        "tests/test_proof.py",
    )
    assert analysis.impact_scope_expanded is False


def test_actual_proof_surface_delta_invalidates_even_when_blob_identity_is_unchanged():
    exact = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    analysis = analyze_fix_impact(
        pack(),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(exact),
        current_blob_resolver=resolver(exact),
        actual_changed_paths=("src/subject.py",),
    )
    assert analysis.invalidated_proof_ids == ("proof-1",)
    assert analysis.carried_forward_proof_ids == ()


def test_changed_bound_test_path_invalidates_proof_and_selects_its_t1():
    data = pack_data()
    data["affected_paths"].append("tests/test_proof.py")
    exact = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    analysis = analyze_fix_impact(
        FixContextPack.from_dict(data),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(exact),
        current_blob_resolver=resolver(exact),
        actual_changed_paths=("tests/test_proof.py",),
    )
    assert analysis.carried_forward_proof_ids == ()
    assert analysis.invalidated_proof_ids == ("proof-1",)
    assert analysis.selected_test_paths == (
        "tests/test_fix.py",
        "tests/test_proof.py",
    )


def test_reviewer_fingerprint_is_recomputed_and_mismatch_fails_closed():
    previous = {"src/subject.py": BLOB_C, "src/dependency.py": BLOB_B}
    with pytest.raises(FixReviewContractError, match="reviewer subject fingerprint mismatch"):
        analyze_fix_impact(
            pack(),
            current_head_sha=HEAD,
            previous_blob_resolver=resolver(previous),
            current_blob_resolver=resolver(previous),
        )


def test_unresolvable_proof_path_becomes_unknown_and_selects_fallback_t1():
    previous = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    current = {"src/subject.py": BLOB_A}
    analysis = analyze_fix_impact(
        pack(),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(previous),
        current_blob_resolver=resolver(current),
        actual_changed_paths=("src/dependency.py",),
    )
    assert analysis.impact_scope_expanded is True
    assert analysis.forbidden_or_unknown_proof_ids == ("proof-1",)
    assert analysis.selected_test_paths == ("tests/test_fallback.py",)


def test_new_or_invalidated_proof_is_forbidden_and_selects_its_t1():
    data = pack_data()
    data["proof_bindings"][0]["status"] = "NEW"
    exact = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    analysis = analyze_fix_impact(
        FixContextPack.from_dict(data),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(exact),
        current_blob_resolver=resolver(exact),
        actual_changed_paths=("src/fix.py",),
    )
    assert analysis.forbidden_or_unknown_proof_ids == ("proof-1",)
    assert analysis.selected_test_paths == ("tests/test_fix.py", "tests/test_proof.py")


def test_actual_delta_escape_expands_impact_and_protects_allowed_scope_authority():
    exact = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    analysis = analyze_fix_impact(
        pack(),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(exact),
        current_blob_resolver=resolver(exact),
        actual_changed_paths=("bridge.py",),
    )
    assert analysis.impact_scope_expanded is True
    assert analysis.selected_test_paths == ("tests/test_fallback.py",)
    # Impact evidence expands review/testing only; executable scope remains a separate gate.
    assert "bridge.py" not in pack().affected_paths


def test_protected_surface_change_is_visible_to_delta_impact_review():
    previous = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    current = {"src/subject.py": BLOB_C, "src/dependency.py": BLOB_B}
    analysis = analyze_fix_impact(
        pack(),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(previous),
        current_blob_resolver=resolver(current),
        actual_changed_paths=("src/subject.py",),
    )
    assert analysis.protected_accepted_paths_unchanged is False
    assert analysis.invalidated_proof_ids == ("proof-1",)


def test_fix_context_is_bounded_provider_neutral_and_retains_source_identity():
    exact = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    analysis = analyze_fix_impact(
        pack(),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(exact),
        current_blob_resolver=resolver(exact),
    )
    rendered = render_fix_executor_context(pack(), analysis)
    assert b"FIX CONTEXT PACK BEGIN" in rendered
    assert b"roadmap/task authority remains external and unchanged" in rendered
    assert b"codex" not in rendered.lower()
    assert b"antigravity" not in rendered.lower()
    assert pack().proof_bindings[0].proof.source_review_round == 2
    assert pack().proof_bindings[0].proof.evidence_fingerprint == EVIDENCE


def test_antigravity_handoff_receives_same_semantic_fix_context_as_codex_pack():
    exact = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    fix_pack = pack()
    analysis = analyze_fix_impact(
        fix_pack,
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(exact),
        current_blob_resolver=resolver(exact),
    )
    auth = {
        "executor_id": "antigravity",
        "fix_context_pack": fix_pack.to_dict(),
        "fix_impact_analysis": analysis.to_dict(),
    }
    assert bridge._interactive_fix_context_for_auth(auth).encode("utf-8") == (
        render_fix_executor_context(fix_pack, analysis)
    )
    auth["executor_id"] = "codex"
    assert bridge._interactive_fix_context_for_auth(auth) is None


def test_delta_impact_evidence_is_compact_machine_readable():
    exact = {"src/subject.py": BLOB_A, "src/dependency.py": BLOB_B}
    analysis = analyze_fix_impact(
        pack(),
        current_head_sha=HEAD,
        previous_blob_resolver=resolver(exact),
        current_blob_resolver=resolver(exact),
    )
    evidence = delta_impact_evidence(analysis, selected_test_status="PASS")
    assert evidence["selected_test_status"] == "PASS"
    assert evidence["carried_forward_proof_ids"] == ["proof-1"]
    assert "proof_decisions" not in evidence
    assert "reasoning" not in json.dumps(evidence)
