"""Flask routes for Chess Storyteller."""

import traceback
from flask import Blueprint, render_template, request, jsonify, current_app

from analysis import analyse_game, analysis_to_prompt_context
from providers import get_provider
from prompts import load_system_prompt, load_analysis_prompt

main = Blueprint("main", __name__)


@main.route("/")
def index():
    config = current_app.config["CHESS_CONFIG"]
    return render_template("index.html", config=config)


@main.route("/analyse", methods=["POST"])
def analyse():
    """Accept PGN, run Stockfish analysis, generate story."""
    config = current_app.config["CHESS_CONFIG"]

    try:
        # Get PGN from request
        pgn_text = None

        if "pgn_file" in request.files:
            file = request.files["pgn_file"]
            if file and file.filename:
                pgn_text = file.read().decode("utf-8")

        if not pgn_text:
            pgn_text = request.form.get("pgn_text", "").strip()

        if not pgn_text:
            return jsonify({"error": "No PGN provided. Paste a PGN or upload a .pgn file."}), 400

        # Allow per-request overrides of storytelling params
        storytelling = config["storytelling"].copy()
        for key in ("verbosity", "length", "mood"):
            override = request.form.get(key)
            if override:
                storytelling[key] = override

        # Step 1: Stockfish analysis
        sf_config = config["stockfish"]
        game_analysis = analyse_game(
            pgn_text,
            stockfish_path=sf_config.get("path", ""),
            depth=sf_config.get("depth", 20),
            threads=sf_config.get("threads", 2),
            hash_mb=sf_config.get("hash_mb", 128),
        )

        # Step 2: Convert to prompt context
        analysis_text = analysis_to_prompt_context(game_analysis)

        # Step 3: Generate story via LLM
        provider = get_provider(config)
        system_prompt = load_system_prompt()
        user_prompt = load_analysis_prompt(analysis_text, storytelling)
        story = provider.generate(system_prompt, user_prompt)

        return jsonify({
            "story": story,
            "meta": {
                "white": game_analysis.white_player,
                "black": game_analysis.black_player,
                "result": game_analysis.result,
                "opening": game_analysis.opening,
                "total_moves": game_analysis.total_moves,
                "provider": provider.provider_name,
                "model": provider.model,
            },
        })

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500
