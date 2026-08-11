from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class UploadSessionState(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class PublicationIdentity:
    artifact_sha256: str
    destination_id: str

    @property
    def operation_key(self) -> str:
        return f"drive.publish:{self.destination_id}:{self.artifact_sha256}"

@dataclass(frozen=True, slots=True)
class DriveFile:
    file_id: str
    name: str
    mime_type: str
    size_bytes: int
    parent_folder_id: str
    web_url: Optional[str] = None
    app_properties: Optional[Dict[str, str]] = None

@dataclass(frozen=True, slots=True)
class UploadSession:
    session_id: str
    state: UploadSessionState
    bytes_uploaded: int
    total_bytes: int
    file_id: Optional[str] = None

@dataclass(frozen=True, slots=True)
class UploadChunkResult:
    session_id: str
    state: UploadSessionState
    bytes_uploaded: int
    file_id: Optional[str] = None

@dataclass(frozen=True, slots=True)
class RemoteArtifact:
    """Canonical model for an artifact published to external target."""
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

@dataclass(frozen=True, slots=True)
class GoogleDriveConfig:
    root_folder_id: str
    folder_name: Optional[str] = None
    create_missing_folders: bool = True

    def __post_init__(self):
        if not self.root_folder_id:
            raise ValueError("root_folder_id cannot be empty")

@dataclass(frozen=True, slots=True)
class GoogleDriveUploadPolicy:
    chunk_size: int = 2 * 1024 * 1024  # 2MB chunks (Google Drive standard multiple of 256KB)
    request_timeout: float = 30.0

    def __post_init__(self):
        if self.chunk_size <= 0 or self.chunk_size % (256 * 1024) != 0:
            raise ValueError("chunk_size must be a positive multiple of 256KB (262,144 bytes)")
