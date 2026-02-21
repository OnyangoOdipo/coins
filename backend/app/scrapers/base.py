import asyncio
import re
import unicodedata
from abc import ABC, abstractmethod
from typing import Optional

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    async_playwright = None  # type: ignore
    Browser = object        # type: ignore
    BrowserContext = object # type: ignore
    Page = object           # type: ignore


def normalize_name(name: str) -> str:
    """
    Clean and normalize a product name for cross-store matching.
    Removes brand noise, units, extra whitespace, punctuation.
    """
    name = unicodedata.normalize("NFKD", name)
    name = name.lower().strip()
    # collapse whitespace
    name = re.sub(r"\s+", " ", name)
    # remove common units from the middle of names (keep at end)
    name = re.sub(r"[^\w\s\-]", "", name)
    return name


def clean_price(raw: str) -> Optional[float]:
    """Parse 'KES 1,250.00' or '1250' into float."""
    if not raw:
        return None
    digits = re.sub(r"[^\d.]", "", raw)
    try:
        return float(digits)
    except ValueError:
        return None


class BaseScraper(ABC):
    store_slug: str
    store_name: str

    PLAYWRIGHT_ARGS = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--no-first-run",
        "--no-zygote",
        "--disable-gpu",
        "--disable-blink-features=AutomationControlled",
    ]

    async def get_browser(self, playwright) -> Browser:
        return await playwright.chromium.launch(
            headless=True,
            args=self.PLAYWRIGHT_ARGS,
        )

    async def get_context(self, browser: Browser) -> BrowserContext:
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-KE",
            timezone_id="Africa/Nairobi",
            java_script_enabled=True,
            ignore_https_errors=True,
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-KE,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            },
        )
        # Mask automation signals
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-KE', 'en'] });
            window.chrome = { runtime: {} };
        """)
        return context

    async def safe_goto(self, page: Page, url: str, retries: int = 3, wait_until: str = "domcontentloaded", timeout: int = 30000):
        for attempt in range(retries):
            try:
                await page.goto(url, wait_until=wait_until, timeout=timeout)
                return
            except Exception as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    @abstractmethod
    async def scrape_search(self, query: str) -> list[dict]:
        """Scrape search results for a query. Returns list of product dicts."""
        pass

    @abstractmethod
    async def scrape_category(self, category_url: str) -> list[dict]:
        """Scrape all products in a category page."""
        pass
