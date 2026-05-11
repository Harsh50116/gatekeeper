import base64
import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

HYPERBOLIC_CHAT_URL = "https://api.hyperbolic.xyz/v1/chat/completions"
HYPERBOLIC_IMAGE_URL = "https://api.hyperbolic.xyz/v1/image/generation"
CHAT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
IMAGE_MODEL = "FLUX.1-dev"

PROMPT_SYSTEM = """You write image-generation prompts. Given today's news themes, \
write ONE prompt (under 60 words) for an abstract editorial cover image. \
Style: muted earth tones, painterly, warm rust accent, no text, no faces, no logos. \
Evoke mood, not literal scenes."""

BUCKET = "digests"


def _api_key() -> str:
    key = os.environ.get("HYPERBOLIC_KEY", "")
    if not key:
        raise RuntimeError("HYPERBOLIC_KEY not set in environment")
    return key


def _supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", "").rstrip("/")


def _supabase_key() -> str:
    return os.environ.get("SUPABASE_KEY", "")


def _check_cover_exists(date_str: str) -> str | None:
    url = f"{_supabase_url()}/storage/v1/object/public/{BUCKET}/covers/{date_str}.png"
    resp = httpx.head(url, timeout=10.0)
    if resp.status_code == 200:
        return url
    return None


def _build_image_prompt(category_summaries: dict[str, str]) -> str:
    combined = "\n".join(f"{cat}: {summary[:200]}" for cat, summary in category_summaries.items() if summary)

    resp = httpx.post(
        HYPERBOLIC_CHAT_URL,
        headers={"Authorization": f"Bearer {_api_key()}"},
        json={
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": PROMPT_SYSTEM},
                {"role": "user", "content": f"Today's news themes:\n\n{combined}"},
            ],
            "temperature": 0.7,
            "max_tokens": 150,
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _generate_image(prompt: str) -> bytes:
    resp = httpx.post(
        HYPERBOLIC_IMAGE_URL,
        headers={"Authorization": f"Bearer {_api_key()}"},
        json={
            "model_name": IMAGE_MODEL,
            "prompt": prompt,
            "height": 1024,
            "width": 1024,
            "steps": "25",
            "cfg_scale": "5",
            "backend": "auto",
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    b64_data = resp.json()["images"][0]["image"]
    return base64.b64decode(b64_data)


def _upload_cover(image_data: bytes, date_str: str) -> str:
    filename = f"covers/{date_str}.png"
    url = f"{_supabase_url()}/storage/v1/object/{BUCKET}/{filename}"

    headers = {
        "Authorization": f"Bearer {_supabase_key()}",
        "apikey": _supabase_key(),
        "Content-Type": "image/png",
    }

    resp = httpx.post(url, headers=headers, content=image_data, timeout=60.0)

    if resp.status_code == 400 and "Duplicate" in resp.text:
        resp = httpx.put(url, headers=headers, content=image_data, timeout=60.0)

    resp.raise_for_status()
    public_url = f"{_supabase_url()}/storage/v1/object/public/{BUCKET}/{filename}"
    logger.info("Cover uploaded: %s", public_url)
    return public_url


def generate_daily_cover(category_summaries: dict[str, str]) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    existing = _check_cover_exists(date_str)
    if existing:
        logger.info("Cover already exists for %s, skipping generation", date_str)
        return existing

    try:
        image_prompt = _build_image_prompt(category_summaries)
        logger.info("Image prompt: %s", image_prompt)

        image_data = _generate_image(image_prompt)
        cover_url = _upload_cover(image_data, date_str)
        return cover_url
    except Exception:
        logger.exception("Cover generation failed, using placeholder")
        return ""
