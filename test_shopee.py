import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://shopee.vn/-MUA-570G-T%E1%BA%B6NG-350G-S%E1%BB%AFa-t%E1%BA%AFm-Lux-Botanicals-H%C6%B0%C6%A1ng-N%C6%B0%E1%BB%9Bc-Hoa-Cao-C%E1%BA%A5p-570G-T%E1%BA%B7ng-S%E1%BB%AFa-T%E1%BA%AFm-Lux-Botanicals-350G-i.111138057.41809495164')
        await page.wait_for_timeout(5000)
        
        # Click main image
        try:
            main_image = await page.query_selector('.page-product__briefing, .product-briefing, [role="main"]')
            if main_image:
                await main_image.click()
                await page.wait_for_timeout(2000)
        except Exception as e:
            print("Click error:", e)
        
        # Get all images
        images = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('img')).map(img => {
                let rect = img.getBoundingClientRect();
                return {
                    src: img.src,
                    width: rect.width,
                    height: rect.height,
                    className: img.className,
                    parentClass: img.parentElement ? img.parentElement.className : ''
                }
            })
        }''')
        
        for img in images:
            if img['width'] > 0 and 'susercontent.com' in img['src']:
                print(f"IMG: {img['width']}x{img['height']} PARENT: {img['parentClass']} URL: {img['src']}")
                
        await browser.close()

asyncio.run(main())
