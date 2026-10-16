"""The ways to reach a customer, as the suppression list covers them."""

from collections.abc import Iterable

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.privacy.strings import SuppressedIdentityText


def phone_identity(phone_number: E164PhoneNumber) -> SuppressedIdentity:
    """A number: SMS to it, a call's text-back, its WhatsApp account."""

    return SuppressedIdentity(
        channel=ChannelKind.PHONE, value=SuppressedIdentityText(str(phone_number))
    )


def channel_identity(
    channel: ChannelKind, channel_user_id: ChannelUserId
) -> SuppressedIdentity:
    """An account in one messenger."""

    return SuppressedIdentity(
        channel=channel, value=SuppressedIdentityText(str(channel_user_id))
    )


def contact_identities(contact: ContactDocument | None) -> list[SuppressedIdentity]:
    """
    Every way to reach the customer: their numbers and their accounts in
    the channels (the owner's test chat left out). None for no contact.
    """

    if contact is None:
        return []

    phones: Iterable[E164PhoneNumber] = dict.fromkeys(
        phone
        for phone in (contact.verified_phone_number, contact.phone_number)
        if phone is not None
    )
    identities: list[SuppressedIdentity] = [phone_identity(phone) for phone in phones]
    for identity in contact.channel_identities:
        if identity.channel is not ChannelKind.OWNER_TEST:
            identities.append(
                channel_identity(identity.channel, identity.channel_user_id)
            )
            if identity.channel is ChannelKind.WHATSAPP:
                # A WhatsApp account is a number: SMS to it stops as well.
                identities.append(
                    SuppressedIdentity(
                        channel=ChannelKind.PHONE,
                        value=SuppressedIdentityText(f"+{identity.channel_user_id}"),
                    )
                )

    return list(dict.fromkeys(identities))
