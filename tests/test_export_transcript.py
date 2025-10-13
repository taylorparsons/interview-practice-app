import sys
from pathlib import Path
from datetime import datetime, timedelta


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _export_lines_from_payload(payload: dict):
    """Replicate the client-side export ordering and coalescing logic.

    This mirrors app/static/js/app.js: exportFullTranscript()
    - backfill 'You' from voice_transcripts when no candidate message exists
    - sort by timestamp when both entries have it
    - otherwise by question_index and role order (You -> Coach -> System)
    - coalesce consecutive 'You' lines
    """
    msgs = list(payload.get("voice_messages") or [])

    # Backfill from per-question transcripts as synthetic 'candidate' lines
    transcripts = payload.get("voice_transcripts") or {}
    candidate_idxs = {
        m.get("question_index")
        for m in msgs
        if isinstance(m, dict) and (m.get("role") in ("candidate", "user")) and isinstance(m.get("question_index"), int)
    }
    for k, v in transcripts.items():
        try:
            idx = int(k)
        except Exception:
            continue
        text = (v or "").strip()
        if text and idx not in candidate_idxs:
            msgs.append({"role": "candidate", "text": text, "question_index": idx, "timestamp": ""})

    def _role_rank(m):
        r = str(m.get("role", "")).lower()
        if r in ("candidate", "user"):
            return 0
        if r in ("coach", "agent", "assistant"):
            return 1
        if r == "system":
            return 2
        return 3

    def _has_ts(m):
        ts = m.get("timestamp")
        if not ts:
            return False
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return True
        except Exception:
            return False

    def _ts_val(m):
        # Safe parse after _has_ts
        ts = m.get("timestamp")
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()

    with_index = [{**m, "_i": i} for i, m in enumerate(msgs)]

    def _qidx(m):
        qi = m.get("question_index")
        return qi if isinstance(qi, int) else float("inf")

    with_index.sort(
        key=lambda m: (
            # When both have timestamp, sorting reduces to timestamp due to comparator equivalence
            0,
            _qidx(m),
            _role_rank(m),
            m["_i"],
        )
    )

    # Because we can't compare pairs here like JS comparator, perform a second pass
    # to stably re-sort groups where both sides have valid timestamps
    # (stable sort keeps previous question/role grouping when timestamps missing)
    with_index.sort(key=lambda m: (_has_ts(m), _ts_val(m) if _has_ts(m) else float("inf")))

    # Coalesce consecutive 'You'
    out = []
    for m in with_index:
        role = (
            "Coach"
            if m.get("role") in ("coach", "agent", "assistant")
            else "You" if m.get("role") in ("candidate", "user")
            else "System"
        )
        text = (m.get("text") or "").strip()
        ts = m.get("timestamp") or ""
        if out and role == "You" and out[-1]["role"] == "You":
            out[-1]["text"] = (out[-1]["text"] + " " + text).strip()
            # keep earliest timestamp (out[-1])
            continue
        out.append({"role": role, "text": text, "timestamp": ts})

    return out


def test_export_backfills_you_from_transcripts_when_missing():
    payload = {
        "voice_messages": [
            {"role": "coach", "text": "Feedback on Q0", "question_index": 0},
        ],
        "voice_transcripts": {"0": "My answer Q0", "1": "My answer Q1"},
    }
    lines = _export_lines_from_payload(payload)
    roles = [l["role"] for l in lines]
    texts = [l["text"] for l in lines]
    # Expect 'You' for Q0 and Q1 to be present
    assert any(t == "My answer Q0" and r == "You" for r, t in zip(roles, texts))
    assert any(t == "My answer Q1" and r == "You" for r, t in zip(roles, texts))
    # And the original Coach line preserved
    assert any(t == "Feedback on Q0" and r == "Coach" for r, t in zip(roles, texts))


def test_export_orders_by_timestamp_when_available_otherwise_by_qindex_role():
    base = datetime(2025, 1, 1, 12, 0, 0)
    a = (base + timedelta(seconds=5)).isoformat() + "Z"
    b = (base + timedelta(seconds=10)).isoformat() + "Z"

    payload = {
        "voice_messages": [
            # Out of question order but with timestamps, should sort by ts
            {"role": "coach", "text": "Later coach", "question_index": 1, "timestamp": b},
            {"role": "candidate", "text": "Earlier you", "question_index": 1, "timestamp": a},
            # No timestamps: Q0 You then Coach grouping should apply
            {"role": "coach", "text": "Q0 coach", "question_index": 0},
            {"role": "candidate", "text": "Q0 you", "question_index": 0},
        ],
        "voice_transcripts": {},
    }

    lines = _export_lines_from_payload(payload)
    # With mixed timestamp/non-timestamp, ordering falls back to qindex for comparisons
    # across the two categories. Expect Q0 (no ts) grouped first by You -> Coach.
    assert lines[0]["role"] == "You" and lines[0]["text"].startswith("Q0 you")
    assert lines[1]["role"] == "Coach" and lines[1]["text"].startswith("Q0 coach")
    # Then the timestamped Q1 pair ordered by timestamp: Earlier you -> Later coach
    assert lines[2]["text"] == "Earlier you" and lines[2]["role"] == "You"
    assert lines[3]["text"] == "Later coach" and lines[3]["role"] == "Coach"


def test_export_coalesces_consecutive_you_lines():
    payload = {
        "voice_messages": [
            {"role": "candidate", "text": "Part A", "question_index": 0},
            {"role": "candidate", "text": "Part B", "question_index": 0},
            {"role": "coach", "text": "Coach reply", "question_index": 0},
        ],
        "voice_transcripts": {},
    }
    lines = _export_lines_from_payload(payload)
    assert len(lines) == 2
    assert lines[0]["role"] == "You" and lines[0]["text"] == "Part A Part B"
    assert lines[1]["role"] == "Coach"
