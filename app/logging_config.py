from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from logging.config import dictConfig
from pathlib import Path

from app.logging_context import ContextFilter, RedactFilter


class JsonFormatter(logging.Formatter):
    """Render log records as compact JSON objects for structured ingestion."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        """Return the JSON-formatted string for a log record."""
        base = {
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "session_id": getattr(record, "session_id", None),
        }
        for attr in ("filename", "lineno", "funcName"):
            base[attr] = getattr(record, attr, None)
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                base[key[4:]] = value
        return json.dumps(base, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Render log records in a developer-friendly single line format."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        """Return the formatted string for a human-readable log record."""
        context_parts = []
        for key, value in record.__dict__.items():
            if key.startswith("ctx_") and value not in (None, "", []):
                context_parts.append(f"{key[4:]}={value}")
        record.context_suffix = f" | {' '.join(context_parts)}" if context_parts else ""
        if getattr(record, "request_id", None) is None:
            record.request_id = "-"
        if getattr(record, "session_id", None) is None:
            record.session_id = "-"
        return super().format(record)


def _prepare_file_logging() -> tuple[str, str]:
    """Ensure log directories exist and archive existing logs on startup.

    Returns (app_log_path, access_log_path).
    """
    root = Path(__file__).resolve().parent.parent
    logs_dir = root / "logs"
    archive_dir = logs_dir / "archive"
    logs_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    app_log = logs_dir / "app.log"
    access_log = logs_dir / "access.log"

    # Rotate non-empty logs into a timestamped archive directory at process start
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest_dir = archive_dir / ts
    for f in (app_log, access_log):
        try:
            if f.exists() and f.stat().st_size > 0:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dest_dir / f.name))
        except Exception:
            # Never block startup from logging
            pass

    return str(app_log), str(access_log)


def _resolve_log_levels(app_level: str) -> dict[str, str]:
    """Capture environment overrides for the various logger levels."""
    return {
        "app": app_level,
        "uvicorn": os.getenv("UVICORN_LOG_LEVEL", app_level),
        "uvicorn_access": os.getenv("UVICORN_ACCESS_LOG_LEVEL", "INFO"),
    }


def _build_formatters(is_json: bool) -> dict[str, dict]:
    """Return formatter configuration for dictConfig."""
    standard = (
        {"()": JsonFormatter}
        if is_json
        else {
            "()": HumanFormatter,
            "format": "%(asctime)s | %(levelname)s | %(message)s%(context_suffix)s | req=%(request_id)s sess=%(session_id)s | %(name)s",
        }
    )
    return {
        "standard": standard,
        "uvicorn": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": "%(levelprefix)s %(client_addr)s rid=%(request_id)s - '%(request_line)s' %(status_code)s",
        },
    }


def _build_handlers(log_level: str, app_log_path: str, access_log_path: str) -> dict[str, dict]:
    """Return handler configuration shared across console and file outputs."""
    base_filters = ["context", "redact"]
    return {
        "app_console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": log_level,
            "filters": base_filters,
        },
        "app_file": {
            "class": "logging.FileHandler",
            "formatter": "standard",
            "level": log_level,
            "filename": app_log_path,
            "encoding": "utf-8",
            "filters": base_filters,
        },
        "uvicorn_console": {
            "class": "logging.StreamHandler",
            "formatter": "uvicorn",
            "filters": base_filters,
        },
        "uvicorn_file": {
            "class": "logging.FileHandler",
            "formatter": "uvicorn",
            "filename": access_log_path,
            "encoding": "utf-8",
            "filters": base_filters,
        },
    }


def _build_loggers(levels: dict[str, str]) -> dict[str, dict]:
    """Return logger configuration ensuring access logs go to separate handlers."""
    return {
        "": {
            "handlers": ["app_console", "app_file"],
            "level": levels["app"],
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["app_console", "app_file"],
            "level": levels["uvicorn"],
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["app_console", "app_file"],
            "level": levels["uvicorn"],
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["uvicorn_console", "uvicorn_file"],
            "level": levels["uvicorn_access"],
            "propagate": False,
        },
    }


def _build_logging_config(
    log_level: str, app_log_path: str, access_log_path: str, is_json: bool
) -> dict:
    """Assemble the combined dictConfig payload."""
    levels = _resolve_log_levels(log_level)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": _build_formatters(is_json),
        "handlers": _build_handlers(log_level, app_log_path, access_log_path),
        "filters": {
            "context": {"()": ContextFilter},
            "redact": {"()": RedactFilter},
        },
        "loggers": _build_loggers(levels),
    }


def setup_logging() -> None:
    """Configure structured logging for the application with console + file handlers.

    Always writes logs to `logs/app.log` and access logs to `logs/access.log`.
    At each process start, existing logs are archived under `logs/archive/YYYY-MM-DD_HH-MM-SS/`.
    """
    # Avoid reconfiguration when setup is invoked multiple times (e.g., tests)
    if getattr(setup_logging, "_configured", False):
        return

    log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("APP_LOG_FORMAT", "text").lower()
    is_json = fmt == "json"

    app_log_path, access_log_path = _prepare_file_logging()
    config = _build_logging_config(log_level, app_log_path, access_log_path, is_json)
    dictConfig(config)

    logging.captureWarnings(True)
    setup_logging._configured = True
