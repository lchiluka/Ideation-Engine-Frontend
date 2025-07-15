"""Helper functions for TRL assessments."""
from pathlib import Path

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "trl_rubric.md"

def load_trl_rubric() -> str:
    """Return the NASA TRL rubric text."""
    return RUBRIC_PATH.read_text(encoding="utf-8")
