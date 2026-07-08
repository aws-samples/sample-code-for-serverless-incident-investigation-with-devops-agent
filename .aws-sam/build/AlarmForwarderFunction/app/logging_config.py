"""Structured JSON logging configuration for CloudWatch Logs."""

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON with required fields."""

    def __init__(self, service_name: str = "order-processing-service") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "request_id": getattr(record, "request_id", "N/A"),
            "endpoint": getattr(record, "endpoint", "N/A"),
            "message": record.getMessage(),
        }
        # Include optional structured fields for cross-service correlation
        for key in ("upstream_function", "order_id", "error_detail"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        if record.exc_info and record.exc_info[1]:
            entry["traceback"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logging(service_name: str = "order-processing-service", level: str = "INFO") -> None:
    """Configure the root logger with structured JSON output to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(service_name))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
