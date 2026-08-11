import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://shopee.vn/-MUA-570G-T%E1%BA%B6NG-350G-S%E1%BB%AFa-t%E1%BA%AFm-Lux-Botanicals-H%C6%B0%C6%A1ng-N%C6%B0%E1%BB%9Bc-Hoa-Cao-C%E1%BA%A5p-570G-T%E1%BA%B7ng-S%E1%BB%AFa-T%E1%BA%AFm-Lux-Botanicals-350G-i.111138057.41809495164')
        await page.wait_for_timeout(3000)
        
        # Search window for anything containing images
        images = await page.evaluate('''() => {
            let matches = [];
            // Try to find image hashes in scripts
            let scripts = Array.from(document.scripts);
            for (let s of scripts) {
                if (s.innerText.includes('images')) {
                    // Look for array of strings that look like image hashes (32 chars)
                    let regex = /"images"\s*:\s*\[([^\]]+)\]/g;
                    let m;
                    while ((m = regex.exec(s.innerText)) !== null) {
                        matches.push(m[1]);
                    }
                }
            }
            return matches;
        }''')
        
        print('Images found:', images)
        await browser.close()

asyncio.run(main())
