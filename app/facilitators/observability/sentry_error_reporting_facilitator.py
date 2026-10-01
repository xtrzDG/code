import logging

import sentry_sdk
from sentry_sdk.types import Event, Hint

from app.contracts.observability import ErrorReportingFacilitatorContract
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.typings.platform.strings import PlatformSecret

LOGGER: logging.Logger = logging.getLogger(__name__)
SCRUBBED_EVENT_KEYS: tuple[str, ...] = ("request", "user", "breadcrumbs")


class SentryErrorReportingFacilitator(ErrorReportingFacilitatorContract):
    """
    Reports unexpected errors to Sentry without personal data.

    Request bodies, users and breadcrumbs are removed before sending:
    conversations contain customers' personal data, which must stay in the EU
    processing chain described by the concept.
    """

    def __init__(
        self,
        dsn: PlatformSecret | None,
        environment: DeploymentEnvironment,
    ) -> None:
        self._is_enabled: bool = dsn is not None
        if dsn is None:
            return

        sentry_sdk.init(
            dsn=str(dsn),
            environment=str(environment),
            send_default_pii=False,
            max_request_body_size="never",
            traces_sample_rate=0.0,
            before_send=scrub_event,
        )

    def capture_exception(self, error: BaseException) -> None:
        if not self._is_enabled:
            LOGGER.error("Unexpected error", exc_info=error)
            return

        try:
            sentry_sdk.capture_exception(error)
        except Exception:  # noqa: BLE001 - reporting must never fail the caller
            LOGGER.exception("Sentry capture failed")


def scrub_event(event: Event, hint: Hint) -> Event | None:
    """Drop request data, user data and breadcrumbs from a Sentry event."""

    del hint
    for key in SCRUBBED_EVENT_KEYS:
        event.pop(key, None)  # type: ignore[misc]

    return event
