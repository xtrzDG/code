"""
What the platform-admin alerts about sign-in codes share: one alert per key
per hour and process, and an e-mail to every PLATFORM_ADMIN_EMAILS address
(when SMTP is set up). An e-mail that fails is logged, never raised.
"""

import logging
import threading

from typed_time_provider import Microseconds, WallClock

from app.contracts.messaging_clients import EmailSenderClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.users.constrained_strings import EmailAddress

ALERT_INTERVAL_MICROSECONDS: int = 60 * 60 * 1_000_000


class HourlyAlertGate:
    """Lets the first alert of a key through, then none for an hour."""

    def __init__(self, wall_clock: WallClock[Microseconds]) -> None:
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._last_alerts: dict[str, int] = {}
        self._lock: threading.Lock = threading.Lock()

    def claim(self, key: str) -> bool:
        """True for the first alert of this key within an hour."""

        now: int = int(self._wall_clock.now_unix())
        with self._lock:
            last: int | None = self._last_alerts.get(key)
            if last is not None and now - last < ALERT_INTERVAL_MICROSECONDS:
                return False

            self._last_alerts[key] = now
            return True


def email_platform_admins(
    email_client: EmailSenderClientContract | None,
    recipients: list[EmailAddress],
    summary: str,
    what_to_check: str,
    logger: logging.Logger,
) -> None:
    """The summary and what to check, to every platform admin address."""

    if email_client is None:
        return

    for recipient in recipients:
        try:
            email_client.send_email(
                recipient=recipient,
                subject=EmailSubject(f"[Assistant Workshop] {summary}"),
                text_body=EmailBodyText(f"{summary}\n\n{what_to_check}\n"),
                html_body=None,
            )
        except ExternalServiceError as error:
            logger.error("Platform admin alert e-mail failed: %s", error)
