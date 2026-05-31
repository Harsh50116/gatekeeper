import asyncio
import hashlib
import html
import logging
import os
import re
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
CLASSIFY_CONCURRENCY = 10

HYPERBOLIC_URL = "https://api.hyperbolic.xyz/v1/chat/completions"
MODEL = "meta-llama/Llama-3.3-70B-Instruct"

CLASSIFY_SYSTEM = """You are a content classifier for a news digest. Given a Reddit post title and body, classify it as exactly one of:
- news: factual reporting of events, product launches, research papers, data releases
- announcement: official announcements, releases, updates from organizations
- skip: opinions, personal stories, discussions, memes, self-promotion, questions, advice requests

Respond with ONLY the label: news, announcement, or skip. No explanation."""


def _item_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _within_24h(dt: datetime) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return dt >= cutoff


def _strip_html(raw: str) -> str:
    text = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    # Remove trailing "submitted by /u/... [link] [comments]"
    text = re.sub(r"\s*submitted by\s+/u/\S+.*$", "", text, flags=re.DOTALL)
    return text


def _api_key() -> str:
    key = os.environ.get("HYPERBOLIC_KEY", "")
    if not key:
        raise RuntimeError("HYPERBOLIC_KEY not set in environment")
    return key


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

        body = None
        content_list = getattr(entry, "content", None)
        if content_list and len(content_list) > 0:
            body = _strip_html(content_list[0].get("value", ""))
        if not body:
            raw_summary = getattr(entry, "summary", None)
            if raw_summary:
                body = _strip_html(raw_summary)

        items.append({
            "id": _item_id(link),
            "subreddit": subreddit,
            "title": title.strip(),
            "body": body or None,
            "url": link,
            "category": category,
            "subcategory": subcategory,
            "published": pub_dt.isoformat(),
            "fetched_at": fetched_at,
        })

    return items


async def _classify_post(client: httpx.AsyncClient, sem: asyncio.Semaphore, item: dict) -> str:
    prompt = f"Title: {item['title']}"
    if item.get("body"):
        prompt += f"\n\nBody: {item['body'][:500]}"

    async with sem:
        try:
            resp = await client.post(
                HYPERBOLIC_URL,
                headers={"Authorization": f"Bearer {_api_key()}"},
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": CLASSIFY_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 16,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            label = resp.json()["choices"][0]["message"]["content"].strip().lower()
            if label in ("news", "announcement", "skip"):
                return label
            return "skip"
        except Exception as e:
            logger.warning("Classification failed for '%s': %s", item["title"][:50], e)
            return "skip"


async def classify_reddit_posts(items: list[dict]) -> list[dict]:
    if not items:
        return []
    sem = asyncio.Semaphore(CLASSIFY_CONCURRENCY)
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        labels = await asyncio.gather(*[
            _classify_post(client, sem, item) for item in items
        ])
    kept = []
    for item, label in zip(items, labels):
        if label in ("news", "announcement"):
            kept.append(item)
        else:
            logger.debug("Skipping [%s]: %s", label, item["title"][:60])
    logger.info("Reddit classification: %d/%d posts kept", len(kept), len(items))
    return kept


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

    logger.info("Reddit fetch complete: %d total posts (pre-classification)", len(all_items))
    kept = await classify_reddit_posts(all_items)
    return kept
