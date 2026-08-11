import pytest
import os
import shutil
from src.images.storage import LocalArtifactStore
from src.images.models import ValidatedImage, ImageCandidate
import hashlib

@pytest.mark.asyncio
async def test_store_put_and_get():
    base_dir = "tests/data/temp_artifacts"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    store = LocalArtifactStore(base_dir)
    
    try:
        candidate = ImageCandidate(source_url="http://example.com/test.jpg")
        content = b"fakeimagebytes"
        sha256 = hashlib.sha256(content).hexdigest()
        
        val = ValidatedImage(
            content=content,
            mime_type="image/jpeg",
            width=100,
            height=100,
            size_bytes=len(content),
            sha256=sha256
        )
        
        artifact = await store.put(val, candidate)
        assert artifact.artifact_id is not None
        assert artifact.sha256 == sha256
        assert os.path.exists(artifact.storage_key)
        
        # Check retrieval
        retrieved = await store.get(artifact.artifact_id)
        assert retrieved is not None
        assert retrieved.sha256 == sha256
        
        # Check exists
        assert await store.exists(artifact.artifact_id) == True
    finally:
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)

@pytest.mark.asyncio
async def test_store_deduplication():
    base_dir = "tests/data/temp_artifacts2"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    store = LocalArtifactStore(base_dir)
    
    try:
        candidate = ImageCandidate(source_url="http://example.com/test.jpg")
        content = b"fakeimagebytes2"
        sha256 = hashlib.sha256(content).hexdigest()
        
        val = ValidatedImage(
            content=content,
            mime_type="image/jpeg",
            width=100,
            height=100,
            size_bytes=len(content),
            sha256=sha256
        )
        
        artifact1 = await store.put(val, candidate)
        
        # Put same validated image again
        candidate2 = ImageCandidate(source_url="http://example.com/test2.jpg")
        artifact2 = await store.put(val, candidate2)
        
        # Should return the exact same artifact
        assert artifact1.artifact_id == artifact2.artifact_id
    finally:
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
