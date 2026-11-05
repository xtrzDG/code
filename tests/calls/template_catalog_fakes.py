"""Meta's template catalog of a WhatsApp business account, as a test sets it."""

from app.contracts.channel_clients import ProviderToken
from app.contracts.whatsapp_templates import WhatsAppTemplateCatalogClientContract
from app.schemas.constants.whatsapp_templates import WhatsAppTemplateCategory
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)


class FakeTemplateCatalog(WhatsAppTemplateCatalogClientContract):
    """Templates by name; every question asked is kept (token, account, name)."""

    def __init__(
        self,
        templates: dict[str, list[WhatsAppTemplateCategory]] | None = None,
        is_unreachable: bool = False,
    ) -> None:
        self.templates: dict[str, list[WhatsAppTemplateCategory]] = templates or {}
        self.is_unreachable: bool = is_unreachable
        self.asked: list[tuple[str, str, str]] = []

    def find_categories(
        self,
        access_token: ProviderToken,
        business_account_id: WhatsAppBusinessAccountId,
        template_name: WhatsAppTemplateName,
    ) -> list[WhatsAppTemplateCategory]:
        self.asked.append(
            (str(access_token), str(business_account_id), str(template_name))
        )
        if self.is_unreachable:
            raise ExternalServiceError("Meta Graph API request failed: ConnectError.")

        return list(self.templates.get(str(template_name), []))
