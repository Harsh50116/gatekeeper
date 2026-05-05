import asyncio
import logging
import time

from .main import run as run_scraper
from .store import get_all_users, get_user_items
from .summarizer import build_user_digest, clear_cache
from .tts import generate_audio, cleanup_old_audio
from .storage import upload_audio, delete_audio

logger = logging.getLogger(__name__)


def run_pipeline():
    start = time.time()
    logger.info("Pipeline started")

    logger.info("Step 1: Cleaning up old local audio")
    cleanup_old_audio()

    logger.info("Step 2: Scraping fresh data")
    asyncio.run(run_scraper())

    users = get_all_users()
    logger.info("Step 3: Processing %d users", len(users))

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
        public_url = upload_audio(audio_path)

        results.append({"email": email, "url": public_url})
        logger.info("  Done: %s", public_url)

    clear_cache()

    elapsed = time.time() - start
    logger.info("Pipeline finished. %d digests generated in %.1fs", len(results), elapsed)
    return results
