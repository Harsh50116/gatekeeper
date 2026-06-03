import os
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, abort

from ...db.store import (
    get_admin_users, get_digest_dates, get_digest_run_inputs,
    get_digest_by_date, get_user_by_email, get_user_subcategories,
)
from ...briefing.sources import SUBCATEGORIES

bp = Blueprint("admin", __name__, url_prefix="/admin")

DISPLAY_NAMES = {
    "tech_ai": "Tech & AI",
    "business_markets": "Business & Markets",
    "sports": "Sports",
    "world_news": "World News",
    "science": "Science",
}


def _require_password(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_pw = os.environ.get("ADMIN_PASSWORD", "")
        if not admin_pw:
            abort(403)
        if request.args.get("pw") != admin_pw:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
@_require_password
def index():
    return redirect(url_for("admin.digest_eval", pw=request.args.get("pw", "")))


@bp.route("/digest-eval")
@_require_password
def digest_eval():
    pw = request.args.get("pw", "")
    users = get_admin_users()

    user_id = request.args.get("user_id", "")
    date = request.args.get("date", "")

    dates = []
    inputs = {"rss": [], "reddit": []}
    digest_text = ""
    selected_user = None
    user_categories = []
    user_subcats = {}

    if not user_id and users:
        user_id = users[0]["id"]

    if user_id:
        dates = get_digest_dates(user_id)
        if not date and dates:
            date = dates[0]

        selected_user = next((u for u in users if u["id"] == user_id), None)

        if date:
            inputs = get_digest_run_inputs(user_id, date)
            digest_text = get_digest_by_date(user_id, date) or ""

        sub_prefs = get_user_subcategories(user_id)
        for cat, subs in sub_prefs.items():
            cat_label = DISPLAY_NAMES.get(cat, cat.replace("_", " ").title())
            user_categories.append(cat_label)
            sub_defs = SUBCATEGORIES.get(cat, [])
            sub_names = [s["name"] for s in sub_defs if s["id"] in subs]
            user_subcats[cat_label] = sub_names

    return render_template(
        "admin_digest_eval.html",
        users=users,
        dates=dates,
        selected_user_id=user_id,
        selected_date=date,
        selected_user=selected_user,
        user_categories=user_categories,
        user_subcats=user_subcats,
        rss_items=inputs["rss"],
        reddit_items=inputs["reddit"],
        digest_text=digest_text,
        display_names=DISPLAY_NAMES,
        pw=pw,
    )


@bp.route("/qa-eval")
@_require_password
def qa_eval():
    return render_template("admin_qa_eval.html", pw=request.args.get("pw", ""))
