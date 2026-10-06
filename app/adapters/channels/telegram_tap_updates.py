"""Whether a business bot is sent the taps of its inline buttons."""

import hashlib
import logging
import threading

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.channels.provider_profiles import TelegramWebhookInfo
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret

LOGGER: logging.Logger = logging.getLogger(__name__)


class TelegramTapUpdates:
    """
    A bot connected before the platform sent buttons gets only messages
    (its webhook's `allowed_updates`), so its taps would be lost: before a
    bot's first keyboard in this process, its webhook is checked once and
    registered again, at the same address, with button taps. A bot that
    cannot be checked or registered gets its options as a numbered list
    instead (the caller's fallback), and is asked again next time.
    """

    def __init__(
        self,
        telegram_client: TelegramBotApiClientContract,
        app_settings: AppSettings,
    ) -> None:
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._app_settings: AppSettings = app_settings
        self._lock: threading.Lock = threading.Lock()
        # Fingerprints of the bots known to receive taps (technical cache).
        self._ready: set[str] = set()

    def ensure(self, bot_token: ChannelSecret) -> bool:
        """True when the bot's taps reach the platform."""

        fingerprint: str = hashlib.sha256(str(bot_token).encode()).hexdigest()
        with self._lock:
            if fingerprint in self._ready:
                return True

        try:
            is_ready: bool = self._enable(bot_token)
        except ApplicationError as error:
            LOGGER.warning("Telegram button taps could not be enabled: %s", error)
            return False

        if is_ready:
            with self._lock:
                self._ready.add(fingerprint)
        return is_ready

    def _enable(self, bot_token: ChannelSecret) -> bool:
        info: TelegramWebhookInfo = self._telegram_client.get_webhook_info(bot_token)
        if info.receives_taps:
            return True

        encryption_key: PlatformSecret | None = self._app_settings.encryption_key
        if info.url is None or encryption_key is None:
            return False

        self._telegram_client.set_webhook(
            bot_token,
            info.url,
            derive_telegram_webhook_secret(encryption_key, bot_token),
        )
        return True
