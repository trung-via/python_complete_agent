from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest

from src.product_source.downloader import (
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

    async def __aenter__(self):
        if self._exc:
            raise self._exc
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def read(self) -> bytes:
        return self._body


def _mock_session_get_map(response_map: Dict[str, FakeAiohttpResponse]):
    """Returns a mock ClientSession where get(url) looks up response_map."""
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
async def test_sha256_matches_source_bytes(downloader: OriginalMediaDownloader, jpeg_bytes: bytes):
    """2. SHA-256 matches source bytes."""
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

    expected_hash = hashlib.sha256(jpeg_bytes).hexdigest()
    assert downloaded_refs[0].sha256_hash == expected_hash


@pytest.mark.asyncio
async def test_invalid_non_image_payload_rejected(downloader: OriginalMediaDownloader):
    """3. Invalid/non-image payload rejected."""
    ref = OriginalMediaRef(
        source_url="http://example.com/text.txt",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    resp_map = {
        "http://example.com/text.txt": FakeAiohttpResponse(
            status=200, body=b"<html>Hello HTML</html>", headers={"Content-Type": "text/html"}
        )
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref])

    assert len(downloaded_refs) == 0
    assert len(diagnostics) > 0


@pytest.mark.asyncio
async def test_oversize_media_rejected(downloader: OriginalMediaDownloader):
    """5. Oversize media rejected."""
    ref = OriginalMediaRef(
        source_url="http://example.com/big.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    # 21 MiB payload
    big_bytes = b"\xFF\xD8\xFF\xE0" + b"\x00" * (MAX_FILE_BYTES + 1024)
    resp_map = {
        "http://example.com/big.jpg": FakeAiohttpResponse(
            status=200, body=big_bytes, headers={"Content-Type": "image/jpeg"}
        )
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref])

    assert len(downloaded_refs) == 0
    assert any("OVERSIZE_MEDIA_REJECTED" in str(d) for d in diagnostics)


@pytest.mark.asyncio
async def test_byte_duplicate_collapse_after_download(
    downloader: OriginalMediaDownloader, jpeg_bytes: bytes
):
    """6. Byte-duplicate collapse after download."""
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
    assert any("SHA256_DUPLICATE_COLLAPSED" in str(d) for d in diagnostics)


@pytest.mark.asyncio
async def test_perceptual_hash_near_duplicates_not_deleted(
    downloader: OriginalMediaDownloader, jpeg_bytes: bytes, png_bytes: bytes
):
    """7. Perceptual-hash near duplicates NOT aggressively deleted."""
    ref1 = OriginalMediaRef(
        source_url="http://example.com/img1.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    ref2 = OriginalMediaRef(
        source_url="http://example.com/img2.png",
        platform="shopee",
        role=MediaRole.GALLERY,
        provenance=MediaProvenance.SEMANTIC_PRODUCT_GALLERY,
        ordinal=1,
    )
    resp_map = {
        "http://example.com/img1.jpg": FakeAiohttpResponse(
            status=200, body=jpeg_bytes, headers={"Content-Type": "image/jpeg"}
        ),
        "http://example.com/img2.png": FakeAiohttpResponse(
            status=200, body=png_bytes, headers={"Content-Type": "image/png"}
        ),
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref1, ref2])

    assert len(downloaded_refs) == 2


@pytest.mark.asyncio
async def test_malformed_one_ref_does_not_discard_siblings(
    downloader: OriginalMediaDownloader, jpeg_bytes: bytes
):
    """8. Malformed one ref does not discard siblings."""
    ref1 = OriginalMediaRef(
        source_url="http://example.com/img1.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    ref2 = OriginalMediaRef(
        source_url="http://example.com/fail.jpg",
        platform="shopee",
        role=MediaRole.GALLERY,
        provenance=MediaProvenance.SEMANTIC_PRODUCT_GALLERY,
        ordinal=1,
    )
    resp_map = {
        "http://example.com/img1.jpg": FakeAiohttpResponse(
            status=200, body=jpeg_bytes, headers={"Content-Type": "image/jpeg"}
        ),
        "http://example.com/fail.jpg": FakeAiohttpResponse(
            status=404, body=b"Not found"
        ),
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref1, ref2])

    assert len(downloaded_refs) == 1
    assert downloaded_refs[0].source_url == "http://example.com/img1.jpg"


@pytest.mark.asyncio
async def test_canonical_url_dedupe_before_download(
    downloader: OriginalMediaDownloader, jpeg_bytes: bytes
):
    """9. Canonical URL dedupe before download (preserves highest confidence)."""
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
    """10. Max media per product enforced (30 max)."""
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


@pytest.mark.asyncio
async def test_content_type_validation(downloader: OriginalMediaDownloader, jpeg_bytes: bytes):
    """11. Content-type validation: header not in supported rejected."""
    ref = OriginalMediaRef(
        source_url="http://example.com/img1.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    resp_map = {
        "http://example.com/img1.jpg": FakeAiohttpResponse(
            status=200, body=jpeg_bytes, headers={"Content-Type": "text/html"}
        )
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref])

    assert len(downloaded_refs) == 0


@pytest.mark.asyncio
async def test_timeout_handling(downloader: OriginalMediaDownloader):
    """12. Timeout handling."""
    ref = OriginalMediaRef(
        source_url="http://example.com/timeout.jpg",
        platform="shopee",
        role=MediaRole.PRIMARY,
        provenance=MediaProvenance.STRUCTURED_PRODUCT_DATA,
        ordinal=0,
    )
    resp_map = {
        "http://example.com/timeout.jpg": FakeAiohttpResponse(
            exc=asyncio.TimeoutError("Connection timed out")
        )
    }

    with patch("aiohttp.ClientSession.get", side_effect=_mock_session_get_map(resp_map)):
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref])

    assert len(downloaded_refs) == 0
    assert any("TIMEOUT" in str(d) for d in diagnostics)


@pytest.mark.asyncio
async def test_deterministic_filename(downloader: OriginalMediaDownloader, jpeg_bytes: bytes):
    """14. Deterministic filename formatting."""
    ref = OriginalMediaRef(
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
        downloaded_refs, diagnostics = await downloader.download_accepted_media([ref])

    sha256_hash = hashlib.sha256(jpeg_bytes).hexdigest()[:12]
    expected_filename = f"orig_001_{sha256_hash}.jpg"

    assert len(downloaded_refs) == 1
    assert downloaded_refs[0].local_filename == expected_filename
