import logging
import re
import threading

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for

from .sources import CATEGORIES
from .store import init_db, register_user, get_user_items
from .summarizer import build_user_digest, clear_cache
from .tts import generate_audio
from .storage import upload_audio
from .mailer import send_digest_email

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

        digest_text = build_user_digest(items)
        if not digest_text:
            logger.warning("Empty digest for %s", email)
            return

        audio_path = generate_audio(digest_text, email)
        public_url = upload_audio(audio_path)
        send_digest_email(email, public_url)
        logger.info("Welcome digest sent to %s", email)
    except Exception:
        logger.exception("Failed to send welcome digest to %s", email)


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
