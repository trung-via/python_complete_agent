from typing import Protocol, List
from src.images.models import ValidatedImage
from src.images.errors import ImageFilterError

class ImageFilter(Protocol):
    def check(self, image: ValidatedImage) -> None:
        """Raises ImageFilterError if the image is rejected."""
        ...

class BasicImageFilter:
    def __init__(self, 
                 min_width: int = 10,
                 min_height: int = 10,
                 min_pixels: int = 100,
                 max_pixels: int = 50_000_000,
                 allowed_formats: List[str] = None):
        self.min_width = min_width
        self.min_height = min_height
        self.min_pixels = min_pixels
        self.max_pixels = max_pixels
        self.allowed_formats = allowed_formats or ["image/jpeg", "image/png", "image/webp"]

    def check(self, image: ValidatedImage) -> None:
        if image.mime_type not in self.allowed_formats:
            raise ImageFilterError(f"Format {image.mime_type} is not allowed", details={"mime_type": image.mime_type})
            
        if image.width < self.min_width or image.height < self.min_height:
            raise ImageFilterError(f"Image too small: {image.width}x{image.height}", details={"width": image.width, "height": image.height})
            
        pixels = image.width * image.height
        if pixels < self.min_pixels:
            raise ImageFilterError(f"Image has too few pixels: {pixels}")
            
        if pixels > self.max_pixels:
            raise ImageFilterError(f"Image has too many pixels: {pixels}")
