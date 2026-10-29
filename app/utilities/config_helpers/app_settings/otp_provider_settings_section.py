"""TWILIO_*, TELEGRAM_GATEWAY_*, WHATSAPP_OTP_* and SMTP_*: who sends login codes."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.constants.messaging import SmtpSecurity
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.messaging.constrained_integers import SmtpPort
from app.schemas.typings.messaging.constrained_strings import (
    EmailSenderAddress,
    SmsSenderId,
    SmtpHost,
    TwilioAccountSid,
    TwilioMessagingServiceSid,
)
from app.schemas.typings.messaging.strings import SmtpUsername
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_setting,
    optional_text,
    parse_setting,
    read_integer,
    read_raw_list,
    read_text,
)

# Approved translations of the WhatsApp login code template; the first one
# is used when the user's language has none.
DEFAULT_WHATSAPP_OTP_TEMPLATE_LANGUAGES: str = "en"
DEFAULT_SMTP_PORTS: dict[SmtpSecurity, int] = {
    SmtpSecurity.STARTTLS: 587,
    SmtpSecurity.SSL: 465,
    SmtpSecurity.NONE: 25,
}
TWILIO_VARIABLES: tuple[str, ...] = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "TWILIO_MESSAGING_SERVICE_SID",
)
WHATSAPP_OTP_VARIABLES: tuple[str, ...] = (
    "WHATSAPP_OTP_PHONE_NUMBER_ID",
    "WHATSAPP_OTP_TEMPLATE",
    "WHATSAPP_OTP_ACCESS_TOKEN",
)
SMTP_VARIABLES: tuple[str, ...] = (
    "SMTP_HOST",
    "SMTP_FROM",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
)


class OtpProviderSettingsSection(TypedDict):
    """The `AppSettings` fields of the login code providers."""

    twilio_account_sid: TwilioAccountSid | None
    twilio_auth_token: PlatformSecret | None
    twilio_sender: SmsSenderId | None
    twilio_messaging_service_sid: TwilioMessagingServiceSid | None
    telegram_gateway_api_token: PlatformSecret | None
    whatsapp_otp_phone_number_id: MetaObjectId | None
    whatsapp_otp_access_token: PlatformSecret | None
    whatsapp_otp_template_name: WhatsAppTemplateName | None
    whatsapp_otp_template_languages: list[WhatsAppTemplateLanguageCode]
    smtp_host: SmtpHost | None
    smtp_port: SmtpPort
    smtp_security: SmtpSecurity
    smtp_username: SmtpUsername | None
    smtp_password: PlatformSecret | None
    smtp_sender: EmailSenderAddress | None


def check_login_code_providers(environment_variables: Mapping[str, str]) -> None:
    """
    A login code provider is configured completely or not at all, so a typo
    stops the start instead of silently hiding a sign-in channel.
    """

    present: set[str] = {
        variable_name
        for variable_name in (
            *TWILIO_VARIABLES,
            *WHATSAPP_OTP_VARIABLES,
            *SMTP_VARIABLES,
        )
        if environment_variables.get(variable_name, "").strip() != ""
    }
    has_twilio_sender: bool = bool(
        present & {"TWILIO_FROM_NUMBER", "TWILIO_MESSAGING_SERVICE_SID"}
    )
    if present & set(TWILIO_VARIABLES) and not (
        {"TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"} <= present and has_twilio_sender
    ):
        raise ValidationFailedError(
            "Login codes by SMS need TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and "
            "TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID."
        )

    has_whatsapp_token: bool = (
        "WHATSAPP_OTP_ACCESS_TOKEN" in present
        or environment_variables.get("WHATSAPP_SYSTEM_USER_TOKEN", "").strip() != ""
    )
    if present & set(WHATSAPP_OTP_VARIABLES) and not (
        {"WHATSAPP_OTP_PHONE_NUMBER_ID", "WHATSAPP_OTP_TEMPLATE"} <= present
        and has_whatsapp_token
    ):
        raise ValidationFailedError(
            "Login codes by WhatsApp need WHATSAPP_OTP_PHONE_NUMBER_ID, "
            "WHATSAPP_OTP_TEMPLATE and WHATSAPP_OTP_ACCESS_TOKEN (or "
            "WHATSAPP_SYSTEM_USER_TOKEN)."
        )

    has_smtp_login: bool = "SMTP_USERNAME" in present
    if present & set(SMTP_VARIABLES) and not (
        {"SMTP_HOST", "SMTP_FROM"} <= present
        and has_smtp_login == ("SMTP_PASSWORD" in present)
    ):
        raise ValidationFailedError(
            "Login codes by e-mail need SMTP_HOST and SMTP_FROM, and "
            "SMTP_USERNAME together with SMTP_PASSWORD when the server needs a "
            "login."
        )


def read_smtp_security(environment_variables: Mapping[str, str]) -> SmtpSecurity:
    return SmtpSecurity(
        read_text(environment_variables, "SMTP_SECURITY", SmtpSecurity.STARTTLS)
    )


def read_otp_provider_settings(
    environment_variables: Mapping[str, str],
    smtp_security: SmtpSecurity,
) -> OtpProviderSettingsSection:
    def secret(variable_name: str) -> PlatformSecret | None:
        return optional_text(environment_variables, variable_name, PlatformSecret)

    return OtpProviderSettingsSection(
        twilio_account_sid=optional_setting(
            environment_variables, "TWILIO_ACCOUNT_SID", TwilioAccountSid
        ),
        twilio_auth_token=secret("TWILIO_AUTH_TOKEN"),
        twilio_sender=optional_setting(
            environment_variables, "TWILIO_FROM_NUMBER", SmsSenderId
        ),
        twilio_messaging_service_sid=optional_setting(
            environment_variables,
            "TWILIO_MESSAGING_SERVICE_SID",
            TwilioMessagingServiceSid,
        ),
        telegram_gateway_api_token=secret("TELEGRAM_GATEWAY_API_TOKEN"),
        whatsapp_otp_phone_number_id=optional_setting(
            environment_variables, "WHATSAPP_OTP_PHONE_NUMBER_ID", MetaObjectId
        ),
        # The platform's system user token usually serves both purposes.
        whatsapp_otp_access_token=(
            secret("WHATSAPP_OTP_ACCESS_TOKEN") or secret("WHATSAPP_SYSTEM_USER_TOKEN")
        ),
        whatsapp_otp_template_name=optional_setting(
            environment_variables, "WHATSAPP_OTP_TEMPLATE", WhatsAppTemplateName
        ),
        whatsapp_otp_template_languages=[
            parse_setting(
                "WHATSAPP_OTP_TEMPLATE_LANGUAGES",
                raw_language,
                WhatsAppTemplateLanguageCode,
            )
            for raw_language in (
                read_raw_list(environment_variables, "WHATSAPP_OTP_TEMPLATE_LANGUAGES")
                or [DEFAULT_WHATSAPP_OTP_TEMPLATE_LANGUAGES]
            )
        ],
        smtp_host=optional_setting(environment_variables, "SMTP_HOST", SmtpHost),
        smtp_port=parse_setting(
            "SMTP_PORT",
            read_integer(
                environment_variables,
                "SMTP_PORT",
                DEFAULT_SMTP_PORTS[smtp_security],
            ),
            SmtpPort,
        ),
        smtp_security=smtp_security,
        smtp_username=optional_setting(
            environment_variables, "SMTP_USERNAME", SmtpUsername
        ),
        smtp_password=secret("SMTP_PASSWORD"),
        smtp_sender=optional_setting(
            environment_variables, "SMTP_FROM", EmailSenderAddress
        ),
    )
