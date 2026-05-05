import re

from flask import Flask, render_template, request, redirect, url_for

from .sources import CATEGORIES
from .store import init_db, register_user

app = Flask(__name__)

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
        register_user(email, selected)
    except ValueError as e:
        return render_template("register.html", categories=CATEGORIES, error=str(e), email=email, selected=selected)

    return redirect(url_for("success", email=email, cats=",".join(selected)))


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
