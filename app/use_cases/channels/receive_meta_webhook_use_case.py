import logging

from app.contracts.channels import ChannelAdapterContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.channel_webhooks import (
    ChannelInboundMessage,
    MetaWebhookRequest,
)
from app.schemas.dto.deliveries import RoutedInboundMessage
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.json_values import JsonObject, parse_json_object, read_text

logger: logging.Logger = logging.getLogger(__name__)

WHATSAPP_OBJECT: str = "whatsapp_business_account"
PAGE_OBJECT: str = "page"
INSTAGRAM_OBJECT: str = "instagram"


class ReceiveMetaWebhookUseCase(
    UseCaseContract[MetaWebhookRequest, list[RoutedInboundMessage]]
):
    """
    Verify and read a webhook of the platform's Meta app (one endpoint for
    WhatsApp, Messenger and Instagram).

    The X-Hub-Signature-256 header must be the HMAC-SHA256 of the raw body
    with META_APP_SECRET. Each message is routed to the business whose
    connected channel owns the account it was sent to (WhatsApp phone number
    id, page id, Instagram account id); messages for unknown or disconnected
    accounts are dropped, so one tenant never answers for another.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        whatsapp_adapter: ChannelAdapterContract,
        messenger_adapter: ChannelAdapterContract,
        instagram_adapter: ChannelAdapterContract,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._whatsapp_adapter: ChannelAdapterContract = whatsapp_adapter
        self._adapters_by_object: dict[str, ChannelAdapterContract] = {
            WHATSAPP_OBJECT: whatsapp_adapter,
            PAGE_OBJECT: messenger_adapter,
            INSTAGRAM_OBJECT: instagram_adapter,
        }

    def run(self, input_data: MetaWebhookRequest) -> list[RoutedInboundMessage]:
        root: JsonObject | None = parse_json_object(input_data.payload.body)
        object_name: str | None = None if root is None else read_text(root, "object")
        adapter: ChannelAdapterContract | None = (
            None if object_name is None else self._adapters_by_object.get(object_name)
        )
        # Every Meta product signs with the same app secret, so a delivery of
        # an unknown kind is still verified before it is ignored.
        (adapter or self._whatsapp_adapter).verify_signature(input_data.payload, None)
        if adapter is None:
            return []

        routed: list[RoutedInboundMessage] = []
        for message in adapter.parse_webhook(input_data.payload):
            routed_message: RoutedInboundMessage | None = self._route(message)
            if routed_message is not None:
                routed.append(routed_message)

        return routed

    def _route(self, message: ChannelInboundMessage) -> RoutedInboundMessage | None:
        if message.account_id is None:
            return None

        channel: ChannelDocument | None = self._channel_repo.find_by_external_id(
            message.channel,
            message.account_id,
        )
        if channel is None or not is_channel_active(channel):
            logger.info(
                "Dropped a %s message for account %s: no connected channel.",
                message.channel.value,
                message.account_id,
            )
            return None

        return RoutedInboundMessage(
            business_id=channel.business_id,
            channel_id=channel.id,
            channel=channel.kind,
            message=message,
        )
