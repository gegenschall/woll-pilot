import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from wool_pilot.scrapers import BaseScraper, WollplatzScraper
from wool_pilot.models import Product, ProductMetaInformation, Price


class TestBaseScraper:
    """Test cases for the BaseScraper base class"""

    @pytest.fixture
    def base_scraper(self):
        return BaseScraper("https://example.com", headless=True)

    def test_init(self, base_scraper):
        """Test BaseScraper initialization"""
        assert base_scraper.base_url == "https://example.com"
        assert base_scraper.headless is True
        assert base_scraper.browser is None
        assert base_scraper.page is None

    @pytest.mark.asyncio
    async def test_context_manager(self, base_scraper):
        """Test async context manager functionality"""
        with (
            patch.object(base_scraper, "start") as mock_start,
            patch.object(base_scraper, "close") as mock_close,
        ):
            async with base_scraper:
                mock_start.assert_called_once()

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_products_not_implemented(self, base_scraper):
        """Test that find_products raises NotImplementedError"""
        with pytest.raises(
            NotImplementedError, match="Subclasses must implement find_products method"
        ):
            await base_scraper.find_products("test")

    @pytest.mark.asyncio
    async def test_get_product_not_implemented(self, base_scraper):
        """Test that get_product raises NotImplementedError"""
        product_meta = ProductMetaInformation(
            id="123", url="https://example.com/product"
        )
        with pytest.raises(
            NotImplementedError,
            match="Subclasses must implement get_price_for_product method",
        ):
            await base_scraper.get_product(product_meta)


class TestWollplatzScraper:
    """Test cases for the WollplatzScraper implementation"""

    @pytest.fixture
    def scraper(self):
        return WollplatzScraper(headless=True)

    def test_init(self, scraper):
        """Test WollplatzScraper initialization"""
        assert scraper.base_url == "https://www.wollplatz.de"
        assert scraper.headless is True

    def test_build_search_url(self, scraper):
        """Test URL building for search terms"""
        # Test simple search term
        url = scraper._build_search_url("wool")
        expected = "https://www.wollplatz.de/?#sqr:(q%5Bwool%5D)"
        assert url == expected

        # Test search term with spaces
        url = scraper._build_search_url("DMC Natura XL")
        expected = "https://www.wollplatz.de/?#sqr:(q%5BDMC%20Natura%20XL%5D)"
        assert url == expected

        # Test search term with special characters
        url = scraper._build_search_url("wool & yarn")
        expected = "https://www.wollplatz.de/?#sqr:(q%5Bwool%20%26%20yarn%5D)"
        assert url == expected

    @pytest.mark.asyncio
    async def test_parse_product_from_element_success(self, scraper):
        """Test successful parsing of product element"""
        # Mock product element
        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(return_value="12345")

        # Mock title link
        mock_title_link = AsyncMock()
        mock_title_link.count = AsyncMock(return_value=1)
        mock_title_link.get_attribute = AsyncMock(
            side_effect=lambda attr: {
                "title": "Test Wool Product",
                "href": "/products/test-wool",
            }.get(attr)
        )

        mock_locator = AsyncMock()
        mock_locator.first = mock_title_link
        mock_element.locator = Mock(return_value=mock_locator)

        result = await scraper._parse_product_from_element(mock_element)

        assert result is not None
        assert result.id == "12345"
        assert result.url == "https://www.wollplatz.de/products/test-wool"

    @pytest.mark.asyncio
    async def test_parse_product_from_element_no_id(self, scraper):
        """Test parsing when product ID is missing"""
        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(return_value=None)

        result = await scraper._parse_product_from_element(mock_element)
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_product_from_element_no_title_link(self, scraper):
        """Test parsing when title link is missing"""
        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(return_value="12345")

        # Mock title link with count 0 (not found)
        mock_title_link = AsyncMock()
        mock_title_link.count = AsyncMock(return_value=0)

        mock_locator = AsyncMock()
        mock_locator.first = mock_title_link
        mock_element.locator = AsyncMock(return_value=mock_locator)

        result = await scraper._parse_product_from_element(mock_element)
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_details_table(self, scraper):
        """Test parsing of product details table"""
        # Mock table element and rows
        mock_row1 = AsyncMock()
        mock_row2 = AsyncMock()

        # Mock cells for row 1
        mock_cell1_1 = AsyncMock()
        mock_cell1_1.text_content = AsyncMock(return_value="Nadelstärke")
        mock_cell1_2 = AsyncMock()
        mock_cell1_2.text_content = AsyncMock(return_value="4-5 mm")

        mock_row1_locator = AsyncMock()
        mock_row1_locator.all = AsyncMock(return_value=[mock_cell1_1, mock_cell1_2])
        mock_row1.locator = Mock(return_value=mock_row1_locator)

        # Mock cells for row 2
        mock_cell2_1 = AsyncMock()
        mock_cell2_1.text_content = AsyncMock(return_value="Zusammenstellung")
        mock_cell2_2 = AsyncMock()
        mock_cell2_2.text_content = AsyncMock(return_value="100% Baumwolle")

        mock_row2_locator = AsyncMock()
        mock_row2_locator.all = AsyncMock(return_value=[mock_cell2_1, mock_cell2_2])
        mock_row2.locator = Mock(return_value=mock_row2_locator)

        mock_table_locator = Mock()
        mock_table_locator.all = AsyncMock(return_value=[mock_row1, mock_row2])
        mock_table = AsyncMock()
        mock_table.locator = Mock(return_value=mock_table_locator)

        result = await scraper._parse_details_table(mock_table)

        expected = {"Nadelstärke": "4-5 mm", "Zusammenstellung": "100% Baumwolle"}
        assert result == expected

    @pytest.mark.asyncio
    async def test_find_products_no_page(self, scraper):
        """Test find_products when page is not initialized"""
        with pytest.raises(RuntimeError, match="Scraper not initialized"):
            await scraper.find_products("test")

    @pytest.mark.asyncio
    async def test_find_products_success(self, scraper):
        """Test successful product finding"""
        # Mock page
        mock_page = AsyncMock()
        scraper.page = mock_page

        # Mock product containers
        mock_container1 = AsyncMock()
        mock_container2 = AsyncMock()

        mock_locator = AsyncMock()
        mock_locator.all = AsyncMock(return_value=[mock_container1, mock_container2])
        mock_page.locator = Mock(return_value=mock_locator)

        # Mock the parsing method
        expected_products = [
            ProductMetaInformation(id="1", url="https://www.wollplatz.de/product1"),
            ProductMetaInformation(id="2", url="https://www.wollplatz.de/product2"),
        ]

        with patch.object(scraper, "_parse_product_from_element") as mock_parse:
            mock_parse.side_effect = expected_products

            result = await scraper.find_products("test wool")

            assert len(result) == 2
            assert result == expected_products

            # Verify page interactions
            mock_page.goto.assert_called_once()
            mock_page.wait_for_selector.assert_called_once_with(
                "div.sooqrSearchContainer", timeout=10000
            )
            mock_page.wait_for_timeout.assert_called_once_with(2000)

    @pytest.mark.asyncio
    async def test_get_product_no_page(self, scraper):
        """Test get_product when page is not initialized"""
        product_meta = ProductMetaInformation(
            id="123", url="https://example.com/product"
        )

        with pytest.raises(RuntimeError, match="Scraper not initialized"):
            await scraper.get_product(product_meta)

    @pytest.mark.asyncio
    async def test_get_product_success(self, scraper):
        """Test successful product information retrieval"""
        # Mock page
        mock_page = AsyncMock()
        scraper.page = mock_page

        # Create mock locators for each element
        mock_title_locator = AsyncMock()
        mock_title_locator.text_content = AsyncMock(return_value="Test Wool Product")

        mock_price_locator = AsyncMock()
        mock_price_locator.get_attribute = AsyncMock(return_value="15.99")

        mock_availability_locator = AsyncMock()
        mock_availability_locator.text_content = AsyncMock(return_value="  In Stock  ")

        mock_details_locator = AsyncMock()

        # Mock page.locator to return appropriate mocks based on selector
        def mock_page_locator(selector):
            selector_map = {
                "h1#pageheadertitle": mock_title_locator,
                "span.product-price": mock_price_locator,
                "div#ContentPlaceHolder1_upStockInfoDescription": mock_availability_locator,
                "div#pdetailTableSpecs": mock_details_locator,
            }
            return selector_map.get(selector, AsyncMock())

        mock_page.locator = mock_page_locator

        # Mock details parsing
        expected_details = {
            "Nadelstärke": "4-5 mm",
            "Zusammenstellung": "100% Baumwolle",
        }

        with patch.object(
            scraper, "_parse_details_table", return_value=expected_details
        ):
            product_meta = ProductMetaInformation(
                id="123", url="https://www.wollplatz.de/product123"
            )

            result = await scraper.get_product(product_meta)

            assert isinstance(result, Product)
            assert result.meta == product_meta
            assert result.name == "Test Wool Product"
            assert result.price.amount == "15.99"
            assert result.price.currency == "EUR"
            assert result.needle_size == "4-5 mm"
            assert result.composition == "100% Baumwolle"
            assert result.availability == "In Stock"

    @pytest.mark.asyncio
    async def test_get_product_missing_required_fields(self, scraper):
        """Test get_product when required fields are missing"""
        mock_page = AsyncMock()
        scraper.page = mock_page

        # Create mock locators
        mock_title_locator = AsyncMock()
        mock_title_locator.text_content = AsyncMock(return_value=None)

        mock_price_locator = AsyncMock()
        mock_price_locator.get_attribute = AsyncMock(return_value="15.99")

        mock_availability_locator = AsyncMock()
        mock_availability_locator.text_content = AsyncMock(return_value="In Stock")

        mock_details_locator = AsyncMock()

        # Mock page.locator to return appropriate mocks based on selector
        def mock_page_locator(selector):
            selector_map = {
                "h1#pageheadertitle": mock_title_locator,
                "span.product-price": mock_price_locator,
                "div#ContentPlaceHolder1_upStockInfoDescription": mock_availability_locator,
                "div#pdetailTableSpecs": mock_details_locator,
            }
            return selector_map.get(selector, AsyncMock())

        mock_page.locator = mock_page_locator

        with patch.object(scraper, "_parse_details_table", return_value={}):
            product_meta = ProductMetaInformation(
                id="123", url="https://www.wollplatz.de/product123"
            )

            with pytest.raises(ValueError, match="Product name or price not found"):
                await scraper.get_product(product_meta)


class TestScraperIntegration:
    """Integration tests that can use provided HTML snippets"""

    @pytest.fixture
    def scraper_with_mock_page(self):
        """Create a scraper with a mocked page for HTML testing"""
        scraper = WollplatzScraper(headless=True)
        scraper.page = AsyncMock()
        return scraper

    def create_mock_element_from_html(self, html_content: str, selector_map: dict):
        """Helper to create mock elements that simulate HTML parsing"""
        mock_element = AsyncMock()

        # Configure the mock based on the selector map
        for selector, value in selector_map.items():
            if selector == "data-id":
                mock_element.get_attribute.return_value = value
            elif selector.startswith("locator:"):
                # Handle nested locators
                locator_selector = selector.replace("locator:", "")
                mock_locator = AsyncMock()

                if isinstance(value, dict):
                    # Handle complex locator responses
                    for method, result in value.items():
                        setattr(mock_locator, method, AsyncMock(return_value=result))
                else:
                    mock_locator.text_content.return_value = value

                mock_element.locator.return_value = mock_locator

        return mock_element

    @pytest.mark.asyncio
    async def test_parse_product_with_html_snippet(self, scraper_with_mock_page):
        """Test parsing with a realistic HTML structure"""
        # This test would use actual HTML snippets you provide
        # Example structure based on the scraper's expectations
        html_snippet = """
        <div class="sqr-resultItem" data-id="12345">
            <h3 class="productlist-title">
                <a href="/products/dmc-natura-xl" title="DMC Natura XL - Natural Cotton">
                    DMC Natura XL - Natural Cotton
                </a>
            </h3>
        </div>
        """

        # Configure the mock element properly
        mock_element = AsyncMock()
        mock_element.get_attribute = AsyncMock(return_value="12345")

        mock_title_link = AsyncMock()
        mock_title_link.count = AsyncMock(return_value=1)
        mock_title_link.get_attribute = AsyncMock(
            side_effect=lambda attr: {
                "title": "DMC Natura XL - Natural Cotton",
                "href": "/products/dmc-natura-xl",
            }.get(attr)
        )

        mock_locator = AsyncMock()
        mock_locator.first = mock_title_link
        mock_element.locator = Mock(return_value=mock_locator)

        result = await scraper_with_mock_page._parse_product_from_element(mock_element)

        assert result is not None
        assert result.id == "12345"
        assert result.url == "https://www.wollplatz.de/products/dmc-natura-xl"

    @pytest.mark.asyncio
    async def test_parse_details_table_with_html_snippet(self, scraper_with_mock_page):
        """Test parsing details table with realistic HTML"""
        # Example HTML structure for details table
        html_snippet = """
        <div id="pdetailTableSpecs">
            <table>
                <tr>
                    <td>Nadelstärke</td>
                    <td>4-5 mm</td>
                </tr>
                <tr>
                    <td>Zusammenstellung</td>
                    <td>100% Baumwolle</td>
                </tr>
                <tr>
                    <td>Lauflänge</td>
                    <td>85m / 100g</td>
                </tr>
            </table>
        </div>
        """

        # Mock table element with rows
        mock_row1 = AsyncMock()
        mock_cell1_1 = AsyncMock()
        mock_cell1_1.text_content = AsyncMock(return_value="Nadelstärke")
        mock_cell1_2 = AsyncMock()
        mock_cell1_2.text_content = AsyncMock(return_value="4-5 mm")

        mock_row1_locator = AsyncMock()
        mock_row1_locator.all = AsyncMock(return_value=[mock_cell1_1, mock_cell1_2])
        mock_row1.locator = Mock(return_value=mock_row1_locator)

        mock_row2 = AsyncMock()
        mock_cell2_1 = AsyncMock()
        mock_cell2_1.text_content = AsyncMock(return_value="Zusammenstellung")
        mock_cell2_2 = AsyncMock()
        mock_cell2_2.text_content = AsyncMock(return_value="100% Baumwolle")

        mock_row2_locator = AsyncMock()
        mock_row2_locator.all = AsyncMock(return_value=[mock_cell2_1, mock_cell2_2])
        mock_row2.locator = Mock(return_value=mock_row2_locator)

        mock_row3 = AsyncMock()
        mock_cell3_1 = AsyncMock()
        mock_cell3_1.text_content = AsyncMock(return_value="Lauflänge")
        mock_cell3_2 = AsyncMock()
        mock_cell3_2.text_content = AsyncMock(return_value="85m / 100g")

        mock_row3_locator = AsyncMock()
        mock_row3_locator.all = AsyncMock(return_value=[mock_cell3_1, mock_cell3_2])
        mock_row3.locator = Mock(return_value=mock_row3_locator)

        mock_table_locator = AsyncMock()
        mock_table_locator.all = AsyncMock(
            return_value=[mock_row1, mock_row2, mock_row3]
        )
        mock_table = AsyncMock()
        mock_table.locator = Mock(return_value=mock_table_locator)

        result = await scraper_with_mock_page._parse_details_table(mock_table)

        expected = {
            "Nadelstärke": "4-5 mm",
            "Zusammenstellung": "100% Baumwolle",
            "Lauflänge": "85m / 100g",
        }
        assert result == expected


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test data fixtures that can be used with HTML snippets
@pytest.fixture
def sample_product_list_html():
    """Sample HTML for product list page"""
    return """
    <div class="sooqrSearchContainer">
        <div class="sqr-resultItem" data-id="12345">
            <h3 class="productlist-title">
                <a href="/products/dmc-natura-xl-red" title="DMC Natura XL - Red">
                    DMC Natura XL - Red
                </a>
            </h3>
        </div>
        <div class="sqr-resultItem" data-id="12346">
            <h3 class="productlist-title">
                <a href="/products/dmc-natura-xl-blue" title="DMC Natura XL - Blue">
                    DMC Natura XL - Blue
                </a>
            </h3>
        </div>
    </div>
    """


@pytest.fixture
def sample_product_detail_html():
    """Sample HTML for product detail page"""
    return """
    <div class="product-detail">
        <h1 id="pageheadertitle">DMC Natura XL - Red</h1>
        <span class="product-price" content="8.95">€ 8,95</span>
        <div id="ContentPlaceHolder1_upStockInfoDescription">
            Sofort lieferbar
        </div>
        <div id="pdetailTableSpecs">
            <table>
                <tr>
                    <td>Nadelstärke</td>
                    <td>4-5 mm</td>
                </tr>
                <tr>
                    <td>Zusammenstellung</td>
                    <td>100% Baumwolle</td>
                </tr>
                <tr>
                    <td>Lauflänge</td>
                    <td>85m / 100g</td>
                </tr>
            </table>
        </div>
    </div>
    """
