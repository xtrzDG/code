"""One entry of a customer's history across channels (Customers → a customer)."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import CallOutcome, ConversationStatus
from app.schemas.constants.customers import CustomerTimelineKind
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.conversations.constrained_integers import CallDurationSeconds
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId


class CustomerTimelineEntry(ImmutableDTO):
    """
    A conversation (by its latest message, with the summary the worker
    wrote once it went quiet), a booking (by its start), a request for a
    manager or a call; `occurred_at` orders the history. The fields of the
    other kinds are None.
    """

    kind: CustomerTimelineKind
    occurred_at: Microseconds
    channel: ChannelKind | None = None
    conversation_id: ConversationId | None = None
    conversation_status: ConversationStatus | None = None
    summary: ConversationSummaryText | None = None
    booking_id: BookingId | None = None
    booking_status: BookingStatus | None = None
    starts_at: BookingStartsAtUnixSeconds | None = None
    party_size: PartySize | None = None
    resource_id: ResourceId | None = None
    lead_id: LeadId | None = None
    lead_status: LeadStatus | None = None
    lead_type: LeadType | None = None
    call_id: CallId | None = None
    duration_seconds: CallDurationSeconds | None = None
    call_outcome: CallOutcome | None = None
