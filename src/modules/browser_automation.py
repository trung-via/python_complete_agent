import asyncio
import os
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class BrowserAutomation:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.playwright = None

    async def start(self):
        """Starts the playwright browser session using a native Chrome process."""
        self.playwright = await async_playwright().start()
        
        user_data_dir = os.path.join(os.getcwd(), "chrome_dev_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # 1. Find local Chrome
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        chrome_exe = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_exe = path
                break
                
        if not chrome_exe:
            raise RuntimeError("Could not find Google Chrome installed on this system.")
            
        # 2. Launch Chrome natively using subprocess (this bypasses Playwright automation flags!)
        import subprocess
        import time
        import socket
        
        # Check if port is already in use (Chrome already running)
        port = 9222
        def is_port_in_use(p):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('127.0.0.1', p)) == 0
                
        if not is_port_in_use(port):
            self.chrome_process = subprocess.Popen(
                [
                    chrome_exe,
                    f"--remote-debugging-port={port}",
                    f"--user-data-dir={user_data_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # Wait for CDP to be available
            for _ in range(30):
                if is_port_in_use(port): break
                time.sleep(0.5)
        
        # 3. Connect Playwright over CDP
        self.browser = await self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        self.context = self.browser.contexts[0]
        
        logger.info(f"Connected to native Chrome successfully on port {port}.")

    async def stop(self):
        """Stops the browser session."""
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
        if hasattr(self, 'chrome_process') and self.chrome_process:
            try:
                self.chrome_process.terminate()
            except:
                pass
        logger.info("Browser stopped.")

    def get_context(self):
        """Returns the current browser context for tools to use."""
        return self.context
