import logging
import re
import threading
from datetime import datetime, timezone

import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for

from .sources import CATEGORIES
from .store import init_db, register_user, get_user_items
from .summarizer import build_user_digest, summarize_category, clear_cache
from .tts import generate_audio
from .storage import upload_audio
from .mailer import send_digest_email
from .image_gen import generate_daily_cover

logger = logging.getLogger(__name__)

app = Flask(__name__)
init_db()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.route("/")
def index():
    return render_template("register.html", categories=CATEGORIES, error=None, email="", selected=[])


@app.route("/register", methods=["POST"])
def register():
    email = request.form.get("email", "").strip()
    selected = request.form.getlist("categories")

    error = None
    if not email or not EMAIL_RE.match(email):
        error = "Please enter a valid email address."
    elif not selected or not all(c in CATEGORIES for c in selected):
        error = "Select between 1 and 5 valid categories."

    if error:
        return render_template("register.html", categories=CATEGORIES, error=error, email=email, selected=selected)

    try:
        user_id = register_user(email, selected)
    except ValueError as e:
        return render_template("register.html", categories=CATEGORIES, error=str(e), email=email, selected=selected)

    threading.Thread(
        target=_send_welcome_digest,
        args=(user_id, email),
        daemon=True,
    ).start()

    return redirect(url_for("success", email=email, cats=",".join(selected)))


def _send_welcome_digest(user_id: str, email: str):
    try:
        items = get_user_items(user_id)
        if not items:
            logger.info("No items yet for %s, skipping welcome digest", email)
            return

        category_summaries = {}
        for cat, cat_items in items.items():
            category_summaries[cat] = summarize_category(cat, cat_items)

        cover_url = generate_daily_cover(category_summaries)

        digest_text = build_user_digest(items)
        if not digest_text:
            logger.warning("Empty digest for %s", email)
            return

        audio_path = generate_audio(digest_text, email)
        audio_url = upload_audio(audio_path)

        app_url = os.environ.get("APP_URL", "http://localhost:8080")
        cats = ",".join(items.keys())
        player_url = f"{app_url}/play?audio={audio_url}&cats={cats}&cover={cover_url}"
        send_digest_email(email, player_url)
        logger.info("Welcome digest sent to %s", email)
    except Exception:
        logger.exception("Failed to send welcome digest to %s", email)


@app.route("/play")
def player():
    audio_url = request.args.get("audio", "")
    cats = request.args.get("cats", "")
    cover_url = request.args.get("cover", "")
    date_str = request.args.get("date", datetime.now(timezone.utc).strftime("%A, %B %d").upper())
    categories = [c.strip() for c in cats.split(",") if c.strip()]

    display_names = {
        "tech_ai": "Tech & AI",
        "business_markets": "Markets",
        "sports": "Sports",
        "world_news": "World News",
        "science": "Science",
    }
    category_labels = [display_names.get(c, c.replace("_", " ").title()) for c in categories]

    return render_template(
        "player.html",
        audio_url=audio_url,
        cover_url=cover_url,
        categories=category_labels,
        date_display=date_str,
    )


@app.route("/success")
def success():
    email = request.args.get("email", "")
    cats = request.args.get("cats", "").split(",")
    return render_template("success.html", email=email, categories=cats)


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    init_db()
    app.run(debug=True, port=port)
