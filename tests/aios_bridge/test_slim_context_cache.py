from __future__ import annotations

import json
from types import SimpleNamespace

import bridge
from src.aios_bridge import slim_runtime


def test_interactive_context_discards_preflight_from_other_task(monkeypatch):
    """Proof: CROSS_TASK_CONTEXT_CACHE_GUARD_PRESERVED."""
    key = id(bridge)
    slim_runtime._captured_preflight[key] = SimpleNamespace(
        work_path=".ai/tasks/TASK-001.md",
        markers=SimpleNamespace(allowed_paths=("wrong.txt",), context_refs=()),
    )
    monkeypatch.setattr(
        bridge,
        "load_authorization",
        lambda task_id: {
            "executor_id": "antigravity",
            "action": "RUN",
            "status": "ACTIVE",
            "branch": f"ai/task-{task_id:03d}",
        },
    )
    seen = []
    monkeypatch.setattr(bridge, "_slim_cmd_context", lambda args: seen.append(args.task_id))

    bridge.cmd_context(SimpleNamespace(task_id=2))

    assert key not in slim_runtime._captured_preflight
    assert seen == [2]


def test_codex_compact_context_available_after_authorization_and_matches_antigravity(monkeypatch, capsys):
    """Proof: CODEX_COMPACT_CONTEXT_AVAILABLE_AFTER_AUTHORIZATION & CODEX_CONTEXT_EQUALS_ANTIGRAVITY_SHAPE_FOR_EQUIVALENT_AUTH."""
    slim_runtime.install_slim_runtime(bridge)
    key = id(bridge)

    fake_ref = SimpleNamespace(path=".ai/decisions/ADR-067.md")
    machine_ref = SimpleNamespace(path=".ai/roadmaps/AIOS-BRIDGE.md")
    slim_runtime._captured_preflight[key] = SimpleNamespace(
        work_path=".ai/tasks/TASK-096.md",
        markers=SimpleNamespace(
            allowed_paths=("bridge.py", "src/aios_bridge/worker_flow.py"),
            context_refs=(fake_ref, machine_ref),
        ),
    )

    monkeypatch.setattr(bridge, "current_branch", lambda: "ai/task-096")
    monkeypatch.setattr(bridge, "get_artifact_path", lambda p: f"C:/repo/{p}")

    def fake_load_auth_codex(task_id):
        return {
            "executor_id": "codex",
            "action": "RUN",
            "status": "ACTIVE",
            "branch": "ai/task-096",
        }

    monkeypatch.setattr(bridge, "load_authorization", fake_load_auth_codex)

    bridge.cmd_context(SimpleNamespace(task_id=96))
    captured_codex = capsys.readouterr().out
    data_codex = json.loads(captured_codex)

    assert data_codex["task_id"] == "TASK-096"
    assert data_codex["action"] == "RUN"
    assert data_codex["executor_id"] == "codex"
    assert data_codex["allowed_paths"] == ["bridge.py", "src/aios_bridge/worker_flow.py"]
    # Machine-only roadmap prose still omitted! (Proof: ROADMAP_MACHINE_CONTEXT_STILL_OMITTED_FROM_MODEL)
    assert data_codex["semantic_context_files"] == [".ai/decisions/ADR-067.md"]

    # Now run for Antigravity with equivalent auth
    slim_runtime._captured_preflight[key] = SimpleNamespace(
        work_path=".ai/tasks/TASK-096.md",
        markers=SimpleNamespace(
            allowed_paths=("bridge.py", "src/aios_bridge/worker_flow.py"),
            context_refs=(fake_ref, machine_ref),
        ),
    )

    def fake_load_auth_ag(task_id):
        return {
            "executor_id": "antigravity",
            "action": "RUN",
            "status": "ACTIVE",
            "branch": "ai/task-096",
        }

    monkeypatch.setattr(bridge, "load_authorization", fake_load_auth_ag)

    bridge.cmd_context(SimpleNamespace(task_id=96))
    captured_ag = capsys.readouterr().out
    data_ag = json.loads(captured_ag)

    # Codex context shape equals Antigravity context shape!
    data_codex_compare = {**data_codex, "executor_id": "SAME"}
    data_ag_compare = {**data_ag, "executor_id": "SAME"}
    assert data_codex_compare == data_ag_compare
