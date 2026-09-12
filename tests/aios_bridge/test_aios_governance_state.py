"""Focused offline checks for cross-chat roadmap and AIOS-adoption planning state."""
from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROADMAP_FILE = REPO_ROOT / ".ai" / "roadmap-state.yaml"
ADOPTION_FILE = REPO_ROOT / ".ai" / "aios-adoption-state.yaml"
PIN_FILE = (
    REPO_ROOT / ".agents" / "skills" / "aios-worker" / "requirements-aios-renew.txt"
)
EXPECTED_PIN = "2599202afedb0622e9e9bdc7b5a15f34da01cc27"


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


def test_roadmap_has_one_next_and_durable_governance_return():
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
    assert state["active_track"]["id"] == "AIOS_DOWNSTREAM_PARITY"
    assert state["roadmap_sources"] == [
        "docs/POST_M4_PRODUCT_INTELLIGENCE_ROADMAP.md",
        "docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md",
    ]
    assert state["next"]["task_id"] == "TASK-192"
    assert state["next"]["status"] == "NEXT"
    assert state["return_to"] == {
        "id": "PYTHON_AGENT_GOVERNANCE_FOUNDATION",
        "title": "Python Agent Governance Foundation",
        "status": "PENDING_AFTER_ACTIVE_TRACK",
    }
    assert {item["id"]: item["status"] for item in state["pending_commitments"]} == {
        "PYTHON_AGENT_MANIFESTO": "NOT_DONE",
        "PYTHON_AGENT_CONSTITUTION": "NOT_DONE",
        "PYTHON_AGENT_PRODUCT_CONTRACT": "NOT_DONE",
        "CHATGPT_PROJECT_CONTRACT_RECONCILIATION": "NOT_DONE",
    }


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
    assert classification_for_task(state, "TASK-083") == "PORT_GOVERNANCE"
    for task_id in (
        "TASK-086", "TASK-087", "TASK-089", "TASK-090", "TASK-091", "TASK-092",
        "TASK-093", "TASK-094", "TASK-095", "TASK-096", "TASK-097", "TASK-098",
        "TASK-099", "TASK-100", "TASK-102",
    ):
        assert classification_for_task(state, task_id) == "ADOPTED_BY_PIN"
    assert classification_for_task(state, "TASK-101") == "BLOCKED_PENDING_UPSTREAM"
    assert classification_for_task(state, "TASK-103") == "BLOCKED_PENDING_UPSTREAM"
    families = indexed_families(state)
    assert families["PERFORMANCE_CLOSURE"]["source_published"] is False
    assert families["PERFORMANCE_CLOSURE"]["upstream_roadmap_reconciled"] is False
    assert families["AUTHORED_POST_CHECKPOINT_CAPABILITY"]["semantic_pass"] is False
    assert families["AUTHORED_POST_CHECKPOINT_CAPABILITY"]["source_published"] is False
    assert families["OPTIONAL_OUTER_AUTOMATION"]["classification"] == (
        "EXPLICITLY_NOT_APPLICABLE_OR_OPTIONAL"
    )
    assert families[
        "CONTINUE_IMPLEMENTATION_SAFE_PUBLICATION_AND_NATIVE_INSTRUCTIONS"
    ]["safe_publisher"] == "ACTIVE"
