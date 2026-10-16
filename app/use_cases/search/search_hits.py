"""Hits of the cabinet's search: conversations and bookings of customers."""

from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.search import BookingHit, ConversationHit
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId


def read_conversation_id(text: str) -> ConversationId | None:
    try:
        return ConversationId(text)
    except ValueError, TypeError:
        return None


def read_booking_id(text: str) -> BookingId | None:
    try:
        return BookingId(text)
    except ValueError, TypeError:
        return None


def conversation_hit(
    conversation: ConversationDocument, contacts: dict[ContactId, ContactDocument]
) -> ConversationHit:
    contact: ContactDocument | None = contacts.get(conversation.contact_id)
    return ConversationHit(
        id=conversation.id,
        contact_id=conversation.contact_id,
        contact_name=None if contact is None else contact.name,
        channel=conversation.channel,
        status=conversation.status,
        last_message_at=conversation.last_message_at,
    )


def booking_hit(
    booking: BookingDocument, contacts: dict[ContactId, ContactDocument]
) -> BookingHit:
    contact: ContactDocument | None = contacts.get(booking.contact_id)
    return BookingHit(
        id=booking.id,
        contact_id=booking.contact_id,
        contact_name=None if contact is None else contact.name,
        starts_at=booking.starts_at,
        status=booking.status,
        party_size=booking.party_size,
        source_channel=booking.source_channel,
    )


def without_duplicates[Item: ConversationDocument | BookingDocument](
    items: list[Item],
) -> list[Item]:
    """The items in order, each id once."""

    seen: set[str] = set()
    kept: list[Item] = []
    for item in items:
        if str(item.id) not in seen:
            seen.add(str(item.id))
            kept.append(item)

    return kept
