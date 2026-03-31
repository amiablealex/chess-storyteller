"""
Chess game analysis engine.
Parses PGN, runs Stockfish evaluation, and produces structured analysis.
"""

import io
import shutil
from dataclasses import dataclass, field
from typing import Optional

import chess
import chess.pgn
import chess.engine


@dataclass
class MoveAnalysis:
    """Analysis of a single move."""
    move_number: int
    side: str  # "white" or "black"
    move_san: str  # Standard algebraic (internal use)
    move_description: str  # Human-readable description
    piece_moved: str
    eval_before: float  # Centipawn score before (from white's perspective)
    eval_after: float  # Centipawn score after
    eval_change: float  # Difference
    classification: str  # "brilliant", "good", "inaccuracy", "mistake", "blunder"
    is_capture: bool
    is_check: bool
    is_castling: bool
    best_move_san: Optional[str] = None
    best_move_description: Optional[str] = None
    material_after: Optional[str] = None  # Material snapshot after captures


@dataclass
class GameAnalysis:
    """Complete analysis of a chess game."""
    white_player: str
    black_player: str
    result: str
    opening: str
    termination: str
    total_moves: int
    moves: list[MoveAnalysis] = field(default_factory=list)
    white_blunders: int = 0
    black_blunders: int = 0
    white_mistakes: int = 0
    black_mistakes: int = 0
    white_inaccuracies: int = 0
    black_inaccuracies: int = 0
    key_moments: list[int] = field(default_factory=list)  # Indices of critical moves


_PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}

_SQUARE_NAMES_DESCRIPTIVE = {}  # Populated on first use


def _board_region(square: int) -> str:
    """Classify a square into a board region."""
    file_idx = chess.square_file(square)
    rank = chess.square_rank(square) + 1
    if file_idx <= 2:
        flank = "queenside"
    elif file_idx >= 5:
        flank = "kingside"
    else:
        flank = "centre"
    if rank <= 2:
        depth = "back ranks"
    elif rank <= 4:
        depth = "middle"
    elif rank <= 6:
        depth = "advanced"
    else:
        depth = "deep"
    return f"{flank} {depth}"


def _square_name_short(square: int) -> str:
    """Short human-friendly square name like 'e4' area description."""
    file_names = ["a", "b", "c", "d", "e", "f", "g", "h"]
    rank = chess.square_rank(square) + 1
    file_letter = file_names[chess.square_file(square)]
    return f"{file_letter}{rank}"


def _describe_square(square: int) -> str:
    """Convert square index to a concise descriptive name."""
    region = _board_region(square)
    short = _square_name_short(square)
    return f"{region} ({short})"


def _describe_move(board: chess.Board, move: chess.Move) -> str:
    """Create a concise, human-readable description of a move."""
    piece = board.piece_at(move.from_square)
    if piece is None:
        return "unknown move"

    piece_name = _PIECE_NAMES.get(piece.piece_type, "piece")
    to_region = _board_region(move.to_square)
    to_short = _square_name_short(move.to_square)
    from_short = _square_name_short(move.from_square)

    # Castling
    if board.is_castling(move):
        if chess.square_file(move.to_square) > chess.square_file(move.from_square):
            return "castles kingside"
        else:
            return "castles queenside"

    # Capture
    captured = board.piece_at(move.to_square)
    if captured:
        captured_name = _PIECE_NAMES.get(captured.piece_type, "piece")
        desc = f"{piece_name} on {from_short} takes {captured_name} on {to_short} ({to_region})"
    else:
        desc = f"{piece_name} moves {from_short} to {to_short} ({to_region})"

    # Promotion
    if move.promotion:
        promo_name = _PIECE_NAMES.get(move.promotion, "piece")
        desc += f", promotes to {promo_name}"

    return desc


def _classify_eval_change(change: float) -> str:
    """Classify a move based on evaluation change (centipawns)."""
    abs_change = abs(change)
    if abs_change < 20:
        return "good"
    elif abs_change < 50:
        return "good"
    elif abs_change < 100:
        return "inaccuracy"
    elif abs_change < 200:
        return "mistake"
    else:
        return "blunder"


def _score_to_cp(score: chess.engine.PovScore) -> float:
    """Convert engine score to centipawns from white's perspective."""
    white_score = score.white()
    if white_score.is_mate():
        mate_in = white_score.mate()
        return 10000 if mate_in > 0 else -10000
    return white_score.score()


def find_stockfish() -> str:
    """Auto-detect Stockfish binary path."""
    # Check common locations
    for name in ["stockfish", "stockfish.exe"]:
        path = shutil.which(name)
        if path:
            return path

    common_paths = [
        "/usr/games/stockfish",
        "/usr/local/bin/stockfish",
        "/usr/bin/stockfish",
        "/opt/homebrew/bin/stockfish",
    ]
    for path in common_paths:
        if shutil.which(path) or __import__("os").path.isfile(path):
            return path

    raise FileNotFoundError(
        "Stockfish not found. Install it (apt install stockfish / brew install stockfish) "
        "or set stockfish.path in config.yaml"
    )


def parse_pgn(pgn_text: str) -> chess.pgn.Game:
    """Parse PGN text into a game object."""
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)
    if game is None:
        raise ValueError("Could not parse PGN. Check the format and try again.")
    return game


def analyse_game(pgn_text: str, stockfish_path: str = "", depth: int = 20,
                 threads: int = 2, hash_mb: int = 128) -> GameAnalysis:
    """
    Analyse a complete chess game from PGN.
    Returns structured analysis with move-by-move evaluation.
    """
    if not stockfish_path:
        stockfish_path = find_stockfish()

    game = parse_pgn(pgn_text)
    board = game.board()

    # Extract game metadata
    white = game.headers.get("White", "White")
    black = game.headers.get("Black", "Black")
    result = game.headers.get("Result", "*")
    opening = game.headers.get("Opening", game.headers.get("ECO", "Unknown Opening"))
    termination = game.headers.get("Termination", "")

    # Start engine
    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    engine.configure({"Threads": threads, "Hash": hash_mb})

    analysis = GameAnalysis(
        white_player=white,
        black_player=black,
        result=result,
        opening=opening,
        termination=termination,
        total_moves=0,
    )

    # Evaluate initial position
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    prev_eval = _score_to_cp(info["score"])

    move_number = 1
    moves_list = list(game.mainline_moves())
    analysis.total_moves = len(moves_list)

    for i, move in enumerate(moves_list):
        side = "white" if board.turn == chess.WHITE else "black"

        # Describe the move before making it
        move_desc = _describe_move(board, move)
        move_san = board.san(move)
        piece = board.piece_at(move.from_square)
        piece_name = _PIECE_NAMES.get(piece.piece_type, "piece") if piece else "piece"

        is_capture = board.is_capture(move)
        is_castling = board.is_castling(move)

        # Make the move
        board.push(move)

        is_check = board.is_check()

        # Evaluate new position
        if board.is_game_over():
            if board.is_checkmate():
                current_eval = -10000 if board.turn == chess.WHITE else 10000
            else:
                current_eval = 0
            best_move_san = None
            best_move_desc = None
        else:
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            current_eval = _score_to_cp(info["score"])

            # Get best move for context
            if "pv" in info and len(info["pv"]) > 0:
                best_move = info["pv"][0]
                best_move_san = board.san(best_move)
                best_move_desc = _describe_move(board, best_move)
            else:
                best_move_san = None
                best_move_desc = None

        # Calculate evaluation change (negative = bad for the side that moved)
        if side == "white":
            eval_change = current_eval - prev_eval
        else:
            eval_change = -(current_eval - prev_eval)

        classification = _classify_eval_change(eval_change)

        move_analysis = MoveAnalysis(
            move_number=move_number if side == "white" else move_number,
            side=side,
            move_san=move_san,
            move_description=move_desc,
            piece_moved=piece_name,
            eval_before=prev_eval,
            eval_after=current_eval,
            eval_change=eval_change,
            classification=classification,
            is_capture=is_capture,
            is_check=is_check,
            is_castling=is_castling,
            best_move_san=best_move_san,
            best_move_description=best_move_desc,
            material_after=_count_material(board) if is_capture else None,
        )

        analysis.moves.append(move_analysis)

        # Track errors
        if side == "white":
            if classification == "blunder":
                analysis.white_blunders += 1
            elif classification == "mistake":
                analysis.white_mistakes += 1
            elif classification == "inaccuracy":
                analysis.white_inaccuracies += 1
        else:
            if classification == "blunder":
                analysis.black_blunders += 1
            elif classification == "mistake":
                analysis.black_mistakes += 1
            elif classification == "inaccuracy":
                analysis.black_inaccuracies += 1

        # Mark key moments (big eval swings)
        if abs(eval_change) > 100:
            analysis.key_moments.append(i)

        prev_eval = current_eval
        if side == "black":
            move_number += 1

    engine.quit()
    return analysis


def analysis_to_prompt_context(analysis: GameAnalysis) -> str:
    """Convert structured analysis into text context for the LLM prompt."""
    lines = []
    lines.append(f"Game: {analysis.white_player} (White) vs {analysis.black_player} (Black)")
    lines.append(f"Result: {analysis.result}")
    if analysis.termination:
        lines.append(f"Termination: {analysis.termination}")
    lines.append(f"Opening: {analysis.opening}")
    lines.append(f"Total half-moves: {analysis.total_moves}")
    lines.append("")
    lines.append(f"White errors: {analysis.white_blunders} blunders, {analysis.white_mistakes} mistakes, {analysis.white_inaccuracies} inaccuracies")
    lines.append(f"Black errors: {analysis.black_blunders} blunders, {analysis.black_mistakes} mistakes, {analysis.black_inaccuracies} inaccuracies")
    lines.append("")
    lines.append("=" * 50)
    lines.append("MOVE-BY-MOVE SEQUENCE (follow this order exactly)")
    lines.append("=" * 50)
    lines.append("")

    current_move_num = 0
    for i, move in enumerate(analysis.moves):
        # Group moves into numbered pairs
        if move.side == "white":
            current_move_num = move.move_number
            lines.append(f"--- Move {current_move_num} ---")

        side_label = "WHITE" if move.side == "white" else "BLACK"
        eval_str = f"{move.eval_after / 100:+.1f}" if move.eval_after != 10000 and move.eval_after != -10000 else ("mate for white" if move.eval_after > 0 else "mate for black")

        # Build factual description with explicit flags
        desc = f"  {side_label}: {move.move_description}"

        # Add explicit factual tags the LLM must respect
        facts = []
        if move.is_capture:
            facts.append("THIS IS A CAPTURE")
        else:
            facts.append("this is NOT a capture")
        if move.is_check:
            facts.append("THIS GIVES CHECK")
        if move.is_castling:
            facts.append("THIS IS CASTLING")
        if board_result := _check_game_ending(i, analysis):
            facts.append(board_result)

        desc += f" [{', '.join(facts)}]"
        desc += f" [eval: {eval_str}]"

        if move.classification not in ("good",):
            desc += f" [{move.classification.upper()}]"

        lines.append(desc)

        if move.material_after:
            lines.append(f"    [MATERIAL ON BOARD: {move.material_after}]")

        if move.classification in ("blunder", "mistake") and move.best_move_description:
            lines.append(f"    → Better was: {move.best_move_description}")

        if i in analysis.key_moments:
            lines.append(f"    ★ KEY MOMENT — significant shift in the position")

    lines.append("")
    lines.append("=" * 50)
    lines.append("END OF SEQUENCE")
    lines.append("=" * 50)

    return "\n".join(lines)


def _check_game_ending(move_index: int, analysis: GameAnalysis) -> str:
    """Check if this move ends the game."""
    if move_index == len(analysis.moves) - 1:
        if analysis.termination:
            return f"GAME ENDS — {analysis.termination}"
        result = analysis.result
        if result == "1-0":
            return "GAME ENDS — White wins"
        elif result == "0-1":
            return "GAME ENDS — Black wins"
        elif result == "1/2-1/2":
            return "GAME ENDS — Draw"
        else:
            return "GAME ENDS"
    return ""


def _count_material(board: chess.Board) -> str:
    """Count material for both sides, returning a human-readable summary."""
    piece_order = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]

    def _count_side(color):
        pieces = []
        for piece_type in piece_order:
            count = len(board.pieces(piece_type, color))
            if count > 0:
                name = _PIECE_NAMES[piece_type]
                if count > 1:
                    name += "s"
                pieces.append(f"{count} {name}")
        return ", ".join(pieces) if pieces else "king only"

    white_material = _count_side(chess.WHITE)
    black_material = _count_side(chess.BLACK)
    return f"White: {white_material} | Black: {black_material}"
