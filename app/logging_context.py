import logging
from contextvars import ContextVar
from typing import Optional


# Context variables populated per request by middleware
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


class ContextFilter(logging.Filter):
    """Injects contextvars (request_id, session_id) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        """Attach contextual identifiers to the log record before emission."""
        rid = request_id_var.get()
        sid = session_id_var.get()
        if not hasattr(record, "request_id"):
            record.request_id = rid
        if not hasattr(record, "session_id"):
            record.session_id = sid
        return True


class RedactFilter(logging.Filter):
    """Very light redaction for common secrets in messages.

    This is a safety net; avoid logging sensitive data explicitly in code.
    """

    REDACTIONS = (
        ("Bearer ", "Bearer [REDACTED]"),
        ("OPENAI_API_KEY", "OPENAI_API_KEY=[REDACTED]"),
    )

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        """Redact known secret patterns from the log record."""
        try:
            record.msg = self._redact_value(record.msg)
            if record.args:
                record.args = self._redact_args(record.args)
        except Exception:
            pass
        return True

    def _redact_args(self, args):
        """Apply redaction to common arg container types."""
        if isinstance(args, dict):
            return {
                key: self._redact_value(value)
                if isinstance(value, str)
                else value
                for key, value in args.items()
            }
        if isinstance(args, list):
            return [self._redact_value(arg) if isinstance(arg, str) else arg for arg in args]
        if isinstance(args, tuple):
            return tuple(self._redact_value(arg) if isinstance(arg, str) else arg for arg in args)
        return self._redact_value(args) if isinstance(args, str) else args

    def _redact_value(self, value):
        """Redact a single value if it contains secret markers."""
        if not isinstance(value, str):
            return value
        result = value
        for needle, replacement in self.REDACTIONS:
            if needle in result:
                result = result.replace(needle, replacement)
        return result
