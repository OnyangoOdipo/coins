"""
Orchestrates scraping and persists results to MySQL.
"""
import asyncio
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from .database import SessionLocal
from .models import Store, Product, PriceHistory, ScrapeLog, Category
from .scrapers import SCRAPERS

# Playwright-based scrapers need a ProactorEventLoop on Windows for subprocess
# support. Uvicorn's event loop may not support this, so we run them in a
# separate thread with their own loop.
PLAYWRIGHT_STORES = {"naivas", "quickmart"}
_scrape_executor = ThreadPoolExecutor(max_workers=2)

# In-memory cache: tracks (query, store_slug) combos we've already scraped
# so we don't re-scrape stores that returned zero results for a query.
# Entries expire after CACHE_TTL seconds. Resets on server restart.
_scrape_cache: dict[tuple[str, str], float] = {}
CACHE_TTL = 3600  # 1 hour


def normalize_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.lower().strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"[^\w\s\-]", "", name)
    return name


def get_or_create_store(db: Session, slug: str, name: str, base_url: str) -> Store:
    store = db.query(Store).filter_by(slug=slug).first()
    if not store:
        store_meta = {
            "naivas": {"color": "#e30613", "logo_url": "https://naivas.online/favicon.ico"},
            "carrefour": {"color": "#004f9f", "logo_url": "https://www.carrefour.ke/favicon.ico"},
            "quickmart": {"color": "#e8232a", "logo_url": "https://www.quickmart.co.ke/favicon.ico"},
        }
        meta = store_meta.get(slug, {})
        store = Store(
            slug=slug,
            name=name,
            base_url=base_url,
            color=meta.get("color", "#333"),
            logo_url=meta.get("logo_url", ""),
        )
        db.add(store)
        db.commit()
        db.refresh(store)
    return store


def upsert_product(db: Session, store: Store, data: dict) -> Product:
    """Insert or update a product, recording price history on change."""
    product = (
        db.query(Product)
        .filter_by(store_id=store.id, normalized_name=data["normalized_name"])
        .first()
    )

    if product:
        # Record price history if price changed
        if data["current_price"] and product.current_price != data["current_price"]:
            history = PriceHistory(product_id=product.id, price=data["current_price"])
            db.add(history)
        # Update fields
        product.name = data["name"]
        product.current_price = data["current_price"]
        product.original_price = data.get("original_price")
        product.image_url = data.get("image_url")
        product.url = data.get("url")
        product.unit = data.get("unit")
        product.in_stock = data.get("in_stock", True)
        product.last_scraped = datetime.utcnow()
    else:
        product = Product(
            store_id=store.id,
            name=data["name"],
            normalized_name=data["normalized_name"],
            current_price=data["current_price"],
            original_price=data.get("original_price"),
            image_url=data.get("image_url"),
            url=data.get("url"),
            unit=data.get("unit"),
            in_stock=data.get("in_stock", True),
        )
        db.add(product)
        db.flush()
        if data["current_price"]:
            history = PriceHistory(product_id=product.id, price=data["current_price"])
            db.add(history)

    db.commit()
    return product


def _sync_playwright_scrape(store_slug: str, query: str) -> list[dict]:
    """Run a Playwright scrape in a new ProactorEventLoop (Windows subprocess fix)."""
    ScraperClass = SCRAPERS.get(store_slug)
    if not ScraperClass:
        return []

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    try:
        scraper = ScraperClass()
        return loop.run_until_complete(scraper.scrape_search(query))
    finally:
        loop.close()


async def scrape_and_save(store_slug: str, query: str) -> list[dict]:
    """
    Run a search scrape for a given store and query, save to DB, return results.
    Playwright scrapers (naivas, quickmart) run in a separate thread to avoid
    Windows event loop subprocess issues.
    """
    ScraperClass = SCRAPERS.get(store_slug)
    if not ScraperClass:
        return []

    scraper_meta = ScraperClass()

    if store_slug in PLAYWRIGHT_STORES and sys.platform == "win32":
        loop = asyncio.get_event_loop()
        products = await loop.run_in_executor(
            _scrape_executor, _sync_playwright_scrape, store_slug, query
        )
    else:
        products = await scraper_meta.scrape_search(query)

    db = SessionLocal()
    try:
        store = get_or_create_store(
            db, scraper_meta.store_slug, scraper_meta.store_name, scraper_meta.base_url
        )
        for data in products:
            upsert_product(db, store, data)
    finally:
        db.close()

    return products


async def scrape_all_stores(query: str) -> list[dict]:
    """
    Scrape all stores for a query and return combined results.
    Runs sequentially to avoid resource contention between multiple browser instances.
    """
    combined = []
    for slug in SCRAPERS:
        try:
            results = await scrape_and_save(slug, query)
            combined.extend(results)
        except Exception as e:
            print(f"[{slug}] Scrape error: {e}")
    return combined


def _cache_key(query: str, slug: str) -> tuple[str, str]:
    return (query.lower().strip(), slug)


def find_missing_stores(query: str, db: Session) -> list[str]:
    """
    Check which stores need scraping for this query.
    A store is skipped if:
      1. It has matching products in the DB, OR
      2. We already scraped it for this query recently (cache hit)
    """
    now = time.time()
    missing = []

    # Split query into words for word-level matching
    words = query.lower().split()
    word_conditions = []
    for word in words:
        pattern = f"%{word}%"
        word_conditions.append(
            or_(
                func.lower(Product.name).like(pattern),
                func.lower(Product.normalized_name).like(pattern),
            )
        )

    for slug in SCRAPERS:
        # Check cache first — did we already try this query+store?
        key = _cache_key(query, slug)
        if key in _scrape_cache and (now - _scrape_cache[key]) < CACHE_TTL:
            continue

        store = db.query(Store).filter_by(slug=slug).first()
        if not store:
            missing.append(slug)
            continue

        count = (
            db.query(Product)
            .filter(
                Product.store_id == store.id,
                Product.in_stock == True,
                and_(*word_conditions),
            )
            .limit(1)
            .count()
        )
        if count == 0:
            missing.append(slug)

    return missing


async def smart_scrape(query: str, db: Session, fast_only: bool = False) -> list[str]:
    """
    Auto-scrape: check DB for each store, only scrape stores
    that have zero results for this query. Returns list of stores scraped.

    - Carrefour: fast (~2s, direct API) — always attempted
    - Naivas/Quickmart: slow (~30s, Playwright) — skipped when fast_only=True
    - Results are cached so the same query+store won't be re-scraped for 1 hour

    Use fast_only=True for optimize/batch operations to avoid blocking on
    slow Playwright scrapes. Only explicit "Live" searches should use full scrape.
    """
    missing = find_missing_stores(query, db)

    if not missing:
        return []

    # In fast mode, only scrape Carrefour (httpx, ~2s)
    if fast_only:
        missing = [s for s in missing if s not in PLAYWRIGHT_STORES]
        if not missing:
            return []

    print(f"[AutoScrape] '{query}' missing from: {missing}")

    scraped = []

    # Scrape Carrefour first (fast, httpx)
    if "carrefour" in missing:
        try:
            await scrape_and_save("carrefour", query)
            scraped.append("carrefour")
        except Exception as e:
            print(f"[carrefour] Scrape error: {e}")
        _scrape_cache[_cache_key(query, "carrefour")] = time.time()
        missing = [s for s in missing if s != "carrefour"]

    # Scrape remaining stores (Playwright-based) concurrently
    if missing:
        tasks = [scrape_and_save(slug, query) for slug in missing]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for slug, result in zip(missing, results):
            if isinstance(result, Exception):
                print(f"[{slug}] Scrape error: {result}")
            else:
                scraped.append(slug)
            _scrape_cache[_cache_key(query, slug)] = time.time()

    return scraped
