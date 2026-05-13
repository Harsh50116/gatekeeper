import asyncio
import logging
import time

import httpx

from .sources import SOURCES
from .store import insert_items
from .fetcher import fetch_source, TIMEOUT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def scrape_category(client: httpx.AsyncClient, category: str, sources: list[dict]) -> int:
    tasks = [fetch_source(client, src, category) for src in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Source %s failed: %s", sources[i]["source"], result)
            continue
        all_items.extend(result)

    inserted = insert_items(all_items)
    logger.info("%-20s fetched=%d inserted=%d", category, len(all_items), inserted)
    return inserted


async def run():
    start = time.time()

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        tasks = [
            scrape_category(client, cat, sources)
            for cat, sources in SOURCES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    total = sum(r for r in results if isinstance(r, int))
    elapsed = time.time() - start
    logger.info("Done. Total inserted: %d in %.1fs", total, elapsed)


if __name__ == "__main__":
    asyncio.run(run())
