import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


def record_completed_run(session: Dict[str, Any], *, model_id: Optional[str], voice_id: Optional[str]) -> Dict[str, Any]:
    """Append a practice run entry to session['practice_history']."""
    history: List[Dict[str, Any]] = session.get("practice_history") or []
    entry = {
        "run_id": str(uuid.uuid4()),
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "question_ids": list(session.get("questions") or []),
        "model_id": model_id,
        "voice_id": voice_id,
    }
    history.append(entry)
    session["practice_history"] = history
    return entry
