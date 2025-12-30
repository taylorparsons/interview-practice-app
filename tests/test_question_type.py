import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils.question_type import (  # noqa: E402
    infer_question_type,
    normalize_question_text,
    resolve_question_type,
)


def test_infer_question_type_behavioral():
    assert infer_question_type("Tell me about a time you led a team.") == "behavioral"


def test_infer_question_type_narrative_for_tell_me_about_yourself():
    assert infer_question_type("Tell me about yourself.") == "narrative"


def test_resolve_question_type_override_wins():
    overrides = {normalize_question_text("Tell me about yourself."): "behavioral"}
    assert resolve_question_type("Tell me about yourself.", overrides) == "behavioral"
