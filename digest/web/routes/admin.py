import os
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session

from ...db.store import (
    get_admin_users, get_digest_dates, get_digest_run_inputs,
    get_digest_by_date, get_user_by_email, get_user_subcategories,
    get_pass1_summaries,
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


def _require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin"):
        return redirect(url_for("admin.digest_eval"))
    error = None
    if request.method == "POST":
        admin_pw = os.environ.get("ADMIN_PASSWORD", "")
        if admin_pw and request.form.get("password") == admin_pw:
            session["admin"] = True
            return redirect(url_for("admin.digest_eval"))
        error = "Invalid password"
    return render_template("admin_login.html", error=error)


@bp.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin.login"))


@bp.route("/")
@_require_login
def index():
    return redirect(url_for("admin.digest_eval"))


@bp.route("/digest-eval")
@_require_login
def digest_eval():
    users = get_admin_users()

    user_id = request.args.get("user_id", "")
    date = request.args.get("date", "")

    dates = []
    inputs = {"rss": [], "reddit": []}
    digest_text = ""
    pass1_summaries = []
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
            pass1_summaries = get_pass1_summaries(user_id, date)

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
        pass1_summaries=pass1_summaries,
        display_names=DISPLAY_NAMES,
    )


@bp.route("/qa-eval")
@_require_login
def qa_eval():
    return render_template("admin_qa_eval.html")
