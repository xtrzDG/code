"""The log context: bound per request, business and job, carried by every line."""

import io
import json
import logging
import sys
from collections.abc import Iterator

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.observability import LogFormat
from app.schemas.dto.observability import LogContext
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, RequestId
from app.utilities.observability.log_context import (
    bound_log_context,
    current_log_context,
    log_context_of_error,
    restored_log_context,
)
from app.utilities.observability.log_formatting import (
    CONTEXT_FIELDS_ATTRIBUTE,
    JsonLogFormatter,
    LogContextFilter,
    TextLogFormatter,
    redact_secrets,
)
from app.utilities.observability.logging_setup import (
    HANDLER_MARK,
    UVICORN_LOGGER_NAMES,
    configure_logging,
)

BUSINESS_ID: BusinessId = BusinessId("business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10")


@pytest.fixture
def restored_logging() -> Iterator[None]:
    root: logging.Logger = logging.getLogger()
    handlers: list[logging.Handler] = list(root.handlers)
    level: int = root.level
    uvicorn_state = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).propagate,
        )
        for name in UVICORN_LOGGER_NAMES
    }
    yield
    root.handlers = handlers
    root.setLevel(level)
    for name, (uvicorn_handlers, propagate) in uvicorn_state.items():
        logging.getLogger(name).handlers = uvicorn_handlers
        logging.getLogger(name).propagate = propagate


def make_record(message: str, *arguments: object) -> logging.LogRecord:
    return logging.LogRecord(
        name="app.tests",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=arguments,
        exc_info=None,
    )


def test_bindings_nest_and_are_undone_on_exit() -> None:
    assert current_log_context() == LogContext()

    with bound_log_context(request_id=RequestId("req-1")):
        with bound_log_context(business_id=BUSINESS_ID, channel=ChannelKind.TELEGRAM):
            inner: LogContext = current_log_context()
        outer: LogContext = current_log_context()

    assert inner.as_fields() == {
        "request_id": "req-1",
        "business_id": str(BUSINESS_ID),
        "channel": "telegram",
    }
    assert outer.as_fields() == {"request_id": "req-1"}
    assert current_log_context() == LogContext()


def test_an_error_keeps_the_innermost_context_it_left() -> None:
    caught: RuntimeError | None = None
    try:
        with (
            bound_log_context(request_id=RequestId("req-2")),
            bound_log_context(job_name=JobName("send_booking_reminders")),
        ):
            raise RuntimeError("boom")
    except RuntimeError as error:
        caught = error

    assert caught is not None
    assert log_context_of_error(caught).as_fields() == {
        "request_id": "req-2",
        "job_name": "send_booking_reminders",
    }
    # An error never raised inside a binding gets the current context.
    with restored_log_context(LogContext(request_id=RequestId("req-3"))):
        assert log_context_of_error(ValueError()).request_id == RequestId("req-3")


def test_json_lines_carry_the_context_and_the_exception() -> None:
    formatter = JsonLogFormatter()
    with bound_log_context(request_id=RequestId("req-4"), business_id=BUSINESS_ID):
        record = make_record("Booking %s saved", "booking_1")
        LogContextFilter().filter(record)
    try:
        raise ValueError("bad value")
    except ValueError:
        record.exc_info = sys.exc_info()

    entry = json.loads(formatter.format(record))

    assert entry["message"] == "Booking booking_1 saved"
    assert entry["level"] == "WARNING"
    assert entry["logger"] == "app.tests"
    assert entry["request_id"] == "req-4"
    assert entry["business_id"] == str(BUSINESS_ID)
    assert entry["time"].endswith("+00:00")
    assert "ValueError: bad value" in entry["exception"]


def test_text_lines_append_the_context_and_hide_bot_tokens() -> None:
    formatter = TextLogFormatter()
    plain = make_record("Worker started")
    with bound_log_context(job_name=JobName("purge_stale_rows")):
        record = make_record(
            "HTTP Request: POST %s",
            "https://api.telegram.org/bot123456:AAH-secret_token/sendMessage",
        )
        LogContextFilter().filter(record)

    line: str = formatter.format(record)

    assert line.endswith("[job_name=purge_stale_rows]")
    assert "AAH-secret_token" not in line
    assert "/bot<redacted>/sendMessage" in line
    assert formatter.format(plain).endswith("app.tests: Worker started")
    assert redact_secrets("GET /x?access_token=abc&page=2") == (
        "GET /x?access_token=<redacted>&page=2"
    )


def test_the_filter_keeps_fields_already_set_on_a_record() -> None:
    record = make_record("from another thread")
    setattr(record, CONTEXT_FIELDS_ATTRIBUTE, {"job_name": "flush_llm_traces"})

    LogContextFilter().filter(record)

    assert json.loads(JsonLogFormatter().format(record))["job_name"] == (
        "flush_llm_traces"
    )


@pytest.mark.usefixtures("restored_logging")
def test_configure_logging_sends_app_and_uvicorn_lines_to_one_stream() -> None:
    stream = io.StringIO()
    configure_logging(LogFormat.TEXT, stream=io.StringIO())
    handler = configure_logging(LogFormat.JSON, stream=stream)

    with bound_log_context(request_id=RequestId("req-5")):
        logging.getLogger("app.anything").info("app line")
        logging.getLogger("uvicorn.error").info("uvicorn line")
    logging.getLogger("httpx").info("HTTP Request: GET https://example.com")

    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    marked = [
        existing
        for existing in logging.getLogger().handlers
        if getattr(existing, HANDLER_MARK, False)
    ]
    assert marked == [handler]
    assert [line["message"] for line in lines] == ["app line", "uvicorn line"]
    assert {line["request_id"] for line in lines} == {"req-5"}
    for name in UVICORN_LOGGER_NAMES:
        assert logging.getLogger(name).handlers == []
        assert logging.getLogger(name).propagate is True
