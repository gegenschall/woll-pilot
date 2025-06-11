import dataclasses
import logging

from pymongo.database import Database
from wool_pilot.models import Product


logger = logging.getLogger(__name__)


def insert_product(db: Database, product: Product):
    try:
        product_dict = dataclasses.asdict(product)
        result = db.products.update_one(
            {"name": product.name},
            {"$set": product_dict},
            upsert=True,
        )

        logger.info("Upserted product: %s", product.name)

        return result.upserted_id
    except Exception:
        logger.exception("Failed inserting product into database")


def get_products(db: Database) -> list[Product] | None:
    try:
        product_data = db.products.find()
        if not product_data:
            return None

        products = []
        for product_dict in product_data:
            del product_dict["_id"]
            products.append(Product(**product_dict))

        return products
    except Exception:
        logger.exception("Failed fetching product from database")
        return None
