# WOLL-PILOT

> The wool pricing software tailored to jumper manufacturers

This project is part of a coding challenge for MARKT-PILOT. It consists of three parts:

1. A scraper implementation in [scraper implementation for wollplatz.de](wool_pilot/scrapers.py) utilizing Playwright and [playwright-stealth](https://pypi.org/project/playwright-stealth/) to circumvent bot detection.
2. A [task runner](tasks.py) using Celery that handles automatic resource management for scheduled scraping tasks.
3. A [simple REST API](api.py) built with FastAPI that provides endpoints to retrieve the scraped data.

## Requirements

- Docker & Docker Compose
- (Optional) Python 3.13+ for local development
- (Optional) [uv](https://docs.astral.sh/uv/)

## Installation

These steps assume that you're using the containerized version of the project. If you want to run it without a Docker container you may have to set environment variables accordingly.

OS X & Linux:

```sh
docker compose build
docker compose up
```

To run the tests simply run:

```sh
uv run pytest
```

The above command assumes a working Python environment and [uv](https://docs.astral.sh/uv/) on your machine.

## Usage example

To actually trigger the Celery task that starts the scraping process run the following command. Please note that this is not run within the Docker container but locally. It assumes that all containers are running correctly and that it can connect to Redis on port 6379, forwarded from the container.

```sh
uv run main.py
```

The above command will trigger as many scraping tasks as there are search terms defined in `main.py`.
All tasks will be executed in parallel.
Tasks occasionally fail due to the bot detection mechanism of the website in which case Celery will try to rerun the affected tasks at most 3 times with a constant back off interval of 10 seconds.

Results of scrapes will be upserted into a MongoDB with the name of the wool type as the filter criterion. To retrieve data stored in the database you can utilize one of these REST endpoints:

- `GET /products`
- `GET /products/:id`, where `id` is the product id from wollplatz's PDP for each product
- `GET /product/:name` which should retrieve a product by name.

Here's an exemplary response from the `GET /products` endpoint:

```json
[
    {
        "availability": "Auf Lager – Versand innerhalb von 24 Stunden",
        "composition": "100% Baumwolle",
        "meta": {
            "id": "4647",
            "url": "https://www.wollplatz.de/wolle/drops/drops-safran"
        },
        "name": "Drops Safran 001 Wüstenrose",
        "needle_size": "3 mm",
        "price": {
            "amount": "1.55",
            "currency": "EUR"
        }
    },
    // --- snip ---
    {
        "availability": "Auf Lager – Versand innerhalb von 24 Stunden",
        "composition": "100% Acryl",
        "meta": {
            "id": "18098",
            "url": "https://www.wollplatz.de/wolle/stylecraft/stylecraft-special-dk"
        },
        "name": "Stylecraft Special dk 1001 White",
        "needle_size": "4 mm",
        "price": {
            "amount": "3.25",
            "currency": "EUR"
        }
    }
]
```

## Notes

- It took me a little while to figure out how to overcome the bot protection and it is still not perfect. `playwright-stealth` works great until it doesn't in which case the only solution with this code base is to re-run a scraping task and hope that CF looks the other way.
  I'm sure there are other options that work better but in the interest of time I settled on the above solution.

- Concerning performance, there's likely a lot of room for improvement but premature optimization and such... Currently, Playwright runs the whole show which is retrieving piloting the browser, retrieving and parsing HTML and being used as a DOM selector library.
  There are better tools available for some of these steps (e.g. lxml with beautifulsoup, requests for pulling HTML, etc). One notable optimization could be to minimize the amount of browser-based scraping, e.g:

    1. Use Playwright to successfully load the target page once, s.t. the client's cookie jar contains a `cf_clearance` cookie
    2. Use sooqr's API directly to fetch results of product searches, i.e. PLP content
    3. To scrape individual PDPs, use the `cf_clearance` cookie with `requests`, fetch the HTML, parse it using `lxml`

- The task sheet asks for abstraction of the parser in a way that would allow it to be extended and adapted to other yarn websites. I created a `BaseScraper` and the concrete implementation `WollplatzScraper` to handle the specific use case. I opted to not create a deeper level of abstraction since it's very much unclear if there ever will be more yarn ecommerce stores, how they can be scraped, what their data model would be etc. I believe that it is better to keep abstractions simple initially (YAGNI!) and expand on them once use cases and requirements are clearer. Otherwise one usually ends up with a lot of unused and dead code, i.e. tech debt from the start.

- Code organization is intentionally kept simple, i.e. similar things are kept in the same Python file. In a real world project this might not be the best approach and one should opt for better modularization. Additionally, the project root should not contain application code however I wanted to remove the need to start fiddling with `PYTHONPATH`.

- With the foundation of Celery, it should be relatively straight forward to scale the project to multiple workers that run off the same Docker image. With more workers there might potentially be concurrency problems that I have not tested for.

- When building the Docker images, playwright downloads browsers. This process is sometimes extremely slow (several minutes). It looks like there's [no good solution](https://github.com/microsoft/playwright/issues/26607) to this problem. The only way to workaround it is to Ctrl+C and restart the image building.

- There's no security whatsoever, especially MongoDB and the REST API provide no authentication or authorization.

## Meta

Max Liebkies – <hi@gegenschall.com>
