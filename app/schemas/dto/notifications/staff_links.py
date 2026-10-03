"""Notification links: the signed claims of a link and what opening one shows."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.notifications.booleans import IsStaffLinkExpired
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.users.prefixed_id import UserId


class StaffLinkClaims(ImmutableDTO):
    """
    What a notification link opens: a page of one business (a conversation,
    a request, a booking, the notification settings) until `expires_at`.
    The id that matches `target` is set; the others are None.
    """

    business_id: BusinessId
    target: StaffLinkTarget
    conversation_id: ConversationId | None = None
    lead_id: LeadId | None = None
    booking_id: BookingId | None = None
    expires_at: Microseconds


class StaffLinkQuery(ImmutableDTO):
    """A signed-in user opens a notification link of a business."""

    user_id: UserId
    business_id: BusinessId
    token: StaffLinkToken


class StaffLinkView(ImmutableDTO):
    """
    Where a link leads, for the cabinet to open (it maps the target to its
    page; a booking opens the bookings of `booking_date`). An expired link
    (`is_expired`) names no page. Every page still checks access itself.
    """

    business_id: BusinessId
    target: StaffLinkTarget
    conversation_id: ConversationId | None = None
    lead_id: LeadId | None = None
    booking_id: BookingId | None = None
    booking_date: LocalDate | None = None
    expires_at: Microseconds
    is_expired: IsStaffLinkExpired = False
