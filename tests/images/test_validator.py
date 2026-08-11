import pytest
import os
from src.images.validator import StrictImageValidator
from src.images.models import DownloadedImage
from src.images.errors import (
    ImageFormatError,
    ImageCorruptedError,
    ImageTooLargeError
)

@pytest.fixture
def valid_jpg_bytes():
    with open("tests/fixtures/images/valid.jpg", "rb") as f:
        return f.read()

@pytest.fixture
def valid_png_bytes():
    with open("tests/fixtures/images/valid.png", "rb") as f:
        return f.read()

@pytest.fixture
def corrupted_bytes():
    with open("tests/fixtures/images/corrupted.jpg", "rb") as f:
        return f.read()

def test_validator_valid_images(valid_jpg_bytes, valid_png_bytes):
    validator = StrictImageValidator()
    
    # JPG
    img = DownloadedImage(content=valid_jpg_bytes, source_url="http://x", final_url="http://x")
    val_jpg = validator.validate(img)
    assert val_jpg.mime_type in ("image/jpeg", "image/jpg")
    assert val_jpg.width == 10
    assert val_jpg.height == 10
    
    # PNG
    img = DownloadedImage(content=valid_png_bytes, source_url="http://x", final_url="http://x")
    val_png = validator.validate(img)
    assert val_png.mime_type == "image/png"
    assert val_png.width == 10
    assert val_png.height == 10

def test_validator_corrupted(corrupted_bytes):
    validator = StrictImageValidator()
    img = DownloadedImage(content=corrupted_bytes, source_url="http://x", final_url="http://x")
    
    # Depending on magic bytes it might fail format or corrupted
    with pytest.raises((ImageFormatError, ImageCorruptedError)):
        validator.validate(img)

def test_validator_too_large(valid_jpg_bytes):
    validator = StrictImageValidator(max_bytes=10) # 10 bytes max
    img = DownloadedImage(content=valid_jpg_bytes, source_url="http://x", final_url="http://x")
    
    with pytest.raises(ImageTooLargeError):
        validator.validate(img)
