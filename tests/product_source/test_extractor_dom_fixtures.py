import pytest
import asyncio
from playwright.async_api import async_playwright
from src.product_source.platforms.shopee import ShopeeSourceExtractor, _SHOPEE_EXTRACTION_SCRIPT
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


@pytest.mark.asyncio
async def test_shopee_near_seed_ancestor_with_two_images_expands_to_full_sibling_thumbnail_strip():
    """
    Proves that when a near seed ancestor contains 2 images (main product view + non-product overlay badge),
    expansion does not terminate prematurely at 2 images, but expands upward to the enclosing
    product-media cluster to capture all sibling thumbnail strip product images (5 actual product views total),
    while explicitly excluding the standalone overlay/badge image and unrelated non-product sections.
    """
    html = '''
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Camera TC70 WiFi",
            "productID": "52764529835",
            "url": "https://shopee.vn/product-i.24625047.52764529835",
            "image": "https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg"
        }
        </script>
    </head>
    <body>
        <section class="C21rQm">
            <div class="media-column-container">
                <!-- Near seed ancestor containing main image wrapped in picture + sibling overlay badge -->
                <div class="BvNoX2 OMOWB7">
                    <picture>
                        <img src="https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg" />
                    </picture>
                    <img class="overlay-badge" src="https://down-vn.img.susercontent.com/file/vn-11134258-overlay-badge.png" />
                </div>
                <!-- Sibling thumbnail strip with 4 more seller images under common media-column-container -->
                <div class="qIctnQ">
                    <div class="mdCA_C">
                        <picture><img src="https://down-vn.img.susercontent.com/file/vn-11134207-thumb1.jpg" /></picture>
                        <img class="overlay-badge" src="https://down-vn.img.susercontent.com/file/vn-11134258-overlay-badge.png" />
                    </div>
                    <div class="mdCA_C">
                        <picture><img src="https://down-vn.img.susercontent.com/file/vn-11134207-thumb2.jpg" /></picture>
                    </div>
                    <div class="mdCA_C">
                        <picture><img src="https://down-vn.img.susercontent.com/file/vn-11134207-thumb3.jpg" /></picture>
                    </div>
                    <div class="mdCA_C">
                        <picture><img src="https://down-vn.img.susercontent.com/file/vn-11134207-thumb4.jpg" /></picture>
                    </div>
                </div>
            </div>
            <div class="details-column">
                <h1>Camera TC70 WiFi</h1>
            </div>
        </section>

        <!-- Unrelated section with same-CDN images -->
        <section class="unrelated-campaign">
            <div>
                <img src="https://down-vn.img.susercontent.com/file/unrelated1.jpg" />
                <img src="https://down-vn.img.susercontent.com/file/unrelated2.jpg" />
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

        # 1. Proves all 5 authentic seller product gallery media (main + 4 thumbnails) are captured
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-main.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb1.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb2.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb3.jpg" in result["gallery"]
        assert "https://down-vn.img.susercontent.com/file/vn-11134207-thumb4.jpg" in result["gallery"]
        assert len(result["gallery"]) == 5

        # 2. Proves non-product overlay badge is REJECTED
        assert "https://down-vn.img.susercontent.com/file/vn-11134258-overlay-badge.png" not in result["gallery"]

        # 3. Proves unrelated section is strictly rejected
        all_media = result["gallery"] + result["description_media"] + result["fallback_media"]
        assert "https://down-vn.img.susercontent.com/file/unrelated1.jpg" not in all_media
        assert "https://down-vn.img.susercontent.com/file/unrelated2.jpg" not in all_media


@pytest.mark.asyncio
async def test_tiktok_dom_global_captcha_scripts_do_not_block_normal_product():
    """
    Proves that a normal TikTok product page loading background/global captcha loader scripts
    (e.g. lucifer-captcha-loader-js) is NOT falsely flagged as blocked.
    """
    html = '''
    <html>
    <head>
        <title>[TẶNG LỌC 1.250K] Máy Lọc Không Khí UVGREEN KA600 - TikTok Shop</title>
        <!-- Global captcha loader script loaded on normal pages -->
        <script id="lucifer-captcha-loader-js" src="https://sf16-website-login.neutral.ttwstatic.com/obj/tiktok_web_login_static/oec-ttweb-captcha/loader/sg/1.0.0.58/captcha/index.js"></script>
    </head>
    <body>
        <h1>[TẶNG LỌC 1.250K] Máy Lọc Không Khí UVGREEN KA600</h1>
        <div class="slick-slider">
            <div class="slick-track">
                <img src="https://p16-oec-sg.ibyteimg.com/gal1.webp" />
                <img src="https://p16-oec-sg.ibyteimg.com/gal2.webp" />
            </div>
        </div>
        <div class="reviews-section">
            <img src="https://p16-oec-sg.ibyteimg.com/review_ugc.webp" />
        </div>
    </body>
    </html>
    '''

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_TIKTOK_EXTRACTOR_JS, "1729981094029264939")
        await browser.close()

        # 1. Proves page is NOT marked blocked
        assert result["blocked"] is False

        # 2. Proves gallery images are extracted
        assert "https://p16-oec-sg.ibyteimg.com/gal1.webp" in result["gallery_images"]
        assert "https://p16-oec-sg.ibyteimg.com/gal2.webp" in result["gallery_images"]

        # 3. Proves review UGC is excluded
        assert "https://p16-oec-sg.ibyteimg.com/review_ugc.webp" not in result["gallery_images"]


@pytest.mark.asyncio
async def test_tiktok_dom_active_challenge_blocks_extraction():
    """
    Proves that an active captcha challenge modal/dialog causes extraction to fail closed with blocked=True.
    """
    html = '''
    <html>
    <head>
        <title>Security Check</title>
    </head>
    <body>
        <div id="captcha_container" style="display: block;">
            <div class="captcha_verify_container" style="visibility: visible;">
                <div class="captcha_verify_bar">Please verify</div>
                <div class="secsdk-captcha-drag-icon"></div>
            </div>
        </div>
    </body>
    </html>
    '''

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_TIKTOK_EXTRACTOR_JS, "1729981094029264939")
        await browser.close()

        # Proves active challenge triggers blocked=True
        assert result["blocked"] is True


@pytest.mark.asyncio
async def test_shopee_dom_multi_group_selection_deterministic_order():
    """
    Proves that fully explicit multi-group selection inside positive current-product
    scope is emitted in deterministic canonical DOM first-appearance order, with exact
    observed group and selected option strings.
    """
    html = '''
    <html>
    <body>
        <div class="product-briefing">
            <div class="product-variation-group">
                <div class="group-label">Màu sắc</div>
                <div class="items">
                    <button class="product-variation product-variation--selected">Đen</button>
                    <button class="product-variation">Trắng</button>
                </div>
            </div>
            <div class="product-variation-group">
                <label class="group-label">Kích thước</label>
                <div class="items">
                    <button class="product-variation" aria-selected="false">M</button>
                    <button class="product-variation" aria-selected="true">XL</button>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123")
        await browser.close()

        assert result["selected_variants_complete"] is True
        assert len(result["selected_variants"]) == 2
        assert result["selected_variants"][0] == {"group_label": "Màu sắc", "option_label": "Đen"}
        assert result["selected_variants"][1] == {"group_label": "Kích thước", "option_label": "XL"}


@pytest.mark.asyncio
async def test_shopee_dom_incomplete_group_selection_rejected_as_a_whole():
    """
    Proves all-or-nothing variation evidence: when one group is selected but another
    group has zero selected options, the entire variation evidence is rejected.
    """
    html = '''
    <html>
    <body>
        <div class="product-briefing">
            <!-- Group 1 has 1 selected option -->
            <div class="product-variation-group">
                <div class="group-label">Màu sắc</div>
                <button class="product-variation product-variation--selected">Đen</button>
                <button class="product-variation">Trắng</button>
            </div>
            <!-- Group 2 has 0 selected options -->
            <div class="product-variation-group">
                <div class="group-label">Kích thước</div>
                <button class="product-variation">M</button>
                <button class="product-variation">XL</button>
            </div>
        </div>
    </body>
    </html>
    '''
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123")
        await browser.close()

        assert result["selected_variants_complete"] is False
        assert result["selected_variants"] == []


@pytest.mark.asyncio
async def test_shopee_dom_ambiguous_group_selection_rejected_as_a_whole():
    """
    Proves that ambiguous group selections (multiple selected options in one group,
    duplicate group labels, or blank labels) are rejected as a whole.
    """
    # Case A: Multiple selected options in one group
    html_multi = '''
    <html>
    <body>
        <div class="product-briefing">
            <div class="product-variation-group">
                <div class="group-label">Màu sắc</div>
                <button class="product-variation product-variation--selected">Đen</button>
                <button class="product-variation product-variation--selected">Trắng</button>
            </div>
        </div>
    </body>
    </html>
    '''
    # Case B: Duplicate group identity
    html_duplicate = '''
    <html>
    <body>
        <div class="product-briefing">
            <div class="product-variation-group">
                <div class="group-label">Màu sắc</div>
                <button class="product-variation product-variation--selected">Đen</button>
            </div>
            <div class="product-variation-group">
                <div class="group-label">Màu sắc</div>
                <button class="product-variation product-variation--selected">Trắng</button>
            </div>
        </div>
    </body>
    </html>
    '''
    # Case C: Blank group label
    html_blank_label = '''
    <html>
    <body>
        <div class="product-briefing">
            <div class="product-variation-group">
                <div class="group-label">   </div>
                <button class="product-variation product-variation--selected">Đen</button>
            </div>
        </div>
    </body>
    </html>
    '''

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.set_content(html_multi)
        result_multi = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123")
        assert result_multi["selected_variants_complete"] is False
        assert result_multi["selected_variants"] == []

        await page.set_content(html_duplicate)
        result_duplicate = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123")
        assert result_duplicate["selected_variants_complete"] is False
        assert result_duplicate["selected_variants"] == []

        await page.set_content(html_blank_label)
        result_blank = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123")
        assert result_blank["selected_variants_complete"] is False
        assert result_blank["selected_variants"] == []

        await browser.close()


@pytest.mark.asyncio
async def test_shopee_dom_selected_controls_outside_positive_scope_ignored():
    """
    Proves that selected variation controls placed in reviews, recommendations,
    headers, footers, or outside the briefing container are strictly ignored.
    """
    html = '''
    <html>
    <body>
        <header>
            <button class="product-variation product-variation--selected">Header Selected</button>
        </header>

        <!-- Product briefing with NO selected variation controls -->
        <div class="product-briefing">
            <div class="product-image-carousel">
                <img src="https://cf.shopee.vn/file/gallery.jpg" />
            </div>
        </div>

        <!-- Out-of-scope review section with selected buttons -->
        <div class="product-reviews">
            <div class="product-variation-group">
                <div class="group-label">Review Variant</div>
                <button class="product-variation product-variation--selected">Review Black</button>
            </div>
        </div>

        <!-- Out-of-scope recommendations with selected buttons -->
        <div class="similar-products">
            <button class="product-variation product-variation--selected">Similar Blue</button>
        </div>

        <footer>
            <button class="product-variation product-variation--selected">Footer Selected</button>
        </footer>
    </body>
    </html>
    '''
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123")
        await browser.close()

        assert result["selected_variants_complete"] is False
        assert result["selected_variants"] == []
        assert "https://cf.shopee.vn/file/gallery.jpg" in result["gallery"]


@pytest.mark.asyncio
async def test_shopee_dom_preserves_variant_media_and_review_exclusions():
    """
    Proves that the listing option catalogue media (SEMANTIC_VARIANT_MEDIA) is extracted
    in full, selected controls are observed, and review UGC is strictly excluded.
    """
    html = '''
    <html>
    <body>
        <div class="product-briefing">
            <div class="product-image-carousel">
                <img src="https://cf.shopee.vn/file/main.jpg" />
            </div>

            <!-- Variation controls with media and selection -->
            <div class="product-variation-group">
                <div class="group-label">Màu sắc</div>
                <div class="product-variation product-variation--selected">
                    <img src="https://cf.shopee.vn/file/black_option.jpg" />
                    <span>Đen</span>
                </div>
                <div class="product-variation">
                    <img src="https://cf.shopee.vn/file/white_option.jpg" />
                    <span>Trắng</span>
                </div>
            </div>

            <!-- Review nested in briefing -->
            <div class="product-ratings">
                <img src="https://cf.shopee.vn/file/review_ugc.jpg" />
                <button class="product-variation product-variation--selected">UGC</button>
            </div>
        </div>
    </body>
    </html>
    '''
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123")
        await browser.close()

        # Selected variant observed accurately
        assert result["selected_variants_complete"] is True
        assert result["selected_variants"] == [{"group_label": "Màu sắc", "option_label": "Đen"}]

        # Both option media in catalogue are extracted
        variant_urls = [v["url"] for v in result["variants"]]
        assert "https://cf.shopee.vn/file/black_option.jpg" in variant_urls
        assert "https://cf.shopee.vn/file/white_option.jpg" in variant_urls

        # Review UGC excluded
        all_media = result["gallery"] + [v["url"] for v in result["variants"]] + result["description_media"] + result["fallback_media"]
        assert "https://cf.shopee.vn/file/review_ugc.jpg" not in all_media


@pytest.mark.asyncio
async def test_shopee_dom_and_source_pack_selected_variants_preserves_exact_whitespace():
    """
    Proves that the Shopee DOM extractor and ProductSourcePack preserve exact raw observed
    group and option strings byte-for-byte in selected_variants and in resulting ProductFact values,
    including both attribute-backed and rendered-text labels with leading and trailing whitespace.
    """
    html = '''
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Whitespace Product",
            "productID": "123456",
            "url": "https://shopee.vn/product-i.100.123456",
            "image": "https://cf.shopee.vn/file/main.jpg"
        }
        </script>
    </head>
    <body>
        <div class="product-briefing">
            <!-- Group 1: Attribute-backed group label and option label with leading/trailing whitespace -->
            <div class="product-variation-group" aria-label="  Attribute Group  ">
                <div class="items">
                    <button class="product-variation product-variation--selected" aria-label="  Attribute Option  ">
                        Button Option 1
                    </button>
                    <button class="product-variation">Button Option 2</button>
                </div>
            </div>

            <!-- Group 2: Rendered-text group label and option label with leading/trailing whitespace -->
            <div class="product-variation-group">
                <label class="group-label">  Rendered Group  </label>
                <div class="items">
                    <button class="product-variation" aria-selected="false">Rendered Opt 1</button>
                    <button class="product-variation" aria-selected="true">  Rendered Option  </button>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)

        # 1. Verify DOM extraction preserves exact whitespace text-for-text
        result = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123456")
        assert result["selected_variants_complete"] is True
        assert len(result["selected_variants"]) == 2
        assert result["selected_variants"][0] == {
            "group_label": "  Attribute Group  ",
            "option_label": "  Attribute Option  ",
        }
        assert result["selected_variants"][1] == {
            "group_label": "  Rendered Group  ",
            "option_label": "  Rendered Option  ",
        }

        # 2. Verify ProductSourcePack extraction embeds exact whitespace in ProductFact values
        from unittest.mock import AsyncMock
        page.goto = AsyncMock()
        extractor = ShopeeSourceExtractor(browser=page)
        pack = await extractor.extract("https://shopee.vn/product/100/123456")
        variant_facts = [f for f in pack.facts if f.key == "variant"]
        assert len(variant_facts) == 2
        assert variant_facts[0].value == "  Attribute Group  :   Attribute Option  "
        assert variant_facts[0].source_section == "selected_variant_controls"
        assert variant_facts[1].value == "  Rendered Group  :   Rendered Option  "
        assert variant_facts[1].source_section == "selected_variant_controls"

        await browser.close()


@pytest.mark.asyncio
async def test_shopee_dom_and_source_pack_blank_only_labels_fail_closed():
    """
    Proves that blank-only group or option labels (both attribute-backed and rendered-text)
    fail closed: selected_variants is empty, selected_variants_complete is False, and
    zero variant facts are emitted in the ProductSourcePack.
    """
    # Case 1: Attribute-backed group label is whitespace-only
    html_blank_attr_group = '''
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Blank Attr Group",
            "productID": "123456",
            "url": "https://shopee.vn/product-i.100.123456",
            "image": "https://cf.shopee.vn/file/main.jpg"
        }
        </script>
    </head>
    <body>
        <div class="product-briefing">
            <div class="product-variation-group" aria-label="   ">
                <button class="product-variation product-variation--selected">Valid Option</button>
            </div>
        </div>
    </body>
    </html>
    '''

    # Case 2: Attribute-backed option label is whitespace-only
    html_blank_attr_option = '''
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Blank Attr Option",
            "productID": "123456",
            "url": "https://shopee.vn/product-i.100.123456",
            "image": "https://cf.shopee.vn/file/main.jpg"
        }
        </script>
    </head>
    <body>
        <div class="product-briefing">
            <div class="product-variation-group" aria-label="Valid Group">
                <button class="product-variation product-variation--selected" aria-label="   ">   </button>
            </div>
        </div>
    </body>
    </html>
    '''

    # Case 3: Rendered-text option label is whitespace-only
    html_blank_rendered_option = '''
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Blank Rendered Option",
            "productID": "123456",
            "url": "https://shopee.vn/product-i.100.123456",
            "image": "https://cf.shopee.vn/file/main.jpg"
        }
        </script>
    </head>
    <body>
        <div class="product-briefing">
            <div class="product-variation-group">
                <div class="group-label">Valid Group</div>
                <button class="product-variation product-variation--selected">   </button>
            </div>
        </div>
    </body>
    </html>
    '''

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        from unittest.mock import AsyncMock
        page.goto = AsyncMock()

        for case_html in [html_blank_attr_group, html_blank_attr_option, html_blank_rendered_option]:
            await page.set_content(case_html)
            res = await page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123456")
            assert res["selected_variants_complete"] is False
            assert res["selected_variants"] == []

            extractor = ShopeeSourceExtractor(browser=page)
            pack = await extractor.extract("https://shopee.vn/product/100/123456")
            variant_facts = [f for f in pack.facts if f.key == "variant"]
            assert len(variant_facts) == 0

        await browser.close()


