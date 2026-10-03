"""Settings → Reviews: the latest requests for feedback after visits."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import FeedbackRequestStatus, FeedbackSkipReason
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.feedback.constrained_integers import (
    ReviewLinkClickCount,
    VisitScore,
)
from app.schemas.typings.feedback.prefixed_id import FeedbackRequestId
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class FeedbackRequestPageQuery(ImmutableDTO):
    """The business's feedback requests, newest first (owners, audited)."""

    user_id: UserId
    business_id: BusinessId
    page: PageRequest = PageRequest()
    client_ip_address: ClientIpAddress | None = None


class FeedbackRequestView(ImmutableDTO):
    """
    One visit and its request: the customer (their name when known), when
    the visit ended, whether they were asked and how (or why not), their
    rating, whether they opened the review link, and the conversation and
    handoff it led to.
    """

    id: FeedbackRequestId
    booking_id: BookingId
    contact_id: ContactId
    contact_name: ContactName | None = None
    visit_ended_at: Microseconds
    status: FeedbackRequestStatus
    skip_reason: FeedbackSkipReason | None = None
    channel: ChannelKind | None = None
    sent_at: Microseconds | None = None
    score: VisitScore | None = None
    answered_at: Microseconds | None = None
    review_clicks: ReviewLinkClickCount
    conversation_id: ConversationId | None = None
    handoff_id: HandoffId | None = None
    last_error: DeliveryErrorText | None = None


class FeedbackRequestPage(ImmutableDTO):
    items: list[FeedbackRequestView]
    next_cursor: PageCursor | None = None
