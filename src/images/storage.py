import os
import uuid
import json
import asyncio
from collections import defaultdict
from typing import Protocol, Optional
import aiofiles
import aiofiles.os

from src.images.models import ImageArtifact, ValidatedImage, ImageCandidate
from src.images.errors import ArtifactStoreError

class ArtifactStore(Protocol):
    async def put(self, validated_image: ValidatedImage, candidate: ImageCandidate) -> ImageArtifact:
        ...
        
    async def get(self, artifact_id: str) -> Optional[ImageArtifact]:
        ...
        
    async def get_by_sha256(self, sha256: str) -> Optional[ImageArtifact]:
        ...
        
    async def exists(self, artifact_id: str) -> bool:
        ...
        
    async def delete(self, artifact_id: str) -> None:
        ...

class LocalArtifactStore:
    def __init__(self, base_dir: str = "data/artifacts"):
        self.base_dir = base_dir
        self.images_dir = os.path.join(base_dir, "images")
        self.metadata_dir = os.path.join(base_dir, "metadata")
        self.temp_dir = os.path.join(base_dir, "temp")
        self._locks = defaultdict(asyncio.Lock)
        
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def _get_image_path(self, sha256: str) -> str:
        # We use sha256 as the filename for the raw image bytes to easily dedup local files
        return os.path.join(self.images_dir, f"{sha256}.bin")
        
    def _get_metadata_path(self, artifact_id: str) -> str:
        return os.path.join(self.metadata_dir, f"{artifact_id}.json")

    async def get_by_sha256(self, sha256: str) -> Optional[ImageArtifact]:
        # This is an O(N) search in the local store since we don't have a DB yet.
        # We iterate over all metadata to find a matching sha256.
        # In a real DB, this would be `SELECT * FROM artifacts WHERE sha256=?`
        try:
            files = await aiofiles.os.listdir(self.metadata_dir)
            for f in files:
                if f.endswith(".json"):
                    artifact_id = f.replace(".json", "")
                    artifact = await self.get(artifact_id)
                    if artifact and artifact.sha256 == sha256:
                        return artifact
        except FileNotFoundError:
            pass
        return None

    async def get(self, artifact_id: str) -> Optional[ImageArtifact]:
        path = self._get_metadata_path(artifact_id)
        if not await aiofiles.os.path.exists(path):
            return None
            
        async with aiofiles.open(path, 'r') as f:
            content = await f.read()
            data = json.loads(content)
            return ImageArtifact(**data)

    async def exists(self, artifact_id: str) -> bool:
        return await aiofiles.os.path.exists(self._get_metadata_path(artifact_id))

    async def put(self, validated_image: ValidatedImage, candidate: ImageCandidate) -> ImageArtifact:
        async with self._locks[validated_image.sha256]:
            # 1. Deduplication check at the storage level inside lock
            existing = await self.get_by_sha256(validated_image.sha256)
            if existing:
                return existing
                
            artifact_id = f"img_{uuid.uuid4().hex}"
            temp_path = os.path.join(self.temp_dir, f"temp_{artifact_id}.bin")
            final_image_path = self._get_image_path(validated_image.sha256)
        
        try:
            # 2. Atomic write of the image binary
            if not await aiofiles.os.path.exists(final_image_path):
                async with aiofiles.open(temp_path, 'wb') as f:
                    await f.write(validated_image.content)
                    await f.flush()
                    os.fsync(f.fileno())
                
                # Atomic rename
                await aiofiles.os.replace(temp_path, final_image_path)
            
            # 3. Create metadata
            artifact = ImageArtifact(
                artifact_id=artifact_id,
                sha256=validated_image.sha256,
                mime_type=validated_image.mime_type,
                size_bytes=validated_image.size_bytes,
                width=validated_image.width,
                height=validated_image.height,
                source_url=candidate.source_url,
                storage_key=final_image_path,
                metadata=candidate.metadata
            )
            
            # 4. Atomic write of metadata
            temp_meta = os.path.join(self.temp_dir, f"temp_meta_{artifact_id}.json")
            meta_path = self._get_metadata_path(artifact_id)
            
            async with aiofiles.open(temp_meta, 'w') as f:
                await f.write(json.dumps(artifact.__dict__))
                await f.flush()
                os.fsync(f.fileno())
                
            await aiofiles.os.replace(temp_meta, meta_path)
            
            return artifact
            
        except Exception as e:
            # Cleanup temp files if any
            try:
                if await aiofiles.os.path.exists(temp_path):
                    await aiofiles.os.remove(temp_path)
            except:
                pass
            raise ArtifactStoreError(f"Failed to store artifact: {e}")
        finally:
            # Clean up the lock if nobody is waiting
            if not self._locks[validated_image.sha256].locked():
                del self._locks[validated_image.sha256]

    async def delete(self, artifact_id: str) -> None:
        artifact = await self.get(artifact_id)
        if artifact:
            # We don't necessarily delete the binary if other artifacts might reference it (dedup),
            # but for a simple local store we could.
            # Safest is just deleting metadata.
            meta_path = self._get_metadata_path(artifact_id)
            if await aiofiles.os.path.exists(meta_path):
                await aiofiles.os.remove(meta_path)
