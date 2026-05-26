import logging
import os

import httpx

logger = logging.getLogger(__name__)

BUCKET = "digests"


def _supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL", "")
    if not url:
        raise RuntimeError("SUPABASE_URL not set in environment")
    return url.rstrip("/")


def _supabase_key() -> str:
    key = os.environ.get("SUPABASE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_KEY not set in environment")
    return key


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_supabase_key()}",
        "apikey": _supabase_key(),
    }


def upload_audio(file_path: str) -> str:
    filename = os.path.basename(file_path)
    url = f"{_supabase_url()}/storage/v1/object/{BUCKET}/{filename}"

    with open(file_path, "rb") as f:
        resp = httpx.post(
            url,
            headers={**_headers(), "Content-Type": "audio/mpeg"},
            content=f.read(),
            timeout=60.0,
        )

    if resp.status_code == 400 and "Duplicate" in resp.text:
        resp = httpx.put(
            url,
            headers={**_headers(), "Content-Type": "audio/mpeg"},
            content=open(file_path, "rb").read(),
            timeout=60.0,
        )

    resp.raise_for_status()
    public_url = f"{_supabase_url()}/storage/v1/object/public/{BUCKET}/{filename}"
    logger.info("Uploaded to: %s", public_url)
    return public_url


def delete_audio(filename: str):
    url = f"{_supabase_url()}/storage/v1/object/{BUCKET}"
    resp = httpx.delete(
        url,
        headers=_headers(),
        json={"prefixes": [filename]},
        timeout=30.0,
    )
    resp.raise_for_status()
    logger.info("Deleted from storage: %s", filename)
