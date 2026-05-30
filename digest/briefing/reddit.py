import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser
import httpx

from .sources import SUBREDDIT_MAP

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(15.0)
USER_AGENT = "GatekeeperDigest/1.0"
POSTS_PER_SUBREDDIT = 10
REQUEST_DELAY = 7


def _item_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _within_24h(dt: datetime) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return dt >= cutoff


async def fetch_subreddit(
    client: httpx.AsyncClient, subreddit: str, category: str, subcategory: str
) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/top.rss?t=day&limit={POSTS_PER_SUBREDDIT}"
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Reddit fetch failed for r/%s: %s", subreddit, e)
        return []

    feed = feedparser.parse(resp.text)
    items = []
    fetched_at = _now_utc()

    for entry in feed.entries:
        title = getattr(entry, "title", None)
        link = getattr(entry, "link", None)
        if not title or not link:
            continue

        pub_parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        if not pub_parsed:
            continue
        try:
            pub_dt = datetime.fromtimestamp(mktime(pub_parsed), tz=timezone.utc)
        except (ValueError, OverflowError):
            continue
        if not _within_24h(pub_dt):
            continue

        items.append({
            "id": _item_id(link),
            "subreddit": subreddit,
            "title": title.strip(),
            "body": None,
            "url": link,
            "category": category,
            "subcategory": subcategory,
            "published": pub_dt.isoformat(),
            "fetched_at": fetched_at,
        })

    return items


async def fetch_all() -> list[dict]:
    all_items = []
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for category, subs in SUBREDDIT_MAP.items():
            for subcategory, subreddits in subs.items():
                for subreddit in subreddits:
                    items = await fetch_subreddit(client, subreddit, category, subcategory)
                    all_items.extend(items)
                    logger.info("r/%s: fetched %d posts", subreddit, len(items))
                    await asyncio.sleep(REQUEST_DELAY)

    logger.info("Reddit fetch complete: %d total posts", len(all_items))
    return all_items
