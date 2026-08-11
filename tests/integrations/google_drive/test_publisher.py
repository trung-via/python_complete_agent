import pytest
import os
import shutil
import tempfile
from typing import Optional, Dict
from unittest.mock import AsyncMock, MagicMock

from src.images.models import ImageArtifact
from src.integrations.google_drive.models import (
    RemoteArtifact,
    GoogleDriveConfig,
    GoogleDriveUploadPolicy,
    UploadSession,
    UploadState
)
from src.integrations.google_drive.publisher import GoogleDrivePublisher
from src.integrations.google_drive.errors import GoogleDriveNetworkError, GoogleDriveUploadStateError

class DummyGoogleDriveClient:
    def __init__(self):
        self.existing_remote: Optional[RemoteArtifact] = None
        self.fail_on_chunk = False
        self.chunk_attempts = 0

    async def find_file_by_app_properties(self, folder_id: str, app_properties: Dict[str, str]) -> Optional[RemoteArtifact]:
        return self.existing_remote

    async def create_folder(self, name: str, parent_folder_id: str) -> str:
        return "folder_123"

    async def create_resumable_upload_session(
        self,
        name: str,
        mime_type: str,
        size_bytes: int,
        parent_folder_id: str,
        app_properties: Dict[str, str]
    ) -> UploadSession:
        return UploadSession(
            session_id="sess_123",
            artifact_id=app_properties["agent_artifact_id"],
            sha256=app_properties["agent_sha256"],
            upload_url="https://drive.google.com/upload/session/sess_123",
            total_bytes=size_bytes
        )

    async def upload_chunk(self, session: UploadSession, chunk: bytes, start_offset: int) -> UploadSession:
        self.chunk_attempts += 1
        if self.fail_on_chunk and self.chunk_attempts == 1:
            raise GoogleDriveNetworkError("Network socket reset during chunk upload")
            
        session.bytes_uploaded += len(chunk)
        if session.bytes_uploaded >= session.total_bytes:
            session.drive_file_id = "drive_file_999"
        return session

    async def get_upload_session_status(self, session: UploadSession) -> UploadSession:
        return session

    async def delete_file(self, drive_file_id: str) -> None:
        pass

@pytest.mark.asyncio
async def test_publisher_remote_idempotency():
    client = DummyGoogleDriveClient()
    existing_artifact = RemoteArtifact(
        artifact_id="img_001",
        sha256="sha_abc",
        drive_file_id="existing_drive_id",
        name="img_001.bin",
        mime_type="image/jpeg",
        size_bytes=512,
        parent_folder_id="root_folder"
    )
    client.existing_remote = existing_artifact

    config = GoogleDriveConfig(root_folder_id="root_folder")
    publisher = GoogleDrivePublisher(client=client, config=config)

    artifact = ImageArtifact(
        artifact_id="img_001",
        sha256="sha_abc",
        mime_type="image/jpeg",
        size_bytes=512,
        width=10,
        height=10,
        source_url="http://example.com/a.jpg",
        storage_key="/tmp/a.jpg"
    )

    result = await publisher.publish(artifact, local_filepath="dummy_path", run_id="r1")
    assert result.drive_file_id == "existing_drive_id"
    assert result.artifact_id == "img_001"

@pytest.mark.asyncio
async def test_publisher_successful_chunked_upload():
    client = DummyGoogleDriveClient()
    config = GoogleDriveConfig(root_folder_id="root_folder")
    policy = GoogleDriveUploadPolicy(chunk_size=256 * 1024)
    publisher = GoogleDrivePublisher(client=client, config=config, policy=policy)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"x" * (512 * 1024)) # 512KB
        tmp_path = tmp.name

    try:
        artifact = ImageArtifact(
            artifact_id="img_002",
            sha256="sha_xyz",
            mime_type="image/png",
            size_bytes=512 * 1024,
            width=20,
            height=20,
            source_url="http://example.com/b.png",
            storage_key=tmp_path
        )

        result = await publisher.publish(artifact, local_filepath=tmp_path, run_id="r2")
        assert result.drive_file_id == "drive_file_999"
        assert result.sha256 == "sha_xyz"
        assert client.chunk_attempts == 2 # 256KB * 2 chunks
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@pytest.mark.asyncio
async def test_publisher_unknown_state_recovery():
    client = DummyGoogleDriveClient()
    client.fail_on_chunk = True # Simulates network drop on 1st chunk attempt

    config = GoogleDriveConfig(root_folder_id="root_folder")
    policy = GoogleDriveUploadPolicy(chunk_size=256 * 1024)
    publisher = GoogleDrivePublisher(client=client, config=config, policy=policy)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"y" * (256 * 1024)) # 256KB
        tmp_path = tmp.name

    try:
        artifact = ImageArtifact(
            artifact_id="img_003",
            sha256="sha_recovery",
            mime_type="image/png",
            size_bytes=256 * 1024,
            width=20,
            height=20,
            source_url="http://example.com/c.png",
            storage_key=tmp_path
        )

        # The first attempt on chunk 1 raises NetworkError -> triggers UNKNOWN -> recovers via status/retry -> succeeds
        result = await publisher.publish(artifact, local_filepath=tmp_path, run_id="r3")
        assert result.drive_file_id == "drive_file_999"
        assert result.artifact_id == "img_003"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
