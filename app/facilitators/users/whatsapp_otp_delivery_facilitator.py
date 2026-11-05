from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.messaging_clients import WhatsAppAuthenticationClientContract
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    UnsupportedLanguageError,
)
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.utilities.channels.language_codes import to_whatsapp_template_language


class WhatsAppOtpDeliveryFacilitator(OtpDeliveryFacilitatorContract):
    """
    Login codes by the approved WhatsApp authentication template.

    The template is sent in the user's language when it is one of the
    approved translations (WHATSAPP_OTP_TEMPLATE_LANGUAGES; "pt_BR" also
    serves "pt"), otherwise in the first listed language.
    """

    def __init__(
        self,
        whatsapp_client: WhatsAppAuthenticationClientContract,
        template_languages: list[WhatsAppTemplateLanguageCode],
    ) -> None:
        if not template_languages:
            raise ValueError("The WhatsApp template needs at least one language.")

        self._whatsapp_client: WhatsAppAuthenticationClientContract = whatsapp_client
        self._template_languages: list[WhatsAppTemplateLanguageCode] = list(
            template_languages
        )

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        return frozenset({OtpDeliveryChannel.WHATSAPP})

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        del email
        if delivery_channel is not OtpDeliveryChannel.WHATSAPP or phone_number is None:
            raise ExternalServiceError(
                "The WhatsApp provider only sends codes to phone numbers."
            )

        self._whatsapp_client.send_authentication_code(
            phone_number,
            code,
            self._choose_template_language(language_tag),
        )

    def _choose_template_language(
        self,
        language_tag: LanguageTag,
    ) -> WhatsAppTemplateLanguageCode:
        try:
            requested: WhatsAppTemplateLanguageCode = to_whatsapp_template_language(
                language_tag
            )
        except UnsupportedLanguageError:
            return self._template_languages[0]

        if requested in self._template_languages:
            return requested

        requested_base: str = str(requested).split("_")[0]
        for template_language in self._template_languages:
            if str(template_language).split("_")[0] == requested_base:
                return template_language

        return self._template_languages[0]
