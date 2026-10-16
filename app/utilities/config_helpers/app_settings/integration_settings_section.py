"""META_*, WHATSAPP_*, TELEGRAM_PLATFORM_*, GOOGLE_OAUTH_* and FLITT_*."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateName,
)
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
)


class IntegrationSettingsSection(TypedDict):
    """The `AppSettings` fields of the messengers, the calendar and payments."""

    meta_app_id: PlatformIdentifier | None
    meta_app_secret: PlatformSecret | None
    meta_verify_token: PlatformSecret | None
    whatsapp_system_user_token: PlatformSecret | None
    whatsapp_notification_phone_number_id: MetaObjectId | None
    whatsapp_notification_template_name: WhatsAppTemplateName | None
    whatsapp_reminder_template_name: WhatsAppTemplateName | None
    whatsapp_owner_report_template_name: WhatsAppTemplateName | None
    whatsapp_booking_confirmation_template_name: WhatsAppTemplateName | None
    telegram_platform_bot_token: PlatformSecret | None
    google_oauth_client_id: PlatformIdentifier | None
    google_oauth_client_secret: PlatformSecret | None
    flitt_merchant_id: PlatformIdentifier | None
    flitt_secret_key: PlatformSecret | None


def read_integration_settings(
    environment_variables: Mapping[str, str],
) -> IntegrationSettingsSection:
    def secret(variable_name: str) -> PlatformSecret | None:
        return optional_text(environment_variables, variable_name, PlatformSecret)

    def identifier(variable_name: str) -> PlatformIdentifier | None:
        return optional_text(environment_variables, variable_name, PlatformIdentifier)

    return IntegrationSettingsSection(
        meta_app_id=identifier("META_APP_ID"),
        meta_app_secret=secret("META_APP_SECRET"),
        meta_verify_token=secret("META_VERIFY_TOKEN"),
        whatsapp_system_user_token=secret("WHATSAPP_SYSTEM_USER_TOKEN"),
        whatsapp_notification_phone_number_id=optional_text(
            environment_variables,
            "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID",
            MetaObjectId,
        ),
        whatsapp_notification_template_name=optional_text(
            environment_variables,
            "WHATSAPP_NOTIFICATION_TEMPLATE",
            WhatsAppTemplateName,
        ),
        whatsapp_reminder_template_name=optional_text(
            environment_variables,
            "WHATSAPP_REMINDER_TEMPLATE",
            WhatsAppTemplateName,
        ),
        whatsapp_owner_report_template_name=optional_text(
            environment_variables,
            "WHATSAPP_OWNER_REPORT_TEMPLATE",
            WhatsAppTemplateName,
        ),
        whatsapp_booking_confirmation_template_name=optional_text(
            environment_variables,
            "WHATSAPP_BOOKING_CONFIRMATION_TEMPLATE",
            WhatsAppTemplateName,
        ),
        telegram_platform_bot_token=secret("TELEGRAM_PLATFORM_BOT_TOKEN"),
        google_oauth_client_id=identifier("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=secret("GOOGLE_OAUTH_CLIENT_SECRET"),
        flitt_merchant_id=identifier("FLITT_MERCHANT_ID"),
        flitt_secret_key=secret("FLITT_SECRET_KEY"),
    )
