"""Application configuration loaded from environment variables and .env file."""

import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env automatically so `uvicorn app.main:app` works without sourcing.
load_dotenv(BASE_DIR / ".env")


def _resolve_upload_dir(value: str | None) -> str:
    if not value:
        return str(BASE_DIR / "app" / "uploads")
    expanded = os.path.expanduser(value)
    return os.path.abspath(expanded)


def _parse_extensions(value: str | None, default: Set[str]) -> Set[str]:
    if not value:
        return default
    items = {item.strip().lower() for item in value.split(",") if item.strip()}
    return items or default


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-mini-2025-10-06").strip()
OPENAI_REALTIME_VOICE = os.getenv("OPENAI_REALTIME_VOICE", "verse").strip()
OPENAI_REALTIME_URL = os.getenv("OPENAI_REALTIME_URL", "https://api.openai.com/v1/realtime").strip()

OPENAI_TURN_DETECTION = os.getenv("OPENAI_TURN_DETECTION", "server_vad").strip()
OPENAI_TURN_THRESHOLD = os.getenv("OPENAI_TURN_THRESHOLD", "0.5").strip()
OPENAI_TURN_PREFIX_MS = os.getenv("OPENAI_TURN_PREFIX_MS", "300").strip()
OPENAI_TURN_SILENCE_MS = os.getenv("OPENAI_TURN_SILENCE_MS", "500").strip()

UPLOAD_FOLDER = _resolve_upload_dir(os.getenv("UPLOAD_FOLDER"))
ALLOWED_EXTENSIONS = _parse_extensions(os.getenv("ALLOWED_EXTENSIONS"), {"pdf", "docx", "txt"})

__all__ = [
    "BASE_DIR",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_REALTIME_MODEL",
    "OPENAI_REALTIME_VOICE",
    "OPENAI_REALTIME_URL",
    "OPENAI_TURN_DETECTION",
    "OPENAI_TURN_THRESHOLD",
    "OPENAI_TURN_PREFIX_MS",
    "OPENAI_TURN_SILENCE_MS",
    "UPLOAD_FOLDER",
    "ALLOWED_EXTENSIONS",
]
