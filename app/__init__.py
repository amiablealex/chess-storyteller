"""Flask application factory."""

from flask import Flask
from config import load_config


def create_app() -> Flask:
    config = load_config()

    app = Flask(__name__)
    app.config["CHESS_CONFIG"] = config
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1MB upload limit

    from app.routes import main
    app.register_blueprint(main)

    return app
