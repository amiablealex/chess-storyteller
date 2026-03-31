"""
Prompt loader.
Reads prompt templates from the prompts/ directory and fills in variables.
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_system_prompt() -> str:
    """Load the system prompt."""
    return (_PROMPTS_DIR / "system.txt").read_text(encoding="utf-8").strip()


def load_analysis_prompt(analysis_text: str, storytelling_config: dict) -> str:
    """Load and fill the analysis prompt template."""
    template = (_PROMPTS_DIR / "analysis.txt").read_text(encoding="utf-8")
    return template.format(
        verbosity=storytelling_config.get("verbosity", "balanced"),
        length=storytelling_config.get("length", "medium"),
        mood=storytelling_config.get("mood", "calm"),
        analysis=analysis_text,
    )
