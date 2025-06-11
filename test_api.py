import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from pymongo.database import Database

from api import app, get_db
from wool_pilot.models import Product, ProductMetaInformation, Price


sample_product_data = {
    "meta": {"id": "wool-001", "url": "https://example.com/wool-001"},
    "name": "Merino Wool Yarn",
    "price": {"amount": "15.99", "currency": "EUR"},
    "needle_size": "4mm",
    "composition": "100% Merino Wool",
    "availability": "In Stock",
}

sample_product = Product(
    meta=ProductMetaInformation(id="wool-001", url="https://example.com/wool-001"),
    name="Merino Wool Yarn",
    price=Price(amount="15.99", currency="EUR"),
    needle_size="4mm",
    composition="100% Merino Wool",
    availability="In Stock",
)

sample_product_data_2 = {
    "meta": {"id": "wool-002", "url": "https://example.com/wool-002"},
    "name": "Cotton Blend Yarn",
    "price": {"amount": "12.50", "currency": "EUR"},
    "needle_size": "3.5mm",
    "composition": "60% Cotton, 40% Acrylic",
    "availability": "Limited Stock",
}

sample_product_2 = Product(
    meta=ProductMetaInformation(id="wool-002", url="https://example.com/wool-002"),
    name="Cotton Blend Yarn",
    price=Price(amount="12.50", currency="EUR"),
    needle_size="3.5mm",
    composition="60% Cotton, 40% Acrylic",
    availability="Limited Stock",
)


class TestProductsAPI:
    """Test suite for the Products API"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        mock_db = Mock(spec=Database)
        mock_db.products = Mock()
        return mock_db

    @pytest.fixture(autouse=True)
    def override_db_dependency(self, mock_db):
        """Override the database dependency for all tests"""
        app.dependency_overrides[get_db] = lambda: mock_db
        yield
        app.dependency_overrides.clear()

    def test_health_check(self, client):
        """Test the health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "wool-pilot-api"}

    @patch("api.get_products")
    def test_get_all_products_success(self, mock_get_products, client):
        """Test successful retrieval of all products"""
        mock_get_products.return_value = [sample_product, sample_product_2]

        response = client.get("/products")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Merino Wool Yarn"
        assert data[1]["name"] == "Cotton Blend Yarn"

    @patch("api.get_products")
    def test_get_all_products_empty(self, mock_get_products, client):
        """Test retrieval when no products exist"""
        mock_get_products.return_value = None

        response = client.get("/products")

        assert response.status_code == 200
        assert response.json() == []

    @patch("api.get_products")
    def test_get_all_products_exception(self, mock_get_products, client):
        """Test handling of database exceptions when getting all products"""
        mock_get_products.side_effect = Exception("Database connection failed")

        response = client.get("/products")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_get_product_by_id_success(self, client, mock_db):
        """Test successful retrieval of product by ID"""
        mock_db.products.find_one.return_value = {
            **sample_product_data,
            "_id": "mock_object_id",
        }

        response = client.get("/products/wool-001")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Merino Wool Yarn"
        assert data["meta"]["id"] == "wool-001"
        assert data["price"]["amount"] == "15.99"
        mock_db.products.find_one.assert_called_once_with({"meta.id": "wool-001"})

    def test_get_product_by_id_not_found(self, client, mock_db):
        """Test product not found by ID"""
        mock_db.products.find_one.return_value = None

        response = client.get("/products/nonexistent-id")

        assert response.status_code == 404
        assert "Product with ID 'nonexistent-id' not found" in response.json()["detail"]

    def test_get_product_by_id_database_error(self, client, mock_db):
        """Test database error when getting product by ID"""
        mock_db.products.find_one.side_effect = Exception("Database error")

        response = client.get("/products/wool-001")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_get_product_by_name_success(self, client, mock_db):
        """Test successful retrieval of product by name"""
        mock_db.products.find_one.return_value = {
            **sample_product_data,
            "_id": "mock_object_id",
        }

        response = client.get("/products/name/Merino Wool Yarn")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Merino Wool Yarn"
        assert data["meta"]["id"] == "wool-001"

        # Verify case-insensitive regex query was used
        expected_query = {"name": {"$regex": "^Merino Wool Yarn$", "$options": "i"}}
        mock_db.products.find_one.assert_called_once_with(expected_query)

    def test_get_product_by_name_case_insensitive(self, client, mock_db):
        """Test case-insensitive name search"""
        mock_db.products.find_one.return_value = {
            **sample_product_data,
            "_id": "mock_object_id",
        }

        response = client.get("/products/name/merino wool yarn")  # lowercase

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Merino Wool Yarn"

        # Verify case-insensitive regex query
        expected_query = {"name": {"$regex": "^merino wool yarn$", "$options": "i"}}
        mock_db.products.find_one.assert_called_once_with(expected_query)

    def test_get_product_by_name_not_found(self, client, mock_db):
        """Test product not found by name"""
        # Arrange
        mock_db.products.find_one.return_value = None

        # Act
        response = client.get("/products/name/Nonexistent Product")

        # Assert
        assert response.status_code == 404
        assert (
            "Product with name 'Nonexistent Product' not found"
            in response.json()["detail"]
        )

    def test_get_product_by_name_database_error(self, client, mock_db):
        """Test database error when getting product by name"""
        mock_db.products.find_one.side_effect = Exception("Database error")

        response = client.get("/products/name/Some Product")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_product_reconstruction_with_optional_fields_none(self, client, mock_db):
        """Test product reconstruction when optional fields are None"""
        product_data_minimal = {
            "meta": {"id": "wool-003", "url": "https://example.com/wool-003"},
            "name": "Basic Yarn",
            "price": {"amount": "10.00", "currency": "EUR"},
            "needle_size": None,
            "composition": None,
            "availability": None,
            "_id": "mock_object_id",
        }
        mock_db.products.find_one.return_value = product_data_minimal

        response = client.get("/products/wool-003")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Basic Yarn"
        assert data["needle_size"] is None
        assert data["composition"] is None
        assert data["availability"] is None

    def test_product_reconstruction_missing_optional_fields(self, client, mock_db):
        """Test product reconstruction when optional fields are missing from database"""
        product_data_missing_fields = {
            "meta": {"id": "wool-004", "url": "https://example.com/wool-004"},
            "name": "Minimal Yarn",
            "price": {"amount": "8.00", "currency": "EUR"},
            "_id": "mock_object_id",
            # needle_size, composition, availability are missing
        }
        mock_db.products.find_one.return_value = product_data_missing_fields

        response = client.get("/products/wool-004")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal Yarn"
        assert data["needle_size"] is None
        assert data["composition"] is None
        assert data["availability"] is None

    def test_url_encoding_in_product_name(self, client, mock_db):
        """Test handling of URL-encoded characters in product names"""
        mock_db.products.find_one.return_value = {
            **sample_product_data,
            "_id": "mock_object_id",
        }

        response = client.get("/products/name/Merino%20Wool%20Yarn")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Merino Wool Yarn"
