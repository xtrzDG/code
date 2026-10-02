from enum import StrEnum


class LogFormat(StrEnum):
    """How log lines are written (LOG_FORMAT)."""

    # One JSON object per line with the request, business, conversation and
    # job of the line: for log search in production.
    JSON = "json"
    # One readable line, the same fields appended: for a terminal.
    TEXT = "text"


class ReadinessState(StrEnum):
    """Whether this API instance should receive traffic (GET /readyz)."""

    READY = "ready"
    NOT_READY = "not_ready"


class HealthCheckStatus(StrEnum):
    """Outcome of one check of the readiness report."""

    OK = "ok"
    # Something is wrong, but the instance still serves traffic (a worker
    # heartbeat that is old or missing: requests are answered, jobs wait).
    DEGRADED = "degraded"
    FAILED = "failed"
    # Nothing to check: storage in memory, no database.
    SKIPPED = "skipped"


class DatabaseProbeFailure(StrEnum):
    """Why the readiness probe could not use the database."""

    # No connection could be opened (the server is down or unreachable).
    UNREACHABLE = "unreachable"
    # Every connection of the pool stayed in use for the whole probe.
    POOL_EXHAUSTED = "pool_exhausted"
    # The server took longer than the probe allows to answer `select 1`.
    TIMEOUT = "timeout"
    # The server answered with an error.
    ERROR = "error"


class PeriodicJobOutcome(StrEnum):
    """How the last run of a periodic job in one worker process ended."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WidgetErrorKind(StrEnum):
    """What went wrong in the website widget, as its error beacon reports it."""

    # An exception thrown by the widget's own code.
    SCRIPT_ERROR = "script_error"
    # A promise of the widget's own code rejected without a handler.
    UNHANDLED_REJECTION = "unhandled_rejection"
    # The chat configuration answered with an error status.
    CONFIG_FAILED = "config_failed"


class WidgetErrorPhase(StrEnum):
    """Which part of the widget failed."""

    BOOT = "boot"
    MOUNT = "mount"
    SEND = "send"
    POLL = "poll"
    RENDER = "render"
