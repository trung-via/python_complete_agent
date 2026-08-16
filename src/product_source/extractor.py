from __future__ import annotations
from typing import Protocol, Optional
from datetime import datetime
from .models import ProductSourcePack, OriginalMediaRef

class ProductSourceExtractor(Protocol):
    async def extract(self, product_url: str, *, observed_at: Optional[datetime] = None) -> ProductSourcePack: ...

class OriginalMediaDownloader(Protocol):
    async def download(self, media_ref: OriginalMediaRef, output_dir: str) -> str: ...
