"""The contact a customer message comes from: found, merged or created."""

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.dto.conversations import InboundMessage


def resolve_contact(
    contact_repo: ContactRepoContract,
    business: BusinessDocument,
    message: InboundMessage,
    is_sandbox: bool,
    now: Microseconds,
) -> ContactDocument:
    """
    By channel identity, then by a phone the channel proved (only a contact
    whose own phone is proved the same way; never for sandbox messages),
    else a new one; missing name, phone and identity are added, and a phone
    the channel proved is remembered as verified.
    """

    contact: ContactDocument | None = contact_repo.find_by_channel_identity(
        business.id, message.channel, message.channel_user_id
    )
    if contact is None and not is_sandbox and message.contact_phone_number is not None:
        # Only a contact whose phone a channel proved is the same person;
        # a phone someone typed into a chat proves nothing.
        contact = contact_repo.find_by_verified_phone_number(
            business.id, message.contact_phone_number
        )

    identity = ChannelIdentity(
        channel=message.channel,
        channel_user_id=message.channel_user_id,
    )
    if contact is None:
        contact = ContactDocument(
            business_id=business.id,
            name=message.contact_name,
            phone_number=message.contact_phone_number,
            verified_phone_number=(
                None if is_sandbox else message.contact_phone_number
            ),
            channel_identities=[identity],
            created_at=now,
            updated_at=now,
        )
        contact_repo.save(contact)
        return contact

    is_changed: bool = False
    if identity not in contact.channel_identities:
        contact.channel_identities.append(identity)
        is_changed = True

    if contact.name is None and message.contact_name is not None:
        contact.name = message.contact_name
        is_changed = True

    if contact.phone_number is None and message.contact_phone_number is not None:
        contact.phone_number = message.contact_phone_number
        is_changed = True

    if (
        not is_sandbox
        and message.contact_phone_number is not None
        and contact.verified_phone_number != message.contact_phone_number
    ):
        contact.verified_phone_number = message.contact_phone_number
        is_changed = True

    if is_changed:
        contact.updated_at = now
        contact_repo.save(contact)

    return contact
