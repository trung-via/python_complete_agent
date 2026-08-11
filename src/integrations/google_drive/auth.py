from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional
from src.core.errors import AgentException

@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str
    expires_at: Optional[float] = None

class GoogleDriveAuthError(AgentException):
    """Base error for Google Drive authentication."""
    def __init__(self, message: str = "Google Drive authentication failed", details: Optional[dict] = None):
        super().__init__(message, code="GDRIVE_AUTH_ERROR", retryable=False, details=details)

class GoogleDriveAuthenticationError(GoogleDriveAuthError):
    """Raised when authentication fails permanently or token refresh fails."""
    def __init__(self, message: str = "Invalid credentials or token refresh failed"):
        super().__init__(message)
        self.code = "GDRIVE_AUTHENTICATION_FAILED"

class GoogleDriveAuth(Protocol):
    async def get_access_token(self) -> AccessToken:
        """Return a valid access token."""
        ...

    async def refresh_access_token(self) -> AccessToken:
        """Refresh and return an access token."""
        ...

class SingleFlightGoogleDriveAuth:
    """
    Decorator/Wrapper for GoogleDriveAuth that enforces single-flight token refresh.
    Prevents multiple concurrent 401 requests from firing parallel refresh requests to Google.
    """
    def __init__(self, auth: GoogleDriveAuth):
        self._auth = auth
        import asyncio
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> AccessToken:
        return await self._auth.get_access_token()

    async def refresh_access_token(self) -> AccessToken:
        async with self._lock:
            return await self._auth.refresh_access_token()

