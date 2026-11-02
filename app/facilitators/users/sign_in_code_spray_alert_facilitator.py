import logging

import sentry_sdk
from typed_time_provider import Microseconds, WallClock

from app.contracts.messaging_clients import EmailSenderClientContract
from app.contracts.sign_in_alerts import SignInCodeSprayAlertFacilitatorContract
from app.facilitators.users.hourly_admin_alerts import (
    HourlyAlertGate,
    email_platform_admins,
)
from app.schemas.dto.sign_in_alerts import SignInCodeSprayAlert
from app.schemas.typings.users.constrained_strings import EmailAddress

logger: logging.Logger = logging.getLogger(__name__)
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
        self._alert_gate: HourlyAlertGate = HourlyAlertGate(wall_clock)

    def report_code_spray(self, alert: SignInCodeSprayAlert) -> None:
        try:
            if not self._alert_gate.claim(str(alert.client_network)):
                return

            summary: str = describe_spray(alert)
            logger.warning("%s", summary)
            try:
                sentry_sdk.capture_message(summary, level="warning")
            except Exception:  # noqa: BLE001 - alerting must never fail the caller
                logger.exception("Sentry capture of a sign-in code spray failed")

            email_platform_admins(
                self._email_client,
                self._platform_admin_emails,
                summary,
                WHAT_TO_CHECK,
                logger,
            )
        except Exception:  # noqa: BLE001 - a sign-in never fails on its alert
            logger.exception("The sign-in code spray alert failed")


def describe_spray(alert: SignInCodeSprayAlert) -> str:
    """One English line: the network and how many destinations it asked for."""

    return (
        f"Sign-in codes sprayed: the network {alert.client_network} asked codes "
        f"for {int(alert.destination_count)} different phones and e-mails in the "
        f"last hour (alert from {int(alert.threshold)})."
    )
