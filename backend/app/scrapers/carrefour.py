import httpx
from .base import BaseScraper, normalize_name, clean_price


class CarrefourScraper(BaseScraper):
    store_slug = "carrefour"
    store_name = "Carrefour"
    base_url = "https://www.carrefour.ke"

    SEARCH_API = "https://www.carrefour.ke/api/v8/search"

    # MAF (Majid Al Futtaim) platform headers — reverse-engineered from browser
    MAF_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en",
        "appid": "Reactweb",
        "channel": "c4online",
        "currency": "KES",
        "env": "prod",
        "lang": "en",
        "langcode": "en",
        "latitude": "-1.2672236834605626",
        "longitude": "36.810586556760555",
        "posinfo": "express=KE4_Zone01,food=684_Zone01,nonfood=681_Zone01",
        "producttype": "ANY",
        "servicetypes": "SLOTTED|DEFAULT|MKP_GLOBAL",
        "storeid": "mafken",
        "userid": "anonymous",
        "x-maf-account": "carrefour",
        "x-maf-env": "prod",
        "x-maf-revamp": "true",
        "x-maf-tenant": "mafretail",
        "x-requested-with": "XMLHttpRequest",
        "hashedemail": "KU3jVX2dALPS2KHmqrAozw==",
        "Referer": "https://www.carrefour.ke/mafken/en/",
        "Origin": "https://www.carrefour.ke",
    }

    _client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create a reusable httpx client with seeded Akamai cookies."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                headers=self.MAF_HEADERS,
                timeout=20,
                follow_redirects=True,
                http2=False,
            )
            self._seed_cookies()
        return self._client

    def _seed_cookies(self):
        """Hit homepage to get Akamai session cookies (cart_api, bm_sv)."""
        self._client.get(f"{self.base_url}/mafken/en/")

    def _api_get(self, params: dict) -> dict | None:
        """Make an API call with one retry on cookie failure."""
        client = self._get_client()
        for attempt in range(2):
            resp = client.get(self.SEARCH_API, params=params)
            if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
                return resp.json()
            # Cookie expired — reseed and retry
            if attempt == 0:
                self._seed_cookies()
        return None

    async def scrape_search(self, query: str) -> list[dict]:
        """
        Hit the MAF v8/search API directly via httpx.
        No Playwright needed — just seed cookies and call the JSON API.
        """
        try:
            data = self._api_get({
                "keyword": query,
                "lang": "en",
                "sortBy": "relevance",
                "currentPage": "0",
                "pageSize": "40",
            })
            if not data:
                print(f"[Carrefour] API failed for '{query}'")
                return []
            return self._parse_api_response(data)
        except Exception as e:
            print(f"[Carrefour] Search error for '{query}': {e}")
            return []

    async def scrape_category(self, category_url: str) -> list[dict]:
        """
        Scrape a category by extracting the category ID from the URL
        and calling the MAF search API with a category filter.
        """
        try:
            cat_id = None
            for segment in category_url.strip("/").split("/"):
                if segment.startswith("FKEN") or segment.startswith("NFKEN"):
                    cat_id = segment
                    break

            if not cat_id:
                print(f"[Carrefour] Could not extract category ID from: {category_url}")
                return []

            data = self._api_get({
                "keyword": "",
                "lang": "en",
                "sortBy": "relevance",
                "currentPage": "0",
                "pageSize": "60",
                "filter": f"categories:{cat_id}",
            })
            if not data:
                print(f"[Carrefour] Category API failed")
                return []
            return self._parse_api_response(data)
        except Exception as e:
            print(f"[Carrefour] Category error: {e}")
            return []

    def _parse_api_response(self, data: dict) -> list[dict]:
        """Parse MAF v8/search JSON into normalized product dicts."""
        cleaned = []
        products = data.get("products") or []

        for item in products:
            try:
                name = item.get("name", "")
                if not name:
                    continue

                # Price: {"price": {"price": 169, "currency": "KES", "formattedValue": "KES169.00"}}
                price_obj = item.get("price") or {}
                price = price_obj.get("price")
                if price is None:
                    price = clean_price(price_obj.get("formattedValue", ""))

                # Original/was price (shown on discounted items)
                was_obj = item.get("wasPrice") or item.get("originalPrice") or {}
                orig = was_obj.get("price")
                if orig is None and was_obj:
                    orig = clean_price(was_obj.get("formattedValue", ""))

                # Image URL from links.images or links.defaultImages
                image_url = None
                links = item.get("links") or {}
                default_images = links.get("defaultImages") or []
                if default_images:
                    image_url = default_images[0]
                else:
                    link_images = links.get("images") or []
                    if link_images:
                        image_url = link_images[0].get("href")

                # Product URL from links.productUrl.href
                product_url = None
                product_url_obj = links.get("productUrl") or {}
                href = product_url_obj.get("href", "")
                if href:
                    product_url = f"{self.base_url}{href}" if not href.startswith("http") else href

                # Stock status
                avail = item.get("availability") or {}
                stock = item.get("stock") or {}
                in_stock = avail.get("isAvailable", True) and stock.get("stockLevelStatus") != "outOfStock"

                # Unit/size
                unit = item.get("size") or (item.get("unit") or {}).get("size")

                cleaned.append({
                    "store": self.store_slug,
                    "name": name,
                    "normalized_name": normalize_name(name),
                    "current_price": float(price) if price is not None else None,
                    "original_price": float(orig) if orig and orig != price else None,
                    "unit": unit,
                    "image_url": image_url,
                    "url": product_url,
                    "in_stock": in_stock,
                })
            except Exception:
                continue

        return cleaned
