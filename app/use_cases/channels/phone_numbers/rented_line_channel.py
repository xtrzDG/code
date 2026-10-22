"""The business's phone channel carries the number the platform rents for it."""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.telephony.constrained_strings import RentedLineNumber
from app.utilities.channels.delivery_targets import find_business_channel


def find_phone_channel(
    channel_repo: ChannelRepoContract, business_id: BusinessId
) -> ChannelDocument | None:
    return find_business_channel(channel_repo, business_id, ChannelKind.PHONE)


def connected_number(channel: ChannelDocument | None) -> ChannelExternalId | None:
    """The number a phone channel is connected with (None: off or not set)."""

    if channel is None or channel.status is ChannelStatus.DISABLED:
        return None

    return channel.external_id


def connect_rented_line(
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
    phone_number: RentedLineNumber,
    now: Microseconds,
) -> tuple[ChannelDocument, bool]:
    """
    Connect the phone channel with the rented number (calls find their
    business by it); True when the channel is new.
    """

    existing: ChannelDocument | None = find_phone_channel(channel_repo, business_id)
    channel: ChannelDocument = existing or ChannelDocument(
        business_id=business_id,
        kind=ChannelKind.PHONE,
        created_at=now,
        updated_at=now,
    )
    channel.external_id = ChannelExternalId(str(phone_number))
    channel.encrypted_secret = None
    channel.status = ChannelStatus.CONNECTED
    channel.last_error = None
    channel.last_error_at = None
    channel.last_error_reason = None
    channel.updated_at = now
    channel_repo.save(channel)
    return channel, existing is None


def disconnect_rented_line(
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
    phone_number: RentedLineNumber,
    now: Microseconds,
) -> bool:
    """
    Turn the phone channel off when it still carries this number (a number
    given back for want of payment); True when it was turned off now.
    """

    channel: ChannelDocument | None = find_phone_channel(channel_repo, business_id)
    if channel is None or connected_number(channel) != ChannelExternalId(
        str(phone_number)
    ):
        return False

    channel.status = ChannelStatus.DISABLED
    channel.external_id = None
    channel.encrypted_secret = None
    channel.updated_at = now
    channel_repo.save(channel)
    return True
