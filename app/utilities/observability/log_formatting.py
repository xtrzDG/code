"""
Log line formats: JSON for production log search, readable text for a
terminal. Both carry the log context (request, business, conversation,
channel, job), the measured fields of the line itself (`log_fields`, e.g.
how long a job waited before a worker took it) and hide secrets (tokens in
URLs, Authorization credentials, provider keys), card and account numbers
and contacts in messages and tracebacks (`redact_log_text`).
"""

import json
import logging
import re
from datetime import UTC, datetime
from typing import cast

from app.utilities.observability.contact_log_masking import mask_contact_details
from app.utilities.observability.log_context import current_log_context
from app.utilities.privacy.sensitive_numbers import mask_sensitive_numbers

# Set on every record by LogContextFilter: the context fields of the line.
CONTEXT_FIELDS_ATTRIBUTE: str = "log_context_fields"
# Set by the caller (`extra=log_fields(...)`): the line's own measured values.
LINE_FIELDS_ATTRIBUTE: str = "log_fields"
# Telegram bot tokens travel in the URL path (/bot<id>:<secret>/method), and
# HTTP client libraries log request URLs.
SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"/bot\d+:[A-Za-z0-9_-]+"), "/bot<redacted>"),
    (
        re.compile(r"(?i)\b(access_token|api_key|token|key|secret)=[^&\s\"']+"),
        r"\1=<redacted>",
    ),
    # The credentials of an Authorization header ("Bearer eyJ...").
    (re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 <redacted>"),
    # Stripe secret and restricted keys, webhook signing secrets (Stripe's
    # and the platform's), and the platform's API keys past their prefix.
    (
        re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]+|\bwhsec_[A-Za-z0-9_+/=-]+"),
        "<redacted>",
    ),
    (re.compile(r"\b(awk_[a-z2-7]{8})_[A-Za-z0-9]+"), r"\1_<redacted>"),
)
TEXT_FORMAT: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"
# NEL, LINE SEPARATOR and PARAGRAPH SEPARATOR as JSON escapes.
JSON_LINE_BREAK_ESCAPES: dict[int, str] = {
    0x85: "\\u0085",
    0x2028: "\\u2028",
    0x2029: "\\u2029",
}


class LogContextFilter(logging.Filter):
    """
    Copies the current log context onto each record as it is emitted (in
    the thread and context that logged it), so formatters, also deferred
    ones, see the context of the line.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, CONTEXT_FIELDS_ATTRIBUTE):
            setattr(record, CONTEXT_FIELDS_ATTRIBUTE, current_log_context().as_fields())

        return True


class JsonLogFormatter(logging.Formatter):
    """
    One JSON object per line: time (UTC, ISO 8601), level, logger, thread,
    message, the context fields, and the exception or stack when present.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "thread": record.threadName,
            "message": redact_log_text(record.getMessage()),
        }
        entry.update(read_context_fields(record))
        entry.update(read_line_fields(record))
        if record.exc_info:
            entry["exception"] = redact_log_text(self.formatException(record.exc_info))
        if record.stack_info:
            entry["stack"] = self.formatStack(record.stack_info)

        # json.dumps escapes \n, \r and the other C0 controls; the line
        # separators some readers also break on are escaped here, so a
        # value never starts a line of its own (log injection, LOG-03).
        return json.dumps(entry, ensure_ascii=False, default=str).translate(
            JSON_LINE_BREAK_ESCAPES
        )


class TextLogFormatter(logging.Formatter):
    """`time LEVEL logger: message [field=value ...]` for a terminal."""

    def __init__(self) -> None:
        super().__init__(TEXT_FORMAT)

    def format(self, record: logging.LogRecord) -> str:
        line: str = redact_log_text(super().format(record))
        fields: dict[str, object] = {
            **read_context_fields(record),
            **read_line_fields(record),
        }
        if not fields:
            return line

        first_line, separator, rest = line.partition("\n")
        context: str = " ".join(f"{name}={value}" for name, value in fields.items())
        return f"{first_line} [{context}]{separator}{rest}"


def read_context_fields(record: logging.LogRecord) -> dict[str, str]:
    """The context fields LogContextFilter put on the record (or the current)."""

    fields: object = getattr(record, CONTEXT_FIELDS_ATTRIBUTE, None)
    if isinstance(fields, dict):
        items: list[tuple[object, object]] = list(
            cast(dict[object, object], fields).items()
        )
        return {str(name): str(value) for name, value in items}

    return current_log_context().as_fields()


def log_fields(**fields: int | str) -> dict[str, object]:
    """
    The `extra` of a log call whose line carries measured values as fields
    of their own (JSON keys, `name=value` in text), e.g.
    `LOGGER.info("Job picked up", extra=log_fields(pickup_delay_ms=120))`.
    Ids and numbers only, never texts or contact data.
    """

    return {LINE_FIELDS_ATTRIBUTE: dict(fields)}


def read_line_fields(record: logging.LogRecord) -> dict[str, object]:
    """The fields the caller attached with `log_fields` (none by default)."""

    fields: object = getattr(record, LINE_FIELDS_ATTRIBUTE, None)
    if not isinstance(fields, dict):
        return {}

    items: list[tuple[object, object]] = list(
        cast(dict[object, object], fields).items()
    )
    return {str(name): value for name, value in items}


def redact_log_text(text: str) -> str:
    """
    A log text (a message, a traceback) without secrets, card, security
    code, IBAN and ID numbers, e-mail addresses and international phone
    numbers.
    """

    return mask_contact_details(mask_sensitive_numbers(redact_secrets(text)))


def redact_secrets(text: str) -> str:
    """
    Hide bot tokens, credential query parameters, Authorization credentials
    and provider keys in a log text.
    """

    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)

    return text
