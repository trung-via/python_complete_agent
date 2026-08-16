"""Unit tests for External Brain Prompt and Message rendering."""
from __future__ import annotations

import pytest

from src.aios_bridge.external_brain import (
    BrainOperation,
    BrainOutputType,
    BrainRole,
    ContextItem,
    ContextKind,
    ContractValidationError,
    ModelRequest,
    REQUIRED_SECTIONS,
    render_context_item,
    render_messages,
)


def test_render_messages_structure_and_governance():
    """Prompt renderer includes role, operation, proposal-only governance, and required sections."""
    task_item = ContextItem(kind=ContextKind.TASK, content="Implement feature X", path="task.md")
    req = ModelRequest(
        schema_version="1",
        request_id="req-001",
        task_id="TASK-016",
        role=BrainRole.ARCHITECT,
        operation=BrainOperation.PLAN,
        instruction="Plan the implementation for TASK-016.",
        output_format=BrainOutputType.PLAN,
        context=(task_item,),
        provider="minimax",
        model="MiniMax-M3",
    )

    messages = render_messages(req)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    system_content = messages[0]["content"]
    assert "PROPOSAL-ONLY" in system_content
    assert "NO execution authority" in system_content
    assert "cannot read or write filesystem files" in system_content
    for sec in REQUIRED_SECTIONS[BrainOutputType.PLAN]:
        assert f"## {sec}" in system_content
    assert "PLAN" in system_content

    user_content = messages[1]["content"]
    assert "## Task ID\nTASK-016" in user_content
    assert "## Instruction\nPlan the implementation for TASK-016." in user_content
    assert render_context_item(task_item) in user_content


def test_render_messages_determinism():
    """Same ModelRequest produces identical message lists."""
    t = ContextItem(kind=ContextKind.TASK, content="Task")
    s = ContextItem(kind=ContextKind.SOURCE, content="Code", path="a.py")
    req = ModelRequest(
        schema_version="1",
        request_id="req-002",
        task_id="TASK-016",
        role=BrainRole.CODER,
        operation=BrainOperation.GENERATE_PATCH,
        instruction="Propose a patch.",
        output_format=BrainOutputType.PATCH_PROPOSAL,
        context=(t, s),
        provider="minimax",
        model="MiniMax-M3",
    )

    m1 = render_messages(req)
    m2 = render_messages(req)
    assert m1 == m2


def test_render_messages_all_operations_contain_correct_sections():
    """Each operation specifies its exact required sections in the system prompt."""
    ops_and_sections = [
        (BrainOperation.PLAN, BrainRole.ARCHITECT, BrainOutputType.PLAN),
        (BrainOperation.GENERATE_PATCH, BrainRole.CODER, BrainOutputType.PATCH_PROPOSAL),
        (BrainOperation.DIAGNOSE_FAILURE, BrainRole.DEBUGGER, BrainOutputType.DIAGNOSIS),
        (BrainOperation.REVIEW_PATCH, BrainRole.REVIEWER, BrainOutputType.REVIEW),
    ]

    for op, role, out_type in ops_and_sections:
        t = ContextItem(kind=ContextKind.TASK, content="Task")
        req = ModelRequest(
            schema_version="1",
            request_id="req-test",
            task_id="TASK-016",
            role=role,
            operation=op,
            instruction="Test",
            output_format=out_type,
            context=(t,),
            provider="minimax",
            model="MiniMax-M3",
        )
        messages = render_messages(req)
        sys_prompt = messages[0]["content"]
        for sec in REQUIRED_SECTIONS[out_type]:
            assert f"## {sec}" in sys_prompt


def test_render_messages_invalid_request():
    """Non-ModelRequest argument raises ContractValidationError."""
    with pytest.raises(ContractValidationError):
        render_messages({"invalid": "dict"})  # type: ignore
