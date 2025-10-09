import logging
import os
from logging.config import dictConfig


def setup_logging() -> None:
    """Configure structured logging for the application."""
    log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()

    # Avoid reconfiguration when setup is invoked multiple times (e.g., in tests)
    if getattr(setup_logging, "_configured", False):
        return

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                    "class": "logging.Formatter",
                },
                "uvicorn": {
                    "()": "uvicorn.logging.AccessFormatter",
                    "fmt": "%(levelprefix)s %(client_addr)s - '%(request_line)s' %(status_code)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": log_level,
                },
                "uvicorn.access": {
                    "class": "logging.StreamHandler",
                    "formatter": "uvicorn",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["console"],
                    "level": log_level,
                },
                "uvicorn": {
                    "handlers": ["console"],
                    "level": os.getenv("UVICORN_LOG_LEVEL", log_level),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": os.getenv("UVICORN_LOG_LEVEL", log_level),
                    "handlers": ["console"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["uvicorn.access"],
                    "level": os.getenv("UVICORN_ACCESS_LOG_LEVEL", "INFO"),
                    "propagate": False,
                },
            },
        }
    )

    logging.captureWarnings(True)
    setup_logging._configured = True
