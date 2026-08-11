from typing import Protocol, Optional, Dict, Any, List
from src.images.models import ImageArtifact
from src.integrations.google_drive.models import RemoteArtifact, UploadSession

class ArtifactPublisher(Protocol):
    """Generic contract for publishing a local ImageArtifact to an external storage service."""
    async def publish(self, artifact: ImageArtifact, local_filepath: str, run_id: Optional[str] = None) -> RemoteArtifact:
        ...

class GoogleDriveAuth(Protocol):
    """Protocol for managing and refreshing OAuth2 / Service Account tokens."""
    async def get_access_token(self) -> str:
        ...

    async def refresh_token(self) -> str:
        ...

class GoogleDriveClient(Protocol):
    """Low-level protocol abstracting direct Google Drive REST API calls."""
    async def find_file_by_app_properties(self, folder_id: str, app_properties: Dict[str, str]) -> Optional[RemoteArtifact]:
        ...

    async def create_folder(self, name: str, parent_folder_id: str) -> str:
        """Returns the folder_id of the existing or newly created folder."""
        ...

    async def create_resumable_upload_session(
        self,
        name: str,
        mime_type: str,
        size_bytes: int,
        parent_folder_id: str,
        app_properties: Dict[str, str]
    ) -> UploadSession:
        ...

    async def upload_chunk(self, session: UploadSession, chunk: bytes, start_offset: int) -> UploadSession:
        """Uploads a single byte chunk to an active resumable upload session."""
        ...

    async def get_upload_session_status(self, session: UploadSession) -> UploadSession:
        """Queries Google Drive server for the current byte offset and state of an upload session."""
        ...

    async def delete_file(self, drive_file_id: str) -> None:
        ...
