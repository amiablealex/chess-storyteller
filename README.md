# Chess Storyteller

A self-hosted web app that transforms chess games into calm, descriptive narratives. Feed it a PGN file and get back a storytelling script — no algebraic notation, just rich positional language.

Built for [Calm Échecs](https://youtube.com/@calmechecs).

## Quick Start

```bash
# 1. Install Stockfish
sudo apt install stockfish        # Ubuntu/Debian/Raspberry Pi
brew install stockfish            # macOS

# 2. Clone and install
git clone https://github.com/YOUR_USER/chess-storyteller.git
cd chess-storyteller
pip install -r requirements.txt

# 3. Configure
cp config/config.example.yaml config/config.yaml
# Edit config.yaml — add your API key and choose your LLM provider

# 4. Run
python run.py
# Open http://localhost:5000
```

## Configuration

All settings live in `config/config.yaml`. Key options:

- **`llm.provider`** — `anthropic`, `openai`, or `google`
- **`llm.api_key`** — your API key for the chosen provider
- **`llm.model`** — model name (defaults provided per provider)
- **`storytelling.verbosity`** — `minimal`, `balanced`, or `rich`
- **`storytelling.length`** — `short`, `medium`, or `long`
- **`storytelling.mood`** — `calm`, `dramatic`, or `reflective`
- **`stockfish.depth`** — analysis depth (default: 20)
- **`stockfish.path`** — path to Stockfish binary (auto-detected)

## Prompt Customisation

The storytelling voice lives in `prompts/system.txt` and `prompts/analysis.txt`. Edit these files directly to change tone, style, or personality. No code changes needed.

## Deploy to Railway

```bash
# Set environment variable CHESS_STORYTELLER_CONFIG to "railway"
# Set LLM__API_KEY in Railway's environment variables
# Stockfish is installed via Dockerfile
```

## Project Structure

```
├── config/            # YAML configuration
├── prompts/           # Editable prompt templates
├── providers/         # LLM provider modules (swap/add providers here)
├── analysis/          # Stockfish + python-chess analysis engine
├── app/               # Flask app, routes, templates, static assets
├── scripts/           # Utility scripts
└── run.py             # Entry point
```
