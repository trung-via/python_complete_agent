import asyncio
from playwright.async_api import async_playwright
import re

async def main():
    url = 'https://shopee.vn/-MUA-570G-T%E1%BA%B6NG-350G-S%E1%BB%AFa-t%E1%BA%AFm-Lux-Botanicals-H%C6%B0%C6%A1ng-N%C6%B0%E1%BB%9Bc-Hoa-Cao-C%E1%BA%A5p-570G-T%E1%BA%B7ng-S%E1%BB%AFa-T%E1%BA%AFm-Lux-Botanicals-350G-i.111138057.41809495164'
    
    # Extract itemid and shopid
    match = re.search(r'-i\.(\d+)\.(\d+)', url)
    if not match:
        print("No match")
        return
        
    shopid, itemid = match.groups()
    print(f"ShopID: {shopid}, ItemID: {itemid}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(3000)
        
        # Try to fetch from API
        api_url = f"/api/v4/item/get?itemid={itemid}&shopid={shopid}"
        print(f"Fetching API: {api_url}")
        
        try:
            data = await page.evaluate(f'''async () => {{
                let res = await fetch("{api_url}");
                let json = await res.json();
                return json;
            }}''')
            
            if data and 'data' in data and data['data'] and 'images' in data['data']:
                images = data['data']['images']
                print(f"FOUND {len(images)} IMAGES VIA API!")
                for img in images:
                    print(f"https://down-vn.img.susercontent.com/file/{img}")
            else:
                print("API returned no images:", data)
                
        except Exception as e:
            print("API fetch failed:", e)
            
        await browser.close()

asyncio.run(main())
