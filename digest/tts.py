import asyncio
import logging
import os
from datetime import datetime, timezone

import edge_tts

logger = logging.getLogger(__name__)

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
VOICE = os.environ.get("TTS_VOICE", "en-US-GuyNeural")
RATE = os.environ.get("TTS_RATE", "+0%")


async def _generate(text: str, path: str):
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(path)


def generate_audio(text: str, email: str) -> str:
    os.makedirs(AUDIO_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    safe_email = email.replace("@", "_at_").replace(".", "_")
    filename = f"{safe_email}_{date_str}.mp3"
    path = os.path.join(AUDIO_DIR, filename)

    asyncio.run(_generate(text, path))
    logger.info("Audio saved: %s", path)
    return path


def cleanup_old_audio(keep_date: str | None = None):
    if keep_date is None:
        keep_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not os.path.exists(AUDIO_DIR):
        return

    for f in os.listdir(AUDIO_DIR):
        if f.endswith(".mp3") and keep_date not in f:
            filepath = os.path.join(AUDIO_DIR, f)
            os.remove(filepath)
            logger.info("Deleted old audio: %s", filepath)
