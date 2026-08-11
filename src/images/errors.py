from typing import Optional, Dict, Any
from src.core.errors import AgentException

class ImageError(AgentException):
    """Base class for all errors originating from the Image Pipeline."""
    def __init__(self, message: str, code: str = "IMAGE_ERROR", retryable: bool = False, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code, retryable=retryable, details=details)

# --- Downloader Errors ---

class ImageDownloadError(ImageError):
    def __init__(self, message: str, code: str = "IMAGE_DOWNLOAD_ERROR", retryable: bool = True, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code, retryable=retryable, details=details)

class ImageDownloadTimeoutError(ImageDownloadError):
    def __init__(self, url: str):
        super().__init__(f"Timeout downloading image from {url}", code="IMAGE_DOWNLOAD_TIMEOUT", retryable=True, details={"url": url})

class ImageHttpError(ImageDownloadError):
    def __init__(self, status_code: int, url: str, retryable: bool):
        super().__init__(f"HTTP {status_code} when downloading {url}", code=f"IMAGE_HTTP_{status_code}", retryable=retryable, details={"url": url, "status_code": status_code})

class ImageRedirectError(ImageDownloadError):
    def __init__(self, url: str, message: str = "Too many redirects or unsafe redirect"):
        super().__init__(message, code="IMAGE_REDIRECT_ERROR", retryable=False, details={"url": url})

class ImageSecurityError(ImageDownloadError):
    def __init__(self, url: str, message: str = "Unsafe URL rejected by policy"):
        super().__init__(message, code="IMAGE_SECURITY_ERROR", retryable=False, details={"url": url})

# --- Validation Errors ---

class ImageValidationError(ImageError):
    def __init__(self, message: str, code: str = "IMAGE_VALIDATION_ERROR", details: Optional[Dict[str, Any]] = None):
        # Validation errors are NEVER retryable; the content is fundamentally bad.
        super().__init__(message, code=code, retryable=False, details=details)

class ImageFormatError(ImageValidationError):
    def __init__(self, message: str = "Unsupported or invalid image format"):
        super().__init__(message, code="IMAGE_FORMAT_ERROR")

class ImageCorruptedError(ImageValidationError):
    def __init__(self, message: str = "Image data is corrupted"):
        super().__init__(message, code="IMAGE_CORRUPTED_ERROR")

class ImageTooLargeError(ImageValidationError):
    def __init__(self, size_bytes: int, max_bytes: int):
        super().__init__(f"Image size {size_bytes} exceeds maximum {max_bytes}", code="IMAGE_TOO_LARGE", details={"size_bytes": size_bytes, "max_bytes": max_bytes})

class ImageDimensionsError(ImageValidationError):
    def __init__(self, message: str = "Invalid image dimensions"):
        super().__init__(message, code="IMAGE_DIMENSIONS_ERROR")

# --- Filter Errors ---

class ImageFilterError(ImageError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="IMAGE_FILTER_REJECTED", retryable=False, details=details)

# --- Storage Errors ---

class ArtifactStoreError(ImageError):
    def __init__(self, message: str, retryable: bool = False, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="ARTIFACT_STORE_ERROR", retryable=retryable, details=details)
