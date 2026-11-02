import logging
import threading

import sentry_sdk
from typed_time_provider import Microseconds, WallClock

from app.contracts.messaging_clients import EmailSenderClientContract
from app.contracts.sign_in_alerts import SignInCodeSprayAlertFacilitatorContract
from app.schemas.dto.sign_in_alerts import SignInCodeSprayAlert
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.users.constrained_strings import EmailAddress

logger: logging.Logger = logging.getLogger(__name__)
ALERT_INTERVAL_MICROSECONDS: int = 60 * 60 * 1_000_000
WHAT_TO_CHECK: str = (
    "Each address is still held to its own caps. If this is not an office or "
    "a public network signing many people in, it is likely SMS pumping, an "
    "enumeration of accounts or a takeover attempt: look at the security log "
    "(Admin -> Audit) and the SMS provider's logs for that network, turn on "
    "the Turnstile bot check (TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY) and "
    "block the network at the edge if it goes on."
)


class SignInCodeSprayAlertFacilitator(SignInCodeSprayAlertFacilitatorContract):
    """
    Tells the platform team that one client network asks sign-in codes for
    many different phones and e-mails: a warning in the log, a Sentry event
    (when Sentry is set up) and an e-mail to every PLATFORM_ADMIN_EMAILS
    address (when SMTP is set up). The network is named (an IPv4 address or
    an IPv6 /64), never the phones or e-mails. One alert per network per
    hour and process, so a spray that goes on does not flood the inbox.
    """

    def __init__(
        self,
        email_client: EmailSenderClientContract | None,
        platform_admin_emails: list[EmailAddress],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._email_client: EmailSenderClientContract | None = email_client
        self._platform_admin_emails: list[EmailAddress] = platform_admin_emails
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._last_alerts: dict[str, int] = {}
        self._lock: threading.Lock = threading.Lock()

    def report_code_spray(self, alert: SignInCodeSprayAlert) -> None:
        try:
            if not self._claim_alert(alert):
                return

            summary: str = describe_spray(alert)
            logger.warning("%s", summary)
            try:
                sentry_sdk.capture_message(summary, level="warning")
            except Exception:  # noqa: BLE001 - alerting must never fail the caller
                logger.exception("Sentry capture of a sign-in code spray failed")

            self._email_platform_admins(summary)
        except Exception:  # noqa: BLE001 - a sign-in never fails on its alert
            logger.exception("The sign-in code spray alert failed")

    def _claim_alert(self, alert: SignInCodeSprayAlert) -> bool:
        """True for the first alert of this network within an hour."""

        key: str = str(alert.client_network)
        now: int = int(self._wall_clock.now_unix())
        with self._lock:
            last: int | None = self._last_alerts.get(key)
            if last is not None and now - last < ALERT_INTERVAL_MICROSECONDS:
                return False

            self._last_alerts[key] = now
            return True

    def _email_platform_admins(self, summary: str) -> None:
        if self._email_client is None:
            return

        for recipient in self._platform_admin_emails:
            try:
                self._email_client.send_email(
                    recipient=recipient,
                    subject=EmailSubject(f"[Assistant Workshop] {summary}"),
                    text_body=EmailBodyText(f"{summary}\n\n{WHAT_TO_CHECK}\n"),
                    html_body=None,
                )
            except ExternalServiceError as error:
                logger.error("Sign-in code spray alert e-mail failed: %s", error)


def describe_spray(alert: SignInCodeSprayAlert) -> str:
    """One English line: the network and how many destinations it asked for."""

    return (
        f"Sign-in codes sprayed: the network {alert.client_network} asked codes "
        f"for {int(alert.destination_count)} different phones and e-mails in the "
        f"last hour (alert from {int(alert.threshold)})."
    )
