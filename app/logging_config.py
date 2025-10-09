import logging
import os
from logging.config import dictConfig
from pathlib import Path
from datetime import datetime
import shutil
import json
from app.logging_context import ContextFilter, RedactFilter


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


def setup_logging() -> None:
    """Configure structured logging for the application with console + file handlers.

    Always writes logs to `logs/app.log` and access logs to `logs/access.log`.
    At each process start, existing logs are archived under `logs/archive/YYYY-MM-DD_HH-MM-SS/`.
    """
    log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()

    # Prepare file paths and rotate any existing logs for this process
    app_log_path, access_log_path = _prepare_file_logging()

    # Avoid reconfiguration when setup is invoked multiple times (e.g., tests)
    if getattr(setup_logging, "_configured", False):
        return

    fmt = os.getenv("APP_LOG_FORMAT", "text").lower()
    is_json = fmt == "json"

    # Simple JSON formatter using standard logging
    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:  # noqa: D401
            base = {
                "time": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "request_id": getattr(record, "request_id", None),
                "session_id": getattr(record, "session_id", None),
            }
            # Add commonly useful fields if present
            for attr in ("filename", "lineno", "funcName"):
                base[attr] = getattr(record, attr, None)
            if record.exc_info:
                base["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(base, ensure_ascii=False)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": (
                    {
                        "format": "%(asctime)s | %(levelname)s | %(name)s | rid=%(request_id)s sid=%(session_id)s | %(message)s",
                        "class": "logging.Formatter",
                    }
                    if not is_json
                    else {"()": JsonFormatter}
                ),
                "uvicorn": {
                    "()": "uvicorn.logging.AccessFormatter",
                    "fmt": "%(levelprefix)s %(client_addr)s rid=%(request_id)s - '%(request_line)s' %(status_code)s",
                },
            },
            "handlers": {
                # App logs
                "app_console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": log_level,
                    "filters": ["context", "redact"],
                },
                "app_file": {
                    "class": "logging.FileHandler",
                    "formatter": "standard",
                    "level": log_level,
                    "filename": app_log_path,
                    "encoding": "utf-8",
                    "filters": ["context", "redact"],
                },

                # Uvicorn access logs
                "uvicorn_console": {
                    "class": "logging.StreamHandler",
                    "formatter": "uvicorn",
                    "filters": ["context", "redact"],
                },
                "uvicorn_file": {
                    "class": "logging.FileHandler",
                    "formatter": "uvicorn",
                    "filename": access_log_path,
                    "encoding": "utf-8",
                    "filters": ["context", "redact"],
                },
            },
            "filters": {
                "context": {"()": ContextFilter},
                "redact": {"()": RedactFilter},
            },
            "loggers": {
                # Root/app logger
                "": {
                    "handlers": ["app_console", "app_file"],
                    "level": log_level,
                    "propagate": False,
                },
                # Uvicorn framework logs → app handlers so they land in app.log too
                "uvicorn": {
                    "handlers": ["app_console", "app_file"],
                    "level": os.getenv("UVICORN_LOG_LEVEL", log_level),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["app_console", "app_file"],
                    "level": os.getenv("UVICORN_LOG_LEVEL", log_level),
                    "propagate": False,
                },
                # Access logs → separate access file + console
                "uvicorn.access": {
                    "handlers": ["uvicorn_console", "uvicorn_file"],
                    "level": os.getenv("UVICORN_ACCESS_LOG_LEVEL", "INFO"),
                    "propagate": False,
                },
            },
        }
    )

    logging.captureWarnings(True)
    setup_logging._configured = True
