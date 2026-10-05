"""
Keep widget visitor keys and booking manage links out of the access log.

The widget sends its visitor key in a header; widget.js copies cached from
before that change still put `session_key=` in the poll URL, which uvicorn's
access log would record. A guest's manage link carries its signed token in
the path (/v1/public/bookings/{token}), and whoever holds it may cancel the
booking. The filter rewrites both before the line is written.
"""

import logging
import re

ACCESS_LOGGER_NAME: str = "uvicorn.access"
SESSION_KEY_PATTERN: re.Pattern[str] = re.compile(r"(session_key=)[^&\s]+")
MANAGE_TOKEN_PATTERN: re.Pattern[str] = re.compile(r"(/v1/public/bookings/)[^/?\s]+")
REDACTED_VALUE: str = r"\1REDACTED"
# uvicorn's access record arguments: client, method, path with query, ...
PATH_ARGUMENT_INDEX: int = 2


class SessionKeyRedactionFilter(logging.Filter):
    """
    Replaces `session_key=<value>` and a manage link's token in the logged
    path with REDACTED.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        arguments: object = record.args
        if isinstance(arguments, tuple) and len(arguments) > PATH_ARGUMENT_INDEX:
            redacted: list[object] = list(arguments)
            path: object = redacted[PATH_ARGUMENT_INDEX]
            if isinstance(path, str):
                redacted[PATH_ARGUMENT_INDEX] = MANAGE_TOKEN_PATTERN.sub(
                    REDACTED_VALUE, SESSION_KEY_PATTERN.sub(REDACTED_VALUE, path)
                )
                record.args = tuple(redacted)

        return True


def install_access_log_redaction() -> None:
    """Add the filter to uvicorn's access logger once."""

    access_logger: logging.Logger = logging.getLogger(ACCESS_LOGGER_NAME)
    if not any(
        isinstance(existing, SessionKeyRedactionFilter)
        for existing in access_logger.filters
    ):
        access_logger.addFilter(SessionKeyRedactionFilter())
