"""Which staff notification channels have a provider in this deployment."""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.typings.deliveries.strings import DeliveryErrorText


def is_provider_configured(
    settings: AppSettings,
    channel: ManagerContactChannel,
) -> bool:
    """Whether the platform can send by this channel (not a development log)."""

    match channel:
        case ManagerContactChannel.TELEGRAM:
            return settings.telegram_platform_bot_token is not None
        case ManagerContactChannel.WHATSAPP:
            return (
                settings.whatsapp_notification_phone_number_id is not None
                and settings.whatsapp_notification_template_name is not None
            )
        case ManagerContactChannel.EMAIL:
            return settings.smtp_host is not None and settings.smtp_sender is not None
        case ManagerContactChannel.SMS:
            return (
                settings.twilio_account_sid is not None
                and settings.twilio_auth_token is not None
                and (
                    settings.twilio_sender is not None
                    or settings.twilio_messaging_service_sid is not None
                )
            )


MISSING_PROVIDER_TEXTS: dict[ManagerContactChannel, str] = {
    ManagerContactChannel.TELEGRAM: "TELEGRAM_PLATFORM_BOT_TOKEN is not configured.",
    ManagerContactChannel.WHATSAPP: (
        "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID or WHATSAPP_NOTIFICATION_TEMPLATE "
        "is not configured."
    ),
    ManagerContactChannel.EMAIL: "SMTP_HOST and SMTP_FROM are not configured.",
    ManagerContactChannel.SMS: (
        "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and a sender are not configured."
    ),
}


def missing_staff_provider(
    settings: AppSettings,
    channel: ManagerContactChannel,
) -> DeliveryErrorText | None:
    """
    Why a channel cannot deliver here, None when it can. Telegram and
    WhatsApp need their provider everywhere (their delivery is real);
    e-mail and SMS are written to the log outside production.
    """

    if is_provider_configured(settings, channel):
        return None

    is_logged_in_development: bool = channel in (
        ManagerContactChannel.EMAIL,
        ManagerContactChannel.SMS,
    )
    if is_logged_in_development and (
        settings.environment is not DeploymentEnvironment.PRODUCTION
    ):
        return None

    return DeliveryErrorText(MISSING_PROVIDER_TEXTS[channel])
