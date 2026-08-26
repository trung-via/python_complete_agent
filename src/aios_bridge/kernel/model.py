"""AIOS Bridge Kernel v1 Data Models and Runtime Storage (ADR-068 / TASK-098)."""

from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any


class KernelStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    BLOCKED = "BLOCKED"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class KernelAction(str, Enum):
    RUN = "RUN"
    FIX = "FIX"


class KernelExecutor(str, Enum):
    CODEX = "codex"
    ANTIGRAVITY = "antigravity"


def compute_fingerprint(data: Any) -> str:
    """Computes SHA-256 fingerprint for structured JSON data."""
    raw = json.dumps(data, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class KernelTaskRecord:
    task_id: str
    action: str
    executor_id: str
    base_main_sha: str
    target_branch: str
    authorized_artifact_sha: str
    allowed_paths: List[str]
    allowed_paths_fingerprint: str
    verify_command_fingerprint: str
    verify_commands: Dict[str, List[str]]
    pre_execution_head: str
    status: str = KernelStatus.AUTHORIZED.value
    review_sha: Optional[str] = None
    published_head_sha: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KernelTaskRecord":
        return cls(
            task_id=data["task_id"],
            action=data["action"],
            executor_id=data["executor_id"],
            base_main_sha=data["base_main_sha"],
            target_branch=data["target_branch"],
            authorized_artifact_sha=data["authorized_artifact_sha"],
            review_sha=data.get("review_sha"),
            allowed_paths=list(data["allowed_paths"]),
            allowed_paths_fingerprint=data["allowed_paths_fingerprint"],
            verify_command_fingerprint=data["verify_command_fingerprint"],
            verify_commands=dict(data.get("verify_commands", {})),
            pre_execution_head=data["pre_execution_head"],
            status=data["status"],
            published_head_sha=data.get("published_head_sha"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


def get_kernel_runtime_dir(repo_root: Optional[Path] = None) -> Path:
    """Returns the path to ignored .aios_runtime/kernel/ directory."""
    if repo_root is None:
        repo_root = Path(os.getcwd())
    override = os.environ.get("AIOS_KERNEL_RUNTIME_DIR")
    if override:
        d = Path(override)
    else:
        d = repo_root / ".aios_runtime" / "kernel"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_task_record_path(task_id: str, repo_root: Optional[Path] = None) -> Path:
    norm_id = task_id.upper()
    if not norm_id.startswith("TASK-"):
        if norm_id.isdigit():
            norm_id = f"TASK-{int(norm_id):03d}"
    return get_kernel_runtime_dir(repo_root) / f"task_{norm_id}.json"


def save_task_record(record: KernelTaskRecord, repo_root: Optional[Path] = None) -> Path:
    path = get_task_record_path(record.task_id, repo_root)
    temp_path = path.with_suffix(".tmp")
    data = record.to_dict()
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    temp_path.replace(path)
    return path


def load_task_record(task_id: str, repo_root: Optional[Path] = None) -> Optional[KernelTaskRecord]:
    path = get_task_record_path(task_id, repo_root)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return KernelTaskRecord.from_dict(data)
    except Exception:
        return None
