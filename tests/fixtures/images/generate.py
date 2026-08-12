import os
from PIL import Image

def generate_fixtures():
    os.makedirs("tests/fixtures/images", exist_ok=True)
    
    # 1. Valid JPEG
    img = Image.new('RGB', (10, 10), color = 'red')
    img.save('tests/fixtures/images/valid.jpg', format='JPEG')
    
    # 2. Valid PNG
    img = Image.new('RGB', (10, 10), color = 'blue')
    img.save('tests/fixtures/images/valid.png', format='PNG')
    
    # 3. Corrupted image (just some text)
    with open('tests/fixtures/images/corrupted.jpg', 'w') as f:
        f.write('This is not an image at all.')
        
if __name__ == '__main__':
    generate_fixtures()
    print("Fixtures generated.")
