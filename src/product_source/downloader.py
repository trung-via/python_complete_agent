from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import Sequence
from dataclasses import replace
import aiohttp

# Assuming these are available from the models file as specified
from src.product_source.models import OriginalMediaRef, MediaProvenance

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MiB
MAX_MEDIA_PER_PRODUCT = 30
DOWNLOAD_TIMEOUT_SECONDS = 30

SUPPORTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/svg+xml"
}

CONTENT_TYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/svg+xml": "svg"
}

# Ordered by highest confidence first
PROVENANCE_PRIORITY = {
    MediaProvenance.STRUCTURED_PRODUCT_DATA: 5,
    MediaProvenance.SEMANTIC_PRODUCT_GALLERY: 4,
    MediaProvenance.SEMANTIC_VARIANT_MEDIA: 3,
    MediaProvenance.SEMANTIC_SELLER_DESCRIPTION: 2,
    MediaProvenance.PLATFORM_SCOPED_FALLBACK: 1,
}

def _validate_image_magic(data: bytes) -> bool:
    if data.startswith(b"\xFF\xD8"):
        return True  # JPEG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True  # PNG
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return True  # GIF
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return True  # WebP
    if data.startswith(b"BM"):
        return True  # BMP
    if data.startswith(b"II\x2A\x00") or data.startswith(b"MM\x00\x2A"):
        return True  # TIFF
    if b"<svg" in data[:1024]: # Basic check for SVG
        return True
    return False

def _derive_extension(content_type: str) -> str:
    return CONTENT_TYPE_TO_EXT.get(content_type.lower(), "bin")

class OriginalMediaDownloader:
    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir
        self.original_dir = os.path.join(output_dir, "original")
        os.makedirs(self.original_dir, exist_ok=True)

    async def download_accepted_media(self, media_refs: Sequence[OriginalMediaRef]) -> tuple[list[OriginalMediaRef], list[str]]:
        diagnostics: list[str] = []
        
        # 1. Pre-download URL dedupe
        unique_refs_map: dict[str, OriginalMediaRef] = {}
        for ref in media_refs:
            url = ref.source_url
            if url not in unique_refs_map:
                unique_refs_map[url] = ref
            else:
                # Compare provenance confidence
                existing = unique_refs_map[url]
                existing_priority = PROVENANCE_PRIORITY.get(existing.provenance, 0)
                new_priority = PROVENANCE_PRIORITY.get(ref.provenance, 0)
                
                if new_priority > existing_priority:
                    unique_refs_map[url] = ref
                elif new_priority == existing_priority:
                    # Preserve first-seen ordinal order
                    if ref.ordinal < existing.ordinal:
                        unique_refs_map[url] = ref

        # Sort by ordinal and cap at MAX_MEDIA_PER_PRODUCT
        deduped_refs = sorted(unique_refs_map.values(), key=lambda r: r.ordinal)[:MAX_MEDIA_PER_PRODUCT]
        
        updated_refs: list[OriginalMediaRef] = []
        
        # 2. Download each
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_SECONDS),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        ) as session:
            for ref in deduped_refs:
                if not (ref.source_url.startswith("http://") or ref.source_url.startswith("https://")):
                    diagnostics.append(f"NON_HTTP_URL_SKIPPED: {ref.source_url}")
                    continue
                
                try:
                    async with session.get(ref.source_url) as response:
                        if response.status != 200:
                            diagnostics.append(f"HTTP_ERROR_{response.status}: {ref.source_url}")
                            continue
                            
                        # Check header content-type if available
                        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                        
                        data = await response.read()
                        
                        if len(data) > MAX_FILE_BYTES:
                            diagnostics.append(f"OVERSIZE_MEDIA_REJECTED: {ref.source_url}")
                            continue
                            
                        # If content-type from header is missing or not in supported, try to derive or just check magic
                        # Actually, instruction says: "Validate content-type is in SUPPORTED_CONTENT_TYPES (check both response header and magic bytes)"
                        if content_type not in SUPPORTED_CONTENT_TYPES:
                            diagnostics.append(f"UNSUPPORTED_CONTENT_TYPE: {content_type} for {ref.source_url}")
                            continue
                            
                        if not _validate_image_magic(data):
                            diagnostics.append(f"INVALID_IMAGE_MAGIC: {ref.source_url}")
                            continue
                            
                        # Hash
                        sha256_hash = hashlib.sha256(data).hexdigest()
                        
                        # Save
                        ext = _derive_extension(content_type)
                        filename = f"orig_{ref.ordinal:03d}_{sha256_hash[:12]}.{ext}"
                        filepath = os.path.join(self.original_dir, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(data)
                            
                        # Update ref
                        updated_ref = replace(
                            ref,
                            content_type=content_type,
                            byte_size=len(data),
                            sha256_hash=sha256_hash,
                            local_filename=filename
                        )
                        updated_refs.append(updated_ref)
                        
                except asyncio.TimeoutError:
                    diagnostics.append(f"DOWNLOAD_TIMEOUT: {ref.source_url}")
                except Exception as e:
                    diagnostics.append(f"DOWNLOAD_ERROR: {ref.source_url} ({str(e)})")

        # 3. Post-download SHA-256 dedupe
        seen_hashes: set[str] = set()
        final_refs: list[OriginalMediaRef] = []
        
        for ref in updated_refs:
            if ref.sha256_hash in seen_hashes:
                diagnostics.append(f"SHA256_DUPLICATE_COLLAPSED: {ref.sha256_hash}")
            else:
                seen_hashes.add(ref.sha256_hash) # type: ignore
                final_refs.append(ref)
                
        return final_refs, diagnostics
