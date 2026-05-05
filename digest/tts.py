import logging
import os
from datetime import datetime, timezone

from gtts import gTTS

logger = logging.getLogger(__name__)

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")


def generate_audio(text: str, email: str) -> str:
    os.makedirs(AUDIO_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    safe_email = email.replace("@", "_at_").replace(".", "_")
    filename = f"{safe_email}_{date_str}.mp3"
    path = os.path.join(AUDIO_DIR, filename)

    tts = gTTS(text=text, lang="en")
    tts.save(path)
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
