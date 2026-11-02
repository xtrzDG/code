"""
Log lines never carry a phone number or an e-mail address: the handler's
filter masks them in the message and its arguments and hands the formatter
a copy, so structured fields, ids, amounts and every other handler of the
record stay as they are.
"""

import io
import json
import logging
from collections.abc import Iterator

import pytest

from app.schemas.constants.observability import LogFormat
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.observability.contact_log_masking import (
    ContactDetailsLogFilter,
    mask_contact_details,
)
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.log_formatting import log_fields
from app.utilities.observability.logging_setup import (
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


@pytest.mark.parametrize(
    ("text", "masked"),
    [
        ("code sent to +393331234567", "code sent to [phone]"),
        ("call +39 333 123 4567 now", "call [phone] now"),
        ("US +1 (415) 555-0100.", "US [phone]."),
        ("owner Mario.Rossi@Example.it asked", "owner [email] asked"),
        ("both: +995555123456, a@b.example", "both: [phone], [email]"),
    ],
)
def test_phones_and_emails_are_masked(text: str, masked: str) -> None:
    assert mask_contact_details(text) == masked


@pytest.mark.parametrize(
    "text",
    [
        f"business {BUSINESS_ID} job 550e8400-e29b-41d4-a716-446655440000",
        "Request threads: 40; database connections: 10",
        "client 10.123.45.67:41234 waited 1234567 ms at 2026-11-02 10:15:30",
        "price 1500000 minor units, Telegram chat 123456789",
        "80 % of the budget",
    ],
)
def test_ids_amounts_addresses_and_times_stay(text: str) -> None:
    assert mask_contact_details(text) == text


def test_the_filter_masks_the_arguments_and_leaves_the_record_alone() -> None:
    record = logging.LogRecord(
        "app.tests",
        logging.INFO,
        __file__,
        1,
        "Code for %s sent to %s",
        ("+393331234567", "a@b.example"),
        None,
    )

    masked = ContactDetailsLogFilter().filter(record)

    assert isinstance(masked, logging.LogRecord)
    assert masked is not record
    assert masked.getMessage() == "Code for [phone] sent to [email]"
    assert record.getMessage() == "Code for +393331234567 sent to a@b.example"


def test_a_record_without_contacts_or_with_a_broken_format_passes_as_it_is() -> None:
    plain = logging.LogRecord(
        "app.tests", logging.INFO, __file__, 1, "%d jobs", (3,), None
    )
    broken = logging.LogRecord(
        "app.tests", logging.INFO, __file__, 1, "%d jobs", ("x",), None
    )

    assert ContactDetailsLogFilter().filter(plain) is True
    assert ContactDetailsLogFilter().filter(broken) is True


@pytest.mark.usefixtures("restored_logging")
def test_json_lines_are_masked_and_keep_their_fields() -> None:
    stream = io.StringIO()
    configure_logging(LogFormat.JSON, stream=stream)
    captured: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    logging.getLogger().addHandler(Capture())
    with bound_log_context(business_id=BUSINESS_ID):
        logging.getLogger("app.tests").info(
            "Login code sent to %s", "+39 333 123 4567", extra=log_fields(attempt=2)
        )

    entry = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert entry["message"] == "Login code sent to [phone]"
    assert entry["business_id"] == str(BUSINESS_ID)
    assert entry["attempt"] == 2
    # Another handler of the same record still gets it unmasked.
    assert captured[-1].getMessage() == "Login code sent to +39 333 123 4567"


@pytest.mark.usefixtures("restored_logging")
def test_text_lines_are_masked_too() -> None:
    stream = io.StringIO()
    configure_logging(LogFormat.TEXT, stream=stream)

    logging.getLogger("app.tests").warning(
        "Mail to %s bounced", "owner@workshop.example"
    )

    assert "Mail to [email] bounced" in stream.getvalue()
    assert "owner@workshop.example" not in stream.getvalue()
