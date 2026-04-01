"""Flask routes for Chess Storyteller."""

import io
import json
import hashlib
import traceback
from datetime import datetime
from pathlib import Path

import chess.pgn
from flask import Blueprint, render_template, request, jsonify, current_app

from analysis import analyse_game, analysis_to_prompt_context
from providers import get_provider
from prompts import load_system_prompt, load_analysis_prompt

main = Blueprint("main", __name__)

STORIES_DIR = Path(__file__).parent.parent / "stories"


def _ensure_stories_dir():
    STORIES_DIR.mkdir(exist_ok=True)


def _game_id(white: str, black: str, date: str, result: str) -> str:
    """Generate a stable ID for a game based on its key metadata."""
    raw = f"{white}|{black}|{date}|{result}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _story_id(game_id: str, verbosity: str, length: str, mood: str) -> str:
    """Generate a unique story filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{game_id}_{verbosity}_{length}_{mood}_{timestamp}"


@main.route("/")
def index():
    config = current_app.config["CHESS_CONFIG"]
    return render_template("index.html", config=config)


@main.route("/stories")
def stories_page():
    """Display saved stories grouped by game."""
    _ensure_stories_dir()

    all_stories = []
    for f in sorted(STORIES_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_filename"] = f.stem
            all_stories.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    # Group by game_id
    games = {}
    for story in all_stories:
        gid = story.get("game_id", "unknown")
        if gid not in games:
            games[gid] = {
                "game_id": gid,
                "white": story.get("meta", {}).get("white", "?"),
                "black": story.get("meta", {}).get("black", "?"),
                "result": story.get("meta", {}).get("result", "?"),
                "date": story.get("meta", {}).get("date", ""),
                "stories": [],
            }
        games[gid]["stories"].append(story)

    games_list = sorted(
        games.values(),
        key=lambda g: g["stories"][0].get("saved_at", ""),
        reverse=True,
    )

    return render_template("stories.html", games=games_list)


@main.route("/stories/<filename>")
def load_story(filename):
    """Load a saved story by filename."""
    _ensure_stories_dir()
    filepath = STORIES_DIR / f"{filename}.json"

    if not filepath.exists():
        return jsonify({"error": "Story not found."}), 404

    data = json.loads(filepath.read_text(encoding="utf-8"))
    return jsonify(data)


@main.route("/save", methods=["POST"])
def save_story():
    """Save a story to disk."""
    _ensure_stories_dir()

    try:
        data = request.get_json()
        story = data.get("story", "")
        meta = data.get("meta", {})
        pgn = data.get("pgn", "")
        params = data.get("params", {})
        filename = data.get("filename", "")

        if not story:
            return jsonify({"error": "No story to save."}), 400

        game_id = _game_id(
            meta.get("white", ""),
            meta.get("black", ""),
            meta.get("date", ""),
            meta.get("result", ""),
        )

        if filename:
            file_stem = filename
        else:
            file_stem = _story_id(
                game_id,
                params.get("verbosity", "balanced"),
                params.get("length", "medium"),
                params.get("mood", "calm"),
            )

        save_data = {
            "story": story,
            "meta": meta,
            "pgn": pgn,
            "params": params,
            "game_id": game_id,
            "saved_at": datetime.now().isoformat(),
        }

        filepath = STORIES_DIR / f"{file_stem}.json"
        filepath.write_text(json.dumps(save_data, indent=2), encoding="utf-8")

        return jsonify({"filename": file_stem, "saved": True})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Could not save: {str(e)}"}), 500


@main.route("/stories/<filename>", methods=["DELETE"])
def delete_story(filename):
    """Delete a saved story."""
    _ensure_stories_dir()
    filepath = STORIES_DIR / f"{filename}.json"

    if not filepath.exists():
        return jsonify({"error": "Story not found."}), 404

    filepath.unlink()
    return jsonify({"deleted": True})


@main.route("/analyse", methods=["POST"])
def analyse():
    """Accept PGN, run Stockfish analysis, generate story."""
    config = current_app.config["CHESS_CONFIG"]

    try:
        pgn_text = None

        if "pgn_file" in request.files:
            file = request.files["pgn_file"]
            if file and file.filename:
                pgn_text = file.read().decode("utf-8")

        if not pgn_text:
            pgn_text = request.form.get("pgn_text", "").strip()

        if not pgn_text:
            return jsonify({"error": "No PGN provided. Paste a PGN or upload a .pgn file."}), 400

        storytelling = config["storytelling"].copy()
        for key in ("verbosity", "length", "mood"):
            override = request.form.get(key)
            if override:
                storytelling[key] = override

        sf_config = config["stockfish"]
        game_analysis = analyse_game(
            pgn_text,
            stockfish_path=sf_config.get("path", ""),
            depth=sf_config.get("depth", 20),
            threads=sf_config.get("threads", 2),
            hash_mb=sf_config.get("hash_mb", 128),
        )

        perspective = request.form.get("perspective", "auto")
        if perspective == "auto":
            usernames = [u.lower() for u in config.get("player", {}).get("usernames", [])]
            if game_analysis.white_player.lower() in usernames:
                perspective = "white"
            elif game_analysis.black_player.lower() in usernames:
                perspective = "black"
            else:
                perspective = "white"

        analysis_text = analysis_to_prompt_context(game_analysis)

        provider = get_provider(config)
        system_prompt = load_system_prompt()
        user_prompt = load_analysis_prompt(analysis_text, storytelling, perspective, game_analysis)
        story = provider.generate(system_prompt, user_prompt)

        # Extract date from PGN headers
        game_date = ""
        g = chess.pgn.read_game(io.StringIO(pgn_text))
        if g:
            game_date = g.headers.get("Date", "")

        return jsonify({
            "story": story,
            "pgn": pgn_text,
            "params": storytelling,
            "meta": {
                "white": game_analysis.white_player,
                "black": game_analysis.black_player,
                "result": game_analysis.result,
                "opening": game_analysis.opening,
                "total_moves": game_analysis.total_moves,
                "provider": provider.provider_name,
                "model": provider.model,
                "perspective": perspective,
                "date": game_date,
            },
        })

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500
