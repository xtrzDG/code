"""
Logging of the API and worker processes: one handler on the root logger in
the configured format (LOG_FORMAT), which uvicorn's own loggers use too.
"""

import logging
import sys
from typing import TextIO

from app.schemas.constants.observability import LogFormat
from app.utilities.observability.log_formatting import (
    JsonLogFormatter,
    LogContextFilter,
    TextLogFormatter,
)

# uvicorn installs its own handlers before it calls the application factory;
# they are replaced so that its lines have the same format and context.
UVICORN_LOGGER_NAMES: tuple[str, ...] = ("uvicorn", "uvicorn.error", "uvicorn.access")
# Libraries that log every request at INFO (with the full URL, where some
# providers put credentials): only their warnings are kept.
QUIET_LOGGER_NAMES: tuple[str, ...] = ("httpx", "httpcore", "urllib3", "hpack")
# Marks the handler this module installed, so a second call replaces it.
HANDLER_MARK: str = "_workshop_log_handler"


def configure_logging(
    log_format: LogFormat,
    level: int = logging.INFO,
    stream: TextIO | None = None,
) -> logging.Handler:
    """
    Send every log line (application, uvicorn, libraries) to one stream in
    `log_format` with the log context; INFO and above by default. Calling it
    again replaces the handler it installed before. Returns the handler.
    """

    handler = logging.StreamHandler(sys.stderr if stream is None else stream)
    handler.addFilter(LogContextFilter())
    handler.setFormatter(
        JsonLogFormatter() if log_format is LogFormat.JSON else TextLogFormatter()
    )
    setattr(handler, HANDLER_MARK, True)

    root: logging.Logger = logging.getLogger()
    for existing in list(root.handlers):
        if getattr(existing, HANDLER_MARK, False):
            root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    for logger_name in UVICORN_LOGGER_NAMES:
        uvicorn_logger: logging.Logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
    for logger_name in QUIET_LOGGER_NAMES:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    return handler
