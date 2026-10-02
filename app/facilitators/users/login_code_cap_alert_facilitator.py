import logging
import threading

import sentry_sdk
from typed_time_provider import Microseconds, WallClock

from app.contracts.login_protection import LoginCodeCapAlertFacilitatorContract
from app.contracts.messaging_clients import EmailSenderClientContract
from app.schemas.constants.users import LoginCodeCap
from app.schemas.dto.login_protection import LoginCodeCapAlert
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.users.constrained_strings import EmailAddress

logger: logging.Logger = logging.getLogger(__name__)
ALERT_INTERVAL_MICROSECONDS: int = 60 * 60 * 1_000_000
CAP_DESCRIPTIONS: dict[LoginCodeCap, str] = {
    LoginCodeCap.COUNTRY: (
        "login codes to phones of one country (OTP_SENDS_PER_COUNTRY_PER_HOUR)"
    ),
    LoginCodeCap.NEW_DESTINATIONS: (
        "login codes to new phones and e-mails (OTP_SENDS_PER_HOUR)"
    ),
    LoginCodeCap.VERIFIED_USERS: (
        "login codes to verified users (OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR)"
    ),
}
WHAT_TO_CHECK: str = (
    "Sends over the cap are refused until the hour passes. If this is not a "
    "real rush of sign-ins, it is likely SMS pumping or a login flood: look "
    "at the SMS provider's logs (destinations, countries), turn on the "
    "Turnstile bot check (TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY) and add "
    "abused countries to OTP_HIGH_RISK_COUNTRIES or ranges to "
    "OTP_DENIED_PHONE_PREFIXES. If it is real demand, raise the cap."
)


class LoginCodeCapAlertFacilitator(LoginCodeCapAlertFacilitatorContract):
    """
    Tells the platform team that a platform cap refused login code sends:
    a warning in the log, a Sentry event (when Sentry is set up) and an
    e-mail to every PLATFORM_ADMIN_EMAILS address (when SMTP is set up).

    One alert per cap (and country) per hour and process, so an attack that
    keeps hitting a cap does not flood the inbox. It runs in the refused
    request, after the send lock is released.
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

    def report_cap_reached(self, alert: LoginCodeCapAlert) -> None:
        if not self._claim_alert(alert):
            return

        summary: str = describe_alert(alert)
        logger.warning("%s", summary)
        try:
            sentry_sdk.capture_message(summary, level="warning")
        except Exception:  # noqa: BLE001 - alerting must never fail the caller
            logger.exception("Sentry capture of a login code cap alert failed")

        self._email_platform_admins(summary)

    def _claim_alert(self, alert: LoginCodeCapAlert) -> bool:
        """True for the first alert of this cap and country within an hour."""

        key: str = f"{alert.cap.value}:{alert.country_code or ''}"
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
                logger.error("Login code cap alert e-mail failed: %s", error)


def describe_alert(alert: LoginCodeCapAlert) -> str:
    """One English line: which cap refused sends, its limit and country."""

    country: str = "" if alert.country_code is None else f" for {alert.country_code}"
    return (
        f"Login code cap reached{country}: {int(alert.limit)} "
        f"{CAP_DESCRIPTIONS[alert.cap]} in the last hour."
    )
