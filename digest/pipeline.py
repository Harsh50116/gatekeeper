import asyncio
import logging
import os
import time

from dotenv import load_dotenv
load_dotenv()

from .main import run as run_scraper
from .store import get_all_users, get_user_items, get_all_recent_items
from .summarizer import build_user_digest, summarize_category, clear_cache
from .tts import generate_audio, cleanup_old_audio
from .storage import upload_audio, delete_audio
from .mailer import send_digest_email
from .image_gen import generate_daily_cover

logger = logging.getLogger(__name__)

APP_URL = os.environ.get("APP_URL", "http://localhost:8080")


def run_pipeline():
    start = time.time()
    logger.info("Pipeline started")

    logger.info("Step 1: Cleaning up old local audio")
    cleanup_old_audio()

    logger.info("Step 2: Scraping fresh data")
    asyncio.run(run_scraper())

    logger.info("Step 3: Generating daily cover image")
    all_items = get_all_recent_items()
    category_summaries = {}
    for cat, items in all_items.items():
        category_summaries[cat] = summarize_category(cat, items)
    cover_url = generate_daily_cover(category_summaries)
    logger.info("Cover URL: %s", cover_url or "(none)")

    users = get_all_users()
    logger.info("Step 4: Processing %d users", len(users))

    results = []
    for user in users:
        email = user["email"]
        logger.info("Processing user: %s", email)

        items = get_user_items(user["id"])
        if not items:
            logger.info("No items for %s, skipping", email)
            continue

        total_items = sum(len(v) for v in items.values())
        logger.info("  %d items across %d categories", total_items, len(items))

        digest_text = build_user_digest(items)
        if not digest_text:
            logger.warning("  Empty digest for %s, skipping", email)
            continue

        audio_path = generate_audio(digest_text, email)
        audio_url = upload_audio(audio_path)

        cats = ",".join(items.keys())
        player_url = f"{APP_URL}/play?audio={audio_url}&cats={cats}&cover={cover_url}"
        send_digest_email(email, player_url)

        results.append({"email": email, "url": player_url})
        logger.info("  Done: %s", player_url)

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
