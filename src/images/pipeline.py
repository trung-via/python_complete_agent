import logging
from typing import Protocol, Optional

from src.core.checkpoint import CheckpointManager
from src.images.models import ImageCandidate, ImageArtifact
from src.images.downloader import ImageDownloader
from src.images.validator import ImageValidator
from src.images.filter import ImageFilter
from src.images.deduplicator import Deduplicator
from src.images.storage import ArtifactStore
from src.images.errors import ImageError

logger = logging.getLogger(__name__)

class ImagePipeline:
    def __init__(self,
                 downloader: ImageDownloader,
                 validator: ImageValidator,
                 filter_engine: ImageFilter,
                 deduplicator: Deduplicator,
                 storage: ArtifactStore,
                 checkpoints: CheckpointManager = None):
        self.downloader = downloader
        self.validator = validator
        self.filter = filter_engine
        self.deduplicator = deduplicator
        self.storage = storage
        self.checkpoints = checkpoints

    def _log_event(self, run_id: Optional[str], event_name: str, payload: dict):
        if self.checkpoints and run_id:
            try:
                # We reuse the checkpoint manager to emit a structured event
                self.checkpoints.log_event(run_id, event_name, payload)
            except Exception as e:
                logger.warning(f"Failed to log event {event_name}: {e}")

    async def process(self, candidate: ImageCandidate, run_id: Optional[str] = None) -> ImageArtifact:
        self._log_event(run_id, "IMAGE_DISCOVERED", {"url": candidate.source_url})
        
        try:
            # 1. Download
            self._log_event(run_id, "IMAGE_DOWNLOAD_STARTED", {"url": candidate.source_url})
            downloaded = await self.downloader.download(candidate)
            self._log_event(run_id, "IMAGE_DOWNLOADED", {"url": downloaded.source_url, "size_bytes": len(downloaded.content)})
            
            # 2. Validate
            validated = self.validator.validate(downloaded)
            self._log_event(run_id, "IMAGE_VALIDATED", {"sha256": validated.sha256, "mime": validated.mime_type})
            
            # 3. Filter
            self.filter.check(validated)
            
            # 4. Deduplicate (early check)
            existing = await self.deduplicator.find_duplicate(validated.sha256)
            if existing:
                self._log_event(run_id, "IMAGE_DEDUPLICATED", {"artifact_id": existing.artifact_id, "sha256": existing.sha256})
                return existing
                
            # 5. Store
            artifact = await self.storage.put(validated, candidate)
            self._log_event(run_id, "IMAGE_STORED", {
                "artifact_id": artifact.artifact_id,
                "sha256": artifact.sha256,
                "mime_type": artifact.mime_type,
                "size_bytes": artifact.size_bytes
            })
            
            return artifact
            
        except ImageError as e:
            self._log_event(run_id, "IMAGE_REJECTED", {"url": candidate.source_url, "error": str(e), "code": getattr(e, 'code', 'UNKNOWN')})
            raise e
        except Exception as e:
            self._log_event(run_id, "IMAGE_PIPELINE_FAILED", {"url": candidate.source_url, "error": str(e)})
            raise e
