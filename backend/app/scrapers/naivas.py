import asyncio
from playwright.async_api import async_playwright
from .base import BaseScraper, normalize_name, clean_price


class NaivasScraper(BaseScraper):
    store_slug = "naivas"
    store_name = "Naivas"
    base_url = "https://naivas.online"

    # Category map: keyword -> category URL path (from site navigation)
    CATEGORY_MAP = {
        # Commodities
        "sugar": "/commodities/sugar-sweeteners",
        "sweetener": "/commodities/sugar-sweeteners",
        "flour": "/commodities/flour",
        "unga": "/commodities/flour",
        "maize": "/commodities/flour",
        "ugali": "/commodities/flour",
        "wheat": "/commodities/flour",
        "rice": "/commodities/rice-cereals",
        "cereal": "/commodities/rice-cereals",
        "pasta": "/commodities/pasta-noodles",
        "noodle": "/commodities/pasta-noodles",
        "spaghetti": "/commodities/pasta-noodles",
        # Dairy
        "milk": "/dairy/fresh-milk",
        "yoghurt": "/dairy/yoghurt",
        "yogurt": "/dairy/yoghurt",
        "ghee": "/dairy/ghee",
        # Cold Deli
        "butter": "/cold-deli/butter",
        "cheese": "/cold-deli/cheese",
        "cream": "/cold-deli/cooking-and-whipping-cream",
        # Breakfast
        "egg": "/breakfast/eggs",
        "margarine": "/breakfast/spreads",
        "spread": "/breakfast/spreads",
        # Fats & Oils
        "oil": "/fats-oils/vegetable-oils",
        "cooking oil": "/fats-oils/vegetable-oils",
        "fat": "/fats-oils/fats",
        "cooking fat": "/fats-oils/fats",
        # Bakery
        "bread": "/naivas-bakery/bread-bread-rolls",
        # Pre-packed Meat
        "beef": "/pre-packed-meat-products/beef",
        "chicken": "/pre-packed-meat-products/frozen-chicken",
        "sausage": "/pre-packed-meat-products/sausages-smokies",
        "fish": "/pre-packed-meat-products/fish-omena",
        # Hot Beverages
        "tea": "/hot-beverage/tea-tea-bags",
        "coffee": "/hot-beverage/coffee",
        "chocolate": "/food-cupboard/confectionery",
        "cocoa": "/hot-beverage/cocoa",
        # Cold Beverages
        "juice": "/cold-beverage/ready-to-drink-juices",
        "water": "/cold-beverage/pure-and-mineral-water",
        "soda": "/cold-beverage/soda",
        # Cleaning & Laundry
        "soap": "/laundry/bar-soaps",
        "detergent": "/laundry/detergents",
        # Personal Care
        "toothpaste": "/personal-care/oral-care",
        "shampoo": "/haircare-styling/hair-wash",
        # Tissue
        "tissue": "/tissue-papers",
        # Fresh Produce
        "tomato": "/fruit-veggie/vegetable",
        "onion": "/fruit-veggie/vegetable",
        "vegetable": "/fruit-veggie/vegetable",
        "fruit": "/fruit-veggie/fruit",
        # Food Cupboard
        "biscuit": "/food-cupboard/biscuits-cookies",
        "cookie": "/food-cupboard/biscuits-cookies",
        # Dry Cereals & Legumes
        "bean": "/naivas-dry-cereals-nuts/dry-cereals",
        "lentil": "/naivas-dry-cereals-nuts/dry-cereals",
        # Spices & Condiments
        "salt": "/food-additives",
        "pepper": "/naivas-dry-cereals-nuts/weighed-spices",
        "spice": "/naivas-dry-cereals-nuts/weighed-spices",
        "sauce": "/food-additives",
    }

    def _get_category_url(self, query: str) -> str | None:
        q_lower = query.lower()
        for keyword, path in self.CATEGORY_MAP.items():
            if keyword in q_lower:
                return f"{self.base_url}{path}"
        return None

    async def scrape_search(self, query: str) -> list[dict]:
        """
        Naivas uses Livewire (Laravel SSR). We load category pages,
        click "Load More" to get all products, then extract.
        """
        cat_url = self._get_category_url(query)
        url_to_use = cat_url or f"{self.base_url}/search?term={query.replace(' ', '+')}"

        async with async_playwright() as p:
            browser = await self.get_browser(p)
            context = await self.get_context(browser)
            page = await context.new_page()
            try:
                await self.safe_goto(page, url_to_use, wait_until="commit", timeout=60000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    pass
                await asyncio.sleep(2)

                # Click "Load More" to get all products (up to 20 pages)
                await self._click_load_more(page, max_clicks=20)

                all_results = await self._extract_products(page)

                # Filter to products matching the query
                if cat_url:
                    q_lower = query.lower()
                    q_words = set(q_lower.split())
                    filtered = [
                        r for r in all_results
                        if any(word in r["normalized_name"] for word in q_words)
                        or q_lower in r["normalized_name"]
                    ]
                    return filtered if filtered else all_results
                return all_results

            except Exception as e:
                print(f"[Naivas] Search error for '{query}': {e}")
                return []
            finally:
                await browser.close()

    async def scrape_category(self, category_url: str) -> list[dict]:
        async with async_playwright() as p:
            browser = await self.get_browser(p)
            context = await self.get_context(browser)
            page = await context.new_page()
            try:
                await self.safe_goto(page, category_url, wait_until="commit", timeout=60000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    pass
                await asyncio.sleep(2)

                await self._click_load_more(page, max_clicks=20)

                return await self._extract_products(page)
            except Exception as e:
                print(f"[Naivas] Category error: {e}")
                return []
            finally:
                await browser.close()

    async def _click_load_more(self, page, max_clicks: int = 20) -> None:
        """Scroll to bottom and click 'Load More' repeatedly to load all products."""
        for _ in range(max_clicks):
            try:
                # Scroll to bottom to trigger any lazy-loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

                btn = page.locator("button:has-text('Load More')")
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)
                else:
                    break
            except Exception:
                break

    async def _extract_products(self, page) -> list[dict]:
        """
        Extract products from Naivas Livewire pages.
        Uses .product-price elements as anchors, walks up to the card container.
        """
        products = await page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();

                // Find all product-card-img containers (each is one product)
                const cards = document.querySelectorAll('.product-card-img');

                cards.forEach(imgContainer => {
                    try {
                        // Walk up to find the parent that also contains the price
                        let card = imgContainer;
                        for (let i = 0; i < 6; i++) {
                            card = card.parentElement;
                            if (!card) return;
                            if (card.querySelector('.product-price')) break;
                        }
                        if (!card || !card.querySelector('.product-price')) return;

                        // Name from link title attribute
                        const linkEl = card.querySelector('a[title]');
                        const name = linkEl ? linkEl.getAttribute('title') : null;
                        if (!name || seen.has(name)) return;
                        seen.add(name);

                        // Price
                        const priceEl = card.querySelector('.product-price');
                        const rawPrice = priceEl ? priceEl.innerText.trim() : '';
                        const priceMatches = rawPrice.match(/[\\d,]+(?:\\.[\\d]+)?/g);
                        const currentPrice = priceMatches ? priceMatches[0] : null;
                        const originalPrice = priceMatches && priceMatches.length > 1 &&
                            parseFloat(priceMatches[1].replace(',','')) > parseFloat(priceMatches[0].replace(',',''))
                            ? priceMatches[1] : null;

                        // Image
                        const imgEl = imgContainer.querySelector('img');
                        const image_url = imgEl ? (imgEl.src || imgEl.getAttribute('data-src')) : null;

                        // URL
                        const url = linkEl ? linkEl.href : null;

                        results.push({ name, currentPrice, originalPrice, image_url, url });
                    } catch (e) {}
                });

                return results;
            }
        """)

        cleaned = []
        for item in products:
            if not item.get("name"):
                continue
            price = clean_price(item.get("currentPrice") or "")
            orig = clean_price(item.get("originalPrice") or "")
            cleaned.append({
                "store": self.store_slug,
                "name": item["name"],
                "normalized_name": normalize_name(item["name"]),
                "current_price": price,
                "original_price": orig if orig and orig != price else None,
                "unit": None,
                "image_url": item.get("image_url"),
                "url": item.get("url"),
                "in_stock": True,
            })
        return cleaned
