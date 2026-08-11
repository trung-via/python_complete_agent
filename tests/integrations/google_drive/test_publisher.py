import pytest
import os
import tempfile
from typing import Optional, Dict

from src.core.retry import RetryPolicy
from src.images.models import ImageArtifact
from src.integrations.google_drive.auth import AccessToken, GoogleDriveAuth
from src.integrations.google_drive.models import (
    DriveFile,
    GoogleDriveConfig,
    GoogleDriveUploadPolicy,
    UploadSession,
    UploadSessionState,
    UploadChunkResult,
    PublicationIdentity
)
from src.integrations.google_drive.publisher import GoogleDrivePublisher
from src.integrations.google_drive.errors import GoogleDriveNetworkError, GoogleDriveAuthError

class FakeGoogleDriveAuth:
    def __init__(self):
        self.access_token = AccessToken(value="token_v1")
        self.refresh_count = 0

    async def get_access_token(self) -> AccessToken:
        return self.access_token

    async def refresh_access_token(self) -> AccessToken:
        self.refresh_count += 1
        self.access_token = AccessToken(value=f"token_v{self.refresh_count + 1}")
        return self.access_token

class FakeGoogleDriveClient:
    def __init__(self):
        self.files_by_folder: Dict[str, Dict[str, DriveFile]] = {}
        self.fail_on_chunk = False
        self.fail_auth_once = False
        self.chunk_attempts = 0
        self.auth_attempts = 0

    async def find_file(
        self,
        *,
        parent_folder_id: str,
        app_properties: Dict[str, str],
    ) -> Optional[DriveFile]:
        if self.fail_auth_once and self.auth_attempts == 0:
            self.auth_attempts += 1
            raise GoogleDriveAuthError("Invalid Access Token")

        folder_files = self.files_by_folder.get(parent_folder_id, {})
        for file in folder_files.values():
            if file.app_properties and file.app_properties.get("agent_sha256") == app_properties.get("agent_sha256"):
                return file
        return None

    async def get_file(self, file_id: str) -> DriveFile:
        for folder_files in self.files_by_folder.values():
            if file_id in folder_files:
                return folder_files[file_id]
        raise ValueError(f"File {file_id} not found")

    async def create_folder(self, *, parent_folder_id: str, name: str) -> str:
        return f"folder_{name}"

    async def create_resumable_upload_session(
        self,
        *,
        parent_folder_id: str,
        name: str,
        mime_type: str,
        total_bytes: int,
        app_properties: Dict[str, str],
    ) -> UploadSession:
        return UploadSession(
            session_id="sess_fake_1",
            state=UploadSessionState.ACTIVE,
            bytes_uploaded=0,
            total_bytes=total_bytes
        )

    async def upload_chunk(
        self,
        *,
        session_id: str,
        offset: int,
        chunk: bytes,
        total_bytes: int,
    ) -> UploadChunkResult:
        self.chunk_attempts += 1
        if self.fail_on_chunk and self.chunk_attempts == 1:
            raise GoogleDriveNetworkError("Network socket reset during chunk upload")

        new_offset = offset + len(chunk)
        file_id = f"drive_file_{offset + len(chunk)}" if new_offset >= total_bytes else None
        state = UploadSessionState.COMPLETED if new_offset >= total_bytes else UploadSessionState.ACTIVE

        return UploadChunkResult(
            session_id=session_id,
            state=state,
            bytes_uploaded=new_offset,
            file_id=file_id
        )

    async def get_upload_session_status(self, *, session_id: str) -> UploadSession:
        return UploadSession(
            session_id=session_id,
            state=UploadSessionState.ACTIVE,
            bytes_uploaded=0,
            total_bytes=256 * 1024
        )

    async def delete_file(self, file_id: str) -> None:
        pass

@pytest.mark.asyncio
async def test_publisher_remote_idempotency():
    client = FakeGoogleDriveClient()
    existing_file = DriveFile(
        file_id="drive_file_001",
        name="img_001.bin",
        mime_type="image/jpeg",
        size_bytes=512,
        parent_folder_id="root_folder",
        app_properties={"agent_sha256": "sha_abc"}
    )
    client.files_by_folder["root_folder"] = {"drive_file_001": existing_file}

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
    assert result.drive_file_id == "drive_file_001"
    assert result.artifact_id == "img_001"

@pytest.mark.asyncio
async def test_publisher_auth_401_refresh():
    client = FakeGoogleDriveClient()
    client.fail_auth_once = True
    auth = FakeGoogleDriveAuth()

    config = GoogleDriveConfig(root_folder_id="root_folder")
    publisher = GoogleDrivePublisher(client=client, config=config, auth=auth)

    artifact = ImageArtifact(
        artifact_id="img_auth_test",
        sha256="sha_auth",
        mime_type="image/jpeg",
        size_bytes=256 * 1024,
        width=10,
        height=10,
        source_url="http://example.com/auth.jpg",
        storage_key="/tmp/auth.jpg"
    )

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"z" * (256 * 1024))
        tmp_path = tmp.name

    try:
        result = await publisher.publish(artifact, local_filepath=tmp_path, run_id="r_auth")
        assert result.drive_file_id is not None
        assert auth.refresh_count == 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@pytest.mark.asyncio
async def test_publisher_same_artifact_different_destinations():
    client = FakeGoogleDriveClient()
    config = GoogleDriveConfig(root_folder_id="root_folder")
    publisher = GoogleDrivePublisher(client=client, config=config)

    artifact = ImageArtifact(
        artifact_id="img_multi_dest",
        sha256="sha_common",
        mime_type="image/jpeg",
        size_bytes=256 * 1024,
        width=10,
        height=10,
        source_url="http://example.com/common.jpg",
        storage_key="/tmp/common.jpg"
    )

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"w" * (256 * 1024))
        tmp_path = tmp.name

    try:
        res1 = await publisher.publish(artifact, local_filepath=tmp_path, destination_id="folder_A", run_id="rA")
        
        # Add res1 to client's folder_A memory
        client.files_by_folder["folder_A"] = {
            res1.drive_file_id: DriveFile(
                file_id=res1.drive_file_id,
                name=res1.name,
                mime_type=res1.mime_type,
                size_bytes=res1.size_bytes,
                parent_folder_id="folder_A",
                app_properties={"agent_sha256": "sha_common"}
            )
        }

        # Publishing same artifact to folder_B must not be short-circuited by folder_A's file
        res2 = await publisher.publish(artifact, local_filepath=tmp_path, destination_id="folder_B", run_id="rB")

        assert res1.parent_folder_id == "folder_A"
        assert res2.parent_folder_id == "folder_B"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@pytest.mark.asyncio
async def test_publisher_unknown_state_recovery_bounded_loop():
    client = FakeGoogleDriveClient()
    client.fail_on_chunk = True

    config = GoogleDriveConfig(root_folder_id="root_folder")
    policy = GoogleDriveUploadPolicy(chunk_size=256 * 1024)
    retry_policy = RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False)
    publisher = GoogleDrivePublisher(client=client, config=config, policy=policy, retry_policy=retry_policy)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"y" * (256 * 1024))
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

        result = await publisher.publish(artifact, local_filepath=tmp_path, run_id="r3")
        assert result.drive_file_id == "drive_file_262144"
        assert result.artifact_id == "img_003"
        assert client.chunk_attempts == 2
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
