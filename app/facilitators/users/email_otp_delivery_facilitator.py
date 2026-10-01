from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.messaging_clients import EmailSenderClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.utilities.security.login_code_texts import (
    LOGIN_CODE_EMAIL_BODY,
    LOGIN_CODE_EMAIL_SUBJECT,
    build_login_code_email_html,
    fill_login_code_text,
    lifetime_in_minutes,
)


class EmailOtpDeliveryFacilitator(OtpDeliveryFacilitatorContract):
    """
    Login codes by e-mail: a localized subject with the code, a plain text
    body and its HTML version (English when the language has no text).
    """

    def __init__(
        self,
        email_client: EmailSenderClientContract,
        localized_text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
    ) -> None:
        self._email_client: EmailSenderClientContract = email_client
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._app_settings: AppSettings = app_settings

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        return frozenset({OtpDeliveryChannel.EMAIL})

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        del phone_number
        if delivery_channel is not OtpDeliveryChannel.EMAIL or email is None:
            raise ExternalServiceError(
                "The e-mail provider only sends codes to e-mail addresses."
            )

        minutes: int = lifetime_in_minutes(self._app_settings.otp_lifetime_seconds)
        body_template: str = self._localized_text_resolver.resolve(
            LOGIN_CODE_EMAIL_BODY, language_tag
        )
        self._email_client.send_email(
            recipient=email,
            subject=EmailSubject(
                fill_login_code_text(
                    self._localized_text_resolver.resolve(
                        LOGIN_CODE_EMAIL_SUBJECT, language_tag
                    ),
                    code,
                    minutes,
                )
            ),
            text_body=EmailBodyText(fill_login_code_text(body_template, code, minutes)),
            html_body=build_login_code_email_html(body_template, code, minutes),
        )
