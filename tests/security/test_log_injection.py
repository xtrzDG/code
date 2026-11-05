"""
A logged value never forges a log line (LOG-03, ASVS V16.4.1): in the JSON
format production requires, a value with a line break (CR, LF, NEL, the
Unicode line and paragraph separators) stays inside its field, escaped, so
every record is exactly one line and reads back as the value it logged.
"""

import io
import json
import logging
from collections.abc import Generator

import pytest

from app.schemas.typings.platform.constrained_strings import RequestId
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.log_formatting import (
    JsonLogFormatter,
    LogContextFilter,
    log_fields,
)
from app.utilities.observability.security_events import (
    AUTHORIZATION_DENIED,
    SECURITY_LOGGER,
    log_security_event,
)

FORGED: str = '"}\n{"level": "CRITICAL", "message": "admin signed in"}'
BREAKS: tuple[str, ...] = ("\n", "\r\n", "\r", "\u0085", " ", " ")


@pytest.fixture
def json_lines() -> Generator[io.StringIO]:
    """What the JSON handler writes, for this test's loggers only."""

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(LogContextFilter())
    handler.setFormatter(JsonLogFormatter())
    loggers = (logging.getLogger("tests.log_injection"), SECURITY_LOGGER)
    for logger in loggers:
        logger.addHandler(handler)
    try:
        yield stream
    finally:
        for logger in loggers:
            logger.removeHandler(handler)


def records(stream: io.StringIO) -> list[dict[str, object]]:
    text: str = stream.getvalue()
    lines: list[str] = text.split("\n")
    assert lines[-1] == "", "every record ends its own line"
    return [json.loads(line) for line in lines[:-1]]


@pytest.mark.parametrize("line_break", BREAKS)
def test_a_value_with_a_line_break_is_one_escaped_line(
    json_lines: io.StringIO, line_break: str
) -> None:
    name: str = f"mario{line_break}rossi{FORGED}"
    logger = logging.getLogger("tests.log_injection")
    logger.setLevel(logging.INFO)

    with bound_log_context(request_id=RequestId("req-injection")):
        logger.info(
            "Sign-in code asked for %s", name, extra=log_fields(display_name=name)
        )

    raw: str = json_lines.getvalue()
    assert raw.count("\n") == 1
    for separator in ("\r", "\u0085", " ", " "):
        assert separator not in raw
    [record] = records(json_lines)
    assert record["message"] == f"Sign-in code asked for {name}"
    assert record["display_name"] == name
    assert record["request_id"] == "req-injection"
    assert record["level"] == "INFO"


def test_a_security_line_with_a_forged_path_stays_one_line(
    json_lines: io.StringIO,
) -> None:
    log_security_event(
        AUTHORIZATION_DENIED,
        path="GET /v1/x\nsecurity_event=none",
        reason=f"reason{FORGED}",
        client_address="203.0.113.5\r\n",
    )

    [record] = records(json_lines)
    assert record["security_event"] == AUTHORIZATION_DENIED
    assert record["path"] == "GET /v1/x\nsecurity_event=none"
    assert record["reason"] == f"reason{FORGED}"
    assert record["client_network"] == "203.0.113.0/24"


def test_an_exception_message_with_line_breaks_stays_in_its_record(
    json_lines: io.StringIO,
) -> None:
    logger = logging.getLogger("tests.log_injection")
    try:
        raise ValueError(f"bad input{FORGED}")
    except ValueError:
        logger.exception("Request failed level=CRITICAL")

    [record] = records(json_lines)
    assert record["message"] == "Request failed level=CRITICAL"
    assert "bad input" in str(record["exception"])
