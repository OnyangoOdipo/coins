"""
Bulk-populate the database by scraping common Kenyan grocery products
from all stores. Run this once to seed the DB, then periodically to refresh.

Usage:
    python populate_db.py              # scrape all stores, all categories
    python populate_db.py --store carrefour   # only one store
    python populate_db.py --fast       # only Carrefour (no Playwright needed)
"""
import asyncio
import argparse
import time
import sys

# Ensure the app package is importable
sys.path.insert(0, ".")

from app.scrape_service import scrape_and_save, scrape_all_stores
from app.database import engine, Base

# Common Kenyan grocery search terms
SEARCH_TERMS = [
    # Staples
    "sugar",
    "unga",
    "maize flour",
    "wheat flour",
    "rice",
    "bread",
    "milk",
    "eggs",
    # Cooking
    "cooking oil",
    "salt",
    "tomato",
    "onion",
    "cooking fat",
    "butter",
    "margarine",
    # Proteins
    "beef",
    "chicken",
    "fish",
    "sausage",
    # Beverages
    "tea",
    "coffee",
    "juice",
    "water",
    "soda",
    # Household
    "soap",
    "detergent",
    "tissue",
    "toothpaste",
    # Snacks & others
    "biscuits",
    "chocolate",
    "yoghurt",
    "cheese",
    "noodles",
    "spaghetti",
    "beans",
    "lentils",
]


async def populate(store_filter: str | None = None, terms: list[str] | None = None):
    """Scrape all search terms across stores and save to DB."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    search_terms = terms or SEARCH_TERMS
    total = len(search_terms)
    grand_total = 0
    start = time.time()

    print(f"\n{'='*60}")
    print(f"  Populating database — {total} categories")
    if store_filter:
        print(f"  Store filter: {store_filter}")
    print(f"{'='*60}\n")

    for i, term in enumerate(search_terms, 1):
        term_start = time.time()
        print(f"[{i}/{total}] Scraping \"{term}\"...", end=" ", flush=True)

        try:
            if store_filter:
                results = await scrape_and_save(store_filter, term)
            else:
                results = await scrape_all_stores(term)

            count = len(results)
            grand_total += count
            elapsed = time.time() - term_start
            print(f"{count} products ({elapsed:.1f}s)")

        except Exception as e:
            print(f"ERROR: {e}")

    elapsed_total = time.time() - start
    minutes = int(elapsed_total // 60)
    seconds = int(elapsed_total % 60)

    print(f"\n{'='*60}")
    print(f"  Done! {grand_total} products saved in {minutes}m {seconds}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate the Coins database")
    parser.add_argument("--store", type=str, help="Only scrape this store (naivas, carrefour, quickmart)")
    parser.add_argument("--fast", action="store_true", help="Only scrape Carrefour (fast, no Playwright)")
    parser.add_argument("--terms", nargs="+", help="Custom search terms instead of defaults")
    args = parser.parse_args()

    store = args.store
    if args.fast:
        store = "carrefour"

    asyncio.run(populate(store_filter=store, terms=args.terms))
