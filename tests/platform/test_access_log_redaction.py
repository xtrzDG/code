"""Widget visitor keys never reach the access log."""

import logging

from app.gateways.http.access_log_redaction import (
    ACCESS_LOGGER_NAME,
    SessionKeyRedactionFilter,
    install_access_log_redaction,
)


def access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        ACCESS_LOGGER_NAME,
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", path, "1.1", 200),
        None,
    )


def test_session_keys_in_old_poll_urls_are_redacted() -> None:
    record = access_record(
        "/v1/widget/business_x/messages?session_key=v1_SECRET1234&after=message_1"
    )

    assert SessionKeyRedactionFilter().filter(record) is True
    assert record.getMessage() == (
        '127.0.0.1:5000 - "GET /v1/widget/business_x/messages'
        '?session_key=REDACTED&after=message_1 HTTP/1.1" 200'
    )


def test_other_paths_are_logged_as_they_are() -> None:
    record = access_record("/v1/widget/business_x/messages?after=message_1")

    SessionKeyRedactionFilter().filter(record)

    assert "after=message_1" in record.getMessage()


def test_the_filter_is_installed_once() -> None:
    install_access_log_redaction()
    install_access_log_redaction()

    filters = logging.getLogger(ACCESS_LOGGER_NAME).filters
    assert len([f for f in filters if isinstance(f, SessionKeyRedactionFilter)]) == 1
