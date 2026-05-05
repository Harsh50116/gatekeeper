import logging
import os

import httpx

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
FROM_EMAIL = "onboarding@resend.dev"


def _api_key() -> str:
    key = os.environ.get("RESEND_API_KEY", "")
    if not key:
        raise RuntimeError("RESEND_API_KEY not set in environment")
    return key


def send_digest_email(to_email: str, audio_url: str) -> str:
    resp = httpx.post(
        RESEND_URL,
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        json={
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Your Morning Digest is ready",
            "html": (
                '<div style="font-family: Georgia, serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">'
                '<h1 style="font-size: 1.5rem; font-weight: 400; color: #1a1715;">Good morning.</h1>'
                '<p style="color: #6b635b; line-height: 1.6;">Your daily audio briefing is ready. '
                'Click below to listen to today\'s three-minute digest.</p>'
                f'<a href="{audio_url}" style="display: inline-block; margin: 24px 0; padding: 12px 32px; '
                'background: #c47a3a; color: #fff; text-decoration: none; font-size: 0.9rem; '
                'letter-spacing: 0.1em; text-transform: uppercase;">Listen Now &rarr;</a>'
                '<p style="font-size: 0.75rem; color: #9a9088; margin-top: 32px;">Sent by Digest &middot; '
                'Unsubscribe anytime</p>'
                '</div>'
            ),
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    email_id = resp.json().get("id", "")
    logger.info("Email sent to %s (id: %s)", to_email, email_id)
    return email_id
