from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class UploadState(str, Enum):
    PENDING = "PENDING"
    SESSION_CREATED = "SESSION_CREATED"
    UPLOADING = "UPLOADING"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"

@dataclass(frozen=True)
class RemoteArtifact:
    """Canonical model for an artifact published to Google Drive."""
    artifact_id: str
    sha256: str
    drive_file_id: str
    name: str
    mime_type: str
    size_bytes: int
    parent_folder_id: str
    web_url: Optional[str] = None
    uploaded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.artifact_id:
            raise ValueError("artifact_id cannot be empty")
        if not self.sha256:
            raise ValueError("sha256 cannot be empty")
        if not self.drive_file_id:
            raise ValueError("drive_file_id cannot be empty")
        if self.size_bytes <= 0:
            raise ValueError("size_bytes must be positive")

@dataclass
class GoogleDriveConfig:
    root_folder_id: str
    folder_name: Optional[str] = None
    create_missing_folders: bool = True

    def __post_init__(self):
        if not self.root_folder_id:
            raise ValueError("root_folder_id cannot be empty")

@dataclass
class GoogleDriveUploadPolicy:
    chunk_size: int = 2 * 1024 * 1024  # 2MB chunks (Google Drive standard multiple of 256KB)
    request_timeout: float = 30.0
    max_attempts: int = 3
    backoff: float = 1.5
    jitter: bool = True

    def __post_init__(self):
        if self.chunk_size <= 0 or self.chunk_size % (256 * 1024) != 0:
            raise ValueError("chunk_size must be a positive multiple of 256KB (262,144 bytes)")

@dataclass
class UploadSession:
    session_id: str
    artifact_id: str
    sha256: str
    upload_url: str
    total_bytes: int
    bytes_uploaded: int = 0
    state: UploadState = UploadState.PENDING
    drive_file_id: Optional[str] = None
