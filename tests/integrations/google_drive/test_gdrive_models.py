import pytest
from src.integrations.google_drive.models import (
    RemoteArtifact,
    GoogleDriveConfig,
    GoogleDriveUploadPolicy,
    UploadSession,
    UploadState
)

def test_remote_artifact_validation():
    artifact = RemoteArtifact(
        artifact_id="img_123",
        sha256="hash123",
        drive_file_id="drive_file_abc",
        name="img_123.bin",
        mime_type="image/png",
        size_bytes=1024,
        parent_folder_id="folder_xyz"
    )
    assert artifact.artifact_id == "img_123"

    with pytest.raises(ValueError, match="artifact_id cannot be empty"):
        RemoteArtifact(
            artifact_id="",
            sha256="hash123",
            drive_file_id="drive_file_abc",
            name="img_123.bin",
            mime_type="image/png",
            size_bytes=1024,
            parent_folder_id="folder_xyz"
        )

def test_upload_policy_validation():
    policy = GoogleDriveUploadPolicy(chunk_size=256 * 1024 * 4) # 1MB (multiple of 256KB)
    assert policy.chunk_size == 1048576

    with pytest.raises(ValueError, match="multiple of 256KB"):
        GoogleDriveUploadPolicy(chunk_size=1000)

def test_config_validation():
    config = GoogleDriveConfig(root_folder_id="root_123")
    assert config.root_folder_id == "root_123"

    with pytest.raises(ValueError, match="root_folder_id cannot be empty"):
        GoogleDriveConfig(root_folder_id="")
