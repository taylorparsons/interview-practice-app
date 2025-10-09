import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime

SESSION_DIR = Path(__file__).resolve().parent.parent / "session_store"


def _ensure_dir() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    return SESSION_DIR / f"{session_id}.json"


def save_session(session_id: str, data: Dict[str, Any]) -> None:
    """Persist the session payload (excluding unserializable fields) to disk."""
    _ensure_dir()
    serializable = {key: value for key, value in data.items() if key != "agent"}
    # Stamp update time
    serializable["updated_at"] = datetime.utcnow().isoformat() + "Z"
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


def list_sessions() -> List[Dict[str, Any]]:
    """Return lightweight metadata for all saved sessions on disk."""
    _ensure_dir()
    items: List[Dict[str, Any]] = []
    for file in sorted(SESSION_DIR.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            items.append({
                "id": file.stem,
                "name": data.get("name") or f"Session {file.stem[:8]}",
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "questions_count": len(data.get("questions") or []),
                "answers_count": len(data.get("answers") or []),
            })
        except Exception:
            # Skip corrupted entries
            continue
    return items


def rename_session(session_id: str, new_name: str) -> Optional[Dict[str, Any]]:
    """Rename a session by updating its persisted 'name' field.

    Returns the updated session or None if not found.
    """
    data = load_session(session_id)
    if data is None:
        return None
    data["name"] = new_name
    save_session(session_id, data)
    return data
