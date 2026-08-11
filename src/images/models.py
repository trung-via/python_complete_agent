from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass(frozen=True)
class ImageCandidate:
    """Input from Browser Tool, represents an unverified image URL."""
    source_url: str
    filename: Optional[str] = None
    expected_mime_type: Optional[str] = None
    source_page_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.source_url:
            raise ValueError("source_url cannot be empty")
        if not self.source_url.startswith(("http://", "https://")):
            raise ValueError("source_url must use http or https scheme")

@dataclass
class DownloadedImage:
    """Raw bytes downloaded from URL, yet to be validated."""
    content: bytes
    source_url: str
    final_url: str  # Post-redirect URL
    content_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidatedImage:
    """Internal model representing a fully verified and decoded image."""
    content: bytes
    mime_type: str
    width: int
    height: int
    size_bytes: int
    sha256: str
    
    def __post_init__(self):
        if self.size_bytes <= 0:
            raise ValueError("size_bytes must be positive")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("dimensions must be positive")
        if not self.sha256:
            raise ValueError("sha256 cannot be empty")
        if not self.mime_type:
            raise ValueError("mime_type cannot be empty")

@dataclass
class ImageArtifact:
    """
    Public representation of a stored, verified image.
    Does not hold raw bytes in memory.
    """
    artifact_id: str
    sha256: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    source_url: str
    storage_key: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.artifact_id:
            raise ValueError("artifact_id cannot be empty")
        if not self.storage_key:
            raise ValueError("storage_key cannot be empty")
