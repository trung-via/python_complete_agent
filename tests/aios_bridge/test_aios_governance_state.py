"""Focused offline checks for cross-chat roadmap and AIOS-adoption planning state."""
from __future__ import annotations

import re
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROADMAP_FILE = REPO_ROOT / ".ai" / "roadmap-state.yaml"
ADOPTION_FILE = REPO_ROOT / ".ai" / "aios-adoption-state.yaml"
PIN_FILE = (
    REPO_ROOT / ".agents" / "skills" / "aios-worker" / "requirements-aios-renew.txt"
)
EXPECTED_PIN = "a3b723b49cd65677f548c5694a52a6fc006a9e2a"
UPSTREAM_PLANNING_CHECKPOINT = "df65e3f9468d1cc408739ebd89165880ea18afd7"
TASK_192_SOURCE_SHA = "dcb7432abc58ed983e6c26d5456ace1423e49981"
TASK_194_SOURCE_SHA = "e0d8998ee004fda80ca3fbc3de4eb0afb59160a5"
TASK_196_SOURCE_SHA = "4f6d91858c93192f497342315c4650e30b0a2718"
GOVERNANCE_TRACK_ID = "PYTHON_AGENT_GOVERNANCE_FOUNDATION"
GOVERNANCE_SEQUENCE = [
    "PYTHON_AGENT_MANIFESTO",
    "PYTHON_AGENT_CONSTITUTION",
    "PYTHON_AGENT_PRODUCT_CONTRACT",
    "CHATGPT_PROJECT_CONTRACT_RECONCILIATION",
]


def load_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def indexed_families(state: dict) -> dict[str, dict]:
    return {family["id"]: family for family in state["capability_families"]}


def classification_for_task(state: dict, task_id: str) -> str:
    matches = [
        family["classification"]
        for family in state["capability_families"]
        if task_id in family["upstream_tasks"]
    ]
    assert len(matches) == 1
    return matches[0]


def values_for_key(value: object, key: str) -> list[object]:
    matches: list[object] = []
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            if child_key == key:
                matches.append(child_value)
            matches.extend(values_for_key(child_value, key))
    elif isinstance(value, list):
        for child_value in value:
            matches.extend(values_for_key(child_value, key))
    return matches


def test_roadmap_has_one_active_track_and_transition_safe_governance_next():
    state = load_yaml(ROADMAP_FILE)
    assert state["authority"] == {
        "owner": "BRAIN",
        "purpose": "CROSS_CHAT_PLANNING_BOOKMARK",
        "engineering_truth": False,
        "auto_advance_from_runtime_or_worker_state": False,
        "priority_change_owner": "HUMAN",
    }
    assert state["product_checkpoint"]["task_id"] == "TASK-191"
    assert state["product_checkpoint"]["status"] == "DONE"
    assert state["active_track"]["id"] == GOVERNANCE_TRACK_ID
    assert state["active_track"]["status"] == "ACTIVE"
    assert values_for_key(state, "status").count("ACTIVE") == 1
    assert state["roadmap_sources"] == [
        "docs/POST_M4_PRODUCT_INTELLIGENCE_ROADMAP.md",
        "docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md",
    ]
    assert state["next"]["status"] == "NEXT"
    assert values_for_key(state, "status").count("NEXT") == 1

    governance_completed = [
        item
        for item in state["completed_milestones"]
        if item["track_id"] == GOVERNANCE_TRACK_ID
    ]
    completed_ids = [item["milestone_id"] for item in governance_completed]
    pending = state["pending_commitments"]
    pending_ids = [item["id"] for item in pending]
    partitioned_ids = completed_ids + pending_ids

    assert partitioned_ids == GOVERNANCE_SEQUENCE
    assert len(partitioned_ids) == len(set(partitioned_ids))
    assert all(item["status"] == "DONE" for item in governance_completed)
    assert all(
        re.fullmatch(r"TASK-\d+", item["task_id"])
        for item in governance_completed
    )
    assert all(
        re.fullmatch(r"[0-9a-f]{40}", item["source_sha"])
        for item in governance_completed
    )
    assert pending
    assert all(item["status"] == "NOT_DONE" for item in pending)
    assert state["next"]["id"] == pending[0]["id"]
    assert state["next"]["title"] == pending[0]["title"]


def test_roadmap_records_exact_completion_provenance_and_recovered_upstream_work():
    state = load_yaml(ROADMAP_FILE)
    completed = {
        item["task_id"]: item for item in state["completed_milestones"]
    }
    assert completed["TASK-192"] == {
        "task_id": "TASK-192",
        "track_id": "AIOS_DOWNSTREAM_PARITY",
        "title": "Canonical downstream AIOS adoption baseline",
        "status": "DONE",
        "source_sha": TASK_192_SOURCE_SHA,
    }
    assert completed["TASK-194"] == {
        "task_id": "TASK-194",
        "track_id": GOVERNANCE_TRACK_ID,
        "milestone_id": "PYTHON_AGENT_MANIFESTO",
        "title": "Python Agent Manifesto",
        "status": "DONE",
        "source_sha": TASK_194_SOURCE_SHA,
    }
    assert completed["TASK-196"] == {
        "task_id": "TASK-196",
        "track_id": GOVERNANCE_TRACK_ID,
        "milestone_id": "PYTHON_AGENT_CONSTITUTION",
        "title": "Python Agent Constitution",
        "status": "DONE",
        "source_sha": TASK_196_SOURCE_SHA,
    }

    upstream = state["upstream_recovery"]
    assert upstream["status"] == "ADOPTED_BY_PIN"
    assert upstream["blocking_current_track"] is False
    assert [item["task_id"] for item in upstream["items"]] == [
        "TASK-101",
        "TASK-103",
    ]
    assert all(
        item["status"] == "ADOPTED_BY_PIN"
        and item["blocking_current_track"] is False
        for item in upstream["items"]
    )
    assert upstream["recovery_kind"] == "NON_PRODUCT_CONTROL_PLANE"
    assert "does not advance" in upstream["roadmap_effect"]
    pending = {item["id"]: item["status"] for item in state["pending_commitments"]}
    assert pending["PYTHON_AGENT_PRODUCT_CONTRACT"] == "NOT_DONE"
    assert pending["CHATGPT_PROJECT_CONTRACT_RECONCILIATION"] == "NOT_DONE"
    assert state["authority"]["owner"] == "BRAIN"
    assert state["authority"]["auto_advance_from_runtime_or_worker_state"] is False


def test_adoption_registry_pin_audit_authority_and_classes_are_explicit():
    state = load_yaml(ADOPTION_FILE)
    requirement = PIN_FILE.read_text(encoding="utf-8").strip()
    assert requirement.endswith("@" + EXPECTED_PIN)
    assert state["downstream_pin"]["commit"] == EXPECTED_PIN
    assert state["upstream_audit"] == {
        "checkpoint": UPSTREAM_PLANNING_CHECKPOINT,
        "through_authored_task": "TASK-105",
        "checkpoint_role": "BRAIN_PLANNING_EVIDENCE",
        "checkpoint_is_runtime_authority": False,
    }
    assert state["authority"]["engineering_truth"] is False
    assert set(state["classification_vocabulary"]) == {
        "ADOPTED_BY_PIN",
        "PORT_GOVERNANCE",
        "EXPLICITLY_NOT_APPLICABLE_OR_OPTIONAL",
        "BLOCKED_PENDING_UPSTREAM",
    }


def test_relevant_upstream_tasks_have_one_fail_closed_classification():
    state = load_yaml(ADOPTION_FILE)
    expected_task_classes = {
        **{
            task_id: "ADOPTED_BY_PIN"
            for task_id in (
                "TASK-064", "TASK-065", "TASK-067", "TASK-075", "TASK-076",
                "TASK-077", "TASK-078", "TASK-079", "TASK-080", "TASK-081",
                "TASK-085", "TASK-086", "TASK-087", "TASK-088", "TASK-089",
                "TASK-090", "TASK-091", "TASK-092", "TASK-093", "TASK-094",
                "TASK-095", "TASK-096", "TASK-097", "TASK-098", "TASK-099",
                "TASK-100", "TASK-102",
            )
        },
        **{
            task_id: "EXPLICITLY_NOT_APPLICABLE_OR_OPTIONAL"
            for task_id in (
                "TASK-066", "TASK-068", "TASK-069", "TASK-070", "TASK-071",
                "TASK-072", "TASK-073", "TASK-074", "TASK-084",
            )
        },
        "TASK-083": "PORT_GOVERNANCE",
        "TASK-101": "ADOPTED_BY_PIN",
        "TASK-103": "ADOPTED_BY_PIN",
        "TASK-104": "ADOPTED_BY_PIN",
        "TASK-105": "ADOPTED_BY_PIN",
    }
    classified_tasks = {
        task_id: classification_for_task(state, task_id)
        for task_id in expected_task_classes
    }
    assert classified_tasks == expected_task_classes
    families = indexed_families(state)
    assert families["ADMISSION_FAILURE_V2_AND_CORRECTION_PREFLIGHT"] == {
        "id": "ADMISSION_FAILURE_V2_AND_CORRECTION_PREFLIGHT",
        "upstream_tasks": ["TASK-081", "TASK-085"],
        "classification": "ADOPTED_BY_PIN",
        "consumption": "PINNED_KERNEL_ONLY",
        "boundary": "NO_DOWNSTREAM_CONTROL_PLANE_IMPLEMENTATION",
    }
    assert families["PERFORMANCE_CLOSURE"]["source_published"] is True
    assert families["PERFORMANCE_CLOSURE"]["upstream_revision"] == 4
    assert families["CORRECTION_FRONTIER_HARDENING"]["source_published"] is True
    ingress = families["RECOVERED_BRAIN_AUTHORING_INGRESS"]
    assert ingress["upstream_tasks"] == ["TASK-104", "TASK-105"]
    assert ingress["authoritative_semantics"] == "POST_TASK_105_RECOVERY"
    assert families["OPTIONAL_OUTER_AUTOMATION"]["classification"] == (
        "EXPLICITLY_NOT_APPLICABLE_OR_OPTIONAL"
    )
    assert "TASK-084" in families["OPTIONAL_OUTER_AUTOMATION"]["upstream_tasks"]
    assert families[
        "CONTINUE_IMPLEMENTATION_SAFE_PUBLICATION_AND_NATIVE_INSTRUCTIONS"
    ]["safe_publisher"] == "ACTIVE"


def test_task_197_malformed_decision_remains_incident_only():
    state = load_yaml(ADOPTION_FILE)
    assert state["incident_lineage"] == {
        "run_id": "RUN-197-001",
        "task_revision": 1,
        "candidate": "8992e64654b1342a70ad37c9c0aa693ce537a975",
        "review": "REVIEW-197-001",
        "semantic_review": "PASS",
        "malformed_decision": "f334312384543dd4726e83089601e375dd5da17b",
        "disposition": "IMMUTABLE_NOT_PUBLICATION_AUTHORITY",
        "resumed": False,
    }
