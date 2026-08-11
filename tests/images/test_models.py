import pytest
from src.images.models import ImageCandidate, ValidatedImage, ImageArtifact

def test_image_candidate_validation():
    # Valid
    ImageCandidate(source_url="https://example.com/img.jpg")
    
    # Invalid scheme
    with pytest.raises(ValueError, match="http or https"):
        ImageCandidate(source_url="ftp://example.com/img.jpg")
        
    # Empty url
    with pytest.raises(ValueError):
        ImageCandidate(source_url="")

def test_validated_image_validation():
    # Valid
    ValidatedImage(
        content=b"123",
        mime_type="image/jpeg",
        width=10,
        height=10,
        size_bytes=3,
        sha256="abc"
    )
    
    # Negative size
    with pytest.raises(ValueError):
        ValidatedImage(content=b"", mime_type="image/jpeg", width=10, height=10, size_bytes=-1, sha256="abc")
        
    # Zero dimension
    with pytest.raises(ValueError):
        ValidatedImage(content=b"", mime_type="image/jpeg", width=0, height=10, size_bytes=3, sha256="abc")
        
    # Empty sha256
    with pytest.raises(ValueError):
        ValidatedImage(content=b"", mime_type="image/jpeg", width=10, height=10, size_bytes=3, sha256="")

def test_image_artifact_validation():
    ImageArtifact(
        artifact_id="a1",
        sha256="abc",
        mime_type="image/jpeg",
        size_bytes=3,
        width=10,
        height=10,
        source_url="https://example.com/img.jpg",
        storage_key="/tmp/a1"
    )
    
    with pytest.raises(ValueError):
        ImageArtifact(
            artifact_id="",
            sha256="abc",
            mime_type="image/jpeg",
            size_bytes=3,
            width=10,
            height=10,
            source_url="https://example.com/img.jpg",
            storage_key="/tmp/a1"
        )
