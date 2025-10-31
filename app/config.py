"""Application configuration loaded from environment variables and .env file.

This module centralizes runtime configuration with sensible defaults so the
server can boot in local/dev environments without extra flags. Values can be
overridden via environment variables or a `.env` file at the repo root.
"""

import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Auto-load .env so `uvicorn app.main:app` works without sourcing.
load_dotenv(BASE_DIR / ".env")


def _resolve_upload_dir(value: str | None) -> str:
    """Return the absolute uploads directory from env or default path."""
    if not value:
        return str(BASE_DIR / "app" / "uploads")
    expanded = os.path.expanduser(value)
    return os.path.abspath(expanded)


def _parse_extensions(value: str | None, default: Set[str]) -> Set[str]:
    """Parse a comma-separated list of extensions into a normalized set."""
    if not value:
        return default
    items = {item.strip().lower() for item in value.split(",") if item.strip()}
    return items or default


# Core OpenAI config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()

# Realtime voice defaults
OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-mini-2025-10-06").strip()
OPENAI_REALTIME_VOICE = os.getenv("OPENAI_REALTIME_VOICE", "verse").strip()
OPENAI_REALTIME_URL = os.getenv("OPENAI_REALTIME_URL", "https://api.openai.com/v1/realtime").strip()

# Server-side VAD defaults
OPENAI_TURN_DETECTION = os.getenv("OPENAI_TURN_DETECTION", "server_vad").strip()
OPENAI_TURN_THRESHOLD = os.getenv("OPENAI_TURN_THRESHOLD", "0.5").strip()
OPENAI_TURN_PREFIX_MS = os.getenv("OPENAI_TURN_PREFIX_MS", "300").strip()
OPENAI_TURN_SILENCE_MS = os.getenv("OPENAI_TURN_SILENCE_MS", "500").strip()

# Optional: server-side input audio transcription for realtime
OPENAI_INPUT_TRANSCRIPTION_MODEL = os.getenv("OPENAI_INPUT_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe").strip()

# Uploads and file handling
UPLOAD_FOLDER = _resolve_upload_dir(os.getenv("UPLOAD_FOLDER"))
ALLOWED_EXTENSIONS = _parse_extensions(os.getenv("ALLOWED_EXTENSIONS"), {"pdf", "doc", "docx", "txt"})

# Knowledge store locations
KNOWLEDGE_STORE_DIR = (BASE_DIR / "app" / "knowledge_store").resolve()
WORK_HISTORY_STORE_FILE = KNOWLEDGE_STORE_DIR / "work_history.json"


__all__ = [
    "BASE_DIR",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_EMBEDDING_MODEL",
    "OPENAI_REALTIME_MODEL",
    "OPENAI_REALTIME_VOICE",
    "OPENAI_REALTIME_URL",
    "OPENAI_TURN_DETECTION",
    "OPENAI_TURN_THRESHOLD",
    "OPENAI_TURN_PREFIX_MS",
    "OPENAI_TURN_SILENCE_MS",
    "OPENAI_INPUT_TRANSCRIPTION_MODEL",
    "UPLOAD_FOLDER",
    "ALLOWED_EXTENSIONS",
    "KNOWLEDGE_STORE_DIR",
    "WORK_HISTORY_STORE_FILE",
]
