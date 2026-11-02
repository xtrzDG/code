"""
Who asks to cancel or move a booking, and with what authority.

A staff member (`actor_id`, from the cabinet's authenticated user) may
change any booking of the business by its id, at any time. A customer
(their conversation's contact, or the phone their channel proved) may
change only their own bookings, under the online-booking rules, and staff
are told. A command naming neither is refused: missing customer fields
never fall back to staff authority. Neither is a caller on the phone: a
caller id proves nobody's identity, so a customer request that came in a
call is refused with what the agent should offer instead.
"""

from dataclasses import dataclass

from app.schemas.constants.channels import ChannelKind
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId

# Channels whose only identity is a caller id.
CALLER_ID_CHANNELS: frozenset[ChannelKind] = frozenset({ChannelKind.PHONE})
NO_REQUESTER_MESSAGE: str = (
    "A booking is changed by a staff member or by its customer; this request "
    "names neither."
)
CALLER_ID_MESSAGE: str = (
    "On a phone call the caller's number does not prove who is calling, so a "
    "booking is not cancelled or moved from a call. Offer to pass the request "
    "to a colleague, who calls back the number on the booking; the customer "
    "can also use the link in their booking confirmation."
)


@dataclass(frozen=True, slots=True)
class StaffRequester:
    """A staff member in the cabinet: any booking of the business, by its id."""

    actor_id: UserId


@dataclass(frozen=True, slots=True)
class CustomerRequester:
    """A customer: only their own bookings, under the customer rules."""

    contact_id: ContactId | None
    phone_number: E164PhoneNumber | None


type BookingRequester = StaffRequester | CustomerRequester


def identify_requester(
    actor_id: UserId | None,
    contact_id: ContactId | None,
    phone_number: E164PhoneNumber | None,
    source_channel: ChannelKind | None,
) -> BookingRequester:
    """
    The requester a cancel or reschedule command names.

    Raises:
        AccessDeniedError: the command names neither staff nor a customer,
            or a customer asks in a call.
    """

    if actor_id is not None:
        return StaffRequester(actor_id=actor_id)

    if contact_id is None and phone_number is None:
        raise AccessDeniedError(NO_REQUESTER_MESSAGE)

    if source_channel in CALLER_ID_CHANNELS:
        raise AccessDeniedError(CALLER_ID_MESSAGE)

    return CustomerRequester(contact_id=contact_id, phone_number=phone_number)


def customer_contact_of(requester: BookingRequester) -> ContactId | None:
    """The customer's contact, for a customer request; None for staff."""

    return requester.contact_id if isinstance(requester, CustomerRequester) else None


def customer_phone_of(requester: BookingRequester) -> E164PhoneNumber | None:
    """The phone the customer's channel proved; None for staff."""

    return (
        requester.phone_number if isinstance(requester, CustomerRequester) else None
    )


def staff_actor_of(requester: BookingRequester) -> UserId | None:
    """The staff member, for a staff request; None for a customer."""

    return requester.actor_id if isinstance(requester, StaffRequester) else None
