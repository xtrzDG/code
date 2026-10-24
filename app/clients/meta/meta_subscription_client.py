from app.clients.meta.graph_api_client import GraphApiClient
from app.clients.meta.graph_requests import graph_request
from app.contracts.channel_clients import ProviderToken
from app.contracts.channel_deprovisioning import MetaSubscriptionClientContract
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)


class MetaSubscriptionClient(GraphApiClient, MetaSubscriptionClientContract):
    """
    `DELETE /{object}/subscribed_apps` of the Graph API: a page (named by
    its own token, `me`) or a WhatsApp business account no longer delivers
    its webhooks to the platform's app.
    """

    def unsubscribe_page(self, page_token: ProviderToken) -> None:
        self._unsubscribe("/me/subscribed_apps", page_token)

    def unsubscribe_whatsapp_business_account(
        self,
        access_token: ProviderToken,
        business_account_id: WhatsAppBusinessAccountId,
    ) -> None:
        self._unsubscribe(f"/{business_account_id}/subscribed_apps", access_token)

    def _unsubscribe(self, path: str, access_token: ProviderToken) -> None:
        graph_request(
            self._http_client, "DELETE", path, str(access_token), is_lookup=True
        )
