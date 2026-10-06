"""
Seal one business's stored secrets again with the current key: its
channels' credentials, its Google Calendar tokens and its resources'
calendar secrets (iCal feed addresses, booking-system keys), each written back
only if it did not change meanwhile; and register its Telegram bots'
webhooks again with the secret of the current key.
"""

import logging
from dataclasses import dataclass

from app.contracts.calendar_sync import ResourceCalendarLinkRepoContract
from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.operations import CalendarConnectionRepoContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import (
    SecretCipherAdapterContract,
    SecretRotationAdapterContract,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.calendar import CalendarConnectionDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import ChannelWebhookUrl
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.use_cases.admin.security.calendar_link_resealer import reseal_calendar_links
from app.utilities.channels.channel_endpoints import (
    build_telegram_webhook_path,
    join_public_url,
)
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret

LOGGER: logging.Logger = logging.getLogger(__name__)


@dataclass
class RotationTally:
    """What a run did so far (plain counters while it walks the platform)."""

    total: int = 0
    current: int = 0
    rotated: int = 0
    unreadable: int = 0
    webhooks_renewed: int = 0
    webhooks_failed: int = 0


class SecretResealer:
    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        calendar_connection_repo: CalendarConnectionRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        secret_rotation: SecretRotationAdapterContract,
        telegram_client: TelegramBotApiClientContract,
        app_settings: AppSettings,
        calendar_link_repo: ResourceCalendarLinkRepoContract | None = None,
    ) -> None:
        self._calendar_link_repo: ResourceCalendarLinkRepoContract | None = (
            calendar_link_repo
        )
        self._channel_repo: ChannelRepoContract = channel_repo
        self._calendar_connection_repo: CalendarConnectionRepoContract = (
            calendar_connection_repo
        )
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._secret_rotation: SecretRotationAdapterContract = secret_rotation
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._app_settings: AppSettings = app_settings

    def reseal_business(self, business_id: BusinessId, tally: RotationTally) -> None:
        renews_webhooks: bool = int(self._secret_rotation.key_count()) > 1
        for channel in self._channel_repo.list_by_business(business_id):
            if channel.encrypted_secret is None:
                continue

            sealed = self._reseal(channel.encrypted_secret, tally)
            if sealed is not None and sealed != channel.encrypted_secret:
                self._store_channel_secret(channel, sealed, tally)
            if (
                renews_webhooks
                and sealed is not None
                and channel.kind is ChannelKind.TELEGRAM
                and is_channel_active(channel)
            ):
                self._renew_webhook(channel, sealed, tally)

        connection = self._calendar_connection_repo.get_by_business(business_id)
        if connection is not None:
            self._reseal_calendar(connection, tally)
        if self._calendar_link_repo is not None:
            reseal_calendar_links(
                self._calendar_link_repo,
                business_id,
                lambda encrypted: self._reseal(encrypted, tally),
            )

    def _reseal(
        self, encrypted: EncryptedChannelSecret, tally: RotationTally
    ) -> EncryptedChannelSecret | None:
        """The secret under the current key (itself when it was); None: unreadable."""

        tally.total += 1
        if self._secret_rotation.is_current(encrypted):
            tally.current += 1
            return encrypted

        try:
            resealed: EncryptedChannelSecret = self._secret_rotation.rotate(encrypted)
        except ApplicationError:
            tally.unreadable += 1
            return None

        tally.rotated += 1
        return resealed

    def _store_channel_secret(
        self,
        channel: ChannelDocument,
        sealed: EncryptedChannelSecret,
        tally: RotationTally,
    ) -> None:
        def replace_secret(stored: ChannelDocument) -> ChannelDocument | None:
            if stored.encrypted_secret != channel.encrypted_secret:
                return None  # Reconnected meanwhile: sealed with the current key.

            return stored.model_copy(update={"encrypted_secret": sealed})

        if (
            self._channel_repo.modify(channel.business_id, channel.id, replace_secret)
            is None
        ):
            tally.rotated -= 1
            tally.current += 1

    def _renew_webhook(
        self,
        channel: ChannelDocument,
        sealed: EncryptedChannelSecret,
        tally: RotationTally,
    ) -> None:
        current_key = self._app_settings.encryption_key
        base_url = self._app_settings.app_base_url
        try:
            if current_key is None or base_url is None:
                raise ExternalServiceError(
                    "APP_BASE_URL or the encryption key is missing."
                )

            bot_token = self._secret_cipher.decrypt(sealed)
            self._telegram_client.set_webhook(
                bot_token,
                ChannelWebhookUrl(
                    join_public_url(
                        str(base_url), build_telegram_webhook_path(channel.id)
                    )
                ),
                derive_telegram_webhook_secret(current_key, bot_token),
            )
        except (ApplicationError, ValueError) as error:
            LOGGER.warning(
                "Telegram webhook of channel %s not registered again: %s",
                channel.id,
                error,
            )
            tally.webhooks_failed += 1
            return

        tally.webhooks_renewed += 1

    def _reseal_calendar(
        self, connection: CalendarConnectionDocument, tally: RotationTally
    ) -> None:
        refresh = self._reseal(connection.encrypted_refresh_token, tally)
        access = (
            None
            if connection.encrypted_access_token is None
            else self._reseal(connection.encrypted_access_token, tally)
        )
        update: dict[str, EncryptedChannelSecret] = {}
        if refresh is not None and refresh != connection.encrypted_refresh_token:
            update["encrypted_refresh_token"] = refresh
        if access is not None and access != connection.encrypted_access_token:
            update["encrypted_access_token"] = access
        if not update:
            return

        def replace_tokens(
            stored: CalendarConnectionDocument,
        ) -> CalendarConnectionDocument | None:
            if (
                stored.encrypted_refresh_token != connection.encrypted_refresh_token
                or stored.encrypted_access_token != connection.encrypted_access_token
            ):
                return None  # Refreshed or reconnected meanwhile.

            return stored.model_copy(update=update)

        if (
            self._calendar_connection_repo.modify(
                connection.business_id, replace_tokens
            )
            is None
        ):
            tally.rotated -= len(update)
            tally.current += len(update)
