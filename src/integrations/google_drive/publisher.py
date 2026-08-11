import logging
import asyncio
import aiofiles
from typing import Optional, Dict
from collections import defaultdict

from src.core.checkpoint import CheckpointManager
from src.core.retry import RetryPolicy
from src.core.errors import AgentException
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
    Enforces remote idempotency via appProperties and destination folder scope,
    handles chunked resumable uploads using core RetryPolicy, and implements 
    bounded UNKNOWN state recovery for network timeouts.
    """
    def __init__(
        self,
        client: GoogleDriveClient,
        config: GoogleDriveConfig,
        policy: Optional[GoogleDriveUploadPolicy] = None,
        retry_policy: Optional[RetryPolicy] = None,
        checkpoints: Optional[CheckpointManager] = None
    ):
        self.client = client
        self.config = config
        self.policy = policy or GoogleDriveUploadPolicy()
        self.retry_policy = retry_policy or RetryPolicy(max_attempts=3, base_delay=1.0, jitter=False)
        self.checkpoints = checkpoints
        # Process-level concurrency lock per operation_key
        self._locks = defaultdict(asyncio.Lock)

    def _log_event(self, run_id: Optional[str], event_name: str, payload: dict):
        if self.checkpoints and run_id:
            try:
                self.checkpoints.log_event(run_id, event_name, payload)
            except Exception as e:
                logger.warning(f"Failed to log checkpoint event {event_name}: {e}")

    async def publish(self, artifact: ImageArtifact, local_filepath: str, run_id: Optional[str] = None) -> RemoteArtifact:
        destination_folder_id = self.config.root_folder_id
        # Canonical identity scope: (artifact.sha256, destination_folder_id)
        operation_key = f"drive.publish:{destination_folder_id}:{artifact.sha256}"

        async with self._locks[operation_key]:
            app_properties = {
                "agent_artifact_id": artifact.artifact_id,
                "agent_sha256": artifact.sha256
            }

            # 1. Remote Idempotency Check
            self._log_event(run_id, "DRIVE_UPLOAD_CREATED", {
                "artifact_id": artifact.artifact_id,
                "sha256": artifact.sha256,
                "operation_key": operation_key
            })
            
            existing = await self.client.find_file_by_app_properties(destination_folder_id, app_properties)
            if existing:
                logger.info(f"Artifact {artifact.artifact_id} already exists on Drive in folder {destination_folder_id} (id: {existing.drive_file_id}). Skipping upload.")
                self._log_event(run_id, "DRIVE_UPLOAD_COMPLETED", {
                    "artifact_id": artifact.artifact_id,
                    "drive_file_id": existing.drive_file_id,
                    "operation_key": operation_key,
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
                "operation_key": operation_key,
                "total_bytes": artifact.size_bytes
            })

            # 3. Bounded Iterative Upload & Recovery Loop
            attempts = 0
            max_attempts = self.retry_policy.max_attempts

            while attempts < max_attempts:
                attempts += 1
                try:
                    session.state = UploadState.UPLOADING
                    async with aiofiles.open(local_filepath, "rb") as f:
                        while session.bytes_uploaded < session.total_bytes:
                            await f.seek(session.bytes_uploaded)
                            chunk = await f.read(self.policy.chunk_size)
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
                        raise GoogleDriveUploadStateError(session.session_id, "Upload finished but no drive_file_id returned")

                    remote_artifact = RemoteArtifact(
                        artifact_id=artifact.artifact_id,
                        sha256=artifact.sha256,
                        drive_file_id=session.drive_file_id,
                        name=filename,
                        mime_type=artifact.mime_type,
                        size_bytes=artifact.size_bytes,
                        parent_folder_id=destination_folder_id,
                        metadata=artifact.metadata
                    )

                    session.state = UploadState.COMPLETED
                    self._log_event(run_id, "DRIVE_UPLOAD_COMPLETED", {
                        "artifact_id": artifact.artifact_id,
                        "drive_file_id": remote_artifact.drive_file_id,
                        "operation_key": operation_key,
                        "idempotent": False
                    })
                    return remote_artifact

                except Exception as exc:
                    session.state = UploadState.UNKNOWN
                    self._log_event(run_id, "DRIVE_UPLOAD_UNKNOWN", {
                        "artifact_id": artifact.artifact_id,
                        "session_id": session.session_id,
                        "attempt": attempts,
                        "error": str(exc)
                    })

                    # If error is explicitly marked non-retryable, abort immediately
                    if getattr(exc, "retryable", False) is False:
                        session.state = UploadState.FAILED
                        raise exc

                    # Bounded Recovery Attempt
                    recovered = await self._attempt_recovery(session, destination_folder_id, app_properties, run_id)
                    if recovered:
                        return recovered

                    # If recovery couldn't find a completed file, but session status updated `bytes_uploaded`,
                    # the loop will retry uploading remaining bytes on next attempt.
                    if attempts >= max_attempts:
                        session.state = UploadState.FAILED
                        self._log_event(run_id, "DRIVE_UPLOAD_REJECTED", {
                            "artifact_id": artifact.artifact_id,
                            "session_id": session.session_id,
                            "reason": "RECOVERY_EXHAUSTED"
                        })
                        raise GoogleDriveUploadStateError(session.session_id, f"Exhausted {max_attempts} attempts for artifact {artifact.artifact_id}")

                    # Backoff sleep before next bounded attempt
                    delay = self.retry_policy.get_delay(attempts, exc if isinstance(exc, AgentException) else None)
                    await asyncio.sleep(delay)

            # Fallback if loop exits
            session.state = UploadState.FAILED
            raise GoogleDriveUploadStateError(session.session_id, f"Failed upload for artifact {artifact.artifact_id}")

    async def _attempt_recovery(
        self,
        session: UploadSession,
        folder_id: str,
        app_properties: Dict[str, str],
        run_id: Optional[str]
    ) -> Optional[RemoteArtifact]:
        """Performs a non-recursive recovery attempt."""
        # Check A: Remote lookup in case commit succeeded on Drive server before timeout
        existing = await self.client.find_file_by_app_properties(folder_id, app_properties)
        if existing:
            logger.info(f"Recovery successful: File {existing.artifact_id} was committed on Drive (id: {existing.drive_file_id}).")
            session.state = UploadState.COMPLETED
            self._log_event(run_id, "DRIVE_UPLOAD_RECOVERED", {
                "artifact_id": existing.artifact_id,
                "drive_file_id": existing.drive_file_id,
                "mode": "REMOTE_LOOKUP"
            })
            return existing

        # Check B: Query upload session status to get updated bytes_uploaded offset
        try:
            status_session = await self.client.get_upload_session_status(session)
            if status_session.state != UploadState.FAILED:
                session.bytes_uploaded = status_session.bytes_uploaded
                logger.info(f"Recovery updated session {session.session_id} offset to {session.bytes_uploaded}.")
                self._log_event(run_id, "DRIVE_UPLOAD_RECOVERED", {
                    "artifact_id": session.artifact_id,
                    "session_id": session.session_id,
                    "mode": "RESUME_OFFSET",
                    "offset": session.bytes_uploaded
                })
        except Exception as err:
            logger.warning(f"Failed to query session status during recovery: {err}")

        return None
