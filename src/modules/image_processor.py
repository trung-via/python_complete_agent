import os
import json
import imagehash
import asyncio
import aiohttp
from PIL import Image
from io import BytesIO
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, output_dir="data/images", db_path="data/hash_db.json"):
        self.output_dir = output_dir
        self.db_path = db_path
        self.hash_db = set()
        
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        self._load_db()

    def _load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.hash_db = set(data)
                logger.info(f"Loaded {len(self.hash_db)} image hashes from persistence.")
            except Exception as e:
                logger.error(f"Failed to load hash DB: {e}")

    def _save_db(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(list(self.hash_db), f)
        except Exception as e:
            logger.error(f"Failed to save hash DB: {e}")

    async def download_image(self, url: str) -> Optional[Image.Image]:
        """Downloads an image asynchronously using aiohttp."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as response:
                    response.raise_for_status()
                    content = await response.read()
                    
            def _open_img(c):
                return Image.open(BytesIO(c)).copy() # Force load into memory before closing BytesIO
                
            img = await asyncio.to_thread(_open_img, content)
            return img
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None

    def get_image_hash(self, img: Image.Image) -> Optional[str]:
        """Calculates the perceptual hash of an image."""
        try:
            return str(imagehash.phash(img))
        except Exception as e:
            logger.error(f"Failed to calculate hash: {e}")
            return None

    async def process_and_save(self, url: str) -> Optional[str]:
        """
        Downloads the image, checks for duplicates, and saves it using its hash.
        Returns the filename if saved/already exists, None if failed.
        """
        img = await self.download_image(url)
        if not img:
            return None

        img_hash = await asyncio.to_thread(self.get_image_hash, img)
        if not img_hash:
            return None

        filename = f"img_{img_hash}.jpg"
        save_path = os.path.join(self.output_dir, filename)

        if img_hash in self.hash_db or os.path.exists(save_path):
            logger.info(f"Duplicate/existing image detected: {filename}")
            # Ensure it is in DB if the file existed but DB didn't have it
            if img_hash not in self.hash_db:
                self.hash_db.add(img_hash)
                self._save_db()
            return filename
        
        try:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            # Save in a separate thread just in case it's a large image
            await asyncio.to_thread(img.save, save_path, "JPEG")
            
            # TRANSACTION FIX: Only add to hash_db AFTER successful save
            self.hash_db.add(img_hash)
            self._save_db()
            
            logger.info(f"Saved unique image to {save_path}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save image to {save_path}: {e}")
            return None
