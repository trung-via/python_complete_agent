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


