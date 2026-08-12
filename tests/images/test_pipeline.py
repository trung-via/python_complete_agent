import pytest
import os
import shutil

from src.images.models import ImageCandidate, DownloadedImage
from src.images.pipeline import ImagePipeline
from src.images.validator import StrictImageValidator
from src.images.filter import BasicImageFilter
from src.images.deduplicator import StoreBasedDeduplicator
from src.images.storage import LocalArtifactStore
from src.images.errors import ImageValidationError

class MockDownloader:
    async def download(self, candidate: ImageCandidate) -> DownloadedImage:
        # candidate.source_url is expected to be a mapped to local path
        local_path = "tests/fixtures/images/" + candidate.source_url.split("/")[-1]
        with open(local_path, "rb") as f:
            content = f.read()
            
        return DownloadedImage(
            content=content,
            source_url=candidate.source_url,
            final_url=candidate.source_url,
            content_type=None
        )

@pytest.mark.asyncio
async def test_pipeline_valid_image():
    base_dir = "tests/data/temp_pipeline"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
        
    store = LocalArtifactStore(base_dir)
    validator = StrictImageValidator()
    filter_engine = BasicImageFilter()
    dedup = StoreBasedDeduplicator(store)
    downloader = MockDownloader()
    
    pipeline = ImagePipeline(
        downloader=downloader,
        validator=validator,
        filter_engine=filter_engine,
        deduplicator=dedup,
        storage=store
    )
    
    try:
        candidate = ImageCandidate(source_url="http://example.com/valid.jpg")
        artifact = await pipeline.process(candidate, run_id="r1")
        
        assert artifact.artifact_id is not None
        assert artifact.mime_type in ("image/jpeg", "image/jpg")
        assert artifact.width == 10
        assert artifact.height == 10
    finally:
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)

@pytest.mark.asyncio
async def test_pipeline_corrupted_image():
    base_dir = "tests/data/temp_pipeline2"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
        
    store = LocalArtifactStore(base_dir)
    validator = StrictImageValidator()
    filter_engine = BasicImageFilter()
    dedup = StoreBasedDeduplicator(store)
    downloader = MockDownloader()
    
    pipeline = ImagePipeline(
        downloader=downloader,
        validator=validator,
        filter_engine=filter_engine,
        deduplicator=dedup,
        storage=store
    )
    
    try:
        candidate = ImageCandidate(source_url="http://example.com/corrupted.jpg")
        with pytest.raises(ImageValidationError):
            await pipeline.process(candidate, run_id="r2")
    finally:
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
