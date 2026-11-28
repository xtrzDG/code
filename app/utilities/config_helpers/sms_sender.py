"""
Whether the platform can send SMS, decided once for every SMS it sends
(login codes, staff notifications, text-backs): the Twilio account
(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN) with a sender
(TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID). The account alone
rents phone numbers and signs the call fallback; its sender is set only
once the phone carriers approved it (a US A2P 10DLC campaign or a verified
toll-free number), and until then SMS is off and the cabinet says why.
"""

import logging

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.messaging import SmsUnavailableReason
from app.schemas.dto.messaging import TwilioSmsSender

LOGGER: logging.Logger = logging.getLogger(__name__)

# The start-up line of an account without a sender (`report_sms_sender`).
SMS_OFF_MESSAGE: str = (
    "SMS is off: the Twilio account has no sender (TWILIO_FROM_NUMBER or "
    "TWILIO_MESSAGING_SERVICE_SID). Phone numbers and calls work; login codes, "
    "staff notifications and text-backs by SMS are not sent."
)


def platform_sms_sender(settings: AppSettings) -> TwilioSmsSender | None:
    """The Twilio account with its sender; None when the platform sends no SMS."""

    if (
        settings.twilio_account_sid is None
        or settings.twilio_auth_token is None
        or (
            settings.twilio_sender is None
            and settings.twilio_messaging_service_sid is None
        )
    ):
        return None

    return TwilioSmsSender(
        account_sid=settings.twilio_account_sid,
        auth_token=settings.twilio_auth_token,
        sender=settings.twilio_sender,
        messaging_service_sid=settings.twilio_messaging_service_sid,
    )


def platform_sms_unavailable_reason(
    settings: AppSettings,
) -> SmsUnavailableReason | None:
    """
    Why the platform sends no SMS: NO_SENDER while its Twilio account waits
    for a sender, NOT_CONFIGURED without an account; None when it sends.
    """

    if platform_sms_sender(settings) is not None:
        return None

    if (
        settings.twilio_account_sid is not None
        and settings.twilio_auth_token is not None
    ):
        return SmsUnavailableReason.NO_SENDER

    return SmsUnavailableReason.NOT_CONFIGURED


def report_sms_sender(settings: AppSettings) -> None:
    """One INFO line at start-up while the Twilio account has no sender."""

    if platform_sms_unavailable_reason(settings) is SmsUnavailableReason.NO_SENDER:
        LOGGER.info(SMS_OFF_MESSAGE)
