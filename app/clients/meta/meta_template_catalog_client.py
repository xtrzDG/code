from app.clients.meta.graph_api_client import GraphApiClient
from app.clients.meta.graph_requests import graph_request
from app.contracts.channel_clients import ProviderToken
from app.contracts.whatsapp_templates import WhatsAppTemplateCatalogClientContract
from app.schemas.constants.whatsapp_templates import WhatsAppTemplateCategory
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from app.utilities.channels.json_values import JsonObject, read_objects, read_text

TEMPLATE_FIELDS: str = "name,category,language,status"
# One name exists in at most a few dozen languages.
TEMPLATE_PAGE_SIZE: str = "100"
# Meta's names of the categories; one Meta adds later is left out.
KNOWN_CATEGORIES: dict[str, WhatsAppTemplateCategory] = {
    "MARKETING": WhatsAppTemplateCategory.MARKETING,
    "UTILITY": WhatsAppTemplateCategory.UTILITY,
    "AUTHENTICATION": WhatsAppTemplateCategory.AUTHENTICATION,
}


class MetaTemplateCatalogClient(GraphApiClient, WhatsAppTemplateCatalogClientContract):
    """
    The message templates of a WhatsApp business account by name (Meta
    filters by a part of the name, so the exact name is matched here).
    """

    def find_categories(
        self,
        access_token: ProviderToken,
        business_account_id: WhatsAppBusinessAccountId,
        template_name: WhatsAppTemplateName,
    ) -> list[WhatsAppTemplateCategory]:
        body: JsonObject = graph_request(
            self._http_client,
            "GET",
            f"/{business_account_id}/message_templates",
            str(access_token),
            params={
                "name": str(template_name),
                "fields": TEMPLATE_FIELDS,
                "limit": TEMPLATE_PAGE_SIZE,
            },
            is_lookup=True,
        )
        return [
            KNOWN_CATEGORIES[category]
            for template in read_objects(body, "data")
            if read_text(template, "name") == str(template_name)
            and (category := (read_text(template, "category") or "").upper())
            in KNOWN_CATEGORIES
        ]
