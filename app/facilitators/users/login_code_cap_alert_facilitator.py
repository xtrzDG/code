import logging

import sentry_sdk
from typed_time_provider import Microseconds, WallClock

from app.contracts.login_protection import LoginCodeCapAlertFacilitatorContract
from app.contracts.messaging_clients import EmailSenderClientContract
from app.contracts.monitoring import SignalCounterAdapterContract
from app.facilitators.users.hourly_admin_alerts import (
    HourlyAlertGate,
    email_platform_admins,
)
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.constants.users import LoginCodeCap
from app.schemas.dto.login_protection import LoginCodeCapAlert
from app.schemas.typings.users.constrained_strings import EmailAddress

logger: logging.Logger = logging.getLogger(__name__)
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
    request, after the send lock is released. Every refusal is also counted
    in the shared platform signals (the OTP_CAP_TRIPS platform alert reads
    them across every process).
    """

    def __init__(
        self,
        email_client: EmailSenderClientContract | None,
        platform_admin_emails: list[EmailAddress],
        wall_clock: WallClock[Microseconds],
        signal_counter: SignalCounterAdapterContract | None = None,
    ) -> None:
        self._signal_counter: SignalCounterAdapterContract | None = signal_counter
        self._email_client: EmailSenderClientContract | None = email_client
        self._platform_admin_emails: list[EmailAddress] = platform_admin_emails
        self._alert_gate: HourlyAlertGate = HourlyAlertGate(wall_clock)

    def report_cap_reached(self, alert: LoginCodeCapAlert) -> None:
        if self._signal_counter is not None:
            self._signal_counter.count(PlatformSignal.OTP_CAP_TRIP)

        if not self._alert_gate.claim(f"{alert.cap.value}:{alert.country_code or ''}"):
            return

        summary: str = describe_alert(alert)
        logger.warning("%s", summary)
        try:
            sentry_sdk.capture_message(summary, level="warning")
        except Exception:  # noqa: BLE001 - alerting must never fail the caller
            logger.exception("Sentry capture of a login code cap alert failed")

        email_platform_admins(
            self._email_client,
            self._platform_admin_emails,
            summary,
            WHAT_TO_CHECK,
            logger,
        )


def describe_alert(alert: LoginCodeCapAlert) -> str:
    """One English line: which cap refused sends, its limit and country."""

    country: str = "" if alert.country_code is None else f" for {alert.country_code}"
    return (
        f"Login code cap reached{country}: {int(alert.limit)} "
        f"{CAP_DESCRIPTIONS[alert.cap]} in the last hour."
    )
