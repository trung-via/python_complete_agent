from __future__ import annotations

import json
import os
import tempfile

import pytest

from src.agent.messages import MessageRole
from src.agent.replay_engine import ReplayEngine
from src.core.checkpoint_contract import (
    CheckpointEvent,
    CheckpointEventType,
    RunState,
)


def _write_jsonl(path: str, events: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for evt in events:
            f.write(json.dumps(evt) + "\n")


def test_replay_non_existent_file() -> None:
    session = ReplayEngine.reconstruct_session("non_existent.jsonl", "run-missing")
    assert session.run_id == "run-missing"
    assert session.last_state == RunState.PENDING
    assert session.next_sequence_id == 1
    assert session.messages == []
    assert session.completed_tool_calls == {}
    assert session.pending_tool_calls == {}


def test_replay_read_only_invariant() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {
                "run_id": "run-ro",
                "sequence_id": 1,
                "timestamp": 100.0,
                "event_type": "RUN_STARTED",
                "payload": {"system_prompt": "s1", "user_prompt": "u1"},
            }
        ]
        _write_jsonl(db_path, events)

        # Get initial file mtime / size
        initial_size = os.path.getsize(db_path)

        session = ReplayEngine.reconstruct_session(db_path, "run-ro")

        # File size must be identical (no mutations)
        assert os.path.getsize(db_path) == initial_size
        assert session.run_id == "run-ro"
        assert session.last_state == RunState.RUNNING


def test_replay_reconstructs_messages_and_prompts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {
                "run_id": "run-msg",
                "sequence_id": 1,
                "timestamp": 100.0,
                "event_type": "RUN_STARTED",
                "payload": {"system_prompt": "You are helpful.", "user_prompt": "Hello!"},
            },
            {
                "run_id": "run-msg",
                "sequence_id": 2,
                "timestamp": 101.0,
                "event_type": "LLM_REQUESTED",
                "payload": {"iteration": 1},
            },
            {
                "run_id": "run-msg",
                "sequence_id": 3,
                "timestamp": 102.0,
                "event_type": "LLM_RESPONDED",
                "payload": {
                    "iteration": 1,
                    "content": "Hello! How can I help you?",
                    "num_tool_calls": 0,
                    "tool_calls": [],
                },
            },
        ]
        _write_jsonl(db_path, events)

        session = ReplayEngine.reconstruct_session(db_path, "run-msg")

        assert session.run_id == "run-msg"
        assert session.system_prompt == "You are helpful."
        assert session.user_prompt == "Hello!"
        assert session.last_state == RunState.COMPLETED
        assert session.next_sequence_id == 4

        # Messages reconstructed: System, User, Assistant
        assert len(session.messages) == 3
        assert session.messages[0].role == MessageRole.SYSTEM
        assert session.messages[0].content == "You are helpful."
        assert session.messages[1].role == MessageRole.USER
        assert session.messages[1].content == "Hello!"
        assert session.messages[2].role == MessageRole.ASSISTANT
        assert session.messages[2].content == "Hello! How can I help you?"


def test_replay_multi_tool_call_partial_completion() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {
                "run_id": "run-multi",
                "sequence_id": 1,
                "timestamp": 100.0,
                "event_type": "RUN_STARTED",
                "payload": {"system_prompt": "sys", "user_prompt": "do work"},
            },
            {
                "run_id": "run-multi",
                "sequence_id": 2,
                "timestamp": 101.0,
                "event_type": "LLM_REQUESTED",
                "payload": {"iteration": 1},
            },
            {
                "run_id": "run-multi",
                "sequence_id": 3,
                "timestamp": 102.0,
                "event_type": "LLM_RESPONDED",
                "payload": {
                    "iteration": 1,
                    "content": "Executing tools...",
                    "num_tool_calls": 3,
                    "tool_calls": [
                        {"call_id": "c1", "name": "t_read", "arguments": {"path": "a.txt"}, "idempotency_key": "idem-c1"},
                        {"call_id": "c2", "name": "t_write", "arguments": {"path": "b.txt"}, "idempotency_key": "idem-c2"},
                        {"call_id": "c3", "name": "t_fetch", "arguments": {"url": "http://x"}, "idempotency_key": "idem-c3"},
                    ],
                },
            },
            {
                "run_id": "run-multi",
                "sequence_id": 4,
                "timestamp": 103.0,
                "event_type": "TOOL_RESULT_RECEIVED",
                "payload": {
                    "call_id": "c1",
                    "tool_name": "t_read",
                    "status": "success",
                    "result": {"data": "file content a"},
                    "iteration_complete": False,
                },
            },
        ]
        _write_jsonl(db_path, events)

        session = ReplayEngine.reconstruct_session(db_path, "run-multi")

        assert session.last_state == RunState.TOOL_EXECUTING
        assert session.next_sequence_id == 5

        # Completed: c1 ONLY
        assert set(session.completed_tool_calls.keys()) == {"c1"}
        assert session.completed_tool_calls["c1"].data == "file content a"

        # Pending: c2 and c3 with exact attributes
        assert set(session.pending_tool_calls.keys()) == {"c2", "c3"}

        c2_call = session.pending_tool_calls["c2"]
        assert c2_call.call_id == "c2"
        assert c2_call.run_id == "run-multi"
        assert c2_call.name == "t_write"
        assert c2_call.arguments == {"path": "b.txt"}
        assert c2_call.idempotency_key == "idem-c2"

        c3_call = session.pending_tool_calls["c3"]
        assert c3_call.call_id == "c3"
        assert c3_call.run_id == "run-multi"
        assert c3_call.name == "t_fetch"
        assert c3_call.arguments == {"url": "http://x"}
        assert c3_call.idempotency_key == "idem-c3"


def test_replay_interleaved_runs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "checkpoints.jsonl")
        events = [
            {"run_id": "run-A", "sequence_id": 1, "timestamp": 100.0, "event_type": "RUN_STARTED", "payload": {"user_prompt": "A"}},
            {"run_id": "run-B", "sequence_id": 1, "timestamp": 101.0, "event_type": "RUN_STARTED", "payload": {"user_prompt": "B"}},
            {"run_id": "run-A", "sequence_id": 2, "timestamp": 102.0, "event_type": "LLM_REQUESTED", "payload": {}},
            {"run_id": "run-B", "sequence_id": 2, "timestamp": 103.0, "event_type": "LLM_REQUESTED", "payload": {}},
            {"run_id": "run-A", "sequence_id": 3, "timestamp": 104.0, "event_type": "LLM_RESPONDED", "payload": {"num_tool_calls": 0, "content": "Done A"}},
        ]
        _write_jsonl(db_path, events)

        sess_A = ReplayEngine.reconstruct_session(db_path, "run-A")
        assert sess_A.user_prompt == "A"
        assert sess_A.last_state == RunState.COMPLETED
        assert sess_A.next_sequence_id == 4

        sess_B = ReplayEngine.reconstruct_session(db_path, "run-B")
        assert sess_B.user_prompt == "B"
        assert sess_B.last_state == RunState.LLM_WAITING
        assert sess_B.next_sequence_id == 3
