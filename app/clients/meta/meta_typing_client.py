import httpx

from app.clients.meta.meta_graph_client import (
    DEFAULT_GRAPH_API_VERSION,
    META_GRAPH_BASE_URL,
)
from app.clients.meta.meta_graph_errors import build_graph_error
from app.contracts.channel_clients import MetaTypingClientContract, ProviderToken
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.channels.json_values import JsonObject, parse_json_object

# A typing signal is worth nothing late: it never waits long.
TYPING_TIMEOUT_SECONDS: float = 3.0
WHATSAPP_TEXT_TYPING: str = "text"
PAGE_TYPING_ON: str = "typing_on"


class MetaTypingClient(MetaTypingClientContract):
    """
    The "typing…" signals of Meta's messaging APIs: the WhatsApp Cloud API
    typing indicator, sent with the read receipt of the customer's message,
    and the Messenger / Instagram Send API `sender_action`. Tokens travel in
    the Authorization header, never in URLs.
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        base_url: str = META_GRAPH_BASE_URL,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/{api_version}",
            timeout=TYPING_TIMEOUT_SECONDS,
            transport=transport,
        )

    def show_whatsapp_typing(
        self,
        access_token: ProviderToken,
        phone_number_id: MetaObjectId,
        message_id: ProviderMessageId,
    ) -> None:
        self._post(
            f"/{phone_number_id}/messages",
            access_token,
            {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": str(message_id),
                "typing_indicator": {"type": WHATSAPP_TEXT_TYPING},
            },
        )

    def show_page_typing(
        self,
        access_token: ProviderToken,
        recipient: ChannelUserId,
    ) -> None:
        self._post(
            "/me/messages",
            access_token,
            {"recipient": {"id": str(recipient)}, "sender_action": PAGE_TYPING_ON},
        )

    def _post(
        self, path: str, access_token: ProviderToken, json_body: JsonObject
    ) -> None:
        try:
            response: httpx.Response = self._http_client.post(
                path,
                json=json_body,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.HTTPError as transport_error:
            raise ExternalServiceError(
                f"Meta typing signal failed: {type(transport_error).__name__}."
            ) from None

        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code < 400 and "error" not in body:
            return

        raise build_graph_error(
            response.status_code,
            body,
            response.headers.get("Retry-After"),
            is_lookup=False,
        )
