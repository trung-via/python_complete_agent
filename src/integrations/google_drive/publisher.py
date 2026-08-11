import logging
import asyncio
import aiofiles
from typing import Optional, Dict
from collections import defaultdict

from src.core.checkpoint import CheckpointManager
from src.images.models import ImageArtifact
from src.integrations.google_drive.models import (
    RemoteArtifact,
    GoogleDriveConfig,
    GoogleDriveUploadPolicy,
    UploadState,
    UploadSession
)
from src.integrations.google_drive.protocols import ArtifactPublisher, GoogleDriveClient
from src.integrations.google_drive.errors import (
    GoogleDriveNetworkError,
    GoogleDriveUploadStateError,
    GoogleDriveError
)

logger = logging.getLogger(__name__)

class GoogleDrivePublisher(ArtifactPublisher):
    """
    Publisher implementation for Google Drive.
    Enforces remote idempotency via appProperties, handles chunked resumable uploads,
    and implements UNKNOWN state recovery for network timeouts.
    """
    def __init__(
        self,
        client: GoogleDriveClient,
        config: GoogleDriveConfig,
        policy: Optional[GoogleDriveUploadPolicy] = None,
        checkpoints: Optional[CheckpointManager] = None
    ):
        self.client = client
        self.config = config
        self.policy = policy or GoogleDriveUploadPolicy()
        self.checkpoints = checkpoints
        # Process-level concurrency lock per sha256 to prevent parallel duplicate uploads
        self._locks = defaultdict(asyncio.Lock)

    def _log_event(self, run_id: Optional[str], event_name: str, payload: dict):
        if self.checkpoints and run_id:
            try:
                self.checkpoints.log_event(run_id, event_name, payload)
            except Exception as e:
                logger.warning(f"Failed to log checkpoint event {event_name}: {e}")

    async def publish(self, artifact: ImageArtifact, local_filepath: str, run_id: Optional[str] = None) -> RemoteArtifact:
        async with self._locks[artifact.sha256]:
            app_properties = {
                "agent_artifact_id": artifact.artifact_id,
                "agent_sha256": artifact.sha256
            }
            destination_folder_id = self.config.root_folder_id

            # 1. Remote Idempotency Check
            self._log_event(run_id, "DRIVE_UPLOAD_CREATED", {
                "artifact_id": artifact.artifact_id,
                "sha256": artifact.sha256
            })
            
            existing = await self.client.find_file_by_app_properties(destination_folder_id, app_properties)
            if existing:
                logger.info(f"Artifact {artifact.artifact_id} already exists on Drive (id: {existing.drive_file_id}). Skipping upload.")
                self._log_event(run_id, "DRIVE_UPLOAD_COMPLETED", {
                    "artifact_id": artifact.artifact_id,
                    "drive_file_id": existing.drive_file_id,
                    "idempotent": True
                })
                return existing

            # 2. Create Resumable Upload Session
            filename = f"{artifact.artifact_id}.bin"
            session = await self.client.create_resumable_upload_session(
                name=filename,
                mime_type=artifact.mime_type,
                size_bytes=artifact.size_bytes,
                parent_folder_id=destination_folder_id,
                app_properties=app_properties
            )
            session.state = UploadState.SESSION_CREATED
            
            self._log_event(run_id, "DRIVE_UPLOAD_STARTED", {
                "artifact_id": artifact.artifact_id,
                "session_id": session.session_id,
                "total_bytes": artifact.size_bytes
            })

            # 3. Perform Chunked Upload with Recovery
            return await self._execute_upload_loop(session, local_filepath, artifact, run_id)

    async def _execute_upload_loop(
        self,
        session: UploadSession,
        local_filepath: str,
        artifact: ImageArtifact,
        run_id: Optional[str]
    ) -> RemoteArtifact:
        chunk_size = self.policy.chunk_size

        try:
            session.state = UploadState.UPLOADING
            async with aiofiles.open(local_filepath, "rb") as f:
                while session.bytes_uploaded < session.total_bytes:
                    await f.seek(session.bytes_uploaded)
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break

                    session = await self.client.upload_chunk(session, chunk, session.bytes_uploaded)
                    
                    self._log_event(run_id, "DRIVE_UPLOAD_PROGRESS", {
                        "artifact_id": artifact.artifact_id,
                        "session_id": session.session_id,
                        "bytes_uploaded": session.bytes_uploaded,
                        "total_bytes": session.total_bytes
                    })

            session.state = UploadState.FINALIZING
            if not session.drive_file_id:
                raise GoogleDriveUploadStateError(session.session_id, "Upload finished but no drive_file_id was returned")

            remote_artifact = RemoteArtifact(
                artifact_id=artifact.artifact_id,
                sha256=artifact.sha256,
                drive_file_id=session.drive_file_id,
                name=f"{artifact.artifact_id}.bin",
                mime_type=artifact.mime_type,
                size_bytes=artifact.size_bytes,
                parent_folder_id=self.config.root_folder_id,
                metadata=artifact.metadata
            )

            session.state = UploadState.COMPLETED
            self._log_event(run_id, "DRIVE_UPLOAD_COMPLETED", {
                "artifact_id": artifact.artifact_id,
                "drive_file_id": remote_artifact.drive_file_id,
                "idempotent": False
            })
            return remote_artifact

        except (GoogleDriveNetworkError, Exception) as exc:
            logger.warning(f"Upload interrupted for session {session.session_id}: {exc}. Transitioning to UNKNOWN.")
            session.state = UploadState.UNKNOWN
            self._log_event(run_id, "DRIVE_UPLOAD_UNKNOWN", {
                "artifact_id": artifact.artifact_id,
                "session_id": session.session_id,
                "error": str(exc)
            })

            # 4. Attempt UNKNOWN Recovery Protocol
            return await self._recover_unknown_upload(session, local_filepath, artifact, run_id)

    async def _recover_unknown_upload(
        self,
        session: UploadSession,
        local_filepath: str,
        artifact: ImageArtifact,
        run_id: Optional[str]
    ) -> RemoteArtifact:
        app_properties = {
            "agent_artifact_id": artifact.artifact_id,
            "agent_sha256": artifact.sha256
        }

        # Step A: Check if the file was committed on Google Drive despite network timeout
        existing = await self.client.find_file_by_app_properties(self.config.root_folder_id, app_properties)
        if existing:
            logger.info(f"Recovery successful: File {artifact.artifact_id} was committed on Drive (id: {existing.drive_file_id}).")
            session.state = UploadState.COMPLETED
            self._log_event(run_id, "DRIVE_UPLOAD_RECOVERED", {
                "artifact_id": artifact.artifact_id,
                "drive_file_id": existing.drive_file_id,
                "mode": "REMOTE_LOOKUP"
            })
            return existing

        # Step B: Query session status to resume chunked upload
        try:
            status_session = await self.client.get_upload_session_status(session)
            if status_session.state != UploadState.FAILED:
                logger.info(f"Recovery resuming session {session.session_id} from offset {status_session.bytes_uploaded}.")
                session.bytes_uploaded = status_session.bytes_uploaded
                self._log_event(run_id, "DRIVE_UPLOAD_RECOVERED", {
                    "artifact_id": artifact.artifact_id,
                    "session_id": session.session_id,
                    "mode": "RESUME_SESSION",
                    "offset": session.bytes_uploaded
                })
                return await self._execute_upload_loop(session, local_filepath, artifact, run_id)
        except Exception as status_exc:
            logger.warning(f"Failed to query session status for {session.session_id}: {status_exc}")

        # Step C: If recovery is impossible, log rejection/failure and raise
        session.state = UploadState.FAILED
        self._log_event(run_id, "DRIVE_UPLOAD_REJECTED", {
            "artifact_id": artifact.artifact_id,
            "session_id": session.session_id,
            "reason": "RECOVERY_FAILED"
        })
        raise GoogleDriveUploadStateError(session.session_id, f"Failed to recover upload for artifact {artifact.artifact_id}")
