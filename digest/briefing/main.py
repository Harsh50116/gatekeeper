import asyncio
import logging
import os
import time

import httpx
from groq import AsyncGroq

from .ratelimit import AsyncRateLimiter
from .sources import SOURCES
from ..db.store import insert_items
from .fetcher import fetch_source, TIMEOUT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Groq free tier (llama-3.3-70b-versatile): 30 RPM. Pace below it with margin.
GROQ_RPM = 28
GROQ_MAX_RETRIES = 6
MODEL = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
SKIP_CLASSIFY_SOURCES = {"espn_scores", "yfinance"}

CLASSIFY_SYSTEM = """You are a content classifier for a news digest. Given a news item title and summary, classify it as exactly one of:
- news: factual reporting of events, product launches, research papers, data releases
- announcement: official announcements, releases, updates from organizations
- skip: opinions, personal stories, discussions, editorials, self-promotion, listicles, advice

Respond with ONLY the label: news, announcement, or skip. No explanation."""


async def _classify_item(client: AsyncGroq, limiter: AsyncRateLimiter, item: dict) -> str:
    prompt = f"Title: {item['title']}"
    if item.get("summary"):
        prompt += f"\n\nSummary: {item['summary'][:500]}"

    await limiter.acquire()
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=16,
        )
        label = resp.choices[0].message.content.strip().lower()
        if label in ("news", "announcement", "skip"):
            return label
        return "skip"
    except Exception as e:
        logger.warning("RSS classification failed for '%s': %s", item["title"][:50], e)
        return "news"


async def classify_rss_items_by_type(items: list[dict]) -> list[dict]:
    to_classify = [it for it in items if it["source"] not in SKIP_CLASSIFY_SOURCES]
    passthrough = [it for it in items if it["source"] in SKIP_CLASSIFY_SOURCES]

    if not to_classify:
        return passthrough

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    limiter = AsyncRateLimiter(GROQ_RPM)
    async with AsyncGroq(api_key=GROQ_API_KEY, max_retries=GROQ_MAX_RETRIES) as client:
        labels = await asyncio.gather(*[
            _classify_item(client, limiter, item) for item in to_classify
        ])

    kept = list(passthrough)
    for item, label in zip(to_classify, labels):
        if label in ("news", "announcement"):
            kept.append(item)
        else:
            logger.debug("Skipping RSS [%s]: %s", label, item["title"][:60])

    logger.info("RSS classification: %d/%d items kept (%d passthrough)",
                len(kept) - len(passthrough), len(to_classify), len(passthrough))
    return kept


async def scrape_category(client: httpx.AsyncClient, category: str, sources: list[dict]) -> list[dict]:
    tasks = [fetch_source(client, src, category) for src in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Source %s failed: %s", sources[i]["source"], result)
            continue
        all_items.extend(result)

    logger.info("%-20s fetched=%d", category, len(all_items))
    return all_items


async def run():
    start = time.time()

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        tasks = [
            scrape_category(client, cat, sources)
            for cat, sources in SOURCES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for result in results:
        if isinstance(result, list):
            all_items.extend(result)

    kept = await classify_rss_items_by_type(all_items)
    inserted = insert_items(kept)

    elapsed = time.time() - start
    logger.info("Done. fetched=%d kept=%d inserted=%d in %.1fs",
                len(all_items), len(kept), inserted, elapsed)


if __name__ == "__main__":
    asyncio.run(run())
