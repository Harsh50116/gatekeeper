import logging
import os

import httpx

logger = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "")


def send_digest_email(to_email: str, player_url: str) -> None:
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY not set in environment")
    if not FROM_EMAIL:
        raise RuntimeError("FROM_EMAIL not set in environment")

    html = (
        '<div style="font-family: Georgia, serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">'
        '<h1 style="font-size: 1.5rem; font-weight: 400; color: #1a1715;">Good morning.</h1>'
        '<p style="color: #6b635b; line-height: 1.6;">Your daily audio briefing is ready. '
        'Click below to listen to today\'s three-minute brief.</p>'
        f'<a href="{player_url}" style="display: inline-block; margin: 24px 0; padding: 12px 32px; '
        'background: #c47a3a; color: #fff; text-decoration: none; font-size: 0.9rem; '
        'letter-spacing: 0.1em; text-transform: uppercase;">Listen Now &rarr;</a>'
        '<p style="font-size: 0.75rem; color: #9a9088; margin-top: 32px;">Sent by Brief &middot; '
        'Unsubscribe anytime</p>'
        '</div>'
    )

    resp = httpx.post(
        BREVO_URL,
        headers={
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "sender": {"email": FROM_EMAIL},
            "to": [{"email": to_email}],
            "subject": "Your Morning Briefing is ready",
            "htmlContent": html,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    msg_id = resp.json().get("messageId", "")
    logger.info("Email sent to %s (id: %s)", to_email, msg_id)
