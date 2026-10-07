"""
What an announced change is about, read in its public shape: the record
(the webhook's `data`), the business event it is, the customer it names.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from base_typed_id import BasePrefixedTypedId

from app.contracts.integrations import PublicRecordReaderContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.integrations import BusinessEventType
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.integrations.business_events import BusinessEventData
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.handoffs.prefixed_id import HandoffId


@dataclass(frozen=True)
class EventSubject:
    """The record of a business event and the customer it is about."""

    event_type: BusinessEventType
    data: BusinessEventData
    # The record's id: what a once-per-record event's id is derived from.
    key: str
    contact_id: ContactId | None


def first_of[Identifier: BasePrefixedTypedId](
    ids: Sequence[BasePrefixedTypedId], kind: type[Identifier]
) -> Identifier | None:
    """The first announced id of that kind (a handoff names its conversation too)."""

    return next((item for item in ids if isinstance(item, kind)), None)


def read_event_subject(
    reader: PublicRecordReaderContract,
    business: BusinessDocument,
    event: LiveEventKind,
    ids: Sequence[BasePrefixedTypedId],
) -> EventSubject | None:
    """None when the record is gone or the change is not a business event."""

    if event in (LiveEventKind.BOOKING_CREATED, LiveEventKind.BOOKING_CHANGED):
        return booking_subject(reader, business, event, first_of(ids, BookingId))

    if event in (LiveEventKind.LEAD_CREATED, LiveEventKind.LEAD_CHANGED):
        lead_id = first_of(ids, LeadId)
        lead = None if lead_id is None else reader.lead(business, lead_id)
        if lead is None:
            return None

        event_type = (
            BusinessEventType.LEAD_CREATED
            if event is LiveEventKind.LEAD_CREATED
            else BusinessEventType.LEAD_UPDATED
        )
        return EventSubject(event_type, lead, str(lead.id), lead.contact.id)

    if event in (LiveEventKind.HANDOFF_CREATED, LiveEventKind.HANDOFF_RESOLVED):
        handoff_id = first_of(ids, HandoffId)
        handoff = None if handoff_id is None else reader.handoff(business, handoff_id)
        if handoff is None:
            return None

        event_type = (
            BusinessEventType.HANDOFF_CREATED
            if event is LiveEventKind.HANDOFF_CREATED
            else BusinessEventType.HANDOFF_RESOLVED
        )
        return EventSubject(event_type, handoff, str(handoff.id), handoff.contact.id)

    return activity_subject(reader, business, event, ids)


def booking_subject(
    reader: PublicRecordReaderContract,
    business: BusinessDocument,
    event: LiveEventKind,
    booking_id: BookingId | None,
) -> EventSubject | None:
    booking = None if booking_id is None else reader.booking(business, booking_id)
    if booking is None:
        return None

    if event is LiveEventKind.BOOKING_CREATED:
        event_type = BusinessEventType.BOOKING_CREATED
    elif booking.status is BookingStatus.CANCELLED:
        event_type = BusinessEventType.BOOKING_CANCELLED
    else:
        event_type = BusinessEventType.BOOKING_UPDATED

    return EventSubject(event_type, booking, str(booking.id), booking.contact.id)


def activity_subject(
    reader: PublicRecordReaderContract,
    business: BusinessDocument,
    event: LiveEventKind,
    ids: Sequence[BasePrefixedTypedId],
) -> EventSubject | None:
    """A conversation started or a call finished."""

    if event is LiveEventKind.CONVERSATION_STARTED:
        conversation_id = first_of(ids, ConversationId)
        conversation = (
            None
            if conversation_id is None
            else reader.conversation(business, conversation_id)
        )
        if conversation is None:
            return None

        return EventSubject(
            BusinessEventType.CONVERSATION_STARTED,
            conversation,
            str(conversation.id),
            conversation.contact.id,
        )

    if event is LiveEventKind.CALL_FINISHED:
        call_id = first_of(ids, CallId)
        call = None if call_id is None else reader.call(business, call_id)
        if call is None:
            return None

        return EventSubject(
            BusinessEventType.CALL_FINISHED,
            call,
            str(call.id),
            None if call.contact is None else call.contact.id,
        )

    return None
