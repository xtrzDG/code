from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import (
    ChannelAdapterContract,
    ChannelMessageReceiptRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import (
    ChannelInboundDelivery,
    ChannelInboundMessage,
    TelegramWebhookRequest,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.channels.channel_webhook_support import accept_inbound_message
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import decrypt_channel_secret


class ReceiveTelegramWebhookUseCase(
    UseCaseContract[TelegramWebhookRequest, list[ChannelInboundDelivery]]
):
    """
    Accept a webhook of a business's Telegram bot.

    The channel named in the webhook address must be a connected Telegram
    channel; the X-Telegram-Bot-Api-Secret-Token header must equal the
    secret derived from that bot's token. The business is the channel's
    owner. Repeated deliveries of a message are dropped.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        telegram_adapter: ChannelAdapterContract,
        receipt_repo: ChannelMessageReceiptRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._telegram_adapter: ChannelAdapterContract = telegram_adapter
        self._receipt_repo: ChannelMessageReceiptRepoContract = receipt_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: TelegramWebhookRequest) -> list[ChannelInboundDelivery]:
        channel: ChannelDocument | None = self._channel_repo.get(input_data.channel_id)
        if (
            channel is None
            or channel.kind is not ChannelKind.TELEGRAM
            or not is_channel_active(channel)
        ):
            raise NotFoundError("This Telegram channel is not connected.")

        bot_token: ChannelSecret | None = decrypt_channel_secret(
            channel,
            self._secret_cipher,
        )
        self._telegram_adapter.verify_signature(input_data.payload, bot_token)
        messages: list[ChannelInboundMessage] = self._telegram_adapter.parse_webhook(
            input_data.payload
        )
        now: Microseconds = self._wall_clock.now_unix()
        deliveries: list[ChannelInboundDelivery] = []
        for message in messages:
            delivery: ChannelInboundDelivery | None = accept_inbound_message(
                message,
                channel,
                self._secret_cipher,
                self._receipt_repo,
                now,
            )
            if delivery is not None:
                deliveries.append(delivery)

        return deliveries
