"""AIOS Bridge Kernel v1 Compact Context Generator (ADR-068 / TASK-098)."""

from pathlib import Path
from typing import Dict, Any, Optional

from src.aios_bridge.kernel.model import load_task_record, KernelTaskRecord


class KernelContextError(RuntimeError):
    pass


def get_compact_context(task_id: str, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    if repo_root is None:
        repo_root = Path.cwd()

    record = load_task_record(task_id, repo_root)
    if not record:
        raise KernelContextError(f"No task record found for '{task_id}'")

    task_file = f".ai/tasks/{record.task_id}.md"
    review_file = f".ai/reviews/REVIEW-{record.task_id.replace('TASK-', '')}.md" if record.action == "FIX" else None

    # Bounded semantic refs
    bounded_semantic_refs = [
        task_file,
    ]
    if review_file:
        bounded_semantic_refs.append(review_file)

    return {
        "task_id": record.task_id,
        "action": record.action,
        "executor_id": record.executor_id,
        "target_branch": record.target_branch,
        "base_main_sha": record.base_main_sha,
        "task_file": task_file,
        "review_file": review_file,
        "allowed_paths": record.allowed_paths,
        "bounded_semantic_refs": bounded_semantic_refs,
        "status": record.status,
    }
