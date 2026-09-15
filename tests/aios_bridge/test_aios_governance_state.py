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
EXPECTED_PIN = "652b00b103dd50e2a550dd0ec0fe4063e69631b7"
TASK_201_HISTORICAL_PIN = "f0237a3b98985ce6ebbaf41af1e06fa3eb4e998e"
UPSTREAM_PLANNING_CHECKPOINT = "e95d12122f35bf4e224dbbb28be1866c8250c069"
TASK_192_SOURCE_SHA = "dcb7432abc58ed983e6c26d5456ace1423e49981"
TASK_194_SOURCE_SHA = "e0d8998ee004fda80ca3fbc3de4eb0afb59160a5"
TASK_196_SOURCE_SHA = "4f6d91858c93192f497342315c4650e30b0a2718"
TASK_199_SOURCE_SHA = "702e85e9e77a556f3716717ccaa186919b1a9dab"
ACTIVE_TRACK_ID = "AIOS_FULL_DOWNSTREAM_ADOPTION_AND_GOVERNANCE_REBUILD"
NEXT_MILESTONE_ID = "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_1"
APPROVED_PENDING_SEQUENCE = [
    "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_1",
    "FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_2",
    "FULL_AIOS_DOWNSTREAM_CONFORMANCE",
    "PROJECT_CONTRACT_REBUILD",
    "GOVERNANCE_FOUNDATION_CLOSURE_AND_P7_RETURN",
]


def load_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def indexed_families(state: dict) -> dict[str, dict]:
    return {family["id"]: family for family in state["capability_families"]}


def package_capability_for_task(state: dict, task_id: str) -> str:
    matches = [
        family["package_capability_availability"]
        for family in state["capability_families"]
        if task_id in family["upstream_tasks"]
    ]
    assert len(matches) == 1
    return matches[0]


def repository_binding_for_task(state: dict, task_id: str) -> str:
    matches = [
        family["repository_binding_activation"]
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


def test_roadmap_has_one_active_track_and_unique_next():
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
    assert state["active_track"]["id"] == ACTIVE_TRACK_ID
    assert state["active_track"]["status"] == "ACTIVE"
    assert values_for_key(state, "status").count("ACTIVE") == 1
    assert state["roadmap_sources"] == [
        "docs/POST_M4_PRODUCT_INTELLIGENCE_ROADMAP.md",
        "docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md",
    ]
    assert state["next"]["id"] == NEXT_MILESTONE_ID
    assert state["next"]["status"] == "NEXT"
    assert values_for_key(state, "status").count("NEXT") == 1

    pending = state["pending_commitments"]
    pending_ids = [item["id"] for item in pending]
    assert pending_ids == APPROVED_PENDING_SEQUENCE
    assert len(pending_ids) == len(set(pending_ids))
    assert all(item["status"] == "NOT_DONE" for item in pending)
    assert state["next"]["id"] == pending[0]["id"]
    assert state["next"]["title"] == pending[0]["title"]

    superseded = {item["id"]: item for item in state.get("superseded_commitments", [])}
    assert (
        superseded["CHATGPT_PROJECT_CONTRACT_RECONCILIATION"]["status"]
        == "SUPERSEDED"
    )


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
        "track_id": "PYTHON_AGENT_GOVERNANCE_FOUNDATION",
        "milestone_id": "PYTHON_AGENT_MANIFESTO",
        "title": "Python Agent Manifesto",
        "status": "DONE",
        "source_sha": TASK_194_SOURCE_SHA,
    }
    assert completed["TASK-196"] == {
        "task_id": "TASK-196",
        "track_id": "PYTHON_AGENT_GOVERNANCE_FOUNDATION",
        "milestone_id": "PYTHON_AGENT_CONSTITUTION",
        "title": "Python Agent Constitution",
        "status": "DONE",
        "source_sha": TASK_196_SOURCE_SHA,
    }
    assert completed["TASK-199"] == {
        "task_id": "TASK-199",
        "track_id": "PYTHON_AGENT_GOVERNANCE_FOUNDATION",
        "milestone_id": "PYTHON_AGENT_PRODUCT_CONTRACT",
        "title": "Python Agent Product Contract",
        "status": "DONE",
        "source_sha": TASK_199_SOURCE_SHA,
    }
    assert completed["TASK-204"] == {
        "task_id": "TASK-204",
        "track_id": ACTIVE_TRACK_ID,
        "milestone_id": "AIOS_DOWNSTREAM_ADOPTION_POLICY_RECONCILIATION",
        "title": "AIOS downstream-adoption policy reconciliation",
        "status": "DONE",
        "upstream_source_sha": EXPECTED_PIN,
        "boundary": "NO_PHASE_1_OR_PHASE_2_REPOSITORY_BINDING_ACTIVATED",
    }

    upstream = state["upstream_recovery"]
    assert upstream["status"] == "ADOPTED_BY_PIN"
    assert upstream["blocking_current_track"] is False
    assert upstream["recovery_kind"] == "NON_PRODUCT_CONTROL_PLANE"
    assert upstream["recovery_task"] == "TASK-198"
    assert [item["task_id"] for item in upstream["items"]] == [
        "TASK-101",
        "TASK-103",
    ]
    assert all(
        item["status"] == "ADOPTED_BY_PIN"
        and item["blocking_current_track"] is False
        for item in upstream["items"]
    )
    assert upstream["downstream_pin"] == "a3b723b49cd65677f548c5694a52a6fc006a9e2a"
    assert "does not advance" in upstream["roadmap_effect"]

    migration = state["historical_upstream_migration"]
    assert migration["status"] == "SUPERSEDED_PIN_HISTORY"
    assert migration["blocking_current_track"] is False
    assert migration["migration_kind"] == "NON_PRODUCT_AIOS_MIGRATION"
    assert migration["migration_task"] == "TASK-201"
    assert migration["historical_downstream_pin"] == TASK_201_HISTORICAL_PIN
    assert migration["runtime_authority"] is False
    assert migration["superseded_by"] == "TASK-204"
    assert "does not advance" in migration["roadmap_effect"]

    reconciliation = state["adoption_policy_reconciliation"]
    assert reconciliation["status"] == "DONE"
    assert reconciliation["migration_task"] == "TASK-204"
    assert reconciliation["downstream_pin"] == EXPECTED_PIN
    assert reconciliation["upstream_provenance"] == [
        "TASK-114", "TASK-115", "TASK-116",
    ]
    assert reconciliation["closed_commitment"] == (
        "AIOS_DOWNSTREAM_ADOPTION_POLICY_RECONCILIATION"
    )
    assert reconciliation["next_commitment"] == NEXT_MILESTONE_ID
    assert reconciliation["repository_binding_activation"] == "NONE"
    assert "does not implement" in reconciliation["roadmap_effect"]

    assert state["authority"]["owner"] == "BRAIN"
    assert state["authority"]["auto_advance_from_runtime_or_worker_state"] is False


def test_adoption_registry_pin_audit_authority_and_dimensions_are_explicit():
    state = load_yaml(ADOPTION_FILE)
    requirement = PIN_FILE.read_text(encoding="utf-8").strip()
    assert requirement.endswith("@" + EXPECTED_PIN)
    assert state["downstream_pin"]["commit"] == EXPECTED_PIN
    assert state["upstream_audit"] == {
        "checkpoint": EXPECTED_PIN,
        "through_authored_task": "TASK-116",
        "checkpoint_role": "REVIEWED_SOURCE_PUBLISHED_PROVENANCE",
        "checkpoint_is_runtime_authority": False,
        "review": "REVIEW-116-001",
        "review_outcome": "PRIMARY_PASS",
        "source_published": True,
        "prior_planning_checkpoint": UPSTREAM_PLANNING_CHECKPOINT,
        "provenance": [
            {
                "task_id": "TASK-114",
                "role": "DOWNSTREAM_PORTABILITY_POLICY",
                "activates_repository_binding": False,
            },
            {
                "task_id": "TASK-115",
                "role": "PINNED_PUBLICATION_HARDENING",
                "activates_repository_binding": False,
            },
            {
                "task_id": "TASK-116",
                "role": "GOVERNANCE_POLICY_INTEGRATION",
                "activates_repository_binding": False,
            },
        ],
    }
    assert state["authority"]["engineering_truth"] is False
    dimensions = state["classification_dimensions"]
    assert set(dimensions["package_capability_availability"]) == {
        "ADOPTED_BY_PIN",
        "PORT_GOVERNANCE",
        "BLOCKED_PENDING_UPSTREAM",
    }
    assert set(dimensions["repository_binding_activation"]) == {
        "ACTIVE",
        "REQUIRED_PENDING",
        "NOT_REQUIRED",
    }


def test_relevant_upstream_tasks_have_distinct_package_and_binding_dimensions():
    state = load_yaml(ADOPTION_FILE)

    all_audited_tasks = [
        "TASK-064", "TASK-065", "TASK-066", "TASK-067", "TASK-068", "TASK-069",
        "TASK-070", "TASK-071", "TASK-072", "TASK-073", "TASK-074", "TASK-075",
        "TASK-076", "TASK-077", "TASK-078", "TASK-079", "TASK-080", "TASK-081",
        "TASK-083", "TASK-084", "TASK-085", "TASK-086", "TASK-087", "TASK-088",
        "TASK-089", "TASK-090", "TASK-091", "TASK-092", "TASK-093", "TASK-094",
        "TASK-095", "TASK-096", "TASK-097", "TASK-098", "TASK-099", "TASK-100",
        "TASK-101", "TASK-102", "TASK-103", "TASK-104", "TASK-105", "TASK-106",
        "TASK-107", "TASK-108", "TASK-110", "TASK-111", "TASK-112", "TASK-113",
        "TASK-114", "TASK-115", "TASK-116",
    ]

    for task_id in all_audited_tasks:
        pkg_cap = package_capability_for_task(state, task_id)
        if task_id in ("TASK-083", "TASK-114", "TASK-116"):
            assert pkg_cap == "PORT_GOVERNANCE"
        else:
            assert pkg_cap == "ADOPTED_BY_PIN"

    assert repository_binding_for_task(state, "TASK-069") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-071") == "NOT_REQUIRED"

    assert repository_binding_for_task(state, "TASK-070") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-072") == "NOT_REQUIRED"

    for task_id in ("TASK-066", "TASK-068", "TASK-073", "TASK-074", "TASK-084"):
        assert repository_binding_for_task(state, task_id) == "REQUIRED_PENDING"

    assert repository_binding_for_task(state, "TASK-104") == "ACTIVE"
    assert repository_binding_for_task(state, "TASK-105") == "ACTIVE"

    for task_id in ("TASK-107", "TASK-108", "TASK-110", "TASK-111", "TASK-112"):
        assert repository_binding_for_task(state, task_id) == "REQUIRED_PENDING"

    assert repository_binding_for_task(state, "TASK-113") == "REQUIRED_PENDING"
    assert repository_binding_for_task(state, "TASK-114") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-115") == "NOT_REQUIRED"
    assert repository_binding_for_task(state, "TASK-116") == "NOT_REQUIRED"

    families = indexed_families(state)

    assert families["PACKAGE_RUNTIME_OPERATOR_HARDENING"]["upstream_tasks"] == [
        "TASK-069", "TASK-071",
    ]
    assert families["PACKAGE_PUBLICATION_CONTROL_HARDENING"]["upstream_tasks"] == [
        "TASK-070", "TASK-072",
    ]

    assert families["AUDITED_A1_A2_A3_A6_AUTOMATION_CARRIERS"]["upstream_tasks"] == [
        "TASK-066", "TASK-068", "TASK-073", "TASK-074", "TASK-084",
    ]

    ingress = families["RECOVERED_BRAIN_AUTHORING_INGRESS"]
    assert ingress["upstream_tasks"] == ["TASK-104", "TASK-105"]
    assert ingress["carrier"] == ".agents/skills/aios-worker/scripts/aios_brain_ingress.py"
    assert ingress["repository_binding_activation"] == "ACTIVE"

    assert families["REPOSITORY_SPECIFIC_OUTER_AUTOMATION"]["upstream_tasks"] == [
        "TASK-107", "TASK-108", "TASK-110", "TASK-111", "TASK-112",
    ]
    assert families["TERMINAL_ATTENTION_PACKAGE_COMPATIBILITY"]["upstream_tasks"] == [
        "TASK-113",
    ]
    safe_publication = families["SAFE_PUBLICATION_ZERO_DELTA_HARDENING"]
    assert safe_publication["upstream_tasks"] == ["TASK-115"]
    assert safe_publication["package_capability_availability"] == "ADOPTED_BY_PIN"
    assert safe_publication["repository_binding_activation"] == "NOT_REQUIRED"

    policy = families["DOWNSTREAM_PORTABILITY_POLICY_PROVENANCE"]
    assert policy["upstream_tasks"] == ["TASK-114", "TASK-116"]
    assert policy["package_capability_availability"] == "PORT_GOVERNANCE"
    assert policy["repository_binding_activation"] == "NOT_REQUIRED"


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
