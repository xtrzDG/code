from enum import StrEnum


class ResourceKind(StrEnum):
    """What is booked, as in the concept's resources table."""

    TABLE = "table"
    ROOM = "room"
    STAFF = "staff"
    ARENA = "arena"
    BAY = "bay"
    VEHICLE = "vehicle"
    SLOT = "slot"


class BookingUnit(StrEnum):
    """How a resource is booked: for a time slot or for nights (hotels)."""

    TIME_SLOT = "time_slot"
    NIGHT = "night"


class BookingStatus(StrEnum):
    """Lifecycle of a booking."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class BookingOrigin(StrEnum):
    """
    Where a booking came from besides the usual ways, for the revenue the
    assistant brought: a place freed by a cancellation that a customer on
    the waitlist took (WAITLIST), or a booking a customer made after a
    rebooking campaign invited them back (CAMPAIGN). None for every other
    booking.
    """

    WAITLIST = "waitlist"
    CAMPAIGN = "campaign"


class LeadType(StrEnum):
    """Kind of request passed to a manager."""

    BANQUET = "banquet"
    GROUP = "group"
    CORPORATE = "corporate"
    ORDER = "order"
    VIEWING = "viewing"
    OTHER = "other"


class LeadStatus(StrEnum):
    """Lifecycle of a lead."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"


class BookingReminderKind(StrEnum):
    """
    Which reminder of a booking a message is: the one the day before
    (DAY_BEFORE). A booking gets each kind once per start time, so a moved
    booking is reminded of its new time.
    """

    DAY_BEFORE = "day_before"


class BookingOrder(StrEnum):
    """
    Order of the cabinet's booking list by start time: upcoming bookings
    read earliest first, past ones latest first.
    """

    EARLIEST_FIRST = "earliest_first"
    LATEST_FIRST = "latest_first"


class BookingRefusalCode(StrEnum):
    """
    Why a booking could not be placed, as the `reasons[].code` of the error,
    so the cabinet shows the reason in the user's language.
    """

    CLOSED = "closed"
    TOO_SOON = "too_soon"
    TIME_REQUIRED = "time_required"
    TAKEN = "taken"
    PARTY_TOO_LARGE = "party_too_large"
    NO_SEATING_RESOURCE = "no_seating_resource"
    # A service, package or room type no name or id matches, or several.
    UNKNOWN_SERVICE = "unknown_service"
    AMBIGUOUS_SERVICE = "ambiguous_service"
    # A master, room or table no name or id matches, or several.
    UNKNOWN_RESOURCE = "unknown_resource"
    AMBIGUOUS_RESOURCE = "ambiguous_resource"
    # The chosen resource does not perform the chosen service.
    NOT_PERFORMED = "not_performed"


class BookingUndoRefusalCode(StrEnum):
    """
    Why the last status change of a booking could not be undone, as the
    `reasons[].code` of the error (the cabinet explains it in the user's
    language).
    """

    # No status change staff made in the cabinet to undo (none yet, the
    # customer or the assistant changed it, or it was undone already).
    NOTHING_TO_UNDO = "nothing_to_undo"
    # The booking has another status than the one the undo names.
    STATUS_CHANGED = "status_changed"
    # The undo window after the change has passed.
    UNDO_EXPIRED = "undo_expired"
    # Another booking took the freed time in the meantime.
    SLOT_TAKEN = "slot_taken"
    # The booking's place no longer exists.
    PLACE_GONE = "place_gone"


class BookingConfirmationChange(StrEnum):
    """
    What a guest's written confirmation confirms: a new booking (BOOKED)
    or a booking moved to another time (MOVED).
    """

    BOOKED = "booked"
    MOVED = "moved"


class ManagedBookingRefusalCode(StrEnum):
    """
    Why a guest's manage link (/r/{token}) cannot show or change the
    booking, as the `reasons[].code` of the error, so the page explains it
    in the guest's language.
    """

    # The link is not one this platform signed (altered or cut off).
    LINK_INVALID = "link_invalid"
    # The link was issued long enough ago that it no longer opens.
    LINK_EXPIRED = "link_expired"
    # The booking was moved or removed after the link was sent: only the
    # latest confirmation's link manages it.
    BOOKING_CHANGED = "booking_changed"
    # The booking is cancelled, completed or a no-show: nothing to change.
    NOT_ACTIVE = "not_active"
    # The booking has started or is over: it can no longer be changed here.
    ALREADY_STARTED = "already_started"
