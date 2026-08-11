import pytest
import os
from PIL import Image
from src.modules.image_processor import ImageProcessor

def test_image_processor_duplicate_logic(tmp_path):
    # Use tmp_path fixture provided by pytest for temporary directory
    processor = ImageProcessor(output_dir=str(tmp_path))
    
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color = 'red')
    
    # Hash it
    img_hash = processor.get_image_hash(img)
    assert img_hash is not None
    
    # Add to DB
    processor.hash_db.add(img_hash)
    
    # Check if duplicate logic works (mocking the download part)
    # We'll bypass download_image by manually injecting the hash check
    assert img_hash in processor.hash_db
    
    # Another identical image should yield the same hash
    img2 = Image.new('RGB', (100, 100), color = 'red')
    hash2 = processor.get_image_hash(img2)
    assert hash2 == img_hash
    
    # A different image should yield a different hash (add a pattern so phash differs)
    from PIL import ImageDraw
    img3 = Image.new('RGB', (100, 100), color = 'blue')
    draw = ImageDraw.Draw(img3)
    draw.rectangle([10, 10, 50, 50], fill="white")
    hash3 = processor.get_image_hash(img3)
    assert hash3 != img_hash
