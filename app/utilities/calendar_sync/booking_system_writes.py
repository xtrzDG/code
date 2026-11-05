"""
What a booking should look like in the booking system of its resource, and
how a write there is recorded: the draft written (the guest's name, the
business's zone, the customer's language, the platform's mark), whether a
booking written before still matches, and the write status the resource's
calendar card shows.
"""

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.calendar_sync import (
    BookingSystemBookingRef,
    BookingSystemLink,
    BookingSystemWriteStatus,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.calendar_sync.busy_reads import BookingSystemBookingDraft
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.bookings.constrained_strings import CalendarSyncErrorSummary
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.calendar_sync.strings import BookingSystemBookingId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.owner_texts import owner_text
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES

# The name a guest who gave none has in the booking system (the business
# reads it there, in its owner's language).
GUEST_WITHOUT_NAME: LocalizedText = owner_text(
    "calendar_sync.booking_system.guest_without_name"
)
MAX_DETAIL_LENGTH: int = 300
# Reasons a retry cannot change: the key was refused, the event type is gone.
FINAL_PROBLEMS: frozenset[CalendarSyncProblem] = frozenset(
    {CalendarSyncProblem.ACCESS_DENIED, CalendarSyncProblem.NOT_FOUND}
)


def is_wanted(booking: BookingDocument, system: BookingSystemLink | None) -> bool:
    """A real booking that takes its time, of a resource that follows a system."""

    return (
        system is not None
        and not booking.is_sandbox
        and booking.status in BLOCKING_BOOKING_STATUSES
    )


def is_written_as_now(
    written: BookingSystemBookingRef,
    booking: BookingDocument,
    system: BookingSystemLink | None,
) -> bool:
    """The booking written before is still the booking: same place, same time."""

    return (
        system is not None
        and written.kind is system.kind
        and written.resource_id == booking.resource_id
        and int(written.starts_at) == int(booking.starts_at)
        and int(written.ends_at) == int(booking.ends_at)
    )


def booking_system_draft(
    booking: BookingDocument,
    contact: ContactDocument | None,
    business: BusinessDocument,
    resolver: LocalizedTextResolverContract,
) -> BookingSystemBookingDraft:
    language: LanguageTag = (
        booking.language
        or (None if contact is None else contact.language)
        or business.default_language
    )
    name: ContactName | None = None if contact is None else contact.name
    return BookingSystemBookingDraft(
        starts_at=BusyStartsAtUnixSeconds(int(booking.starts_at)),
        ends_at=BusyEndsAtUnixSeconds(int(booking.ends_at)),
        guest_name=name
        or ContactName(
            str(resolver.resolve(GUEST_WITHOUT_NAME, business.owner_language))
        ),
        time_zone=business.timezone,
        language=language,
        platform_booking_id=booking.id,
    )


def written_ref(
    system: BookingSystemLink,
    booking: BookingDocument,
    external_id: BookingSystemBookingId,
    now: Microseconds,
) -> BookingSystemBookingRef:
    return BookingSystemBookingRef(
        kind=system.kind,
        resource_id=booking.resource_id,
        booking_id=external_id,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        written_at=now,
    )


def write_succeeded(
    status: BookingSystemWriteStatus, now: Microseconds
) -> BookingSystemWriteStatus:
    """A write went through: the last failure is cleared."""

    return BookingSystemWriteStatus(
        last_written_at=now, last_failed_at=status.last_failed_at
    )


def write_failed(
    status: BookingSystemWriteStatus,
    now: Microseconds,
    problem: CalendarSyncProblem,
    detail: str,
) -> BookingSystemWriteStatus:
    """A write failed: its reason, keeping when one last went through."""

    text: str = " ".join(detail.split())[:MAX_DETAIL_LENGTH] or problem.value
    return BookingSystemWriteStatus(
        last_written_at=status.last_written_at,
        last_failed_at=now,
        problem=problem,
        problem_detail=CalendarSyncErrorSummary(text),
    )
