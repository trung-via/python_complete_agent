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
EXPECTED_PIN = "2599202afedb0622e9e9bdc7b5a15f34da01cc27"
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


def test_roadmap_records_exact_completion_provenance_and_non_blocking_upstream_work():
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

    upstream = state["pending_upstream_closure"]
    assert upstream["blocking_current_track"] is False
    assert [item["task_id"] for item in upstream["items"]] == [
        "TASK-101",
        "TASK-103",
    ]
    assert all(
        item["status"] == "BLOCKED_PENDING_UPSTREAM"
        and item["blocking_current_track"] is False
        for item in upstream["items"]
    )
    assert "exact reviewed and source-published upstream candidate" in (
        upstream["migration_gate"]
    )
    assert "never follow mutable AIOS-renew main" in upstream["migration_gate"]


def test_adoption_registry_pin_audit_authority_and_classes_are_explicit():
    state = load_yaml(ADOPTION_FILE)
    requirement = PIN_FILE.read_text(encoding="utf-8").strip()
    assert requirement.endswith("@" + EXPECTED_PIN)
    assert state["downstream_pin"]["commit"] == EXPECTED_PIN
    assert state["upstream_audit"] == {
        "checkpoint": "7d0bbcbce4b1bfeaa47634f9069a8ae9ac44930c",
        "through_authored_task": "TASK-103",
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
        "TASK-101": "BLOCKED_PENDING_UPSTREAM",
        "TASK-103": "BLOCKED_PENDING_UPSTREAM",
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
    assert families["PERFORMANCE_CLOSURE"]["source_published"] is False
    assert families["PERFORMANCE_CLOSURE"]["upstream_roadmap_reconciled"] is False
    assert families["AUTHORED_POST_CHECKPOINT_CAPABILITY"]["semantic_pass"] is False
    assert families["AUTHORED_POST_CHECKPOINT_CAPABILITY"]["source_published"] is False
    assert families["OPTIONAL_OUTER_AUTOMATION"]["classification"] == (
        "EXPLICITLY_NOT_APPLICABLE_OR_OPTIONAL"
    )
    assert "TASK-084" in families["OPTIONAL_OUTER_AUTOMATION"]["upstream_tasks"]
    assert families[
        "CONTINUE_IMPLEMENTATION_SAFE_PUBLICATION_AND_NATIVE_INSTRUCTIONS"
    ]["safe_publisher"] == "ACTIVE"
