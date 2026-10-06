from app.contracts.channels import ChannelAdapterContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.channel_webhooks import TelegramWebhookRequest
from app.schemas.typings.channels.strings import ChannelSecret
from app.utilities.channels.delivery_targets import decrypt_channel_secret


class AcknowledgeTelegramTapsUseCase(UseCaseContract[TelegramWebhookRequest, None]):
    """
    Answer the button tap of a verified Telegram webhook once its message is
    stored: the button stops showing progress and the tapped message keeps
    the chosen option without its buttons (the adapter's
    `acknowledge_taps`, best effort). Anything else does nothing.
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

    def run(self, input_data: TelegramWebhookRequest) -> None:
        channel: ChannelDocument | None = self._channel_repo.get(input_data.channel_id)
        if channel is None or channel.kind is not ChannelKind.TELEGRAM:
            return

        bot_token: ChannelSecret | None = decrypt_channel_secret(
            channel,
            self._secret_cipher,
        )
        self._telegram_adapter.acknowledge_taps(input_data.payload, bot_token)
