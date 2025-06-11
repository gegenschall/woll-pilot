import logging
import urllib.parse
from typing import List, Optional

from playwright.async_api import Browser, Page, async_playwright
from playwright_stealth import stealth_async

from wool_pilot.models import Price, Product, ProductMetaInformation

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base scraper class for e-commerce websites"""

    def __init__(self, base_url: str, headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def start(self):
        """Initialize the browser and page"""
        playwright = await async_playwright().start()
        # XXX: webkit and firefox seem to be the only ones that work using playwright-stealth
        self.browser = await playwright.webkit.launch(headless=self.headless)
        self.page = await self.browser.new_page()

        logger.info(
            f"Starting scraper for {self.base_url} with {self.browser.browser_type.name}"
        )

        await stealth_async(self.page)

    async def close(self):
        """Close the browser"""
        if self.browser:
            logger.info(f"Closing scraper for {self.base_url}")
            await self.browser.close()

    async def find_products(self, search_term: str) -> List[ProductMetaInformation]:
        """Find products based on search term"""
        raise NotImplementedError("Subclasses must implement find_products method")

    async def get_product(self, product: ProductMetaInformation) -> Product:
        """Get price for a specific product"""
        raise NotImplementedError(
            "Subclasses must implement get_price_for_product method"
        )


class WollplatzScraper(BaseScraper):
    """Scraper specifically for wollplatz.de using Playwright"""

    def __init__(self, headless: bool = True):
        super().__init__("https://www.wollplatz.de", headless)

    def _build_search_url(self, search_term: str) -> str:
        """Build the search URL for wollplatz.de"""
        # URL encode the search term
        encoded_term = urllib.parse.quote(search_term)
        # Build the search URL based on the pattern provided
        search_url = f"{self.base_url}/?#sqr:(q%5B{encoded_term}%5D)"
        return search_url

    async def _parse_product_from_element(
        self, product_element
    ) -> Optional[ProductMetaInformation]:
        try:
            # Extract product ID
            product_id = await product_element.get_attribute("data-id")
            if not product_id:
                return None

            # Extract product name and URL
            title_link = product_element.locator("h3.productlist-title a").first
            if await title_link.count() == 0:
                return None

            name = await title_link.get_attribute("title") or ""
            name = name.strip()
            relative_url = await title_link.get_attribute("href") or ""
            full_url = urllib.parse.urljoin(self.base_url, relative_url)

            return ProductMetaInformation(
                id=product_id,
                url=full_url,
            )

        except Exception:
            logger.exception("Error parsing product")
            return None

    async def _parse_details_table(self, table_element) -> dict:
        """Parse the details table for additional product information"""
        details = {}
        rows = await table_element.locator("tr").all()
        for row in rows:
            cells = await row.locator("td").all()
            if len(cells) == 2:
                key = await cells[0].text_content()
                value = await cells[1].text_content()
                if key and value:
                    details[key.strip()] = value.strip()
        return details

    async def find_products(self, search_term: str) -> List[ProductMetaInformation]:
        """Find products on wollplatz.de based on search term"""
        if not self.page:
            raise RuntimeError(
                "Scraper not initialized. Use async context manager or call start() first."
            )

        search_url = self._build_search_url(search_term)

        try:
            logger.info(f"Searching for products with term: {search_term}")

            await self.page.goto(search_url, wait_until="networkidle", timeout=30000)

            try:
                await self.page.wait_for_selector(
                    "div.sooqrSearchContainer", timeout=10000
                )
            except:
                # If no products found, the selector might not appear
                logger.error("Failed waiting for search results selector")
                raise

            # Wait a bit more for any dynamic content
            await self.page.wait_for_timeout(2000)

            product_containers = self.page.locator("div.sqr-resultItem")

            products = [
                await self._parse_product_from_element(container)
                for container in await product_containers.all()
            ]
            return [product for product in products if product is not None]

        except Exception:
            logger.exception("Error finding products")
            raise

    async def get_product(self, product: ProductMetaInformation) -> Product:
        if not self.page:
            raise RuntimeError(
                "Scraper not initialized. Use async context manager or call start() first."
            )

        try:
            logger.info(f"Fetching product info for {product.id}")

            await self.page.goto(product.url, wait_until="networkidle", timeout=30000)

            try:
                await self.page.wait_for_selector(
                    "div.pdetail-specsholder", timeout=10000
                )
            except:
                # If no products found, the selector might not appear
                logger.error("Failed waiting for search results selector")
                raise

            name = await self.page.locator("h1#pageheadertitle").text_content()
            price_amount = await self.page.locator("span.product-price").get_attribute(
                "content"
            )
            availability = await self.page.locator(
                "div#ContentPlaceHolder1_upStockInfoDescription"
            ).text_content()

            if not name or not price_amount:
                raise ValueError("Product name or price not found")

            details_table = self.page.locator("div#pdetailTableSpecs")
            details = await self._parse_details_table(details_table)

            return Product(
                meta=product,
                name=name,
                needle_size=details.get("Nadelstärke"),
                composition=details.get("Zusammenstellung"),
                availability=availability.strip() if availability else None,
                price=Price(
                    currency="EUR",  # TODO: this should be dynamically determined
                    amount=price_amount,
                ),
            )
        except Exception:
            logger.exception(f"Error handling product URL: {product.url}")
            raise
