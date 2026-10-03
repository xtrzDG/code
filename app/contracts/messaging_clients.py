"""Providers that carry login codes: SMS, Telegram Gateway, WhatsApp, e-mail."""

from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.strings import (
    EmailBodyText,
    EmailSubject,
    SmsMessageText,
)
from app.schemas.typings.users.constrained_integers import OtpLifetimeSeconds
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode


class SmsMessagingClientContract(ClientContract, Protocol):
    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        """Send one SMS. Raises ExternalServiceError when the provider refuses."""
        raise NotImplementedError


class TelegramGatewayClientContract(ClientContract, Protocol):
    def send_verification_message(
        self,
        phone_number: E164PhoneNumber,
        code: OtpCode,
        lifetime_seconds: OtpLifetimeSeconds,
    ) -> None:
        """
        Deliver a code to the Telegram account of a phone number (Telegram
        writes the message itself). Raises ExternalServiceError, also when
        the number has no Telegram account.
        """
        raise NotImplementedError


class WhatsAppAuthenticationClientContract(ClientContract, Protocol):
    def send_authentication_code(
        self,
        recipient: E164PhoneNumber,
        code: OtpCode,
        language_code: WhatsAppTemplateLanguageCode,
    ) -> None:
        """
        Send the approved authentication template with the code (body and
        copy-code button). Raises ExternalServiceError.
        """
        raise NotImplementedError


class EmailSenderClientContract(ClientContract, Protocol):
    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
    ) -> None:
        """Send one e-mail. Raises ExternalServiceError when the server refuses."""
        raise NotImplementedError
