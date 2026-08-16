import pytest
import asyncio
from playwright.async_api import async_playwright
from src.product_source.platforms.shopee import _SHOPEE_EXTRACTION_SCRIPT
from src.product_source.platforms.tiktok import _TIKTOK_EXTRACTOR_JS

@pytest.mark.asyncio
async def test_shopee_dom_selection_and_ugc_exclusion():
    """
    Deterministically test that the Shopee JS extractor selects gallery images
    and excludes review/UGC images even if they share the same CDN host.
    """
    html = '''
    <html>
    <body>
        <!-- The valid product gallery -->
        <div class="product-image-carousel">
            <img src="https://cf.shopee.vn/file/gallery_image.jpg" />
        </div>
        
        <!-- Seller description -->
        <div class="product-detail">
            <img src="https://cf.shopee.vn/file/seller_image.jpg" />
        </div>
        
        <!-- Review section (UGC) - shares the SAME CDN HOST -->
        <div class="product-ratings">
            <img src="https://cf.shopee.vn/file/review_image.jpg" />
            <div class="comment">
                <img src="https://cf.shopee.vn/file/comment_image.jpg" />
            </div>
        </div>
        
        <!-- Recommendation section -->
        <div class="similar-products">
            <img src="https://cf.shopee.vn/file/recommend_image.jpg" />
        </div>
    </body>
    </html>
    '''
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)
        
        script = f"const targetProductId = '123';\n" + _SHOPEE_EXTRACTION_SCRIPT
        
        result = await page.evaluate(script)
        await browser.close()
        
        # Assertions
        assert "https://cf.shopee.vn/file/gallery_image.jpg" in result["gallery"]
        assert "https://cf.shopee.vn/file/seller_image.jpg" in result["description_media"]
        
        # Proving exclusions
        assert "https://cf.shopee.vn/file/review_image.jpg" not in result["fallback_media"]
        assert "https://cf.shopee.vn/file/comment_image.jpg" not in result["fallback_media"]
        assert "https://cf.shopee.vn/file/recommend_image.jpg" not in result["fallback_media"]
        
        all_media = result["gallery"] + result["description_media"] + result["fallback_media"]
        assert "https://cf.shopee.vn/file/review_image.jpg" not in all_media
        assert "https://cf.shopee.vn/file/comment_image.jpg" not in all_media
        assert "https://cf.shopee.vn/file/recommend_image.jpg" not in all_media

@pytest.mark.asyncio
async def test_tiktok_dom_selection_and_ugc_exclusion():
    """
    Deterministically test that the TikTok JS extractor selects gallery images
    and excludes review/UGC images even if they share the same CDN host.
    """
    html = '''
    <html>
    <body>
        <!-- The valid product gallery -->
        <div class="product-image">
            <img src="https://p16-oec-va.ibyteimg.com/gallery_image.jpg" />
        </div>
        
        <!-- Seller description -->
        <div class="seller-description">
            <img src="https://p16-oec-va.ibyteimg.com/seller_image.jpg" />
        </div>
        
        <!-- Review section (UGC) - shares the SAME CDN HOST -->
        <div class="review-item">
            <img src="https://p16-oec-va.ibyteimg.com/review_image.jpg" />
        </div>
        
        <!-- Generic outer page content -->
        <div class="generic-sidebar">
            <img src="https://p16-oec-va.ibyteimg.com/sidebar_image.jpg" />
        </div>
    </body>
    </html>
    '''
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)
        
        script = f"const targetProductId = '123';\n" + _TIKTOK_EXTRACTOR_JS
        
        result = await page.evaluate(script)
        await browser.close()
        
        # Assertions
        assert "https://p16-oec-va.ibyteimg.com/gallery_image.jpg" in result["gallery_images"]
        assert "https://p16-oec-va.ibyteimg.com/seller_image.jpg" in result["seller_images"]
        
        # Proving exclusions
        assert "https://p16-oec-va.ibyteimg.com/review_image.jpg" not in result["fallback_images"]
        assert "https://p16-oec-va.ibyteimg.com/sidebar_image.jpg" not in result["fallback_images"]
        
        all_media = result["gallery_images"] + result["seller_images"] + result["fallback_images"]
        assert "https://p16-oec-va.ibyteimg.com/review_image.jpg" not in all_media
        assert "https://p16-oec-va.ibyteimg.com/sidebar_image.jpg" not in all_media
