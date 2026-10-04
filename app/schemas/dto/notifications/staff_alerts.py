"""
Staff alerts: an event (handoff, lead, booking) that every staff contact
and every subscribed device of a business hears about, each in its own
language and with as much as its channel may show.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import LeadType
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffUrgency,
    ManagerContactChannel,
)
from app.schemas.constants.notifications import (
    StaffAlertEvent,
    StaffBookingChange,
    StaffLinkTarget,
    StaffTextStyle,
)
from app.schemas.dto.bookings import BookingView
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.booleans import IsUrgentStaffAlert
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    PushNotificationTag,
    StaffAlertSubject,
)
from app.schemas.typings.notifications.prefixed_id import PushSubscriptionId
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.schemas.typings.users.prefixed_id import UserId


class StaffAlertBrief(ImmutableDTO):
    """
    An alert as a locked screen may show it: a title and one line, nothing
    about the customer (no name, phone or transcript).
    """

    title: StaffAlertTitle
    detail: StaffAlertDetail | None = None


class StaffAlert(ImmutableDTO):
    """
    One event to tell staff about, and the page its link opens: a
    conversation, a request or a booking. `is_urgent` alerts (urgent
    handoffs) come through quiet hours; `tag` lets a device replace an
    older notification about the same thing. An alert with a `subject`
    reaches each recipient once however often it is raised (a handoff is
    always once per handoff); `contact_channels` limits the staff contacts
    it goes to (None: every channel). An alert without an `event` (a
    milestone of the business, such as its first booking) is news for
    everyone it goes to, whatever events they chose.
    """

    business_id: BusinessId
    event: StaffAlertEvent | None = None
    target: StaffLinkTarget
    conversation_id: ConversationId | None = None
    lead_id: LeadId | None = None
    booking_id: BookingId | None = None
    handoff_id: HandoffId | None = None
    is_urgent: IsUrgentStaffAlert = False
    tag: PushNotificationTag
    subject: StaffAlertSubject | None = None
    contact_channels: list[ManagerContactChannel] | None = None


class HandoffBrief(ImmutableDTO):
    """Why a conversation went to a person and how urgently."""

    reason: HandoffReason
    urgency: HandoffUrgency


class LeadBrief(ImmutableDTO):
    """The kind of a request and the date it is for, when given."""

    lead_type: LeadType
    requested_date: LocalDate | None = None


class BookingBrief(ImmutableDTO):
    """A booking and what happened to it."""

    booking: BookingView
    change: StaffBookingChange


class StaffAlertBriefInput(ImmutableDTO):
    """The brief of one alert in one language; exactly one fact is set."""

    business_name: BusinessName
    language: LanguageTag
    handoff: HandoffBrief | None = None
    lead: LeadBrief | None = None
    booking: BookingBrief | None = None


class StaffNotificationTextInput(ImmutableDTO):
    """
    The text one recipient gets: the detailed text (DETAILED) or the brief
    (BRIEF), and the link line in the recipient's language.
    """

    style: StaffTextStyle
    language: LanguageTag
    detailed: MessageText | None = None
    brief: StaffAlertBrief | None = None
    link: CabinetDeepLink | None = None


class PushNotification(ImmutableDTO):
    """
    A notification for one device of a cabinet user, held until
    `deliver_after` (quiet hours). One about a handoff is queued once per
    handoff and device, and its delivery counts for the handoff like a
    contact's.
    """

    business_id: BusinessId
    subscription_id: PushSubscriptionId
    user_id: UserId
    brief: StaffAlertBrief
    link: CabinetDeepLink | None = None
    tag: PushNotificationTag | None = None
    handoff_id: HandoffId | None = None
    subject: StaffAlertSubject | None = None
    is_urgent: IsUrgentStaffAlert = False
    deliver_after: Microseconds | None = None
