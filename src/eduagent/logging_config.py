"""Structured (JSON) logging, so a single essay can be followed from intake
through to the teacher digest. Cloud Logging on Cloud Run parses JSON log lines natively
(severity/message/jsonPayload), so this format is also what makes the
Cloud Run log viewer filterable by essay_id in production, not just locally.

No external dependency (no python-json-logger) -- a small Formatter is
enough and keeps requirements.txt from growing for one formatter.
"""

from __future__ import annotations

import json
import logging
import sys

_RESERVED = frozenset(logging.LogRecord(None, None, "", 0, "", (), None).__dict__.keys()) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        # Any extra=... kwargs passed to the logging call (essay_id, student_id,
        # etc.) ride along as top-level JSON fields -- this is the trace_id
        # correlation mechanism, not a special API.
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_configured = False


def configure_json_logging(level: int = logging.INFO) -> None:
    """Idempotent. Call once per process (Cloud Run instance / script start)."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    _configured = True
