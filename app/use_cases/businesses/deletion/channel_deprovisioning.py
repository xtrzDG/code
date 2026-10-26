"""A deleted business's Telegram bots and Meta pages stop calling the platform."""

import logging
from collections.abc import Callable

from app.contracts.channel_clients import ProviderToken, TelegramBotApiClientContract
from app.contracts.channel_deprovisioning import MetaSubscriptionClientContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.business_closures import (
    DeprovisionOutcome,
    DeprovisionTarget,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.business_closures import DeprovisionRecord
from app.schemas.domain.channels import ChannelDocument
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.business_closures.constrained_integers import (
    DeprovisionedItemCount,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.utilities.channels.delivery_targets import decrypt_channel_secret

logger: logging.Logger = logging.getLogger(__name__)
PAGE_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.MESSENGER, ChannelKind.INSTAGRAM}
)


class ChannelDeprovisioner:
    """
    Every Telegram bot of the business drops the platform's webhook, every
    Facebook page (Messenger, Instagram) and the business's own WhatsApp
    account (Embedded Signup) drop the platform app's subscription. Best
    effort: a provider that cannot be reached is reported SKIPPED, since
    the credential that would reach it is deleted with the business and
    nothing of the platform can use it any more. A number connected under
    the platform's own WhatsApp account keeps that account's subscription
    (other businesses' numbers share it).
    """

    def __init__(
        self,
        secret_cipher: SecretCipherAdapterContract,
        telegram_client: TelegramBotApiClientContract,
        meta_subscriptions: MetaSubscriptionClientContract,
    ) -> None:
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._meta_subscriptions: MetaSubscriptionClientContract = meta_subscriptions

    def telegram(self, channels: list[ChannelDocument]) -> DeprovisionRecord:
        return self._each(
            DeprovisionTarget.TELEGRAM_WEBHOOK,
            [channel for channel in channels if channel.kind is ChannelKind.TELEGRAM],
            lambda channel, token: self._telegram_client.delete_webhook(token),
        )

    def meta(self, channels: list[ChannelDocument]) -> DeprovisionRecord:
        pages: list[ChannelDocument] = [
            channel for channel in channels if channel.kind in PAGE_CHANNELS
        ]
        accounts: list[ChannelDocument] = [
            channel
            for channel in channels
            if channel.kind is ChannelKind.WHATSAPP
            and channel.whatsapp_business_account_id is not None
        ]
        return self._each(
            DeprovisionTarget.META_SUBSCRIPTION,
            [*pages, *accounts],
            self._unsubscribe,
        )

    def _unsubscribe(self, channel: ChannelDocument, token: ProviderToken) -> None:
        account = channel.whatsapp_business_account_id
        if channel.kind is ChannelKind.WHATSAPP and account is not None:
            self._meta_subscriptions.unsubscribe_whatsapp_business_account(
                token, account
            )
        else:
            self._meta_subscriptions.unsubscribe_page(token)

    def _each(
        self,
        target: DeprovisionTarget,
        channels: list[ChannelDocument],
        switch_off: Callable[[ChannelDocument, ProviderToken], None],
    ) -> DeprovisionRecord:
        done: int = 0
        skipped: int = 0
        for channel in channels:
            try:
                token: ChannelSecret | None = decrypt_channel_secret(
                    channel, self._secret_cipher
                )
                if token is None:
                    continue

                switch_off(channel, token)
                done += 1
            except ApplicationError as error:
                skipped += 1
                logger.warning(
                    "%s of channel %s was not switched off: %s",
                    target.value,
                    channel.id,
                    error,
                )

        return deprovision_record(target, done, skipped)


def deprovision_record(
    target: DeprovisionTarget, done: int, skipped: int
) -> DeprovisionRecord:
    """DONE when anything was switched off, SKIPPED when only failures, else NOTHING."""

    outcome: DeprovisionOutcome = (
        DeprovisionOutcome.DONE
        if done
        else DeprovisionOutcome.SKIPPED
        if skipped
        else DeprovisionOutcome.NOTHING
    )
    return DeprovisionRecord(
        target=target, outcome=outcome, item_count=DeprovisionedItemCount(done)
    )
