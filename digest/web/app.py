import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask

from .routes.register import bp as register_bp
from .routes.player import bp as player_bp
from .routes.ask import bp as ask_bp
from .routes.admin import bp as admin_bp

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-prod")

app.register_blueprint(register_bp)
app.register_blueprint(player_bp)
app.register_blueprint(ask_bp)
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(debug=True, host=host, port=port)
