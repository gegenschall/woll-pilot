from fastapi import FastAPI, HTTPException, Depends
from pymongo import MongoClient
from pymongo.database import Database
import logging
import os
from typing import List

from wool_pilot.constants import MONGO_DEFAULT_DATABASE
from wool_pilot.models import Product, ProductMetaInformation, Price
from wool_pilot.database import get_products
from wool_pilot.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wool Pilot Products API",
    description="REST API for managing wool products",
    version="0.1.0",
)


# Database connection
def get_database() -> Database:
    """Get MongoDB database connection"""
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")

    client = MongoClient(mongo_url)
    return client[MONGO_DEFAULT_DATABASE]


def get_db():
    """Dependency to inject database connection"""
    return get_database()


@app.get("/products", response_model=List[Product])
async def get_all_products(db: Database = Depends(get_db)):
    """
    Get all products from the database

    Returns:
        List[Product]: List of all products
    """
    try:
        products = get_products(db)
        if products is None:
            return []
        return products
    except Exception:
        logger.exception("Error fetching all products")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/products/{product_id}", response_model=Product)
async def get_product_by_id(product_id: str, db: Database = Depends(get_db)):
    """
    Get a specific product by its ID

    Args:
        product_id (str): The product ID to search for

    Returns:
        Product: The product with the specified ID

    Raises:
        HTTPException: 404 if product not found
    """
    try:
        product_data = db.products.find_one({"meta.id": product_id})

        if not product_data:
            raise HTTPException(
                status_code=404, detail=f"Product with ID '{product_id}' not found"
            )

        # Remove MongoDB's _id field before creating Product object
        del product_data["_id"]

        # Reconstruct the Product object
        product = Product(
            meta=ProductMetaInformation(**product_data["meta"]),
            name=product_data["name"],
            price=Price(**product_data["price"]),
            needle_size=product_data.get("needle_size"),
            composition=product_data.get("composition"),
            availability=product_data.get("availability"),
        )

        return product

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching product by ID: %s", product_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/products/name/{product_name}", response_model=Product)
async def get_product_by_name(product_name: str, db: Database = Depends(get_db)):
    """
    Get a specific product by its name

    Args:
        product_name (str): The product name to search for

    Returns:
        Product: The product with the specified name

    Raises:
        HTTPException: 404 if product not found
    """
    try:
        # Use case-insensitive search for better user experience
        product_data = db.products.find_one(
            {"name": {"$regex": f"^{product_name}$", "$options": "i"}}
        )

        if not product_data:
            raise HTTPException(
                status_code=404, detail=f"Product with name '{product_name}' not found"
            )

        # Remove MongoDB's _id field before creating Product object
        del product_data["_id"]

        # Reconstruct the Product object
        product = Product(
            meta=ProductMetaInformation(**product_data["meta"]),
            name=product_data["name"],
            price=Price(**product_data["price"]),
            needle_size=product_data.get("needle_size"),
            composition=product_data.get("composition"),
            availability=product_data.get("availability"),
        )

        return product

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching product by name: %s", product_name)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        dict: Health status
    """
    return {"status": "healthy", "service": "wool-pilot-api"}
