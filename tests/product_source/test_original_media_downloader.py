from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from src.product_source.downloader import (
    CHUNK_SIZE,
    MAX_FILE_BYTES,
    MAX_MEDIA_PER_PRODUCT,
    OriginalMediaDownloader,
)
from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    OriginalMediaRef,
)


@pytest.fixture
def jpeg_bytes() -> bytes:
    """Minimal valid JPEG bytes."""
    return b"\xFF\xD8\xFF\xE0" + b"\x00" * 100


@pytest.fixture
def png_bytes() -> bytes:
    """Minimal valid PNG bytes."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture
def downloader() -> OriginalMediaDownloader:
    temp_dir = tempfile.mkdtemp()
    return OriginalMediaDownloader(output_dir=temp_dir)


class FakeStreamContent:
    """Simulates an aiohttp response.content stream."""
    def __init__(self, data: bytes, chunk_size: int = CHUNK_SIZE):
        self._data = data
        self._offset = 0
        self._chunk_size = chunk_size
        self.chunks_read = 0

    async def read(self, n: int = -1) -> bytes:
        if self._offset >= len(self._data):
            return b""
        read_len = self._chunk_size if n <= 0 else min(n, self._chunk_size)
        chunk = self._data[self._offset : self._offset + read_len]
        self._offset += len(chunk)
        self.chunks_read += 1
        return chunk


class FakeAiohttpResponse:
    def __init__(
        self,
        status: int = 200,
        body: bytes = b"",
        headers: Optional[Dict[str, str]] = None,
        exc: Optional[Exception] = None,
    ):
        self.status = status
        self._body = body
        self.headers = headers or {"Content-Type": "image/jpeg"}
        self._exc = exc
        self.content = FakeStreamContent(body)

    async def __aenter__(self):
        if self._exc:
            raise self._exc
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def read(self) -> bytes:
        return self._body


def _mock_session_get_map(response_map: Dict[str, FakeAiohttpResponse]):
    def fake_get(url: str, *args, **kwargs):
        if url in response_map:
            return response_map[url]
        return FakeAiohttpResponse(status=404, body=b"Not found")
    return fake_get


@pytest.mark.asyncio
async def test_preserves_exact_original_bytes(downloader: OriginalMediaDownloader, jpeg_bytes: bytes):
    """1. Preserves exact original bytes."""
    ref = OriginalMediaRef(
        source_url="http://example.com/img1.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    resp_map = {
        "http://example.com/img1.jpg": FakeAiohttpResponse(
            status=200, body=jpeg_bytes, headers={"Content-Type": "image/jpeg"}
        )
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref])

    assert len(downloaded_refs) == 1
    assert downloaded_refs[0].local_filename is not None
    out_file = os.path.join(downloader.original_dir, downloaded_refs[0].local_filename)
    with open(out_file, "rb") as f:
        saved_bytes = f.read()
    assert saved_bytes == jpeg_bytes


@pytest.mark.asyncio
async def test_streaming_oversize_media_aborts_early(downloader: OriginalMediaDownloader):
    """2. Streaming oversize download aborts during transfer without reading entire payload."""
    ref = OriginalMediaRef(
        source_url="http://example.com/huge.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    # Simulate a stream with 25 MiB data in 64 KiB chunks
    total_oversize_bytes = 25 * 1024 * 1024
    payload = b"\xFF\xD8\xFF\xE0" + b"\x00" * (total_oversize_bytes - 4)
    fake_resp = FakeAiohttpResponse(
        status=200, body=payload, headers={"Content-Type": "image/jpeg"}
    )
    resp_map = {"http://example.com/huge.jpg": fake_resp}

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref])

    assert len(downloaded_refs) == 0
    assert any("OVERSIZE_MEDIA_REJECTED" in str(d) for d in diagnostics)
    # Verify stream reading stopped early (before reading all ~400 chunks)
    max_expected_chunks = (MAX_FILE_BYTES // CHUNK_SIZE) + 2
    assert fake_resp.content.chunks_read <= max_expected_chunks + 5


@pytest.mark.asyncio
async def test_diagnostics_do_not_leak_sensitive_url_tokens(downloader: OriginalMediaDownloader):
    """3. Diagnostics do not leak token/auth query parameters."""
    ref = OriginalMediaRef(
        source_url="http://example.com/image.jpg?token=secret_abc_123&session=user_xyz",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    resp_map = {
        ref.source_url: FakeAiohttpResponse(status=403, body=b"Forbidden")
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref])

    assert len(downloaded_refs) == 0
    diag_str = " ".join(diagnostics)
    assert "secret_abc_123" not in diag_str
    assert "user_xyz" not in diag_str
    assert "token=%5BREDACTED%5D" in diag_str or "token=[REDACTED]" in diag_str


@pytest.mark.asyncio
async def test_byte_duplicate_collapse_leaves_no_orphan_files(
    downloader: OriginalMediaDownloader, jpeg_bytes: bytes
):
    """4. Byte-duplicate collapse leaves exactly one file in original/ directory."""
    ref1 = OriginalMediaRef(
        source_url="http://example.com/img1.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    ref2 = OriginalMediaRef(
        source_url="http://example.com/img2.jpg",
        platform="shopee",
        role=MediaRole.GALLERY,
        provenance=MediaProvenance.SEMANTIC_PRODUCT_GALLERY,
        ordinal=1,
    )
    resp_map = {
        "http://example.com/img1.jpg": FakeAiohttpResponse(
            status=200, body=jpeg_bytes, headers={"Content-Type": "image/jpeg"}
        ),
        "http://example.com/img2.jpg": FakeAiohttpResponse(
            status=200, body=jpeg_bytes, headers={"Content-Type": "image/jpeg"}
        ),
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref1, ref2])

    assert len(downloaded_refs) == 1
    # Check physical files in directory
    files_on_disk = os.listdir(downloader.original_dir)
    assert len(files_on_disk) == 1


@pytest.mark.asyncio
async def test_canonical_url_dedupe_before_download(
    downloader: OriginalMediaDownloader, jpeg_bytes: bytes
):
    """5. Canonical URL dedupe before download."""
    ref1 = OriginalMediaRef(
        source_url="http://example.com/img1.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.PLATFORM_SCOPED_FALLBACK,
        ordinal=0,
    )
    ref2 = OriginalMediaRef(
        source_url="http://example.com/img1.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=1,
    )
    resp_map = {
        "http://example.com/img1.jpg": FakeAiohttpResponse(
            status=200, body=jpeg_bytes, headers={"Content-Type": "image/jpeg"}
        )
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref1, ref2])

    assert len(downloaded_refs) == 1
    assert downloaded_refs[0].provenance == MediaProvenance.STRUCTURED_PRODUCT_DATA


@pytest.mark.asyncio
async def test_max_media_per_product_enforced(
    downloader: OriginalMediaDownloader, jpeg_bytes: bytes
):
    """6. Max media per product enforced."""
    refs = [
        OriginalMediaRef(
            source_url=f"http://example.com/img{i}.jpg",
            platform="shopee",
            role=MediaRole.GALLERY,
            provenance=MediaProvenance.SEMANTIC_PRODUCT_GALLERY,
            ordinal=i,
        )
        for i in range(35)
    ]
    resp_map = {
        f"http://example.com/img{i}.jpg": FakeAiohttpResponse(
            status=200,
            body=b"\xFF\xD8\xFF\xE0" + bytes([i]) * 50,
            headers={"Content-Type": "image/jpeg"},
        )
        for i in range(35)
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media(refs)

    assert len(downloaded_refs) <= MAX_MEDIA_PER_PRODUCT
