import asyncio
from playwright.async_api import async_playwright
from .base import BaseScraper, normalize_name, clean_price


class QuickmartScraper(BaseScraper):
    store_slug = "quickmart"
    store_name = "Quickmart"
    base_url = "https://www.quickmart.co.ke"

    # Nairobi CBD coordinates for the delivery location
    LOCATION = {"lat": "-1.2921", "lng": "36.8219", "address": "Nairobi CBD"}

    async def _set_location(self, page) -> None:
        """
        Quickmart requires a delivery location before showing products.
        The location modal (#locationInfoBox) auto-opens on load.
        We inject Nairobi CBD coordinates and call setupUserLocation() directly.
        """
        try:
            # Inject lat/lng into the modal form's hidden inputs
            await page.evaluate("""(loc) => {
                const form = document.getElementById("frmModalPopupUserLocation");
                if (!form) return;
                const latInput = form.querySelector("input[name=lat]");
                const lngInput = form.querySelector("input[name=lng]");
                const addrInput = form.querySelector("input[name=address]");
                if (latInput) latInput.value = loc.lat;
                if (lngInput) lngInput.value = loc.lng;
                if (addrInput) addrInput.value = loc.address;
            }""", self.LOCATION)

            # Call the site's own setupUserLocation handler (triggers navigation)
            try:
                async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                    await page.evaluate("""() => {
                        const form = document.getElementById("frmModalPopupUserLocation");
                        if (form && typeof setupUserLocation === "function") {
                            setupUserLocation(form, window.topHdrModalLocFrmObj || {}, "topHdrModalLocFrmObj");
                        }
                    }""")
            except Exception:
                pass  # Navigation might complete before we can wait for it

            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            await asyncio.sleep(1)

        except Exception as e:
            print(f"[Quickmart] Location setup: {e}")

    async def scrape_search(self, query: str) -> list[dict]:
        results = []
        async with async_playwright() as p:
            browser = await self.get_browser(p)
            context = await self.get_context(browser)
            page = await context.new_page()
            try:
                # Step 1: Load homepage to get the location modal and session
                await self.safe_goto(page, self.base_url)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await asyncio.sleep(2)

                # Step 2: Set location (Nairobi CBD)
                await self._set_location(page)

                # Step 3: Navigate to Quickmart's custom search endpoint
                # URL format: /products/search?keyword-{query}&pagesize-30
                keyword = query.replace(" ", "+")
                search_url = f"{self.base_url}/products/search?keyword-{keyword}&pagesize-30"
                await self.safe_goto(page, search_url)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(2)
                results = await self._extract_products(page)

            except Exception as e:
                print(f"[Quickmart] Search error for '{query}': {e}")
            finally:
                await browser.close()
        return results

    async def scrape_category(self, category_url: str) -> list[dict]:
        results = []
        async with async_playwright() as p:
            browser = await self.get_browser(p)
            context = await self.get_context(browser)
            page = await context.new_page()
            try:
                await self.safe_goto(page, self.base_url)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await asyncio.sleep(2)
                await self._set_location(page)
                await self.safe_goto(page, category_url)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(2)
                results = await self._extract_products(page)
            except Exception as e:
                print(f"[Quickmart] Category error: {e}")
            finally:
                await browser.close()
        return results

    async def _extract_products(self, page) -> list[dict]:
        """
        Quickmart uses a custom (non-WooCommerce) frontend.
        Real selectors discovered via debug:
        - Product card: .productInfoJs
        - Name: .products-title
        - Current price: .products-price-new
        - Original price: .products-price-old
        - Image: img inside .products-img
        - Link: a in .products-action or first <a> in card
        """
        products = await page.evaluate("""
            () => {
                const results = [];
                const cards = Array.from(document.querySelectorAll(".productInfoJs"));

                cards.forEach(card => {
                    try {
                        const nameEl = card.querySelector(".products-title, h2, h3");
                        const name = nameEl ? nameEl.innerText.trim() : null;
                        if (!name || name.length < 2) return;

                        const priceNewEl = card.querySelector(".products-price-new");
                        const priceOldEl = card.querySelector(".products-price-old");
                        const priceText = priceNewEl ? priceNewEl.innerText.trim() : null;
                        const origText = priceOldEl ? priceOldEl.innerText.trim() : null;

                        const imgEl = card.querySelector("img");
                        const image_url = imgEl ? (imgEl.src || imgEl.getAttribute("data-src") || imgEl.getAttribute("data-lazy-src")) : null;

                        const linkEl = card.querySelector("a");
                        const url = linkEl ? linkEl.href : null;

                        results.push({ name, priceText, origText, image_url, url });
                    } catch (e) {}
                });

                return results;
            }
        """)
        cleaned = []
        for item in products:
            if not item.get("name"):
                continue
            price = clean_price(item.get("priceText") or "")
            orig = clean_price(item.get("origText") or "")
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
