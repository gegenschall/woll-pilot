from dotenv import load_dotenv

from tasks import find_and_scrape_products
from wool_pilot.logger import setup_logging


load_dotenv()
setup_logging()

DEFAULT_SEARCH_TERMS = [
    "DMC Natura XL",
    "Drops Safran",
    "Drops Baby Merino Mix",
    "Hahn Alpacca Speciale",
    "Stylecraft Special double knit",
]


def main():
    [find_and_scrape_products.delay(term) for term in DEFAULT_SEARCH_TERMS]


if __name__ == "__main__":
    main()
