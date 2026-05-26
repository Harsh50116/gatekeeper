from datetime import datetime, timezone

from flask import Blueprint, render_template, request

bp = Blueprint("player", __name__)

DISPLAY_NAMES = {
    "tech_ai": "Tech & AI",
    "business_markets": "Markets",
    "sports": "Sports",
    "world_news": "World News",
    "science": "Science",
}


@bp.route("/play")
def player():
    audio_url = request.args.get("audio", "")
    cats = request.args.get("cats", "")
    user_id = request.args.get("user", "")
    digest_date = request.args.get("date", "")
    date_display = datetime.now(timezone.utc).strftime("%A, %B %d").upper()
    categories = [c.strip() for c in cats.split(",") if c.strip()]
    category_labels = [DISPLAY_NAMES.get(c, c.replace("_", " ").title()) for c in categories]

    return render_template(
        "player.html",
        audio_url=audio_url,
        categories=category_labels,
        date_display=date_display,
        user_id=user_id,
        digest_date=digest_date,
    )
