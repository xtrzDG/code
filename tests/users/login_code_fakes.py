"""Fake SMS, WhatsApp and email providers and settings for login code delivery."""

from dataclasses import dataclass

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.messaging_clients import (
    EmailSenderClientContract,
    SmsMessagingClientContract,
    TelegramGatewayClientContract,
    WhatsAppAuthenticationClientContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.messaging.strings import (
    EmailBodyText,
    EmailSubject,
    SmsMessageText,
)
from app.schemas.typings.users.constrained_integers import OtpLifetimeSeconds
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

PHONE = E164PhoneNumber("+995555123456")

EMAIL = EmailAddress("owner@example.com")

CODE = OtpCode("042317")

ALL_CHANNELS = frozenset(OtpDeliveryChannel)

TWILIO_ENVIRONMENT: dict[str, str] = {
    "TWILIO_ACCOUNT_SID": "AC" + "1f" * 16,
    "TWILIO_AUTH_TOKEN": "twilio-token",
    "TWILIO_FROM_NUMBER": "Workshop",
}

SMTP_ENVIRONMENT: dict[str, str] = {
    "SMTP_HOST": "smtp.workshop.example",
    "SMTP_FROM": "Assistant Workshop <no-reply@workshop.example>",
}

WHATSAPP_ENVIRONMENT: dict[str, str] = {
    "WHATSAPP_OTP_PHONE_NUMBER_ID": "106540352242922",
    "WHATSAPP_OTP_TEMPLATE": "login_code",
    "WHATSAPP_SYSTEM_USER_TOKEN": "system-user-token",
}


class FakeSms(SmsMessagingClientContract):
    def __init__(self) -> None:
        self.sent: list[tuple[E164PhoneNumber, SmsMessageText]] = []

    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        self.sent.append((recipient, text))


class FakeGateway(TelegramGatewayClientContract):
    def __init__(self) -> None:
        self.sent: list[tuple[E164PhoneNumber, OtpCode, OtpLifetimeSeconds]] = []

    def send_verification_message(
        self,
        phone_number: E164PhoneNumber,
        code: OtpCode,
        lifetime_seconds: OtpLifetimeSeconds,
    ) -> None:
        self.sent.append((phone_number, code, lifetime_seconds))


class FakeWhatsApp(WhatsAppAuthenticationClientContract):
    def __init__(self) -> None:
        self.sent: list[
            tuple[E164PhoneNumber, OtpCode, WhatsAppTemplateLanguageCode]
        ] = []

    def send_authentication_code(
        self,
        recipient: E164PhoneNumber,
        code: OtpCode,
        language_code: WhatsAppTemplateLanguageCode,
    ) -> None:
        self.sent.append((recipient, code, language_code))


@dataclass
class SentEmail:
    recipient: EmailAddress
    subject: EmailSubject
    text_body: EmailBodyText
    html_body: EmailBodyText | None


class FakeMailer(EmailSenderClientContract):
    def __init__(self) -> None:
        self.sent: list[SentEmail] = []

    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
    ) -> None:
        self.sent.append(SentEmail(recipient, subject, text_body, html_body))


def settings(**environment: str) -> AppSettings:
    return assemble_app_settings(environment)


def deliver(
    facilitator: OtpDeliveryFacilitatorContract,
    channel: OtpDeliveryChannel,
    language: str = "en",
) -> None:
    facilitator.deliver(
        delivery_channel=channel,
        phone_number=None if channel is OtpDeliveryChannel.EMAIL else PHONE,
        email=EMAIL if channel is OtpDeliveryChannel.EMAIL else None,
        code=CODE,
        language_tag=LanguageTag(language),
    )
