"""
Where a caller can get a text message from the business (concept section 7).

After a call the platform may text the caller: the booking confirmation,
the links the phone assistant promised. Only a messenger the business has
connected and the caller is already known in can carry it (Telegram first:
no messaging window and no cost; then WhatsApp, where most callers are).
"""

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId

CALLER_MESSAGE_CHANNELS: tuple[ChannelKind, ...] = (
    ChannelKind.TELEGRAM,
    ChannelKind.WHATSAPP,
    ChannelKind.MESSENGER,
    ChannelKind.INSTAGRAM,
)


def list_reachable_identities(
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
    contact: ContactDocument,
) -> list[ChannelIdentity]:
    """The caller's identities on connected messengers, best channel first."""

    # One read of the business's channels: this runs on every voice tool call.
    connected_channels: set[ChannelKind] = {
        channel.kind
        for channel in channel_repo.list_by_business(business_id)
        if channel.kind in CALLER_MESSAGE_CHANNELS
        and channel.status is ChannelStatus.CONNECTED
    }

    identities: list[ChannelIdentity] = [
        identity
        for identity in contact.channel_identities
        if identity.channel in connected_channels
    ]
    return sorted(
        identities,
        key=lambda identity: CALLER_MESSAGE_CHANNELS.index(identity.channel),
    )
