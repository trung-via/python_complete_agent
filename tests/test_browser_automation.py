import pytest
import asyncio
from src.modules.browser_automation import BrowserAutomation

@pytest.mark.asyncio
async def test_browser_start_stop():
    browser = BrowserAutomation(headless=True)
    await browser.start()
    assert browser.playwright is not None
    assert browser.browser is not None
    assert browser.context is not None
    await browser.stop()

@pytest.mark.asyncio
async def test_extract_tiktok_mock():
    # Since navigating to real sites in CI can be flaky, we test the basic flow.
    # A more robust test would use a local mock HTML file.
    browser = BrowserAutomation(headless=True)
    await browser.start()
    
    # We just test that the method doesn't crash on a basic URL.
    res = await browser.extract_video_from_tiktok("https://example.com")
    
    assert isinstance(res, dict)
    await browser.stop()
