import io
import magic
import hashlib
from typing import Protocol
from PIL import Image, UnidentifiedImageError

from src.images.models import DownloadedImage, ValidatedImage
from src.images.errors import (
    ImageFormatError,
    ImageCorruptedError,
    ImageTooLargeError,
    ImageDimensionsError
)

class ImageValidator(Protocol):
    def validate(self, image: DownloadedImage) -> ValidatedImage:
        ...

class StrictImageValidator:
    def __init__(self, max_bytes: int = 10 * 1024 * 1024):
        self.max_bytes = max_bytes

    def validate(self, image: DownloadedImage) -> ValidatedImage:
        content = image.content
        size_bytes = len(content)
        
        # 1. Size check
        if size_bytes > self.max_bytes:
            raise ImageTooLargeError(size_bytes, self.max_bytes)
            
        if size_bytes == 0:
            raise ImageCorruptedError("Image is empty (0 bytes)")
            
        # 2. Magic bytes / MIME detection
        try:
            mime_type = magic.from_buffer(content, mime=True)
        except Exception as e:
            raise ImageCorruptedError(f"Could not determine magic bytes: {e}")
            
        if not mime_type.startswith("image/"):
            raise ImageFormatError(f"Detected MIME type is not an image: {mime_type}")
            
        # 3. Decode & check dimensions
        try:
            img = Image.open(io.BytesIO(content))
            img.verify() # Verify it's actually an image
            
            # verify() doesn't always catch everything, we need to reopen to get safe dimensions
            # actually verify() closes the file in some PIL versions, so reopen:
            img = Image.open(io.BytesIO(content))
            width, height = img.size
            
            if width <= 0 or height <= 0:
                raise ImageDimensionsError("Image dimensions must be positive")
                
        except UnidentifiedImageError:
            raise ImageFormatError("Image could not be decoded by PIL")
        except Exception as e:
            raise ImageCorruptedError(f"Image is corrupted or unreadable: {e}")
            
        # 4. Hash (SHA-256)
        hasher = hashlib.sha256()
        hasher.update(content)
        sha256_hash = hasher.hexdigest()
        
        return ValidatedImage(
            content=content,
            mime_type=mime_type,
            width=width,
            height=height,
            size_bytes=size_bytes,
            sha256=sha256_hash
        )
