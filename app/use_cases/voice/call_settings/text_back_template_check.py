"""
A text-back is a service message ("you called us, write here"): its
WhatsApp template must not sit in Meta's MARKETING category, which may
promote and reaches only customers who gave marketing consent (VOICE-09).

When the owner names a template, the business's WhatsApp account is asked
for that template's category (its own token from Embedded Signup, else
the platform's system user token); a MARKETING one is refused with the
reason `marketing_template`. Where the account cannot be asked (no
business account id on record, no token, Meta unreachable) the name is
kept and the warning logged: Meta's own warning that a template moved
into MARKETING still reaches the WHATSAPP_QUALITY alert.
"""

import logging

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.whatsapp_templates import WhatsAppTemplateCatalogClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.whatsapp_templates import WhatsAppTemplateCategory
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage, PlatformSecret
from app.utilities.channels.delivery_targets import (
    decrypt_channel_secret,
    find_business_channel,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
MARKETING_TEMPLATE_REASON: ErrorReasonCode = ErrorReasonCode("marketing_template")


class TextBackTemplateCheck:
    """Refuses a MARKETING template for text-backs (see the module)."""

    def __init__(
        self,
        catalog: WhatsAppTemplateCatalogClientContract,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract | None,
        app_settings: AppSettings,
    ) -> None:
        self._catalog: WhatsAppTemplateCatalogClientContract = catalog
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract | None = secret_cipher
        self._system_token: PlatformSecret | None = (
            app_settings.whatsapp_system_user_token
        )

    def refuse_marketing(
        self, business_id: BusinessId, template_name: WhatsAppTemplateName
    ) -> None:
        """
        Raises:
            ValidationFailedError: Meta files the template as MARKETING.
        """

        channel: ChannelDocument | None = find_business_channel(
            self._channel_repo, business_id, ChannelKind.WHATSAPP
        )
        if channel is None or channel.whatsapp_business_account_id is None:
            return

        try:
            token: ChannelSecret | PlatformSecret | None = self._token(channel)
            if token is None:
                return

            categories: list[WhatsAppTemplateCategory] = self._catalog.find_categories(
                token, channel.whatsapp_business_account_id, template_name
            )
        except ExternalServiceError as error:
            LOGGER.warning(
                "The category of WhatsApp template %s of business %s is unknown: %s",
                template_name,
                business_id,
                error,
            )
            return

        if WhatsAppTemplateCategory.MARKETING in categories:
            raise ValidationFailedError(
                f"The WhatsApp template {template_name} is in Meta's marketing "
                "category; a text-back needs a utility template.",
                reasons=[
                    ErrorReason(
                        code=MARKETING_TEMPLATE_REASON,
                        message=ErrorReasonMessage(
                            "Name a utility template without promotion."
                        ),
                    )
                ],
            )

    def _token(self, channel: ChannelDocument) -> ChannelSecret | PlatformSecret | None:
        """The number's own token, else the platform's system user token."""

        own: ChannelSecret | None = (
            None
            if self._secret_cipher is None
            else decrypt_channel_secret(channel, self._secret_cipher)
        )
        return own if own is not None else self._system_token
