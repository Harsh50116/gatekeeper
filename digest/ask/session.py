import json
import logging
import os
import secrets

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL = int(os.environ.get("SESSION_TTL", "1800"))  # 30 minutes

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


def create_session(digest_text: str) -> str:
    session_id = secrets.token_urlsafe(16)
    data = {
        "digest": digest_text,
        "older_summary": "",
        "recent_turns": [],
    }
    r = _get_redis()
    r.setex(_session_key(session_id), SESSION_TTL, json.dumps(data))
    logger.info("Session created: %s", session_id)
    return session_id


def get_session(session_id: str) -> dict | None:
    r = _get_redis()
    raw = r.get(_session_key(session_id))
    if raw is None:
        return None
    r.expire(_session_key(session_id), SESSION_TTL)
    return json.loads(raw)


def update_session(session_id: str, data: dict) -> None:
    r = _get_redis()
    r.setex(_session_key(session_id), SESSION_TTL, json.dumps(data))


def destroy_session(session_id: str) -> None:
    r = _get_redis()
    r.delete(_session_key(session_id))
    logger.info("Session destroyed: %s", session_id)
