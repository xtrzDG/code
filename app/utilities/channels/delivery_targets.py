"""The way back to a customer through a business's connected channel."""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import ChannelDeliveryTarget
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.channels.channel_health import ACTIVE_CHANNEL_STATUSES


def find_business_channel(
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
    channel_kind: ChannelKind,
) -> ChannelDocument | None:
    """The business's channel of a kind (one per kind), connected or not."""

    for channel in channel_repo.list_by_business(business_id):
        if channel.kind is channel_kind:
            return channel

    return None


def decrypt_channel_secret(
    channel: ChannelDocument,
    secret_cipher: SecretCipherAdapterContract,
) -> ChannelSecret | None:
    """
    The channel's credential, or None when it has none. Raises
    ExternalServiceError when it cannot be decrypted (the owner must
    reconnect the channel).
    """

    if channel.encrypted_secret is None:
        return None

    try:
        return secret_cipher.decrypt(channel.encrypted_secret)
    except ValidationFailedError as error:
        raise ExternalServiceError(
            f"The {channel.kind.value} credential cannot be read; reconnect the "
            "channel."
        ) from error


def build_delivery_target(
    channel: ChannelDocument,
    channel_user_id: ChannelUserId,
    secret_cipher: SecretCipherAdapterContract,
) -> ChannelDeliveryTarget:
    """
    Delivery target for a connected channel (also one in ERROR: a working
    delivery is what clears the error); raises ExternalServiceError.
    """

    if channel.status not in ACTIVE_CHANNEL_STATUSES:
        raise ExternalServiceError(
            f"The {channel.kind.value} channel of this business is not connected."
        )

    return ChannelDeliveryTarget(
        channel=channel.kind,
        account_id=channel.external_id,
        channel_user_id=channel_user_id,
        credential=decrypt_channel_secret(channel, secret_cipher),
    )


def build_whatsapp_usage_event(
    business_id: BusinessId,
    conversation_id: ConversationId | None,
    delivered_messages: DeliveredMessageCount,
    occurred_at: Microseconds,
) -> UsageEventDocument:
    """
    Metered WhatsApp replies (concept usage_events wa_reply). The provider
    cost is settled on Meta's invoice, so it is recorded as zero here.
    """

    return UsageEventDocument(
        business_id=business_id,
        conversation_id=conversation_id,
        kind=UsageKind.WHATSAPP_REPLY,
        quantity=UsageQuantity(int(delivered_messages)),
        occurred_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )
