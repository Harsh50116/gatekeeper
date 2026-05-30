import os
import re
import threading
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, redirect, url_for

from ...briefing.sources import CATEGORIES, SUBCATEGORIES
from ...briefing.summarizer import build_user_digest
from ...db.store import register_user, get_user_subcategories, save_digest, get_user_by_email, update_user_categories, save_user_subcategories
from ...services.tts import generate_audio
from ...services.storage import upload_audio
from ...services.mailer import send_digest_email

bp = Blueprint("register", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DISPLAY_NAMES = {
    "tech_ai": "Tech & AI",
    "business_markets": "Business & Markets",
    "sports": "Sports",
    "world_news": "World News",
    "science": "Science",
}


def _parse_subcategories(selected: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for cat in selected:
        sub_str = request.form.get(f"subs_{cat}", "")
        if sub_str:
            result[cat] = sub_str.split(",")
        else:
            result[cat] = [s["id"] for s in SUBCATEGORIES.get(cat, [])]
    return result


@bp.route("/")
def index():
    return render_template("register.html", categories=CATEGORIES, subcategories=SUBCATEGORIES, display_names=DISPLAY_NAMES, error=None, email="", selected=[])


@bp.route("/register", methods=["POST"])
def register():
    email = request.form.get("email", "").strip()
    selected = request.form.getlist("categories")

    error = None
    if not email or not EMAIL_RE.match(email):
        error = "Please enter a valid email address."
    elif not selected or not all(c in CATEGORIES for c in selected):
        error = "Select between 1 and 5 valid categories."

    if error:
        return render_template("register.html", categories=CATEGORIES, subcategories=SUBCATEGORIES, display_names=DISPLAY_NAMES, error=error, email=email, selected=selected)

    existing = get_user_by_email(email)
    if existing:
        prev_labels = [DISPLAY_NAMES.get(c, c.replace("_", " ").title()) for c in existing["categories"]]
        new_labels = [DISPLAY_NAMES.get(c, c.replace("_", " ").title()) for c in selected]
        prev_cats_detail = []
        for cat in existing["categories"]:
            cat_subs = SUBCATEGORIES.get(cat, [])
            prev_sub_ids = existing["subcategories"].get(cat, [])
            if prev_sub_ids:
                sub_names = [s["name"] for s in cat_subs if s["id"] in prev_sub_ids]
            else:
                sub_names = [s["name"] for s in cat_subs]
            prev_cats_detail.append({
                "name": DISPLAY_NAMES.get(cat, cat.replace("_", " ").title()),
                "subs": sub_names,
            })
        new_cats_detail = []
        for cat in selected:
            sub_str = request.form.get(f"subs_{cat}", "")
            cat_subs = SUBCATEGORIES.get(cat, [])
            if sub_str:
                sub_ids = sub_str.split(",")
                sub_names = [s["name"] for s in cat_subs if s["id"] in sub_ids]
            else:
                sub_names = [s["name"] for s in cat_subs]
            new_cats_detail.append({
                "name": DISPLAY_NAMES.get(cat, cat.replace("_", " ").title()),
                "subs": sub_names,
            })
        sub_selections = {}
        for cat in selected:
            sub_str = request.form.get(f"subs_{cat}", "")
            if sub_str:
                sub_selections[cat] = sub_str
        return render_template(
            "register.html",
            categories=CATEGORIES,
            subcategories=SUBCATEGORIES,
            display_names=DISPLAY_NAMES,
            error=None,
            email=email,
            selected=selected,
            show_modal=True,
            prev_categories=prev_labels,
            new_categories=new_labels,
            prev_cats_detail=prev_cats_detail,
            new_cats_detail=new_cats_detail,
            sub_selections=sub_selections,
            user_id=existing["id"],
        )

    sub_selections = _parse_subcategories(selected)
    try:
        user_id = register_user(email, selected)
        save_user_subcategories(user_id, sub_selections)
    except ValueError:
        return render_template("register.html", categories=CATEGORIES, subcategories=SUBCATEGORIES, display_names=DISPLAY_NAMES, error="Something went wrong. Please try again.", email=email, selected=selected)

    threading.Thread(
        target=_send_welcome_digest,
        args=(user_id, email),
        daemon=True,
    ).start()

    return redirect(url_for("register.success", email=email, cats=",".join(selected)))


@bp.route("/register/update", methods=["POST"])
def register_update():
    user_id = request.form.get("user_id", "").strip()
    email = request.form.get("email", "").strip()
    selected = request.form.getlist("categories")

    if not user_id or not email or not selected:
        return redirect(url_for("register.index"))

    update_user_categories(user_id, selected)
    save_user_subcategories(user_id, _parse_subcategories(selected))

    threading.Thread(
        target=_send_welcome_digest,
        args=(user_id, email),
        daemon=True,
    ).start()

    return redirect(url_for("register.success", email=email, cats=",".join(selected)))


def _send_welcome_digest(user_id: str, email: str):
    try:
        print(f"[DIGEST] Starting welcome digest for {email}")
        user_subs = get_user_subcategories(user_id)
        if not user_subs:
            print(f"[DIGEST] No subcategory preferences for {email}, skipping")
            return

        print(f"[DIGEST] Building digest for {len(user_subs)} categories...")
        digest_text = build_user_digest(user_subs)
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
        cats = ",".join(user_subs.keys())
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        player_url = f"{app_url}/play?audio={audio_url}&cats={cats}&user={user_id}&date={date_str}"
        print(f"[DIGEST] Sending email...")
        send_digest_email(email, player_url)
        print(f"[DIGEST] Done — welcome digest sent to {email}")
    except Exception as e:
        print(f"[DIGEST] FAILED for {email}: {e}")
        import traceback
        traceback.print_exc()


@bp.route("/success")
def success():
    email = request.args.get("email", "")
    cats = request.args.get("cats", "").split(",")
    return render_template("success.html", email=email, categories=cats)
