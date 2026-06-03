import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from .main import run as run_scraper
from .reddit import fetch_all as fetch_reddit
from .sources import CATEGORIES, SUBCATEGORIES
from ..db.store import (
    get_all_users, get_user_subcategories,
    get_previous_digest, save_digest, save_digest_run_inputs,
    insert_reddit_items, get_unclassified_items, update_item_subcategories,
    get_rss_items_by_subcategory, get_reddit_items_by_category,
)
from .summarizer import build_user_digest, classify_rss_items, clear_cache
from ..services.tts import generate_audio, cleanup_old_audio
from ..services.storage import upload_audio, delete_audio
from ..services.mailer import send_digest_email

logger = logging.getLogger(__name__)

APP_URL = os.environ.get("APP_URL", "http://localhost:8080")


def run_pipeline():
    start = time.time()
    logger.info("Pipeline started")

    logger.info("Step 1: Cleaning up old local audio")
    cleanup_old_audio()

    logger.info("Step 2a: Scraping RSS feeds")
    asyncio.run(run_scraper())

    logger.info("Step 2b: Scraping Reddit")
    reddit_raw = asyncio.run(fetch_reddit())
    reddit_inserted = insert_reddit_items(reddit_raw)
    logger.info("Reddit: fetched=%d inserted=%d", len(reddit_raw), reddit_inserted)

    logger.info("Step 2c: Classifying RSS items")
    for category in CATEGORIES:
        unclassified = get_unclassified_items(category)
        if unclassified:
            logger.info("  %s: %d unclassified items", category, len(unclassified))
            updates = classify_rss_items(category, unclassified)
            update_item_subcategories(updates)

    users = get_all_users()
    logger.info("Step 3: Processing %d users", len(users))

    results = []
    for user in users:
        email = user["email"]
        logger.info("Processing user: %s", email)
        try:
            user_subs = get_user_subcategories(user["id"])
            if not user_subs:
                user_subs = {
                    cat: [s["id"] for s in SUBCATEGORIES.get(cat, [])]
                    for cat in user["categories"]
                }

            logger.info("  %d categories, %d subcategories",
                        len(user_subs), sum(len(v) for v in user_subs.values()))

            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            snapshot_rss = []
            snapshot_reddit = []
            for cat, subs in user_subs.items():
                for sub in subs:
                    for r in get_rss_items_by_subcategory(cat, sub):
                        r["category"] = cat
                        r["subcategory"] = sub
                        snapshot_rss.append(r)
                    for r in get_reddit_items_by_category(cat, [sub], cutoff):
                        r["source"] = f"r/{r['subreddit']}"
                        snapshot_reddit.append(r)
            save_digest_run_inputs(user["id"], date_str, snapshot_rss, snapshot_reddit)

            previous = get_previous_digest(user["id"])
            digest_text = build_user_digest(user_subs, previous_digest=previous)
            if not digest_text:
                logger.warning("  Empty digest for %s, skipping", email)
                continue

            save_digest(user["id"], digest_text)
            audio_path = generate_audio(digest_text, email)
            audio_url = upload_audio(audio_path)

            cats = ",".join(user_subs.keys())
            player_url = f"{APP_URL}/play?audio={audio_url}&cats={cats}&user={user['id']}&date={date_str}"
            send_digest_email(email, player_url)

            results.append({"email": email, "url": player_url})
            logger.info("  Done: %s", player_url)
        except Exception:
            logger.exception("Failed to process user %s, continuing", email)

    clear_cache()

    elapsed = time.time() - start
    logger.info("Pipeline finished. %d digests generated in %.1fs", len(results), elapsed)
    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    run_pipeline()
