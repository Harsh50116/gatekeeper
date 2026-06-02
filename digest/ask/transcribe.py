import logging
import os

from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = "whisper-large-v3-turbo"


def _get_client() -> Groq:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    return Groq(api_key=GROQ_API_KEY)


def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    client = _get_client()
    transcription = client.audio.transcriptions.create(
        model=MODEL,
        file=(filename, audio_bytes),
        language="en",
        temperature=0,
        response_format="verbose_json",
    )
    text = transcription.text.strip()
    logger.info("Transcribed: %s", text[:100])
    return text
