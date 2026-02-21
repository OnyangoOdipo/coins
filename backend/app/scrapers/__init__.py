try:
    from .naivas import NaivasScraper
    from .carrefour import CarrefourScraper
    from .quickmart import QuickmartScraper

    SCRAPERS = {
        "naivas": NaivasScraper,
        "carrefour": CarrefourScraper,
        "quickmart": QuickmartScraper,
    }
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    SCRAPERS = {}
    PLAYWRIGHT_AVAILABLE = False
    print("WARNING: playwright not installed. Scraping disabled until you run: pip install playwright playwright-stealth")
