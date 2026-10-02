import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import (
    ChannelAdapterContract,
    ChannelMessageReceiptRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import (
    ChannelInboundDelivery,
    ChannelInboundMessage,
    MetaWebhookRequest,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.use_cases.channels.channel_webhook_support import accept_inbound_message
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.json_values import JsonObject, parse_json_object, read_text

logger: logging.Logger = logging.getLogger(__name__)

WHATSAPP_OBJECT: str = "whatsapp_business_account"
PAGE_OBJECT: str = "page"
INSTAGRAM_OBJECT: str = "instagram"


class ReceiveMetaWebhookUseCase(
    UseCaseContract[MetaWebhookRequest, list[ChannelInboundDelivery]]
):
    """
    Accept a webhook of the platform's Meta app (one endpoint for WhatsApp,
    Messenger and Instagram).

    The X-Hub-Signature-256 header must be the HMAC-SHA256 of the raw body
    with META_APP_SECRET. Each message is routed to the business whose
    connected channel owns the account it was sent to (WhatsApp phone number
    id, page id, Instagram account id); messages for unknown or disconnected
    accounts are dropped, so one tenant never answers for another.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        whatsapp_adapter: ChannelAdapterContract,
        messenger_adapter: ChannelAdapterContract,
        instagram_adapter: ChannelAdapterContract,
        receipt_repo: ChannelMessageReceiptRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._whatsapp_adapter: ChannelAdapterContract = whatsapp_adapter
        self._adapters_by_object: dict[str, ChannelAdapterContract] = {
            WHATSAPP_OBJECT: whatsapp_adapter,
            PAGE_OBJECT: messenger_adapter,
            INSTAGRAM_OBJECT: instagram_adapter,
        }
        self._receipt_repo: ChannelMessageReceiptRepoContract = receipt_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: MetaWebhookRequest) -> list[ChannelInboundDelivery]:
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

        now: Microseconds = self._wall_clock.now_unix()
        deliveries: list[ChannelInboundDelivery] = []
        for message in adapter.parse_webhook(input_data.payload):
            delivery: ChannelInboundDelivery | None = self._accept(message, now)
            if delivery is not None:
                deliveries.append(delivery)

        return deliveries

    def _accept(
        self,
        message: ChannelInboundMessage,
        now: Microseconds,
    ) -> ChannelInboundDelivery | None:
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

        try:
            return accept_inbound_message(
                message,
                channel,
                self._secret_cipher,
                self._receipt_repo,
                now,
            )
        except ExternalServiceError as error:
            logger.warning(
                "Dropped a %s message of business %s: %s",
                message.channel.value,
                channel.business_id,
                error,
            )
            return None
