"""
The contact of a phone call. A caller id proves nobody's identity (anyone
can send any number), so a call never reaches a contact by a verified
phone, never creates a contact with one and never overwrites one.

A call joins, for continuity, only a call-only contact: one found by the
call's PHONE identity (the caller's number, or the call's id for a
withheld number) whose identities are all PHONE ones, i.e. a caller known
from earlier calls from the same number and from nothing else. A contact a
channel proved (WhatsApp, Telegram, a web chat, ...) is never joined: its
bookings, memory and name stay out of reach of a faked number, and the
call gets a contact of its own instead.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


def whatsapp_user_id(phone_number: E164PhoneNumber) -> ChannelUserId:
    """WhatsApp names a customer by the international digits of their number."""

    return ChannelUserId(str(phone_number).removeprefix("+"))


def contacts_holding_number(
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
    phone_number: E164PhoneNumber,
) -> list[ContactDocument]:
    """
    Every contact of the business that holds the number: a proved or a
    given phone, the call-only contact of its calls (its PHONE identity),
    the per-call contacts and the WhatsApp customer a text-back writes to.
    Only checks that refuse the number read them (a block, a STOP): a
    caller id may count against a customer, never for one.
    """

    found: list[ContactDocument | None] = [
        contact_repo.find_by_verified_phone_number(business_id, phone_number),
        contact_repo.find_by_channel_identity(
            business_id, ChannelKind.PHONE, ChannelUserId(str(phone_number))
        ),
        contact_repo.find_by_channel_identity(
            business_id, ChannelKind.WHATSAPP, whatsapp_user_id(phone_number)
        ),
        *contact_repo.list_by_phone_number(business_id, phone_number),
    ]
    holders: dict[ContactId, ContactDocument] = {}
    for contact in found:
        if contact is not None:
            holders.setdefault(contact.id, contact)

    return list(holders.values())


def is_call_only_contact(contact: ContactDocument) -> bool:
    """A contact known only from phone calls (every identity is PHONE)."""

    return all(
        identity.channel is ChannelKind.PHONE for identity in contact.channel_identities
    )


def find_or_create_call_contact(
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
    caller: E164PhoneNumber | None,
    call_user_id: ChannelUserId,
    now: Microseconds,
) -> ContactDocument:
    """
    The call-only contact of the caller's number, else a new contact with
    the number as its phone (staff call it back) and no verified phone.
    A number some proven contact also holds as a PHONE identity (a missed
    call's text-back) gives the new contact the call's own id instead, so
    later calls from it find nobody either.
    """

    identity = ChannelIdentity(
        channel=ChannelKind.PHONE,
        channel_user_id=call_user_id if caller is None else ChannelUserId(str(caller)),
    )
    found: ContactDocument | None = contact_repo.find_by_channel_identity(
        business_id, identity.channel, identity.channel_user_id
    )
    if found is not None and is_call_only_contact(found):
        return found

    contact = ContactDocument(
        business_id=business_id,
        phone_number=caller,
        verified_phone_number=None,
        channel_identities=[
            identity
            if found is None
            else ChannelIdentity(
                channel=ChannelKind.PHONE, channel_user_id=call_user_id
            )
        ],
        created_at=now,
        updated_at=now,
    )
    contact_repo.save(contact)
    return contact
