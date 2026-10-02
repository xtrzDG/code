"""
What the voice agent learns when a call starts (concept section 7).

The phone instruction has no date by design (the prompt cache), so the
call-initiation webhook gives the agent the business-local date and time,
the next days and the time zone; "tomorrow" and "this Friday" then become
dates. A caller known by the phone a channel proved also gets their name
and their next booking, so the agent can greet them and answer "what time
is my booking?". The name is customer-given text: it is put on one line,
without brackets or markup, and kept short, so it cannot pose as a rule.
"""

import re

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.channels.strings import (
    CallerNameText,
    CallUpcomingBookingText,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.conversations.turn_context import describe_local_now
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.zoned_time import load_time_zone, to_local_moment

MAX_CALLER_NAME_LENGTH: int = 60
MARKUP_CHARACTERS: re.Pattern[str] = re.compile(r"[{}\[\]<>#*_`|\\]+")
WHITESPACE: re.Pattern[str] = re.compile(r"\s+")


def find_known_caller(
    contact_repo: ContactRepoContract,
    business: BusinessDocument,
    caller_phone_number: E164PhoneNumber | None,
) -> ContactDocument | None:
    """The contact whose phone a channel proved is the caller's; never an erased one."""

    if caller_phone_number is None:
        return None

    contact: ContactDocument | None = contact_repo.find_by_verified_phone_number(
        business.id, caller_phone_number
    )
    if contact is None or contact.erased_at is not None:
        return None

    return contact


def describe_caller_name(contact: ContactDocument | None) -> CallerNameText | None:
    """The contact's name on one line, without markup, at most 60 characters."""

    if contact is None or contact.name is None:
        return None

    plain_name: str = WHITESPACE.sub(
        " ", MARKUP_CHARACTERS.sub(" ", str(contact.name))
    ).strip()
    if plain_name == "":
        return None

    return CallerNameText(plain_name[:MAX_CALLER_NAME_LENGTH].strip())


def describe_upcoming_booking(
    booking_repo: BookingRepoContract,
    resource_repo: ResourceRepoContract,
    business: BusinessDocument,
    contact: ContactDocument | None,
    now_seconds: int,
) -> CallUpcomingBookingText | None:
    """
    The caller's next real booking that has not started yet, in the
    business's time zone: "Saturday 2026-10-03 20:00, Table 4, 4 people".
    """

    if contact is None:
        return None

    upcoming: list[BookingDocument] = [
        booking
        for booking in booking_repo.list_by_business(business.id)
        if booking.contact_id == contact.id
        and booking.status in BLOCKING_BOOKING_STATUSES
        and not booking.is_sandbox
        and int(booking.starts_at) > now_seconds
    ]
    if not upcoming:
        return None

    booking: BookingDocument = min(upcoming, key=lambda item: int(item.starts_at))
    resource: ResourceDocument | None = resource_repo.get(
        business.id, booking.resource_id
    )
    parts: list[str] = [
        describe_local_now(
            to_local_moment(int(booking.starts_at), load_time_zone(business.timezone))
        )
    ]
    if resource is not None:
        parts.append(str(resource.name))

    party_size: int = int(booking.party_size)
    parts.append("1 person" if party_size == 1 else f"{party_size} people")
    return CallUpcomingBookingText(", ".join(parts))
