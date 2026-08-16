"""Unit tests for the manual External Brain PLAN runner (TASK-017 / ADR-008)."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.aios_bridge.external_brain import (
    BrainOutputType,
    BrainRole,
    ContextItem,
    ContextKind,
    ContractValidationError,
    GatewayResult,
    ModelGateway,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
    TransportRequest,
    TransportResult,
    UsageRecord,
)
from src.aios_bridge.external_brain.runner import (
    build_plan_request,
    execute_plan_runner,
    extract_task_id,
    format_safe_plan_output,
    load_explicit_context,
    parse_context_spec,
)
import scripts.aios_external_brain_plan as cli_module


class MockTransport:
    """Mock transport tracking sent requests without making live network calls."""

    def __init__(self, result: TransportResult | None = None) -> None:
        self.sent_requests: list[TransportRequest] = []
        self.result = result or TransportResult(
            status_code=200,
            body={
                "id": "mock-plan-res-001",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": (
                                "# PLAN\n\n"
                                "## SUMMARY\n"
                                "Mock plan summary for testing.\n\n"
                                "## STEPS\n"
                                "1. Step one\n"
                                "2. Step two\n\n"
                                "## FILES\n"
                                "1. src/app.py\n\n"
                                "## TESTS\n"
                                "1. pytest tests/\n\n"
                                "## RISKS\n"
                                "1. Low risk\n"
                            ),
                            "reasoning_content": "Secret hidden thoughts that must be ignored",
                        },
                    }
                ],
                "usage": {"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700},
            },
            latency_ms=150,
            provider_request_id="mock-plan-res-001",
        )

    async def send(self, request: TransportRequest) -> TransportResult:
        self.sent_requests.append(request)
        return self.result


def test_parse_context_spec():
    """parse_context_spec parses 'KIND:PATH' and rejects invalid formats and kinds."""
    # Valid specs
    kind, path = parse_context_spec("CONTRACT:docs/ADR.md")
    assert kind == ContextKind.CONTRACT
    assert path == "docs/ADR.md"

    kind, path = parse_context_spec("source:src/aios_bridge/gateway.py")
    assert kind == ContextKind.SOURCE
    assert path == "src/aios_bridge/gateway.py"

    kind, path = parse_context_spec("TEST:tests/test_gateway.py")
    assert kind == ContextKind.TEST
    assert path == "tests/test_gateway.py"

    # Invalid format (no colon)
    with pytest.raises(ContractValidationError, match="Invalid context spec format"):
        parse_context_spec("just_a_path.py")

    # Invalid format (empty kind)
    with pytest.raises(ContractValidationError, match="both KIND and PATH must be non-empty"):
        parse_context_spec(":src/app.py")

    # Invalid kind
    with pytest.raises(ContractValidationError, match="Unrecognized ContextKind"):
        parse_context_spec("INVALID_KIND:src/app.py")


def test_extract_task_id_valid_and_invalid():
    """extract_task_id enforces case-sensitive TASK-<digits> format and fails closed on invalid filenames."""
    assert extract_task_id("TASK-017.md") == "TASK-017"
    assert extract_task_id(".ai/tasks/TASK-001.md") == "TASK-001"
    assert extract_task_id("path/to/TASK-999.md") == "TASK-999"

    # Invalid task filenames (including lowercase/mixed case which must fail)
    invalid_filenames = [
        "task-999.md",
        "Task-017.md",
        "task.md",
        "TASK.md",
        "MY_TASK-017.md",
        "TASK-abc.md",
        "README.md",
        "",
    ]
    for name in invalid_filenames:
        with pytest.raises(ContractValidationError, match="Invalid task identity"):
            extract_task_id(name)


def test_load_explicit_context_reads_only_specified_files(tmp_path: Path):
    """load_explicit_context reads only explicitly given files, no repo crawl or globbing."""
    task_file = tmp_path / "TASK-017.md"
    task_file.write_text("# Task 017 content", encoding="utf-8")

    contract_file = tmp_path / "ADR.md"
    contract_file.write_text("# ADR contract content", encoding="utf-8")

    source_file = tmp_path / "module.py"
    source_file.write_text("def run(): pass", encoding="utf-8")

    # Extra file in directory that should NOT be loaded
    stray_file = tmp_path / "stray.py"
    stray_file.write_text("secrets = 123", encoding="utf-8")

    items = load_explicit_context(
        task_file=task_file,
        context_specs=[f"CONTRACT:{contract_file}", f"SOURCE:{source_file}"],
        base_dir=tmp_path,
    )

    assert len(items) == 3
    assert items[0].kind == ContextKind.TASK
    assert items[0].content == "# Task 017 content"
    assert items[1].kind == ContextKind.CONTRACT
    assert items[1].content == "# ADR contract content"
    assert items[2].kind == ContextKind.SOURCE
    assert items[2].content == "def run(): pass"

    # Ensure stray file was NOT loaded
    loaded_refs = [it.path for it in items]
    assert str(stray_file) not in loaded_refs


def test_load_explicit_context_missing_task_file_fails(tmp_path: Path):
    """Missing task file raises ContractValidationError."""
    missing_task = tmp_path / "TASK-999.md"
    with pytest.raises(ContractValidationError, match="Task file not found"):
        load_explicit_context(task_file=missing_task, base_dir=tmp_path)


def test_load_explicit_context_missing_context_file_fails(tmp_path: Path):
    """Missing context file raises ContractValidationError."""
    task_file = tmp_path / "TASK-017.md"
    task_file.write_text("# Task", encoding="utf-8")

    with pytest.raises(ContractValidationError, match="Context file not found"):
        load_explicit_context(
            task_file=task_file,
            context_specs=["SOURCE:non_existent_file.py"],
            base_dir=tmp_path,
        )


@pytest.mark.asyncio
async def test_execute_plan_runner_invalid_task_id_fails_closed(tmp_path: Path):
    """Invalid task filename fails closed with non-zero exit before any network call."""
    invalid_task_file = tmp_path / "invalid_task_name.md"
    invalid_task_file.write_text("# Task", encoding="utf-8")

    mock_transport = MockTransport()
    code, output = await execute_plan_runner(
        task_file=invalid_task_file,
        api_key="test-key",
        custom_transport=mock_transport,
    )

    assert code == 1
    assert "Task identity validation failed" in output
    assert len(mock_transport.sent_requests) == 0


@pytest.mark.asyncio
async def test_execute_plan_runner_locked_provider_and_model_enforcement(tmp_path: Path):
    """Non-locked provider or model fails closed before network call."""
    task_file = tmp_path / "TASK-017.md"
    task_file.write_text("# Task", encoding="utf-8")

    mock_transport = MockTransport()

    # Invalid provider
    code, output = await execute_plan_runner(
        task_file=task_file,
        provider_id="openai",
        api_key="test-key",
        custom_transport=mock_transport,
    )
    assert code == 1
    assert "Invalid provider 'openai'" in output
    assert len(mock_transport.sent_requests) == 0

    # Invalid model
    code, output = await execute_plan_runner(
        task_file=task_file,
        model="gpt-4o",
        api_key="test-key",
        custom_transport=mock_transport,
    )
    assert code == 1
    assert "Invalid model 'gpt-4o'" in output
    assert len(mock_transport.sent_requests) == 0


@pytest.mark.asyncio
async def test_execute_plan_runner_missing_api_key_fails_closed(tmp_path: Path):
    """Missing API key fails preflight check before any network call."""
    task_file = tmp_path / "TASK-017.md"
    task_file.write_text("# Task", encoding="utf-8")

    with patch.dict("os.environ", {}, clear=True):
        code, output = await execute_plan_runner(
            task_file=task_file,
            api_key="",
        )

    assert code == 1
    assert "Missing MiniMax API key" in output


@pytest.mark.asyncio
async def test_execute_plan_runner_sensitive_context_fails_closed(tmp_path: Path):
    """M2 ContextBuilder rejects sensitive file paths (.env) before network call."""
    task_file = tmp_path / "TASK-017.md"
    task_file.write_text("# Task", encoding="utf-8")

    sensitive_file = tmp_path / ".env"
    sensitive_file.write_text("AIOS_SECRET=12345", encoding="utf-8")

    mock_transport = MockTransport()
    code, output = await execute_plan_runner(
        task_file=task_file,
        context_specs=[f"SOURCE:{sensitive_file}"],
        api_key="test-key",
        custom_transport=mock_transport,
    )

    assert code == 1
    assert "Context build failed" in output
    # Zero transport calls
    assert len(mock_transport.sent_requests) == 0


@pytest.mark.asyncio
async def test_execute_plan_runner_context_budget_overflow_fails_closed(tmp_path: Path):
    """Exceeding context budget fails closed without invoking transport."""
    task_file = tmp_path / "TASK-017.md"
    task_file.write_text("# Task with long text " * 500, encoding="utf-8")

    mock_transport = MockTransport()
    code, output = await execute_plan_runner(
        task_file=task_file,
        max_context_tokens=50,  # Tiny budget
        api_key="test-key",
        custom_transport=mock_transport,
    )

    assert code == 1
    assert "Context build failed" in output
    assert len(mock_transport.sent_requests) == 0


@pytest.mark.asyncio
async def test_execute_plan_runner_successful_execution_and_safe_output(tmp_path: Path):
    """Full execution flow produces exit 0 and safe telemetry without secrets or reasoning."""
    task_file = tmp_path / "TASK-017.md"
    task_file.write_text("# TASK-017\nDescription of plan task", encoding="utf-8")

    contract_file = tmp_path / "ADR-008.md"
    contract_file.write_text("# ADR-008\nContract lock", encoding="utf-8")

    ledger_file = tmp_path / "logs" / "usage.jsonl"
    mock_transport = MockTransport()

    secret_key = "sk-super-secret-key-12345678"

    code, output = await execute_plan_runner(
        task_file=task_file,
        context_specs=[f"CONTRACT:{contract_file}"],
        api_key=secret_key,
        model="MiniMax-M3",
        timeout_seconds=90.0,
        max_output_tokens=8192,
        ledger_path=ledger_file,
        custom_transport=mock_transport,
    )

    assert code == 0
    assert len(mock_transport.sent_requests) == 1
    sent = mock_transport.sent_requests[0]
    assert sent.timeout_seconds == 90.0
    assert sent.payload["model"] == "MiniMax-M3"
    assert sent.payload["max_completion_tokens"] == 8192

    # Verify output formatting
    assert "AIOS EXTERNAL BRAIN — PLAN EXECUTION RESULT" in output
    assert "Status:               SUCCESS" in output
    assert "Provider:             minimax" in output
    assert "Model:                MiniMax-M3" in output
    assert "VALIDATED PLAN CONTENT" in output
    assert "Mock plan summary for testing" in output

    # Secret isolation verification
    assert secret_key not in output
    assert "Secret hidden thoughts" not in output

    # Ledger was written
    assert ledger_file.exists()
    assert "Ledger Persisted:     True" in output


@pytest.mark.asyncio
async def test_execute_plan_runner_provider_failure_redacts_error_message(tmp_path: Path):
    """Normalized provider failure returns non-zero and does NOT emit provider error_message text."""
    task_file = tmp_path / "TASK-017.md"
    task_file.write_text("# Task", encoding="utf-8")

    sensitive_error_msg = "Database connection string leaked: postgres://user:secret@internal:5432/db"

    mock_transport = MockTransport(
        result=TransportResult(
            status_code=429,
            body={"error": sensitive_error_msg},
            latency_ms=80,
        )
    )

    code, output = await execute_plan_runner(
        task_file=task_file,
        api_key="test-key",
        custom_transport=mock_transport,
    )

    assert code == 1
    assert "Status:               RATE_LIMITED" in output
    assert "Error Code:           RATE_LIMITED" in output
    # Regression check: error_message must NOT be printed in output
    assert sensitive_error_msg not in output
    assert "Error Message:" not in output
    assert len(mock_transport.sent_requests) == 1


def test_cli_argument_parsing_rejects_api_key_provider_model(tmp_path: Path):
    """CLI parser accepts supported flags and rejects removed options (--api-key, --provider, --model)."""
    args = cli_module.parse_args([
        "--task-file", "tasks/TASK-017.md",
        "--context", "CONTRACT:ADR.md",
        "--context", "SOURCE:src/app.py",
        "--max-context-tokens", "40000",
        "--max-output-tokens", "4096",
        "--timeout-seconds", "120.0",
        "--ledger-file", "logs/usage.jsonl",
    ])

    assert args.task_file == "tasks/TASK-017.md"
    assert args.contexts == ["CONTRACT:ADR.md", "SOURCE:src/app.py"]
    assert args.max_context_tokens == 40000
    assert args.max_output_tokens == 4096
    assert args.timeout_seconds == 120.0
    assert args.ledger_file == "logs/usage.jsonl"

    # Verify removed flags cause SystemExit / unrecognized arguments
    for removed_flag in ["--api-key", "--provider", "--model"]:
        with pytest.raises(SystemExit):
            cli_module.parse_args(["--task-file", "tasks/TASK-017.md", removed_flag, "foo"])
