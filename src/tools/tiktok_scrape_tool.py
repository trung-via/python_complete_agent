import os
import re
import logging
from typing import Dict, Any
from src.core.base_tool import BaseTool
from src.core.types import ToolCall, ToolResult
from src.core.errors import DependencyError, BrowserNavigationError, ExtractionError

logger = logging.getLogger(__name__)

class TikTokScrapeTool(BaseTool):
    @property
    def name(self) -> str:
        return "tiktok_scrape"

    @property
    def description(self) -> str:
        return "Scrapes product images from a TikTok Shop URL, processes them, and uploads to Google Drive."

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The TikTok Shop product URL to scrape"
                }
            },
            "required": ["url"]
        }

    async def execute(self, call: ToolCall, context: Dict[str, Any]) -> ToolResult:
        url = call.arguments.get("url")
        if not url:
            return ToolResult(is_success=False, error_message="Missing 'url' in arguments.")
            
        logger.info(f"Executing TikTokScrapeTool for URL: {url}")
        
        browser = context.get('browser')
        image_processor = context.get('image_processor')
        gdrive = context.get('gdrive')
        ai_controller = context.get('ai_controller')
        gdrive_folder_id = context.get('gdrive_folder_id')
        
        if not all([browser, image_processor, gdrive, ai_controller]):
            raise DependencyError("Missing required context components for TikTokScrapeTool")

        # 1. Playwright Scraping Logic
        logger.info(f"Navigating to TikTok: {url}")
        result = {'images': [], 'product_name': 'TikTok Product', 'shop_name': 'TikTok Shop'}
        images = set()
        
        async with browser.new_page() as page:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.warning(f"TikTok goto issue (tab closed/redirect): {e}")
                
            await page.wait_for_timeout(4000)
            
            try:
                await page.evaluate('''() => {
                    const words = ['not now', 'lúc khác', 'để sau', 'không, cảm ơn', 'no thanks'];
                    document.querySelectorAll('button,span,div').forEach(el => {
                        const text = (el.innerText || '').toLowerCase().trim();
                        if (text && words.some(w => text === w)) el.click();
                    });
                }''')
                await page.wait_for_timeout(1000)
            except:
                pass
                
            try:
                dom_urls = await page.evaluate('''() => {
                    const out = [];
                    let limitY = Infinity;
                    const stopWords = [
                        'explore more', 'khám phá', 'recommend', 'similar', 'bạn có thể thích', 'you may also like',
                        'đánh giá', 'review', 'bình luận', 'đánh giá khách hàng', 'customer reviews', 'shop reviews'
                    ];
                    
                    document.querySelectorAll('div,h2,h3,p,span').forEach(el => {
                        const text = (el.innerText || '').toLowerCase().trim();
                        if (text && stopWords.some(word => text.includes(word))) {
                            const y = el.getBoundingClientRect().top + window.scrollY;
                            if (y > 300) limitY = Math.min(limitY, y);
                        }
                    });
                    
                    document.querySelectorAll('img').forEach(img => {
                        const rect = img.getBoundingClientRect();
                        const y = rect.top + window.scrollY;
                        if (y < limitY && rect.width >= 60 && rect.height >= 60) {
                            const src = img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || '';
                            if (src) out.push(src);
                        }
                    });
                    
                    document.querySelectorAll('*').forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (!style.backgroundImage || style.backgroundImage === 'none') return;
                        const rect = el.getBoundingClientRect();
                        const y = rect.top + window.scrollY;
                        if (y >= limitY || rect.width < 60 || rect.height < 60) return;
                        const match = style.backgroundImage.match(/url\(['"]?(.*?)['"]?\)/);
                        if (match && match[1]) out.push(match[1]);
                    });
                    
                    return out;
                }''')
                
                for u in dom_urls:
                    images.add(u)
            except Exception as e:
                logger.warning(f"TikTok DOM extraction failed (possibly closed tab): {e}")
                
            try:
                title_el = await page.query_selector('title')
                if title_el:
                    result['product_name'] = (await title_el.inner_text()).split('|')[0].strip()
            except:
                pass
                
            result['images'] = list(images)
            logger.info(f"TikTok data extracted: {len(result['images'])} images.")
                
        extracted_data = result

        # 2. Process extracted data
        image_urls = extracted_data.get('images', [])
        product_name = extracted_data.get('product_name', 'Unknown Product')
        shop_name = extracted_data.get('shop_name', 'Unknown Shop')
        
        if not image_urls:
            return ToolResult(is_success=False, error_message="No images found or TikTok extraction failed.")

        downloaded_files = []
        for img_url in image_urls:
            filename = await image_processor.process_and_save(img_url)
            if filename:
                file_path = os.path.join(image_processor.output_dir, filename)
                downloaded_files.append(file_path)
                
        if not downloaded_files:
            return ToolResult(is_success=False, error_message="Failed to download any images locally.")
            
        unique_files = downloaded_files
        
        logger.info("Setting up GDrive folders...")
        platform_folder_id = gdrive.get_or_create_folder("TikTok", parent_id=gdrive_folder_id)
        if not platform_folder_id:
            logger.error("Could not access or create 'TikTok' folder. Uploading to root instead.")
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
        
        upload_success_count = 0
        for file_path in unique_files:
            if gdrive.upload_file(file_path, folder_id=product_folder_id):
                upload_success_count += 1
            
        is_partial = upload_success_count < len(unique_files)
        
        if upload_success_count == 0:
             return ToolResult(is_success=False, error_message="Failed to upload any images to GDrive.")
             
        logger.info("TikTok Scrape task completed.")
        return ToolResult(
            is_success=True, 
            is_partial_success=is_partial, 
            data={"uploaded_count": upload_success_count, "total_found": len(unique_files)}
        )
