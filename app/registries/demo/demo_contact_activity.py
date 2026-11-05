"""
Each demo customer's latest activity (`last_seen_at`, the order of the
customer list), from what the story recorded for them: the last message of
their conversations and the bookings and requests made for them, outside
the owner's test chat. The use cases keep it the same way for real
customers (`app/use_cases/shared/contact_activity.py`); the demo writes its
records directly, so it sets it once at the end.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.contacts.prefixed_id import ContactId


def mark_demo_contacts_seen(
    contacts: Sequence[ContactDocument],
    conversations: Sequence[ConversationDocument],
    bookings: Sequence[BookingDocument],
    leads: Sequence[LeadDocument],
) -> None:
    """Move every customer's `last_seen_at` on to their latest record."""

    moments: list[tuple[ContactId, Microseconds]] = [
        *(
            (conversation.contact_id, conversation.last_message_at)
            for conversation in conversations
            if not conversation.is_sandbox
        ),
        *(
            (booking.contact_id, booking.created_at)
            for booking in bookings
            if not booking.is_sandbox
        ),
        *((lead.contact_id, lead.created_at) for lead in leads if not lead.is_sandbox),
    ]
    latest: dict[ContactId, int] = {}
    for contact_id, moment in moments:
        latest[contact_id] = max(latest.get(contact_id, 0), int(moment))

    for contact in contacts:
        if contact.is_test_only or contact.id not in latest:
            continue

        seen: int = int(contact.last_seen_at or contact.created_at)
        contact.last_seen_at = Microseconds(max(seen, latest[contact.id]))
