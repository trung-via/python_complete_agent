import logging
import asyncio
import uuid
from typing import Optional, Dict, Any, List

from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from src.browser.session import BrowserSession
from src.browser.models import BrowserState, BrowserConfig, LocatorSpec, BrowserElement
from src.browser.errors import (
    BrowserNotStartedError,
    NavigationError,
    NavigationTimeoutError,
    ElementNotFoundError,
    ElementNotVisibleError,
    ElementInteractionError,
    PageClosedError,
    BrowserContextError
)

logger = logging.getLogger(__name__)

class PlaywrightBrowserSession(BrowserSession):
    CDP_CONNECTION_TIMEOUT_MS = 30_000

    def __init__(self, run_id: str, config: BrowserConfig, cdp_endpoint: Optional[str] = None):
        self._run_id = run_id
        self._config = config
        self._cdp_endpoint = cdp_endpoint
        self._owns_browser_resources = cdp_endpoint is None
        self._listeners = []
        self._state = BrowserState.UNINITIALIZED
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # Element cache: run_id/page_id/element_index -> locator representation
        self._page_generation: str = str(uuid.uuid4())
        self._element_cache: Dict[str, LocatorSpec] = {}
        self._element_counter = 0

    @property
    def state(self) -> BrowserState:
        # Also check synchronously when a manager consults its cache, in case the
        # disconnect event has not yet been dispatched.
        if (self._cdp_endpoint is not None
                and self._state in (BrowserState.READY, BrowserState.BUSY)
                and self._browser is not None and not self._browser.is_connected()):
            self._on_disconnected()
        return self._state

    @property
    def run_id(self) -> str:
        return self._run_id

    async def start(self) -> None:
        if self._state not in (BrowserState.UNINITIALIZED, BrowserState.CLOSED, BrowserState.CRASHED):
            logger.warning(f"Session {self._run_id} is already starting or ready.")
            return

        self._state = BrowserState.STARTING
        try:
            if self._cdp_endpoint is not None and self._config.browser_type != "chromium":
                raise BrowserContextError("CDP attachment requires browser_type='chromium'.")
            self._playwright = await async_playwright().start()

            if self._cdp_endpoint is not None:
                self._browser = await self._playwright.chromium.connect_over_cdp(
                    self._cdp_endpoint, timeout=self.CDP_CONNECTION_TIMEOUT_MS
                )
                self._listen(self._browser, "disconnected", self._on_disconnected)
                if not self._browser.contexts:
                    raise BrowserContextError("CDP browser has no existing context; open a Chrome tab before retrying.")
                self._context = self._browser.contexts[0]
                self._page = next((page for page in self._context.pages if not page.is_closed()), None)
                if self._page is None:
                    raise BrowserContextError("CDP first context has no open page; open a Chrome tab before retrying.")
            else:
                browser_type = getattr(self._playwright, self._config.browser_type)
                launch_args = {"headless": self._config.headless}
                if self._config.executable_path:
                    launch_args["executable_path"] = self._config.executable_path
                self._browser = await browser_type.launch(**launch_args)
                context_args = {
                    "viewport": {"width": self._config.viewport_width, "height": self._config.viewport_height}
                }
                if self._config.user_agent:
                    context_args["user_agent"] = self._config.user_agent
                self._context = await self._browser.new_context(**context_args)
                self._page = await self._context.new_page()

            self._listen(self._page, "crash", self._on_crash)
            if self._cdp_endpoint is not None:
                if not self._browser.is_connected() or self._state == BrowserState.CRASHED:
                    raise BrowserContextError("CDP browser disconnected during attachment.")
                if self._page.is_closed():
                    raise BrowserContextError("CDP page closed during attachment.")
            
            self._state = BrowserState.READY
            logger.info(f"Playwright session started for run {self._run_id}.")
        except asyncio.CancelledError:
            await self._release_resources()
            self._state = BrowserState.CRASHED
            raise
        except Exception as e:
            await self._release_resources()
            self._state = BrowserState.CRASHED
            if self._cdp_endpoint is not None:
                raise BrowserContextError(
                    f"Failed to attach Playwright to CDP {self._cdp_endpoint}: {e}. "
                    "Ensure the operator-managed Chrome endpoint and an existing tab are available; "
                    "no browser was launched."
                ) from e
            raise BrowserContextError(f"Failed to start Playwright: {e}") from e

    def _listen(self, emitter, event, callback):
        self._listeners.append((emitter, event, callback))
        emitter.on(event, callback)

    def _on_disconnected(self, *args):
        if self._state not in (BrowserState.CLOSING, BrowserState.CLOSED):
            self._state = BrowserState.CRASHED

    def _on_crash(self, page: Page):
        logger.error(f"Page crashed in session {self._run_id}")
        self._state = BrowserState.CRASHED

    def _check_ready(self):
        if self.state == BrowserState.CRASHED:
            raise BrowserContextError("Browser session has crashed.")
        if self._state != BrowserState.READY and self._state != BrowserState.BUSY:
            raise BrowserNotStartedError()
        if not self._page or self._page.is_closed():
            raise PageClosedError()

    async def _release_resources(self) -> None:
        for emitter, event, callback in self._listeners:
            try:
                emitter.remove_listener(event, callback)
            except Exception as e:
                logger.warning(f"Error removing Playwright session listener: {e}")
        self._listeners.clear()

        # Each session owns its Playwright connection. CDP browser/context/page
        # are borrowed; stopping the connection must not close those resources.
        cleanup = []
        if self._owns_browser_resources:
            if self._context is not None:
                cleanup.append(self._context.close)
            if self._browser is not None:
                cleanup.append(self._browser.close)
        if self._playwright is not None:
            cleanup.append(self._playwright.stop)
        for release in cleanup:
            try:
                await release()
            except Exception as e:
                # Continue releasing other owned resources, including after a
                # partial start; cleanup must not replace the original error.
                logger.warning(f"Error while releasing Playwright resource: {e}")
        self._context = None
        self._browser = None
        self._playwright = None
        self._page = None
        self._element_cache.clear()

    async def close(self) -> None:
        if self._state == BrowserState.CLOSED:
            return
        self._state = BrowserState.CLOSING
        await self._release_resources()
        self._state = BrowserState.CLOSED
        logger.info(f"Playwright session closed for run {self._run_id}.")

    async def navigate(self, url: str) -> None:
        self._check_ready()
        self._state = BrowserState.BUSY
        try:
            await self._page.goto(url, timeout=self._config.timeout_seconds * 1000)
            # Navigation invalidates the previous page generation
            self._page_generation = str(uuid.uuid4())
            self._element_cache.clear()
            self._element_counter = 0
        except PlaywrightTimeoutError:
            raise NavigationTimeoutError(url)
        except PlaywrightError as e:
            raise NavigationError(f"Failed to navigate: {e}", url=url)
        finally:
            self._state = BrowserState.READY if self._state != BrowserState.CRASHED else BrowserState.CRASHED

    def _resolve_locator(self, spec: LocatorSpec):
        if spec.strategy == "css":
            return self._page.locator(f"css={spec.value}")
        elif spec.strategy == "xpath":
            return self._page.locator(f"xpath={spec.value}")
        elif spec.strategy == "role":
            if spec.name:
                return self._page.get_by_role(spec.value, name=spec.name)
            return self._page.get_by_role(spec.value)
        elif spec.strategy == "text":
            return self._page.get_by_text(spec.value)
        elif spec.strategy == "test-id":
            return self._page.get_by_test_id(spec.value)
        elif spec.strategy == "label":
            return self._page.get_by_label(spec.value)
        else:
            raise ValueError(f"Unknown locator strategy: {spec.strategy}")

    async def _get_locator_for_action(self, element_id: Optional[str] = None, locator: Optional[LocatorSpec] = None):
        if not element_id and not locator:
            raise ValueError("Must provide either element_id or locator.")
            
        if element_id:
            # Check for stale element reference (generation mismatch)
            if self._page_generation not in element_id:
                raise ElementNotFoundError(
                    f"Element ID {element_id} is stale. The page has navigated since it was inspected.", 
                    details={"element_id": element_id, "current_generation": self._page_generation}
                )
                
            if element_id not in self._element_cache:
                raise ElementNotFoundError(f"Element ID {element_id} not found in cache. It may be stale.", details={"element_id": element_id})
            spec = self._element_cache[element_id]
        else:
            spec = locator
            
        pw_locator = self._resolve_locator(spec)
        
        # Check if it actually resolves
        try:
            count = await pw_locator.count()
            if count == 0:
                raise ElementNotFoundError(f"Could not find element using strategy {spec.strategy}='{spec.value}'")
        except PlaywrightError as e:
            raise ElementNotFoundError(f"Error evaluating locator: {e}")
            
        return pw_locator

    async def click(self, element_id: Optional[str] = None, locator: Optional[LocatorSpec] = None) -> None:
        self._check_ready()
        self._state = BrowserState.BUSY
        try:
            pw_locator = await self._get_locator_for_action(element_id, locator)
            
            # Using force=False checks for visibility, actionability
            await pw_locator.first.click(timeout=self._config.timeout_seconds * 1000)
        except PlaywrightTimeoutError:
            raise ElementNotVisibleError("Timed out waiting for element to be visible/clickable.")
        except PlaywrightError as e:
            raise ElementInteractionError(f"Failed to click element: {e}")
        except Exception as e:
            raise e
        finally:
            if self._state != BrowserState.CRASHED:
                self._state = BrowserState.READY

    async def type_text(self, text: str, element_id: Optional[str] = None, locator: Optional[LocatorSpec] = None) -> None:
        self._check_ready()
        self._state = BrowserState.BUSY
        try:
            pw_locator = await self._get_locator_for_action(element_id, locator)
            
            await pw_locator.first.fill(text, timeout=self._config.timeout_seconds * 1000)
        except PlaywrightTimeoutError:
            raise ElementNotVisibleError("Timed out waiting for element to be visible/fillable.")
        except PlaywrightError as e:
            raise ElementInteractionError(f"Failed to type text: {e}")
        finally:
            if self._state != BrowserState.CRASHED:
                self._state = BrowserState.READY
                
    async def press(self, key: str) -> None:
        self._check_ready()
        self._state = BrowserState.BUSY
        try:
            await self._page.keyboard.press(key)
        except PlaywrightError as e:
            raise ElementInteractionError(f"Failed to press key {key}: {e}")
        finally:
            if self._state != BrowserState.CRASHED:
                self._state = BrowserState.READY

    async def screenshot(self) -> bytes:
        self._check_ready()
        self._state = BrowserState.BUSY
        try:
            # Full page screenshot
            return await self._page.screenshot(full_page=True, timeout=self._config.timeout_seconds * 1000)
        except PlaywrightError as e:
            raise BrowserContextError(f"Failed to take screenshot: {e}")
        finally:
            if self._state != BrowserState.CRASHED:
                self._state = BrowserState.READY

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        self._check_ready()
        self._state = BrowserState.BUSY
        try:
            return await self._page.evaluate(script, arg=arg)
        except PlaywrightError as e:
            raise BrowserContextError(f"Failed to evaluate script: {e}")
        finally:
            if self._state != BrowserState.CRASHED:
                self._state = BrowserState.READY

    async def inspect(self) -> Dict[str, Any]:
        self._check_ready()
        self._state = BrowserState.BUSY
        try:
            url = self._page.url
            title = await self._page.title()
            
            # Basic DOM snapshot extraction using JS
            # In MVP we only extract links, buttons, and inputs for simplicity
            js_code = """
            () => {
                const elements = [];
                let counter = 0;
                
                const processNode = (node, role) => {
                    if (!node) return;
                    
                    const rect = node.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0 && window.getComputedStyle(node).visibility !== 'hidden';
                    
                    if (!isVisible) return;
                    
                    let name = node.innerText || node.value || node.getAttribute('aria-label') || node.getAttribute('alt') || '';
                    name = name.trim().substring(0, 50);
                    
                    // Generate a unique CSS selector path to cache it
                    let cssPath = node.tagName.toLowerCase();
                    if (node.id) cssPath += '#' + node.id;
                    else if (node.className && typeof node.className === 'string') {
                        const classes = node.className.split(' ').filter(c => c).join('.');
                        if (classes) cssPath += '.' + classes;
                    }
                    
                    elements.push({
                        role: role,
                        name: name,
                        visible: isVisible,
                        tag: node.tagName.toLowerCase(),
                        css: cssPath
                    });
                };
                
                document.querySelectorAll('a').forEach(n => processNode(n, 'link'));
                document.querySelectorAll('button').forEach(n => processNode(n, 'button'));
                document.querySelectorAll('input, textarea, select').forEach(n => processNode(n, 'input'));
                
                return elements;
            }
            """
            
            dom_elements = await self._page.evaluate(js_code)
            
            browser_elements = []
            
            for el in dom_elements:
                self._element_counter += 1
                el_id = f"{self._run_id}/{self._page_generation}/e{self._element_counter}"
                
                # Cache the locator spec using CSS
                self._element_cache[el_id] = LocatorSpec(strategy="css", value=el["css"])
                
                browser_elements.append(BrowserElement(
                    element_id=el_id,
                    role=el["role"],
                    name=el["name"],
                    visible_text=el["name"] if el["role"] != "input" else None,
                    metadata={"tag": el["tag"]}
                ))
            
            return {
                "url": url,
                "title": title,
                "elements": [
                    {
                        "id": e.element_id,
                        "role": e.role,
                        "name": e.name
                    }
                    for e in browser_elements
                ]
            }
            
        except PlaywrightError as e:
            raise BrowserContextError(f"Failed to inspect page: {e}")
        finally:
            if self._state != BrowserState.CRASHED:
                self._state = BrowserState.READY
