import json
import logging
import re
import threading
import time
from datetime import datetime, timezone

import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, jsonify

from ..briefing.sources import CATEGORIES
from ..db.store import register_user, get_user_items, save_digest, get_digest_by_date, get_user_by_email, update_user_categories
from ..ask.session import create_session, destroy_session, get_session
from ..ask.interactive import handle_question
from ..services.tts import generate_response_audio
from ..briefing.summarizer import build_user_digest, clear_cache
from ..services.tts import generate_audio
from ..services.storage import upload_audio
from ..services.mailer import send_digest_email

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))

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

    existing = get_user_by_email(email)
    if existing:
        display_names = {
            "tech_ai": "Tech & AI",
            "business_markets": "Business & Markets",
            "sports": "Sports",
            "world_news": "World News",
            "science": "Science",
        }
        prev_labels = [display_names.get(c, c.replace("_", " ").title()) for c in existing["categories"]]
        new_labels = [display_names.get(c, c.replace("_", " ").title()) for c in selected]
        return render_template(
            "register.html",
            categories=CATEGORIES,
            error=None,
            email=email,
            selected=selected,
            show_modal=True,
            prev_categories=prev_labels,
            new_categories=new_labels,
            user_id=existing["id"],
        )

    try:
        user_id = register_user(email, selected)
    except ValueError:
        return render_template("register.html", categories=CATEGORIES, error="Something went wrong. Please try again.", email=email, selected=selected)

    threading.Thread(
        target=_send_welcome_digest,
        args=(user_id, email),
        daemon=True,
    ).start()

    return redirect(url_for("success", email=email, cats=",".join(selected)))


@app.route("/register/update", methods=["POST"])
def register_update():
    user_id = request.form.get("user_id", "").strip()
    email = request.form.get("email", "").strip()
    selected = request.form.getlist("categories")

    if not user_id or not email or not selected:
        return redirect(url_for("index"))

    update_user_categories(user_id, selected)

    threading.Thread(
        target=_send_welcome_digest,
        args=(user_id, email),
        daemon=True,
    ).start()

    return redirect(url_for("success", email=email, cats=",".join(selected)))


def _send_welcome_digest(user_id: str, email: str):
    try:
        print(f"[DIGEST] Starting welcome digest for {email}")
        items = get_user_items(user_id)
        if not items:
            print(f"[DIGEST] No items yet for {email}, skipping")
            return

        print(f"[DIGEST] Got {len(items)} categories, building digest...")
        digest_text = build_user_digest(items)
        if not digest_text:
            print(f"[DIGEST] Empty digest for {email}")
            return

        print(f"[DIGEST] Saving digest to history...")
        save_digest(user_id, digest_text)
        print(f"[DIGEST] Generating audio...")
        audio_path = generate_audio(digest_text, email)
        print(f"[DIGEST] Uploading audio...")
        audio_url = upload_audio(audio_path)

        app_url = os.environ.get("APP_URL", "http://localhost:8080")
        cats = ",".join(items.keys())
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        player_url = f"{app_url}/play?audio={audio_url}&cats={cats}&user={user_id}&date={date_str}"
        print(f"[DIGEST] Sending email...")
        send_digest_email(email, player_url)
        print(f"[DIGEST] Done — welcome digest sent to {email}")
    except Exception as e:
        print(f"[DIGEST] FAILED for {email}: {e}")
        import traceback
        traceback.print_exc()


@app.route("/play")
def player():
    audio_url = request.args.get("audio", "")
    cats = request.args.get("cats", "")
    user_id = request.args.get("user", "")
    digest_date = request.args.get("date", "")
    date_display = datetime.now(timezone.utc).strftime("%A, %B %d").upper()
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
        categories=category_labels,
        date_display=date_display,
        user_id=user_id,
        digest_date=digest_date,
    )


@app.route("/session", methods=["POST"])
def session_create():
    data = request.get_json()
    if not data or not data.get("user_id") or not data.get("digest_date"):
        return jsonify({"error": "user_id and digest_date required"}), 400

    digest_text = get_digest_by_date(data["user_id"], data["digest_date"])
    if not digest_text:
        return jsonify({"error": "Digest not found"}), 404

    session_id = create_session(digest_text)
    return jsonify({"session_id": session_id})


@app.route("/ask", methods=["POST"])
def ask():
    t_start = time.time()

    session_id = request.form.get("session_id", "")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    if get_session(session_id) is None:
        return jsonify({"error": "Session not found or expired"}), 404

    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "audio file required"}), 400

    audio_bytes = audio_file.read()
    filename = audio_file.filename or "audio.webm"

    from ..ask.transcribe import transcribe
    t_stt = time.time()
    question = transcribe(audio_bytes, filename)
    stt_latency = round(time.time() - t_stt, 3)
    if not question:
        return jsonify({"error": "Could not transcribe audio"}), 400

    result = handle_question(session_id, question)

    t_tts = time.time()
    response_audio = generate_response_audio(result["answer"])
    tts_latency = round(time.time() - t_tts, 3)

    total_latency = round(time.time() - t_start, 3)

    print(f"[ASK_E2E] {json.dumps({'session_id': session_id, 'stt_latency_s': stt_latency, 'tts_latency_s': tts_latency, 'total_latency_s': total_latency})}")

    return jsonify({
        "audio": response_audio,
        "question": result["question"],
        "answer": result["answer"],
    })


@app.route("/session/destroy", methods=["POST"])
def session_destroy():
    data = request.get_json(silent=True)
    if not data or not data.get("session_id"):
        return jsonify({"error": "session_id required"}), 400

    destroy_session(data["session_id"])
    return jsonify({"ok": True})


@app.route("/success")
def success():
    email = request.args.get("email", "")
    cats = request.args.get("cats", "").split(",")
    return render_template("success.html", email=email, categories=cats)


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    app.run(debug=True, port=port)
