"""
The texts a tool call carries, checked against their limits by the tool's
input DTO (`CustomerGivenName`, `AssistantBookingNote`, ...), as the records
downstream keep them: a booking's contact name, a lead's details.
"""

from app.schemas.typings.bookings.constrained_strings import AssistantBookingNote
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.contacts.constrained_strings import CustomerGivenName
from app.schemas.typings.contacts.strings import ContactName


def given_contact_name(name: CustomerGivenName) -> ContactName:
    """The name the customer gave, as the contact's name."""

    return ContactName(str(name))


def optional_contact_name(name: CustomerGivenName | None) -> ContactName | None:
    """The name the customer gave, if any, as the contact's name."""

    return None if name is None else given_contact_name(name)


def given_booking_note(note: AssistantBookingNote | None) -> BookingNote | None:
    """The customer's wish, as the note of a booking or a waitlist place."""

    return None if note is None else BookingNote(str(note))
