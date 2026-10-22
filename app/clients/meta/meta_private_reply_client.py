import httpx

from app.clients.meta.graph_requests import graph_request
from app.clients.meta.meta_graph_client import (
    DEFAULT_GRAPH_API_VERSION,
    META_GRAPH_BASE_URL,
    REQUEST_TIMEOUT_SECONDS,
)
from app.contracts.meta_connection import MetaPrivateReplyClientContract
from app.schemas.typings.channels.strings import ChannelSecret, ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.meta_connection.constrained_strings import MetaCommentId
from app.utilities.channels.json_values import JsonObject, read_identifier


class MetaPrivateReplyClient(MetaPrivateReplyClientContract):
    """
    Instagram's private replies: `POST /me/messages` with the page token
    and the comment as the recipient (`{"comment_id": ...}`). Meta delivers
    the message to the comment's author and opens a conversation they can
    answer; one private reply per comment, within seven days of it. The
    token travels in the Authorization header, never in the URL; errors map
    as a page message's (`meta_graph_errors.py`).
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        base_url: str = META_GRAPH_BASE_URL,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/{api_version}",
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def send_private_reply(
        self,
        page_token: ChannelSecret,
        comment_id: MetaCommentId,
        text: MessageText,
    ) -> ProviderMessageId | None:
        sent: JsonObject = graph_request(
            self._http_client,
            "POST",
            "/me/messages",
            str(page_token),
            json_body={
                "recipient": {"comment_id": str(comment_id)},
                "message": {"text": str(text)},
            },
        )
        message_id: str | None = read_identifier(sent, "message_id")
        return None if message_id is None else ProviderMessageId(message_id)
