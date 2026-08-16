import pytest
import asyncio
from playwright.async_api import async_playwright
from src.product_source.platforms.shopee import _SHOPEE_EXTRACTION_SCRIPT
from src.product_source.platforms.tiktok import _TIKTOK_EXTRACTOR_JS

@pytest.mark.asyncio
async def test_shopee_dom_selection_and_ugc_exclusion():
    """
    Deterministically test that the Shopee JS extractor selects gallery images
    and excludes review/UGC/recommendation images even if nested directly inside
    scanned product containers and sharing the same CDN host.
    """
    html = '''
    <html>
    <body>
        <!-- Outer product container scanned by fallback/context -->
        <div class="product-briefing">
            <!-- The valid product gallery container scanned by priority 2 -->
            <div class="product-image-carousel">
                <img src="https://cf.shopee.vn/file/gallery_image.jpg" />
                
                <!-- Review/UGC subtree nested directly inside the scanned gallery container -->
                <div class="product-reviews">
                    <img src="https://cf.shopee.vn/file/nested_review_image.jpg" />
                </div>
            </div>
            
            <!-- Seller description container scanned by priority 3 -->
            <div class="product-detail">
                <img src="https://cf.shopee.vn/file/seller_image.jpg" />
                
                <!-- Comment/rating subtree nested directly inside scanned description container -->
                <div class="comment">
                    <img src="https://cf.shopee.vn/file/nested_comment_image.jpg" />
                </div>
                
                <!-- Recommendation subtree nested directly inside scanned container -->
                <div class="similar-products">
                    <img src="https://cf.shopee.vn/file/nested_recommend_image.jpg" />
                </div>
            </div>
            
            <!-- Generic review element directly in product-briefing -->
            <div class="shop-review">
                <img src="https://cf.shopee.vn/file/nested_shop_review.jpg" />
            </div>
        </div>
        
        <!-- Outside generic page sidebar -->
        <div class="shopee-header-section">
            <img src="https://cf.shopee.vn/file/header_banner.jpg" />
        </div>
    </body>
    </html>
    '''
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)
        
        # Call the extractor function with targetProductId parameter
        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123")
        await browser.close()
        
        # Assertions for accepted seller/gallery media
        assert "https://cf.shopee.vn/file/gallery_image.jpg" in result["gallery"]
        assert "https://cf.shopee.vn/file/seller_image.jpg" in result["description_media"]
        
        # Proving exclusions of nested UGC / review / recommendation elements
        all_media = result["gallery"] + result["description_media"] + result["fallback_media"]
        assert "https://cf.shopee.vn/file/nested_review_image.jpg" not in all_media
        assert "https://cf.shopee.vn/file/nested_comment_image.jpg" not in all_media
        assert "https://cf.shopee.vn/file/nested_recommend_image.jpg" not in all_media
        assert "https://cf.shopee.vn/file/nested_shop_review.jpg" not in all_media
        assert "https://cf.shopee.vn/file/header_banner.jpg" not in all_media

@pytest.mark.asyncio
async def test_tiktok_dom_selection_and_ugc_exclusion():
    """
    Deterministically test that the TikTok JS extractor selects gallery images
    and excludes review/UGC/recommendation images even if nested directly inside
    scanned product containers and sharing the same CDN host.
    """
    html = '''
    <html>
    <body>
        <!-- Outer PDP container scanned by fallback -->
        <div class="pdp-container">
            <!-- The valid product gallery container scanned by priority 2 -->
            <div class="product-image">
                <img src="https://p16-oec-va.ibyteimg.com/gallery_image.jpg" />
                
                <!-- Review subtree nested directly inside the scanned gallery container -->
                <div class="review-item">
                    <img src="https://p16-oec-va.ibyteimg.com/nested_review_image.jpg" />
                </div>
            </div>
            
            <!-- Seller description container scanned by priority 3 -->
            <div class="seller-description">
                <img src="https://p16-oec-va.ibyteimg.com/seller_image.jpg" />
                
                <!-- Comment/rating subtree nested inside scanned description container -->
                <div class="comment-box" data-testid="rating-section">
                    <img src="https://p16-oec-va.ibyteimg.com/nested_comment_image.jpg" />
                </div>
                
                <!-- Recommendation subtree nested inside scanned description container -->
                <div class="similar-products">
                    <img src="https://p16-oec-va.ibyteimg.com/nested_recommend_image.jpg" />
                </div>
            </div>
        </div>
        
        <!-- Generic outer page content outside PDP container -->
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
        
        # Call the extractor function with targetProductId parameter
        result = await page.evaluate(_TIKTOK_EXTRACTOR_JS, "123")
        await browser.close()
        
        # Assertions for accepted seller/gallery media
        assert "https://p16-oec-va.ibyteimg.com/gallery_image.jpg" in result["gallery_images"]
        assert "https://p16-oec-va.ibyteimg.com/seller_image.jpg" in result["seller_images"]
        
        # Proving exclusions of nested UGC / review / recommendation elements and outer page content
        all_media = result["gallery_images"] + result["seller_images"] + result["fallback_images"]
        assert "https://p16-oec-va.ibyteimg.com/nested_review_image.jpg" not in all_media
        assert "https://p16-oec-va.ibyteimg.com/nested_comment_image.jpg" not in all_media
        assert "https://p16-oec-va.ibyteimg.com/nested_recommend_image.jpg" not in all_media
        assert "https://p16-oec-va.ibyteimg.com/sidebar_image.jpg" not in all_media

