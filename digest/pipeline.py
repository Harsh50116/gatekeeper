import asyncio
import logging
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from .main import run as run_scraper
from .store import get_all_users, get_user_items, get_previous_digest, save_digest
from .summarizer import build_user_digest, clear_cache
from .tts import generate_audio, cleanup_old_audio
from .storage import upload_audio, delete_audio
from .mailer import send_digest_email

logger = logging.getLogger(__name__)

APP_URL = os.environ.get("APP_URL", "http://localhost:8080")


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
        try:
            items = get_user_items(user["id"])
            if not items:
                logger.info("No items for %s, skipping", email)
                continue

            total_items = sum(len(v) for v in items.values())
            logger.info("  %d items across %d categories", total_items, len(items))

            previous = get_previous_digest(user["id"])
            digest_text = build_user_digest(items, previous)
            if not digest_text:
                logger.warning("  Empty digest for %s, skipping", email)
                continue

            save_digest(user["id"], digest_text)
            audio_path = generate_audio(digest_text, email)
            audio_url = upload_audio(audio_path)

            cats = ",".join(items.keys())
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
