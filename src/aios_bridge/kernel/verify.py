"""AIOS Bridge Kernel v1 Deterministic VERIFY Pipeline (ADR-068 / TASK-098)."""

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import Optional, List, Dict, Any

from src.aios_bridge.kernel.model import KernelTaskRecord


@dataclass
class KernelVerifyResult:
    passed: bool
    exit_code: int
    t0_executed: bool
    t1_executed: bool
    output: str


def run_command_array(cmd_array: List[str], cwd: Path) -> subprocess.CompletedProcess:
    """Executes a command array synchronously using foreground process waiting."""
    if not cmd_array:
        return subprocess.CompletedProcess(cmd_array, 0, "", "")

    # On Windows, resolve python.exe if specified as venv/Scripts/python.exe
    exec_cmd = list(cmd_array)
    first = exec_cmd[0]
    if "/" in first or "\\" in first:
        p = cwd / first
        if p.exists():
            exec_cmd[0] = str(p)

    return subprocess.run(
        exec_cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def run_kernel_verify(record: KernelTaskRecord, repo_root: Optional[Path] = None) -> KernelVerifyResult:
    if repo_root is None:
        repo_root = Path.cwd()

    commands = record.verify_commands or {}
    t0_cmd = commands.get("t0", [])
    t1_cmd = commands.get("t1", [])

    output_lines = []
    t0_executed = False
    t1_executed = False

    # 1. Execute T0 exactly once
    if t0_cmd:
        t0_executed = True
        res0 = run_command_array(t0_cmd, repo_root)
        output_lines.append(f"=== T0 Output (exit={res0.returncode}) ===\n{res0.stdout}\n{res0.stderr}")
        if res0.returncode != 0:
            return KernelVerifyResult(
                passed=False,
                exit_code=res0.returncode,
                t0_executed=True,
                t1_executed=False,
                output="\n".join(output_lines),
            )

    # 2. Execute T1 exactly once (only after T0 passes)
    if t1_cmd:
        t1_executed = True
        res1 = run_command_array(t1_cmd, repo_root)
        output_lines.append(f"=== T1 Output (exit={res1.returncode}) ===\n{res1.stdout}\n{res1.stderr}")
        if res1.returncode != 0:
            return KernelVerifyResult(
                passed=False,
                exit_code=res1.returncode,
                t0_executed=t0_executed,
                t1_executed=True,
                output="\n".join(output_lines),
            )

    return KernelVerifyResult(
        passed=True,
        exit_code=0,
        t0_executed=t0_executed,
        t1_executed=t1_executed,
        output="\n".join(output_lines),
    )
