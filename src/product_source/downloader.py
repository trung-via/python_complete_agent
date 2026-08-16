from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from collections.abc import Sequence
from dataclasses import replace
from typing import List, Optional, Set, Tuple

import aiohttp

from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
    sanitize_url,
)

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MiB
MAX_MEDIA_PER_PRODUCT = 30
DOWNLOAD_TIMEOUT_SECONDS = 30
CHUNK_SIZE = 64 * 1024  # 64 KiB chunks for streaming

SUPPORTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/svg+xml",
}

CONTENT_TYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/svg+xml": "svg",
}

PROVENANCE_PRIORITY = {
    MediaProvenance.STRUCTURED_PRODUCT_DATA: 5,
    MediaProvenance.SEMANTIC_PRODUCT_GALLERY: 4,
    MediaProvenance.SEMANTIC_VARIANT_MEDIA: 3,
    MediaProvenance.SEMANTIC_SELLER_DESCRIPTION: 2,
    MediaProvenance.PLATFORM_SCOPED_FALLBACK: 1,
}


def _validate_image_magic(data: bytes) -> bool:
    if len(data) < 4:
        return False
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
    if b"<svg" in data[:1024].lower():
        return True
    return False


def _derive_extension(content_type: str) -> str:
    return CONTENT_TYPE_TO_EXT.get(content_type.lower(), "bin")


class OriginalMediaDownloader:
    """
    Downloads accepted original media references byte-preservingly.
    Enforces streaming size bounds, magic byte checks, and two-stage deduplication.
    """

    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir
        self.original_dir = os.path.join(output_dir, "original")
        os.makedirs(self.original_dir, exist_ok=True)

    async def download_accepted_media(
        self, media_refs: Sequence[OriginalMediaRef]
    ) -> Tuple[List[OriginalMediaRef], List[str]]:
        diagnostics: List[str] = []

        # 1. Pre-download URL deduplication (highest-confidence provenance tier first)
        unique_refs_map: dict[str, OriginalMediaRef] = {}
        for ref in media_refs:
            url = ref.source_url
            if url not in unique_refs_map:
                unique_refs_map[url] = ref
            else:
                existing = unique_refs_map[url]
                existing_priority = PROVENANCE_PRIORITY.get(existing.provenance, 0)
                new_priority = PROVENANCE_PRIORITY.get(ref.provenance, 0)
                if new_priority > existing_priority:
                    unique_refs_map[url] = ref
                elif new_priority == existing_priority and ref.ordinal < existing.ordinal:
                    unique_refs_map[url] = ref

        deduped_refs = sorted(unique_refs_map.values(), key=lambda r: r.ordinal)[:MAX_MEDIA_PER_PRODUCT]

        downloaded_refs: List[OriginalMediaRef] = []
        seen_hashes: Set[str] = set()

        # 2. Download each streamingly with bounded chunks
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_SECONDS)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for ref in deduped_refs:
                safe_url = sanitize_url(ref.source_url)
                if not (ref.source_url.startswith("http://") or ref.source_url.startswith("https://")):
                    diagnostics.append(f"NON_HTTP_URL_SKIPPED: {safe_url}")
                    continue

                try:
                    async with session.get(ref.source_url) as response:
                        if response.status != 200:
                            diagnostics.append(f"HTTP_ERROR_{response.status}: {safe_url}")
                            continue

                        # Header content-length check if present
                        content_length = response.headers.get("Content-Length")
                        if content_length:
                            try:
                                if int(content_length) > MAX_FILE_BYTES:
                                    diagnostics.append(f"OVERSIZE_MEDIA_REJECTED: {safe_url}")
                                    continue
                            except ValueError:
                                pass

                        # Content-Type check
                        raw_content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                        if raw_content_type and raw_content_type not in SUPPORTED_CONTENT_TYPES:
                            diagnostics.append(f"UNSUPPORTED_CONTENT_TYPE: {raw_content_type} for {safe_url}")
                            continue

                        # Stream reading with running byte counter
                        chunks: List[bytes] = []
                        received_bytes = 0
                        oversize = False

                        if hasattr(response, "content") and hasattr(response.content, "read"):
                            while True:
                                chunk = await response.content.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                received_bytes += len(chunk)
                                if received_bytes > MAX_FILE_BYTES:
                                    oversize = True
                                    break
                                chunks.append(chunk)
                        elif hasattr(response, "read"):
                            data = await response.read()
                            if len(data) > MAX_FILE_BYTES:
                                oversize = True
                            else:
                                chunks.append(data)
                                received_bytes = len(data)

                        if oversize:
                            diagnostics.append(f"OVERSIZE_MEDIA_REJECTED: {safe_url}")
                            continue

                        full_data = b"".join(chunks)
                        if not full_data:
                            diagnostics.append(f"EMPTY_RESPONSE_BODY: {safe_url}")
                            continue

                        if not _validate_image_magic(full_data):
                            diagnostics.append(f"INVALID_IMAGE_MAGIC: {safe_url}")
                            continue

                        # Compute SHA-256
                        sha256_hash = hashlib.sha256(full_data).hexdigest()

                        # Stage 2: Post-download SHA-256 duplicate collapse
                        if sha256_hash in seen_hashes:
                            diagnostics.append(f"SHA256_DUPLICATE_COLLAPSED: {sha256_hash[:12]}")
                            continue

                        seen_hashes.add(sha256_hash)

                        # Determine extension and write unchanged bytes
                        eff_content_type = raw_content_type if raw_content_type in SUPPORTED_CONTENT_TYPES else "image/jpeg"
                        ext = _derive_extension(eff_content_type)
                        filename = f"orig_{ref.ordinal:03d}_{sha256_hash[:12]}.{ext}"
                        filepath = os.path.join(self.original_dir, filename)

                        with open(filepath, "wb") as f:
                            f.write(full_data)

                        updated_ref = replace(
                            ref,
                            content_type=eff_content_type,
                            byte_size=len(full_data),
                            sha256_hash=sha256_hash,
                            local_filename=filename,
                        )
                        downloaded_refs.append(updated_ref)

                except asyncio.TimeoutError:
                    diagnostics.append(f"DOWNLOAD_TIMEOUT: {safe_url}")
                except Exception as e:
                    diagnostics.append(f"DOWNLOAD_ERROR: {safe_url} ({type(e).__name__})")

        return downloaded_refs, diagnostics
