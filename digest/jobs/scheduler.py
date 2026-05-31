import logging
import os

from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ..briefing.pipeline import run_pipeline

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

SCHEDULE_HOUR = int(os.environ.get("DIGEST_HOUR", "7"))
SCHEDULE_MINUTE = int(os.environ.get("DIGEST_MINUTE", "0"))


def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
        id="daily_digest",
        name="Daily Digest Pipeline",
        misfire_grace_time=3600,
    )

    logger.info("Scheduler started. Pipeline runs daily at %02d:%02d UTC.", SCHEDULE_HOUR, SCHEDULE_MINUTE)
    logger.info("No startup run — pipeline only fires on schedule. For a manual run, use: python -m digest.pipeline")
    scheduler.start()


if __name__ == "__main__":
    main()
