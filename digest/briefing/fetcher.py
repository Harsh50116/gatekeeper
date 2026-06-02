import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
import yfinance as yf

from .sources import ESPN_LEAGUES, MARKET_INDICES

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(15.0)
HN_TOP_LIMIT = 30


def _item_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _within_24h(dt: datetime) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return dt >= cutoff


def _parse_published(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, attr, None)
        if tp:
            try:
                from time import mktime
                dt = datetime.fromtimestamp(mktime(tp), tz=timezone.utc)
                return dt
            except (ValueError, OverflowError):
                continue
    return None


async def fetch_rss(client: httpx.AsyncClient, source_cfg: dict, category: str) -> list[dict]:
    url = source_cfg["url"]
    source = source_cfg["source"]
    try:
        resp = await client.get(url)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("RSS fetch failed for %s: %s", source, e)
        return []

    feed = feedparser.parse(resp.text)
    items = []
    fetched_at = _now_utc()

    for entry in feed.entries:
        title = getattr(entry, "title", None)
        link = getattr(entry, "link", None)
        if not title or not link:
            continue

        pub_dt = _parse_published(entry)
        if pub_dt is None:
            continue
        if not _within_24h(pub_dt):
            continue

        items.append({
            "id": _item_id(link),
            "category": category,
            "title": title.strip(),
            "summary": getattr(entry, "summary", None),
            "url": link,
            "published": pub_dt.isoformat(),
            "source": source,
            "fetched_at": fetched_at,
        })

    return items


async def fetch_hn(client: httpx.AsyncClient, category: str) -> list[dict]:
    try:
        resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        resp.raise_for_status()
        story_ids = resp.json()[:HN_TOP_LIMIT]
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("HN top stories fetch failed: %s", e)
        return []

    async def get_story(sid: int) -> dict | None:
        try:
            r = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError):
            return None

    stories = await asyncio.gather(*[get_story(sid) for sid in story_ids])
    items = []
    fetched_at = _now_utc()

    for story in stories:
        if not story or not story.get("title") or not story.get("url"):
            continue

        ts = story.get("time")
        if ts is None:
            continue
        pub_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if not _within_24h(pub_dt):
            continue

        items.append({
            "id": _item_id(story["url"]),
            "category": category,
            "title": story["title"],
            "summary": None,
            "url": story["url"],
            "published": pub_dt.isoformat(),
            "source": "hn",
            "fetched_at": fetched_at,
        })

    return items


async def fetch_espn_scores(client: httpx.AsyncClient, category: str) -> list[dict]:
    items = []
    fetched_at = _now_utc()

    for sport, league in ESPN_LEAGUES:
        url = f"http://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("ESPN scores fetch failed for %s/%s: %s", sport, league, e)
            continue

        for event in data.get("events", []):
            name = event.get("name")
            event_url = event.get("links", [{}])[0].get("href") if event.get("links") else None
            if not name or not event_url:
                continue

            date_str = event.get("date")
            if date_str is None:
                continue
            try:
                pub_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            if not _within_24h(pub_dt):
                continue

            status = event.get("status", {}).get("type", {}).get("shortDetail", "")
            title = f"{name} — {status}" if status else name

            items.append({
                "id": _item_id(event_url),
                "category": category,
                "title": title,
                "summary": None,
                "url": event_url,
                "published": pub_dt.isoformat(),
                "source": "espn_scores",
                "fetched_at": fetched_at,
            })

    return items


def fetch_yfinance(category: str) -> list[dict]:
    items = []
    fetched_at = _now_utc()

    for symbol in MARKET_INDICES:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) < 2:
                continue

            prev_close = hist["Close"].iloc[-2]
            last_close = hist["Close"].iloc[-1]
            pct_change = ((last_close - prev_close) / prev_close) * 100
            direction = "+" if pct_change >= 0 else ""

            title = f"{symbol}: {last_close:,.2f} ({direction}{pct_change:.2f}%)"
            fake_url = f"https://finance.yahoo.com/quote/{symbol}"

            items.append({
                "id": _item_id(fake_url + fetched_at[:10]),
                "category": category,
                "title": title,
                "summary": None,
                "url": fake_url,
                "published": fetched_at,
                "source": "yfinance",
                "fetched_at": fetched_at,
            })
        except Exception as e:
            logger.warning("yfinance fetch failed for %s: %s", symbol, e)

    return items


async def fetch_source(client: httpx.AsyncClient, source_cfg: dict, category: str) -> list[dict]:
    src_type = source_cfg["type"]

    if src_type == "rss":
        return await fetch_rss(client, source_cfg, category)
    elif src_type == "hn_api":
        return await fetch_hn(client, category)
    elif src_type == "espn_json":
        return await fetch_espn_scores(client, category)
    elif src_type == "yfinance":
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch_yfinance, category)
    else:
        logger.warning("Unknown source type: %s", src_type)
        return []
