from __future__ import annotations

from types import SimpleNamespace

import bridge
from src.aios_bridge import slim_runtime


def test_interactive_context_discards_preflight_from_other_task(monkeypatch):
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
