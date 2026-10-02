"""
How one outbox message goes out: the parts it is sent as and the call that
sends one part, for a customer reply (the business's channel) or a staff
notification (the platform's providers).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.contracts.channels import ChannelAdapterContract
from app.contracts.facilitators import StaffNotificationSenderContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
)
from app.schemas.dto.channels.channel_webhooks import ChannelDeliveryTarget
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.strings import ChannelSecret, ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import decrypt_channel_secret

type PartSender = Callable[[MessageText], ProviderMessageId | None]


@dataclass(frozen=True)
class OutboundRoute:
    """The parts of one message and how to send one of them."""

    parts: list[MessageText]
    send_part: PartSender


def route_customer_reply(
    message: OutboundMessageDocument,
    recipient: CustomerRecipient,
    channel_repo: ChannelRepoContract,
    secret_cipher: SecretCipherAdapterContract,
    adapters: Mapping[ChannelKind, ChannelAdapterContract],
) -> OutboundRoute:
    """
    Through the business's channel as it is now (a reconnected bot sends
    with its new token). Raises ValidationFailedError when the channel was
    disconnected or the platform cannot carry replies, and
    ChannelCredentialRejectedError when its credential cannot be read.
    """

    adapter: ChannelAdapterContract | None = adapters.get(recipient.channel)
    channel: ChannelDocument | None = channel_repo.get(recipient.channel_id)
    if (
        adapter is None
        or channel is None
        or channel.business_id != message.business_id
        or not is_channel_active(channel)
    ):
        raise ValidationFailedError(
            f"The {recipient.channel.value} channel of this business is no longer "
            "connected."
        )

    try:
        credential: ChannelSecret | None = decrypt_channel_secret(
            channel, secret_cipher
        )
    except ExternalServiceError as error:
        raise ChannelCredentialRejectedError(str(error)) from error

    target = ChannelDeliveryTarget(
        channel=channel.kind,
        account_id=channel.external_id,
        channel_user_id=recipient.channel_user_id,
        credential=credential,
    )
    return OutboundRoute(
        parts=adapter.split(message.text),
        send_part=lambda part: adapter.send(target, part).provider_message_id,
    )


def route_staff_notification(
    message: OutboundMessageDocument,
    contact: ManagerContact,
    staff_sender: StaffNotificationSenderContract,
) -> OutboundRoute:
    """Through the platform's provider for the contact's channel."""

    return OutboundRoute(
        parts=staff_sender.split(contact, message.text),
        send_part=lambda part: staff_sender.send(contact, part, message.template),
    )
