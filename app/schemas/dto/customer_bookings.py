"""The customer's own bookings, as the list_my_bookings tool reads them."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.bookings import BookingStatus
from app.schemas.dto.bookings import BookingView
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class CustomerBookingsQuery(ImmutableDTO):
    """
    The customer of a conversation: their contact and the phone their
    channel proved (never a phone they typed), in the conversation's
    sandbox mode.
    """

    business_id: BusinessId
    contact_id: ContactId
    verified_phone_number: E164PhoneNumber | None = None
    is_sandbox: IsSandboxConversation = False


class CustomerBookingList(ImmutableDTO):
    """Their bookings not over yet, the soonest first (cancelled ones marked)."""

    bookings: list[BookingView] = Field(default_factory=list[BookingView])


class ContactBookingLookup(ImmutableDTO):
    """
    Which of a customer's bookings to read by their contacts (the indexed
    `contact_id` and `ends_at`): those of `contact_ids` in `statuses` and
    the sandbox mode that have not ended at `ends_after`, the soonest
    first, at most `limit`.
    """

    contact_ids: tuple[ContactId, ...]
    statuses: tuple[BookingStatus, ...]
    is_sandbox: IsSandboxConversation
    ends_after: BookingSearchBoundSeconds
    limit: DocumentQueryLimit
