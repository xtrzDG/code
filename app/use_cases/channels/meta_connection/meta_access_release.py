"""
A Meta channel the owner switches off gives back the platform app's access
at Meta before its token is erased: the page (Messenger, Instagram) or the
business's own WhatsApp account no longer sends the app its messages.
"""

import logging
from collections.abc import Sequence

from app.contracts.channel_deprovisioning import MetaSubscriptionClientContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.strings import ChannelSecret
from app.utilities.channels.delivery_targets import decrypt_channel_secret

logger: logging.Logger = logging.getLogger(__name__)
PAGE_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.MESSENGER, ChannelKind.INSTAGRAM}
)


class MetaAccessRelease:
    """
    Before a Meta channel's credential is erased:

    - a page channel (Messenger, Instagram) unsubscribes the app from the
      page the token belongs to, unless another page channel of the
      business is still on (both may be the same page: its subscription
      carries both);
    - a WhatsApp channel connected with Embedded Signup unsubscribes the
      app from the business's own WhatsApp account (a number connected
      under the platform's account keeps that shared subscription).

    Meta has no call that revokes a page or a business token itself: once
    unsubscribed and erased here, the platform can no longer use it, and
    the owner may remove the app in Meta's Business Integrations settings.
    Best effort: a refusal or an unreachable Meta is logged, and switching
    off goes on (the token is erased all the same). Never raises.
    """

    def __init__(
        self,
        secret_cipher: SecretCipherAdapterContract,
        meta_subscriptions: MetaSubscriptionClientContract,
    ) -> None:
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._meta_subscriptions: MetaSubscriptionClientContract = meta_subscriptions

    def release(
        self, channel: ChannelDocument, business_channels: Sequence[ChannelDocument]
    ) -> None:
        try:
            token: ChannelSecret | None = decrypt_channel_secret(
                channel, self._secret_cipher
            )
            if token is None:
                return

            if channel.kind in PAGE_CHANNELS:
                if not shares_a_page(channel, business_channels):
                    self._meta_subscriptions.unsubscribe_page(token)
                return

            account = channel.whatsapp_business_account_id
            if channel.kind is ChannelKind.WHATSAPP and account is not None:
                self._meta_subscriptions.unsubscribe_whatsapp_business_account(
                    token, account
                )
        except ApplicationError as error:
            logger.warning(
                "Meta access of channel %s was not given back: %s", channel.id, error
            )


def shares_a_page(
    channel: ChannelDocument, business_channels: Sequence[ChannelDocument]
) -> bool:
    """Another page channel of the business is still on (maybe the same page)."""

    return any(
        other.id != channel.id
        and other.kind in PAGE_CHANNELS
        and other.status is ChannelStatus.CONNECTED
        for other in business_channels
    )
