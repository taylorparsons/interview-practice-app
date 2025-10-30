from pathlib import Path
from typing import Optional


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt_template(persona: str, scope: str, role: str) -> Optional[str]:
    """Load a text template for a given persona/scope/role.

    - persona: one of ruthless|helpful|discovery
    - scope: questions|evaluation|example
    - role: system|user
    Returns the file contents or None if missing.
    """
    p = PROMPTS_DIR / persona / f"{scope}_{role}.txt"
    try:
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return None

