import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask

from .routes.register import bp as register_bp
from .routes.player import bp as player_bp
from .routes.ask import bp as ask_bp

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))

app.register_blueprint(register_bp)
app.register_blueprint(player_bp)
app.register_blueprint(ask_bp)

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    app.run(debug=True, port=port)
