import logging
import httpx
import socket
import asyncio
import ipaddress
from typing import Protocol, List
from urllib.parse import urlparse

from src.images.models import ImageCandidate, DownloadedImage
from src.images.errors import (
    ImageDownloadTimeoutError,
    ImageHttpError,
    ImageRedirectError,
    ImageSecurityError,
    ImageTooLargeError
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

    async def _validate_url_and_ip(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme not in self.policy.allowed_schemes:
            raise ImageSecurityError(url, f"Scheme {parsed.scheme} is not allowed")
            
        hostname = parsed.hostname or ""
        
        loop = asyncio.get_running_loop()
        try:
            # Resolve to all IPs (A and AAAA records)
            addr_info = await loop.getaddrinfo(hostname, None)
        except socket.gaierror:
            raise ImageSecurityError(url, f"Could not resolve hostname {hostname}")
            
        for info in addr_info:
            ip_str = info[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
                # Reject anything that is not a public, global IP
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                    raise ImageSecurityError(url, f"Resolved to forbidden IP: {ip_str}")
            except ValueError:
                # Should not happen for valid getaddrinfo return values
                pass

    async def download(self, candidate: ImageCandidate) -> DownloadedImage:
        current_url = candidate.source_url
        redirects = 0
        
        async with httpx.AsyncClient(
            follow_redirects=False, # We handle redirects manually for SSRF protection
            timeout=self.policy.timeout
        ) as client:
            while True:
                await self._validate_url_and_ip(current_url)
                
                try:
                    async with client.stream("GET", current_url) as response:
                        if response.status_code in (301, 302, 303, 307, 308):
                            if redirects >= self.policy.max_redirects:
                                raise ImageRedirectError(candidate.source_url)
                            next_url = response.headers.get("location")
                            if not next_url:
                                raise ImageRedirectError(candidate.source_url, "Redirect without location")
                            # join url in case it's relative
                            current_url = str(response.url.join(next_url))
                            redirects += 1
                            continue
                            
                        if response.status_code >= 400:
                            retryable = response.status_code in (408, 429, 500, 502, 503, 504)
                            raise ImageHttpError(response.status_code, current_url, retryable)
                            
                        # Stream and check max bytes
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > self.policy.max_bytes:
                                raise ImageTooLargeError(len(content), self.policy.max_bytes)
                                
                        return DownloadedImage(
                            content=bytes(content),
                            source_url=candidate.source_url,
                            final_url=current_url,
                            content_type=response.headers.get("content-type")
                        )
                        
                except httpx.TimeoutException:
                    raise ImageDownloadTimeoutError(candidate.source_url)
                except httpx.RequestError as e:
                    # Generic connection error
                    raise ImageHttpError(500, current_url, True)
