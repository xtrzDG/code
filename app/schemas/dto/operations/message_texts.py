"""
Inputs of the staff and customer message texts of bookings, leads and
handoffs, and of calendar event texts.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.bookings import BookingView, LeadView
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.schemas.typings.profiles.strings import CancellationPolicyText


class StaffMessage(ImmutableDTO):
    """One notification text for one staff contact, in their language."""

    contact: ManagerContact
    text: MessageText


class BookingMessageInput(ImmutableDTO):
    """
    Customer-facing booking text (confirmation, cancellation, new time).

    `cancellation_policy` is the owner's rule from the profile, quoted as is.
    """

    business_name: BusinessName
    booking: BookingView
    booking_unit: BookingUnit
    language: LanguageTag
    cancellation_policy: CancellationPolicyText | None = None


class BookingStaffNotificationInput(ImmutableDTO):
    """Staff notification about a booking, rendered in the staff language."""

    business_name: BusinessName
    booking: BookingView
    contact_phone_display: FormattedPhoneNumber | None = None
    language: LanguageTag


class LeadStaffNotificationInput(ImmutableDTO):
    """Staff notification about a new lead."""

    business_name: BusinessName
    lead: LeadView
    contact_name: ContactName | None = None
    contact_phone_display: FormattedPhoneNumber | None = None
    language: LanguageTag


class HandoffStaffNotificationInput(ImmutableDTO):
    """Staff notification about a conversation passed to a human."""

    business_name: BusinessName
    reason: HandoffReason
    urgency: HandoffUrgency
    summary: HandoffSummary
    contact_name: ContactName | None = None
    contact_phone_display: FormattedPhoneNumber | None = None
    channel: ChannelKind
    language: LanguageTag


class HandoffCustomerMessageInput(ImmutableDTO):
    """
    What to tell the customer after a handoff. Without a reopening moment the
    business is open now (or its hours are unknown): "a colleague will reply
    soon".
    """

    language: LanguageTag
    reopens_on: LocalDate | None = None
    reopens_at: LocalTimeOfDay | None = None


class CalendarEventTextInput(ImmutableDTO):
    """Booking to describe in the owner's calendar, in the owner's language."""

    booking: BookingView
    contact_phone_display: FormattedPhoneNumber | None = None
    language: LanguageTag
