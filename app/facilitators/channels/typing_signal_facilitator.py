import logging
import threading
from collections.abc import Generator, Mapping
from contextlib import AbstractContextManager, contextmanager

from app.contracts.channels import ChannelAdapterContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.typing_signals import TypingSignalFacilitatorContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.channel_webhooks import ChannelDeliveryTarget
from app.schemas.dto.channels.typing_signals import TypingRequest
from app.schemas.exceptions.base_exception import ApplicationError
from app.utilities.channels.delivery_targets import build_delivery_target
from app.utilities.channels.typing_refresh import (
    MAX_TYPING_SECONDS,
    TYPING_REFRESH_SECONDS,
)

logger: logging.Logger = logging.getLogger(__name__)
STOP_WAIT_SECONDS: float = 1.0

type TypingTarget = tuple[ChannelAdapterContract, ChannelDeliveryTarget]


class TypingSignalFacilitator(TypingSignalFacilitatorContract):
    """
    "typing…" in the business's own Telegram bot, WhatsApp number,
    Messenger page or Instagram account (the channel adapters'
    `signal_typing`), shown again before each platform hides it while the
    reply is being written. The website widget shows its own typing dots;
    phone calls have none. Signals are best effort: the first one a
    platform refuses ends that turn's typing with one log line.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        telegram_adapter: ChannelAdapterContract,
        whatsapp_adapter: ChannelAdapterContract,
        messenger_adapter: ChannelAdapterContract,
        instagram_adapter: ChannelAdapterContract,
        refresh_seconds: Mapping[ChannelKind, float] | None = None,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._adapters: dict[ChannelKind, ChannelAdapterContract] = {
            ChannelKind.TELEGRAM: telegram_adapter,
            ChannelKind.WHATSAPP: whatsapp_adapter,
            ChannelKind.MESSENGER: messenger_adapter,
            ChannelKind.INSTAGRAM: instagram_adapter,
        }
        self._refresh_seconds: dict[ChannelKind, float] = dict(
            TYPING_REFRESH_SECONDS if refresh_seconds is None else refresh_seconds
        )

    def signal_once(self, request: TypingRequest) -> None:
        typing_target: TypingTarget | None = self._resolve(request)
        if typing_target is not None:
            self._signal(typing_target, request)

    def keep_typing(self, request: TypingRequest) -> AbstractContextManager[None]:
        return self._typing(request)

    @contextmanager
    def _typing(self, request: TypingRequest) -> Generator[None]:
        typing_target: TypingTarget | None = self._resolve(request)
        if typing_target is None:
            yield
            return

        stopped = threading.Event()
        thread = threading.Thread(
            target=self._repeat,
            args=(typing_target, request, stopped),
            name=f"typing-{request.channel.value}",
            daemon=True,
        )
        thread.start()
        try:
            yield
        finally:
            stopped.set()
            thread.join(timeout=STOP_WAIT_SECONDS)

    def _repeat(
        self,
        typing_target: TypingTarget,
        request: TypingRequest,
        stopped: threading.Event,
    ) -> None:
        interval: float = self._refresh_seconds.get(request.channel, 0.0)
        signals_left: int = max(1, int(MAX_TYPING_SECONDS / max(interval, 0.001)))
        while not stopped.is_set() and signals_left > 0:
            if not self._signal(typing_target, request):
                return

            signals_left -= 1
            stopped.wait(timeout=interval)

    def _signal(self, typing_target: TypingTarget, request: TypingRequest) -> bool:
        """One signal; False when the platform refused it (stop trying)."""

        adapter, target = typing_target
        try:
            adapter.signal_typing(target, request.replying_to)
        except ApplicationError as error:
            logger.info(
                "No typing signal in %s for business %s: %s",
                request.channel.value,
                request.business_id,
                error,
            )
            return False

        return True

    def _resolve(self, request: TypingRequest) -> TypingTarget | None:
        """The adapter and the delivery target, when typing can be shown."""

        adapter: ChannelAdapterContract | None = self._adapters.get(request.channel)
        if adapter is None or request.channel_id is None:
            return None

        channel: ChannelDocument | None = self._channel_repo.get(request.channel_id)
        if channel is None or channel.business_id != request.business_id:
            return None

        try:
            target: ChannelDeliveryTarget = build_delivery_target(
                channel, request.channel_user_id, self._secret_cipher
            )
        except ApplicationError as error:
            logger.info(
                "No typing signal for business %s: %s", channel.business_id, error
            )
            return None

        return adapter, target
