"""
A customer's history across channels as one list, the latest first:
conversations by their latest message, bookings by their start (so the
upcoming ones lead), requests by when they came in, calls by when they
started. Test chats are not in the records it is built from.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.customers import CustomerTimelineKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.contacts import ContactActivity
from app.schemas.dto.customers.customer_timeline import CustomerTimelineEntry

MICROSECONDS_PER_SECOND: int = 1_000_000


def build_timeline(
    activity: ContactActivity, calls: list[CallDocument]
) -> list[CustomerTimelineEntry]:
    entries: list[CustomerTimelineEntry] = [
        *(conversation_entry(item) for item in activity.conversations),
        *(booking_entry(item) for item in activity.bookings),
        *(lead_entry(item) for item in activity.leads),
        *(call_entry(item) for item in calls),
    ]
    return sorted(entries, key=lambda entry: int(entry.occurred_at), reverse=True)


def conversation_entry(conversation: ConversationDocument) -> CustomerTimelineEntry:
    return CustomerTimelineEntry(
        kind=CustomerTimelineKind.CONVERSATION,
        occurred_at=conversation.last_message_at,
        channel=conversation.channel,
        conversation_id=conversation.id,
        conversation_status=conversation.status,
        summary=conversation.summary,
    )


def booking_entry(booking: BookingDocument) -> CustomerTimelineEntry:
    return CustomerTimelineEntry(
        kind=CustomerTimelineKind.BOOKING,
        occurred_at=Microseconds(int(booking.starts_at) * MICROSECONDS_PER_SECOND),
        channel=booking.source_channel,
        conversation_id=booking.conversation_id,
        booking_id=booking.id,
        booking_status=booking.status,
        starts_at=booking.starts_at,
        party_size=booking.party_size,
        resource_id=booking.resource_id,
    )


def lead_entry(lead: LeadDocument) -> CustomerTimelineEntry:
    return CustomerTimelineEntry(
        kind=CustomerTimelineKind.LEAD,
        occurred_at=lead.created_at,
        channel=lead.source_channel,
        conversation_id=lead.conversation_id,
        lead_id=lead.id,
        lead_status=lead.status,
        lead_type=lead.lead_type,
    )


def call_entry(call: CallDocument) -> CustomerTimelineEntry:
    return CustomerTimelineEntry(
        kind=CustomerTimelineKind.CALL,
        occurred_at=call.started_at,
        conversation_id=call.conversation_id,
        call_id=call.id,
        duration_seconds=call.duration_seconds,
        call_outcome=call.outcome,
    )
