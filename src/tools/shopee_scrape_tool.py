import os
import re
import logging
from typing import Dict, Any
from src.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ShopeeScrapeTool(BaseTool):
    @property
    def name(self) -> str:
        return "shopee_scrape"

    @property
    def description(self) -> str:
        return "Scrapes product images from a Shopee URL, processes them, and uploads to Google Drive."

    async def execute(self, url: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Executing ShopeeScrapeTool for URL: {url}")
        
        browser = context.get('browser')
        image_processor = context.get('image_processor')
        gdrive = context.get('gdrive')
        ai_controller = context.get('ai_controller')
        gdrive_folder_id = context.get('gdrive_folder_id')
        
        if not all([browser, image_processor, gdrive, ai_controller]):
            raise ValueError("Missing required context components for ShopeeScrapeTool")

        # 1. Playwright Scraping Logic
        browser_context = browser.get_context()
        if not browser_context:
            logger.error("No active browser context available.")
            return {"status": "error", "message": "Browser context unavailable."}
            
        logger.info(f"Navigating to Shopee: {url}")
        api_images = []
        try:
            page = await browser_context.new_page()
            
            try:
                await page.goto(url, referer="https://google.com/", wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                logger.warning(f"Navigation issue (might still work): {e}")
            
            try:
                await page.wait_for_selector('[role="main"], .page-product__briefing, .product-briefing', timeout=25000)
            except:
                logger.warning("Product main container not found (could be a Captcha or slow loading).")
            
            await page.wait_for_timeout(3000)
            
            try:
                await page.evaluate("window.scrollBy(0, 1000)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollBy(0, 1000)")
                await page.wait_for_timeout(1000)
                await page.wait_for_timeout(1000)
            except:
                pass
                
            try:
                for _ in range(5):
                    arrow = await page.query_selector('svg.icon-arrow-right-bold')
                    if arrow:
                        btn = await arrow.evaluate_handle('node => node.closest("button")')
                        if btn:
                            await btn.click()
                            await page.wait_for_timeout(300)
            except:
                pass
                
            script = r'''() => {
                let images = new Set();
                let productName = document.title ? document.title.split('|')[0].trim() : 'Unknown Product';
                let shopElement = document.querySelector('.VlDReK, .shop-name__text, a[href*="/shop/"] h1, .LrcIX3, .Cq5O3a');
                let shopName = shopElement ? shopElement.innerText.trim() : 'Unknown Shop';
                if (shopName === 'Unknown Shop') {
                    let html = document.documentElement.innerHTML;
                    let m = html.match(/"shopName"\s*:\s*"([^"]+)"/i) || html.match(/"shop_name"\s*:\s*"([^"]+)"/i);
                    if (m) shopName = m[1];
                }
                
                let screenWidth = window.innerWidth;
                let maxRightX = screenWidth * 0.75;
                
                let stopKeywords = ['ĐÁNH GIÁ SẢN PHẨM', 'CÓ THỂ BẠN CŨNG THÍCH', 'CÁC SẢN PHẨM KHÁC', 'TOP SẢN PHẨM NỔI BẬT'];
                let reviewHeader = Array.from(document.querySelectorAll('div, h2')).find(el => 
                    el.innerText && stopKeywords.some(kw => el.innerText.toUpperCase().includes(kw)) && el.innerText.length < 50
                );
                
                let reviewContainer = document.querySelector('.product-ratings, .product-reviews, [data-sqe="rating"]');
                let maxBottomY = document.body.scrollHeight;
                if (reviewHeader) {
                    maxBottomY = reviewHeader.getBoundingClientRect().top + window.scrollY;
                } else if (reviewContainer) {
                    maxBottomY = reviewContainer.getBoundingClientRect().top + window.scrollY;
                }
                
                let allImages = document.querySelectorAll('.page-product__briefing img, .product-briefing img, [role="main"] img, .page-product__detail img, .product-detail img');
                allImages.forEach(img => {
                    let rect = img.getBoundingClientRect();
                    let absoluteY = rect.top + window.scrollY;
                    let absoluteX = rect.left;
                    
                    if (rect.width === 0 && !img.closest('.product-image-carousel__item, .product-image-carousel, [role="main"]')) return;
                    if (rect.width > 0 && rect.width < 40) return;
                    if (rect.height > 0 && rect.height < 40) return;
                    
                    if (absoluteY > maxBottomY) return;
                    if (absoluteY > 800 && absoluteX > maxRightX) return;
                    
                    if (img.src && img.src.includes('susercontent.com')) {
                        images.add(img.src);
                    }
                    
                    let bg = window.getComputedStyle(img).backgroundImage;
                    if (bg && bg.includes('susercontent.com')) {
                        images.add(bg.slice(5, -2));
                    }
                });
                
                let allDivs = document.querySelectorAll('.page-product__briefing div, .product-briefing div, [role="main"] div, .page-product__detail div, .product-detail div');
                allDivs.forEach(div => {
                     let rect = div.getBoundingClientRect();
                     let absoluteY = rect.top + window.scrollY;
                     let absoluteX = rect.left;
                     
                     if (rect.width === 0 && !div.closest('.product-image-carousel__item, .product-image-carousel, [role="main"]')) return;
                     if (rect.width > 0 && rect.width < 40) return;
                     if (rect.height > 0 && rect.height < 40) return;
                     
                     if (absoluteY > maxBottomY) return;
                     if (absoluteY > 800 && absoluteX > maxRightX) return;
                     
                     let bg = window.getComputedStyle(div).backgroundImage;
                     if (bg && bg.includes('susercontent.com')) {
                         images.add(bg.slice(5, -2));
                     }
                });
                
                return {
                    'images': Array.from(images),
                    'product_name': productName,
                    'shop_name': shopName
                };
            }'''
            
            try:
                extracted_data_js = await page.evaluate(script)
                extracted = extracted_data_js.get('images', [])
                for u in extracted:
                    if u.startswith('//'): u = 'https:' + u
                    api_images.append(u)
            except Exception as e:
                logger.error(f"Error executing DOM snipe script: {e}")
                extracted_data_js = {'images': [], 'product_name': 'Unknown Product', 'shop_name': 'Unknown Shop'}
            
            image_urls = []
            for u in set(api_images):
                if u.endswith('_tn'):
                    u = u[:-3]
                if u not in image_urls:
                    image_urls.append(u)
                    
            logger.info(f"Sniper mode extracted {len(image_urls)} core product images.")
            
            extracted_data = {
                'images': image_urls,
                'product_name': extracted_data_js.get('product_name', 'Unknown Product'),
                'shop_name': extracted_data_js.get('shop_name', 'Unknown Shop')
            }
        except Exception as e:
            logger.error(f"Error extracting from Shopee: {e}")
            extracted_data = {'images': [], 'product_name': 'Unknown', 'shop_name': 'Unknown'}
        finally:
            try:
                await page.close()
            except:
                pass

        # 2. Process extracted data
        image_urls = extracted_data.get('images', [])
        product_name = extracted_data.get('product_name', 'Unknown Product')
        shop_name = extracted_data.get('shop_name', 'Unknown Shop')
        
        if not image_urls:
            logger.warning("No images found or extraction failed.")
            return {"status": "error", "message": "No images found."}

        downloaded_files = []
        for i, img_url in enumerate(image_urls):
            filename = f"shopee_img_{i}.jpg"
            saved = image_processor.process_and_save(img_url, filename)
            if saved:
                file_path = os.path.join(image_processor.output_dir, filename)
                downloaded_files.append(file_path)
                
        if not downloaded_files:
            logger.warning("No images could be downloaded locally.")
            return {"status": "error", "message": "Failed to download images."}
            
        unique_files = downloaded_files
        
        logger.info("Setting up GDrive folders...")
        platform_folder_id = gdrive.get_or_create_folder("Shopee", parent_id=gdrive_folder_id)
        if not platform_folder_id:
            platform_folder_id = gdrive_folder_id
            
        safe_product_name = re.sub(r'[\\/*?:"<>|]', "", product_name)[:80].strip() or "Unknown Product"
        product_folder_id = gdrive.get_or_create_folder(safe_product_name, parent_id=platform_folder_id)
        if not product_folder_id:
            product_folder_id = platform_folder_id
            
        info_path = os.path.join(image_processor.output_dir, "info.txt")
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"Product Name: {product_name}\n")
            f.write(f"Shop Name: {shop_name}\n")
            f.write(f"Product Link: {url}\n")
        
        logger.info(f"Uploading metadata and {len(unique_files)} unique images to folder: {safe_product_name}")
        gdrive.upload_file(info_path, folder_id=product_folder_id)
        for file_path in unique_files:
            gdrive.upload_file(file_path, folder_id=product_folder_id)
            
        logger.info("Shopee Scrape task completed successfully.")
        return {"status": "success", "uploaded_count": len(unique_files)}
