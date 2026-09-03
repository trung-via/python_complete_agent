"""Browser attachment/ownership regressions; never contact an operator browser.

Lifecycle doubles replace only the Playwright boundary. DOM regressions below
launch isolated Chromium and fulfill local fixture documents in memory.
"""

import asyncio
import inspect
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from playwright.async_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from src.browser.errors import (
    BrowserContextError,
    BrowserNotStartedError,
    BrowserSessionUnavailableError,
    NavigationTimeoutError,
    PageClosedError,
)
from src.browser.models import BrowserConfig, BrowserState
from src.browser.session import BrowserSession
from src.integrations.playwright.manager import PlaywrightBrowserManager
from src.integrations.playwright.session import PlaywrightBrowserSession
from src.product_source.models import (
    MediaProvenance,
    MediaRole,
    SourcePackBlockedError,
    SourcePackExtractionError,
)
from src.product_source.platforms.shopee import ShopeeSourceExtractor, _SHOPEE_EXTRACTION_SCRIPT


ENDPOINT = "http://127.0.0.1:9222"


def forbidden(name):
    return AsyncMock(side_effect=AssertionError(f"Forbidden Playwright call: {name}"))


class Emitter:
    def __init__(self):
        self.listeners = {}
        self.removed = []

    def on(self, event, callback):
        self.listeners.setdefault(event, []).append(callback)

    def remove_listener(self, event, callback):
        self.listeners[event].remove(callback)
        self.removed.append((event, callback))

    def emit(self, event):
        for callback in list(self.listeners.get(event, [])):
            callback(self)


class PageDouble(Emitter):
    def __init__(self, closed=False):
        super().__init__()
        self.closed = closed
        self.is_closed = Mock(side_effect=lambda: self.closed)
        self.close = AsyncMock(side_effect=self._close)
        self.goto = forbidden("page.goto on start")
        self.evaluate = AsyncMock()
        self.set_viewport_size = forbidden("borrowed page.set_viewport_size")
        self.set_default_timeout = Mock(side_effect=AssertionError("borrowed page timeout"))

    def _close(self):
        self.closed = True


class ContextDouble:
    def __init__(self, pages):
        self.pages = pages
        self.new_page = forbidden("context.new_page")
        self.close = AsyncMock(side_effect=self._close)
        self.set_default_timeout = Mock(side_effect=AssertionError("borrowed context timeout"))

    async def _close(self):
        for page in self.pages:
            await page.close()


class BrowserDouble(Emitter):
    def __init__(self, contexts):
        super().__init__()
        self.contexts = contexts
        self.connected = True
        self.is_connected = Mock(side_effect=lambda: self.connected)
        self.new_context = forbidden("browser.new_context")
        self.close = AsyncMock(side_effect=self._close)

    def _close(self):
        self.connected = False
        self.emit("disconnected")


class PlaywrightBoundary:
    def __init__(self, monkeypatch):
        self.page = PageDouble()
        self.context = ContextDouble([self.page])
        self.browser = BrowserDouble([self.context])
        self.types = {
            name: SimpleNamespace(
                connect_over_cdp=AsyncMock(return_value=self.browser),
                launch=forbidden(f"{name}.launch"),
                launch_persistent_context=forbidden(f"{name}.launch_persistent_context"),
            )
            for name in ("chromium", "firefox", "webkit")
        }
        self.connections = []

        async def start():
            connection = SimpleNamespace(**self.types, stop=AsyncMock())
            self.connections.append(connection)
            return connection

        self.start = AsyncMock(side_effect=start)
        self.factory = Mock(return_value=SimpleNamespace(start=self.start))
        monkeypatch.setattr("src.integrations.playwright.session.async_playwright", self.factory)

    @property
    def connect(self):
        return self.types["chromium"].connect_over_cdp

    def allow_launch(self, browser_type="chromium"):
        self.types[browser_type].launch = AsyncMock(return_value=self.browser)
        self.browser.new_context = AsyncMock(return_value=self.context)
        self.context.new_page = AsyncMock(return_value=self.page)

    def assert_no_creation(self):
        for browser_type in self.types.values():
            browser_type.launch.assert_not_called()
            browser_type.launch_persistent_context.assert_not_called()
        self.browser.new_context.assert_not_called()
        for context in self.browser.contexts:
            context.new_page.assert_not_called()

    def assert_borrowed_open(self):
        self.browser.close.assert_not_called()
        for context in self.browser.contexts:
            context.close.assert_not_called()
            for page in context.pages:
                page.close.assert_not_called()


@pytest.fixture
def boundary(monkeypatch):
    return PlaywrightBoundary(monkeypatch)


@pytest.mark.asyncio
async def test_cdp_reuses_exact_first_context_and_first_open_page(boundary):
    closed, later = PageDouble(closed=True), PageDouble()
    boundary.context.pages = [closed, boundary.page, later]
    other_context = ContextDouble([PageDouble()])
    boundary.browser.contexts.append(other_context)
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    config = BrowserConfig(
        headless=False, executable_path="unused-chrome", viewport_width=333,
        viewport_height=444, user_agent="unused-agent", timeout_seconds=0,
    )
    session = await manager.get_or_create_session("run", config)
    assert type(session) is PlaywrightBrowserSession
    assert session._context is boundary.context
    assert session._page is boundary.page
    assert session.state is BrowserState.READY
    assert await manager.get_or_create_session("run", BrowserConfig()) is session
    await session.start()
    boundary.connect.assert_awaited_once_with(ENDPOINT, timeout=30_000)
    boundary.start.assert_awaited_once()
    boundary.assert_no_creation()
    for context in boundary.browser.contexts:
        context.set_default_timeout.assert_not_called()
        for page in context.pages:
            page.goto.assert_not_called()
            page.set_viewport_size.assert_not_called()
            page.set_default_timeout.assert_not_called()
    await manager.close_all()
    boundary.assert_borrowed_open()


@pytest.mark.asyncio
async def test_concurrent_acquisition_attaches_once(boundary):
    entered, release = asyncio.Event(), asyncio.Event()

    async def attach(*args, **kwargs):
        entered.set()
        await release.wait()
        return boundary.browser

    boundary.connect.side_effect = attach
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    acquisitions = [asyncio.create_task(manager.get_or_create_session("shared-run")) for _ in range(8)]
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        assert boundary.connect.await_count == 1
        release.set()
        sessions = await asyncio.gather(*acquisitions)
        assert all(session is sessions[0] for session in sessions)
        boundary.connect.assert_awaited_once()
        boundary.assert_no_creation()
    finally:
        release.set()
        await asyncio.gather(*acquisitions, return_exceptions=True)
        await manager.close_all()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["refused", "timeout", "missing-context", "empty-pages", "closed-pages", "disconnected"])
async def test_attachment_failures_never_cache_or_launch(boundary, failure):
    if failure == "refused":
        boundary.connect.side_effect = PlaywrightError("connection refused")
    elif failure == "timeout":
        boundary.connect.side_effect = PlaywrightTimeoutError("connection timed out")
    elif failure == "missing-context":
        boundary.browser.contexts = []
    elif failure == "empty-pages":
        boundary.context.pages = []
        # A page in a later context does not authorize selecting that context.
        boundary.browser.contexts.append(ContextDouble([PageDouble()]))
    elif failure == "closed-pages":
        boundary.page.closed = True
    else:
        boundary.browser.connected = False
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    with pytest.raises(BrowserContextError, match="Failed to attach") as error:
        await manager.get_or_create_session("failed")
    assert ENDPOINT in str(error.value)
    assert manager._sessions == {}
    boundary.connect.assert_awaited_once_with(ENDPOINT, timeout=30_000)
    boundary.connections[0].stop.assert_awaited_once()
    assert boundary.browser.listeners.get("disconnected", []) == []
    assert boundary.page.listeners.get("crash", []) == []
    boundary.assert_no_creation()
    boundary.assert_borrowed_open()
    await manager.close_all()


@pytest.mark.asyncio
@pytest.mark.parametrize("browser_type", ["firefox", "webkit", "unknown"])
async def test_non_chromium_is_rejected_before_start(boundary, browser_type):
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    with pytest.raises(BrowserContextError, match="requires browser_type='chromium'"):
        await manager.get_or_create_session("unsupported", BrowserConfig(browser_type=browser_type))
    assert manager._sessions == {}
    boundary.factory.assert_not_called()
    boundary.assert_no_creation()


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal", ["closed", "crashed", "disconnect-event", "disconnect-without-event"])
async def test_cached_terminal_session_is_not_restarted(boundary, terminal):
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    session = await manager.get_or_create_session("run")
    if terminal == "closed":
        await session.close()
        expected_error = BrowserNotStartedError
    else:
        expected_error = BrowserContextError
        if terminal == "crashed":
            boundary.page.emit("crash")
        else:
            boundary.browser.connected = False
            if terminal == "disconnect-event":
                boundary.browser.emit("disconnected")
    with pytest.raises(BrowserSessionUnavailableError):
        await manager.get_or_create_session("run")
    assert manager._sessions["run"] is session
    with pytest.raises(expected_error):
        await session.evaluate("1")
    boundary.page.evaluate.assert_not_called()
    assert session.state is (BrowserState.CLOSED if terminal == "closed" else BrowserState.CRASHED)
    boundary.connect.assert_awaited_once()
    boundary.assert_no_creation()
    await manager.close_all()


@pytest.mark.asyncio
async def test_shared_borrowed_resources_and_listener_ownership(boundary):
    external_crash, external_disconnect = Mock(), Mock()
    boundary.page.on("crash", external_crash)
    boundary.browser.on("disconnected", external_disconnect)
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    first = await manager.get_or_create_session("first")
    second = await manager.get_or_create_session("second")
    assert first is not second
    assert first._context is second._context is boundary.context
    assert first._page is second._page is boundary.page
    assert len(boundary.page.listeners["crash"]) == 3
    await manager.close_session("first")
    await manager.close_session("first")
    await first.close()
    assert first.state is BrowserState.CLOSED
    assert boundary.page.listeners["crash"] == [external_crash, second._on_crash]
    assert boundary.browser.listeners["disconnected"] == [external_disconnect, second._on_disconnected]
    assert second.state is BrowserState.READY
    boundary.page.evaluate.return_value = "still usable"
    assert await second.evaluate("'still usable'") == "still usable"
    boundary.connections[0].stop.assert_awaited_once()
    boundary.connections[1].stop.assert_not_called()
    boundary.page.emit("crash")
    assert first.state is BrowserState.CLOSED
    assert second.state is BrowserState.CRASHED
    external_crash.assert_called_once()
    await manager.close_all()
    await manager.close_all()
    assert manager._sessions == {}
    assert boundary.page.listeners["crash"] == [external_crash]
    assert boundary.browser.listeners["disconnected"] == [external_disconnect]
    for connection in boundary.connections:
        connection.stop.assert_awaited_once()
    boundary.assert_borrowed_open()


@pytest.mark.asyncio
async def test_partial_start_cleans_listeners_and_preserves_original_error(boundary):
    original_on = boundary.page.on

    def broken_listener(event, callback):
        original_on(event, callback)
        raise PlaywrightError("original listener setup failure")

    boundary.page.on = broken_listener
    original_start = boundary.start.side_effect

    async def start():
        connection = await original_start()
        connection.stop.side_effect = PlaywrightError("secondary cleanup failure")
        return connection

    boundary.start.side_effect = start
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    with pytest.raises(BrowserContextError, match="original listener setup failure") as error:
        await manager.get_or_create_session("partial")
    assert str(error.value.__cause__) == "original listener setup failure"
    assert manager._sessions == {}
    assert boundary.page.listeners["crash"] == []
    assert boundary.browser.listeners["disconnected"] == []
    boundary.connections[0].stop.assert_awaited_once()
    boundary.assert_borrowed_open()


@pytest.mark.asyncio
@pytest.mark.parametrize("event", ["disconnect", "page-close"])
async def test_attachment_cannot_overwrite_failure_with_ready(boundary, event):
    original_on = boundary.page.on

    def interrupted_listener(name, callback):
        original_on(name, callback)
        if event == "disconnect":
            boundary.browser.connected = False
            boundary.browser.emit("disconnected")
        else:
            boundary.page.closed = True

    boundary.page.on = interrupted_listener
    session = PlaywrightBrowserSession("partial", BrowserConfig(), cdp_endpoint=ENDPOINT)
    with pytest.raises(BrowserContextError):
        await session.start()
    assert session.state is BrowserState.CRASHED
    assert session._page is session._context is session._browser is session._playwright is None
    with pytest.raises(BrowserContextError):
        await session.evaluate("1")
    await session.close()
    await session.close()
    boundary.connections[0].stop.assert_awaited_once()
    boundary.assert_borrowed_open()


@pytest.mark.asyncio
async def test_cancelled_attachment_releases_connection_without_cache(boundary):
    boundary.connect.side_effect = asyncio.CancelledError()
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    with pytest.raises(asyncio.CancelledError):
        await manager.get_or_create_session("cancelled")
    assert manager._sessions == {}
    boundary.connections[0].stop.assert_awaited_once()
    boundary.assert_no_creation()
    boundary.assert_borrowed_open()


@pytest.mark.asyncio
@pytest.mark.parametrize("browser_type", ["chromium", "firefox", "webkit"])
async def test_launch_mode_preserves_configuration_and_owned_cleanup(boundary, browser_type):
    boundary.allow_launch(browser_type)
    config = BrowserConfig(
        browser_type=browser_type, headless=False, executable_path="isolated-browser",
        viewport_width=901, viewport_height=702, user_agent="isolated-agent", timeout_seconds=7,
    )
    manager = PlaywrightBrowserManager()
    session = await manager.get_or_create_session("isolated", config)
    boundary.types[browser_type].launch.assert_awaited_once_with(headless=False, executable_path="isolated-browser")
    boundary.browser.new_context.assert_awaited_once_with(
        viewport={"width": 901, "height": 702}, user_agent="isolated-agent",
    )
    boundary.context.new_page.assert_awaited_once_with()
    boundary.connect.assert_not_called()
    boundary.page.goto = AsyncMock()
    await session.navigate("https://fixture.invalid/")
    boundary.page.goto.assert_awaited_once_with("https://fixture.invalid/", timeout=7000)
    boundary.page.goto.side_effect = PlaywrightTimeoutError("navigation timeout")
    with pytest.raises(NavigationTimeoutError):
        await session.navigate("https://fixture.invalid/")
    assert session.state is BrowserState.READY
    await manager.close_all()
    await session.close()
    boundary.context.close.assert_awaited_once()
    boundary.page.close.assert_awaited_once()
    boundary.browser.close.assert_awaited_once()
    boundary.connections[0].stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_direct_session_still_launches_with_defaults(boundary):
    boundary.allow_launch()
    session = PlaywrightBrowserSession("direct", BrowserConfig())
    await session.start()
    boundary.types["chromium"].launch.assert_awaited_once_with(headless=True)
    boundary.browser.new_context.assert_awaited_once_with(viewport={"width": 1280, "height": 720})
    boundary.context.new_page.assert_awaited_once()
    boundary.connect.assert_not_called()
    await session.close()
    boundary.browser.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_at", ["new-context", "new-page", "listener"])
async def test_partial_launch_releases_all_owned_resources(boundary, failure_at):
    boundary.allow_launch()
    if failure_at == "new-context":
        boundary.browser.new_context.side_effect = PlaywrightError("partial launch")
    elif failure_at == "new-page":
        boundary.context.new_page.side_effect = PlaywrightError("partial launch")
    else:
        original_on = boundary.page.on

        def fail_on(event, callback):
            original_on(event, callback)
            raise PlaywrightError("partial launch")

        boundary.page.on = fail_on
    manager = PlaywrightBrowserManager()
    with pytest.raises(BrowserContextError, match="partial launch"):
        await manager.get_or_create_session("partial")
    assert manager._sessions == {}
    if failure_at != "new-context":
        boundary.context.close.assert_awaited_once()
    boundary.browser.close.assert_awaited_once()
    boundary.connections[0].stop.assert_awaited_once()
    assert boundary.page.listeners.get("crash", []) == []


@pytest.mark.asyncio
async def test_launch_cleanup_continues_after_context_close_failure(boundary):
    boundary.allow_launch()
    manager = PlaywrightBrowserManager()
    session = await manager.get_or_create_session("isolated")
    boundary.context.close.side_effect = PlaywrightError("context already gone")
    await manager.close_all()
    assert session.state is BrowserState.CLOSED
    boundary.browser.close.assert_awaited_once()
    boundary.connections[0].stop.assert_awaited_once()
    assert boundary.page.listeners["crash"] == []


def test_evaluate_protocol_and_implementation_signatures():
    for contract in (BrowserSession, PlaywrightBrowserSession):
        method = inspect.signature(contract.evaluate)
        assert method.parameters["arg"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert method.parameters["arg"].default is None
        method.bind(None, "script")
        method.bind(None, "script", False)
        method.bind(None, "script", arg=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["product-123", None, False, 0, "", [0, False, None], {"id": "123"}])
@pytest.mark.parametrize("keyword", [False, True])
async def test_evaluate_forwards_argument_unchanged(boundary, value, keyword):
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    session = await manager.get_or_create_session("evaluate")
    returned = value

    async def evaluate(script, *, arg):
        assert session.state is BrowserState.BUSY
        assert arg is value
        return returned

    boundary.page.evaluate.side_effect = evaluate
    try:
        result = await session.evaluate("value => value", arg=value) if keyword else await session.evaluate("value => value", value)
        assert result is returned
        boundary.page.evaluate.assert_awaited_once_with("value => value", arg=value)
        assert session.state is BrowserState.READY
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_evaluate_one_argument_errors_and_readiness(boundary):
    session = PlaywrightBrowserSession("evaluate", BrowserConfig(), cdp_endpoint=ENDPOINT)
    with pytest.raises(BrowserNotStartedError):
        await session.evaluate("1")
    await session.start()
    boundary.page.evaluate.return_value = 42
    assert await session.evaluate("40 + 2") == 42
    boundary.page.evaluate.assert_awaited_once_with("40 + 2", arg=None)
    session._state = BrowserState.BUSY
    assert await session.evaluate("40 + 2") == 42
    assert session.state is BrowserState.READY
    boundary.page.evaluate.side_effect = PlaywrightError("bad script")
    with pytest.raises(BrowserContextError, match="Failed to evaluate script: bad script"):
        await session.evaluate("bad", arg=False)
    assert session.state is BrowserState.READY
    boundary.page.evaluate.side_effect = ValueError("unexpected error")
    with pytest.raises(ValueError, match="unexpected error"):
        await session.evaluate("bad")
    assert session.state is BrowserState.READY
    boundary.page.closed = True
    boundary.page.evaluate.reset_mock()
    with pytest.raises(PageClosedError):
        await session.evaluate("1")
    boundary.page.evaluate.assert_not_called()
    await session.close()
    with pytest.raises(BrowserNotStartedError):
        await session.evaluate("1")


@pytest.mark.asyncio
@pytest.mark.parametrize("event", ["crash", "disconnected"])
async def test_evaluate_does_not_restore_ready_after_crash_or_disconnect(boundary, event):
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    session = await manager.get_or_create_session("evaluate")

    async def evaluate(script, *, arg):
        assert session.state is BrowserState.BUSY
        if event == "crash":
            boundary.page.emit("crash")
        else:
            boundary.browser.connected = False
            boundary.browser.emit("disconnected")
        raise PlaywrightError("target lost")

    boundary.page.evaluate.side_effect = evaluate
    with pytest.raises(BrowserContextError, match="target lost"):
        await session.evaluate("1", None)
    assert session.state is BrowserState.CRASHED
    with pytest.raises(BrowserSessionUnavailableError):
        await manager.get_or_create_session("evaluate")
    await manager.close_all()


@pytest.mark.asyncio
async def test_shopee_extractor_through_real_manager_and_session(boundary):
    boundary.page.goto = AsyncMock()
    boundary.page.evaluate.return_value = {
        "structured": {"product_id": "456789", "title": "Product", "images": ["https://fixture.invalid/image.jpg"]},
    }
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    try:
        pack = await ShopeeSourceExtractor(browser=manager).extract(
            "https://shopee.vn/product/123/456789", run_id="extract",
        )
        session = await manager.get_or_create_session("extract")
        assert type(session) is PlaywrightBrowserSession
        boundary.page.goto.assert_awaited_once_with("https://shopee.vn/product/123/456789", timeout=30_000)
        boundary.page.evaluate.assert_awaited_once_with(_SHOPEE_EXTRACTION_SCRIPT, arg="456789")
        assert boundary.page.evaluate.call_args.args[0] is _SHOPEE_EXTRACTION_SCRIPT
        assert pack.source_product_id == "456789"
        assert pack.title == "Product"
        assert pack.media[0].provenance is MediaProvenance.STRUCTURED_PRODUCT_DATA
        boundary.connect.assert_awaited_once()
        boundary.assert_no_creation()
    finally:
        await manager.close_all()


FIXTURE_URL = "https://fixture.invalid/product/123/456789"
MEDIA = "https://fixture.invalid/media/"


@asynccontextmanager
async def isolated_document(html):
    """Real launch/session path; all requests are fulfilled locally or aborted."""
    manager = PlaywrightBrowserManager()
    try:
        session = await manager.get_or_create_session("dom", BrowserConfig(headless=True))

        async def local_only(route):
            if route.request.url == FIXTURE_URL and route.request.resource_type == "document":
                await route.fulfill(status=200, content_type="text/html", body=html)
            else:
                await route.abort()

        await session._context.route("**/*", local_only)
        yield manager, session
    finally:
        await manager.close_all()


@pytest.mark.asyncio
@pytest.mark.parametrize("matches", [True, False])
async def test_shopee_local_dom_identity_and_source_pack_through_real_session(matches):
    structured = {
        "@type": "Product", "productID": "456789" if matches else "999999",
        "sku": "fixture-sku", "name": "Structured title", "brand": {"name": "Fixture brand"},
        "description": "Structured description", "image": MEDIA + "structured.jpg",
    }
    html = f"""
    <html><head><title>Local product</title>
      <script type="application/ld+json">{json.dumps(structured)}</script>
      <script src="https://external.invalid/incidental.js"></script>
    </head><body>
      <div class="product-briefing">
        <div class="product-image-carousel">
          <img src="{MEDIA}gallery.jpg_tn">
          <img src="{MEDIA}gallery.jpg">
          <div class="product-reviews"><img src="{MEDIA}review.jpg"></div>
          <div class="similar-products"><img src="{MEDIA}recommended.jpg"></div>
        </div>
      </div>
      <div class="product-variation"><span>Blue</span><img src="{MEDIA}variant.jpg"></div>
      <div class="product-detail">
        <div class="kIo6pj"><label>Material</label><div>Cotton</div></div>
        <img src="{MEDIA}seller.jpg"><img src="{MEDIA}gallery.jpg">
        <div class="comment"><img src="{MEDIA}comment.jpg"></div>
      </div>
      <footer><img src="{MEDIA}footer.jpg"></footer>
      <aside><img src="{MEDIA}unrelated.jpg"></aside>
    </body></html>
    """
    async with isolated_document(html) as (manager, session):
        pack = await ShopeeSourceExtractor(browser=manager).extract(FIXTURE_URL, run_id="dom")
        assert await manager.get_or_create_session("dom") is session
        # Execute the exact source script through the wrapper as well as extract().
        data = await session.evaluate(_SHOPEE_EXTRACTION_SCRIPT, arg="456789")
        assert data["structured"]["product_id"] == ("456789" if matches else None)
        assert data["structured"]["images"] == ([MEDIA + "structured.jpg"] if matches else [])
        assert data["gallery"] == [MEDIA + "gallery.jpg"]
        assert data["description_media"] == [MEDIA + "seller.jpg", MEDIA + "gallery.jpg"]
        assert data["fallback_media"] == []
        assert data["blocked"] is False
        assert pack.source_pack_id == "shopee_456789"
        assert pack.source_product_id == "456789"
        assert pack.platform == "shopee"
        assert pack.title == ("Structured title" if matches else None)
        assert pack.brand == ("Fixture brand" if matches else None)
        assert pack.model_sku == ("fixture-sku" if matches else None)
        assert pack.description_text == ("Structured description" if matches else None)
        expected = []
        if matches:
            expected.append(("structured.jpg", MediaRole.PRIMARY, MediaProvenance.STRUCTURED_PRODUCT_DATA))
        expected.extend([
            ("gallery.jpg", MediaRole.GALLERY if matches else MediaRole.PRIMARY, MediaProvenance.SEMANTIC_PRODUCT_GALLERY),
            ("variant.jpg", MediaRole.VARIANT, MediaProvenance.SEMANTIC_VARIANT_MEDIA),
            ("seller.jpg", MediaRole.SELLER_DESCRIPTION, MediaProvenance.SEMANTIC_SELLER_DESCRIPTION),
        ])
        assert [(m.source_url, m.role, m.provenance, m.ordinal) for m in pack.media] == [
            (MEDIA + name, role, provenance, ordinal)
            for ordinal, (name, role, provenance) in enumerate(expected)
        ]
        assert next(m for m in pack.media if m.role is MediaRole.VARIANT).variant_label == "Blue"
        assert [(fact.key, fact.value) for fact in pack.facts] == (
            [("Material", "Cotton"), ("Brand", "Fixture brand")] if matches else [("Material", "Cotton")]
        )
        assert all(m.byte_size is None and m.local_filename is None for m in pack.media)
        page, browser = session._page, session._browser
    assert page.is_closed()
    assert not browser.is_connected()
    assert session.state is BrowserState.CLOSED


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["fallback", "untrusted-only", "blocked"])
async def test_shopee_local_dom_fallback_and_fail_closed_through_real_session(case):
    if case == "fallback":
        images = "".join(f'<img src="{MEDIA}{i}.jpg">' for i in range(12))
        html = f'<div class="product-briefing">{images}</div><aside><img src="{MEDIA}outside.jpg"></aside>'
    elif case == "blocked":
        html = '<div class="shopee-captcha">Verification</div>'
    else:
        html = f'<div class="product-reviews"><img src="{MEDIA}review.jpg"></div><aside><img src="{MEDIA}outside.jpg"></aside>'
    async with isolated_document(html) as (manager, session):
        extractor = ShopeeSourceExtractor(browser=manager)
        if case == "fallback":
            pack = await extractor.extract(FIXTURE_URL, run_id="dom")
            assert [media.source_url for media in pack.media] == [f"{MEDIA}{i}.jpg" for i in range(10)]
            assert all(media.provenance is MediaProvenance.PLATFORM_SCOPED_FALLBACK for media in pack.media)
        else:
            expected = SourcePackBlockedError if case == "blocked" else SourcePackExtractionError
            with pytest.raises(expected):
                await extractor.extract(FIXTURE_URL, run_id="dom")
        assert session.state is BrowserState.READY


@pytest.mark.asyncio
async def test_evaluate_real_isolated_javascript_values():
    async with isolated_document("<html></html>") as (_, session):
        assert await session.evaluate("40 + 2") == 42
        for value in ("product", None, False, 0, "", [0, None, False], {"id": "123"}):
            assert await session.evaluate("value => value", value) == value
            assert await session.evaluate("value => value", arg=value) == value
