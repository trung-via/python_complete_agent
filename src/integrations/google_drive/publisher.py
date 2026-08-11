from __future__ import annotations

import logging
import asyncio
import aiofiles
from typing import Optional, Dict
from collections import defaultdict

from src.core.checkpoint import CheckpointManager
from src.core.retry import RetryPolicy
from src.core.errors import AgentException
from src.images.models import ImageArtifact
from src.integrations.google_drive.auth import GoogleDriveAuth, GoogleDriveAuthenticationError
from src.integrations.google_drive.models import (
    RemoteArtifact,
    GoogleDriveConfig,
    GoogleDriveUploadPolicy,
    UploadSessionState,
    UploadSession,
    UploadChunkResult,
    DriveFile,
    PublicationIdentity
)
from src.integrations.google_drive.protocols import ArtifactPublisher, GoogleDriveClient, GoogleDriveFolderResolver
from src.integrations.google_drive.errors import (
    GoogleDriveAuthError,
    GoogleDriveUploadStateError,
    GoogleDriveSessionExpiredError,
    GoogleDriveError
)

logger = logging.getLogger(__name__)

class GoogleDrivePublisher(ArtifactPublisher):
    """
    Publisher implementation for Google Drive.
    Enforces remote idempotency via appProperties and destination scope (PublicationIdentity),
    handles chunked resumable uploads using core RetryPolicy, bounded 401 auth refresh,
    and implements UNKNOWN state recovery for network timeouts.
    """
    def __init__(
        self,
        client: GoogleDriveClient,
        config: GoogleDriveConfig,
        auth: Optional[GoogleDriveAuth] = None,
        resolver: Optional[GoogleDriveFolderResolver] = None,
        policy: Optional[GoogleDriveUploadPolicy] = None,
        retry_policy: Optional[RetryPolicy] = None,
        checkpoints: Optional[CheckpointManager] = None
    ):
        self.client = client
        self.config = config
        self.auth = auth
        self.resolver = resolver
        self.policy = policy or GoogleDriveUploadPolicy()
        self.retry_policy = retry_policy or RetryPolicy(max_attempts=3, base_delay=1.0, jitter=False)
        self.checkpoints = checkpoints
        # Process-level concurrency lock per operation_key
        self._locks = defaultdict(asyncio.Lock)
        # Single-flight lock for concurrent 401 token refresh attempts
        self._auth_lock = asyncio.Lock()

    def _log_event(self, run_id: Optional[str], event_name: str, payload: dict):
        if self.checkpoints and run_id:
            try:
                self.checkpoints.log_event(run_id, event_name, payload)
            except Exception as e:
                logger.warning(f"Failed to log checkpoint event {event_name}: {e}")

    async def publish(
        self,
        artifact: ImageArtifact,
        source_path: str,
        destination_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> RemoteArtifact:
        dest_id = destination_id or self.config.root_folder_id
        identity = PublicationIdentity(artifact_sha256=artifact.sha256, destination_id=dest_id)
        operation_key = identity.operation_key

        async with self._locks[operation_key]:
            app_properties = {
                "agent_artifact_id": artifact.artifact_id,
                "agent_sha256": artifact.sha256,
                "agent_destination_id": dest_id,
                "agent_schema_version": "1"
            }

            self._log_event(run_id, "DRIVE_UPLOAD_CREATED", {
                "artifact_id": artifact.artifact_id,
                "sha256": artifact.sha256,
                "operation_key": operation_key
            })

            # 1. Remote Idempotency Check via app_properties
            existing_drive_file = await self._call_with_auth_refresh(
                lambda: self.client.find_file(parent_folder_id=dest_id, app_properties=app_properties)
            )

            if existing_drive_file:
                logger.info(f"Artifact {artifact.artifact_id} already exists on Drive in folder {dest_id} (id: {existing_drive_file.file_id}). Skipping upload.")
                remote_artifact = self._map_to_remote_artifact(artifact, existing_drive_file, dest_id)
                self._log_event(run_id, "DRIVE_UPLOAD_COMPLETED", {
                    "artifact_id": artifact.artifact_id,
                    "drive_file_id": remote_artifact.drive_file_id,
                    "operation_key": operation_key,
                    "idempotent": True
                })
                return remote_artifact

            # 2. Create Resumable Upload Session
            filename = f"{artifact.artifact_id}.bin"
            session: UploadSession = await self._call_with_auth_refresh(
                lambda: self.client.create_resumable_upload_session(
                    parent_folder_id=dest_id,
                    name=filename,
                    mime_type=artifact.mime_type,
                    total_bytes=artifact.size_bytes,
                    app_properties=app_properties
                )
            )

            self._log_event(run_id, "DRIVE_UPLOAD_STARTED", {
                "artifact_id": artifact.artifact_id,
                "session_id": session.session_id,
                "operation_key": operation_key,
                "total_bytes": artifact.size_bytes
            })

            # 3. Bounded Iterative Upload & Recovery Loop
            attempts = 0
            max_attempts = self.retry_policy.max_attempts
            current_session = session

            while attempts < max_attempts:
                attempts += 1
                try:
                    current_session = UploadSession(
                        session_id=current_session.session_id,
                        state=UploadSessionState.ACTIVE,
                        bytes_uploaded=current_session.bytes_uploaded,
                        total_bytes=current_session.total_bytes,
                        file_id=current_session.file_id
                    )

                    async with aiofiles.open(source_path, "rb") as f:
                        while current_session.bytes_uploaded < current_session.total_bytes:
                            await f.seek(current_session.bytes_uploaded)
                            chunk = await f.read(self.policy.chunk_size)
                            if not chunk:
                                break

                            offset = current_session.bytes_uploaded
                            chunk_res: UploadChunkResult = await self._call_with_auth_refresh(
                                lambda: self.client.upload_chunk(
                                    session_id=current_session.session_id,
                                    offset=offset,
                                    chunk=chunk,
                                    total_bytes=artifact.size_bytes
                                )
                            )

                            current_session = UploadSession(
                                session_id=chunk_res.session_id,
                                state=chunk_res.state,
                                bytes_uploaded=chunk_res.bytes_uploaded,
                                total_bytes=artifact.size_bytes,
                                file_id=chunk_res.file_id
                            )

                            self._log_event(run_id, "DRIVE_UPLOAD_PROGRESS", {
                                "artifact_id": artifact.artifact_id,
                                "session_id": current_session.session_id,
                                "bytes_uploaded": current_session.bytes_uploaded,
                                "total_bytes": current_session.total_bytes
                            })

                    if not current_session.file_id:
                        raise GoogleDriveUploadStateError(current_session.session_id, "Upload finished but no file_id returned")

                    drive_file = DriveFile(
                        file_id=current_session.file_id,
                        name=filename,
                        mime_type=artifact.mime_type,
                        size_bytes=artifact.size_bytes,
                        parent_folder_id=dest_id,
                        app_properties=app_properties
                    )

                    remote_artifact = self._map_to_remote_artifact(artifact, drive_file, dest_id)
                    self._log_event(run_id, "DRIVE_UPLOAD_COMPLETED", {
                        "artifact_id": artifact.artifact_id,
                        "drive_file_id": remote_artifact.drive_file_id,
                        "operation_key": operation_key,
                        "idempotent": False
                    })
                    return remote_artifact

                except Exception as exc:
                    self._log_event(run_id, "DRIVE_UPLOAD_UNKNOWN", {
                        "artifact_id": artifact.artifact_id,
                        "session_id": current_session.session_id,
                        "attempt": attempts,
                        "error": str(exc)
                    })

                    # If non-retryable error, fail immediately
                    if getattr(exc, "retryable", False) is False:
                        raise exc

                    # Bounded Recovery Attempt
                    recovered_file = await self._attempt_recovery(current_session, dest_id, app_properties, run_id)
                    if recovered_file:
                        remote_artifact = self._map_to_remote_artifact(artifact, recovered_file, dest_id)
                        return remote_artifact

                    if attempts >= max_attempts:
                        self._log_event(run_id, "DRIVE_UPLOAD_REJECTED", {
                            "artifact_id": artifact.artifact_id,
                            "session_id": current_session.session_id,
                            "reason": "RECOVERY_EXHAUSTED"
                        })
                        raise GoogleDriveUploadStateError(current_session.session_id, f"Exhausted {max_attempts} attempts for artifact {artifact.artifact_id}")

                    delay = self.retry_policy.get_delay(attempts, exc if isinstance(exc, AgentException) else None)
                    await asyncio.sleep(delay)

            raise GoogleDriveUploadStateError(session.session_id, f"Failed upload for artifact {artifact.artifact_id}")

    async def _call_with_auth_refresh(self, fn):
        """Helper to invoke client methods with single-flight 401 auth refresh retry."""
        try:
            return await fn()
        except GoogleDriveAuthError:
            if not self.auth:
                raise
            async with self._auth_lock:
                logger.info("Encountered 401 Auth error. Executing single-flight access token refresh...")
                await self.auth.refresh_access_token()
            return await fn()

    async def _attempt_recovery(
        self,
        session: UploadSession,
        folder_id: str,
        app_properties: Dict[str, str],
        run_id: Optional[str]
    ) -> Optional[DriveFile]:
        """Performs a non-recursive recovery attempt."""
        # Check A: Remote lookup in case commit succeeded on Drive server before timeout
        existing = await self._call_with_auth_refresh(
            lambda: self.client.find_file(parent_folder_id=folder_id, app_properties=app_properties)
        )
        if existing:
            logger.info(f"Recovery successful: File {session.artifact_id if hasattr(session, 'artifact_id') else ''} was committed on Drive (id: {existing.file_id}).")
            self._log_event(run_id, "DRIVE_UPLOAD_RECOVERED", {
                "drive_file_id": existing.file_id,
                "mode": "REMOTE_LOOKUP"
            })
            return existing

        # Check B: Query upload session status to get updated bytes_uploaded offset
        try:
            status_session = await self._call_with_auth_refresh(
                lambda: self.client.get_upload_session_status(session_id=session.session_id)
            )
            if status_session.state != UploadSessionState.FAILED:
                logger.info(f"Recovery updated session {session.session_id} offset to {status_session.bytes_uploaded}.")
                self._log_event(run_id, "DRIVE_UPLOAD_RECOVERED", {
                    "session_id": session.session_id,
                    "mode": "RESUME_OFFSET",
                    "offset": status_session.bytes_uploaded
                })
        except Exception as err:
            logger.warning(f"Failed to query session status during recovery: {err}")

        return None

    def _map_to_remote_artifact(self, artifact: ImageArtifact, drive_file: DriveFile, dest_id: str) -> RemoteArtifact:
        return RemoteArtifact(
            artifact_id=artifact.artifact_id,
            sha256=artifact.sha256,
            drive_file_id=drive_file.file_id,
            name=drive_file.name,
            mime_type=artifact.mime_type,
            size_bytes=artifact.size_bytes,
            parent_folder_id=dest_id,
            web_url=drive_file.web_url,
            metadata=artifact.metadata
        )
