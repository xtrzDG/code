"""The WhatsApp templates a business registered at Meta."""

from typing import Protocol

from app.contracts.channel_clients import ProviderToken
from app.contracts.client_contract import ClientContract
from app.schemas.constants.whatsapp_templates import WhatsAppTemplateCategory
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)


class WhatsAppTemplateCatalogClientContract(ClientContract, Protocol):
    """
    `GET /{waba}/message_templates` of the Graph API. Errors:
    ExternalServiceError when Meta cannot be asked or refuses the token.
    """

    def find_categories(
        self,
        access_token: ProviderToken,
        business_account_id: WhatsAppBusinessAccountId,
        template_name: WhatsAppTemplateName,
    ) -> list[WhatsAppTemplateCategory]:
        """
        The categories of the account's templates of exactly that name (one
        per language); [] when it has none, categories Meta added since are
        left out.
        """
        raise NotImplementedError
