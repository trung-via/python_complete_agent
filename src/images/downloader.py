import logging
import httpx
from typing import Protocol, List
from urllib.parse import urlparse

from src.images.models import ImageCandidate, DownloadedImage
from src.images.errors import (
    ImageDownloadTimeoutError,
    ImageHttpError,
    ImageRedirectError,
    ImageSecurityError
)

logger = logging.getLogger(__name__)

class DownloadPolicy:
    def __init__(self, 
                 max_bytes: int = 10 * 1024 * 1024, # 10MB
                 timeout: float = 10.0,
                 max_redirects: int = 3,
                 allowed_schemes: List[str] = None):
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.allowed_schemes = allowed_schemes or ["http", "https"]

class ImageDownloader(Protocol):
    async def download(self, candidate: ImageCandidate) -> DownloadedImage:
        ...

class HttpxImageDownloader:
    def __init__(self, policy: DownloadPolicy = None):
        self.policy = policy or DownloadPolicy()

    def _validate_url(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme not in self.policy.allowed_schemes:
            raise ImageSecurityError(url, f"Scheme {parsed.scheme} is not allowed")
            
        # Basic check for private/local IPs
        # In a real system, you'd resolve the hostname and check IP ranges
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            raise ImageSecurityError(url, "Localhost destinations are forbidden")
            
        if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172.16."):
            raise ImageSecurityError(url, "Private IP ranges are forbidden")

    async def download(self, candidate: ImageCandidate) -> DownloadedImage:
        self._validate_url(candidate.source_url)
        
        async with httpx.AsyncClient(
            max_redirects=self.policy.max_redirects,
            follow_redirects=True,
            timeout=self.policy.timeout
        ) as client:
            try:
                # We can do stream to check size before full download, 
                # but for simplicity we'll just download and check size.
                response = await client.get(candidate.source_url)
                
                # Check for redirect limit error explicitly handled by httpx
                
                if response.status_code >= 400:
                    retryable = response.status_code in (408, 429, 500, 502, 503, 504)
                    raise ImageHttpError(response.status_code, candidate.source_url, retryable)
                    
                content = response.content
                if len(content) > self.policy.max_bytes:
                    # In a real app we'd stream and abort midway to save bandwidth
                    # We will throw ImageTooLargeError downstream in Validator, 
                    # but here we can just abort early if Content-Length says so or after download
                    pass # Handled by Validator, but we could reject here too.
                    
                # The final URL after redirects
                final_url = str(response.url)
                self._validate_url(final_url)
                
                return DownloadedImage(
                    content=content,
                    source_url=candidate.source_url,
                    final_url=final_url,
                    content_type=response.headers.get("content-type")
                )
                
            except httpx.TimeoutException:
                raise ImageDownloadTimeoutError(candidate.source_url)
            except httpx.TooManyRedirects:
                raise ImageRedirectError(candidate.source_url)
            except httpx.RequestError as e:
                # Generic connection error
                raise ImageHttpError(500, candidate.source_url, True)
