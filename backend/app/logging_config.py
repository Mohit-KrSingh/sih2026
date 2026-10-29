"""Logging configuration with automatic APAAR ID redaction/masking."""

import logging
import re
from typing import Any

# Match 12-digit APAAR IDs (optional whitespace or hyphens: 1234 5678 9012 or 123456789012)
APAAR_LOG_PATTERN = re.compile(r"\b(?:\d{4}[\s-]?\d{4}[\s-]?|\d{8})(\d{4})\b")


def mask_apaar_string(val: str) -> str:
    """Mask a 12-digit APAAR ID in a string, preserving only the last 4 digits."""
    if not isinstance(val, str):
        return val
    return APAAR_LOG_PATTERN.sub(r"********\1", val)


def mask_data_structures(obj: Any) -> Any:
    """Recursively mask APAAR IDs inside strings, dicts, lists, and tuples."""
    if isinstance(obj, str):
        return mask_apaar_string(obj)
    elif isinstance(obj, dict):
        return {k: mask_data_structures(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [mask_data_structures(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(mask_data_structures(item) for item in obj)
    return obj


class ApaarIdMaskingFilter(logging.Filter):
    """Logging filter that masks 12-digit APAAR IDs in record messages and record arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_apaar_string(record.msg)
        if record.args:
            record.args = mask_data_structures(record.args)
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger and existing handlers with APAAR ID masking."""
    root_logger = logging.getLogger()
    masking_filter = ApaarIdMaskingFilter()

    # Ensure root logger has the filter
    if not any(isinstance(f, ApaarIdMaskingFilter) for f in root_logger.filters):
        root_logger.addFilter(masking_filter)

    # Attach filter to all existing handlers on root and uvicorn loggers
    target_loggers = [
        root_logger,
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.access"),
        logging.getLogger("uvicorn.error"),
        logging.getLogger("app"),
    ]

    for log in target_loggers:
        if not any(isinstance(f, ApaarIdMaskingFilter) for f in log.filters):
            log.addFilter(masking_filter)
        for handler in log.handlers:
            if not any(isinstance(f, ApaarIdMaskingFilter) for f in handler.filters):
                handler.addFilter(masking_filter)
