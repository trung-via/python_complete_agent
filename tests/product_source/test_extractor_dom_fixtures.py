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

@pytest.mark.asyncio
async def test_shopee_obfuscated_live_dom_gallery_extraction_and_footer_exclusion():
    """
    Reproduces modern live Shopee DOM shape (observed on product 52764529835)
    with JSON-LD structured seed, obfuscated classes (SECTION.C21rQm, BvNoX2/OMOWB7 main image,
    qIctnQ/mdCA_C/FAWPL0 thumbnails), proves full gallery extraction,
    and proves strict rejection of unrelated obfuscated sections with multiple same-CDN images,
    FOOTER.Dtu9HW, and review/recommendation images.
    """
    html = '''
    <html>
    <head>
        <!-- JSON-LD structured data providing positive seed identity -->
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Áo thun nam phong cách Hàn Quốc",
            "productID": "52764529835",
            "url": "https://shopee.vn/product-i.24625047.52764529835",
            "image": "https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg"
        }
        </script>
    </head>
    <body>
        <!-- Header -->
        <header class="shopee-top">
            <img src="https://down-vn.img.susercontent.com/file/header_logo.png" />
        </header>

        <!-- Top product section with modern hashed class C21rQm anchored to product -->
        <section class="C21rQm">
            <div class="media-column">
                <!-- Main product image matching structured seed -->
                <div class="BvNoX2 OMOWB7">
                    <img src="https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg" />
                </div>
                <!-- Thumbnail carousel strip -->
                <div class="qIctnQ">
                    <div class="mdCA_C FAWPL0">
                        <img src="https://down-vn.img.susercontent.com/file/vn-11134207-thumb1.jpg" />
                    </div>
                    <div class="mdCA_C FAWPL0">
                        <img src="https://down-vn.img.susercontent.com/file/vn-11134207-thumb2.jpg" />
                    </div>
                    <div class="mdCA_C FAWPL0" style="background-image: url('https://down-vn.img.susercontent.com/file/vn-11134207-thumb3.jpg')">
                    </div>
                </div>
            </div>
            <div class="details-column">
                <h1>Áo thun nam phong cách Hàn Quốc</h1>
                <div class="product-price">199.000₫</div>
            </div>
        </section>

        <!-- Middle section: Product specifications and description -->
        <div class="product-detail">
            <div class="product-description">
                <p>Mô tả chi tiết sản phẩm chính hãng</p>
                <img src="https://down-vn.img.susercontent.com/file/vn-11134207-desc-banner.jpg" />
            </div>
        </div>

        <!-- Unrelated obfuscated non-product section containing multiple same-CDN images without exclusion keywords -->
        <section class="kL89_Z mN01_X">
            <div class="pQ23_Y">
                <img src="https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-banner1.jpg" />
                <img src="https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-banner2.jpg" />
                <div style="background-image: url('https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-thumb.jpg')"></div>
            </div>
        </section>

        <!-- Review section with same-CDN images (UGC) -->
        <div class="product-ratings">
            <div class="shopee-product-rating">
                <img src="https://down-vn.img.susercontent.com/file/vn-11134207-customer-review.jpg" />
            </div>
        </div>

        <!-- Recommendations section -->
        <div class="similar-products">
            <img src="https://down-vn.img.susercontent.com/file/vn-11134207-recommended-other.jpg" />
        </div>

        <!-- Footer with modern hashed class Dtu9HW -->
        <footer class="Dtu9HW">
            <img src="https://down-vn.img.susercontent.com/file/footer_payment_badge.png" />
            <img src="https://down-vn.img.susercontent.com/file/footer_cert_badge.png" />
        </footer>
    </body>
    </html>
    '''

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "52764529835")
        await browser.close()

        # 1. Proves all seller gallery images (main + thumbnails including background-image) are extracted
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb1.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb2.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb3.jpg" in result["gallery"]
        assert len(result["gallery"]) >= 4

        # 2. Proves seller description image is captured
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-desc-banner.jpg" in result["description_media"]

        # 3. Proves unrelated obfuscated section images (kL89_Z) are strictly rejected (not in gallery or anywhere)
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-banner1.jpg" not in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-banner2.jpg" not in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-thumb.jpg" not in result["gallery"]

        # 4. Proves review, recommendation, header, footer, and unrelated images are absent from all extracted media
        all_media = result["gallery"] + result["description_media"] + result["fallback_media"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-banner1.jpg" not in all_media
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-banner2.jpg" not in all_media
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-unrelated-thumb.jpg" not in all_media
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-customer-review.jpg" not in all_media
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-recommended-other.jpg" not in all_media
        assert "https://down-vn.img.susercontent.com/file/header_logo.png" not in all_media
        assert "https://down-vn.img.susercontent.com/file/footer_payment_badge.png" not in all_media
        assert "https://down-vn.img.susercontent.com/file/footer_cert_badge.png" not in all_media


@pytest.mark.asyncio
async def test_shopee_image_seed_anchor_independently_extracts_gallery_without_title_anchor():
    """
    Proves that when structured data contains an identity-verified product image seed
    but NO matching DOM title anchor exists, the image seed node itself anchors the
    gallery cluster in the DOM and extracts seller thumbnails while excluding unrelated sections.
    """
    html = '''
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Different Unmatched Title In JSON-LD",
            "productID": "52764529835",
            "url": "https://shopee.vn/product-i.24625047.52764529835",
            "image": "https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg"
        }
        </script>
    </head>
    <body>
        <!-- Product Section with obfuscated classes and non-matching DOM title -->
        <section class="C21rQm">
            <div class="media-column">
                <div class="BvNoX2 OMOWB7">
                    <!-- Root img node matching structured image seed -->
                    <img src="https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg" />
                </div>
                <div class="qIctnQ">
                    <div class="mdCA_C FAWPL0">
                        <img src="https://down-vn.img.susercontent.com/file/vn-11134207-thumb1.jpg" />
                    </div>
                    <div class="mdCA_C FAWPL0">
                        <img src="https://down-vn.img.susercontent.com/file/vn-11134207-thumb2.jpg" />
                    </div>
                </div>
            </div>
            <div class="details-column">
                <h1>Some Random Non Matching Heading</h1>
            </div>
        </section>

        <!-- Unrelated obfuscated section with multiple same-CDN images -->
        <section class="kL89_Z">
            <div>
                <img src="https://down-vn.img.susercontent.com/file/vn-11134207-unrelated1.jpg" />
                <img src="https://down-vn.img.susercontent.com/file/vn-11134207-unrelated2.jpg" />
            </div>
        </section>
    </body>
    </html>
    '''

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "52764529835")
        await browser.close()

        # Proves gallery is anchored by image seed alone
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb1.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb2.jpg" in result["gallery"]

        # Proves unrelated section is not captured
        all_media = result["gallery"] + result["description_media"] + result["fallback_media"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-unrelated1.jpg" not in all_media
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-unrelated2.jpg" not in all_media


@pytest.mark.asyncio
async def test_shopee_no_structured_images_and_no_semantic_gallery_fails_closed_without_fallback():
    """
    Proves that when there are no structured images, no semantic gallery,
    and no positive briefing container, generic page sections containing multiple
    images are NOT accepted as fallback media (Priority 4 fails closed).
    """
    html = '''
    <html>
    <body>
        <header>
            <img src="https://down-vn.img.susercontent.com/file/logo.png" />
        </header>

        <!-- Generic unrelated sections on the page -->
        <section class="unrelated-promo-box">
            <img src="https://down-vn.img.susercontent.com/file/promo1.jpg" />
            <img src="https://down-vn.img.susercontent.com/file/promo2.jpg" />
            <img src="https://down-vn.img.susercontent.com/file/promo3.jpg" />
        </section>

        <section class="shop-campaign-banner">
            <img src="https://down-vn.img.susercontent.com/file/campaign1.jpg" />
            <img src="https://down-vn.img.susercontent.com/file/campaign2.jpg" />
        </section>

        <footer>
            <img src="https://down-vn.img.susercontent.com/file/footer.png" />
        </footer>
    </body>
    </html>
    '''

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "52764529835")
        await browser.close()

        # Proves no media accepted (fails closed)
        assert len(result["structured"]["images"]) == 0
        assert len(result["gallery"]) == 0
        assert len(result["description_media"]) == 0
        assert len(result["fallback_media"]) == 0
        all_media = result["gallery"] + result["description_media"] + result["fallback_media"]
        assert len(all_media) == 0




