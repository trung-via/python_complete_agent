import pytest
import os
from pathlib import Path

from src.browser.models import BrowserConfig, LocatorSpec
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.core.types import ToolCall
from src.tools.browser.navigate import NavigateTool, NavigateArgs
from src.tools.browser.inspect import InspectTool, InspectArgs
from src.tools.browser.type_text import TypeTextTool, TypeTextArgs
from src.tools.browser.click import ClickTool, ClickArgs
from src.tools.browser.screenshot import ScreenshotTool, ScreenshotArgs

@pytest.fixture
def local_fixture_url():
    fixture_path = Path(os.getcwd()) / "tests" / "fixtures" / "browser" / "index.html"
    # Ensure URL format
    return f"file:///{fixture_path.absolute().as_posix()}"

@pytest.mark.asyncio
async def test_browser_tools_end_to_end(local_fixture_url):
    browser_manager = PlaywrightBrowserManager()
    run_id = "test_run_123"
    
    try:
        # 1. Navigate
        nav_tool = NavigateTool(browser_manager)
        nav_call = ToolCall(name="browser.navigate", arguments={"url": local_fixture_url}, call_id="c1", run_id=run_id)
        res_nav = await nav_tool.execute(nav_call, {})
        assert res_nav.status.value == "success"
        
        # 2. Inspect
        inspect_tool = InspectTool(browser_manager)
        insp_call = ToolCall(name="browser.inspect", arguments={}, call_id="c2", run_id=run_id)
        res_insp = await inspect_tool.execute(insp_call, {})
        assert res_insp.status.value == "success"
        
        data = res_insp.data
        assert data["title"] == "Test Local Fixture"
        
        elements = data["elements"]
        
        # Find input and button
        input_el = next((e for e in elements if e["role"] == "input"), None)
        button_el = next((e for e in elements if e["role"] == "button" and e["name"] == "Submit Data"), None)
        
        assert input_el is not None
        assert button_el is not None
        
        # 3. Type text
        type_tool = TypeTextTool(browser_manager)
        type_call = ToolCall(name="browser.type", arguments={
            "text": "testuser",
            "element_id": input_el["id"]
        }, call_id="c3", run_id=run_id)
        res_type = await type_tool.execute(type_call, {})
        assert res_type.status.value == "success"
        
        # 4. Click Submit
        click_tool = ClickTool(browser_manager)
        click_call = ToolCall(name="browser.click", arguments={
            "element_id": button_el["id"]
        }, call_id="c4", run_id=run_id)
        res_click = await click_tool.execute(click_call, {})
        assert res_click.status.value == "success"
        
        # Wait for JS to run and evaluate success
        session = await browser_manager.get_or_create_session(run_id)
        is_visible = await session._page.locator("#output").is_visible()
        assert is_visible is True
        
        # 5. Screenshot
        shot_tool = ScreenshotTool(browser_manager)
        shot_call = ToolCall(name="browser.screenshot", arguments={}, call_id="c5", run_id=run_id)
        res_shot = await shot_tool.execute(shot_call, {})
        assert res_shot.status.value == "success"
        assert "artifact_id" in res_shot.data
        
        assert os.path.exists(res_shot.data["path"])
    finally:
        await browser_manager.close_all()
