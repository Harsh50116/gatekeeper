import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_LOGIN = os.environ.get("SMTP_LOGIN", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_LOGIN)


def send_digest_email(to_email: str, player_url: str) -> None:
    if not SMTP_LOGIN or not SMTP_PASSWORD:
        raise RuntimeError("SMTP_LOGIN and SMTP_PASSWORD must be set")

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

    msg = MIMEMultipart("alternative")
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "Your Morning Briefing is ready"
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())

    logger.info("Email sent to %s", to_email)
