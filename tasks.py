import os
import asyncio
import pymongo
from dotenv import load_dotenv
from celery import Celery

from wool_pilot.logger import setup_logging
from wool_pilot.database import insert_product
from wool_pilot.scrapers import WollplatzScraper
from wool_pilot.constants import MONGO_DEFAULT_DATABASE

setup_logging()
load_dotenv()

app = Celery("wool_pilot", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
app.conf.update(
    worker_hijack_root_logger=False,
)


@app.task(bind=True, max_retries=3, default_retry_delay=10)
def find_and_scrape_products(self, search_term):
    try:
        asyncio.run(_find_products_async(search_term))
    except Exception as exc:
        self.retry(exc=exc)


async def _find_products_async(search_term):
    client = pymongo.MongoClient(os.getenv("MONGO_URL", "mongodb://localhost:27017"))
    db = client[MONGO_DEFAULT_DATABASE]

    async with WollplatzScraper(headless=True) as scraper:
        products = await scraper.find_products(search_term)

    async with WollplatzScraper(headless=True) as scraper:
        for product in products:
            product_info = await scraper.get_product(product)
            insert_product(db, product_info)
