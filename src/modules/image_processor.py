import os
import requests
import imagehash
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, output_dir="output_images"):
        self.output_dir = output_dir
        self.hash_db = set()
        os.makedirs(self.output_dir, exist_ok=True)

    def download_image(self, url: str) -> Image.Image:
        """Downloads an image from a URL and returns a PIL Image object."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            return img
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None

    def get_image_hash(self, img: Image.Image) -> str:
        """Calculates the perceptual hash of an image."""
        try:
            # Using phash (perceptual hash) which is good for finding similar images
            return str(imagehash.phash(img))
        except Exception as e:
            logger.error(f"Failed to calculate hash: {e}")
            return None

    def process_and_save(self, url: str, filename: str) -> bool:
        """
        Downloads the image, checks for duplicates, and saves it if unique.
        Returns True if saved, False if duplicate or failed.
        """
        img = self.download_image(url)
        if not img:
            return False

        img_hash = self.get_image_hash(img)
        if not img_hash:
            return False

        if img_hash in self.hash_db:
            logger.info(f"Duplicate image detected: {filename} (hash: {img_hash})")
            return False

        # It's a new image
        self.hash_db.add(img_hash)
        
        # Save image
        save_path = os.path.join(self.output_dir, filename)
        try:
            # Convert to RGB if it's RGBA (e.g., PNG to JPEG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(save_path, "JPEG")
            logger.info(f"Saved unique image to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save image to {save_path}: {e}")
            return False
