from __future__ import annotations

from typing import Protocol, Optional, Dict, Tuple
from src.images.models import ImageArtifact
from src.integrations.google_drive.models import (
    DriveFile,
    UploadSession,
    UploadChunkResult,
    RemoteArtifact
)

class ArtifactPublisher(Protocol):
    """Generic contract for publishing a local ImageArtifact to an external target."""
    async def publish(
        self,
        artifact: ImageArtifact,
        local_filepath: str,
        destination_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> RemoteArtifact:
        ...

class GoogleDriveFolderResolver(Protocol):
    """Protocol for resolving folder path tuples into Drive Folder IDs."""
    async def resolve(self, *, root_folder_id: str, path: Tuple[str, ...]) -> str:
        ...

class GoogleDriveClient(Protocol):
    """Low-level transport protocol abstracting Drive API calls with typed primitives."""
    async def find_file(
        self,
        *,
        parent_folder_id: str,
        app_properties: Dict[str, str],
    ) -> Optional[DriveFile]:
        ...

    async def get_file(self, file_id: str) -> DriveFile:
        ...

    async def create_folder(
        self,
        *,
        parent_folder_id: str,
        name: str,
    ) -> str:
        ...

    async def create_resumable_upload_session(
        self,
        *,
        parent_folder_id: str,
        name: str,
        mime_type: str,
        total_bytes: int,
        app_properties: Dict[str, str],
    ) -> UploadSession:
        ...

    async def get_upload_session_status(
        self,
        *,
        session_id: str,
    ) -> UploadSession:
        ...

    async def upload_chunk(
        self,
        *,
        session_id: str,
        offset: int,
        chunk: bytes,
        total_bytes: int,
    ) -> UploadChunkResult:
        ...

    async def delete_file(self, file_id: str) -> None:
        ...
