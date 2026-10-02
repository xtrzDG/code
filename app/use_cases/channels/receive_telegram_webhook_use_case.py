from app.contracts.channels import ChannelAdapterContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.channel_webhooks import (
    ChannelInboundMessage,
    TelegramWebhookRequest,
)
from app.schemas.dto.deliveries import RoutedInboundMessage
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.channels.strings import ChannelSecret
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import decrypt_channel_secret


class ReceiveTelegramWebhookUseCase(
    UseCaseContract[TelegramWebhookRequest, list[RoutedInboundMessage]]
):
    """
    Verify and read a webhook of a business's Telegram bot.

    The channel named in the webhook address must be a connected Telegram
    channel; the X-Telegram-Bot-Api-Secret-Token header must equal the
    secret derived from that bot's token. The business is the channel's
    owner (never anything the payload says).
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        telegram_adapter: ChannelAdapterContract,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._telegram_adapter: ChannelAdapterContract = telegram_adapter

    def run(self, input_data: TelegramWebhookRequest) -> list[RoutedInboundMessage]:
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
        return [
            RoutedInboundMessage(
                business_id=channel.business_id,
                channel_id=channel.id,
                channel=channel.kind,
                message=message,
            )
            for message in messages
        ]
