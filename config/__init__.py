"""
Configuration loader.
Reads from config/config.yaml with environment variable overrides.
Environment variables use double-underscore notation: LLM__PROVIDER, STOCKFISH__DEPTH, etc.
"""

import os
import yaml
from pathlib import Path


_DEFAULT_CONFIG = {
    "llm": {
        "provider": "anthropic",
        "api_key": "",
        "model": "",
        "max_tokens": 4096,
        "temperature": 0.7,
    },
    "stockfish": {
        "path": "",
        "depth": 20,
        "threads": 2,
        "hash_mb": 128,
    },
    "storytelling": {
        "verbosity": "balanced",
        "length": "medium",
        "mood": "calm",
    },
    "app": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
    },
    "player": {
        "usernames": [],
    },
}

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "google": "gemini-2.0-flash",
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, recursively."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(config: dict) -> dict:
    """Apply environment variables like LLM__PROVIDER over config values."""
    for env_key, env_value in os.environ.items():
        if "__" not in env_key:
            continue
        parts = env_key.lower().split("__")
        if len(parts) == 2 and parts[0] in config:
            section, key = parts
            if key in config[section]:
                # Cast to the correct type
                existing = config[section][key]
                if isinstance(existing, bool):
                    config[section][key] = env_value.lower() in ("true", "1", "yes")
                elif isinstance(existing, int):
                    try:
                        config[section][key] = int(env_value)
                    except ValueError:
                        pass
                elif isinstance(existing, float):
                    try:
                        config[section][key] = float(env_value)
                    except ValueError:
                        pass
                else:
                    config[section][key] = env_value
    return config


def load_config() -> dict:
    """Load configuration from YAML file with env overrides."""
    config_env = os.environ.get("CHESS_STORYTELLER_CONFIG", "")

    # Determine config file path
    config_dir = Path(__file__).parent
    if config_env == "railway":
        config_path = config_dir / "config.railway.yaml"
    else:
        config_path = config_dir / "config.yaml"

    # Start with defaults
    config = _DEFAULT_CONFIG.copy()

    # Merge YAML if it exists
    if config_path.exists():
        with open(config_path, "r") as f:
            file_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, file_config)

    # Apply environment variable overrides
    config = _apply_env_overrides(config)

    # Fill in default model if blank
    if not config["llm"]["model"]:
        provider = config["llm"]["provider"]
        config["llm"]["model"] = _DEFAULT_MODELS.get(provider, "")

    return config
