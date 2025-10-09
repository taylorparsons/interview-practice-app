import json
from pathlib import Path
from typing import Any, Dict, Optional

SESSION_DIR = Path(__file__).resolve().parent.parent / "session_store"


def _ensure_dir() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    return SESSION_DIR / f"{session_id}.json"


def save_session(session_id: str, data: Dict[str, Any]) -> None:
    """Persist the session payload (excluding unserializable fields) to disk."""
    _ensure_dir()
    serializable = {key: value for key, value in data.items() if key != "agent"}
    _session_path(session_id).write_text(json.dumps(serializable, ensure_ascii=False), encoding="utf-8")


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Load a saved session from disk, returning None when it is missing."""
    path = _session_path(session_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["agent"] = None
    return data


def delete_session(session_id: str) -> None:
    """Remove persisted state for a session."""
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
