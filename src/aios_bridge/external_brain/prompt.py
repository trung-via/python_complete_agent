"""Deterministic prompt and message rendering for External Brain ModelRequest."""
from __future__ import annotations

from .contracts import BrainOperation, BrainOutputType, BrainRole, ModelRequest
from .context import render_context_item
from .errors import ContractValidationError
from .validation import REQUIRED_SECTIONS


def _build_system_message(role: BrainRole, operation: BrainOperation, output_format: BrainOutputType) -> str:
    """Constructs the deterministic system prompt establishing governance and format boundaries."""
    required_sections = REQUIRED_SECTIONS.get(output_format, ())
    sections_formatted = "\n".join(f"- `## {s}`" for s in required_sections)

    return f"""You are an External Brain AI advisor acting in the role of {role.value}.
Your operation is: {operation.value}.

GOVERNANCE & SAFETY INVARIANTS:
1. You are a PROPOSAL-ONLY reasoning advisor.
2. You have NO execution authority: you cannot read or write filesystem files directly, execute shell commands, run Git commands, browse the web, or apply patches.
3. You must produce strictly structured markdown proposal content.
4. Do NOT output tool calls, function calls, or execution scripts.
5. Your output MUST be in {output_format.value} format and include all required section headers:
{sections_formatted}"""


def _build_user_message(request: ModelRequest) -> str:
    """Constructs the deterministic user prompt containing task, instruction, and rendered context items."""
    parts: list[str] = [
        f"## Task ID\n{request.task_id}",
        f"## Instruction\n{request.instruction}",
    ]

    if request.context:
        rendered_contexts = [render_context_item(item) for item in request.context]
        context_block = "\n\n".join(rendered_contexts)
        parts.append(f"## Context Items\n{context_block}")
    else:
        parts.append("## Context Items\n(No context items provided)")

    parts.append(
        f"## Output Requirements\n"
        f"Output MUST be in {request.output_format.value} format conforming to operation {request.operation.value}."
    )

    return "\n\n".join(parts)


def render_messages(request: ModelRequest) -> list[dict[str, str]]:
    """
    Renders a ModelRequest into a deterministic provider-neutral list of chat messages.
    Pure function with zero side-effects and zero credential inclusion.
    """
    if not isinstance(request, ModelRequest):
        raise ContractValidationError(f"request must be a ModelRequest instance, got: {type(request)}")

    system_content = _build_system_message(request.role, request.operation, request.output_format)
    user_content = _build_user_message(request)

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
