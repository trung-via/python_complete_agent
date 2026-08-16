"""Comprehensive test suite for AIOS Continuity State M1 (ADR-010 / ADR-011)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.aios_bridge.continuity import (
    MAX_SERIALIZED_BYTES,
    PHASE_NEXT_OPERATION_MAP,
    SCHEMA_VERSION,
    ArtifactRef,
    BrainOperation,
    BrainState,
    BranchState,
    ContinuityArtifacts,
    ContinuityPhase,
    ContinuityState,
    ContinuityStateValidationError,
    ExecutorState,
    FreshnessIssueCode,
    FreshnessStatus,
    NextOperation,
    StateObservation,
    check_freshness,
)
import scripts.aios_continuity_state as cli_module


def _make_valid_state_dict() -> dict:
    """Returns a valid dictionary representation of a ContinuityState in READY_FOR_RUN phase."""
    return {
        "schema_version": "1",
        "task_id": "TASK-019",
        "phase": "READY_FOR_RUN",
        "next_operation": "RUN_APPROVAL",
        "main": {
            "branch": "main",
            "sha": "689c2c6dd8e41fe0f735b822118ba6530379b7dd",
        },
        "task_branch": {
            "branch": "ai/task-019",
            "sha": None,
        },
        "artifacts": {
            "task": {
                "path": ".ai/tasks/TASK-019.md",
                "ref": "ai-control",
                "blob_sha": "adc44f449f2a991a455b8039d8e8978fe4643146",
            },
            "contracts": [
                {
                    "path": ".ai/decisions/ADR-010.md",
                    "ref": "ai-control",
                    "blob_sha": "504630c25f37c83819ae951076704765609105c7",
                },
                {
                    "path": ".ai/decisions/ADR-011.md",
                    "ref": "ai-control",
                    "blob_sha": "0ce561b1de5c964bb93ea0a5a127b48d86a65839",
                },
            ],
            "plan": {
                "path": ".ai/context/TASK-019-CHATGPT-PLAN.md",
                "ref": "ai-control",
                "blob_sha": "9583000000000000000000000000000000000000",
            },
            "result": None,
            "review": None,
        },
        "brain": {
            "last_id": "chatgpt-chat",
            "last_operation": "TASK_AND_PLAN",
        },
        "executor": {
            "last_id": "antigravity",
        },
    }


def test_valid_schema_v1_parse_and_properties():
    """Valid schema v1 state parses successfully with all properties intact."""
    data = _make_valid_state_dict()
    state = ContinuityState.from_dict(data)

    assert state.schema_version == "1"
    assert state.task_id == "TASK-019"
    assert state.phase == ContinuityPhase.READY_FOR_RUN
    assert state.next_operation == NextOperation.RUN_APPROVAL
    assert state.main.branch == "main"
    assert state.main.sha == "689c2c6dd8e41fe0f735b822118ba6530379b7dd"
    assert state.task_branch.branch == "ai/task-019"
    assert state.task_branch.sha is None
    assert state.artifacts.task.path == ".ai/tasks/TASK-019.md"
    assert len(state.artifacts.contracts) == 2
    assert state.brain.last_id == "chatgpt-chat"
    assert state.brain.last_operation == BrainOperation.TASK_AND_PLAN
    assert state.executor.last_id == "antigravity"


def test_deterministic_round_trip_canonical_json():
    """State serialized to canonical JSON produces identical data when parsed and re-serialized."""
    data = _make_valid_state_dict()
    state1 = ContinuityState.from_dict(data)
    json1 = state1.to_canonical_json()

    state2 = ContinuityState.from_json(json1)
    json2 = state2.to_canonical_json()

    assert json1 == json2
    assert state1 == state2


def test_deterministic_fingerprint():
    """Same semantic state produces exact same SHA-256 fingerprint across runs."""
    state1 = ContinuityState.from_dict(_make_valid_state_dict())
    state2 = ContinuityState.from_dict(_make_valid_state_dict())

    fp1 = state1.fingerprint()
    fp2 = state2.fingerprint()

    assert fp1 == fp2
    assert len(fp1) == 64
    assert all(c in "0123456789abcdef" for c in fp1)


def test_fingerprint_changes_with_any_semantic_change():
    """Any change to task_id, phase, commit SHA, blob SHA, or actor metadata changes fingerprint."""
    base_data = _make_valid_state_dict()
    base_fp = ContinuityState.from_dict(base_data).fingerprint()

    # 1. Change main SHA
    data1 = _make_valid_state_dict()
    data1["main"]["sha"] = "1111111111111111111111111111111111111111"
    assert ContinuityState.from_dict(data1).fingerprint() != base_fp

    # 2. Change brain actor id
    data2 = _make_valid_state_dict()
    data2["brain"]["last_id"] = "claude-chat"
    assert ContinuityState.from_dict(data2).fingerprint() != base_fp

    # 3. Change brain operation
    data3 = _make_valid_state_dict()
    data3["brain"]["last_operation"] = "PLAN"
    assert ContinuityState.from_dict(data3).fingerprint() != base_fp

    # 4. Add a contract
    data4 = _make_valid_state_dict()
    data4["artifacts"]["contracts"].append({
        "path": ".ai/decisions/ADR-009.md",
        "ref": "ai-control",
        "blob_sha": "3333333333333333333333333333333333333333",
    })
    assert ContinuityState.from_dict(data4).fingerprint() != base_fp


def test_strict_case_sensitive_task_id_validation():
    """Task ID must strictly match case-sensitive '^TASK-\\d+$' without normalization."""
    valid_ids = ["TASK-001", "TASK-019", "TASK-9999"]
    for tid in valid_ids:
        d = _make_valid_state_dict()
        d["task_id"] = tid
        d["artifacts"]["task"]["path"] = f".ai/tasks/{tid}.md"
        d["artifacts"]["plan"] = None
        state = ContinuityState.from_dict(d)
        assert state.task_id == tid

    invalid_ids = [
        "task-019",  # Lowercase
        "Task-019",  # Mixed case
        "TASK_019",  # Underscore
        "TASK-abc",  # Letters in number
        "TASK-",     # No number
        "019",       # Missing prefix
        "",          # Empty
        None,        # None
        True,        # Bool
    ]
    for inv in invalid_ids:
        d = _make_valid_state_dict()
        d["task_id"] = inv
        with pytest.raises(ContinuityStateValidationError):
            ContinuityState.from_dict(d)


def test_sha_validation_strict_40_hex_lowercase():
    """All commit and blob SHAs must be exactly 40 lowercase hex characters."""
    invalid_shas = [
        "689C2C6DD8E41FE0F735B822118BA6530379B7DD",  # Uppercase
        "689c2c6dd8e41fe0f735b822118ba6530379b7d",   # 39 chars
        "689c2c6dd8e41fe0f735b822118ba6530379b7dd0",  # 41 chars
        "689c2c6dd8e41fe0f735b822118ba6530379b7zg",   # Non-hex character 'z', 'g'
        "HEAD",
        "",
        12345,
        True,
    ]
    for inv_sha in invalid_shas:
        d = _make_valid_state_dict()
        d["main"]["sha"] = inv_sha
        with pytest.raises(ContinuityStateValidationError):
            ContinuityState.from_dict(d)

        d_art = _make_valid_state_dict()
        d_art["artifacts"]["task"]["blob_sha"] = inv_sha
        with pytest.raises(ContinuityStateValidationError):
            ContinuityState.from_dict(d_art)


def test_path_safety_validation():
    """Artifact paths must be relative POSIX under '.ai/' without backslashes or traversal."""
    unsafe_paths = [
        "/etc/passwd",
        "C:\\Windows\\system32",
        ".ai/../secrets.txt",
        ".ai\\tasks\\TASK-019.md",
        "src/app.py",  # Not under .ai/
        "tasks/TASK-019.md",
        ".ai//tasks/TASK-019.md",
        "",
        None,
    ]
    for unsafe_p in unsafe_paths:
        d = _make_valid_state_dict()
        d["artifacts"]["task"]["path"] = unsafe_p
        with pytest.raises(ContinuityStateValidationError):
            ContinuityState.from_dict(d)


def test_sensitive_path_rejection():
    """Sensitive file paths (.env, keys, credentials, tokens, secrets) are strictly rejected regardless of extension."""
    sensitive_paths = [
        ".ai/.env",
        ".ai/.env.local",
        ".ai/.env.production",
        ".ai/keys/id_rsa",
        ".ai/certs/server.key",
        ".ai/certs/cert.pem",
        ".ai/secrets/token.bin",
        ".ai/secrets/plan.md",               # Sensitive directory + markdown
        ".ai/context/token.json",            # Sensitive keyword in JSON
        ".ai/credentials/creds.yaml",        # Sensitive directory + YAML
        ".ai/auth/tokens.md",                # Sensitive keyword + markdown
        ".ai/profiles/admin.json",           # Sensitive directory + JSON
    ]
    for sp in sensitive_paths:
        d = _make_valid_state_dict()
        d["artifacts"]["contracts"] = [
            {
                "path": sp,
                "ref": "ai-control",
                "blob_sha": "1111111111111111111111111111111111111111",
            }
        ]
        with pytest.raises(ContinuityStateValidationError, match="Sensitive"):
            ContinuityState.from_dict(d)


def test_git_ref_validation_conservative_hardening():
    """Git references must be conservative valid ref labels; unsafe/malformed refs are rejected."""
    # Valid Git refs
    valid_refs = ["main", "ai/task-019", "ai-control", "refs/heads/main", "feat.v1", "release-1.0.0"]
    for r in valid_refs:
        b = BranchState(branch=r, sha="689c2c6dd8e41fe0f735b822118ba6530379b7dd")
        assert b.branch == r

    # Invalid Git refs
    invalid_refs = [
        "main/",            # Trailing slash
        "/main",            # Leading slash
        "main//branch",     # Double slash
        "main.lock",        # Component ends with .lock
        "ai/task.lock",     # Component ends with .lock
        "ai/.task",         # Component starts with .
        ".main",            # Starts with .
        "main.",            # Ends with .
        "main..branch",     # Traversal ..
        "main~1",           # Tilde
        "main^1",           # Caret
        "main:branch",      # Colon
        "main?branch",      # Question mark
        "main*branch",      # Asterisk
        "main[1]",          # Bracket
        "main\\branch",     # Backslash
        "main@branch",      # @
        "main@{0}",         # @{}
        "main branch",      # Space
        "main\tbranch",     # Tab
        "main\nbranch",     # Newline
        "",                 # Empty
        None,               # None
        True,               # Bool
    ]
    for inv_r in invalid_refs:
        with pytest.raises(ContinuityStateValidationError):
            BranchState(branch=inv_r)  # type: ignore


def test_unknown_fields_rejection_at_all_layers():
    """Unknown fields are rejected fail-closed at root and nested object layers."""
    # 1. Root level unknown field
    d_root = _make_valid_state_dict()
    d_root["extra_field"] = "malicious_payload"
    with pytest.raises(ContinuityStateValidationError, match="Unknown root fields"):
        ContinuityState.from_dict(d_root)

    # 2. Main level unknown field
    d_main = _make_valid_state_dict()
    d_main["main"]["extra_info"] = 123
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in main"):
        ContinuityState.from_dict(d_main)

    # 3. ArtifactRef level unknown field
    d_art = _make_valid_state_dict()
    d_art["artifacts"]["task"]["notes"] = "some text"
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in artifacts.task"):
        ContinuityState.from_dict(d_art)

    # 4. Brain level unknown field
    d_brain = _make_valid_state_dict()
    d_brain["brain"]["prompt"] = "system prompt here"
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in brain"):
        ContinuityState.from_dict(d_brain)

    # 5. Executor level unknown field
    d_exec = _make_valid_state_dict()
    d_exec["executor"]["lease_id"] = "lease-123"
    with pytest.raises(ContinuityStateValidationError, match="Unknown fields in executor"):
        ContinuityState.from_dict(d_exec)


def test_phase_next_operation_compatibility():
    """Only locked phase -> next_operation pairs are accepted; all others fail."""
    for phase, next_op in PHASE_NEXT_OPERATION_MAP.items():
        d = _make_valid_state_dict()
        d["phase"] = phase.value
        d["next_operation"] = next_op.value

        # Adjust task_branch and artifacts for phases that require them
        if phase in [
            ContinuityPhase.RUNNING,
            ContinuityPhase.READY_FOR_REVIEW,
            ContinuityPhase.CHANGES_REQUIRED,
            ContinuityPhase.FIXING,
            ContinuityPhase.APPROVED,
            ContinuityPhase.MERGED,
        ]:
            d["task_branch"]["sha"] = "2222222222222222222222222222222222222222"

        if phase in [
            ContinuityPhase.READY_FOR_REVIEW,
            ContinuityPhase.CHANGES_REQUIRED,
            ContinuityPhase.FIXING,
            ContinuityPhase.APPROVED,
            ContinuityPhase.MERGED,
        ]:
            d["artifacts"]["result"] = {
                "path": ".ai/results/RESULT-019.md",
                "ref": "ai/task-019",
                "blob_sha": "3333333333333333333333333333333333333333",
            }

        if phase in [
            ContinuityPhase.CHANGES_REQUIRED,
            ContinuityPhase.FIXING,
            ContinuityPhase.APPROVED,
            ContinuityPhase.MERGED,
        ]:
            d["artifacts"]["review"] = {
                "path": ".ai/reviews/REVIEW-019.md",
                "ref": "ai-control",
                "blob_sha": "4444444444444444444444444444444444444444",
            }

        state = ContinuityState.from_dict(d)
        assert state.phase == phase
        assert state.next_operation == next_op

        # Incompatible next_operation must fail
        d_bad = dict(d)
        d_bad["next_operation"] = "NONE" if next_op != NextOperation.NONE else "PLAN"
        with pytest.raises(ContinuityStateValidationError, match="Incompatible phase/next_operation pair"):
            ContinuityState.from_dict(d_bad)


def test_task_branch_sha_requirement_from_running_onward():
    """task_branch.sha is optional before RUNNING, but mandatory from RUNNING onward."""
    # Pre-running phases allow null sha
    for phase in [ContinuityPhase.TASK_DEFINED, ContinuityPhase.READY_FOR_RUN]:
        d = _make_valid_state_dict()
        d["phase"] = phase.value
        d["next_operation"] = PHASE_NEXT_OPERATION_MAP[phase].value
        d["task_branch"]["sha"] = None
        state = ContinuityState.from_dict(d)
        assert state.task_branch.sha is None

    # Running and post-running phases reject null sha
    for phase in [
        ContinuityPhase.RUNNING,
        ContinuityPhase.READY_FOR_REVIEW,
        ContinuityPhase.CHANGES_REQUIRED,
        ContinuityPhase.FIXING,
        ContinuityPhase.APPROVED,
        ContinuityPhase.MERGED,
    ]:
        d = _make_valid_state_dict()
        d["phase"] = phase.value
        d["next_operation"] = PHASE_NEXT_OPERATION_MAP[phase].value
        d["task_branch"]["sha"] = None
        d["artifacts"]["result"] = {
            "path": ".ai/results/RESULT-019.md",
            "ref": "ai/task-019",
            "blob_sha": "3333333333333333333333333333333333333333",
        }
        d["artifacts"]["review"] = {
            "path": ".ai/reviews/REVIEW-019.md",
            "ref": "ai-control",
            "blob_sha": "4444444444444444444444444444444444444444",
        }
        with pytest.raises(ContinuityStateValidationError, match="task_branch.sha is required"):
            ContinuityState.from_dict(d)


def test_task_identity_and_canonical_namespace_consistency():
    """TASK-NNN, RESULT-NNN, REVIEW-NNN must live in exact canonical directories and match active task_id."""
    # 1. Task file mismatch
    d1 = _make_valid_state_dict()
    d1["artifacts"]["task"]["path"] = ".ai/tasks/TASK-018.md"
    with pytest.raises(ContinuityStateValidationError, match="artifacts.task path must be exactly"):
        ContinuityState.from_dict(d1)

    # 2. Task file in wrong directory (e.g. .ai/context/TASK-019.md)
    d1_wrong_dir = _make_valid_state_dict()
    d1_wrong_dir["artifacts"]["task"]["path"] = ".ai/context/TASK-019.md"
    with pytest.raises(ContinuityStateValidationError, match="artifacts.task path must be exactly"):
        ContinuityState.from_dict(d1_wrong_dir)

    # 3. Result file mismatch
    d2 = _make_valid_state_dict()
    d2["phase"] = "READY_FOR_REVIEW"
    d2["next_operation"] = "REVIEW"
    d2["task_branch"]["sha"] = "2222222222222222222222222222222222222222"
    d2["artifacts"]["result"] = {
        "path": ".ai/results/RESULT-018.md",
        "ref": "ai/task-019",
        "blob_sha": "3333333333333333333333333333333333333333",
    }
    with pytest.raises(ContinuityStateValidationError, match="artifacts.result path must be exactly"):
        ContinuityState.from_dict(d2)

    # 4. Result file in wrong directory (e.g. .ai/context/RESULT-019.md)
    d2_wrong_dir = _make_valid_state_dict()
    d2_wrong_dir["phase"] = "READY_FOR_REVIEW"
    d2_wrong_dir["next_operation"] = "REVIEW"
    d2_wrong_dir["task_branch"]["sha"] = "2222222222222222222222222222222222222222"
    d2_wrong_dir["artifacts"]["result"] = {
        "path": ".ai/context/RESULT-019.md",
        "ref": "ai/task-019",
        "blob_sha": "3333333333333333333333333333333333333333",
    }
    with pytest.raises(ContinuityStateValidationError, match="artifacts.result path must be exactly"):
        ContinuityState.from_dict(d2_wrong_dir)

    # 5. Review file mismatch
    d3 = _make_valid_state_dict()
    d3["phase"] = "APPROVED"
    d3["next_operation"] = "MERGE_APPROVAL"
    d3["task_branch"]["sha"] = "2222222222222222222222222222222222222222"
    d3["artifacts"]["result"] = {
        "path": ".ai/results/RESULT-019.md",
        "ref": "ai/task-019",
        "blob_sha": "3333333333333333333333333333333333333333",
    }
    d3["artifacts"]["review"] = {
        "path": ".ai/reviews/REVIEW-018.md",
        "ref": "ai-control",
        "blob_sha": "4444444444444444444444444444444444444444",
    }
    with pytest.raises(ContinuityStateValidationError, match="artifacts.review path must be exactly"):
        ContinuityState.from_dict(d3)

    # 6. Review file in wrong directory (e.g. .ai/context/REVIEW-019.md)
    d3_wrong_dir = _make_valid_state_dict()
    d3_wrong_dir["phase"] = "APPROVED"
    d3_wrong_dir["next_operation"] = "MERGE_APPROVAL"
    d3_wrong_dir["task_branch"]["sha"] = "2222222222222222222222222222222222222222"
    d3_wrong_dir["artifacts"]["result"] = {
        "path": ".ai/results/RESULT-019.md",
        "ref": "ai/task-019",
        "blob_sha": "3333333333333333333333333333333333333333",
    }
    d3_wrong_dir["artifacts"]["review"] = {
        "path": ".ai/context/REVIEW-019.md",
        "ref": "ai-control",
        "blob_sha": "4444444444444444444444444444444444444444",
    }
    with pytest.raises(ContinuityStateValidationError, match="artifacts.review path must be exactly"):
        ContinuityState.from_dict(d3_wrong_dir)

    # 7. Plan file mismatch
    d4 = _make_valid_state_dict()
    d4["artifacts"]["plan"] = {
        "path": ".ai/context/TASK-018-MINIMAX-PLAN.md",
        "ref": "ai-control",
        "blob_sha": "5555555555555555555555555555555555555555",
    }
    with pytest.raises(ContinuityStateValidationError, match="declares task identifier 'TASK-018'"):
        ContinuityState.from_dict(d4)


def test_duplicate_contract_rejection():
    """Duplicate contract artifact paths or identities are rejected."""
    d = _make_valid_state_dict()
    dup_contract = {
        "path": ".ai/decisions/ADR-010.md",
        "ref": "ai-control",
        "blob_sha": "504630c25f37c83819ae951076704765609105c7",
    }
    d["artifacts"]["contracts"] = [dup_contract, dup_contract]
    with pytest.raises(ContinuityStateValidationError, match="Duplicate contract"):
        ContinuityState.from_dict(d)


def test_phase_required_artifacts_enforcement():
    """READY_FOR_REVIEW requires result; CHANGES_REQUIRED/FIXING/APPROVED/MERGED require result + review."""
    # READY_FOR_REVIEW without result
    d1 = _make_valid_state_dict()
    d1["phase"] = "READY_FOR_REVIEW"
    d1["next_operation"] = "REVIEW"
    d1["task_branch"]["sha"] = "2222222222222222222222222222222222222222"
    d1["artifacts"]["result"] = None
    with pytest.raises(ContinuityStateValidationError, match="requires artifacts.result"):
        ContinuityState.from_dict(d1)

    # CHANGES_REQUIRED without review
    d2 = _make_valid_state_dict()
    d2["phase"] = "CHANGES_REQUIRED"
    d2["next_operation"] = "FIX_APPROVAL"
    d2["task_branch"]["sha"] = "2222222222222222222222222222222222222222"
    d2["artifacts"]["result"] = {
        "path": ".ai/results/RESULT-019.md",
        "ref": "ai/task-019",
        "blob_sha": "3333333333333333333333333333333333333333",
    }
    d2["artifacts"]["review"] = None
    with pytest.raises(ContinuityStateValidationError, match="requires artifacts.review"):
        ContinuityState.from_dict(d2)


def test_size_limit_16kib_fail_closed_in_constructor_and_parser():
    """State exceeding 16 KiB (16384 bytes) fails closed in constructor, from_dict, and from_json."""
    d = _make_valid_state_dict()
    # Add many valid contract items to exceed 16 KiB
    many_contracts = []
    for i in range(250):
        many_contracts.append({
            "path": f".ai/decisions/ADR-{i:04d}-EXTENDED-VERY-LONG-NAME-TEST-PADDING.md",
            "ref": "ai-control",
            "blob_sha": f"{i:040x}",
        })
    d["artifacts"]["contracts"] = many_contracts

    # from_dict must fail closed immediately
    with pytest.raises(ContinuityStateValidationError, match="exceeds MAX_SERIALIZED_BYTES"):
        ContinuityState.from_dict(d)

    # from_json must fail closed immediately
    huge_json = json.dumps(d)
    assert len(huge_json.encode("utf-8")) > MAX_SERIALIZED_BYTES
    with pytest.raises(ContinuityStateValidationError, match="exceeds maximum allowable size"):
        ContinuityState.from_json(huge_json)

    # Direct constructor must fail closed immediately
    contracts_objs = tuple(
        ArtifactRef(path=c["path"], ref=c["ref"], blob_sha=c["blob_sha"]) for c in many_contracts
    )
    with pytest.raises(ContinuityStateValidationError, match="exceeds MAX_SERIALIZED_BYTES"):
        ContinuityState(
            task_id="TASK-019",
            phase=ContinuityPhase.READY_FOR_RUN,
            next_operation=NextOperation.RUN_APPROVAL,
            main=BranchState(branch="main", sha="689c2c6dd8e41fe0f735b822118ba6530379b7dd"),
            task_branch=BranchState(branch="ai/task-019", sha=None),
            artifacts=ContinuityArtifacts(
                task=ArtifactRef(
                    path=".ai/tasks/TASK-019.md",
                    ref="ai-control",
                    blob_sha="adc44f449f2a991a455b8039d8e8978fe4643146",
                ),
                contracts=contracts_objs,
            ),
        )


def test_freshness_evaluation_fresh():
    """check_freshness returns FRESH when all observed SHAs match state exactly."""
    state = ContinuityState.from_dict(_make_valid_state_dict())
    obs = StateObservation(
        main_sha="689c2c6dd8e41fe0f735b822118ba6530379b7dd",
        task_branch_sha=None,
        artifact_blobs={
            ".ai/tasks/TASK-019.md": "adc44f449f2a991a455b8039d8e8978fe4643146",
            ".ai/decisions/ADR-010.md": "504630c25f37c83819ae951076704765609105c7",
            ".ai/decisions/ADR-011.md": "0ce561b1de5c964bb93ea0a5a127b48d86a65839",
            ".ai/context/TASK-019-CHATGPT-PLAN.md": "9583000000000000000000000000000000000000",
        },
    )

    report = check_freshness(state, obs)
    assert report.status == FreshnessStatus.FRESH
    assert report.is_fresh is True
    assert len(report.issues) == 0
    assert report.state_fingerprint == state.fingerprint()


def test_freshness_evaluation_stale_main_sha():
    """check_freshness returns STALE when main SHA has drifted."""
    state = ContinuityState.from_dict(_make_valid_state_dict())
    obs = StateObservation(
        main_sha="1111111111111111111111111111111111111111",  # Drifted
        task_branch_sha=None,
        artifact_blobs={
            ".ai/tasks/TASK-019.md": "adc44f449f2a991a455b8039d8e8978fe4643146",
            ".ai/decisions/ADR-010.md": "504630c25f37c83819ae951076704765609105c7",
            ".ai/decisions/ADR-011.md": "0ce561b1de5c964bb93ea0a5a127b48d86a65839",
            ".ai/context/TASK-019-CHATGPT-PLAN.md": "9583000000000000000000000000000000000000",
        },
    )

    report = check_freshness(state, obs)
    assert report.status == FreshnessStatus.STALE
    assert report.is_fresh is False
    assert any(i.code == FreshnessIssueCode.MAIN_SHA_MISMATCH for i in report.issues)


def test_freshness_evaluation_stale_task_sha():
    """check_freshness returns STALE when task branch SHA has drifted."""
    d = _make_valid_state_dict()
    d["phase"] = "RUNNING"
    d["next_operation"] = "WAIT_FOR_RESULT"
    d["task_branch"]["sha"] = "2222222222222222222222222222222222222222"
    state = ContinuityState.from_dict(d)

    obs = StateObservation(
        main_sha="689c2c6dd8e41fe0f735b822118ba6530379b7dd",
        task_branch_sha="9999999999999999999999999999999999999999",  # Drifted
        artifact_blobs={
            ".ai/tasks/TASK-019.md": "adc44f449f2a991a455b8039d8e8978fe4643146",
            ".ai/decisions/ADR-010.md": "504630c25f37c83819ae951076704765609105c7",
            ".ai/decisions/ADR-011.md": "0ce561b1de5c964bb93ea0a5a127b48d86a65839",
            ".ai/context/TASK-019-CHATGPT-PLAN.md": "9583000000000000000000000000000000000000",
        },
    )

    report = check_freshness(state, obs)
    assert report.status == FreshnessStatus.STALE
    assert any(i.code == FreshnessIssueCode.TASK_SHA_MISMATCH for i in report.issues)


def test_freshness_evaluation_stale_artifact_blob():
    """check_freshness returns STALE when an artifact blob has drifted."""
    state = ContinuityState.from_dict(_make_valid_state_dict())
    obs = StateObservation(
        main_sha="689c2c6dd8e41fe0f735b822118ba6530379b7dd",
        task_branch_sha=None,
        artifact_blobs={
            ".ai/tasks/TASK-019.md": "9999999999999999999999999999999999999999",  # Drifted
            ".ai/decisions/ADR-010.md": "504630c25f37c83819ae951076704765609105c7",
            ".ai/decisions/ADR-011.md": "0ce561b1de5c964bb93ea0a5a127b48d86a65839",
            ".ai/context/TASK-019-CHATGPT-PLAN.md": "9583000000000000000000000000000000000000",
        },
    )

    report = check_freshness(state, obs)
    assert report.status == FreshnessStatus.STALE
    assert any(i.code == FreshnessIssueCode.ARTIFACT_BLOB_MISMATCH for i in report.issues)


def test_freshness_evaluation_incomplete_observations():
    """check_freshness returns INCOMPLETE when required observations are missing without mismatches."""
    state = ContinuityState.from_dict(_make_valid_state_dict())
    obs = StateObservation(
        main_sha="689c2c6dd8e41fe0f735b822118ba6530379b7dd",
        task_branch_sha=None,
        artifact_blobs={
            ".ai/tasks/TASK-019.md": "adc44f449f2a991a455b8039d8e8978fe4643146",
            # ADR-010, ADR-011, and plan observations are omitted
        },
    )

    report = check_freshness(state, obs)
    assert report.status == FreshnessStatus.INCOMPLETE
    assert any(i.code == FreshnessIssueCode.MISSING_ARTIFACT_OBSERVATION for i in report.issues)


def test_actor_metadata_validation():
    """Actor IDs must be valid conservative lowercase identifiers; operations must be valid enum."""
    # Valid actor IDs
    for valid_id in ["chatgpt-chat", "claude-chat", "gemini-chat", "antigravity", "codex", "claude-code"]:
        b = BrainState(last_id=valid_id, last_operation=BrainOperation.PLAN)
        assert b.last_id == valid_id
        e = ExecutorState(last_id=valid_id)
        assert e.last_id == valid_id

    # Invalid actor IDs
    invalid_ids = ["ChatGPT", "Claude_Code", "anti gravity", "bad!id", ""]
    for inv_id in invalid_ids:
        with pytest.raises(ContinuityStateValidationError):
            BrainState(last_id=inv_id)
        with pytest.raises(ContinuityStateValidationError):
            ExecutorState(last_id=inv_id)

    # Invalid BrainOperation
    with pytest.raises(ContinuityStateValidationError):
        BrainState(last_id="chatgpt-chat", last_operation="INVALID_OP")  # type: ignore


def test_cli_validate_and_fingerprint_commands(tmp_path: Path):
    """CLI validate and fingerprint commands succeed on valid files and fail on invalid files."""
    valid_file = tmp_path / "CURRENT-STATE.json"
    state = ContinuityState.from_dict(_make_valid_state_dict())
    valid_file.write_text(state.to_canonical_json(), encoding="utf-8")

    # CLI validate success
    assert cli_module.main(["validate", str(valid_file)]) == 0

    # CLI fingerprint success
    assert cli_module.main(["fingerprint", str(valid_file)]) == 0

    # CLI validate failure on malformed file
    invalid_file = tmp_path / "INVALID-STATE.json"
    invalid_file.write_text("{\"schema_version\": \"999\"}", encoding="utf-8")
    assert cli_module.main(["validate", str(invalid_file)]) == 1

    # CLI validate failure on non-existent file
    missing_file = tmp_path / "NON-EXISTENT.json"
    assert cli_module.main(["validate", str(missing_file)]) == 1
