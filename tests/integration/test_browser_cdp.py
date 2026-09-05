from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

import pytest

from src.browser.errors import BrowserContextError, BrowserSessionUnavailableError
from src.browser.models import BrowserConfig, BrowserState
from src.integrations.playwright.manager import PlaywrightBrowserManager
import src.integrations.playwright.session as session_module


ENDPOINT = "http://127.0.0.1:9222"


class FakeEmitter:
    def __init__(self) -> None:
        self.listeners: dict[str, list[Callable[..., None]]] = {}
        self.removed: list[tuple[str, Callable[..., None]]] = []

    def on(self, event: str, handler: Callable[..., None]) -> None:
        self.listeners.setdefault(event, []).append(handler)

    def remove_listener(self, event: str, handler: Callable[..., None]) -> None:
        self.removed.append((event, handler))
        if handler in self.listeners.get(event, []):
            self.listeners[event].remove(handler)

    def emit(self, event: str) -> None:
        for handler in list(self.listeners.get(event, [])):
            handler(self)


class FakePage(FakeEmitter):
    def __init__(self, *, closed: bool = False, evaluate_result: Any = None) -> None:
        super().__init__()
        self.closed = closed
        self.close_count = 0
        self.goto_calls: list[tuple[str, dict[str, Any]]] = []
        self.evaluate_calls: list[tuple[Any, ...]] = []
        self.evaluate_result = evaluate_result

    def is_closed(self) -> bool:
        return self.closed

    async def close(self) -> None:
        self.close_count += 1
        self.closed = True

    async def goto(self, url: str, **kwargs: Any) -> None:
        self.goto_calls.append((url, kwargs))

    async def evaluate(self, *args: Any) -> Any:
        self.evaluate_calls.append(args)
        return self.evaluate_result


class FakeContext:
    def __init__(self, pages: Optional[list[FakePage]] = None) -> None:
        self.pages = pages or []
        self.close_count = 0
        self.new_page_count = 0

    async def new_page(self) -> FakePage:
        self.new_page_count += 1
        page = FakePage()
        self.pages.append(page)
        return page

    async def close(self) -> None:
        self.close_count += 1


class FakeBrowser(FakeEmitter):
    def __init__(self, contexts: Optional[list[FakeContext]] = None) -> None:
        super().__init__()
        self.contexts = contexts or []
        self.connected = True
        self.close_count = 0
        self.new_context_count = 0

    def is_connected(self) -> bool:
        return self.connected

    async def new_context(self, **kwargs: Any) -> FakeContext:
        self.new_context_count += 1
        context = FakeContext()
        self.contexts.append(context)
        return context

    async def close(self) -> None:
        self.close_count += 1
        self.connected = False


class FakeChromium:
    def __init__(
        self,
        *,
        cdp_browser: Optional[FakeBrowser] = None,
        connect_error: Optional[Exception] = None,
        launch_browser: Optional[FakeBrowser] = None,
    ) -> None:
        self.cdp_browser = cdp_browser
        self.connect_error = connect_error
        self.launch_browser = launch_browser or FakeBrowser()
        self.connect_calls: list[tuple[str, int]] = []
        self.launch_calls: list[dict[str, Any]] = []

    async def connect_over_cdp(self, endpoint: str, *, timeout: int) -> FakeBrowser:
        self.connect_calls.append((endpoint, timeout))
        if self.connect_error:
            raise self.connect_error
        assert self.cdp_browser is not None
        return self.cdp_browser

    async def launch(self, **kwargs: Any) -> FakeBrowser:
        self.launch_calls.append(kwargs)
        return self.launch_browser


class FakePlaywright:
    def __init__(self, chromium: FakeChromium) -> None:
        self.chromium = chromium
        self.firefox = chromium
        self.stop_count = 0

    async def stop(self) -> None:
        self.stop_count += 1


class FakeStarter:
    def __init__(self, playwright: FakePlaywright) -> None:
        self.playwright = playwright
        self.start_count = 0

    async def start(self) -> FakePlaywright:
        self.start_count += 1
        return self.playwright


def install_playwright(
    monkeypatch: pytest.MonkeyPatch,
    chromium: FakeChromium,
) -> tuple[FakePlaywright, FakeStarter]:
    playwright = FakePlaywright(chromium)
    starter = FakeStarter(playwright)
    monkeypatch.setattr(session_module, "async_playwright", lambda: starter)
    return playwright, starter


@pytest.mark.asyncio
async def test_cdp_attaches_once_and_borrows_first_context_and_open_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_page = FakePage(closed=True)
    selected_page = FakePage()
    later_page = FakePage()
    selected_context = FakeContext([closed_page, selected_page, later_page])
    later_context = FakeContext([FakePage()])
    browser = FakeBrowser([selected_context, later_context])
    chromium = FakeChromium(cdp_browser=browser)
    _, starter = install_playwright(monkeypatch, chromium)
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)

    first, second = await asyncio.gather(
        manager.get_or_create_session("run", BrowserConfig(timeout_seconds=7)),
        manager.get_or_create_session("run", BrowserConfig(timeout_seconds=99)),
    )

    assert first is second
    assert first._context is selected_context
    assert first._page is selected_page
    assert chromium.connect_calls == [(ENDPOINT, 7000)]
    assert chromium.launch_calls == []
    assert starter.start_count == 1
    assert browser.new_context_count == 0
    assert selected_context.new_page_count == 0
    assert selected_page.goto_calls == []


@pytest.mark.asyncio
async def test_cdp_rejects_non_chromium_without_connecting_or_caching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser = FakeBrowser([FakeContext([FakePage()])])
    chromium = FakeChromium(cdp_browser=browser)
    _, starter = install_playwright(monkeypatch, chromium)
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)

    with pytest.raises(BrowserContextError, match="only the Chromium"):
        await manager.get_or_create_session(
            "unsupported",
            BrowserConfig(browser_type="firefox"),
        )

    assert starter.start_count == 0
    assert chromium.connect_calls == []
    assert "unsupported" not in manager._sessions


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [ConnectionRefusedError("refused"), TimeoutError("timed out")],
    ids=["refusal", "timeout"],
)
async def test_cdp_connection_failures_fail_closed_without_launch_or_cache(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    chromium = FakeChromium(connect_error=failure)
    playwright, _ = install_playwright(monkeypatch, chromium)
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)

    with pytest.raises(BrowserContextError, match="Failed to start Playwright"):
        await manager.get_or_create_session("failed")

    assert chromium.connect_calls == [(ENDPOINT, 30000)]
    assert chromium.launch_calls == []
    assert playwright.stop_count == 1
    assert "failed" not in manager._sessions


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "browser",
    [FakeBrowser([]), FakeBrowser([FakeContext([FakePage(closed=True)])])],
    ids=["missing-context", "no-usable-page"],
)
async def test_cdp_requires_existing_context_and_open_page(
    monkeypatch: pytest.MonkeyPatch,
    browser: FakeBrowser,
) -> None:
    chromium = FakeChromium(cdp_browser=browser)
    playwright, _ = install_playwright(monkeypatch, chromium)
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)

    with pytest.raises(BrowserContextError):
        await manager.get_or_create_session("failed-attachment")

    assert chromium.launch_calls == []
    assert browser.new_context_count == 0
    assert all(context.new_page_count == 0 for context in browser.contexts)
    assert browser.close_count == 0
    assert playwright.stop_count == 1
    assert "failed-attachment" not in manager._sessions


@pytest.mark.asyncio
@pytest.mark.parametrize("event", ["disconnected", "close"])
async def test_cdp_disconnection_marks_cached_session_crashed(
    monkeypatch: pytest.MonkeyPatch,
    event: str,
) -> None:
    page = FakePage()
    browser = FakeBrowser([FakeContext([page])])
    install_playwright(monkeypatch, FakeChromium(cdp_browser=browser))
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    session = await manager.get_or_create_session("disconnected")

    (browser if event == "disconnected" else page).emit(event)

    assert session.state == BrowserState.CRASHED
    with pytest.raises(BrowserSessionUnavailableError):
        await manager.get_or_create_session("disconnected")


@pytest.mark.asyncio
async def test_failed_listener_attachment_releases_only_owned_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ListenerFailingPage(FakePage):
        def on(self, event: str, handler: Callable[..., None]) -> None:
            if event == "close":
                raise RuntimeError("listener install failed")
            super().on(event, handler)

    page = ListenerFailingPage()
    context = FakeContext([page])
    browser = FakeBrowser([context])
    playwright, _ = install_playwright(
        monkeypatch,
        FakeChromium(cdp_browser=browser),
    )
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)

    with pytest.raises(BrowserContextError, match="listener install failed"):
        await manager.get_or_create_session("listener-failure")

    assert browser.close_count == 0
    assert context.close_count == 0
    assert page.close_count == 0
    assert playwright.stop_count == 1
    assert page.listeners.get("crash") == []
    assert browser.listeners.get("disconnected") == []
    assert "listener-failure" not in manager._sessions


@pytest.mark.asyncio
async def test_cdp_cleanup_never_closes_borrowed_resources_and_is_repeatable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakePage()
    context = FakeContext([page])
    browser = FakeBrowser([context])
    playwright, _ = install_playwright(
        monkeypatch,
        FakeChromium(cdp_browser=browser),
    )
    manager = PlaywrightBrowserManager(cdp_endpoint=ENDPOINT)
    session = await manager.get_or_create_session("borrowed")

    await session.close()
    await session.close()
    await manager.close_session("borrowed")
    await manager.close_all()

    assert browser.close_count == 0
    assert context.close_count == 0
    assert page.close_count == 0
    assert playwright.stop_count == 1
    assert browser.listeners.get("disconnected") == []
    assert page.listeners.get("crash") == []
    assert page.listeners.get("close") == []


@pytest.mark.asyncio
async def test_manager_without_endpoint_retains_launch_owned_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = FakePage()
    context = FakeContext([page])
    browser = FakeBrowser([context])
    chromium = FakeChromium(launch_browser=browser)
    playwright, _ = install_playwright(monkeypatch, chromium)
    manager = PlaywrightBrowserManager()

    session = await manager.get_or_create_session("launch")
    await manager.close_all()

    assert manager.cdp_endpoint is None
    assert session.state == BrowserState.CLOSED
    assert chromium.connect_calls == []
    assert chromium.launch_calls == [{"headless": True}]
    assert browser.new_context_count == 1
    assert browser.contexts[-1].new_page_count == 1
    assert browser.contexts[-1].close_count == 1
    assert browser.close_count == 1
    assert playwright.stop_count == 1


@pytest.mark.asyncio
async def test_evaluate_preserves_omission_and_falsey_arguments() -> None:
    page = FakePage(evaluate_result={"ok": True})
    browser = FakeBrowser([FakeContext([page])])
    session = session_module.PlaywrightBrowserSession("evaluate", BrowserConfig())
    session._browser = browser
    session._context = browser.contexts[0]
    session._page = page
    session._state = BrowserState.READY

    assert await session.evaluate("script") == {"ok": True}
    for value in (None, False, 0, "", [], {}):
        assert await session.evaluate("script", value) == {"ok": True}
    await session.evaluate("script", arg="keyword")

    assert page.evaluate_calls == [
        ("script",),
        ("script", None),
        ("script", False),
        ("script", 0),
        ("script", ""),
        ("script", []),
        ("script", {}),
        ("script", "keyword"),
    ]
    with pytest.raises(TypeError):
        await session.evaluate("script", 1, 2)  # type: ignore[call-arg]
