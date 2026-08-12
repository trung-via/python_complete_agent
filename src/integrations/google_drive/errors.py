from __future__ import annotations

from typing import Optional, Dict, Any
from src.core.errors import AgentException

class GoogleDriveError(AgentException):
    """Base exception for Google Drive integration."""
    def __init__(self, message: str, code: str = "GDRIVE_ERROR", retryable: bool = False, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code, retryable=retryable, details=details)

class GoogleDriveAuthError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive authentication failed"):
        super().__init__(message, code="GDRIVE_AUTH_ERROR", retryable=False)

class GoogleDriveAuthorizationError(GoogleDriveError):
    def __init__(self, message: str = "Permission denied for Google Drive resource"):
        super().__init__(message, code="GDRIVE_AUTHORIZATION_DENIED", retryable=False)

class GoogleDriveNotFoundError(GoogleDriveError):
    def __init__(self, resource_id: str, message: str = "Google Drive resource not found"):
        super().__init__(message, code="GDRIVE_NOT_FOUND", retryable=False, details={"resource_id": resource_id})

class GoogleDriveQuotaError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive storage quota exceeded"):
        super().__init__(message, code="GDRIVE_QUOTA_EXCEEDED", retryable=False)

class GoogleDriveRateLimitError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive rate limit exceeded (HTTP 429)"):
        super().__init__(message, code="GDRIVE_RATE_LIMIT", retryable=True)

class GoogleDriveNetworkError(GoogleDriveError):
    def __init__(self, message: str = "Network failure communicating with Google Drive"):
        super().__init__(message, code="GDRIVE_NETWORK_ERROR", retryable=True)

class GoogleDriveUploadError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive upload failed"):
        super().__init__(message, code="GDRIVE_UPLOAD_FAILED", retryable=True)

class GoogleDriveSessionExpiredError(GoogleDriveUploadError):
    def __init__(self, session_id: str):
        super().__init__(f"Resumable upload session {session_id} has expired")
        self.code = "GDRIVE_SESSION_EXPIRED"
        self.retryable = False

class GoogleDriveInvalidResponseError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive returned an invalid response"):
        super().__init__(message, code="GDRIVE_INVALID_RESPONSE", retryable=False)

class GoogleDriveUploadStateError(GoogleDriveError):
    def __init__(self, session_id: str, message: str = "Invalid upload session state transition"):
        super().__init__(message, code="GDRIVE_UPLOAD_STATE_ERROR", retryable=False, details={"session_id": session_id})
