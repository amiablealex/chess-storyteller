"""Chess Storyteller — entry point."""

from app import create_app
from config import load_config

if __name__ == "__main__":
    config = load_config()
    app = create_app()
    app.run(
        host=config["app"]["host"],
        port=config["app"]["port"],
        debug=config["app"]["debug"],
    )
