import logging
from contextvars import ContextVar
from typing import Optional


# Context variables populated per request by middleware
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


class ContextFilter(logging.Filter):
    """Injects contextvars (request_id, session_id) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
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
        try:
            msg = record.msg
            args = record.args

            if isinstance(msg, str):
                for needle, repl in self.REDACTIONS:
                    if needle in msg:
                        msg = msg.replace(needle, repl)
                record.msg = msg

            if args:
                changed = False
                new_args = []
                for arg in args:
                    if isinstance(arg, str):
                        redacted = arg
                        for needle, repl in self.REDACTIONS:
                            if needle in redacted:
                                redacted = redacted.replace(needle, repl)
                                changed = True
                        new_args.append(redacted)
                    else:
                        new_args.append(arg)
                if changed:
                    record.args = tuple(new_args)
        except Exception:
            pass
        return True
