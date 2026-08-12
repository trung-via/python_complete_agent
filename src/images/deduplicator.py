from typing import Protocol, Optional
from src.images.models import ImageArtifact
from src.images.storage import ArtifactStore

class Deduplicator(Protocol):
    async def find_duplicate(self, sha256: str) -> Optional[ImageArtifact]:
        ...

class StoreBasedDeduplicator:
    """Uses the ArtifactStore to check if an artifact with the same SHA256 already exists."""
    def __init__(self, store: ArtifactStore):
        self.store = store

    async def find_duplicate(self, sha256: str) -> Optional[ImageArtifact]:
        # We assume the store has a fast index by SHA256
        return await self.store.get_by_sha256(sha256)
